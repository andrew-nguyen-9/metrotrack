// @ts-check
import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import mdx from "@astrojs/mdx";
import vercel from "@astrojs/vercel";
import tailwindcss from "@tailwindcss/vite";

// ADR-002: Astro + React islands on Vercel. Static by default; the map/charts/search
// hydrate as `client:*` islands. Tailwind v4 via the Vite plugin (no config file).
// `/` is the national homepage + metro directory (E2, src/pages/index.astro) — no
// longer a redirect to the default metro.

export default defineConfig({
  site: "https://transit.an9.dev",
  adapter: vercel(),
  integrations: [react(), mdx()],
  vite: {
    plugins: [tailwindcss()],
  },
});
