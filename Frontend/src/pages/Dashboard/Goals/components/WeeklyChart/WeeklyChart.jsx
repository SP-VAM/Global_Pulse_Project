import React from "react";
import "./WeeklyChart.css";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
} from "recharts";

function getChartMode(startDate, endDate) {
  const start = new Date(startDate);
  const end = new Date(endDate);

  const totalDays = Math.ceil(
    (end - start) / (1000 * 60 * 60 * 24)
  );

  if (totalDays <= 31) return "day";

  if (totalDays <= 365) return "month";

  return "year";
}

function formatLabel(date, mode) {
  const d = new Date(date);

  if (mode === "day") {
    return d.toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
    });
  }

  if (mode === "month") {
    return d.toLocaleDateString("en-IN", {
      month: "short",
    });
  }

  return d.getFullYear().toString();
}

export default function WeeklyChart({ goal }) {

  if (!goal) return null;

  const mode = getChartMode(goal.startDate, goal.endDate);

  const sortedHistory = [...goal.history].sort(
    (a, b) => new Date(a.date) - new Date(b.date)
  );

  let runningTotal = 0;

  const chartData = [];

  sortedHistory.forEach((item) => {

    runningTotal += Number(item.amount);

    const label = formatLabel(item.date, mode);

    const existing = chartData.find(
      (x) => x.label === label
    );

    if (existing) {

      existing.value = runningTotal;

    } else {

      chartData.push({
        label,
        value: runningTotal,
      });

    }

  });
    return (
    <div className="wc-root">

      <h3>Investment Progress</h3>

      <ResponsiveContainer
        width="100%"
        height={350}
      >

        <BarChart
          data={chartData}
          margin={{
            top: 35,
            right: 20,
            left: 10,
            bottom: 10,
          }}
        >

          <CartesianGrid
            strokeDasharray="3 3"
            vertical={false}
          />

          <XAxis
            dataKey="label"
            tick={{
              fill: "#B8C0CC",
              fontSize: 12,
            }}
          />

          <YAxis
            allowDecimals={false}
            tick={{
              fill: "#B8C0CC",
              fontSize: 12,
            }}
            label={{
              value: goal.unit,
              angle: -90,
              position: "insideLeft",
              fill: "#B8C0CC",
            }}
          />

          <Tooltip
            formatter={(value) => [
              `${value} ${goal.unit}`,
              "Current Progress",
            ]}
          />

          <Bar
            dataKey="value"
            fill="#2F6BFF"
            radius={[8, 8, 0, 0]}
            maxBarSize={40}
          >
            <LabelList
              dataKey="value"
              position="top"
              fill="#FFFFFF"
              fontSize={12}
              fontWeight={600}
            />
          </Bar>

        </BarChart>

      </ResponsiveContainer>

    </div>
  );

}