// Article listing helpers over the native `articles` content collection.
// Drafts are hidden in production, kept in dev so authors can preview.
import { getCollection, type CollectionEntry } from "astro:content";

export type Article = CollectionEntry<"articles">;

// Published, newest first. Drafts show only during `astro dev`.
export const publishedArticles = async (): Promise<Article[]> => {
  const all = await getCollection("articles", ({ data }) => import.meta.env.DEV || !data.draft);
  return all.sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
};

// A piece belongs to a region's index if it targets that region or is "national".
export const inRegion = (a: Article, region: string): boolean =>
  a.data.region === "national" || a.data.region === region;

export const fmtDate = (d: Date): string =>
  d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
