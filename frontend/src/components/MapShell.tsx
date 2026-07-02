import { useEffect, useRef, useState, type ReactNode } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import { Protocol } from "pmtiles";
import "maplibre-gl/dist/maplibre-gl.css";

// MapShell — the reusable MapLibre wrapper E3/E4/E5 build their maps on. It owns
// the boilerplate every transit map needs: PMTiles protocol, reduced-motion-aware
// init, NavigationControl, resize + refit-until-the-user-takes-the-camera, and a
// standard error banner. Consumers provide the style and, via `onReady(map)`,
// wire their own layers / popups / layer-control. Overlay UI (legend + controls)
// goes in `children`; wrap it in <MapPanel> for consistent chrome.
//
// Usage:
//   <MapShell buildStyle={() => style(url, data)} bbox={bbox} ariaLabel="…"
//             onReady={(map) => { mapRef.current = map; /* click, popups */ }}
//             errorMessage="The map failed to load. Tables below have the data.">
//     <MapPanel label="Overlay">…controls + <Legend/>…</MapPanel>
//   </MapShell>

export function MapPanel({
  children, label, className = "",
}: { children: ReactNode; label?: string; className?: string }) {
  return (
    <div
      aria-label={label}
      className={`absolute left-2 top-2 max-w-[68%] rounded-md border border-hairline bg-surface-2/90 p-3 text-xs text-text shadow-lg backdrop-blur-sm ${className}`}
    >
      {children}
    </div>
  );
}

export type MapShellProps = {
  buildStyle: () => StyleSpecification;
  bbox: [number, number, number, number];
  ariaLabel: string;
  onReady?: (map: maplibregl.Map) => void;
  errorMessage?: string;
  children?: ReactNode;
};

export default function MapShell({
  buildStyle, bbox, ariaLabel, onReady, errorMessage, children,
}: MapShellProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  // Keep the latest callbacks/style without forcing a map re-init on each render.
  const styleRef = useRef(buildStyle);
  const readyRef = useRef(onReady);
  styleRef.current = buildStyle;
  readyRef.current = onReady;

  useEffect(() => {
    if (!ref.current) return;
    const protocol = new Protocol();
    maplibregl.addProtocol("pmtiles", protocol.tile);
    const reduce =
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      document.documentElement.getAttribute("data-motion") === "reduce";

    const map = new maplibregl.Map({
      container: ref.current,
      style: styleRef.current(),
      bounds: bbox,
      fitBoundsOptions: { padding: 24, animate: false },
      attributionControl: { compact: true },
      dragRotate: false,
      ...(reduce ? { fadeDuration: 0 } : {}),
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("error", (e) => {
      console.error("[map]", e.error?.message ?? e);
      setError(true);
    });

    const ready = () => readyRef.current?.(map);
    map.isStyleLoaded() ? ready() : map.once("load", ready);

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
      maplibregl.removeProtocol("pmtiles");
    };
  }, [bbox]);

  return (
    <div className="relative h-full w-full">
      <div ref={ref} role="application" aria-label={ariaLabel} className="h-full w-full" />
      {children}
      {error && (
        <p role="alert" className="absolute inset-x-0 bottom-0 bg-surface/90 p-2 text-center text-sm text-text-muted">
          {errorMessage ?? "The map failed to load."}
        </p>
      )}
    </div>
  );
}
