const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const DEV_ACCOUNT_ID = "66e809f1-2f0e-4a3a-8ea3-bdb7c2d5a849";

export interface RiskSettings {
  mode: "percent" | "dollar";
  value: number; // percent: 1.0 = 1%; dollar: 500.0 = $500
}

export interface Hypothesis {
  id: string;
  account_id: string;
  symbol: string;
  side: "buy" | "sell";
  order_type: string;
  qty: number;
  entry_price?: number;
  target_price: number;
  stop_loss_price: number;
  thesis_text: string;
  invalidation_triggers: { condition: string; threshold: string }[];
  status: "PENDING" | "ACTIVE" | "CLOSED" | "ABORTED";
  alpaca_order_id?: string;
  risk_metadata?: {
    triggered_by?: "manual" | "scanner" | string;
    risk_mode?: string;
    risk_value?: number;
    dollar_risk?: number;
    pct_of_equity?: number;
    position_value?: number;
    capped?: boolean;
    equity_at_trade?: number;
    hard_ceiling_pct?: number;
  };
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  hypothesis_id: string;
  llm_verdict: "HOLD" | "CLOSE";
  reasoning_summary: string;
  market_snapshot: {
    current_price?: number;
    unrealised_pnl?: number;
    unrealised_pnl_pct?: number;
  };
  created_at: string;
}

export interface PostMortem {
  id: string;
  hypothesis_id: string;
  pnl_percentage: number;
  pnl_absolute?: number;
  outcome: "WIN" | "LOSS" | "BREAKEVEN";
  lesson_learned: string;
  created_at: string;
}

export interface PortfolioData {
  account: {
    portfolio_value?: string;
    cash?: string;
    buying_power?: string;
    equity?: string;
  };
  positions: Array<{
    symbol: string;
    qty: string;
    current_price: string;
    avg_entry_price: string;
    unrealized_pl: string;
    unrealized_plpc: string;
  }>;
}

export interface SavedAccount {
  id: string;
  name: string;
  apiKey: string;
  secretKey: string;
  strategyProfile: "SCALPING" | "SWING" | "CONSERVATIVE";
  riskSettings?: RiskSettings;
}

