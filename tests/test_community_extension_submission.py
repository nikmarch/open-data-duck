from __future__ import annotations

from pathlib import Path

import yaml


DESCRIPTOR = Path("docs/community-extensions/open_data_duck/description.yml")
SUBMISSION_NOTES = Path("docs/community-extension-submission.md")
README = Path("README.md")
PYPROJECT = Path("pyproject.toml")
MAIN_DISTRIBUTION_WORKFLOW = Path(".github/workflows/MainDistributionPipeline.yml")
PINNED_COMMUNITY_REF = "677b5418ab6b6f1c739a6083347dad2db16c1399"
LINUX_X64_EXCLUDED_PLATFORMS = (
    "linux_arm64;linux_amd64_musl;linux_arm64_musl;"
    "osx_amd64;osx_arm64;"
    "windows_amd64;windows_arm64;windows_amd64_mingw;"
    "wasm_mvp;wasm_eh;wasm_threads"
)


def load_descriptor() -> dict:
    return yaml.safe_load(DESCRIPTOR.read_text(encoding="utf-8"))


def test_community_extension_descriptor_has_required_submission_fields() -> None:
    descriptor = load_descriptor()

    assert descriptor["extension"] == {
        "name": "open_data_duck",
        "description": "DuckDB extension exposing an embedded, queryable index of authoritative open-data source recipes.",
        "version": "0.1.0",
        "language": "C++",
        "build": "cmake",
        "excluded_platforms": LINUX_X64_EXCLUDED_PLATFORMS,
        "license": "MIT",
        "maintainers": ["nikmarch"],
    }
    assert descriptor["repo"] == {
        "github": "nikmarch/open-data-duck",
        "ref": PINNED_COMMUNITY_REF,
    }
    assert "hello_world" in descriptor["docs"]
    assert "extended_description" in descriptor["docs"]


def test_community_extension_descriptor_matches_project_metadata_and_ci_scope() -> None:
    descriptor = load_descriptor()
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    workflow = MAIN_DISTRIBUTION_WORKFLOW.read_text(encoding="utf-8")

    assert f"version = \"{descriptor['extension']['version']}\"" in pyproject
    assert f"license = \"{descriptor['extension']['license']}\"" in pyproject
    assert descriptor["extension"]["excluded_platforms"] in workflow
    assert "open_data_duck-v2.0.0-extension-linux_amd64" in workflow


def test_community_extension_hello_world_uses_real_offline_functions() -> None:
    hello_world = load_descriptor()["docs"]["hello_world"]

    assert "LOAD open_data_duck;" in hello_world
    assert "SELECT open_data_duck_ping();" in hello_world
    assert "FROM open_data_search('overture maps')" in hello_world
    assert "SELECT open_data_sql('overture.maps.release');" in hello_world
    assert "open_data_table" not in hello_world
    assert "http://" not in hello_world
    assert "https://" not in hello_world
    assert "read_parquet" not in hello_world
    assert "STAC_" not in hello_world


def test_community_extension_submission_notes_call_out_copy_target_and_limits() -> None:
    notes = SUBMISSION_NOTES.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    assert "duckdb/community-extensions/extensions/open_data_duck/description.yml" in notes
    assert PINNED_COMMUNITY_REF in notes
    assert "linux_amd64" in notes
    assert "open_data_table(...)" in notes
    assert "not implemented yet" in notes
    assert "normal tests and descriptor checks must stay offline" in notes.casefold()
    assert "docs/community-extension-submission.md" in readme
