// GENERATED FILE. DO NOT EDIT.
// Source of truth: registry/sources.yml
// Regenerate with: uv run odd generate-extension-registry
// Drift check:     uv run odd generate-extension-registry --check
#pragma once

namespace duckdb {
namespace open_data_duck {

static constexpr int REGISTRY_SCHEMA_VERSION = 2;
static constexpr int REGISTRY_SOURCE_COUNT = 30;

static const char *const REGISTRY_JSON = R"odd_registry(
{
  "schema_version": 2,
  "source_count": 30,
  "sources": [
    {
      "attribution": "Overture Maps Foundation and contributing data providers.",
      "authority": "Overture Maps Foundation",
      "discovery": {
        "discover_sql": "SELECT collection AS name,\n       'read_parquet' AS reader,\n       regexp_replace(regexp_replace(min(assets.aws.href), '^https://([^.]+)\\.s3\\.[^/]+/', 's3://\\1/'), '/part-[^/]+$', '/*') AS path\nFROM read_parquet('https://stac.overturemaps.org/{release}/collections.parquet')\nGROUP BY collection;\n",
        "namespace": "odd.overturemaps.latest"
      },
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
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "overture",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "bbox or area",
            "release or latest",
            "limit"
          ],
          "columns_hint": {
            "bbox": "Bounding box for fast spatial prefilters.",
            "geometry": "Place geometry.",
            "id": "Stable Overture feature id.",
            "names": "Nested names object; primary/common/local names are not plain text columns."
          },
          "description": "Places and points of interest. One row per Overture place feature.",
          "id": "place",
          "ref": "odd.overturemaps.latest.place",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the latest Overture places facade with the direct public S3 parquet recipe over a sampled tiny bbox.",
              "direct_sql": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_latest_release_url = (\n  SELECT l.href\n  FROM (SELECT unnest(links) AS l FROM read_json('https://stac.overturemaps.org/catalog.json'))\n  WHERE l.rel = 'child' AND l.latest\n);\nSET VARIABLE s3_uri = (\n  SELECT regexp_replace(\n           regexp_replace(min(assets.aws.href), '^https://([^.]+)\\\\.s3\\\\.[^/]+/', 's3://\\\\1/'),\n           '/part-[^/]+$',\n           '/*'\n         )\n  FROM read_parquet(replace(getvariable('overture_latest_release_url'), '/catalog.json', '/collections.parquet'))\n  WHERE collection = 'place'\n);\n\nSELECT id, names, bbox\nFROM read_parquet(getvariable('s3_uri'))\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
              "id": "odd.overturemaps.latest.place",
              "limit": 10,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSELECT id, names, bbox\nFROM odd.overturemaps.latest.place\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
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
          ],
          "warnings": [
            "Large global table; always use tight bbox filters."
          ]
        },
        {
          "ask_for": [
            "bbox or area",
            "release or latest",
            "limit"
          ],
          "description": "Building footprint polygons. One row per Overture building feature.",
          "id": "building",
          "ref": "odd.overturemaps.latest.building",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the latest Overture buildings facade with the direct public S3 parquet recipe over a sampled tiny bbox.",
              "direct_sql": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\nSELECT id, bbox\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=buildings/type=building/*'\n)\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
              "id": "odd.overturemaps.latest.building",
              "limit": 10,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\nSELECT id, bbox\nFROM odd.overturemaps.latest.building\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
              "order_by": [
                "id"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "Large global table; always use tight bbox filters."
          ]
        },
        {
          "ask_for": [
            "bbox or area",
            "release or latest",
            "limit"
          ],
          "description": "Transportation road/path segments. One row per Overture segment feature.",
          "id": "segment",
          "ref": "odd.overturemaps.latest.segment",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the latest Overture transportation segments facade with the direct public S3 parquet recipe over a sampled tiny bbox.",
              "direct_sql": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\nSELECT id, bbox\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=transportation/type=segment/*'\n)\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
              "id": "odd.overturemaps.latest.segment",
              "limit": 10,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\nSELECT id, bbox\nFROM odd.overturemaps.latest.segment\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
              "order_by": [
                "id"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "Large global table; always use tight bbox filters."
          ]
        },
        {
          "ask_for": [
            "bbox or area",
            "release or latest",
            "limit"
          ],
          "description": "Address point/record features. One row per Overture address feature.",
          "id": "address",
          "ref": "odd.overturemaps.latest.address",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the latest Overture addresses facade with the direct public S3 parquet recipe over a sampled tiny bbox.",
              "direct_sql": "LOAD httpfs;\nSET s3_region='us-west-2';\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\n\nSELECT id, bbox\nFROM read_parquet(\n  getvariable('overture_s3_base') || '/release/' || getvariable('overture_release') || '/theme=addresses/type=address/*'\n)\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
              "id": "odd.overturemaps.latest.address",
              "limit": 10,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE overture_release = '2026-10-21.0';\nSET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';\nSELECT id, bbox\nFROM odd.overturemaps.latest.address\nWHERE bbox.xmin <= 66.981\n  AND bbox.xmax >= 66.976\n  AND bbox.ymin <= 39.657\n  AND bbox.ymax >= 39.652\nORDER BY id\nLIMIT 10;\n",
              "order_by": [
                "id"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "Large global table; always use tight bbox filters."
          ]
        }
      ]
    },
    {
      "attribution": "Natural Earth public-domain map data; optional credit: Made with Natural Earth.",
      "authority": "Natural Earth",
      "discovery": {
        "discover_sql": "SELECT 'countries_{release}' AS name,\n       'st_read' AS reader,\n       '/vsizip/vsicurl/https://naciscdn.org/naturalearth/{release}/cultural/ne_{release}_admin_0_countries.zip/ne_{release}_admin_0_countries.shp' AS path;\n",
        "namespace": "odd.naturalearth.latest"
      },
      "id": "naturalearth.admin0-countries",
      "license_url": "https://www.naturalearthdata.com/about/terms-of-use/",
      "name": "Natural Earth Admin 0 countries",
      "release": {
        "latest": {
          "method": "static-download",
          "resolve_sql": "SELECT regexp_extract('https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip', '/naturalearth/([0-9]+m)/', 1) AS release;\n",
          "url": "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
        },
        "pinned": {
          "duckdb_setting": "naturalearth_scale",
          "example": "110m"
        }
      },
      "requirements": {
        "duckdb_extensions": [
          "spatial"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "scale",
            "whether de facto boundaries are acceptable",
            "country or sovereignty fields",
            "limit"
          ],
          "columns_hint": {
            "CONTINENT": "Continent grouping from Natural Earth.",
            "ISO_A3": "Three-letter ISO-style country code where assigned.",
            "NAME": "Display name for the country or map unit.",
            "POP_EST": "Estimated population attribute from Natural Earth.",
            "geom": "Generalized polygon or multipolygon geometry."
          },
          "description": "Generalized Admin 0 country polygons at 1:110m scale. One row per country or country-like map unit in the Natural Earth countries layer.",
          "id": "countries_110m",
          "ref": "odd.naturalearth.latest.countries_110m",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the Natural Earth Admin 0 countries facade with the direct zipped shapefile recipe for two stable country rows.",
              "direct_sql": "LOAD spatial;\nSELECT NAME, ISO_A3, CONTINENT, POP_EST\nFROM ST_Read('/vsizip/vsicurl/https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip/ne_110m_admin_0_countries.shp')\nWHERE ISO_A3 IN ('USA', 'UZB')\nORDER BY ISO_A3;\n",
              "id": "odd.naturalearth.latest.countries_110m",
              "limit": 2,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSELECT NAME, ISO_A3, CONTINENT, POP_EST\nFROM odd.naturalearth.latest.countries_110m\nWHERE ISO_A3 IN ('USA', 'UZB')\nORDER BY ISO_A3;\n",
              "order_by": [
                "ISO_A3"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "Natural Earth is cartographic generalized data for small-scale maps, not legal or survey boundaries.",
            "The Admin 0 countries layer uses de facto boundaries by default; choose a different Natural Earth Admin 0 product if map units, sovereignty, or disputed areas matter."
          ]
        }
      ]
    },
    {
      "attribution": "Dataset-specific attribution required; verify per collection.",
      "authority": "Element 84 / AWS Open Data ecosystem",
      "id": "stac.earth-search.aws",
      "license_url": "https://registry.opendata.aws/sentinel-2-l2a-cogs/",
      "name": "Earth Search STAC API",
      "requirements": {
        "duckdb_extensions": [
          "httpfs",
          "spatial",
          "stac"
        ]
      },
      "source_type": "stac",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "collection",
            "bbox",
            "date range",
            "cloud cover",
            "limit"
          ],
          "description": "STAC item search results from Earth Search. One row per imagery item returned by the STAC API.",
          "id": "stac_items",
          "warnings": [
            "Assets can be large; inspect metadata before reading imagery assets."
          ]
        }
      ]
    },
    {
      "attribution": "Dataset-specific attribution required; verify per Planetary Computer collection.",
      "authority": "Microsoft Planetary Computer",
      "id": "stac.microsoft.planetary-computer",
      "license_url": "https://planetarycomputer.microsoft.com/terms",
      "name": "Microsoft Planetary Computer STAC API",
      "requirements": {
        "duckdb_extensions": [
          "httpfs",
          "spatial",
          "stac"
        ]
      },
      "source_type": "stac",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "collection",
            "bbox",
            "date range",
            "limit"
          ],
          "description": "STAC item search results from Microsoft Planetary Computer. One row per catalog item returned by the STAC API.",
          "id": "stac_items",
          "warnings": [
            "Some assets require Planetary Computer signing or access patterns."
          ]
        }
      ]
    },
    {
      "attribution": "NASA LP DAAC data; cite dataset-specific DOI and attribution.",
      "authority": "NASA Land Processes Distributed Active Archive Center",
      "id": "stac.nasa.lpcloud",
      "license_url": "https://www.earthdata.nasa.gov/engage/open-data-services-and-software/data-and-information-policy",
      "name": "NASA LP DAAC LPCLOUD STAC catalog",
      "requirements": {
        "duckdb_extensions": [
          "httpfs",
          "spatial",
          "stac"
        ]
      },
      "source_type": "stac",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "product or collection",
            "bbox or area",
            "date range",
            "limit"
          ],
          "description": "NASA LP DAAC STAC item metadata. One row per land-processes product item returned by the STAC API.",
          "id": "stac_items",
          "warnings": [
            "Some downstream assets may require Earthdata access workflows."
          ]
        }
      ]
    },
    {
      "attribution": "U.S. Census Bureau TIGERweb.",
      "authority": "U.S. Census Bureau",
      "id": "arcgis.census.tigerweb.state-county",
      "license_url": "https://www.census.gov/data/developers/about/terms-of-service.html",
      "name": "U.S. Census TIGERweb state and county layers",
      "requirements": {
        "duckdb_extensions": [
          "arcgis"
        ]
      },
      "source_type": "arcgis",
      "status": "connector-blocked",
      "tables": [
        {
          "ask_for": [
            "state or county",
            "fields",
            "whether geometry is needed"
          ],
          "description": "TIGERweb state/county boundary layer features. One row per ArcGIS boundary feature.",
          "id": "county_boundaries",
          "warnings": [
            "Connector is blocked; use REST pagination until ArcGIS support is stable."
          ]
        }
      ]
    },
    {
      "attribution": "U.S. Census Bureau Geography Program, Cartographic Boundary Files; cite the selected year and scale and do not imply Census Bureau endorsement.",
      "authority": "U.S. Census Bureau Geography Program",
      "discovery": {
        "discover_sql": "SELECT regexp_extract(z, 'cb_{release}_us_(.+)\\.zip', 1) AS name,\n       'st_read' AS reader,\n       '/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ{release}/shp/' || z || '/' || replace(z, '.zip', '.shp') AS path\nFROM (SELECT DISTINCT unnest(regexp_extract_all(content, 'cb_{release}_us_county[a-z0-9_]*\\.zip')) AS z\n      FROM read_text('https://www2.census.gov/geo/tiger/GENZ{release}/shp/'));\n",
        "namespace": "odd.census.latest"
      },
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
      "requirements": {
        "duckdb_extensions": [
          "spatial"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "year",
            "scale",
            "state filter",
            "GEOID join key"
          ],
          "description": "Generalized U.S. county polygons at 20m scale. One row per county or county-equivalent feature.",
          "id": "county_20m",
          "ref": "odd.census.latest.county_20m",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the latest Census county boundary facade with the direct zipped shapefile recipe.",
              "direct_sql": "LOAD spatial;\nSELECT GEOID, NAME, STATE_NAME\nFROM ST_Read('/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_county_20m.zip/cb_2025_us_county_20m.shp')\nWHERE STATEFP = '02'\nORDER BY GEOID\nLIMIT 10;\n",
              "id": "odd.census.latest.county_20m",
              "limit": 10,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE census_cartographic_year = '2025';\nSELECT GEOID, NAME, STATE_NAME\nFROM odd.census.latest.county_20m\nWHERE STATEFP = '02'\nORDER BY GEOID\nLIMIT 10;\n",
              "order_by": [
                "GEOID"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "Generalized for thematic mapping",
            "not surveying."
          ]
        }
      ]
    },
    {
      "attribution": "U.S. Census Bureau Geography Program, Cartographic Boundary Files; cite the selected year and scale and do not imply Census Bureau endorsement.",
      "authority": "U.S. Census Bureau Geography Program",
      "discovery": {
        "discover_sql": "SELECT regexp_extract(z, 'cb_{release}_us_(.+)\\.zip', 1) AS name,\n       'st_read' AS reader,\n       '/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ{release}/shp/' || z || '/' || replace(z, '.zip', '.shp') AS path\nFROM (SELECT DISTINCT unnest(regexp_extract_all(content, 'cb_{release}_us_tract[a-z0-9_]*\\.zip')) AS z\n      FROM read_text('https://www2.census.gov/geo/tiger/GENZ{release}/shp/'));\n",
        "namespace": "odd.census.latest"
      },
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
      "requirements": {
        "duckdb_extensions": [
          "spatial"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "year",
            "scale",
            "state filter",
            "tract GEOID join key"
          ],
          "description": "Generalized U.S. census tract polygons at 5m scale. One row per census tract feature.",
          "id": "tract_5m",
          "ref": "odd.census.latest.tract_5m",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the latest Census tract boundary facade with the direct zipped shapefile recipe.",
              "direct_sql": "LOAD spatial;\nSELECT GEOID, NAME, STATEFP, COUNTYFP\nFROM ST_Read('/vsizip/vsicurl/https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_tract_5m.zip/cb_2025_us_tract_5m.shp')\nWHERE STATEFP = '02'\nORDER BY GEOID\nLIMIT 10;\n",
              "id": "odd.census.latest.tract_5m",
              "limit": 10,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE census_cartographic_year = '2025';\nSELECT GEOID, NAME, STATEFP, COUNTYFP\nFROM odd.census.latest.tract_5m\nWHERE STATEFP = '02'\nORDER BY GEOID\nLIMIT 10;\n",
              "order_by": [
                "GEOID"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "National tract files are larger; filter by state when possible."
          ]
        }
      ]
    },
    {
      "attribution": "Federal Emergency Management Agency National Flood Hazard Layer.",
      "authority": "Federal Emergency Management Agency",
      "id": "arcgis.fema.nfhl.flood-hazard-zones",
      "license_url": "https://www.fema.gov/about/openfema/terms-conditions",
      "name": "FEMA National Flood Hazard Layer flood hazard zones",
      "requirements": {
        "duckdb_extensions": [
          "arcgis"
        ]
      },
      "source_type": "arcgis",
      "status": "connector-blocked",
      "tables": [
        {
          "ask_for": [
            "bbox or jurisdiction",
            "fields",
            "whether geometry is needed"
          ],
          "description": "FEMA NFHL flood hazard zone features. One row per flood hazard zone feature.",
          "id": "flood_hazard_zones",
          "warnings": [
            "Not a substitute for official determinations; connector path is not stable yet."
          ]
        }
      ]
    },
    {
      "attribution": "Cite FEMA OpenFEMA and the Disaster Declarations Summaries dataset/retrieval per the OpenFEMA Terms and Conditions citation guidance.",
      "authority": "Federal Emergency Management Agency OpenFEMA",
      "discovery": {
        "discover_sql": "SELECT 'disaster_declarations' AS name,\n       'read_parquet' AS reader,\n       'https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries.parquet' AS path\nWHERE '{release}' = 'v2';\n",
        "namespace": "odd.fema.latest"
      },
      "id": "fema.openfema.disaster-declarations",
      "license_url": "https://www.fema.gov/about/openfema/terms-conditions",
      "name": "FEMA OpenFEMA Disaster Declarations Summaries",
      "release": {
        "latest": {
          "method": "static-parquet",
          "resolve_sql": "SELECT 'v2' AS release;\n",
          "url": "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries.parquet"
        },
        "pinned": {
          "duckdb_setting": "fema_disaster_declarations_release",
          "example": "v2"
        }
      },
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "parquet",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "state or territory",
            "declaration date or fiscal year range",
            "incident type",
            "declaration type",
            "assistance program flags",
            "limit"
          ],
          "columns_hint": {
            "declarationDate": "Date FEMA declared the disaster.",
            "declarationType": "FEMA declaration type code.",
            "designatedArea": "County, parish, borough, census area, statewide area, or Tribal area covered by the declaration.",
            "disasterNumber": "FEMA disaster declaration number.",
            "hmProgramDeclared": "Whether Hazard Mitigation was declared for the record.",
            "ihProgramDeclared": "Whether the Individual and Households Program was declared for the record.",
            "incidentType": "Incident category such as Flood, Fire, Hurricane, or Earthquake.",
            "paProgramDeclared": "Whether Public Assistance was declared for the record.",
            "state": "Two-letter state, territory, or Tribal Nation state-code grouping."
          },
          "description": "FEMA disaster declaration summary records. One row per federally declared disaster declaration and designated geographic area from 1953 forward.",
          "id": "disaster_declarations",
          "ref": "odd.fema.latest.disaster_declarations",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the FEMA OpenFEMA disaster declarations facade with the direct public Parquet export for stable state aggregates.",
              "direct_sql": "LOAD httpfs;\nSELECT state, count(*) AS declarations, min(disasterNumber) AS first_disaster, max(disasterNumber) AS latest_disaster\nFROM read_parquet('https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries.parquet')\nWHERE state IN ('AK', 'CA')\nGROUP BY state\nORDER BY state;\n",
              "id": "odd.fema.latest.disaster_declarations",
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE fema_disaster_declarations_release = 'v2';\nSELECT state, count(*) AS declarations, min(disasterNumber) AS first_disaster, max(disasterNumber) AS latest_disaster\nFROM odd.fema.latest.disaster_declarations\nWHERE state IN ('AK', 'CA')\nGROUP BY state\nORDER BY state;\n",
              "order_by": [
                "state"
              ],
              "release": "latest",
              "source_release": "v2"
            }
          ],
          "warnings": [
            "FEMA describes OpenFEMA as raw, unedited NEMIS data; historical/manual records can contain a small percentage of human error.",
            "County data is not available before 1964, Fire Management records are partial, and Tribal Nation declarations are currently included in state data."
          ]
        }
      ]
    },
    {
      "attribution": "U.S. Geological Survey National Map.",
      "authority": "U.S. Geological Survey",
      "id": "arcgis.usgs.national-map-contours",
      "license_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
      "name": "USGS National Map elevation contours",
      "requirements": {
        "duckdb_extensions": [
          "arcgis"
        ]
      },
      "source_type": "arcgis",
      "status": "connector-blocked",
      "tables": [
        {
          "ask_for": [
            "bbox",
            "contour interval or elevation need",
            "fields"
          ],
          "description": "USGS National Map elevation contour line features. One row per contour segment feature.",
          "id": "contours",
          "warnings": [
            "Connector is blocked; large geometry layers need paging."
          ]
        }
      ]
    },
    {
      "attribution": "National Highway Traffic Safety Administration (NHTSA), U.S. Department of Transportation; credit NHTSA/DOT and do not imply endorsement.",
      "authority": "National Highway Traffic Safety Administration, U.S. Department of Transportation",
      "id": "nhtsa.vehicle-safety",
      "license_url": "https://www.nhtsa.gov/about-nhtsa/terms-use",
      "name": "NHTSA vehicle safety recalls and ratings APIs",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "model year",
            "make",
            "model",
            "limit"
          ],
          "columns_hint": {
            "Component": "Vehicle component affected by the recall.",
            "NHTSACampaignNumber": "NHTSA recall campaign identifier.",
            "ReportReceivedDate": "Date NHTSA received the campaign report.",
            "Summary": "Long recall summary text."
          },
          "description": "NHTSA recall campaign results for a requested model year, make, and model. One row per recall campaign result.",
          "id": "recalls_by_vehicle",
          "warnings": [
            "Parameterized API endpoint; preserve model year",
            "make",
            "and model filters instead of treating it as a full-table scan."
          ]
        },
        {
          "ask_for": [
            "model year",
            "make",
            "model",
            "limit"
          ],
          "columns_hint": {
            "VehicleDescription": "Human-readable vehicle variant description.",
            "VehicleId": "Identifier used by NHTSA rating-detail lookups."
          },
          "description": "NHTSA safety-rating vehicle variants for a requested model year, make, and model. One row per returned vehicle variant.",
          "id": "safety_rating_variants",
          "warnings": [
            "Parameterized API endpoint; use the returned VehicleId for rating-detail lookups."
          ]
        }
      ]
    },
    {
      "attribution": "U.S. Geological Survey Earthquake Hazards Program; credit USGS earthquake feeds and do not imply USGS endorsement.",
      "authority": "U.S. Geological Survey Earthquake Hazards Program",
      "id": "usgs.earthquake.realtime-geojson",
      "license_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
      "name": "USGS realtime earthquake GeoJSON feeds",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "feed window",
            "magnitude threshold",
            "bbox or region",
            "limit"
          ],
          "columns_hint": {
            "geometry": "GeoJSON point with longitude, latitude, and depth.",
            "mag": "Earthquake magnitude.",
            "place": "Human-readable event location.",
            "time": "Event time in epoch milliseconds."
          },
          "description": "Recent USGS earthquake event features. One row per reported seismic event in the selected rolling feed.",
          "id": "earthquake_events",
          "warnings": [
            "Rolling feeds are not stable historical snapshots."
          ]
        }
      ]
    },
    {
      "attribution": "Credit U.S. Geological Survey / USGS Water Data for the Nation; cite the site, parameter, time range, and retrieval endpoint used.",
      "authority": "U.S. Geological Survey Water Data for the Nation",
      "id": "usgs.nwis.instantaneous-values",
      "license_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
      "name": "USGS NWIS instantaneous water values API",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "site number",
            "parameter code",
            "start datetime",
            "end datetime",
            "site status",
            "whether provisional operational values are acceptable"
          ],
          "columns_hint": {
            "observed_at": "Observation timestamp returned by the service, generally UTC when date ranges are supplied without local timezone offsets.",
            "observed_value": "Observation value cast to DOUBLE from the nested JSON string value.",
            "parameter_cd": "USGS parameter code such as 00060 for streamflow.",
            "qualifiers": "USGS value qualifiers such as approved or provisional status flags.",
            "site_no": "USGS monitoring site number such as 01646500."
          },
          "description": "USGS NWIS instantaneous observations. One row per timestamped monitoring-site and parameter observation after flattening the WaterML JSON timeSeries payload.",
          "id": "instantaneous_values",
          "warnings": [
            "Responses are nested by time series and values arrays; unnest timeSeries and values before treating observations as rows.",
            "Large multi-site or multi-parameter requests should be bounded by date range.",
            "Instantaneous operational values can be provisional and not fully quality-assured."
          ]
        }
      ]
    },
    {
      "attribution": "World Bank Group, World Development Indicators; attribute as: The World Bank: World Development Indicators: World Bank Group. Do not imply World Bank endorsement.",
      "authority": "World Bank Group",
      "id": "worldbank.wdi.indicators",
      "license_url": "https://www.worldbank.org/ext/en/legal/terms-conditions/datasets",
      "name": "World Bank World Development Indicators API",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "country code",
            "indicator id",
            "year range"
          ],
          "description": "World Bank indicator observations. One row per country, indicator, and year.",
          "id": "indicators",
          "warnings": [
            "Values may be null; API responses use a JSON envelope."
          ]
        }
      ]
    },
    {
      "attribution": "Cite BLS.gov and the API retrieval date; state that BLS.gov cannot vouch for data or analyses derived after retrieval; do not use the BLS logo or imply BLS sponsorship.",
      "authority": "U.S. Bureau of Labor Statistics",
      "id": "bls.cpi.timeseries",
      "license_url": "https://www.bls.gov/developers/termsOfService.htm",
      "name": "BLS Consumer Price Index time series API",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "series id",
            "start year",
            "end year"
          ],
          "description": "BLS CPI time-series observations. One row per BLS series and period.",
          "id": "cpi_observations",
          "warnings": [
            "Values are returned as strings and should be cast before numeric analysis."
          ]
        }
      ]
    },
    {
      "attribution": "Data provided by the U.S. Food and Drug Administration (https://open.fda.gov); openFDA materials are public domain / CC0 unless otherwise noted.",
      "authority": "U.S. Food and Drug Administration openFDA",
      "id": "openfda.food.enforcement-reports",
      "license_url": "https://open.fda.gov/license/",
      "name": "FDA openFDA food enforcement recall reports",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "classification",
            "status",
            "date window",
            "product or firm search term",
            "limit"
          ],
          "columns_hint": {
            "classification": "Recall classification, such as Class I, Class II, or Class III.",
            "product_description": "Product description text from the recall report.",
            "recall_number": "FDA recall number for the enforcement report.",
            "recalling_firm": "Firm responsible for the recall.",
            "report_date": "FDA report date as YYYYMMDD text.",
            "status": "Recall status, such as Ongoing, Completed, or Terminated."
          },
          "description": "FDA food enforcement recall reports. One row per public recall report returned from the openFDA food enforcement endpoint after unnesting the JSON results envelope.",
          "id": "food_enforcement_reports",
          "warnings": [
            "API keys are optional but keyless access can be rate-limited; responses are nested JSON envelopes",
            "so unnest results before treating reports as rows."
          ]
        }
      ]
    },
    {
      "attribution": "U.S. Department of the Treasury, Bureau of the Fiscal Service, Fiscal Data / Debt to the Penny; do not imply Treasury endorsement.",
      "authority": "U.S. Department of the Treasury, Bureau of the Fiscal Service",
      "id": "treasury.fiscaldata.debt-to-penny",
      "license_url": "https://catalog.data.gov/dataset/debt-to-the-penny",
      "name": "U.S. Treasury Fiscal Data Debt to the Penny API",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "date window",
            "debt field",
            "limit"
          ],
          "description": "U.S. Treasury daily public debt outstanding records. One row per record date.",
          "id": "debt_observations",
          "warnings": [
            "Fiscal Data CSV responses are gzipped; use compression = 'gzip'."
          ]
        }
      ]
    },
    {
      "attribution": "World Resources Institute / Global Power Plant Database; preserve CC BY 4.0 attribution and do not imply WRI endorsement.",
      "authority": "World Resources Institute",
      "discovery": {
        "discover_sql": "SELECT 'global_power_plants' AS name,\n       'read_csv' AS reader,\n       'https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv' AS path\nWHERE '{release}' = 'v1x3x0';\n",
        "namespace": "odd.wri.latest"
      },
      "id": "wri.global-power-plant-database",
      "license_url": "https://raw.githubusercontent.com/wri/global-power-plant-database/master/README.md",
      "name": "WRI Global Power Plant Database",
      "release": {
        "latest": {
          "method": "static-csv",
          "resolve_sql": "SELECT 'v1x3x0' AS release;\n",
          "url": "https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv"
        },
        "pinned": {
          "duckdb_setting": "wri_global_power_plants_release",
          "example": "v1x3x0"
        }
      },
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "country or countries",
            "fuel type",
            "capacity threshold",
            "whether stale 2021/2022-era data is acceptable",
            "limit"
          ],
          "columns_hint": {
            "capacity_mw": "Plant capacity in megawatts.",
            "country": "ISO-like three-letter country code used by the dataset.",
            "country_long": "Country display name.",
            "latitude": "Plant latitude.",
            "longitude": "Plant longitude.",
            "name": "Power plant name.",
            "primary_fuel": "Primary fuel category.",
            "year_of_capacity_data": "Year attached to the reported capacity data where available."
          },
          "description": "Global power plant records. One row per plant with country, fuel, capacity, geolocation, ownership/source metadata, and generation fields.",
          "id": "global_power_plants",
          "ref": "odd.wri.latest.global_power_plants",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the WRI Global Power Plant Database facade with the direct public CSV recipe for stable country aggregates.",
              "direct_sql": "LOAD httpfs;\nSELECT country, count(*) AS plants, round(sum(capacity_mw), 1) AS capacity_mw\nFROM read_csv_auto('https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv')\nWHERE country IN ('USA', 'UZB')\nGROUP BY country\nORDER BY country;\n",
              "id": "odd.wri.latest.global_power_plants",
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE wri_global_power_plants_release = 'v1x3x0';\nSELECT country, count(*) AS plants, round(sum(capacity_mw), 1) AS capacity_mw\nFROM odd.wri.latest.global_power_plants\nWHERE country IN ('USA', 'UZB')\nGROUP BY country\nORDER BY country;\n",
              "order_by": [
                "country"
              ],
              "release": "latest",
              "source_release": "v1.3.0"
            }
          ],
          "warnings": [
            "WRI says the project is not currently maintained and has no planned updates as of early 2022; use it as a broad reference index, not a freshness-sensitive operational source.",
            "The integrated database combines national and manual sources, so inspect source-year and lineage fields before comparing countries."
          ]
        }
      ]
    },
    {
      "attribution": "NOAA National Centers for Environmental Information, Storm Events Database; credit NOAA/NCEI and do not imply NOAA endorsement.",
      "authority": "NOAA National Centers for Environmental Information",
      "discovery": {
        "discover_sql": "WITH files AS (\n  SELECT regexp_extract(m, 'StormEvents_([a-z]+)-ftp_v1\\.0_d{release}_c([0-9]{8})\\.csv\\.gz', 1) AS table_kind,\n         regexp_extract(m, '(StormEvents_[a-z]+-ftp_v1\\.0_d{release}_c[0-9]{8}\\.csv\\.gz)', 1) AS file_name,\n         regexp_extract(m, '_c([0-9]{8})\\.csv\\.gz', 1) AS created\n  FROM (SELECT DISTINCT unnest(regexp_extract_all(content, 'StormEvents_[a-z]+-ftp_v1\\.0_d{release}_c[0-9]{8}\\.csv\\.gz')) AS m\n        FROM read_text('https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/'))\n), latest AS (\n  SELECT table_kind, max(created) AS created\n  FROM files\n  GROUP BY table_kind\n)\nSELECT 'storm_events_' || files.table_kind AS name,\n       'read_csv' AS reader,\n       'https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/' || files.file_name AS path\nFROM files\nJOIN latest USING (table_kind, created)\nORDER BY name;\n",
        "namespace": "odd.noaa.latest"
      },
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
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "year",
            "state",
            "event type",
            "limit"
          ],
          "description": "NOAA Storm Events detail rows. One row per reported storm event.",
          "id": "storm_events_details",
          "ref": "odd.noaa.latest.storm_events_details",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare NOAA Storm Events details facade with the direct bulk CSV recipe.",
              "direct_sql": "LOAD httpfs;\nSELECT event_id, state, event_type, begin_date_time, cz_name\nFROM read_csv_auto(\n  'https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_details-ftp_v1.0_d2024_c20261119.csv.gz',\n  sample_size = 20000\n)\nWHERE event_type IS NOT NULL\nORDER BY event_id\nLIMIT 10;\n",
              "id": "odd.noaa.latest.storm_events_details",
              "limit": 10,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE noaa_storm_events_year = '2024';\nSELECT event_id, state, event_type, begin_date_time, cz_name\nFROM odd.noaa.latest.storm_events_details\nWHERE event_type IS NOT NULL\nORDER BY event_id\nLIMIT 10;\n",
              "order_by": [
                "event_id"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "Files are revised with creation-date suffixes; pin year for reproducible examples."
          ]
        },
        {
          "ask_for": [
            "year",
            "state or event id",
            "limit"
          ],
          "description": "NOAA Storm Events fatality rows. One row per fatality associated with a storm event.",
          "id": "storm_events_fatalities",
          "ref": "odd.noaa.latest.storm_events_fatalities",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare NOAA Storm Events fatalities facade with the direct bulk CSV recipe.",
              "direct_sql": "LOAD httpfs;\nSELECT fatality_id, event_id, fatality_type, fatality_date, fatality_age\nFROM read_csv_auto(\n  'https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_fatalities-ftp_v1.0_d2024_c20261119.csv.gz',\n  sample_size = 20000\n)\nWHERE event_id IS NOT NULL\nORDER BY fatality_id\nLIMIT 10;\n",
              "id": "odd.noaa.latest.storm_events_fatalities",
              "limit": 10,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE noaa_storm_events_year = '2024';\nSELECT fatality_id, event_id, fatality_type, fatality_date, fatality_age\nFROM odd.noaa.latest.storm_events_fatalities\nWHERE event_id IS NOT NULL\nORDER BY fatality_id\nLIMIT 10;\n",
              "order_by": [
                "fatality_id"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "Join to details by event_id for event context."
          ]
        },
        {
          "ask_for": [
            "year",
            "state or event id",
            "limit"
          ],
          "description": "NOAA Storm Events location rows. One row per location attached to a storm event.",
          "id": "storm_events_locations",
          "ref": "odd.noaa.latest.storm_events_locations",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare NOAA Storm Events locations facade with the direct bulk CSV recipe.",
              "direct_sql": "LOAD httpfs;\nSELECT event_id, location_index, location, latitude, longitude\nFROM read_csv_auto(\n  'https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_locations-ftp_v1.0_d2024_c20261119.csv.gz',\n  sample_size = 20000\n)\nWHERE event_id IS NOT NULL\nORDER BY event_id, location_index\nLIMIT 10;\n",
              "id": "odd.noaa.latest.storm_events_locations",
              "limit": 10,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE noaa_storm_events_year = '2024';\nSELECT event_id, location_index, location, latitude, longitude\nFROM odd.noaa.latest.storm_events_locations\nWHERE event_id IS NOT NULL\nORDER BY event_id, location_index\nLIMIT 10;\n",
              "order_by": [
                "event_id",
                "location_index"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "Join to details by event_id for event context."
          ]
        }
      ]
    },
    {
      "attribution": "Credit NOAA/NOS Center for Operational Oceanographic Products and Services (CO-OPS); cite the station, product, datum, time zone, units, endpoint, and retrieval date, and do not imply NOAA endorsement.",
      "authority": "NOAA National Ocean Service Center for Operational Oceanographic Products and Services",
      "discovery": {
        "discover_sql": "SELECT 'hourly_heights' AS name,\n       'read_csv_auto' AS reader,\n       'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date=20200101&end_date=20200102&station=8518750&product=hourly_height&datum=MLLW&time_zone=gmt&units=metric&format=csv&application=open_data_duck' AS path;\n",
        "namespace": "odd.noaa_coops.latest"
      },
      "id": "noaa.coops.water-level-observations",
      "license_url": "https://www.noaa.gov/information-policies-and-instructions/copyrights-and-credits",
      "name": "NOAA CO-OPS water-level observations API",
      "release": {
        "latest": {
          "method": "static-api-sample",
          "url": "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        }
      },
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "station id",
            "begin date",
            "end date",
            "water-level product",
            "datum",
            "time zone",
            "units",
            "limit"
          ],
          "columns_hint": {
            "Date Time": "Observation timestamp in the requested time zone.",
            "I": "Inferred flag returned by CO-OPS.",
            "L": "Flat tolerance flag returned by CO-OPS.",
            "Sigma": "Standard deviation for the observation where provided.",
            "Water Level": "Water-level height in the requested units and datum."
          },
          "description": "NOAA CO-OPS hourly water-level observations. One row per timestamped station observation for the selected product, datum, time zone, and units.",
          "id": "hourly_heights",
          "ref": "odd.noaa_coops.latest.hourly_heights",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the NOAA CO-OPS hourly heights sample facade with the direct bounded CSV API recipe.",
              "direct_sql": "LOAD httpfs;\nSELECT count(*) AS row_count,\n       min(\"Date Time\") AS first_observation,\n       max(\"Date Time\") AS last_observation\nFROM read_csv_auto(\n  'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date=20200101&end_date=20200102&station=8518750&product=hourly_height&datum=MLLW&time_zone=gmt&units=metric&format=csv&application=open_data_duck'\n);\n",
              "id": "odd.noaa_coops.latest.hourly_heights",
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSELECT count(*) AS row_count,\n       min(\"Date Time\") AS first_observation,\n       max(\"Date Time\") AS last_observation\nFROM odd.noaa_coops.latest.hourly_heights;\n",
              "release": "latest"
            }
          ],
          "warnings": [
            "Parameterized API endpoint; preserve station, date range, product, datum, time zone, units, and application identifier instead of treating it as a full-table scan.",
            "CO-OPS products have product-specific date-range limits and water-level products require a datum.",
            "Preliminary and verified products differ; keep requests bounded and cite the selected station and retrieval endpoint/date.",
            "Validation facade is a small fixed smoke sample: station=8518750, product=hourly_height, datum=MLLW, begin_date=20200101, end_date=20200102, time_zone=gmt, units=metric; expected result is 48 hourly rows."
          ]
        }
      ]
    },
    {
      "attribution": "NOAA National Centers for Environmental Information, Global Historical Climatology Network Daily.",
      "authority": "NOAA National Centers for Environmental Information",
      "discovery": {
        "discover_sql": "SELECT 'ghcn_daily' AS name,\n       'read_csv' AS reader,\n       'https://noaa-ghcn-pds.s3.amazonaws.com/csv/by_year/{release}.csv' AS path;\n",
        "namespace": "odd.noaa.latest"
      },
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
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "year",
            "station id",
            "climate element"
          ],
          "description": "GHCN Daily station observations. One row per station, date, and observed climate element.",
          "id": "ghcn_daily",
          "ref": "odd.noaa.latest.ghcn_daily",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare NOAA GHCN Daily facade with the direct year CSV recipe.",
              "direct_sql": "LOAD httpfs;\nSELECT id, date, element, data_value\nFROM read_csv_auto('https://noaa-ghcn-pds.s3.amazonaws.com/csv/by_year/2024.csv')\nWHERE id IS NOT NULL\nORDER BY id, date, element\nLIMIT 10;\n",
              "id": "odd.noaa.latest.ghcn_daily",
              "limit": 10,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSET VARIABLE noaa_ghcn_year = '2024';\nSELECT id, date, element, data_value\nFROM odd.noaa.latest.ghcn_daily\nWHERE id IS NOT NULL\nORDER BY id, date, element\nLIMIT 10;\n",
              "order_by": [
                "id",
                "date",
                "element"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "CSV files are large; filter by year/station/element early."
          ]
        }
      ]
    },
    {
      "attribution": "NOAA National Centers for Environmental Information, Global Surface Summary of the Day.",
      "authority": "NOAA National Centers for Environmental Information",
      "id": "aws.noaa-gsod",
      "license_url": "https://www.ncei.noaa.gov/products/land-based-weather-stations",
      "name": "NOAA Global Surface Summary of the Day",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "station id",
            "year",
            "weather fields"
          ],
          "description": "NOAA GSOD daily station weather summaries. One row per station-day summary.",
          "id": "daily_summaries",
          "warnings": [
            "Station files are split by year and station."
          ]
        }
      ]
    },
    {
      "attribution": "NOAA National Centers for Environmental Information, Integrated Surface Database.",
      "authority": "NOAA National Centers for Environmental Information",
      "id": "aws.noaa-isd-history",
      "license_url": "https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database",
      "name": "NOAA Integrated Surface Database station history",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "other",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "country",
            "state",
            "station name",
            "nearby place"
          ],
          "description": "NOAA ISD station metadata. One row per weather station history record.",
          "id": "station_history",
          "warnings": [
            "Metadata lookup only; use observation datasets for measurements."
          ]
        }
      ]
    },
    {
      "attribution": "Wyndham City Council; licensed under Creative Commons Attribution 3.0 Australia.",
      "authority": "Wyndham City Council via data.gov.au",
      "id": "ckan.data-gov-au.wyndham-pets",
      "license_url": "https://creativecommons.org/licenses/by/3.0/au/",
      "name": "Data.gov.au Wyndham registered dogs and cats",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "ckan",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "suburb or animal type"
          ],
          "description": "Wyndham registered dog and cat counts. One row per suburb/count record in the public CSV distribution.",
          "id": "wyndham_pet_registrations",
          "warnings": [
            "CKAN is discovery metadata; query the direct readable CSV distribution."
          ]
        }
      ]
    },
    {
      "attribution": "NYC Open Data, 311 Service Requests from 2020 to Present, City of New York Office of Technology and Innovation.",
      "authority": "City of New York Office of Technology and Innovation via NYC Open Data",
      "id": "socrata.nyc.311-service-requests",
      "license_url": "https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCadmin/0-0-0-216807",
      "name": "NYC Open Data 311 Service Requests",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "socrata",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "date range",
            "borough",
            "complaint type",
            "limit"
          ],
          "description": "NYC 311 service request records. One row per 311 request.",
          "id": "service_requests",
          "warnings": [
            "Large table requires bounded SODA queries with select/order/limit."
          ]
        }
      ]
    },
    {
      "attribution": "Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention and Health Promotion, Division of Population Health. PLACES - Local Data for Better Health, County Data, 2025 release. Public domain.",
      "authority": "Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention and Health Promotion, Division of Population Health",
      "id": "socrata.cdc.places-county-2025",
      "license_url": "https://data.cdc.gov/api/views/metadata/v1/swc5-untb",
      "name": "CDC PLACES county health estimates, 2025 release",
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "socrata",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "state",
            "measure id",
            "age-adjusted or crude prevalence"
          ],
          "description": "CDC PLACES county health estimate rows. One row per county, measure, and data-value type.",
          "id": "county_health_estimates",
          "warnings": [
            "Model-based estimates; filter datavaluetypeid to avoid duplicate measure rows."
          ]
        }
      ]
    },
    {
      "attribution": "CDC/NCHS, National Vital Statistics System mortality data, and CDC WONDER; do not imply CDC endorsement.",
      "authority": "Centers for Disease Control and Prevention, National Center for Health Statistics, Division of Vital Statistics",
      "discovery": {
        "discover_sql": "SELECT 'leading_causes_of_death' AS name,\n       'read_csv_auto' AS reader,\n       'https://data.cdc.gov/resource/bi63-dtpu.csv?$select=year,_113_cause_name,cause_name,state,deaths,aadr&$order=year,state,cause_name&$limit=50000' AS path;\n",
        "namespace": "odd.cdc.latest"
      },
      "id": "socrata.cdc.nchs-leading-causes-of-death",
      "license_url": "https://www.usa.gov/government-works",
      "name": "CDC NCHS leading causes of death, United States",
      "release": {
        "latest": {
          "method": "static-soda-export",
          "url": "https://data.cdc.gov/resource/bi63-dtpu.csv"
        }
      },
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "socrata",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "state",
            "year range",
            "cause name or whether to include the All causes rollup",
            "limit"
          ],
          "columns_hint": {
            "_113_cause_name": "Detailed ICD-coded cause-of-death grouping from Socrata's 113 Cause Name field.",
            "aadr": "Age-adjusted death rate for the selected year, state, and cause.",
            "cause_name": "Cause-of-death grouping; filter out All causes for ranked-cause comparisons.",
            "deaths": "Death count for the selected year, state, and cause.",
            "state": "U.S. state or District of Columbia reported by the dataset.",
            "year": "Reporting year from Socrata's Year field."
          },
          "description": "CDC NCHS leading-cause mortality summary rows. One row per year, state, and cause with death count and age-adjusted death rate.",
          "id": "leading_causes_of_death",
          "ref": "odd.cdc.latest.leading_causes_of_death",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the CDC NCHS Socrata facade with the direct bounded SODA CSV recipe for a stable Alaska mortality sample.",
              "direct_sql": "LOAD httpfs;\nSELECT count(*) AS row_count,\n       min(year) AS first_year,\n       max(year) AS last_year,\n       CAST(sum(CASE WHEN year = 2017 AND cause_name <> 'All causes' THEN deaths ELSE 0 END) AS BIGINT) AS ranked_deaths_2017\nFROM read_csv_auto('https://data.cdc.gov/resource/bi63-dtpu.csv?$select=year,_113_cause_name,cause_name,state,deaths,aadr&$order=year,state,cause_name&$limit=50000')\nWHERE state = 'Alaska';\n",
              "id": "odd.cdc.latest.leading_causes_of_death",
              "limit": 1,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSELECT count(*) AS row_count,\n       min(year) AS first_year,\n       max(year) AS last_year,\n       CAST(sum(CASE WHEN year = 2017 AND cause_name <> 'All causes' THEN deaths ELSE 0 END) AS BIGINT) AS ranked_deaths_2017\nFROM odd.cdc.latest.leading_causes_of_death\nWHERE state = 'Alaska';\n",
              "order_by": [
                "row_count"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "Dataset is a compact NCHS summary, not record-level mortality microdata.",
            "Latest rows in this Socrata asset currently stop at 2017.",
            "Filter out All causes when comparing ranked cause totals.",
            "Facade uses a bounded Socrata SODA CSV export with selected columns, deterministic ordering, and a 50000-row cap.",
            "Smoke sample: Alaska rows returned row_count=209, first_year=1999, last_year=2017, ranked_deaths_2017=3118 on 2026-11-22."
          ]
        }
      ]
    },
    {
      "attribution": "Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention and Health Promotion, Division of Population Health; licensed under ODbL v1.0.",
      "authority": "Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention and Health Promotion, Division of Population Health",
      "discovery": {
        "discover_sql": "SELECT 'chronic_disease_indicators' AS name,\n       'read_csv_auto' AS reader,\n       'https://data.cdc.gov/resource/hksd-2xuw.csv?$select=yearstart,locationabbr,topic,question,datavalue,datavalueunit&$where=yearstart=2023%20AND%20locationabbr=%27AK%27&$order=topic,question&$limit=5000' AS path;\n",
        "namespace": "odd.cdc.latest"
      },
      "id": "socrata.cdc.chronic-disease-indicators",
      "license_url": "https://opendatacommons.org/licenses/odbl/1.0/",
      "name": "CDC U.S. Chronic Disease Indicators",
      "release": {
        "latest": {
          "method": "static-soda-export",
          "url": "https://data.cdc.gov/resource/hksd-2xuw.csv"
        }
      },
      "requirements": {
        "duckdb_extensions": [
          "httpfs"
        ]
      },
      "source_type": "socrata",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "year range",
            "location abbreviation or geography",
            "topic or question filters",
            "stratification fields",
            "limit"
          ],
          "columns_hint": {
            "datavalue": "Indicator value; many rows vary by stratification and some values are suppressed or null.",
            "datavalueunit": "Unit for datavalue, commonly percent.",
            "locationabbr": "U.S. state or territory abbreviation reported by the dataset.",
            "question": "Indicator question text.",
            "topic": "Chronic-disease topic grouping.",
            "yearstart": "Start year for the indicator observation."
          },
          "description": "CDC chronic-disease indicator observations. One row per location, topic, question, stratification, and time period in the bounded Socrata sample.",
          "id": "chronic_disease_indicators",
          "ref": "odd.cdc.latest.chronic_disease_indicators",
          "validations": [
            {
              "compare": "exact",
              "description": "Compare the CDC Chronic Disease Indicators Socrata facade with the direct bounded SODA CSV recipe for a stable Alaska 2023 sample.",
              "direct_sql": "LOAD httpfs;\nSELECT count(*) AS row_count,\n       min(yearstart) AS min_year,\n       max(yearstart) AS max_year,\n       count(DISTINCT topic) AS topics,\n       count(DISTINCT question) AS questions\nFROM read_csv_auto('https://data.cdc.gov/resource/hksd-2xuw.csv?$select=yearstart,locationabbr,topic,question,datavalue,datavalueunit&$where=yearstart=2023%20AND%20locationabbr=%27AK%27&$order=topic,question&$limit=5000');\n",
              "id": "odd.cdc.latest.chronic_disease_indicators",
              "limit": 1,
              "odd_sql": "LOAD open_data_duck;\nATTACH ':memory:' AS odd (TYPE open_data_duck);\nSELECT count(*) AS row_count,\n       min(yearstart) AS min_year,\n       max(yearstart) AS max_year,\n       count(DISTINCT topic) AS topics,\n       count(DISTINCT question) AS questions\nFROM odd.cdc.latest.chronic_disease_indicators;\n",
              "order_by": [
                "row_count"
              ],
              "release": "latest"
            }
          ],
          "warnings": [
            "ODbL license obligations are explicit in the Socrata metadata; preserve attribution and share-alike review when reusing broadly.",
            "Dataset is a wide Socrata table with repeated rows across stratifications; filter by year, location, topic, and question before broad scans.",
            "Facade is a fixed Alaska 2023 validation sample using selected columns, deterministic ordering, and a 5000-row cap until ODD supports parameterized Socrata paging.",
            "Smoke sample: Alaska 2023 rows returned row_count=983, topics=14, questions=48 on 2026-11-23."
          ]
        }
      ]
    },
    {
      "attribution": "Google Open Buildings and Microsoft GlobalMLBuildingFootprints, combined by VIDA; licensed under ODbL v1.0.",
      "authority": "VIDA, combining Google Open Buildings V3 and Microsoft GlobalMLBuildingFootprints",
      "id": "sourcecoop.vida.google-microsoft-open-buildings",
      "license_url": "https://data.source.coop/vida/google-microsoft-open-buildings/README.md",
      "name": "VIDA Google-Microsoft Open Buildings (Source Cooperative GeoParquet)",
      "requirements": {
        "duckdb_extensions": [
          "httpfs",
          "spatial"
        ]
      },
      "source_type": "parquet",
      "status": "candidate",
      "tables": [
        {
          "ask_for": [
            "ISO3 country code",
            "bbox",
            "limit"
          ],
          "description": "Combined Google/Microsoft building footprint polygons. One row per building footprint.",
          "id": "building_footprints",
          "warnings": [
            "Large countries are partitioned; use country and S2 paths to avoid huge scans."
          ]
        }
      ]
    }
  ]
}
)odd_registry";

} // namespace open_data_duck
} // namespace duckdb
