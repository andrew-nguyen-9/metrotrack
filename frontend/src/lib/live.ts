// Live CTA feed — server-side fetch + normalize (e4a). Keys stay server-side;
// this module is imported ONLY by the API endpoint (src/pages/api/live/[metro].ts),
// never shipped to the browser bundle. e4b consumes the *normalized* shape below
// (fetched from that endpoint); e11 samples the same shape for delay/crowding.
//
// Sources (docs/architecture/DATA_SOURCES.md → "GTFS-realtime (CTA Bus/Train Tracker)"):
//   Bus Tracker (BusTime v2)  https://www.ctabustime.com/bustime/api/v2  — key CTA_BUS_TRACKER_API
//   Train Tracker             https://lapi.transitchicago.com/api/1.0    — key CTA_TRAIN_TRACKER_API
// Both are free tier with daily call caps → the endpoint caches; see CACHE_TTL_MS.

export const BUS_BASE = "https://www.ctabustime.com/bustime/api/v2";
export const TRAIN_BASE = "https://lapi.transitchicago.com/api/1.0";

// ponytail: free-tier daily caps (~10k). Server caches each upstream response this
// long; clients should poll no faster than POLL_MS. Raising cadence risks a ban.
export const CACHE_TTL_MS = 15_000;
export const POLL_MS = 30_000;

// Train Tracker line tokens → CTA GTFS route_id (joins e3a gold_routes.route_id,
// authority_id='cta', mode='rail'). Tracker uses lowercase tokens; GTFS uses these.
export const L_ROUTE_ID: Record<string, string> = {
  red: "Red", blue: "Blue", brn: "Brn", g: "G",
  org: "Org", pink: "Pink", p: "P", y: "Y",
};

// ── Normalized schema (the e4b / e11 contract) ───────────────────────────────
export type LiveVehicle = {
  authority: "cta";
  mode: "bus" | "rail";
  route_id: string;       // joins gold_routes.route_id (authority_id='cta')
  vehicle_id: string;
  lat: number;
  lon: number;
  heading: number | null;
  destination: string | null;
  delayed: boolean;
  source_ts: string | null; // upstream timestamp, as reported (Chicago local)
};

export type LiveArrival = {
  authority: "cta";
  mode: "bus" | "rail";
  stop_id: string;        // joins gold_stops.stop_id (authority_id='cta')
  stop_name: string | null;
  route_id: string;       // joins gold_routes.route_id
  vehicle_id: string | null;
  destination: string | null;
  direction: string | null;
  arrival_local: string | null; // "yyyy-MM-ddTHH:mm:ss" Chicago local (no tz)
  countdown_min: number | null; // minutes to arrival; 0 = DUE
  arrival_type: "A" | "D" | null; // bus: Arrival vs Departure prediction
  delayed: boolean;
};

export type LiveFeed = {
  metro: string;
  generated: string;      // ISO8601 UTC — when this response was assembled
  vehicles: LiveVehicle[];
  arrivals: LiveArrival[];
  errors: string[];       // upstream/credential/rate-limit notes (never throws)
};

