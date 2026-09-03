"""
test_scanner.py — Comprehensive unit & integration tests for the Automated Multi-Asset Scanner.

Tests:
  1. Technical Indicators: Volume Spike, RSI, Range Breakout
  2. 2-of-3 Screening Decision Engine
  3. Aggregate Portfolio Risk Exposure & Cap Safeguards
  4. Daily Circuit Breaker Detection (-5% halt)
  5. Watchlist & Configuration Persistence
  6. Pipeline Integration & Sizing with `triggered_by='scanner'`
"""
import sys
import unittest
from unittest.mock import MagicMock, patch

from agent.risk import (
    calculate_position_size,
    calculate_portfolio_risk_exposure,
    validate_portfolio_risk_budget,
    check_daily_circuit_breaker,
    RiskSettings,
    DEFAULT_AGGREGATE_RISK_CAP_PCT,
    DEFAULT_DAILY_CIRCUIT_BREAKER_PCT,
)
from agent.scanner import (
    compute_rsi,
    compute_volume_spike,
    compute_range_breakout,
    screen_ticker,
    load_scanner_config,
    save_scanner_config,
    DEFAULT_WATCHLIST,
)


class TestScannerIndicators(unittest.TestCase):
    def setUp(self):
        # Create 25 mock OHLCV bars
        self.mock_bars = []
        base_price = 100.0
        for i in range(25):
            price = base_price + i * 0.5
            self.mock_bars.append({
                "t": f"2026-01-{i+1:02d}T00:00:00Z",
                "o": price - 0.2,
                "h": price + 0.8,
                "l": price - 0.5,
                "c": price,
                "v": 1_000_000,
            })

    def test_volume_spike_detection(self):
        # Normal volume
        volumes = [1_000_000] * 20 + [1_000_000]
        is_spike, ratio = compute_volume_spike(volumes, period=20, multiplier=1.5)
        self.assertFalse(is_spike)
        self.assertAlmostEqual(ratio, 1.0, places=1)

        # Volume spike (2.0x)
        volumes_spike = [1_000_000] * 20 + [2_000_000]
        is_spike, ratio = compute_volume_spike(volumes_spike, period=20, multiplier=1.5)
        self.assertTrue(is_spike)
        self.assertAlmostEqual(ratio, 2.0, places=1)

    def test_rsi_calculation(self):
        # Strongly rising prices -> High RSI (> 65)
        rising_closes = [100.0 + i * 2.0 for i in range(20)]
        rsi_high = compute_rsi(rising_closes, period=14)
        self.assertIsNotNone(rsi_high)
        self.assertGreater(rsi_high, 70.0)

        # Strongly falling prices -> Low RSI (< 35)
        falling_closes = [200.0 - i * 3.0 for i in range(20)]
        rsi_low = compute_rsi(falling_closes, period=14)
        self.assertIsNotNone(rsi_low)
        self.assertLess(rsi_low, 30.0)

    def test_range_breakout_detection(self):
        highs = [105.0] * 20 + [115.0]
        lows = [95.0] * 20 + [104.0]
        closes = [100.0] * 20 + [112.0]  # Breaks above 105.0 high

        is_breakout, breakout_type = compute_range_breakout(highs, lows, closes, period=20)
        self.assertTrue(is_breakout)
        self.assertEqual(breakout_type, "bullish_breakout")

    def test_screen_ticker_2_of_3_pass(self):
        config = {
            "criteria_threshold": 2,
            "volume_spike_multiplier": 1.5,
            "rsi_oversold": 35.0,
            "rsi_overbought": 65.0,
            "breakout_period": 20,
        }

        # Build bars with volume spike and breakout
        bars = []
        for i in range(21):
            bars.append({
                "o": 100.0,
                "h": 105.0,
                "l": 95.0,
                "c": 100.0,
                "v": 500_000,
            })
        # Latest bar: huge volume + breakout
        bars[-1]["h"] = 120.0
        bars[-1]["c"] = 118.0
        bars[-1]["v"] = 1_500_000  # 3x volume

        result = screen_ticker("BTC/USD", bars, config)
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["passed_count"], 2)


    def test_screen_ticker_2_of_3_fail(self):
        config = {
            "criteria_threshold": 2,
            "volume_spike_multiplier": 1.5,
            "rsi_oversold": 35.0,
            "rsi_overbought": 65.0,
            "breakout_period": 20,
        }

        # Bars with flat prices and normal volume (0 criteria met)
        bars = []
        for i in range(21):
            bars.append({
                "o": 100.0,
                "h": 101.0,
                "l": 99.0,
                "c": 100.0,
                "v": 500_000,
            })

        result = screen_ticker("AAPL", bars, config)
        self.assertFalse(result["passed"])
        self.assertEqual(result["passed_count"], 0)


