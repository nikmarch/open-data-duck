# Current state

## Scope

This map covers the current Open Data Duck repository wiring for:

- Python CLI, registry loading, validation, rendering, and schema inspection.
- The registry-to-generated-header pipeline consumed by the native DuckDB extension.
- Native extension registration, attached catalog views, table discovery, release resolution, and replacement scans.
- Static docs/site generation from the same registry.

It does not describe all files inside the vendored DuckDB submodule. The native extension depends on DuckDB APIs, but the repo-owned architecture lives mainly in `odd/`, `registry/`, `schema/`, `src/`, `scripts/`, `docs/`, `site/`, and `test/sql/`.

## Source-backed component map

### `odd/cli.py`

Responsibility: command-line entrypoint for registry and docs operations.

Key symbols:

- `main(argv)` builds the `argparse` command tree and dispatches each subcommand.
- `_validate()` calls `odd.registry.validate_registry()`.
- `_index()`, `_show()`, `_search()`, and `_sql()` call registry render/search helpers.
- `_generate_index()` calls `odd.registry.write_index_artifacts()`.
- `_generate_site()` calls `odd.registry.write_site_index()`.
- `_generate_extension_registry()` calls `odd.extension_registry.write_extension_registry_header()` or `check_extension_registry_header()`.
- `_schema()` dispatches to schema inspection/check/refresh helpers in `odd.schema_manifest`.

Current pain points:

- One `main()` function owns parser construction and command dispatch for every domain.
- Command names, default paths, and behavior all live in one file.

### `odd/registry.py`

Responsibility: source registry model, loading, search, rendering, site generation, and validation hygiene.

Key symbols:

- `Source` dataclass normalizes a YAML source mapping into runtime fields.
- `ValidationError` formats validation failures.
- `load_yaml()`, `load_json()`, `load_sources()`, `find_source()`, and `search_sources()` own registry reads and lookups.
- `render_source_sql()`, `_first_validation_pair()`, and `_render_validation_pair_sql()` choose validation-pair SQL or legacy query SQL.
- `render_index_text()`, `render_source_detail()`, `render_index_markdown()`, `render_index_json()`, and `render_site_index_html()` render user-facing outputs.
- `write_index_artifacts()` and `write_site_index()` write generated docs/site artifacts.
- `validate_registry()`, `_validate_hygiene()`, `_validate_tables()`, and `_validate_validation_pairs()` enforce schema plus repository-specific rules.

Current pain points:

- `registry.py` mixes four responsibilities: data model, loading/search, rendering, and validation.
- HTML generation for the public site lives next to registry validation rules.
- Validation-pair logic is shared conceptually with the native extension, but only by generated data and tests, not by a small named boundary.

### `odd/extension_registry.py`

Responsibility: render the C++ header that embeds a JSON snapshot of the source registry.

Key symbols:

- `source_to_extension_dict()` chooses which `Source` fields are embedded.
- `build_extension_registry()` wraps sources with schema version and count.
- `render_extension_registry_json()` serializes deterministic JSON.
- `render_extension_registry_header()` writes `REGISTRY_JSON`, `REGISTRY_SCHEMA_VERSION`, and `REGISTRY_SOURCE_COUNT` inside C++ namespaces.
- `write_extension_registry_header()` and `check_extension_registry_header()` are the write/check endpoints used by CLI and tests.

Current pain point:

- Field selection is centralized, which is good, but its contract with `src/open_data_duck_extension.cpp` is implicit.

### `odd/schema_manifest.py`

Responsibility: inspect generated SQL against DuckDB, cache source schemas, and detect breaking schema drift.

Key symbols:

- `SchemaColumn`, `SourceSchema`, `CompatibilityIssue`, `SchemaCheckResult`, and `SchemaManifest` model cached inspection output.
- `inspect_source_schema()` calls `registry.render_source_sql()` then `inspect_sql_schema()`.
- `inspect_sql_schema()` uses DuckDB plus `sql/open_data_duck.sql` helper functions.
- `check_source_schema()` and `compare_schemas()` compare current inspection with cached manifest data.
- `refresh_manifest_for_sources()`, `load_manifest()`, `write_manifest()`, and `load_requested_sources()` support CLI subcommands.

