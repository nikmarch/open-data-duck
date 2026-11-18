# Open Data Duck

<p align="center">
  <img src="docs/assets/brand/odd-wordmark.svg" alt="Open Data Duck" width="360">
</p>

An open, DuckDB-friendly index of pluggable public data tables.

Open Data Duck does **not** mirror datasets. It stores source metadata, licenses, attribution, and executable query recipes so DuckDB users and AI workers can discover and query authoritative open data safely.

## Goals

- Index authoritative public datasets as queryable table entries.
- Route each entry to the right engine: DuckDB extensions, SQL macros, `read_parquet`, STAC, ArcGIS FeatureServer, CKAN, Socrata, and similar sources.
- Track missing engines/connectors as GitHub `engine` issues.
- Let autonomous AI workers propose sources and maintenance work through reviewable issues/PRs.

See [Engine maintenance track](docs/engine-maintenance.md) for the umbrella tracker, current connector tracks, and smoke-test policy.

## GitHub Pages

The project site is published from a dedicated GitHub Actions workflow to the default Pages URL: https://nikmarch.github.io/open-data-duck/.

The workflow builds the static landing page in `site/`, copies the checked-in brand assets from `docs/assets/brand/`, and deploys the generated `_site/` artifact. No custom domain is configured yet.

## Non-goals

- No copied public datasets in this repo.
- No private, paid, gray-area, or key-gated sources.
- No scraping where terms do not allow it.
- No unofficial source unless clearly marked as `candidate`.

## Initial source types

- `overture` — Overture Maps releases on public object storage.
- `stac` — SpatioTemporal Asset Catalogs and STAC APIs.
- `arcgis` — ArcGIS FeatureServer / MapServer layers.
- `parquet` — public Parquet / GeoParquet files.
- `ckan` — CKAN/data.gov-style catalogs.
- `socrata` — Socrata open-data portals.

## Overture source family

Open Data Duck is an **unofficial router/index**, not an Overture Maps mirror.
It does not copy Overture data into this repo.

The registry does not depend on an external `overture` DuckDB community extension.
Current Overture recipes use DuckDB's `httpfs` extension to query public Overture
release files directly from S3. The future `open_data_duck` extension should wrap
that release/path logic behind stable table functions.

Pinned release example:

```sql
SET VARIABLE overture_release = '2026-03-18.0';
```

## Registry entry lifecycle

```text
candidate -> verified -> deprecated
connector-blocked -> candidate or verified once the engine path is usable
```

A source can become `verified` only when it has:

- authoritative publisher URL
- license / terms URL
- attribution text
- DuckDB query recipe
- validation query
- freshness or release-check method

Use `connector-blocked` when the source is authoritative, but the DuckDB path depends on an extension or connector that users cannot install reliably yet.

## ArcGIS engine path

ArcGIS FeatureServer / MapServer layers are useful Open Data Duck targets, but the current DuckDB engine path is blocked on packaging.

