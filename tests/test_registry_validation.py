from __future__ import annotations

from pathlib import Path
import importlib

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


def test_validate_registry_accepts_connector_blocked_status(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    registry["sources"][0]["status"] = "connector-blocked"
    registry_path, schema_path = write_registry(tmp_path, registry)

    assert validate_registry(registry_path, schema_path) == []


@pytest.mark.parametrize(
    ("field_path", "expected_path"),
    [
        (("authority",), "authority"),
        (("description",), "description"),
        (("license_url",), "license_url"),
        (("attribution",), "attribution"),
        (("duckdb", "example_query"), "duckdb.example_query"),
        (("duckdb", "validation_query"), "duckdb.validation_query"),
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


def test_project_census_cartographic_counties_use_direct_spatial_file_recipe() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    source = next(source for source in registry["sources"] if source["id"] == "census.cartographic.county-boundaries")
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
    assert "/vsizip/vsicurl/https://www2.census.gov/geo/tiger/genz2025/shp/cb_2025_us_county_20m.zip/cb_2025_us_county_20m.shp" in rendered_sql
    assert "count(*) = 3222" in rendered_sql
    assert "arcgis_query" not in rendered_sql


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

    assert source["release"]["latest"]["url"] == "https://docs.overturemaps.org/release-calendar/"
    assert source["release"]["pinned"]["duckdb_setting"] == "overture_release"
    assert source["release"]["pinned"]["example"]

    examples = source["duckdb"]["examples"]
    assert "read_parquet" in examples["places_direct_s3"]
    assert "overturemaps-us-west-2" in examples["places_direct_s3"]

    validation_query = source["duckdb"]["validation_query"]
    assert "read_parquet" in validation_query
    assert "overturemaps-us-west-2" in validation_query
    assert "read_overture_places" not in validation_query


def test_seed_sources_include_required_query_metadata() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))

    for source in registry["sources"]:
        assert source["description"].strip(), source["id"]
        assert source["license_url"].startswith("https://"), source["id"]
        assert source["attribution"].strip(), source["id"]
        assert source.get("ai", {}).get("summary", "").strip(), source["id"]
        assert source["duckdb"]["example_query"].strip(), source["id"]
        assert source["duckdb"]["validation_query"].strip(), source["id"]


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
    assert '\"source_count\": 1' in json_output


def test_render_source_detail_includes_ai_usage(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    detail = render_source_detail(source)

    assert "AI usage:" in detail
    assert "Use for registry tests" in detail


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
    assert "read_parquet" in sql_payload["sql"]


def test_search_sources_requires_all_terms(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    matches = search_sources(registry_path, "example missing")

    assert matches == []


def test_find_source_returns_source_by_id(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    source = find_source(registry_path, "example.source")

    assert source is not None
    assert source.name == "Example source"


def test_render_source_sql_includes_install_and_example_query(tmp_path: Path) -> None:
    registry = yaml.safe_load(yaml.safe_dump(VALID_REGISTRY))
    registry["sources"][0]["duckdb"]["install"] = "INSTALL httpfs;"
    registry_path, _schema_path = write_registry(tmp_path, registry)
    source = find_source(registry_path, "example.source")

    assert source is not None
    sql = render_source_sql(source)

    assert "INSTALL httpfs;" in sql
    assert "read_parquet" in sql


def test_render_source_sql_can_print_validation_query(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)
    source = find_source(registry_path, "example.source")

    assert source is not None
    sql = render_source_sql(source, validation=True, include_install=False)

    assert sql == "SELECT 1;\n"


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
    assert "read_parquet" in capsys.readouterr().out


def test_cli_sql_exits_nonzero_for_unknown_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    exit_code = main(["sql", "missing.source", "--registry", str(registry_path)])

    assert exit_code == 1
    assert "Source not found: missing.source" in capsys.readouterr().out
