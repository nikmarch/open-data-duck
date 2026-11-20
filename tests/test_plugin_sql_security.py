from __future__ import annotations

from pathlib import Path


CPP_SOURCE = Path("src/open_data_duck_extension.cpp")
SECURITY_DOC = Path("docs/plugin-sql-security.md")


def test_source_controlled_sql_uses_isolated_database_not_caller_session() -> None:
    source = CPP_SOURCE.read_text(encoding="utf-8")

    assert "RunSourceControlledSql" in source
    assert "DuckDB database(nullptr);" in source
    assert "Connection connection(database);" in source
    assert "Connection connection(DatabaseInstance::GetDatabase(context));" not in source
    assert 'RunSourceControlledSql(source, "release resolution", source.latest_resolve_sql)' in source
    assert 'RunSourceControlledSql(source, "table discovery", sql)' in source


def test_source_controlled_sql_guard_blocks_secret_and_mutating_tokens() -> None:
    source = CPP_SOURCE.read_text(encoding="utf-8")

    for token in (
        "attach",
        "load",
        "install",
        "create",
        "copy",
        "set",
        "reset",
        "pragma",
        "getvariable",
        "current_setting",
        "duckdb_settings",
        "duckdb_secrets",
    ):
        assert f'"{token}"' in source
    assert "must be a single statement" in source
    assert "must be a SELECT query" in source


def test_source_sql_security_doc_explains_boundary() -> None:
    doc = SECURITY_DOC.read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "fresh in-memory DuckDB database" in doc
    assert "attached databases" in doc
    assert "temp objects" in doc
    assert "user variables" in doc
    assert "DuckDB secrets" in doc
    assert "single `SELECT`/`WITH` query" in doc
    assert "docs/plugin-sql-security.md" in readme
