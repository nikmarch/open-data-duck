# Open Data Duck

<p align="center">
  <img src="docs/assets/brand/odd-wordmark.svg" alt="Open Data Duck" width="360">
</p>

Open Data Duck is a DuckDB-friendly index of public data tables.
The goal is simple: install the plugin, search for a table, then query that table from DuckDB.
It does not mirror datasets; it maps friendly table names to authoritative public data.

## Quick start: install the latest pre-community extension

Open Data Duck is not in DuckDB community extensions yet. For normal use, install from the temporary DuckDB custom extension repository published by GitHub Pages. It always serves the latest published Open Data Duck build for the current DuckDB version and platform.

```sql
-- Start DuckDB as: duckdb -unsigned :memory:
FORCE INSTALL open_data_duck FROM 'https://nikmarch.github.io/open-data-duck/extensions';
LOAD open_data_duck;
SELECT open_data_duck_ping();
SELECT count(*) > 0 FROM open_data_sources();
```

Expected output includes:

```text
open_data_duck: pong
true
```

These are temporary unsigned builds, not signed community artifacts. Start DuckDB with unsigned extensions enabled until Open Data Duck is accepted into DuckDB community extensions. Use `INSTALL open_data_duck FROM community;` only after that acceptance.

Manual GitHub release asset downloads remain available for debugging, rollback, and checksum verification, but they are not the normal install path.

## Intended plugin flow

This is the product shape Open Data Duck is moving toward:

```sql
INSTALL open_data_duck;
LOAD open_data_duck;

-- Overture Maps public S3 data lives in us-west-2.
-- Set this before the first Overture query to avoid S3 region retry warnings.
SET s3_region='us-west-2';

-- Attach the virtual ODD catalog.
ATTACH ':memory:' AS odd (TYPE open_data_duck);

-- Search the attached index view.
SELECT *
FROM odd.index
WHERE list_contains(tags, 'buildings')
   OR name ILIKE '%building%';

-- Inspect only queryable data tables (discovered from the source, cached per process).
SELECT table_reference, reader, path
FROM odd.tables
WHERE table_reference = 'odd.overturemaps.latest.building';

-- Query the matched table through an ODD table facade.
SELECT *
FROM odd.overturemaps.latest.building
WHERE bbox.xmin <= -149
  AND bbox.xmax >= -150
  AND bbox.ymin <= 61
  AND bbox.ymax >= 60
LIMIT 10;
```

`odd.index` is the SQL-searchable catalog view. Each source that exposes data tables carries a `namespace` such as `odd.overturemaps.latest`. The native extension exposes the catalog through `ATTACH ... (TYPE open_data_duck)` and keeps resolving `namespace.<table>` references with replacement scans into DuckDB readers. Query `odd.tables` first and copy the `table_reference` exactly; Overture facade table names are singular, for example `place`, `building`, `address`, and `segment`. Keep bbox filters tight; Overture tables are large.

### How `latest` tables are discovered

The registry stores no table paths. Each source with a namespace carries two SQL snippets:

- `release.latest.resolve_sql` returns the current release id (Overture: the `latest` child of `https://stac.overturemaps.org/catalog.json`; Census: the newest `GENZ<year>` directory; NOAA: the newest `by_year` file).
- `duckdb.tables.discover_sql` returns one `(name, reader, path)` row per table for a given `{release}` (Overture: every STAC collection of the release; Census: every county/tract shapefile at every scale).

On the first touch of `odd.tables` or of any `namespace.<table>` in a process, the extension runs both snippets on its own connection and caches the rows for that `source@release`. Pin a release with the source's `release.pinned.duckdb_setting` variable; the pin always wins over the lookup and gets its own cache entry:

```sql
SET VARIABLE overture_release = '2026-10-21.0';
SELECT open_data_release('overture.maps.release');  -- 2026-10-21.0
RESET VARIABLE overture_release;
SELECT open_data_release('overture.maps.release');  -- resolved from the STAC catalog, then cached
SELECT table_reference, path FROM odd.tables WHERE source_id = 'overture.maps.release';
```

## Current pre-community behavior

The extension also returns SQL recipes and table metadata for inspection.

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
SELECT id, name, namespace FROM open_data_search('building');
SELECT table_reference, reader, path FROM open_data_tables();
SELECT id, name, namespace FROM odd.index WHERE list_contains(tags, 'buildings');
SELECT table_reference, reader, path FROM odd.tables;
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
- `open_data_tables()`
- `open_data_sql(id)`
- `open_data_validation_sql(id)`
- `open_data_release(id)`

Table namespaces today, each discovered from the source at first use. Readers are `read_parquet` (with `hive_partitioning`), `read_csv`, `read_json`, or `st_read`:

| namespace | tables | reader | pin variable |
| --- | --- | --- | --- |
| `odd.overturemaps.latest` | every STAC collection of the release (`building`, `place`, `segment`, `address`, `division`, `land`, `water`, ...) | `read_parquet` | `overture_release` |
| `odd.census.latest` | `county_20m`, `county_5m`, `county_500k`, `tract_5m`, `tract_500k`, ... | `st_read` (needs `LOAD spatial`) | `census_cartographic_year` |
| `odd.noaa.latest` | `ghcn_daily`, `storm_events_details`, `storm_events_fatalities`, `storm_events_locations` | `read_csv` | `noaa_ghcn_year`, `noaa_storm_events_year` |

### Registry validation pairs

