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

## CKAN/DCAT direct-resource path

CKAN and DCAT catalogs should be treated as discovery metadata first, not as a DuckDB engine by themselves. The supported path is:

1. Use CKAN `package_show` / `package_search` or a DCAT distribution list to discover resource URLs.
2. Move a registry entry to `candidate` only when at least one public distribution is directly readable by DuckDB (`read_csv_auto`, `read_json_auto`, `read_parquet`, or `ST_Read`) over `httpfs`.
3. Keep entries `connector-blocked` when the catalog only exposes API pages, authenticated downloads, zipped archives without a stable unpacking path, non-tabular documents, or formats that need a future wrapper.
4. Do not emit or document a fictional `ckan_*` / `dcat_*` DuckDB table function. If a table function or extension appears later, prove it with real DuckDB before registry entries depend on it.
5. Public smoke coverage must fetch at least one official catalog package/feed and show that a resource URL can be converted into DuckDB SQL using `httpfs`.

A CKAN/DCAT registry entry can move to `verified` only after the direct resource SQL itself is run against the public source or a stable wrapper is proven by normal CI.

## ArcGIS first target

ArcGIS FeatureServer and MapServer layers remain the first engine-maintenance target. The current path is:

1. Keep ArcGIS registry entries `connector-blocked` while `duckdb-arcgis` is unsigned, version-pinned, and unavailable from DuckDB community extensions.
2. Build the wrapper/macro/REST pagination path first, so Open Data Duck can count records and page with `resultOffset` / `resultRecordCount` instead of treating truncated responses as complete.
3. Add public-source smoke coverage for paginated layers.
4. Pursue upstream or community-extension packaging after the REST path is proven.
5. Fork native extension work only if the upstream/community path stalls.

Do not emit or document `INSTALL arcgis FROM community;` as a working user path until it succeeds against real DuckDB.

### ArcGIS evidence checklist

An ArcGIS source family can move from `connector-blocked` to `candidate` only after the PR shows all of this:

- a public FeatureServer or MapServer layer URL that does not require a key;
- metadata discovery for the layer's object-id field;
- a count request using `returnCountOnly=true`;
- planned query pages using `resultOffset`, `resultRecordCount`, and deterministic `orderByFields`;
- more than one planned page against a public source, so pagination is proven rather than assumed;
- normal CI that does not install or load unsigned native DuckDB extensions;
- no claim that `INSTALL arcgis FROM community;` works before real DuckDB proves it.

A registry entry can move to `verified` only after the public-source smoke test also proves the generated page requests remain valid for that source.

Run the opt-in ArcGIS smoke locally with:

```bash
ODD_ARCGIS_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_arcgis_engine.py
```

## Socrata path

Socrata portals expose every dataset through the SODA resource endpoint (`https://<domain>/resource/<four-by-four>.<csv|json|geojson>`). DuckDB can read it today with `httpfs` + `read_csv_auto` / `read_json_auto`, anonymously, without an app token. The smallest supported path is therefore **SODA export URLs with explicit paging**, not a native extension.

The risky part is truncation: SODA caps every response at `$limit` (default 1,000; max 50,000 on SODA 2.1), so a bare `read_csv_auto('.../resource/<id>.csv')` silently returns the first page of a 23M-row table. `odd/socrata.py` plans pages the same way the ArcGIS helper does: count first via `$select=count(*)`, then page with `$limit` / `$offset` under a deterministic `$order`.

### Socrata evidence checklist

A Socrata source can move from `connector-blocked` to `candidate` only after the PR shows all of this:

- a public SODA resource URL on an official portal that works without an app token;
- a count request using `$select=count(*)`;
- planned query pages using `$order`, `$limit`, and `$offset`, with `$limit` never above the SODA cap;
- more than one planned page against a public source, so pagination is proven rather than assumed;
- every recipe passes `$select` / `$where` / `$limit`; no recipe reads the bare `.csv` export of a large table;
- normal CI does not call the network.

A registry entry can move to `verified` only after the public-source smoke test also proves DuckDB `httpfs` reads a planned page and returns exactly the planned row count.

Registry entries whose dataset-level license is unresolved stay blocked regardless of engine state; see the `needs-license-review` label.

Run the opt-in Socrata smoke (NYC Open Data 311, `erm2-nwe9`) locally with:

```bash
ODD_SOCRATA_NETWORK_TESTS=1 uv run --extra dev pytest tests/test_socrata_engine.py
```