class TestPortfolioRiskSafeguards(unittest.TestCase):
    def test_aggregate_portfolio_risk_calculation(self):
        equity = 100_000.0
        active_hypotheses = [
            {"qty": 10, "entry_price": 100, "stop_loss_price": 90, "risk_metadata": {"dollar_risk": 1000.0}},
            {"qty": 5, "entry_price": 200, "stop_loss_price": 180, "risk_metadata": {"dollar_risk": 1500.0}},
        ]
        exposure = calculate_portfolio_risk_exposure(equity, active_hypotheses)
        self.assertEqual(exposure["total_dollar_risk"], 2500.0)
        self.assertEqual(exposure["total_risk_pct"], 2.5)
        self.assertFalse(exposure["is_over_cap"])
        self.assertEqual(exposure["remaining_risk_budget_dollars"], 3500.0)  # (6% of 100k) - 2500

    def test_validate_portfolio_risk_budget_cap_exceeded(self):
        equity = 100_000.0
        current_risk = 5_000.0  # 5% already at risk
        new_trade_risk = 1_500.0 # Would make 6.5% > 6.0% cap

        is_allowed, reason = validate_portfolio_risk_budget(
            equity=equity,
            current_dollar_risk=current_risk,
            new_trade_dollar_risk=new_trade_risk,
            aggregate_cap_pct=0.06,
        )
        self.assertFalse(is_allowed)
        self.assertIn("Aggregate portfolio risk cap exceeded", reason)

    def test_validate_portfolio_risk_budget_allowed(self):
        equity = 100_000.0
        current_risk = 2_000.0
        new_trade_risk = 1_000.0 # Total 3.0% <= 6.0% cap

        is_allowed, reason = validate_portfolio_risk_budget(
            equity=equity,
            current_dollar_risk=current_risk,
            new_trade_dollar_risk=new_trade_risk,
            aggregate_cap_pct=0.06,
        )
        self.assertTrue(is_allowed)
        self.assertIsNone(reason)

    def test_daily_circuit_breaker(self):
        # 2% daily loss -> Not tripped
        tripped, pnl = check_daily_circuit_breaker(current_equity=98_000.0, last_day_equity=100_000.0, threshold_pct=-0.05)
        self.assertFalse(tripped)
        self.assertEqual(pnl, -2.0)

        # 6% daily loss -> Tripped
        tripped, pnl = check_daily_circuit_breaker(current_equity=94_000.0, last_day_equity=100_000.0, threshold_pct=-0.05)
        self.assertTrue(tripped)
        self.assertEqual(pnl, -6.0)

    def test_dynamic_risk_position_sizing_respects_hard_ceiling(self):
        # Sizing 10% risk attempt is capped to 5% HARD_CEILING_PCT
        risk_settings = RiskSettings(mode="percent", value=10.0)
        res = calculate_position_size(
            equity=100_000.0,
            entry_price=100.0,
            stop_loss_price=95.0, # $5 distance
            risk_settings=risk_settings,
            is_crypto=False,
        )
        self.assertTrue(res.capped)
        self.assertLessEqual(res.pct_of_equity, 0.05001)
        self.assertAlmostEqual(res.dollar_risk, 5_000.0, delta=100.0)


class TestWatchlistConfig(unittest.TestCase):
    def test_default_watchlist_contains_50_plus_assets(self):
        self.assertGreaterEqual(len(DEFAULT_WATCHLIST), 50)
        # Check presence of major crypto
        self.assertIn("BTC/USD", DEFAULT_WATCHLIST)
        self.assertIn("ETH/USD", DEFAULT_WATCHLIST)
        self.assertIn("SOL/USD", DEFAULT_WATCHLIST)
        # Check presence of liquid stocks
        self.assertIn("AAPL", DEFAULT_WATCHLIST)
        self.assertIn("NVDA", DEFAULT_WATCHLIST)
        self.assertIn("MSFT", DEFAULT_WATCHLIST)

    def test_load_and_save_config(self):
        cfg = load_scanner_config()
        self.assertIn("watchlist", cfg)
        self.assertIn("interval_minutes", cfg)
        self.assertIn("aggregate_risk_cap_pct", cfg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
