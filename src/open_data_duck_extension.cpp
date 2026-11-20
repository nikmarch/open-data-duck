#define DUCKDB_EXTENSION_MAIN

#include "open_data_duck_extension.hpp"
#include "open_data_duck_registry.generated.hpp"
#include "duckdb.hpp"
#include "duckdb/common/exception.hpp"
#include "duckdb/common/json_document.hpp"
#include "duckdb/common/string_util.hpp"
#include "duckdb/common/vector_operations/unary_executor.hpp"
#include "duckdb/function/scalar_function.hpp"
#include "duckdb/function/table_function.hpp"
#include "duckdb/function/replacement_scan.hpp"
#include "duckdb/catalog/default/default_views.hpp"
#include "duckdb/catalog/duck_catalog.hpp"
#include "duckdb/catalog/catalog_entry/duck_schema_entry.hpp"
#include "duckdb/catalog/catalog_entry/view_catalog_entry.hpp"
#include "duckdb/main/client_config.hpp"
#include "duckdb/main/config.hpp"
#include "duckdb/main/connection.hpp"
#include "duckdb/main/database.hpp"
#include "duckdb/main/attached_database.hpp"
#include "duckdb/main/extension/extension_loader.hpp"
#include "duckdb/parser/parser.hpp"
#include "duckdb/parser/expression/constant_expression.hpp"
#include "duckdb/parser/expression/function_expression.hpp"
#include "duckdb/parser/parsed_data/attach_info.hpp"
#include "duckdb/parser/tableref.hpp"
#include "duckdb/parser/tableref/table_function_ref.hpp"
#include "duckdb/planner/expression/bound_function_expression.hpp"
#include "duckdb/storage/storage_extension.hpp"
#include "duckdb/transaction/duck_transaction_manager.hpp"
#include <duckdb/parser/parsed_data/create_scalar_function_info.hpp>

#include <cctype>
#include <mutex>
#include <unordered_map>

namespace duckdb {

//===--------------------------------------------------------------------===//
// Embedded registry (issue #31 contract, parsed once per process)
//===--------------------------------------------------------------------===//

struct OpenDataSource {
	string id;
	string name;
	string source_type;
	string status;
	string description;
	string authority;
	string homepage;
	string license_url;
	string attribution;
	vector<string> tags;
	vector<string> extensions;
	//! duckdb.tables.namespace: odd.<provider>.<version> prefix of this source's data tables.
	string tables_namespace;
	//! duckdb.tables.discover_sql: SQL returning (name, reader, path) rows, with {release} substituted.
	string tables_discover_sql;
	string install;
	string example_query;
	string validation_query;
	//! release.latest.resolve_sql: SQL returning the current release id of a `latest` table.
	string latest_resolve_sql;
	//! release.pinned.duckdb_setting: user variable that pins the release instead.
	string pinned_variable;
	//! Casefolded haystack used by open_data_search(); mirrors odd.registry.Source.search_text().
	string search_text;
};

static string JsonString(const JSONValue &object, const string &key) {
	auto member = object.GetMember(key);
	if (!member.IsValid() || !member.IsString()) {
		return string();
	}
	return member.GetString();
}

static vector<string> JsonStringArray(const JSONValue &object, const string &key) {
	vector<string> result;
	auto member = object.GetMember(key);
	if (!member.IsValid() || !member.IsArray()) {
		return result;
	}
	member.IterateArray([&](JSONValue item) {
		if (item.IsString()) {
			result.push_back(item.GetString());
		}
	});
	return result;
}

static string Stripped(string value) {
	StringUtil::Trim(value);
	return value;
}

//===--------------------------------------------------------------------===//
// Source-controlled SQL sandbox
//===--------------------------------------------------------------------===//

static vector<string> TokenizeSourceSql(const string &sql) {
	vector<string> tokens;
	string current;
	for (auto c : sql) {
		if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_') {
			current.push_back(char(std::tolower(static_cast<unsigned char>(c))));
			continue;
		}
		if (!current.empty()) {
			tokens.push_back(current);
			current.clear();
		}
	}
	if (!current.empty()) {
		tokens.push_back(current);
	}
	return tokens;
}

static bool SourceSqlHasToken(const vector<string> &tokens, const string &needle) {
	for (auto &token : tokens) {
		if (token == needle) {
			return true;
		}
	}
	return false;
}

