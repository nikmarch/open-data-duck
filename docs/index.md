<p align="center">
  <img src="assets/brand/odd-wordmark.svg" alt="Open Data Duck" width="360">
</p>

# Open Data Duck source index

Table-first catalog of public data sources with legal metadata and executable ODD-vs-direct validation pairs.

## arcgis

### `arcgis.census.tigerweb.state-county` — U.S. Census TIGERweb state and county layers

- Status: `connector-blocked`
- Authority: U.S. Census Bureau
- License: https://www.census.gov/data/developers/about/terms-of-service.html
- DuckDB extensions: arcgis
- Tables:
  - `county_boundaries`: TIGERweb state/county boundary layer features. One row per ArcGIS boundary feature.
    - Ask for: state or county, fields, whether geometry is needed
    - Warnings: Connector is blocked; use REST pagination until ArcGIS support is stable.

### `arcgis.fema.nfhl.flood-hazard-zones` — FEMA National Flood Hazard Layer flood hazard zones

- Status: `connector-blocked`
- Authority: Federal Emergency Management Agency
- License: https://www.fema.gov/about/openfema/terms-conditions
- DuckDB extensions: arcgis
- Tables:
  - `flood_hazard_zones`: FEMA NFHL flood hazard zone features. One row per flood hazard zone feature.
    - Ask for: bbox or jurisdiction, fields, whether geometry is needed
    - Warnings: Not a substitute for official determinations; connector path is not stable yet.

### `arcgis.usgs.national-map-contours` — USGS National Map elevation contours

- Status: `connector-blocked`
- Authority: U.S. Geological Survey
- License: https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits
- DuckDB extensions: arcgis
- Tables:
  - `contours`: USGS National Map elevation contour line features. One row per contour segment feature.
    - Ask for: bbox, contour interval or elevation need, fields
    - Warnings: Connector is blocked; large geometry layers need paging.

## ckan

### `ckan.data-gov-au.wyndham-pets` — Data.gov.au Wyndham registered dogs and cats

- Status: `candidate`
- Authority: Wyndham City Council via data.gov.au
- License: https://creativecommons.org/licenses/by/3.0/au/
- DuckDB extensions: httpfs
- Tables:
  - `wyndham_pet_registrations`: Wyndham registered dog and cat counts. One row per suburb/count record in the public CSV distribution.
    - Ask for: suburb or animal type
    - Warnings: CKAN is discovery metadata; query the direct readable CSV distribution.

## other

### `naturalearth.admin0-countries` — Natural Earth Admin 0 countries

- Status: `candidate`
- Authority: Natural Earth
- License: https://www.naturalearthdata.com/about/terms-of-use/
- DuckDB extensions: spatial
- Discovery namespace: `odd.naturalearth.latest`
- Tables:
  - `countries_110m` (`odd.naturalearth.latest.countries_110m`): Generalized Admin 0 country polygons at 1:110m scale. One row per country or country-like map unit in the Natural Earth countries layer.
    - Ask for: scale, whether de facto boundaries are acceptable, country or sovereignty fields, limit
    - Warnings: Natural Earth is cartographic generalized data for small-scale maps, not legal or survey boundaries., The Admin 0 countries layer uses de facto boundaries by default; choose a different Natural Earth Admin 0 product if map units, sovereignty, or disputed areas matter.
    - Columns: NAME: Display name for the country or map unit.; ISO_A3: Three-letter ISO-style country code where assigned.; CONTINENT: Continent grouping from Natural Earth.; POP_EST: Estimated population attribute from Natural Earth.; geom: Generalized polygon or multipolygon geometry.
    - Validation: `odd.naturalearth.latest.countries_110m`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SELECT NAME, ISO_A3, CONTINENT, POP_EST
      FROM odd.naturalearth.latest.countries_110m
      WHERE ISO_A3 IN ('USA', 'UZB')
      ORDER BY ISO_A3;
      ```

### `census.cartographic.county-boundaries` — U.S. Census cartographic county boundary files

- Status: `candidate`
- Authority: U.S. Census Bureau Geography Program
- License: https://www.census.gov/data/developers/about/terms-of-service.html
- DuckDB extensions: spatial
- Discovery namespace: `odd.census.latest`
- Tables:
  - `county_20m` (`odd.census.latest.county_20m`): Generalized U.S. county polygons at 20m scale. One row per county or county-equivalent feature.
    - Ask for: year, scale, state filter, GEOID join key
    - Warnings: Generalized for thematic mapping, not surveying.
    - Validation: `odd.census.latest.county_20m`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE census_cartographic_year = '2025';
      SELECT GEOID, NAME, STATE_NAME
      FROM odd.census.latest.county_20m
      WHERE STATEFP = '02'
      ORDER BY GEOID
      LIMIT 10;
      ```

