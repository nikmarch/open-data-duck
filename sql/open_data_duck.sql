-- Open Data Duck DuckDB-side schema helpers.
-- This file is intentionally pure SQL so e2e tests can show the public contract
-- exactly as a DuckDB user or future extension wrapper should call it.

CREATE OR REPLACE MACRO open_data_schema(sql_text) AS TABLE
    SELECT
        column_name AS name,
        upper(column_type) AS duckdb_type,
        "null" = 'YES' AS nullable
    FROM (DESCRIBE SELECT * FROM query(sql_text));

CREATE OR REPLACE MACRO open_data_schema_hash(sql_text) AS TABLE
    SELECT sha256(
        string_agg(
            name || ':' || duckdb_type || ':' || coalesce(nullable::VARCHAR, 'UNKNOWN'),
            ','
            ORDER BY name
        )
    ) AS schema_hash
    FROM open_data_schema(sql_text);

CREATE OR REPLACE MACRO open_data_schema_diff(cached_sql_text, current_sql_text) AS TABLE
    WITH
    cached AS (
        SELECT name, duckdb_type
        FROM open_data_schema(cached_sql_text)
    ),
    current_schema AS (
        SELECT name, duckdb_type
        FROM open_data_schema(current_sql_text)
    ),
    missing_columns AS (
        SELECT
            'breaking' AS severity,
            'missing cached column: ' || cached.name AS message
        FROM cached
        ANTI JOIN current_schema USING (name)
    ),
    changed_types AS (
        SELECT
            'breaking' AS severity,
            'column ' || cached.name || ' changed type from ' || cached.duckdb_type || ' to ' || current_schema.duckdb_type AS message
        FROM cached
        JOIN current_schema USING (name)
        WHERE cached.duckdb_type != current_schema.duckdb_type
    ),
    added_columns AS (
        SELECT
            'info' AS severity,
            'added columns: ' || string_agg(current_schema.name, ', ' ORDER BY current_schema.name) AS message
        FROM current_schema
        ANTI JOIN cached USING (name)
        HAVING count(*) > 0
    )
    SELECT severity, message FROM missing_columns
    UNION ALL
    SELECT severity, message FROM changed_types
    UNION ALL
    SELECT severity, message FROM added_columns;
