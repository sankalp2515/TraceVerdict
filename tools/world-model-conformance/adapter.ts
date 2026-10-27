// Bridge the unchanged upstream suite to the Python engine used by the product.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
const bridge = fileURLToPath(new URL("./bridge.py", import.meta.url));
function invoke(operation: string, args: unknown, state?: unknown, namespace = "conformance", clock?: string) {
  const result = spawnSync(process.env.WORLD_MODEL_PYTHON || "python", [bridge], {
    input: JSON.stringify({ operation, args, state, namespace, clock }), encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024, env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error("Python World Model bridge failed");
  const value = JSON.parse(result.stdout);
  if (value.error) throw new Error(value.error);
  return value;
}
export function normalizeName(name: string) { return invoke("normalize", name).result; }
export function entityIdFromName(type: string, name: string) { return invoke("identity", [type, name]).result; }
export function decide(score: number) { return invoke("decide", score).result; }
export class WorldModel {
  state: unknown = { schema_version: 1, events: [] };
  namespace: string;
  clock?: string;
  constructor(opts: { namespace: string; clock?: () => Date }) {
    this.namespace = opts.namespace;
    this.clock = opts.clock?.().toISOString();
  }
  call(operation: string, args: unknown) {
    const value = invoke(operation, args, this.state, this.namespace, this.clock);
    this.state = value.state;
    return value.result;
  }
  async ingest(values: unknown) { return this.call("ingest", values); }
  async upsertEntity(value: unknown) { return this.call("upsert", value); }
  async relate(value: unknown) { return this.call("relate", value); }
  stateShapeCanonical() { return this.call("shape", null); }
  audit() { return this.call("audit", null); }
  view(name: string) {
    if (name !== "graph") throw new Error("Unsupported view");
    return { neighborsOf: (id: string, opts: unknown) => this.call("neighbors", [id, opts]) };
  }
}
