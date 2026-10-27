import { Database, GitBranch, Cpu, ShieldCheck } from "lucide-react";
import { pretty } from "./types";
export function Connections({ data }: { data: unknown }) {
  const connections = data as Record<string, { online?: boolean; [key: string]: unknown }>;
  const definitions = [
    {
      id: "database",
      title: "Application database",
      description: "Persisted cases, evidence versions and review records.",
      Icon: Database,
    },
    {
      id: "zetaris",
      title: "Zetaris evidence",
      description: "Governed access to source records and historical context.",
      Icon: GitBranch,
    },
    {
      id: "nightshift",
      title: "Nightshift reasoning",
      description: "Model discovery for live investigator and critic requests.",
      Icon: Cpu,
    },
  ];
  return (
    <>
      <div className="connection-grid">
        {definitions.map(({ id, title, description, Icon }) => {
          const connection = connections[id];
          const online = connection?.online;
          return (
            <article className="panel connection-card" key={id}>
              <div className="panel-heading">
                <span className="line-icon">
                  <Icon size={20} />
                </span>
                <span className={`status ${online === true ? "status-green" : "status-amber"}`}>
                  <span />
                  {online === true ? "Available" : online === false ? "Unavailable" : "Unknown"}
                </span>
              </div>
              <h3>{title}</h3>
              <p>{description}</p>
              {connection && (
                <dl className="metadata">
                  {Object.entries(connection)
                    .filter(([key]) => key !== "online")
                    .map(([key, value]) => (
                      <div key={key}>
                        <dt>{key.replaceAll("_", " ")}</dt>
                        <dd>{typeof value === "string" ? value : pretty(value)}</dd>
                      </div>
                    ))}
                </dl>
              )}
            </article>
          );
        })}
      </div>
      <div className="notice">
        <ShieldCheck size={17} />
        <div>
          Status comes from backend dependency checks. Availability does not establish a successful
          live investigation. No cached sample is presented as a live connection.
        </div>
      </div>
    </>
  );
}
