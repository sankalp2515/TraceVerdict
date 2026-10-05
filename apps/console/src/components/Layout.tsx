import { useEffect, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { api, ApiError, PRODUCT_NAME } from "../api";

type Status = "checking" | "ok" | "waking" | "down";

function useBackendStatus(): Status {
  const [status, setStatus] = useState<Status>("checking");
  useEffect(() => {
    let alive = true;
    let failures = 0;
    const tick = async () => {
      try {
        await api.health();
        failures = 0;
        if (alive) setStatus("ok");
      } catch (e) {
        failures += 1;
        if (alive) setStatus(e instanceof ApiError && e.status === 0 && failures < 3 ? "waking" : "down");
      }
    };
    tick();
    const id = setInterval(tick, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);
  return status;
}

function StatusBanner({ status }: { status: Status }) {
  if (status === "ok" || status === "checking") return null;
  const waking = status === "waking";
  return (
    <div role="status" className="px-4 py-2 text-sm" style={{ background: waking ? "color-mix(in srgb, var(--neutralise) 15%, var(--bg))" : "color-mix(in srgb, var(--block) 15%, var(--bg))" }}>
      {waking
        ? "The security backend is waking up (free hosting sleeps when idle). This can take up to a minute."
        : "The security backend is unavailable. Results shown may be out of date; live runs are paused."}
    </div>
  );
}

function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    try {
      const saved = localStorage.getItem("theme");
      if (saved) return saved === "dark";
    } catch {
      /* storage unavailable */
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");   // remember only an explicit choice
    } catch {
      /* storage unavailable */
    }
  };
  return (
    <button className="btn" onClick={toggle} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}>
      {dark ? "☀" : "☾"}
    </button>
  );
}

const NAV = [
  { to: "/", label: "Playground" },
  { to: "/replay", label: "Session replay" },
  { to: "/scorecard", label: "Scorecard" },
  { to: "/decisions", label: "Decisions" },
];

export function Layout({ children }: { children: ReactNode }) {
  const status = useBackendStatus();
  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 btn">Skip to content</a>
      <header className="sticky top-0 z-10 border-b backdrop-blur" style={{ borderColor: "var(--border)", background: "color-mix(in srgb, var(--bg) 85%, transparent)" }}>
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
          <div className="flex items-center gap-2 font-semibold">
            <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden><path d="M16 2 4 7v8c0 7 5 12.5 12 15 7-2.5 12-8 12-15V7z" fill="var(--accent)" /></svg>
            <span>{PRODUCT_NAME}</span>
            <span className="muted hidden text-sm font-normal sm:inline">Security Console</span>
          </div>
          <nav aria-label="Main" className="order-3 flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto sm:flex-1 sm:justify-center">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end
                className={({ isActive }) => `whitespace-nowrap rounded-md px-3 py-1.5 text-sm ${isActive ? "font-semibold" : "muted"}`}
                style={({ isActive }) => (isActive ? { background: "var(--panel-2)" } : undefined)}
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <span className="muted hidden text-xs sm:inline" aria-live="polite">
              {status === "ok" ? "● Backend online" : status === "checking" ? "Checking…" : ""}
            </span>
            <ThemeToggle />
          </div>
        </div>
        <StatusBanner status={status} />
      </header>
      <main id="main" className="mx-auto max-w-6xl space-y-4 px-4 py-5">{children}</main>
      <footer className="muted mx-auto max-w-6xl px-4 pb-8 text-xs">
        Rules decide, AI advises. Every decision is logged with its reason. Demo actions run in a sandbox: no real email or external calls.
      </footer>
    </div>
  );
}
