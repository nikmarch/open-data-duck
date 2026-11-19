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
#include "duckdb/main/client_config.hpp"
#include "duckdb/main/config.hpp"
#include "duckdb/main/connection.hpp"
#include "duckdb/main/database.hpp"
#include "duckdb/main/extension/extension_loader.hpp"
#include "duckdb/parser/expression/constant_expression.hpp"
#include "duckdb/parser/expression/function_expression.hpp"
#include "duckdb/parser/tableref.hpp"
#include "duckdb/parser/tableref/table_function_ref.hpp"
#include <duckdb/parser/parsed_data/create_scalar_function_info.hpp>

#include <mutex>
#include <unordered_map>

namespace duckdb {

//===--------------------------------------------------------------------===//
// Embedded registry (issue #31 contract, parsed once per process)
//===--------------------------------------------------------------------===//

struct OpenDataFacade {
	string table_reference;
	string facade_function;
	string path_glob;
	string example_sql;
	string description;
};

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
	vector<OpenDataFacade> facades;
	string install;
	string example_query;
	string validation_query;
	//! release.latest.resolve_sql: SQL returning the current release id of a `latest` facade.
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

static vector<OpenDataFacade> JsonFacades(const JSONValue &duckdb_value) {
	vector<OpenDataFacade> result;
	auto facades_value = duckdb_value.GetMember("facades");
	if (!facades_value.IsValid() || !facades_value.IsArray()) {
		return result;
	}
	facades_value.IterateArray([&](JSONValue item) {
		if (!item.IsObject()) {
			return;
		}
		OpenDataFacade facade;
		facade.table_reference = JsonString(item, "table_reference");
		facade.facade_function = JsonString(item, "facade_function");
		facade.path_glob = JsonString(item, "path_glob");
		facade.example_sql = JsonString(item, "example_sql");
		facade.description = JsonString(item, "description");
		if (!facade.table_reference.empty() && !facade.path_glob.empty()) {
			result.push_back(std::move(facade));
		}
	});
	return result;
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
	for (auto &facade : source.facades) {
		parts.push_back(facade.table_reference);
		parts.push_back(facade.facade_function);
		parts.push_back(facade.description);
	}
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
			source.facades = JsonFacades(duckdb_value);
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

static const OpenDataFacade *FindFacadeByReference(const string &table_reference, const OpenDataSource *&owner) {
	owner = nullptr;
	for (auto &source : GetEmbeddedRegistry()) {
		for (auto &facade : source.facades) {
			if (StringUtil::Lower(facade.table_reference) == StringUtil::Lower(table_reference)) {
				owner = &source;
				return &facade;
			}
		}
	}
	return nullptr;
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

//! Release id a `latest` facade reads from. Precedence: the pinned user variable
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

	Connection connection(DatabaseInstance::GetDatabase(context));
	auto result = connection.Query(source.latest_resolve_sql);
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

static void OpenDataReleaseFunction(DataChunk &args, ExpressionState &state, Vector &result) {
	auto &context = state.GetClientContext();
	UnaryExecutor::Execute<string_t, string_t>(args.data[0], result, args.size(), [&](string_t source_id) {
		const string id = source_id.GetString();
		return StringVector::AddString(result, ResolveRelease(context, FindSourceOrThrow(id)));
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
	names.emplace_back("table_reference");
	return_types.emplace_back(LogicalType::VARCHAR);
	names.emplace_back("facade_function");
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

static const OpenDataFacade *PrimaryFacadeForSource(const OpenDataSource &source) {
	return source.facades.empty() ? nullptr : &source.facades[0];
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
		auto facade = PrimaryFacadeForSource(source);
		output.data[col++].Append(Value(facade ? facade->table_reference : string()));
		output.data[col++].Append(Value(facade ? facade->facade_function : string()));
		count++;
	}
}


//===--------------------------------------------------------------------===//
// Table facades and replacement scan
//===--------------------------------------------------------------------===//

struct OpenDataFacadesGlobalState : public GlobalTableFunctionState {
	idx_t source_offset = 0;
	idx_t facade_offset = 0;

	idx_t MaxThreads() const override {
		return 1;
	}
};

static unique_ptr<FunctionData> OpenDataFacadesBind(ClientContext &context, TableFunctionBindInput &input,
                                                    vector<LogicalType> &return_types, vector<Identifier> &names) {
	const char *varchar_columns[] = {"source_id", "table_reference", "facade_function", "path_glob", "example_sql",
	                                 "description"};
	for (auto column : varchar_columns) {
		names.emplace_back(column);
		return_types.emplace_back(LogicalType::VARCHAR);
	}
	return nullptr;
}

static unique_ptr<GlobalTableFunctionState> OpenDataFacadesInit(ClientContext &context, TableFunctionInitInput &input) {
	return make_uniq<OpenDataFacadesGlobalState>();
}

static void OpenDataFacadesScan(ClientContext &context, TableFunctionInput &data_p, DataChunk &output) {
	auto &state = data_p.global_state->Cast<OpenDataFacadesGlobalState>();
	auto &registry = GetEmbeddedRegistry();

	idx_t count = 0;
	while (state.source_offset < registry.size() && count < STANDARD_VECTOR_SIZE) {
		auto &source = registry[state.source_offset];
		if (state.facade_offset >= source.facades.size()) {
			state.source_offset++;
			state.facade_offset = 0;
			continue;
		}

		auto &facade = source.facades[state.facade_offset++];
		idx_t col = 0;
		output.data[col++].Append(Value(source.id));
		output.data[col++].Append(Value(facade.table_reference));
		output.data[col++].Append(Value(facade.facade_function));
		output.data[col++].Append(Value(facade.path_glob));
		output.data[col++].Append(Value(facade.example_sql));
		output.data[col++].Append(Value(facade.description));
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
		return TableFunctionReplacement("open_data_facades", "tables");
	}

	const OpenDataSource *source = nullptr;
	auto facade = FindFacadeByReference(table_name, source);
	if (!facade) {
		return nullptr;
	}

	auto path_glob = facade->path_glob;
	if (StringUtil::Contains(path_glob, "{release}")) {
		path_glob = StringUtil::Replace(path_glob, "{release}", ResolveRelease(context, *source));
	}

	auto table_function = make_uniq<TableFunctionRef>();
	vector<FunctionArgument> children;
	children.emplace_back(ConstantExpression::String(path_glob));
	children.emplace_back(Identifier("hive_partitioning"), ConstantExpression::Boolean(true));
	table_function->function = make_uniq<FunctionExpression>(Identifier("read_parquet"), std::move(children));
	table_function->alias = Identifier(facade->facade_function.empty() ? table_name : facade->facade_function);
	return std::move(table_function);
}

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

	// Release a `latest` facade resolves to: pinned variable, else cached release.latest.resolve_sql.
	ScalarFunction open_data_release("open_data_release", {LogicalType::VARCHAR}, LogicalType::VARCHAR,
	                                 OpenDataReleaseFunction);
	open_data_release.SetFallible();
	loader.RegisterFunction(open_data_release);

	TableFunction sources("open_data_sources", {}, OpenDataSourcesScan, OpenDataSourcesBind, OpenDataSourcesInit);
	loader.RegisterFunction(sources);

	TableFunction search("open_data_search", {LogicalType::VARCHAR}, OpenDataSourcesScan, OpenDataSearchBind,
	                     OpenDataSourcesInit);
	loader.RegisterFunction(search);

	TableFunction facades("open_data_facades", {}, OpenDataFacadesScan, OpenDataFacadesBind, OpenDataFacadesInit);
	loader.RegisterFunction(facades);

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