static void ValidateSourceControlledSql(const string &source_id, const string &purpose, const string &sql) {
	auto stripped = Stripped(sql);
	while (!stripped.empty() && stripped.back() == ';') {
		stripped.pop_back();
		stripped = Stripped(stripped);
	}
	if (stripped.empty()) {
		throw InvalidInputException("open_data_duck: source '%s' has empty %s SQL", source_id, purpose);
	}
	if (StringUtil::Contains(stripped, ";")) {
		throw InvalidInputException("open_data_duck: source '%s' %s SQL must be a single statement", source_id,
		                            purpose);
	}

	auto tokens = TokenizeSourceSql(stripped);
	if (!SourceSqlHasToken(tokens, "select") && !SourceSqlHasToken(tokens, "with")) {
		throw InvalidInputException("open_data_duck: source '%s' %s SQL must be a SELECT query", source_id,
		                            purpose);
	}
	const char *blocked_tokens[] = {"attach", "detach", "load",   "install", "create", "drop",  "alter",
	                                "insert", "update", "delete", "copy",    "export", "import", "call",
	                                "pragma", "set",    "reset",  "vacuum",  "checkpoint"};
	for (auto token : blocked_tokens) {
		if (SourceSqlHasToken(tokens, token)) {
			throw InvalidInputException("open_data_duck: source '%s' %s SQL uses blocked token '%s'", source_id,
			                            purpose, token);
		}
	}
	const char *secret_tokens[] = {"getvariable", "current_setting", "duckdb_settings", "duckdb_secrets"};
	for (auto token : secret_tokens) {
		if (SourceSqlHasToken(tokens, token)) {
			throw InvalidInputException("open_data_duck: source '%s' %s SQL may not inspect session state via '%s'",
			                            source_id, purpose, token);
		}
	}
}

static unique_ptr<QueryResult> RunSourceControlledSql(const OpenDataSource &source, const string &purpose, const string &sql) {
	ValidateSourceControlledSql(source.id, purpose, sql);
	DuckDB database(nullptr);
	Connection connection(database);
	return connection.Query(sql);
}

static void JsonTables(const JSONValue &duckdb_value, OpenDataSource &source) {
	auto tables_value = duckdb_value.GetMember("tables");
	if (!tables_value.IsValid() || !tables_value.IsObject()) {
		return;
	}
	auto ns = Stripped(JsonString(tables_value, "namespace"));
	auto discover_sql = Stripped(JsonString(tables_value, "discover_sql"));
	if (ns.empty() || discover_sql.empty()) {
		return;
	}
	source.tables_namespace = std::move(ns);
	source.tables_discover_sql = std::move(discover_sql);
}

static string BuildSearchText(const OpenDataSource &source) {
	vector<string> parts {source.id,       source.name,        source.description, source.status,
	                      source.source_type, source.authority, source.homepage,    source.license_url,
	                      source.attribution};
	for (auto &tag : source.tags) {
		parts.push_back(tag);
	}
	for (auto &extension : source.extensions) {
		parts.push_back(extension);
	}
	parts.push_back(source.tables_namespace);
	parts.push_back(source.example_query);
	return StringUtil::Lower(StringUtil::Join(parts, " "));
}

static vector<OpenDataSource> ParseEmbeddedRegistry() {
	auto json = string(open_data_duck::REGISTRY_JSON);
	auto document = JSONDocument::Parse(json.c_str(), json.size());
	auto root = document->GetRoot();
	auto sources_value = root.GetMember("sources");
	if (!sources_value.IsValid() || !sources_value.IsArray()) {
		throw InternalException("open_data_duck: embedded registry JSON has no 'sources' array");
	}

	vector<OpenDataSource> sources;
	sources_value.IterateArray([&](JSONValue item) {
		OpenDataSource source;
		source.id = JsonString(item, "id");
		source.name = JsonString(item, "name");
		source.source_type = JsonString(item, "source_type");
		source.status = JsonString(item, "status");
		source.description = JsonString(item, "description");
		source.authority = JsonString(item, "authority");
		source.homepage = JsonString(item, "homepage");
		source.license_url = JsonString(item, "license_url");
		source.attribution = JsonString(item, "attribution");
		source.tags = JsonStringArray(item, "tags");

		auto duckdb_value = item.GetMember("duckdb");
		if (duckdb_value.IsValid() && duckdb_value.IsObject()) {
			source.extensions = JsonStringArray(duckdb_value, "extensions");
			JsonTables(duckdb_value, source);
			source.install = JsonString(duckdb_value, "install");
			source.example_query = JsonString(duckdb_value, "example_query");
			source.validation_query = JsonString(duckdb_value, "validation_query");
		}
		auto release_value = item.GetMember("release");
		if (release_value.IsValid() && release_value.IsObject()) {
			auto latest_value = release_value.GetMember("latest");
			if (latest_value.IsValid() && latest_value.IsObject()) {
				source.latest_resolve_sql = Stripped(JsonString(latest_value, "resolve_sql"));
			}
			auto pinned_value = release_value.GetMember("pinned");
			if (pinned_value.IsValid() && pinned_value.IsObject()) {
				source.pinned_variable = Stripped(JsonString(pinned_value, "duckdb_setting"));
			}
		}
		source.search_text = BuildSearchText(source);
		sources.push_back(std::move(source));
	});

	if (sources.size() != static_cast<size_t>(open_data_duck::REGISTRY_SOURCE_COUNT)) {
		throw InternalException("open_data_duck: embedded registry declares %d sources but JSON has %llu",
		                        open_data_duck::REGISTRY_SOURCE_COUNT, (unsigned long long)sources.size());
	}
	return sources;
}

