import { useEffect, useRef, useState } from "react";
import maplibregl, { type StyleSpecification, type ExpressionSpecification } from "maplibre-gl";
import { Protocol } from "pmtiles";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  HEX_RAMPS, HEX_LABELS, hexBinLabels,
  type HexData, type HexMetric,
} from "../lib/transit";

type Overlay = "none" | HexMetric;

type Props = {
  pmtilesUrl: string;
  bbox: [number, number, number, number];
  hex: HexData;
  // Metro name for the accessible label; data + bbox are the only per-metro inputs.
  metro?: string;
};

// ponytail: structural map paint mirrors the dark-theme tokens (globals.css).
// MapLibre WebGL paint can't be Tailwind utilities, so these few values are
// literals here. Routes use their own GTFS color below, never a guessed agency hex.
const BG = "#0b0f14";
const STOP = "#2bb8cf"; // accent cyan
const ROUTE_FALLBACK = "#8a94a3";

// Choropleth step: v < b0 → ramp0 … ≥ b3 → ramp4 (matches hexBinLabels).
const hexFill = (metric: HexMetric, breaks: number[]): ExpressionSpecification => {
  const r = HEX_RAMPS[metric];
  return [
    "step", ["to-number", ["get", metric]],
    r[0],
    breaks[0], r[1],
    breaks[1], r[2],
    breaks[2], r[3],
    breaks[3], r[4],
  ];
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
    // Hex choropleths sit BELOW routes/stops so the network stays readable on top.
    // Both start hidden; the overlay radio toggles exactly one on.
    {
      id: "hex-jobs", type: "fill", source: "transit", "source-layer": "hex",
      layout: { visibility: "none" },
      paint: { "fill-color": hexFill("jobs", hex.breaks.jobs), "fill-opacity": 0.6 },
    },
    {
      id: "hex-population", type: "fill", source: "transit", "source-layer": "hex",
      layout: { visibility: "none" },
      paint: { "fill-color": hexFill("population", hex.breaks.population), "fill-opacity": 0.6 },
    },
    {
      id: "hex-access", type: "fill", source: "transit", "source-layer": "hex",
      layout: { visibility: "none" },
      paint: { "fill-color": hexFill("access", hex.breaks.access), "fill-opacity": 0.6 },
    },
    {
      id: "routes", type: "line", source: "transit", "source-layer": "routes",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        "line-color": [
          "case",
          ["all", ["has", "color"], ["!=", ["get", "color"], ""]],
          ["concat", "#", ["get", "color"]],
          ROUTE_FALLBACK,
        ],
        "line-width": ["interpolate", ["linear"], ["zoom"], 6, 1, 12, 3],
        "line-opacity": 0.9,
      },
    },
    {
      id: "stops", type: "circle", source: "transit", "source-layer": "stops",
      paint: {
        "circle-color": STOP,
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 1.5, 14, 4],
        "circle-stroke-color": BG,
        "circle-stroke-width": 0.5,
      },
    },
  ],
});

const LAYER: Record<HexMetric, string> = {
  jobs: "hex-jobs", population: "hex-population", access: "hex-access",
};