The registry contract is moving toward proof instead of brochure metadata. The old registry shape required descriptive fields such as `description` and `homepage`; those are now optional. The required source fields are the smaller legal/execution core: `id`, `name`, `status`, `source_type`, `authority`, `license_url`, `attribution`, and `duckdb`.

There is no separate `freshness` contract. If a source needs update logic, keep it in release discovery or a validation pair.

For queryable facade work, prefer validation pairs over extra prose. A table-like entry can carry `validations` where each validation `id` is the canonical ODD table reference. The `odd_sql` side is also the user-facing example snippet; the `direct_sql` side is only the control query used to prove ODD returns the same data:

```yaml
validations:
  - id: odd.overturemaps.latest.place
    direct_sql: |
      SELECT ... FROM read_parquet('s3://.../theme=places/type=place/*')
    odd_sql: |
      SELECT ... FROM odd.overturemaps.latest.place
    compare: exact
```

For pinned releases, keep the ODD path SQL-safe. Use `x` separators instead of punctuation:

```sql
SELECT * FROM odd.overturemaps.x2026x10x21.place;
```

The same validation should select the same columns, filters, ordering, and limit in direct SQL and ODD SQL so the result sets can be compared.

## Temporary custom extension repository

GitHub Pages publishes the primary pre-community DuckDB custom repository:

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

Use this path for normal pre-community installs. It fetches the latest GitHub Pages-published build for the current DuckDB version and platform. This is still a temporary unsigned bridge; use `INSTALL open_data_duck FROM community;` only after the community extension is accepted.

Manual release-asset install example:

```bash
bash <<BASH
set -euo pipefail

release_tag=v0.1.0
case \$(uname -s)-\$(uname -m) in
  Darwin-arm64) platform=osx_arm64 ;;
  Linux-x86_64) platform=linux_amd64 ;;
  *) echo unsupported platform: \$(uname -s)-\$(uname -m) >&2; exit 1 ;;
esac

curl --fail --location --show-error \
  --output open_data_duck.duckdb_extension \
  h""ttps://git""hub"".com/nikmarch/open-data-duck/releases/download/\${release_tag}/open_data_duck-v2.0.0-\${platform}.duckdb_extension

xattr -dr com.apple.quarantine open_data_duck.duckdb_extension 2>/dev/null || true
codesign --force --deep --sign - open_data_duck.duckdb_extension 2>/dev/null || true

duckdb -unsigned :memory: <<SQL
LOAD './open_data_duck.duckdb_extension';
SELECT open_data_duck_ping();
SELECT count(*) > 0 FROM open_data_sources();
SQL
BASH
```

The downloaded file is saved as `open_data_duck.duckdb_extension` on purpose. DuckDB derives the extension entrypoint name from the local filename; loading the versioned asset filename directly can fail.

Python load example:

```python
import duckdb

con = duckdb.connect(":memory:", config={"allow_unsigned_extensions": "true"})
con.execute("LOAD './open_data_duck.duckdb_extension'")
print(con.execute("SELECT open_data_duck_ping()").fetchone()[0])
```

## Release from GitHub Actions

Use the existing **Pre-community Extension Release** workflow for pre-community binaries:

1. Open GitHub Actions -> **Pre-community Extension Release** -> **Run workflow**.
2. Select `main` as the workflow ref.
3. Enter a new tag such as `v0.1.0-pre.4`.
4. Keep `create_tag=true` so the workflow creates the Git tag from `target_ref`.
5. Use `draft=true` for a private test release, or `draft=false` to publish a public prerelease.

The workflow validates the tag, refuses to overwrite existing tags/releases unless `update_existing=true`, builds Linux/macOS assets, smoke-tests the Linux asset, and writes release notes with a one-copy-paste install block for that exact tag.

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
uv run odd generate-site
```

Useful CLI commands:

```bash
uv run odd search overture
uv run odd show overture.maps.release
uv run odd index
uv run odd index --format json
```

Render a local Overture spatial-query map from a pre-community release:

```bash
scripts/render_spatial_map.py \
  --lat 61.60757040082204 \
  --lon -149.38067090928263 \
  --radius-m 100 \
  --limit 5 \
  --release-tag v0.1.0-pre.N \
  --output /tmp/odd-spatial-map.png
```

The helper downloads DuckDB v2.0.0 plus the selected `open_data_duck` release asset, resolves the Overture release through ODD, runs bounded spatial queries, and writes both a PNG map and a Markdown report.

Optional network smoke tests:

```bash
ODD_DUCKDB_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_duckdb_execution.py -k real_duckdb_can_install_and_load_supported_extensions
ODD_ARCGIS_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_arcgis_engine.py
ODD_SOCRATA_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_socrata_engine.py
```

## Project notes

- Source lifecycle: `candidate -> verified -> deprecated`; `connector-blocked` means the source is authoritative but the DuckDB engine path still needs work.
- Engine work is tracked in the [Engine maintenance track](docs/engine-maintenance.md).
- Source-controlled discovery SQL runs inside the [source SQL security boundary](docs/plugin-sql-security.md), isolated from the caller's session secrets and attached databases.
- Community submission notes live in [`docs/community-extension-submission.md`](docs/community-extension-submission.md), with the descriptor at [`docs/community-extensions/open_data_duck/description.yml`](docs/community-extensions/open_data_duck/description.yml).
- MCP server for AI clients: `uv sync --extra mcp && uv run python -m odd.mcp_server`.

Non-goals:

- no copied public datasets in this repo
- no private, paid, gray-area, or key-gated sources
- no scraping where terms do not allow it
