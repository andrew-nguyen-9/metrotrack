import { useEffect, useRef, useState } from "react";
// Tree-shaken ECharts — line chart for the NTD efficiency trends (see FundingChart
// for the bundle-size rationale).
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent, TooltipComponent, LegendComponent, AriaComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import {
  authorityLabel, rowsFor, trendYears, TREND_METRICS,
  type FundingRow, type TrendMetricKey,
} from "../lib/funding";
import { useChartTheme, SERIES_SYMBOLS, type ChartTheme } from "../lib/chart";

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, AriaComponent, CanvasRenderer]);

type Props = { rows: FundingRow[]; authorities: string[]; metro?: string };

// One NTD-internal ratio at a time, one line per service board — all three metrics
// (farebox recovery, subsidy/rider, cost/rider) come from the SAME NTD receipt, so
// no cross-source mixing. Color comes from the shared colorblind-aware ramp and each
// line carries a distinct marker SYMBOL, so color is never the only signal.
function buildOption(rows: FundingRow[], authorities: string[], metric: TrendMetricKey, theme: ChartTheme) {
  const m = TREND_METRICS[metric];
  const years = trendYears(rows);
  return {
    animation: !window.matchMedia("(prefers-reduced-motion: reduce)").matches
      && document.documentElement.getAttribute("data-motion") !== "reduce",
    aria: { enabled: true, decal: { show: true } },
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    legend: { top: 0, textStyle: { color: theme.text }, inactiveColor: theme.muted },
    tooltip: {
      trigger: "axis",
      valueFormatter: (v: number | null) => (v == null ? "—" : m.fmt(v)),
    },
    xAxis: {
      type: "category",
      data: years.map(String),
      axisLabel: { color: theme.text },
      axisLine: { lineStyle: { color: theme.line } },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: m.isPct ? 1 : undefined,
      name: m.axis,
      nameTextStyle: { color: theme.muted, align: "left" },
      axisLabel: { color: theme.muted, formatter: (v: number) => m.fmt(v) },
      splitLine: { lineStyle: { color: theme.line } },
    },
    series: authorities.map((a, i) => {
      const byYear = new Map(rowsFor(rows, a).map((r) => [r.fiscal_year, r[metric]]));
      return {
        name: authorityLabel(a),
        type: "line",
        color: theme.cat[i % theme.cat.length],
        symbol: SERIES_SYMBOLS[i % SERIES_SYMBOLS.length],
        symbolSize: 9,
        showSymbol: true,
        connectNulls: false,
        data: years.map((y) => byYear.get(y) ?? null),
      };
    }),
  };
}

export default function FundingTrendChart({ rows, authorities, metro }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const [metric, setMetric] = useState<TrendMetricKey>("farebox_recovery");
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
      console.error("[funding-trend-chart]", e);
      setError(true);
    }
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.setOption(buildOption(rows, authorities, metric, theme), true);
  }, [rows, authorities, metric, theme]);

  if (error) {
    return (
      <p role="alert" className="p-4 text-sm text-text-muted">
        The chart failed to load. The table below has the same efficiency figures.
      </p>
    );
  }

  return (
    <div>
      <fieldset className="mb-3">
        <legend className="text-sm font-medium">Measure</legend>
        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
          {(Object.keys(TREND_METRICS) as TrendMetricKey[]).map((k) => (
            <label key={k} className="flex cursor-pointer items-center gap-2 py-1 text-sm">
              <input
                type="radio"
                name="funding-trend-metric"
                value={k}
                checked={metric === k}
                onChange={() => setMetric(k)}
                className="h-4 w-4 accent-accent"
              />
              <span>{TREND_METRICS[k].label}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <div
        ref={ref}
        role="img"
        aria-label={`${TREND_METRICS[metric].label} per service board${metro ? ` (${metro})` : ""} by fiscal year, from the FTA National Transit Database. Exact figures are in the table below.`}
        className="h-[48vh] min-h-72 w-full"
      />
    </div>
  );
}
