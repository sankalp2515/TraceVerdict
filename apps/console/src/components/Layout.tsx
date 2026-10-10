import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { api, PRODUCT_NAME } from "../api";
import { ReviewerSignIn } from "./ReviewerSignIn";
import { SealMark } from "./ui";
import { LandingFooter, LandingHeader } from "./LandingNav";

type Status = "checking" | "ok" | "waking" | "down";
const BackendStatusContext = createContext<Status>("checking");
export const useBackendAvailability = () => useContext(BackendStatusContext);
const WAKE_GRACE_MS = 150_000;

function useBackendStatus(): Status {
  const [status, setStatus] = useState<Status>("checking");
  useEffect(() => {
    let alive = true;
    let firstFailureAt: number | null = null;
    let pending = false;
    const tick = async () => {
      if (pending || !alive) return;
      pending = true;
      try {
        await api.health();
        firstFailureAt = null;
        if (alive) setStatus("ok");
      } catch {
        firstFailureAt ??= Date.now();
        if (alive) setStatus(Date.now() - firstFailureAt < WAKE_GRACE_MS ? "waking" : "down");
      } finally {
        pending = false;
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
  const tone = waking ? "var(--neutralise)" : "var(--block)";
  return (
    <div role="status" className="mx-4 mb-3 rounded-2xl border px-4 py-3 text-[13px] sm:mx-8" style={{ borderColor: `color-mix(in srgb, ${tone} 45%, transparent)`, color: tone }}>
      {waking
        ? "The security backend is waking up (free hosting sleeps when idle). This can take 2–3 minutes."
        : "The security backend is unavailable. Results shown may be out of date; live runs are paused."}
    </div>
  );
}

function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* storage unavailable */
    }
  };
  return { dark, toggle };
}

function ThemeToggle({ dark, toggle }: { dark: boolean; toggle: () => void }) {
  return (
    <button className="pill pill-sm" style={{ minHeight: 40, width: 40, padding: 0 }} onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"} title={dark ? "Light theme" : "Dark theme"}>
      <svg viewBox="0 0 20 20" aria-hidden>
        {dark ? <><circle cx="10" cy="10" r="3.5" /><path d="M10 1.5v2M10 16.5v2M1.5 10h2M16.5 10h2M4 4l1.4 1.4M14.6 14.6 16 16M4 16l1.4-1.4M14.6 5.4 16 4" /></>
              : <path d="M16 12.5A7 7 0 0 1 7.5 4a7 7 0 1 0 8.5 8.5Z" />}
      </svg>
    </button>
  );
}

const NAV = [
  { to: "/", label: "Overview" },
  { to: "/setup", label: "Set up" },
  { to: "/playground", label: "Playground" },
  { to: "/replay", label: "Replay" },
  { to: "/results", label: "Results" },
  { to: "/decisions", label: "Decisions" },
  { to: "/review", label: "Review" },
  { to: "/policy", label: "Policy" },
];

export function Layout({ children }: { children: ReactNode }) {
  const theme = useTheme();
  const status = useBackendStatus();
  const { pathname, search } = useLocation();
  const landing = pathname === "/";
  useEffect(() => {
    const section = pathname === "/" ? new URLSearchParams(search).get("section") : null;
    const target = section ? document.getElementById(section) : null;
    if (target) { target.scrollIntoView({ behavior: "instant" }); target.focus({ preventScroll: true }); }
    else window.scrollTo({ top: 0, behavior: "instant" });
  }, [pathname, search]);
  return (
    <BackendStatusContext.Provider value={status}><div className="min-h-screen">
      <a href={landing ? "#/?section=main" : `#${pathname}`} className="sr-only skip pill" onClick={(event) => {
        event.preventDefault();
        document.getElementById("main")?.focus();
        document.getElementById("main")?.scrollIntoView({ behavior: "instant" });
      }}>Skip to content</a>
      {landing ? <LandingHeader themeToggle={<ThemeToggle {...theme} />} /> : <header className="sticky top-0 z-20 backdrop-blur-md" style={{ background: "color-mix(in srgb, var(--bg) 78%, transparent)" }}>
        <div className="mx-auto flex max-w-[1440px] items-center gap-4 px-4 py-4 sm:px-8">
          <Link to="/" className="flex items-center gap-2.5 text-[20px] tracking-tight" aria-label={`${PRODUCT_NAME} overview`}>
            <span style={{ color: "var(--accent-soft)" }}><SealMark /></span>
            <span className="brand-text">{PRODUCT_NAME}</span>
          </Link>
          <nav aria-label="Main" className="hidden flex-1 justify-center gap-1 lg:flex">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>{n.label}</NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 lg:ml-0">
            <span className="subtle hidden items-center gap-2 text-xs sm:flex" aria-live="polite">
              <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full"
                style={{ background: status === "ok" ? "var(--allow)" : status === "checking" ? "var(--subtle)" : "var(--block)" }} />
              {status === "ok" ? "Backend online" : status === "checking" ? "Checking" : status === "waking" ? "Waking" : "Offline"}
            </span>
            <ThemeToggle {...theme} />
            <ReviewerSignIn />
            <Link to="/playground" className="pill pill-primary pill-sm hidden xl:inline-flex">Run the demo</Link>
          </div>
        </div>
        <nav aria-label="Main (compact)" className="no-scrollbar flex gap-1 overflow-x-auto px-4 pb-3 sm:px-8 lg:hidden">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>{n.label}</NavLink>
          ))}
        </nav>
        <div className="h-px w-full" style={{ background: "var(--line)" }} />
        <StatusBanner status={status} />
      </header>}
      <main id="main" tabIndex={-1} className={landing ? "landing-main" : "mx-auto max-w-[1440px] px-4 py-10 sm:px-8 sm:py-14"}>{children}</main>
      {landing ? <LandingFooter /> : <footer className="mx-auto flex max-w-[1440px] flex-col gap-3 px-4 pb-10 pt-6 text-[11px] sm:flex-row sm:justify-between sm:px-8" style={{ color: "var(--subtle)", borderTop: "1px solid var(--line)" }}>
        <span className="brand-text text-[15px]">{PRODUCT_NAME}</span>
        <span>Catch what can be caught. Limit the damage. Prove what happened.</span>
        <span>Demo actions run in a sandbox · rules decide, AI advises</span>
      </footer>}
    </div></BackendStatusContext.Provider>
  );
}
