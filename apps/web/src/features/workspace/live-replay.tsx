import { Status } from "./case-ui";
import { label, pretty, type ReplayTrial } from "./types";
export function LiveReplay({
  trials,
}: {
  trials: { baseline: ReplayTrial[]; candidate: ReplayTrial[] };
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="section-label">Model-driven local replay</span>
          <h3>What the agent attempted in a fresh trial</h3>
        </div>
      </div>
      <p className="muted small">
        A resisted attack means the model did not attempt the unsafe action. It is not proof that
        the policy blocked it. Provider errors remain unresolved.
      </p>
      <div className="table-scroll">
        <table className="results-table">
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Baseline trial</th>
              <th>Candidate trial</th>
              <th>Returned evidence</th>
            </tr>
          </thead>
          <tbody>
            {trials.candidate.map((trial, i) => {
              const baseline = trials.baseline.find((b) => b.scenario_id === trial.scenario_id);
              return (
                <tr key={`${trial.scenario_id}-${i}`}>
                  <td>
                    <strong>{label(trial.scenario_id)}</strong>
                    <small>{label(trial.category)} · end to end</small>
                  </td>
                  <td>
                    {baseline ? (
                      <>
                        <Status value={baseline.outcome} />
                        <small>
                          {baseline.duration_ms === undefined
                            ? "Duration not returned"
                            : `${baseline.duration_ms.toFixed(1)} ms`}
                        </small>
                      </>
                    ) : (
                      "Unavailable"
                    )}
                  </td>
                  <td>
                    <Status value={trial.outcome} />
                    <small>
                      {trial.duration_ms === undefined
                        ? "Duration not returned"
                        : `${trial.duration_ms.toFixed(1)} ms`}
                    </small>
                  </td>
                  <td>
                    <details>
                      <summary className="text-link">Inspect trial</summary>
                      <pre>{pretty({ baseline, candidate: trial })}</pre>
                    </details>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
