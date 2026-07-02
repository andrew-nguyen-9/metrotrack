// Editorial content collection — native Astro Content Layer (MDX), no CMS.
// Author a piece by dropping an .mdx file in src/content/articles/; frontmatter
// below is the schema. `region` drives the per-metro filtered index: use a metro's
// region name (e.g. "Chicagoland") to scope a piece, or "national" to show it on
// every region's index + the general /articles index.
// NOTE: `z` is imported from astro:content (not zod directly) — Astro flows this
// exact instance into the generated CollectionEntry types. It carries a
// deprecation *hint* in this version; importing zod directly breaks type
// inference, so we keep it. Hints are not errors/warnings.
import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const articles = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/articles" }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    region: z.string().default("national"),
    summary: z.string(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { articles };
