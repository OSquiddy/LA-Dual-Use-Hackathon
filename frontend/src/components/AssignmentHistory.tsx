import type { IncidentDetail } from "../types";
import { AssignmentTime } from "./AssignmentSummary";

export default function AssignmentHistory({ incident }: { incident: IncidentDetail }) {
  const history = incident.assignment_history ?? (incident.assignment ? [incident.assignment] : []);
  return (
    <section className="assignment-history" aria-label="Assignment history">
      <h3>Assignment history</h3>
      {!history.length && <p className="muted">No department assignment has been recorded.</p>}
      <ol className="assignment-records">
        {history.map((assignment, index) => (
          <li key={assignment.id ?? index}>
            <strong>{assignment.department_display_name ?? assignment.department}</strong> · {assignment.owner_display_name ?? assignment.owner ?? "Individual not assigned"}
            {assignment.operational_unit && <small>{assignment.operational_unit}</small>}
            {assignment.owner_role && <small>{assignment.owner_role}</small>}
            <dl className="responsibility-fields">
              <div><dt>Assigned at</dt><dd><AssignmentTime value={assignment.assigned_at} /></dd></div>
              <div><dt>Recorded by</dt><dd>{assignment.assigned_by || "Not recorded in legacy assignment"}</dd></div>
              <div><dt>Acknowledgment</dt><dd>{assignment.acknowledged_at ? <>{assignment.acknowledged_by || "Name not recorded"} · <AssignmentTime value={assignment.acknowledged_at} /></> : "Not recorded"}</dd></div>
              <div><dt>Acceptance</dt><dd>{assignment.accepted_at ? <>{assignment.accepted_by || "Name not recorded"} · <AssignmentTime value={assignment.accepted_at} /></> : "Not accepted"}</dd></div>
            </dl>
            {assignment.change_reason && <p className="muted">{assignment.change_reason}</p>}
          </li>
        ))}
      </ol>
    </section>
  );
}
