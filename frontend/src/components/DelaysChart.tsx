import { useEffect, useRef, useState } from "react";
// Tree-shaken ECharts (see RidershipChart for the bundle rationale). One variant:
// the next-arrival wait distribution as a vertical histogram. Restyles live on the
// theme/colorblind toggles via useChartTheme.
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent, AriaComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { CountdownBucket } from "../lib/delays";
import { useChartTheme, type ChartTheme } from "../lib/chart";

echarts.use([BarChart, GridComponent, TooltipComponent, AriaComponent, CanvasRenderer]);

type Props = { buckets: CountdownBucket[]; ariaLabel: string };

const animated = () =>
  !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  && document.documentElement.getAttribute("data-motion") !== "reduce";

function option(buckets: CountdownBucket[], theme: ChartTheme) {
  return {
    animation: animated(),
    aria: { enabled: true, decal: { show: true } },
    grid: { left: 8, right: 16, top: 8, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "category",
      data: buckets.map((b) => b.bucket),
      name: "Minutes to arrival",
      nameLocation: "middle",
      nameGap: 30,
      nameTextStyle: { color: theme.muted },
      axisLabel: { color: theme.text },
      axisLine: { lineStyle: { color: theme.line } },
    },
    yAxis: {
      type: "value",
      min: 0,
      name: "Predictions",
      nameTextStyle: { color: theme.muted, align: "left" },
      axisLabel: { color: theme.muted, formatter: (v: number) => v.toLocaleString() },
      splitLine: { lineStyle: { color: theme.line } },
    },
    series: [{
      type: "bar",
      color: theme.cat[0],
      data: buckets.map((b) => b.count),
    }],
  };
}

export default function DelaysChart({ buckets, ariaLabel }: Props) {
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
      console.error("[delays-chart]", e);
      setError(true);
    }
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.setOption(option(buckets, theme), true);
  }, [buckets, theme]);

  if (error) {
    return (
      <p role="alert" className="p-4 text-sm text-text-muted">
        The chart failed to load. The table below has the same numbers.
      </p>
    );
  }
  if (!buckets.some((b) => b.count > 0)) {
    return <p className="p-4 text-sm text-text-muted">No arrival predictions sampled yet.</p>;
  }
  return (
    <div
      ref={ref}
      role="img"
      aria-label={`${ariaLabel} Exact values are in the table below.`}
      className="h-[42vh] min-h-64 w-full"
    />
  );
}
