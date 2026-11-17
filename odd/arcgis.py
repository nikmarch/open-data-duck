from __future__ import annotations

import json
from dataclasses import dataclass
from math import ceil
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


@dataclass(frozen=True)
class ArcGISLayerMetadata:
    layer_url: str
    object_id_field: str
    max_record_count: int | None
    supports_pagination: bool


@dataclass(frozen=True)
class ArcGISPageRequest:
    layer_url: str
    offset: int
    record_count: int
    params: dict[str, str]


@dataclass(frozen=True)
class ArcGISEngineEvidence:
    public_layer_url: str
    object_id_field: str
    total_records: int
    page_size: int
    page_count: int
    normal_ci_uses_unsigned_extension: bool = False
    installs_from_community: bool = False

    def can_be_candidate(self) -> bool:
        return (
            self.public_layer_url.startswith(("http://", "https://"))
            and bool(self.object_id_field.strip())
            and self.total_records > self.page_size > 0
            and self.page_count > 1
            and not self.normal_ci_uses_unsigned_extension
            and not self.installs_from_community
        )

    def can_be_verified(self) -> bool:
        return self.can_be_candidate() and self.total_records > 0


def normalize_layer_url(layer_url: str) -> str:
    if not layer_url.startswith(("http://", "https://")):
        raise ValueError("layer_url must be an HTTP(S) URL")
    return layer_url.rstrip("/")


def layer_metadata_url(layer_url: str) -> str:
    return arcgis_url(layer_url, {"f": "json"})


def layer_count_url(layer_url: str, *, where: str = "1=1") -> str:
    return layer_query_url(layer_url, count_query_params(where=where))


def layer_query_url(layer_url: str, params: dict[str, str]) -> str:
    return arcgis_url(f"{normalize_layer_url(layer_url)}/query", params)


def arcgis_url(url: str, params: dict[str, str]) -> str:
    separator = "&" if "?" in url else "?"
    return f"{normalize_layer_url(url)}{separator}{urlencode(params)}"


def count_query_params(*, where: str = "1=1") -> dict[str, str]:
    return {
        "f": "json",
        "where": where,
        "returnCountOnly": "true",
    }


def fetch_json(url: str, *, timeout: int = 20) -> dict[str, Any]:
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - public smoke-test helper
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"ArcGIS response must be a JSON object: {url}")
    if "error" in payload:
        raise ValueError(f"ArcGIS returned error for {url}: {payload['error']}")
    return payload


def fetch_layer_metadata(layer_url: str, *, timeout: int = 20) -> ArcGISLayerMetadata:
    return parse_layer_metadata(layer_url, fetch_json(layer_metadata_url(layer_url), timeout=timeout))


def fetch_layer_count(layer_url: str, *, where: str = "1=1", timeout: int = 20) -> int:
    payload = fetch_json(layer_count_url(layer_url, where=where), timeout=timeout)
    count = payload.get("count")
    if not isinstance(count, int):
        raise ValueError(f"ArcGIS count response missing integer count: {payload}")
    return count


def parse_layer_metadata(layer_url: str, metadata: dict[str, Any]) -> ArcGISLayerMetadata:
    object_id_field = metadata.get("objectIdField") or metadata.get("objectIdFieldName")
    if not isinstance(object_id_field, str) or not object_id_field.strip():
        object_id_field = _object_id_field_from_fields(metadata.get("fields"))
    if not object_id_field:
        raise ValueError("ArcGIS layer metadata does not include an object id field")

    max_record_count = metadata.get("maxRecordCount")
    if not isinstance(max_record_count, int):
        max_record_count = None

    advanced_query = metadata.get("advancedQueryCapabilities")
    supports_pagination = False
    if isinstance(advanced_query, dict):
        supports_pagination = bool(advanced_query.get("supportsPagination"))

    return ArcGISLayerMetadata(
        layer_url=normalize_layer_url(layer_url),
        object_id_field=object_id_field,
        max_record_count=max_record_count,
        supports_pagination=supports_pagination,
    )


def plan_pages_from_metadata(
    metadata: ArcGISLayerMetadata,
    *,
    total_records: int,
    page_size: int | None = None,
    where: str = "1=1",
    out_fields: str = "*",
    return_geometry: bool = True,
) -> list[ArcGISPageRequest]:
    requested_page_size = page_size or metadata.max_record_count or 2000
    return plan_offset_pages(
        metadata.layer_url,
        total_records=total_records,
        page_size=requested_page_size,
        object_id_field=metadata.object_id_field,
        where=where,
        out_fields=out_fields,
        return_geometry=return_geometry,
    )


def plan_pages_from_public_layer(
    layer_url: str,
    *,
    page_size: int | None = None,
    where: str = "1=1",
    out_fields: str = "*",
    return_geometry: bool = True,
    timeout: int = 20,
) -> list[ArcGISPageRequest]:
    metadata = fetch_layer_metadata(layer_url, timeout=timeout)
    total_records = fetch_layer_count(layer_url, where=where, timeout=timeout)
    return plan_pages_from_metadata(
        metadata,
        total_records=total_records,
        page_size=page_size,
        where=where,
        out_fields=out_fields,
        return_geometry=return_geometry,
    )


def arcgis_engine_evidence(
    *,
    public_layer_url: str,
    object_id_field: str,
    total_records: int,
    page_size: int,
    page_count: int,
    normal_ci_uses_unsigned_extension: bool = False,
    installs_from_community: bool = False,
) -> ArcGISEngineEvidence:
    return ArcGISEngineEvidence(
        public_layer_url=public_layer_url,
        object_id_field=object_id_field,
        total_records=total_records,
        page_size=page_size,
        page_count=page_count,
        normal_ci_uses_unsigned_extension=normal_ci_uses_unsigned_extension,
        installs_from_community=installs_from_community,
    )


def plan_offset_pages(
    layer_url: str,
    *,
    total_records: int,
    page_size: int,
    object_id_field: str,
    where: str = "1=1",
    out_fields: str = "*",
    return_geometry: bool = True,
) -> list[ArcGISPageRequest]:
    """Plan ArcGIS REST offset pagination requests for one public layer.

    ArcGIS FeatureServer and MapServer layers cap each response at maxRecordCount.
    A wrapper engine should first ask for a count, then page with resultOffset /
    resultRecordCount rather than relying on a single truncated response.
    """

    normalized_layer_url = normalize_layer_url(layer_url)
    if total_records < 0:
        raise ValueError("total_records must be non-negative")
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    if not object_id_field.strip():
        raise ValueError("object_id_field must be present")

    page_count = ceil(total_records / page_size) if total_records else 0
    return [
        ArcGISPageRequest(
            layer_url=normalized_layer_url,
            offset=offset,
            record_count=min(page_size, total_records - offset),
            params={
                "f": "json",
                "where": where,
                "outFields": out_fields,
                "returnGeometry": "true" if return_geometry else "false",
                "resultOffset": str(offset),
                "resultRecordCount": str(min(page_size, total_records - offset)),
                "orderByFields": object_id_field,
            },
        )
        for offset in (page_index * page_size for page_index in range(page_count))
    ]


def _object_id_field_from_fields(fields: Any) -> str | None:
    if not isinstance(fields, list):
        return None
    for field in fields:
        if not isinstance(field, dict):
            continue
        if field.get("type") == "esriFieldTypeOID" and isinstance(field.get("name"), str):
            return field["name"]
    return None
