"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchPortfolio,
  fetchHypotheses,
  triggerTrade,
  getActiveAccount,
  PortfolioData,
  Hypothesis,
} from "@/lib/api";
import WatchlistScanner from "@/components/WatchlistScanner";
import RiskControl from "@/components/RiskControl";

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [symbolInput, setSymbolInput] = useState("BTC/USD");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [lastRiskResult, setLastRiskResult] = useState<{ qty: number; dollarRisk: number; pctOfEquity: number } | null>(null);

  const loadData = async () => {
    try {
      const [portData, hypData] = await Promise.all([
        fetchPortfolio(),
        fetchHypotheses(),
      ]);
      setPortfolio(portData);
      setHypotheses(hypData);
    } catch (e: any) {
      console.error("Dashboard error:", e);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000); // 15s polling
    return () => clearInterval(interval);
  }, []);

  const handleTriggerTrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbolInput.trim()) return;

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    const activeAcc = getActiveAccount();
    const strategy = activeAcc?.strategyProfile || "SWING";

    try {
      const result = await triggerTrade(symbolInput.trim().toUpperCase(), strategy);
      setSuccessMsg(
        `Hypothesis created (${strategy} mode)! ID: ${result.hypothesis_id} | Status: ${result.status}`
      );
      if (result.computed_qty != null && result.dollar_risk != null && result.pct_of_equity != null) {
        setLastRiskResult({
          qty: result.computed_qty,
          dollarRisk: result.dollar_risk,
          pctOfEquity: result.pct_of_equity * 100,
        });
      }
      setSymbolInput("BTC/USD");
      await loadData();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to trigger trade");
    } finally {
      setLoading(false);
    }
  };

  const account = portfolio?.account;
  const positions = portfolio?.positions || [];

  return (
    <div className="space-[#1e293b] space-y-6">
      {/* Top Banner & Quick Trigger Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trigger Trade Card */}
        <div className="lg:col-span-1 terminal-card p-6 terminal-glow-green border-emerald-900/50">
          <h2 className="text-sm font-semibold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Trigger Trade Agent (Phase 1 & 2)
          </h2>
          <p className="text-xs text-slate-400 mb-4">
            Runs Gemini LLM reasoning to generate OHLCV hypothesis, validate risk parameters, and place Alpaca order.
          </p>

          <form onSubmit={handleTriggerTrade} className="space-y-3">
            <div>
              <label className="block text-xs text-slate-300 mb-1">
                Ticker Symbol
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={symbolInput}
                  onChange={(e) => setSymbolInput(e.target.value)}
                  placeholder="e.g. BTC/USD, ETH/USD, AAPL, NVDA"
                  className="flex-1 bg-slate-900/90 border border-slate-700 rounded px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 uppercase"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-4 py-2 rounded text-sm transition-all disabled:opacity-50 flex items-center gap-1.5"
                >
                  {loading ? (
                    <>
                      <span className="w-3 h-3 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    "Execute"
                  )}
                </button>
              </div>
            </div>

            {/* Risk Control */}
            <div className="border-t border-slate-800/60 pt-2">
              <label className="block text-[10px] text-slate-400 uppercase tracking-wider mb-1.5">
                Max Risk Per Trade
              </label>
              <RiskControl compact />
            </div>

            {errorMsg && (
              <div className="p-2.5 rounded bg-red-950/60 border border-red-800/80 text-xs text-red-300">
                {errorMsg}
              </div>
            )}
            {successMsg && (
              <div className="p-2.5 rounded bg-emerald-950/60 border border-emerald-800/80 text-xs text-emerald-300 space-y-1">
                <div>{successMsg}</div>
                {lastRiskResult && (
                  <div className="flex items-center gap-3 text-[10px] text-emerald-400/80 border-t border-emerald-900/60 pt-1">
                    <span>Qty: <strong>{lastRiskResult.qty}</strong></span>
                    <span>At Risk: <strong>${lastRiskResult.dollarRisk.toFixed(2)}</strong></span>
                    <span>Equity: <strong>{lastRiskResult.pctOfEquity.toFixed(2)}%</strong></span>
                  </div>
                )}
              </div>
            )}
          </form>
        </div>

        {/* Account Overview Metric Cards */}
        <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="terminal-card p-4 flex flex-col justify-between">
            <span className="text-xs text-slate-400 uppercase">Portfolio Value</span>
            <span className="text-xl font-bold text-slate-100 mt-1">
              ${account?.portfolio_value ? Number(account.portfolio_value).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "100,000.00"}
            </span>
            <span className="text-[10px] text-emerald-400 mt-2">Live Alpaca Balance</span>
          </div>

          <div className="terminal-card p-4 flex flex-col justify-between">
            <span className="text-xs text-slate-400 uppercase">Buying Power</span>
            <span className="text-xl font-bold text-slate-100 mt-1">
              ${account?.buying_power ? Number(account.buying_power).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "200,000.00"}
            </span>
            <span className="text-[10px] text-slate-500 mt-2">2x Margin Available</span>
          </div>

          <div className="terminal-card p-4 flex flex-col justify-between">
            <span className="text-xs text-slate-400 uppercase">Cash</span>
            <span className="text-xl font-bold text-slate-100 mt-1">
              ${account?.cash ? Number(account.cash).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "100,000.00"}
            </span>
            <span className="text-[10px] text-slate-500 mt-2">Unallocated Funds</span>
          </div>

          <div className="terminal-card p-4 flex flex-col justify-between">
            <span className="text-xs text-slate-400 uppercase">Active Positions</span>
            <span className="text-xl font-bold text-emerald-400 mt-1">
              {positions.length}
            </span>
            <span className="text-[10px] text-emerald-400 mt-2">Monitored by Phase 3</span>
          </div>
        </div>
      </div>

      {/* Selected Investment Watchlist & Auto-Scanner Bar */}
      <WatchlistScanner onScanComplete={loadData} />

      {/* Open Positions Section */}
      <div className="terminal-card p-6">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500" />
          Active Open Positions ({positions.length})
        </h3>

        {positions.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded">
            No open positions in Alpaca paper account. Trigger a new trade above to get started.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase">
                  <th className="py-2.5 px-3">Symbol</th>
                  <th className="py-2.5 px-3">Qty</th>
                  <th className="py-2.5 px-3">Avg Entry</th>
                  <th className="py-2.5 px-3">Current Price</th>
                  <th className="py-2.5 px-3">Unrealized PnL ($)</th>
                  <th className="py-2.5 px-3">Unrealized PnL (%)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {positions.map((pos) => {
                  const pnl = Number(pos.unrealized_pl);
                  const pnlPct = Number(pos.unrealized_plpc) * 100;
                  const isPositive = pnl >= 0;
                  return (
                    <tr key={pos.symbol} className="hover:bg-slate-900/40">
                      <td className="py-3 px-3 font-bold text-emerald-400">{pos.symbol}</td>
                      <td className="py-3 px-3 text-slate-200">{pos.qty}</td>
                      <td className="py-3 px-3 text-slate-300">${Number(pos.avg_entry_price).toFixed(2)}</td>
                      <td className="py-3 px-3 text-slate-300">${Number(pos.current_price).toFixed(2)}</td>
                      <td className={`py-3 px-3 font-semibold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
                        {isPositive ? "+" : ""}${pnl.toFixed(2)}
                      </td>
                      <td className={`py-3 px-3 font-semibold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
                        {isPositive ? "+" : ""}{pnlPct.toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Hypotheses Overview */}
      <div className="terminal-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-purple-500" />
            Recent Hypotheses & Trade Records ({hypotheses.length})
          </h3>
          <Link
            href="/hypotheses"
            className="text-xs text-emerald-400 hover:underline flex items-center gap-1"
          >
            View All &rarr;
          </Link>
        </div>

        {hypotheses.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded">
            No trade hypotheses created yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase">
                  <th className="py-2.5 px-3">Symbol</th>
                  <th className="py-2.5 px-3">Side</th>
                  <th className="py-2.5 px-3">Entry Price</th>
                  <th className="py-2.5 px-3">Exit Price</th>
                  <th className="py-2.5 px-3">PnL ($ / %)</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Created</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {hypotheses.slice(0, 6).map((hyp) => {
                  const pnlPct = hyp.pnl_percentage != null ? Number(hyp.pnl_percentage) : null;
                  const pnlAbs = hyp.pnl_absolute != null ? Number(hyp.pnl_absolute) : null;
                  const isPositive = (pnlPct ?? 0) >= 0;

                  return (
                    <tr key={hyp.id} className="hover:bg-slate-900/40">
                      <td className="py-3 px-3 font-bold text-slate-100 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span className="text-emerald-400">{hyp.symbol}</span>
                          <span
                            className={`px-1.5 py-0.2 rounded text-[9px] uppercase font-bold ${
                              hyp.risk_metadata?.triggered_by === "scanner"
                                ? "bg-purple-950 text-purple-300 border border-purple-800"
                                : "bg-slate-900 text-slate-400 border border-slate-700"
                            }`}
                          >
                            {hyp.risk_metadata?.triggered_by === "scanner" ? "⚡ SCAN" : "MANUAL"}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                            hyp.side === "buy"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              : "bg-red-950 text-red-400 border border-red-800"
                          }`}
                        >
                          {hyp.side}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-300 font-mono">
                        ${hyp.entry_price ? Number(hyp.entry_price).toFixed(2) : "Market"}
                      </td>
                      <td className="py-3 px-3 font-mono">
                        {hyp.exit_price != null ? (
                          <span className="text-slate-200 font-semibold">
                            ${Number(hyp.exit_price).toFixed(2)}
                          </span>
                        ) : hyp.status === "ACTIVE" ? (
                          <span className="text-emerald-400 text-[11px] animate-pulse">Live</span>
                        ) : hyp.status === "PENDING" ? (
                          <span className="text-amber-400 text-[11px]">Pending</span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        {pnlPct != null ? (
                          <div className="flex items-center gap-1.5 font-mono font-bold text-xs">
                            <span
                              className={`px-2 py-0.5 rounded border text-[11px] ${
                                isPositive
                                  ? "bg-emerald-950 text-emerald-400 border-emerald-800"
                                  : "bg-red-950 text-red-400 border-red-800"
                              }`}
                            >
                              {isPositive ? "+" : ""}
                              {pnlPct.toFixed(2)}%
                            </span>
                            {pnlAbs != null && (
                              <span className={isPositive ? "text-emerald-400" : "text-red-400"}>
                                ({isPositive ? "+" : ""}${pnlAbs.toFixed(2)})
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-600 font-mono">—</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            hyp.status === "ACTIVE"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800 animate-pulse"
                              : hyp.status === "PENDING"
                              ? "bg-amber-950 text-amber-400 border border-amber-800"
                              : hyp.status === "CLOSED"
                              ? "bg-slate-800 text-slate-300 border border-slate-700"
                              : "bg-red-950 text-red-400 border border-red-800"
                          }`}
                        >
                          {hyp.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-500">
                        {new Date(hyp.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <Link
                          href={`/hypotheses/${hyp.id}`}
                          className="text-emerald-400 hover:text-emerald-300 hover:underline text-[11px]"
                        >
                          Inspect Audit &rarr;
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
