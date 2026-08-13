"""
Graph RAG answer synthesis (Phase 3).

Takes the facts retrieval.py already pulled from the graph and asks
Claude to format them into a short, cited natural-language answer. The
LLM never originates facts here - the system prompt forbids using
anything outside the retrieved facts block, per CLAUDE.md's Architecture
section ("LLM does not originate facts"). If a call fails, this raises
rather than returning a placeholder - a failed API call must never be
mistaken for "no relevant facts."

Model: claude-opus-5 by default (this project's Model Usage convention
in CLAUDE.md scopes cheaper tiers to development-time engineering tasks,
not to what a shipped query layer calls at runtime) - override with the
ANTHROPIC_MODEL env var if needed.
"""
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")

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


def answer(question: str, facts: str, model: str = DEFAULT_MODEL) -> str:
    """Sends the retrieved facts + question to Claude for formatting into
    a cited natural-language answer."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"FACTS:\n{facts}\n\nQUESTION: {question}",
            }
        ],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError(
            "Claude declined to answer (safety classifier refusal) - "
            f"stop_details: {response.stop_details}"
        )

    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise RuntimeError(f"No text content in response (stop_reason={response.stop_reason})")
    return text
