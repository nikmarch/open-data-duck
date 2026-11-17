-- name: schema_inspect
-- This is the public DuckDB contract: load the SQL helpers, then call
-- open_data_schema() with the source query.

SELECT name, duckdb_type, nullable
FROM open_data_schema('SELECT 1::INTEGER AS id, ''a''::VARCHAR AS name')
ORDER BY name;
