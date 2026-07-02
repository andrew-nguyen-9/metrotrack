import { useEffect, useRef, useState } from "react";
// Tree-shaken ECharts — see VacancyChart for the bundle-size rationale. Two variants:
// a bus-vs-rail monthly trend (line) and a latest-month ranking (horizontal bar).
import * as echarts from "echarts/core";
import { LineChart, BarChart } from "echarts/charts";
import {
  GridComponent, TooltipComponent, LegendComponent, AriaComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { monthLabel, type TrendPoint } from "../lib/ridership";
import { useChartTheme, SERIES_SYMBOLS, type ChartTheme } from "../lib/chart";

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, AriaComponent, CanvasRenderer]);

type TrendProps = { variant: "trend"; trend: TrendPoint[]; metro?: string };
type BarProps = {
  variant: "bar"; bars: { label: string; value: number }[]; valueName: string; ariaLabel: string;
};
type Props = TrendProps | BarProps;

const animated = () =>
  !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  && document.documentElement.getAttribute("data-motion") !== "reduce";

// Series color comes from the shared categorical ramp (theme.cat — colorblind aware)
// and each trend line carries a distinct marker SYMBOL, so color is never the only
// signal (legend + symbols + table for the trend; axis labels for the bar).
function trendOption(trend: TrendPoint[], theme: ChartTheme) {
  const series = [
    { key: "bus" as const, name: "Bus" },
    { key: "rail" as const, name: "Rail ('L')" },
  ];
  return {
    animation: animated(),
    aria: { enabled: true, decal: { show: true } },
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    legend: { top: 0, textStyle: { color: theme.text }, inactiveColor: theme.muted },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: trend.map((p) => monthLabel(p.month)),
      axisLabel: { color: theme.text },
      axisLine: { lineStyle: { color: theme.line } },
    },
    yAxis: {
      type: "value",
      min: 0,
      name: "Monthly rides",
      nameTextStyle: { color: theme.muted, align: "left" },
      axisLabel: {
        color: theme.muted,
        formatter: (v: number) => (v >= 1e6 ? `${v / 1e6}M` : v.toLocaleString()),
      },
      splitLine: { lineStyle: { color: theme.line } },
    },
    series: series.map((s, i) => ({
      name: s.name,
      type: "line",
      color: theme.cat[i % theme.cat.length],
      symbol: SERIES_SYMBOLS[i % SERIES_SYMBOLS.length],
      symbolSize: 7,
      showSymbol: false,
      data: trend.map((p) => p[s.key]),
    })),
  };
}

function barOption(bars: { label: string; value: number }[], valueName: string, theme: ChartTheme) {
  return {
    animation: animated(),
    aria: { enabled: true },
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "value",
      name: valueName,
      nameTextStyle: { color: theme.muted },
      axisLabel: {
        color: theme.muted,
        formatter: (v: number) => (v >= 1e6 ? `${v / 1e6}M` : v.toLocaleString()),
      },
      splitLine: { lineStyle: { color: theme.line } },
    },
    yAxis: {
      type: "category",
      // Reverse so the largest bar sits at the top.
      data: bars.map((b) => b.label).reverse(),
      axisLabel: { color: theme.text },
      axisLine: { lineStyle: { color: theme.line } },
    },
    series: [{
      type: "bar",
      color: theme.cat[0],
      data: bars.map((b) => b.value).reverse(),
    }],
  };
}

export default function RidershipChart(props: Props) {
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
      console.error("[ridership-chart]", e);
      setError(true);
    }
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const option = props.variant === "trend"
      ? trendOption(props.trend, theme)
      : barOption(props.bars, props.valueName, theme);
    chart.setOption(option, true);
  }, [props, theme]);

  if (error) {
    return (
      <p role="alert" className="p-4 text-sm text-text-muted">
        The chart failed to load. The table below has the same numbers.
      </p>
    );
  }

  const empty = props.variant === "trend" ? !props.trend.length : !props.bars.length;
  if (empty) {
    return <p className="p-4 text-sm text-text-muted">No ridership data yet.</p>;
  }

  const label = props.variant === "trend"
    ? `Monthly CTA bus and rail ridership over time${props.metro ? ` (${props.metro})` : ""}. Exact counts are in the table below.`
    : props.ariaLabel;
  return (
    <div
      ref={ref}
      role="img"
      aria-label={`${label} Exact values are in the table below.`}
      className="h-[48vh] min-h-72 w-full"
    />
  );
}
