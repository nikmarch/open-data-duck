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

## Example direction

```sql
-- future shape
INSTALL open_data_duck FROM community;
LOAD open_data_duck;

SELECT * FROM open_data_search('buildings alaska');
SELECT * FROM open_data_table('overture.places', bbox := [-150, 60, -149, 61]);
```

For now the repo starts with the registry/schema and issues. Engine code comes next.