export function getSavedAccounts(): SavedAccount[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem("xai_saved_accounts");
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function getActiveAccount(): SavedAccount | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem("xai_active_account");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setActiveAccount(acc: SavedAccount | null) {
  if (typeof window === "undefined") return;
  if (acc) {
    localStorage.setItem("xai_active_account", JSON.stringify(acc));
    setCustomAlpacaKeys(acc.apiKey, acc.secretKey);
  } else {
    localStorage.removeItem("xai_active_account");
    setCustomAlpacaKeys("", "");
  }
}

export function saveAccount(acc: SavedAccount) {
  if (typeof window === "undefined") return;
  const list = getSavedAccounts().filter((a) => a.id !== acc.id);
  list.push(acc);
  localStorage.setItem("xai_saved_accounts", JSON.stringify(list));
  setActiveAccount(acc);
}

export function removeAccount(id: string) {
  if (typeof window === "undefined") return;
  const list = getSavedAccounts().filter((a) => a.id !== id);
  localStorage.setItem("xai_saved_accounts", JSON.stringify(list));
  const active = getActiveAccount();
  if (active && active.id === id) {
    setActiveAccount(null);
  }
}

export function getCustomAlpacaKeys(): { key?: string; secret?: string } {
  if (typeof window === "undefined") return {};
  const active = getActiveAccount();
  if (active && active.apiKey?.trim() && active.secretKey?.trim()) {
    return { key: active.apiKey.trim(), secret: active.secretKey.trim() };
  }

  const rawKey = localStorage.getItem("xai_alpaca_key");
  const rawSecret = localStorage.getItem("xai_alpaca_secret");

  const key = rawKey && rawKey.trim() && rawKey !== "undefined" && rawKey !== "null" ? rawKey.trim() : undefined;
  const secret = rawSecret && rawSecret.trim() && rawSecret !== "undefined" && rawSecret !== "null" ? rawSecret.trim() : undefined;

  return { key, secret };
}

export function setCustomAlpacaKeys(key: string, secret: string) {
  if (typeof window === "undefined") return;
  if (key && key.trim()) localStorage.setItem("xai_alpaca_key", key.trim());
  else localStorage.removeItem("xai_alpaca_key");

  if (secret && secret.trim()) localStorage.setItem("xai_alpaca_secret", secret.trim());
  else localStorage.removeItem("xai_alpaca_secret");
}

export function getAccountId(): string {
  if (typeof window === "undefined") return DEV_ACCOUNT_ID;
  const active = getActiveAccount();
  return active?.id || DEV_ACCOUNT_ID;
}

// ── Risk Settings ─────────────────────────────────────────────────────

export const DEFAULT_RISK_SETTINGS: RiskSettings = { mode: "percent", value: 1.0 };
export const HARD_CEILING_PCT = 5.0; // mirrors agent/risk.py HARD_CEILING_PCT

export function getRiskSettings(): RiskSettings {
  if (typeof window === "undefined") return DEFAULT_RISK_SETTINGS;
  // Per-account risk settings take priority
  const active = getActiveAccount();
  if (active?.riskSettings) return active.riskSettings;
  // Fall back to global localStorage key
  try {
    const raw = localStorage.getItem("xai_risk_settings");
    return raw ? JSON.parse(raw) : DEFAULT_RISK_SETTINGS;
  } catch {
    return DEFAULT_RISK_SETTINGS;
  }
}

export function setRiskSettings(settings: RiskSettings): void {
  if (typeof window === "undefined") return;
  // Clamp value to hard ceiling in percent mode
  const clamped: RiskSettings = {
    ...settings,
    value:
      settings.mode === "percent"
        ? Math.min(settings.value, HARD_CEILING_PCT)
        : settings.value,
  };
  localStorage.setItem("xai_risk_settings", JSON.stringify(clamped));
  // Also persist into the active account so it survives account switching
  const active = getActiveAccount();
  if (active) {
    const updated: SavedAccount = { ...active, riskSettings: clamped };
    const list = getSavedAccounts().filter((a) => a.id !== active.id);
    list.push(updated);
    localStorage.setItem("xai_saved_accounts", JSON.stringify(list));
    localStorage.setItem("xai_active_account", JSON.stringify(updated));
  }
}

export async function fetchPortfolio(accountId: string = getAccountId()): Promise<PortfolioData> {
  const { key, secret } = getCustomAlpacaKeys();
  const headers: Record<string, string> = {};
  if (key) headers["X-Alpaca-Key"] = key;
  if (secret) headers["X-Alpaca-Secret"] = secret;

  try {
    const res = await fetch(`${API_BASE_URL}/portfolio?account_id=${accountId}`, {
      cache: "no-store",
      headers,
    });
    if (!res.ok) {
      return {
        account: { portfolio_value: "100000.00", cash: "100000.00", buying_power: "200000.00", equity: "100000.00" },
        positions: [],
      };
    }
    return res.json();
  } catch (err) {
    return {
      account: { portfolio_value: "100000.00", cash: "100000.00", buying_power: "200000.00", equity: "100000.00" },
      positions: [],
    };
  }
}

export async function scanWatchlist(
  symbols: string[],
  strategyProfile: string = "SWING",
  accountId: string = getAccountId()
): Promise<{ scanned_count: number; results: Array<{ symbol: string; status: string; hypothesis_id?: string; error?: string }> }> {
  const risk = getRiskSettings();
  const res = await fetch(`${API_BASE_URL}/trade/scan-watchlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symbols,
      strategy_profile: strategyProfile,
      account_id: accountId,
      risk_mode: risk.mode,
      risk_value: risk.value,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to scan watchlist");
  }
  return res.json();
}

export async function fetchHypotheses(accountId: string = getAccountId()): Promise<Hypothesis[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/trade/hypotheses?account_id=${accountId}`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn("fetchHypotheses network error:", err);
    return [];
  }
}

export async function fetchTradeDetail(hypothesisId: string): Promise<{ hypothesis: Hypothesis; audit_logs: AuditLog[] }> {
  const res = await fetch(`${API_BASE_URL}/trade/${hypothesisId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch trade details");
  return res.json();
}

export async function triggerTrade(
  symbol: string,
  strategyProfile: string = "SWING",
  accountId: string = getAccountId()
): Promise<{ hypothesis_id: string; status: string; alpaca_order_id?: string; computed_qty?: number; dollar_risk?: number; pct_of_equity?: number }> {
  const risk = getRiskSettings();
  const res = await fetch(`${API_BASE_URL}/trade/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symbol,
      strategy_profile: strategyProfile,
      account_id: accountId,
      risk_mode: risk.mode,
      risk_value: risk.value,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to start trade");
  }
  return res.json();
}

export async function triggerAudit(hypothesisId: string): Promise<{ audit_verdict: string; status: string; lesson_learned?: string }> {
  const res = await fetch(`${API_BASE_URL}/trade/${hypothesisId}/audit`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to run audit");
  }
  return res.json();
}

export async function fetchMemories(accountId: string = getAccountId()): Promise<PostMortem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/memory?account_id=${accountId}`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn("fetchMemories network error:", err);
    return [];
  }
}

export interface MarketBar {
  t: string;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

export async function fetchMarketBars(
  symbol: string,
  timeframe: string = "1Day",
  limit: number = 40
): Promise<MarketBar[]> {
  const encoded = encodeURIComponent(symbol);
  const res = await fetch(
    `${API_BASE_URL}/market-data?symbol=${encoded}&timeframe=${timeframe}&limit=${limit}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error("Failed to fetch market data");
  const data = await res.json();
  return data.bars || [];
}

