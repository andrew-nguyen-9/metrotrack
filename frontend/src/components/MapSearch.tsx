import { useId, useMemo, useRef, useState } from "react";

// MapSearch — an ARIA combobox (APG "combobox with listbox popup") over the
// map's routes + stops. Zero backend: entries are the transit.json route list
// plus a stop index the map snapshots from the loaded vector tiles. Keyboard:
// ↓/↑ move, Enter select, Esc close. Matches on label / id / sublabel.

export type SearchEntry = {
  kind: "route" | "stop";
  id: string;
  authority: string;
  label: string;
  sublabel?: string;
  lngLat?: [number, number]; // stops carry their point for fly-to
};

const MAX = 8;

export default function MapSearch({
  entries, onSelect,
}: { entries: SearchEntry[]; onSelect: (e: SearchEntry) => void }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return [];
    const hits: SearchEntry[] = [];
    for (const e of entries) {
      if (
        e.label.toLowerCase().includes(s) ||
        e.id.toLowerCase().includes(s) ||
        e.sublabel?.toLowerCase().includes(s)
      ) {
        hits.push(e);
        if (hits.length >= MAX) break;
      }
    }
    return hits;
  }, [q, entries]);

  const choose = (e: SearchEntry | undefined) => {
    if (!e) return;
    onSelect(e);
    setQ(e.label);
    setOpen(false);
  };

  const onKey = (ev: React.KeyboardEvent) => {
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (ev.key === "Enter") {
      if (open && results[active]) {
        ev.preventDefault();
        choose(results[active]);
      }
    } else if (ev.key === "Escape") {
      setOpen(false);
    }
  };

  const showList = open && results.length > 0;

  return (
    <div className="relative">
      <label htmlFor={`${listId}-in`} className="mb-1 block font-medium text-text">
        Find a route or stop
      </label>
      <input
        id={`${listId}-in`}
        ref={inputRef}
        type="text"
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList ? `${listId}-opt-${active}` : undefined}
        autoComplete="off"
        placeholder="e.g. Red Line, 22, Union Station"
        value={q}
        onChange={(e) => { setQ(e.target.value); setOpen(true); setActive(0); }}
        onFocus={() => q && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKey}
        className="w-full rounded border border-hairline bg-surface px-2 py-1.5 text-text placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
      />
      {showList && (
        <ul
          id={listId}
          role="listbox"
          aria-label="Routes and stops"
          className="absolute z-10 mt-1 max-h-64 w-full overflow-auto rounded border border-hairline bg-surface-2 shadow-lg"
        >
          {results.map((e, i) => (
            <li
              key={`${e.kind}-${e.authority}-${e.id}`}
              id={`${listId}-opt-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(ev) => { ev.preventDefault(); choose(e); }}
              onMouseEnter={() => setActive(i)}
              className={`flex cursor-pointer items-baseline justify-between gap-2 px-2 py-1.5 ${
                i === active ? "bg-accent text-accent-ink" : "text-text"
              }`}
            >
              <span className="truncate">{e.label}</span>
              <span className={`shrink-0 text-xs ${i === active ? "text-accent-ink/80" : "text-text-muted"}`}>
                {e.sublabel}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
