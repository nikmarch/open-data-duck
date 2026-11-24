from pathlib import Path


README = Path("README.md")
SOURCE_HARVESTING = Path("docs/source-harvesting.md")


def test_readme_positions_open_data_duck_as_validated_query_facade() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "Open Data Duck is not an open-data catalog" in readme
    assert "DuckDB-native, validated query facade" in readme
    assert "docs/source-harvesting.md" in readme


def test_source_harvesting_doc_captures_candidate_feeder_strategy() -> None:
    doc = SOURCE_HARVESTING.read_text(encoding="utf-8")

    assert "Do not ingest millions of catalog records directly" in doc
    assert "AWS Open Data feeder" in doc
    assert "Socrata feeder" in doc
    assert "CKAN / DCAT feeder" in doc
    assert "STAC feeder" in doc
    assert "Promotion gate" in doc
    assert "direct_sql" in doc
    assert "odd_sql" in doc
