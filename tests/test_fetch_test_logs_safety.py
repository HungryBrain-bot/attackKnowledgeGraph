"""
Deterministic unit test for .claude/skills/fetch-test-logs/
fetch_test_logs.py's `_safe_filename()` guard - no network call, no skip.

Written by the red-team-assessment skill's first code-lens pass
(docs/security-assessment.md, 2026-08-15): `download_scenario()` joins a
filename taken directly from the GitHub API's file-listing response onto
a local Path with no validation, which is a path-traversal shape if that
name is ever a `..`-containing or absolute path rather than a plain leaf
name. `_safe_filename()` closes that. Pinned here so a future edit can't
silently narrow the guard back to the version that let ".." through -
`Path("..").name` returns `'..'`, not `''`, which is exactly what broke
the guard's first draft before this test existed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "skills" / "fetch-test-logs"))

import pytest
from fetch_test_logs import _safe_filename


@pytest.mark.parametrize(
    "name",
    ["T1059.001.csv", "sample.evtx", "report.json"],
)
def test_safe_filename_accepts_plain_leaf_names(name):
    assert _safe_filename(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "../../../etc/cron.d/evil",
        "../evil",
        "/etc/passwd",
        "a/b",
        "..",
        ".",
        "",
    ],
)
def test_safe_filename_rejects_traversal_and_non_leaf_names(name):
    with pytest.raises(ValueError):
        _safe_filename(name)
