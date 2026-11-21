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
    description: str
    status: str
    source_type: str
    authority: str
    homepage: str
    license_url: str
    attribution: str
    duckdb: dict[str, Any]
    tables: list[dict[str, Any]]
    tags: list[str]
    topics: list[str]
    coverage: dict[str, Any]
    cadence: str | None
    ai: dict[str, Any]
    release: dict[str, Any]

    @classmethod
    def from_mapping(cls, source: dict[str, Any]) -> Source:
        return cls(
            id=str(source["id"]),
            name=str(source["name"]),
            description=str(source.get("description", "")),
            status=str(source["status"]),
            source_type=str(source["source_type"]),
            authority=str(source["authority"]),
            homepage=str(source.get("homepage", "")),
            license_url=str(source["license_url"]),
            attribution=str(source["attribution"]),
            duckdb=dict(source.get("duckdb", {})),
            tables=_mapping_list(source.get("tables")),
            tags=_string_list(source.get("tags")),
            topics=_string_list(source.get("topics")),
            coverage=dict(source.get("coverage", {})),
            cadence=str(source["cadence"]) if source.get("cadence") is not None else None,
            ai=dict(source.get("ai", {})),
            release=dict(source.get("release", {})),
        )

    def search_text(self) -> str:
        return " ".join(
            str(item)
            for item in (
                self.id,
                self.name,
                self.description,
                self.status,
                self.source_type,
                self.authority,
                self.homepage,
                self.license_url,
                self.attribution,
                self.cadence or "",
                _flatten_text(self.tags),
                _flatten_text(self.topics),
                _flatten_text(self.coverage),
                _flatten_text(self.ai),
                _flatten_text(self.duckdb.get("extensions", [])),
                _flatten_text(self.duckdb.get("tables", {})),
                _flatten_text(self.tables),
                self.duckdb.get("example_query", ""),
            )
        ).casefold()

    def to_ai_dict(self, *, include_sql: bool = True) -> dict[str, Any]:
        duckdb: dict[str, Any] = {
            "extensions": self.duckdb.get("extensions", []),
            "has_install": bool(str(self.duckdb.get("install", "")).strip()),
        }
        if include_sql:
            for key in ("install", "example_query", "validation_query", "examples"):
                if key in self.duckdb:
                    duckdb[key] = self.duckdb[key]

        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "source_type": self.source_type,
            "authority": self.authority,
            "homepage": self.homepage,
            "license_url": self.license_url,
            "attribution": self.attribution,
            "tags": self.tags,
            "topics": self.topics,
            "coverage": self.coverage,
            "cadence": self.cadence,
            "ai": self.ai,
            "release": self.release,
            "tables": self.tables,
            "duckdb": duckdb,
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
