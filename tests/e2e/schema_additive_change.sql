-- name: schema_additive_change
-- Additive upstream columns are safe. They should report info only.

SELECT severity, message
FROM open_data_schema_diff(
    'SELECT 1::INTEGER AS id',
    'SELECT 1::INTEGER AS id, ''a''::VARCHAR AS name'
)
ORDER BY severity, message;
