# Open Data Duck architecture

This directory maps the current Open Data Duck code before larger refactors. It is current-state first: diagrams show how the code is wired today, then `refactor-plan.md` proposes small behavior-preserving cleanup slices.

## Entry points

- [Current state](current-state.md) — source-backed map of Python, registry generation, native extension, and docs/site flows.
- [Refactor plan](refactor-plan.md) — small refactor slices tied to diagram-visible pain points.

## Diagrams

- [Module dependency map](diagrams/module-dependencies.mmd)
- [CLI registry sequence](diagrams/cli-registry-sequence.mmd)
- [Registry to extension artifact flow](diagrams/registry-to-extension-flow.mmd)
- [ODD facade and replacement scan flow](diagrams/odd-facade-replacement-scan.mmd)
- [Schema manifest flow](diagrams/schema-manifest-flow.mmd)

## How to read this

Open the `.mmd` files in a Mermaid renderer, or paste them into a Mermaid preview. The diagrams use real file paths and symbols from the repository. When a relationship is inferred rather than directly called, the text says so.

## Current high-level shape

Open Data Duck has two connected halves:

1. **Python tooling** under `odd/` owns the YAML registry, validation, generated Markdown/site output, schema inspection, and generated C++ registry header.
2. **Native DuckDB extension** under `src/` embeds that generated registry header and exposes SQL functions, `ATTACH ... (TYPE open_data_duck)`, `odd.index`, `odd.tables`, and `odd.<provider>.<release>.<table>` replacement-scan facades.

The main architectural seam is `registry/sources.yml` -> `odd.extension_registry` -> `src/include/open_data_duck_registry.generated.hpp` -> `src/open_data_duck_extension.cpp`.
