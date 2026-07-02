import { useEffect, useMemo, useRef, useState } from "react";
import type {
  StyleSpecification, ExpressionSpecification, FilterSpecification,
} from "maplibre-gl";
import maplibregl from "maplibre-gl";
import MapShell, { MapPanel } from "./MapShell";
import MapSearch, { type SearchEntry } from "./MapSearch";
import LiveArrivals, { type ArrStatus } from "./LiveArrivals";
import {
  HEX_RAMPS, HEX_LABELS, hexBinLabels, authorityLabel,
  ALL_ON, modeAuthorities, stopAuthorities, MODE_DASH, MODE_LABEL,
  type HexData, type HexMetric, type Route, type FilterState, type FilterKey,
} from "../lib/transit";
// Type-only import — erased at build, so no server fetch/normalizer code (or the
// CTA base URLs) is pulled into the client bundle. e4b consumes the *shape* only.
import type { LiveVehicle, LiveFeed } from "../lib/live";

// TransitMap — the reference consumer of MapShell. Owns the transit style, the
// agency/mode filters + route/stop search (e3b), the overlay control, legend and
// click popups; MapShell owns init/protocol/resize/error. Routes/stops layers &
// props (authority_id, mode, color) are e3a's tile schema.

type Overlay = "none" | HexMetric;

type Props = {
  pmtilesUrl: string;
  bbox: [number, number, number, number];
  hex: HexData;
  routes: Route[];
  metro?: string;
};

// ponytail: WebGL paint can't be Tailwind utilities, so these structural values
// mirror the dark-theme tokens (globals.css) as literals. Routes use their own
// GTFS `color` below — the three agency brand blues collide (globals.css note),
// so agency/mode is encoded by the FILTERS + a per-mode DASH (colorblind-safe),
// never by a guessed agency hex on the line.
const BG = "#0b0f14";
const STOP = "#2bb8cf";       // accent cyan
const HILITE = "#ffd479";     // warm highlight for search hits
const ROUTE_FALLBACK = "#8a94a3";
const FALSE_FILTER: FilterSpecification = ["==", ["literal", 0], ["literal", 1]];

const ROUTE_MODES = ["bus", "rail", "commuter-rail"] as const;
const routeLayerId = (m: string) => `routes-${m.replace("commuter-rail", "commuter")}`;

const hexFill = (metric: HexMetric, breaks: number[]): ExpressionSpecification => {
  const r = HEX_RAMPS[metric];
  return [
    "step", ["to-number", ["get", metric]],
    r[0], breaks[0], r[1], breaks[1], r[2], breaks[2], r[3], breaks[3], r[4],
  ];
};

const routeColor: ExpressionSpecification = [
  "case",
  ["all", ["has", "color"], ["!=", ["get", "color"], ""]],
  ["concat", "#", ["get", "color"]],
  ROUTE_FALLBACK,
];
const routeWidth: ExpressionSpecification =
  ["interpolate", ["linear"], ["zoom"], 6, 1, 12, 3];

// Authorities allowed for a mode → a tile filter. Empty ⇒ hide all.
const authFilter = (auths: string[]): FilterSpecification =>
  auths.length ? ["match", ["get", "authority_id"], auths, true, false] : FALSE_FILTER;

const routeFilter = (mode: string, auths: string[]): FilterSpecification =>
  ["all", ["==", ["get", "mode"], mode], authFilter(auths)] as FilterSpecification;

// ── Live vehicle layer (e4b) ─────────────────────────────────────────────────
// Polls the e4a server endpoint (/api/live/<metro>) — keys stay server-side. The
// default slice is all eight CTA 'L' lines (one ttpositions call). Positions are a
// GeoJSON source animated between polls; reduce-motion → plain position updates.
const LIVE_SRC = "live";
const LIVE_LAYER = "live-vehicles";
const L_LINES = "red,blue,brn,g,org,pink,p,y"; // Train Tracker tokens (see L_ROUTE_ID)
// CTA agency blue (globals.css --agency-cta #1743a6), lightened for contrast on the
// dark map (agency-color token per brief; shape below carries the colorblind cue).
const CTA_FILL = "#4f83e6";
const EMPTY_FC = { type: "FeatureCollection", features: [] } as const;
const MAX_TWEEN_MS = 20_000; // ease across ~the poll gap, capped so stalls don't crawl

