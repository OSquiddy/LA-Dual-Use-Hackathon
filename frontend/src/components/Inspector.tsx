import { CircleCheck, CircleDashed, FileText, GitCommitVertical, Inbox, TriangleAlert } from "lucide-react";
import { acceptIncident, acknowledgeIncident, closeIncident, simulateCallback, type ActionResult } from "../api";
import { useIncidentDetail, type Tone } from "../hooks";
import type { Incident, Outcome } from "../types";
import AccountabilityChain from "./inspector/AccountabilityChain";
import AuditTrail from "./inspector/AuditTrail";
import CloseCase from "./inspector/CloseCase";
import FollowUpCard from "./inspector/FollowUpCard";
import OwnershipHeader from "./inspector/OwnershipHeader";
import ReportsList from "./inspector/ReportsList";

interface Props {
  incident: Incident; // the fresh summary from /api/state
  now: string;
  operator: string;
  notify: (text: string, tone?: Tone) => void;
  onChanged: () => void;
}

export default function Inspector({ incident, now, operator, notify, onChanged }: Props) {
  const { detail, reload } = useIncidentDetail(incident.id);

  const act = async (action: () => Promise<ActionResult>, done: string, tone: Tone = "ok") => {
    try {
      const result = await action();
      if (result === "skipped") notify("Sample data: nothing was sent. Set VITE_API=live to act.", "warn");
      else notify(done, tone);
      onChanged();
      reload();
    } catch (e) {
      notify(String(e), "danger");
    }
  };

  const closed = incident.status === "closed";

  return (
    <div>
      <OwnershipHeader
        incident={incident}
        assignment={detail?.assignment ?? null}
        now={now}
        onAcknowledge={() => act(() => acknowledgeIncident(incident.id, operator), `Acknowledged by ${operator} (not accepted)`, "accent")}
        onAccept={() => act(() => acceptIncident(incident.id, operator), `Accepted by ${operator}. The case is yours.`)}
      />

      <div className="inspector-body">
        <section className="card">
          <div className="card-head">
            <h3 className="card-title"><GitCommitVertical /> Accountability chain</h3>
            <span className="card-note">Assigned ≠ acknowledged ≠ accepted ≠ resolved</span>
          </div>
          <AccountabilityChain incident={incident} detail={detail} now={now} />
        </section>

        <div className="grid-2">
          <FollowUpCard
            incident={incident}
            detail={detail}
            disabled={closed}
            onSimulate={(outcome: Outcome) =>
              act(() => simulateCallback(incident.id, outcome, outcome === "worse"), `Simulated callback: ${outcome.replace("_", " ")}`, "accent")
            }
          />

          <section className="card">
            <div className="card-head">
              <h3 className="card-title"><CircleDashed /> Still missing</h3>
              <span className="card-note">{incident.debts.length} open</span>
            </div>
            {incident.debts.length === 0 ? (
              <p className="debts-empty"><CircleCheck /> Nothing outstanding</p>
            ) : (
              <div className="debts">
                {incident.debts.map((d) => (
                  <div key={d.kind} className="debt"><TriangleAlert /> {d.label}</div>
                ))}
              </div>
            )}
          </section>
        </div>

        <section className="card">
          <div className="card-head">
            <h3 className="card-title"><Inbox /> Why it's here</h3>
            <span className="card-note">Append-only audit trail</span>
          </div>
          <AuditTrail events={detail?.events ?? null} />
        </section>

        <section className="card">
          <div className="card-head">
            <h3 className="card-title"><FileText /> Original reports</h3>
            <span className="card-note">Every caller's words kept, even after linking</span>
          </div>
          <ReportsList reports={detail?.reports ?? null} />
        </section>

        {!closed && (
          <CloseCase
            operator={operator}
            onClose={(by, note) => act(() => closeIncident(incident.id, by, note), `Closed by ${by}`)}
          />
        )}
      </div>
    </div>
  );
}
