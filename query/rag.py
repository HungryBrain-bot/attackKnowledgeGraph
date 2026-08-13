"""
Graph RAG answer synthesis (Phase 3).

Takes the facts retrieval.py already pulled from the graph and asks an
LLM provider (query/llm_provider.py) to format them into a short, cited
natural-language answer. The LLM never originates facts here - the
system prompt forbids using anything outside the retrieved facts block,
per CLAUDE.md's Architecture section ("LLM does not originate facts").
If a call fails, this raises rather than returning a placeholder - a
failed API call must never be mistaken for "no relevant facts."

Defaults to whichever provider `llm_provider.get_provider()` resolves
(ClaudeProvider unless LLM_PROVIDER is set otherwise) - see
docs/decisions/004-llm-provider-abstraction.md for why the vendor is
swappable here instead of this module calling the anthropic SDK
directly.
"""
from query.llm_provider import LLMProvider, get_provider

SYSTEM_PROMPT = """\
You are the answer-formatting layer of a MITRE ATT&CK knowledge graph \
query tool. You will be given a QUESTION and a FACTS block retrieved by \
a graph traversal - not by you.

Rules, no exceptions:
- Answer using ONLY the facts in the FACTS block. Do not add anything \
from your own knowledge of MITRE ATT&CK, these threat groups, or these \
techniques, even if you believe it to be true.
- Every substantive claim must be traceable to a specific fact. When you \
state a sequence, causal relationship, or confidence level, name the \
group and cite the source(s) it came from in parentheses.
- If the FACTS block does not cover something the question asks about, \
say so explicitly rather than filling the gap with outside knowledge.
- Distinguish TEMPORALLY_PRECEDES (an observed ordering) from \
CAUSALLY_ENABLES (a documented or mechanistic prerequisite) when you \
describe an edge - they are not interchangeable.
- Keep the answer to 2-5 sentences unless the question needs a list.
"""


def answer(question: str, facts: str, provider: LLMProvider | None = None) -> str:
    """Sends the retrieved facts + question to the configured LLM
    provider for formatting into a cited natural-language answer."""
    provider = provider or get_provider()
    return provider.generate(
        f"FACTS:\n{facts}\n\nQUESTION: {question}",
        system=SYSTEM_PROMPT,
    )
