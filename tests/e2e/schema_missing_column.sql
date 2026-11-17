-- name: schema_missing_column
-- Removing a cached column is breaking. App refresh/check code should quarantine
-- the source instead of crashing later.

SELECT severity, message
FROM open_data_schema_diff(
    'SELECT 1::INTEGER AS id, ''a''::VARCHAR AS name',
    'SELECT 1::INTEGER AS id'
)
ORDER BY severity, message;
