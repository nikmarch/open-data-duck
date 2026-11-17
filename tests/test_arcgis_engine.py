from __future__ import annotations

import os

import pytest

from odd.arcgis import (
    arcgis_engine_evidence,
    count_query_params,
    layer_count_url,
    layer_metadata_url,
    layer_query_url,
    parse_layer_metadata,
    plan_pages_from_metadata,
    plan_pages_from_public_layer,
)

PUBLIC_LAYER_URL = (
    "https://services.arcgis.com/V6ZHFr6zdgNZuVG0/arcgis/rest/services/"
    "CongressionalDistricts/FeatureServer/0"
)


def test_arcgis_metadata_and_count_urls_are_public_rest_urls() -> None:
    assert layer_metadata_url(f"{PUBLIC_LAYER_URL}/") == f"{PUBLIC_LAYER_URL}?f=json"
    assert layer_count_url(PUBLIC_LAYER_URL) == (
        f"{PUBLIC_LAYER_URL}/query?f=json&where=1%3D1&returnCountOnly=true"
    )
    assert count_query_params(where="STATE = 'AK'") == {
        "f": "json",
        "where": "STATE = 'AK'",
        "returnCountOnly": "true",
    }


def test_arcgis_query_url_includes_planned_page_params() -> None:
    metadata = parse_layer_metadata(
        PUBLIC_LAYER_URL,
        {
            "objectIdField": "OBJECTID",
            "maxRecordCount": 2000,
            "advancedQueryCapabilities": {"supportsPagination": True},
        },
    )
    page = plan_pages_from_metadata(
        metadata,
        total_records=435,
        page_size=200,
        out_fields="OBJECTID,DISTRICTID,NAME",
        return_geometry=False,
    )[1]

    url = layer_query_url(page.layer_url, page.params)

    assert url.startswith(f"{PUBLIC_LAYER_URL}/query?")
    assert "resultOffset=200" in url
    assert "resultRecordCount=200" in url
    assert "outFields=OBJECTID%2CDISTRICTID%2CNAME" in url
    assert "returnGeometry=false" in url
    assert "orderByFields=OBJECTID" in url


def test_parse_layer_metadata_falls_back_to_oid_field_definition() -> None:
    metadata = parse_layer_metadata(
        PUBLIC_LAYER_URL,
        {
            "fields": [
                {"name": "NAME", "type": "esriFieldTypeString"},
                {"name": "FID", "type": "esriFieldTypeOID"},
            ]
        },
    )

    assert metadata.object_id_field == "FID"
    assert metadata.max_record_count is None
    assert metadata.supports_pagination is False


def test_arcgis_candidate_evidence_requires_public_multi_page_smoke() -> None:
    good = arcgis_engine_evidence(
        public_layer_url=PUBLIC_LAYER_URL,
        object_id_field="OBJECTID",
        total_records=435,
        page_size=200,
        page_count=3,
    )
    unsigned_ci = arcgis_engine_evidence(
        public_layer_url=PUBLIC_LAYER_URL,
        object_id_field="OBJECTID",
        total_records=435,
        page_size=200,
        page_count=3,
        normal_ci_uses_unsigned_extension=True,
    )
    fake_community_install = arcgis_engine_evidence(
        public_layer_url=PUBLIC_LAYER_URL,
        object_id_field="OBJECTID",
        total_records=435,
        page_size=200,
        page_count=3,
        installs_from_community=True,
    )
    one_page = arcgis_engine_evidence(
        public_layer_url=PUBLIC_LAYER_URL,
        object_id_field="OBJECTID",
        total_records=100,
        page_size=200,
        page_count=1,
    )

    assert good.can_be_candidate()
    assert good.can_be_verified()
    assert not unsigned_ci.can_be_candidate()
    assert not fake_community_install.can_be_candidate()
    assert not one_page.can_be_candidate()


@pytest.mark.skipif(
    os.environ.get("ODD_ARCGIS_NETWORK_TESTS") != "1",
    reason="set ODD_ARCGIS_NETWORK_TESTS=1 to run public ArcGIS FeatureServer smoke tests",
)
def test_public_arcgis_feature_server_smoke_plans_multiple_pages() -> None:
    pages = plan_pages_from_public_layer(
        PUBLIC_LAYER_URL,
        page_size=200,
        out_fields="OBJECTID,DISTRICTID,NAME",
        return_geometry=False,
    )

    assert len(pages) >= 2
    assert [page.offset for page in pages[:2]] == [0, 200]
    assert all(page.params["orderByFields"] == "OBJECTID" for page in pages)
    assert all(page.params["returnGeometry"] == "false" for page in pages)