static const vector<OpenDataSource> &GetEmbeddedRegistry() {
	static const vector<OpenDataSource> registry = ParseEmbeddedRegistry();
	return registry;
}

static const OpenDataSource *FindSource(const string &source_id) {
	for (auto &source : GetEmbeddedRegistry()) {
		if (source.id == source_id) {
			return &source;
		}
	}
	return nullptr;
}

static const OpenDataSource &FindSourceOrThrow(const string &source_id) {
	auto source = FindSource(source_id);
	if (source) {
		return *source;
	}
	throw InvalidInputException("open_data_duck: unknown source id '%s'. Use open_data_sources() or "
	                            "open_data_search('<terms>') to list known ids.",
	                            source_id);
}

//! Mirrors odd.registry.render_source_sql(): install statements, blank line, query, trailing newline.
static string RenderSourceSql(const OpenDataSource &source, bool validation) {
	vector<string> statements;
	auto install = Stripped(source.install);
	if (!install.empty()) {
		statements.push_back(install);
	}
	auto query = Stripped(validation ? source.validation_query : source.example_query);
	if (query.empty()) {
		throw InvalidInputException("open_data_duck: source '%s' has no duckdb.%s", source.id,
		                            validation ? "validation_query" : "example_query");
	}
	statements.push_back(query);
	return StringUtil::Join(statements, "\n\n") + "\n";
}

//===--------------------------------------------------------------------===//
// Latest release resolution
//===--------------------------------------------------------------------===//

//! Release id a `latest` table reads from. Precedence: the pinned user variable
//! (SET VARIABLE overture_release = '...'), then a process-wide cache, then
//! release.latest.resolve_sql run once on its own connection and cached.
static string ResolveRelease(ClientContext &context, const OpenDataSource &source) {
	if (!source.pinned_variable.empty()) {
		Value pinned;
		if (ClientConfig::GetConfig(context).GetUserVariable(source.pinned_variable, pinned) && !pinned.IsNull()) {
			return pinned.ToString();
		}
	}
	if (source.latest_resolve_sql.empty()) {
		throw InvalidInputException("open_data_duck: source '%s' has no release.latest.resolve_sql", source.id);
	}

	static std::mutex cache_lock;
	static std::unordered_map<string, string> cache;
	{
		std::lock_guard<std::mutex> guard(cache_lock);
		auto entry = cache.find(source.id);
		if (entry != cache.end()) {
			return entry->second;
		}
	}

	auto result = RunSourceControlledSql(source, "release resolution", source.latest_resolve_sql);
	string release;
	if (!result->HasError()) {
		for (auto &row : *result) {
			if (!row.IsNull(0)) {
				release = row.GetValue<string>(0);
			}
			break;
		}
	}
	if (release.empty()) {
		throw InvalidInputException("open_data_duck: could not resolve the latest release for '%s' (%s). Pin one "
		                            "with SET VARIABLE %s = '<release>'.",
		                            source.id, result->HasError() ? result->GetError() : "query returned no release",
		                            source.pinned_variable);
	}

	std::lock_guard<std::mutex> guard(cache_lock);
	cache.emplace(source.id, release);
	return release;
}

//===--------------------------------------------------------------------===//
// Table discovery
//===--------------------------------------------------------------------===//

struct OpenDataTable {
	string name;
	string reader;
	string path;
};

struct DiscoveredTables {
	string release;
	vector<OpenDataTable> tables;
};

