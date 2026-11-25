"""Generate the embedded registry artifact consumed by the native DuckDB extension."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from odd.registry_model import Source, load_sources

EXTENSION_REGISTRY_SCHEMA_VERSION = 2
DEFAULT_EXTENSION_REGISTRY_HEADER = Path("src/include/open_data_duck_registry.generated.hpp")
_RAW_DELIMITER = "odd_registry"

_SOURCE_FIELDS = (
    "id",
    "name",
    "source_type",
    "status",
    "authority",
    "license_url",
    "attribution",
    "requirements",
    "auth",
    "release",
    "discovery",
    "tables",
)


def source_to_extension_dict(source: Source) -> dict[str, Any]:
    return {field: getattr(source, field) for field in _SOURCE_FIELDS if getattr(source, field) not in (None, [], {})}


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
    expected = render_extension_registry_header(load_sources(registry_path))
    if not output_path.exists():
        return [f"{output_path} is missing; run `uv run odd generate-extension-registry`"]
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        return [f"{output_path} is out of date with {registry_path}; run `uv run odd generate-extension-registry`"]
    return []
