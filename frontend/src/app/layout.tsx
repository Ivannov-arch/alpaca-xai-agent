import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
});

export const metadata: Metadata = {
  title: "XAI Trading Agent — Explainable Autonomous Trading",
  description: "Self-correcting AI trading agent using LangGraph, Alpaca Paper Trading, and Supabase Vector Memory.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistMono.variable} dark`}>
      <body className="bg-[#090d16] text-slate-100 min-h-screen flex flex-col font-mono selection:bg-emerald-500/30">
        {/* Header Navigation */}
        <header className="border-b border-slate-800 bg-[#0f172a]/80 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/" className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-bold text-lg tracking-wider text-emerald-400">
                  XAI.AGENT
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  ALPACA PAPER
                </span>
              </Link>
            </div>

            <nav className="flex items-center space-x-6 text-sm">
              <Link
                href="/"
                className="hover:text-emerald-400 transition-colors py-1"
              >
                Dashboard
              </Link>
              <Link
                href="/hypotheses"
                className="hover:text-emerald-400 transition-colors py-1"
              >
                Hypotheses & Audits
              </Link>
              <Link
                href="/memory"
                className="hover:text-emerald-400 transition-colors py-1"
              >
                Vector Memory
              </Link>
            </nav>

            <div className="flex items-center space-x-3 text-xs text-slate-400">
              <span className="flex items-center space-x-1.5 bg-emerald-950/40 border border-emerald-800/50 text-emerald-400 px-2.5 py-1 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                <span>Worker Active</span>
              </span>
            </div>
          </div>
        </header>

        {/* Main Content Container */}
        <main className="flex-1 max-w-7xl w-full mx-auto p-6">{children}</main>

        {/* Terminal Footer */}
        <footer className="border-t border-slate-800 py-4 text-center text-xs text-slate-500">
          XAI Autonomous Agent &copy; 2026 | Powered by LangGraph &bull; Gemini 3.6 Flash &bull; Supabase pgvector
        </footer>
      </body>
    </html>
  );
}
