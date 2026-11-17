#define DUCKDB_EXTENSION_MAIN

#include "open_data_duck_extension.hpp"
#include "open_data_duck_registry.generated.hpp"
#include "duckdb.hpp"
#include "duckdb/function/scalar_function.hpp"
#include "duckdb/main/extension/extension_loader.hpp"
#include <duckdb/parser/parsed_data/create_scalar_function_info.hpp>

namespace duckdb {

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

static void LoadInternal(ExtensionLoader &loader) {
	loader.RegisterFunction(ScalarFunction("open_data_duck_ping", {}, LogicalType::VARCHAR, OpenDataDuckPingFunction));
	loader.RegisterFunction(
	    ScalarFunction("open_data_duck_version", {}, LogicalType::VARCHAR, OpenDataDuckVersionFunction));
	loader.RegisterFunction(ScalarFunction("open_data_duck_registry_json", {}, LogicalType::VARCHAR,
	                                       OpenDataDuckRegistryJsonFunction));
	loader.RegisterFunction(ScalarFunction("open_data_duck_registry_source_count", {}, LogicalType::INTEGER,
	                                       OpenDataDuckRegistrySourceCountFunction));
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
