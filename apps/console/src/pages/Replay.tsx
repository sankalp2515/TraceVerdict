import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type EventRow } from "../api";
import { Empty, Section } from "../components/ui";
import { Timeline } from "../components/Timeline";

export function Replay() {
  const [params, setParams] = useSearchParams();
  const [sessionId, setSessionId] = useState(params.get("session") ?? "");
  const [events, setEvents] = useState<EventRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load(id: string) {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setEvents(await api.events(id));
      setParams({ session: id });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const id = params.get("session");
    if (id) load(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const risk = events?.reduce((m, e) => Math.max(m, e.session_risk ?? 0), 0) ?? 0;
  const stopped = events?.filter((e) => e.decision && e.decision !== "ALLOW").length ?? 0;

  return (
    <Section title="Session replay" subtitle="Reconstruct a session end to end: content in, finding, decision, action.">
      <form className="mb-4 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); load(sessionId.trim()); }}>
        <label className="sr-only" htmlFor="sid">Session ID</label>
        <input id="sid" className="input mono min-w-0 flex-1" placeholder="Session ID (from the Playground or the Decisions feed)" value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
        <button className="btn btn-primary" disabled={!sessionId.trim() || loading}>{loading ? "Loading…" : "Replay"}</button>
      </form>
      {error && <p className="mb-3 text-sm" style={{ color: "var(--block)" }}>{error}</p>}
      {events === null ? (
        <Empty>Enter a session ID to replay it.</Empty>
      ) : (
        <>
          <p className="muted mb-3 text-sm">
            {events.length} events · {stopped} decisions other than allow · peak session risk {risk.toFixed(2)}
          </p>
          <Timeline events={events} />
        </>
      )}
    </Section>
  );
}
