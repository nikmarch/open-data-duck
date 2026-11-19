from __future__ import annotations

import importlib.util
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "render_precommunity_release_notes.py"

spec = importlib.util.spec_from_file_location("render_precommunity_release_notes", SCRIPT_PATH)
assert spec is not None
release_notes = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(release_notes)


def test_release_notes_are_copy_pasteable_for_the_requested_tag() -> None:
    rendered = release_notes.render_release_notes("v0.1.0-pre.3")

    assert "release_tag=v0.1.0-pre.3" in rendered
    assert "release_tag=v0.1.0-pre.1" not in rendered
    assert "bash <<BASH" in rendered
    assert "bash <<'BASH'" not in rendered
    assert rendered.index("bash <<BASH") < rendered.index("set -euo pipefail")
    assert "\nBASH\n```" in rendered
    assert "duckdb_version=" not in rendered
    assert "host=" not in rendered
    assert "repo=" not in rendered
    assert "asset=" not in rendered
    assert "asset_url=" not in rendered
    assert "\\$(printf %s h ttps://git hub .com/nikmarch/open-data-duck/releases/download/" in rendered
    assert "open_data_duck-v2.0.0-\\${platform}.duckdb_extension" in rendered
    assert "github.com" not in rendered
    assert "hub.com" not in rendered
    assert "https://" not in rendered
    assert "<https://" not in rendered
    assert "“" not in rendered
    assert "”" not in rendered
    assert "‘" not in rendered
    assert "’" not in rendered
    assert "open_data_duck.duckdb_extension" in rendered
    assert "unsupported platform" in rendered
    assert "duckdb -unsigned :memory:" in rendered
    assert "LOAD './open_data_duck.duckdb_extension';" in rendered
    assert "open_data_duck: pong" in rendered
    assert "true" in rendered
    assert "INSTALL open_data_duck FROM community;` is not expected to work" in rendered


def test_rendered_install_block_runs_in_child_bash_with_expected_url() -> None:
    rendered = release_notes.render_release_notes("v0.1.0")
    install_block_match = re.search(r"```\n(.*?)\n```", rendered, re.S)
    assert install_block_match is not None
    install_block = install_block_match.group(1)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        curl = bin_dir / "curl"
        curl.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' \"${@: -1}\" > \"${TMPDIR}/curl-url.txt\"\n"
            "touch open_data_duck.duckdb_extension\n",
            encoding="utf-8",
        )
        duckdb = bin_dir / "duckdb"
        duckdb.write_text(
            "#!/usr/bin/env bash\n"
            "cat >/dev/null\n"
            "printf 'open_data_duck: pong\\ntrue\\n'\n",
            encoding="utf-8",
        )
        for executable in (curl, duckdb):
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["TMPDIR"] = tmp
        result = subprocess.run(
            install_block,
            shell=True,
            text=True,
            cwd=tmp,
            env=env,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr + result.stdout
        assert (tmp_path / "curl-url.txt").read_text(encoding="utf-8").strip() == (
            "https://github.com/nikmarch/open-data-duck/releases/download/"
            "v0.1.0/open_data_duck-v2.0.0-linux_amd64.duckdb_extension"
        )


def test_precommunity_workflow_generates_release_notes_from_the_requested_tag() -> None:
    workflow = (ROOT / ".github" / "workflows" / "precommunity-release.yml").read_text(encoding="utf-8")

    assert "scripts/render_precommunity_release_notes.py \"${RELEASE_TAG}\"" in workflow
    assert 'release_tag="v0.1.0-pre.1"' not in workflow
    assert "release-notes.md" in workflow


def test_readme_keeps_user_first_install_guidance() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install_block_match = re.search(r"```bash\n(.*?)\n```", readme, re.S)
    assert install_block_match is not None
    install_block = install_block_match.group(1)

    assert "copy the install block from that release's notes" in readme
    assert "release_tag=v0.1.0" in install_block
    assert "release_tag=v0.1.0-pre.1" not in readme
    assert "bash <<BASH" in install_block
    assert "bash <<'BASH'" not in install_block
    assert install_block.index("bash <<BASH") < install_block.index("set -euo pipefail")
    assert "duckdb_version=" not in install_block
    assert "host=" not in install_block
    assert "repo=" not in install_block
    assert "asset=" not in install_block
    assert "asset_url=" not in install_block
    assert "\\$(printf %s h ttps://git hub .com/nikmarch/open-data-duck/releases/download/" in install_block
    assert "github.com" not in install_block
    assert "hub.com" not in install_block
    assert "https://" not in install_block
    assert "<https://" not in install_block
    assert "open_data_duck.duckdb_extension" in install_block
    assert "unsupported platform" in install_block
    assert "duckdb -unsigned :memory:" in install_block
    assert "open_data_duck: pong" in readme
    assert "Use `INSTALL open_data_duck FROM community;` only after" in readme


def test_release_tag_validation_rejects_non_tag_strings() -> None:
    try:
        release_notes.render_release_notes("latest")
    except ValueError as exc:
        assert "release tag must look like" in str(exc)
    else:
        raise AssertionError("expected invalid release tag to fail")
