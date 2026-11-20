from __future__ import annotations

from pathlib import Path


CPP_SOURCE = Path("src/open_data_duck_extension.cpp")
SECURITY_DOC = Path("docs/plugin-sql-security.md")


def test_source_controlled_sql_uses_separate_connection_and_not_caller_session_functions() -> None:
    source = CPP_SOURCE.read_text(encoding="utf-8")

    assert "RunSourceControlledSql" in source
    assert "Connection connection(DatabaseInstance::GetDatabase(context));" in source
    assert 'RunSourceControlledSql(context, source, "release resolution", source.latest_resolve_sql)' in source
    assert 'RunSourceControlledSql(context, source, "table discovery", sql)' in source
    assert '"getvariable"' in source
    assert '"duckdb_secrets"' in source


def test_source_controlled_sql_loads_declared_extensions_inside_discovery_connection() -> None:
    source = CPP_SOURCE.read_text(encoding="utf-8")

    assert "for (auto &extension : source.extensions)" in source
    assert "ValidateSourceExtensionName(source.id, extension)" in source
    assert 'connection.Query("INSTALL " + extension_name)' in source
    assert 'connection.Query("LOAD " + extension_name)' in source
    assert "could not load DuckDB extension" in source


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

    assert "separate DuckDB connection" in doc
    assert "declared DuckDB extensions" in doc
    assert "attach new databases" in doc
    assert "mutate caller state" in doc
    assert "session/secret inspection APIs" in doc
    assert "single `SELECT`/`WITH` query" in doc
    assert "docs/plugin-sql-security.md" in readme
