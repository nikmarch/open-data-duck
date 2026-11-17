# Open Data Duck

An open, DuckDB-friendly index of pluggable public data tables.

Open Data Duck does **not** mirror datasets. It stores source metadata, licenses, attribution, and executable query recipes so DuckDB users and AI workers can discover and query authoritative open data safely.

## Goals

- Index authoritative public datasets as queryable table entries.
- Route each entry to the right engine: DuckDB extensions, SQL macros, `read_parquet`, STAC, ArcGIS FeatureServer, CKAN, Socrata, and similar sources.
- Track missing engines/connectors as GitHub issues.
- Let autonomous AI workers propose sources and maintenance work through reviewable issues/PRs.

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
```

A source can become `verified` only when it has:

- authoritative publisher URL
- license / terms URL
- attribution text
- DuckDB query recipe
- validation query
- freshness or release-check method

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
