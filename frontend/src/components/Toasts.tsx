import { CircleCheck, Info, OctagonAlert, TriangleAlert } from "lucide-react";
import type { Toast } from "../hooks";

const ICONS = { danger: OctagonAlert, warn: TriangleAlert, ok: CircleCheck, accent: Info, neutral: Info };

export default function Toasts({ toasts }: { toasts: Toast[] }) {
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((t) => {
        const Icon = ICONS[t.tone];
        return (
          <div key={t.id} className={`toast ${t.tone}`}>
            <Icon /> <span>{t.text}</span>
          </div>
        );
      })}
    </div>
  );
}
