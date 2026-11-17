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


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    status: str
    source_type: str
    authority: str
    homepage: str
    license_url: str
    attribution: str
    duckdb: dict[str, Any]

    @classmethod
    def from_mapping(cls, source: dict[str, Any]) -> Source:
        return cls(
            id=str(source["id"]),
            name=str(source["name"]),
            status=str(source["status"]),
            source_type=str(source["source_type"]),
            authority=str(source["authority"]),
            homepage=str(source["homepage"]),
            license_url=str(source["license_url"]),
            attribution=str(source["attribution"]),
            duckdb=dict(source["duckdb"]),
        )

    def search_text(self) -> str:
        return " ".join(
            (
                self.id,
                self.name,
                self.status,
                self.source_type,
                self.authority,
                self.homepage,
                self.license_url,
                self.attribution,
                " ".join(str(item) for item in self.duckdb.get("extensions", [])),
                str(self.duckdb.get("example_query", "")),
            )
        ).casefold()


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


def load_sources(registry_path: Path) -> list[Source]:
    registry = load_yaml(registry_path)
    sources = registry.get("sources")
    if not isinstance(sources, list):
        raise ValueError(f"{registry_path} must contain a sources list")
    return [Source.from_mapping(source) for source in sources if isinstance(source, dict)]


def search_sources(
    registry_path: Path,
    query: str,
    *,
    source_type: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> list[Source]:
    terms = [term.casefold() for term in query.split() if term.strip()]
    matches: list[Source] = []

    for source in load_sources(registry_path):
        if source_type and source.source_type != source_type:
            continue
        if status and source.status != status:
            continue
        haystack = source.search_text()
        if terms and not all(term in haystack for term in terms):
            continue
        matches.append(source)
        if limit is not None and len(matches) >= limit:
            break

    return matches


def find_source(registry_path: Path, source_id: str) -> Source | None:
    for source in load_sources(registry_path):
        if source.id == source_id:
            return source
    return None


def render_source_sql(source: Source, *, validation: bool = False, include_install: bool = True) -> str:
    statements: list[str] = []
    install = source.duckdb.get("install")
    if include_install and isinstance(install, str) and install.strip():
        statements.append(install.strip())

    query_key = "validation_query" if validation else "example_query"
    query = source.duckdb.get(query_key)
    if not isinstance(query, str) or not query.strip():
        raise ValueError(f"{source.id} has no duckdb.{query_key}")
    statements.append(query.strip())
    return "\n\n".join(statements) + "\n"


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