export default function TransitMap({ pmtilesUrl, bbox, hex, metro }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const overlayRef = useRef<Overlay>("none");
  const [overlay, setOverlay] = useState<Overlay>("none");
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const protocol = new Protocol();
    maplibregl.addProtocol("pmtiles", protocol.tile);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const map = new maplibregl.Map({
      container: ref.current,
      style: style(pmtilesUrl, hex),
      bounds: bbox,
      fitBoundsOptions: { padding: 24, animate: false },
      attributionControl: { compact: true },
      dragRotate: false,
      ...(reduce ? { fadeDuration: 0 } : {}),
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("error", (e) => {
      console.error("[map]", e.error?.message ?? e);
      setError(true);
    });

    // Click a hex (only the visible overlay returns features) → exact values popup.
    map.on("click", (e) => {
      const ov = overlayRef.current;
      if (ov === "none") return;
      const feats = map.queryRenderedFeatures(e.point, { layers: [LAYER[ov]] });
      if (!feats.length) return;
      const p = feats[0].properties as { jobs: number; population: number; access: number };
      new maplibregl.Popup({ closeButton: true })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div style="color:#0b0f14;font:13px system-ui">` +
          `<strong>${HEX_LABELS[ov]}</strong><br>` +
          `Jobs: ${Number(p.jobs).toLocaleString()}<br>` +
          `Population: ${Number(p.population).toLocaleString()}<br>` +
          `Jobs reachable (½-mi walk): ${Number(p.access).toLocaleString()}</div>`,
        )
        .addTo(map);
    });

    // Refit on container resize until the user takes over the camera.
    let userMoved = false;
    map.on("dragstart", () => { userMoved = true; });
    map.on("zoomstart", (ev) => { if (ev.originalEvent) userMoved = true; });
    const ro = new ResizeObserver(() => {
      map.resize();
      if (!userMoved) map.fitBounds(bbox, { padding: 24, animate: false });
    });
    ro.observe(ref.current);

    return () => {
      ro.disconnect();
      map.remove();
      mapRef.current = null;
      maplibregl.removeProtocol("pmtiles");
    };
  }, [pmtilesUrl, bbox, hex]);

  // Toggle overlay visibility when the radio changes.
  useEffect(() => {
    overlayRef.current = overlay;
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      (["jobs", "population", "access"] as HexMetric[]).forEach((m) =>
        map.setLayoutProperty(LAYER[m], "visibility", overlay === m ? "visible" : "none"));
    };
    map.isStyleLoaded() ? apply() : map.once("load", apply);
  }, [overlay]);

  const activeBreaks = overlay === "none" ? null : hex.breaks[overlay];
  const labels = activeBreaks ? hexBinLabels(activeBreaks) : [];

  return (
    <div className="relative h-full w-full">
      <div
        ref={ref}
        role="application"
        aria-label={`Interactive map of ${metro ?? "transit"} routes and stops with a population and jobs overlay`}
        className="h-full w-full"
      />

      {/* Overlay controls + legend. Native radios = keyboard + screen-reader access. */}
      <div className="absolute left-2 top-2 max-w-[68%] rounded-md border border-hairline bg-[#0b0f14]/90 p-3 text-xs text-text shadow-lg backdrop-blur-sm">
        <fieldset>
          <legend className="font-medium text-text">Overlay</legend>
          <div className="mt-1 flex flex-col">
            {([
              ["none", "None"],
              ["jobs", HEX_LABELS.jobs],
              ["population", HEX_LABELS.population],
              ["access", HEX_LABELS.access],
            ] as [Overlay, string][]).map(([val, label]) => (
              <label key={val} className="flex cursor-pointer items-center gap-2 py-1.5">
                <input
                  type="radio"
                  name="map-overlay"
                  value={val}
                  checked={overlay === val}
                  onChange={() => setOverlay(val)}
                  className="h-4 w-4 accent-[#2bb8cf]"
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        {activeBreaks && (
          <ul className="mt-2 border-t border-hairline pt-2" aria-label={`${HEX_LABELS[overlay as HexMetric]} legend (per hex cell)`}>
            {labels.map((lab, i) => (
              <li key={lab} className="flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="inline-block h-3 w-3 rounded-sm border border-hairline/50"
                  style={{ background: HEX_RAMPS[overlay as HexMetric][i] }}
                />
                <span className="tabular">{lab}</span>
              </li>
            ))}
            <li className="mt-1 text-text-muted">per hex cell · click a cell for exact values</li>
          </ul>
        )}
      </div>

      {error && (
        <p role="alert" className="absolute inset-x-0 bottom-0 bg-surface/90 p-2 text-center text-sm text-text-muted">
          The map failed to load. The route and area tables below have the same data.
        </p>
      )}
    </div>
  );
}
