#define DUCKDB_EXTENSION_MAIN

#include "open_data_duck_extension.hpp"
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

static void LoadInternal(ExtensionLoader &loader) {
	loader.RegisterFunction(ScalarFunction("open_data_duck_ping", {}, LogicalType::VARCHAR, OpenDataDuckPingFunction));
	loader.RegisterFunction(
	    ScalarFunction("open_data_duck_version", {}, LogicalType::VARCHAR, OpenDataDuckVersionFunction));
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
