# 🚀 Future Improvements & Roadmap: XAI Trading Agent

This document outlines the advanced development roadmap for enhancing the autonomous XAI trading agent in future iterations.

---

## 1. 💰 Dynamic Portfolio Risk & Position Sizing Control ✅
* **Description:** Implement percentage-based risk control (e.g., maximum 2% of total portfolio equity per trade) instead of fixed lot ranges.
* **UI Feature:** "Max Allocation ($ / %)" input field on the frontend dashboard to allow users to customize transaction limits.

## 2. 🔍 Automated Multi-Asset Scanner (Auto-Discovery) ✅
* **Description:** Create a background scanner that periodically monitors 50+ stock and crypto tickers. The agent automatically selects the best setups based on technical criteria for Phase 1 analysis without requiring manual user triggers.

## 3. 🎯 Dynamic Trailing Stop & Partial Profit Taking (Scale-Out)
* **Description:** Enhance Phase 3 Audit to support partial position closing (e.g., take 50% profit at 1:1 risk-to-reward ratio, then move Stop Loss to breakeven for the remaining 50%).

## 4. ⚡ Real-time WebSocket Streaming Feed
* **Description:** Replace REST API polling (15s interval) with Alpaca WebSocket Data Streaming (`wss://stream.data.alpaca.markets`) for sub-second audit evaluation during extreme market volatility (flash crashes / breakouts).

## 5. 📰 Sentiment Analysis & News Integration
* **Description:** Integrate real-time financial news sentiment data (via Finnhub / CryptoPanic API / X) into the Phase 1 LLM prompt, combining news catalysts with OHLCV price action analysis.

## 6. 🤝 Multi-LLM Ensemble Voting
* **Description:** Expand hypothesis formulation by aggregating signals from multiple LLMs (e.g., Gemini 3.6 Flash + Claude 3.5 Sonnet + DeepSeek V3). Trades execute only when at least 2 out of 3 models reach consensus.

## 7. 📊 Quantitative Backtesting Engine
* **Description:** Build a backtesting module using 1-3 years of historical market data to evaluate LangGraph state machine performance and hypothesis accuracy before live deployment.

## 8. 🏢 Multi-Account & Portfolio Scenario Isolation
* **Description:** Support managing multiple accounts and sub-portfolios with independent risk scenarios.
* **Implementation:** The database schema is ready with `account_id` foreign keys across all tables (`accounts`, `hypotheses`, `audit_logs`, `post_mortems`). Users can isolate high-risk speculative crypto portfolios from low-risk conservative stock portfolios.
* **UI Feature:** An "Account Switcher" dropdown in the terminal header to filter analytics and trade histories per account.

## 9. 🧠 Multi-Strategy Archetypes (Aggressive, Swing, Conservative)
* **Description:** Offer selectable strategy personas and risk profiles prior to triggering trades:
  * ⚡ **Scalping Mode (Aggressive):** 1-5 minute timeframe, tight stop loss (0.5–1%), sub-minute audit frequency.
  * 📈 **Swing Trading Mode (Standard):** H1–1Day timeframe, 2:1+ risk-to-reward ratio, 15-minute audit frequency.
  * 🛡️ **Conservative / Long-Term Mode:** Weekly timeframe, wider stop loss (5–10%), focus on fundamentals & accumulation, daily audit frequency.
* **Implementation:** Inject `strategy_profile` parameters into the Gemini system prompt in Phase 1 & Phase 3 to dynamically adapt risk tolerance, price targets, and invalidation triggers.
