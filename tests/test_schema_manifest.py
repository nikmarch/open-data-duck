from __future__ import annotations

import json
from pathlib import Path

import yaml

from odd.cli import main
from odd.mcp_server import get_cached_source_schema
from odd.registry import find_source
from odd.schema_manifest import (
    SchemaColumn,
    SourceSchema,
    compare_schemas,
    inspect_sql_schema,
    load_manifest,
)


def write_registry(tmp_path: Path, example_query: str) -> Path:
    registry = {
        "sources": [
            {
                "id": "local.schema",
                "name": "Local schema source",
                "description": "Local source used to test DuckDB schema discovery.",
                "status": "candidate",
                "source_type": "other",
                "authority": "Local test",
                "homepage": "https://example.com",
                "license_url": "https://example.com/license",
                "attribution": "Local test fixture.",
                "duckdb": {
                    "extensions": [],
                    "example_query": example_query,
                    "validation_query": "SELECT 1 AS ok;",
                },
            }
        ]
    }
    path = tmp_path / "sources.yml"
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    return path


def test_inspect_sql_schema_uses_duckdb_describe_for_final_query() -> None:
    columns = inspect_sql_schema(
        "CREATE TEMP TABLE rows AS SELECT 1::INTEGER AS id, 'a'::VARCHAR AS name; "
        "SELECT id, name FROM rows;"
    )

    assert columns == [
        SchemaColumn(name="id", duckdb_type="INTEGER", nullable=True),
        SchemaColumn(name="name", duckdb_type="VARCHAR", nullable=True),
    ]


def test_compare_schemas_accepts_additive_columns() -> None:
    cached = SourceSchema.from_columns("local.schema", [SchemaColumn("id", "INTEGER")])
    current = SourceSchema.from_columns(
        "local.schema",
        [SchemaColumn("id", "INTEGER"), SchemaColumn("name", "VARCHAR")],
    )

    issues = compare_schemas("local.schema", cached, current)

    assert not any(issue.severity == "breaking" for issue in issues)
    assert [issue.message for issue in issues] == ["added columns: name"]


def test_compare_schemas_rejects_missing_cached_columns() -> None:
    cached = SourceSchema.from_columns(
        "local.schema",
        [SchemaColumn("id", "INTEGER"), SchemaColumn("name", "VARCHAR")],
    )
    current = SourceSchema.from_columns("local.schema", [SchemaColumn("id", "INTEGER")])

    issues = compare_schemas("local.schema", cached, current)

    assert [issue.message for issue in issues] == ["missing cached column: name"]
    assert all(issue.severity == "breaking" for issue in issues)


def test_compare_schemas_rejects_incompatible_type_changes() -> None:
    cached = SourceSchema.from_columns("local.schema", [SchemaColumn("id", "INTEGER")])
    current = SourceSchema.from_columns("local.schema", [SchemaColumn("id", "VARCHAR")])

    issues = compare_schemas("local.schema", cached, current)

    assert [issue.message for issue in issues] == ["column id changed type from INTEGER to VARCHAR"]
    assert all(issue.severity == "breaking" for issue in issues)


def test_cli_schema_inspect_prints_discovered_schema(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    registry_path = write_registry(tmp_path, "SELECT 1::INTEGER AS id, 'a'::VARCHAR AS name;")

    exit_code = main(["schema", "inspect", "local.schema", "--registry", str(registry_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["source_id"] == "local.schema"
    assert payload["status"] == "ok"
    assert payload["columns"] == [
        {"duckdb_type": "INTEGER", "name": "id", "nullable": True},
        {"duckdb_type": "VARCHAR", "name": "name", "nullable": True},
    ]


def test_cli_schema_refresh_writes_manifest_and_check_passes(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    registry_path = write_registry(tmp_path, "SELECT 1::INTEGER AS id;")
    manifest_path = tmp_path / "source-manifest.json"

    refresh_exit = main(
        [
            "schema",
            "refresh",
            "local.schema",
            "--registry",
            str(registry_path),
            "--manifest",
            str(manifest_path),
        ]
    )
    refresh_output = capsys.readouterr().out
    check_exit = main(
        [
            "schema",
            "check",
            "local.schema",
            "--registry",
            str(registry_path),
            "--manifest",
            str(manifest_path),
        ]
    )
    check_output = capsys.readouterr().out

    manifest = load_manifest(manifest_path)
    assert refresh_exit == 0
    assert "local.schema: ok" in refresh_output
    assert manifest.sources["local.schema"].columns == [SchemaColumn("id", "INTEGER", nullable=True)]
    assert check_exit == 0
    assert "local.schema: ok" in check_output
    assert get_cached_source_schema("local.schema", manifest_path=manifest_path)["columns"] == [
        {"duckdb_type": "INTEGER", "name": "id", "nullable": True}
    ]


def test_cli_schema_check_fails_when_required_cached_column_disappears(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    registry_path = write_registry(tmp_path, "SELECT 1::INTEGER AS id, 'a'::VARCHAR AS name;")
    manifest_path = tmp_path / "source-manifest.json"
    assert main(["schema", "refresh", "local.schema", "--registry", str(registry_path), "--manifest", str(manifest_path)]) == 0
    capsys.readouterr()
    registry_path = write_registry(tmp_path, "SELECT 1::INTEGER AS id;")

    exit_code = main(["schema", "check", "local.schema", "--registry", str(registry_path), "--manifest", str(manifest_path)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "local.schema: breaking" in output
    assert "missing cached column: name" in output


def test_source_schema_failed_status_contains_inspection_errors(tmp_path: Path) -> None:
    registry_path = write_registry(tmp_path, "SELECT * FROM missing_table;")
    source = find_source(registry_path, "local.schema")

    assert source is not None
    from odd.schema_manifest import inspect_source_schema

    schema = inspect_source_schema(source)

    assert schema.status == "failed"
    assert schema.error is not None
    assert "missing_table" in schema.error
