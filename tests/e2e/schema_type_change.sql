-- name: schema_type_change
-- Changing a cached column type is breaking.

SELECT severity, message
FROM open_data_schema_diff(
    'SELECT 1::INTEGER AS id',
    'SELECT ''1''::VARCHAR AS id'
)
ORDER BY severity, message;
