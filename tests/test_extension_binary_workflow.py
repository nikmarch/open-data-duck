from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW = Path(".github/workflows/extension-binaries.yml")


def test_extension_binary_workflow_builds_and_smokes_unsigned_artifact() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    parsed = yaml.safe_load(workflow)

    assert parsed["name"] == "Extension Binaries"
    assert "pull_request" in parsed[True]
    assert parsed[True]["push"]["branches"] == ["main"]

    jobs = parsed["jobs"]
    assert jobs["build-linux"]["timeout-minutes"] == 45
    assert jobs["smoke-linux"]["needs"] == "build-linux"
    assert jobs["smoke-linux"]["timeout-minutes"] == 15

    assert "submodules: recursive" in workflow
    assert "make release" in workflow
    assert "extension-ci-tools/scripts/ci_phase.py upload" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "CI_EXTENSION_ARTIFACT_DIR" in workflow
    assert "extension-ci-tools/scripts/ci_phase.py test" in workflow
    assert "test/sql/open_data_duck.test" in workflow
    assert "open_data_duck-linux_amd64-unsigned" in workflow


def test_readme_documents_pre_community_unsigned_artifacts() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Pre-community extension artifacts" in readme
    assert "open_data_duck-linux_amd64-unsigned" in readme
    assert "unsigned" in readme
    assert "temporary" in readme
