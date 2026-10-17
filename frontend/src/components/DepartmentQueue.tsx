import { acceptIncident } from "../api";
import type { AppState, Incident } from "../types";
import IncidentCard from "./IncidentCard";

interface Props {
  state: AppState;
  onOpen: (id: number) => void;
}

export default function DepartmentQueue({ state, onOpen }: Props) {
  const byDepartment = new Map<string, Incident[]>();
  for (const incident of state.incidents) {
    const name = incident.department ?? "Unassigned";
    byDepartment.set(name, [...(byDepartment.get(name) ?? []), incident]);
  }

  // TODO(C7): pick the accepting person instead of a generic desk name; optimistic grey-out.
  const accept = (incident: Incident) => acceptIncident(incident.id, `${incident.department ?? "Department"} desk`);

  return (
    <section className="pane">
      <h2>Department queues</h2>
      {byDepartment.size === 0 && <p className="muted">No open incidents.</p>}
      {[...byDepartment].map(([name, incidents]) => {
        const stats = state.departments.find((d) => d.name === name);
        return (
          <div key={name} className="dept">
            <h4>
              {name}
              {stats && (
                <span className={`muted ${stats.silent ? "silent" : ""}`}>
                  {" "}· accepted {stats.accepted_1h} of {stats.assigned_1h} in the last hour
                </span>
              )}
            </h4>
            {incidents.map((incident) => (
              <IncidentCard key={incident.id} incident={incident} now={state.now} onOpen={onOpen} onAccept={accept} />
            ))}
          </div>
        );
      })}
    </section>
  );
}
