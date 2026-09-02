"""
llm.py — LLM client factory + embedding helper.

Interaction pattern:
  - All nodes (phase1–4) call get_llm() to get the chat model.
  - memory.py calls embed_text() to convert lesson text → vector.
  - Supports "gemini", "deepseek", "openrouter", and "mock" providers.
"""
import os
import re
from typing import Any, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from google import genai as google_genai

from agent.config import (
    GEMINI_API_KEY,
    DEEPSEEK_API_KEY,
    OPENROUTER_API_KEY,
    LLM_PROVIDER,
    EMBEDDING_PROVIDER,
)


# ── Mock LLM for Local / Free Testing ─────────────────────────────────

class MockStructuredRunnable:
    """Simulates LLM structured JSON output for Phase 1 without consuming API quota."""
    def __init__(self, schema_cls: Any):
        self.schema_cls = schema_cls

    async def ainvoke(self, messages: list[BaseMessage], **kwargs) -> Any:
        content = ""
        for m in messages:
            content += f"\n{m.content}"

        # Extract symbol if mentioned (e.g. BTC/USD or AAPL)
        symbol_match = re.search(r"Analyze\s+([A-Z0-9/]+)", content)
        symbol = symbol_match.group(1) if symbol_match else "BTC/USD"

        # Extract latest close price from the prompt if available
        price_match = re.search(r"Latest close:\s*\$([0-9.,]+)", content)
        latest_price = float(price_match.group(1).replace(",", "")) if price_match else 100.0

        # Create realistic stop loss (2.5% below) and target price (5% above)
        stop_loss = round(latest_price * 0.975, 2)
        target_price = round(latest_price * 1.05, 2)

        data = {
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "qty": 1.0,  # Advisory qty — will be replaced by risk engine
            "entry_price": latest_price,
            "target_price": target_price,
            "stop_loss_price": stop_loss,
            "thesis_text": (
                f"Technical breakout momentum observed on {symbol}. "
                f"Price holding above support at ${stop_loss:.2f}. "
                f"Targeting expansion toward ${target_price:.2f} with 2:1 reward-to-risk ratio."
            ),
            "invalidation_triggers": [
                {"condition": "Price closes below support", "threshold": f"Price < ${stop_loss:.2f}"},
                {"condition": "Sudden volume spike to downside", "threshold": "High volume red candle breach"},
            ],
        }

        if hasattr(self.schema_cls, "model_validate"):
            return self.schema_cls.model_validate(data)
        return self.schema_cls(**data)


class MockChatModel:
    """Mock Chat Model providing instant local responses for testing."""
    def with_structured_output(self, schema: Any, **kwargs):
        return MockStructuredRunnable(schema)

    async def ainvoke(self, messages: list[BaseMessage], **kwargs) -> AIMessage:
        prompt_text = "".join(str(m.content) for m in messages)

        # Phase 3 Audit check
        if "HOLD or CLOSE" in prompt_text:
            return AIMessage(content="HOLD")

        # Phase 4 Post-mortem check
        if "post-mortem" in prompt_text.lower():
            return AIMessage(
                content="Trade executed and closed disciplined according to predetermined stop-loss and take-profit targets."
            )

        return AIMessage(content="HOLD")


# ── LLM Factory ───────────────────────────────────────────────────────

def get_llm():
    """
    Returns the configured LLM client based on LLM_PROVIDER in .env.
    Supported values: "gemini", "deepseek", "openrouter", "mock"
    """
    provider = (LLM_PROVIDER or "gemini").lower()

    if provider == "mock":
        return MockChatModel()

    elif provider == "gemini":
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GEMINI_API_KEY,
            temperature=0.3,
        )

    elif provider == "deepseek":
        model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        return ChatOpenAI(
            model=model_name,
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            temperature=0.3,
        )

    elif provider == "openrouter":
        model_name = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
        return ChatOpenAI(
            model=model_name,
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.3,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'. "
        "Supported values: 'gemini', 'deepseek', 'openrouter', 'mock'"
    )


def embed_text(text: str) -> list[float]:
    """
    Converts a plain text string into a vector embedding.
    Uses google-genai SDK directly (v1 API) to avoid v1beta compatibility issues.
    Falls back gracefully if quota is unavailable.
    """
    provider = (EMBEDDING_PROVIDER or "gemini").lower()

    if provider == "mock" or not GEMINI_API_KEY:
        return [0.0] * 3072

    try:
        client = google_genai.Client(api_key=GEMINI_API_KEY)
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
        )
        return result.embeddings[0].values
    except Exception:
        # Fallback to zero vector so memory lookups don't crash execution
        return [0.0] * 3072
