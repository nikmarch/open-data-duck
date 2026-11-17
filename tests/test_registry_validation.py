from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from odd.cli import main
from odd.registry import find_source, render_source_sql, search_sources, validate_registry


VALID_REGISTRY = {
    "sources": [
        {
            "id": "example.source",
            "name": "Example source",
            "status": "candidate",
            "source_type": "parquet",
            "authority": "Example Authority",
            "homepage": "https://example.com/data",
            "license_url": "https://example.com/license",
            "attribution": "Credit Example Authority.",
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


@pytest.mark.parametrize(
    ("field_path", "expected_path"),
    [
        (("authority",), "authority"),
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


def test_project_registry_meets_seed_source_targets() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))
    sources = registry["sources"]
    source_types = [source["source_type"] for source in sources]
    source_ids = [source["id"] for source in sources]

    assert "overture.maps.release" in source_ids
    assert source_types.count("stac") >= 3
    assert source_types.count("arcgis") >= 3
    assert sum(source_id.startswith("aws.") for source_id in source_ids) >= 3


def test_seed_sources_include_required_query_metadata() -> None:
    registry = yaml.safe_load(Path("registry/sources.yml").read_text(encoding="utf-8"))

    for source in registry["sources"]:
        assert source["license_url"].startswith("https://"), source["id"]
        assert source["attribution"].strip(), source["id"]
        assert source["duckdb"]["example_query"].strip(), source["id"]
        assert source["duckdb"]["validation_query"].strip(), source["id"]


def test_search_sources_matches_terms_and_filters(tmp_path: Path) -> None:
    registry_path, _schema_path = write_registry(tmp_path, VALID_REGISTRY)

    matches = search_sources(registry_path, "example parquet", source_type="parquet", status="candidate")

    assert [source.id for source in matches] == ["example.source"]


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
