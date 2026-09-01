const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const DEV_ACCOUNT_ID = "66e809f1-2f0e-4a3a-8ea3-bdb7c2d5a849";

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
  const res = await fetch(`${API_BASE_URL}/trade/scan-watchlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbols, strategy_profile: strategyProfile, account_id: accountId }),
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
): Promise<{ hypothesis_id: string; status: string; alpaca_order_id?: string }> {
  const res = await fetch(`${API_BASE_URL}/trade/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, strategy_profile: strategyProfile, account_id: accountId }),
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
