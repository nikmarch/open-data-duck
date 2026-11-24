from __future__ import annotations

from pathlib import Path
import argparse
import importlib
import re

import pytest
import yaml

from odd.arcgis import plan_offset_pages
from odd.cli import build_parser, main
from odd.registry import (
    find_source,
    render_ai_catalog_json,
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
            "status": "candidate",
            "source_type": "parquet",
            "authority": "Example Authority",
            "license_url": "https://example.com/license",
            "attribution": "Credit Example Authority.",
            "requirements": {"duckdb_extensions": ["httpfs"]},
            "tables": [
                {
                    "id": "rows",
                    "ref": "odd.example.latest.rows",
                    "description": "Example rows. One row per fixture record.",
                    "columns_hint": {"id": "Stable fixture row id."},
                    "ask_for": ["limit"],
                    "warnings": ["Fixture only."],
                    "schema_org": {
                        "@type": "Dataset",
                        "spatialCoverage": "fixture space",
                        "temporalCoverage": "2026",
                        "variableMeasured": [{"@type": "PropertyValue", "name": "fixture value", "unitText": "count"}],
                        "measurementTechnique": "fixture generation",
                    },
                    "ai_capabilities": {
                        "grain": "one fixture row",
                        "geography_level": "none",
                        "join_keys": [{"field": "id", "description": "Fixture row id."}],
                        "time": {"field": "created_at", "grain": "instant"},
                        "metrics": [{"name": "fixture value", "field": "id", "unit": "count"}],
                        "dimensions": [{"name": "fixture id", "field": "id"}],
                        "safe_operations": ["rank", "compare"],
                        "caveats": ["Fixture only."],
                        "example_questions": ["Which fixture rows exist?"],
                        "missing_for_questions": [
                            {
                                "question": "Can fixtures explain production data?",
                                "missing_source_families": ["production source"],
                                "missing_metrics": ["production metric"],
                            }
                        ],
                    },
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
            "tables": [
                {
                    "id": "rows",
                    "ref": "odd.minimal.latest.rows",
                    "description": "Minimal rows.",
                    "validations": [
                        {
                            "id": "odd.minimal.latest.rows",
                            "direct_sql": "SELECT id FROM read_parquet('https://example.com/data.parquet') ORDER BY id LIMIT 5;",
                            "odd_sql": "SELECT id FROM odd.minimal.latest.rows ORDER BY id LIMIT 5;",
                        }
                    ],
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


def load_project_registry() -> dict:
    return yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))


def all_validation_sql(source: dict) -> str:
    return "\n".join(
        f"{validation.get('direct_sql', '')}\n{validation.get('odd_sql', '')}"
        for table in source.get("tables", [])
        for validation in table.get("validations", [])
    ).casefold()


def test_validate_registry_accepts_valid_source(tmp_path: Path) -> None:
    registry_path, schema_path = write_registry(tmp_path, VALID_REGISTRY)

    assert validate_registry(registry_path, schema_path) == []


def test_validate_registry_accepts_minimal_validation_pair_source(tmp_path: Path) -> None:
    registry_path, schema_path = write_registry(tmp_path, MINIMAL_REGISTRY)

    assert validate_registry(registry_path, schema_path) == []
    source = find_source(registry_path, "minimal.source")
    assert source is not None
    assert source.requirements == {}


def test_schema_source_required_fields_are_small_core_without_duckdb() -> None:
    schema = yaml.safe_load(Path("schema/source.schema.json").read_text(encoding="utf-8"))

    assert schema["$defs"]["source"]["required"] == [
        "id",
        "name",
        "status",
        "source_type",
        "authority",
        "license_url",
        "attribution",
        "tables",
    ]
    assert "duckdb" not in schema["$defs"]["source"]["properties"]
    assert "description" not in schema["$defs"]["source"]["properties"]
    assert "validations" not in schema["$defs"]["source"]["properties"]
    assert "validations" in schema["$defs"]["table"]["properties"]
    assert "schema_org" in schema["$defs"]["table"]["properties"]
    assert "ai_capabilities" in schema["$defs"]["table"]["properties"]
    assert schema["$defs"]["ai_capabilities"]["required"] == ["grain", "safe_operations", "example_questions"]
    assert schema["$defs"]["validation"]["required"] == ["id", "direct_sql", "odd_sql"]
    assert schema["$defs"]["source"]["additionalProperties"] is False


@pytest.mark.parametrize("legacy_field", ["duckdb", "description", "homepage", "tags", "topics", "coverage", "cadence", "ai"])
def test_validate_registry_rejects_legacy_source_junk_drawer_fields(tmp_path: Path, legacy_field: str) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    registry["sources"][0][legacy_field] = {} if legacy_field in {"duckdb", "coverage", "ai"} else "legacy"
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any(legacy_field in error.message for error in errors)


def test_validate_registry_rejects_source_level_validations(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    source = registry["sources"][0]
    source["validations"] = [source["tables"][0]["validations"][0].copy()]
    source["tables"][0].pop("validations")
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("validations" in error.path or "validations" in error.message for error in errors)


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
        (("tables", 0, "validations", 0, "direct_sql"), "tables[0](rows).validations[0](odd.example.latest.rows).direct_sql"),
        (("tables", 0, "validations", 0, "odd_sql"), "tables[0](rows).validations[0](odd.example.latest.rows).odd_sql"),
    ],
)
def test_validate_registry_rejects_blank_required_text(
    tmp_path: Path,
    field_path: tuple[str | int, ...],
    expected_path: str,
) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    target = registry["sources"][0]
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


def test_validate_registry_requires_validations_for_odd_refs(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(MINIMAL_REGISTRY))
    registry["sources"][0]["tables"][0].pop("validations")
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("validations" in error.path for error in errors)
    assert any("must be present for ref: odd.* tables" == error.message for error in errors)


def test_non_queryable_tables_do_not_need_validation_pairs(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(MINIMAL_REGISTRY))
    table = registry["sources"][0]["tables"][0]
    table.pop("ref")
    table.pop("validations")
    registry_path, schema_path = write_registry(tmp_path, registry)

    assert validate_registry(registry_path, schema_path) == []


def test_validate_registry_rejects_duplicate_validation_ids(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    table = registry["sources"][0]["tables"][0]
    table["validations"].append(table["validations"][0].copy())
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("duplicate validation id" == error.message for error in errors)


def test_validate_registry_rejects_duplicate_validation_ids_across_table_metadata(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    source = registry["sources"][0]
    duplicate_table = yaml.safe_load(yaml.safe_dump(source["tables"][0]))
    duplicate_table["id"] = "rows_copy"
    source["tables"].append(duplicate_table)
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("duplicate validation id odd.example.latest.rows" == error.message for error in errors)


def test_validate_registry_rejects_non_odd_validation_sql(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    registry["sources"][0]["tables"][0]["validations"][0]["odd_sql"] = "SELECT id FROM direct_table;"
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("must query an odd.* facade" == error.message for error in errors)


def test_validate_registry_rejects_odd_facade_inside_direct_sql(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    registry["sources"][0]["tables"][0]["validations"][0]["direct_sql"] = "SELECT id FROM odd.example.latest.rows;"
    registry_path, schema_path = write_registry(tmp_path, registry)

    errors = validate_registry(registry_path, schema_path)

    assert any("direct DuckDB control" in error.message for error in errors)


def test_validate_registry_rejects_non_sql_safe_release_ids(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    validation = registry["sources"][0]["tables"][0]["validations"][0]
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


def test_build_parser_exposes_expected_top_level_commands() -> None:
    parser = build_parser()
    subparser_action = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))

    assert set(subparser_action.choices) >= {
        "validate",
        "index",
        "ai-catalog",
        "show",
        "generate-index",
        "generate-site",
        "generate-extension-registry",
        "search",
        "sql",
        "schema",
    }


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
    registry = load_project_registry()
    sources = registry["sources"]
    source_types = [source["source_type"] for source in sources]
    source_ids = [source["id"] for source in sources]

    assert "overture.maps.release" in source_ids
    assert source_types.count("stac") >= 3
    assert source_types.count("arcgis") >= 3
    assert source_types.count("ckan") >= 1
    assert source_types.count("socrata") >= 1
    assert sum(source_id.startswith("aws.") for source_id in source_ids) >= 3


def test_cdc_nchs_leading_causes_source_exposes_bounded_socrata_facade_validation() -> None:
    registry = load_project_registry()
    source = next(source for source in registry["sources"] if source["id"] == "socrata.cdc.nchs-leading-causes-of-death")

    assert source["source_type"] == "socrata"
    assert source["requirements"]["duckdb_extensions"] == ["httpfs"]
    assert source["release"]["latest"]["method"] == "static-soda-export"
    assert source["discovery"]["namespace"] == "odd.cdc.latest"
    assert "bi63-dtpu.csv?$select=year,_113_cause_name,cause_name,state,deaths,aadr" in source["discovery"]["discover_sql"]
    table = source["tables"][0]
    assert table["id"] == "leading_causes_of_death"
    assert table["ref"] == "odd.cdc.latest.leading_causes_of_death"
    assert "state" in table["ask_for"]
    assert any("row_count=209" in warning for warning in table["warnings"])
    assert any("50000-row cap" in warning for warning in table["warnings"])
    assert table["columns_hint"]["cause_name"].startswith("Cause-of-death grouping")
    validation = table["validations"][0]
    assert validation["id"] == table["ref"]
    assert "read_csv_auto('https://data.cdc.gov/resource/bi63-dtpu.csv" in validation["direct_sql"]
    assert "FROM odd.cdc.latest.leading_causes_of_death" in validation["odd_sql"]
    assert "ranked_deaths_2017" in validation["odd_sql"]


def test_cdc_chronic_disease_indicators_source_exposes_bounded_socrata_facade_validation() -> None:
    registry = load_project_registry()
    source = next(source for source in registry["sources"] if source["id"] == "socrata.cdc.chronic-disease-indicators")

    assert source["source_type"] == "socrata"
    assert source["requirements"]["duckdb_extensions"] == ["httpfs"]
    assert source["license_url"] == "https://opendatacommons.org/licenses/odbl/1.0/"
    assert source["release"]["latest"]["method"] == "static-soda-export"
    assert source["discovery"]["namespace"] == "odd.cdc.latest"
    assert "hksd-2xuw.csv?$select=yearstart,locationabbr,topic,question,datavalue,datavalueunit" in source["discovery"]["discover_sql"]
    assert "$where=yearstart=2023%20AND%20locationabbr=%27AK%27" in source["discovery"]["discover_sql"]
    table = source["tables"][0]
    assert table["id"] == "chronic_disease_indicators"
    assert table["ref"] == "odd.cdc.latest.chronic_disease_indicators"
    assert "location abbreviation or geography" in table["ask_for"]
    assert any("row_count=983" in warning for warning in table["warnings"])
    assert any("parameterized Socrata paging" in warning for warning in table["warnings"])
    assert table["columns_hint"]["datavalue"].startswith("Indicator value")
    validation = table["validations"][0]
    assert validation["id"] == table["ref"]
    assert "read_csv_auto('https://data.cdc.gov/resource/hksd-2xuw.csv" in validation["direct_sql"]
    assert "FROM odd.cdc.latest.chronic_disease_indicators" in validation["odd_sql"]
    assert "count(DISTINCT topic)" in validation["odd_sql"]


def test_cdc_places_source_has_schema_org_ai_capability_metadata() -> None:
    registry = load_project_registry()
    source = next(source for source in registry["sources"] if source["id"] == "socrata.cdc.places-county-2025")
    table = source["tables"][0]
    source_obj = find_source(Path("registry/sources.yml"), source["id"])
    assert source_obj is not None
    catalog = yaml.safe_load(render_ai_catalog_json([source_obj]))
    rendered_docs = render_index_markdown([source_obj]).casefold()

    assert table["schema_org"]["@type"] == "Dataset"
    assert table["schema_org"]["spatialCoverage"] == "United States counties"
    assert table["schema_org"]["variableMeasured"][0]["name"] == "PLACES measure estimate"
    assert table["ai_capabilities"]["grain"] == "one county, measure, and data-value type estimate row"
    assert table["ai_capabilities"]["geography_level"] == "county"
    assert table["ai_capabilities"]["join_keys"][0]["field"] == "locationid"
    assert table["ai_capabilities"]["join_keys"][0]["references"] == "odd.census.latest.county_20m.GEOID"
    assert "correlate" in table["ai_capabilities"]["safe_operations"]
    assert any("Alaska housing insecurity" in question for question in table["ai_capabilities"]["example_questions"])
    assert table["ai_capabilities"]["missing_for_questions"][0]["missing_source_families"] == [
        "county mortality or death-rate source",
        "county real-estate price or assessment source",
    ]
    table_dataset = catalog["dataset"][0]["hasPart"][0]
    assert table_dataset["odd:aiCapabilities"]["metrics"][0]["field"] == "data_value"
    assert "alaska housing insecurity" in rendered_docs
    assert "death rate vs real estate" in rendered_docs


def test_project_registry_has_no_redundant_source_attributes_or_duckdb_junk_drawer() -> None:
    registry = load_project_registry()
    redundant = {"description", "homepage", "tags", "topics", "coverage", "cadence", "ai", "duckdb"}

    for source in registry["sources"]:
        assert not redundant & set(source), source["id"]
        assert source["license_url"].startswith("https://"), source["id"]
        assert source["attribution"].strip(), source["id"]
        assert source["tables"], source["id"]
        for table in source["tables"]:
            assert table["id"].strip(), source["id"]
            assert table["description"].strip(), f"{source['id']}:{table.get('id')}"


def test_seed_validation_pairs_use_odd_ids_and_direct_sql_contract() -> None:
    registry = load_project_registry()
    assert all("freshness" not in source for source in registry["sources"])
    assert all("validations" not in source for source in registry["sources"])
    validations = [
        validation
        for source in registry["sources"]
        for table in source["tables"]
        for validation in table.get("validations", [])
    ]

    assert "odd.overturemaps.latest.place" in {validation["id"] for validation in validations}
    assert "odd.overturemaps.x2026x10x21.place" in {validation["id"] for validation in validations}
    assert "odd.noaa.latest.storm_events_details" in {validation["id"] for validation in validations}
    table_refs = {
        table["ref"]
        for source in registry["sources"]
        for table in source["tables"]
        if table.get("ref")
    }
    validated_refs = {
        validation["id"] if validation["id"] in table_refs else f"odd.{validation['id'].split('.')[1]}.latest.{validation['id'].split('.')[3]}"
        for validation in validations
    }
    assert table_refs <= validated_refs

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


def test_known_table_validation_queries_preserve_direct_readers_and_facades() -> None:
    registry = load_project_registry()
    by_id = {source["id"]: source for source in registry["sources"]}

    overture_sql = all_validation_sql(by_id["overture.maps.release"])
    assert "read_parquet" in overture_sql
    assert "from odd.overturemaps.latest.place" in overture_sql
    assert "bbox.xmin <= 66.981" in overture_sql
    assert "bbox.xmin <= -149" not in overture_sql

    natural_earth_sql = all_validation_sql(by_id["naturalearth.admin0-countries"])
    assert "st_read" in natural_earth_sql
    assert "from odd.naturalearth.latest.countries_110m" in natural_earth_sql

    noaa_sql = all_validation_sql(by_id["noaa.ncei.storm-events"])
    assert "read_csv_auto" in noaa_sql
    assert "from odd.noaa.latest.storm_events_details" in noaa_sql

    coops_sql = all_validation_sql(by_id["noaa.coops.water-level-observations"])
    assert "api.tidesandcurrents.noaa.gov/api/prod/datagetter" in coops_sql
    assert "station=8518750" in coops_sql
    assert "from odd.noaa_coops.latest.hourly_heights" in coops_sql

    cdc_sql = all_validation_sql(by_id["socrata.cdc.nchs-leading-causes-of-death"])
    assert "read_csv_auto" in cdc_sql
    assert "from odd.cdc.latest.leading_causes_of_death" in cdc_sql
    assert "ranked_deaths_2017" in cdc_sql

    cdc_chronic_sql = all_validation_sql(by_id["socrata.cdc.chronic-disease-indicators"])
    assert "read_csv_auto" in cdc_chronic_sql
    assert "from odd.cdc.latest.chronic_disease_indicators" in cdc_chronic_sql
    assert "count(distinct topic)" in cdc_chronic_sql

    nasa_sql = all_validation_sql(by_id["nasa.exoplanet-archive.pscomppars"])
    assert "exoplanetarchive.ipac.caltech.edu/tap/sync" in nasa_sql
    assert "from odd.nasa_exoplanet_archive.latest.planetary_systems_composite" in nasa_sql
    assert "kepler-22 b" in nasa_sql

    nps_sql = all_validation_sql(by_id["nps.visitor-use-statistics"])
    assert "read_csv_auto" in nps_sql
    assert "from odd.nps.latest.state_monthly_visitor_stats" in nps_sql
    assert "from odd.nps.latest.monthly_visitor_stats" in nps_sql


def test_project_nps_visitor_use_statistics_exposes_bounded_csv_facade_validations() -> None:
    registry = load_project_registry()
    source = next(source for source in registry["sources"] if source["id"] == "nps.visitor-use-statistics")
    state_table, monthly_table = source["tables"]
    rendered_metadata = "\n".join(
        [
            source["name"],
            source["authority"],
            source["attribution"],
            state_table["description"],
            monthly_table["description"],
            "\n".join(state_table.get("ask_for", [])),
            "\n".join(state_table.get("warnings", [])),
            "\n".join(monthly_table.get("warnings", [])),
            state_table["validations"][0]["direct_sql"],
            state_table["validations"][0]["odd_sql"],
            monthly_table["validations"][0]["direct_sql"],
            monthly_table["validations"][0]["odd_sql"],
            source["discovery"]["discover_sql"],
        ]
    ).casefold()

    assert source["status"] == "candidate"
    assert source["source_type"] == "other"
    assert source["authority"] == "National Park Service Social Science Program"
    assert source["license_url"] == "https://creativecommons.org/publicdomain/zero/1.0/deed.en"
    assert source["requirements"] == {"duckdb_extensions": ["httpfs"]}
    assert source["release"]["latest"]["method"] == "static-data-package"
    assert source["discovery"] == {
        "namespace": "odd.nps.latest",
        "discover_sql": (
            "SELECT 'state_monthly_visitor_stats' AS name,\n"
            "       'read_csv_auto' AS reader,\n"
            "       'https://irma.nps.gov/DataStore/DownloadFile/756960?Reference=2317666' AS path\n"
            "UNION ALL\n"
            "SELECT 'monthly_visitor_stats' AS name,\n"
            "       'read_csv_auto' AS reader,\n"
            "       'https://irma.nps.gov/DataStore/DownloadFile/756959?Reference=2317666' AS path;\n"
        ),
    }
    assert state_table["id"] == "state_monthly_visitor_stats"
    assert state_table["ref"] == "odd.nps.latest.state_monthly_visitor_stats"
    assert state_table["validations"][0]["id"] == "odd.nps.latest.state_monthly_visitor_stats"
    assert monthly_table["id"] == "monthly_visitor_stats"
    assert monthly_table["ref"] == "odd.nps.latest.monthly_visitor_stats"
    assert monthly_table["validations"][0]["id"] == "odd.nps.latest.monthly_visitor_stats"
    assert "read_csv_auto" in rendered_metadata
    assert "from odd.nps.latest.state_monthly_visitor_stats" in rendered_metadata
    assert "from odd.nps.latest.monthly_visitor_stats" in rendered_metadata
    assert "stateid = 'ak'" in rendered_metadata
    assert "unitcode = 'alag'" in rendered_metadata
    assert "compact nps visitor-use statistic codes" in rendered_metadata
    assert "tens of mb" in rendered_metadata


def test_project_usgs_gnis_uses_geopackage_domestic_names_metadata() -> None:
    registry = load_project_registry()
    source = next(source for source in registry["sources"] if source["id"] == "usgs.gnis.domestic-names")
    table = source["tables"][0]
    validation = table["validations"][0]
    rendered_metadata = "\n".join(
        [
            source["name"],
            source["authority"],
            source["attribution"],
            table["description"],
            "\n".join(table.get("ask_for", [])),
            "\n".join(table.get("warnings", [])),
            "\n".join(table.get("columns_hint", {}).values()),
            validation["direct_sql"],
            validation["odd_sql"],
            source["discovery"]["discover_sql"],
        ]
    ).casefold()

    assert source["status"] == "candidate"
    assert source["source_type"] == "other"
    assert source["authority"] == "U.S. Geological Survey / U.S. Board on Geographic Names"
    assert source["requirements"] == {"duckdb_extensions": ["spatial"]}
    assert "duckdb" not in source
    assert "description" not in source
    assert "homepage" not in source
    assert "ai" not in source
    assert table["id"] == "domestic_names"
    assert table["ref"] == "odd.usgs_gnis.latest.domestic_names"
    assert validation["id"] == table["ref"]
    assert "ST_Read(" in validation["direct_sql"]
    assert "layer = 'DomesticNames'" in validation["direct_sql"]
    assert "FROM odd.usgs_gnis.latest.domestic_names" in validation["odd_sql"]
    assert source["discovery"] == {
        "namespace": "odd.usgs_gnis.latest",
        "discover_sql": (
            "SELECT 'domestic_names' AS name,\n"
            "       'st_read' AS reader,\n"
            "       '/vsizip/vsicurl/https://prd-tnm.s3.amazonaws.com/StagedProducts/GeographicNames/FullModel/Gazetteer_AS_GPKG.zip/Gazetteer_AS_GPKG.gpkg' AS path,\n"
            "       'DomesticNames' AS layer;\n"
        ),
    }
    assert "state or territory" in table["ask_for"]
    assert "feature class" in table["ask_for"]
    assert "geopackage downloads contain multiple layers" in rendered_metadata
    assert "american samoa" in rendered_metadata
    assert "feature_id 1388627" in rendered_metadata
    assert "domesticnames" in rendered_metadata


def test_project_noaa_coops_water_level_observations_uses_parameterized_public_csv_api_metadata() -> None:
    registry = load_project_registry()
    source = next(source for source in registry["sources"] if source["id"] == "noaa.coops.water-level-observations")
    table = source["tables"][0]
    rendered_metadata = "\n".join(
        [
            source["name"],
            source["authority"],
            source["attribution"],
            table["description"],
            "\n".join(table.get("ask_for", [])),
            "\n".join(table.get("warnings", [])),
            "\n".join(table.get("columns_hint", {}).values()),
            table["validations"][0]["direct_sql"],
            table["validations"][0]["odd_sql"],
            source["discovery"]["discover_sql"],
        ]
    ).casefold()

    assert source["status"] == "candidate"
    assert source["source_type"] == "other"
    assert source["authority"] == "NOAA National Ocean Service Center for Operational Oceanographic Products and Services"
    assert source["requirements"] == {"duckdb_extensions": ["httpfs"]}
    assert "duckdb" not in source
    assert "description" not in source
    assert "homepage" not in source
    assert "ai" not in source
    assert table["id"] == "hourly_heights"
    assert table["ref"] == "odd.noaa_coops.latest.hourly_heights"
    assert table["validations"][0]["id"] == "odd.noaa_coops.latest.hourly_heights"
    assert "read_csv_auto" in table["validations"][0]["direct_sql"]
    assert "FROM odd.noaa_coops.latest.hourly_heights" in table["validations"][0]["odd_sql"]
    assert source["discovery"] == {
        "namespace": "odd.noaa_coops.latest",
        "discover_sql": (
            "SELECT 'hourly_heights' AS name,\n"
            "       'read_csv_auto' AS reader,\n"
            "       'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date=20200101&end_date=20200102&station=8518750&product=hourly_height&datum=MLLW&time_zone=gmt&units=metric&format=csv&application=open_data_duck' AS path;\n"
        ),
    }
    assert "station id" in table["ask_for"]
    assert "datum" in table["ask_for"]
    assert "parameterized api endpoint" in rendered_metadata
    assert "date-range limits" in rendered_metadata
    assert "preliminary and verified products differ" in rendered_metadata
    assert "api.tidesandcurrents.noaa.gov/api/prod/datagetter" in rendered_metadata
    assert "station=8518750" in rendered_metadata
    assert "product=hourly_height" in rendered_metadata
    assert "datum=mllw" in rendered_metadata
    assert "48 hourly rows" in rendered_metadata
    assert "load stac" not in rendered_metadata
    assert "install stac" not in rendered_metadata


def test_project_nasa_exoplanet_archive_uses_bounded_tap_csv_facade_metadata() -> None:
    registry = load_project_registry()
    source = next(source for source in registry["sources"] if source["id"] == "nasa.exoplanet-archive.pscomppars")
    table = source["tables"][0]
    validation = table["validations"][0]
    rendered_metadata = "\n".join(
        [
            source["name"],
            source["authority"],
            source["attribution"],
            table["description"],
            "\n".join(table.get("ask_for", [])),
            "\n".join(table.get("warnings", [])),
            "\n".join(table.get("columns_hint", {}).values()),
            validation["direct_sql"],
            validation["odd_sql"],
            source["discovery"]["discover_sql"],
        ]
    ).casefold()

    assert source["status"] == "candidate"
    assert source["source_type"] == "other"
    assert source["license_url"] == "https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html"
    assert source["requirements"] == {"duckdb_extensions": ["httpfs"]}
    assert "duckdb" not in source
    assert "description" not in source
    assert "homepage" not in source
    assert "ai" not in source
    assert table["id"] == "planetary_systems_composite"
    assert table["ref"] == "odd.nasa_exoplanet_archive.latest.planetary_systems_composite"
    assert validation["id"] == table["ref"]
    assert "read_csv_auto('https://exoplanetarchive.ipac.caltech.edu/TAP/sync" in validation["direct_sql"]
    assert "FROM odd.nasa_exoplanet_archive.latest.planetary_systems_composite" in validation["odd_sql"]
    assert source["discovery"] == {
        "namespace": "odd.nasa_exoplanet_archive.latest",
        "discover_sql": (
            "SELECT 'planetary_systems_composite' AS name,\n"
            "       'read_csv_auto' AS reader,\n"
            "       'https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select%20pl_name%2Chostname%2Cdiscoverymethod%2Cdisc_year%2Cpl_rade%2Cpl_bmasse%20from%20pscomppars%20order%20by%20pl_name&format=csv' AS path;\n"
        ),
    }
    assert "planet name or host name" in table["ask_for"]
    assert any("whether composite defaults are acceptable" in item for item in table["ask_for"])
    assert "tap queries must stay bounded" in rendered_metadata
    assert "select=* full-table scans" in rendered_metadata
    assert "kepler-22 b" in rendered_metadata
    assert "pl_rade=2.1" in rendered_metadata
    assert "pscomppars" in rendered_metadata


def test_search_sources_matches_terms_and_filters(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    matches = search_sources(registry_path, "example parquet", source_type="parquet", status="candidate")

    assert [source.id for source in matches] == ["example.source"]


def test_search_sources_matches_table_first_metadata(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    matches = search_sources(registry_path, "fixture rows")

    assert [source.id for source in matches] == ["example.source"]


def test_source_ai_dict_exposes_table_metadata_without_sql_by_default(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    payload = source.to_ai_dict(include_sql=False)

    assert payload["tables"][0]["validations"][0]["id"] == "odd.example.latest.rows"
    assert payload["tables"][0]["ai_capabilities"]["grain"] == "one fixture row"
    assert "direct_sql" not in payload["tables"][0]["validations"][0]
    assert "odd_sql" not in payload["tables"][0]["validations"][0]
    assert "duckdb" not in payload


def test_render_ai_catalog_maps_schema_org_and_odd_capabilities(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    catalog = yaml.safe_load(render_ai_catalog_json([source]))
    dataset = catalog["dataset"][0]
    table = dataset["hasPart"][0]

    assert catalog["@type"] == "DataCatalog"
    assert dataset["license"] == "https://example.com/license"
    assert table["@type"] == "Dataset"
    assert table["spatialCoverage"] == "fixture space"
    assert table["variableMeasured"][0]["name"] == "fixture value"
    assert table["odd:aiCapabilities"]["safe_operations"] == ["rank", "compare"]
    assert table["odd:aiCapabilities"]["missing_for_questions"][0]["missing_source_families"] == ["production source"]


def test_render_index_outputs_pretty_text_markdown_and_json(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    text = render_index_text([source])
    markdown = render_index_markdown([source])
    json_output = render_index_json([source])

    assert "Open Data Duck source index" in text
    assert "Example rows" in text
    assert "### `example.source`" in markdown
    assert "Ask for: limit" in markdown
    assert "Warnings: Fixture only." in markdown
    assert "SELECT id FROM odd.example.latest.rows" in markdown
    assert '\"source_count\": 1' in json_output


def test_render_source_detail_includes_table_usage_and_validation_sql(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    detail = render_source_detail(source)

    assert "Ask for: limit" in detail
    assert "Warnings: Fixture only." in detail
    assert "Columns: id: Stable fixture row id." in detail
    assert "Validation: odd.example.latest.rows" in detail
    assert "SELECT id FROM odd.example.latest.rows" in detail


def test_table_level_validations_drive_rendered_sql(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(MINIMAL_REGISTRY))
    registry_path, schema_path = write_registry(tmp_path, registry)

    assert validate_registry(registry_path, schema_path) == []
    source_obj = find_source(registry_path, "minimal.source")

    assert source_obj is not None
    assert render_source_sql(source_obj) == "SELECT id FROM odd.minimal.latest.rows ORDER BY id LIMIT 5;\n"


def test_write_index_artifacts_creates_markdown_without_json_duplicate(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    output_dir = tmp_path / "docs"

    paths = write_index_artifacts(registry_path, output_dir)

    assert {path.name for path in paths} == {"index.md"}
    assert "Example rows" in (output_dir / "index.md").read_text(encoding="utf-8")
    assert not (output_dir / "index.json").exists()


def test_mcp_server_module_is_import_safe_and_returns_tool_payloads(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    mcp_server = importlib.import_module("odd.mcp_server")

    search_payload = mcp_server.search_registry("fixture", registry_path=registry_path)
    source_payload = mcp_server.get_registry_source("example.source", registry_path=registry_path, include_sql=False)
    sql_payload = mcp_server.get_registry_source_sql("example.source", registry_path=registry_path)

    assert search_payload["count"] == 1
    assert source_payload["tables"][0]["id"] == "rows"
    assert "odd.example.latest.rows" in sql_payload["sql"]
    assert "read_parquet" not in sql_payload["sql"]


def test_search_sources_requires_all_terms(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    matches = search_sources(registry_path, "example absent")

    assert matches == []


def test_find_source_returns_source_by_id(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    source = find_source(registry_path, "example.source")

    assert source is not None
    assert source.name == "Example source"


def test_render_source_sql_prefers_validation_odd_sql_as_example(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    sql = render_source_sql(source)

    assert sql == "SELECT id FROM odd.example.latest.rows ORDER BY id LIMIT 5;\n"
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
    assert "Validation: odd.example.latest.rows" in output
    assert "Example rows" in output


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

    exit_code = main(["search", "absent", "--registry", str(registry_path)])

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
    registry = load_project_registry()
    by_id = {source["id"]: source for source in registry["sources"]}

    for source_id, (pin_variable, namespace) in LATEST_TABLES.items():
        source = by_id[source_id]
        latest = source["release"]["latest"]
        assert latest["resolve_sql"].strip(), source_id
        assert latest["url"] in latest["resolve_sql"], source_id
        assert source["release"]["pinned"]["duckdb_setting"] == pin_variable
        discovery = source["discovery"]
        assert discovery["namespace"] == namespace
        assert re.fullmatch(r"odd\.[a-z0-9_]+\.[a-z0-9_]+", discovery["namespace"])
        assert "{release}" in discovery["discover_sql"], source_id
        assert re.search(r"\bAS name\b", discovery["discover_sql"]), source_id
        assert re.search(r"\bAS reader\b", discovery["discover_sql"]), source_id
        assert re.search(r"\bAS path\b", discovery["discover_sql"]), source_id

    for source in registry["sources"]:
        assert "facades" not in source, source["id"]
        if "discovery" in source:
            assert "release" in source, source["id"]


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
