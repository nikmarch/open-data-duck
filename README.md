# Open Data Duck

An open, DuckDB-friendly index of pluggable public data tables.

Open Data Duck does **not** mirror datasets. It stores source metadata, licenses, attribution, and executable query recipes so DuckDB users and AI workers can discover and query authoritative open data safely.

## Goals

- Index authoritative public datasets as queryable table entries.
- Route each entry to the right engine: DuckDB extensions, SQL macros, `read_parquet`, STAC, ArcGIS FeatureServer, CKAN, Socrata, and similar sources.
- Track missing engines/connectors as GitHub `engine` issues.
- Let autonomous AI workers propose sources and maintenance work through reviewable issues/PRs.

See [Engine maintenance track](docs/engine-maintenance.md) for the umbrella tracker, current connector tracks, and smoke-test policy.

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

Network-backed DuckDB extension checks are opt-in so normal CI stays stable:

```bash
ODD_DUCKDB_NETWORK_TESTS=1 uv run pytest tests/test_duckdb_execution.py
```

Socrata public SODA smoke tests are also opt-in. They count, plan `$limit`/`$offset` pages, and read one planned page through DuckDB `httpfs` against NYC Open Data:

```bash
ODD_SOCRATA_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_socrata_engine.py
```

Validate the registry locally:

```bash
uv run odd validate
```

Search registered sources:

```bash
uv run odd search overture
uv run odd search "stac sentinel" --type stac
```

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
