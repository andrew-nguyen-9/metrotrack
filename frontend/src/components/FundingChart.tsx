import { useEffect, useRef, useState } from "react";
// Tree-shaken ECharts (full build is ~330KB gzip — too heavy for the JS budget,
// DoD performance table). We pull only the bar chart + the components used below.
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import {
  GridComponent, TooltipComponent, LegendComponent, AriaComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import {
  authorityLabel, fmtUSD, rowsFor, RTA_KIND_LABELS, SERIES_LABELS,
  type FundingRow,
} from "../lib/funding";

echarts.use([BarChart, GridComponent, TooltipComponent, LegendComponent, AriaComponent, CanvasRenderer]);

type Props = { rows: FundingRow[]; authorities: string[] };

// Series colors are a DATA ENCODING (actual vs RTA), not decoration — and color is
// never the only signal: bars are positionally paired, the legend names each series,
// ECharts `aria.decal` adds distinct patterns, and the tooltip + table carry exact
// values. Actual reuses the cyan accent; RTA uses a warm amber that reads distinctly
// in both themes. (ponytail: two literals here, like TransitMap's BG/STOP — chart
// series colors aren't tokenized in TOKENS.md.)
const ACTUAL_COLOR = "#2bb8cf";
const RTA_COLOR = "#e09a36";

const cssVar = (el: Element, name: string): string =>
  getComputedStyle(el).getPropertyValue(name).trim();

function buildOption(rows: FundingRow[], authority: string, theme: { text: string; muted: string; line: string }) {
  const data = rowsFor(rows, authority);
  const years = data.map((r) => String(r.fiscal_year));
  const actual = data.map((r) => r.actual_audited);
  const rta = data.map((r) => r.rta_amount);
  const kindByYear = new Map(data.map((r) => [r.fiscal_year, r.rta_kind]));

  return {
    animation: !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    aria: { enabled: true, decal: { show: true } },
    color: [ACTUAL_COLOR, RTA_COLOR],
    grid: { left: 8, right: 12, top: 36, bottom: 8, containLabel: true },
    legend: { top: 0, textStyle: { color: theme.text }, inactiveColor: theme.muted },
    // Default axis tooltip shows the year + both series; the column's true nature
    // (adopted budget / plan / estimate) is printed under each year on the x-axis.
    tooltip: {
      trigger: "axis",
      valueFormatter: (v: number | null) => (v == null ? "—" : fmtUSD(v)),
    },
    xAxis: {
      type: "category",
      data: years,
      axisLabel: {
        color: theme.text,
        formatter: (y: string) => {
          const kind = kindByYear.get(Number(y));
          return kind ? `${y}\n{k|${RTA_KIND_LABELS[kind] ?? kind}}` : y;
        },
        rich: { k: { color: theme.muted, fontSize: 10, padding: [2, 0, 0, 0] } },
      },
      axisLine: { lineStyle: { color: theme.line } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: theme.muted, formatter: (v: number) => fmtUSD(v) },
      splitLine: { lineStyle: { color: theme.line } },
    },
    series: [
      { name: SERIES_LABELS.actual, type: "bar", data: actual, barMaxWidth: 28 },
      { name: SERIES_LABELS.rta, type: "bar", data: rta, barMaxWidth: 28 },
    ],
  };
}

export default function FundingChart({ rows, authorities }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const [authority, setAuthority] = useState(authorities[0] ?? "cta");
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    try {
      const chart = echarts.init(ref.current);
      chartRef.current = chart;
      const ro = new ResizeObserver(() => chart.resize());
      ro.observe(ref.current);
      return () => {
        ro.disconnect();
        chart.dispose();
        chartRef.current = null;
      };
    } catch (e) {
      console.error("[funding-chart]", e);
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
    chart.setOption(buildOption(rows, authority, theme), true);
  }, [rows, authority]);

  if (error) {
    return (
      <p role="alert" className="p-4 text-sm text-text-muted">
        The chart failed to load. The table below has the same budget-vs-actual data.
      </p>
    );
  }

  return (
    <div>
      <fieldset className="mb-3">
        <legend className="text-sm font-medium">Service board</legend>
        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
          {authorities.map((a) => (
            <label key={a} className="flex cursor-pointer items-center gap-2 py-1 text-sm">
              <input
                type="radio"
                name="funding-authority"
                value={a}
                checked={authority === a}
                onChange={() => setAuthority(a)}
                className="h-4 w-4 accent-accent"
              />
              <span>{authorityLabel(a)}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <div
        ref={ref}
        role="img"
        aria-label={`Operating budget versus audited actual expense for ${authorityLabel(authority)} by fiscal year. Exact figures are in the table below.`}
        className="h-[48vh] min-h-72 w-full"
      />
    </div>
  );
}
