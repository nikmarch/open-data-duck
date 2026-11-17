from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class ArcGISPageRequest:
    layer_url: str
    offset: int
    record_count: int
    params: dict[str, str]


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

    if not layer_url.startswith(("http://", "https://")):
        raise ValueError("layer_url must be an HTTP(S) URL")
    if total_records < 0:
        raise ValueError("total_records must be non-negative")
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    if not object_id_field.strip():
        raise ValueError("object_id_field must be present")

    page_count = ceil(total_records / page_size) if total_records else 0
    return [
        ArcGISPageRequest(
            layer_url=layer_url.rstrip("/"),
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
