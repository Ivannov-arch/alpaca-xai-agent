"use client";

import { useState } from "react";
import { scanWatchlist, getActiveAccount } from "@/lib/api";

const DEFAULT_WATCHLIST = [
  "BTC/USD",
  "ETH/USD",
  "SOL/USD",
  "AAPL",
  "NVDA",
  "TSLA",
];

export default function WatchlistScanner({ onScanComplete }: { onScanComplete?: () => void }) {
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(DEFAULT_WATCHLIST);
  const [newSymbol, setNewSymbol] = useState("");
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<any | null>(null);

  const toggleSymbol = (sym: string) => {
    if (selectedSymbols.includes(sym)) {
      setSelectedSymbols(selectedSymbols.filter((s) => s !== sym));
    } else {
      setSelectedSymbols([...selectedSymbols, sym]);
    }
  };

  const handleAddSymbol = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSymbol.trim()) return;
    const formatted = newSymbol.trim().toUpperCase();
    if (!selectedSymbols.includes(formatted)) {
      setSelectedSymbols([...selectedSymbols, formatted]);
    }
    setNewSymbol("");
  };

  const handleRunScan = async () => {
    if (selectedSymbols.length === 0) return;
    setIsScanning(true);
    setScanResult(null);

    const activeAcc = getActiveAccount();
    const strategy = activeAcc?.strategyProfile || "SWING";

    try {
      const res = await scanWatchlist(selectedSymbols, strategy);
      setScanResult(res);
      if (onScanComplete) onScanComplete();
    } catch (e: any) {
      setScanResult({ error: e.message || "Failed to scan watchlist" });
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <div className="terminal-card p-6 border-purple-900/50 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <h2 className="text-sm font-semibold text-purple-400 uppercase tracking-wider flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
            Selected Investment Options (Watchlist & Auto-Scanner)
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Select a list of your favorite crypto assets/stocks for analysis and automated execution by the AI ​​Agent
          </p>
        </div>

        <button
          onClick={handleRunScan}
          disabled={isScanning || selectedSymbols.length === 0}
          className="bg-purple-600 hover:bg-purple-500 text-slate-950 font-bold px-4 py-2 rounded text-xs transition-all disabled:opacity-50 flex items-center gap-2 self-start sm:self-auto"
        >
          {isScanning ? (
            <>
              <span className="w-3 h-3 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
              Scanning Watchlist ({selectedSymbols.length} assets)...
            </>
          ) : (
            `⚡ Scan & Auto-Trade (${selectedSymbols.length} Assets)`
          )}
        </button>
      </div>

      {/* Symbol Chips */}
      <div className="flex flex-wrap items-center gap-2">
        {selectedSymbols.map((sym) => (
          <button
            key={sym}
            onClick={() => toggleSymbol(sym)}
            className="flex items-center gap-1.5 px-3 py-1 rounded border text-xs font-bold transition-all bg-purple-950/60 border-purple-800 text-purple-300 hover:border-purple-600"
          >
            <span>{sym}</span>
            <span className="text-purple-400 text-[10px]">&times;</span>
          </button>
        ))}

        {/* Add custom symbol input */}
        <form onSubmit={handleAddSymbol} className="inline-flex items-center gap-1">
          <input
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            placeholder="+ Add ticker (e.g. DOGE/USD)"
            className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500 uppercase"
          />
        </form>
      </div>

      {/* Scan Results Output */}
      {scanResult && (
        <div className="mt-3 p-3 rounded bg-slate-950 border border-purple-800/80 text-xs space-y-2">
          {scanResult.error ? (
            <div className="text-red-400 font-medium">Scan failed: {scanResult.error}</div>
          ) : (
            <div>
              <div className="text-purple-300 font-bold mb-1">
                Scan Completed! Scanned {scanResult.scanned_count} assets:
              </div>
              <div className="space-y-1">
                {scanResult.results?.map((res: any) => (
                  <div
                    key={res.symbol}
                    className="flex items-center justify-between py-0.5 text-[11px] border-b border-slate-900"
                  >
                    <span className="font-bold text-slate-200">{res.symbol}</span>
                    <span
                      className={`font-semibold ${
                        res.status === "ACTIVE" ? "text-emerald-400" : "text-amber-400"
                      }`}
                    >
                      STATUS: {res.status} {res.alpaca_order_id ? `(Order: ${res.alpaca_order_id.slice(0, 8)}...)` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
