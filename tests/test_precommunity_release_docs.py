from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "render_precommunity_release_notes.py"

spec = importlib.util.spec_from_file_location("render_precommunity_release_notes", SCRIPT_PATH)
assert spec is not None
release_notes = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(release_notes)


def test_release_notes_are_copy_pasteable_for_the_requested_tag() -> None:
    rendered = release_notes.render_release_notes("v0.1.0-pre.3")

    assert 'release_tag="v0.1.0-pre.3"' in rendered
    assert 'release_tag="v0.1.0-pre.1"' not in rendered
    assert "open_data_duck.duckdb_extension" in rendered
    assert "unsupported platform" in rendered
    assert "duckdb -unsigned :memory:" in rendered
    assert "LOAD './open_data_duck.duckdb_extension';" in rendered
    assert "open_data_duck: pong" in rendered
    assert "true" in rendered
    assert "INSTALL open_data_duck FROM community;` is not expected to work" in rendered


def test_precommunity_workflow_generates_release_notes_from_the_requested_tag() -> None:
    workflow = (ROOT / ".github" / "workflows" / "precommunity-release.yml").read_text(encoding="utf-8")

    assert "scripts/render_precommunity_release_notes.py \"${RELEASE_TAG}\"" in workflow
    assert 'release_tag="v0.1.0-pre.1"' not in workflow
    assert "release-notes.md" in workflow


def test_readme_keeps_user_first_install_guidance() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "copy the install block from that release's notes" in readme
    assert 'release_tag="v0.1.0-pre.1"' in readme
    assert "open_data_duck.duckdb_extension" in readme
    assert "unsupported platform" in readme
    assert "duckdb -unsigned :memory:" in readme
    assert "open_data_duck: pong" in readme
    assert "Use `INSTALL open_data_duck FROM community;` only after" in readme


def test_release_tag_validation_rejects_non_tag_strings() -> None:
    try:
        release_notes.render_release_notes("latest")
    except ValueError as exc:
        assert "release tag must look like" in str(exc)
    else:
        raise AssertionError("expected invalid release tag to fail")