Current pain point:

- Schema inspection uses the same registry SQL rendering path as user-facing CLI SQL. That is good reuse, but renderer changes can affect manifest behavior.

### Engine helper modules

Files:

- `odd/arcgis.py`
- `odd/ckan.py`
- `odd/socrata.py`

Responsibility: small planner/evidence helpers for source-family engine work.

Key symbols:

- ArcGIS: `ArcGISLayerMetadata`, `ArcGISPageRequest`, `ArcGISEngineEvidence`, `plan_pages_from_public_layer()`, `plan_offset_pages()`.
- CKAN: `CatalogResource`, `CKANDirectPathEvidence`, `resources_from_ckan_package()`, `direct_duckdb_resources()`, `render_direct_resource_sql()`.
- Socrata: `SocrataDatasetMetadata`, `SocrataPageRequest`, `SocrataEngineEvidence`, `plan_pages_from_public_dataset()`, `plan_offset_pages()`.

Current state:

- These modules are well separated from the core registry today.
- They are not yet represented as a common engine interface. That is fine now; adding one would be premature unless more source-family automation needs it.

### `odd/mcp_server.py`

Responsibility: optional MCP surface around registry search/source/sql/schema lookup.

Key symbols:

- `search_registry()`, `get_registry_source()`, `get_registry_source_sql()`, and `get_cached_source_schema()` are pure wrappers around registry/schema helpers.
- `create_server()` wires those wrappers into FastMCP tools when the optional `mcp` extra is installed.

### `scripts/build_pages_site.py`

Responsibility: build the static GitHub Pages output.

Key symbol:

- `build_site(output_dir=ROOT / "_site")` copies `site/`, renders `site/index.html` from `registry/sources.yml`, copies brand assets from `docs/assets/brand`, and writes `.nojekyll`.

Current pain point:

- The generated HTML implementation is in `odd.registry.render_site_index_html()`, while the file-copy/deploy shape lives in `scripts/build_pages_site.py`.

### `src/open_data_duck_extension.cpp`

Responsibility: native DuckDB extension runtime.

Major regions:

- Embedded registry parsing: `OpenDataSource`, `ParseEmbeddedRegistry()`, `GetEmbeddedRegistry()`, `FindSource()`, `FindSourceOrThrow()`.
- Source-controlled SQL guardrails: `TokenizeSourceSql()`, `ValidateSourceControlledSql()`, `ValidateSourceExtensionName()`, `RunSourceControlledSql()`.
- SQL recipe and release helpers: `RenderSourceSql()`, `ResolveRelease()`, `DiscoverTables()`.
- Scalar functions: `open_data_duck_ping()`, `open_data_duck_version()`, `open_data_duck_registry_json()`, `open_data_duck_registry_source_count()`, `open_data_sql()`, `open_data_validation_sql()`, `open_data_release()`.
- Table functions: `open_data_sources()`, `open_data_search(query)`, `open_data_tables()`.
- Attached catalog and replacement scans: `OpenDataDuckReplacementScan()`, `OpenDataDuckCatalogViewGenerator`, `OpenDataDuckStorageAttach()`, `OpenDataDuckStorageExtension`.
- Registration: `LoadInternal()`, `OpenDataDuckExtension::Load()`, and `DUCKDB_CPP_EXTENSION_ENTRY(open_data_duck, loader)`.

Current pain points:

- One C++ file contains parsing, security validation, release resolution, table discovery, scalar functions, table functions, replacement scan binding, catalog attach, and registration.
- The file is sectioned clearly, but each section communicates through local structs and static functions in the same translation unit.
- The replacement-scan path depends on discovered table cache behavior and release-resolution cache behavior, so a diagram is needed before splitting.

