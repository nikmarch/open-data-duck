from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    license_url: str
    attribution: str
    tables: list[dict[str, Any]]
    requirements: dict[str, Any]
    release: dict[str, Any]
    discovery: dict[str, Any]

    @classmethod
    def from_mapping(cls, source: dict[str, Any]) -> Source:
        return cls(
            id=str(source["id"]),
            name=str(source["name"]),
            status=str(source["status"]),
            source_type=str(source["source_type"]),
            authority=str(source["authority"]),
            license_url=str(source["license_url"]),
            attribution=str(source["attribution"]),
            tables=_mapping_list(source.get("tables")),
            requirements=dict(source.get("requirements", {})),
            release=dict(source.get("release", {})),
            discovery=dict(source.get("discovery", {})),
        )

    def search_text(self) -> str:
        return " ".join(
            str(item)
            for item in (
                self.id,
                self.name,
                self.status,
                self.source_type,
                self.authority,
                self.license_url,
                self.attribution,
                _flatten_text(self.requirements),
                _flatten_text(self.release),
                _flatten_text(self.discovery),
                _flatten_text(self.tables),
            )
        ).casefold()

    def to_ai_dict(self, *, include_sql: bool = True) -> dict[str, Any]:
        tables: list[dict[str, Any]] = []
        for table in self.tables:
            table_data = dict(table)
            if not include_sql:
                table_data["validations"] = [
                    {key: value for key, value in validation.items() if key not in {"direct_sql", "odd_sql"}}
                    for validation in _mapping_list(table.get("validations"))
                ]
            tables.append(table_data)
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "source_type": self.source_type,
            "authority": self.authority,
            "license_url": self.license_url,
            "attribution": self.attribution,
            "requirements": self.requirements,
            "release": self.release,
            "discovery": self.discovery,
            "tables": tables,
        }
        return {key: value for key, value in data.items() if value not in (None, [], {})}


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


def load_registry(registry_path: Path) -> dict[str, Any]:
    """Load the registry as the legacy aggregate {sources: [...]} shape.

    New source definitions live one-per-file under registry/sources/ to make
    parallel source PRs additive. The public loader still returns the aggregate
    shape expected by validators, renderers, and existing callers.
    """

    return {"sources": load_source_mappings(registry_path)}


def load_source_mappings(registry_path: Path) -> list[dict[str, Any]]:
    if registry_path.is_dir():
        return _load_source_directory(registry_path)

    registry = load_yaml(registry_path)
    sources = registry.get("sources")
    if isinstance(sources, list):
        return _sort_source_mappings([dict(source) for source in sources if isinstance(source, dict)])

    sources_dir = registry.get("sources_dir")
    if isinstance(sources_dir, str) and sources_dir.strip():
        return _load_source_directory((registry_path.parent / sources_dir).resolve())

    default_sources_dir = registry_path.parent / "sources"
    if default_sources_dir.is_dir():
        return _load_source_directory(default_sources_dir)

    raise ValueError(f"{registry_path} must contain either a sources list or sources_dir")


def load_sources(registry_path: Path) -> list[Source]:
    return [Source.from_mapping(source) for source in load_source_mappings(registry_path)]


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


def _load_source_directory(source_dir: Path) -> list[dict[str, Any]]:
    if not source_dir.is_dir():
        raise ValueError(f"{source_dir} must be a directory of source YAML files")
    sources: list[dict[str, Any]] = []
    for path in sorted((*source_dir.glob("*.yml"), *source_dir.glob("*.yaml"))):
        data = load_yaml(path)
        if "sources" in data:
            nested_sources = data.get("sources")
            if not isinstance(nested_sources, list):
                raise ValueError(f"{path} sources must be a list when present")
            sources.extend(dict(source) for source in nested_sources if isinstance(source, dict))
            continue
        sources.append(data)
    return _sort_source_mappings(sources)


def _sort_source_mappings(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(sources, key=lambda source: str(source.get("id", "")))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)
