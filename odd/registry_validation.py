from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema

from odd.registry_model import ValidationError, load_json, load_registry, _mapping_list

REQUIRED_TEXT_FIELDS = (("authority",), ("license_url",), ("attribution",))


def validate_registry(registry_path: Path, schema_path: Path) -> list[ValidationError]:
    registry = load_registry(registry_path)
    schema = load_json(schema_path)
    errors: list[ValidationError] = []
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(registry), key=lambda item: list(item.path)):
        errors.append(ValidationError(_format_schema_path(error.path), error.message))
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
                errors.append(ValidationError(f"{source_path}.{'.'.join(field_path)}", "must be present and non-blank"))
        errors.extend(_validate_auth(source, source_path))
        errors.extend(_validate_discovery(source, source_path))
        errors.extend(_validate_tables(source, source_path))
        for table_index, table in enumerate(_mapping_list(source.get("tables"))):
            table_id = table.get("id", table_index)
            errors.extend(_validate_validation_pairs(table, f"{source_path}.tables[{table_index}]({table_id})"))
    return errors


def _validate_auth(source: dict[str, Any], source_path: str) -> list[ValidationError]:
    auth = source.get("auth")
    if auth is None or not isinstance(auth, dict):
        return []
    errors: list[ValidationError] = []
    auth_type = auth.get("type")
    if auth_type == "api_key":
        for field in ("duckdb_setting", "env_var", "placeholder", "query_parameter"):
            value = auth.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(ValidationError(f"{source_path}.auth.{field}", "must be present and non-blank for api_key auth"))
    placeholder = auth.get("placeholder")
    if isinstance(placeholder, str) and placeholder.strip():
        sql_parts = []
        discovery = source.get("discovery")
        if isinstance(discovery, dict):
            sql_parts.append(str(discovery.get("discover_sql", "")))
        for table in _mapping_list(source.get("tables")):
            for validation in _mapping_list(table.get("validations")):
                sql_parts.append(str(validation.get("direct_sql", "")))
                sql_parts.append(str(validation.get("odd_sql", "")))
        if not any(placeholder in part for part in sql_parts):
            errors.append(ValidationError(f"{source_path}.auth.placeholder", "must appear in discovery or validation SQL"))
    return errors


def _validate_discovery(source: dict[str, Any], source_path: str) -> list[ValidationError]:
    discovery = source.get("discovery")
    if discovery is None or not isinstance(discovery, dict):
        return []
    errors: list[ValidationError] = []
    for field in ("namespace", "discover_sql"):
        value = discovery.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(ValidationError(f"{source_path}.discovery.{field}", "must be present and non-blank"))
    return errors


def _validate_tables(source: dict[str, Any], source_path: str) -> list[ValidationError]:
    tables = source.get("tables")
    if not isinstance(tables, list):
        return []
    errors: list[ValidationError] = []
    seen_ids: set[str] = set()
    seen_validation_ids: set[str] = set()
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
        table_ref = table.get("ref")
        validations = _mapping_list(table.get("validations"))
        if isinstance(table_ref, str) and table_ref.startswith("odd.") and not validations:
            errors.append(ValidationError(f"{table_path}.validations", "must be present for ref: odd.* tables"))
        for validation in validations:
            validation_id = validation.get("id")
            if isinstance(validation_id, str):
                if validation_id in seen_validation_ids:
                    errors.append(ValidationError(source_path, f"duplicate validation id {validation_id}"))
                seen_validation_ids.add(validation_id)
                if validation_id.startswith("odd.") and not _validation_matches_table_ref(validation_id, {str(table_ref)} if table_ref else set()):
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
    if validations is None or not isinstance(validations, list):
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
                errors.append(ValidationError(f"{validation_path}.id", "must use SQL-safe odd.<provider>.<release>.<table> identifiers"))
        for field in ("direct_sql", "odd_sql"):
            value = validation.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(ValidationError(f"{validation_path}.{field}", "must be present and non-blank"))
        odd_sql = validation.get("odd_sql")
        if isinstance(odd_sql, str) and "odd." not in odd_sql.casefold():
            errors.append(ValidationError(f"{validation_path}.odd_sql", "must query an odd.* facade"))
        direct_sql = validation.get("direct_sql")
        if isinstance(direct_sql, str) and "odd." in direct_sql.casefold():
            errors.append(ValidationError(f"{validation_path}.direct_sql", "must be the direct DuckDB control, not an odd.* facade"))
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
