from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema

from odd.registry_model import ValidationError, load_json, load_yaml, _mapping_list

REQUIRED_TEXT_FIELDS = (
    ("authority",),
    ("license_url",),
    ("attribution",),
)

LEGACY_QUERY_TEXT_FIELDS = (
    ("duckdb", "example_query"),
    ("duckdb", "validation_query"),
)

def validate_registry(registry_path: Path, schema_path: Path) -> list[ValidationError]:
    registry = load_yaml(registry_path)
    schema = load_json(schema_path)

    errors: list[ValidationError] = []
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(registry), key=lambda item: list(item.path)):
        path = _format_schema_path(error.path)
        errors.append(ValidationError(path, error.message))

    errors.extend(_validate_hygiene(registry))
    return errors


def _validate_hygiene(registry: dict[str, Any]) -> list[ValidationError]:
    sources = registry.get("sources")
    if not isinstance(sources, list):
        return []

    errors: list[ValidationError] = []
    seen_ids: set[str] = set()
    for index, source in enumerate(sources):
        source_path = f"sources[{index}]"
        if not isinstance(source, dict):
            continue

        source_id = source.get("id")
        if isinstance(source_id, str) and source_id.strip():
            source_path = f"sources[{index}]({source_id})"
            if source_id in seen_ids:
                errors.append(ValidationError(source_path, "duplicate source id"))
            seen_ids.add(source_id)

        for field_path in REQUIRED_TEXT_FIELDS:
            value = _nested_get(source, field_path)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    ValidationError(
                        f"{source_path}.{'.'.join(field_path)}",
                        "must be present and non-blank",
                    )
                )

        table_validations = [
            validation
            for table in _mapping_list(source.get("tables"))
            for validation in _mapping_list(table.get("validations"))
        ]
        has_validation_pairs = bool(table_validations)
        errors.extend(_validate_tables(source, source_path))
        if not has_validation_pairs:
            for field_path in LEGACY_QUERY_TEXT_FIELDS:
                value = _nested_get(source, field_path)
                if not isinstance(value, str) or not value.strip():
                    errors.append(
                        ValidationError(
                            f"{source_path}.{'.'.join(field_path)}",
                            "must be present and non-blank unless validations are present",
                        )
                    )

        for table_index, table in enumerate(_mapping_list(source.get("tables"))):
            table_id = table.get("id", table_index)
            errors.extend(_validate_validation_pairs(table, f"{source_path}.tables[{table_index}]({table_id})"))

    return errors



def _validate_tables(source: dict[str, Any], source_path: str) -> list[ValidationError]:
    tables = source.get("tables")
    if not isinstance(tables, list):
        return []

    errors: list[ValidationError] = []
    seen_ids: set[str] = set()
    for index, table in enumerate(tables):
        table_path = f"{source_path}.tables[{index}]"
        if not isinstance(table, dict):
            continue
        table_id = table.get("id")
        if isinstance(table_id, str) and table_id.strip():
            table_path = f"{table_path}({table_id})"
            if table_id in seen_ids:
                errors.append(ValidationError(table_path, "duplicate table id"))
            seen_ids.add(table_id)
        description = table.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(ValidationError(f"{table_path}.description", "must be present and non-blank"))

    seen_validation_ids: set[str] = set()
    for table in _mapping_list(source.get("tables")):
        table_ref = table.get("ref")
        for validation in _mapping_list(table.get("validations")):
            validation_id = validation.get("id")
            if isinstance(validation_id, str):
                if validation_id in seen_validation_ids:
                    errors.append(ValidationError(source_path, f"duplicate validation id {validation_id}"))
                seen_validation_ids.add(validation_id)
                if validation_id.startswith("odd.") and not _validation_matches_table_ref(validation_id, {str(table_ref)} if table_ref else set()):
                    table_id = table.get("id", "unknown")
                    errors.append(ValidationError(source_path, f"validation id {validation_id} must match table {table_id} ref"))

    return errors


def _validation_matches_table_ref(validation_id: str, table_refs: set[str]) -> bool:
    if validation_id in table_refs:
        return True
    parts = validation_id.split(".")
    if len(parts) != 4:
        return False
    _odd, provider, _release, table = parts
    return f"odd.{provider}.latest.{table}" in table_refs

def _validate_validation_pairs(source: dict[str, Any], source_path: str) -> list[ValidationError]:
    validations = source.get("validations", [])
    if validations is None:
        return []
    if not isinstance(validations, list):
        return []

    errors: list[ValidationError] = []
    seen_ids: set[str] = set()
    for index, validation in enumerate(validations):
        validation_path = f"{source_path}.validations[{index}]"
        if not isinstance(validation, dict):
            continue

        validation_id = validation.get("id")
        if isinstance(validation_id, str) and validation_id.strip():
            validation_path = f"{validation_path}({validation_id})"
            if validation_id in seen_ids:
                errors.append(ValidationError(validation_path, "duplicate validation id"))
            seen_ids.add(validation_id)
            if not validation_id.startswith("odd."):
                errors.append(ValidationError(f"{validation_path}.id", "must be an ODD table reference"))
            if not _is_sql_safe_table_reference(validation_id):
                errors.append(
                    ValidationError(
                        f"{validation_path}.id",
                        "must use SQL-safe odd.<provider>.<release>.<table> identifiers",
                    )
                )

        for field in ("direct_sql", "odd_sql"):
            value = validation.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(ValidationError(f"{validation_path}.{field}", "must be present and non-blank"))

        odd_sql = validation.get("odd_sql")
        if isinstance(odd_sql, str) and "odd." not in odd_sql.casefold():
            errors.append(ValidationError(f"{validation_path}.odd_sql", "must query an odd.* facade"))

        release = validation.get("release")
        if isinstance(release, str) and release.strip() and not _is_sql_safe_identifier(release):
            errors.append(ValidationError(f"{validation_path}.release", "must be SQL-safe; use x instead of punctuation"))

    return errors


def _is_sql_safe_table_reference(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 4 and parts[0] == "odd" and all(_is_sql_safe_identifier(part) for part in parts[1:])


def _is_sql_safe_identifier(value: str) -> bool:
    return bool(value) and all(char.isalnum() or char == "_" for char in value) and not value[0].isdigit()

def _nested_get(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _format_schema_path(path: Any) -> str:
    parts = list(path)
    if not parts:
        return "registry"
    formatted = ""
    for part in parts:
        if isinstance(part, int):
            formatted += f"[{part}]"
        else:
            formatted += f".{part}" if formatted else str(part)
    return formatted
