# AI capability metadata

Open Data Duck uses schema.org as the public discovery layer and keeps analytics semantics in a small ODD-specific block.

The goal is source-led exploration: an agent should inspect the registry, say what questions a source can answer, cite the source correctly, and say when a question needs a missing source family.

## Schema.org mapping

Existing source fields map to schema.org `Dataset` concepts in the generated AI catalog:

| ODD field | schema.org field | Notes |
| --- | --- | --- |
| `source.name` / `table.id` | `name` | Human-readable dataset/table label. |
| `source.id` / `table.ref` | `identifier` / `@id` | Stable ODD identifiers. Non-facade tables use `source_id#table_id`. |
| `source.authority` | `creator` / `publisher` | Stored as an `Organization`. |
| `source.license_url` | `license` | Link to terms or license. |
| `source.attribution` | `citation` | Required citation / attribution text. |
| `table.description` | `description` | What one table row means. |
| `table.schema_org.spatialCoverage` | `spatialCoverage` | Plain text coverage until richer shapes are needed. |
| `table.schema_org.temporalCoverage` | `temporalCoverage` | Release year, date range, or period. |
| `table.schema_org.variableMeasured` | `variableMeasured` | Public, schema.org-native variables. |
| `table.schema_org.measurementTechnique` | `measurementTechnique` | Method or collection technique where useful. |
| `table.ref` | `distribution.contentUrl` | Queryable ODD facade when one exists. |

## ODD analytics metadata

Schema.org is intentionally broad, so table entries can also carry `ai_capabilities`:

- `grain`: the row-level analytic unit.
- `geography_level`: county, tract, station, country, grid cell, etc.
- `join_keys`: fields an agent can use to join to another ODD table.
- `time`: the main time field and time grain.
- `metrics`: measurable values, units, and descriptions.
- `dimensions`: filters/grouping fields.
- `safe_operations`: allowed analysis shapes such as `rank`, `compare`, `correlate`, `map`, `trend`, `summarize`, and `join`.
- `caveats`: warnings that must survive summaries and citations.
- `example_questions`: source-led questions this table can answer.
- `missing_for_questions`: explicit gaps for questions current ODD sources cannot answer.

## Worked example: CDC PLACES county health estimates

`registry/sources.yml` now annotates `socrata.cdc.places-county-2025` / `county_health_estimates` with:

- schema.org `Dataset` metadata for U.S. county coverage, 2025 temporal coverage, PLACES modeled estimates, and CDC small-area estimation.
- ODD analytics metadata with grain `one county, measure, and data-value type estimate row`.
- `locationid` as a county FIPS/GEOID join key to Census county boundaries.
- metrics and dimensions for `data_value`, `measureid`, `locationid`, and `datavaluetypeid`.
- safe operations for ranking, comparison, correlation, mapping, and joins.
- example questions such as comparing Alaska housing insecurity with mental distress by county.
- a known gap saying death-rate-vs-real-estate questions still need mortality and real-estate source families.

Generate the machine-readable catalog with:

```
uv run odd ai-catalog
```

The output is schema.org-aligned JSON-LD-style data with `odd:aiCapabilities` embedded on each table dataset.
