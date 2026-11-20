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
- Tables:
  - `county_boundaries`: TIGERweb state/county boundary layer features. One row per ArcGIS boundary feature.
    - Ask for: state or county, fields, whether geometry is needed
    - Warnings: Connector is blocked; use REST pagination until ArcGIS support is stable.
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
- Tables:
  - `flood_hazard_zones`: FEMA NFHL flood hazard zone features. One row per flood hazard zone feature.
    - Ask for: bbox or jurisdiction, fields, whether geometry is needed
    - Warnings: Not a substitute for official determinations; connector path is not stable yet.
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
- Tables:
  - `contours`: USGS National Map elevation contour line features. One row per contour segment feature.
    - Ask for: bbox, contour interval or elevation need, fields
    - Warnings: Connector is blocked; large geometry layers need paging.
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
- Tables:
  - `wyndham_pet_registrations`: Wyndham registered dog and cat counts. One row per suburb/count record in the public CSV distribution.
    - Ask for: suburb or animal type
    - Warnings: CKAN is discovery metadata; query the direct readable CSV distribution.
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
- Tables:
  - `county_20m` (`odd.census.latest.county_20m`): Generalized U.S. county polygons at 20m scale. One row per county or county-equivalent feature.
    - Ask for: year, scale, state filter, GEOID join key
    - Warnings: Generalized for thematic mapping, not surveying.
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
- Tables:
  - `tract_5m` (`odd.census.latest.tract_5m`): Generalized U.S. census tract polygons at 5m scale. One row per census tract feature.
    - Ask for: year, scale, state filter, tract GEOID join key
    - Warnings: National tract files are larger; filter by state when possible.
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
- Tables:
  - `earthquake_events`: Recent USGS earthquake event features. One row per reported seismic event in the selected rolling feed.
    - Ask for: feed window, magnitude threshold, bbox or region, limit
    - Warnings: Rolling feeds are not stable historical snapshots.
    - Columns: mag: Earthquake magnitude.; place: Human-readable event location.; time: Event time in epoch milliseconds.; geometry: GeoJSON point with longitude, latitude, and depth.
- AI use cases: list recent earthquakes by magnitude, monitor significant events, map recent seismic activity
- Caveats: rolling feeds are not stable historical snapshots, all_day can be empty during unusually quiet periods, event coordinates are GeoJSON point arrays with longitude latitude depth

### `worldbank.wdi.indicators` — World Bank World Development Indicators API

Official World Bank Indicators API access to World Development Indicators time-series development data, queryable as public JSON over HTTPS with DuckDB httpfs and JSON functions.

- Status: `candidate`
- Authority: World Bank Group
- Homepage: https://api.worldbank.org/v2/
- License: https://www.worldbank.org/ext/en/legal/terms-conditions/datasets
- Tags: `world-bank`, `wdi`, `indicators`, `development`, `json`
- Topics: development indicators, population, economy, health, education, country time series
- Cadence: API metadata reports source-specific last updated dates
- Tables:
  - `indicators`: World Bank indicator observations. One row per country, indicator, and year.
    - Ask for: country code, indicator id, year range
    - Warnings: Values may be null; API responses use a JSON envelope.
- AI use cases: query country indicator histories, compare development indicators across years, pull WDI time series into DuckDB
- Caveats: API responses use a two-element JSON envelope, some indicators can have null values, some third-party datasets or indicators may carry different metadata terms

### `bls.cpi.timeseries` — BLS Consumer Price Index time series API

Official U.S. Bureau of Labor Statistics Public Data API access to Consumer Price Index time-series observations, queryable as public JSON over HTTPS with DuckDB httpfs.

- Status: `candidate`
- Authority: U.S. Bureau of Labor Statistics
- Homepage: https://www.bls.gov/developers/home.htm
- License: https://www.bls.gov/developers/termsOfService.htm
- Tags: `bls`, `cpi`, `inflation`, `labor-statistics`, `json`
- Topics: consumer price index, inflation, economic indicators, monthly time series
- Cadence: CPI series are updated on the BLS release schedule; API responses reflect published BLS time-series data
- Tables:
  - `cpi_observations`: BLS CPI time-series observations. One row per BLS series and period.
    - Ask for: series id, start year, end year
    - Warnings: Values are returned as strings and should be cast before numeric analysis.
- AI use cases: pull recent CPI observations, compare CPI series, build inflation trend examples in DuckDB
- Caveats: keyless public access should stay to small single-series requests, registered v2 API access is better for multi-series or heavier usage, values are returned as strings and should be cast