### `census.cartographic.tract-boundaries` — U.S. Census cartographic tract boundary files

- Status: `candidate`
- Authority: U.S. Census Bureau Geography Program
- License: https://www.census.gov/data/developers/about/terms-of-service.html
- DuckDB extensions: spatial
- Discovery namespace: `odd.census.latest`
- Tables:
  - `tract_5m` (`odd.census.latest.tract_5m`): Generalized U.S. census tract polygons at 5m scale. One row per census tract feature.
    - Ask for: year, scale, state filter, tract GEOID join key
    - Warnings: National tract files are larger; filter by state when possible.
    - Validation: `odd.census.latest.tract_5m`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE census_cartographic_year = '2025';
      SELECT GEOID, NAME, STATEFP, COUNTYFP
      FROM odd.census.latest.tract_5m
      WHERE STATEFP = '02'
      ORDER BY GEOID
      LIMIT 10;
      ```

### `nhtsa.vehicle-safety` — NHTSA vehicle safety recalls and ratings APIs

- Status: `candidate`
- Authority: National Highway Traffic Safety Administration, U.S. Department of Transportation
- License: https://www.nhtsa.gov/about-nhtsa/terms-use
- DuckDB extensions: httpfs
- Tables:
  - `recalls_by_vehicle`: NHTSA recall campaign results for a requested model year, make, and model. One row per recall campaign result.
    - Ask for: model year, make, model, limit
    - Warnings: Parameterized API endpoint; preserve model year, make, and model filters instead of treating it as a full-table scan.
    - Columns: NHTSACampaignNumber: NHTSA recall campaign identifier.; ReportReceivedDate: Date NHTSA received the campaign report.; Component: Vehicle component affected by the recall.; Summary: Long recall summary text.
  - `safety_rating_variants`: NHTSA safety-rating vehicle variants for a requested model year, make, and model. One row per returned vehicle variant.
    - Ask for: model year, make, model, limit
    - Warnings: Parameterized API endpoint; use the returned VehicleId for rating-detail lookups.
    - Columns: VehicleId: Identifier used by NHTSA rating-detail lookups.; VehicleDescription: Human-readable vehicle variant description.

### `usgs.earthquake.realtime-geojson` — USGS realtime earthquake GeoJSON feeds

- Status: `candidate`
- Authority: U.S. Geological Survey Earthquake Hazards Program
- License: https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits
- DuckDB extensions: httpfs
- Tables:
  - `earthquake_events`: Recent USGS earthquake event features. One row per reported seismic event in the selected rolling feed.
    - Ask for: feed window, magnitude threshold, bbox or region, limit
    - Warnings: Rolling feeds are not stable historical snapshots.
    - Columns: mag: Earthquake magnitude.; place: Human-readable event location.; time: Event time in epoch milliseconds.; geometry: GeoJSON point with longitude, latitude, and depth.

### `usgs.nwis.instantaneous-values` — USGS NWIS instantaneous water values API

- Status: `candidate`
- Authority: U.S. Geological Survey Water Data for the Nation
- License: https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits
- DuckDB extensions: httpfs
- Tables:
  - `instantaneous_values`: USGS NWIS instantaneous observations. One row per timestamped monitoring-site and parameter observation after flattening the WaterML JSON timeSeries payload.
    - Ask for: site number, parameter code, start datetime, end datetime, site status, whether provisional operational values are acceptable
    - Warnings: Responses are nested by time series and values arrays; unnest timeSeries and values before treating observations as rows., Large multi-site or multi-parameter requests should be bounded by date range., Instantaneous operational values can be provisional and not fully quality-assured.
    - Columns: site_no: USGS monitoring site number such as 01646500.; parameter_cd: USGS parameter code such as 00060 for streamflow.; observed_at: Observation timestamp returned by the service, generally UTC when date ranges are supplied without local timezone offsets.; observed_value: Observation value cast to DOUBLE from the nested JSON string value.; qualifiers: USGS value qualifiers such as approved or provisional status flags.

### `worldbank.wdi.indicators` — World Bank World Development Indicators API

- Status: `candidate`
- Authority: World Bank Group
- License: https://www.worldbank.org/ext/en/legal/terms-conditions/datasets
- DuckDB extensions: httpfs
- Tables:
  - `indicators`: World Bank indicator observations. One row per country, indicator, and year.
    - Ask for: country code, indicator id, year range
    - Warnings: Values may be null; API responses use a JSON envelope.

### `bls.cpi.timeseries` — BLS Consumer Price Index time series API

- Status: `candidate`
- Authority: U.S. Bureau of Labor Statistics
- License: https://www.bls.gov/developers/termsOfService.htm
- DuckDB extensions: httpfs
- Tables:
  - `cpi_observations`: BLS CPI time-series observations. One row per BLS series and period.
    - Ask for: series id, start year, end year
    - Warnings: Values are returned as strings and should be cast before numeric analysis.

### `openfda.food.enforcement-reports` — FDA openFDA food enforcement recall reports

- Status: `candidate`
- Authority: U.S. Food and Drug Administration openFDA
- License: https://open.fda.gov/license/
- DuckDB extensions: httpfs
- Tables:
  - `food_enforcement_reports`: FDA food enforcement recall reports. One row per public recall report returned from the openFDA food enforcement endpoint after unnesting the JSON results envelope.
    - Ask for: classification, status, date window, product or firm search term, limit
    - Warnings: API keys are optional but keyless access can be rate-limited; responses are nested JSON envelopes, so unnest results before treating reports as rows.
    - Columns: recall_number: FDA recall number for the enforcement report.; status: Recall status, such as Ongoing, Completed, or Terminated.; classification: Recall classification, such as Class I, Class II, or Class III.; product_description: Product description text from the recall report.; recalling_firm: Firm responsible for the recall.; report_date: FDA report date as YYYYMMDD text.

### `treasury.fiscaldata.debt-to-penny` — U.S. Treasury Fiscal Data Debt to the Penny API

- Status: `candidate`
- Authority: U.S. Department of the Treasury, Bureau of the Fiscal Service
- License: https://catalog.data.gov/dataset/debt-to-the-penny
- DuckDB extensions: httpfs
- Tables:
  - `debt_observations`: U.S. Treasury daily public debt outstanding records. One row per record date.
    - Ask for: date window, debt field, limit
    - Warnings: Fiscal Data CSV responses are gzipped; use compression = 'gzip'.

### `wri.global-power-plant-database` — WRI Global Power Plant Database

- Status: `candidate`
- Authority: World Resources Institute
- License: https://raw.githubusercontent.com/wri/global-power-plant-database/master/README.md
- DuckDB extensions: httpfs
- Discovery namespace: `odd.wri.latest`
- Tables:
  - `global_power_plants` (`odd.wri.latest.global_power_plants`): Global power plant records. One row per plant with country, fuel, capacity, geolocation, ownership/source metadata, and generation fields.
    - Ask for: country or countries, fuel type, capacity threshold, whether stale 2021/2022-era data is acceptable, limit
    - Warnings: WRI says the project is not currently maintained and has no planned updates as of early 2022; use it as a broad reference index, not a freshness-sensitive operational source., The integrated database combines national and manual sources, so inspect source-year and lineage fields before comparing countries.
    - Columns: country: ISO-like three-letter country code used by the dataset.; country_long: Country display name.; name: Power plant name.; primary_fuel: Primary fuel category.; capacity_mw: Plant capacity in megawatts.; latitude: Plant latitude.; longitude: Plant longitude.; year_of_capacity_data: Year attached to the reported capacity data where available.
    - Validation: `odd.wri.latest.global_power_plants`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE wri_global_power_plants_release = 'v1x3x0';
      SELECT country, count(*) AS plants, round(sum(capacity_mw), 1) AS capacity_mw
      FROM odd.wri.latest.global_power_plants
      WHERE country IN ('USA', 'UZB')
      GROUP BY country
      ORDER BY country;
      ```

