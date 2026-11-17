from __future__ import annotations

from pathlib import Path

import duckdb  # type: ignore[import-not-found]
import pytest  # type: ignore[import-not-found]

HELPERS_SQL = Path("sql/open_data_duck.sql")
E2E_DIR = Path("tests/e2e")

EXPECTED_ROWS = {
    "schema_inspect.sql": [
        ("id", "INTEGER", True),
        ("name", "VARCHAR", True),
    ],
    "schema_additive_change.sql": [
        ("info", "added columns: name"),
    ],
    "schema_missing_column.sql": [
        ("breaking", "missing cached column: name"),
    ],
    "schema_type_change.sql": [
        ("breaking", "column id changed type from INTEGER to VARCHAR"),
    ],
}


@pytest.mark.parametrize("case_file", sorted(EXPECTED_ROWS))
def test_duckdb_schema_e2e_sql_cases(case_file: str) -> None:
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(HELPERS_SQL.read_text(encoding="utf-8"))
        rows = connection.execute((E2E_DIR / case_file).read_text(encoding="utf-8")).fetchall()
    finally:
        connection.close()

    assert rows == EXPECTED_ROWS[case_file]
