#!/usr/bin/env bash
# Build the open_data_duck extension locally and smoke test it.
#
# Usage:
#   scripts/build_local_extension.sh            # build + smoke test
#   scripts/build_local_extension.sh --no-test  # build only
#   scripts/build_local_extension.sh --sqltest  # build + run sqllogictest suite
#
# First build compiles DuckDB from source (10-30 min). Later builds are incremental.
# Speed tips: brew install ninja ccache

set -euo pipefail

cd "$(dirname "$0")/.."

RUN_SMOKE=1
RUN_SQLTEST=0
for arg in "$@"; do
  case "$arg" in
    --no-test) RUN_SMOKE=0 ;;
    --sqltest) RUN_SQLTEST=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 1 ;;
  esac
done

# 1. Submodules (duckdb + extension-ci-tools) must be checked out.
if [ ! -f duckdb/CMakeLists.txt ] || [ ! -f extension-ci-tools/makefiles/duckdb_extension.Makefile ]; then
  echo ">> initializing submodules"
  git submodule update --init --recursive
fi

# 2. Keep embedded registry header in sync with split registry source files.
if command -v uv >/dev/null; then
  echo ">> regenerating extension registry header"
  uv run odd generate-extension-registry
fi

# 3. Build. Use ninja + ccache when available.
GEN_ARGS=()
command -v ninja >/dev/null && GEN_ARGS+=(GEN=ninja)
if command -v ccache >/dev/null; then
  export EXT_FLAGS="${EXT_FLAGS:-} -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache"
fi
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-$(sysctl -n hw.ncpu 2>/dev/null || nproc)}"

echo ">> building release"
make release ${GEN_ARGS[@]+"${GEN_ARGS[@]}"}

EXT=build/release/extension/open_data_duck/open_data_duck.duckdb_extension
DUCKDB_BIN=build/release/duckdb
test -f "$EXT"
echo ">> built: $EXT"
echo ">> duckdb shell with extension statically linked: $DUCKDB_BIN"

# 4. Smoke test: load loadable extension into the freshly built shell.
if [ "$RUN_SMOKE" = 1 ]; then
  echo ">> smoke test"
  "$DUCKDB_BIN" -unsigned :memory: <<SQL
LOAD '$EXT';
SELECT open_data_duck_ping();
SELECT open_data_duck_version();
SELECT open_data_duck_registry_source_count();
SELECT count(*) > 0 FROM open_data_sources();
SQL
fi

# 5. Full sqllogictest suite (test/sql/*.test).
if [ "$RUN_SQLTEST" = 1 ]; then
  echo ">> sqllogictest"
  make test-extension-sql ${GEN_ARGS[@]+"${GEN_ARGS[@]}"}
fi

cat <<MSG

Done. Try it interactively:
  $DUCKDB_BIN                      # extension already linked in
  duckdb -unsigned -c "LOAD '$PWD/$EXT'; SELECT open_data_duck_ping();"   # system duckdb (must match v2.0.0)
MSG
