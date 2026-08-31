"use client";

import { useEffect, useState } from "react";
import { fetchMarketBars, MarketBar } from "@/lib/api";

interface TradingChartProps {
  symbol: string;
  targetPrice?: number;
  stopLossPrice?: number;
  entryPrice?: number;
}

export default function TradingChart({
  symbol,
  targetPrice,
  stopLossPrice,
  entryPrice,
}: TradingChartProps) {
  const [timeframe, setTimeframe] = useState<string>("1Day");
  const [bars, setBars] = useState<MarketBar[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    setLoading(true);
    fetchMarketBars(symbol, timeframe, 35)
      .then((data) => setBars(data))
      .catch((err) => console.error("Chart fetch error:", err))
      .finally(() => setLoading(false));
  }, [symbol, timeframe]);

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center text-xs text-slate-400 gap-2 border border-slate-800 rounded bg-slate-950/40">
        <span className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        Loading candlestick market data ({timeframe})...
      </div>
    );
  }

  if (!bars || bars.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-xs text-slate-500 border border-dashed border-slate-800 rounded">
        No candlestick data available for {symbol} ({timeframe}).
      </div>
    );
  }

  // Calculate scales for SVG rendering
  const minPrice = Math.min(
    ...bars.map((b) => b.l),
    stopLossPrice || Infinity,
    entryPrice || Infinity,
    targetPrice || Infinity
  );
  const maxPrice = Math.max(
    ...bars.map((b) => b.h),
    targetPrice || -Infinity,
    entryPrice || -Infinity,
    stopLossPrice || -Infinity
  );
  const pricePadding = (maxPrice - minPrice) * 0.08 || 1;
  const yMin = minPrice - pricePadding;
  const yMax = maxPrice + pricePadding;

  const chartHeight = 220;
  const svgWidth = 600;
  const barWidth = Math.max(4, (svgWidth / bars.length) * 0.6);
  const gap = svgWidth / bars.length;

  const getY = (price: number) => {
    return chartHeight - ((price - yMin) / (yMax - yMin)) * chartHeight;
  };

  return (
    <div className="space-y-3">
      {/* Timeframe Selector Header */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
        <div className="flex items-center space-x-2 text-xs">
          <span className="font-bold text-slate-200">{symbol}</span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400 font-mono">OHLCV Candlestick</span>
        </div>

        {/* Timeframe Buttons */}
        <div className="flex items-center gap-1 bg-slate-900 p-0.5 rounded border border-slate-800 text-[11px]">
          {[
            { label: "1M", value: "1Min" },
            { label: "5M", value: "5Min" },
            { label: "1H", value: "1Hour" },
            { label: "1D", value: "1Day" },
          ].map((tf) => (
            <button
              key={tf.value}
              onClick={() => setTimeframe(tf.value)}
              className={`px-2 py-0.5 rounded font-semibold transition-all ${
                timeframe === tf.value
                  ? "bg-emerald-600 text-slate-950 shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* SVG Candlestick Chart */}
      <div className="relative bg-slate-950/80 p-3 rounded border border-slate-800 overflow-hidden">
        <svg
          viewBox={`0 0 ${svgWidth} ${chartHeight}`}
          className="w-full h-56 overflow-visible"
        >
          {/* Target Price Line (Green) */}
          {targetPrice && (
            <g>
              <line
                x1="0"
                y1={getY(targetPrice)}
                x2={svgWidth}
                y2={getY(targetPrice)}
                stroke="#10b981"
                strokeWidth="1.5"
                strokeDasharray="4 4"
              />
              <text
                x={svgWidth - 90}
                y={getY(targetPrice) - 4}
                fill="#10b981"
                fontSize="10"
                fontWeight="bold"
              >
                TARGET: ${targetPrice.toFixed(2)}
              </text>
            </g>
          )}

          {/* Entry Price Line (Blue) */}
          {entryPrice && (
            <g>
              <line
                x1="0"
                y1={getY(entryPrice)}
                x2={svgWidth}
                y2={getY(entryPrice)}
                stroke="#3b82f6"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <text
                x={svgWidth - 90}
                y={getY(entryPrice) - 4}
                fill="#3b82f6"
                fontSize="9"
              >
                ENTRY: ${entryPrice.toFixed(2)}
              </text>
            </g>
          )}

          {/* Stop Loss Line (Red) */}
          {stopLossPrice && (
            <g>
              <line
                x1="0"
                y1={getY(stopLossPrice)}
                x2={svgWidth}
                y2={getY(stopLossPrice)}
                stroke="#ef4444"
                strokeWidth="1.5"
                strokeDasharray="4 4"
              />
              <text
                x={svgWidth - 90}
                y={getY(stopLossPrice) - 4}
                fill="#ef4444"
                fontSize="10"
                fontWeight="bold"
              >
                STOP: ${stopLossPrice.toFixed(2)}
              </text>
            </g>
          )}

          {/* Candlesticks */}
          {bars.map((bar, idx) => {
            const x = idx * gap + gap / 2;
            const isBullish = bar.c >= bar.o;
            const candleColor = isBullish ? "#10b981" : "#ef4444";

            const yHigh = getY(bar.h);
            const yLow = getY(bar.l);
            const yOpen = getY(bar.o);
            const yClose = getY(bar.c);

            const candleTop = Math.min(yOpen, yClose);
            const candleHeight = Math.max(2, Math.abs(yOpen - yClose));

            return (
              <g key={bar.t || idx} className="hover:opacity-80 transition-opacity">
                {/* Wick */}
                <line
                  x1={x}
                  y1={yHigh}
                  x2={x}
                  y2={yLow}
                  stroke={candleColor}
                  strokeWidth="1"
                />
                {/* Body */}
                <rect
                  x={x - barWidth / 2}
                  y={candleTop}
                  width={barWidth}
                  height={candleHeight}
                  fill={candleColor}
                  rx="0.5"
                />
              </g>
            );
          })}
        </svg>

        {/* Legend Footer */}
        <div className="flex items-center justify-between text-[10px] text-slate-500 pt-2 border-t border-slate-900">
          <div className="flex items-center space-x-3">
            <span className="flex items-center gap-1 text-emerald-400 font-medium">
              <span className="w-2 h-0.5 bg-emerald-500 inline-block" /> Target Price
            </span>
            <span className="flex items-center gap-1 text-red-400 font-medium">
              <span className="w-2 h-0.5 bg-red-500 inline-block" /> Stop Loss
            </span>
          </div>
          <span>Showing last {bars.length} sessions ({timeframe})</span>
        </div>
      </div>
    </div>
  );
}
