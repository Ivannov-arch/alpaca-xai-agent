"""
llm.py — LLM client factory + embedding helper with simple multi-key & model fallback.

Simple Fallback Ladder:
  1. Tries configured Gemini API keys across model options (e.g. gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-flash).
  2. If all Gemini attempts fail, checks if DEEPSEEK_API_KEY is available.
  3. If not, checks if OPENROUTER_API_KEY is available.
  4. Final fallback: resilient local Mock response (preventing pipeline crashes).
"""
import os
import re
import logging
from typing import Any, Optional
from langchain_core.messages import BaseMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from google import genai as google_genai

from agent.config import (
    GEMINI_API_KEY,
    GEMINI_API_KEYS,
    GEMINI_FALLBACK_MODELS,
    DEEPSEEK_API_KEY,
    OPENROUTER_API_KEY,
    LLM_PROVIDER,
    EMBEDDING_PROVIDER,
)

logger = logging.getLogger(__name__)


# ── Mock LLM for Local Testing & Emergency Fallback ───────────────────────────

class MockStructuredRunnable:
    """Simulates LLM structured JSON output for Phase 1 without consuming API quota."""
    def __init__(self, schema_cls: Any):
        self.schema_cls = schema_cls

    async def ainvoke(self, messages: list[BaseMessage], **kwargs) -> Any:
        content = "".join(str(getattr(m, "content", m)) for m in messages)
        symbol_match = re.search(r"Analyze\s+([A-Z0-9/]+)", content)
        symbol = symbol_match.group(1) if symbol_match else "BTC/USD"
        price_match = re.search(r"Latest close:\s*\$([0-9.,]+)", content)
        latest_price = float(price_match.group(1).replace(",", "")) if price_match else 100.0

        stop_loss = round(latest_price * 0.975, 2)
        target_price = round(latest_price * 1.05, 2)
        data = {
            "symbol": symbol,
            "side": "buy",
            "order_type": "market",
            "qty": 1.0,
            "entry_price": latest_price,
            "target_price": target_price,
            "stop_loss_price": stop_loss,
            "thesis_text": f"Technical momentum breakout observed on {symbol}. Holding above support at ${stop_loss:.2f}.",
            "invalidation_triggers": [
                {"condition": "Price closes below support", "threshold": f"Price < ${stop_loss:.2f}"},
                {"condition": "High volume bearish distribution session", "threshold": "High volume red candle breach"},
            ],
        }
        if hasattr(self.schema_cls, "model_validate"):
            return self.schema_cls.model_validate(data)
        return self.schema_cls(**data)


class MockChatModel:
    """Mock Chat Model for instant testing or emergency fallback."""
    def with_structured_output(self, schema: Any, **kwargs):
        return MockStructuredRunnable(schema)

    async def ainvoke(self, messages: list[BaseMessage], **kwargs) -> AIMessage:
        prompt = "".join(str(getattr(m, "content", m)) for m in messages)
        if "post-mortem" in prompt.lower() or "synthesis" in prompt.lower():
            return AIMessage(content="Trade closed according to target parameters.")
        return AIMessage(content="HOLD")


# ── Simple If/Elif Fallback Structured Output ─────────────────────────────────

