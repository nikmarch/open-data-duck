# Contributing

Open Data Duck welcomes focused fixes, source candidates, validation improvements, docs, and security hardening.

## Before opening a pull request

- Keep changes small and reviewable.
- Do not modify vendored DuckDB files unless the task is explicitly about the vendored tree.
- Do not add private, paid, key-gated, gray-area, or disallowed-scraping sources.
- Do not commit secrets, credentials, personal data, large copied datasets, or generated local artifacts.
- For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Source registry contributions

A source candidate should include:

- authoritative publisher and homepage;
- license or terms URL;
- attribution requirement;
- table metadata explaining what one row means;
- access warnings, scan-size warnings, and compliance caveats;
- a bounded direct DuckDB query path, or a clear connector blocker;
- validation SQL when a queryable Open Data Duck facade exists.

See [docs/legal/data-source-policy.md](docs/legal/data-source-policy.md) and [docs/source-harvesting.md](docs/source-harvesting.md).

## Development checks

For Python/registry changes, run:

```bash
uv run odd validate
uv run pytest
```

For native extension changes, also run the relevant DuckDB extension SQL tests documented in the README.

Docs-only changes should at least pass:

```bash
git diff --check
```
