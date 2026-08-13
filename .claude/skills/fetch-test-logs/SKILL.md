---
name: fetch-test-logs
description: "Use this skill when you need real Windows EVTX/JSON attack-simulation logs to test or validate the query layer (or any future detection logic) against this project's seed technique set. Documents which of the 13 SEED_TECHNIQUES have real simulated log samples in the arniki/atomic-evtx dataset, which of its three filtering tiers to use for which purpose, and a script to pull them."
---

# Fetch Test Logs (atomic-evtx)

Source: [`github.com/arniki/atomic-evtx`](https://github.com/arniki/atomic-evtx)
- real, verified against the live repo (its README, its
`full_list_of_attacks_simulated.csv`, and its directory structure via
the GitHub API) while writing this skill, not assumed. 1,064 Windows
attack scenarios, simulated via the Atomic Red Team framework on a
Windows 10 VM, with logs from Sysmon, Application, System, Security,
and Windows PowerShell. Spans 12 ATT&CK tactic categories, from Initial
Access (12 techniques) to Defense Evasion (367).

## The three filtering tiers - and a real caveat about what they actually filter

The dataset's own README documents three tiers, each a top-level
directory:

| Tier | Directory | What's removed | What remains |
|---|---|---|---|
| Raw | `attacks_by_category_unfiltered` | Nothing | Everything, unmodified |
| Tools visible | `attacks_by_category_atomic_removed` | Atomic Red Team framework references (`atomic`, `redcanary`, etc.) and pre-attack log-clearing events (`wevtutil.exe cl ...`) | Offensive tool names (Mimikatz, Cobalt Strike, WinPwn, ...) stay intact |
| Sanitized | `attacks_by_category_atomic_and_tools_removed` | Everything the tools-visible tier removes, **plus** offensive tool/project names (replaced with the generic string `script`) | Only PowerShell script content and Event ID patterns - the dataset's own README calls this the "most challenging" tier for exactly that reason |

**Caveat, verified directly against the repo and not obvious from the
README alone: this filtering only touches the JSON representations, in
each scenario's `json/` subdirectory.** The top-level `.evtx`, `.csv`,
and `.txt` files are byte-identical across all three tiers - confirmed
by comparing file sizes for the same scenario (`Process Discovery -
tasklist`, T1057-2) across `attacks_by_category_unfiltered` and
`attacks_by_category_atomic_and_tools_removed`: every top-level file
matched exactly, while the `json/` files differed substantially (e.g.
the Sysmon JSON dropped from 58,796 to 31,700 bytes - consistent with
the README's description of event-entry removal, not just string
substitution). **If the goal is testing whether detection logic holds
up without literal tool-name strings, the redacted content is in
`json/`, not the raw `.evtx` files** - `fetch_test_logs.py` (below)
downloads both by default specifically because skipping `json/` would
silently defeat the point of picking a tier.

## Which tier for which purpose

- **Sanitized** (`attacks_by_category_atomic_and_tools_removed`) - use
  this for testing whether detection reasoning or a query-layer answer
  holds up without relying on literal tool-name strings (Mimikatz,
  Cobalt Strike, ...). This is the tier the project owner asked for
  specifically for that purpose.
- **Tools visible** (`attacks_by_category_atomic_removed`) - use when
  tool names should stay present but Atomic Red Team's own framework
  noise (and the log-clearing artifacts from generating the dataset)
  would otherwise contaminate the test.
- **Raw** (`attacks_by_category_unfiltered`) - only when the literal,
  unmodified ground truth is needed, framework artifacts included.

## Cross-reference against this project's SEED_TECHNIQUES

Computed by matching `full_list_of_attacks_simulated.csv`'s `TTP ID`
column (format `<technique_id>-<scenario index>`, e.g. `T1059.001-17`)
against `graph/seed_config.py`'s `SEED_TECHNIQUES`. Verified result as
of this writing: **11 of 13 seed techniques have matching simulated
scenarios (96 scenarios total)**.

| Technique | Scenarios | Technique | Scenarios |
|---|---|---|---|
| T1566.001 | 2 | T1057 | 7 |
| T1204.002 | 11 | T1083 | 5 |
| T1059.001 | 12 | T1021.001 | 4 |
| T1547.001 | 19 | T1071.001 | 2 |
| T1078 | **0** | T1105 | 21 |
| T1003.002 | 8 | T1560.001 | 5 |
| | | T1074.002 | **0** |

**T1078 (Valid Accounts) and T1074.002 (Remote Data Staging) have no
matching scenarios in this dataset.** Not a bug in the matching logic -
Atomic Red Team doesn't have atomics for either as standalone
techniques in this dataset's simulation run. Don't invent samples for
them; if test coverage for those two is ever needed, it has to come
from a different source.

## Directory layout (for manual browsing)

```
attacks_by_category_<tier>/<category-kebab-case>/<Description>/
    <TTP_ID>.csv
    <TTP_ID>.txt
    <TTP_ID>_Application.evtx
    <TTP_ID>_Microsoft-Windows-Sysmon_Operational.evtx
    <TTP_ID>_Security.evtx
    <TTP_ID>_System.evtx
    <TTP_ID>_Windows PowerShell.evtx
    json/
        <TTP_ID>_<same 5 log sources>.json   <- tier-specific filtering lives here
```

`<category-kebab-case>` and `<Description>` are the CSV's `Category`
and `Description` columns, used as literal directory names (stripped of
leading/trailing whitespace - some CSV rows have trailing spaces that
the actual directory names don't). There's also a flat `ttp_evtx/
<TTP_ID>/` index at the repo root that mirrors the raw tier's top-level
files by TTP ID for quick lookup - it has no tier selection and no
`json/` variant, so `fetch_test_logs.py` doesn't use it.

## Fetching samples

`fetch_test_logs.py` in this directory (stdlib-only, no new project
dependency). Run from the repository root:

```bash
# list which seed techniques have matches - no download
python .claude/skills/fetch-test-logs/fetch_test_logs.py

# download 1 sample scenario per matched technique, sanitized tier (the default)
python .claude/skills/fetch-test-logs/fetch_test_logs.py --fetch

# more scenarios, a different tier
python .claude/skills/fetch-test-logs/fetch_test_logs.py --fetch --tier raw --limit 3

# every matched scenario, tools-visible tier
python .claude/skills/fetch-test-logs/fetch_test_logs.py --fetch --tier tools-visible --limit 0
```

Output lands in `data/test_logs/<tier>/<technique_id>/<ttp_id>/`
(gitignored - this is fetched test data, not committed). Unauthenticated
GitHub API calls are rate-limited to 60/hour; set `GITHUB_TOKEN` in the
environment to raise that if a larger `--limit` run hits it.

## Scope - what this is not

This is a data-fetching utility only. It is not wired into the query
layer, a test suite, or any CI step - see CLAUDE.md's note under
Current status. It exists so real test/validation data is one command
away whenever detection-logic testing against the query layer becomes
the next piece of work, not because that work has started.
