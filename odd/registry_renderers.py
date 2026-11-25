from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from odd.registry_model import Source, load_sources, _mapping_list


def render_source_sql(source: Source, *, validation: bool = False, include_install: bool = True) -> str:
    validation_pair = _first_validation_pair(source)
    if validation_pair is None:
        raise ValueError(f"{source.id} has no table validation pair")
    if validation:
        return _render_validation_pair_sql(source, validation_pair)
    odd_sql = validation_pair.get("odd_sql")
    if not isinstance(odd_sql, str) or not odd_sql.strip():
        raise ValueError(f"{source.id} has no validation odd_sql")
    return odd_sql.strip() + "\n"


def _first_validation_pair(source: Source) -> dict[str, Any] | None:
    for table in source.tables:
        for validation in _mapping_list(table.get("validations")):
            if isinstance(validation.get("direct_sql"), str) and isinstance(validation.get("odd_sql"), str):
                return validation
    return None


def _render_auth_text(auth: dict[str, Any]) -> list[str]:
    if not auth:
        return []
    lines = [f"Auth: {auth.get('type', 'custom')}"]
    if auth.get("required"):
        lines.append("Auth required: yes")
    setting = auth.get("duckdb_setting")
    env_var = auth.get("env_var")
    if setting:
        lines.append(f"DuckDB setting: SET {setting} = '<secret>';")
    if env_var:
        lines.append(f"Environment variable: {env_var}")
    if auth.get("custom_user_agent"):
        lines.append(f"Suggested user agent: {auth['custom_user_agent']}")
    return lines


def _render_auth_markdown(auth: dict[str, Any]) -> list[str]:
    if not auth:
        return []
    lines = [f"- Auth: `{auth.get('type', 'custom')}`"]
    if auth.get("required"):
        lines.append("- Auth required: `true`")
    setting = auth.get("duckdb_setting")
    env_var = auth.get("env_var")
    if setting:
        lines.append(f"- Secret setup: `SET {setting} = '<secret>';`")
    if env_var:
        lines.append(f"- Environment variable fallback: `{env_var}`")
    if auth.get("custom_user_agent"):
        lines.append(f"- Suggested user agent: `{auth['custom_user_agent']}`")
    return lines


def _render_validation_pair_sql(source: Source, validation_pair: dict[str, Any]) -> str:
    validation_id = str(validation_pair.get("id", source.id))
    return (
        f"-- direct DuckDB control for {validation_id}\n"
        f"{str(validation_pair['direct_sql']).strip()}\n\n"
        f"-- ODD facade example for {validation_id}\n"
        f"{str(validation_pair['odd_sql']).strip()}\n"
    )


