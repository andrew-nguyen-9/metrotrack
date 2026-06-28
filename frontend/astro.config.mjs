// @ts-check
import { readFileSync } from "node:fs";
import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import vercel from "@astrojs/vercel";
import tailwindcss from "@tailwindcss/vite";

// ADR-002: Astro + React islands on Vercel. Static by default; the map/charts/search
// hydrate as `client:*` islands. Tailwind v4 via the Vite plugin (no config file).

// `/` redirects to the default metro (first live, from config) until the v2.1 homepage
// city directory exists. The slug comes from the generated metros.json (prebuild
// regenerates it from metros/*.toml) so nothing metro-specific is hardcoded here.
/** @type {{ slug: string, status: string }[]} */
const metros = JSON.parse(
  readFileSync(new URL("./src/data/metros.json", import.meta.url), "utf8"),
);
const defaultSlug = (metros.find((m) => m.status === "live") ?? metros[0]).slug;

export default defineConfig({
  site: "https://transit.an9.dev",
  adapter: vercel(),
  integrations: [react()],
  redirects: {
    "/": `/${defaultSlug}`,
  },
  vite: {
    plugins: [tailwindcss()],
  },
});
