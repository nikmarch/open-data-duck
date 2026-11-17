from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

from odd.registry import find_source, render_source_sql


REGISTRY_PATH = Path("registry/sources.yml")


def execute_duckdb_sql(sql: str) -> None:
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(sql)
    finally:
        connection.close()


def test_rendered_validation_sql_executes_in_real_duckdb_for_simple_source(tmp_path: Path) -> None:
    registry_path = tmp_path / "sources.yml"
    registry_path.write_text(
        """
sources:
  - id: local.simple
    name: Local simple source
    description: Minimal local source used to prove rendered SQL executes in DuckDB.
    status: candidate
    source_type: other
    authority: Local test
    homepage: https://example.com
    license_url: https://example.com/license
    attribution: Local test fixture.
    duckdb:
      extensions: []
      example_query: |
        SELECT 1 AS ok;
      validation_query: |
        SELECT 1 AS ok;
""".strip(),
        encoding="utf-8",
    )
    source = find_source(registry_path, "local.simple")

    assert source is not None
    execute_duckdb_sql(render_source_sql(source, validation=True))


def test_project_overture_source_does_not_depend_on_missing_community_extension() -> None:
    source = find_source(REGISTRY_PATH, "overture.maps.release")

    assert source is not None
    rendered_sql = render_source_sql(source).casefold()
    assert "install overture from community" not in rendered_sql
    assert "load overture" not in rendered_sql


def test_duckdb_dependency_is_available() -> None:
    connection = duckdb.connect(":memory:")
    try:
        assert connection.execute("SELECT 42").fetchone() == (42,)
    finally:
        connection.close()


@pytest.mark.skipif(
    os.environ.get("ODD_DUCKDB_NETWORK_TESTS") != "1",
    reason="set ODD_DUCKDB_NETWORK_TESTS=1 to install/load DuckDB extensions from remote repositories",
)
def test_real_duckdb_can_install_and_load_supported_extensions() -> None:
    connection = duckdb.connect(":memory:")
    try:
        for statement in (
            "INSTALL httpfs;",
            "LOAD httpfs;",
            "INSTALL spatial;",
            "LOAD spatial;",
            "INSTALL stac FROM community;",
            "LOAD stac;",
        ):
            connection.execute(statement)

        row = connection.execute(
            "SELECT count(*) FROM duckdb_functions() WHERE function_name = 'STAC_Collections'"
        ).fetchone()
        assert row is not None
        assert row[0] >= 1
    finally:
        connection.close()
