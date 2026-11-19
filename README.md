# Open Data Duck

<p align="center">
  <img src="docs/assets/brand/odd-wordmark.svg" alt="Open Data Duck" width="360">
</p>

Open Data Duck is a DuckDB-friendly index of public data tables.
The goal is simple: install the plugin, search for a table, then query that table from DuckDB.
It does not mirror datasets; it maps friendly table names to authoritative public data.

## Quick start: install the pre-community extension

The extension is not in DuckDB community yet. Use DuckDB v2.0.0 with unsigned extensions enabled.

```bash
set -euo pipefail

release_tag="v0.1.0-pre.1"
duckdb_version="v2.0.0"
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) platform="osx_arm64" ;;
  Linux-x86_64) platform="linux_amd64" ;;
  *) echo "unsupported platform: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

rm -f open_data_duck.duckdb_extension

curl --fail --location \
  --output open_data_duck.duckdb_extension \
  "https://github.com/nikmarch/open-data-duck/releases/download/${release_tag}/open_data_duck-${duckdb_version}-${platform}.duckdb_extension"

xattr -dr com.apple.quarantine open_data_duck.duckdb_extension 2>/dev/null || true
codesign --force --deep --sign - open_data_duck.duckdb_extension 2>/dev/null || true

duckdb -unsigned :memory: <<'SQL'
LOAD './open_data_duck.duckdb_extension';
SELECT open_data_duck_ping();
SELECT count(*) > 0 FROM open_data_sources();
SQL
```

Expected output:

```text
open_data_duck: pong
true
```

Important: the GitHub release asset is versioned, but the local filename must be the canonical local filename `open_data_duck.duckdb_extension`. DuckDB derives the entrypoint name from the local filename. Loading `open_data_duck-v2.0.0-<platform>.duckdb_extension` directly will fail.

Each GitHub prerelease asset is DuckDB-version- and platform-specific. These are temporary pre-community unsigned builds, not signed community artifacts. The Pre-community Extension Release workflow publishes:

- `open_data_duck-v2.0.0-linux_amd64.duckdb_extension`
- `open_data_duck-v2.0.0-osx_arm64.duckdb_extension`

The Main Extension Distribution Pipeline also builds the CI artifact `open_data_duck-v2.0.0-extension-linux_amd64`. Install commands and release names may change while the native extension is in active current development.

## Intended plugin flow

This is the product shape Open Data Duck is moving toward:

```sql
INSTALL open_data_duck;
LOAD open_data_duck;

-- The extension resolves ODD table references with a replacement scan.
ATTACH 'open_data_duck' AS odd;

-- Search the attached index table.
SELECT *
FROM odd.index
WHERE list_contains(tags, 'buildings')
   OR name ILIKE '%building%';

-- Inspect only queryable data tables.
SELECT table_reference, path_glob
FROM odd.tables
WHERE table_reference = 'odd.overturemaps.latest.buildings';

-- Query the matched table through an ODD table facade.
SELECT *
FROM odd.overturemaps.latest.buildings
WHERE bbox.xmin <= -149
  AND bbox.xmax >= -150
  AND bbox.ymin <= 61
  AND bbox.ymax >= 60
LIMIT 10;
```

`odd.index` is the SQL-searchable catalog. It returns queryable references such as `odd.overturemaps.latest.buildings`. The native extension resolves those references with replacement scans into DuckDB readers. Keep bbox filters tight; Overture tables are large.

### How `latest` is resolved

`odd.overturemaps.latest.*` facades carry a `{release}` placeholder in their `path_glob`. On the first query in a process the extension runs the registry's `release.latest.resolve_sql` (a lookup against `https://stac.overturemaps.org/catalog.json`), fills in the release, and caches it for the rest of the process. Pin a release instead with the source's `release.pinned.duckdb_setting` variable; the pin always wins over the lookup:

```sql
SET VARIABLE overture_release = '2026-10-21.0';
SELECT open_data_release('overture.maps.release');  -- 2026-10-21.0
RESET VARIABLE overture_release;
SELECT open_data_release('overture.maps.release');  -- resolved from the STAC catalog, then cached
```

## Current pre-community behavior

The extension also returns SQL recipes and facade metadata for inspection.

```sql
LOAD './open_data_duck.duckdb_extension';
SELECT open_data_sql('overture.maps.release');
```

Copy the returned SQL and run it in DuckDB. For Overture buildings in a small bbox, it is this shape:

