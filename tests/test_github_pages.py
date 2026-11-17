from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

from odd.registry import find_source, render_source_sql


class LinkAndAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()
        self.assets: set[str] = set()
        self.scripts: set[str] = set()
        self.examples: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.add(values["href"] or "")
        if tag in {"img", "link"}:
            ref = values.get("src") or values.get("href")
            if ref:
                self.assets.add(ref)
        if tag == "script" and values.get("src"):
            self.scripts.add(values["src"] or "")
        if values.get("data-example"):
            self.examples.add(values["data-example"] or "")


def load_pages_builder():
    spec = importlib.util.spec_from_file_location(
        "build_pages_site", Path("scripts/build_pages_site.py")
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pages_builder_publishes_static_site_with_brand_assets(tmp_path: Path) -> None:
    builder = load_pages_builder()
    output_dir = builder.build_site(tmp_path / "site")

    index = output_dir / "index.html"
    assert index.exists()
    assert (output_dir / "styles.css").exists()
    assert (output_dir / "terminal.js").exists()
    assert (output_dir / "demo-recipes.json").exists()
    assert (output_dir / ".nojekyll").exists()

    parser = LinkAndAssetParser()
    parser.feed(index.read_text(encoding="utf-8"))

    assert "assets/brand/odd-wordmark.svg" in parser.assets
    assert "assets/brand/odd-icon.svg" in parser.assets
    assert (output_dir / "assets" / "brand" / "odd-wordmark.svg").exists()
    assert (output_dir / "assets" / "brand" / "odd-icon.svg").exists()
    assert "terminal.js" in parser.scripts
    assert "#try-it" in parser.links
    assert "https://github.com/nikmarch/open-data-duck" in parser.links
    assert "https://github.com/nikmarch/open-data-duck/blob/main/docs/index.md" in parser.links


def test_pages_try_it_demo_is_allowlisted_and_static() -> None:
    parser = LinkAndAssetParser()
    parser.feed(Path("site/index.html").read_text(encoding="utf-8"))
    recipes = json.loads(Path("site/demo-recipes.json").read_text(encoding="utf-8"))
    script = Path("site/terminal.js").read_text(encoding="utf-8")

    recipe_ids = {recipe["id"] for recipe in recipes["examples"]}
    assert parser.examples == {
        "overture.maps.release",
        "census.cartographic.county-boundaries",
        "aws.noaa-ghcn-daily",
    }
    assert recipe_ids == parser.examples
    assert recipes["architecture"]["mode"] == "static-allowlisted-sql"
    assert len(recipes["examples"]) == 3
    assert all(recipe["command"].startswith("odd sql ") for recipe in recipes["examples"])
    assert all("LIMIT 10" in recipe["sql"] for recipe in recipes["examples"])
    assert "fetch(\"demo-recipes.json\"" in script
    assert "eval(" not in script
    assert "new Function" not in script
    assert "@duckdb/duckdb-wasm" not in Path("site/index.html").read_text(encoding="utf-8")


def test_pages_demo_recipes_match_registry_sql() -> None:
    recipes = json.loads(Path("site/demo-recipes.json").read_text(encoding="utf-8"))

    for recipe in recipes["examples"]:
        source = find_source(Path("registry/sources.yml"), recipe["id"])
        assert source is not None
        assert recipe["sql"] == render_source_sql(source, validation=False, include_install=True)


def test_pages_workflow_uses_github_actions_pages_deploy() -> None:
    workflow = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")

    assert "actions/configure-pages@v5" in workflow
    assert "actions/upload-pages-artifact@v3" in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "python scripts/build_pages_site.py" in workflow
    assert "branches: [main]" in workflow


def test_pages_site_source_is_valid_html() -> None:
    result = subprocess.run(
        ["python3", "scripts/build_pages_site.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stderr == ""
    try:
        parser = LinkAndAssetParser()
        parser.feed(Path("_site/index.html").read_text(encoding="utf-8"))
    finally:
        shutil.rmtree("_site")
