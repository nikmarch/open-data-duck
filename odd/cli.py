from __future__ import annotations

import argparse
import json
from pathlib import Path

from odd.registry import (
    find_source,
    load_sources,
    render_index_json,
    render_index_markdown,
    render_index_text,
    render_source_detail,
    render_source_sql,
    search_sources,
    validate_registry,
    write_index_artifacts,
)
from odd.schema_manifest import (
    check_source_schema,
    inspect_source_schema,
    load_manifest,
    load_requested_sources,
    refresh_manifest_for_sources,
    write_manifest,
)

DEFAULT_REGISTRY = Path("registry/sources.yml")
DEFAULT_SCHEMA = Path("schema/source.schema.json")
DEFAULT_DOCS_DIR = Path("docs")
DEFAULT_SCHEMA_MANIFEST = Path("schema/source-manifest.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="odd", description="Open Data Duck tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate the source registry")
    validate_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    validate_parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)

    index_parser = subparsers.add_parser("index", help="print the source index")
    index_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    index_parser.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    index_parser.add_argument("--include-sql", action="store_true", help="include SQL recipes in JSON output")

    show_parser = subparsers.add_parser("show", help="print details for one registry source")
    show_parser.add_argument("source_id")
    show_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    show_parser.add_argument("--format", choices=("text", "json"), default="text")
    show_parser.add_argument("--include-sql", action="store_true", help="include SQL recipes in JSON output")

    docs_parser = subparsers.add_parser("generate-index", help="write generated docs/index.md from registry YAML")
    docs_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    docs_parser.add_argument("--output-dir", type=Path, default=DEFAULT_DOCS_DIR)

    search_parser = subparsers.add_parser("search", help="search registry sources")
    search_parser.add_argument("query", nargs="*", help="search terms; all terms must match")
    search_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    search_parser.add_argument("--type", dest="source_type", help="filter by source_type")
    search_parser.add_argument("--status", help="filter by lifecycle status")
    search_parser.add_argument("--limit", type=int, default=20)

    sql_parser = subparsers.add_parser("sql", help="print DuckDB SQL for a registry source")
    sql_parser.add_argument("source_id")
    sql_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    sql_parser.add_argument(
        "--validation",
        action="store_true",
        help="print validation SQL instead of the example query",
    )
    sql_parser.add_argument(
        "--no-install",
        action="store_true",
        help="omit installation/setup statements",
    )

    schema_parser = subparsers.add_parser("schema", help="inspect and check DuckDB-discovered source schemas")
    schema_subparsers = schema_parser.add_subparsers(dest="schema_command", required=True)

    schema_inspect_parser = schema_subparsers.add_parser("inspect", help="print a discovered schema for one source")
    schema_inspect_parser.add_argument("source_id")
    schema_inspect_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    schema_inspect_parser.add_argument(
        "--validation",
        action="store_true",
        help="inspect validation SQL instead of example SQL",
    )
    schema_inspect_parser.add_argument("--no-install", action="store_true", help="omit installation/setup statements")

    schema_refresh_parser = schema_subparsers.add_parser("refresh", help="refresh the cached source schema manifest")
    schema_refresh_parser.add_argument("source_ids", nargs="*", help="source ids to refresh; omit for all sources")
    schema_refresh_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    schema_refresh_parser.add_argument("--manifest", type=Path, default=DEFAULT_SCHEMA_MANIFEST)
    schema_refresh_parser.add_argument(
        "--validation",
        action="store_true",
        help="inspect validation SQL instead of example SQL",
    )
    schema_refresh_parser.add_argument("--no-install", action="store_true", help="omit installation/setup statements")

    schema_check_parser = schema_subparsers.add_parser("check", help="compare discovered schemas against the cached manifest")
    schema_check_parser.add_argument("source_ids", nargs="*", help="source ids to check; omit for all cached sources")
    schema_check_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    schema_check_parser.add_argument("--manifest", type=Path, default=DEFAULT_SCHEMA_MANIFEST)
    schema_check_parser.add_argument(
        "--validation",
        action="store_true",
        help="inspect validation SQL instead of example SQL",
    )
    schema_check_parser.add_argument("--no-install", action="store_true", help="omit installation/setup statements")

    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate(args.registry, args.schema)
    if args.command == "index":
        return _index(args.registry, args.format, include_sql=args.include_sql)
    if args.command == "show":
        return _show(args.registry, args.source_id, args.format, include_sql=args.include_sql)
    if args.command == "generate-index":
        return _generate_index(args.registry, args.output_dir)
    if args.command == "search":
        return _search(args.registry, " ".join(args.query), args.source_type, args.status, args.limit)
    if args.command == "sql":
        return _sql(args.registry, args.source_id, args.validation, include_install=not args.no_install)
    if args.command == "schema":
        return _schema(args)

    parser.error(f"unknown command: {args.command}")
    return 2


