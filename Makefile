PROJ_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# Configuration for DuckDB's out-of-tree extension build.
EXT_NAME=open_data_duck
EXT_CONFIG=${PROJ_DIR}extension_config.cmake

include extension-ci-tools/makefiles/duckdb_extension.Makefile

REGISTRY_SOURCES := $(wildcard $(PROJ_DIR)registry/sources/*.yml) $(wildcard $(PROJ_DIR)registry/sources/*.yaml)
REGISTRY_HEADER := $(PROJ_DIR)src/include/open_data_duck_registry.generated.hpp
REGISTRY_GENERATOR_INPUTS := $(PROJ_DIR)registry/sources.yml $(REGISTRY_SOURCES) $(PROJ_DIR)odd/extension_registry.py $(PROJ_DIR)odd/registry_model.py

$(REGISTRY_HEADER): $(REGISTRY_GENERATOR_INPUTS)
	cd $(PROJ_DIR) && \
		if command -v uv >/dev/null 2>&1; then \
			uv run odd generate-extension-registry; \
		else \
			python3 -m pip install . && \
			python3 -m odd.cli generate-extension-registry; \
		fi

release: $(REGISTRY_HEADER)

.PHONY: test-extension-sql
test-extension-sql: release
	LOCAL_EXTENSION_REPO=$(PROJ_DIR)build/release/repository \
		build/release/test/unittest --autoloading available "test/sql/*"
