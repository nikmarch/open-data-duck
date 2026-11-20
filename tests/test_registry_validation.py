from __future__ import annotations

from pathlib import Path
import importlib
import re

import pytest
import yaml

from odd.arcgis import plan_offset_pages
from odd.cli import main
from odd.registry import (
    find_source,
    render_index_json,
    render_index_markdown,
    render_index_text,
    render_source_detail,
    render_source_sql,
    search_sources,
    validate_registry,
    write_index_artifacts,
)


VALID_REGISTRY = {
    "sources": [
        {
            "id": "example.source",
            "name": "Example source",
            "description": "Example source description for humans and AI agents.",
            "status": "candidate",
            "source_type": "parquet",
            "authority": "Example Authority",
            "homepage": "https://example.com/data",
            "license_url": "https://example.com/license",
            "attribution": "Credit Example Authority.",
            "tags": ["example", "parquet"],
            "topics": ["testing"],
            "coverage": {"spatial": "test", "temporal": "static", "grain": "rows"},
            "cadence": "static fixture",
            "ai": {
                "summary": "Use for registry tests.",
                "use_cases": ["test search"],
                "caveats": ["fixture only"],
                "prompt_hints": ["Use a tiny query."],
            },
            "duckdb": {
                "extensions": ["httpfs"],
                "example_query": "SELECT * FROM read_parquet('https://example.com/data.parquet');",
                "validation_query": "SELECT 1;",
            },
            "tables": [
                {
                    "id": "rows",
                    "ref": "odd.example.latest.rows",
                    "description": "Example rows. One row per fixture record.",
                    "columns_hint": {"id": "Stable fixture row id."},
                    "ask_for": ["limit"],
                    "warnings": ["Fixture only."],
                }
            ],
            "validations": [
                {
                    "id": "odd.example.latest.rows",
                    "description": "Compare the ODD facade against the direct reader.",
                    "release": "latest",
                    "direct_sql": "SELECT id FROM read_parquet('https://example.com/data.parquet') ORDER BY id LIMIT 5;",
                    "odd_sql": "SELECT id FROM odd.example.latest.rows ORDER BY id LIMIT 5;",
                    "compare": "exact",
                    "order_by": ["id"],
                    "limit": 5,
                }
            ],
        }
    ]
}


MINIMAL_REGISTRY = {
    "sources": [
        {
            "id": "minimal.source",
            "name": "Minimal source",
            "status": "candidate",
            "source_type": "parquet",
            "authority": "Minimal Authority",
            "license_url": "https://example.com/license",
            "attribution": "Credit Minimal Authority.",
            "duckdb": {"extensions": ["httpfs"]},
            "tables": [
                {"id": "rows", "ref": "odd.minimal.latest.rows", "description": "Minimal rows."}
            ],
            "validations": [
                {
                    "id": "odd.minimal.latest.rows",
                    "direct_sql": "SELECT id FROM read_parquet('https://example.com/data.parquet') ORDER BY id LIMIT 5;",
                    "odd_sql": "SELECT id FROM odd.minimal.latest.rows ORDER BY id LIMIT 5;",
                }
            ],
        }
    ]
}


