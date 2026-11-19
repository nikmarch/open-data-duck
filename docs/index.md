<p align="center">
  <img src="assets/brand/odd-wordmark.svg" alt="Open Data Duck" width="360">
</p>

# Open Data Duck source index

AI-friendly catalog of public data sources with DuckDB recipes, licenses, and usage hints.

## arcgis

### `arcgis.census.tigerweb.state-county` — U.S. Census TIGERweb state and county layers

Census TIGERweb ArcGIS layers for U.S. state and county boundaries, useful once ArcGIS paging is available in the DuckDB path.

- Status: `connector-blocked`
- Authority: U.S. Census Bureau
- Homepage: https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer
- License: https://www.census.gov/data/developers/about/terms-of-service.html
- Tags: `arcgis`, `census`, `boundaries`, `us`
- Topics: administrative boundaries, counties, states
- Cadence: Census service updates
- AI use cases: join data to county boundaries, inspect state and county geometries
- Caveats: connector is blocked; use REST pagination path until extension install is reliable

### `arcgis.fema.nfhl.flood-hazard-zones` — FEMA National Flood Hazard Layer flood hazard zones

FEMA NFHL ArcGIS layer for flood hazard zones, intended for risk and property-context queries after ArcGIS paging support is stable.

- Status: `connector-blocked`
- Authority: Federal Emergency Management Agency
- Homepage: https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer
- License: https://www.fema.gov/about/openfema/terms-conditions
- Tags: `arcgis`, `fema`, `flood`, `hazards`
- Topics: flood risk, hazards, property context
- Cadence: FEMA service updates
- AI use cases: identify flood hazard zones, enrich property or parcel analysis
- Caveats: not a substitute for official determinations; connector path is not stable yet

### `arcgis.usgs.national-map-contours` — USGS National Map elevation contours

USGS National Map ArcGIS contour layer for elevation-line features and terrain context, pending stable ArcGIS support.

- Status: `connector-blocked`
- Authority: U.S. Geological Survey
- Homepage: https://carto.nationalmap.gov/arcgis/rest/services/contours/MapServer
- License: https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits
- Tags: `arcgis`, `usgs`, `elevation`, `contours`
- Topics: terrain, elevation, topography
- Cadence: USGS service updates
- AI use cases: inspect terrain context, locate contour features, enrich map analysis
- Caveats: connector is blocked; large geometry layers need paging

## ckan

### `ckan.data-gov-au.wyndham-pets` — Data.gov.au Wyndham registered dogs and cats

Australian Government CKAN catalog package with a public CSV distribution of Wyndham registered dog and cat counts by suburb.

- Status: `candidate`
- Authority: Wyndham City Council via data.gov.au
- Homepage: https://data.gov.au/data/dataset/wyndham-registered-dogs-catscsv
- License: https://creativecommons.org/licenses/by/3.0/au/
- Tags: `ckan`, `dcat`, `australia`, `csv`, `animals`
- Topics: open data catalogs, local government, pets
- Cadence: catalog-maintained updates
- AI use cases: test CKAN resource discovery, query a simple government CSV distribution
- Caveats: CKAN is not a DuckDB table function; only directly readable distributions should be marked candidate

## other

### `census.cartographic.county-boundaries` — U.S. Census cartographic county boundary files

Official generalized U.S. county boundary shapefiles from the Census Bureau Cartographic Boundary Files collection, queryable directly from the public zipped shapefile with DuckDB spatial/GDAL virtual file paths.

- Status: `candidate`
- Authority: U.S. Census Bureau Geography Program
- Homepage: https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html
- License: https://www.census.gov/data/developers/about/terms-of-service.html
- Tags: `census`, `boundaries`, `counties`, `shapefile`, `geospatial`
- Topics: administrative boundaries, counties, thematic mapping, fips
- Cadence: annual Census cartographic boundary file releases
- AI use cases: map county-level indicators, join county FIPS codes to generalized boundaries, build thematic maps without TIGERweb paging
- Caveats: generalized for thematic mapping rather than surveying, choose year and scale explicitly, zipped shapefile access requires DuckDB spatial/GDAL virtual paths

### `census.cartographic.tract-boundaries` — U.S. Census cartographic tract boundary files

Official generalized U.S. census tract boundary shapefiles from the Census Bureau Cartographic Boundary Files collection, queryable directly from the public zipped shapefile with DuckDB spatial/GDAL virtual file paths.