//! Rows of duckdb.tables.discover_sql for the source's current release. Runs once per
//! process and source@release on its own connection, then serves from cache. Pinning a
//! different release (SET VARIABLE ...) gets its own cache entry.
static DiscoveredTables DiscoverTables(ClientContext &context, const OpenDataSource &source) {
	if (source.tables_discover_sql.empty()) {
		throw InvalidInputException("open_data_duck: source '%s' has no duckdb.tables.discover_sql", source.id);
	}
	DiscoveredTables result;
	auto sql = source.tables_discover_sql;
	if (StringUtil::Contains(sql, "{release}")) {
		result.release = ResolveRelease(context, source);
		sql = StringUtil::Replace(sql, "{release}", result.release);
	}
	const auto cache_key = source.id + "@" + result.release;

	static std::mutex cache_lock;
	static std::unordered_map<string, DiscoveredTables> cache;
	{
		std::lock_guard<std::mutex> guard(cache_lock);
		auto entry = cache.find(cache_key);
		if (entry != cache.end()) {
			return entry->second;
		}
	}

	auto query_result = RunSourceControlledSql(source, "table discovery", sql);
	if (query_result->HasError()) {
		throw InvalidInputException("open_data_duck: could not discover tables for '%s': %s", source.id,
		                            query_result->GetError());
	}
	if (query_result->ColumnCount() < 3) {
		throw InvalidInputException("open_data_duck: duckdb.tables.discover_sql for '%s' must return (name, reader, path)",
		                            source.id);
	}
	for (auto &row : *query_result) {
		if (row.IsNull(0) || row.IsNull(2)) {
			continue;
		}
		OpenDataTable table;
		table.name = row.GetValue<string>(0);
		table.reader = row.IsNull(1) ? string() : row.GetValue<string>(1);
		table.path = row.GetValue<string>(2);
		if (table.name.empty() || table.path.empty()) {
			continue;
		}
		if (table.reader.empty()) {
			table.reader = "read_parquet";
		}
		result.tables.push_back(std::move(table));
	}

	std::lock_guard<std::mutex> guard(cache_lock);
	cache[cache_key] = result;
	return result;
}

//===--------------------------------------------------------------------===//
// Scalar functions
//===--------------------------------------------------------------------===//

static void OpenDataDuckPingFunction(DataChunk &args, ExpressionState &state, Vector &result) {
	result.SetVectorType(VectorType::CONSTANT_VECTOR);
	auto data = ConstantVector::GetData<string_t>(result);
	data[0] = StringVector::AddString(result, "open_data_duck: pong");
}

static void OpenDataDuckVersionFunction(DataChunk &args, ExpressionState &state, Vector &result) {
	result.SetVectorType(VectorType::CONSTANT_VECTOR);
	auto data = ConstantVector::GetData<string_t>(result);
#ifdef EXT_VERSION_OPEN_DATA_DUCK
	data[0] = StringVector::AddString(result, EXT_VERSION_OPEN_DATA_DUCK);
#else
	data[0] = StringVector::AddString(result, "dev");
#endif
}

// Embedded registry contract (issue #31). The JSON is generated at development
// time from registry/sources.yml and compiled into the extension, so the runtime
// never needs Python, PyYAML, or repo-relative files.
static void OpenDataDuckRegistryJsonFunction(DataChunk &args, ExpressionState &state, Vector &result) {
	result.SetVectorType(VectorType::CONSTANT_VECTOR);
	auto data = ConstantVector::GetData<string_t>(result);
	data[0] = StringVector::AddString(result, open_data_duck::REGISTRY_JSON);
}

static void OpenDataDuckRegistrySourceCountFunction(DataChunk &args, ExpressionState &state, Vector &result) {
	result.SetVectorType(VectorType::CONSTANT_VECTOR);
	auto data = ConstantVector::GetData<int32_t>(result);
	data[0] = open_data_duck::REGISTRY_SOURCE_COUNT;
}

template <bool VALIDATION>
static void OpenDataSqlFunction(DataChunk &args, ExpressionState &state, Vector &result) {
	UnaryExecutor::Execute<string_t, string_t>(args.data[0], result, args.size(), [&](string_t source_id) {
		const string id = source_id.GetString();
		return StringVector::AddString(result, RenderSourceSql(FindSourceOrThrow(id), VALIDATION));
	});
}

