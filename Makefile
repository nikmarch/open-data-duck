PROJ_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# Configuration for DuckDB's out-of-tree extension build.
EXT_NAME=open_data_duck
EXT_CONFIG=${PROJ_DIR}extension_config.cmake

include extension-ci-tools/makefiles/duckdb_extension.Makefile

.PHONY: test-extension-sql
test-extension-sql: release
	LOCAL_EXTENSION_REPO=$(PROJ_DIR)build/release/repository \
		build/release/test/unittest --autoloading available test/sql/open_data_duck.test
