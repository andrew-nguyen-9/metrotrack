import { useEffect, useState } from "react";

// The ONE a11y/theme island (DIRECTION §5). Four preferences, all applied as
// data-* on <html> and persisted to localStorage. An inline head script (see
// Base.astro) applies them pre-paint so there is no FOUC; this island only reads
// the current DOM state and edits it. Keys + attrs are the shared contract:
//   data-theme=light|·(dark)   mt-theme
//   data-colorblind=on|·       mt-colorblind
//   data-motion=reduce|·       mt-motion
//   data-text-size=s|l|·(m)    mt-text-size
type Theme = "dark" | "light";
type TextSize = "s" | "m" | "l";
const K = { theme: "mt-theme", cb: "mt-colorblind", motion: "mt-motion", text: "mt-text-size" };

function setAttr(name: string, val: string | null) {
  const el = document.documentElement;
  if (val) el.setAttribute(name, val);
  else el.removeAttribute(name);
}
function store(key: string, val: string | null) {
  try {
    if (val) localStorage.setItem(key, val);
    else localStorage.removeItem(key);
  } catch {
    /* private mode / storage disabled — preference just won't persist */
  }
}

function Segmented<T extends string>(props: {
  legend: string;
  name: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <fieldset className="flex items-center justify-between gap-3">
      <legend className="float-left text-sm text-text-muted">{props.legend}</legend>
      <div className="flex rounded-md border border-hairline p-0.5" role="radiogroup" aria-label={props.legend}>
        {props.options.map((o) => {
          const active = o.value === props.value;
          return (
            <label
              key={o.value}
              className={`cursor-pointer rounded px-2.5 py-1 text-sm ${active ? "bg-accent text-accent-ink" : "text-text-muted hover:text-text"}`}
            >
              <input
                type="radio"
                name={props.name}
                className="sr-only"
                checked={active}
                onChange={() => props.onChange(o.value)}
              />
              {o.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export default function Toggles() {
  const [theme, setTheme] = useState<Theme>("dark");
  const [cb, setCb] = useState(false);
  const [reduce, setReduce] = useState(false);
  const [size, setSize] = useState<TextSize>("m");

  // Sync control state from the pre-paint DOM once mounted (avoids SSR mismatch).
  useEffect(() => {
    const d = document.documentElement;
    setTheme(d.getAttribute("data-theme") === "light" ? "light" : "dark");
    setCb(d.getAttribute("data-colorblind") === "on");
    setReduce(d.getAttribute("data-motion") === "reduce");
    const ts = d.getAttribute("data-text-size");
    setSize(ts === "s" || ts === "l" ? ts : "m");
  }, []);

  const onTheme = (t: Theme) => {
    setTheme(t);
    setAttr("data-theme", t === "light" ? "light" : null);
    store(K.theme, t);
  };
  const onCb = (on: boolean) => {
    setCb(on);
    setAttr("data-colorblind", on ? "on" : null);
    store(K.cb, on ? "on" : null);
  };
  const onReduce = (on: boolean) => {
    setReduce(on);
    setAttr("data-motion", on ? "reduce" : null);
    store(K.motion, on ? "reduce" : null);
  };
  const onSize = (s: TextSize) => {
    setSize(s);
    setAttr("data-text-size", s === "m" ? null : s);
    store(K.text, s === "m" ? null : s);
  };

  return (
    <details className="relative">
      <summary className="flex cursor-pointer list-none items-center gap-2 rounded-md border border-hairline px-3 py-2 text-sm text-text-muted hover:text-text">
        <span aria-hidden="true">⚙</span>
        <span>Display</span>
      </summary>
      <div
        className="absolute right-0 z-40 mt-2 w-72 rounded-lg border border-hairline bg-surface-2 p-4 shadow-lg"
        role="group"
        aria-label="Display settings"
      >
        <div className="flex flex-col gap-4">
          <Segmented<Theme>
            legend="Theme" name="mt-theme" value={theme}
            options={[{ value: "dark", label: "Dark" }, { value: "light", label: "Light" }]}
            onChange={onTheme}
          />
          <Segmented<TextSize>
            legend="Text size" name="mt-text-size" value={size}
            options={[{ value: "s", label: "S" }, { value: "m", label: "M" }, { value: "l", label: "L" }]}
            onChange={onSize}
          />
          <label className="flex items-center justify-between gap-3 text-sm">
            <span className="text-text-muted">Colorblind-safe palette</span>
            <input type="checkbox" className="h-4 w-4 accent-[var(--accent)]" checked={cb} onChange={(e) => onCb(e.target.checked)} />
          </label>
          <label className="flex items-center justify-between gap-3 text-sm">
            <span className="text-text-muted">Reduce motion</span>
            <input type="checkbox" className="h-4 w-4 accent-[var(--accent)]" checked={reduce} onChange={(e) => onReduce(e.target.checked)} />
          </label>
        </div>
      </div>
    </details>
  );
}
