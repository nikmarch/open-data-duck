# Registry-backed source scouting

Open Data Duck should borrow discovery from existing open-data catalogs, then add the part those catalogs usually do not provide: a DuckDB-native, validated query facade.

Open Data Duck is not an open-data catalog. It is a DuckDB-native, validated query facade for public datasets discovered from open-data catalogs.

## Why this exists

Large public catalogs already exist. They are good at discovery, metadata, and institutional publishing. They are not enough for the ODD user workflow because they usually stop before the data is queryable from DuckDB with a stable table reference.

Catalogs answer:

- Where might data exist?
- Who published it?
- What license or metadata did the publisher attach?
- Which files, APIs, or resources are linked?

ODD should answer:

- Which public table can I query from DuckDB right now?
- What is the stable `odd.<provider>.<release>.<table>` facade?
- What source SQL proves the facade returns the same data?
- What warnings, scan costs, licenses, and attribution apply?

Do not ingest millions of catalog records directly into the registry. Use external catalogs as candidate feeders, then promote only the sources that can pass the ODD validation gate.

## Source families worth scouting

| Family | Examples | Why it matters | First ODD use |
| --- | --- | --- | --- |
| Public portal directories | DataPortals.org | Finds national, state, city, and thematic portals | Seed CKAN, Socrata, ArcGIS, and custom portal scouts |
| Government catalog portals | Data.gov, data.europa.eu | Large DCAT/catalog inventories | Discover downloadable distributions and APIs |
| Cloud open-data registries | AWS Registry of Open Data, Google Cloud Public Datasets | Often includes public object storage and examples | Prioritize S3/GCS assets that DuckDB can read directly |
| Dataset collections | DataHub, Source Cooperative | Curated topical data and geospatial products | Find small sets of high-signal candidate sources |
| City/state API portals | Socrata / SODA portals | Queryable CSV/JSON/GeoJSON exports | Generate bounded SODA smoke queries |
| Catalog software APIs | CKAN APIs, DCAT feeds | Common metadata model across many portals | Extract resource-level URLs and formats |
| Spatiotemporal catalogs | STAC catalogs and APIs | Standard metadata for imagery and geospatial assets | Promote collections with DuckDB/GDAL-readable assets |
| Dataset metadata standards | DCAT, schema.org Dataset | Shared vocabulary for metadata exchange | Normalize imported metadata, not execution behavior |

## Feeder design

A feeder is allowed to discover many records, but it should emit small candidate briefs rather than directly modifying `registry/sources/`.

Each candidate brief should include:

- source family and upstream URL;
- publisher / authority;
- license URL and license-confidence notes;
- attribution text or candidate attribution;
- table/resource name and what one row means;
- resource format and access URL;
- likely DuckDB reader (`read_csv_auto`, `read_json_auto`, `read_parquet`, `ST_Read`, or future wrapper);
- bounded smoke-query idea;
- scan-size and pagination warnings;
- reason to promote, block, or discard.

### AWS Open Data feeder

Use the machine-readable registry export before scraping the rendered site.

The AWS registry entry for the registry itself lists an NDJSON export under:

```text
s3://registry.opendata.aws/roda/ndjson/
```

Prioritize entries that include one or more of:

- S3 bucket resources;
- Parquet, CSV, JSON, Cloud Optimized GeoTIFF, Zarr, or STAC hints;
- explicit license and attribution metadata;
- usage examples that imply stable paths;
- tags matching existing ODD strengths such as geospatial, climate, census, transportation, public safety, or health.

Do not promote a source only because it is on S3. The candidate still needs a bounded direct SQL recipe and clear license/attribution.

### Socrata feeder

Socrata datasets are attractive because SODA exports can be read with DuckDB `httpfs` today.

For each Socrata domain/dataset candidate:

1. read dataset metadata;
2. capture the official portal URL and SODA resource id;
3. verify anonymous access;
4. plan a count request with `$select=count(*)`;
5. plan bounded pages with deterministic `$order`, `$limit`, and `$offset`;
6. generate a small `read_csv_auto` or `read_json_auto` smoke query over an export URL;
7. record license ambiguity instead of inventing a license.

Never generate a bare full-table CSV export for large datasets. Socrata truncates default responses and large tables need explicit paging.

### CKAN / DCAT feeder

CKAN and DCAT are discovery metadata paths first. They are not DuckDB engines by themselves.

For each package or dataset:

1. inspect resource/distribution URLs;
2. filter for direct public downloads or HTTP-readable files;
3. classify file formats;
4. discard brochure-only pages, dashboards, authenticated files, and unstable UI links;
5. emit candidates only for resources that can become direct DuckDB reader SQL or have a concrete engine issue.

Keep candidates `connector-blocked` when a wrapper/table function is required but unproven.

### STAC feeder

STAC catalogs are the natural path for earth-observation and spatiotemporal assets.

For each collection candidate:

1. inspect collection metadata, license, providers, and asset roles;
2. identify assets readable by DuckDB/GDAL or existing extensions;
3. require a bounded time/spatial/sample smoke query;
4. record warnings for scan size, requester-pays/cloud-region behavior, and large raster/vector assets;
5. prefer table facades over exposing STAC internals to normal users.

## Promotion gate

A candidate can become a checked-in ODD source only after it has:

- authoritative publisher/authority metadata;
- a defensible license URL and attribution;
- table-level metadata describing what one row means;
- practical `ask_for`, `warnings`, and `columns_hint` where needed;
- a bounded `direct_sql` query that reads the source directly;
- a matching `odd_sql` query that reads the ODD facade;
- verification that the two queries compare correctly, or a clear `connector-blocked` status with a linked engine issue.

Volume is not the goal. Validated queryability is the goal.

## Suggested backlog

1. Add an AWS Open Data scout that reads the registry NDJSON and emits candidate briefs.
2. Add a Socrata scout that accepts a portal domain and emits candidate table briefs.
3. Add a CKAN scout that accepts a portal base URL and emits resource-level candidate briefs.
4. Add a DCAT feed scout for data.gov/data.europa-style catalogs.
5. Add a STAC collection scout for geospatial catalogs.
6. Add a candidate scoring model with fields for license confidence, authority confidence, DuckDB reader, bounded smoke query, table usefulness, scan cost, and connector blockers.
7. Add a review command that turns an accepted candidate brief into a draft `registry/sources/<id>.yml` entry plus validation SQL.

## Non-goals

- Do not mirror upstream datasets.
- Do not claim to be the global registry of all open data.
- Do not import millions of metadata records into the runtime registry.
- Do not mark a source queryable just because an authoritative endpoint exists.
- Do not invent DuckDB table functions for CKAN, DCAT, Socrata, ArcGIS, or STAC before a real implementation exists.