### `openfda.food.enforcement-reports` — FDA openFDA food enforcement recall reports

Official openFDA food enforcement recall reports from FDA Recall Enterprise System records, queryable as a public JSON API with DuckDB httpfs.

- Status: `candidate`
- Authority: U.S. Food and Drug Administration openFDA
- Homepage: https://open.fda.gov/apis/food/enforcement/
- License: https://open.fda.gov/license/
- Tags: `fda`, `openfda`, `recalls`, `food-safety`, `json`, `public-domain`
- Topics: food recalls, enforcement reports, product safety, public health
- Cadence: openFDA documents food enforcement data updates weekly
- Tables:
  - `food_enforcement_reports`: FDA food enforcement recall reports. One row per public recall report returned from the openFDA food enforcement endpoint after unnesting the JSON results envelope.
    - Ask for: classification, status, date window, product or firm search term, limit
    - Warnings: API keys are optional but keyless access can be rate-limited; responses are nested JSON envelopes, so unnest results before treating reports as rows.
    - Columns: recall_number: FDA recall number for the enforcement report.; status: Recall status, such as Ongoing, Completed, or Terminated.; classification: Recall classification, such as Class I, Class II, or Class III.; product_description: Product description text from the recall report.; recalling_firm: Firm responsible for the recall.; report_date: FDA report date as YYYYMMDD text.
- AI use cases: list recent food recalls, filter recalls by classification or status, search product descriptions or recalling firms
- Caveats: openFDA warns the API is not validated for clinical or production use, keyless requests have lower rate limits, query the nested results array rather than the response envelope

### `treasury.fiscaldata.debt-to-penny` — U.S. Treasury Fiscal Data Debt to the Penny API

Official Bureau of the Fiscal Service daily total public debt outstanding records from the Treasury Fiscal Data API, queryable as gzipped CSV over HTTPS with DuckDB httpfs.

- Status: `candidate`
- Authority: U.S. Department of the Treasury, Bureau of the Fiscal Service
- Homepage: https://fiscaldata.treasury.gov/datasets/debt-to-the-penny/debt-to-the-penny
- License: https://catalog.data.gov/dataset/debt-to-the-penny
- Tags: `treasury`, `fiscal-data`, `debt`, `public-debt`, `csv`
- Topics: federal debt, public debt outstanding, treasury, fiscal data, daily time series
- Cadence: daily on Treasury Fiscal Data publication schedule
- Tables:
  - `debt_observations`: U.S. Treasury daily public debt outstanding records. One row per record date.
    - Ask for: date window, debt field, limit
    - Warnings: Fiscal Data CSV responses are gzipped; use compression = 'gzip'.
- AI use cases: pull recent debt-to-the-penny observations, monitor daily public debt changes, join federal debt levels into economic time-series analysis
- Caveats: Fiscal Data CSV responses are gzipped even though the URL has no .gz suffix, so DuckDB queries must pass compression = 'gzip'; amounts are large dollar values and should be handled as numeric fields

### `noaa.ncei.storm-events` — NOAA NCEI Storm Events bulk CSV files

Official NOAA National Centers for Environmental Information Storm Events Database bulk CSV exports for severe weather events, fatalities, and locations, queryable from public HTTPS gzip files with DuckDB httpfs.

- Status: `candidate`
- Authority: NOAA National Centers for Environmental Information
- Homepage: https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/
- License: https://www.noaa.gov/information-policies-and-instructions/copyrights-and-credits
- Tags: `noaa`, `ncei`, `storms`, `weather`, `hazards`, `csv`
- Topics: severe weather, storm reports, tornadoes, hail, wind, fatalities
- Cadence: bulk files are revised with new creation-date suffixes as NOAA/NCEI republishes each data year
- Tables:
  - `storm_events_details` (`odd.noaa.latest.storm_events_details`): NOAA Storm Events detail rows. One row per reported storm event.
    - Ask for: year, state, event type, limit
    - Warnings: Files are revised with creation-date suffixes; pin year for reproducible examples.
  - `storm_events_fatalities` (`odd.noaa.latest.storm_events_fatalities`): NOAA Storm Events fatality rows. One row per fatality associated with a storm event.
    - Ask for: year, state or event id, limit
    - Warnings: Join to details by event_id for event context.
  - `storm_events_locations` (`odd.noaa.latest.storm_events_locations`): NOAA Storm Events location rows. One row per location attached to a storm event.
    - Ask for: year, state or event id, limit
    - Warnings: Join to details by event_id for event context.
