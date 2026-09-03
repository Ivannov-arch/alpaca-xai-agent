"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  fetchTradeDetail,
  triggerAudit,
  Hypothesis,
  AuditLog,
} from "@/lib/api";
import TradingChart from "@/components/TradingChart";

export default function HypothesisDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const hypothesisId = resolvedParams.id;

  const [trade, setTrade] = useState<{
    hypothesis: Hypothesis;
    audit_logs: AuditLog[];
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [auditing, setAuditing] = useState(false);
  const [auditMsg, setAuditMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const data = await fetchTradeDetail(hypothesisId);
      setTrade(data);
    } catch (e: any) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [hypothesisId]);

  const handleManualAudit = async () => {
    setAuditing(true);
    setAuditMsg(null);
    try {
      const res = await triggerAudit(hypothesisId);
      setAuditMsg(`Audit complete! Verdict: ${res.audit_verdict}`);
      await loadData();
    } catch (e: any) {
      setAuditMsg(`Audit failed: ${e.message}`);
    } finally {
      setAuditing(false);
    }
  };

  if (loading) {
    return (
      <div className="py-20 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
        <span className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        Loading hypothesis details...
      </div>
    );
  }

  if (!trade) {
    return (
      <div className="py-20 text-center text-red-400 text-xs">
        Hypothesis not found. <Link href="/hypotheses" className="underline">Back to list</Link>
      </div>
    );
  }

  const { hypothesis, audit_logs } = trade;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center space-x-3">
            <Link
              href="/hypotheses"
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              &larr; Back to Hypotheses
            </Link>
            <span className="text-slate-600">/</span>
            <span className="text-xs font-bold text-emerald-400">{hypothesis.symbol}</span>
          </div>
          <h1 className="text-xl font-bold text-slate-100 mt-1 flex items-center gap-3">
            <span>Trade Hypothesis Spec</span>
            <span
              className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                hypothesis.status === "ACTIVE"
                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800 animate-pulse"
                  : hypothesis.status === "PENDING"
                  ? "bg-amber-950 text-amber-400 border border-amber-800"
                  : hypothesis.status === "CLOSED"
                  ? "bg-slate-800 text-slate-300 border border-slate-700"
                  : "bg-red-950 text-red-400 border border-red-800"
              }`}
            >
              {hypothesis.status}
            </span>
          </h1>
        </div>

        {hypothesis.status === "ACTIVE" && (
          <button
            onClick={handleManualAudit}
            disabled={auditing}
            className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-4 py-2 rounded text-xs transition-all disabled:opacity-50 flex items-center gap-2 self-start sm:self-auto"
          >
            {auditing ? (
              <>
                <span className="w-3 h-3 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                Auditing...
              </>
            ) : (
              "⚡ Run Manual Audit (Phase 3)"
            )}
          </button>
        )}
      </div>

      {auditMsg && (
        <div className="p-3 rounded bg-slate-900 border border-emerald-800 text-xs text-emerald-300">
          {auditMsg}
        </div>
      )}

      {/* Main Spec Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Thesis & Parameters */}
        <div className="lg:col-span-2 space-y-6">
          {/* Interactive Candlestick & Risk Target Chart */}
          <div className="terminal-card p-6">
            <TradingChart
              symbol={hypothesis.symbol}
              targetPrice={Number(hypothesis.target_price)}
              stopLossPrice={Number(hypothesis.stop_loss_price)}
              entryPrice={hypothesis.entry_price ? Number(hypothesis.entry_price) : undefined}
            />
          </div>

          {/* Thesis Text Card */}
          <div className="terminal-card p-6">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              Pre-Trade Thesis & Reasoning
            </h3>
            <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line bg-slate-950/60 p-4 rounded border border-slate-800/80">
              {hypothesis.thesis_text}
            </p>
          </div>

          {/* Invalidation Triggers Card */}
          <div className="terminal-card p-6">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
              Invalidation Triggers (Breach = Auto-Close)
            </h3>
            {hypothesis.invalidation_triggers?.length === 0 ? (
              <p className="text-xs text-slate-500">No explicit invalidation triggers recorded.</p>
            ) : (
              <ul className="space-y-2">
                {hypothesis.invalidation_triggers?.map((trig, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 bg-slate-950/40 p-3 rounded border border-slate-800 text-xs"
                  >
                    <span className="text-red-400 font-bold"># {idx + 1}</span>
                    <div>
                      <span className="text-slate-200 font-semibold">{trig.condition}: </span>
                      <span className="text-slate-400">{trig.threshold}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Right Column: Key Parameters Card */}
        <div className="space-y-6">
          <div className="terminal-card p-6 space-y-4 text-xs">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2">
              Trade Parameters
            </h3>

            <div className="flex justify-between py-1 border-b border-slate-800/50">
              <span className="text-slate-400">Hypothesis ID</span>
              <span className="font-mono text-slate-300 text-[10px]">{hypothesis.id.slice(0, 8)}...</span>
            </div>

            <div className="flex justify-between py-1 border-b border-slate-800/50">
              <span className="text-slate-400">Trigger Source</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                hypothesis.risk_metadata?.triggered_by === "scanner"
                  ? "bg-purple-950 text-purple-300 border border-purple-800"
                  : "bg-slate-900 text-slate-300 border border-slate-700"
              }`}>
                {hypothesis.risk_metadata?.triggered_by === "scanner" ? "⚡ Auto-Scanner" : "👤 Manual"}
              </span>
            </div>

            <div className="flex justify-between py-1 border-b border-slate-800/50">
              <span className="text-slate-400">Symbol / Side</span>
              <span className="font-bold text-slate-100 uppercase">{hypothesis.symbol} ({hypothesis.side})</span>
            </div>

            <div className="flex justify-between py-1 border-b border-slate-800/50">
              <span className="text-slate-400">Order Quantity</span>
              <span className="text-slate-200 font-medium">{hypothesis.qty} shares</span>
            </div>

            <div className="flex justify-between py-1 border-b border-slate-800/50">
              <span className="text-slate-400">Entry Price</span>
              <span className="text-slate-200 font-medium">${hypothesis.entry_price ? Number(hypothesis.entry_price).toFixed(2) : "Market"}</span>
            </div>

            <div className="flex justify-between py-1 border-b border-slate-800/50">
              <span className="text-slate-400">Target Price</span>
              <span className="text-emerald-400 font-bold">${Number(hypothesis.target_price).toFixed(2)}</span>
            </div>

            <div className="flex justify-between py-1 border-b border-slate-800/50">
              <span className="text-slate-400">Stop Loss Price</span>
              <span className="text-red-400 font-bold">${Number(hypothesis.stop_loss_price).toFixed(2)}</span>
            </div>

            <div className="flex justify-between py-1">
              <span className="text-slate-400">Alpaca Order ID</span>
              <span className="font-mono text-slate-400 text-[10px]">
                {hypothesis.alpaca_order_id ? hypothesis.alpaca_order_id.slice(0, 8) + "..." : "Pending"}
              </span>
            </div>

            {/* ── Risk Breakdown ───────────────────────────── */}
            <div className="mt-3 pt-3 border-t border-slate-800 space-y-2">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Risk Breakdown
              </h4>
              {hypothesis.risk_metadata && Object.keys(hypothesis.risk_metadata).length > 0 ? (
                <>
                  <div className="flex justify-between py-0.5">
                    <span className="text-slate-500">Dollar at Risk</span>
                    <span className="text-amber-400 font-bold">
                      ${Number(hypothesis.risk_metadata.dollar_risk ?? 0).toFixed(2)}
                      {hypothesis.risk_metadata.capped && (
                        <span className="ml-1 text-[9px] text-amber-500 border border-amber-700 rounded px-1 py-0.5">
                          CAP
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between py-0.5">
                    <span className="text-slate-500">% of Equity</span>
                    <span className="text-slate-300 font-medium">
                      {Number(hypothesis.risk_metadata.pct_of_equity ?? 0).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between py-0.5">
                    <span className="text-slate-500">Position Value</span>
                    <span className="text-slate-300">
                      ${Number(hypothesis.risk_metadata.position_value ?? 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between py-0.5">
                    <span className="text-slate-500">Risk Mode</span>
                    <span className="text-slate-400 capitalize">
                      {hypothesis.risk_metadata.risk_mode ?? "percent"}{" "}
                      ({hypothesis.risk_metadata.risk_value ?? 1}
                      {hypothesis.risk_metadata.risk_mode === "dollar" ? " $" : "%"})
                    </span>
                  </div>
                  {hypothesis.risk_metadata.equity_at_trade != null && (
                    <div className="flex justify-between py-0.5">
                      <span className="text-slate-500">Equity at Trade</span>
                      <span className="text-slate-500">
                        ${Number(hypothesis.risk_metadata.equity_at_trade).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-[10px] text-slate-600 italic">
                  Legacy trade — fixed-size sizing (pre-risk engine).
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Audit Log Timeline */}
      <div className="terminal-card p-6">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-6 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          Audit Log Timeline ({audit_logs.length} Cycles)
        </h3>

        {audit_logs.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded">
            No audit logs recorded yet. The background worker runs audits every 15 minutes.
          </div>
        ) : (
          <div className="relative border-l-2 border-slate-800 pl-6 space-y-6 ml-2">
            {audit_logs.map((log) => (
              <div key={log.id} className="relative">
                {/* Timeline Dot */}
                <div
                  className={`absolute -left-[31px] top-1.5 w-3 h-3 rounded-full border-2 ${
                    log.llm_verdict === "CLOSE"
                      ? "bg-red-500 border-slate-900"
                      : "bg-emerald-500 border-slate-900"
                  }`}
                />

                <div className="bg-slate-900/80 p-4 rounded-lg border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-mono">
                      {new Date(log.created_at).toLocaleString()}
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded text-[11px] font-bold ${
                        log.llm_verdict === "CLOSE"
                          ? "bg-red-950 text-red-400 border border-red-800"
                          : "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      }`}
                    >
                      VERDICT: {log.llm_verdict}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 font-mono bg-slate-950/60 p-3 rounded border border-slate-800/80">
                    {log.reasoning_summary}
                  </p>

                  {log.market_snapshot && (
                    <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1">
                      <span>Price: ${log.market_snapshot.current_price?.toFixed(2) || "N/A"}</span>
                      <span>
                        PnL: ${log.market_snapshot.unrealised_pnl?.toFixed(2) || "0.00"} ({log.market_snapshot.unrealised_pnl_pct?.toFixed(2) || "0.00"}%)
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
