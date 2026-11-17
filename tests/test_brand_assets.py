from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


BRAND_ASSETS = [
    Path("docs/assets/brand/odd-icon.svg"),
    Path("docs/assets/brand/odd-wordmark.svg"),
    Path("docs/assets/brand/odd-wordmark-dark.svg"),
]


def test_brand_svg_assets_are_checked_in_and_safe() -> None:
    for asset in BRAND_ASSETS:
        text = asset.read_text(encoding="utf-8")

        assert text.startswith("<svg ")
        assert "<script" not in text.lower()
        assert "href=\"http://" not in text
        assert "href=\"https://" not in text
        ET.fromstring(text)


def test_brand_assets_are_linked_from_readme_and_pages_docs() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    index = Path("docs/index.md").read_text(encoding="utf-8")
    brand_page = Path("docs/brand-assets.md").read_text(encoding="utf-8")

    assert "docs/assets/brand/odd-wordmark.svg" in readme
    assert "assets/brand/odd-wordmark.svg" in index
    for asset in BRAND_ASSETS:
        assert str(asset.relative_to("docs")) in brand_page
