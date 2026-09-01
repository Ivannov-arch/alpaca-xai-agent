"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  getSavedAccounts,
  getActiveAccount,
  setActiveAccount,
  saveAccount,
  removeAccount,
  SavedAccount,
  setCustomAlpacaKeys,
} from "@/lib/api";

export default function SettingsModal() {
  const [mounted, setMounted] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [savedAccounts, setSavedAccounts] = useState<SavedAccount[]>([]);
  const [activeAccount, setActiveAccState] = useState<SavedAccount | null>(null);

  // Form states
  const [accountName, setAccountName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [strategyProfile, setStrategyProfile] = useState<"SCALPING" | "SWING" | "CONSERVATIVE">("SWING");
  const [saveAsAccount, setSaveAsAccount] = useState(true);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    reloadAccounts();
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim() || !secretKey.trim()) {
      setSavedMsg("Please provide both API Key and Secret Key.");
      return;
    }

    if (saveAsAccount) {
      const name = accountName.trim() || `Account (${strategyProfile})`;
      const acc: SavedAccount = {
        id: activeAccount?.id || `acc_${Date.now()}`,
        name,
        apiKey: apiKey.trim(),
        secretKey: secretKey.trim(),
        strategyProfile,
      };
      saveAccount(acc);
      setSavedMsg(`Account "${name}" saved & activated!`);
    } else {
      setCustomAlpacaKeys(apiKey.trim(), secretKey.trim());
      setSavedMsg("Temporary keys active!");
    }

    setTimeout(() => {
      setSavedMsg(null);
      setIsOpen(false);
      window.location.reload();
    }, 1000);
  };

  const handleSwitchAccount = (acc: SavedAccount) => {
    setActiveAccount(acc);
    reloadAccounts();
    setSavedMsg(`Switched to "${acc.name}" (${acc.strategyProfile})`);
    setTimeout(() => {
      setSavedMsg(null);
      setIsOpen(false);
      window.location.reload();
    }, 800);
  };

  const handleDeleteAccount = (id: string, name: string) => {
    if (confirm(`Delete recorded account "${name}"?`)) {
      removeAccount(id);
      reloadAccounts();
      setSavedMsg(`Deleted "${name}"`);
      setTimeout(() => setSavedMsg(null), 1500);
    }
  };

  const handleClear = () => {
    setActiveAccount(null);
    setApiKey("");
    setSecretKey("");
    setAccountName("");
    setSavedMsg("Defaulting to system environment keys.");
    setTimeout(() => {
      setSavedMsg(null);
      setIsOpen(false);
      window.location.reload();
    }, 1000);
  };

  return (
    <>
      <button
        onClick={() => {
          reloadAccounts();
          setIsOpen(true);
        }}
        className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-2.5 py-1 rounded text-xs transition-colors"
      >
        <span>🔑</span>
        <span>
          {activeAccount
            ? `${activeAccount.name} (${activeAccount.strategyProfile})`
            : "API & Strategy Settings"}
        </span>
      </button>

      {isOpen && mounted && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/85 backdrop-blur-md p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-lg p-6 space-y-4 bg-[#0f172a] border border-emerald-500/40 rounded-xl shadow-2xl max-h-[90vh] overflow-y-auto text-slate-100">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <span>🔑</span>
                <span>Recorded Accounts & Strategy Profiles</span>
              </h3>
              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold"
              >
                &times;
              </button>
            </div>

            {/* Saved Accounts Switcher List */}
            {savedAccounts.length > 0 && (
              <div className="space-y-2 border-b border-slate-800/80 pb-4">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Switch Active Recorded Account:
                </span>
                <div className="space-y-1.5">
                  {savedAccounts.map((acc) => {
                    const isActive = activeAccount?.id === acc.id;
                    return (
                      <div
                        key={acc.id}
                        className={`flex items-center justify-between p-2.5 rounded border text-xs transition-all ${
                          isActive
                            ? "bg-emerald-950/60 border-emerald-700 text-emerald-300"
                            : "bg-slate-900/80 border-slate-800 text-slate-300 hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-bold">{acc.name}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 border border-slate-700 uppercase">
                            {acc.strategyProfile}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          {!isActive && (
                            <button
                              onClick={() => handleSwitchAccount(acc)}
                              className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-2.5 py-0.5 rounded text-[10px]"
                            >
                              Activate
                            </button>
                          )}
                          <button
                            onClick={() => handleDeleteAccount(acc.id, acc.name)}
                            className="text-red-400 hover:text-red-300 text-xs px-1"
                            title="Delete Account"
                          >
                            &times;
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Add / Edit Account Form */}
            <form onSubmit={handleSave} className="space-y-3 text-xs">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                {activeAccount ? "Edit Current Account Keys" : "Connect New Alpaca Account"}
              </span>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Account Label / Name</label>
                <input
                  type="text"
                  value={accountName}
                  onChange={(e) => setAccountName(e.target.value)}
                  placeholder="e.g. Scalping Account 1, Swing Paper Account"
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Strategy Archetype Selection */}
              <div>
                <label className="block text-slate-300 mb-1 font-medium">
                  Trading Strategy Profile (LLM Persona)
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "SCALPING", label: "⚡ Scalping", desc: "Aggressive (0.5-1% SL)" },
                    { id: "SWING", label: "📈 Swing", desc: "Balanced (2-4% SL)" },
                    { id: "CONSERVATIVE", label: "🛡️ Long-Term", desc: "Conservative (5-10% SL)" },
                  ].map((st) => (
                    <button
                      type="button"
                      key={st.id}
                      onClick={() => setStrategyProfile(st.id as any)}
                      className={`p-2 rounded border text-left flex flex-col justify-between transition-all ${
                        strategyProfile === st.id
                          ? "bg-emerald-950 border-emerald-500 text-emerald-300"
                          : "bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <span className="font-bold text-[11px]">{st.label}</span>
                      <span className="text-[9px] text-slate-500 mt-0.5">{st.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">
                  Alpaca API Key ID (APCA-API-KEY-ID)
                </label>
                <input
                  type="text"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="PK..."
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
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
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="saveAcc"
                  checked={saveAsAccount}
                  onChange={(e) => setSaveAsAccount(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-emerald-500 focus:ring-0"
                />
                <label htmlFor="saveAcc" className="text-slate-300 text-xs">
                  Save as Recorded Account profile for 1-click switching
                </label>
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
                    Save & Activate Account
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