def render_index_text(sources: list[Source]) -> str:
    lines = ["Open Data Duck source index", "===========================", ""]
    for source_type in sorted({source.source_type for source in sources}):
        group = [source for source in sources if source.source_type == source_type]
        lines.append(f"{source_type} ({len(group)})")
        lines.append("-" * (len(source_type) + len(str(len(group))) + 3))
        for source in group:
            lines.append(f"- {source.id} — {source.name} ({source.status})")
            for table in source.tables:
                ref = f" ({table['ref']})" if table.get("ref") else ""
                lines.append(f"  - {table.get('id')}{ref}: {table.get('description')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_source_detail(source: Source) -> str:
    lines = [source.name, "=" * len(source.name), ""]
    fields = [
        ("ID", source.id),
        ("Status", source.status),
        ("Type", source.source_type),
        ("Authority", source.authority),
        ("License", source.license_url),
        ("Attribution", source.attribution),
    ]
    for label, value in fields:
        if value:
            lines.append(f"{label}: {value}")
    extensions = source.requirements.get("duckdb_extensions", [])
    if extensions:
        lines.append(f"DuckDB extensions: {_inline_value(extensions)}")
    lines.extend(_render_auth_text(source.auth))
    if source.discovery:
        lines.append(f"Discovery namespace: {source.discovery.get('namespace', '')}")
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
            if table.get("schema_org"):
                lines.append(f"  Schema.org: {_schema_org_summary(table['schema_org'])}")
            if table.get("ai_capabilities"):
                lines.extend(_render_ai_capabilities_text(table["ai_capabilities"], indent="  "))
            for validation in _mapping_list(table.get("validations")):
                lines.append(f"  Validation: {validation.get('id')}")
                odd_sql = validation.get("odd_sql")
                if isinstance(odd_sql, str) and odd_sql.strip():
                    lines.append("  ODD SQL:")
                    lines.extend(f"    {line}" for line in odd_sql.strip().splitlines())
    return "\n".join(lines).rstrip() + "\n"


def render_index_markdown(sources: list[Source]) -> str:
    lines = [
        '<p align="center">',
        '  <img src="assets/brand/odd-wordmark.svg" alt="Open Data Duck" width="360">',
        "</p>",
        "",
        "# Open Data Duck source index",
        "",
        "Table-first catalog of public data sources with legal metadata and executable ODD-vs-direct validation pairs.",
        "",
    ]
    for source_type in sorted({source.source_type for source in sources}):
        lines.extend((f"## {source_type}", ""))
        for source in [source for source in sources if source.source_type == source_type]:
            lines.extend((f"### `{source.id}` — {source.name}", ""))
            lines.append(f"- Status: `{source.status}`")
            lines.append(f"- Authority: {source.authority}")
            lines.append(f"- License: {source.license_url}")
            extensions = source.requirements.get("duckdb_extensions", [])
            if extensions:
                lines.append(f"- DuckDB extensions: {_inline_value(extensions)}")
            lines.extend(_render_auth_markdown(source.auth))
            if source.discovery:
                lines.append(f"- Discovery namespace: `{source.discovery.get('namespace')}`")
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
                    if table.get("schema_org"):
                        lines.append(f"    - Schema.org: {_schema_org_summary(table['schema_org'])}")
                    if table.get("ai_capabilities"):
                        lines.extend(_render_ai_capabilities_markdown(table["ai_capabilities"], indent="    "))
                    for validation in _mapping_list(table.get("validations")):
                        lines.append(f"    - Validation: `{validation.get('id')}`")
                        odd_sql = validation.get("odd_sql")
                        if isinstance(odd_sql, str) and odd_sql.strip():
                            lines.append("      ```")
                            lines.extend(f"      {line}" for line in odd_sql.strip().splitlines())
                            lines.append("      ```")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_index_json(sources: list[Source], *, include_sql: bool = False) -> str:
    payload = {"name": "Open Data Duck source index", "source_count": len(sources), "sources": [source.to_ai_dict(include_sql=include_sql) for source in sources]}
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_ai_catalog_json(sources: list[Source]) -> str:
    payload = {
        "@context": {
            "schema": "https://schema.org/",
            "odd": "https://nikmarch.github.io/open-data-duck/vocab#",
        },
        "@type": "DataCatalog",
        "name": "Open Data Duck AI capability catalog",
        "description": "Schema.org Dataset metadata plus ODD analytics capabilities for source-led exploration.",
        "dataset": [_source_dataset(source) for source in sources],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _source_dataset(source: Source) -> dict[str, Any]:
    return _compact(
        {
            "@type": "Dataset",
            "@id": f"odd:source:{source.id}",
            "identifier": source.id,
            "name": source.name,
            "additionalType": source.source_type,
            "creativeWorkStatus": source.status,
            "creator": {"@type": "Organization", "name": source.authority},
            "publisher": {"@type": "Organization", "name": source.authority},
            "license": source.license_url,
            "citation": source.attribution,
            "odd:auth": source.auth,
            "hasPart": [_table_dataset(source, table) for table in source.tables],
        }
    )


def _table_dataset(source: Source, table: dict[str, Any]) -> dict[str, Any]:
    schema_org = dict(table.get("schema_org", {})) if isinstance(table.get("schema_org"), dict) else {}
    capabilities = dict(table.get("ai_capabilities", {})) if isinstance(table.get("ai_capabilities"), dict) else {}
    table_identifier = str(table.get("ref") or f"{source.id}#{table.get('id')}")
    dataset = _compact(
        {
            "@type": schema_org.pop("@type", "Dataset"),
            "@id": table_identifier,
            "identifier": table_identifier,
            "name": str(table.get("id", "")),
            "description": table.get("description"),
            "isPartOf": f"odd:source:{source.id}",
            "license": source.license_url,
            "citation": source.attribution,
            "distribution": schema_org.pop(
                "distribution",
                {"@type": "DataDownload", "encodingFormat": "application/sql", "contentUrl": table.get("ref")}
                if table.get("ref")
                else None,
            ),
        }
    )
    dataset.update(schema_org)
    if capabilities:
        dataset["odd:aiCapabilities"] = capabilities
    return dataset


def _compact(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item not in (None, [], {})}


def render_site_index_html(sources: list[Source]) -> str:
    queryable_tables = [(source, table) for source in sources for table in source.tables if isinstance(table.get("ref"), str) and str(table.get("ref")).startswith("odd.")]
    source_cards = "\n".join(_render_site_source_card(source) for source in sources)
    table_rows = "\n".join(_render_site_table_row(source, table) for source, table in queryable_tables[:8])
    source_type_counts = ", ".join(f"{_html(source_type)} ({sum(1 for source in sources if source.source_type == source_type)})" for source_type in sorted({source.source_type for source in sources}))
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
      <p class=\"lede\">Open Data Duck stores table metadata, licenses, attribution, and executable validation pairs so ODD facade queries can be checked against direct DuckDB controls.</p>
      <div class=\"actions\" aria-label=\"Primary links\">
        <a class=\"button primary\" href=\"#plugin-api\">Plugin API direction</a>
        <a class=\"button\" href=\"#source-catalog\">Browse generated catalog</a>
        <a class=\"button\" href=\"https://github.com/nikmarch/open-data-duck\">View the repository</a>
        <a class=\"button\" href=\"#source-catalog\">Browse the source index</a>
      </div>
    </section>

    <section class=\"api-preview\" id=\"plugin-api\" aria-labelledby=\"plugin-api-title\">
      <div class=\"api-copy\">
        <p class=\"eyebrow\">Plugin API direction</p>
        <h2 id=\"plugin-api-title\">Attach once. Search the catalog table. Query the facade table.</h2>
        <p>The public site stays static for now. No fake terminal, no browser query runner, and no preset picker. The native extension resolves ODD table references with a replacement scan. Set the Overture S3 region before querying those facade tables. Registry validations keep each facade query paired with a direct DuckDB control.</p>
      </div>
      <div class=\"api-card\" aria-label=\"Open Data Duck plugin API example\">
        <pre><code>INSTALL open_data_duck;
LOAD open_data_duck;

SET s3_region='us-west-2';

ATTACH ':memory:' AS odd (TYPE open_data_duck);

SELECT *
FROM odd.index
WHERE name ILIKE '%building%'
   OR source_type = 'overture';

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
          <caption>Generated queryable table refs from registry/sources/</caption>
          <thead><tr><th>source</th><th>table</th><th>table_reference</th></tr></thead>
          <tbody>
{table_rows}
          </tbody>
        </table>
      </div>
    </section>
    <section class=\"catalog\" id=\"source-catalog\" aria-labelledby=\"source-catalog-title\">
      <p class=\"eyebrow\">Generated catalog</p>
      <h2 id=\"source-catalog-title\">Source and table metadata rendered from split registry files.</h2>
      <p class=\"catalog-summary\">{len(sources)} sources across {source_type_counts}. Markdown docs and this page use the same table-first registry renderer so table descriptions, ask-for hints, warnings, licenses, and references drift in one place only.</p>
      <div class=\"catalog-grid\">
{source_cards}
      </div>
    </section>
    <section class=\"grid\" aria-label=\"Project documentation\">
      <article><h2>Source index</h2><p>Human- and AI-friendly catalog entries for public data sources, licenses, table hints, and executable validation pairs.</p><a href=\"#source-catalog\">Read the generated catalog</a></article>
      <article><h2>Engine track</h2><p>Connector status for ArcGIS, CKAN/DCAT, Socrata, Overture, STAC, and public object-storage paths.</p><a href=\"https://github.com/nikmarch/open-data-duck/blob/main/docs/engine-maintenance.md\">See engine maintenance</a></article>
      <article><h2>Brand assets</h2><p>The project wordmark and icon are checked into the repo and reused here by the Pages build.</p><a href=\"https://github.com/nikmarch/open-data-duck/blob/main/docs/brand-assets.md\">View brand assets</a></article>
    </section>
  </main>
</body>
</html>
"""


def _render_site_table_row(source: Source, table: dict[str, Any]) -> str:
    ref = _html(str(table.get("ref", "")))
    return f"            <tr>\n              <td>{_html(source.name)}</td>\n              <td>{_html(str(table.get('id', '')))}</td>\n              <td><code>{ref}</code></td>\n            </tr>"


def _render_site_source_card(source: Source) -> str:
    table_items = "".join(_render_site_source_table(table) for table in source.tables[:4])
    return f"""        <article class=\"source-card\">
          <div class=\"source-card-header\"><span class=\"status\">{_html(source.status)}</span><span>{_html(source.source_type)}</span></div>
          <h3><code>{_html(source.id)}</code></h3>
          <p>{_html(source.name)}</p>
          <dl><dt>Authority</dt><dd>{_html(source.authority)}</dd><dt>License</dt><dd><a href=\"{_html(source.license_url)}\">Terms</a></dd></dl>
          <ul class=\"table-list\">{table_items}</ul>
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
    markdown_path = output_dir / "index.md"
    markdown_path.write_text(render_index_markdown(load_sources(registry_path)), encoding="utf-8")
    return [markdown_path]


def write_site_index(registry_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_site_index_html(load_sources(registry_path)), encoding="utf-8")
    return output_path


def _inline_mapping(value: dict[str, Any]) -> str:
    return "; ".join(f"{key}: {_inline_value(item)}" for key, item in value.items())


def _schema_org_summary(value: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("spatialCoverage", "temporalCoverage", "measurementTechnique"):
        if value.get(key):
            parts.append(f"{key}: {_inline_value(value[key])}")
    variables = value.get("variableMeasured")
    if variables:
        parts.append(f"variableMeasured: {_schema_org_variables_summary(variables)}")
    return "; ".join(parts)


def _schema_org_variables_summary(value: Any) -> str:
    if not isinstance(value, list):
        return str(value)
    labels: list[str] = []
    for item in value:
        if isinstance(item, dict):
            labels.append(str(item.get("name", "")))
        else:
            labels.append(str(item))
    return ", ".join(label for label in labels if label)


def _render_ai_capabilities_markdown(value: dict[str, Any], *, indent: str) -> list[str]:
    prefix = f"{indent}- "
    child = f"{indent}  - "
    lines = _render_ai_capabilities_text(value, indent=indent, prefix=prefix)
    questions = value.get("example_questions")
    if isinstance(questions, list) and questions:
        lines.append(f"{prefix}Example questions:")
        lines.extend(f"{child}{question}" for question in questions)
    missing = value.get("missing_for_questions")
    if isinstance(missing, list) and missing:
        lines.append(f"{prefix}Known gaps:")
        lines.extend(f"{child}{item.get('question')} — missing {_missing_summary(item)}" for item in missing if isinstance(item, dict))
    return lines


def _render_ai_capabilities_text(value: dict[str, Any], *, indent: str, prefix: str | None = None) -> list[str]:
    bullet = prefix or indent
    lines: list[str] = []
    if value.get("grain"):
        lines.append(f"{bullet}AI grain: {value['grain']}")
    if value.get("geography_level"):
        lines.append(f"{bullet}Geography level: {value['geography_level']}")
    if value.get("safe_operations"):
        lines.append(f"{bullet}Safe operations: {_inline_value(value['safe_operations'])}")
    if value.get("join_keys"):
        join_keys = [item.get("field", "") for item in value["join_keys"] if isinstance(item, dict)]
        lines.append(f"{bullet}Join keys: {_inline_value(join_keys)}")
    return lines


def _missing_summary(value: dict[str, Any]) -> str:
    parts: list[str] = []
    if value.get("missing_source_families"):
        parts.append(_inline_value(value["missing_source_families"]))
    if value.get("missing_metrics"):
        parts.append(_inline_value(value["missing_metrics"]))
    return "; ".join(parts) if parts else "unspecified sources or metrics"


def _inline_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return _inline_mapping(value)
    return str(value)
