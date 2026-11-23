from __future__ import annotations

from pathlib import Path


def test_engine_maintenance_tracker_links_current_engine_issues() -> None:
    tracker = Path("docs/engine-maintenance.md").read_text(encoding="utf-8")

    assert "https://github.com/nikmarch/open-data-duck/issues/7" in tracker
    assert "https://github.com/nikmarch/open-data-duck/issues/15" in tracker
    assert "https://github.com/nikmarch/open-data-duck/issues/16" in tracker
    assert "https://github.com/nikmarch/open-data-duck/issues/17" in tracker
    assert "connector-blocked" in tracker
    assert "real smoke tests against public sources" in tracker
    assert "INSTALL arcgis FROM community" in tracker
    assert "CKAN/DCAT direct-resource path" in tracker
    assert "fictional `ckan_*` / `dcat_*` DuckDB table function" in tracker


def test_research_worker_requires_engine_issue_links_for_blocked_sources() -> None:
    brief = Path("agents/research-worker.md").read_text(encoding="utf-8")

    assert "search for an existing `engine` issue first" in brief
    assert "create one with the `engine` label" in brief
    assert "Link blocked source-candidate issues or PRs" in brief
    assert "real public-source smoke coverage" in brief


def test_research_worker_uses_table_first_source_candidates() -> None:
    brief = Path("agents/research-worker.md").read_text(encoding="utf-8")

    assert "at least one proposed table" in brief
    assert "## Tables" in brief
    assert "One row means" in brief
    assert "Ask for before writing SQL" in brief
    assert "Validation id linked to this table ref" in brief


def test_readme_links_engine_maintenance_tracker() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "[Engine maintenance track](docs/engine-maintenance.md)" in readme
    assert "[docs/architecture](docs/architecture/README.md)" in readme
    assert "[docs/ai-capability-metadata.md](docs/ai-capability-metadata.md)" in readme


def test_ai_capability_metadata_docs_explain_schema_org_and_odd_fields() -> None:
    docs = Path("docs/ai-capability-metadata.md").read_text(encoding="utf-8")

    assert "schema.org" in docs
    assert "variableMeasured" in docs
    assert "ai_capabilities" in docs
    assert "CDC PLACES" in docs
    assert "death-rate-vs-real-estate" in docs


def test_readme_uses_current_facade_first_language() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "## Query with the ODD catalog" in readme
    assert "## Inspect sources and generated SQL" in readme
    assert "## Current pre-community behavior" not in readme
    assert "This is the product shape Open Data Duck is moving toward" not in readme
    assert "hive_partitioning = true" not in readme


def test_readme_overture_facade_example_sets_region_and_uses_exact_table_refs() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "SET s3_region='us-west-2';" in readme
    assert "ATTACH ':memory:' AS odd (TYPE open_data_duck);" in readme
    assert "Query `odd.tables` first and copy the `table_reference` exactly" in readme
    assert "Overture facade table names are singular" in readme
    assert "FROM odd.overturemaps.latest.building" in readme
    assert "odd.overturemaps.latest.buildings" not in readme