### `noaa.ncei.storm-events` — NOAA NCEI Storm Events bulk CSV files

- Status: `candidate`
- Authority: NOAA National Centers for Environmental Information
- License: https://www.noaa.gov/information-policies-and-instructions/copyrights-and-credits
- DuckDB extensions: httpfs
- Discovery namespace: `odd.noaa.latest`
- Tables:
  - `storm_events_details` (`odd.noaa.latest.storm_events_details`): NOAA Storm Events detail rows. One row per reported storm event.
    - Ask for: year, state, event type, limit
    - Warnings: Files are revised with creation-date suffixes; pin year for reproducible examples.
    - Validation: `odd.noaa.latest.storm_events_details`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE noaa_storm_events_year = '2024';
      SELECT event_id, state, event_type, begin_date_time, cz_name
      FROM odd.noaa.latest.storm_events_details
      WHERE event_type IS NOT NULL
      ORDER BY event_id
      LIMIT 10;
      ```
  - `storm_events_fatalities` (`odd.noaa.latest.storm_events_fatalities`): NOAA Storm Events fatality rows. One row per fatality associated with a storm event.
    - Ask for: year, state or event id, limit
    - Warnings: Join to details by event_id for event context.
    - Validation: `odd.noaa.latest.storm_events_fatalities`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE noaa_storm_events_year = '2024';
      SELECT fatality_id, event_id, fatality_type, fatality_date, fatality_age
      FROM odd.noaa.latest.storm_events_fatalities
      WHERE event_id IS NOT NULL
      ORDER BY fatality_id
      LIMIT 10;
      ```
  - `storm_events_locations` (`odd.noaa.latest.storm_events_locations`): NOAA Storm Events location rows. One row per location attached to a storm event.
    - Ask for: year, state or event id, limit
    - Warnings: Join to details by event_id for event context.
    - Validation: `odd.noaa.latest.storm_events_locations`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE noaa_storm_events_year = '2024';
      SELECT event_id, location_index, location, latitude, longitude
      FROM odd.noaa.latest.storm_events_locations
      WHERE event_id IS NOT NULL
      ORDER BY event_id, location_index
      LIMIT 10;
      ```

### `noaa.coops.water-level-observations` — NOAA CO-OPS water-level observations API

- Status: `candidate`
- Authority: NOAA National Ocean Service Center for Operational Oceanographic Products and Services
- License: https://www.noaa.gov/information-policies-and-instructions/copyrights-and-credits
- DuckDB extensions: httpfs
- Discovery namespace: `odd.noaa_coops.latest`
- Tables:
  - `hourly_heights` (`odd.noaa_coops.latest.hourly_heights`): NOAA CO-OPS hourly water-level observations. One row per timestamped station observation for the selected product, datum, time zone, and units.
    - Ask for: station id, begin date, end date, water-level product, datum, time zone, units, limit
    - Warnings: Parameterized API endpoint; preserve station, date range, product, datum, time zone, units, and application identifier instead of treating it as a full-table scan., CO-OPS products have product-specific date-range limits and water-level products require a datum., Preliminary and verified products differ; keep requests bounded and cite the selected station and retrieval endpoint/date., Validation facade is a small fixed smoke sample: station=8518750, product=hourly_height, datum=MLLW, begin_date=20200101, end_date=20200102, time_zone=gmt, units=metric; expected result is 48 hourly rows.
    - Columns: Date Time: Observation timestamp in the requested time zone.; Water Level: Water-level height in the requested units and datum.; Sigma: Standard deviation for the observation where provided.; I: Inferred flag returned by CO-OPS.; L: Flat tolerance flag returned by CO-OPS.
    - Validation: `odd.noaa_coops.latest.hourly_heights`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SELECT count(*) AS row_count,
             min("Date Time") AS first_observation,
             max("Date Time") AS last_observation
      FROM odd.noaa_coops.latest.hourly_heights;
      ```