// "yyyyMMdd HH:mm[:ss]" (CTA local) → "yyyy-MM-ddTHH:mm:ss". Timezone-naive by
// design: both feeds report Chicago local, and countdowns are same-tz differences.
function ctaTimeToLocalIso(t: string | undefined | null): string | null {
  if (!t) return null;
  const m = t.match(/^(\d{4})(\d{2})(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?$/);
  if (!m) return null;
  const [, y, mo, d, h, mi, s] = m;
  return `${y}-${mo}-${d}T${h}:${mi}:${s ?? "00"}`;
}

function minutesBetween(fromIso: string | null, toIso: string | null): number | null {
  if (!fromIso || !toIso) return null;
  const a = Date.parse(fromIso), b = Date.parse(toIso);
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.max(0, Math.round((b - a) / 60_000));
}

function num(v: unknown): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

// ── Pure normalizers (unit-testable, no network) ─────────────────────────────

/** BusTime getvehicles `{"bustime-response":{"vehicle":[...]}}` → LiveVehicle[]. */
export function normalizeBusVehicles(payload: any): LiveVehicle[] {
  const list = payload?.["bustime-response"]?.vehicle ?? [];
  const out: LiveVehicle[] = [];
  for (const v of list) {
    const lat = num(v?.lat), lon = num(v?.lon);
    if (lat === null || lon === null || !v?.rt) continue;
    out.push({
      authority: "cta", mode: "bus",
      route_id: String(v.rt),
      vehicle_id: String(v.vid ?? ""),
      lat, lon,
      heading: num(v?.hdg),
      destination: v?.des ?? null,
      delayed: v?.dly === true || v?.dly === "true",
      source_ts: ctaTimeToLocalIso(v?.tmstmp),
    });
  }
  return out;
}

/** BusTime getpredictions `{"bustime-response":{"prd":[...]}}` → LiveArrival[]. */
export function normalizeBusPredictions(payload: any): LiveArrival[] {
  const list = payload?.["bustime-response"]?.prd ?? [];
  const out: LiveArrival[] = [];
  for (const p of list) {
    if (!p?.stpid || !p?.rt) continue;
    const cd = String(p?.prdctdn ?? "").toUpperCase();
    const countdown = cd === "DUE" ? 0 : cd === "DLY" ? null : num(cd);
    out.push({
      authority: "cta", mode: "bus",
      stop_id: String(p.stpid),
      stop_name: p?.stpnm ?? null,
      route_id: String(p.rt),
      vehicle_id: p?.vid ? String(p.vid) : null,
      destination: p?.des ?? null,
      direction: p?.rtdir ?? null,
      arrival_local: ctaTimeToLocalIso(p?.prdtm),
      countdown_min: countdown,
      arrival_type: p?.typ === "A" ? "A" : p?.typ === "D" ? "D" : null,
      delayed: p?.dly === true || p?.dly === "true",
    });
  }
  return out;
}

/** Train Tracker ttpositions `{"ctatt":{"route":[{"@name","train":[...]}]}}`. */
export function normalizeTrainPositions(payload: any): LiveVehicle[] {
  const routes = payload?.ctatt?.route ?? [];
  const out: LiveVehicle[] = [];
  for (const r of routes) {
    const routeId = L_ROUTE_ID[String(r?.["@name"]).toLowerCase()] ?? String(r?.["@name"] ?? "");
    for (const t of r?.train ?? []) {
      const lat = num(t?.lat), lon = num(t?.lon);
      if (lat === null || lon === null) continue;
      out.push({
        authority: "cta", mode: "rail",
        route_id: routeId,
        vehicle_id: String(t?.rn ?? ""),
        lat, lon,
        heading: num(t?.heading),
        destination: t?.destNm ?? null,
        delayed: t?.isDly === "1" || t?.isDly === 1,
        source_ts: ctaTimeToLocalIso(t?.prdt),
      });
    }
  }
  return out;
}

/** Train Tracker ttarrivals `{"ctatt":{"eta":[...]}}` → LiveArrival[]. */
export function normalizeTrainArrivals(payload: any): LiveArrival[] {
  const list = payload?.ctatt?.eta ?? [];
  const out: LiveArrival[] = [];
  for (const e of list) {
    if (!e?.stpId) continue;
    const routeId = L_ROUTE_ID[String(e?.rt).toLowerCase()] ?? String(e?.rt ?? "");
    const prdt = ctaTimeToLocalIso(e?.prdt);
    const arrT = ctaTimeToLocalIso(e?.arrT);
    out.push({
      authority: "cta", mode: "rail",
      stop_id: String(e.stpId),
      stop_name: e?.staNm ?? null,
      route_id: routeId,
      vehicle_id: e?.rn ? String(e.rn) : null,
      destination: e?.destNm ?? null,
      direction: e?.trDr ?? null,
      arrival_local: arrT,
      countdown_min: e?.isApp === "1" ? 0 : minutesBetween(prdt, arrT),
      arrival_type: null,
      delayed: e?.isDly === "1" || e?.isDly === 1,
    });
  }
  return out;
}

// ── Server-side fetch orchestration ──────────────────────────────────────────
export type LiveParams = {
  busRoutes: string[];  // getvehicles rt= (positions)
  busStops: string[];   // getpredictions stpid= (arrivals)
  lines: string[];      // ttpositions rt= (positions)
  stations: string[];   // ttarrivals mapid= (arrivals)
};

export type LiveKeys = { bus?: string; train?: string };

async function getJson(url: string, errors: string[]): Promise<any | null> {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(8_000) });
    if (!res.ok) { errors.push(`upstream ${res.status}`); return null; }
    return await res.json();
  } catch (e) {
    errors.push(`fetch failed: ${(e as Error).message}`);
    return null;
  }
}

/** Fetch + normalize the requested slice. Never throws — degrades into `errors`. */
export async function fetchLive(
  metro: string, keys: LiveKeys, params: LiveParams,
): Promise<LiveFeed> {
  const errors: string[] = [];
  const vehicles: LiveVehicle[] = [];
  const arrivals: LiveArrival[] = [];
  const jobs: Promise<void>[] = [];

  const wantBus = params.busRoutes.length || params.busStops.length;
  const wantTrain = params.lines.length || params.stations.length;

  if (wantBus && !keys.bus) errors.push("credentials_missing: CTA_BUS_TRACKER_API");
  if (wantTrain && !keys.train) errors.push("credentials_missing: CTA_TRAIN_TRACKER_API");

  if (keys.bus && params.busRoutes.length) {
    // getvehicles rt caps at 10 routes/call.
    const rt = params.busRoutes.slice(0, 10).join(",");
    const url = `${BUS_BASE}/getvehicles?key=${keys.bus}&rt=${encodeURIComponent(rt)}&tmres=s&format=json`;
    jobs.push(getJson(url, errors).then((j) => { if (j) vehicles.push(...normalizeBusVehicles(j)); }));
  }
  if (keys.bus && params.busStops.length) {
    const stp = params.busStops.slice(0, 10).join(",");
    const url = `${BUS_BASE}/getpredictions?key=${keys.bus}&stpid=${encodeURIComponent(stp)}&format=json`;
    jobs.push(getJson(url, errors).then((j) => { if (j) arrivals.push(...normalizeBusPredictions(j)); }));
  }
  if (keys.train && params.lines.length) {
    const rt = params.lines.join(",");
    const url = `${TRAIN_BASE}/ttpositions.aspx?key=${keys.train}&rt=${encodeURIComponent(rt)}&outputType=JSON`;
    jobs.push(getJson(url, errors).then((j) => { if (j) vehicles.push(...normalizeTrainPositions(j)); }));
  }
  if (keys.train && params.stations.length) {
    for (const mapid of params.stations.slice(0, 4)) {
      const url = `${TRAIN_BASE}/ttarrivals.aspx?key=${keys.train}&mapid=${encodeURIComponent(mapid)}&outputType=JSON`;
      jobs.push(getJson(url, errors).then((j) => { if (j) arrivals.push(...normalizeTrainArrivals(j)); }));
    }
  }

  await Promise.all(jobs);
  return { metro, generated: new Date().toISOString(), vehicles, arrivals, errors };
}
