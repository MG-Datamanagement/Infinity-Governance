"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { ComplianceTrend } from "@/types";
import { TrendingUpIcon } from "lucide-react";

interface ComplianceTrendsChartProps {
  data: {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
    }[];
  };
}

export function ComplianceTrendsChart({ data }: ComplianceTrendsChartProps) {
  // Transform API data format to Recharts format
  // From: { labels: ["Mar"], datasets: [{ label: "Overall", data: [44.4] }, ...] }
  // To: [{ month: "Mar", "Overall": 44.4, ... }]
  const chartData = data.labels.map((label, index) => {
    const point: any = { month: label };
    data.datasets.forEach((dataset) => {
      point[dataset.label] = dataset.data[index];
    });
    return point;
  });

  const getLineColor = (label: string) => {
    switch (label.toUpperCase()) {
      case "OVERALL":
        return "#6b7280";
      case "GDPR":
        return "#10b981";
      case "SOC2":
        return "#3b82f6";
      case "HIPAA":
        return "#f59e0b";
      default:
        return "#94a3b8";
    }
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-gray-900">
            Compliance Score Trends
          </h3>
          <p className="text-xs text-gray-500">Performance across frameworks</p>
        </div>
        <div className="flex items-center gap-1 text-xs text-success font-medium bg-success/10 px-1.5 py-0.5 rounded-full border border-success/50">
          <TrendingUpIcon size={14} className="text-success" />
          Live Data
        </div>
      </div>

      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="month"
            tick={{ fill: "#6b7280", fontSize: 8 }}
            tickLine={{ stroke: "#e5e7eb" }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "#6b7280", fontSize: 8 }}
            tickLine={{ stroke: "#e5e7eb" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "white",
              border: "1px solid #e5e7eb",
              borderRadius: "8px",
              boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
            }}
          />
          <Legend
            wrapperStyle={{ paddingTop: "5px", fontSize: "12px" }}
            iconType="circle"
            iconSize={12}
          />
          {data.datasets.map((dataset) => (
            <Line
              key={dataset.label}
              type="monotone"
              dataKey={dataset.label}
              stroke={getLineColor(dataset.label)}
              strokeWidth={dataset.label.toUpperCase() === "OVERALL" ? 3 : 2}
              dot={{ r: 2 }}
              name={dataset.label}
              activeDot={{ r: 4 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