- Status: `candidate`
- Authority: U.S. Census Bureau Geography Program
- Homepage: https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html
- License: https://www.census.gov/data/developers/about/terms-of-service.html
- Tags: `census`, `boundaries`, `tracts`, `shapefile`, `geospatial`
- Topics: census tracts, statistical geographies, thematic mapping, geoid, fips
- Cadence: annual Census cartographic boundary file releases
- AI use cases: map tract-level indicators, join tract GEOIDs to ACS estimates, build thematic maps without TIGERweb paging
- Caveats: generalized for thematic mapping rather than surveying, choose year and scale explicitly, national tract files are larger than county files, zipped shapefile access requires DuckDB spatial/GDAL virtual paths

### `usgs.earthquake.realtime-geojson` — USGS realtime earthquake GeoJSON feeds

Official U.S. Geological Survey realtime earthquake summary feeds for recent seismic events, queryable directly from GeoJSON over HTTPS with DuckDB read_json_auto.

- Status: `candidate`
- Authority: U.S. Geological Survey Earthquake Hazards Program
- Homepage: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php
- License: https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits
- Tags: `usgs`, `earthquakes`, `hazards`, `geojson`, `realtime`
- Topics: earthquakes, seismic events, natural hazards, realtime monitoring
- Cadence: feeds update every minute; older events age out by feed window
- AI use cases: list recent earthquakes by magnitude, monitor significant events, map recent seismic activity
- Caveats: rolling feeds are not stable historical snapshots, all_day can be empty during unusually quiet periods, event coordinates are GeoJSON point arrays with longitude latitude depth

### `aws.noaa-ghcn-daily` — NOAA Global Historical Climatology Network Daily

NOAA GHCN Daily station observations in public S3 CSV files for temperature, precipitation, and other daily climate measurements.

- Status: `candidate`
- Authority: NOAA National Centers for Environmental Information
- Homepage: https://registry.opendata.aws/noaa-ghcn/
- License: https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily
- Tags: `aws`, `noaa`, `climate`, `weather`, `csv`
- Topics: daily climate observations, stations, temperature, precipitation
- Cadence: daily and historical updates
- AI use cases: analyze daily station observations, compare precipitation or temperature by year
- Caveats: CSV files are large; filter by year/station/element early

### `aws.noaa-gsod` — NOAA Global Surface Summary of the Day

NOAA GSOD daily weather summaries by station, exposed as public S3 CSV objects queryable with DuckDB httpfs.

- Status: `candidate`
- Authority: NOAA National Centers for Environmental Information
- Homepage: https://registry.opendata.aws/noaa-gsod/
- License: https://www.ncei.noaa.gov/products/land-based-weather-stations
- Tags: `aws`, `noaa`, `weather`, `daily`, `csv`
- Topics: daily weather summaries, stations, temperature
- Cadence: daily and historical updates
- AI use cases: query station daily summaries, compare temperatures by station, join station weather to events
- Caveats: station files are split by year and station; choose a target file before scanning

### `aws.noaa-isd-history` — NOAA Integrated Surface Database station history

NOAA ISD station-history lookup table with station identifiers, names, country/state, and coordinates.

- Status: `candidate`
- Authority: NOAA National Centers for Environmental Information
- Homepage: https://registry.opendata.aws/noaa-isd/
- License: https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database
- Tags: `aws`, `noaa`, `stations`, `lookup`, `csv`
- Topics: weather stations, station metadata, geocoding
- Cadence: periodic metadata updates
- AI use cases: find nearby station IDs, map weather station locations, join station metadata to GSOD or ISD data
- Caveats: metadata lookup only; use observation datasets for measurements

## overture

### `overture.maps.release` — Overture Maps source family

Global open map data releases for places, buildings, transportation, addresses, divisions, and base layers queryable from public S3 with DuckDB httpfs.

- Status: `candidate`
- Authority: Overture Maps Foundation
- Homepage: https://docs.overturemaps.org/getting-data/
- License: https://docs.overturemaps.org/attribution/
- Tags: `maps`, `geospatial`, `places`, `buildings`, `transportation`, `addresses`
- Topics: basemaps, points of interest, buildings, addresses, roads, geocoding
- Cadence: monthly releases
- AI use cases: find places in a bounding box, inspect global building footprints, sample road segments, query address points, compare map releases
- Caveats: large files require tight spatial filters, attribution varies by contributing provider, release paths should be pinned for reproducible workflows

## parquet

### `sourcecoop.vida.google-microsoft-open-buildings` — VIDA Google-Microsoft Open Buildings (Source Cooperative GeoParquet)

VIDA's combined Google and Microsoft global building-footprint dataset, partitioned as public GeoParquet on Source Cooperative for direct DuckDB scans.

