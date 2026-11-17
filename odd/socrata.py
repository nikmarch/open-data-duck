from __future__ import annotations

import json
from dataclasses import dataclass
from math import ceil
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

# SODA 2.1 endpoints cap a single response at 50,000 rows; older 2.0 endpoints
# cap at 1,000. Open Data Duck never asks for more than this per page so a
# truncated response is never mistaken for the full dataset.
SODA_MAX_PAGE_SIZE = 50_000
SODA_DEFAULT_PAGE_SIZE = 1_000
SODA_FORMATS = ("csv", "json", "geojson")


@dataclass(frozen=True)
class SocrataDatasetMetadata:
    domain: str
    dataset_id: str
    name: str
    attribution: str | None
    license: str | None
    data_updated_at: str | None


@dataclass(frozen=True)
class SocrataPageRequest:
    resource_url: str
    offset: int
    limit: int
    params: dict[str, str]


@dataclass(frozen=True)
class SocrataEngineEvidence:
    public_resource_url: str
    order_field: str
    total_records: int
    page_size: int
    page_count: int
    requires_app_token: bool = False
    reads_bare_export: bool = False

    def can_be_candidate(self) -> bool:
        return (
            self.public_resource_url.startswith(("http://", "https://"))
            and bool(self.order_field.strip())
            and 0 < self.page_size <= SODA_MAX_PAGE_SIZE
            and self.total_records > self.page_size
            and self.page_count > 1
            and not self.requires_app_token
            and not self.reads_bare_export
        )

    def can_be_verified(self) -> bool:
        return self.can_be_candidate() and self.total_records > 0


def normalize_domain(domain: str) -> str:
    domain = domain.strip()
    if domain.startswith(("http://", "https://")):
        domain = domain.split("://", 1)[1]
    domain = domain.rstrip("/")
    if not domain or "/" in domain:
        raise ValueError("domain must be a bare Socrata host such as data.cityofnewyork.us")
    return domain


def validate_dataset_id(dataset_id: str) -> str:
    dataset_id = dataset_id.strip()
    parts = dataset_id.split("-")
    if len(parts) != 2 or not all(len(part) == 4 and part.isalnum() for part in parts):
        raise ValueError("dataset_id must be a Socrata four-by-four id such as erm2-nwe9")
    return dataset_id


def resource_url(domain: str, dataset_id: str, *, fmt: str = "csv") -> str:
    if fmt not in SODA_FORMATS:
        raise ValueError(f"fmt must be one of {SODA_FORMATS}")
    return f"https://{normalize_domain(domain)}/resource/{validate_dataset_id(dataset_id)}.{fmt}"


def metadata_url(domain: str, dataset_id: str) -> str:
    return f"https://{normalize_domain(domain)}/api/views/metadata/v1/{validate_dataset_id(dataset_id)}"


def soda_url(url: str, params: dict[str, str]) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(params)}"


def count_query_params(*, where: str | None = None) -> dict[str, str]:
    params = {"$select": "count(*) AS n"}
    if where:
        params["$where"] = where
    return params


def count_url(domain: str, dataset_id: str, *, where: str | None = None) -> str:
    return soda_url(resource_url(domain, dataset_id, fmt="json"), count_query_params(where=where))


def fetch_json(url: str, *, timeout: int = 20) -> Any:
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - public smoke-test helper
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, dict) and payload.get("error"):
        raise ValueError(f"Socrata returned error for {url}: {payload.get('message', payload)}")
    return payload


def parse_dataset_metadata(domain: str, dataset_id: str, metadata: dict[str, Any]) -> SocrataDatasetMetadata:
    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Socrata metadata does not include a dataset name")
    return SocrataDatasetMetadata(
        domain=normalize_domain(domain),
        dataset_id=validate_dataset_id(dataset_id),
        name=name,
        attribution=_optional_str(metadata.get("attribution")),
        license=_optional_str(metadata.get("license")),
        data_updated_at=_optional_str(metadata.get("dataUpdatedAt")),
    )


def parse_count(payload: Any) -> int:
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise ValueError(f"Socrata count response must be a single-row list: {payload!r}")
    raw = payload[0].get("n")
    if not isinstance(raw, (str, int)):
        raise ValueError(f"Socrata count response missing integer n: {payload!r}")
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError(f"Socrata count response missing integer n: {payload!r}") from error


def fetch_dataset_metadata(domain: str, dataset_id: str, *, timeout: int = 20) -> SocrataDatasetMetadata:
    payload = fetch_json(metadata_url(domain, dataset_id), timeout=timeout)
    if not isinstance(payload, dict):
        raise ValueError("Socrata metadata response must be a JSON object")
    return parse_dataset_metadata(domain, dataset_id, payload)


def fetch_dataset_count(domain: str, dataset_id: str, *, where: str | None = None, timeout: int = 20) -> int:
    return parse_count(fetch_json(count_url(domain, dataset_id, where=where), timeout=timeout))


def plan_offset_pages(
    domain: str,
    dataset_id: str,
    *,
    total_records: int,
    order_field: str,
    page_size: int = SODA_DEFAULT_PAGE_SIZE,
    fmt: str = "csv",
    select: str | None = None,
    where: str | None = None,
) -> list[SocrataPageRequest]:
    """Plan SODA offset pagination requests for one public dataset.

    Socrata caps each response at $limit (default 1,000; max 50,000 on SODA 2.1).
    A wrapper engine should ask for a count first, then page with $limit/$offset
    under a deterministic $order so truncated responses are never treated as the
    complete dataset.
    """

    url = resource_url(domain, dataset_id, fmt=fmt)
    if total_records < 0:
        raise ValueError("total_records must be non-negative")
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    if page_size > SODA_MAX_PAGE_SIZE:
        raise ValueError(f"page_size must not exceed SODA cap of {SODA_MAX_PAGE_SIZE}")
    if not order_field.strip():
        raise ValueError("order_field must be present")

    page_count = ceil(total_records / page_size) if total_records else 0
    pages: list[SocrataPageRequest] = []
    for page_index in range(page_count):
        offset = page_index * page_size
        limit = min(page_size, total_records - offset)
        params: dict[str, str] = {}
        if select:
            params["$select"] = select
        if where:
            params["$where"] = where
        params["$order"] = order_field
        params["$limit"] = str(limit)
        params["$offset"] = str(offset)
        pages.append(SocrataPageRequest(resource_url=url, offset=offset, limit=limit, params=params))
    return pages


def plan_pages_from_public_dataset(
    domain: str,
    dataset_id: str,
    *,
    order_field: str,
    page_size: int = SODA_DEFAULT_PAGE_SIZE,
    fmt: str = "csv",
    select: str | None = None,
    where: str | None = None,
    timeout: int = 20,
) -> list[SocrataPageRequest]:
    total_records = fetch_dataset_count(domain, dataset_id, where=where, timeout=timeout)
    return plan_offset_pages(
        domain,
        dataset_id,
        total_records=total_records,
        order_field=order_field,
        page_size=page_size,
        fmt=fmt,
        select=select,
        where=where,
    )


def page_url(page: SocrataPageRequest) -> str:
    return soda_url(page.resource_url, page.params)


def duckdb_read_sql(page: SocrataPageRequest) -> str:
    """Render the DuckDB read call for one planned page (httpfs must be loaded)."""

    url = page_url(page).replace("'", "''")
    if page.resource_url.endswith(".csv"):
        return f"SELECT * FROM read_csv_auto('{url}')"
    return f"SELECT * FROM read_json_auto('{url}')"


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None
