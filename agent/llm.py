"""
llm.py — LLM client factory + embedding helper.

Interaction pattern:
  - All nodes (phase1–4) call get_llm() to get the chat model.
  - memory.py calls embed_text() to convert lesson text → vector.
  - Centralised here so switching from Gemini to DeepSeek only
    requires changes in this one file.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
from google import genai as google_genai

from agent.config import (
    GEMINI_API_KEY,
    LLM_PROVIDER,
    EMBEDDING_PROVIDER,
)


def get_llm() -> BaseChatModel:
    """
    Returns the configured LLM client.
    Defaulting to Gemini 2.0 Flash (free tier, fast, and reliable).
    """
    if LLM_PROVIDER == "gemini":
        return ChatGoogleGenerativeAI(
            model="gemini-3.6-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0.3,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'. "
        "Supported values: 'gemini'"
    )


def embed_text(text: str) -> list[float]:
    """
    Converts a plain text string into a vector embedding (768 dims).
    Uses google-genai SDK directly (v1 API) to avoid v1beta compatibility issues
    with langchain-google-genai.
    Used in Phase 4 (post-mortem storage) and Phase 1 (memory retrieval).
    """
    if EMBEDDING_PROVIDER == "gemini":
        client = google_genai.Client(api_key=GEMINI_API_KEY)
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
        )
        return result.embeddings[0].values

    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER '{EMBEDDING_PROVIDER}'. "
        "Supported values: 'gemini'"
    )

