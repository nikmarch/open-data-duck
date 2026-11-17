from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema
import yaml


@dataclass(frozen=True)
class ValidationError:
    path: str
    message: str

    def format(self) -> str:
        return f"{self.path}: {self.message}"


REQUIRED_TEXT_FIELDS = (
    ("authority",),
    ("license_url",),
    ("attribution",),
    ("duckdb", "example_query"),
    ("duckdb", "validation_query"),
)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


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

    return errors


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
