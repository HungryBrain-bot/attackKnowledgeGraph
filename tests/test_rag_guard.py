"""
Deterministic unit tests for query/rag.py's _check_no_ungrounded_
techniques() guard - no LLM call, no credentials, no skip. Unlike
tests/test_adversarial_queries.py (which needs a real provider and
therefore skips without credentials), these tests exercise the guard
function directly with hand-built strings, so they always run,
including in CI where no LLM_PROVIDER secret is configured.

Written by the ai-security-assessment skill following its 2026-08-14
pass (docs/security-assessment.md) - the guard reliably catches a
fabricated *technique ID* (2026-08-13 Finding 1), but that same pass's
live testing found it does not, and structurally cannot, catch a
fabricated *edge* or fabricated *attributes* (confidence/sample_size/
sources/group_context) between two technique IDs that are each
individually real and present in the facts block. That's a documented,
open limitation (docs/decisions/005's scope note), not a bug - this
test pins it in code so it can't be silently "fixed" by an unrelated
refactor without someone noticing the guarantee changed.
"""
from query.rag import _check_no_ungrounded_techniques

FACTS = """\
TECHNIQUE: T1059.001 - PowerShell
Semantic edges (filtered to group: APT29):
  - [APT29] T1059.001 --TEMPORALLY_PRECEDES--> T1078 (Valid Accounts)
    confidence: 0.85, sample_size: 2, sources: Mandiant UNC2452 APT29 April 2022
  - [APT29] T1204.002 (Malicious File) --CAUSALLY_ENABLES--> T1059.001
    confidence: 0.8, sample_size: 3, sources: Secureworks IRON HEMLOCK Profile
"""


def test_catches_a_technique_id_absent_from_facts():
    """Regression for 2026-08-13 Finding 1: a technique ID that never
    appears in the facts block at all must be rejected."""
    response = "T1059.001 also CAUSALLY_ENABLES T1553.002 for APT29."
    try:
        _check_no_ungrounded_techniques(response, FACTS)
        assert False, "expected RuntimeError for an ungrounded technique ID"
    except RuntimeError as e:
        assert "T1553.002" in str(e)


def test_does_not_catch_a_fabricated_edge_between_two_real_ids():
    """Known, open limitation (2026-08-14 pass): the guard checks that
    every technique ID mentioned in the answer appears SOMEWHERE in the
    facts block text - it does not check that a cited edge between two
    such IDs actually exists. T1204.002 and T1078 are both individually
    present in FACTS (as parts of two different real edges), but no
    edge connects them directly - the guard cannot see that and does
    not raise. This is exactly what three live adversarial attempts
    exploited without tripping it (docs/security-assessment.md); this
    test exists so that gap stays documented and visible even though
    it's an accepted, not-yet-fixed limitation."""
    response = (
        "T1204.002 --TEMPORALLY_PRECEDES--> T1078 (confidence: 0.9, "
        "sample_size: 5) for APT29."
    )
    _check_no_ungrounded_techniques(response, FACTS)  # must not raise
