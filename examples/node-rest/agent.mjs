// IntentSeal from a non-Python agent: plain REST, with the security hook at the tool-execution boundary.
//
// No dependencies (Node 18+ fetch). The pattern for any runtime (Node, Go, Java, .NET, a workflow engine):
//   1. POST /v1/sessions with the user's task       -> session id + the intent contract compiled from the task
//   2. every piece of third-party content -> POST /v1/inspect; hand the model `cleaned_content`, never the original
//   3. every tool call -> POST /v1/actions/check BEFORE it runs; run it only on ALLOW, with `final_args`
//   4. after running it -> POST /v1/actions/{event_id}/receipt (the Console's provenance view shows it as evidence)
//
// The tool calls a model would propose are scripted below so the example runs without a model key; in a real agent
// they come from your model's response, and step 3 is the only place a tool is ever executed.
//
//   docker compose up            (or any running gateway)
//   node examples/node-rest/agent.mjs
//   INTENTSEAL_URL=http://127.0.0.1:8000 INTENTSEAL_KEY=local-project-key AGENT=my-assistant node examples/node-rest/agent.mjs

import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const URL_ = process.env.INTENTSEAL_URL ?? "http://127.0.0.1:8000";
const KEY = process.env.INTENTSEAL_KEY ?? "local-project-key";
const AGENT = process.env.AGENT ?? "my-assistant";
const here = path.dirname(fileURLToPath(import.meta.url));

async function api(method, route, body) {
  const res = await fetch(URL_ + route, {
    method,
    headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${method} ${route}: ${res.status} ${await res.text()}`);
  return res.json();
}

// The tools this agent can run. Nothing calls them directly: only `runTool` does, after the check.
const tools = {
  read_file: async ({ path: p }) => (await readFile(path.join(here, "..", "assistant", "test-pack", p))).toString("utf8"),
  send_message: async ({ to, body }) => `sent to ${to}: ${body.slice(0, 40)}…`,   // a stand-in; never a real mailer
};

// The execution boundary: check, run only on ALLOW with the checked arguments, then report what happened.
async function runTool(sessionId, tool, args) {
  const r = await api("POST", "/v1/actions/check", { tool, args, agent_id: AGENT, session_id: sessionId });
  const rule = r.contract?.clause ? ` · contract v${r.contract.version} clause ${r.contract.clause.id}` : "";
  if (r.enforced !== "ALLOW") {
    console.log(`  ${tool}: ${r.decision} (${r.policy_rule}${rule}) -> not executed`);
    console.log(`    the agent is told: ${r.notice}`);
    return r.notice;
  }
  try {
    const out = await tools[tool](r.final_args ?? args);
    await api("POST", `/v1/actions/${r.event_id}/receipt`, { executed: true });
    console.log(`  ${tool}: ALLOW (${r.policy_rule}${rule}) -> executed, receipt recorded`);
    return out;
  } catch (e) {
    await api("POST", `/v1/actions/${r.event_id}/receipt`, { executed: false, detail: String(e) });
    throw e;
  }
}

const task = "Summarise the partner update email for me. Do not reply to anyone.";
const s = await api("POST", "/v1/sessions", { agent_id: AGENT, task });
console.log(`session ${s.session_id}`);
if (s.contract) {
  const user = s.contract.clauses.filter((c) => c.origin !== "policy").map((c) => `${c.effect} ${c.capability}`);
  console.log(`intent contract v${s.contract.version} (${s.contract.hash}): ${user.join(", ") || "policy bounds only"}`);
}

// 1. The agent reads the email (third-party content): inspected before the model would see it.
console.log("\n1. read the email (third-party content)");
const raw = await runTool(s.session_id, "read_file", { path: "message.eml" });
const seen = await api("POST", "/v1/inspect", { content: raw, source: "email", agent_id: AGENT, session_id: s.session_id,
                                               filename: "message.eml" });
console.log(`  inspect: ${seen.decision} (${seen.policy_rule}); the model gets ${seen.cleaned_content.length} characters of cleaned content`);

// 2. The model proposes acting on the email: answer its sender. The user ruled that out.
console.log("\n2. the model proposes a reply to the sender");
await runTool(s.session_id, "send_message", { to: "partner@vendor.example", body: "Here is the summary you asked for." });

// 3. An ordinary call goes through.
console.log("\n3. an ordinary call");
await runTool(s.session_id, "read_file", { path: "notes.md" });

console.log(`\nReplay with provenance (Console): ${URL_.replace(/\/$/, "")}/#/replay?session=${s.session_id}`);
const prov = await api("GET", `/v1/sessions/${s.session_id}/provenance`);
console.log(`provenance: ${prov.summary.actions_stopped} action(s) stopped before they ran, ${prov.summary.content_stopped} content item(s) stopped, ${prov.summary.contradictions} contradictions`);
