from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from odd.registry import Source, find_source, load_sources, render_source_sql

MANIFEST_VERSION = 1
DUCKDB_HELPERS_PATH = Path(__file__).resolve().parents[1] / "sql" / "open_data_duck.sql"


@dataclass(frozen=True)
class SchemaColumn:
    name: str
    duckdb_type: str
    nullable: bool | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> SchemaColumn:
        nullable = data.get("nullable")
        return cls(
            name=str(data["name"]),
            duckdb_type=canonical_type(str(data["duckdb_type"])),
            nullable=nullable if isinstance(nullable, bool) else None,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "duckdb_type": canonical_type(self.duckdb_type),
        }
        if self.nullable is not None:
            data["nullable"] = self.nullable
        return data


@dataclass(frozen=True)
class SourceSchema:
    source_id: str
    schema_hash: str
    generated_at: str
    columns: list[SchemaColumn]
    status: str = "ok"
    error: str | None = None

    @classmethod
    def from_columns(
        cls,
        source_id: str,
        columns: list[SchemaColumn],
        *,
        generated_at: str | None = None,
    ) -> SourceSchema:
        return cls(
            source_id=source_id,
            schema_hash=hash_columns(columns),
            generated_at=generated_at or _utc_now(),
            columns=columns,
        )

    @classmethod
    def failed(cls, source_id: str, error: str, *, generated_at: str | None = None) -> SourceSchema:
        return cls(
            source_id=source_id,
            schema_hash="",
            generated_at=generated_at or _utc_now(),
            columns=[],
            status="failed",
            error=error,
        )

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> SourceSchema:
        return cls(
            source_id=str(data["source_id"]),
            schema_hash=str(data.get("schema_hash", "")),
            generated_at=str(data.get("generated_at", "")),
            columns=[SchemaColumn.from_mapping(column) for column in data.get("columns", [])],
            status=str(data.get("status", "ok")),
            error=str(data["error"]) if data.get("error") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "source_id": self.source_id,
            "status": self.status,
            "generated_at": self.generated_at,
            "schema_hash": self.schema_hash,
            "columns": [column.to_dict() for column in self.columns],
        }
        if self.error:
            data["error"] = self.error
        return data


@dataclass(frozen=True)
class CompatibilityIssue:
    source_id: str
    severity: str
    message: str

    def format(self) -> str:
        return f"{self.source_id}: {self.severity}: {self.message}"


@dataclass(frozen=True)
class SchemaCheckResult:
    source_id: str
    current: SourceSchema
    cached: SourceSchema | None
    issues: list[CompatibilityIssue]

    @property
    def compatible(self) -> bool:
        return not any(issue.severity == "breaking" for issue in self.issues)


