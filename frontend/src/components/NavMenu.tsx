"use client";

import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/hypotheses", label: "Hypotheses & Audits" },
  { href: "/memory", label: "Vector Memory" },
];

export default function NavMenu() {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();

  // Only portal-render after mount (avoids SSR mismatch)
  useEffect(() => {
    setMounted(true);
  }, []);

  // Close drawer when route changes
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Lock body scroll while drawer is open
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  const drawer = mounted
    ? createPortal(
        <>
          {/* Backdrop — rendered at body level, z-index 998 */}
          {open && (
            <div
              aria-hidden="true"
              onClick={() => setOpen(false)}
              style={{
                position: "fixed",
                inset: 0,
                zIndex: 998,
                background: "rgba(9,13,22,0.65)",
                backdropFilter: "blur(2px)",
                WebkitBackdropFilter: "blur(2px)",
                animation: "navFadeIn 0.15s ease forwards",
              }}
            />
          )}

          {/* Drawer panel — rendered at body level, z-index 999 */}
          {open && (
            <div
              id="mobile-drawer"
              role="dialog"
              aria-modal="true"
              aria-label="Navigation menu"
              style={{
                position: "fixed",
                top: "4rem", // sits just below the 64px header
                left: 0,
                right: 0,
                zIndex: 999,
                background: "#0f172a",
                borderBottom: "1px solid rgba(51,65,85,0.7)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
                animation: "navSlideDown 0.22s ease forwards",
              }}
            >
              {/* Drawer inner */}
              <div style={{ padding: "0.75rem 1rem 1.25rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                <p style={{ fontSize: "0.6875rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#475569", marginBottom: "0.375rem" }}>
                  Navigation
                </p>
                {NAV_LINKS.map(({ href, label }) => (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setOpen(false)}
                    style={{
                      display: "block",
                      padding: "0.625rem 0.75rem",
                      borderRadius: "0.375rem",
                      fontSize: "0.9375rem",
                      color: pathname === href ? "#34d399" : "#94a3b8",
                      background: pathname === href ? "rgba(52,211,153,0.1)" : "transparent",
                      transition: "background 0.12s ease, color 0.12s ease",
                    }}
                    onMouseEnter={(e) => {
                      if (pathname !== href) {
                        (e.currentTarget as HTMLElement).style.background = "rgba(52,211,153,0.08)";
                        (e.currentTarget as HTMLElement).style.color = "#34d399";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (pathname !== href) {
                        (e.currentTarget as HTMLElement).style.background = "transparent";
                        (e.currentTarget as HTMLElement).style.color = "#94a3b8";
                      }
                    }}
                  >
                    {label}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </>,
        document.body
      )
    : null;

  return (
    <>
      {/* ── Desktop nav — hidden below 768px via CSS ── */}
      <nav className="nav-desktop" aria-label="Primary navigation">
        {NAV_LINKS.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`nav-link${pathname === href ? " nav-link--active" : ""}`}
          >
            {label}
          </Link>
        ))}
      </nav>

      {/* ── Hamburger button — hidden above 768px via CSS ── */}
      <button
        className="nav-hamburger"
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        aria-controls="mobile-drawer"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          /* × close icon */
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          /* ☰ hamburger icon */
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        )}
      </button>

      {/* Portal-rendered drawer + backdrop */}
      {drawer}
    </>
  );
}
