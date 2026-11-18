from pathlib import Path


WORKFLOW = Path(".github/workflows/MainDistributionPipeline.yml")
RELEASE_WORKFLOW = Path(".github/workflows/precommunity-release.yml")
PAGES_WORKFLOW = Path(".github/workflows/pages.yml")
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
    assert "duckdb-cli-linux-amd64.tar.gz" in workflow
    assert "custom-extension-repository/v2.0.0/linux_amd64" in workflow
    assert "open_data_duck.duckdb_extension.gz" in workflow
    assert "./duckdb -unsigned -noheader -csv :memory:" in workflow
    assert "FORCE INSTALL open_data_duck FROM './custom-extension-repository';" in workflow
    assert "LOAD open_data_duck;" in workflow
    assert "SELECT open_data_duck_ping();" in workflow
    assert "SELECT open_data_duck_registry_source_count() > 0;" in workflow
    assert "SELECT count(*) > 0 FROM open_data_sources();" in workflow
    assert "SELECT open_data_sql('overture.maps.release') LIKE '%LOAD httpfs;%';" in workflow


def test_precommunity_release_workflow_publishes_smoked_release_assets() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "release_tag:" in workflow
    assert "tags:" in workflow
    assert "duckdb/extension-ci-tools/.github/workflows/_extension_distribution.yml@v2.0-cyanoptera" in workflow
    assert "open_data_duck-v2.0.0-extension-*" in workflow
    assert "open_data_duck-v2.0.0-extension-linux_amd64" in workflow
    assert "osx_arm64" in workflow
    assert "open_data_duck-v2.0.0-linux_amd64.duckdb_extension" in workflow
    assert "open_data_duck-v2.0.0-osx_arm64.duckdb_extension" in workflow
    assert "SHA256SUMS.txt" in workflow
    assert "actions/checkout@v4" in workflow
    assert "./duckdb -unsigned -noheader -csv :memory:" in workflow
    assert "gh release edit" in workflow
    assert "gh release create" in workflow
    assert "gh release upload" in workflow
    assert "--prerelease" in workflow
    assert "--draft" in workflow
    assert "active current development" in workflow


def test_pages_workflow_publishes_custom_extension_repository() -> None:
    workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")

    assert "duckdb-stable-build:" in workflow
    assert "duckdb/extension-ci-tools/.github/workflows/_extension_distribution.yml@v2.0-cyanoptera" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "open_data_duck-v2.0.0-extension-*" in workflow
    assert "EXTENSION_PLATFORMS: linux_amd64 osx_arm64" in workflow
    assert "_site/${CUSTOM_EXTENSION_REPO_PATH}/${DUCKDB_VERSION}/${platform}" in workflow
    assert "${EXTENSION_NAME}.duckdb_extension.gz" in workflow
    assert "extensions enabled before installing from this repository URL" in workflow
    assert "actions/upload-pages-artifact@v3" in workflow


def test_readme_describes_unsigned_extension_artifacts() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "Main Extension Distribution Pipeline" in readme
    assert "Pre-community Extension Release workflow" in readme
    assert "open_data_duck-v2.0.0-extension-linux_amd64" in readme
    assert "open_data_duck-v2.0.0-linux_amd64.duckdb_extension" in readme
    assert "open_data_duck-v2.0.0-osx_arm64.duckdb_extension" in readme
    assert "temporary pre-community unsigned builds" in readme
    assert "not signed community" in readme
    assert "GitHub prerelease asset" in readme
    assert "DuckDB-version- and platform-specific" in readme
    assert "canonical local filename `open_data_duck.duckdb_extension`" in readme
    assert "Darwin-arm64) platform=\"osx_arm64\"" in readme
    assert "Linux-x86_64) platform=\"linux_amd64\"" in readme
    assert "--output open_data_duck.duckdb_extension" in readme
    assert "xattr -dr com.apple.quarantine open_data_duck.duckdb_extension" in readme
    assert "codesign --force --deep --sign - open_data_duck.duckdb_extension" in readme
    assert "active current development" in readme
    assert "install commands" in readme.casefold()
    assert "https://nikmarch.github.io/open-data-duck/extensions" in readme
    assert "v2.0.0/osx_arm64/open_data_duck.duckdb_extension.gz" in readme
    assert "open_data_duck.duckdb_extension.gz" in readme
    assert "FORCE INSTALL open_data_duck FROM 'https://nikmarch.github.io/open-data-duck/extensions';" in readme
    assert "temporary pre-community bridge" in readme
    assert "duckdb -unsigned :memory:" in readme
    assert "allow_unsigned_extensions" in readme
    assert "INSTALL open_data_duck FROM community" in readme
