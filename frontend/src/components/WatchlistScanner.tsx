"use client";

import { useEffect, useState, useMemo } from "react";
import {
  fetchScannerStatus,
  fetchScannerConfig,
  updateScannerConfig,
  toggleScanner,
  triggerManualScan,
  fetchPortfolioRisk,
  ScannerStatus,
  ScannerConfig,
  PortfolioRiskExposure,
  ScreenResult,
} from "@/lib/api";

const DEFAULT_CRYPTO_PRESET = [
  "BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "AVAX/USD",
  "LINK/USD", "DOT/USD", "ADA/USD", "LTC/USD", "XRP/USD",
  "NEAR/USD", "UNI/USD", "MATIC/USD", "SHIB/USD", "BCH/USD", "ATOM/USD"
];

const DEFAULT_STOCK_PRESET = [
  "AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "GOOGL", "META", "AMD",
  "INTC", "NFLX", "SPY", "QQQ", "IWM", "COIN", "PLTR", "ARM",
  "SMCI", "MU", "AVGO", "DIS", "JPM", "BAC", "V", "MA",
  "PYPL", "CRM", "ORCL", "CSCO", "ADBE", "UBER", "ABNB", "SQ",
  "MARA", "RIOT", "MSTR", "HOOD"
];

export default function WatchlistScanner({ onScanComplete }: { onScanComplete?: () => void }) {
  const [status, setStatus] = useState<ScannerStatus | null>(null);
  const [config, setConfig] = useState<ScannerConfig | null>(null);
  const [riskExposure, setRiskExposure] = useState<PortfolioRiskExposure | null>(null);

  const [activeTab, setActiveTab] = useState<"all" | "crypto" | "stocks">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [newTickerInput, setNewTickerInput] = useState("");

  const [isScanningManual, setIsScanningManual] = useState(false);
  const [isToggling, setIsToggling] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  // Editable settings modal state
  const [editInterval, setEditInterval] = useState(15);
  const [editThreshold, setEditThreshold] = useState(2);
  const [editMaxEscalations, setEditMaxEscalations] = useState(3);
  const [editCapPct, setEditCapPct] = useState(6.0);
  const [editCircuitBreaker, setEditCircuitBreaker] = useState(-5.0);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // Time until next scan countdown
  const [secondsUntilNext, setSecondsUntilNext] = useState<number | null>(null);

  const loadAll = async () => {
    try {
      const [statusData, cfgData, riskData] = await Promise.all([
        fetchScannerStatus(),
        fetchScannerConfig(),
        fetchPortfolioRisk(),
      ]);
      setStatus(statusData);
      setConfig(cfgData);
      setRiskExposure(riskData);

      if (cfgData) {
        setEditInterval(cfgData.interval_minutes || 15);
        setEditThreshold(cfgData.criteria_threshold || 2);
        setEditMaxEscalations(cfgData.max_escalations_per_cycle || 3);
        setEditCapPct(cfgData.aggregate_risk_cap_pct || 6.0);
        setEditCircuitBreaker(cfgData.daily_circuit_breaker_pct || -5.0);
      }
    } catch (err) {
      console.error("WatchlistScanner load error:", err);
    }
  };

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, 10000); // 10s polling
    return () => clearInterval(interval);
  }, []);

  // Compute countdown timer
  useEffect(() => {
    if (!status?.last_scan_time || !config?.interval_minutes || !status.enabled) {
      setSecondsUntilNext(null);
      return;
    }

    const updateCountdown = () => {
      const lastMs = new Date(status.last_scan_time!).getTime();
      const intervalMs = (config.interval_minutes || 15) * 60 * 1000;
      const nextMs = lastMs + intervalMs;
      const nowMs = Date.now();
      const remainingSecs = Math.max(0, Math.floor((nextMs - nowMs) / 1000));
      setSecondsUntilNext(remainingSecs);
    };

    updateCountdown();
    const timer = setInterval(updateCountdown, 1000);
    return () => clearInterval(timer);
  }, [status?.last_scan_time, config?.interval_minutes, status?.enabled]);

  const handleToggleAuto = async () => {
    if (!status) return;
    setIsToggling(true);
    try {
      const nextState = !status.enabled;
      await toggleScanner(nextState);
      setStatus({ ...status, enabled: nextState });
      if (config) setConfig({ ...config, enabled: nextState });
    } catch (e: any) {
      alert("Failed to toggle scanner: " + e.message);
    } finally {
      setIsToggling(false);
    }
  };

  const handleTriggerInstantScan = async () => {
    setIsScanningManual(true);
    try {
      await triggerManualScan();
      await loadAll();
      if (onScanComplete) onScanComplete();
    } catch (e: any) {
      alert("Manual scan failed: " + e.message);
    } finally {
      setIsScanningManual(false);
    }
  };

  const handleAddTicker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTickerInput.trim() || !config) return;
    const formatted = newTickerInput.trim().toUpperCase();
    if (!config.watchlist.includes(formatted)) {
      const updatedList = [...config.watchlist, formatted];
      const updated = await updateScannerConfig({ watchlist: updatedList });
      setConfig(updated);
    }
    setNewTickerInput("");
  };

  const handleRemoveTicker = async (sym: string) => {
    if (!config) return;
    const updatedList = config.watchlist.filter((s) => s !== sym);
    const updated = await updateScannerConfig({ watchlist: updatedList });
    setConfig(updated);
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const updated = await updateScannerConfig({
        interval_minutes: Number(editInterval),
        criteria_threshold: Number(editThreshold),
        max_escalations_per_cycle: Number(editMaxEscalations),
        aggregate_risk_cap_pct: Number(editCapPct),
        daily_circuit_breaker_pct: Number(editCircuitBreaker),
      });
      setConfig(updated);
      setSaveSuccessMsg("Scanner parameters saved successfully!");
      setTimeout(() => {
        setSaveSuccessMsg(null);
        setShowConfigModal(false);
      }, 1200);
    } catch (err: any) {
      alert("Failed to save settings: " + err.message);
    }
  };

  const handleResetDefaults = async () => {
    if (!confirm("Reset watchlist to all 52 default crypto and stock assets?")) return;
    const fullPreset = Array.from(new Set([...DEFAULT_CRYPTO_PRESET, ...DEFAULT_STOCK_PRESET]));
    const updated = await updateScannerConfig({ watchlist: fullPreset });
    setConfig(updated);
  };

  // Filter watchlist items
  const currentWatchlist = config?.watchlist || [];
  const filteredWatchlist = useMemo(() => {
    return currentWatchlist.filter((sym) => {
      const isCrypto = sym.includes("/") || sym.endsWith("USD") || sym.endsWith("USDT");
      if (activeTab === "crypto" && !isCrypto) return false;
      if (activeTab === "stocks" && isCrypto) return false;
      if (searchQuery.trim() && !sym.toLowerCase().includes(searchQuery.trim().toLowerCase())) return false;
      return true;
    });
  }, [currentWatchlist, activeTab, searchQuery]);

  const lastCycle = status?.last_cycle;
  const isCircuitTripped = lastCycle?.circuit_breaker_tripped;
  const totalRiskPct = riskExposure?.total_risk_pct ?? 0;
  const capRiskPct = riskExposure?.aggregate_cap_pct ?? 6.0;
  const riskProgressRatio = Math.min(100, (totalRiskPct / capRiskPct) * 100);

  const formatCountdown = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s < 10 ? "0" : ""}${s}s`;
  };

  return (
    <div className="terminal-card p-6 border-purple-900/60 terminal-glow-purple space-y-6">
      {/* ── Top Header & Status Indicators ───────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 animate-pulse" />
            <h2 className="text-base font-bold text-purple-300 uppercase tracking-wider">
              Automated Multi-Asset Scanner (Auto-Discovery)
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-purple-950 border border-purple-800 text-purple-300">
              50+ Asset Universe
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Autonomous background discovery engine. Continuously screens 50+ crypto and equity tickers using OHLCV technical criteria (2-of-3 rule), dynamically sizes positions, and respects aggregate portfolio risk caps.
          </p>
        </div>

        {/* Action Buttons Cluster */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Config Modal Button */}
          <button
            onClick={() => setShowConfigModal(true)}
            className="bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 font-semibold px-3 py-1.5 rounded text-xs transition-all flex items-center gap-1.5"
            title="Configure Scanner & Risk Caps"
          >
            ⚙️ <span>Config</span>
          </button>

          {/* Auto-Scanner Toggle Switch */}
          <button
            onClick={handleToggleAuto}
            disabled={isToggling}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded text-xs font-bold transition-all border ${
              status?.enabled
                ? "bg-emerald-950/80 border-emerald-600 text-emerald-300 hover:bg-emerald-900/80"
                : "bg-slate-900 border-slate-700 text-slate-400 hover:bg-slate-800"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                status?.enabled ? "bg-emerald-400 animate-ping" : "bg-slate-500"
              }`}
            />
            <span>{status?.enabled ? "Auto-Scanner: ACTIVE" : "Auto-Scanner: PAUSED"}</span>
          </button>

          {/* Instant Scan Trigger */}
          <button
            onClick={handleTriggerInstantScan}
            disabled={isScanningManual || status?.is_scanning}
            className="bg-purple-600 hover:bg-purple-500 text-slate-950 font-bold px-4 py-1.5 rounded text-xs transition-all disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-purple-950/40"
          >
            {isScanningManual || status?.is_scanning ? (
              <>
                <span className="w-3 h-3 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                Scanning Universe...
              </>
            ) : (
              "⚡ Run Instant Scan"
            )}
          </button>
        </div>
      </div>

      {/* ── Status Metrics & Aggregate Risk Exposure ─────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Scanner Engine Status */}
        <div className="bg-slate-950/60 p-3.5 rounded border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400 uppercase">
            <span>Scanner Status</span>
            <span className="text-[10px] font-mono text-purple-400">
              {config?.interval_minutes || 15}m cycle
            </span>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isCircuitTripped
                  ? "bg-red-500 animate-pulse"
                  : status?.is_scanning
                  ? "bg-amber-400 animate-spin"
                  : status?.enabled
                  ? "bg-emerald-400 animate-pulse"
                  : "bg-slate-500"
              }`}
            />
            <span className="text-sm font-bold text-slate-100">
              {isCircuitTripped
                ? "CIRCUIT BREAKER"
                : status?.is_scanning
                ? "SCANNING NOW..."
                : status?.enabled
                ? "RUNNING (IDLE)"
                : "PAUSED"}
            </span>
          </div>
          <div className="text-[11px] text-slate-500 mt-2">
            {status?.last_scan_time ? (
              <span>Last: {new Date(status.last_scan_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
            ) : (
              <span>No scans executed yet</span>
            )}
          </div>
        </div>

        {/* Next Scan Countdown */}
        <div className="bg-slate-950/60 p-3.5 rounded border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400 uppercase">
            <span>Next Auto-Scan In</span>
            <span className="text-[10px] text-slate-500">APScheduler</span>
          </div>
          <div className="mt-2 text-lg font-bold font-mono text-purple-300">
            {status?.enabled && secondsUntilNext != null
              ? formatCountdown(secondsUntilNext)
              : status?.enabled
              ? "Calculating..."
              : "Disabled"}
          </div>
          <div className="text-[11px] text-slate-500 mt-2">
            Escalation limit: {config?.max_escalations_per_cycle || 3} trades/cycle
          </div>
        </div>

        {/* Aggregate Portfolio Risk Gauge */}
        <div className="bg-slate-950/60 p-3.5 rounded border border-slate-800 md:col-span-2 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 uppercase font-semibold">Portfolio Risk Exposure</span>
            <span className={`text-xs font-bold font-mono ${riskExposure?.is_over_cap ? "text-red-400" : "text-emerald-400"}`}>
              {totalRiskPct.toFixed(2)}% / {capRiskPct.toFixed(1)}% Cap
            </span>
          </div>

          {/* Progress Bar */}
          <div className="mt-2.5 w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
            <div
              className={`h-full transition-all duration-500 ${
                riskExposure?.is_over_cap
                  ? "bg-red-500"
                  : riskProgressRatio > 75
                  ? "bg-amber-400"
                  : "bg-emerald-500"
              }`}
              style={{ width: `${Math.max(3, riskProgressRatio)}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
            <span>
              ${riskExposure?.total_dollar_risk?.toFixed(2) || "0.00"} at risk across {riskExposure?.active_positions_count || 0} active positions
            </span>
            <span>
              Remaining budget: <strong className="text-slate-200 font-mono">${riskExposure?.remaining_risk_budget_dollars?.toFixed(2) || "0.00"}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* ── Circuit Breaker Warning Alert ────────────────────────── */}
      {isCircuitTripped && (
        <div className="p-3 rounded bg-red-950/80 border border-red-700 text-xs text-red-200 flex items-center justify-between gap-2 animate-pulse">
          <div className="flex items-center gap-2">
            <span className="text-base">🚨</span>
            <div>
              <strong>Circuit Breaker Triggered:</strong> {lastCycle?.circuit_breaker_msg || "Daily portfolio drawdown exceeded -5%. Background scanner halted to protect capital."}
            </div>
          </div>
          <button
            onClick={() => handleToggleAuto()}
            className="bg-red-900 hover:bg-red-800 text-slate-100 px-3 py-1 rounded text-[11px] font-bold border border-red-600 whitespace-nowrap"
          >
            Acknowledge & Resume
          </button>
        </div>
      )}

      {/* ── Watchlist Management & Universe Browser ─────────────── */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Watchlist Filter Tabs */}
          <div className="flex items-center gap-1 bg-slate-900/90 p-1 rounded border border-slate-800 text-xs">
            <button
              onClick={() => setActiveTab("all")}
              className={`px-3 py-1 rounded font-bold transition-all ${
                activeTab === "all" ? "bg-purple-600 text-slate-950" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All Assets ({currentWatchlist.length})
            </button>
            <button
              onClick={() => setActiveTab("crypto")}
              className={`px-3 py-1 rounded font-bold transition-all ${
                activeTab === "crypto" ? "bg-purple-600 text-slate-950" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Crypto ({currentWatchlist.filter(s => s.includes("/") || s.endsWith("USD") || s.endsWith("USDT")).length})
            </button>
            <button
              onClick={() => setActiveTab("stocks")}
              className={`px-3 py-1 rounded font-bold transition-all ${
                activeTab === "stocks" ? "bg-purple-600 text-slate-950" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Stocks & ETFs ({currentWatchlist.filter(s => !(s.includes("/") || s.endsWith("USD") || s.endsWith("USDT"))).length})
            </button>
          </div>

          {/* Search & Add Ticker Bar */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search ticker..."
              className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 uppercase w-32 sm:w-40"
            />

            <form onSubmit={handleAddTicker} className="flex items-center gap-1">
              <input
                type="text"
                value={newTickerInput}
                onChange={(e) => setNewTickerInput(e.target.value)}
                placeholder="+ Add symbol (e.g. INTC)"
                className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 uppercase w-36 sm:w-44"
              />
            </form>

            <button
              onClick={handleResetDefaults}
              className="text-[11px] text-slate-500 hover:text-purple-400 hover:underline px-1 py-1"
              title="Reset to 52 default assets"
            >
              Reset 52
            </button>
          </div>
        </div>

        {/* Watchlist Chips Universe */}
        <div className="max-h-48 overflow-y-auto p-3 bg-slate-950/60 rounded border border-slate-800/80 flex flex-wrap gap-1.5">
          {filteredWatchlist.length === 0 ? (
            <div className="text-xs text-slate-500 py-3 w-full text-center">
              No matching tickers found. Type a symbol above to add one.
            </div>
          ) : (
            filteredWatchlist.map((sym) => {
              const isCrypto = sym.includes("/") || sym.endsWith("USD") || sym.endsWith("USDT");
              const isPassedInLastCycle = lastCycle?.tickers?.some((t) => t.symbol === sym && t.passed);
              return (
                <div
                  key={sym}
                  className={`group inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold border transition-all ${
                    isPassedInLastCycle
                      ? "bg-purple-950/80 border-purple-500 text-purple-200 shadow-sm shadow-purple-900/50"
                      : isCrypto
                      ? "bg-slate-900/80 border-slate-700/80 text-amber-300/90 hover:border-slate-500"
                      : "bg-slate-900/80 border-slate-700/80 text-blue-300/90 hover:border-slate-500"
                  }`}
                >
                  <span>{sym}</span>
                  {isPassedInLastCycle && (
                    <span className="text-[9px] bg-purple-500 text-slate-950 px-1 rounded font-extrabold uppercase">
                      2/3 Pass
                    </span>
                  )}
                  <button
                    onClick={() => handleRemoveTicker(sym)}
                    className="text-slate-500 hover:text-red-400 text-xs ml-0.5"
                    title={`Remove ${sym}`}
                  >
                    &times;
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ── Last Scan Cycle Breakdown Table ──────────────────────── */}
      {lastCycle && lastCycle.scanned_count > 0 && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <span>Recent Scan Cycle Breakdown</span>
              <span className="text-purple-400 font-mono text-[11px]">
                ({lastCycle.scanned_count} scanned, {lastCycle.passed_count} passed pre-filter, {lastCycle.escalated_count} escalated)
              </span>
            </h3>

            <button
              onClick={() => setShowDetailsModal(true)}
              className="text-xs text-purple-400 hover:text-purple-300 hover:underline flex items-center gap-1"
            >
              View Full Pre-filter Audit ({lastCycle.tickers.length} tickers) &rarr;
            </button>
          </div>

          {/* Top Candidates / Escalated Tickers Highlights */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase">
                  <th className="py-2 px-3">Symbol</th>
                  <th className="py-2 px-3">Screening (2-of-3 Rule)</th>
                  <th className="py-2 px-3">Volume Spike</th>
                  <th className="py-2 px-3">RSI (14)</th>
                  <th className="py-2 px-3">Range / ATR</th>
                  <th className="py-2 px-3 text-right">Escalation Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {lastCycle.tickers
                  .filter((t) => t.passed || t.escalation_status)
                  .slice(0, 6)
                  .map((t) => (
                    <tr key={t.symbol} className="hover:bg-slate-900/40">
                      <td className="py-2.5 px-3 font-bold text-slate-100">{t.symbol}</td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            t.passed
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              : "bg-slate-800 text-slate-400 border border-slate-700"
                          }`}
                        >
                          {t.passed ? `PASSED (${t.passed_count}/3)` : `FAILED (${t.passed_count}/3)`}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 font-mono">
                        {t.metrics?.volume_ratio ? `${t.metrics.volume_ratio}x avg` : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 font-mono">
                        {t.metrics?.rsi != null ? `${t.metrics.rsi}` : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">
                        {t.metrics?.breakout_type ? t.metrics.breakout_type.replace("_", " ") : "In Range"}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span
                          className={`font-semibold text-[11px] ${
                            t.escalation_status?.startsWith("EXECUTED")
                              ? "text-emerald-400 font-bold"
                              : t.escalation_status?.startsWith("SKIPPED")
                              ? "text-slate-400"
                              : t.escalation_status?.startsWith("REJECTED")
                              ? "text-amber-400"
                              : "text-purple-400"
                          }`}
                        >
                          {t.escalation_status || (t.passed ? "Candidate" : "Filtered")}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Configuration Modal ──────────────────────────────────── */}
      {showConfigModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="terminal-card p-6 border-purple-800 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-purple-300 uppercase tracking-wider flex items-center gap-2">
                <span>⚙️</span> Scanner & Portfolio Risk Parameters
              </h3>
              <button
                onClick={() => setShowConfigModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveSettings} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Scan Interval (Minutes)
                </label>
                <input
                  type="number"
                  min="1"
                  max="120"
                  value={editInterval}
                  onChange={(e) => setEditInterval(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-slate-100 focus:outline-none focus:border-purple-500"
                />
                <span className="text-[10px] text-slate-500">How frequently the worker runs discovery across all 50+ tickers</span>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Pre-filter Criteria Threshold (N of 3)
                </label>
                <select
                  value={editThreshold}
                  onChange={(e) => setEditThreshold(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-slate-100 focus:outline-none focus:border-purple-500"
                >
                  <option value="1">1 of 3 (Aggressive Discovery)</option>
                  <option value="2">2 of 3 (Balanced - Recommended)</option>
                  <option value="3">3 of 3 (Strict High-Conviction)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Max Escalations Per Cycle (Cap)
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={editMaxEscalations}
                  onChange={(e) => setEditMaxEscalations(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-slate-100 focus:outline-none focus:border-purple-500"
                />
                <span className="text-[10px] text-slate-500">Maximum candidates sent to Gemini LLM per interval to control costs</span>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Aggregate Portfolio Risk Cap (% Equity)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="1"
                  max="20"
                  value={editCapPct}
                  onChange={(e) => setEditCapPct(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-slate-100 focus:outline-none focus:border-purple-500"
                />
                <span className="text-[10px] text-slate-500">Max combined dollar risk across all active open positions</span>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Daily Loss Circuit Breaker (% Equity)
                </label>
                <input
                  type="number"
                  step="0.5"
                  max="-1"
                  min="-25"
                  value={editCircuitBreaker}
                  onChange={(e) => setEditCircuitBreaker(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-slate-100 focus:outline-none focus:border-purple-500"
                />
                <span className="text-[10px] text-slate-500">Halts auto-scanner immediately if daily portfolio drawdown breaches this level</span>
              </div>

              {saveSuccessMsg && (
                <div className="p-2 rounded bg-emerald-950 border border-emerald-700 text-emerald-300 text-center font-bold">
                  {saveSuccessMsg}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowConfigModal(false)}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded bg-purple-600 hover:bg-purple-500 text-slate-950 font-bold"
                >
                  Save Configuration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Full Pre-filter Audit Modal ─────────────────────────── */}
      {showDetailsModal && lastCycle && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="terminal-card p-6 border-purple-800 max-w-4xl w-full max-h-[85vh] flex flex-col space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold text-purple-300 uppercase tracking-wider flex items-center gap-2">
                  <span>📊</span> Full Pre-Filter Technical Screening Audit
                </h3>
                <p className="text-[11px] text-slate-400">
                  Detailed breakdown of Volume, RSI, and Range Breakout scores across all scanned tickers.
                </p>
              </div>
              <button
                onClick={() => setShowDetailsModal(false)}
                className="text-slate-400 hover:text-slate-200 text-base font-bold"
              >
                &times;
              </button>
            </div>

            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-slate-900 text-slate-400 uppercase">
                  <tr className="border-b border-slate-800">
                    <th className="py-2.5 px-3">Symbol</th>
                    <th className="py-2.5 px-3">Verdict</th>
                    <th className="py-2.5 px-3">Criteria Satisfied</th>
                    <th className="py-2.5 px-3">Latest Close</th>
                    <th className="py-2.5 px-3">Volume Ratio</th>
                    <th className="py-2.5 px-3">RSI (14)</th>
                    <th className="py-2.5 px-3 text-right">Escalation Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {lastCycle.tickers.map((t) => (
                    <tr key={t.symbol} className="hover:bg-slate-900/40">
                      <td className="py-2 px-3 font-bold text-slate-100">{t.symbol}</td>
                      <td className="py-2 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            t.passed
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              : "bg-slate-800 text-slate-400 border border-slate-700"
                          }`}
                        >
                          {t.passed ? `PASS (${t.passed_count}/3)` : `FAIL (${t.passed_count}/3)`}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-slate-300">
                        {t.criteria_met?.length ? t.criteria_met.join(", ") : "None"}
                      </td>
                      <td className="py-2 px-3 font-mono text-slate-200">
                        ${t.metrics?.latest_close ? Number(t.metrics.latest_close).toFixed(2) : "—"}
                      </td>
                      <td className="py-2 px-3 font-mono text-slate-300">
                        {t.metrics?.volume_ratio ? `${t.metrics.volume_ratio}x` : "—"}
                      </td>
                      <td className="py-2 px-3 font-mono text-slate-300">
                        {t.metrics?.rsi != null ? `${t.metrics.rsi}` : "—"}
                      </td>
                      <td className="py-2 px-3 text-right">
                        <span className="text-[11px] font-medium text-purple-300">
                          {t.escalation_status || (t.already_active ? "Already Active" : t.passed ? "Candidate" : "Filtered Out")}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowDetailsModal(false)}
                className="px-4 py-1.5 rounded bg-purple-600 hover:bg-purple-500 text-slate-950 font-bold text-xs"
              >
                Close Audit View
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
