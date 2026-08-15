"""
Graph RAG CLI (Phase 3).

    python -m query.ask "what happens after T1059.001 for APT29?"

Extracts a technique ID (required) and an optional group name from the
question with plain string/regex matching - no LLM call is needed or
used for this step, since ATT&CK technique IDs and this project's three
seed group names are unambiguous, well-known identifiers. Retrieval
(graph traversal, query/retrieval.py) and generation (Claude formats the
retrieved facts, query/rag.py) stay two separate, clearly-bounded steps.
"""
import re
import sys

from graph.seed_config import SEED_GROUPS
from query.graph_loader import load_graph
from query.llm_provider import has_credentials
from query.rag import answer
from query.retrieval import format_context, get_technique_context

TECHNIQUE_ID_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE)


def extract_technique_id(question: str) -> str | None:
    m = TECHNIQUE_ID_RE.search(question)
    return m.group(0).upper() if m else None


def extract_group(question: str) -> str | None:
    q = question.lower()
    for group in SEED_GROUPS:
        if group.lower() in q:
            return group
    return None


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m query.ask "<question mentioning a technique ID, e.g. T1059.001>"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])

    technique_id = extract_technique_id(question)
    if technique_id is None:
        print(
            "Couldn't find a technique ID (e.g. T1059.001) in the question - "
            "this prototype's query layer requires one."
        )
        sys.exit(1)
    group = extract_group(question)

    g = load_graph()

    try:
        context = get_technique_context(g, technique_id, group=group)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    facts = format_context(context)
    print("--- Retrieved facts (from the graph, not the LLM) ---")
    print(facts)

    if not has_credentials():
        print(
            "\n(No LLM provider credentials configured - showing retrieved "
            "facts only. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env, "
            "matching LLM_PROVIDER, for a formatted answer.)"
        )
        return

    print("\n--- Answer ---")
    print(answer(question, facts))


if __name__ == "__main__":
    main()
