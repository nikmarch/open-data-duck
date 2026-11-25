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
#include "duckdb/parser/expression/columnref_expression.hpp"
#include "duckdb/parser/expression/comparison_expression.hpp"
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
#include <cstdlib>
#include <limits>
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
	string authority;
	string license_url;
	string attribution;
	vector<string> extensions;
	//! discovery.namespace: odd.<provider>.<version> prefix of this source's data tables.
	string tables_namespace;
	//! discovery.discover_sql: SQL returning (name, reader, path) rows, with {release} substituted.
	string tables_discover_sql;
	//! First table validation's odd_sql, used as the source-level example SQL.
	string example_query;
	//! First table validation rendered as direct control + ODD facade SQL.
	string validation_query;
	//! auth metadata for sources that require user-provided values in discovered paths.
	string auth_type;
	string auth_placeholder;
	string auth_variable;
	string auth_env_var;
	string auth_query_parameter;
	string auth_url;
	bool auth_required = false;
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

static bool JsonBoolean(const JSONValue &object, const string &key) {
	auto member = object.GetMember(key);
	return member.IsValid() && member.GetType() == JSONValueType::BOOLEAN && member.GetBoolean();
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

static string ValidateSourceExtensionName(const string &source_id, const string &extension) {
	auto stripped = Stripped(extension);
	if (stripped.empty()) {
		return stripped;
	}
	for (auto c : stripped) {
		if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_')) {
			throw InvalidInputException("open_data_duck: source '%s' declares invalid DuckDB extension '%s'", source_id,
			                            extension);
		}
	}
	return stripped;
}

static unique_ptr<QueryResult> RunSourceControlledSql(ClientContext &context, const OpenDataSource &source,
                                                     const string &purpose, const string &sql) {
	ValidateSourceControlledSql(source.id, purpose, sql);
	Connection connection(DatabaseInstance::GetDatabase(context));
	for (auto &extension : source.extensions) {
		auto extension_name = ValidateSourceExtensionName(source.id, extension);
		if (extension_name.empty()) {
			continue;
		}
		auto install_result = connection.Query("INSTALL " + extension_name);
		if (install_result->HasError()) {
			throw InvalidInputException("open_data_duck: could not install DuckDB extension '%s' for source '%s': %s",
			                            extension_name, source.id, install_result->GetError());
		}
		auto load_result = connection.Query("LOAD " + extension_name);
		if (load_result->HasError()) {
			throw InvalidInputException("open_data_duck: could not load DuckDB extension '%s' for source '%s': %s",
			                            extension_name, source.id, load_result->GetError());
		}
	}
	return connection.Query(sql);
}

static void JsonDiscovery(const JSONValue &source_value, OpenDataSource &source) {
	auto discovery_value = source_value.GetMember("discovery");
	if (!discovery_value.IsValid() || !discovery_value.IsObject()) {
		return;
	}
	auto ns = Stripped(JsonString(discovery_value, "namespace"));
	auto discover_sql = Stripped(JsonString(discovery_value, "discover_sql"));
	if (ns.empty() || discover_sql.empty()) {
		return;
	}
	source.tables_namespace = std::move(ns);
	source.tables_discover_sql = std::move(discover_sql);
}

static void JsonFirstValidationPair(const JSONValue &source_value, OpenDataSource &source) {
	auto tables_value = source_value.GetMember("tables");
	if (!tables_value.IsValid() || !tables_value.IsArray()) {
		return;
	}
	bool found = false;
	tables_value.IterateArray([&](JSONValue table_value) {
		if (found || !table_value.IsObject()) {
			return;
		}
		auto validations_value = table_value.GetMember("validations");
		if (!validations_value.IsValid() || !validations_value.IsArray()) {
			return;
		}
		validations_value.IterateArray([&](JSONValue validation_value) {
			if (found || !validation_value.IsObject()) {
				return;
			}
			auto direct_sql = Stripped(JsonString(validation_value, "direct_sql"));
			auto odd_sql = Stripped(JsonString(validation_value, "odd_sql"));
			if (direct_sql.empty() || odd_sql.empty()) {
				return;
			}
			auto validation_id = Stripped(JsonString(validation_value, "id"));
			if (validation_id.empty()) {
				validation_id = source.id;
			}
			source.example_query = odd_sql;
			source.validation_query = "-- direct DuckDB control for " + validation_id + "\n" + direct_sql +
			                          "\n\n-- ODD facade example for " + validation_id + "\n" + odd_sql;
			found = true;
		});
	});
}

