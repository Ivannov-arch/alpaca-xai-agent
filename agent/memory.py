"""
memory.py — Vector memory retrieval helper.

How it fits in the system:
  - Called at the START of Phase 1 (before LLM prompt is built).
  - Takes the target symbol + trade intent as a query string.
  - Embeds that query using llm.embed_text().
  - Runs a cosine similarity search via db.search_similar_post_mortems().
  - Returns a list of past lessons that get injected into the Phase 1 prompt,
    so the agent doesn't repeat the same mistakes.

Imports from:
  - agent/llm.py  (embed_text)
  - agent/db.py   (search_similar_post_mortems)
"""
from agent.llm import embed_text
from agent.db import search_similar_post_mortems


def retrieve_relevant_memories(query: str, top_k: int = 3) -> list[dict]:
    """
    Given a natural language query (e.g. "buying AAPL on momentum breakout"),
    returns the top_k most similar past post-mortem lessons.

    Args:
        query:  Natural language description of the planned trade.
        top_k:  Maximum number of lessons to retrieve.

    Returns:
        List of post-mortem dicts with fields:
          - lesson_learned (str)
          - outcome        ("WIN" | "LOSS" | "BREAKEVEN")
          - pnl_percentage (float)
          - similarity     (float, 0–1)
    """
    embedding = embed_text(query)
    return search_similar_post_mortems(embedding, limit=top_k)


def format_memories_for_prompt(memories: list[dict]) -> str:
    """
    Formats retrieved memories into a readable string block
    to be injected into the Phase 1 LLM system prompt.
    """
    if not memories:
        return "No relevant past lessons found."

    lines = ["## Relevant Past Lessons (from vector memory)\n"]
    for i, m in enumerate(memories, 1):
        lines.append(
            f"{i}. [{m['outcome']} | PnL: {m['pnl_percentage']:.1f}%] "
            f"{m['lesson_learned']}"
        )
    return "\n".join(lines)
