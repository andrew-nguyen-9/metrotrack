import { useEffect, useRef, useState } from "react";
// Tree-shaken ECharts — grouped bars of jobs + population by distance-to-CBD ring
// (see VacancyChart for the bundle-size rationale).
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import {
  GridComponent, TooltipComponent, LegendComponent, AriaComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { TodRing } from "../lib/tod";
import { useChartTheme, type ChartTheme } from "../lib/chart";

echarts.use([BarChart, GridComponent, TooltipComponent, LegendComponent, AriaComponent, CanvasRenderer]);

type Props = { rings: TodRing[]; metro?: string };

// Two categorical colors (colorblind-aware ramp), each bar group also labelled in
// the legend + carried in the table below, so color is never the only signal.
function buildOption(rings: TodRing[], theme: ChartTheme) {
  const labels = rings.map((r) => r.label);
  const bar = (name: string, key: "jobs" | "population", i: number) => ({
    name,
    type: "bar" as const,
    color: theme.cat[i % theme.cat.length],
    emphasis: { focus: "series" as const },
    data: rings.map((r) => r[key]),
  });
  return {
    animation: !window.matchMedia("(prefers-reduced-motion: reduce)").matches
      && document.documentElement.getAttribute("data-motion") !== "reduce",
    aria: { enabled: true, decal: { show: true } },
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    legend: { top: 0, textStyle: { color: theme.text }, inactiveColor: theme.muted },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "category",
      data: labels,
      name: "distance to nearest CBD",
      nameLocation: "middle",
      nameGap: 32,
      nameTextStyle: { color: theme.muted },
      axisLabel: { color: theme.text },
      axisLine: { lineStyle: { color: theme.line } },
    },
    yAxis: {
      type: "value",
      min: 0,
      name: "Count",
      nameTextStyle: { color: theme.muted, align: "left" },
      axisLabel: {
        color: theme.muted,
        formatter: (v: number) => (v >= 1e6 ? `${v / 1e6}M` : v >= 1e3 ? `${v / 1e3}k` : `${v}`),
      },
      splitLine: { lineStyle: { color: theme.line } },
    },
    series: [bar("Jobs", "jobs", 0), bar("Population", "population", 1)],
  };
}

export default function TodChart({ rings, metro }: Props) {
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
      console.error("[tod-chart]", e);
      setError(true);
    }
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.setOption(buildOption(rings, theme), true);
  }, [rings, theme]);

  if (error) {
    return (
      <p role="alert" className="p-4 text-sm text-text-muted">
        The chart failed to load. The table below has the same distance-band data.
      </p>
    );
  }
  if (!rings.length) {
    return <p className="p-4 text-sm text-text-muted">No distance bands to show.</p>;
  }

  return (
    <div
      ref={ref}
      role="img"
      aria-label={`Jobs and population by distance to the nearest central business district${metro ? ` (${metro})` : ""}. Exact counts are in the table below.`}
      className="h-[48vh] min-h-72 w-full"
    />
  );
}
