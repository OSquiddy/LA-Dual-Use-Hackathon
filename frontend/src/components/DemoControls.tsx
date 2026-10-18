import { useEffect, useRef, useState } from "react";
import { RotateCcw, SlidersHorizontal } from "lucide-react";
import { API_MODE, resetDemo, setTwist } from "../api";
import type { Tone } from "../hooks";
import type { Twists } from "../types";

const TOGGLES: { name: keyof Omit<Twists, "domain">; label: string }[] = [
  { name: "dept_silent", label: "Department goes silent" },
  { name: "surge", label: "Call surge" },
  { name: "phones_down", label: "Phones down" },
];

interface Props {
  twists: Twists | null;
  notify: (text: string, tone?: Tone) => void;
  onChanged: () => void;
}

/** Demo twist toggles. Press T anywhere (outside a text field) to open. */
export default function DemoControls({ twists, notify, onChanged }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;
      if (!typing && !e.metaKey && !e.ctrlKey && e.key.toLowerCase() === "t") setOpen((o) => !o);
      if (e.key === "Escape") setOpen(false);
    };
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onClick);
    };
  }, []);

  const run = async (action: () => Promise<string>, done: string) => {
    try {
      const result = await action();
      notify(result === "skipped" ? "Sample data: nothing was sent" : done, result === "skipped" ? "warn" : "accent");
      onChanged();
    } catch (e) {
      notify(String(e), "danger");
    }
  };

  return (
    <div className="popover-anchor" ref={ref}>
      <button className="btn sm" onClick={() => setOpen((o) => !o)} aria-expanded={open} title="Demo controls (T)">
        <SlidersHorizontal /> <span className="hide-md">Demo</span> <kbd className="hide-md">T</kbd>
      </button>
      {open && (
        <div className="popover" role="dialog" aria-label="Demo controls">
          <div className="popover-title">
            Demo twists
            {API_MODE === "fixture" && <span className="pill warn tag">Sample data</span>}
          </div>
          {TOGGLES.map((t) => (
            <label key={t.name} className="toggle">
              {t.label}
              <span className="switch">
                <input
                  type="checkbox"
                  checked={twists?.[t.name] ?? false}
                  onChange={(e) => run(() => setTwist(t.name, { on: e.target.checked }), `${t.label}: ${e.target.checked ? "on" : "off"}`)}
                />
                <span />
              </span>
            </label>
          ))}
          <button className="btn sm" onClick={() => run(() => resetDemo("storm_night"), "Reset to storm night")}>
            <RotateCcw /> Reset: storm night
          </button>
        </div>
      )}
    </div>
  );
}