- Status: `candidate`
- Authority: VIDA, combining Google Open Buildings V3 and Microsoft GlobalMLBuildingFootprints
- Homepage: https://source.coop/repositories/vida/google-microsoft-open-buildings/description
- License: https://data.source.coop/vida/google-microsoft-open-buildings/README.md
- Tags: `source-cooperative`, `buildings`, `geospatial`, `geoparquet`, `footprints`
- Topics: building footprints, open buildings, country partitions, S2 partitions
- Cadence: source README changelog updates
- AI use cases: query building footprints by country, filter footprints by bounding box, compare footprint source and confidence
- Caveats: large countries are partitioned; use country and S2 paths to avoid huge scans

## socrata

### `socrata.nyc.311-service-requests` — NYC Open Data 311 Service Requests

New York City 311 service-request records from 2020 to present, exposed through the official NYC Open Data Socrata portal with bounded SODA export queries.

- Status: `candidate`
- Authority: City of New York Office of Technology and Innovation via NYC Open Data
- Homepage: https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9
- License: https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCadmin/0-0-0-216807
- Tags: `socrata`, `nyc`, `311`, `service-requests`, `csv`
- Topics: municipal services, civic requests, complaints, open data
- Cadence: daily automated updates
- AI use cases: query recent 311 complaints by borough, inspect service-request categories, test Socrata pagination
- Caveats: large table requires bounded SODA queries, dataset metadata has no explicit license field, use the NYC Open Data law citation for use-policy context

### `socrata.cdc.places-county-2025` — CDC PLACES county health estimates, 2025 release

CDC PLACES model-based county-level estimates for chronic disease outcomes, prevention measures, risk behaviors, disabilities, health status, and health-related social needs, published on the official CDC Socrata portal with bounded SODA export queries.

- Status: `candidate`
- Authority: Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention and Health Promotion, Division of Population Health
- Homepage: https://data.cdc.gov/d/swc5-untb
- License: https://data.cdc.gov/api/views/metadata/v1/swc5-untb
- Tags: `socrata`, `cdc`, `health`, `counties`, `public-domain`, `csv`
- Topics: public health, chronic disease, county estimates, health outcomes, social determinants
- Cadence: annual PLACES release; each release is a separate Socrata dataset id
- AI use cases: compare health measures across counties in a state, join county health estimates to boundary data, inspect confidence limits for a single measure
- Caveats: model-based small-area estimates rather than direct survey counts, each measure appears twice per county so filter datavaluetypeid to AgeAdjPrv or CrdPrv, 229k rows require bounded SODA paging, the dataset id is release-specific

## stac

### `stac.earth-search.aws` — Earth Search STAC API

Element 84 STAC API for cloud-optimized geospatial imagery, especially Sentinel collections hosted in the AWS open data ecosystem.

- Status: `candidate`
- Authority: Element 84 / AWS Open Data ecosystem
- Homepage: https://earth-search.aws.element84.com/v1
- License: https://registry.opendata.aws/sentinel-2-l2a-cogs/
- Tags: `stac`, `imagery`, `aws`, `sentinel`
- Topics: satellite imagery, earth observation, cloud optimized geotiff
- Cadence: collection-specific updates
- AI use cases: discover Sentinel scenes, filter imagery by bounding box and date, inspect asset URLs
- Caveats: license and attribution are collection-specific, assets may be large

### `stac.microsoft.planetary-computer` — Microsoft Planetary Computer STAC API

Microsoft Planetary Computer STAC catalog for environmental, climate, and satellite datasets exposed through a STAC API.

- Status: `candidate`
- Authority: Microsoft Planetary Computer
- Homepage: https://planetarycomputer.microsoft.com/catalog
- License: https://planetarycomputer.microsoft.com/terms
- Tags: `stac`, `imagery`, `climate`, `microsoft`
- Topics: earth observation, climate data, environmental analysis
- Cadence: collection-specific updates
- AI use cases: discover public imagery collections, inspect STAC item assets, build climate-data queries
- Caveats: some assets require signing or Planetary Computer-specific access patterns

### `stac.nasa.lpcloud` — NASA LP DAAC LPCLOUD STAC catalog

NASA LP DAAC STAC catalog for land processes data products served through Earthdata/CMR endpoints.

- Status: `candidate`
- Authority: NASA Land Processes Distributed Active Archive Center
- Homepage: https://cmr.earthdata.nasa.gov/stac/LPCLOUD/
- License: https://www.earthdata.nasa.gov/engage/open-data-services-and-software/data-and-information-policy
- Tags: `stac`, `nasa`, `land`, `earthdata`
- Topics: land processes, remote sensing, NASA earth science
- Cadence: product-specific updates
- AI use cases: find LP DAAC products, inspect land remote-sensing assets, cite NASA datasets
- Caveats: some downstream assets may require Earthdata access workflows
