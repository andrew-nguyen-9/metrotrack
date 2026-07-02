import { useRef } from "react";
import type { StyleSpecification, ExpressionSpecification } from "maplibre-gl";
import maplibregl from "maplibre-gl";
import MapShell, { MapPanel } from "./MapShell";
import { HEX_RAMPS, hexBinLabels, type HexData } from "../lib/transit";

// AccessMap — the job-access page's focused H3 choropleth: one layer, the
// job-access score (jobs reachable within a ½-mi walk) per hex cell. Reuses the
// shared MapShell (protocol/init/resize/error) and the same access ramp + breaks
// the map page uses, so the two surfaces read identically. Not color-only: the
// legend prints exact numeric ranges, a click reveals a cell's values, and the
// page carries a no-JS table with the same scores.

const BG = "#0b0f14";

const accessFill = (breaks: number[]): ExpressionSpecification => {
  const r = HEX_RAMPS.access;
  return [
    "step", ["to-number", ["get", "access"]],
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
      attribution: "Jobs: Census LODES · ½-mi straight-line walkshed",
    },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": BG } },
    {
      id: "hex-access", type: "fill", source: "transit", "source-layer": "hex",
      paint: {
        "fill-color": accessFill(hex.breaks.access),
        "fill-opacity": 0.72,
        "fill-outline-color": "rgba(11,15,20,0.35)",
      },
    },
  ],
});

type Props = {
  pmtilesUrl: string;
  bbox: [number, number, number, number];
  hex: HexData;
  metro?: string;
};

export default function AccessMap({ pmtilesUrl, bbox, hex, metro }: Props) {
  const mapRef = useRef<maplibregl.Map | null>(null);

  const onReady = (map: maplibregl.Map) => {
    mapRef.current = map;
    // Click a hex → exact reachable-jobs count (+ the jobs/population behind it).
    map.on("click", (e) => {
      const feats = map.queryRenderedFeatures(e.point, { layers: ["hex-access"] });
      if (!feats.length) return;
      const p = feats[0].properties as { jobs: number; population: number; access: number };
      new maplibregl.Popup({ closeButton: true })
        .setLngLat(e.lngLat)
        .setHTML(
          `<div style="color:#0b0f14;font:13px system-ui">` +
          `<strong>Jobs reachable (½-mi walk)</strong><br>` +
          `${Number(p.access).toLocaleString()} jobs<br>` +
          `<span style="color:#555">${Number(p.jobs).toLocaleString()} jobs based here · ` +
          `pop ${Number(p.population).toLocaleString()}</span></div>`,
        )
        .addTo(map);
    });
  };

  const labels = hexBinLabels(hex.breaks.access);

  return (
    <MapShell
      buildStyle={() => style(pmtilesUrl, hex)}
      bbox={bbox}
      ariaLabel={`Choropleth of jobs reachable within a half-mile walk across ${metro ?? "the region"}, by H3 hex cell`}
      onReady={onReady}
      errorMessage="The map failed to load. The job-access table below has the same scores."
    >
      <MapPanel label="Jobs reachable (½-mi walk)">
        <p className="font-medium text-text">Jobs reachable (½-mi walk)</p>
        <ul className="mt-2 border-t border-hairline pt-2" aria-label="Job-access legend (per hex cell)">
          {labels.map((lab, i) => (
            <li key={lab} className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className="inline-block h-3 w-3 rounded-sm border border-hairline/50"
                style={{ background: HEX_RAMPS.access[i] }}
              />
              <span className="tabular">{lab}</span>
            </li>
          ))}
          <li className="mt-1 text-text-muted">per hex cell · click a cell for exact values</li>
        </ul>
      </MapPanel>
    </MapShell>
  );
}