### `src/include/open_data_duck_registry.generated.hpp`

Responsibility: generated C++ registry artifact.

- Source of truth: `registry/sources.yml`.
- Generated by: `uv run odd generate-extension-registry` through `odd.extension_registry.write_extension_registry_header()`.
- Consumed by: `src/open_data_duck_extension.cpp` through `open_data_duck::REGISTRY_JSON`, `REGISTRY_SCHEMA_VERSION`, and `REGISTRY_SOURCE_COUNT`.

### SQL tests

Files:

- `test/sql/open_data_duck.test`
- `test/sql/open_data_duck_network.test`

Relevant covered surfaces:

- Extension load/ping/version/registry JSON.
- `open_data_sources()` and `open_data_search()` result shape.
- `open_data_sql()` and `open_data_validation_sql()` behavior.
- `open_data_release()` behavior and error paths.
- `ATTACH ... (TYPE open_data_duck)` exposing `odd.index` and `odd.tables`.
- Network-backed table discovery and facade reads in the network test.

## Main communication paths

### Python CLI and registry path

1. `odd.cli.main()` parses a command.
2. The command handler calls `odd.registry`, `odd.extension_registry`, or `odd.schema_manifest`.
3. `odd.registry.load_sources()` reads `registry/sources.yml` into `Source` objects.
4. Render/check commands produce docs, JSON, SQL, site HTML, validation errors, or generated C++ headers.

Diagram: [CLI registry sequence](diagrams/cli-registry-sequence.mmd).

### Registry to native extension artifact path

1. `registry/sources.yml` is the source of truth.
2. `uv run odd generate-extension-registry` dispatches through `odd.cli._generate_extension_registry()`.
3. `odd.extension_registry.render_extension_registry_header()` embeds selected registry fields as JSON.
4. `src/include/open_data_duck_registry.generated.hpp` is compiled into the extension.
5. `src/open_data_duck_extension.cpp` parses `open_data_duck::REGISTRY_JSON` at runtime.

Diagram: [Registry to extension artifact flow](diagrams/registry-to-extension-flow.mmd).

### Native `odd.<provider>.<release>.<table>` facade path

1. User loads the extension and attaches the storage extension as `odd`.
2. `OpenDataDuckStorageAttach()` creates a virtual Duck catalog.
3. `OpenDataDuckCatalogViewGenerator` exposes `odd.index` and `odd.tables` views.
4. `OpenDataDuckReplacementScan()` catches `odd.index`, `odd.tables`, and `odd.<namespace>.<table>` references.
5. For data table references, replacement scan calls `DiscoverTables()`.
6. `DiscoverTables()` may call `ResolveRelease()` and then `RunSourceControlledSql()`.
7. The discovered row returns `(name, reader, path)`.
8. Replacement scan binds the configured reader function, currently by constructing a `TableFunctionRef` with `table.reader(table.path)`.

Diagram: [ODD facade and replacement scan flow](diagrams/odd-facade-replacement-scan.mmd).

### Site/docs path

1. `registry/sources.yml` feeds `odd.registry.load_sources()`.
2. `uv run odd generate-index` writes `docs/index.md` through `write_index_artifacts()`.
3. `uv run odd generate-site` writes `site/index.html` through `write_site_index()`.
4. `scripts/build_pages_site.py` copies static site assets and renders `_site/index.html` for GitHub Pages.

This relationship is included in [Module dependency map](diagrams/module-dependencies.mmd).

## Important inferred relationships

- The generated-header contract is inferred from matching Python renderer fields in `odd/extension_registry.py` and C++ parser reads in `src/open_data_duck_extension.cpp`. There is no shared schema file specifically for the embedded header payload today.
- The native extension mirrors parts of Python CLI behavior, for example `RenderSourceSql()` says it mirrors `odd.registry.render_source_sql()`. Tests verify behavior, but the implementation is duplicated across Python and C++.
