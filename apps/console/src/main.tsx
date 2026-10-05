import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import { Layout } from "./components/Layout";
import { Decisions } from "./pages/Decisions";
import { Playground } from "./pages/Playground";
import { Replay } from "./pages/Replay";
import { Scorecard } from "./pages/Scorecard";

// Apply the saved/system theme before first paint.
try {
  const saved = localStorage.getItem("theme");
  const dark = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.classList.toggle("dark", dark);
} catch {
  /* storage unavailable */
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* HashRouter: works on any static host without rewrite rules */}
    <HashRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Playground />} />
          <Route path="/replay" element={<Replay />} />
          <Route path="/scorecard" element={<Scorecard />} />
          <Route path="/decisions" element={<Decisions />} />
        </Routes>
      </Layout>
    </HashRouter>
  </StrictMode>,
);