### `aws.noaa-ghcn-daily` — NOAA Global Historical Climatology Network Daily

- Status: `candidate`
- Authority: NOAA National Centers for Environmental Information
- License: https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily
- DuckDB extensions: httpfs
- Discovery namespace: `odd.noaa.latest`
- Tables:
  - `ghcn_daily` (`odd.noaa.latest.ghcn_daily`): GHCN Daily station observations. One row per station, date, and observed climate element.
    - Ask for: year, station id, climate element
    - Warnings: CSV files are large; filter by year/station/element early.
    - Validation: `odd.noaa.latest.ghcn_daily`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE noaa_ghcn_year = '2024';
      SELECT id, date, element, data_value
      FROM odd.noaa.latest.ghcn_daily
      WHERE id IS NOT NULL
      ORDER BY id, date, element
      LIMIT 10;
      ```

### `aws.noaa-gsod` — NOAA Global Surface Summary of the Day

- Status: `candidate`
- Authority: NOAA National Centers for Environmental Information
- License: https://www.ncei.noaa.gov/products/land-based-weather-stations
- DuckDB extensions: httpfs
- Tables:
  - `daily_summaries`: NOAA GSOD daily station weather summaries. One row per station-day summary.
    - Ask for: station id, year, weather fields
    - Warnings: Station files are split by year and station.

### `aws.noaa-isd-history` — NOAA Integrated Surface Database station history

- Status: `candidate`
- Authority: NOAA National Centers for Environmental Information
- License: https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database
- DuckDB extensions: httpfs
- Tables:
  - `station_history`: NOAA ISD station metadata. One row per weather station history record.
    - Ask for: country, state, station name, nearby place
    - Warnings: Metadata lookup only; use observation datasets for measurements.

## overture

### `overture.maps.release` — Overture Maps source family

- Status: `candidate`
- Authority: Overture Maps Foundation
- License: https://docs.overturemaps.org/attribution/
- DuckDB extensions: httpfs
- Discovery namespace: `odd.overturemaps.latest`
- Tables:
  - `place` (`odd.overturemaps.latest.place`): Places and points of interest. One row per Overture place feature.
    - Ask for: bbox or area, release or latest, limit
    - Warnings: Large global table; always use tight bbox filters.
    - Columns: id: Stable Overture feature id.; names: Nested names object; primary/common/local names are not plain text columns.; bbox: Bounding box for fast spatial prefilters.; geometry: Place geometry.
    - Validation: `odd.overturemaps.latest.place`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SELECT id, names, bbox
      FROM odd.overturemaps.latest.place
      WHERE bbox.xmin <= 66.981
        AND bbox.xmax >= 66.976
        AND bbox.ymin <= 39.657
        AND bbox.ymax >= 39.652
      ORDER BY id
      LIMIT 10;
      ```
    - Validation: `odd.overturemaps.x2026x10x21.place`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SELECT id, names, bbox
      FROM odd.overturemaps.x2026x10x21.place
      WHERE bbox.xmin <= 66.981
        AND bbox.xmax >= 66.976
        AND bbox.ymin <= 39.657
        AND bbox.ymax >= 39.652
      ORDER BY id
      LIMIT 10;
      ```
  - `building` (`odd.overturemaps.latest.building`): Building footprint polygons. One row per Overture building feature.
    - Ask for: bbox or area, release or latest, limit
    - Warnings: Large global table; always use tight bbox filters.
    - Validation: `odd.overturemaps.latest.building`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE overture_release = '2026-10-21.0';
      SET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';
      SELECT id, bbox
      FROM odd.overturemaps.latest.building
      WHERE bbox.xmin <= 66.981
        AND bbox.xmax >= 66.976
        AND bbox.ymin <= 39.657
        AND bbox.ymax >= 39.652
      ORDER BY id
      LIMIT 10;
      ```
  - `segment` (`odd.overturemaps.latest.segment`): Transportation road/path segments. One row per Overture segment feature.
    - Ask for: bbox or area, release or latest, limit
    - Warnings: Large global table; always use tight bbox filters.
    - Validation: `odd.overturemaps.latest.segment`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE overture_release = '2026-10-21.0';
      SET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';
      SELECT id, bbox
      FROM odd.overturemaps.latest.segment
      WHERE bbox.xmin <= 66.981
        AND bbox.xmax >= 66.976
        AND bbox.ymin <= 39.657
        AND bbox.ymax >= 39.652
      ORDER BY id
      LIMIT 10;
      ```
  - `address` (`odd.overturemaps.latest.address`): Address point/record features. One row per Overture address feature.
    - Ask for: bbox or area, release or latest, limit
    - Warnings: Large global table; always use tight bbox filters.
    - Validation: `odd.overturemaps.latest.address`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE overture_release = '2026-10-21.0';
      SET VARIABLE overture_s3_base = 's3://overturemaps-us-west-2';
      SELECT id, bbox
      FROM odd.overturemaps.latest.address
      WHERE bbox.xmin <= 66.981
        AND bbox.xmax >= 66.976
        AND bbox.ymin <= 39.657
        AND bbox.ymax >= 39.652
      ORDER BY id
      LIMIT 10;
      ```

