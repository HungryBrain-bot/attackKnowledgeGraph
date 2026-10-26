"""
Graph RAG CLI (Phase 3 + Phase 5 multi-hop extension).

    python -m query.ask "what happens after T1059.001 for APT29?"
    python -m query.ask "T1566.001 then T1204.002 then T1059.001 for APT29?"

Extracts every technique ID (at least one required) and an optional
group name from the question with plain string/regex matching - no LLM
call is needed or used for this step, since ATT&CK technique IDs and
this project's three seed group names are unambiguous, well-known
identifiers. One technique ID uses the single-hop retrieval path
(query/retrieval.py's get_technique_context()); 2+, in the order they
appear in the question, uses the bounded multi-hop chain path
(get_chain_context() - see docs/decisions/008-multi-hop-chain-
retrieval.md). Retrieval (graph traversal, query/retrieval.py) and
generation (the LLM formats the retrieved facts, query/rag.py) stay two
separate, clearly-bounded steps either way.
"""
import re
import sys

from graph.seed_config import SEED_GROUPS
from query.graph_loader import load_graph
from query.llm_provider import has_credentials
from query.rag import answer
from query.retrieval import format_chain_context, format_context, get_chain_context, get_technique_context

TECHNIQUE_ID_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE)


def extract_technique_ids(question: str) -> list[str]:
    """Every technique ID mentioned, in the order they first appear,
    deduplicated. Powers both the single-technique and multi-hop chain
    paths in main() below, and api/main.py's /query."""
    ids = []
    for m in TECHNIQUE_ID_RE.finditer(question):
        tid = m.group(0).upper()
        if tid not in ids:
            ids.append(tid)
    return ids


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

    technique_ids = extract_technique_ids(question)
    if not technique_ids:
        print(
            "Couldn't find a technique ID (e.g. T1059.001) in the question - "
            "this prototype's query layer requires one."
        )
        sys.exit(1)
    group = extract_group(question)

    g = load_graph()

    try:
        if len(technique_ids) >= 2:
            context = get_chain_context(g, technique_ids, group=group)
            facts = format_chain_context(context)
        else:
            context = get_technique_context(g, technique_ids[0], group=group)
            facts = format_context(context)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

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