- AI use cases: query storm events by state and event type, inspect tornado or hail reports by year, join event details to fatalities or locations
- Caveats: file names include both data year and NOAA creation-date suffix, latest table discovery scans the directory listing to choose the newest suffix per file family, CSV files can be large

### `aws.noaa-ghcn-daily` — NOAA Global Historical Climatology Network Daily

NOAA GHCN Daily station observations in public S3 CSV files for temperature, precipitation, and other daily climate measurements.

- Status: `candidate`
- Authority: NOAA National Centers for Environmental Information
- Homepage: https://registry.opendata.aws/noaa-ghcn/
- License: https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily
- Tags: `aws`, `noaa`, `climate`, `weather`, `csv`
- Topics: daily climate observations, stations, temperature, precipitation
- Cadence: daily and historical updates
- Tables:
  - `ghcn_daily` (`odd.noaa.latest.ghcn_daily`): GHCN Daily station observations. One row per station, date, and observed climate element.
    - Ask for: year, station id, climate element
    - Warnings: CSV files are large; filter by year/station/element early.
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
- Tables:
  - `daily_summaries`: NOAA GSOD daily station weather summaries. One row per station-day summary.
    - Ask for: station id, year, weather fields
    - Warnings: Station files are split by year and station.
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
- Tables:
  - `station_history`: NOAA ISD station metadata. One row per weather station history record.
    - Ask for: country, state, station name, nearby place
    - Warnings: Metadata lookup only; use observation datasets for measurements.
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
- Tables:
  - `place` (`odd.overturemaps.latest.place`): Places and points of interest. One row per Overture place feature.
    - Ask for: bbox or area, release or latest, limit
    - Warnings: Large global table; always use tight bbox filters.
    - Columns: id: Stable Overture feature id.; names: Nested names object; primary/common/local names are not plain text columns.; bbox: Bounding box for fast spatial prefilters.; geometry: Place geometry.
  - `building` (`odd.overturemaps.latest.building`): Building footprint polygons. One row per Overture building feature.
    - Ask for: bbox or area, release or latest, limit
    - Warnings: Large global table; always use tight bbox filters.
  - `segment` (`odd.overturemaps.latest.segment`): Transportation road/path segments. One row per Overture segment feature.
    - Ask for: bbox or area, release or latest, limit
    - Warnings: Large global table; always use tight bbox filters.
  - `address` (`odd.overturemaps.latest.address`): Address point/record features. One row per Overture address feature.
    - Ask for: bbox or area, release or latest, limit
    - Warnings: Large global table; always use tight bbox filters.
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
- Tables:
  - `building_footprints`: Combined Google/Microsoft building footprint polygons. One row per building footprint.
    - Ask for: ISO3 country code, bbox, limit
    - Warnings: Large countries are partitioned; use country and S2 paths to avoid huge scans.
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
- Tables:
  - `service_requests`: NYC 311 service request records. One row per 311 request.
    - Ask for: date range, borough, complaint type, limit
    - Warnings: Large table requires bounded SODA queries with select/order/limit.
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
- Tables:
  - `county_health_estimates`: CDC PLACES county health estimate rows. One row per county, measure, and data-value type.
    - Ask for: state, measure id, age-adjusted or crude prevalence
    - Warnings: Model-based estimates; filter datavaluetypeid to avoid duplicate measure rows.
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
- Tables:
  - `stac_items`: STAC item search results from Earth Search. One row per imagery item returned by the STAC API.
    - Ask for: collection, bbox, date range, cloud cover, limit
    - Warnings: Assets can be large; inspect metadata before reading imagery assets.
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
- Tables:
  - `stac_items`: STAC item search results from Microsoft Planetary Computer. One row per catalog item returned by the STAC API.
    - Ask for: collection, bbox, date range, limit
    - Warnings: Some assets require Planetary Computer signing or access patterns.
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
- Tables:
  - `stac_items`: NASA LP DAAC STAC item metadata. One row per land-processes product item returned by the STAC API.
    - Ask for: product or collection, bbox or area, date range, limit
    - Warnings: Some downstream assets may require Earthdata access workflows.
- AI use cases: find LP DAAC products, inspect land remote-sensing assets, cite NASA datasets
- Caveats: some downstream assets may require Earthdata access workflows
