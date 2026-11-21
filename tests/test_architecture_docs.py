from __future__ import annotations

import re
from pathlib import Path

ARCHITECTURE_DIR = Path("docs/architecture")
DIAGRAM_DIR = ARCHITECTURE_DIR / "diagrams"
EXPECTED_DIAGRAMS = {
    "module-dependencies.mmd": ("flowchart",),
    "cli-registry-sequence.mmd": ("sequenceDiagram",),
    "registry-to-extension-flow.mmd": ("flowchart",),
    "odd-facade-replacement-scan.mmd": ("sequenceDiagram",),
    "schema-manifest-flow.mmd": ("flowchart",),
}


def test_architecture_docs_link_existing_diagrams() -> None:
    readme = (ARCHITECTURE_DIR / "README.md").read_text(encoding="utf-8")
    current_state = (ARCHITECTURE_DIR / "current-state.md").read_text(encoding="utf-8")

    for diagram in EXPECTED_DIAGRAMS:
        rel = f"diagrams/{diagram}"
        assert rel in readme or rel in current_state
        assert (DIAGRAM_DIR / diagram).exists()


def test_mermaid_diagrams_have_supported_entrypoints() -> None:
    for diagram, allowed_prefixes in EXPECTED_DIAGRAMS.items():
        text = (DIAGRAM_DIR / diagram).read_text(encoding="utf-8").strip()
        assert text
        assert text.startswith(allowed_prefixes)


def test_architecture_markdown_links_resolve_locally() -> None:
    for markdown_path in ARCHITECTURE_DIR.glob("*.md"):
        text = markdown_path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^):#]+(?:#[^)]+)?)\)", text):
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            assert (markdown_path.parent / path_part).exists(), f"{markdown_path} links missing {target}"
