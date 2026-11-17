from __future__ import annotations

from pathlib import Path
from typing import Any

from odd.registry import find_source, render_source_sql, search_sources
from odd.schema_manifest import load_manifest

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - depends on optional extra
    FastMCP = None  # type: ignore[assignment]

DEFAULT_REGISTRY = Path("registry/sources.yml")
DEFAULT_SCHEMA_MANIFEST = Path("schema/source-manifest.json")


def search_registry(
    query: str = "",
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    source_type: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    sources = search_sources(
        registry_path,
        query,
        source_type=source_type,
        status=status,
        limit=limit,
    )
    return {
        "count": len(sources),
        "sources": [source.to_ai_dict(include_sql=False) for source in sources],
    }


def get_registry_source(
    source_id: str,
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    include_sql: bool = True,
) -> dict[str, Any]:
    source = find_source(registry_path, source_id)
    if source is None:
        return {"error": f"Source not found: {source_id}"}
    return source.to_ai_dict(include_sql=include_sql)


def get_registry_source_sql(
    source_id: str,
    *,
    registry_path: Path = DEFAULT_REGISTRY,
    validation: bool = False,
    include_install: bool = True,
) -> dict[str, str]:
    source = find_source(registry_path, source_id)
    if source is None:
        return {"error": f"Source not found: {source_id}"}
    return {"source_id": source.id, "sql": render_source_sql(source, validation=validation, include_install=include_install)}


def get_cached_source_schema(
    source_id: str,
    *,
    manifest_path: Path = DEFAULT_SCHEMA_MANIFEST,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    schema = manifest.sources.get(source_id)
    if schema is None:
        return {"error": f"Cached schema not found: {source_id}"}
    return schema.to_dict()


def create_server(registry_path: Path = DEFAULT_REGISTRY) -> Any:
    if FastMCP is None:
        raise RuntimeError("Install open-data-duck[mcp] to run the MCP server.")

    server = FastMCP("Open Data Duck")

    @server.tool()
    def search_sources_tool(query: str = "", source_type: str | None = None, status: str | None = None, limit: int = 20) -> dict[str, Any]:
        """Search Open Data Duck sources by text, type, and lifecycle status."""
        return search_registry(query, registry_path=registry_path, source_type=source_type, status=status, limit=limit)

    @server.tool()
    def get_source(source_id: str, include_sql: bool = True) -> dict[str, Any]:
        """Return one source with AI-friendly metadata and optional DuckDB SQL recipes."""
        return get_registry_source(source_id, registry_path=registry_path, include_sql=include_sql)

    @server.tool()
    def get_source_sql(source_id: str, validation: bool = False, include_install: bool = True) -> dict[str, str]:
        """Return executable DuckDB SQL for one source."""
        return get_registry_source_sql(
            source_id,
            registry_path=registry_path,
            validation=validation,
            include_install=include_install,
        )

    @server.tool()
    def get_source_schema(source_id: str) -> dict[str, Any]:
        """Return the cached DuckDB-discovered schema manifest for one source."""
        return get_cached_source_schema(source_id)

    return server


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
