# Interactive terminal architecture

Open Data Duck's first public "try it" surface is a static, allowlisted SQL generator on GitHub Pages.

## Decision

Ship a terminal-style demo that loads checked-in preset recipes from `site/demo-recipes.json`, lets visitors pick an allowlisted source, and renders the real SQL output generated from the registry by `odd sql`.

This is intentionally not an arbitrary SQL execution environment. It demonstrates the Open Data Duck workflow without turning the project site into an open compute proxy.

## Current proof of concept

The Pages site includes:

- three preset examples: Overture Maps, Census cartographic county boundaries, and NOAA GHCN Daily;
- a terminal-like command/output panel;
- a visible result summary table for the selected source;
- explicit copy that the demo returns generated SQL output rather than executing DuckDB in the page.

The demo is static and works on GitHub Pages with no backend, no third-party script, and no API key.

## Tradeoffs

### Browser-side DuckDB-Wasm

DuckDB-Wasm is the likely next execution path for recipes that are small, CORS-friendly, and safe to run in a visitor's browser.

Benefits:

- static GitHub Pages can host the UI;
- there is no server bill or backend state;
- user data stays in the browser;
- good fit for small public files and generated SQL walkthroughs.

Limits:

- the current `open_data_duck` extension artifact is a Linux x64 native build, not a browser-loadable Wasm extension;
- a real `open_data_duck.duckdb_extension.wasm` would need a separate build and browser-friendly hosting headers;
- remote data reads still depend on browser CORS, available memory, and query size.

### Worker-backed DuckDB runner

A Cloudflare Worker-backed runner is not the first implementation path.

Before using it, the project needs to prove:

- whether DuckDB can run acceptably in the Worker runtime for this workload;
- whether that path uses native DuckDB, DuckDB-Wasm, or a different hosted service;
- whether the Open Data Duck plugin can be packaged and loaded there;
- CPU, memory, bundle-size, cold-start, and network behavior;
- a sandbox model that accepts source/example ids instead of arbitrary SQL.

If this path is revisited, the safer API shape is an allowlisted endpoint that accepts a source id or example id, runs bounded recipes with row/time limits, and returns JSON results.

## Abuse boundary

The current demo prevents network/proxy abuse by never accepting arbitrary SQL and never executing user input. Visitors can only select recipes checked into the repository.

Future execution modes should keep that boundary unless there is a separate sandboxing design and review.
