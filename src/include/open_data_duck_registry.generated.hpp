// GENERATED FILE. DO NOT EDIT.
// Source of truth: registry/sources.yml
// Regenerate with: uv run odd generate-extension-registry
// Drift check:     uv run odd generate-extension-registry --check
#pragma once

namespace duckdb {
namespace open_data_duck {

static constexpr int REGISTRY_SCHEMA_VERSION = 1;
static constexpr int REGISTRY_SOURCE_COUNT = 20;

static const char *const REGISTRY_JSON = R"odd_registry(
{
  "schema_version": 1,
  "source_count": 20,
  "sources": [
    {
      "attribution": "Overture Maps Foundation and contributing data providers.",
      "authority": "Overture Maps Foundation",
      "description": "Global open map data releases for places, buildings, transportation, addresses, divisions, and base layers queryable from public S3 with DuckDB httpfs.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\n-- Direct public S3 recipe. The future open_data_duck extension should wrap\n-- this release/path logic instead of relying on a separate Overture plugin.\nSELECT *\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=places/type=place/*',\n  hive_partitioning = true\n)\nWHERE bbox.xmin <= -149\n  AND bbox.xmax >= -150\n  AND bbox.ymin <= 61\n  AND bbox.ymax >= 60\nLIMIT 10;",
        "examples": {
          "addresses_bbox_direct_s3": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\nSELECT *\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=addresses/type=address/*',\n  hive_partitioning = true\n)\nWHERE bbox.xmin <= -149\n  AND bbox.xmax >= -150\n  AND bbox.ymin <= 61\n  AND bbox.ymax >= 60\nLIMIT 10;",
          "buildings_bbox_direct_s3": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\nSELECT *\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=buildings/type=building/*',\n  hive_partitioning = true\n)\nWHERE bbox.xmin <= -149\n  AND bbox.xmax >= -150\n  AND bbox.ymin <= 61\n  AND bbox.ymax >= 60\nLIMIT 10;",
          "places_bbox_direct_s3": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\nSELECT *\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=places/type=place/*',\n  hive_partitioning = true\n)\nWHERE bbox.xmin <= -149\n  AND bbox.xmax >= -150\n  AND bbox.ymin <= 61\n  AND bbox.ymax >= 60\nLIMIT 10;",
          "road_segments_bbox_direct_s3": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\nSELECT *\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=transportation/type=segment/*',\n  hive_partitioning = true\n)\nWHERE bbox.xmin <= -149\n  AND bbox.xmax >= -150\n  AND bbox.ymin <= 61\n  AND bbox.ymax >= 60\nLIMIT 10;"
        },
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {
          "discover_sql": "SELECT collection AS name,\n       'read_parquet' AS reader,\n       regexp_replace(regexp_replace(min(assets.aws.href), '^https://([^.]+)\\.s3\\.[^/]+/', 's3://\\1/'), '/part-[^/]+$', '/*') AS path\nFROM read_parquet('https://stac.overturemaps.org/{release}/collections.parquet')\nGROUP BY collection;",
          "namespace": "odd.overturemaps.latest"
        },
        "validation_query": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\nSELECT count(*) >= 0 AS small_bbox_query_ok\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=places/type=place/*',\n  hive_partitioning = true\n)\nWHERE bbox.xmin <= -149\n  AND bbox.xmax >= -150\n  AND bbox.ymin <= 61\n  AND bbox.ymax >= 60\nLIMIT 1;"
      },
      "homepage": "https://docs.overturemaps.org/getting-data/",
      "id": "overture.maps.release",
      "license_url": "https://docs.overturemaps.org/attribution/",
      "name": "Overture Maps source family",
      "release": {
        "latest": {
          "method": "stac-catalog",
          "resolve_sql": "SELECT regexp_extract(l.href, '/([0-9]{4}-[0-9]{2}-[0-9]{2}\\.[0-9]+)/catalog\\.json$', 1) AS release\nFROM (SELECT unnest(links) AS l FROM read_json('https://stac.overturemaps.org/catalog.json'))\nWHERE l.rel = 'child' AND l.latest;\n",
          "url": "https://stac.overturemaps.org/catalog.json"
        },
        "pinned": {
          "duckdb_setting": "overture_release",
          "example": "2026-10-21.0",
          "s3_base_setting": "overture_s3_base"
        }
      },
      "source_type": "overture",
      "status": "candidate",
      "tags": [
        "maps",
        "geospatial",
        "places",
        "buildings",
        "transportation",
        "addresses"
      ],
      "validations": [
        {
          "compare": "exact",
          "description": "Compare the latest Overture places facade with the direct public S3 parquet recipe over a sampled tiny bbox.",
          "direct_sql": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\nSELECT id, names, bbox\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=places/type=place/*'\n)\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
          "id": "odd.overturemaps.latest.place",
          "limit": 10,
          "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\nSELECT id, names, bbox\nFROM odd.overturemaps.latest.place\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
          "order_by": [
            "id"
          ],
          "release": "latest"
        },
        {
          "compare": "exact",
          "description": "Compare a pinned, SQL-safe Overture release facade with the same direct release path over a sampled tiny bbox.",
          "direct_sql": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\nSELECT id, names, bbox\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/2026-10-21.0/theme=places/type=place/*'\n)\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
          "id": "odd.overturemaps.x2026x10x21.place",
          "limit": 10,
          "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSELECT id, names, bbox\nFROM odd.overturemaps.x2026x10x21.place\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
          "order_by": [
            "id"
          ],
          "release": "x2026x10x21",
          "source_release": "2026-10-21.0"
        }
      ]
    },
    {
      "attribution": "Dataset-specific attribution required; verify per collection.",
      "authority": "Element 84 / AWS Open Data ecosystem",
      "description": "Element 84 STAC API for cloud-optimized geospatial imagery, especially Sentinel collections hosted in the AWS open data ecosystem.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nLOAD spatial;\nLOAD stac;\nSELECT collection, id, bbox\nFROM STAC_Search('https://earth-search.aws.element84.com/v1/search', max_items := 10)\nLIMIT 10;",
        "examples": {},
        "extensions": [
          "httpfs",
          "spatial",
          "stac"
        ],
        "install": "INSTALL httpfs;\nINSTALL spatial;\nINSTALL stac FROM community;",
        "tables": {},
        "validation_query": "SELECT count(*) > 0 AS ok\nFROM STAC_Collections('https://earth-search.aws.element84.com/v1');"
      },
      "homepage": "https://earth-search.aws.element84.com/v1",
      "id": "stac.earth-search.aws",
      "license_url": "https://registry.opendata.aws/sentinel-2-l2a-cogs/",
      "name": "Earth Search STAC API",
      "release": {},
      "source_type": "stac",
      "status": "candidate",
      "tags": [
        "stac",
        "imagery",
        "aws",
        "sentinel"
      ],
      "validations": []
    },
    {
      "attribution": "Dataset-specific attribution required; verify per Planetary Computer collection.",
      "authority": "Microsoft Planetary Computer",
      "description": "Microsoft Planetary Computer STAC catalog for environmental, climate, and satellite datasets exposed through a STAC API.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nLOAD spatial;\nLOAD stac;\nSELECT collection, id, bbox\nFROM STAC_Search('https://planetarycomputer.microsoft.com/api/stac/v1/search', max_items := 10)\nLIMIT 10;",
        "examples": {},
        "extensions": [
          "httpfs",
          "spatial",
          "stac"
        ],
        "install": "INSTALL httpfs;\nINSTALL spatial;\nINSTALL stac FROM community;",
        "tables": {},
        "validation_query": "SELECT count(*) > 0 AS ok\nFROM STAC_Collections('https://planetarycomputer.microsoft.com/api/stac/v1');"
      },
      "homepage": "https://planetarycomputer.microsoft.com/catalog",
      "id": "stac.microsoft.planetary-computer",
      "license_url": "https://planetarycomputer.microsoft.com/terms",
      "name": "Microsoft Planetary Computer STAC API",
      "release": {},
      "source_type": "stac",
      "status": "candidate",
      "tags": [
        "stac",
        "imagery",
        "climate",
        "microsoft"
      ],
      "validations": []
    },
    {
      "attribution": "NASA LP DAAC data; cite dataset-specific DOI and attribution.",
      "authority": "NASA Land Processes Distributed Active Archive Center",
      "description": "NASA LP DAAC STAC catalog for land processes data products served through Earthdata/CMR endpoints.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nLOAD spatial;\nLOAD stac;\nSELECT collection, id, bbox\nFROM STAC_Search('https://cmr.earthdata.nasa.gov/stac/LPCLOUD/search', max_items := 10)\nLIMIT 10;",
        "examples": {},
        "extensions": [
          "httpfs",
          "spatial",
          "stac"
        ],
        "install": "INSTALL httpfs;\nINSTALL spatial;\nINSTALL stac FROM community;",
        "tables": {},
        "validation_query": "SELECT count(*) > 0 AS ok\nFROM STAC_Collections('https://cmr.earthdata.nasa.gov/stac/LPCLOUD/');"
      },
      "homepage": "https://cmr.earthdata.nasa.gov/stac/LPCLOUD/",
      "id": "stac.nasa.lpcloud",
      "license_url": "https://www.earthdata.nasa.gov/engage/open-data-services-and-software/data-and-information-policy",
      "name": "NASA LP DAAC LPCLOUD STAC catalog",
      "release": {},
      "source_type": "stac",
      "status": "candidate",
      "tags": [
        "stac",
        "nasa",
        "land",
        "earthdata"
      ],
      "validations": []
    },
    {
      "attribution": "U.S. Census Bureau TIGERweb.",
      "authority": "U.S. Census Bureau",
      "description": "Census TIGERweb ArcGIS layers for U.S. state and county boundaries, useful once ArcGIS paging is available in the DuckDB path.",
      "duckdb": {
        "example_query": "-- Future duckdb-arcgis shape once the connector has a stable install path.\nLOAD arcgis;\nSELECT *\nFROM arcgis_query('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1')\nLIMIT 10;",
        "examples": {},
        "extensions": [
          "arcgis"
        ],
        "install": "-- connector-blocked: duckdb-arcgis is not in DuckDB community extensions.\n-- Current releases install from unsigned exact-version binaries.\n-- Open DuckDB with allow_unsigned_extensions before installing a release file.",
        "tables": {},
        "validation_query": "SELECT count(*) > 0 AS ok\nFROM arcgis_query('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1');"
      },
      "homepage": "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer",
      "id": "arcgis.census.tigerweb.state-county",
      "license_url": "https://www.census.gov/data/developers/about/terms-of-service.html",
      "name": "U.S. Census TIGERweb state and county layers",
      "release": {},
      "source_type": "arcgis",
      "status": "connector-blocked",
      "tags": [
        "arcgis",
        "census",
        "boundaries",
        "us"
      ],
      "validations": []
    },
    {
      "attribution": "U.S. Census Bureau Geography Program, Cartographic Boundary Files; cite the selected year and scale and do not imply Census Bureau endorsement.",
      "authority": "U.S. Census Bureau Geography Program",
      "description": "Official generalized U.S. county boundary shapefiles from the Census Bureau Cartographic Boundary Files collection, queryable directly from the public zipped shapefile with DuckDB spatial/GDAL virtual file paths.",
      "duckdb": {
        "example_query": "LOAD spatial;\n\nSELECT GEOID, NAME, STATE_NAME, ST_GeometryType(geom) AS geom_type\nFROM ST_Read('/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_20m.zip/cb_2025_us_county_20m.shp')\nLIMIT 10;",
        "examples": {
          "alaska_counties_2025_20m": "LOAD spatial;\n\nSELECT GEOID, NAME, LSAD, ST_AsText(ST_Centroid(geom)) AS centroid_wkt\nFROM ST_Read('/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_20m.zip/cb_2025_us_county_20m.shp')\nWHERE STATEFP = '02'\nORDER BY GEOID;"
        },
        "extensions": [
          "spatial"
        ],
        "install": "INSTALL spatial;",
        "tables": {
          "discover_sql": "SELECT regexp_extract(z, 'cb_{release}_us_(.+)\\.zip', 1) AS name,\n       'st_read' AS reader,\n       '/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ{release}/shp/' || z || '/' || replace(z, '.zip', '.shp') AS path\nFROM (SELECT DISTINCT unnest(regexp_extract_all(content, 'cb_{release}_us_county[a-z0-9_]*\\.zip')) AS z\n      FROM read_text('https://www2.census.gov/geo/tiger/GENZ{release}/shp/'));",
          "namespace": "odd.census.latest"
        },
        "validation_query": "LOAD spatial;\n\nSELECT count(*) = 3222 AS ok\nFROM ST_Read('/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_20m.zip/cb_2025_us_county_20m.shp');"
      },
      "homepage": "https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html",
      "id": "census.cartographic.county-boundaries",
      "license_url": "https://www.census.gov/data/developers/about/terms-of-service.html",
      "name": "U.S. Census cartographic county boundary files",
      "release": {
        "latest": {
          "method": "html-listing",
          "resolve_sql": "SELECT max(regexp_extract(m, 'GENZ([0-9]{4})', 1)) AS release\nFROM (SELECT unnest(regexp_extract_all(content, 'GENZ[0-9]{4}')) AS m\n      FROM read_text('https://www2.census.gov/geo/tiger/'));\n",
          "url": "https://www2.census.gov/geo/tiger/"
        },
        "pinned": {
          "duckdb_setting": "census_cartographic_year",
          "example": "2025"
        }
      },
      "source_type": "other",
      "status": "candidate",
      "tags": [
        "census",
        "boundaries",
        "counties",
        "shapefile",
        "geospatial"
      ],
      "validations": []
    },
    {
      "attribution": "U.S. Census Bureau Geography Program, Cartographic Boundary Files; cite the selected year and scale and do not imply Census Bureau endorsement.",
      "authority": "U.S. Census Bureau Geography Program",
      "description": "Official generalized U.S. census tract boundary shapefiles from the Census Bureau Cartographic Boundary Files collection, queryable directly from the public zipped shapefile with DuckDB spatial/GDAL virtual file paths.",
      "duckdb": {
        "example_query": "LOAD spatial;\n\nSELECT GEOID, NAME, STATEFP, COUNTYFP, ST_GeometryType(geom) AS geom_type\nFROM ST_Read('/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_tract_5m.zip/cb_2025_us_tract_5m.shp')\nWHERE STATEFP = '02'\nLIMIT 10;",
        "examples": {
          "alaska_tracts_2025_5m": "LOAD spatial;\n\nSELECT GEOID, NAME, COUNTYFP, ST_AsText(ST_Centroid(geom)) AS centroid_wkt\nFROM ST_Read('/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_tract_5m.zip/cb_2025_us_tract_5m.shp')\nWHERE STATEFP = '02'\nORDER BY GEOID\nLIMIT 25;"
        },
        "extensions": [
          "spatial"
        ],
        "install": "INSTALL spatial;",
        "tables": {
          "discover_sql": "SELECT regexp_extract(z, 'cb_{release}_us_(.+)\\.zip', 1) AS name,\n       'st_read' AS reader,\n       '/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ{release}/shp/' || z || '/' || replace(z, '.zip', '.shp') AS path\nFROM (SELECT DISTINCT unnest(regexp_extract_all(content, 'cb_{release}_us_tract[a-z0-9_]*\\.zip')) AS z\n      FROM read_text('https://www2.census.gov/geo/tiger/GENZ{release}/shp/'));",
          "namespace": "odd.census.latest"
        },
        "validation_query": "LOAD spatial;\n\nSELECT count(*) = 85187 AS ok\nFROM ST_Read('/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_tract_5m.zip/cb_2025_us_tract_5m.shp');"
      },
      "homepage": "https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html",
      "id": "census.cartographic.tract-boundaries",
      "license_url": "https://www.census.gov/data/developers/about/terms-of-service.html",
      "name": "U.S. Census cartographic tract boundary files",
      "release": {
        "latest": {
          "method": "html-listing",
          "resolve_sql": "SELECT max(regexp_extract(m, 'GENZ([0-9]{4})', 1)) AS release\nFROM (SELECT unnest(regexp_extract_all(content, 'GENZ[0-9]{4}')) AS m\n      FROM read_text('https://www2.census.gov/geo/tiger/'));\n",
          "url": "https://www2.census.gov/geo/tiger/"
        },
        "pinned": {
          "duckdb_setting": "census_cartographic_year",
          "example": "2025"
        }
      },
      "source_type": "other",
      "status": "candidate",
      "tags": [
        "census",
        "boundaries",
        "tracts",
        "shapefile",
        "geospatial"
      ],
      "validations": []
    },
    {
      "attribution": "Federal Emergency Management Agency National Flood Hazard Layer.",
      "authority": "Federal Emergency Management Agency",
      "description": "FEMA NFHL ArcGIS layer for flood hazard zones, intended for risk and property-context queries after ArcGIS paging support is stable.",
      "duckdb": {
        "example_query": "-- Future duckdb-arcgis shape once the connector has a stable install path.\nLOAD arcgis;\nSELECT *\nFROM arcgis_query('https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28')\nLIMIT 10;",
        "examples": {},
        "extensions": [
          "arcgis"
        ],
        "install": "-- connector-blocked: duckdb-arcgis is not in DuckDB community extensions.\n-- Current releases install from unsigned exact-version binaries.\n-- Open DuckDB with allow_unsigned_extensions before installing a release file.",
        "tables": {},
        "validation_query": "SELECT count(*) > 0 AS ok\nFROM arcgis_query('https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28');"
      },
      "homepage": "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer",
      "id": "arcgis.fema.nfhl.flood-hazard-zones",
      "license_url": "https://www.fema.gov/about/openfema/terms-conditions",
      "name": "FEMA National Flood Hazard Layer flood hazard zones",
      "release": {},
      "source_type": "arcgis",
      "status": "connector-blocked",
      "tags": [
        "arcgis",
        "fema",
        "flood",
        "hazards"
      ],
      "validations": []
    },
    {
      "attribution": "U.S. Geological Survey National Map.",
      "authority": "U.S. Geological Survey",
      "description": "USGS National Map ArcGIS contour layer for elevation-line features and terrain context, pending stable ArcGIS support.",
      "duckdb": {
        "example_query": "-- Future duckdb-arcgis shape once the connector has a stable install path.\nLOAD arcgis;\nSELECT *\nFROM arcgis_query('https://carto.nationalmap.gov/arcgis/rest/services/contours/MapServer/2')\nLIMIT 10;",
        "examples": {},
        "extensions": [
          "arcgis"
        ],
        "install": "-- connector-blocked: duckdb-arcgis is not in DuckDB community extensions.\n-- Current releases install from unsigned exact-version binaries.\n-- Open DuckDB with allow_unsigned_extensions before installing a release file.",
        "tables": {},
        "validation_query": "SELECT count(*) > 0 AS ok\nFROM arcgis_query('https://carto.nationalmap.gov/arcgis/rest/services/contours/MapServer/2');"
      },
      "homepage": "https://carto.nationalmap.gov/arcgis/rest/services/contours/MapServer",
      "id": "arcgis.usgs.national-map-contours",
      "license_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
      "name": "USGS National Map elevation contours",
      "release": {},
      "source_type": "arcgis",
      "status": "connector-blocked",
      "tags": [
        "arcgis",
        "usgs",
        "elevation",
        "contours"
      ],
      "validations": []
    },
    {
      "attribution": "U.S. Geological Survey Earthquake Hazards Program; credit USGS earthquake feeds and do not imply USGS endorsement.",
      "authority": "U.S. Geological Survey Earthquake Hazards Program",
      "description": "Official U.S. Geological Survey realtime earthquake summary feeds for recent seismic events, queryable directly from GeoJSON over HTTPS with DuckDB read_json_auto.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nSELECT id AS event_id,\n       mag AS magnitude,\n       place,\n       time AS event_time_ms,\n       geometry\nFROM read_json_auto(\n  'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson',\n  maximum_object_size = 16777216\n)\nWHERE type = 'earthquake'\nORDER BY time DESC\nLIMIT 10;",
        "examples": {
          "magnitude_4_5_week": "LOAD httpfs;\nSELECT id AS event_id, mag, place, time, updated, geometry\nFROM read_json_auto(\n  'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson',\n  maximum_object_size = 16777216\n)\nORDER BY time DESC\nLIMIT 25;",
          "significant_month": "LOAD httpfs;\nSELECT id AS event_id, mag, place, alert, tsunami, sig, url\nFROM read_json_auto(\n  'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson',\n  maximum_object_size = 16777216\n)\nORDER BY sig DESC\nLIMIT 25;"
        },
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {},
        "validation_query": "LOAD httpfs;\nSELECT count(*) > 0 AS ok\nFROM read_json_auto(\n  'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson',\n  maximum_object_size = 16777216\n)\nWHERE type = 'earthquake'\n  AND id IS NOT NULL\n  AND mag IS NOT NULL;"
      },
      "homepage": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php",
      "id": "usgs.earthquake.realtime-geojson",
      "license_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
      "name": "USGS realtime earthquake GeoJSON feeds",
      "release": {},
      "source_type": "other",
      "status": "candidate",
      "tags": [
        "usgs",
        "earthquakes",
        "hazards",
        "geojson",
        "realtime"
      ],
      "validations": []
    },
    {
      "attribution": "World Bank Group, World Development Indicators; attribute as: The World Bank: World Development Indicators: World Bank Group. Do not imply World Bank endorsement.",
      "authority": "World Bank Group",
      "description": "Official World Bank Indicators API access to World Development Indicators time-series development data, queryable as public JSON over HTTPS with DuckDB httpfs and JSON functions.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nWITH payload AS (\n  SELECT json\n  FROM read_json(\n    'https://api.worldbank.org/v2/country/USA/indicator/SP.POP.TOTL?format=json&per_page=20000',\n    format = 'auto'\n  )\n  WHERE json_type(json) = 'ARRAY'\n), rows AS (\n  SELECT e.value AS item\n  FROM payload, json_each(payload.json) AS e\n)\nSELECT item->'country'->>'id' AS country_id,\n       item->>'countryiso3code' AS iso3,\n       item->'indicator'->>'id' AS indicator_id,\n       CAST(item->>'date' AS INTEGER) AS year,\n       CAST(item->>'value' AS DOUBLE) AS value\nFROM rows\nWHERE item->>'value' IS NOT NULL\nORDER BY year DESC\nLIMIT 10;",
        "examples": {
          "usa_gdp_current_usd": "LOAD httpfs;\nWITH payload AS (\n  SELECT json\n  FROM read_json(\n    'https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json&per_page=20000',\n    format = 'auto'\n  )\n  WHERE json_type(json) = 'ARRAY'\n), rows AS (\n  SELECT e.value AS item\n  FROM payload, json_each(payload.json) AS e\n)\nSELECT CAST(item->>'date' AS INTEGER) AS year,\n       CAST(item->>'value' AS DOUBLE) AS gdp_current_usd\nFROM rows\nWHERE item->>'value' IS NOT NULL\nORDER BY year DESC\nLIMIT 25;"
        },
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {},
        "validation_query": "LOAD httpfs;\nWITH payload AS (\n  SELECT json\n  FROM read_json(\n    'https://api.worldbank.org/v2/country/USA/indicator/SP.POP.TOTL?format=json&per_page=20000',\n    format = 'auto'\n  )\n  WHERE json_type(json) = 'ARRAY'\n), rows AS (\n  SELECT e.value AS item\n  FROM payload, json_each(payload.json) AS e\n)\nSELECT count(*) > 0 AS has_rows,\n       max(CAST(item->>'date' AS INTEGER)) >= 2020 AS has_recent_data\nFROM rows\nWHERE item->>'value' IS NOT NULL;"
      },
      "homepage": "https://api.worldbank.org/v2/",
      "id": "worldbank.wdi.indicators",
      "license_url": "https://www.worldbank.org/ext/en/legal/terms-conditions/datasets",
      "name": "World Bank World Development Indicators API",
      "release": {},
      "source_type": "other",
      "status": "candidate",
      "tags": [
        "world-bank",
        "wdi",
        "indicators",
        "development",
        "json"
      ],
      "validations": []
    },
    {
      "attribution": "Cite BLS.gov and the API retrieval date; state that BLS.gov cannot vouch for data or analyses derived after retrieval; do not use the BLS logo or imply BLS sponsorship.",
      "authority": "U.S. Bureau of Labor Statistics",
      "description": "Official U.S. Bureau of Labor Statistics Public Data API access to Consumer Price Index time-series observations, queryable as public JSON over HTTPS with DuckDB httpfs.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nWITH series AS (\n  SELECT unnest(Results.series) AS s\n  FROM read_json(\n    'https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0?startyear=2024&endyear=2025',\n    format = 'auto'\n  )\n), observations AS (\n  SELECT s.seriesID AS series_id,\n         unnest(s.data) AS obs\n  FROM series\n)\nSELECT series_id,\n       CAST(obs.year AS INTEGER) AS year,\n       obs.period AS period,\n       obs.periodName AS period_name,\n       TRY_CAST(obs.value AS DOUBLE) AS value\nFROM observations\nWHERE TRY_CAST(obs.value AS DOUBLE) IS NOT NULL\nORDER BY year DESC, period DESC\nLIMIT 10;",
        "examples": {
          "core_cpi_recent_observations": "LOAD httpfs;\nWITH series AS (\n  SELECT unnest(Results.series) AS s\n  FROM read_json(\n    'https://api.bls.gov/publicAPI/v1/timeseries/data/CUSR0000SA0L1E?startyear=2024&endyear=2025',\n    format = 'auto'\n  )\n), observations AS (\n  SELECT s.seriesID AS series_id,\n         unnest(s.data) AS obs\n  FROM series\n)\nSELECT series_id,\n       CAST(obs.year AS INTEGER) AS year,\n       obs.periodName AS period_name,\n       TRY_CAST(obs.value AS DOUBLE) AS core_cpi\nFROM observations\nWHERE TRY_CAST(obs.value AS DOUBLE) IS NOT NULL\nORDER BY year DESC, obs.period DESC\nLIMIT 12;"
        },
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {},
        "validation_query": "LOAD httpfs;\nWITH series AS (\n  SELECT unnest(Results.series) AS s\n  FROM read_json(\n    'https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0?startyear=2024&endyear=2025',\n    format = 'auto'\n  )\n), observations AS (\n  SELECT s.seriesID AS series_id,\n         unnest(s.data) AS obs\n  FROM series\n)\nSELECT count(*) > 0 AS has_rows,\n       bool_or(series_id = 'CUUR0000SA0') AS has_cpi_all_items_series,\n       max(CAST(obs.year AS INTEGER)) >= 2024 AS has_recent_data\nFROM observations\nWHERE TRY_CAST(obs.value AS DOUBLE) IS NOT NULL;"
      },
      "homepage": "https://www.bls.gov/developers/home.htm",
      "id": "bls.cpi.timeseries",
      "license_url": "https://www.bls.gov/developers/termsOfService.htm",
      "name": "BLS Consumer Price Index time series API",
      "release": {},
      "source_type": "other",
      "status": "candidate",
      "tags": [
        "bls",
        "cpi",
        "inflation",
        "labor-statistics",
        "json"
      ],
      "validations": []
    },
    {
      "attribution": "NOAA National Centers for Environmental Information, Storm Events Database; credit NOAA/NCEI and do not imply NOAA endorsement.",
      "authority": "NOAA National Centers for Environmental Information",
      "description": "Official NOAA National Centers for Environmental Information Storm Events Database bulk CSV exports for severe weather events, fatalities, and locations, queryable from public HTTPS gzip files with DuckDB httpfs.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nSELECT event_id,\n       state,\n       event_type,\n       begin_date_time,\n       cz_name\nFROM read_csv_auto(\n  'https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_details-ftp_v1.0_d2024_c20261118.csv.gz',\n  sample_size = 20000\n)\nWHERE event_type IS NOT NULL\nORDER BY event_id\nLIMIT 10;",
        "examples": {
          "latest_details_by_state_type": "LOAD httpfs;\nSET VARIABLE noaa_storm_events_year = '2024';\nSELECT event_id, state, event_type, begin_date_time, cz_name\nFROM odd.noaa.latest.storm_events_details\nWHERE state = 'ALASKA'\n  AND event_type IS NOT NULL\nORDER BY begin_date_time\nLIMIT 25;",
          "latest_fatalities_by_year": "LOAD httpfs;\nSET VARIABLE noaa_storm_events_year = '2024';\nSELECT fatality_id, event_id, fatality_type, fatality_date, fatality_age\nFROM odd.noaa.latest.storm_events_fatalities\nORDER BY fatality_date\nLIMIT 25;"
        },
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {
          "discover_sql": "WITH files AS (\n  SELECT regexp_extract(m, 'StormEvents_([a-z]+)-ftp_v1\\.0_d{release}_c([0-9]{8})\\.csv\\.gz', 1) AS table_kind,\n         regexp_extract(m, '(StormEvents_[a-z]+-ftp_v1\\.0_d{release}_c[0-9]{8}\\.csv\\.gz)', 1) AS file_name,\n         regexp_extract(m, '_c([0-9]{8})\\.csv\\.gz', 1) AS created\n  FROM (SELECT DISTINCT unnest(regexp_extract_all(content, 'StormEvents_[a-z]+-ftp_v1\\.0_d{release}_c[0-9]{8}\\.csv\\.gz')) AS m\n        FROM read_text('https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/'))\n), latest AS (\n  SELECT table_kind, max(created) AS created\n  FROM files\n  GROUP BY table_kind\n)\nSELECT 'storm_events_' || files.table_kind AS name,\n       'read_csv' AS reader,\n       'https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/' || files.file_name AS path\nFROM files\nJOIN latest USING (table_kind, created)\nORDER BY name;",
          "namespace": "odd.noaa.latest"
        },
        "validation_query": "LOAD httpfs;\nSELECT count(*) > 0 AS ok\nFROM read_csv_auto(\n  'https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_details-ftp_v1.0_d2024_c20261118.csv.gz',\n  sample_size = 20000\n)\nWHERE event_id IS NOT NULL\n  AND event_type IS NOT NULL;"
      },
      "homepage": "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/",
      "id": "noaa.ncei.storm-events",
      "license_url": "https://www.noaa.gov/information-policies-and-instructions/copyrights-and-credits",
      "name": "NOAA NCEI Storm Events bulk CSV files",
      "release": {
        "latest": {
          "method": "html-listing",
          "resolve_sql": "SELECT max(regexp_extract(m, 'StormEvents_details-ftp_v1\\.0_d([0-9]{4})_c[0-9]{8}\\.csv\\.gz', 1)) AS release\nFROM (SELECT unnest(regexp_extract_all(content, 'StormEvents_details-ftp_v1\\.0_d[0-9]{4}_c[0-9]{8}\\.csv\\.gz')) AS m\n      FROM read_text('https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/'));\n",
          "url": "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
        },
        "pinned": {
          "duckdb_setting": "noaa_storm_events_year",
          "example": "2024"
        }
      },
      "source_type": "other",
      "status": "candidate",
      "tags": [
        "noaa",
        "ncei",
        "storms",
        "weather",
        "hazards",
        "csv"
      ],
      "validations": [
        {
          "compare": "exact",
          "description": "Compare NOAA Storm Events details facade with the direct bulk CSV recipe.",
          "direct_sql": "LOAD httpfs;\nSELECT event_id, state, event_type, begin_date_time, cz_name\nFROM read_csv_auto(\n  'https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_details-ftp_v1.0_d2024_c20261118.csv.gz',\n  sample_size = 20000\n)\nWHERE event_type IS NOT NULL\nORDER BY event_id\nLIMIT 10;\n",
          "id": "odd.noaa.latest.storm_events_details",
          "limit": 10,
          "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE noaa_storm_events_year = '2024';\nSELECT event_id, state, event_type, begin_date_time, cz_name\nFROM odd.noaa.latest.storm_events_details\nWHERE event_type IS NOT NULL\nORDER BY event_id\nLIMIT 10;\n",
          "order_by": [
            "event_id"
          ],
          "release": "latest"
        }
      ]
    },
    {
      "attribution": "NOAA National Centers for Environmental Information, Global Historical Climatology Network Daily.",
      "authority": "NOAA National Centers for Environmental Information",
      "description": "NOAA GHCN Daily station observations in public S3 CSV files for temperature, precipitation, and other daily climate measurements.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nSELECT id, date, element, data_value\nFROM read_csv_auto('https://noaa-ghcn-pds.s3.amazonaws.com/csv/by_year/2024.csv')\nLIMIT 10;",
        "examples": {},
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {
          "discover_sql": "SELECT 'ghcn_daily' AS name,\n       'read_csv' AS reader,\n       'https://noaa-ghcn-pds.s3.amazonaws.com/csv/by_year/{release}.csv' AS path;",
          "namespace": "odd.noaa.latest"
        },
        "validation_query": "SELECT count(*) > 0 AS ok\nFROM read_csv_auto('https://noaa-ghcn-pds.s3.amazonaws.com/csv/by_year/2024.csv')\nLIMIT 1;"
      },
      "homepage": "https://registry.opendata.aws/noaa-ghcn/",
      "id": "aws.noaa-ghcn-daily",
      "license_url": "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily",
      "name": "NOAA Global Historical Climatology Network Daily",
      "release": {
        "latest": {
          "method": "s3-listing",
          "resolve_sql": "SELECT max(regexp_extract(m, '([0-9]{4})\\.csv', 1)) AS release\nFROM (SELECT unnest(regexp_extract_all(content, 'by_year/[0-9]{4}\\.csv')) AS m\n      FROM read_text('https://noaa-ghcn-pds.s3.amazonaws.com/?list-type=2&prefix=csv/by_year/'));\n",
          "url": "https://noaa-ghcn-pds.s3.amazonaws.com/?list-type=2&prefix=csv/by_year/"
        },
        "pinned": {
          "duckdb_setting": "noaa_ghcn_year",
          "example": "2024"
        }
      },
      "source_type": "other",
      "status": "candidate",
      "tags": [
        "aws",
        "noaa",
        "climate",
        "weather",
        "csv"
      ],
      "validations": []
    },
    {
      "attribution": "NOAA National Centers for Environmental Information, Global Surface Summary of the Day.",
      "authority": "NOAA National Centers for Environmental Information",
      "description": "NOAA GSOD daily weather summaries by station, exposed as public S3 CSV objects queryable with DuckDB httpfs.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nSELECT station, date, latitude, longitude, temp\nFROM read_csv_auto('https://noaa-gsod-pds.s3.amazonaws.com/2024/01001099999.csv')\nLIMIT 10;",
        "examples": {},
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {},
        "validation_query": "SELECT count(*) > 0 AS ok\nFROM read_csv_auto('https://noaa-gsod-pds.s3.amazonaws.com/2024/01001099999.csv');"
      },
      "homepage": "https://registry.opendata.aws/noaa-gsod/",
      "id": "aws.noaa-gsod",
      "license_url": "https://www.ncei.noaa.gov/products/land-based-weather-stations",
      "name": "NOAA Global Surface Summary of the Day",
      "release": {},
      "source_type": "other",
      "status": "candidate",
      "tags": [
        "aws",
        "noaa",
        "weather",
        "daily",
        "csv"
      ],
      "validations": []
    },
    {
      "attribution": "NOAA National Centers for Environmental Information, Integrated Surface Database.",
      "authority": "NOAA National Centers for Environmental Information",
      "description": "NOAA ISD station-history lookup table with station identifiers, names, country/state, and coordinates.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nSELECT \"USAF\", \"WBAN\", \"STATION NAME\", \"CTRY\", \"STATE\", \"LAT\", \"LON\"\nFROM read_csv_auto('https://noaa-isd-pds.s3.amazonaws.com/isd-history.csv')\nLIMIT 10;",
        "examples": {},
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {},
        "validation_query": "SELECT count(*) > 0 AS ok\nFROM read_csv_auto('https://noaa-isd-pds.s3.amazonaws.com/isd-history.csv');"
      },
      "homepage": "https://registry.opendata.aws/noaa-isd/",
      "id": "aws.noaa-isd-history",
      "license_url": "https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database",
      "name": "NOAA Integrated Surface Database station history",
      "release": {},
      "source_type": "other",
      "status": "candidate",
      "tags": [
        "aws",
        "noaa",
        "stations",
        "lookup",
        "csv"
      ],
      "validations": []
    },
    {
      "attribution": "Wyndham City Council; licensed under Creative Commons Attribution 3.0 Australia.",
      "authority": "Wyndham City Council via data.gov.au",
      "description": "Australian Government CKAN catalog package with a public CSV distribution of Wyndham registered dog and cat counts by suburb.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nSELECT *\nFROM read_csv_auto('https://data.gov.au/data/dataset/ff0b0b45-e772-4835-9525-a6d7e20ea93d/resource/eef6a84b-ad44-446f-9cf9-fb5d135e3123/download/wyndhamcatdogslist.csv')\nLIMIT 10;",
        "examples": {},
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {},
        "validation_query": "LOAD httpfs;\nSELECT count(*) > 0 AS ok\nFROM read_csv_auto('https://data.gov.au/data/dataset/ff0b0b45-e772-4835-9525-a6d7e20ea93d/resource/eef6a84b-ad44-446f-9cf9-fb5d135e3123/download/wyndhamcatdogslist.csv');"
      },
      "homepage": "https://data.gov.au/data/dataset/wyndham-registered-dogs-catscsv",
      "id": "ckan.data-gov-au.wyndham-pets",
      "license_url": "https://creativecommons.org/licenses/by/3.0/au/",
      "name": "Data.gov.au Wyndham registered dogs and cats",
      "release": {},
      "source_type": "ckan",
      "status": "candidate",
      "tags": [
        "ckan",
        "dcat",
        "australia",
        "csv",
        "animals"
      ],
      "validations": []
    },
    {
      "attribution": "NYC Open Data, 311 Service Requests from 2020 to Present, City of New York Office of Technology and Innovation.",
      "authority": "City of New York Office of Technology and Innovation via NYC Open Data",
      "description": "New York City 311 service-request records from 2020 to present, exposed through the official NYC Open Data Socrata portal with bounded SODA export queries.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nSELECT unique_key, created_date, complaint_type, borough, latitude, longitude\nFROM read_csv_auto('https://data.cityofnewyork.us/resource/erm2-nwe9.csv?$select=unique_key,created_date,complaint_type,borough,latitude,longitude&$where=created_date%20%3E=%20%272026-01-01T00:00:00%27&$order=unique_key&$limit=10');",
        "examples": {
          "recent_borough_page": "LOAD httpfs;\nSELECT unique_key, created_date, complaint_type, borough, status\nFROM read_csv_auto('https://data.cityofnewyork.us/resource/erm2-nwe9.csv?$select=unique_key,created_date,complaint_type,borough,status&$where=borough=%27BROOKLYN%27%20AND%20created_date%20%3E=%20%272026-01-01T00:00:00%27&$order=unique_key&$limit=100&$offset=0');"
        },
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {},
        "validation_query": "LOAD httpfs;\nSELECT count(*) > 0 AS ok\nFROM read_csv_auto('https://data.cityofnewyork.us/resource/erm2-nwe9.csv?$select=unique_key&$order=unique_key&$limit=1');"
      },
      "homepage": "https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9",
      "id": "socrata.nyc.311-service-requests",
      "license_url": "https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCadmin/0-0-0-216807",
      "name": "NYC Open Data 311 Service Requests",
      "release": {},
      "source_type": "socrata",
      "status": "candidate",
      "tags": [
        "socrata",
        "nyc",
        "311",
        "service-requests",
        "csv"
      ],
      "validations": []
    },
    {
      "attribution": "Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention and Health Promotion, Division of Population Health. PLACES - Local Data for Better Health, County Data, 2025 release. Public domain.",
      "authority": "Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention and Health Promotion, Division of Population Health",
      "description": "CDC PLACES model-based county-level estimates for chronic disease outcomes, prevention measures, risk behaviors, disabilities, health status, and health-related social needs, published on the official CDC Socrata portal with bounded SODA export queries.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nSELECT year, stateabbr, locationname, measureid, data_value, totalpopulation, locationid\nFROM read_csv_auto('https://data.cdc.gov/resource/swc5-untb.csv?$select=year,stateabbr,locationname,measureid,data_value,totalpopulation,locationid&$where=stateabbr=%27AK%27%20AND%20measureid=%27OBESITY%27%20AND%20datavaluetypeid=%27AgeAdjPrv%27&$order=locationid&$limit=10');",
        "examples": {
          "state_measure_page": "LOAD httpfs;\nSELECT locationid, locationname, measureid, data_value, low_confidence_limit, high_confidence_limit\nFROM read_csv_auto('https://data.cdc.gov/resource/swc5-untb.csv?$select=locationid,locationname,measureid,data_value,low_confidence_limit,high_confidence_limit&$where=stateabbr=%27TX%27%20AND%20datavaluetypeid=%27AgeAdjPrv%27&$order=locationid,measureid&$limit=1000&$offset=0');"
        },
        "extensions": [
          "httpfs"
        ],
        "install": "INSTALL httpfs;",
        "tables": {},
        "validation_query": "LOAD httpfs;\nSELECT count(*) > 0 AS ok\nFROM read_csv_auto('https://data.cdc.gov/resource/swc5-untb.csv?$select=locationid&$order=locationid&$limit=1');"
      },
      "homepage": "https://data.cdc.gov/d/swc5-untb",
      "id": "socrata.cdc.places-county-2025",
      "license_url": "https://data.cdc.gov/api/views/metadata/v1/swc5-untb",
      "name": "CDC PLACES county health estimates, 2025 release",
      "release": {},
      "source_type": "socrata",
      "status": "candidate",
      "tags": [
        "socrata",
        "cdc",
        "health",
        "counties",
        "public-domain",
        "csv"
      ],
      "validations": []
    },
    {
      "attribution": "Google Open Buildings and Microsoft GlobalMLBuildingFootprints, combined by VIDA; licensed under ODbL v1.0.",
      "authority": "VIDA, combining Google Open Buildings V3 and Microsoft GlobalMLBuildingFootprints",
      "description": "VIDA's combined Google and Microsoft global building-footprint dataset, partitioned as public GeoParquet on Source Cooperative for direct DuckDB scans.",
      "duckdb": {
        "example_query": "LOAD httpfs;\nLOAD spatial;\n\n-- GeoParquet 1.1 partitioned by CGAZ ADM0 country ISO3 code.\n-- Path pattern: geoparquet/by_country/country_iso={ISO3}/{ISO3}.parquet\n-- The bbox struct allows pushdown filtering without loading the geometry.\nSELECT bf_source, confidence, area_in_meters, bbox, ST_AsText(geometry) AS wkt\nFROM read_parquet('https://data.source.coop/vida/google-microsoft-open-buildings/geoparquet/by_country/country_iso=AND/AND.parquet')\nWHERE bbox.xmin <= 1.55\n  AND bbox.xmax >= 1.50\n  AND bbox.ymin <= 42.52\n  AND bbox.ymax >= 42.50\nLIMIT 5;",
        "examples": {
          "by_country_s2": "LOAD httpfs;\n\n-- S2 sub-partitions cap each file at 20M footprints for large countries.\n-- Path pattern: geoparquet/by_country_s2/country_iso={ISO3}/{S2_GRID_ID}.parquet\nSELECT count(*) AS footprints\nFROM read_parquet('https://data.source.coop/vida/google-microsoft-open-buildings/geoparquet/by_country/country_iso=AND/AND.parquet');"
        },
        "extensions": [
          "httpfs",
          "spatial"
        ],
        "install": "INSTALL httpfs;\nINSTALL spatial;",
        "tables": {},
        "validation_query": "LOAD httpfs;\n\nSELECT count(*) > 0 AS ok\nFROM read_parquet('https://data.source.coop/vida/google-microsoft-open-buildings/geoparquet/by_country/country_iso=AND/AND.parquet');"
      },
      "homepage": "https://source.coop/repositories/vida/google-microsoft-open-buildings/description",
      "id": "sourcecoop.vida.google-microsoft-open-buildings",
      "license_url": "https://data.source.coop/vida/google-microsoft-open-buildings/README.md",
      "name": "VIDA Google-Microsoft Open Buildings (Source Cooperative GeoParquet)",
      "release": {},
      "source_type": "parquet",
      "status": "candidate",
      "tags": [
        "source-cooperative",
        "buildings",
        "geospatial",
        "geoparquet",
        "footprints"
      ],
      "validations": []
    }
  ]
}
)odd_registry";

} // namespace open_data_duck
} // namespace duckdb