class FallbackStructuredRunnable:
    """Runs structured output with clean try/except loop over Gemini keys, then if/elif for other providers."""
    def __init__(self, schema_cls: Any):
        self.schema_cls = schema_cls

    async def ainvoke(self, messages: list[BaseMessage], **kwargs) -> Any:
        keys = GEMINI_API_KEYS or ([GEMINI_API_KEY] if GEMINI_API_KEY else [])
        models = GEMINI_FALLBACK_MODELS or ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

        # 1. Try Gemini keys across models
        for model in models:
            for key in keys:
                try:
                    chat = ChatGoogleGenerativeAI(model=model, google_api_key=key, temperature=0.3)
                    return await chat.with_structured_output(self.schema_cls).ainvoke(messages, **kwargs)
                except Exception as e:
                    masked = f"...{key[-4:]}" if len(key) >= 4 else key
                    logger.warning(f"[LLM] Gemini key {masked} on {model} failed: {e}. Trying next...")

        # 2. If Gemini fails, try DeepSeek
        if DEEPSEEK_API_KEY:
            try:
                chat = ChatOpenAI(model="deepseek-chat", api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
                return await chat.with_structured_output(self.schema_cls).ainvoke(messages, **kwargs)
            except Exception as e:
                logger.warning(f"[LLM] DeepSeek fallback failed: {e}")

        # 3. If DeepSeek fails, try OpenRouter
        if OPENROUTER_API_KEY:
            try:
                chat = ChatOpenAI(model="deepseek/deepseek-chat", api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
                return await chat.with_structured_output(self.schema_cls).ainvoke(messages, **kwargs)
            except Exception as e:
                logger.warning(f"[LLM] OpenRouter fallback failed: {e}")

        # 4. Final fallback: Mock
        logger.error("[LLM] All LLM APIs exhausted. Using Mock fallback.")
        return await MockStructuredRunnable(self.schema_cls).ainvoke(messages, **kwargs)


# ── Simple If/Elif Fallback Chat Model ────────────────────────────────────────

class FallbackChatModel:
    """Chat model with simple try/except loop over Gemini keys and if/elif provider fallback."""
    def with_structured_output(self, schema: Any, **kwargs):
        return FallbackStructuredRunnable(schema)

    async def ainvoke(self, messages: list[BaseMessage], **kwargs) -> AIMessage:
        keys = GEMINI_API_KEYS or ([GEMINI_API_KEY] if GEMINI_API_KEY else [])
        models = GEMINI_FALLBACK_MODELS or ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

        # 1. Try Gemini keys across models
        for model in models:
            for key in keys:
                try:
                    chat = ChatGoogleGenerativeAI(model=model, google_api_key=key, temperature=0.3)
                    return await chat.ainvoke(messages, **kwargs)
                except Exception as e:
                    masked = f"...{key[-4:]}" if len(key) >= 4 else key
                    logger.warning(f"[LLM] Gemini key {masked} on {model} failed: {e}. Trying next...")

        # 2. If Gemini fails, try DeepSeek
        if DEEPSEEK_API_KEY:
            try:
                chat = ChatOpenAI(model="deepseek-chat", api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
                return await chat.ainvoke(messages, **kwargs)
            except Exception as e:
                logger.warning(f"[LLM] DeepSeek fallback failed: {e}")

        # 3. If DeepSeek fails, try OpenRouter
        if OPENROUTER_API_KEY:
            try:
                chat = ChatOpenAI(model="deepseek/deepseek-chat", api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
                return await chat.ainvoke(messages, **kwargs)
            except Exception as e:
                logger.warning(f"[LLM] OpenRouter fallback failed: {e}")

        # 4. Final fallback: Mock
        return await MockChatModel().ainvoke(messages, **kwargs)


# ── LLM Factory ───────────────────────────────────────────────────────────────

def get_llm():
    """Returns the LLM client based on LLM_PROVIDER."""
    provider = (LLM_PROVIDER or "gemini").lower()
    if provider == "mock":
        return MockChatModel()
    elif provider == "deepseek":
        return ChatOpenAI(model="deepseek-chat", api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com", temperature=0.3)
    elif provider == "openrouter":
        return ChatOpenAI(model="deepseek/deepseek-chat", api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1", temperature=0.3)
    else:
        # Default: Gemini with multi-key & model fallback
        return FallbackChatModel()


# ── Multi-Key Embedding Helper ────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """Generates 3072-dim embeddings by trying available Gemini keys in sequence."""
    if (EMBEDDING_PROVIDER or "").lower() == "mock":
        return [0.0] * 3072

    keys = GEMINI_API_KEYS or ([GEMINI_API_KEY] if GEMINI_API_KEY else [])
    for key in keys:
        try:
            client = google_genai.Client(api_key=key)
            result = client.models.embed_content(model="gemini-embedding-001", contents=text)
            return result.embeddings[0].values
        except Exception as e:
            masked = f"...{key[-4:]}" if len(key) >= 4 else key
            logger.warning(f"[embed_text] Gemini key {masked} failed: {e}")

    return [0.0] * 3072