static void JsonAuth(const JSONValue &source_value, OpenDataSource &source) {
	auto auth_value = source_value.GetMember("auth");
	if (!auth_value.IsValid() || !auth_value.IsObject()) {
		return;
	}
	source.auth_type = Stripped(JsonString(auth_value, "type"));
	source.auth_placeholder = Stripped(JsonString(auth_value, "placeholder"));
	source.auth_variable = Stripped(JsonString(auth_value, "duckdb_setting"));
	source.auth_env_var = Stripped(JsonString(auth_value, "env_var"));
	source.auth_query_parameter = Stripped(JsonString(auth_value, "query_parameter"));
	source.auth_url = Stripped(JsonString(auth_value, "url"));
	source.auth_required = JsonBoolean(auth_value, "required");
}

static string BuildSearchText(const OpenDataSource &source) {
	vector<string> parts {source.id,   source.name,       source.status,      source.source_type,
	                      source.authority, source.license_url, source.attribution};
	for (auto &extension : source.extensions) {
		parts.push_back(extension);
	}
	parts.push_back(source.auth_type);
	parts.push_back(source.auth_variable);
	parts.push_back(source.auth_env_var);
	parts.push_back(source.auth_query_parameter);
	parts.push_back(source.auth_url);
	parts.push_back(source.tables_namespace);
	parts.push_back(source.example_query);
	parts.push_back(source.validation_query);
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
		source.authority = JsonString(item, "authority");
		source.license_url = JsonString(item, "license_url");
		source.attribution = JsonString(item, "attribution");

		auto requirements_value = item.GetMember("requirements");
		if (requirements_value.IsValid() && requirements_value.IsObject()) {
			source.extensions = JsonStringArray(requirements_value, "duckdb_extensions");
		}
		JsonDiscovery(item, source);
		JsonFirstValidationPair(item, source);
		JsonAuth(item, source);
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

//! Mirrors odd.registry.render_source_sql(): first table validation odd_sql, or direct+ODD validation pair.
static string RenderSourceSql(const OpenDataSource &source, bool validation) {
	auto query = Stripped(validation ? source.validation_query : source.example_query);
	if (query.empty()) {
		throw InvalidInputException("open_data_duck: source '%s' has no table validation %s", source.id,
		                            validation ? "direct_sql/odd_sql pair" : "odd_sql");
	}
	return query + "\n";
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

	auto result = RunSourceControlledSql(context, source, "release resolution", source.latest_resolve_sql);
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
	string layer;
	//! Optional JSON object of safe named arguments passed to CSV-backed readers.
	string reader_options;
};

struct DiscoveredTables {
	string release;
	vector<OpenDataTable> tables;
};

static string ResolveSourceAuthValue(ClientContext &context, const OpenDataSource &source) {
	if (source.auth_placeholder.empty()) {
		return string();
	}
	auto auth_error = [&]() {
		string message = "open_data_duck: source '" + source.id + "'";
		if (!source.name.empty()) {
			message += " (" + source.name + ")";
		}
		message += " requires an API key before querying its ODD facade tables.";
		if (!source.auth_variable.empty()) {
			message += " Run SET " + source.auth_variable + " = '<secret>';";
		}
		if (!source.auth_env_var.empty()) {
			message += " Or set environment variable " + source.auth_env_var + ".";
		}
		if (!source.auth_url.empty()) {
			message += " Get a key at " + source.auth_url + ".";
		}
		if (!source.auth_query_parameter.empty()) {
			message += " ODD sends it as query parameter '" + source.auth_query_parameter + "'.";
		}
		throw InvalidInputException(message);
	};
	auto usable_auth = [&](const string &value) {
		auto stripped = Stripped(value);
		return !stripped.empty() && stripped != source.auth_placeholder && stripped != "<secret>";
	};
	Value auth_value;
	if (!source.auth_variable.empty() && context.TryGetCurrentSetting(Identifier(source.auth_variable), auth_value) && !auth_value.IsNull()) {
		auto value = auth_value.ToString();
		if (usable_auth(value)) {
			return value;
		}
		if (source.auth_required) {
			auth_error();
		}
	}
	if (!source.auth_variable.empty() && ClientConfig::GetConfig(context).GetUserVariable(source.auth_variable, auth_value) &&
	    !auth_value.IsNull()) {
		auto value = auth_value.ToString();
		if (usable_auth(value)) {
			return value;
		}
		if (source.auth_required) {
			auth_error();
		}
	}
	if (!source.auth_env_var.empty()) {
		const auto env_value = std::getenv(source.auth_env_var.c_str());
		if (env_value && usable_auth(string(env_value))) {
			return string(env_value);
		}
	}
	if (source.auth_required) {
		auth_error();
	}
	return string();
}

static string ResolveAuthenticatedPath(ClientContext &context, const OpenDataSource &source, const string &path) {
	if (source.auth_placeholder.empty() || !StringUtil::Contains(path, source.auth_placeholder)) {
		return path;
	}
	auto auth_value = ResolveSourceAuthValue(context, source);
	if (auth_value.empty()) {
		return path;
	}
	return StringUtil::Replace(path, source.auth_placeholder, auth_value);
}

//! Rows of discovery.discover_sql for the source's current release. Runs once per
//! process and source@release on its own connection, then serves from cache. Pinning a
//! different release (SET VARIABLE ...) gets its own cache entry.
//!
//! Discovery rows are positional for compatibility:
//!   name, reader, path[, layer[, reader_options_json]]
//! `layer` is only applied to ST_Read. `reader_options_json` is a source-controlled
//! JSON object of whitelisted named arguments for CSV readers.
static DiscoveredTables DiscoverTables(ClientContext &context, const OpenDataSource &source) {
	if (source.tables_discover_sql.empty()) {
		throw InvalidInputException("open_data_duck: source '%s' has no discovery.discover_sql", source.id);
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

	auto query_result = RunSourceControlledSql(context, source, "table discovery", sql);
	if (query_result->HasError()) {
		throw InvalidInputException("open_data_duck: could not discover tables for '%s': %s", source.id,
		                            query_result->GetError());
	}
	if (query_result->ColumnCount() < 3) {
		throw InvalidInputException("open_data_duck: discovery.discover_sql for '%s' must return at least (name, reader, path)",
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
		if (query_result->ColumnCount() >= 4) {
			table.layer = row.IsNull(3) ? string() : row.GetValue<string>(3);
		}
		if (query_result->ColumnCount() >= 5) {
			table.reader_options = row.IsNull(4) ? string() : row.GetValue<string>(4);
		}
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
	const char *varchar_columns[] = {"id",       "name",        "source_type", "status",
	                                 "authority", "license_url", "attribution"};
	for (auto column : varchar_columns) {
		names.emplace_back(column);
		return_types.emplace_back(LogicalType::VARCHAR);
	}
	names.emplace_back("duckdb_extensions");
	return_types.emplace_back(LogicalType::LIST(LogicalType::VARCHAR));
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
		output.data[col++].Append(Value(source.authority));
		output.data[col++].Append(Value(source.license_url));
		output.data[col++].Append(Value(source.attribution));
		output.data[col++].Append(StringListValue(source.extensions));
		output.data[col++].Append(Value(source.tables_namespace));
		count++;
	}
}

//===--------------------------------------------------------------------===//
// open_data_auth()
//===--------------------------------------------------------------------===//

struct OpenDataAuthBindData : public TableFunctionData {
	vector<idx_t> selected;
};

struct OpenDataAuthGlobalState : public GlobalTableFunctionState {
	idx_t offset = 0;

	idx_t MaxThreads() const override {
		return 1;
	}
};

static unique_ptr<FunctionData> OpenDataAuthBind(ClientContext &context, TableFunctionBindInput &input,
                                                vector<LogicalType> &return_types, vector<Identifier> &names) {
	const char *varchar_columns[] = {"source_id", "auth_type", "setting_name", "env_var", "placeholder",
	                                 "query_parameter", "url"};
	for (auto column : varchar_columns) {
		names.emplace_back(column);
		return_types.emplace_back(LogicalType::VARCHAR);
	}
	names.emplace_back("required");
	return_types.emplace_back(LogicalType::BOOLEAN);
	auto result = make_uniq<OpenDataAuthBindData>();
	auto &registry = GetEmbeddedRegistry();
	for (idx_t i = 0; i < registry.size(); i++) {
		if (!registry[i].auth_type.empty()) {
			result->selected.push_back(i);
		}
	}
	return result;
}

static unique_ptr<GlobalTableFunctionState> OpenDataAuthInit(ClientContext &context, TableFunctionInitInput &input) {
	return make_uniq<OpenDataAuthGlobalState>();
}

static void OpenDataAuthScan(ClientContext &context, TableFunctionInput &data_p, DataChunk &output) {
	auto &bind_data = data_p.bind_data->Cast<OpenDataAuthBindData>();
	auto &state = data_p.global_state->Cast<OpenDataAuthGlobalState>();
	auto &registry = GetEmbeddedRegistry();

	idx_t count = 0;
	while (state.offset < bind_data.selected.size() && count < STANDARD_VECTOR_SIZE) {
		auto &source = registry[bind_data.selected[state.offset++]];
		idx_t col = 0;
		output.data[col++].Append(Value(source.id));
		output.data[col++].Append(Value(source.auth_type));
		output.data[col++].Append(Value(source.auth_variable));
		output.data[col++].Append(Value(source.auth_env_var));
		output.data[col++].Append(Value(source.auth_placeholder));
		output.data[col++].Append(Value(source.auth_query_parameter));
		output.data[col++].Append(Value(source.auth_url));
		output.data[col++].Append(Value::BOOLEAN(source.auth_required));
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

static bool IsCsvReader(const string &reader) {
	auto lower_reader = StringUtil::Lower(reader);
	return lower_reader == "read_csv" || lower_reader == "read_csv_auto";
}

static bool IsSafeCsvReaderOption(const string &option) {
	static const vector<string> allowed = {"all_varchar",    "auto_detect", "columns",       "compression",
	                                    "dateformat",     "delim",       "escape",        "header",
	                                    "ignore_errors",  "max_line_size", "names",        "new_line",
	                                    "null_padding",   "nullstr",     "quote",         "sample_size",
	                                    "sep",            "skip",        "timestampformat"};
	for (auto &allowed_option : allowed) {
		if (option == allowed_option) {
			return true;
		}
	}
	return false;
}

static unique_ptr<ParsedExpression> ReaderOptionObjectExpression(const string &source_id, const string &table_name,
                                                                 const string &option, const JSONValue &value) {
	if (option != "columns") {
		throw InvalidInputException(
		    "open_data_duck: source '%s' table '%s' reader option '%s' must be a scalar, string array, or columns object",
		    source_id, table_name, option);
	}
	child_list_t<Value> fields;
	value.IterateObject([&](const string &key, JSONValue item) {
		if (key.empty() || !item.IsString()) {
			throw InvalidInputException(
			    "open_data_duck: source '%s' table '%s' reader option 'columns' must map column names to type strings",
			    source_id, table_name);
		}
		fields.emplace_back(Identifier(key), Value(item.GetString()));
	});
	if (fields.empty()) {
		throw InvalidInputException("open_data_duck: source '%s' table '%s' reader option 'columns' must not be empty",
		                            source_id, table_name);
	}
	return ConstantExpression::FromValue(Value::STRUCT(fields));
}

static unique_ptr<ParsedExpression> ReaderOptionArrayExpression(const string &source_id, const string &table_name,
                                                                const string &option, const JSONValue &value) {
	vector<Value> values;
	value.IterateArray([&](JSONValue item) {
		if (!item.IsString()) {
			throw InvalidInputException(
			    "open_data_duck: source '%s' table '%s' reader option '%s' arrays may only contain strings", source_id,
			    table_name, option);
		}
		values.emplace_back(item.GetString());
	});
	if (values.empty()) {
		return ConstantExpression::FromValue(Value::LIST(LogicalType::VARCHAR, std::move(values)));
	}
	return ConstantExpression::FromValue(Value::LIST(std::move(values)));
}

static unique_ptr<ParsedExpression> ReaderOptionExpression(const string &source_id, const string &table_name,
                                                           const string &option, const JSONValue &value) {
	if (value.IsString()) {
		return ConstantExpression::String(value.GetString());
	}
	if (value.GetType() == JSONValueType::BOOLEAN) {
		return ConstantExpression::Boolean(value.GetBoolean());
	}
	if (value.GetType() == JSONValueType::SIGNED_INTEGER) {
		return ConstantExpression::Integer(value.GetSignedInteger());
	}
	if (value.GetType() == JSONValueType::UNSIGNED_INTEGER) {
		auto unsigned_value = value.GetUnsignedInteger();
		if (unsigned_value > static_cast<uint64_t>(std::numeric_limits<int64_t>::max())) {
			throw InvalidInputException("open_data_duck: source '%s' table '%s' reader option '%s' is too large",
			                            source_id, table_name, option);
		}
		return ConstantExpression::Integer(static_cast<int64_t>(unsigned_value));
	}
	if (value.GetType() == JSONValueType::DOUBLE || value.GetType() == JSONValueType::RAW) {
		return ConstantExpression::Number(value.ToString());
	}
	if (value.IsArray()) {
		return ReaderOptionArrayExpression(source_id, table_name, option, value);
	}
	if (value.IsObject()) {
		return ReaderOptionObjectExpression(source_id, table_name, option, value);
	}
	throw InvalidInputException("open_data_duck: source '%s' table '%s' reader option '%s' has unsupported JSON value",
	                            source_id, table_name, option);
}

static void AppendReaderOptions(const string &source_id, const OpenDataTable &table, vector<FunctionArgument> &children) {
	auto options = Stripped(table.reader_options);
	if (options.empty()) {
		return;
	}
	if (!IsCsvReader(table.reader)) {
		throw InvalidInputException(
		    "open_data_duck: source '%s' table '%s' declares reader options for unsupported reader '%s'", source_id,
		    table.name, table.reader);
	}
	auto document = JSONDocument::Parse(options.c_str(), options.size());
	auto root = document->GetRoot();
	if (!root.IsObject()) {
		throw InvalidInputException("open_data_duck: source '%s' table '%s' reader options must be a JSON object", source_id,
		                            table.name);
	}
	root.IterateObject([&](const string &key, JSONValue value) {
		auto option = StringUtil::Lower(Stripped(key));
		if (option.empty() || !IsSafeCsvReaderOption(option)) {
			throw InvalidInputException("open_data_duck: source '%s' table '%s' has unsafe CSV reader option '%s'",
			                            source_id, table.name, key);
		}
		// Use the legacy `name = expression` shape instead of FunctionArgument's
		// explicit name constructor here. DuckDB v2.0.0's distribution build
		// headers compile both forms, but its table-function binder only preserves
		// the comparison-expression shape for replacement scans; otherwise CSV
		// options bind as positional arguments in CI.
		auto named_option = make_uniq<ComparisonExpression>(ExpressionType::COMPARE_EQUAL,
		                                                     make_uniq<ColumnRefExpression>(Identifier(option)),
		                                                     ReaderOptionExpression(source_id, table.name, option, value));
		children.emplace_back(std::move(named_option));
	});
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
		// Fail fast for key-protected sources before table discovery installs/loads
		// reader extensions or touches source-controlled API URLs. This gives users
		// the setup message for any table under the protected namespace.
		if (source.auth_required && source.auth_type == "api_key") {
			ResolveSourceAuthValue(context, source);
		}
		auto discovered = DiscoverTables(context, source);
		for (auto &table : discovered.tables) {
			if (StringUtil::Lower(table.name) != wanted) {
				continue;
			}
			auto table_function = make_uniq<TableFunctionRef>();
			vector<FunctionArgument> children;
			children.emplace_back(ConstantExpression::String(ResolveAuthenticatedPath(context, source, table.path)));
			if (!table.layer.empty() && StringUtil::Lower(table.reader) == "st_read") {
				children.emplace_back(Identifier("layer"), ConstantExpression::String(table.layer));
			}
			AppendReaderOptions(source.id, table, children);
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
		} else if (entry_name == Identifier("auth")) {
			sql = "SELECT * FROM open_data_auth()";
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
		return {Identifier("index"), Identifier("tables"), Identifier("auth")};
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

static void RegisterSourceAuthSettings(ExtensionLoader &loader) {
	auto &config = DBConfig::GetConfig(loader.GetDatabaseInstance());
	for (auto &source : GetEmbeddedRegistry()) {
		if (source.auth_variable.empty()) {
			continue;
		}
		const auto setting_name = Identifier(source.auth_variable);
		if (config.HasExtensionOption(setting_name)) {
			continue;
		}
		config.AddExtensionOption(setting_name, "Secret value for Open Data Duck source " + source.id,
		                          LogicalType::VARCHAR, Value());
	}
}

static void LoadInternal(ExtensionLoader &loader) {
	RegisterSourceAuthSettings(loader);
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

	TableFunction auth("open_data_auth", {}, OpenDataAuthScan, OpenDataAuthBind, OpenDataAuthInit);
	loader.RegisterFunction(auth);

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
