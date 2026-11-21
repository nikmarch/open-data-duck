from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from odd import extension_registry
from odd.cli import main
from odd.extension_registry import (
    DEFAULT_EXTENSION_REGISTRY_HEADER,
    EXTENSION_REGISTRY_SCHEMA_VERSION,
    build_extension_registry,
    check_extension_registry_header,
    render_extension_registry_header,
    render_extension_registry_json,
    write_extension_registry_header,
)
from odd.registry import load_sources

REGISTRY_PATH = Path("registry/sources.yml")


def _extract_embedded_json(header_text: str) -> dict:
    start_marker = 'R"odd_registry('
    end_marker = ')odd_registry"'
    start = header_text.index(start_marker) + len(start_marker)
    end = header_text.index(end_marker)
    return json.loads(header_text[start:end])


def test_checked_in_extension_registry_header_is_current() -> None:
    assert check_extension_registry_header(REGISTRY_PATH, DEFAULT_EXTENSION_REGISTRY_HEADER) == []


def test_embedded_registry_round_trips_every_source_with_required_fields() -> None:
    sources = load_sources(REGISTRY_PATH)
    header = DEFAULT_EXTENSION_REGISTRY_HEADER.read_text(encoding="utf-8")
    embedded = _extract_embedded_json(header)

    assert embedded["schema_version"] == EXTENSION_REGISTRY_SCHEMA_VERSION
    assert embedded["source_count"] == len(sources)
    assert [record["id"] for record in embedded["sources"]] == [source.id for source in sources]
    assert f"REGISTRY_SOURCE_COUNT = {len(sources)};" in header

    redundant = {"description", "homepage", "tags", "topics", "coverage", "cadence", "ai", "duckdb"}
    for record in embedded["sources"]:
        for field in ("id", "name", "source_type", "status", "attribution", "tables"):
            assert field in record, f"{record['id']} missing {field}"
        assert not redundant & set(record), record["id"]
        for table in record["tables"]:
            if str(table.get("ref", "")).startswith("odd."):
                assert table.get("validations"), f"{record['id']}:{table.get('id')} missing validations"

    overture = next(record for record in embedded["sources"] if record["id"] == "overture.maps.release")
    assert overture["release"]["pinned"]["duckdb_setting"] == "overture_release"
    assert "stac.overturemaps.org/catalog.json" in overture["release"]["latest"]["resolve_sql"]
    assert overture["discovery"]["namespace"] == "odd.overturemaps.latest"
    assert "{release}/collections.parquet" in overture["discovery"]["discover_sql"]
    assert overture["requirements"]["duckdb_extensions"] == ["httpfs"]
    census = next(record for record in embedded["sources"] if record["id"] == "census.cartographic.county-boundaries")
    assert census["discovery"]["namespace"] == "odd.census.latest"
    assert census["release"]["pinned"]["duckdb_setting"] == "census_cartographic_year"
    plain = next(record for record in embedded["sources"] if record["id"] == "socrata.nyc.311-service-requests")
    assert "discovery" not in plain


def test_header_is_pure_generated_cpp_without_python_runtime_dependency() -> None:
    header = DEFAULT_EXTENSION_REGISTRY_HEADER.read_text(encoding="utf-8")

    assert header.startswith("// GENERATED FILE. DO NOT EDIT.")
    assert "#pragma once" in header
    assert "registry/sources.yml" in header
    assert "uv run odd generate-extension-registry" in header
    header.encode("ascii")


def test_raw_string_delimiter_cannot_leak_from_registry_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry["sources"] = registry["sources"][:1]
    registry["sources"][0]["tables"][0]["description"] = 'contains )odd_registry" delimiter'
    registry_path = tmp_path / "sources.yml"
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")

    rendered = render_extension_registry_header(load_sources(registry_path))
    body = rendered.split('R"odd_registry(', 1)[1]
    assert body.count(')odd_registry"') == 1
    assert _extract_embedded_json(rendered)["sources"][0]["tables"][0]["description"] == 'contains )odd_registry" delimiter'

    monkeypatch.setattr(extension_registry, "render_extension_registry_json", lambda sources: ')odd_registry"')
    with pytest.raises(ValueError):
        extension_registry.render_extension_registry_header(load_sources(registry_path))


def test_cli_generate_and_check_detect_drift(tmp_path: Path) -> None:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry["sources"] = registry["sources"][:2]
    registry_path = tmp_path / "sources.yml"
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    output = tmp_path / "generated.hpp"

    assert main(["generate-extension-registry", "--registry", str(registry_path), "--output", str(output), "--check"]) == 1

    assert main(["generate-extension-registry", "--registry", str(registry_path), "--output", str(output)]) == 0
    assert output.exists()
    assert main(["generate-extension-registry", "--registry", str(registry_path), "--output", str(output), "--check"]) == 0

    registry["sources"][0]["tables"][0]["description"] = "changed table description"
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    assert main(["generate-extension-registry", "--registry", str(registry_path), "--output", str(output), "--check"]) == 1

    first = write_extension_registry_header(registry_path, output).read_text(encoding="utf-8")
    second = write_extension_registry_header(registry_path, output).read_text(encoding="utf-8")
    assert first == second
    assert main(["generate-extension-registry", "--registry", str(registry_path), "--output", str(output), "--check"]) == 0


def test_json_payload_is_sorted_and_stable() -> None:
    sources = load_sources(REGISTRY_PATH)
    payload = render_extension_registry_json(sources)
    assert json.loads(payload) == build_extension_registry(sources)
    assert payload == json.dumps(json.loads(payload), indent=2, sort_keys=True)