## parquet

### `fema.openfema.disaster-declarations` — FEMA OpenFEMA Disaster Declarations Summaries

- Status: `candidate`
- Authority: Federal Emergency Management Agency OpenFEMA
- License: https://www.fema.gov/about/openfema/terms-conditions
- DuckDB extensions: httpfs
- Discovery namespace: `odd.fema.latest`
- Tables:
  - `disaster_declarations` (`odd.fema.latest.disaster_declarations`): FEMA disaster declaration summary records. One row per federally declared disaster declaration and designated geographic area from 1953 forward.
    - Ask for: state or territory, declaration date or fiscal year range, incident type, declaration type, assistance program flags, limit
    - Warnings: FEMA describes OpenFEMA as raw, unedited NEMIS data; historical/manual records can contain a small percentage of human error., County data is not available before 1964, Fire Management records are partial, and Tribal Nation declarations are currently included in state data.
    - Columns: disasterNumber: FEMA disaster declaration number.; state: Two-letter state, territory, or Tribal Nation state-code grouping.; declarationDate: Date FEMA declared the disaster.; incidentType: Incident category such as Flood, Fire, Hurricane, or Earthquake.; designatedArea: County, parish, borough, census area, statewide area, or Tribal area covered by the declaration.; declarationType: FEMA declaration type code.; ihProgramDeclared: Whether the Individual and Households Program was declared for the record.; paProgramDeclared: Whether Public Assistance was declared for the record.; hmProgramDeclared: Whether Hazard Mitigation was declared for the record.
    - Validation: `odd.fema.latest.disaster_declarations`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SET VARIABLE fema_disaster_declarations_release = 'v2';
      SELECT state, count(*) AS declarations, min(disasterNumber) AS first_disaster, max(disasterNumber) AS latest_disaster
      FROM odd.fema.latest.disaster_declarations
      WHERE state IN ('AK', 'CA')
      GROUP BY state
      ORDER BY state;
      ```

### `sourcecoop.vida.google-microsoft-open-buildings` — VIDA Google-Microsoft Open Buildings (Source Cooperative GeoParquet)

- Status: `candidate`
- Authority: VIDA, combining Google Open Buildings V3 and Microsoft GlobalMLBuildingFootprints
- License: https://data.source.coop/vida/google-microsoft-open-buildings/README.md
- DuckDB extensions: httpfs, spatial
- Tables:
  - `building_footprints`: Combined Google/Microsoft building footprint polygons. One row per building footprint.
    - Ask for: ISO3 country code, bbox, limit
    - Warnings: Large countries are partitioned; use country and S2 paths to avoid huge scans.

## socrata

### `socrata.nyc.311-service-requests` — NYC Open Data 311 Service Requests

- Status: `candidate`
- Authority: City of New York Office of Technology and Innovation via NYC Open Data
- License: https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCadmin/0-0-0-216807
- DuckDB extensions: httpfs
- Tables:
  - `service_requests`: NYC 311 service request records. One row per 311 request.
    - Ask for: date range, borough, complaint type, limit
    - Warnings: Large table requires bounded SODA queries with select/order/limit.

### `socrata.cdc.places-county-2025` — CDC PLACES county health estimates, 2025 release

- Status: `candidate`
- Authority: Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention and Health Promotion, Division of Population Health
- License: https://data.cdc.gov/api/views/metadata/v1/swc5-untb
- DuckDB extensions: httpfs
- Tables:
  - `county_health_estimates`: CDC PLACES county health estimate rows. One row per county, measure, and data-value type.
    - Ask for: state, measure id, age-adjusted or crude prevalence
    - Warnings: Model-based estimates; filter datavaluetypeid to avoid duplicate measure rows.
    - Columns: locationid: County FIPS/GEOID join key for Census county boundary tables.; stateabbr: Two-letter U.S. state abbreviation.; countyname: County display name.; measureid: CDC PLACES measure identifier.; measure: Human-readable health or social determinant measure.; datavaluetypeid: Distinguishes age-adjusted prevalence, crude prevalence, and related estimate types.; data_value: Numeric estimate value, commonly percent for prevalence measures.
    - Schema.org: spatialCoverage: United States counties; temporalCoverage: 2025; measurementTechnique: CDC PLACES small-area estimation; variableMeasured: PLACES measure estimate
    - AI grain: one county, measure, and data-value type estimate row
    - Geography level: county
    - Safe operations: rank, compare, correlate, map, join
    - Join keys: locationid
    - Example questions:
      - Which Alaska counties have the highest modeled frequent mental distress prevalence?
      - Can I compare Alaska housing insecurity with mental distress by county using CDC PLACES measures?
      - Join PLACES county estimates to Census county boundaries and map one selected measure.
    - Known gaps:
      - Can I answer death rate vs real estate prices by county? — missing county mortality or death-rate source, county real-estate price or assessment source; death rate, real estate price

### `socrata.cdc.nchs-leading-causes-of-death` — CDC NCHS leading causes of death, United States

- Status: `candidate`
- Authority: Centers for Disease Control and Prevention, National Center for Health Statistics, Division of Vital Statistics
- License: https://www.usa.gov/government-works
- DuckDB extensions: httpfs
- Discovery namespace: `odd.cdc.latest`
- Tables:
  - `leading_causes_of_death` (`odd.cdc.latest.leading_causes_of_death`): CDC NCHS leading-cause mortality summary rows. One row per year, state, and cause with death count and age-adjusted death rate.
    - Ask for: state, year range, cause name or whether to include the All causes rollup, limit
    - Warnings: Dataset is a compact NCHS summary, not record-level mortality microdata., Latest rows in this Socrata asset currently stop at 2017., Filter out All causes when comparing ranked cause totals., Facade uses a bounded Socrata SODA CSV export with selected columns, deterministic ordering, and a 50000-row cap., Smoke sample: Alaska rows returned row_count=209, first_year=1999, last_year=2017, ranked_deaths_2017=3118 on 2026-11-22.
    - Columns: year: Reporting year from Socrata's Year field.; _113_cause_name: Detailed ICD-coded cause-of-death grouping from Socrata's 113 Cause Name field.; cause_name: Cause-of-death grouping; filter out All causes for ranked-cause comparisons.; state: U.S. state or District of Columbia reported by the dataset.; deaths: Death count for the selected year, state, and cause.; aadr: Age-adjusted death rate for the selected year, state, and cause.
    - Validation: `odd.cdc.latest.leading_causes_of_death`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SELECT count(*) AS row_count,
             min(year) AS first_year,
             max(year) AS last_year,
             CAST(sum(CASE WHEN year = 2017 AND cause_name <> 'All causes' THEN deaths ELSE 0 END) AS BIGINT) AS ranked_deaths_2017
      FROM odd.cdc.latest.leading_causes_of_death
      WHERE state = 'Alaska';
      ```

