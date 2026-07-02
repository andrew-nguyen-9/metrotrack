import { useEffect, useRef, useState } from "react";
// Tree-shaken ECharts — horizontal bar of the tract population-change distribution.
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent, AriaComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { Bucket } from "../lib/demographics";
import { useChartTheme, type ChartTheme } from "../lib/chart";

echarts.use([BarChart, GridComponent, TooltipComponent, AriaComponent, CanvasRenderer]);

type Props = { buckets: Bucket[]; metro?: string };

// Single-series bar: color carries no meaning beyond "count", and every bar is
// labelled on the axis, so color is never the only signal. Sequential-neutral: use
// the shared accent for all bars.
function buildOption(buckets: Bucket[], theme: ChartTheme) {
  return {
    animation: !window.matchMedia("(prefers-reduced-motion: reduce)").matches
      && document.documentElement.getAttribute("data-motion") !== "reduce",
    aria: { enabled: true, decal: { show: true } },
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "value",
      name: "Census tracts",
      nameLocation: "middle",
      nameGap: 28,
      nameTextStyle: { color: theme.muted },
      axisLabel: { color: theme.muted },
      splitLine: { lineStyle: { color: theme.line } },
    },
    yAxis: {
      type: "category",
      data: buckets.map((b) => b.label),
      axisLabel: { color: theme.text },
      axisLine: { lineStyle: { color: theme.line } },
    },
    series: [{
      type: "bar",
      data: buckets.map((b) => b.count),
      color: theme.accent,
      barMaxWidth: 36,
      label: { show: true, position: "right", color: theme.text },
    }],
  };
}

export default function DemographicsChart({ buckets, metro }: Props) {
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
      console.error("[demographics-chart]", e);
      setError(true);
    }
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.setOption(buildOption(buckets, theme), true);
  }, [buckets, theme]);

  if (error) {
    return (
      <p role="alert" className="p-4 text-sm text-text-muted">
        The chart failed to load. The table below has the same distribution.
      </p>
    );
  }
  if (!buckets.length) {
    return <p className="p-4 text-sm text-text-muted">No tract data available.</p>;
  }

  return (
    <div
      ref={ref}
      role="img"
      aria-label={`Number of census tracts by population-change band between the two ACS vintages${metro ? ` (${metro})` : ""}. Exact counts are in the table below.`}
      className="h-[42vh] min-h-64 w-full"
    />
  );
}
