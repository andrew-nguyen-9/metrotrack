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
import { useChartTheme, SERIES_SYMBOLS, type ChartTheme } from "../lib/chart";

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, AriaComponent, CanvasRenderer]);

type Props = { rows: VacancyRow[]; authorities: string[]; metro?: string };

// Series color comes from the shared categorical ramp (theme.cat — colorblind
// aware) and each line carries a distinct marker SYMBOL, so color is never the
// only signal (legend + symbols + table).
function buildOption(rows: VacancyRow[], authorities: string[], theme: ChartTheme) {
  const dates = snapshotDates(rows);
  return {
    animation: !window.matchMedia("(prefers-reduced-motion: reduce)").matches
      && document.documentElement.getAttribute("data-motion") !== "reduce",
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
    series: authorities.map((a, i) => {
      const byDate = new Map(rowsFor(rows, a).map((r) => [r.as_of, r.open_postings]));
      return {
        name: authorityLabel(a),
        type: "line",
        color: theme.cat[i % theme.cat.length],
        symbol: SERIES_SYMBOLS[i % SERIES_SYMBOLS.length],
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
  const theme = useChartTheme();

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

  // Re-render option whenever data OR the live theme (dark/light/colorblind) changes.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.setOption(buildOption(rows, authorities, theme), true);
  }, [rows, authorities, theme]);

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
