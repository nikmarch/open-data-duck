"""Generate the embedded registry artifact consumed by the native DuckDB extension.

`registry/sources.yml` stays the only source of truth. This module renders a
build-time C++ header that embeds a JSON snapshot of the registry so the
extension runtime needs no Python, PyYAML, or repo-relative files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from odd.registry import Source, load_sources

EXTENSION_REGISTRY_SCHEMA_VERSION = 1
DEFAULT_EXTENSION_REGISTRY_HEADER = Path("src/include/open_data_duck_registry.generated.hpp")

# Raw-string delimiter for the embedded JSON. Chosen so it cannot appear in JSON
# produced by json.dumps (which escapes quotes, so `)odd_registry"` is impossible).
_RAW_DELIMITER = "odd_registry"

# Field set embedded in the native extension: human identity fields plus enough
# release and DuckDB recipe metadata for extension-side search/help functions.
_SOURCE_FIELDS = (
    "id",
    "name",
    "source_type",
    "status",
    "description",
    "authority",
    "homepage",
    "license_url",
    "attribution",
    "tags",
    "release",
)
_DUCKDB_FIELDS = ("extensions", "install", "example_query", "validation_query", "examples", "tables")


def source_to_extension_dict(source: Source) -> dict[str, Any]:
    record: dict[str, Any] = {field: getattr(source, field) for field in _SOURCE_FIELDS}
    duckdb: dict[str, Any] = {}
    for key in _DUCKDB_FIELDS:
        value = source.duckdb.get(key)
        if key == "extensions":
            duckdb[key] = [str(item) for item in (value or [])]
        elif key == "examples":
            duckdb[key] = {
                str(name): str(sql).strip()
                for name, sql in (value or {}).items()
                if isinstance(sql, str) and sql.strip()
            }
        elif key == "tables":
            tables = value if isinstance(value, dict) else {}
            duckdb[key] = (
                {
                    "namespace": str(tables.get("namespace", "")).strip(),
                    "discover_sql": str(tables.get("discover_sql", "")).strip(),
                }
                if str(tables.get("namespace", "")).strip() and str(tables.get("discover_sql", "")).strip()
                else {}
            )
        else:
            duckdb[key] = str(value).strip() if isinstance(value, str) and value.strip() else ""
    record["duckdb"] = duckdb
    return record


def build_extension_registry(sources: list[Source]) -> dict[str, Any]:
    return {
        "schema_version": EXTENSION_REGISTRY_SCHEMA_VERSION,
        "source_count": len(sources),
        "sources": [source_to_extension_dict(source) for source in sources],
    }


def render_extension_registry_json(sources: list[Source]) -> str:
    return json.dumps(build_extension_registry(sources), indent=2, sort_keys=True, ensure_ascii=True)


def render_extension_registry_header(sources: list[Source]) -> str:
    payload = render_extension_registry_json(sources)
    closing = f"){_RAW_DELIMITER}\""
    if closing in payload:
        raise ValueError(f"registry JSON contains raw-string delimiter {closing!r}")

    lines = [
        "// GENERATED FILE. DO NOT EDIT.",
        "// Source of truth: registry/sources.yml",
        "// Regenerate with: uv run odd generate-extension-registry",
        "// Drift check:     uv run odd generate-extension-registry --check",
        "#pragma once",
        "",
        "namespace duckdb {",
        "namespace open_data_duck {",
        "",
        f"static constexpr int REGISTRY_SCHEMA_VERSION = {EXTENSION_REGISTRY_SCHEMA_VERSION};",
        f"static constexpr int REGISTRY_SOURCE_COUNT = {len(sources)};",
        "",
        f'static const char *const REGISTRY_JSON = R"{_RAW_DELIMITER}(',
        payload,
        f"{closing};",
        "",
        "} // namespace open_data_duck",
        "} // namespace duckdb",
        "",
    ]
    return "\n".join(lines)


def write_extension_registry_header(registry_path: Path, output_path: Path) -> Path:
    sources = load_sources(registry_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_extension_registry_header(sources), encoding="utf-8")
    return output_path


def check_extension_registry_header(registry_path: Path, output_path: Path) -> list[str]:
    """Return human-readable drift problems; empty list means the header is current."""
    expected = render_extension_registry_header(load_sources(registry_path))
    if not output_path.exists():
        return [f"{output_path} is missing; run `uv run odd generate-extension-registry`"]
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        return [f"{output_path} is out of date with {registry_path}; run `uv run odd generate-extension-registry`"]
    return []