// ExpressionState exposes the client context under different names across DuckDB
// versions (GetContext() in v2.0.0, GetClientContext() on main), so capture it at bind time.
struct OpenDataReleaseBindData : public FunctionData {
	explicit OpenDataReleaseBindData(ClientContext &context) : context(context.shared_from_this()) {
	}

	weak_ptr<ClientContext> context;

	unique_ptr<FunctionData> Copy() const override {
		auto result = make_uniq<OpenDataReleaseBindData>(*context.lock());
		return std::move(result);
	}
	bool Equals(const FunctionData &other) const override {
		return true;
	}
};

static unique_ptr<FunctionData> OpenDataReleaseBind(BindScalarFunctionInput &input) {
	return make_uniq<OpenDataReleaseBindData>(input.GetClientContext());
}

static void OpenDataReleaseFunction(DataChunk &args, ExpressionState &state, Vector &result) {
	auto &bind_data = state.expr.Cast<BoundFunctionExpression>().BindInfo()->Cast<OpenDataReleaseBindData>();
	auto context = bind_data.context.lock();
	if (!context) {
		throw InternalException("open_data_duck: open_data_release() lost its client context");
	}
	UnaryExecutor::Execute<string_t, string_t>(args.data[0], result, args.size(), [&](string_t source_id) {
		const string id = source_id.GetString();
		return StringVector::AddString(result, ResolveRelease(*context, FindSourceOrThrow(id)));
	});
}

//===--------------------------------------------------------------------===//
// Table functions: open_data_sources() and open_data_search(query)
//===--------------------------------------------------------------------===//

struct OpenDataSourcesBindData : public TableFunctionData {
	//! Indexes into the embedded registry that this scan should emit.
	vector<idx_t> selected;
};

struct OpenDataSourcesGlobalState : public GlobalTableFunctionState {
	idx_t offset = 0;

	idx_t MaxThreads() const override {
		return 1;
	}
};

static void DefineSourceColumns(vector<LogicalType> &return_types, vector<Identifier> &names) {
	const char *varchar_columns[] = {"id",       "name",        "source_type", "status",     "description",
	                                 "authority", "homepage",    "license_url", "attribution"};
	for (auto column : varchar_columns) {
		names.emplace_back(column);
		return_types.emplace_back(LogicalType::VARCHAR);
	}
	names.emplace_back("tags");
	return_types.emplace_back(LogicalType::LIST(LogicalType::VARCHAR));
	names.emplace_back("extensions");
	return_types.emplace_back(LogicalType::LIST(LogicalType::VARCHAR));
	names.emplace_back("install");
	return_types.emplace_back(LogicalType::VARCHAR);
	names.emplace_back("example_query");
	return_types.emplace_back(LogicalType::VARCHAR);
	names.emplace_back("validation_query");
	return_types.emplace_back(LogicalType::VARCHAR);
	names.emplace_back("namespace");
	return_types.emplace_back(LogicalType::VARCHAR);
}

static unique_ptr<FunctionData> OpenDataSourcesBind(ClientContext &context, TableFunctionBindInput &input,
                                                    vector<LogicalType> &return_types, vector<Identifier> &names) {
	DefineSourceColumns(return_types, names);
	auto result = make_uniq<OpenDataSourcesBindData>();
	auto &registry = GetEmbeddedRegistry();
	for (idx_t i = 0; i < registry.size(); i++) {
		result->selected.push_back(i);
	}
	return result;
}

static unique_ptr<FunctionData> OpenDataSearchBind(ClientContext &context, TableFunctionBindInput &input,
                                                   vector<LogicalType> &return_types, vector<Identifier> &names) {
	DefineSourceColumns(return_types, names);
	if (input.inputs.empty() || input.inputs[0].IsNull()) {
		throw BinderException("open_data_search(query) requires a non-NULL search string");
	}

	// Same matching rule as `odd search`: every whitespace-separated term must appear
	// (case-insensitively) in the source's search text. The CLI's --type/--status
	// filters map to plain SQL: WHERE source_type = ... AND status = ...
	vector<string> terms;
	for (auto &term : StringUtil::Split(StringValue::Get(input.inputs[0]), ' ')) {
		auto stripped = Stripped(term);
		if (!stripped.empty()) {
			terms.push_back(StringUtil::Lower(stripped));
		}
	}

	auto result = make_uniq<OpenDataSourcesBindData>();
	auto &registry = GetEmbeddedRegistry();
	for (idx_t i = 0; i < registry.size(); i++) {
		auto &source = registry[i];
		bool matches = true;
		for (auto &term : terms) {
			if (!StringUtil::Contains(source.search_text, term)) {
				matches = false;
				break;
			}
		}
		if (matches) {
			result->selected.push_back(i);
		}
	}
	return result;
}

