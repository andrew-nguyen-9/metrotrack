import { useEffect, useRef, useState } from "react";
// Tree-shaken ECharts — line chart for the vacancy trend (see FundingChart for the
// bundle-size rationale).
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent, TooltipComponent, LegendComponent, AriaComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import {
  authorityLabel, snapshotDates, rowsFor, type VacancyRow,
} from "../lib/hiring";

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, AriaComponent, CanvasRenderer]);

type Props = { rows: VacancyRow[]; authorities: string[]; metro?: string };

// Per-authority line color (data encoding) — paired with a distinct marker SYMBOL so
// color is never the only signal (legend + symbols + table). (ponytail: literals like
// TransitMap's BG/STOP; agency brand colors aren't tokenized in TOKENS.md.)
const SERIES: Record<string, { color: string; symbol: string }> = {
  cta: { color: "#2bb8cf", symbol: "circle" },
  metra: { color: "#e09a36", symbol: "triangle" },
  pace: { color: "#9b8cf0", symbol: "rect" },
};

const cssVar = (el: Element, name: string): string =>
  getComputedStyle(el).getPropertyValue(name).trim();

function buildOption(rows: VacancyRow[], authorities: string[], theme: { text: string; muted: string; line: string }) {
  const dates = snapshotDates(rows);
  return {
    animation: !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    aria: { enabled: true, decal: { show: true } },
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    legend: { top: 0, textStyle: { color: theme.text }, inactiveColor: theme.muted },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: dates,
      axisLabel: { color: theme.text },
      axisLine: { lineStyle: { color: theme.line } },
    },
    yAxis: {
      type: "value",
      min: 0,
      name: "Open postings",
      nameTextStyle: { color: theme.muted, align: "left" },
      axisLabel: { color: theme.muted },
      splitLine: { lineStyle: { color: theme.line } },
    },
    series: authorities.map((a) => {
      const byDate = new Map(rowsFor(rows, a).map((r) => [r.as_of, r.open_postings]));
      const s = SERIES[a] ?? { color: theme.text, symbol: "circle" };
      return {
        name: authorityLabel(a),
        type: "line",
        color: s.color,
        symbol: s.symbol,
        symbolSize: 9,
        showSymbol: true,      // 1–2 snapshots render as visible points
        connectNulls: false,
        data: dates.map((d) => byDate.get(d) ?? null),
      };
    }),
  };
}

export default function VacancyChart({ rows, authorities, metro }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    try {
      const chart = echarts.init(ref.current);
      chartRef.current = chart;
      const ro = new ResizeObserver(() => chart.resize());
      ro.observe(ref.current);
      return () => { ro.disconnect(); chart.dispose(); chartRef.current = null; };
    } catch (e) {
      console.error("[vacancy-chart]", e);
      setError(true);
    }
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !ref.current) return;
    const root = document.documentElement;
    const theme = {
      text: cssVar(root, "--text") || "#eee",
      muted: cssVar(root, "--text-muted") || "#aaa",
      line: cssVar(ref.current, "--color-hairline") || "rgba(140,148,163,0.3)",
    };
    chart.setOption(buildOption(rows, authorities, theme), true);
  }, [rows, authorities]);

  if (error) {
    return (
      <p role="alert" className="p-4 text-sm text-text-muted">
        The chart failed to load. The table below has the same postings data.
      </p>
    );
  }
  if (!rows.length) {
    return <p className="p-4 text-sm text-text-muted">No snapshots yet — the weekly trend begins once data is collected.</p>;
  }

  return (
    <div
      ref={ref}
      role="img"
      aria-label={`Open job postings per service board over time${metro ? ` (${metro})` : ""}. Exact counts are in the table below.`}
      className="h-[48vh] min-h-72 w-full"
    />
  );
}
