# Engine maintenance track

Issue [#7](https://github.com/nikmarch/open-data-duck/issues/7) is the umbrella tracker for missing or immature DuckDB engines, connectors, table functions, and extension packaging.

Open Data Duck should not mark a source as queryable just because an authoritative endpoint exists. If the DuckDB path is missing, immature, unsigned, version-pinned, or not packaged for normal users, track that gap as an `engine` issue and keep affected registry entries `connector-blocked` until the path is proven.

## Current engine issues

| Track | Issue | Purpose |
| --- | --- | --- |
| ArcGIS packaging and compatibility | [#15](https://github.com/nikmarch/open-data-duck/issues/15) | Stabilize the ArcGIS FeatureServer / MapServer path, with public-source smoke coverage and honest packaging limits. |
| CKAN/DCAT query path | [#16](https://github.com/nikmarch/open-data-duck/issues/16) | Define how CKAN and DCAT catalog resources become DuckDB-queryable registry entries. |
| Socrata query path | [#17](https://github.com/nikmarch/open-data-duck/issues/17) | Define a repeatable Socrata API/export path with public-source smoke tests. |

## Policy

- Missing or immature engines must have an `engine` issue before workers or maintainers claim the source is usable.
- Source-candidate issues and PRs must link the relevant engine issue when a source is blocked by connector work.
- Engine work must include real smoke tests against public sources before related registry entries move to `candidate` or `verified`.
- Smoke tests should prove the risky part of the engine path: pagination, install/load shape, API export format, authentication-free access, or version compatibility.
- Normal CI should avoid unsigned native-extension state unless that state is explicitly part of an opt-in engine test.

## ArcGIS first target

ArcGIS FeatureServer and MapServer layers remain the first engine-maintenance target. The current path is:

1. Keep ArcGIS registry entries `connector-blocked` while `duckdb-arcgis` is unsigned, version-pinned, and unavailable from DuckDB community extensions.
2. Build the wrapper/macro/REST pagination path first, so Open Data Duck can count records and page with `resultOffset` / `resultRecordCount` instead of treating truncated responses as complete.
3. Add public-source smoke coverage for paginated layers.
4. Pursue upstream or community-extension packaging after the REST path is proven.
5. Fork native extension work only if the upstream/community path stalls.

Do not emit or document `INSTALL arcgis FROM community;` as a working user path until it succeeds against real DuckDB.
