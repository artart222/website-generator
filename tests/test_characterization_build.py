"""Characterization (golden) test for the demo site build.

This locks the byte-for-byte output of the demo build (`config.yaml`) so that
the refactoring roadmap can proceed with provable behavior preservation.

The build is deterministic (verified: two consecutive builds produce identical
hashes for all output files), so a SHA-256 manifest is a reliable oracle.

If an intentional change alters output, regenerate the manifest on Linux (matches CI)
after ensuring ``.gitattributes`` enforces LF line endings::

    WG_REGENERATE_GOLDEN=1 python -m pytest tests/test_characterization_build.py

On Windows, use Docker or WSL so the golden matches Ubuntu CI. After adding or
updating ``.gitattributes``, run ``git add --renormalize .`` once and refresh
your working tree so source files are checked out with LF.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_MANIFEST = Path(__file__).resolve().parent / "golden" / "demo_output_manifest.json"


def _hash_tree(root: Path) -> dict[str, str]:
    """Return {relative_posix_path: sha256_hex} for every file under ``root``."""
    manifest: dict[str, str] = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            absolute = Path(dirpath) / filename
            relative = absolute.relative_to(root).as_posix()
            manifest[relative] = hashlib.sha256(absolute.read_bytes()).hexdigest()
    return manifest


def _build_demo_site() -> Path:
    """Run the demo build via the SSG core and return the output directory.

    Uses ``core`` directly (not ``cli``) to keep this characterization test
    focused on the static-site generator and independent of the Django runtime.
    """
    # Imported lazily so collection does not fail if core is mid-refactor.
    from core.bootstrap import bootstrap
    from core.project import Project

    config = bootstrap(str(PROJECT_ROOT / "config.yaml"))
    project = Project(config)
    project.build()

    output_dir = PROJECT_ROOT / "output"
    assert output_dir.is_dir(), "build did not produce an output directory"
    return output_dir


@pytest.fixture(scope="module")
def built_output() -> dict[str, str]:
    output_dir = _build_demo_site()
    return _hash_tree(output_dir)


def test_demo_build_matches_golden_manifest(built_output):
    if os.environ.get("WG_REGENERATE_GOLDEN") == "1":
        GOLDEN_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_MANIFEST.write_text(
            json.dumps(built_output, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Regenerated golden manifest.")

    assert GOLDEN_MANIFEST.exists(), (
        "Golden manifest missing. Generate it with --regenerate-golden."
    )
    golden = json.loads(GOLDEN_MANIFEST.read_text(encoding="utf-8"))

    golden_files = set(golden)
    built_files = set(built_output)

    missing = sorted(golden_files - built_files)
    unexpected = sorted(built_files - golden_files)
    changed = sorted(
        path
        for path in golden_files & built_files
        if golden[path] != built_output[path]
    )

    assert not missing, f"Output files missing vs golden: {missing}"
    assert not unexpected, f"Unexpected new output files vs golden: {unexpected}"
    assert not changed, f"Output content changed vs golden: {changed}"
