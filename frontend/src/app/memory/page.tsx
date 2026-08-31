"use client";

import { useEffect, useState } from "react";
import { fetchMemories, PostMortem } from "@/lib/api";

export default function MemoryPage() {
  const [memories, setMemories] = useState<PostMortem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMemories()
      .then((data) => setMemories(data))
      .catch((err) => console.error("Failed to load post-mortems:", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
            Vector Memory & Post-Mortem Library
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Long-term adaptive memory stored as 3072-dimensional vector embeddings in Supabase pgvector.
          </p>
        </div>

        <div className="bg-purple-950/40 border border-purple-800/50 text-purple-300 px-3 py-1.5 rounded-lg text-xs flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
          <span>Injected into Phase 1 Prompt</span>
        </div>
      </div>

      {/* Main Grid */}
      <div className="terminal-card p-6">
        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
            <span className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            Fetching vector memory from Supabase...
          </div>
        ) : memories.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded">
            No post-mortems stored yet. Once trades are closed in Phase 4, synthesized lessons will appear here.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {memories.map((pm) => {
              const isWin = pm.outcome === "WIN";
              const isLoss = pm.outcome === "LOSS";
              return (
                <div
                  key={pm.id}
                  className="bg-slate-900/80 p-5 rounded-lg border border-slate-800 space-y-3 hover:border-slate-700 transition-all flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span
                        className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                          isWin
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                            : isLoss
                            ? "bg-red-950 text-red-400 border border-red-800"
                            : "bg-slate-800 text-slate-300 border border-slate-700"
                        }`}
                      >
                        {pm.outcome} ({pm.pnl_percentage > 0 ? "+" : ""}
                        {pm.pnl_percentage.toFixed(2)}%)
                      </span>
                      <span className="text-slate-500 font-mono text-[10px]">
                        {new Date(pm.created_at).toLocaleDateString([], {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </span>
                    </div>

                    <p className="text-xs text-slate-200 leading-relaxed bg-slate-950/60 p-3 rounded border border-slate-800/80 italic">
                      "{pm.lesson_learned}"
                    </p>
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-slate-500 border-t border-slate-800/60 pt-2">
                    <span>Hypothesis ID: {pm.hypothesis_id.slice(0, 8)}...</span>
                    <span className="text-purple-400">VECTOR DIM: 3072</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
