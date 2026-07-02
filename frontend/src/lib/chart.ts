import { useEffect, useState } from "react";

// Shared chart theme — reads the design tokens off <html> so every chart
// (E6/E8/E9/E11) is light/dark/colorblind aware by default (DIRECTION §5).
// `useChartTheme()` re-reads live when the theme/colorblind toggle flips.
//
// Usage (ECharts):
//   const theme = useChartTheme();
//   series[i].color = theme.cat[i % theme.cat.length];
//   series[i].symbol = SERIES_SYMBOLS[i % SERIES_SYMBOLS.length]; // redundant w/ color
//   axisLabel: { color: theme.muted }, legend: { textStyle: { color: theme.text } }

export type ChartTheme = {
  text: string;
  muted: string;
  line: string;
  accent: string;
  cat: string[]; // categorical series ramp (colorblind-aware)
};

// Distinct marker symbols so a series is never distinguished by color alone.
export const SERIES_SYMBOLS = ["circle", "triangle", "rect", "diamond", "roundRect", "pin"];

const EMPTY: ChartTheme = {
  text: "#e6e6e6", muted: "#9aa1ac", line: "rgba(140,148,163,0.3)", accent: "#2bb8cf",
  cat: ["#2bb8cf", "#e09a36", "#9b8cf0", "#4fbf87", "#e06a86", "#6f8cf0"],
};

const read = (el: Element, name: string, fallback: string): string =>
  getComputedStyle(el).getPropertyValue(name).trim() || fallback;

export function readChartTheme(): ChartTheme {
  if (typeof document === "undefined") return EMPTY;
  const el = document.documentElement;
  return {
    text: read(el, "--text", EMPTY.text),
    muted: read(el, "--text-muted", EMPTY.muted),
    line: read(el, "--border-hairline", EMPTY.line),
    accent: read(el, "--accent", EMPTY.accent),
    cat: [1, 2, 3, 4, 5, 6].map((i, idx) => read(el, `--cat-${i}`, EMPTY.cat[idx])),
  };
}

export function useChartTheme(): ChartTheme {
  const [theme, setTheme] = useState<ChartTheme>(EMPTY);
  useEffect(() => {
    const update = () => setTheme(readChartTheme());
    update();
    const mo = new MutationObserver(update);
    mo.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme", "data-colorblind"],
    });
    return () => mo.disconnect();
  }, []);
  return theme;
}
