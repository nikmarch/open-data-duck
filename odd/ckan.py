from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

SUPPORTED_DIRECT_FORMATS = {
    "csv": "read_csv_auto",
    "geojson": "ST_Read",
    "json": "read_json_auto",
    "jsonl": "read_json_auto",
    "ndjson": "read_json_auto",
    "parquet": "read_parquet",
}


@dataclass(frozen=True)
class CatalogResource:
    id: str
    name: str
    url: str
    format: str
    media_type: str | None = None

    @property
    def normalized_format(self) -> str:
        normalized = self.format.strip().casefold().replace(".", "")
        if normalized in {"geojson", "geo+json", "application/geo+json"}:
            return "geojson"
        if normalized in {"jsonl", "ndjson"}:
            return "jsonl"
        if normalized == "application/json":
            return "json"
        if normalized in {"text/csv", "csv"}:
            return "csv"
        if normalized in {"application/parquet", "parquet"}:
            return "parquet"
        return normalized

    def is_direct_duckdb_resource(self) -> bool:
        return self.url.startswith(("http://", "https://", "s3://")) and self.normalized_format in SUPPORTED_DIRECT_FORMATS


@dataclass(frozen=True)
class CKANDirectPathEvidence:
    catalog_url: str
    package_id: str
    resource_count: int
    direct_resource_count: int
    uses_table_function: bool = False

    def can_be_candidate(self) -> bool:
        return (
            self.catalog_url.startswith(("http://", "https://"))
            and bool(self.package_id.strip())
            and self.resource_count > 0
            and self.direct_resource_count > 0
            and not self.uses_table_function
        )

    def can_be_verified(self) -> bool:
        return self.can_be_candidate()


def ckan_action_url(catalog_url: str, action: str, params: dict[str, str] | None = None) -> str:
    base = catalog_url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise ValueError("catalog_url must be an HTTP(S) URL")
    query = f"?{urlencode(params)}" if params else ""
    return f"{base}/api/3/action/{action}{query}"


def fetch_ckan_json(catalog_url: str, action: str, params: dict[str, str], *, timeout: int = 20) -> dict[str, Any]:
    url = ckan_action_url(catalog_url, action, params)
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - public catalog smoke-test helper
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"CKAN response must be a JSON object: {url}")
    if not payload.get("success"):
        raise ValueError(f"CKAN returned an unsuccessful response for {url}: {payload}")
    return payload


def fetch_ckan_package(catalog_url: str, package_id: str, *, timeout: int = 20) -> dict[str, Any]:
    payload = fetch_ckan_json(catalog_url, "package_show", {"id": package_id}, timeout=timeout)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError("CKAN package_show result must be a JSON object")
    return result


def resources_from_ckan_package(package: dict[str, Any]) -> list[CatalogResource]:
    resources = package.get("resources")
    if not isinstance(resources, list):
        return []

    parsed: list[CatalogResource] = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        url = resource.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        resource_id = resource.get("id")
        name = resource.get("name") or resource.get("description") or url.rsplit("/", 1)[-1]
        fmt = resource.get("format") or resource.get("mimetype") or ""
        media_type = resource.get("mimetype")
        parsed.append(
            CatalogResource(
                id=str(resource_id or url),
                name=str(name),
                url=url.strip(),
                format=str(fmt),
                media_type=str(media_type) if media_type else None,
            )
        )
    return parsed


def direct_duckdb_resources(resources: list[CatalogResource]) -> list[CatalogResource]:
    return [resource for resource in resources if resource.is_direct_duckdb_resource()]


def render_direct_resource_sql(resource: CatalogResource, *, limit: int = 10) -> str:
    if not resource.is_direct_duckdb_resource():
        raise ValueError(f"resource is not a supported direct DuckDB resource: {resource.url}")
    reader = SUPPORTED_DIRECT_FORMATS[resource.normalized_format]
    escaped_url = resource.url.replace("'", "''")
    return f"LOAD httpfs;\nSELECT *\nFROM {reader}('{escaped_url}')\nLIMIT {limit};\n"


def ckan_direct_path_evidence(
    *,
    catalog_url: str,
    package_id: str,
    resource_count: int,
    direct_resource_count: int,
    uses_table_function: bool = False,
) -> CKANDirectPathEvidence:
    return CKANDirectPathEvidence(
        catalog_url=catalog_url,
        package_id=package_id,
        resource_count=resource_count,
        direct_resource_count=direct_resource_count,
        uses_table_function=uses_table_function,
    )
