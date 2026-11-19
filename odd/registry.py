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
    description: str
    status: str
    source_type: str
    authority: str
    homepage: str
    license_url: str
    attribution: str
    duckdb: dict[str, Any]
    tags: list[str]
    topics: list[str]
    coverage: dict[str, Any]
    cadence: str | None
    ai: dict[str, Any]
    freshness: dict[str, Any]
    release: dict[str, Any]

    @classmethod
    def from_mapping(cls, source: dict[str, Any]) -> Source:
        return cls(
            id=str(source["id"]),
            name=str(source["name"]),
            description=str(source["description"]),
            status=str(source["status"]),
            source_type=str(source["source_type"]),
            authority=str(source["authority"]),
            homepage=str(source["homepage"]),
            license_url=str(source["license_url"]),
            attribution=str(source["attribution"]),
            duckdb=dict(source["duckdb"]),
            tags=_string_list(source.get("tags")),
            topics=_string_list(source.get("topics")),
            coverage=dict(source.get("coverage", {})),
            cadence=str(source["cadence"]) if source.get("cadence") is not None else None,
            ai=dict(source.get("ai", {})),
            freshness=dict(source.get("freshness", {})),
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
            "freshness": self.freshness,
            "release": self.release,
            "duckdb": duckdb,
        }
        return {key: value for key, value in data.items() if value not in (None, [], {})}


REQUIRED_TEXT_FIELDS = (
    ("description",),
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


def render_index_text(sources: list[Source]) -> str:
    lines = ["Open Data Duck source index", "===========================", ""]
    for source_type in sorted({source.source_type for source in sources}):
        group = [source for source in sources if source.source_type == source_type]
        lines.append(f"{source_type} ({len(group)})")
        lines.append("-" * (len(source_type) + len(str(len(group))) + 3))
        for source in group:
            tags = f" [{', '.join(source.tags)}]" if source.tags else ""
            lines.append(f"- {source.id} — {source.name} ({source.status}){tags}")
            lines.append(f"  {source.description}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_source_detail(source: Source) -> str:
    lines = [source.name, "=" * len(source.name), "", source.description, ""]
    fields = [
        ("ID", source.id),
        ("Status", source.status),
        ("Type", source.source_type),
        ("Authority", source.authority),
        ("Homepage", source.homepage),
        ("License", source.license_url),
        ("Attribution", source.attribution),
        ("Cadence", source.cadence),
        ("Tags", ", ".join(source.tags)),
        ("Topics", ", ".join(source.topics)),
    ]
    for label, value in fields:
        if value:
            lines.append(f"{label}: {value}")
    if source.coverage:
        lines.append(f"Coverage: {_inline_mapping(source.coverage)}")
    if source.ai:
        lines.extend(("", "AI usage:"))
        for key, value in source.ai.items():
            lines.append(f"- {key}: {_inline_value(value)}")
    lines.extend(("", "DuckDB extensions: " + ", ".join(source.duckdb.get("extensions", []))))
    return "\n".join(lines).rstrip() + "\n"


def render_index_markdown(sources: list[Source]) -> str:
    lines = [
        '<p align="center">',
        '  <img src="assets/brand/odd-wordmark.svg" alt="Open Data Duck" width="360">',
        "</p>",
        "",
        "# Open Data Duck source index",
        "",
    ]
    lines.append("AI-friendly catalog of public data sources with DuckDB recipes, licenses, and usage hints.")
    lines.append("")
    for source_type in sorted({source.source_type for source in sources}):
        lines.append(f"## {source_type}")
        lines.append("")
        for source in [source for source in sources if source.source_type == source_type]:
            lines.append(f"### `{source.id}` — {source.name}")
            lines.append("")
            lines.append(source.description)
            lines.append("")
            lines.append(f"- Status: `{source.status}`")
            lines.append(f"- Authority: {source.authority}")
            lines.append(f"- Homepage: {source.homepage}")
            lines.append(f"- License: {source.license_url}")
            if source.tags:
                lines.append(f"- Tags: {', '.join(f'`{tag}`' for tag in source.tags)}")
            if source.topics:
                lines.append(f"- Topics: {', '.join(source.topics)}")
            if source.cadence:
                lines.append(f"- Cadence: {source.cadence}")
            if source.ai.get("use_cases"):
                lines.append(f"- AI use cases: {_inline_value(source.ai['use_cases'])}")
            if source.ai.get("caveats"):
                lines.append(f"- Caveats: {_inline_value(source.ai['caveats'])}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_index_json(sources: list[Source], *, include_sql: bool = False) -> str:
    payload = {
        "name": "Open Data Duck source index",
        "source_count": len(sources),
        "sources": [source.to_ai_dict(include_sql=include_sql) for source in sources],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_index_artifacts(registry_path: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = load_sources(registry_path)
    markdown_path = output_dir / "index.md"
    markdown_path.write_text(render_index_markdown(sources), encoding="utf-8")
    return [markdown_path]


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


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _inline_mapping(value: dict[str, Any]) -> str:
    return "; ".join(f"{key}: {_inline_value(item)}" for key, item in value.items())


def _inline_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return _inline_mapping(value)
    return str(value)


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
