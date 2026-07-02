import type { LiveArrival } from "../lib/live";

// LiveArrivals — next-arrival predictions for a selected stop (e4b). Presentational
// only: the poll + fetch live in TransitMap; this renders the DataState (loading /
// empty / error / rate-limited) + the sorted prediction list. Predictions come from
// the e4a server endpoint (keys server-side) — never a direct CTA call.
//
// Source: docs/architecture/DATA_SOURCES.md → "CTA Bus Tracker / Train Tracker (live)".

export type ArrStatus = "idle" | "loading" | "ok" | "error";

type Props = {
  stop: { id: string; name: string; authority: string } | null;
  arrivals: LiveArrival[];
  status: ArrStatus;
  errors: string[];
  generated: string | null; // feed ISO timestamp — "updated Ns ago"
  colorFor: (routeId: string) => string | null;
  onClose: () => void;
};

const countdownLabel = (a: LiveArrival): string =>
  a.countdown_min === 0 ? "Due"
  : a.countdown_min === null ? (a.delayed ? "Delayed" : "—")
  : `${a.countdown_min} min`;

// Turn the endpoint's errors[] into one human sentence (keeps DataState honest).
function errorNote(errors: string[]): string {
  if (errors.some((e) => e.includes("credentials_missing")))
    return "The live feed isn’t configured for this environment yet.";
  if (errors.some((e) => /\b429\b|rate/i.test(e)))
    return "The live feed is rate-limited right now — it’ll refresh shortly.";
  return "The live feed didn’t respond. It’ll retry automatically.";
}

function agoLabel(iso: string | null): string | null {
  if (!iso) return null;
  const s = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 1000));
  return s < 60 ? `updated ${s}s ago` : `updated ${Math.round(s / 60)} min ago`;
}

export default function LiveArrivals({
  stop, arrivals, status, errors, generated, colorFor, onClose,
}: Props) {
  if (!stop) return null;

  const isCta = stop.authority === "cta";
  const rows = [...arrivals].sort((a, b) => {
    const av = a.countdown_min ?? 999, bv = b.countdown_min ?? 999;
    return av - bv;
  });
  const busy = status === "loading";
  const isError = status === "error";
  const ago = agoLabel(generated);

  return (
    <section
      aria-label={`Live arrivals at ${stop.name}`}
      className="space-y-2"
      role={isError ? "alert" : "status"}
      aria-busy={busy ? "true" : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium text-text">Next arrivals</p>
          <p className="text-xs text-text-muted">{stop.name}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close arrivals"
          className="shrink-0 rounded px-1.5 text-text-muted hover:text-text focus:outline-none focus:ring-1 focus:ring-accent"
        >
          ✕
        </button>
      </div>

      {!isCta ? (
        <p className="text-sm text-text-muted">
          Live arrivals are available for CTA stops only. Metra and Pace don’t
          publish a free real-time feed.
        </p>
      ) : busy && rows.length === 0 ? (
        <div className="motion-safe:animate-pulse space-y-1" aria-hidden="true">
          <div className="h-4 w-2/3 rounded bg-hairline" />
          <div className="h-4 w-1/2 rounded bg-hairline" />
        </div>
      ) : isError ? (
        <p className="text-sm text-text-muted">{errorNote(errors)}</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-text-muted">
          No upcoming arrivals right now. This may be a rail platform (arrivals
          are shown for bus stops) or the last service has passed.
        </p>
      ) : (
        <ul className="max-h-56 space-y-1 overflow-y-auto pr-1">
          {rows.map((a, i) => {
            const c = colorFor(a.route_id);
            return (
              <li
                key={`${a.route_id}-${a.vehicle_id ?? i}-${a.destination ?? i}`}
                className="flex items-center justify-between gap-2 border-b border-hairline/50 py-1 last:border-0"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="inline-flex h-5 min-w-[1.5rem] items-center justify-center rounded px-1 text-[11px] font-semibold text-white"
                    style={{ background: c ?? "#4f83e6" }}
                  >
                    {a.route_id}
                  </span>
                  <span className="truncate">
                    {a.destination ?? a.direction ?? "—"}
                    {a.delayed && <span className="ml-1 text-xs text-text-muted">· delayed</span>}
                  </span>
                </span>
                <span className="shrink-0 tabular text-text">{countdownLabel(a)}</span>
              </li>
            );
          })}
        </ul>
      )}

      {isCta && ago && status === "ok" && (
        <p className="text-xs text-text-muted">{ago} · CTA live feed</p>
      )}
    </section>
  );
}
