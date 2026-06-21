"""
rag/prompt_builder.py — Assemble LLM prompts for RAG queries.

The system prompt constrains the model to answer only from the retrieved
context sections, preventing hallucination by making the rules explicit.
"""

from rag.vector_store import RetrievedChunk

SYSTEM_PROMPT = """\
You are a technical assistant for a personal knowledge base.
Answer the user's question using ONLY the information in the context sections below.

Rules:
- If the context contains the answer, provide it clearly and concisely.
- If the context does not contain enough information, say so explicitly. Do not guess.
- Cite the source file when relevant (e.g. "According to [architecture.md]...").
- Do not invent facts, commands, or configurations that are not in the context.
"""


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    """Build the user message that injects retrieved context before the question."""
    context_sections: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        label = f"[{i}] {chunk.file_path}"
        if chunk.heading:
            label += f" — {chunk.heading}"
        context_sections.append(f"### Context {label}\n{chunk.content}")

    context_block = "\n\n".join(context_sections)

    return (
        f"{context_block}\n\n"
        f"---\n"
        f"Question: {question}\n\n"
        f"Answer based only on the context above:"
    )
