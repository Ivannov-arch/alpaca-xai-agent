"use client";

import { useState, useEffect } from "react";
import {
  getRiskSettings,
  setRiskSettings,
  HARD_CEILING_PCT,
  RiskSettings,
} from "@/lib/api";

interface RiskControlProps {
  /** Called whenever the user saves a new setting */
  onChange?: (settings: RiskSettings) => void;
  /** Compact mode: hides description text, suitable for embedding in cards */
  compact?: boolean;
}

export default function RiskControl({ onChange, compact = false }: RiskControlProps) {
  const [settings, setSettings] = useState<RiskSettings>({ mode: "percent", value: 1.0 });
  const [inputValue, setInputValue] = useState<string>("1.0");
  const [inputError, setInputError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const loaded = getRiskSettings();
    setSettings(loaded);
    setInputValue(String(loaded.value ?? (loaded.mode === "percent" ? 1.0 : 500.0)));
  }, []);

  const handleModeToggle = (mode: "percent" | "dollar") => {
    const defaultVal = mode === "percent" ? 1.0 : 500.0;
    const next: RiskSettings = {
      mode,
      value: defaultVal,
    };
    setSettings(next);
    setInputValue(String(defaultVal));
    setInputError(null);
    persist(next);
  };

  const handleValueChange = (raw: string) => {
    setInputValue(raw);

    if (raw.trim() === "") {
      setInputError("Risk value is required");
      return;
    }

    const parsed = parseFloat(raw);
    if (isNaN(parsed) || parsed <= 0) {
      setInputError("Must be greater than 0");
      return;
    }

    setInputError(null);
    const clamped =
      settings.mode === "percent" ? Math.min(parsed, HARD_CEILING_PCT) : parsed;
    const next: RiskSettings = { ...settings, value: clamped };
    setSettings(next);
    persist(next);
  };

  const handleBlur = () => {
    if (inputValue.trim() === "" || inputError) {
      // Revert to a safe default if left blank on blur
      const fallback = settings.mode === "percent" ? 1.0 : 500.0;
      setInputValue(String(fallback));
      setInputError(null);
      const next: RiskSettings = { ...settings, value: fallback };
      setSettings(next);
      persist(next);
    }
  };

  const persist = (s: RiskSettings) => {
    setRiskSettings(s);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
    onChange?.(s);
  };

  const isCapped =
    settings.mode === "percent" && parseFloat(inputValue || "0") >= HARD_CEILING_PCT;

  return (
    <div className={compact ? "space-y-1.5" : "space-y-3"}>
      {!compact && (
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Max Risk Per Trade
          </span>
          {saved && !inputError && (
            <span className="text-[10px] text-emerald-400 animate-pulse">✓ Saved</span>
          )}
        </div>
      )}

      <div className="flex items-center gap-2">
        {/* Mode toggle pills */}
        <div className="flex rounded overflow-hidden border border-slate-700 text-[11px] font-bold shrink-0">
          <button
            type="button"
            onClick={() => handleModeToggle("percent")}
            className={`px-2.5 py-1 transition-colors ${
              settings.mode === "percent"
                ? "bg-emerald-600 text-slate-950"
                : "bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            %
          </button>
          <button
            type="button"
            onClick={() => handleModeToggle("dollar")}
            className={`px-2.5 py-1 transition-colors ${
              settings.mode === "dollar"
                ? "bg-emerald-600 text-slate-950"
                : "bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            $
          </button>
        </div>

        {/* Value input */}
        <div className="relative flex-1">
          {settings.mode === "dollar" && (
            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs pointer-events-none">
              $
            </span>
          )}
          <input
            type="number"
            value={inputValue}
            placeholder={settings.mode === "percent" ? "1.0" : "500"}
            step={settings.mode === "percent" ? 0.1 : 10}
            min={settings.mode === "percent" ? 0.1 : 10}
            max={settings.mode === "percent" ? HARD_CEILING_PCT : undefined}
            onChange={(e) => handleValueChange(e.target.value)}
            onBlur={handleBlur}
            className={`w-full bg-slate-900 border rounded px-2 py-1 text-sm text-slate-100 focus:outline-none transition-colors ${
              inputError
                ? "border-red-500 focus:border-red-400"
                : isCapped
                ? "border-amber-600 focus:border-amber-500"
                : "border-slate-700 focus:border-emerald-500"
            } ${settings.mode === "dollar" ? "pl-5" : ""}`}
          />
          {settings.mode === "percent" && (
            <span className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs pointer-events-none">
              %
            </span>
          )}
        </div>

        {/* Compact saved indicator */}
        {compact && saved && !inputError && (
          <span className="text-[10px] text-emerald-400 shrink-0">✓</span>
        )}
      </div>

      {/* Error message */}
      {inputError ? (
        <div className="text-[10px] text-red-400 flex items-center gap-1 font-medium">
          <span>⚠</span>
          <span>{inputError}</span>
        </div>
      ) : isCapped ? (
        <div className="flex items-center gap-1 text-[10px] text-amber-400">
          <span>⚠</span>
          <span>Hard ceiling reached — {HARD_CEILING_PCT}% max enforced</span>
        </div>
      ) : (
        <div className="text-[10px] text-slate-500">
          {settings.mode === "percent"
            ? `Hard ceiling: ${HARD_CEILING_PCT}% per trade`
            : "Hard ceiling: 5% of equity per trade (server-enforced)"}
        </div>
      )}
    </div>
  );
}
