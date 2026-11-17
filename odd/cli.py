from __future__ import annotations

import argparse
from pathlib import Path

from odd.registry import validate_registry


DEFAULT_REGISTRY = Path("registry/sources.yml")
DEFAULT_SCHEMA = Path("schema/source.schema.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="odd", description="Open Data Duck tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate the source registry")
    validate_parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    validate_parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)

    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate(args.registry, args.schema)

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


if __name__ == "__main__":
    raise SystemExit(main())