static unique_ptr<GlobalTableFunctionState> OpenDataSourcesInit(ClientContext &context,
                                                                TableFunctionInitInput &input) {
	return make_uniq<OpenDataSourcesGlobalState>();
}

static Value StringListValue(const vector<string> &items) {
	vector<Value> values;
	values.reserve(items.size());
	for (auto &item : items) {
		values.emplace_back(item);
	}
	return Value::LIST(LogicalType::VARCHAR, std::move(values));
}

static void OpenDataSourcesScan(ClientContext &context, TableFunctionInput &data_p, DataChunk &output) {
	auto &bind_data = data_p.bind_data->Cast<OpenDataSourcesBindData>();
	auto &state = data_p.global_state->Cast<OpenDataSourcesGlobalState>();
	auto &registry = GetEmbeddedRegistry();

	// Same append-style fill as DuckDB's own duckdb_extensions() table function.
	idx_t count = 0;
	while (state.offset < bind_data.selected.size() && count < STANDARD_VECTOR_SIZE) {
		auto &source = registry[bind_data.selected[state.offset++]];
		idx_t col = 0;
		output.data[col++].Append(Value(source.id));
		output.data[col++].Append(Value(source.name));
		output.data[col++].Append(Value(source.source_type));
		output.data[col++].Append(Value(source.status));
		output.data[col++].Append(Value(source.description));
		output.data[col++].Append(Value(source.authority));
		output.data[col++].Append(Value(source.homepage));
		output.data[col++].Append(Value(source.license_url));
		output.data[col++].Append(Value(source.attribution));
		output.data[col++].Append(StringListValue(source.tags));
		output.data[col++].Append(StringListValue(source.extensions));
		output.data[col++].Append(Value(source.install));
		output.data[col++].Append(Value(source.example_query));
		output.data[col++].Append(Value(source.validation_query));
		output.data[col++].Append(Value(source.tables_namespace));
		count++;
	}
}


//===--------------------------------------------------------------------===//
// open_data_tables() and the replacement scan
//===--------------------------------------------------------------------===//

struct OpenDataTablesRow {
	string source_id;
	string table_reference;
	string reader;
	string path;
	string release;
};

struct OpenDataTablesBindData : public TableFunctionData {
	vector<OpenDataTablesRow> rows;
};

struct OpenDataTablesGlobalState : public GlobalTableFunctionState {
	idx_t offset = 0;

	idx_t MaxThreads() const override {
		return 1;
	}
};

// Discovery happens at bind time so odd.tables reflects the pinned variables of this
// connection; every source@release is cached after its first discovery.
static unique_ptr<FunctionData> OpenDataTablesBind(ClientContext &context, TableFunctionBindInput &input,
                                                   vector<LogicalType> &return_types, vector<Identifier> &names) {
	const char *varchar_columns[] = {"source_id", "table_reference", "reader", "path", "release"};
	for (auto column : varchar_columns) {
		names.emplace_back(column);
		return_types.emplace_back(LogicalType::VARCHAR);
	}
	auto result = make_uniq<OpenDataTablesBindData>();
	for (auto &source : GetEmbeddedRegistry()) {
		if (source.tables_namespace.empty()) {
			continue;
		}
		auto discovered = DiscoverTables(context, source);
		for (auto &table : discovered.tables) {
			OpenDataTablesRow row;
			row.source_id = source.id;
			row.table_reference = source.tables_namespace + "." + table.name;
			row.reader = table.reader;
			row.path = table.path;
			row.release = discovered.release;
			result->rows.push_back(std::move(row));
		}
	}
	return std::move(result);
}

static unique_ptr<GlobalTableFunctionState> OpenDataTablesInit(ClientContext &context, TableFunctionInitInput &input) {
	return make_uniq<OpenDataTablesGlobalState>();
}

static void OpenDataTablesScan(ClientContext &context, TableFunctionInput &data_p, DataChunk &output) {
	auto &bind_data = data_p.bind_data->Cast<OpenDataTablesBindData>();
	auto &state = data_p.global_state->Cast<OpenDataTablesGlobalState>();

	idx_t count = 0;
	while (state.offset < bind_data.rows.size() && count < STANDARD_VECTOR_SIZE) {
		auto &row = bind_data.rows[state.offset++];
		idx_t col = 0;
		output.data[col++].Append(Value(row.source_id));
		output.data[col++].Append(Value(row.table_reference));
		output.data[col++].Append(Value(row.reader));
		output.data[col++].Append(Value(row.path));
		output.data[col++].Append(Value(row.release));
		count++;
	}
}