@dataclass(frozen=True)
class SchemaManifest:
    sources: dict[str, SourceSchema]
    version: int = MANIFEST_VERSION

    @classmethod
    def empty(cls) -> SchemaManifest:
        return cls(sources={})

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> SchemaManifest:
        sources = data.get("sources", {})
        if not isinstance(sources, dict):
            raise ValueError("schema manifest sources must be a mapping")
        return cls(
            version=int(data.get("version", MANIFEST_VERSION)),
            sources={source_id: SourceSchema.from_mapping(source) for source_id, source in sources.items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "sources": {source_id: source.to_dict() for source_id, source in sorted(self.sources.items())},
        }

    def with_schema(self, schema: SourceSchema) -> SchemaManifest:
        return SchemaManifest(version=self.version, sources={**self.sources, schema.source_id: schema})


def inspect_source_schema(source: Source, *, validation: bool = False, include_install: bool = True) -> SourceSchema:
    sql = render_source_sql(source, validation=validation, include_install=include_install)
    try:
        columns = inspect_sql_schema(sql)
    except Exception as exc:  # noqa: BLE001 - captured as source-level status, not app crash
        return SourceSchema.failed(source.id, str(exc))
    return SourceSchema.from_columns(source.id, columns)


def inspect_sql_schema(sql: str) -> list[SchemaColumn]:
    try:
        import duckdb  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised only without dev extra
        raise RuntimeError("DuckDB is required for schema inspection; install the dev extra") from exc

    statements = split_sql_statements(sql)
    if not statements:
        raise ValueError("SQL must contain at least one statement")

    connection = duckdb.connect(":memory:")
    try:
        connection.execute(_duckdb_helpers_sql())
        for statement in statements[:-1]:
            connection.execute(statement)
        rows = connection.execute("SELECT name, duckdb_type, nullable FROM open_data_schema(?)", [statements[-1]]).fetchall()
    finally:
        connection.close()

    return [SchemaColumn(name=str(row[0]), duckdb_type=canonical_type(str(row[1])), nullable=bool(row[2])) for row in rows]


def check_source_schema(
    source: Source,
    manifest: SchemaManifest,
    *,
    validation: bool = False,
    include_install: bool = True,
) -> SchemaCheckResult:
    current = inspect_source_schema(source, validation=validation, include_install=include_install)
    cached = manifest.sources.get(source.id)
    return SchemaCheckResult(
        source_id=source.id,
        current=current,
        cached=cached,
        issues=compare_schemas(source.id, cached, current),
    )


def compare_schemas(source_id: str, cached: SourceSchema | None, current: SourceSchema) -> list[CompatibilityIssue]:
    if cached is None:
        return [CompatibilityIssue(source_id, "info", "no cached schema; refresh manifest to establish baseline")]
    if current.status != "ok":
        return [CompatibilityIssue(source_id, "breaking", f"schema inspection failed: {current.error or 'unknown error'}")]
    if cached.status != "ok":
        return [CompatibilityIssue(source_id, "info", "cached schema was failed; current schema can replace it")]

    issues: list[CompatibilityIssue] = []
    current_by_name = {column.name: column for column in current.columns}
    cached_by_name = {column.name: column for column in cached.columns}

    for name, old_column in cached_by_name.items():
        new_column = current_by_name.get(name)
        if new_column is None:
            issues.append(CompatibilityIssue(source_id, "breaking", f"missing cached column: {name}"))
            continue
        if canonical_type(old_column.duckdb_type) != canonical_type(new_column.duckdb_type):
            issues.append(
                CompatibilityIssue(
                    source_id,
                    "breaking",
                    f"column {name} changed type from {old_column.duckdb_type} to {new_column.duckdb_type}",
                )
            )

    added = sorted(name for name in current_by_name if name not in cached_by_name)
    if added:
        issues.append(CompatibilityIssue(source_id, "info", f"added columns: {', '.join(added)}"))

    if not issues and cached.schema_hash != current.schema_hash:
        issues.append(CompatibilityIssue(source_id, "info", "schema hash changed without breaking column changes"))

    return issues


def refresh_manifest_for_sources(
    sources: list[Source],
    manifest: SchemaManifest | None = None,
    *,
    validation: bool = False,
    include_install: bool = True,
) -> SchemaManifest:
    refreshed = manifest or SchemaManifest.empty()
    for source in sources:
        refreshed = refreshed.with_schema(
            inspect_source_schema(source, validation=validation, include_install=include_install)
        )
    return refreshed


def load_manifest(path: Path) -> SchemaManifest:
    if not path.exists():
        return SchemaManifest.empty()
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return SchemaManifest.from_mapping(data)


def write_manifest(path: Path, manifest: SchemaManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_requested_sources(registry_path: Path, source_ids: list[str]) -> list[Source]:
    if not source_ids:
        return load_sources(registry_path)

    sources: list[Source] = []
    for source_id in source_ids:
        source = find_source(registry_path, source_id)
        if source is None:
            raise ValueError(f"Source not found: {source_id}")
        sources.append(source)
    return sources


def hash_columns(columns: list[SchemaColumn]) -> str:
    payload = json.dumps([column.to_dict() for column in columns], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_type(duckdb_type: str) -> str:
    return " ".join(duckdb_type.strip().upper().split())


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(sql):
        char = sql[index]
        current.append(char)
        if quote is not None:
            if char == quote:
                next_char = sql[index + 1] if index + 1 < len(sql) else ""
                if next_char == quote:
                    current.append(next_char)
                    index += 1
                else:
                    quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == ";":
            statement = "".join(current).strip().rstrip(";").strip()
            if statement:
                statements.append(statement)
            current = []
        index += 1

    statement = "".join(current).strip().rstrip(";").strip()
    if statement:
        statements.append(statement)
    return statements


def _duckdb_helpers_sql() -> str:
    return DUCKDB_HELPERS_PATH.read_text(encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
