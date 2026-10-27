import { useState, type FormEvent } from "react";
import { api } from "./api";
import { Notice } from "./case-ui";
import type { CaseData } from "./types";

export function IntegrationIntake({
  tenant,
  onAgent,
  onCase,
}: {
  tenant: string;
  onAgent: () => Promise<void>;
  onCase: (id: string) => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function act(work: () => Promise<void>) {
    setPending(true);
    setError("");
    setMessage("");
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Integration failed");
    } finally {
      setPending(false);
    }
  }
  async function register(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    await act(async () => {
      const policy: unknown = JSON.parse(String(data.get("policy")));
      await api("/v1/agents", { agent_id: String(data.get("agent")), policy });
      await onAgent();
      setMessage("Agent registered. Existing policies were preserved.");
    });
  }
  async function capture(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    await act(async () => {
      const body = JSON.parse(String(data.get("capture"))) as { agent_id?: unknown };
      if (typeof body.agent_id !== "string")
        throw new Error("Capture must name its registered agent.");
      const snapshot = await api<{ snapshot_id: string }>("/v1/replay-snapshots", body);
      const result = await api<CaseData>("/v1/cases", {
        agent_id: body.agent_id,
        snapshot_id: snapshot.snapshot_id,
        execution_mode: "live",
        idempotency_key: crypto.randomUUID(),
      });
      await onCase(result.case_id);
    });
  }
  return (
    <section className="panel">
      <h2>Connect your agent and incident</h2>
      <p>
        Reviewer access registers an agent policy and an original captured incident. Captures must
        contain redacted data, matching action/receipt identities and legitimate utility checks. No
        uploaded code executes.
      </p>
      <form onSubmit={(e) => void register(e)}>
        <label className="form-field">
          New agent ID
          <input
            name="agent"
            required
            pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,63}"
            placeholder="my-agent"
          />
        </label>
        <label className="form-field">
          Current agent policy JSON
          <textarea
            name="policy"
            rows={7}
            required
            defaultValue={JSON.stringify(
              {
                agent: "my-agent",
                org: tenant,
                mode: "enforce",
                tools: { send_message: { capability: "send" }, summarize: { capability: "read" } },
              },
              null,
              2,
            )}
          />
        </label>
        <button className="button button-outline" disabled={pending}>
          Register agent
        </button>
      </form>
      <hr />
      <form onSubmit={(e) => void capture(e)}>
        <label className="form-field">
          Incident capture JSON
          <textarea
            name="capture"
            rows={10}
            required
            placeholder="Paste an original capture matching POST /v1/replay-snapshots in the API schema"
          />
        </label>
        <p className="fine-print">
          The API schema documents all fields. Supported replay tools are local send_message and
          deterministic document reading. Producer attestations are recorded, not independently
          verified. After import, publish the evidence to the managed sources or ingest it through
          your own governed Zetaris pipeline.
        </p>
        <button className="button button-dark" disabled={pending}>
          Import captured incident
        </button>
      </form>
      {error && <Notice error>{error}</Notice>}
      {message && <Notice>{message}</Notice>}
    </section>
  );
}
