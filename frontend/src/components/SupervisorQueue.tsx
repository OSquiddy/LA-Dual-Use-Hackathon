import type { AppState } from "../types";
import IncidentCard from "./IncidentCard";

interface Props {
  state: AppState;
  onOpen: (id: number) => void;
}

/** The supervisor sees a ranked, capped list (top 10), never the whole backlog. */
export default function SupervisorQueue({ state, onOpen }: Props) {
  const byId = new Map(state.incidents.map((i) => [i.id, i]));
  const ranked = state.supervisor_queue.flatMap((id) => byId.get(id) ?? []);

  return (
    <section className="pane supervisor">
      <h2>Supervisor · top {ranked.length}</h2>
      {ranked.length === 0 && <p className="muted">Nothing needs the supervisor right now.</p>}
      {ranked.map((incident, i) => (
        <IncidentCard key={incident.id} incident={incident} now={state.now} rank={i + 1} onOpen={onOpen} />
      ))}
    </section>
  );
}
