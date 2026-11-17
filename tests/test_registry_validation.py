from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from odd.cli import main
from odd.registry import validate_registry


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