def write_registry(tmp_path: Path, registry: dict) -> tuple[Path, Path]:
    registry_path = tmp_path / "sources.yml"
    schema_path = tmp_path / "source.schema.json"
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    schema_path.write_text(Path("schema/source.schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    return registry_path, schema_path


def test_validate_registry_accepts_valid_source(tmp_path: Path) -> None:
    registry_path, schema_path = write_registry(tmp_path, VALID_REGISTRY)

    assert validate_registry(registry_path, schema_path) == []


def test_validate_registry_accepts_minimal_validation_pair_source(tmp_path: Path) -> None:
    registry_path, schema_path = write_registry(tmp_path, MINIMAL_REGISTRY)

    assert validate_registry(registry_path, schema_path) == []
    source = find_source(registry_path, "minimal.source")
    assert source is not None
    assert source.description == ""
    assert source.homepage == ""
    assert source.duckdb == {"extensions": ["httpfs"]}


def test_schema_source_required_fields_are_small_core() -> None:
    schema = yaml.safe_load(Path("schema/source.schema.json").read_text(encoding="utf-8"))

    assert schema["$defs"]["source"]["required"] == [
        "id",
        "name",
        "status",
        "source_type",
        "authority",
        "license_url",
        "attribution",
        "duckdb",
        "tables",
    ]
    assert schema["$defs"]["source"]["properties"]["duckdb"]["required"] == ["extensions"]
    assert schema["$defs"]["table"]["required"] == ["id", "description"]
    assert schema["$defs"]["validation"]["required"] == ["id", "direct_sql", "odd_sql"]


def test_validate_registry_accepts_connector_blocked_status(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    registry["sources"][0]["status"] = "connector-blocked"
    registry_path, schema_path = write_registry(tmp_path, registry)

    assert validate_registry(registry_path, schema_path) == []


@pytest.mark.parametrize(
    ("field_path", "expected_path"),
    [
        (("authority",), "authority"),
        (("license_url",), "license_url"),
        (("attribution",), "attribution"),
        (("validations", 0, "direct_sql"), "validations[0](odd.example.latest.rows).direct_sql"),
        (("validations", 0, "odd_sql"), "validations[0](odd.example.latest.rows).odd_sql"),
    ],
)
def test_validate_registry_rejects_blank_required_text(
    tmp_path: Path,
    field_path: tuple[str, ...],
    expected_path: str,
) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    source = registry["sources"][0]
    target = source
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = "   "
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any(expected_path in error.path for error in errors)
    assert any("non-blank" in error.message for error in errors)


def test_validate_registry_rejects_duplicate_ids(tmp_path: Path) -> None:
    registry = {"sources": [VALID_REGISTRY["sources"][0], VALID_REGISTRY["sources"][0]]}
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("duplicate source id" == error.message for error in errors)


def test_validate_registry_requires_legacy_queries_only_without_validation_pairs(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(MINIMAL_REGISTRY))
    source = registry["sources"][0]
    source.pop("validations")
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("duckdb.example_query" in error.path for error in errors)
    assert any("duckdb.validation_query" in error.path for error in errors)
    assert any("unless validations are present" in error.message for error in errors)


def test_validate_registry_rejects_duplicate_validation_ids(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    source = registry["sources"][0]
    source["validations"].append(source["validations"][0].copy())
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("duplicate validation id" == error.message for error in errors)


def test_validate_registry_rejects_duplicate_validation_ids_across_table_metadata(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    source = registry["sources"][0]
    source["tables"][0]["validations"] = [source["validations"][0].copy()]
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("duplicate validation id odd.example.latest.rows" == error.message for error in errors)


def test_validate_registry_rejects_non_odd_validation_sql(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    registry["sources"][0]["validations"][0]["odd_sql"] = "SELECT id FROM direct_table;"
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("must query an odd.* facade" == error.message for error in errors)


def test_validate_registry_rejects_non_sql_safe_release_ids(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    validation = registry["sources"][0]["validations"][0]
    validation["id"] = "odd.example.2026-10-21.rows"
    validation["release"] = "2026-10-21"
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("SQL-safe" in error.message for error in errors)


def test_validate_registry_reports_schema_errors(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    del registry["sources"][0]["name"]
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("name" in error.message for error in errors)


def test_cli_validate_exits_zero_for_valid_registry(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry_path, schema_path = write_registry(tmp_path, VALID_REGISTRY)

    exit_code = main(["validate", "--registry", str(registry_path), "--schema", str(schema_path)])

    assert exit_code == 0
    assert "validation passed" in capsys.readouterr().out


def test_cli_validate_exits_nonzero_for_invalid_registry(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    registry["sources"][0]["attribution"] = ""
    registry_path, schema_path = write_registry(tmp_path, registry)

    exit_code = main(["validate", "--registry", str(registry_path), "--schema", str(schema_path)])

    assert exit_code == 1
    assert "Registry validation failed" in capsys.readouterr().out


def test_project_registry_is_valid() -> None:
    errors = validate_registry(Path("registry/sources.yml"), Path("schema/source.schema.json"))

    assert [error.format() for error in errors] == []


def test_checked_in_index_artifacts_are_current() -> None:
    from odd.registry import load_sources

    sources = load_sources(Path("registry/sources.yml"))

    assert Path("docs/index.md").read_text(encoding="utf-8") == render_index_markdown(sources)
    assert not Path("docs/index.json").exists()


def test_project_registry_meets_seed_source_targets() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    sources = registry["sources"]
    source_types = [source["source_type"] for source in sources]
    source_ids = [source["id"] for source in sources]

    assert "overture.maps.release" in source_ids
    assert source_types.count("stac") >= 3
    assert source_types.count("arcgis") >= 3
    assert source_types.count("ckan") >= 1
    assert source_types.count("socrata") >= 1
    assert sum(source_id.startswith("aws.") for source_id in source_ids) >= 3


def test_project_socrata_sources_use_bounded_soda_exports() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    socrata_sources = [source for source in registry["sources"] if source["source_type"] == "socrata"]

    assert len(socrata_sources) >= 1
    for source in socrata_sources:
        assert source["status"] == "candidate", source["id"]
        assert source["license_url"].startswith("https://"), source["id"]
        rendered_sql = "\n".join(
            (
                source["duckdb"].get("install", ""),
                source["duckdb"]["example_query"],
                source["duckdb"]["validation_query"],
                "\n".join(source["duckdb"].get("examples", {}).values()),
            )
        ).casefold()
        assert "load httpfs" in rendered_sql
        assert "read_csv_auto" in rendered_sql or "read_json_auto" in rendered_sql
        assert "$select=" in rendered_sql
        assert "$order=" in rendered_sql
        assert "$limit=" in rendered_sql
        assert "load socrata" not in rendered_sql
        assert "install socrata" not in rendered_sql
        assert "read_csv_auto('https://data.cityofnewyork.us/resource/erm2-nwe9.csv')" not in rendered_sql


def test_project_ckan_sources_use_direct_resources_until_table_function_is_proven() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    ckan_sources = [source for source in registry["sources"] if source["source_type"] == "ckan"]

    assert len(ckan_sources) >= 1
    for source in ckan_sources:
        assert source["status"] == "candidate", source["id"]
        rendered_sql = "\n".join(
            (
                source["duckdb"].get("install", ""),
                source["duckdb"]["example_query"],
                source["duckdb"]["validation_query"],
            )
        ).casefold()
        assert "load httpfs" in rendered_sql
        assert any(reader in rendered_sql for reader in ("read_csv_auto", "read_json_auto", "read_parquet", "st_read"))
        assert "ckan_" not in rendered_sql
        assert "dcat_" not in rendered_sql


def test_project_arcgis_sources_are_connector_blocked_until_engine_path_is_stable() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    arcgis_sources = [source for source in registry["sources"] if source["source_type"] == "arcgis"]

    assert len(arcgis_sources) >= 3
    for source in arcgis_sources:
        assert source["status"] == "connector-blocked", source["id"]
        rendered_sql = "\n".join(
            (
                source["duckdb"].get("install", ""),
                source["duckdb"]["example_query"],
            )
        ).casefold()
        assert "duckdb-arcgis is not in duckdb community extensions" in rendered_sql
        assert "allow_unsigned_extensions" in rendered_sql
        assert "install arcgis from community" not in rendered_sql


def test_project_census_cartographic_boundaries_use_direct_spatial_file_recipes() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    county_source = next(
        source for source in registry["sources"] if source["id"] == "census.cartographic.county-boundaries"
    )
    tract_source = next(
        source for source in registry["sources"] if source["id"] == "census.cartographic.tract-boundaries"
    )

    for source in (county_source, tract_source):
        rendered_sql = "\n".join(
            (
                source["duckdb"].get("install", ""),
                source["duckdb"]["example_query"],
                source["duckdb"]["validation_query"],
                "\n".join(source["duckdb"].get("examples", {}).values()),
            )
        ).casefold()

        assert source["status"] == "candidate"
        assert source["source_type"] == "other"
        assert source["authority"] == "U.S. Census Bureau Geography Program"
        assert "spatial" in source["duckdb"]["extensions"]
        assert "install spatial" in rendered_sql
        assert "load spatial" in rendered_sql
        assert "st_read" in rendered_sql
        assert "arcgis_query" not in rendered_sql

    county_sql = "\n".join(
        (
            county_source["duckdb"]["example_query"],
            county_source["duckdb"]["validation_query"],
        )
    ).casefold()
    tract_sql = "\n".join(
        (
            tract_source["duckdb"]["example_query"],
            tract_source["duckdb"]["validation_query"],
            "\n".join(tract_source["duckdb"].get("examples", {}).values()),
        )
    ).casefold()

    assert "/vsizip/vsicurl/https://www2.census.gov/geo/tiger/genz2025/shp/cb_2025_us_county_20m.zip/cb_2025_us_county_20m.shp" in county_sql
    assert "count(*) = 3222" in county_sql
    assert "/vsizip/vsicurl/https://www2.census.gov/geo/tiger/genz2025/shp/cb_2025_us_tract_5m.zip/cb_2025_us_tract_5m.shp" in tract_sql
    assert "count(*) = 85187" in tract_sql
    assert "where statefp = '02'" in tract_sql


def test_project_usgs_earthquake_feed_uses_direct_geojson_recipe() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    source = next(source for source in registry["sources"] if source["id"] == "usgs.earthquake.realtime-geojson")

    rendered_sql = "\n".join(
        (
            source["duckdb"].get("install", ""),
            source["duckdb"]["example_query"],
            source["duckdb"]["validation_query"],
            "\n".join(source["duckdb"].get("examples", {}).values()),
        )
    ).casefold()

    assert source["status"] == "candidate"
    assert source["source_type"] == "other"
    assert source["authority"] == "U.S. Geological Survey Earthquake Hazards Program"
    assert "httpfs" in source["duckdb"]["extensions"]
    assert "earthquake.usgs.gov/earthquakes/feed/v1.0/summary/" in rendered_sql
    assert "read_json_auto" in rendered_sql
    assert "maximum_object_size" in rendered_sql
    assert "all_month.geojson" in source["duckdb"]["validation_query"]
    assert "install stac" not in rendered_sql
    assert "load stac" not in rendered_sql


def test_project_noaa_ncei_storm_events_uses_latest_bulk_csv_discovery() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    source = next(source for source in registry["sources"] if source["id"] == "noaa.ncei.storm-events")

    rendered_sql = "\n".join(
        (
            source["duckdb"].get("install", ""),
            source["duckdb"]["example_query"],
            source["duckdb"]["validation_query"],
            "\n".join(source["duckdb"].get("examples", {}).values()),
        )
    ).casefold()
    latest = source["release"]["latest"]
    tables = source["duckdb"]["tables"]

    assert source["status"] == "candidate"
    assert source["source_type"] == "other"
    assert source["authority"] == "NOAA National Centers for Environmental Information"
    assert "httpfs" in source["duckdb"]["extensions"]
    assert "www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/" in rendered_sql
    assert "read_csv_auto" in rendered_sql
    assert "StormEvents_details-ftp_v1.0_d2024_c20261118.csv.gz" in source["duckdb"]["validation_query"]
    assert latest["method"] == "html-listing"
    assert latest["url"] in latest["resolve_sql"]
    assert "StormEvents_details-ftp_v1" in latest["resolve_sql"]
    assert source["release"]["pinned"] == {"duckdb_setting": "noaa_storm_events_year", "example": "2024"}
    assert tables["namespace"] == "odd.noaa.latest"
    assert "StormEvents_[a-z]+-ftp_v1" in tables["discover_sql"]
    assert "max(created)" in tables["discover_sql"]
    assert "storm_events_" in tables["discover_sql"]
    assert "c20261118" not in tables["discover_sql"]
    assert "load stac" not in rendered_sql


def test_project_world_bank_wdi_uses_api_json_envelope_recipe() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    source = next(source for source in registry["sources"] if source["id"] == "worldbank.wdi.indicators")

    rendered_sql = "\n".join(
        (
            source["duckdb"].get("install", ""),
            source["duckdb"]["example_query"],
            source["duckdb"]["validation_query"],
            "\n".join(source["duckdb"].get("examples", {}).values()),
        )
    ).casefold()

    assert source["status"] == "candidate"
    assert source["source_type"] == "other"
    assert source["authority"] == "World Bank Group"
    assert "httpfs" in source["duckdb"]["extensions"]
    assert "api.worldbank.org/v2/country/usa/indicator/sp.pop.totl" in rendered_sql
    assert "format=json" in rendered_sql
    assert "read_json" in rendered_sql
    assert "json_each" in rendered_sql
    assert "countryiso3code" in rendered_sql
    assert "freshness" not in source
    assert "load worldbank" not in rendered_sql
    assert "install worldbank" not in rendered_sql


def test_project_bls_cpi_timeseries_uses_public_json_api_recipe() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    source = next(source for source in registry["sources"] if source["id"] == "bls.cpi.timeseries")

    rendered_sql = "\n".join(
        (
            source["duckdb"].get("install", ""),
            source["duckdb"]["example_query"],
            source["duckdb"]["validation_query"],
            "\n".join(source["duckdb"].get("examples", {}).values()),
        )
    ).casefold()

    assert source["status"] == "candidate"
    assert source["source_type"] == "other"
    assert source["authority"] == "U.S. Bureau of Labor Statistics"
    assert "httpfs" in source["duckdb"]["extensions"]
    assert "api.bls.gov/publicapi/v1/timeseries/data/cuur0000sa0" in rendered_sql
    assert "results.series" in rendered_sql
    assert "cuur0000sa0" in source["duckdb"]["validation_query"].casefold()
    assert "try_cast(obs.value as double)" in rendered_sql
    assert "bls.gov" in source["attribution"].casefold()
    assert "load bls" not in rendered_sql
    assert "install bls" not in rendered_sql


def test_project_openfda_food_enforcement_uses_public_json_api_recipe() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    source = next(source for source in registry["sources"] if source["id"] == "openfda.food.enforcement-reports")

    rendered_sql = "\n".join(
        (
            source["duckdb"].get("install", ""),
            source["duckdb"]["example_query"],
            source["duckdb"]["validation_query"],
            "\n".join(source["duckdb"].get("examples", {}).values()),
        )
    ).casefold()
    table = source["tables"][0]

    assert source["status"] == "candidate"
    assert source["source_type"] == "other"
    assert source["authority"] == "U.S. Food and Drug Administration openFDA"
    assert "httpfs" in source["duckdb"]["extensions"]
    assert source["license_url"] == "https://open.fda.gov/license/"
    assert "api.fda.gov/food/enforcement.json" in rendered_sql
    assert "read_json" in rendered_sql
    assert "unnest(results)" in rendered_sql
    assert "recall_number" in rendered_sql
    assert "classification:%22class%20i%22" in rendered_sql
    assert "limit=5" in source["duckdb"]["validation_query"]
    assert "bool_and(report.recall_number is not null)" in rendered_sql
    assert table["id"] == "food_enforcement_reports"
    assert "nested JSON envelopes" in table["warnings"][0]
    assert "load openfda" not in rendered_sql
    assert "install openfda" not in rendered_sql


def test_project_treasury_debt_to_penny_uses_gzipped_fiscal_data_csv_recipe() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    source = next(source for source in registry["sources"] if source["id"] == "treasury.fiscaldata.debt-to-penny")

    rendered_sql = "\n".join(
        (
            source["duckdb"].get("install", ""),
            source["duckdb"]["example_query"],
            source["duckdb"]["validation_query"],
            "\n".join(source["duckdb"].get("examples", {}).values()),
        )
    ).casefold()

    assert source["status"] == "candidate"
    assert source["source_type"] == "other"
    assert source["authority"] == "U.S. Department of the Treasury, Bureau of the Fiscal Service"
    assert "httpfs" in source["duckdb"]["extensions"]
    assert "api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny" in rendered_sql
    assert "format=csv" in rendered_sql
    assert "compression = 'gzip'" in rendered_sql
    assert "tot_pub_debt_out_amt" in rendered_sql
    assert "max(record_date) >= date '2026-01-01'" in rendered_sql
    assert "treasury" in source["attribution"].casefold()
    assert "load treasury" not in rendered_sql
    assert "install treasury" not in rendered_sql


def test_arcgis_feature_server_pagination_acceptance_uses_multiple_pages() -> None:
    layer_url = (
        "https://services.arcgis.com/V6ZHFr6zdgNZuVG0/arcgis/rest/services/"
        "CongressionalDistricts/FeatureServer/0"
    )

    pages = plan_offset_pages(
        layer_url,
        total_records=435,
        page_size=200,
        object_id_field="OBJECTID",
        out_fields="OBJECTID,DISTRICTID,NAME",
        return_geometry=False,
    )

    assert len(pages) == 3
    assert [page.offset for page in pages] == [0, 200, 400]
    assert [page.record_count for page in pages] == [200, 200, 35]
    assert all(page.layer_url == layer_url for page in pages)
    assert [page.params["resultOffset"] for page in pages] == ["0", "200", "400"]
    assert [page.params["resultRecordCount"] for page in pages] == ["200", "200", "35"]
    assert all(page.params["returnGeometry"] == "false" for page in pages)
    assert all(page.params["orderByFields"] == "OBJECTID" for page in pages)


def test_overture_source_family_has_release_modes_and_core_examples() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    source = next(source for source in registry["sources"] if source["id"] == "overture.maps.release")

    assert source["status"] == "candidate"
    latest = source["release"]["latest"]
    assert latest["method"] == "stac-catalog"
    assert latest["url"] == "https://stac.overturemaps.org/catalog.json"
    # The extension runs this snippet once per process to resolve `latest`, then caches it.
    assert "https://stac.overturemaps.org/catalog.json" in latest["resolve_sql"]
    assert "latest" in latest["resolve_sql"]
    tables = source["duckdb"]["tables"]
    assert tables["namespace"] == "odd.overturemaps.latest"
    # Overture tables are discovered from the release's STAC collections, never listed by hand.
    assert "https://stac.overturemaps.org/{release}/collections.parquet" in tables["discover_sql"]
    assert "s3://overturemaps" not in tables["discover_sql"]
    assert "facades" not in source["duckdb"]
    assert source["release"]["pinned"] == {
        "duckdb_setting": "overture_release",
        "s3_base_setting": "overture_s3_base",
        "example": "2026-10-21.0",
    }

    install_and_queries = "\n".join(
        [
            source["duckdb"].get("install", ""),
            source["duckdb"]["example_query"],
            source["duckdb"]["validation_query"],
            *source["duckdb"]["examples"].values(),
        ]
    )
    assert "INSTALL httpfs;" in source["duckdb"]["install"]
    assert "LOAD httpfs;" in install_and_queries
    assert "INSTALL overture" not in install_and_queries
    assert "LOAD overture" not in install_and_queries
    assert "read_overture_" not in install_and_queries

    examples = source["duckdb"]["examples"]
    assert set(examples) >= {
        "places_bbox_direct_s3",
        "buildings_bbox_direct_s3",
        "road_segments_bbox_direct_s3",
        "addresses_bbox_direct_s3",
    }
    expected_paths = {
        "places_bbox_direct_s3": "/theme=places/type=place/*",
        "buildings_bbox_direct_s3": "/theme=buildings/type=building/*",
        "road_segments_bbox_direct_s3": "/theme=transportation/type=segment/*",
        "addresses_bbox_direct_s3": "/theme=addresses/type=address/*",
    }
    for example_name, expected_path in expected_paths.items():
        example_sql = examples[example_name]
        assert "read_parquet" in example_sql
        assert "overture_s3_base" in example_sql
        assert expected_path in example_sql
        assert "hive_partitioning = true" in example_sql
        assert "bbox.xmin" in example_sql

    validation_query = source["duckdb"]["validation_query"]
    assert "read_parquet" in validation_query
    assert "overture_s3_base" in validation_query
    assert "/theme=places/type=place/*" in validation_query


def test_seed_sources_include_required_query_metadata() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))

    for source in registry["sources"]:
        assert source["license_url"].startswith("https://"), source["id"]
        assert source["attribution"].strip(), source["id"]
        assert source["duckdb"]["extensions"], source["id"]
        assert source["tables"], source["id"]
        for table in source["tables"]:
            assert table["id"].strip(), source["id"]
            assert table["description"].strip(), f"{source['id']}:{table.get('id')}"
        if not source.get("validations"):
            assert source["duckdb"]["example_query"].strip(), source["id"]
            assert source["duckdb"]["validation_query"].strip(), source["id"]


def test_seed_validation_pairs_use_odd_ids_and_direct_sql_contract() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    assert all("freshness" not in source for source in registry["sources"])
    validations = [validation for source in registry["sources"] for validation in source.get("validations", [])]

    assert "odd.overturemaps.latest.place" in {validation["id"] for validation in validations}
    assert "odd.overturemaps.x2026x10x21.place" in {validation["id"] for validation in validations}
    assert "odd.noaa.latest.storm_events_details" in {validation["id"] for validation in validations}
    table_refs = {
        table["ref"]
        for source in registry["sources"]
        for table in source["tables"]
        if table.get("ref")
    }

    for validation in validations:
        assert re.fullmatch(r"odd\.[a-z0-9_]+\.[a-z0-9x_]+\.[a-z0-9_]+", validation["id"]), validation["id"]
        validation_parts = validation["id"].split(".")
        latest_ref = f"odd.{validation_parts[1]}.latest.{validation_parts[3]}"
        assert validation["id"] in table_refs or latest_ref in table_refs
        assert validation["direct_sql"].strip(), validation["id"]
        assert validation["odd_sql"].strip(), validation["id"]
        assert validation["id"] in validation["odd_sql"], validation["id"]
        assert "odd." not in validation["direct_sql"].casefold(), validation["id"]
        assert validation.get("compare") == "exact", validation["id"]

    overture_place_validations = [
        validation for validation in validations if validation["id"].startswith("odd.overturemaps.")
    ]
    for validation in overture_place_validations:
        combined_sql = f"{validation['direct_sql']}\n{validation['odd_sql']}"
        assert "bbox.xmin <= 66.981" in combined_sql, validation["id"]
        assert "bbox.xmax >= 66.976" in combined_sql, validation["id"]
        assert "bbox.ymin <= 39.657" in combined_sql, validation["id"]
        assert "bbox.ymax >= 39.652" in combined_sql, validation["id"]
        assert "bbox.xmin <= -149" not in combined_sql, validation["id"]


def test_search_sources_matches_terms_and_filters(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    matches = search_sources(registry_path, "example parquet", source_type="parquet", status="candidate")

    assert [source.id for source in matches] == ["example.source"]


def test_search_sources_matches_description_and_ai_metadata(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    matches = search_sources(registry_path, "humans agents fixture")

    assert [source.id for source in matches] == ["example.source"]


def test_source_ai_dict_exposes_metadata_without_sql_by_default(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    payload = source.to_ai_dict(include_sql=False)

    assert payload["description"] == "Example source description for humans and AI agents."
    assert payload["tags"] == ["example", "parquet"]
    assert payload["ai"]["summary"] == "Use for registry tests."
    assert payload["validations"][0]["id"] == "odd.example.latest.rows"
    assert "example_query" not in payload["duckdb"]


def test_render_index_outputs_pretty_text_markdown_and_json(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    text = render_index_text([source])
    markdown = render_index_markdown([source])
    json_output = render_index_json([source])

    assert "Open Data Duck source index" in text
    assert "Example source description" in text
    assert "### `example.source`" in markdown
    assert "Ask for: limit" in markdown
    assert "Warnings: Fixture only." in markdown
    assert '\"source_count\": 1' in json_output


def test_render_source_detail_includes_ai_usage(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    detail = render_source_detail(source)

    assert "AI usage:" in detail
    assert "Use for registry tests" in detail
    assert "Ask for: limit" in detail
    assert "Warnings: Fixture only." in detail
    assert "Columns: id: Stable fixture row id." in detail


def test_table_level_validations_drive_rendered_sql(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(MINIMAL_REGISTRY))
    source = registry["sources"][0]
    table_validation = source.pop("validations")[0]
    source["tables"][0]["validations"] = [table_validation]
    registry_path, schema_path = write_registry(tmp_path, registry)

    assert validate_registry(registry_path, schema_path) == []
    source_obj = find_source(registry_path, "minimal.source")

    assert source_obj is not None
    assert render_source_sql(source_obj) == "SELECT id FROM odd.minimal.latest.rows ORDER BY id LIMIT 5;\n"


def test_write_index_artifacts_creates_markdown_and_json(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    output_dir = tmp_path / "docs"

    paths = write_index_artifacts(registry_path, output_dir)

    assert {path.name for path in paths} == {"index.md"}
    assert "Example source description" in (output_dir / "index.md").read_text(encoding="utf-8")
    assert not (output_dir / "index.json").exists()


def test_mcp_server_module_is_import_safe_and_returns_tool_payloads(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    mcp_server = importlib.import_module("odd.mcp_server")

    search_payload = mcp_server.search_registry("fixture", registry_path=registry_path)
    source_payload = mcp_server.get_registry_source("example.source", registry_path=registry_path, include_sql=False)
    sql_payload = mcp_server.get_registry_source_sql("example.source", registry_path=registry_path)

    assert search_payload["count"] == 1
    assert source_payload["description"] == "Example source description for humans and AI agents."
    assert "odd.example.latest.rows" in sql_payload["sql"]
    assert "read_parquet" not in sql_payload["sql"]


def test_search_sources_requires_all_terms(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    matches = search_sources(registry_path, "example missing")

    assert matches == []


def test_find_source_returns_source_by_id(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    source = find_source(registry_path, "example.source")

    assert source is not None
    assert source.name == "Example source"


def test_render_source_sql_prefers_validation_odd_sql_as_example(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    registry["sources"][0]["duckdb"]["install"] = "INSTALL httpfs;"
    registry_path, _schema_path = write_registry(tmp_path, registry)
    source = find_source(registry_path, "example.source")

    assert source is not None
    sql = render_source_sql(source)

    assert sql == "SELECT id FROM odd.example.latest.rows ORDER BY id LIMIT 5;\n"
    assert "INSTALL httpfs;" not in sql
    assert "read_parquet" not in sql


def test_render_source_sql_validation_prints_direct_and_odd_pair(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    sql = render_source_sql(source, validation=True, include_install=False)

    assert "direct DuckDB control for odd.example.latest.rows" in sql
    assert "FROM read_parquet" in sql
    assert "ODD facade example for odd.example.latest.rows" in sql
    assert "FROM odd.example.latest.rows" in sql


def test_cli_search_prints_matching_sources(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    exit_code = main(["search", "example", "--registry", str(registry_path)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "example.source" in output
    assert "Example source" in output
    assert "Example source description" in output


def test_cli_index_prints_pretty_source_index(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    exit_code = main(["index", "--registry", str(registry_path)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Open Data Duck source index" in output
    assert "example.source" in output


def test_cli_show_prints_source_detail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    exit_code = main(["show", "example.source", "--registry", str(registry_path)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "AI usage:" in output
    assert "Example source description" in output


def test_cli_generate_index_writes_markdown_docs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    output_dir = tmp_path / "docs"

    exit_code = main(["generate-index", "--registry", str(registry_path), "--output-dir", str(output_dir)])

    assert exit_code == 0
    assert "index.md" in capsys.readouterr().out
    assert (output_dir / "index.md").exists()
    assert not (output_dir / "index.json").exists()


def test_cli_search_exits_nonzero_when_no_sources_match(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    exit_code = main(["search", "missing", "--registry", str(registry_path)])

    assert exit_code == 1
    assert "No registry sources matched" in capsys.readouterr().out


def test_cli_sql_prints_source_query(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    exit_code = main(["sql", "example.source", "--registry", str(registry_path)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "odd.example.latest.rows" in output
    assert "read_parquet" not in output


def test_cli_sql_exits_nonzero_for_unknown_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    exit_code = main(["sql", "missing.source", "--registry", str(registry_path)])

    assert exit_code == 1
    assert "Source not found: missing.source" in capsys.readouterr().out


LATEST_TABLES = {
    "overture.maps.release": ("overture_release", "odd.overturemaps.latest"),
    "census.cartographic.county-boundaries": ("census_cartographic_year", "odd.census.latest"),
    "census.cartographic.tract-boundaries": ("census_cartographic_year", "odd.census.latest"),
    "noaa.ncei.storm-events": ("noaa_storm_events_year", "odd.noaa.latest"),
    "aws.noaa-ghcn-daily": ("noaa_ghcn_year", "odd.noaa.latest"),
}


def test_release_versioned_sources_declare_resolve_sql_and_table_discovery() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    by_id = {source["id"]: source for source in registry["sources"]}

    for source_id, (pin_variable, namespace) in LATEST_TABLES.items():
        source = by_id[source_id]
        latest = source["release"]["latest"]
        assert latest["resolve_sql"].strip(), source_id
        assert latest["url"] in latest["resolve_sql"], source_id
        assert source["release"]["pinned"]["duckdb_setting"] == pin_variable
        tables = source["duckdb"]["tables"]
        assert tables["namespace"] == namespace
        assert re.fullmatch(r"odd\.[a-z0-9_]+\.[a-z0-9_]+", tables["namespace"])
        assert "{release}" in tables["discover_sql"], source_id
        # Contract consumed by the extension: one row per table.
        assert re.search(r"\bAS name\b", tables["discover_sql"]), source_id
        assert re.search(r"\bAS reader\b", tables["discover_sql"]), source_id
        assert re.search(r"\bAS path\b", tables["discover_sql"]), source_id

    for source in registry["sources"]:
        assert "facades" not in source["duckdb"], source["id"]
        if "tables" in source["duckdb"]:
            assert "release" in source, source["id"]
