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
    # Drift guard: fails when registry/sources.yml changes without regenerating the header.
    assert check_extension_registry_header(REGISTRY_PATH, DEFAULT_EXTENSION_REGISTRY_HEADER) == []


def test_embedded_registry_round_trips_every_source_with_required_fields() -> None:
    sources = load_sources(REGISTRY_PATH)
    header = DEFAULT_EXTENSION_REGISTRY_HEADER.read_text(encoding="utf-8")
    embedded = _extract_embedded_json(header)

    assert embedded["schema_version"] == EXTENSION_REGISTRY_SCHEMA_VERSION
    assert embedded["source_count"] == len(sources)
    assert [record["id"] for record in embedded["sources"]] == [source.id for source in sources]
    assert f"REGISTRY_SOURCE_COUNT = {len(sources)};" in header

    for record in embedded["sources"]:
        for field in (
            "id",
            "name",
            "source_type",
            "status",
            "description",
            "tags",
            "attribution",
            "duckdb",
            "release",
        ):
            assert field in record, f"{record['id']} missing {field}"
        assert record["duckdb"]["example_query"].strip()
        assert record["duckdb"]["validation_query"].strip()
        assert isinstance(record["duckdb"]["extensions"], list)
        assert isinstance(record["duckdb"]["examples"], dict)

    overture = next(record for record in embedded["sources"] if record["id"] == "overture.maps.release")
    assert overture["release"]["pinned"]["duckdb_setting"] == "overture_release"
    assert "stac.overturemaps.org/catalog.json" in overture["release"]["latest"]["resolve_sql"]
    assert overture["duckdb"]["facades"][0] == {
        "description": "Global building footprints from Overture Maps releases.",
        "example_sql": "SELECT *\nFROM odd.overturemaps.latest.buildings\nWHERE bbox.xmin <= -149\n  AND bbox.xmax >= -150\n  AND bbox.ymin <= 61\n  AND bbox.ymax >= 60\nLIMIT 10;",
        "facade_function": "open_data_overture_buildings",
        "path_glob": "s3://overturemaps-us-west-2/release/{release}/theme=buildings/type=building/*",
        "reader": "read_parquet",
        "table_reference": "odd.overturemaps.latest.buildings",
    }
    census = next(record for record in embedded["sources"] if record["id"] == "census.cartographic.county-boundaries")
    assert census["duckdb"]["facades"][0]["reader"] == "st_read"
    assert census["duckdb"]["facades"][0]["table_reference"] == "odd.census.latest.counties"
    assert census["release"]["pinned"]["duckdb_setting"] == "census_cartographic_year"
    assert set(overture["duckdb"]["examples"]) >= {
        "places_bbox_direct_s3",
        "buildings_bbox_direct_s3",
        "road_segments_bbox_direct_s3",
        "addresses_bbox_direct_s3",
    }


def test_header_is_pure_generated_cpp_without_python_runtime_dependency() -> None:
    header = DEFAULT_EXTENSION_REGISTRY_HEADER.read_text(encoding="utf-8")

    assert header.startswith("// GENERATED FILE. DO NOT EDIT.")
    assert "#pragma once" in header
    assert "registry/sources.yml" in header
    assert "uv run odd generate-extension-registry" in header
    # ASCII-only so the C++ literal is portable across compilers/locales.
    header.encode("ascii")


def test_raw_string_delimiter_cannot_leak_from_registry_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry["sources"] = registry["sources"][:1]
    registry["sources"][0]["description"] = 'contains )odd_registry" delimiter'
    registry_path = tmp_path / "sources.yml"
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")

    # json.dumps escapes the quote, so the raw delimiter cannot appear verbatim inside the literal.
    rendered = render_extension_registry_header(load_sources(registry_path))
    body = rendered.split('R"odd_registry(', 1)[1]
    assert body.count(')odd_registry"') == 1  # only the real closing delimiter
    assert _extract_embedded_json(rendered)["sources"][0]["description"] == 'contains )odd_registry" delimiter'

    # Belt-and-braces: the explicit guard rejects a crafted payload.
    monkeypatch.setattr(extension_registry, "render_extension_registry_json", lambda sources: ')odd_registry"')
    with pytest.raises(ValueError):
        extension_registry.render_extension_registry_header(load_sources(registry_path))


def test_cli_generate_and_check_detect_drift(tmp_path: Path) -> None:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry["sources"] = registry["sources"][:2]
    registry_path = tmp_path / "sources.yml"
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    output = tmp_path / "generated.hpp"

    # Missing header fails the check.
    assert main(["generate-extension-registry", "--registry", str(registry_path), "--output", str(output), "--check"]) == 1

    assert main(["generate-extension-registry", "--registry", str(registry_path), "--output", str(output)]) == 0
    assert output.exists()
    assert main(["generate-extension-registry", "--registry", str(registry_path), "--output", str(output), "--check"]) == 0

    # Registry change without regeneration is detected.
    registry["sources"][0]["description"] = "changed description"
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    assert main(["generate-extension-registry", "--registry", str(registry_path), "--output", str(output), "--check"]) == 1

    # Regeneration restores a clean check and is deterministic.
    first = write_extension_registry_header(registry_path, output).read_text(encoding="utf-8")
    second = write_extension_registry_header(registry_path, output).read_text(encoding="utf-8")
    assert first == second
    assert main(["generate-extension-registry", "--registry", str(registry_path), "--output", str(output), "--check"]) == 0


def test_json_payload_is_sorted_and_stable() -> None:
    sources = load_sources(REGISTRY_PATH)
    payload = render_extension_registry_json(sources)
    assert json.loads(payload) == build_extension_registry(sources)
    assert payload == json.dumps(json.loads(payload), indent=2, sort_keys=True)
