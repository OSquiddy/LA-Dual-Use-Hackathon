import { useState } from "react";
import { Check, Clock, Eye, OctagonAlert, User } from "lucide-react";
import { clock, hpId, incidentTone, ownershipLabel, riskTone, secondsUntil } from "../format";
import type { AppState, Incident } from "../types";

type TabKey = "all" | "supervisor" | "open" | "accepted";

interface Props {
  state: AppState;
  query: string;
  selectedId: number | null;
  onSelect: (id: number) => void;
}

export default function IncidentList({ state, query, selectedId, onSelect }: Props) {
  const [tab, setTab] = useState<TabKey>("all");
  const byId = new Map(state.incidents.map((i) => [i.id, i]));
  const supervisor = state.supervisor_queue.flatMap((id) => byId.get(id) ?? []);
  const lists: Record<TabKey, Incident[]> = {
    all: state.incidents,
    supervisor,
    open: state.incidents.filter((i) => !i.accepted),
    accepted: state.incidents.filter((i) => i.accepted),
  };

  const q = query.trim().toLowerCase();
  const visible = lists[tab].filter(
    (i) => !q || [i.title, i.department ?? "", i.owner ?? "", hpId(i.id)].some((s) => s.toLowerCase().includes(q)),
  );

  const tabs: { key: TabKey; label: string; tone: string }[] = [
    { key: "all", label: "All", tone: "" },
    { key: "supervisor", label: "Supervisor top 10", tone: "danger" },
    { key: "open", label: "Unaccepted", tone: "warn" },
    { key: "accepted", label: "Accepted", tone: "ok" },
  ];

  return (
    <>
      <div className="tabs" role="tablist">
        {tabs.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            className={`tab ${tab === t.key ? "active" : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label} <span className={`count ${t.tone}`}>{lists[t.key].length}</span>
          </button>
        ))}
      </div>

      <div className="list">
        {visible.length === 0 && (
          <p className="list-empty">{q ? `Nothing matches “${query}”.` : "No incidents here."}</p>
        )}
        {visible.map((incident) => (
          <Row
            key={incident.id}
            incident={incident}
            now={state.now}
            rank={tab === "supervisor" ? supervisor.indexOf(incident) + 1 : undefined}
            selected={incident.id === selectedId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </>
  );
}

function Row({ incident, now, rank, selected, onSelect }: {
  incident: Incident;
  now: string;
  rank?: number;
  selected: boolean;
  onSelect: (id: number) => void;
}) {
  const tone = incidentTone(incident);
  const left = secondsUntil(incident.next_step_at, now);
  const StatusIcon = incident.accepted ? Check : incident.critical ? OctagonAlert : incident.acknowledged ? Eye : User;

  return (
    <button className={`row ${tone} ${selected ? "selected" : ""}`} onClick={() => onSelect(incident.id)} aria-current={selected}>
      <span className="row-top">
        <span className={`dot ${tone}`} />
        {rank !== undefined && <span className="rank">#{rank}</span>}
        <span className="mono faint">{hpId(incident.id)}</span>
        {incident.department && <span className="chip">{incident.department}</span>}
        <span className={`risk ${riskTone(incident)}`} title="Risk score (evidence only)">{incident.risk_score}</span>
      </span>
      <span className="row-title">{incident.title}</span>
      <span className="row-bottom">
        <span className={`status ${tone}`}><StatusIcon /> {ownershipLabel(incident)}</span>
        {left !== null ? (
          <span className="mono" title="Next escalation step">
            <Clock style={{ width: 12, height: 12, verticalAlign: -2 }} /> {clock(left)}
          </span>
        ) : (
          <span className="mono">{incident.report_count} {incident.report_count === 1 ? "report" : "reports"}</span>
        )}
      </span>
    </button>
  );
}