### `socrata.cdc.chronic-disease-indicators` — CDC U.S. Chronic Disease Indicators

- Status: `candidate`
- Authority: Centers for Disease Control and Prevention, National Center for Chronic Disease Prevention and Health Promotion, Division of Population Health
- License: https://opendatacommons.org/licenses/odbl/1.0/
- DuckDB extensions: httpfs
- Discovery namespace: `odd.cdc.latest`
- Tables:
  - `chronic_disease_indicators` (`odd.cdc.latest.chronic_disease_indicators`): CDC chronic-disease indicator observations. One row per location, topic, question, stratification, and time period in the bounded Socrata sample.
    - Ask for: year range, location abbreviation or geography, topic or question filters, stratification fields, limit
    - Warnings: ODbL license obligations are explicit in the Socrata metadata; preserve attribution and share-alike review when reusing broadly., Dataset is a wide Socrata table with repeated rows across stratifications; filter by year, location, topic, and question before broad scans., Facade is a fixed Alaska 2023 validation sample using selected columns, deterministic ordering, and a 5000-row cap until ODD supports parameterized Socrata paging., Smoke sample: Alaska 2023 rows returned row_count=983, topics=14, questions=48 on 2026-11-23.
    - Columns: yearstart: Start year for the indicator observation.; locationabbr: U.S. state or territory abbreviation reported by the dataset.; topic: Chronic-disease topic grouping.; question: Indicator question text.; datavalue: Indicator value; many rows vary by stratification and some values are suppressed or null.; datavalueunit: Unit for datavalue, commonly percent.
    - Validation: `odd.cdc.latest.chronic_disease_indicators`
      ```
      LOAD open_data_duck;
      ATTACH ':memory:' AS odd (TYPE open_data_duck);
      SELECT count(*) AS row_count,
             min(yearstart) AS min_year,
             max(yearstart) AS max_year,
             count(DISTINCT topic) AS topics,
             count(DISTINCT question) AS questions
      FROM odd.cdc.latest.chronic_disease_indicators;
      ```

