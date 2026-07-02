// GET /api/live/[metro] — live CTA positions + arrivals, keys server-side (e4a).
// On-demand rendered (prerender=false) → runs as a Vercel serverless function; the
// CTA keys are read from the server env and NEVER reach the client bundle.
//
// Query params (all optional, comma-separated; caller picks the slice it needs):
//   bus_routes=9,4     getvehicles positions for these CTA bus routes (≤10)
//   bus_stops=1234     getpredictions arrivals for these bus stop ids (≤10)
//   lines=red,blue     train positions for these 'L' lines
//   stations=41320     train arrivals for these station map ids (≤4)
// Response: LiveFeed (see src/lib/live.ts) — { metro, generated, vehicles[], arrivals[], errors[] }.
// Always 200 with a body; upstream/credential/rate-limit issues surface in `errors`
// so e4b/e11 degrade gracefully instead of catching exceptions.
import type { APIRoute } from "astro";
import { fetchLive, CACHE_TTL_MS, POLL_MS, type LiveFeed, type LiveParams } from "@/lib/live";

export const prerender = false;

const SUPPORTED = new Set(["chicago"]);

// ponytail: process-local memo, one entry per distinct query. Bounds upstream calls
// to ~1 per CACHE_TTL_MS per param-set on a warm function; cold starts just re-fetch.
// Good enough for the free tier — no external cache infra stood up.
const cache = new Map<string, { at: number; feed: LiveFeed }>();

const csv = (v: string | null): string[] =>
  (v ?? "").split(",").map((s) => s.trim()).filter(Boolean);

export const GET: APIRoute = async ({ params, url }) => {
  const metro = params.metro ?? "";
  if (!SUPPORTED.has(metro)) {
    return json({ error: `unsupported metro: ${metro}` }, 404, 0);
  }

  const q = url.searchParams;
  const p: LiveParams = {
    busRoutes: csv(q.get("bus_routes")),
    busStops: csv(q.get("bus_stops")),
    lines: csv(q.get("lines")),
    stations: csv(q.get("stations")),
  };

  const key = `${metro}?${new URLSearchParams({
    b: p.busRoutes.join(","), s: p.busStops.join(","),
    l: p.lines.join(","), t: p.stations.join(","),
  })}`;

  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) {
    return json(hit.feed, 200, CACHE_TTL_MS);
  }

  const feed = await fetchLive(metro, {
    bus: import.meta.env.CTA_BUS_TRACKER_API ?? process.env.CTA_BUS_TRACKER_API,
    train: import.meta.env.CTA_TRAIN_TRACKER_API ?? process.env.CTA_TRAIN_TRACKER_API,
  }, p);

  cache.set(key, { at: Date.now(), feed });
  return json(feed, 200, CACHE_TTL_MS);
};

function json(body: unknown, status: number, ttlMs: number): Response {
  const s = Math.round(ttlMs / 1000);
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      // Let a CDN/browser reuse the response for the cache window; poll cadence hint.
      "cache-control": s > 0 ? `public, max-age=${s}, s-maxage=${s}` : "no-store",
      "x-poll-ms": String(POLL_MS),
    },
  });
}