static unique_ptr<TableFunctionRef> TableFunctionReplacement(const string &function_name, const string &alias) {
	auto table_function = make_uniq<TableFunctionRef>();
	vector<unique_ptr<ParsedExpression>> children;
	table_function->function = make_uniq<FunctionExpression>(Identifier(function_name), std::move(children));
	table_function->alias = Identifier(alias);
	return table_function;
}

static unique_ptr<TableRef> OpenDataDuckReplacementScan(ClientContext &context, ReplacementScanInput &input,
                                                        optional_ptr<ReplacementScanData> data) {
	auto table_name = ReplacementScan::GetFullPath(input);
	auto lower_table_name = StringUtil::Lower(table_name);
	if (lower_table_name == "odd.index") {
		return TableFunctionReplacement("open_data_sources", "index");
	}
	if (lower_table_name == "odd.tables") {
		return TableFunctionReplacement("open_data_tables", "tables");
	}

	// odd.<provider>.<version>.<table>: discover the namespace's tables, then bind reader(path).
	// Several sources may share a namespace (both Census boundary sources use odd.census.latest).
	string matched_namespace;
	string wanted;
	for (auto &source : GetEmbeddedRegistry()) {
		if (source.tables_namespace.empty()) {
			continue;
		}
		auto prefix = StringUtil::Lower(source.tables_namespace) + ".";
		if (!StringUtil::StartsWith(lower_table_name, prefix)) {
			continue;
		}
		matched_namespace = source.tables_namespace;
		wanted = lower_table_name.substr(prefix.size());
		auto discovered = DiscoverTables(context, source);
		for (auto &table : discovered.tables) {
			if (StringUtil::Lower(table.name) != wanted) {
				continue;
			}
			auto table_function = make_uniq<TableFunctionRef>();
			vector<FunctionArgument> children;
			children.emplace_back(ConstantExpression::String(table.path));
			table_function->function = make_uniq<FunctionExpression>(Identifier(table.reader), std::move(children));
			table_function->alias = Identifier(table.name);
			return std::move(table_function);
		}
	}
	if (!matched_namespace.empty()) {
		throw InvalidInputException("open_data_duck: no table '%s' under %s. SELECT table_reference FROM odd.tables "
		                            "lists what this release exposes.",
		                            wanted, matched_namespace);
	}
	return nullptr;
}

//===--------------------------------------------------------------------===//
// open_data_duck storage extension catalog
//===--------------------------------------------------------------------===//

class OpenDataDuckCatalogViewGenerator : public DefaultGenerator {
public:
	OpenDataDuckCatalogViewGenerator(Catalog &catalog, SchemaCatalogEntry &schema)
	    : DefaultGenerator(catalog), schema(schema) {
	}

	unique_ptr<CatalogEntry> CreateDefaultEntry(ClientContext &context, const Identifier &entry_name) override {
		string sql;
		if (entry_name == Identifier("index")) {
			sql = "SELECT * FROM open_data_sources()";
		} else if (entry_name == Identifier("tables")) {
			sql = "SELECT * FROM open_data_tables()";
		} else {
			return nullptr;
		}

		auto view = make_uniq<CreateViewInfo>();
		view->SetQualifiedName(QualifiedName({Identifier::DefaultSchema()}, entry_name));
		view->sql = sql;
		auto parser = Parser::GetBuiltinParser();
		auto view_info = CreateViewInfo::FromSelect(parser, std::move(view));
		return make_uniq_base<CatalogEntry, ViewCatalogEntry>(catalog, schema, *view_info);
	}

	vector<Identifier> GetDefaultEntries() override {
		return {Identifier("index"), Identifier("tables")};
	}

private:
	SchemaCatalogEntry &schema;
};