const prefersReduce = (): boolean =>
  (typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) ||
  document.documentElement.getAttribute("data-motion") === "reduce";

// One small colored glyph per mode — shape is the colorblind-safe mode cue (rail =
// triangle pointing in travel direction via icon-rotate; bus = disc). White halo so
// it reads over route lines on the dark basemap. Drawn to a canvas → map.addImage.
function vehicleIcon(mode: "bus" | "rail"): ImageData {
  const S = 30;
  const c = document.createElement("canvas");
  c.width = c.height = S;
  const g = c.getContext("2d")!;
  g.translate(S / 2, S / 2);
  g.lineWidth = 3;
  g.lineJoin = "round";
  g.strokeStyle = "#ffffff";
  g.fillStyle = CTA_FILL;
  g.beginPath();
  if (mode === "rail") {
    const r = 11;
    g.moveTo(0, -r);
    g.lineTo(r * 0.86, r * 0.72);
    g.lineTo(-r * 0.86, r * 0.72);
    g.closePath();
  } else {
    g.arc(0, 0, 9, 0, Math.PI * 2);
  }
  g.fill();
  g.stroke();
  return g.getImageData(0, 0, S, S);
}

// A vehicle mid-tween: last target → new target over the poll interval.
type Veh = {
  fromLng: number; fromLat: number; toLng: number; toLat: number; t0: number;
  heading: number | null; route_id: string; mode: "bus" | "rail";
  destination: string | null; delayed: boolean;
};

const style = (pmtilesUrl: string, hex: HexData): StyleSpecification => ({
  version: 8,
  sources: {
    transit: {
      type: "vector",
      url: `pmtiles://${pmtilesUrl}`,
      attribution: "GTFS: CTA, Pace, Metra · Jobs: Census LODES · Population: Census 2020",
    },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": BG } },
    { id: "hex-jobs", type: "fill", source: "transit", "source-layer": "hex",
      layout: { visibility: "none" },
      paint: { "fill-color": hexFill("jobs", hex.breaks.jobs), "fill-opacity": 0.6 } },
    { id: "hex-population", type: "fill", source: "transit", "source-layer": "hex",
      layout: { visibility: "none" },
      paint: { "fill-color": hexFill("population", hex.breaks.population), "fill-opacity": 0.6 } },
    { id: "hex-access", type: "fill", source: "transit", "source-layer": "hex",
      layout: { visibility: "none" },
      paint: { "fill-color": hexFill("access", hex.breaks.access), "fill-opacity": 0.6 } },
    // One line layer per mode → distinct static dash (colorblind redundancy) and
    // trivial per-mode/agency filtering.
    ...ROUTE_MODES.map((m): StyleSpecification["layers"][number] => ({
      id: routeLayerId(m), type: "line", source: "transit", "source-layer": "routes",
      filter: routeFilter(m, [...modeAuthorities(ALL_ON)[m]]),
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        "line-color": routeColor,
        "line-width": routeWidth,
        "line-opacity": 0.9,
        ...(MODE_DASH[m].length ? { "line-dasharray": MODE_DASH[m] } : {}),
      },
    })),
    { id: "route-highlight", type: "line", source: "transit", "source-layer": "routes",
      filter: FALSE_FILTER,
      layout: { "line-join": "round", "line-cap": "round" },
      paint: { "line-color": HILITE, "line-width": ["interpolate", ["linear"], ["zoom"], 6, 4, 14, 8], "line-opacity": 0.55 } },
    { id: "stops", type: "circle", source: "transit", "source-layer": "stops",
      filter: authFilter(stopAuthorities(ALL_ON)),
      paint: {
        "circle-color": STOP,
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 1.5, 14, 4],
        "circle-stroke-color": BG, "circle-stroke-width": 0.5,
      } },
    { id: "stop-highlight", type: "circle", source: "transit", "source-layer": "stops",
      filter: FALSE_FILTER,
      paint: {
        "circle-color": HILITE, "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 5, 14, 8],
        "circle-stroke-color": BG, "circle-stroke-width": 1.5,
      } },
  ],
});

