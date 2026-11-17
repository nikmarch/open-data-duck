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


def test_research_worker_requires_engine_issue_links_for_blocked_sources() -> None:
    brief = Path("agents/research-worker.md").read_text(encoding="utf-8")

    assert "search for an existing `engine` issue first" in brief
    assert "create one with the `engine` label" in brief
    assert "Link blocked source-candidate issues or PRs" in brief
    assert "real public-source smoke coverage" in brief


def test_readme_links_engine_maintenance_tracker() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "[Engine maintenance track](docs/engine-maintenance.md)" in readme
