from __future__ import annotations

import argparse
from pathlib import Path

from odd.registry import find_source, render_source_sql, search_sources, validate_registry

DEFAULT_REGISTRY = Path("registry/sources.yml")
DEFAULT_SCHEMA = Path("schema/source.schema.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="odd", description="Open Data Duck tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate the source registry")
    validate_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    validate_parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)

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

    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate(args.registry, args.schema)
    if args.command == "search":
        return _search(args.registry, " ".join(args.query), args.source_type, args.status, args.limit)
    if args.command == "sql":
        return _sql(args.registry, args.source_id, args.validation, include_install=not args.no_install)

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
    return 0


def _sql(registry_path: Path, source_id: str, validation: bool, *, include_install: bool) -> int:
    source = find_source(registry_path, source_id)
    if source is None:
        print(f"Source not found: {source_id}")
        return 1

    print(render_source_sql(source, validation=validation, include_install=include_install), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