const LAYER: Record<HexMetric, string> = {
  jobs: "hex-jobs", population: "hex-population", access: "hex-access",
};

const esc = (s: unknown) => String(s ?? "").replace(/[<>&]/g, (c) => (
  { "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c] as string));

export default function TransitMap({ pmtilesUrl, bbox, hex, routes, metro }: Props) {
  const mapRef = useRef<maplibregl.Map | null>(null);
  const overlayRef = useRef<Overlay>("none");
  const [overlay, setOverlay] = useState<Overlay>("none");
  const [filters, setFilters] = useState<FilterState>(ALL_ON);
  const [stopEntries, setStopEntries] = useState<SearchEntry[]>([]);

  // ── Live state (e4b) ──────────────────────────────────────────────────────
  const slug = pmtilesUrl.replace(/^\//, "").split("/")[0] || "chicago";
  const [ready, setReady] = useState(false);        // map + live layer wired
  const [liveOn, setLiveOn] = useState(true);       // poll toggle (also saves quota)
  const [feed, setFeed] = useState<LiveFeed | null>(null);
  const [selectedStop, setSelectedStop] =
    useState<{ id: string; name: string; authority: string } | null>(null);
  const [arrStatus, setArrStatus] = useState<ArrStatus>("idle");
  const liveRef = useRef(new Map<string, Veh>());
  const rafRef = useRef<number | undefined>(undefined);
  const durRef = useRef(0);

  // Route → its GTFS color, for the arrival badges (CTA only; data, not a guess).
  const routeColorMap = useMemo(() => {
    const m = new Map<string, string>();
    for (const r of routes) if (r.color) m.set(`${r.authority_id}:${r.route_id}`, `#${r.color}`);
    return m;
  }, [routes]);

  // Build the GeoJSON at the current animation frame (linear tween per vehicle).
  const frameFC = () => {
    const now = performance.now();
    const features = [] as unknown[];
    for (const v of liveRef.current.values()) {
      const f = durRef.current > 0 ? Math.min(1, (now - v.t0) / durRef.current) : 1;
      features.push({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [v.fromLng + (v.toLng - v.fromLng) * f, v.fromLat + (v.toLat - v.fromLat) * f],
        },
        properties: {
          route_id: v.route_id, mode: v.mode, destination: v.destination,
          delayed: v.delayed, heading: v.heading ?? 0,
        },
      });
    }
    return { type: "FeatureCollection", features };
  };

  const tickAnim = () => {
    const src = mapRef.current?.getSource(LIVE_SRC) as maplibregl.GeoJSONSource | undefined;
    if (!src) { rafRef.current = undefined; return; }
    src.setData(frameFC() as never);
    const now = performance.now();
    const done = durRef.current <= 0 ||
      [...liveRef.current.values()].every((v) => now - v.t0 >= durRef.current);
    rafRef.current = done ? undefined : requestAnimationFrame(tickAnim);
  };

  const applyVehicles = (vehicles: LiveVehicle[], pollMs: number) => {
    const now = performance.now();
    durRef.current = prefersReduce() ? 0 : Math.min(pollMs, MAX_TWEEN_MS);
    const next = new Map<string, Veh>();
    for (const v of vehicles) {
      const prev = liveRef.current.get(v.vehicle_id);
      next.set(v.vehicle_id, {
        fromLng: prev ? prev.toLng : v.lon, fromLat: prev ? prev.toLat : v.lat,
        toLng: v.lon, toLat: v.lat, t0: now, heading: v.heading,
        route_id: v.route_id, mode: v.mode, destination: v.destination, delayed: v.delayed,
      });
    }
    liveRef.current = next;
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    tickAnim();
  };

  // Stop search index: fetched lazily from the served static stops.json (same
  // source as the tiles; sidesteps low-zoom point thinning + keeps the initial
  // HTML lean). Routes stay in the tiles/prop. No backend.
  useEffect(() => {
    const url = pmtilesUrl.replace(/transit\.pmtiles$/, "stops.json");
    let live = true;
    fetch(url)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((rows: { a: string; id: string; n: string; m: string; lng: number; lat: number }[]) => {
        if (!live) return;
        setStopEntries(rows.map((s) => ({
          kind: "stop", id: s.id, authority: s.a, label: s.n,
          sublabel: `${authorityLabel(s.a)} stop`, lngLat: [s.lng, s.lat],
        })));
      })
      .catch(() => { /* routes still searchable; table fallback carries stops */ });
    return () => { live = false; };
  }, [pmtilesUrl]);

  // Search index: routes come labelled from transit.json; stops from stops.json.
  const routeEntries = useMemo<SearchEntry[]>(() => routes.map((r) => ({
    kind: "route",
    id: r.route_id,
    authority: r.authority_id,
    label: [r.short_name, r.long_name].map((s) => s?.trim()).filter(Boolean).join(" — ") || r.route_id,
    sublabel: `${authorityLabel(r.authority_id)} · ${r.mode}`,
  })), [routes]);
  const entries = useMemo(() => [...routeEntries, ...stopEntries], [routeEntries, stopEntries]);

  const popupHTML = (title: string, sub: string) =>
    `<div style="color:#0b0f14;font:13px system-ui"><strong>${esc(title)}</strong><br>${esc(sub)}</div>`;

  const onReady = (map: maplibregl.Map) => {
    mapRef.current = map;

    // Hex click → exact values (only the visible overlay returns features).
    map.on("click", (e) => {
      const ov = overlayRef.current;
      if (ov === "none") return;
      const feats = map.queryRenderedFeatures(e.point, { layers: [LAYER[ov]] });
      if (!feats.length) return;
      const p = feats[0].properties as { jobs: number; population: number; access: number };
      new maplibregl.Popup({ closeButton: true }).setLngLat(e.lngLat).setHTML(
        `<div style="color:#0b0f14;font:13px system-ui"><strong>${HEX_LABELS[ov]}</strong><br>` +
        `Jobs: ${Number(p.jobs).toLocaleString()}<br>Population: ${Number(p.population).toLocaleString()}<br>` +
        `Jobs reachable (½-mi walk): ${Number(p.access).toLocaleString()}</div>`,
      ).addTo(map);
    });

    // Route / stop click popups + pointer cursor.
    map.on("click", "stops", (e) => {
      const p = e.features?.[0]?.properties as
        { name: string; authority_id: string; stop_id?: string } | undefined;
      if (!p) return;
      new maplibregl.Popup({ closeButton: true }).setLngLat(e.lngLat)
        .setHTML(popupHTML(p.name, `${authorityLabel(p.authority_id)} stop`)).addTo(map);
      // Also open the live next-arrivals panel for this stop.
      if (p.stop_id) setSelectedStop({ id: String(p.stop_id), name: p.name, authority: p.authority_id });
    });
    for (const m of ROUTE_MODES) {
      const id = routeLayerId(m);
      map.on("click", id, (e) => {
        const p = e.features?.[0]?.properties as
          { short_name?: string; long_name?: string; route_id: string; authority_id: string } | undefined;
        if (!p) return;
        const name = [p.short_name, p.long_name].filter(Boolean).join(" — ") || p.route_id;
        new maplibregl.Popup({ closeButton: true }).setLngLat(e.lngLat)
          .setHTML(popupHTML(name, `${authorityLabel(p.authority_id)} · ${MODE_LABEL[m] ?? m}`)).addTo(map);
      });
      map.on("mouseenter", id, () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", id, () => { map.getCanvas().style.cursor = ""; });
    }
    map.on("mouseenter", "stops", () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", "stops", () => { map.getCanvas().style.cursor = ""; });

    // Live vehicle layer: mode glyphs + an (initially empty) GeoJSON source + a
    // symbol layer. Icons are added post-load; the poll effect feeds setData.
    if (!map.hasImage("veh-rail")) map.addImage("veh-rail", vehicleIcon("rail"), { pixelRatio: 2 });
    if (!map.hasImage("veh-bus")) map.addImage("veh-bus", vehicleIcon("bus"), { pixelRatio: 2 });
    if (!map.getSource(LIVE_SRC)) map.addSource(LIVE_SRC, { type: "geojson", data: EMPTY_FC as never });
    if (!map.getLayer(LIVE_LAYER)) {
      map.addLayer({
        id: LIVE_LAYER, type: "symbol", source: LIVE_SRC,
        layout: {
          "icon-image": ["match", ["get", "mode"], "bus", "veh-bus", "veh-rail"],
          "icon-rotate": ["coalesce", ["get", "heading"], 0],
          "icon-rotation-alignment": "map",
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
          "icon-size": ["interpolate", ["linear"], ["zoom"], 8, 0.5, 14, 1],
        },
      });
    }
    map.on("click", LIVE_LAYER, (e) => {
      const p = e.features?.[0]?.properties as
        { route_id: string; destination?: string; delayed?: unknown; mode: string } | undefined;
      if (!p) return;
      const title = [p.route_id, p.destination].filter(Boolean).join(" → ");
      const dly = p.delayed === true || p.delayed === "true";
      const sub = `CTA ${p.mode === "bus" ? "bus" : "‘L’ train"}${dly ? " · delayed" : ""} · live`;
      new maplibregl.Popup({ closeButton: true }).setLngLat(e.lngLat).setHTML(popupHTML(title, sub)).addTo(map);
    });
    map.on("mouseenter", LIVE_LAYER, () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", LIVE_LAYER, () => { map.getCanvas().style.cursor = ""; });

    setReady(true);
  };

  // Apply agency/mode filters to the per-mode route layers + the stops layer.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const byMode = modeAuthorities(filters);
      for (const m of ROUTE_MODES) map.setFilter(routeLayerId(m), routeFilter(m, byMode[m]));
      map.setFilter("stops", authFilter(stopAuthorities(filters)));
    };
    map.isStyleLoaded() ? apply() : map.once("load", apply);
  }, [filters]);

  // Overlay radio → hex visibility.
  useEffect(() => {
    overlayRef.current = overlay;
    const map = mapRef.current;
    if (!map) return;
    const apply = () => (["jobs", "population", "access"] as HexMetric[]).forEach((m) =>
      map.setLayoutProperty(LAYER[m], "visibility", overlay === m ? "visible" : "none"));
    map.isStyleLoaded() ? apply() : map.once("load", apply);
  }, [overlay]);

  // Live poll (e4b): one interval hitting the e4a server endpoint. Requests all L
  // lines (positions) plus — when a CTA stop is picked — that stop's arrivals in the
  // SAME call (bus_stops + stations; the endpoint returns whichever id matches).
  // Never calls CTA directly; polls no faster than the endpoint's x-poll-ms hint.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    if (!liveOn) {
      liveRef.current = new Map();
      (map.getSource(LIVE_SRC) as maplibregl.GeoJSONSource | undefined)?.setData(EMPTY_FC as never);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      setFeed(null); setArrStatus("idle");
      return;
    }
    const params = new URLSearchParams({ lines: L_LINES });
    const stopIsCta = selectedStop?.authority === "cta";
    if (stopIsCta && selectedStop) {
      params.set("bus_stops", selectedStop.id);
      params.set("stations", selectedStop.id);
      setArrStatus("loading");
    } else {
      setArrStatus("idle");
    }
    const url = `/api/live/${slug}?${params.toString()}`;

    let alive = true;
    let timer: number | undefined;
    const tick = async () => {
      try {
        const res = await fetch(url);
        const pollMs = Number(res.headers.get("x-poll-ms")) || 30_000;
        const data = (await res.json()) as LiveFeed;
        if (!alive) return;
        applyVehicles(data.vehicles, pollMs);
        setFeed(data);
        if (stopIsCta) {
          setArrStatus(data.errors.length && data.arrivals.length === 0 ? "error" : "ok");
        }
        timer = window.setTimeout(tick, pollMs);
      } catch {
        if (!alive) return;
        if (stopIsCta) setArrStatus("error");
        timer = window.setTimeout(tick, 30_000);
      }
    };
    tick();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, liveOn, selectedStop]);

  const onSelect = (e: SearchEntry) => {
    const map = mapRef.current;
    if (!map) return;
    if (e.kind === "stop" && e.lngLat) {
      map.setFilter("route-highlight", FALSE_FILTER);
      map.setFilter("stop-highlight",
        ["all", ["==", ["get", "stop_id"], e.id], ["==", ["get", "authority_id"], e.authority]]);
      map.flyTo({ center: e.lngLat, zoom: 14 });
      new maplibregl.Popup({ closeButton: true }).setLngLat(e.lngLat)
        .setHTML(popupHTML(e.label, e.sublabel ?? "")).addTo(map);
      setSelectedStop({ id: e.id, name: e.label, authority: e.authority });
      return;
    }
    setSelectedStop(null); // route pick clears any open arrivals panel
    // Route: highlight + fit to its geometry (gathered from the loaded tiles).
    const f: FilterSpecification =
      ["all", ["==", ["get", "route_id"], e.id], ["==", ["get", "authority_id"], e.authority]];
    map.setFilter("stop-highlight", FALSE_FILTER);
    map.setFilter("route-highlight", f);
    const feats = map.querySourceFeatures("transit", { sourceLayer: "routes", filter: f });
    const b = new maplibregl.LngLatBounds();
    let any = false;
    for (const ft of feats) {
      const g = ft.geometry;
      const lines = g.type === "LineString" ? [g.coordinates]
        : g.type === "MultiLineString" ? g.coordinates : [];
      for (const ln of lines) for (const c of ln) { b.extend(c as [number, number]); any = true; }
    }
    if (any) map.fitBounds(b, { padding: 60, maxZoom: 13 });
  };

  const activeBreaks = overlay === "none" ? null : hex.breaks[overlay];
  const labels = activeBreaks ? hexBinLabels(activeBreaks) : [];

  const FILTER_ROWS: [FilterKey, string][] = [
    ["ctaBus", "CTA bus"], ["ctaRail", "CTA rail"], ["metra", "Metra"], ["pace", "Pace"],
  ];

  return (
    <MapShell
      buildStyle={() => style(pmtilesUrl, hex)}
      bbox={bbox}
      ariaLabel={`Interactive map of ${metro ?? "transit"} routes and stops with a population and jobs overlay`}
      onReady={onReady}
      errorMessage="The map failed to load. The route and area tables below have the same data."
    >
      <MapPanel label="Map controls" className="w-72 max-w-[86%]">
        <details open className="[&_summary]:list-none">
          <summary className="mb-2 flex cursor-pointer items-center justify-between font-medium text-text">
            <span>Map controls</span>
            <span aria-hidden="true" className="text-text-muted">▾</span>
          </summary>
          <div className="max-h-[62vh] space-y-3 overflow-y-auto pr-1">
            <MapSearch entries={entries} onSelect={onSelect} />

            <fieldset className="border-t border-hairline pt-2">
              <legend className="font-medium text-text">Agencies &amp; modes</legend>
              <div className="mt-1 flex flex-col">
                {FILTER_ROWS.map(([key, label]) => (
                  <label key={key} className="flex cursor-pointer items-center gap-2 py-1">
                    <input
                      type="checkbox"
                      checked={filters[key]}
                      onChange={(ev) => setFilters((f) => ({ ...f, [key]: ev.target.checked }))}
                      className="h-4 w-4 accent-[var(--accent)]"
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <fieldset className="border-t border-hairline pt-2">
              <legend className="font-medium text-text">Overlay</legend>
              <div className="mt-1 flex flex-col">
                {([["none", "None"], ["jobs", HEX_LABELS.jobs], ["population", HEX_LABELS.population],
                   ["access", HEX_LABELS.access]] as [Overlay, string][]).map(([val, label]) => (
                  <label key={val} className="flex cursor-pointer items-center gap-2 py-1">
                    <input type="radio" name="map-overlay" value={val} checked={overlay === val}
                      onChange={() => setOverlay(val)} className="h-4 w-4 accent-[var(--accent)]" />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <fieldset className="border-t border-hairline pt-2">
              <legend className="font-medium text-text">Live</legend>
              <label className="mt-1 flex cursor-pointer items-center gap-2 py-1">
                <input
                  type="checkbox"
                  checked={liveOn}
                  onChange={(ev) => setLiveOn(ev.target.checked)}
                  className="h-4 w-4 accent-[var(--accent)]"
                />
                <span>Live CTA ‘L’ trains</span>
              </label>
              {liveOn && feed?.errors.some((e) => e.includes("credentials_missing")) && (
                <p className="text-xs text-text-muted">
                  Live feed isn’t configured in this environment.
                </p>
              )}
              <p className="text-xs text-text-muted">
                Positions from the CTA Train Tracker, refreshed live. Click a stop for
                next arrivals.
              </p>
            </fieldset>

            {/* Legend — mode is encoded by line shape (dash), never color alone. */}
            <div className="border-t border-hairline pt-2">
              <p className="font-medium text-text">Legend</p>
              <ul className="mt-1 space-y-1" aria-label="Map legend">
                {ROUTE_MODES.map((m) => (
                  <li key={m} className="flex items-center gap-2">
                    <svg width="20" height="6" aria-hidden="true" className="shrink-0">
                      <line x1="0" y1="3" x2="20" y2="3" stroke="currentColor" strokeWidth="2"
                        strokeDasharray={MODE_DASH[m].length ? MODE_DASH[m].map((n) => n * 2).join(" ") : undefined} />
                    </svg>
                    <span>{MODE_LABEL[m]}</span>
                  </li>
                ))}
                <li className="flex items-center gap-2">
                  <span aria-hidden="true" className="inline-block h-2 w-2 rounded-full" style={{ background: STOP }} />
                  <span>Stop</span>
                </li>
                <li className="flex items-center gap-2">
                  <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" className="shrink-0">
                    <path d="M7 1 L12.5 12 L1.5 12 Z" fill={CTA_FILL} stroke="#fff" strokeWidth="1.5" strokeLinejoin="round" />
                  </svg>
                  <span>Live vehicle (points in travel direction)</span>
                </li>
              </ul>
              <p className="mt-1 text-text-muted">Line color = each route’s own color.</p>
            </div>

            {activeBreaks && (
              <ul className="border-t border-hairline pt-2" aria-label={`${HEX_LABELS[overlay as HexMetric]} legend (per hex cell)`}>
                {labels.map((lab, i) => (
                  <li key={lab} className="flex items-center gap-2">
                    <span aria-hidden="true" className="inline-block h-3 w-3 rounded-sm border border-hairline/50"
                      style={{ background: HEX_RAMPS[overlay as HexMetric][i] }} />
                    <span className="tabular">{lab}</span>
                  </li>
                ))}
                <li className="mt-1 text-text-muted">per hex cell · click a cell for exact values</li>
              </ul>
            )}
          </div>
        </details>
      </MapPanel>

      {selectedStop && (
        <MapPanel label="Live arrivals" className="left-auto right-2 top-auto bottom-8 w-64 max-w-[70%]">
          <LiveArrivals
            stop={selectedStop}
            arrivals={feed?.arrivals ?? []}
            status={arrStatus}
            errors={feed?.errors ?? []}
            generated={feed?.generated ?? null}
            colorFor={(rid) => routeColorMap.get(`cta:${rid}`) ?? null}
            onClose={() => setSelectedStop(null)}
          />
        </MapPanel>
      )}
    </MapShell>
  );
}
