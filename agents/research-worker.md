# Research worker brief

Purpose: find authoritative public data sources that can become Open Data Duck registry entries.

Hard rules:

- Create GitHub issues only. Do not auto-merge sources.
- Do not add private, paid, key-gated, or gray-area scraped sources.
- Every candidate must include publisher, authority URL, license/terms URL, attribution requirement, source type, at least one proposed table, and a proposed DuckDB query path.
- Prefer official catalog/API endpoints over blog posts or mirrors.
- If license is unclear, create a `needs-license-review` issue and mark it blocked.
- If an engine is missing or immature, search for an existing `engine` issue first.
- If no matching issue exists, create one with the `engine` label instead of pretending the source is queryable.
- Link blocked source-candidate issues or PRs to the relevant engine issue and mark the registry entry `connector-blocked` until the engine path has real public-source smoke coverage.

Good source families:

- STAC APIs and catalogs
- ArcGIS FeatureServer / MapServer open layers
- Overture Maps releases
- Source Cooperative repositories
- AWS Registry of Open Data datasets
- CKAN / DCAT government portals
- Socrata open-data portals
- Public GeoParquet / Parquet datasets

Issue shape:

```markdown
## Source
- Publisher:
- Homepage:
- License / terms:
- Attribution:
- Source type:

## DuckDB path
- Existing engine/extension:
- Example query:
- Validation query:

## Tables
- Table id:
- Table ref (if queryable as an ODD facade):
- One row means:
- Ask for before writing SQL:
- Warnings / caveats:
- Validation id linked to this table ref:

## Review notes
- Why authoritative:
- Risks / blockers:
```