## stac

### `stac.earth-search.aws` — Earth Search STAC API

- Status: `candidate`
- Authority: Element 84 / AWS Open Data ecosystem
- License: https://registry.opendata.aws/sentinel-2-l2a-cogs/
- DuckDB extensions: httpfs, spatial, stac
- Tables:
  - `stac_items`: STAC item search results from Earth Search. One row per imagery item returned by the STAC API.
    - Ask for: collection, bbox, date range, cloud cover, limit
    - Warnings: Assets can be large; inspect metadata before reading imagery assets.

### `stac.microsoft.planetary-computer` — Microsoft Planetary Computer STAC API

- Status: `candidate`
- Authority: Microsoft Planetary Computer
- License: https://planetarycomputer.microsoft.com/terms
- DuckDB extensions: httpfs, spatial, stac
- Tables:
  - `stac_items`: STAC item search results from Microsoft Planetary Computer. One row per catalog item returned by the STAC API.
    - Ask for: collection, bbox, date range, limit
    - Warnings: Some assets require Planetary Computer signing or access patterns.

### `stac.nasa.lpcloud` — NASA LP DAAC LPCLOUD STAC catalog

- Status: `candidate`
- Authority: NASA Land Processes Distributed Active Archive Center
- License: https://www.earthdata.nasa.gov/engage/open-data-services-and-software/data-and-information-policy
- DuckDB extensions: httpfs, spatial, stac
- Tables:
  - `stac_items`: NASA LP DAAC STAC item metadata. One row per land-processes product item returned by the STAC API.
    - Ask for: product or collection, bbox or area, date range, limit
    - Warnings: Some downstream assets may require Earthdata access workflows.
