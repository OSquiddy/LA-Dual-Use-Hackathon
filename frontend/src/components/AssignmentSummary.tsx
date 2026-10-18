import type { Assignment, Incident } from "../types";

type Responsibility = Pick<Incident, "department" | "owner" | "status" | "accepted" | "acknowledged"> & {
  assignment?: Assignment | null;
  closed_by?: string | null;
  closed_at?: string | null;
};

export function assignmentStatus(incident: Responsibility): string {
  const assignment = incident.assignment;
  const department = assignment ? assignment.department : incident.department;
  const owner = assignment ? assignment.owner : incident.owner;
  if (incident.status === "closed") return incident.closed_by ? `Closed by ${incident.closed_by}` : "Closed · closing person not recorded";
  const accepted = assignment ? Boolean(assignment.accepted_at) : incident.accepted;
  const acceptedBy = assignment ? assignment.accepted_by : owner;
  if (accepted) return acceptedBy ? `Accepted by ${acceptedBy}` : "Accepted · accepting individual not recorded";
  if (!department) return "Awaiting department assignment";
  const acknowledged = assignment ? Boolean(assignment.acknowledged_at) : incident.acknowledged;
  if (acknowledged) return "Acknowledged · awaiting acceptance";
  if (!owner) return "Department assigned · individual not assigned";
  return "Individual assigned · awaiting acknowledgment";
}

export function AssignmentTime({ value }: { value?: string | null }) {
  if (!value || Number.isNaN(Date.parse(value))) return <span>Not recorded</span>;
  // Use the demonstration's location consistently, including on teammates' computers.
  return <time dateTime={value}>{new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short",
  }).format(new Date(value))}</time>;
}

/** One consistent view of responsibility in all queues, critical alerts and detail. */
export default function AssignmentSummary({ incident }: { incident: Responsibility }) {
  const assignment = incident.assignment;
  const department = assignment ? assignment.department : incident.department;
  const owner = assignment ? assignment.owner : incident.owner;
  const acknowledged = assignment ? Boolean(assignment.acknowledged_at) : incident.acknowledged;
  const accepted = assignment ? Boolean(assignment.accepted_at) : incident.accepted;
  const acceptedBy = assignment ? assignment.accepted_by : owner;
  return (
    <section className="responsibility" aria-label="Assignment and accountability">
      <div className="responsibility-heading">
        <strong>{department || "Department not assigned"}</strong>
        <span aria-label="Assignment status" className={`responsibility-status ${incident.status === "closed" ? "closed" : accepted ? "accepted" : "pending"}`}>
          {assignmentStatus(incident)}
        </span>
      </div>
      <dl className="responsibility-fields">
        <div><dt>Responsible department</dt><dd>{department || "Awaiting assignment"}</dd></div>
        <div><dt>Assigned individual</dt><dd>{owner || "Not assigned"}</dd></div>
        <div><dt>Acknowledgment</dt><dd>
          {acknowledged ? `Recorded${assignment?.acknowledged_by ? ` by ${assignment.acknowledged_by}` : ""}` : "Not recorded"}
          {assignment?.acknowledged_at && <><br /><AssignmentTime value={assignment.acknowledged_at} /></>}
        </dd></div>
        <div><dt>Acceptance</dt><dd>
          {accepted ? acceptedBy ? `Accepted by ${acceptedBy}` : "Recorded · accepting individual not recorded" : "Not accepted"}
          {assignment?.accepted_at && <><br /><AssignmentTime value={assignment.accepted_at} /></>}
        </dd></div>
        <div><dt>Assigned at</dt><dd><AssignmentTime value={assignment?.assigned_at} /></dd></div>
        {assignment?.default_owner_at && <div><dt>On-call individual assigned</dt><dd><AssignmentTime value={assignment.default_owner_at} /></dd></div>}
        {incident.status === "closed" && <div><dt>Closed at</dt><dd><AssignmentTime value={incident.closed_at} /></dd></div>}
      </dl>
      <p className="roster-note">Prototype roster · fictional demo personnel</p>
    </section>
  );
}