static unique_ptr<Catalog> OpenDataDuckStorageAttach(optional_ptr<StorageExtensionInfo> storage_info,
                                                     ClientContext &context, AttachedDatabase &db, const string &name,
                                                     AttachInfo &info, AttachOptions &attach_options) {
	info.path = IN_MEMORY_PATH;
	auto catalog = make_uniq<DuckCatalog>(db);
	catalog->Initialize(false);

	auto system_transaction = CatalogTransaction::GetSystemTransaction(db.GetDatabase());
	auto &schema = catalog->GetSchema(system_transaction, Identifier::DefaultSchema());
	auto &duck_schema = schema.Cast<DuckSchemaEntry>();
	auto &catalog_set = duck_schema.GetCatalogSet(CatalogType::VIEW_ENTRY);
	catalog_set.SetDefaultGenerator(make_uniq<OpenDataDuckCatalogViewGenerator>(*catalog, schema));

	return std::move(catalog);
}

static unique_ptr<TransactionManager> OpenDataDuckStorageTransactionManager(optional_ptr<StorageExtensionInfo> storage_info,
                                                                           AttachedDatabase &db, Catalog &catalog) {
	return make_uniq<DuckTransactionManager>(db);
}

struct OpenDataDuckStorageExtension : StorageExtension {
	OpenDataDuckStorageExtension() {
		attach = OpenDataDuckStorageAttach;
		create_transaction_manager = OpenDataDuckStorageTransactionManager;
	}
};

//===--------------------------------------------------------------------===//
// Registration
//===--------------------------------------------------------------------===//

static void LoadInternal(ExtensionLoader &loader) {
	loader.RegisterFunction(ScalarFunction("open_data_duck_ping", {}, LogicalType::VARCHAR, OpenDataDuckPingFunction));
	loader.RegisterFunction(
	    ScalarFunction("open_data_duck_version", {}, LogicalType::VARCHAR, OpenDataDuckVersionFunction));
	loader.RegisterFunction(ScalarFunction("open_data_duck_registry_json", {}, LogicalType::VARCHAR,
	                                       OpenDataDuckRegistryJsonFunction));
	loader.RegisterFunction(ScalarFunction("open_data_duck_registry_source_count", {}, LogicalType::INTEGER,
	                                       OpenDataDuckRegistrySourceCountFunction));

	// Issue #32: core registry discovery API. Returns SQL recipes; does not execute sources.
	// Both lookups throw on unknown ids, so they must be marked fallible.
	ScalarFunction open_data_sql("open_data_sql", {LogicalType::VARCHAR}, LogicalType::VARCHAR,
	                             OpenDataSqlFunction<false>);
	open_data_sql.SetFallible();
	loader.RegisterFunction(open_data_sql);
	ScalarFunction open_data_validation_sql("open_data_validation_sql", {LogicalType::VARCHAR}, LogicalType::VARCHAR,
	                                        OpenDataSqlFunction<true>);
	open_data_validation_sql.SetFallible();
	loader.RegisterFunction(open_data_validation_sql);

	// Release a `latest` table resolves to: pinned variable, else cached release.latest.resolve_sql.
	ScalarFunction open_data_release("open_data_release", {LogicalType::VARCHAR}, LogicalType::VARCHAR,
	                                 OpenDataReleaseFunction, OpenDataReleaseBind);
	open_data_release.SetFallible();
	loader.RegisterFunction(open_data_release);

	TableFunction sources("open_data_sources", {}, OpenDataSourcesScan, OpenDataSourcesBind, OpenDataSourcesInit);
	loader.RegisterFunction(sources);

	TableFunction search("open_data_search", {LogicalType::VARCHAR}, OpenDataSourcesScan, OpenDataSearchBind,
	                     OpenDataSourcesInit);
	loader.RegisterFunction(search);

	TableFunction tables("open_data_tables", {}, OpenDataTablesScan, OpenDataTablesBind, OpenDataTablesInit);
	loader.RegisterFunction(tables);

	StorageExtension::Register(DBConfig::GetConfig(loader.GetDatabaseInstance()), "open_data_duck",
	                           make_shared_ptr<OpenDataDuckStorageExtension>());
	DBConfig::GetConfig(loader.GetDatabaseInstance()).replacement_scans.emplace_back(OpenDataDuckReplacementScan);
}

void OpenDataDuckExtension::Load(ExtensionLoader &loader) {
	LoadInternal(loader);
}

std::string OpenDataDuckExtension::Name() {
	return "open_data_duck";
}

std::string OpenDataDuckExtension::Version() const {
#ifdef EXT_VERSION_OPEN_DATA_DUCK
	return EXT_VERSION_OPEN_DATA_DUCK;
#else
	return "dev";
#endif
}

} // namespace duckdb

extern "C" {

DUCKDB_CPP_EXTENSION_ENTRY(open_data_duck, loader) {
	duckdb::LoadInternal(loader);
}
}
