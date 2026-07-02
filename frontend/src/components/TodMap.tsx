import { useRef } from "react";
import type { StyleSpecification, ExpressionSpecification } from "maplibre-gl";
import maplibregl from "maplibre-gl";
import MapShell, { MapPanel } from "./MapShell";
import { hexBinLabels } from "../lib/transit";
import type { Cbd } from "../lib/tod";

// TodMap — the transit-oriented-development map: every hex shaded by best-case
// minutes to its nearest configured CBD, with the CBD anchor(s) marked. Reuses
// MapShell (init/protocol/resize/error); this file owns only the TOD style +
// the CBD markers + the click popup. Multi-CBD-ready: it drops a marker per anchor.

type Props = {
  pmtilesUrl: string;
  bbox: [number, number, number, number];
  breaks: number[];        // 4 quantile thresholds on min_to_cbd (transit.json hex.breaks.cbd_time)
  cbds: Cbd[];
  metro?: string;
};

const BG = "#0b0f14";
// Sequential ramp low→high minutes: closest to a CBD is brightest, fading with
// distance. Color is never the only signal (legend ranges + click popup values).
const RAMP: [string, string, string, string, string] =
  ["#9fdcf0", "#52b0db", "#2a86c0", "#1f6091", "#15324a"];
const ACCENT = "#2bb8cf";

const timeFill = (breaks: number[]): ExpressionSpecification => [
  "step", ["to-number", ["get", "cbd_min"]],
  RAMP[0],
  breaks[0], RAMP[1],
  breaks[1], RAMP[2],
  breaks[2], RAMP[3],
  breaks[3], RAMP[4],
];

const style = (pmtilesUrl: string, breaks: number[]): StyleSpecification => ({
  version: 8,
  sources: {
    transit: {
      type: "vector",
      url: `pmtiles://${pmtilesUrl}`,
      attribution: "Jobs: Census LODES · Population: Census · Time-to-CBD: straight-line",
    },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": BG } },
    {
      id: "hex-cbd", type: "fill", source: "transit", "source-layer": "hex",
      paint: { "fill-color": timeFill(breaks), "fill-opacity": 0.62 },
    },
    {
      id: "hex-cbd-line", type: "line", source: "transit", "source-layer": "hex",
      paint: { "line-color": BG, "line-width": 0.3, "line-opacity": 0.4 },
    },
  ],
});

export default function TodMap({ pmtilesUrl, bbox, breaks, cbds, metro }: Props) {
  const mapRef = useRef<maplibregl.Map | null>(null);
  const labels = hexBinLabels(breaks).map((l) => `${l} min`);

  const onReady = (map: maplibregl.Map) => {
    mapRef.current = map;
    // A marker per CBD anchor (data-driven: N per metro).
    for (const c of cbds) {
      new maplibregl.Marker({ color: ACCENT })
        .setLngLat([c.lon, c.lat])
        .setPopup(new maplibregl.Popup({ closeButton: false }).setHTML(
          `<div style="color:#0b0f14;font:13px system-ui"><strong>${c.name}</strong><br>Central business district</div>`,
        ))
        .addTo(map);
    }
    // Click a hex → exact minutes + density.
    map.on("click", (e) => {
      const feats = map.queryRenderedFeatures(e.point, { layers: ["hex-cbd"] });
      if (!feats.length) return;
      const p = feats[0].properties as { cbd_min: number; jobs: number; population: number };
      new maplibregl.Popup({ closeButton: true })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div style="color:#0b0f14;font:13px system-ui">` +
          `<strong>Time to nearest CBD</strong><br>` +
          `~${Number(p.cbd_min).toLocaleString()} min (best-case, straight-line)<br>` +
          `Jobs: ${Number(p.jobs).toLocaleString()}<br>` +
          `Population: ${Number(p.population).toLocaleString()}</div>`,
        )
        .addTo(map);
    });
  };

  return (
    <MapShell
      buildStyle={() => style(pmtilesUrl, breaks)}
      bbox={bbox}
      ariaLabel={`Map of ${metro ?? "the metro"} shaded by best-case straight-line minutes to the nearest central business district`}
      onReady={onReady}
      errorMessage="The map failed to load. The distance-band table below has the same data."
    >
      <MapPanel label="Time to nearest CBD">
        <p className="font-medium text-text">Minutes to nearest CBD</p>
        <ul className="mt-2 border-t border-hairline pt-2" aria-label="Minutes to nearest CBD legend (per hex cell)">
          {labels.map((lab, i) => (
            <li key={lab} className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className="inline-block h-3 w-3 rounded-sm border border-hairline/50"
                style={{ background: RAMP[i] }}
              />
              <span className="tabular">{lab}</span>
            </li>
          ))}
          <li className="mt-1 flex items-center gap-2 text-text-muted">
            <span aria-hidden="true" className="inline-block h-3 w-3 rounded-full" style={{ background: ACCENT }} />
            CBD anchor · click a cell for exact values
          </li>
        </ul>
      </MapPanel>
    </MapShell>
  );
}
