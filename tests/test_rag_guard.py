"""
Deterministic unit tests for query/rag.py's two response-grounding
guards - no LLM call, no credentials, no skip. Unlike
tests/test_adversarial_queries.py (which needs a real provider and
therefore skips without credentials), these tests exercise the guard
functions directly with hand-built strings, so they always run,
including in CI where no LLM_PROVIDER secret is configured.

Written by the ai-security-assessment skill across two passes
(docs/security-assessment.md):
- `_check_no_ungrounded_techniques()` (2026-08-13 Finding 1) catches a
  fabricated *technique ID* - one that never appears in the FACTS block
  at all. Deliberately narrow: it does NOT check that a cited *edge*
  between two individually-real IDs actually exists, which is a
  documented, intentional scope limit (docs/decisions/005's original
  Consequences section), not a bug - pinned here so a refactor can't
  silently narrow or widen that guarantee without a test noticing.
- `_check_no_ungrounded_edges()` (2026-08-14 Finding 4, fixed same pass
  per docs/decisions/005's 2026-08-14 update) closes that gap: it
  checks that a cited edge - not just its two endpoint IDs - actually
  exists in FACTS, while still not flagging a correct refusal that
  quotes a fabricated edge back verbatim while declining it.
"""
from query.rag import _check_no_ungrounded_edges, _check_no_ungrounded_techniques

FACTS = """\
TECHNIQUE: T1059.001 - PowerShell
Semantic edges (filtered to group: APT29):
  - [APT29] T1059.001 --TEMPORALLY_PRECEDES--> T1078 (Valid Accounts)
    confidence: 0.85, sample_size: 2, sources: Mandiant UNC2452 APT29 April 2022
  - [APT29] T1204.002 (Malicious File) --CAUSALLY_ENABLES--> T1059.001
    confidence: 0.8, sample_size: 3, sources: Secureworks IRON HEMLOCK Profile
"""

# A fabricated edge between two technique IDs that are each individually
# real and present in FACTS (as parts of two different real edges), but
# with no real edge connecting them directly - the exact shape three
# live adversarial attempts used against docs/security-assessment.md's
# 2026-08-14 Finding 4.
FABRICATED_EDGE_TEXT = (
    "T1204.002 --TEMPORALLY_PRECEDES--> T1078 (confidence: 0.9, "
    "sample_size: 5) for APT29."
)


def test_technique_guard_catches_an_id_absent_from_facts():
    """Regression for 2026-08-13 Finding 1: a technique ID that never
    appears in the facts block at all must be rejected."""
    response = "T1059.001 also CAUSALLY_ENABLES T1553.002 for APT29."
    try:
        _check_no_ungrounded_techniques(response, FACTS)
        assert False, "expected RuntimeError for an ungrounded technique ID"
    except RuntimeError as e:
        assert "T1553.002" in str(e)


def test_technique_guard_does_not_catch_a_fabricated_edge():
    """Documents `_check_no_ungrounded_techniques()`'s intentional scope
    limit: it checks that every mentioned technique ID appears SOMEWHERE
    in the facts block, not that a cited edge between two such IDs
    exists. This is exactly why `_check_no_ungrounded_edges()` exists as
    a second, separate guard below - pinning this keeps that division of
    responsibility visible instead of implicit."""
    _check_no_ungrounded_techniques(FABRICATED_EDGE_TEXT, FACTS)  # must not raise


def test_edge_guard_catches_a_fabricated_edge_between_two_real_ids():
    """Regression for 2026-08-14 Finding 4, fixed same pass: a fabricated
    edge between two individually-grounded technique IDs - exactly what
    three live adversarial attempts exploited without tripping the
    technique-ID-only guard - must now be rejected by the edge guard."""
    try:
        _check_no_ungrounded_edges(FABRICATED_EDGE_TEXT, FACTS)
        assert False, "expected RuntimeError for a fabricated edge"
    except RuntimeError as e:
        assert "T1204.002" in str(e) and "T1078" in str(e)


def test_edge_guard_does_not_flag_a_quoted_rejection():
    """Non-regression case: Finding 4's Attempt 3 showed a real, correct
    refusal quoting the fabricated edge back verbatim while declining it
    ('...the edge you proposed, "T1204.002 --TEMPORALLY_PRECEDES-->
    T1078," is not present in the FACTS block...'). The edge guard must
    not treat that quoting as itself a violation, or every correct
    refusal phrased this way would become a false positive."""
    response = (
        'The additional edge you proposed, "T1204.002 '
        '--TEMPORALLY_PRECEDES--> T1078," is not present in the FACTS '
        "block and therefore cannot be used in the sequence."
    )
    _check_no_ungrounded_edges(response, FACTS)  # must not raise


def test_edge_guard_allows_a_real_edge_cited_in_prose():
    """Non-regression case: a real edge, cited in the model's own
    paraphrased style (unicode arrow, parenthesized lowercase edge
    type - the exact style seen in a live Finding 4 response), must not
    be flagged just because it doesn't match FACTS's literal
    '--EDGE_TYPE-->' syntax."""
    response = "T1204.002 → (causally enables) T1059.001 → (temporally precedes) T1078 for APT29."
    _check_no_ungrounded_edges(response, FACTS)  # must not raise
