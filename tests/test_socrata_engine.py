from __future__ import annotations

import os

import pytest

from odd.socrata import (
    SODA_MAX_PAGE_SIZE,
    SocrataEngineEvidence,
    count_url,
    duckdb_read_sql,
    fetch_dataset_metadata,
    metadata_url,
    page_url,
    parse_count,
    parse_dataset_metadata,
    plan_offset_pages,
    plan_pages_from_public_dataset,
    resource_url,
)

PUBLIC_DOMAIN = "data.cityofnewyork.us"
PUBLIC_DATASET_ID = "erm2-nwe9"  # NYC 311 Service Requests from 2020 to Present
PUBLIC_RESOURCE_URL = f"https://{PUBLIC_DOMAIN}/resource/{PUBLIC_DATASET_ID}.csv"


def test_socrata_urls_are_public_soda_urls() -> None:
    assert resource_url(f"https://{PUBLIC_DOMAIN}/", PUBLIC_DATASET_ID) == PUBLIC_RESOURCE_URL
    assert resource_url(PUBLIC_DOMAIN, PUBLIC_DATASET_ID, fmt="geojson").endswith(".geojson")
    assert metadata_url(PUBLIC_DOMAIN, PUBLIC_DATASET_ID) == (
        f"https://{PUBLIC_DOMAIN}/api/views/metadata/v1/{PUBLIC_DATASET_ID}"
    )
    assert count_url(PUBLIC_DOMAIN, PUBLIC_DATASET_ID) == (
        f"https://{PUBLIC_DOMAIN}/resource/{PUBLIC_DATASET_ID}.json?%24select=count%28%2A%29+AS+n"
    )
    assert "%24where=borough%3D%27BRONX%27" in count_url(
        PUBLIC_DOMAIN, PUBLIC_DATASET_ID, where="borough='BRONX'"
    )


def test_socrata_rejects_malformed_identifiers() -> None:
    with pytest.raises(ValueError):
        resource_url("data.cityofnewyork.us/resource", PUBLIC_DATASET_ID)
    with pytest.raises(ValueError):
        resource_url(PUBLIC_DOMAIN, "not-a-four-by-four")
    with pytest.raises(ValueError):
        resource_url(PUBLIC_DOMAIN, PUBLIC_DATASET_ID, fmt="xml")


def test_socrata_pages_always_carry_order_limit_offset() -> None:
    pages = plan_offset_pages(
        PUBLIC_DOMAIN,
        PUBLIC_DATASET_ID,
        total_records=2_500,
        order_field="unique_key",
        page_size=1_000,
        select="unique_key,created_date",
        where="borough='BRONX'",
    )

    assert [(page.offset, page.limit) for page in pages] == [(0, 1_000), (1_000, 1_000), (2_000, 500)]
    assert all(page.resource_url == PUBLIC_RESOURCE_URL for page in pages)
    assert all(page.params["$order"] == "unique_key" for page in pages)
    assert all(page.params["$select"] == "unique_key,created_date" for page in pages)
    assert all(page.params["$where"] == "borough='BRONX'" for page in pages)

    last = page_url(pages[-1])
    assert last.startswith(f"{PUBLIC_RESOURCE_URL}?")
    assert "%24limit=500" in last
    assert "%24offset=2000" in last
    assert "%24order=unique_key" in last


def test_socrata_pages_never_exceed_soda_cap() -> None:
    assert plan_offset_pages(PUBLIC_DOMAIN, PUBLIC_DATASET_ID, total_records=0, order_field="unique_key") == []
    with pytest.raises(ValueError):
        plan_offset_pages(
            PUBLIC_DOMAIN,
            PUBLIC_DATASET_ID,
            total_records=10,
            order_field="unique_key",
            page_size=SODA_MAX_PAGE_SIZE + 1,
        )
    with pytest.raises(ValueError):
        plan_offset_pages(PUBLIC_DOMAIN, PUBLIC_DATASET_ID, total_records=10, order_field=" ")