def _validate(registry_path: Path, schema_path: Path) -> int:
    errors = validate_registry(registry_path, schema_path)
    if errors:
        print("Registry validation failed:")
        for error in errors:
            print(f"- {error.format()}")
        return 1

    print(f"Registry validation passed: {registry_path}")
    return 0


def _index(registry_path: Path, output_format: str, *, include_sql: bool) -> int:
    sources = load_sources(registry_path)
    if output_format == "json":
        print(render_index_json(sources, include_sql=include_sql), end="")
    elif output_format == "markdown":
        print(render_index_markdown(sources), end="")
    else:
        print(render_index_text(sources), end="")
    return 0


def _show(registry_path: Path, source_id: str, output_format: str, *, include_sql: bool) -> int:
    source = find_source(registry_path, source_id)
    if source is None:
        print(f"Source not found: {source_id}")
        return 1
    if output_format == "json":
        print(json.dumps(source.to_ai_dict(include_sql=include_sql), indent=2, sort_keys=True))
    else:
        print(render_source_detail(source), end="")
    return 0


def _generate_index(registry_path: Path, output_dir: Path) -> int:
    paths = write_index_artifacts(registry_path, output_dir)
    for path in paths:
        print(path)
    return 0


def _search(
    registry_path: Path,
    query: str,
    source_type: str | None,
    status: str | None,
    limit: int,
) -> int:
    matches = search_sources(
        registry_path,
        query,
        source_type=source_type,
        status=status,
        limit=limit,
    )
    if not matches:
        print("No registry sources matched.")
        return 1

    for source in matches:
        print(f"{source.id}\t{source.source_type}\t{source.status}\t{source.name}")
        print(f"  {source.description}")
    return 0


def _sql(registry_path: Path, source_id: str, validation: bool, *, include_install: bool) -> int:
    source = find_source(registry_path, source_id)
    if source is None:
        print(f"Source not found: {source_id}")
        return 1

    print(render_source_sql(source, validation=validation, include_install=include_install), end="")
    return 0


def _schema(args: argparse.Namespace) -> int:
    try:
        if args.schema_command == "inspect":
            return _schema_inspect(
                args.registry,
                args.source_id,
                validation=args.validation,
                include_install=not args.no_install,
            )
        if args.schema_command == "refresh":
            return _schema_refresh(
                args.registry,
                args.manifest,
                args.source_ids,
                validation=args.validation,
                include_install=not args.no_install,
            )
        if args.schema_command == "check":
            return _schema_check(
                args.registry,
                args.manifest,
                args.source_ids,
                validation=args.validation,
                include_install=not args.no_install,
            )
    except ValueError as exc:
        print(exc)
        return 1
    return 2


def _schema_inspect(registry_path: Path, source_id: str, *, validation: bool, include_install: bool) -> int:
    source = find_source(registry_path, source_id)
    if source is None:
        print(f"Source not found: {source_id}")
        return 1

    schema = inspect_source_schema(source, validation=validation, include_install=include_install)
    print(json.dumps(schema.to_dict(), indent=2, sort_keys=True))
    return 0 if schema.status == "ok" else 1


def _schema_refresh(
    registry_path: Path,
    manifest_path: Path,
    source_ids: list[str],
    *,
    validation: bool,
    include_install: bool,
) -> int:
    sources = load_requested_sources(registry_path, source_ids)
    manifest = load_manifest(manifest_path)
    refreshed = refresh_manifest_for_sources(
        sources,
        manifest,
        validation=validation,
        include_install=include_install,
    )
    write_manifest(manifest_path, refreshed)

    requested_source_ids = {source.id for source in sources}
    failed = [
        source_id
        for source_id, schema in refreshed.sources.items()
        if schema.status != "ok" and source_id in requested_source_ids
    ]
    print(f"Wrote {manifest_path} ({len(sources)} source schema{'s' if len(sources) != 1 else ''} refreshed)")
    for source in sources:
        schema = refreshed.sources[source.id]
        status = schema.status if schema.status == "ok" else f"failed: {schema.error}"
        print(f"- {source.id}: {status}")
    return 1 if failed else 0


def _schema_check(
    registry_path: Path,
    manifest_path: Path,
    source_ids: list[str],
    *,
    validation: bool,
    include_install: bool,
) -> int:
    manifest = load_manifest(manifest_path)
    sources = load_requested_sources(registry_path, source_ids or list(manifest.sources))
    results = [
        check_source_schema(source, manifest, validation=validation, include_install=include_install)
        for source in sources
    ]
    for result in results:
        status = "ok" if result.compatible else "breaking"
        print(f"{result.source_id}: {status}")
        for issue in result.issues:
            print(f"- {issue.severity}: {issue.message}")
    return 0 if all(result.compatible for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
