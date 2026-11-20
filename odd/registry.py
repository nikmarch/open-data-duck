from __future__ import annotations

import html
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


REQUIRED_TEXT_FIELDS = (
    ("authority",),
    ("license_url",),
    ("attribution",),
)

LEGACY_QUERY_TEXT_FIELDS = (
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
    validation_pair = _first_validation_pair(source)
    if validation_pair is not None:
        if validation:
            return _render_validation_pair_sql(source, validation_pair)
        odd_sql = validation_pair.get("odd_sql")
        if isinstance(odd_sql, str) and odd_sql.strip():
            return odd_sql.strip() + "\n"

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


def _first_validation_pair(source: Source) -> dict[str, Any] | None:
    for table in source.tables:
        for validation in _mapping_list(table.get("validations")):
            if isinstance(validation.get("direct_sql"), str) and isinstance(validation.get("odd_sql"), str):
                return validation
    return None


def _render_validation_pair_sql(source: Source, validation_pair: dict[str, Any]) -> str:
    direct_sql = str(validation_pair["direct_sql"]).strip()
    odd_sql = str(validation_pair["odd_sql"]).strip()
    validation_id = str(validation_pair.get("id", source.id))
    return (
        f"-- direct DuckDB control for {validation_id}\n"
        f"{direct_sql}\n\n"
        f"-- ODD facade example for {validation_id}\n"
        f"{odd_sql}\n"
    )


def render_index_text(sources: list[Source]) -> str:
    lines = ["Open Data Duck source index", "===========================", ""]
    for source_type in sorted({source.source_type for source in sources}):
        group = [source for source in sources if source.source_type == source_type]
        lines.append(f"{source_type} ({len(group)})")
        lines.append("-" * (len(source_type) + len(str(len(group))) + 3))
        for source in group:
            tags = f" [{', '.join(source.tags)}]" if source.tags else ""
            lines.append(f"- {source.id} — {source.name} ({source.status}){tags}")
            if source.description:
                lines.append(f"  {source.description}")
            for table in source.tables:
                lines.append(f"  - {table.get('id')}: {table.get('description')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_source_detail(source: Source) -> str:
    lines = [source.name, "=" * len(source.name), ""]
    if source.description:
        lines.extend(("", source.description, ""))
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
    if source.tables:
        lines.extend(("", "Tables:"))
        for table in source.tables:
            ref = f" ({table['ref']})" if table.get("ref") else ""
            lines.append(f"- {table.get('id')}{ref}: {table.get('description')}")
            if table.get("ask_for"):
                lines.append(f"  Ask for: {_inline_value(table['ask_for'])}")
            if table.get("warnings"):
                lines.append(f"  Warnings: {_inline_value(table['warnings'])}")
            if table.get("columns_hint"):
                lines.append(f"  Columns: {_inline_mapping(table['columns_hint'])}")
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
            if source.description:
                lines.append(source.description)
                lines.append("")
            lines.append(f"- Status: `{source.status}`")
            lines.append(f"- Authority: {source.authority}")
            if source.homepage:
                lines.append(f"- Homepage: {source.homepage}")
            lines.append(f"- License: {source.license_url}")
            if source.tags:
                lines.append(f"- Tags: {', '.join(f'`{tag}`' for tag in source.tags)}")
            if source.topics:
                lines.append(f"- Topics: {', '.join(source.topics)}")
            if source.cadence:
                lines.append(f"- Cadence: {source.cadence}")
            if source.tables:
                lines.append("- Tables:")
                for table in source.tables:
                    ref = f" (`{table['ref']}`)" if table.get("ref") else ""
                    lines.append(f"  - `{table.get('id')}`{ref}: {table.get('description')}")
                    if table.get("ask_for"):
                        lines.append(f"    - Ask for: {_inline_value(table['ask_for'])}")
                    if table.get("warnings"):
                        lines.append(f"    - Warnings: {_inline_value(table['warnings'])}")
                    if table.get("columns_hint"):
                        lines.append(f"    - Columns: {_inline_mapping(table['columns_hint'])}")
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


def render_site_index_html(sources: list[Source]) -> str:
    queryable_tables = [
        (source, table)
        for source in sources
        for table in source.tables
        if isinstance(table.get("ref"), str) and str(table.get("ref")).startswith("odd.")
    ]
    source_cards = "\n".join(_render_site_source_card(source) for source in sources)
    table_rows = "\n".join(_render_site_table_row(source, table) for source, table in queryable_tables[:8])
    source_type_counts = ", ".join(
        f"{_html(source_type)} ({sum(1 for source in sources if source.source_type == source_type)})"
        for source_type in sorted({source.source_type for source in sources})
    )
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Open Data Duck</title>
  <meta name=\"description\" content=\"An open, DuckDB-friendly index of pluggable public data tables.\">
  <link rel=\"canonical\" href=\"https://nikmarch.github.io/open-data-duck/\">
  <meta property=\"og:type\" content=\"website\">
  <meta property=\"og:site_name\" content=\"Open Data Duck\">
  <meta property=\"og:title\" content=\"Open Data Duck\">
  <meta property=\"og:description\" content=\"An open, DuckDB-friendly index of pluggable public data tables.\">
  <meta property=\"og:url\" content=\"https://nikmarch.github.io/open-data-duck/\">
  <meta property=\"og:image\" content=\"https://nikmarch.github.io/open-data-duck/assets/brand/odd-wordmark.svg\">
  <meta property=\"og:image:type\" content=\"image/svg+xml\">
  <meta property=\"og:image:alt\" content=\"Open Data Duck logo\">
  <meta name=\"twitter:card\" content=\"summary_large_image\">
  <meta name=\"twitter:title\" content=\"Open Data Duck\">
  <meta name=\"twitter:description\" content=\"An open, DuckDB-friendly index of pluggable public data tables.\">
  <meta name=\"twitter:image\" content=\"https://nikmarch.github.io/open-data-duck/assets/brand/odd-wordmark.svg\">
  <meta name=\"twitter:image:alt\" content=\"Open Data Duck logo\">
  <link rel=\"icon\" href=\"assets/brand/odd-icon.svg\" type=\"image/svg+xml\">
  <link rel=\"stylesheet\" href=\"styles.css\">
</head>
<body>
  <main>
    <section class=\"hero\" aria-labelledby=\"site-title\">
      <img class=\"wordmark\" src=\"assets/brand/odd-wordmark.svg\" alt=\"Open Data Duck\">
      <p class=\"eyebrow\">DuckDB-friendly public data index</p>
      <h1 id=\"site-title\">Find authoritative open data sources and query them safely with DuckDB.</h1>
      <p class=\"lede\">Open Data Duck does not mirror datasets. It stores source metadata, licenses, attribution, and executable query recipes so people and AI workers can plug in public datasets quickly, without Googling, configuring, or remembering every source.</p>
      <div class=\"actions\" aria-label=\"Primary links\">
        <a class=\"button primary\" href=\"#plugin-api\">Plugin API direction</a>
        <a class=\"button\" href=\"#source-catalog\">Browse generated catalog</a>
        <a class=\"button\" href=\"https://github.com/nikmarch/open-data-duck\">View the repository</a>
        <a class=\"button\" href=\"https://github.com/nikmarch/open-data-duck/blob/main/docs/index.md\">Browse the source index</a>
      </div>
    </section>

    <section class=\"api-preview\" id=\"plugin-api\" aria-labelledby=\"plugin-api-title\">
      <div class=\"api-copy\">
        <p class=\"eyebrow\">Plugin API direction</p>
        <h2 id=\"plugin-api-title\">Attach once. Search the catalog table. Query the facade table.</h2>
        <p>The public site stays static for now. No fake terminal, no browser query runner, and no preset picker. The native extension resolves ODD table references with a replacement scan. Set the Overture S3 region before querying those facade tables.</p>
      </div>

      <div class=\"api-card\" aria-label=\"Open Data Duck plugin API example\">
        <pre><code>INSTALL open_data_duck;
LOAD open_data_duck;

SET s3_region='us-west-2';

ATTACH ':memory:' AS odd (TYPE open_data_duck);

SELECT *
FROM odd.index
WHERE list_contains(tags, 'buildings')
   OR name ILIKE '%building%';

SELECT table_reference, reader, path
FROM odd.tables
WHERE table_reference = 'odd.overturemaps.latest.building';

SELECT *
FROM odd.overturemaps.latest.building
WHERE bbox.xmin <= -149
  AND bbox.xmax >= -150
  AND bbox.ymin <= 61
  AND bbox.ymax >= 60
LIMIT 10;</code></pre>
        <table>
          <caption>Generated queryable table refs from registry/sources.yml</caption>
          <thead>
            <tr>
              <th>source</th>
              <th>table</th>
              <th>table_reference</th>
            </tr>
          </thead>
          <tbody>
{table_rows}
          </tbody>
        </table>
      </div>
    </section>

    <section class=\"catalog\" id=\"source-catalog\" aria-labelledby=\"source-catalog-title\">
      <p class=\"eyebrow\">Generated catalog</p>
      <h2 id=\"source-catalog-title\">Source and table metadata rendered from registry/sources.yml.</h2>
      <p class=\"catalog-summary\">{len(sources)} sources across {source_type_counts}. Markdown docs and this page use the same registry renderer so table descriptions, ask-for hints, warnings, licenses, and references drift in one place only.</p>
      <div class=\"catalog-grid\">
{source_cards}
      </div>
    </section>

    <section class=\"grid\" aria-label=\"Project documentation\">
      <article>
        <h2>Source index</h2>
        <p>Human- and AI-friendly catalog entries for public data sources, DuckDB recipes, licenses, usage hints, and validation queries.</p>
        <a href=\"https://github.com/nikmarch/open-data-duck/blob/main/docs/index.md\">Read the generated index</a>
      </article>
      <article>
        <h2>Engine track</h2>
        <p>Connector status for ArcGIS, CKAN/DCAT, Socrata, Overture, STAC, and public object-storage paths.</p>
        <a href=\"https://github.com/nikmarch/open-data-duck/blob/main/docs/engine-maintenance.md\">See engine maintenance</a>
      </article>
      <article>
        <h2>Brand assets</h2>
        <p>The project wordmark and icon are checked into the repo and reused here by the Pages build.</p>
        <a href=\"https://github.com/nikmarch/open-data-duck/blob/main/docs/brand-assets.md\">View brand assets</a>
      </article>
    </section>
  </main>
</body>
</html>
"""


def _render_site_table_row(source: Source, table: dict[str, Any]) -> str:
    ref = _html(str(table.get("ref", "")))
    return (
        "            <tr>\n"
        f"              <td>{_html(source.name)}</td>\n"
        f"              <td>{_html(str(table.get('id', '')))}</td>\n"
        f"              <td><code>{ref}</code></td>\n"
        "            </tr>"
    )


def _render_site_source_card(source: Source) -> str:
    tags = "".join(f"<li>{_html(tag)}</li>" for tag in source.tags[:6])
    table_items = "".join(_render_site_source_table(table) for table in source.tables[:4])
    homepage = f"<a href=\"{_html(source.homepage)}\">Homepage</a>" if source.homepage else ""
    return f"""        <article class=\"source-card\">
          <div class=\"source-card-header\">
            <span class=\"status\">{_html(source.status)}</span>
            <span>{_html(source.source_type)}</span>
          </div>
          <h3><code>{_html(source.id)}</code></h3>
          <p>{_html(source.description or source.name)}</p>
          <dl>
            <dt>Authority</dt><dd>{_html(source.authority)}</dd>
            <dt>License</dt><dd><a href=\"{_html(source.license_url)}\">Terms</a></dd>
          </dl>
          <ul class=\"tag-list\">{tags}</ul>
          <ul class=\"table-list\">{table_items}</ul>
          {homepage}
        </article>"""


def _render_site_source_table(table: dict[str, Any]) -> str:
    ref = f" <code>{_html(str(table['ref']))}</code>" if table.get("ref") else ""
    ask_for = f" <span>Ask for: {_html(_inline_value(table['ask_for']))}</span>" if table.get("ask_for") else ""
    warnings = f" <span>Warnings: {_html(_inline_value(table['warnings']))}</span>" if table.get("warnings") else ""
    return f"<li><strong>{_html(str(table.get('id', '')))}</strong>{ref}: {_html(str(table.get('description', '')))}{ask_for}{warnings}</li>"


def _html(value: str) -> str:
    return html.escape(value, quote=True)


def write_index_artifacts(registry_path: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = load_sources(registry_path)
    markdown_path = output_dir / "index.md"
    markdown_path.write_text(render_index_markdown(sources), encoding="utf-8")
    return [markdown_path]


def write_site_index(registry_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_site_index_html(load_sources(registry_path)), encoding="utf-8")
    return output_path


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
