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
- `_check_no_ungrounded_edges()` (2026-08-14 Finding 4) checks that a
  cited edge - not just its two endpoint IDs - actually exists in
  FACTS, while still not flagging a correct refusal that quotes a
  fabricated edge back verbatim while declining it. Tightened
  2026-10-26 (docs/decisions/005's amendment) after four review probes
  passed it; those probes are the second half of this file.
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


# --- 2026-10-26 senior-security-engineer review probes ---------------------
#
# The review fed answer() fixed model replies (a stub LLMProvider, no
# network) and found four fabrications that passed both guards, even
# though ADR-005's 2026-08-14 update said the edge guard closed the
# "fabricated attribute" gap. Each probe below is one of those replies,
# run through the real answer() entry point rather than the private
# helpers, so the test covers exactly what a caller would get back.
# See docs/decisions/005's 2026-10-26 amendment.

import pytest

from query.llm_provider import LLMProvider
from query.rag import answer


class _FixedReplyProvider(LLMProvider):
    """Returns a canned reply - stands in for a model that has already
    been talked into fabricating something. No network call."""

    def __init__(self, reply: str):
        self.reply = reply

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        return self.reply


def _answer_with(reply: str) -> str:
    return answer("what follows T1059.001 for APT29?", FACTS, provider=_FixedReplyProvider(reply))


def test_probe_a_real_edge_with_fabricated_confidence_is_rejected():
    """Probe (a): the edge exists, but at confidence 0.85, not 0.99."""
    with pytest.raises(RuntimeError, match="confidence"):
        _answer_with("For APT29, T1059.001 --TEMPORALLY_PRECEDES--> T1078 (confidence: 0.99).")


def test_probe_b_real_edge_labelled_with_the_wrong_group_is_rejected():
    """Probe (b): the edge exists for APT29 only; the reply credits APT28."""
    with pytest.raises(RuntimeError, match="APT28"):
        _answer_with("For APT28, T1059.001 --TEMPORALLY_PRECEDES--> T1078.")


def test_probe_c_passive_voice_fabricated_edge_is_rejected():
    """Probe (c): 'T1078 is causally enabled by T1204.002' asserts the
    edge T1204.002 --CAUSALLY_ENABLES--> T1078, which is not in FACTS.
    The old pattern only matched the active form 'causally enables'."""
    with pytest.raises(RuntimeError, match="T1204.002"):
        _answer_with("For APT29, T1078 is causally enabled by T1204.002.")


def test_probe_d_fabricated_edge_followed_by_a_rejection_cue_is_rejected():
    """Probe (d): the old guard skipped any unmatched edge with a
    rejection phrase in the next 160 characters, so an assertion that
    merely mentions 'not documented publicly' slipped through."""
    with pytest.raises(RuntimeError, match="T1204.002"):
        _answer_with(
            "T1204.002 --TEMPORALLY_PRECEDES--> T1078 for APT29. This step is "
            "not documented publicly, but it is how the intrusion proceeded."
        )


def test_correct_answer_with_real_attributes_still_passes():
    """Non-regression for the probe fixes: a reply that cites a real
    edge with its real group and confidence must still come back."""
    reply = "For APT29, T1059.001 --TEMPORALLY_PRECEDES--> T1078 (confidence: 0.85, sample_size: 2)."
    assert _answer_with(reply) == reply


def test_attribute_claims_are_checked_against_their_own_edge():
    """Two edges in one sentence, each with its own real confidence -
    the 0.8 claim belongs to the second edge and must not be checked
    against the first edge's stored 0.85."""
    reply = (
        "For APT29, T1059.001 --TEMPORALLY_PRECEDES--> T1078, and "
        "T1204.002 --CAUSALLY_ENABLES--> T1059.001 (confidence: 0.8)."
    )
    assert _answer_with(reply) == reply


def test_unquoted_rejection_cue_no_longer_excuses_an_edge():
    """The quoted-rejection skip needs the edge quoted verbatim; the
    same refusal wording around an unquoted edge is still an assertion."""
    with pytest.raises(RuntimeError):
        _check_no_ungrounded_edges(
            "T1204.002 --TEMPORALLY_PRECEDES--> T1078 is not present in the FACTS block, but it happened.",
            FACTS,
        )


def test_every_real_facts_block_passes_its_own_guard():
    """False-positive check against the real graph: a reply that just
    repeats a real FACTS block verbatim (every edge, group, confidence
    and sample_size exactly as stored) must pass both guards, for every
    seed technique and for an unfiltered chain."""
    from graph.seed_config import SEED_TECHNIQUES
    from query.graph_loader import load_graph
    from query.retrieval import format_chain_context, format_context, get_chain_context, get_technique_context

    g = load_graph()
    blocks = [format_context(get_technique_context(g, t)) for t in SEED_TECHNIQUES]
    blocks.append(format_chain_context(get_chain_context(g, ["T1566.001", "T1059.001"])))
    for facts in blocks:
        _check_no_ungrounded_techniques(facts, facts)
        _check_no_ungrounded_edges(facts, facts)
