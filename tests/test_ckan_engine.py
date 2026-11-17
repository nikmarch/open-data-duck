from __future__ import annotations

import os

import pytest

from odd.ckan import (
    CatalogResource,
    ckan_action_url,
    ckan_direct_path_evidence,
    direct_duckdb_resources,
    fetch_ckan_package,
    render_direct_resource_sql,
    resources_from_ckan_package,
)

PUBLIC_CKAN_URL = "https://data.gov.au/data"
PUBLIC_PACKAGE_ID = "wyndham-registered-dogs-catscsv"


def test_ckan_action_url_builds_standard_api_urls() -> None:
    assert ckan_action_url(PUBLIC_CKAN_URL + "/", "package_show", {"id": PUBLIC_PACKAGE_ID}) == (
        "https://data.gov.au/data/api/3/action/package_show?id=wyndham-registered-dogs-catscsv"
    )


def test_resources_from_ckan_package_finds_direct_duckdb_resources() -> None:
    package = {
        "resources": [
            {
                "id": "csv-resource",
                "name": "Animals CSV",
                "format": "CSV",
                "url": "https://example.gov/animals.csv",
                "mimetype": "text/csv",
            },
            {
                "id": "html-resource",
                "name": "Landing page",
                "format": "HTML",
                "url": "https://example.gov/animals.html",
            },
            {
                "id": "geojson-resource",
                "name": "Boundaries",
                "format": "GeoJSON",
                "url": "https://example.gov/boundaries.geojson",
            },
        ]
    }

    resources = resources_from_ckan_package(package)
    direct = direct_duckdb_resources(resources)

    assert [resource.id for resource in direct] == ["csv-resource", "geojson-resource"]
    assert direct[0].normalized_format == "csv"
    assert direct[1].normalized_format == "geojson"


def test_render_direct_resource_sql_uses_duckdb_httpfs_reader() -> None:
    resource = CatalogResource(
        id="csv-resource",
        name="Animals CSV",
        format="CSV",
        url="https://example.gov/animals.csv",
    )

    sql = render_direct_resource_sql(resource, limit=5)

    assert "LOAD httpfs;" in sql
    assert "read_csv_auto('https://example.gov/animals.csv')" in sql
    assert "LIMIT 5;" in sql
    assert "ckan" not in sql.casefold()


def test_ckan_candidate_evidence_requires_direct_resource_and_no_table_function() -> None:
    good = ckan_direct_path_evidence(
        catalog_url=PUBLIC_CKAN_URL,
        package_id=PUBLIC_PACKAGE_ID,
        resource_count=3,
        direct_resource_count=1,
    )
    no_direct_resource = ckan_direct_path_evidence(
        catalog_url=PUBLIC_CKAN_URL,
        package_id=PUBLIC_PACKAGE_ID,
        resource_count=3,
        direct_resource_count=0,
    )
    table_function_claim = ckan_direct_path_evidence(
        catalog_url=PUBLIC_CKAN_URL,
        package_id=PUBLIC_PACKAGE_ID,
        resource_count=3,
        direct_resource_count=1,
        uses_table_function=True,
    )

    assert good.can_be_candidate()
    assert good.can_be_verified()
    assert not no_direct_resource.can_be_candidate()
    assert not table_function_claim.can_be_candidate()


@pytest.mark.skipif(
    os.environ.get("ODD_CKAN_NETWORK_TESTS") != "1",
    reason="set ODD_CKAN_NETWORK_TESTS=1 to run public CKAN/DCAT catalog smoke tests",
)
def test_public_ckan_catalog_smoke_finds_direct_csv_resource() -> None:
    package = fetch_ckan_package(PUBLIC_CKAN_URL, PUBLIC_PACKAGE_ID)
    resources = resources_from_ckan_package(package)
    direct = direct_duckdb_resources(resources)

    assert resources
    assert any(resource.normalized_format == "csv" for resource in direct)
    sql = render_direct_resource_sql(direct[0])
    assert "LOAD httpfs;" in sql
    assert "read_csv_auto(" in sql or "read_parquet(" in sql or "read_json_auto(" in sql or "ST_Read(" in sql
