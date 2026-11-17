from pathlib import Path


WORKFLOW = Path(".github/workflows/MainDistributionPipeline.yml")
README = Path("README.md")


def test_extension_distribution_workflow_builds_linux_artifact() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "duckdb/extension-ci-tools/.github/workflows/_extension_distribution.yml@v2.0-cyanoptera" in workflow
    assert "duckdb_version: v2.0.0" in workflow
    assert "ci_tools_version: v2.0-cyanoptera" in workflow
    assert "extension_name: open_data_duck" in workflow
    assert "linux_arm64;linux_amd64_musl;linux_arm64_musl" in workflow
    assert "osx_amd64;osx_arm64;windows_amd64" in workflow
    assert "open_data_duck-v2.0.0-extension-linux_amd64" in workflow


def test_extension_distribution_workflow_smokes_downloaded_artifact() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "actions/download-artifact@v4" in workflow
    assert "duckdb_cli-linux-amd64.zip" in workflow
    assert "./duckdb -unsigned -noheader -csv :memory:" in workflow
    assert "LOAD './extension-artifact/open_data_duck.duckdb_extension';" in workflow
    assert "SELECT open_data_duck_ping();" in workflow
    assert "SELECT open_data_duck_registry_source_count() > 0;" in workflow
    assert "SELECT count(*) > 0 FROM open_data_sources();" in workflow
    assert "SELECT open_data_sql('overture.maps.release') LIKE '%LOAD httpfs;%';" in workflow


def test_readme_describes_unsigned_extension_artifacts() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "Main Extension Distribution Pipeline" in readme
    assert "open_data_duck-v2.0.0-extension-linux_amd64" in readme
    assert "temporary pre-community unsigned builds" in readme
    assert "not signed community" in readme
    assert "extension releases" in readme
