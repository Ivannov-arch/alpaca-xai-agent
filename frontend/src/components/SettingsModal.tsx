"use client";

import { useState, useEffect } from "react";
import { getCustomAlpacaKeys, setCustomAlpacaKeys } from "@/lib/api";

export default function SettingsModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  useEffect(() => {
    const { key, secret } = getCustomAlpacaKeys();
    if (key) setApiKey(key);
    if (secret) setSecretKey(secret);
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setCustomAlpacaKeys(apiKey.trim(), secretKey.trim());
    setSavedMsg("API keys saved safely in local storage!");
    setTimeout(() => {
      setSavedMsg(null);
      setIsOpen(false);
      window.location.reload(); // Refresh to apply custom keys
    }, 1200);
  };

  const handleClear = () => {
    setCustomAlpacaKeys("", "");
    setApiKey("");
    setSecretKey("");
    setSavedMsg("Cleared. Defaulting to system environment keys.");
    setTimeout(() => {
      setSavedMsg(null);
      setIsOpen(false);
      window.location.reload();
    }, 1200);
  };

  const hasCustomKeys = Boolean(apiKey.trim() || secretKey.trim());

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-2.5 py-1 rounded text-xs transition-colors"
      >
        <span>🔑</span>
        <span>{hasCustomKeys ? "Custom Alpaca Keys (Active)" : "API Settings"}</span>
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="terminal-card w-full max-w-md p-6 space-y-4 border-emerald-900/60 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <span>🔑</span>
                <span>Alpaca API & Account Credentials</span>
              </h3>
              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold"
              >
                &times;
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Safely connect your own **Alpaca Paper Trading Account**. Keys are saved locally in your browser and transmitted securely over encrypted headers.
            </p>

            <form onSubmit={handleSave} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 mb-1 font-medium">
                  Alpaca API Key ID (APCA-API-KEY-ID)
                </label>
                <input
                  type="text"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="PK..."
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">
                  Alpaca Secret Key (APCA-API-SECRET-KEY)
                </label>
                <input
                  type="password"
                  value={secretKey}
                  onChange={(e) => setSecretKey(e.target.value)}
                  placeholder="Secret key..."
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>

              {savedMsg && (
                <div className="p-2 rounded bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs">
                  {savedMsg}
                </div>
              )}

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={handleClear}
                  className="text-red-400 hover:text-red-300 text-xs underline"
                >
                  Use System Defaults
                </button>
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => setIsOpen(false)}
                    className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold text-xs"
                  >
                    Save Credentials
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
