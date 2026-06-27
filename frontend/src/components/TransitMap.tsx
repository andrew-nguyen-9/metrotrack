import { useEffect, useRef, useState } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import { Protocol } from "pmtiles";
import "maplibre-gl/dist/maplibre-gl.css";

type Props = {
  pmtilesUrl: string;
  bbox: [number, number, number, number];
};

// ponytail: structural map paint mirrors the dark-theme tokens (globals.css).
// MapLibre WebGL paint can't be Tailwind utilities, so these few values are
// literals here. Agency brand colors arrive in v1.1 (TOKENS.md) — routes use
// their own GTFS color below, never a guessed agency hex.
const BG = "#0b0f14";
const STOP = "#2bb8cf"; // accent cyan
const ROUTE_FALLBACK = "#8a94a3";

const style = (pmtilesUrl: string): StyleSpecification => ({
  version: 8,
  sources: {
    transit: {
      type: "vector",
      url: `pmtiles://${pmtilesUrl}`,
      attribution: "GTFS: CTA, Pace, Metra",
    },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": BG } },
    {
      id: "routes",
      type: "line",
      source: "transit",
      "source-layer": "routes",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        // Each route's own GTFS color when present, else a neutral.
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
      id: "stops",
      type: "circle",
      source: "transit",
      "source-layer": "stops",
      paint: {
        "circle-color": STOP,
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 1.5, 14, 4],
        "circle-stroke-color": BG,
        "circle-stroke-width": 0.5,
      },
    },
  ],
});

export default function TransitMap({ pmtilesUrl, bbox }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const protocol = new Protocol();
    maplibregl.addProtocol("pmtiles", protocol.tile);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const map = new maplibregl.Map({
      container: ref.current,
      style: style(pmtilesUrl),
      bounds: bbox,
      fitBoundsOptions: { padding: 24, animate: false },
      attributionControl: { compact: true },
      // Reduced motion: no inertial/animated camera.
      dragRotate: false,
      ...(reduce ? { fadeDuration: 0 } : {}),
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("error", (e) => {
      console.error("[map]", e.error?.message ?? e);
      setError(true);
    });

    // The island can mount before its flex/grid container reaches final size, so
    // the initial fit is stale. Refit on container resize until the user takes
    // over the camera (then respect their view).
    let userMoved = false;
    map.on("dragstart", () => { userMoved = true; });
    map.on("zoomstart", (e) => { if (e.originalEvent) userMoved = true; });
    const ro = new ResizeObserver(() => {
      map.resize();
      if (!userMoved) map.fitBounds(bbox, { padding: 24, animate: false });
    });
    ro.observe(ref.current);

    return () => {
      ro.disconnect();
      map.remove();
      maplibregl.removeProtocol("pmtiles");
    };
  }, [pmtilesUrl, bbox]);

  return (
    <div className="relative h-full w-full">
      <div
        ref={ref}
        role="application"
        aria-label="Interactive map of CTA, Pace, and Metra routes and stops"
        className="h-full w-full"
      />
      {error && (
        <p role="alert" className="absolute inset-x-0 bottom-0 bg-surface/90 p-2 text-center text-sm text-text-muted">
          The map failed to load. The route table below has the same data.
        </p>
      )}
    </div>
  );
}
