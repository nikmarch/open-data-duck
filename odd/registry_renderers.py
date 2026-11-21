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
        <a class=\"button\" href=\"https://github.com/nikmarch/open-data-duck/blob/main/docs/index.md\">Browse the source index</a>
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
          <caption>Generated queryable table refs from registry/sources.yml</caption>
          <thead><tr><th>source</th><th>table</th><th>table_reference</th></tr></thead>
          <tbody>
{table_rows}
          </tbody>
        </table>
      </div>
    </section>
    <section class=\"catalog\" id=\"source-catalog\" aria-labelledby=\"source-catalog-title\">
      <p class=\"eyebrow\">Generated catalog</p>
      <h2 id=\"source-catalog-title\">Source and table metadata rendered from registry/sources.yml.</h2>
      <p class=\"catalog-summary\">{len(sources)} sources across {source_type_counts}. Markdown docs and this page use the same table-first registry renderer so table descriptions, ask-for hints, warnings, licenses, and references drift in one place only.</p>
      <div class=\"catalog-grid\">
{source_cards}
      </div>
    </section>
    <section class=\"grid\" aria-label=\"Project documentation\">
      <article><h2>Source index</h2><p>Human- and AI-friendly catalog entries for public data sources, licenses, table hints, and executable validation pairs.</p><a href=\"https://github.com/nikmarch/open-data-duck/blob/main/docs/index.md\">Read the generated index</a></article>
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


def _inline_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return _inline_mapping(value)
    return str(value)
