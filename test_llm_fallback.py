"""
test_llm_fallback.py — Tests for multi-key and if/elif LLM fallback logic.
"""
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from pydantic import BaseModel, Field

from agent.llm import (
    FallbackChatModel,
    FallbackStructuredRunnable,
    MockStructuredRunnable,
)


class SampleTradeSchema(BaseModel):
    symbol: str = Field(description="Ticker symbol")
    side: str = Field(description="Order side")
    entry_price: float = Field(description="Entry price")
    target_price: float = Field(description="Target price")
    stop_loss_price: float = Field(description="Stop loss price")
    thesis_text: str = Field(description="Thesis explanation")


class TestLLMFallback(unittest.IsolatedAsyncioTestCase):
    async def test_mock_structured_fallback(self):
        runnable = MockStructuredRunnable(SampleTradeSchema)
        mock_msg = MagicMock(content="Analyze NVDA. Latest close: $135.50")
        res = await runnable.ainvoke([mock_msg])

        self.assertIsInstance(res, SampleTradeSchema)
        self.assertEqual(res.symbol, "NVDA")
        self.assertEqual(res.entry_price, 135.50)
        self.assertGreater(res.target_price, res.entry_price)
        self.assertLess(res.stop_loss_price, res.entry_price)

    async def test_fallback_structured_runnable(self):
        # Test that FallbackStructuredRunnable returns a valid structured schema
        fallback = FallbackStructuredRunnable(SampleTradeSchema)
        mock_msg = MagicMock(content="Analyze BTC/USD. Latest close: $92,000.00")
        res = await fallback.ainvoke([mock_msg])

        self.assertIsInstance(res, SampleTradeSchema)
        self.assertEqual(res.symbol, "BTC/USD")
        self.assertEqual(res.entry_price, 92000.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
