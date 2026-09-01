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

export function getCustomAlpacaKeys(): { key?: string; secret?: string } {
  if (typeof window === "undefined") return {};
  const key = localStorage.getItem("xai_alpaca_key") || undefined;
  const secret = localStorage.getItem("xai_alpaca_secret") || undefined;
  return { key, secret };
}

export function setCustomAlpacaKeys(key: string, secret: string) {
  if (typeof window === "undefined") return;
  if (key) localStorage.setItem("xai_alpaca_key", key);
  else localStorage.removeItem("xai_alpaca_key");

  if (secret) localStorage.setItem("xai_alpaca_secret", secret);
  else localStorage.removeItem("xai_alpaca_secret");
}

export async function fetchPortfolio(accountId: string = DEV_ACCOUNT_ID): Promise<PortfolioData> {
  const { key, secret } = getCustomAlpacaKeys();
  const headers: Record<string, string> = {};
  if (key) headers["X-Alpaca-Key"] = key;
  if (secret) headers["X-Alpaca-Secret"] = secret;

  const res = await fetch(`${API_BASE_URL}/portfolio?account_id=${accountId}`, {
    cache: "no-store",
    headers,
  });
  if (!res.ok) throw new Error("Failed to fetch portfolio");
  return res.json();
}

export async function scanWatchlist(
  symbols: string[],
  accountId: string = DEV_ACCOUNT_ID
): Promise<{ scanned_count: number; results: Array<{ symbol: string; status: string; hypothesis_id?: string; error?: string }> }> {
  const res = await fetch(`${API_BASE_URL}/trade/scan-watchlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbols, account_id: accountId }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to scan watchlist");
  }
  return res.json();
}

export async function fetchHypotheses(accountId: string = DEV_ACCOUNT_ID): Promise<Hypothesis[]> {
  const res = await fetch(`${API_BASE_URL}/trade/hypotheses?account_id=${accountId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch hypotheses");
  return res.json();
}

export async function fetchTradeDetail(hypothesisId: string): Promise<{ hypothesis: Hypothesis; audit_logs: AuditLog[] }> {
  const res = await fetch(`${API_BASE_URL}/trade/${hypothesisId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch trade details");
  return res.json();
}

export async function triggerTrade(symbol: string, accountId: string = DEV_ACCOUNT_ID): Promise<{ hypothesis_id: string; status: string; alpaca_order_id?: string }> {
  const res = await fetch(`${API_BASE_URL}/trade/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, account_id: accountId }),
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

export async function fetchMemories(accountId: string = DEV_ACCOUNT_ID): Promise<PostMortem[]> {
  const res = await fetch(`${API_BASE_URL}/memory?account_id=${accountId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch memory post-mortems");
  return res.json();
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