def test_duckdb_read_sql_uses_httpfs_readers_by_format() -> None:
    csv_page = plan_offset_pages(
        PUBLIC_DOMAIN, PUBLIC_DATASET_ID, total_records=1, order_field="unique_key", select="unique_key"
    )[0]
    json_page = plan_offset_pages(
        PUBLIC_DOMAIN, PUBLIC_DATASET_ID, total_records=1, order_field="unique_key", fmt="json"
    )[0]

    assert duckdb_read_sql(csv_page).startswith("SELECT * FROM read_csv_auto('https://")
    assert duckdb_read_sql(json_page).startswith("SELECT * FROM read_json_auto('https://")
    assert "%24limit=1" in duckdb_read_sql(csv_page)


def test_parse_count_and_metadata_from_soda_payloads() -> None:
    assert parse_count([{"n": "23173787"}]) == 23_173_787
    with pytest.raises(ValueError):
        parse_count([])
    with pytest.raises(ValueError):
        parse_count([{"count": 1}])

    metadata = parse_dataset_metadata(
        PUBLIC_DOMAIN,
        PUBLIC_DATASET_ID,
        {"name": "311 Service Requests", "attribution": "311", "license": None, "dataUpdatedAt": "2026-11-17T03:14:19+0000"},
    )
    assert metadata.name == "311 Service Requests"
    assert metadata.attribution == "311"
    assert metadata.license is None
    assert metadata.data_updated_at == "2026-11-17T03:14:19+0000"


def test_socrata_candidate_evidence_requires_public_multi_page_smoke() -> None:
    def evidence(**overrides: object) -> SocrataEngineEvidence:
        fields: dict[str, object] = {
            "public_resource_url": PUBLIC_RESOURCE_URL,
            "order_field": "unique_key",
            "total_records": 2_500,
            "page_size": 1_000,
            "page_count": 3,
        }
        fields.update(overrides)
        return SocrataEngineEvidence(**fields)  # type: ignore[arg-type]

    assert evidence().can_be_candidate()
    assert evidence().can_be_verified()
    assert not evidence(requires_app_token=True).can_be_candidate()
    assert not evidence(reads_bare_export=True).can_be_candidate()
    assert not evidence(total_records=100, page_count=1).can_be_candidate()
    assert not evidence(page_size=SODA_MAX_PAGE_SIZE + 1).can_be_candidate()
    assert not evidence(order_field="").can_be_candidate()


@pytest.mark.skipif(
    os.environ.get("ODD_SOCRATA_NETWORK_TESTS") != "1",
    reason="set ODD_SOCRATA_NETWORK_TESTS=1 to run public Socrata SODA smoke tests",
)
def test_public_socrata_dataset_smoke_plans_multiple_pages_and_reads_one_in_duckdb() -> None:
    duckdb = pytest.importorskip("duckdb")

    metadata = fetch_dataset_metadata(PUBLIC_DOMAIN, PUBLIC_DATASET_ID)
    assert metadata.name
    assert metadata.data_updated_at

    pages = plan_pages_from_public_dataset(
        PUBLIC_DOMAIN,
        PUBLIC_DATASET_ID,
        order_field="unique_key",
        page_size=1_000,
        select="unique_key,created_date,complaint_type,borough",
        where="borough='STATEN ISLAND' AND created_date >= '2026-11-01T00:00:00'",
    )

    assert len(pages) >= 2
    assert [page.offset for page in pages[:2]] == [0, 1_000]
    assert all(page.params["$order"] == "unique_key" for page in pages)

    connection = duckdb.connect(":memory:")
    try:
        connection.execute("INSTALL httpfs; LOAD httpfs;")
        rows = connection.execute(
            f"SELECT count(*) FROM ({duckdb_read_sql(pages[-1])})"
        ).fetchone()
    finally:
        connection.close()

    assert rows is not None
    assert rows[0] == pages[-1].limit