The relevant extension is [`zbyte64/duckdb-arcgis`](https://github.com/zbyte64/duckdb-arcgis). Current limitations:

- it is not in DuckDB's community extension repository;
- installation is from a GitHub release artifact, not `INSTALL arcgis FROM community;`;
- binaries are unsigned, so DuckDB must be opened with unsigned extensions allowed before install/load;
- release binaries are tied to the exact DuckDB version and platform they were built for;
- the current `v0.2.1` release is built for DuckDB `v1.5.6`, while this project tests with DuckDB `>=2.0.0`;
- other DuckDB versions require building the extension from source with its submodules/toolchain.

Open Data Duck should build a small wrapper/macro/REST pagination path first: discover layer metadata, count features, and page with `resultOffset` / `resultRecordCount` so truncated ArcGIS responses are not treated as complete data. After that path is proven, contribute tests and packaging improvements upstream or to DuckDB community extensions. Forking `duckdb-arcgis` should be a fallback only if the upstream release path stalls.

## Development

Install dependencies and run the test suite:

```bash
uv sync --extra dev
uv run pytest
```

DuckDB is included in the `dev` extra. A quick real-engine smoke test:

```bash
uv run python -c "import duckdb; con = duckdb.connect(':memory:'); print(con.execute('select 42').fetchone())"
```

Network-backed DuckDB extension checks are opt-in locally and run as a separate CI job:

```bash
ODD_DUCKDB_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_duckdb_execution.py -k real_duckdb_can_install_and_load_supported_extensions
```

ArcGIS public FeatureServer smoke tests are also opt-in. They exercise REST metadata, count, and paginated query planning without unsigned DuckDB extensions:

```bash
ODD_ARCGIS_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_arcgis_engine.py
```

Socrata public SODA smoke tests are also opt-in. They count, plan `$limit`/`$offset` pages, and read one planned page through DuckDB `httpfs` against NYC Open Data:

```bash
ODD_SOCRATA_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_socrata_engine.py
```

Validate the registry locally:

```bash
uv run odd validate
```

Build and smoke-test the native DuckDB extension scaffold:

```bash
git submodule update --init --recursive
make
make test
```

Pull requests and `main` also run the Main Extension Distribution Pipeline. It
uses DuckDB's extension CI tooling to publish a Linux x64
`open_data_duck-v2.0.0-extension-linux_amd64` GitHub Actions artifact, then
smoke-tests that artifact with DuckDB's unsigned-extension mode. Actions
artifacts are CI evidence only; the user-facing download path is a versioned
GitHub prerelease asset from the Pre-community Extension Release workflow.

### Pre-community extension releases

The Pre-community Extension Release workflow runs manually or from version tags.
It rebuilds the Linux x64 extension, smokes the downloaded artifact, then attaches
`open_data_duck-v2.0.0-linux_amd64.duckdb_extension` to a draft release or public
prerelease. These are temporary pre-community unsigned builds for validation, not signed community
extension releases.

Compatibility:

| DuckDB version | OS/arch | Release asset |
| --- | --- | --- |
| v2.0.0 | Linux x64 (`linux_amd64`) | `open_data_duck-v2.0.0-linux_amd64.duckdb_extension` |

The binary is DuckDB-version- and platform-specific. Do not use
`INSTALL open_data_duck FROM community;` yet; the extension is not in DuckDB's
community repository and the release asset is unsigned.

### Temporary custom extension repository

The GitHub Pages deployment also publishes the same Linux x64 build in DuckDB's
custom extension repository layout at:

```text
https://nikmarch.github.io/open-data-duck/extensions/v2.0.0/linux_amd64/open_data_duck.duckdb_extension.gz
```

Install from the repository prefix while unsigned extensions are explicitly
enabled:

```sql
-- Start the CLI as: duckdb -unsigned :memory:
FORCE INSTALL open_data_duck FROM 'https://nikmarch.github.io/open-data-duck/extensions';
LOAD open_data_duck;
SELECT open_data_duck_ping();
```

This is a temporary pre-community bridge. It uses the DuckDB repository path
layout, but it is not the future signed community repository flow and it still
requires unsigned-extension mode until Open Data Duck has signed community
artifacts.

CLI smoke test after downloading a release asset:

```bash
curl --fail --location \
  --output open_data_duck.duckdb_extension \
  https://github.com/nikmarch/open-data-duck/releases/download/v0.1.0-pre.1/open_data_duck-v2.0.0-linux_amd64.duckdb_extension

duckdb -unsigned :memory:
LOAD './open_data_duck.duckdb_extension';
SELECT open_data_duck_ping();
SELECT count(*) > 0 FROM open_data_sources();
```

Python smoke test with unsigned extensions enabled:

```python
import duckdb

con = duckdb.connect(":memory:", config={"allow_unsigned_extensions": "true"})
con.execute("LOAD './open_data_duck.duckdb_extension'")
print(con.execute("SELECT open_data_duck_ping()").fetchone()[0])
print(con.execute("SELECT count(*) > 0 FROM open_data_sources()").fetchone()[0])
```

The native surface is deliberately small while the registry and SQL helper
contracts stay in Python/SQL. It only reads the embedded registry and returns SQL
recipes; it does not execute sources or touch the network:

```sql
LOAD open_data_duck;
SELECT open_data_duck_ping();
SELECT open_data_duck_version();
SELECT open_data_duck_registry_source_count();
SELECT open_data_duck_registry_json();

-- Core registry functions (mirror `odd search` / `odd sql`)
SELECT * FROM open_data_sources();
SELECT id, status FROM open_data_sources() WHERE source_type = 'socrata';
SELECT id FROM open_data_search('stac sentinel');
SELECT open_data_sql('overture.maps.release');
SELECT open_data_validation_sql('overture.maps.release');
```

`open_data_sources()` returns one row per registry source with columns `id`,
`name`, `source_type`, `status`, `description`, `authority`, `homepage`,
`license_url`, `attribution`, `tags`, `extensions`, `install`, `example_query`,
and `validation_query`. `open_data_search(query)` keeps the CLI rule: every
whitespace-separated term must match case-insensitively; use plain `WHERE`
clauses instead of the CLI's `--type`/`--status` flags. `open_data_sql(id)` and
`open_data_validation_sql(id)` render the same text as `odd sql` and raise a
clear error for unknown ids. `open_data_table(...)` is intentionally not
implemented yet.

Run only the extension SQL tests through DuckDB's sqllogictest runner:

```bash
git submodule update --init --recursive
make test-extension-sql
```

### Embedded registry contract

The native extension must not depend on Python, PyYAML, or repo-relative files at
runtime. `registry/sources.yml` stays the single source of truth; a generated C++
header embeds a JSON snapshot of it into the extension binary:

```text
registry/sources.yml  --(uv run odd generate-extension-registry)-->  src/include/open_data_duck_registry.generated.hpp
```

Contributor workflow when the registry changes:

```bash
uv run odd generate-extension-registry          # rewrite the header
uv run odd generate-extension-registry --check  # exit non-zero on drift (also runs in CI and pytest)
```

The embedded JSON has `schema_version`, `source_count`, and a `sources` array. Each
source carries `id`, `name`, `source_type`, `status`, `description`, `authority`,
`homepage`, `license_url`, `attribution`, `tags`, and a `duckdb` object with
`extensions`, `install`, `example_query`, and `validation_query`. Bump
`schema_version` in `odd/extension_registry.py` when the shape changes in a
non-additive way.

Search registered sources:

```bash
uv run odd search overture
uv run odd search "stac sentinel" --type stac
```

Print the pretty human/AI source index:

```bash
uv run odd index
uv run odd index --format json
uv run odd show overture.maps.release
uv run odd generate-index
```

Discover and cache DuckDB-visible source schemas:

```bash
uv run odd schema inspect local.source_id
uv run odd schema refresh local.source_id
uv run odd schema check local.source_id
```

The DuckDB-side SQL helper contract lives in `sql/open_data_duck.sql` and is tested by
pure SQL files under `tests/e2e/`. Those SQL cases call the same macros future
DuckDB users/functions should call:

```sql
SELECT * FROM open_data_schema('SELECT 1::INTEGER AS id');
SELECT * FROM open_data_schema_diff(
  'SELECT 1::INTEGER AS id',
  'SELECT 1::INTEGER AS id, ''a''::VARCHAR AS name'
);
```

`schema refresh` writes `schema/source-manifest.json` by default. DuckDB is the
inspector; the JSON manifest is the cached product contract. Additive columns are
reported as safe info, while missing cached columns, incompatible type changes,
or source inspection failures make `schema check` exit non-zero before app paths
try to use the source.

`registry/sources.yml` is the only source of truth for source configuration.
The checked-in `docs/index.md` file is generated from that YAML for human review.
JSON is rendered on demand with `odd index --format json` so the repo does not
store duplicate config in a second format.

Run the optional MCP server for AI clients:

```bash
uv sync --extra mcp
uv run python -m odd.mcp_server
```

MCP tools exposed by the server:

- `search_sources_tool` — search sources by text/type/status.
- `get_source` — return one AI-friendly source record.
- `get_source_sql` — return executable DuckDB SQL for a source.
- `get_source_schema` — return the cached DuckDB-discovered schema manifest for a source.

Print the DuckDB SQL recipe for a source:

```bash
uv run odd sql overture.maps.release
uv run odd sql overture.maps.release --validation --no-install
```

The same validation and test checks run in GitHub Actions on pushes and pull requests.

## Community extension release path

Future install shape:

```sql
INSTALL open_data_duck FROM community;
LOAD open_data_duck;

SELECT * FROM open_data_search('buildings alaska');
SELECT * FROM open_data_table('overture.places', bbox := [-150, 60, -149, 61]);
```

Release checklist:

1. Build the extension from DuckDB's C++ extension template.
2. Add sqllogictest coverage for search and table functions.
3. Publish a source commit that builds with DuckDB's extension CI toolchain.
4. Open a PR to `duckdb/community-extensions` with an `open_data_duck` descriptor.
5. After community CI signs/builds it, users install with `INSTALL open_data_duck FROM community;`.

For now the repo contains the registry/schema/CLI plus real DuckDB validation tests.
Engine code comes next.