// ── Multi-Asset Scanner Interfaces & APIs ─────────────────────────────

export interface ScreenResult {
  symbol: string;
  passed: boolean;
  passed_count: number;
  criteria_met: string[];
  metrics: {
    latest_close?: number;
    volume_ratio?: number;
    rsi?: number;
    breakout_type?: string;
  };
  reason?: string;
  already_active?: boolean;
  escalation_status?: string;
  hypothesis_id?: string;
  alpaca_order_id?: string;
  error?: string;
}

export interface PortfolioRiskExposure {
  equity: number;
  total_dollar_risk: number;
  total_risk_pct: number;
  active_positions_count: number;
  is_over_cap: boolean;
  aggregate_cap_pct: number;
  remaining_risk_budget_dollars: number;
}

export interface ScannerStatus {
  enabled: boolean;
  is_scanning: boolean;
  last_scan_time: string | null;
  next_scan_time: string | null;
  interval_minutes: number;
  watchlist_count: number;
  criteria_threshold: number;
  max_escalations_per_cycle: number;
  aggregate_risk_cap_pct: number;
  daily_circuit_breaker_pct: number;
  last_cycle?: {
    timestamp: string | null;
    scanned_count: number;
    passed_count: number;
    escalated_count: number;
    circuit_breaker_tripped: boolean;
    circuit_breaker_msg: string | null;
    portfolio_risk_exposure?: PortfolioRiskExposure;
    tickers: ScreenResult[];
    errors: string[];
  };
  last_error: string | null;
}

export interface ScannerConfig {
  enabled: boolean;
  interval_minutes: number;
  watchlist: string[];
  criteria_threshold: number;
  volume_spike_multiplier: number;
  rsi_oversold: number;
  rsi_overbought: number;
  breakout_period: number;
  max_escalations_per_cycle: number;
  aggregate_risk_cap_pct: number;
  daily_circuit_breaker_pct: number;
  strategy_profile: string;
  risk_mode: string;
  risk_value: number;
}

export async function fetchScannerStatus(): Promise<ScannerStatus> {
  try {
    const res = await fetch(`${API_BASE_URL}/scanner/status`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch scanner status");
    return await res.json();
  } catch (e) {
    console.warn("fetchScannerStatus error:", e);
    return {
      enabled: true,
      is_scanning: false,
      last_scan_time: null,
      next_scan_time: null,
      interval_minutes: 15,
      watchlist_count: 52,
      criteria_threshold: 2,
      max_escalations_per_cycle: 3,
      aggregate_risk_cap_pct: 6.0,
      daily_circuit_breaker_pct: -5.0,
      last_error: null,
    };
  }
}

export async function toggleScanner(enabled: boolean): Promise<{ enabled: boolean; message: string }> {
  const res = await fetch(`${API_BASE_URL}/scanner/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error("Failed to toggle scanner");
  return res.json();
}

export async function triggerManualScan(accountId: string = getAccountId()): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/scanner/trigger`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account_id: accountId }),
  });
  if (!res.ok) throw new Error("Failed to trigger scanner cycle");
  return res.json();
}

export async function fetchScannerConfig(): Promise<ScannerConfig> {
  const res = await fetch(`${API_BASE_URL}/scanner/config`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch scanner config");
  return res.json();
}

export async function updateScannerConfig(config: Partial<ScannerConfig>): Promise<ScannerConfig> {
  const res = await fetch(`${API_BASE_URL}/scanner/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error("Failed to update scanner config");
  return res.json();
}

export async function fetchPortfolioRisk(accountId: string = getAccountId()): Promise<PortfolioRiskExposure> {
  try {
    const res = await fetch(`${API_BASE_URL}/scanner/portfolio-risk?account_id=${accountId}`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch portfolio risk");
    return await res.json();
  } catch (e) {
    return {
      equity: 100000,
      total_dollar_risk: 0,
      total_risk_pct: 0,
      active_positions_count: 0,
      is_over_cap: false,
      aggregate_cap_pct: 6.0,
      remaining_risk_budget_dollars: 6000,
    };
  }
}