```sql
LOAD httpfs;
SET s3_region='us-west-2';
SET VARIABLE overture_release = '2026-10-21.0';
SET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';

SELECT *
FROM read_parquet(
  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=buildings/type=building/*',
  hive_partitioning = true
)
WHERE bbox.xmin <= -149
  AND bbox.xmax >= -150
  AND bbox.ymin <= 61
  AND bbox.ymax >= 60
LIMIT 10;
```

To read a different Overture table, change the path:

- places: `/theme=places/type=place/*`
- buildings: `/theme=buildings/type=building/*`
- road segments: `/theme=transportation/type=segment/*`
- addresses: `/theme=addresses/type=address/*`

Keep bounding boxes tight. Overture files are large.

From the repo CLI, you can print the same recipe without loading the extension:

```bash
uv run odd sql overture.maps.release
uv run odd sql overture.maps.release --validation --no-install
```

## Find sources

```sql
LOAD './open_data_duck.duckdb_extension';

SELECT id, name, status FROM open_data_sources();
SELECT id, name, table_reference FROM open_data_search('building');
SELECT table_reference, path_glob FROM open_data_facades();
SELECT id, name, table_reference FROM odd.index WHERE list_contains(tags, 'buildings');
SELECT table_reference, path_glob FROM odd.tables;
SELECT open_data_sql('overture.maps.release');
SELECT open_data_validation_sql('overture.maps.release');
```

Implemented native functions:

- `open_data_duck_ping()`
- `open_data_duck_version()`
- `open_data_duck_registry_source_count()`
- `open_data_duck_registry_json()`
- `open_data_sources()`
- `open_data_search(query)`
- `open_data_facades()`
- `open_data_sql(id)`
- `open_data_validation_sql(id)`
- `open_data_release(id)`

The first table-like facade is an Overture replacement scan for `odd.overturemaps.latest.buildings`, with the same pattern exposed for places, roads, and addresses.

## Temporary custom extension repository

GitHub Pages also publishes a DuckDB custom repository:

```text
https://nikmarch.github.io/open-data-duck/extensions/v2.0.0/linux_amd64/open_data_duck.duckdb_extension.gz
https://nikmarch.github.io/open-data-duck/extensions/v2.0.0/osx_arm64/open_data_duck.duckdb_extension.gz
```

```sql
-- Start DuckDB as: duckdb -unsigned :memory:
FORCE INSTALL open_data_duck FROM 'https://nikmarch.github.io/open-data-duck/extensions';
LOAD open_data_duck;
SELECT open_data_duck_ping();
```

This is a temporary pre-community bridge. Use `INSTALL open_data_duck FROM community;` only after the community extension is accepted.

Python load example:

```python
import duckdb

con = duckdb.connect(":memory:", config={"allow_unsigned_extensions": "true"})
con.execute("LOAD './open_data_duck.duckdb_extension'")
print(con.execute("SELECT open_data_duck_ping()").fetchone()[0])
```

## Development

```bash
uv sync --extra dev
uv run pytest
uv run odd validate
```

Build the native extension:

```bash
git submodule update --init --recursive
make release
make test-extension-sql
```

Generate derived registry artifacts after changing `registry/sources.yml`:

```bash
uv run odd generate-extension-registry
uv run odd generate-extension-registry --check
uv run odd generate-index
```

Useful CLI commands:

```bash
uv run odd search overture
uv run odd show overture.maps.release
uv run odd index
uv run odd index --format json
```

Optional network smoke tests:

```bash
ODD_DUCKDB_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_duckdb_execution.py -k real_duckdb_can_install_and_load_supported_extensions
ODD_ARCGIS_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_arcgis_engine.py
ODD_SOCRATA_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_socrata_engine.py
```

## Project notes

- Source lifecycle: `candidate -> verified -> deprecated`; `connector-blocked` means the source is authoritative but the DuckDB engine path still needs work.
- Engine work is tracked in the [Engine maintenance track](docs/engine-maintenance.md).
- Community submission notes live in [`docs/community-extension-submission.md`](docs/community-extension-submission.md), with the descriptor at [`docs/community-extensions/open_data_duck/description.yml`](docs/community-extensions/open_data_duck/description.yml).
- MCP server for AI clients: `uv sync --extra mcp && uv run python -m odd.mcp_server`.

Non-goals:

- no copied public datasets in this repo
- no private, paid, gray-area, or key-gated sources
- no scraping where terms do not allow it
