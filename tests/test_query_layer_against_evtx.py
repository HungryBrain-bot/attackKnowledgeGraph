"""
First real test connecting the query layer to real attack-simulation
evidence.

For every locally-fetched EVTX/JSON sample under data/test_logs/ (see
.claude/skills/fetch-test-logs/), this:

  1. Reads the scenario's own <TTP_ID>.csv metadata - real data from the
     atomic-evtx dataset, not authored by this project - and confirms
     its self-reported "Technique" column matches the technique ID our
     fetch script filed the scenario under. Catches a fetch/parsing
     mismatch rather than trusting our own directory naming.
  2. Confirms that technique is a real node in this project's graph
     with structural usage data and at least one semantic edge - i.e.
     "for a technique real telemetry says actually happened, does our
     graph have something to say about it."
  3. Confirms query/retrieval.py's format_context() produces a
     well-formed facts block for it.

Deterministic and free - exercises query/retrieval.py only (pure Python
graph traversal), not query/rag.py's LLM call, which would be costly and
non-deterministic for an automated test.

Requires data/test_logs/ to already be populated:
    python .claude/skills/fetch-test-logs/fetch_test_logs.py --fetch
Skipped (not failed) if it hasn't been - fetching requires network
access to GitHub and isn't a hard dependency for running this project's
other tests.
"""
import csv
from pathlib import Path

import pytest

from graph.seed_config import SEED_TECHNIQUES
from query.graph_loader import load_graph
from query.retrieval import format_context, get_technique_context

TEST_LOGS_DIR = Path(__file__).parent.parent / "data" / "test_logs"


def _fetched_scenarios() -> list[tuple[str, str, Path]]:
    """Returns (technique_id, ttp_id, scenario_dir) for every locally
    fetched scenario, across whichever tier(s) were fetched."""
    if not TEST_LOGS_DIR.exists():
        return []
    scenarios = []
    for tier_dir in sorted(TEST_LOGS_DIR.iterdir()):
        if not tier_dir.is_dir():
            continue
        for technique_dir in sorted(tier_dir.iterdir()):
            if not technique_dir.is_dir():
                continue
            for scenario_dir in sorted(technique_dir.iterdir()):
                if scenario_dir.is_dir():
                    scenarios.append((technique_dir.name, scenario_dir.name, scenario_dir))
    return scenarios


SCENARIOS = _fetched_scenarios()

pytestmark = pytest.mark.skipif(
    not SCENARIOS,
    reason=(
        "No fetched EVTX samples under data/test_logs/ - run "
        "`python .claude/skills/fetch-test-logs/fetch_test_logs.py --fetch` first."
    ),
)


@pytest.fixture(scope="module")
def graph():
    return load_graph()


def _read_csv_technique(scenario_dir: Path, ttp_id: str) -> str:
    csv_path = scenario_dir / f"{ttp_id}.csv"
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows, f"{csv_path} has no data rows"
    return rows[0]["Technique"]


@pytest.mark.parametrize(
    "technique_id, ttp_id, scenario_dir",
    SCENARIOS,
    ids=[f"{t}/{s}" for t, s, _ in SCENARIOS],
)
def test_real_telemetry_technique_has_graph_context(graph, technique_id, ttp_id, scenario_dir):
    # 1. Cross-check against the real evidence file, not just our own
    # directory naming.
    reported_technique = _read_csv_technique(scenario_dir, ttp_id)
    assert reported_technique == technique_id, (
        f"{scenario_dir}: CSV reports technique {reported_technique!r}, "
        f"but was fetched under {technique_id!r}"
    )

    # 2. The technique this real telemetry says happened has real graph
    # content, not just a name in a folder.
    assert technique_id in SEED_TECHNIQUES

    context = get_technique_context(graph, technique_id)
    assert context["technique_id"] == technique_id
    assert context["name"]
    assert context["used_by"], (
        f"{technique_id} has real simulated telemetry but no structural "
        "USES_TECHNIQUE edge in the graph"
    )
    assert context["semantic_edges"], (
        f"{technique_id} has real simulated telemetry but no semantic "
        "edge in the graph"
    )

    # 3. The retrieval layer's output is well-formed.
    facts = format_context(context)
    assert technique_id in facts
    assert "TECHNIQUE:" in facts


def test_fetched_scenarios_cover_multiple_seed_techniques():
    """Sanity check on the test data itself: fail loudly (not silently
    skip) if the fetch only produced one technique's worth of samples -
    that would mean this test suite is barely exercising anything."""
    techniques_covered = {t for t, _, _ in SCENARIOS}
    assert len(techniques_covered) >= 5, (
        f"Only {len(techniques_covered)} technique(s) have fetched samples "
        f"({sorted(techniques_covered)}) - re-run fetch_test_logs.py --fetch"
    )
