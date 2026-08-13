#!/usr/bin/env python3
"""
Fetches sample EVTX/JSON attack logs from arniki/atomic-evtx
(github.com/arniki/atomic-evtx - real, verified against the live repo
and its README, not assumed) for this project's SEED_TECHNIQUES. See
SKILL.md in this directory for the tier tradeoffs and how the
cross-reference below was computed.

Usage (run from the repository root):

    python .claude/skills/fetch-test-logs/fetch_test_logs.py
        # lists which seed techniques have matching simulated scenarios,
        # no download

    python .claude/skills/fetch-test-logs/fetch_test_logs.py --fetch
        # downloads up to --limit (default 1) sample scenario's log
        # files per matched technique into data/test_logs/

    python .claude/skills/fetch-test-logs/fetch_test_logs.py \
        --fetch --tier sanitized --limit 2
        # sanitized tier (tool names stripped), up to 2 scenarios/technique

Uses only the standard library (urllib) - no new project dependency for
a one-off data-fetching utility. Unauthenticated GitHub API calls are
rate-limited to 60/hour; set GITHUB_TOKEN in the environment to raise
that if you hit it (used as a Bearer token if present, not required).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "arniki/atomic-evtx"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/main"
API_BASE = f"https://api.github.com/repos/{REPO}/contents"
CSV_URL = f"{RAW_BASE}/full_list_of_attacks_simulated.csv"

# Real tier directory names, verified against the repo's own README.md -
# see SKILL.md for what each one strips and why.
TIERS = {
    "raw": "attacks_by_category_unfiltered",
    "tools-visible": "attacks_by_category_atomic_removed",
    "sanitized": "attacks_by_category_atomic_and_tools_removed",
}

TTP_ID_RE = re.compile(r"^(T\d{4}(?:\.\d{3})?)-(\d+)$")

# This script lives three directories below the repo root
# (.claude/skills/fetch-test-logs/) - walk up to it so SEED_TECHNIQUES
# is imported from graph/seed_config.py, not duplicated here to drift.
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
from graph.seed_config import SEED_TECHNIQUES  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "data" / "test_logs"


def _github_request(url: str):
    req = urllib.request.Request(url)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def fetch_csv_rows() -> list[dict]:
    with urllib.request.urlopen(CSV_URL) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def technique_id_for(ttp_id: str) -> str:
    """Strips the trailing `-N` scenario index off a TTP ID, e.g.
    "T1059.001-17" -> "T1059.001"."""
    m = TTP_ID_RE.match(ttp_id.strip())
    return m.group(1) if m else ttp_id.strip()


def cross_reference(rows: list[dict]) -> dict[str, list[dict]]:
    """Groups CSV rows by SEED_TECHNIQUES technique ID."""
    matched: dict[str, list[dict]] = {t: [] for t in SEED_TECHNIQUES}
    for row in rows:
        tid = technique_id_for(row["TTP ID"])
        if tid in matched:
            matched[tid].append(row)
    return matched


def print_summary(matched: dict[str, list[dict]]) -> None:
    matched_count = sum(1 for rows in matched.values() if rows)
    total_scenarios = sum(len(rows) for rows in matched.values())
    print(
        f"{matched_count} of {len(SEED_TECHNIQUES)} seed techniques have "
        f"matching scenarios in atomic-evtx ({total_scenarios} scenario(s) "
        "total):\n"
    )
    for tid in SEED_TECHNIQUES:
        rows = matched[tid]
        print(f"  {tid}: {len(rows)} scenario(s)")
        for row in rows:
            desc = row["Description"].strip()
            print(f"      {row['TTP ID']:<14} [{row['Category']}]  {desc}")
    missing = [t for t in SEED_TECHNIQUES if not matched[t]]
    if missing:
        print(
            f"\nNo matching scenarios for: {', '.join(missing)} - not a bug, "
            "this dataset simply doesn't simulate these techniques."
        )


def _download_file(url: str, out_path: Path) -> None:
    with urllib.request.urlopen(url) as resp:
        out_path.write_bytes(resp.read())
    print(f"    + {out_path.relative_to(REPO_ROOT)}")


def download_scenario(row: dict, tier_dir: str, dest: Path) -> None:
    """Downloads every file in one scenario's leaf directory, including
    its json/ subdirectory. Verified against the live repo: the
    top-level .evtx/.csv/.txt files are byte-identical across all three
    tiers - the tier-specific filtering (see SKILL.md) only touches the
    JSON representations. Skipping json/ would silently defeat the
    whole point of picking a tier, so it's fetched by default here."""
    category = row["Category"].strip()
    description = row["Description"].strip()
    path = f"{tier_dir}/{category}/{description}"
    url = f"{API_BASE}/{urllib.parse.quote(path)}"
    try:
        entries = _github_request(url)
    except urllib.error.HTTPError as e:
        print(f"    ! could not list {path!r}: {e}")
        return

    dest.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        if entry["type"] == "file":
            _download_file(entry["download_url"], dest / entry["name"])
        elif entry["type"] == "dir" and entry["name"] == "json":
            json_dest = dest / "json"
            json_dest.mkdir(exist_ok=True)
            for jentry in _github_request(entry["url"]):
                if jentry["type"] == "file":
                    _download_file(jentry["download_url"], json_dest / jentry["name"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fetch", action="store_true",
        help="download sample log files (default: list matches only)",
    )
    parser.add_argument(
        "--tier", choices=list(TIERS), default="sanitized",
        help="which filtering tier to fetch from (default: sanitized)",
    )
    parser.add_argument(
        "--limit", type=int, default=1,
        help="max scenarios to fetch per technique, 0 = no cap (default: 1)",
    )
    args = parser.parse_args()

    rows = fetch_csv_rows()
    matched = cross_reference(rows)
    print_summary(matched)

    if not args.fetch:
        print("\n(pass --fetch to download sample log files; --help for options)")
        return

    tier_dir = TIERS[args.tier]
    print(f"\nFetching samples (tier: {args.tier} -> {tier_dir}) ...")
    for tid in SEED_TECHNIQUES:
        scenario_rows = matched[tid]
        if not scenario_rows:
            continue
        selected = scenario_rows if args.limit == 0 else scenario_rows[: args.limit]
        for row in selected:
            ttp_id = row["TTP ID"]
            dest = OUTPUT_DIR / args.tier / tid / ttp_id
            print(f"  {ttp_id} -> {dest.relative_to(REPO_ROOT)}")
            download_scenario(row, tier_dir, dest)

    print(f"\nDone. Files under {OUTPUT_DIR.relative_to(REPO_ROOT)}/ (gitignored).")


if __name__ == "__main__":
    main()
