# Refactor plan

This plan is intentionally small-slice and behavior-preserving. It comes from the diagrammed current state, not from a broad rewrite goal.

## Ground rules

- Keep `registry/sources.yml` as the source of truth.
- Keep generated artifacts generated; do not hand-edit `src/include/open_data_duck_registry.generated.hpp`.
- Keep native extension behavior covered by `test/sql/open_data_duck.test` and network-sensitive behavior isolated in `test/sql/open_data_duck_network.test`.
- Do not invent a generic engine framework until at least two source-family paths need the same runtime shape.

## Slice 1: Split registry rendering from registry validation — done

Result:

- `odd/registry.py` is now a compatibility facade.
- `odd/registry_model.py` owns `Source`, `ValidationError`, YAML/JSON loading, source lookup, and search.
- `odd/registry_renderers.py` owns SQL, text, Markdown, JSON, site HTML, and docs/site artifact rendering.
- `odd/registry_validation.py` owns JSON Schema plus registry hygiene checks.
- Internal callers now import focused modules directly where practical; tests and external callers can still import from `odd.registry`.

Behavior expected to stay the same:

- CLI command output.
- MCP wrapper output.
- Generated `docs/index.md` and `site/index.html`.
- Registry validation errors.

Follow-up watchpoint:

- Keep the facade only as a compatibility boundary. New internal code should depend on the focused modules.

## Slice 2: Extract CLI parser construction from command execution — done

Result:

- `odd.cli.build_parser()` now owns the `argparse` command tree.
- `odd.cli.main()` parses arguments only, then calls `_dispatch()`.
- `_dispatch()` owns top-level command routing to the existing small handlers.
- Schema subcommand dispatch remains in `_schema()` because it is still small and behavior-specific.

Behavior expected to stay the same:

- CLI commands and flags.
- Exit codes.
- Printed output.

Follow-up watchpoint:

- If schema subcommands grow, move them into a small schema CLI module later.

## Slice 3: Name the generated extension registry contract

Problem visible in diagram:

- The registry-to-extension flow depends on a Python-selected field set and a C++ parser, but no named contract document or schema exists for the embedded payload.

Files touched:

- `odd/extension_registry.py`
- `src/open_data_duck_extension.cpp`
- Candidate doc: `docs/architecture/embedded-registry-contract.md` or schema fixture under `schema/`
- Tests that check generated header drift.

New/renamed responsibility:

- Give the embedded payload an explicit contract name, for example `ExtensionRegistryPayload` in docs/tests.
- Add a small Python test that asserts the emitted JSON fields match what the C++ parser expects.
- Consider a generated compact JSON fixture for tests, not for runtime.

Behavior expected to stay the same:

- Header content may change only if formatting/contract tests require it; runtime behavior should not.

Tests/verification:

- `uv run odd generate-extension-registry --check`
- `uv run pytest tests/test_registry_validation.py`

Risk:

- Medium only if header formatting changes. Prefer tests/doc first.

## Slice 4: Split native extension runtime by responsibility

Problem visible in diagram:

- `src/open_data_duck_extension.cpp` is the clearest god-file candidate. It owns registry parsing, SQL sandboxing, release/table discovery, scalar functions, table functions, replacement scan, catalog attach, and registration.

Files touched:

- `src/open_data_duck_extension.cpp`
- New candidates under `src/` or `src/include/`:
  - `open_data_duck_registry.cpp/.hpp`
  - `open_data_duck_sql_sandbox.cpp/.hpp`
  - `open_data_duck_tables.cpp/.hpp`
  - `open_data_duck_catalog.cpp/.hpp`

New/renamed responsibility:

- First extraction should be the embedded registry parser and lookup helpers: `OpenDataSource`, `ParseEmbeddedRegistry()`, `GetEmbeddedRegistry()`, `FindSourceOrThrow()`.
- Second extraction should be source-controlled SQL guardrails: `ValidateSourceControlledSql()`, `ValidateSourceExtensionName()`, `RunSourceControlledSql()`.
- Leave `LoadInternal()` and DuckDB registration in the original file until the extracted boundaries are stable.

Behavior expected to stay the same:

- SQL function names and output.
- `ATTACH ... (TYPE open_data_duck)` behavior.
- Replacement scan behavior.

Tests/verification:

- `make test-extension-sql`
- If native build is too slow locally, at minimum compile the extension target and run `test/sql/open_data_duck.test`.

Risk:

- Medium. DuckDB C++ APIs and static initialization can be picky. Extract one boundary per PR.

## Slice 5: Make release/table discovery a named native service

Problem visible in diagram:

- `OpenDataDuckReplacementScan()` depends on `DiscoverTables()`, which depends on `ResolveRelease()` and `RunSourceControlledSql()`. The relationship is correct but implicit; query behavior depends on cache keys and release pinning.

Files touched:

- `src/open_data_duck_extension.cpp`
- Candidate files from Slice 4 if already extracted.
- `test/sql/open_data_duck.test`
- `test/sql/open_data_duck_network.test`

New/renamed responsibility:

- Introduce a small native table-discovery boundary around `ResolveRelease()` and `DiscoverTables()`.
- Make cache key construction and pinned-release behavior visible in that boundary.

Behavior expected to stay the same:

- `open_data_release()` precedence: pinned variable, cached release, `release.latest.resolve_sql`.
- `odd.tables` and facade reads discover the same table rows.

Tests/verification:

- Existing sqllogictests around `open_data_release()`.
- Network sqllogictest for `odd.tables` and facade reads.

Risk:

- Medium. This touches network-backed behavior and cache semantics.

## Slice 6: Keep engine helper modules boring until runtime integration needs them

Problem visible in diagram:

- `odd/arcgis.py`, `odd/ckan.py`, and `odd/socrata.py` are parallel but not wired through one interface. That can look tempting to abstract, but they are currently small and source-family-specific.

Files touched:

- None for now unless a concrete feature needs it.

New/renamed responsibility:

- No immediate abstraction.
- If another engine feature needs the same evidence/planning shape, introduce a small protocol after the second real use.

Behavior expected to stay the same:

- Existing helper tests and source-family planning behavior.

Tests/verification:

- Existing tests that cover these modules.

Risk:

- Low if deferred. High if abstracted prematurely.

## Recommended order

1. Slice 1: split registry rendering/validation/model. Done.
2. Slice 2: extract CLI parser construction. Done.
3. Slice 3: name/test generated extension registry contract.
4. Slice 4: extract native registry parser/lookup from `src/open_data_duck_extension.cpp`.
5. Slice 5: extract native release/table discovery boundary.
6. Slice 6: revisit engine helper abstraction only after a concrete need.

This keeps the first PRs low-risk Python cleanup before touching DuckDB C++ runtime behavior.
