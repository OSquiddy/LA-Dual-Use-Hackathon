import { useEffect, useState } from "react";
import { resetDemo, setTwist } from "../api";
import type { Twists } from "../types";

const TOGGLES: { name: keyof Omit<Twists, "domain">; label: string }[] = [
  { name: "dept_silent", label: "Department goes silent" },
  { name: "surge", label: "Call surge" },
  { name: "phones_down", label: "Phones down" },
];

/** Hidden demo controls. Press T to show or hide. TODO(C12/C15): domain swap seeds. */
export default function TwistPanel({ twists }: { twists: Twists }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "t" && !(e.target instanceof HTMLInputElement)) setOpen((o) => !o);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!open) return null;
  return (
    <div className="twists">
      <strong>Twists</strong>
      {TOGGLES.map((t) => (
        <label key={t.name}>
          <input type="checkbox" checked={twists[t.name]} onChange={(e) => setTwist(t.name, { on: e.target.checked })} />
          {t.label}
        </label>
      ))}
      <button onClick={() => resetDemo("storm_night")}>Reset: storm night</button>
    </div>
  );
}
