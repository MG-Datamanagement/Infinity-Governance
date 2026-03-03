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
  data: ComplianceTrend[];
}

export function ComplianceTrendsChart({ data }: ComplianceTrendsChartProps) {
  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-gray-900">
            Compliance Score Trends
          </h3>
          <p className="text-xs text-gray-500">Last 6 months performance</p>
        </div>
        <div className="flex items-center gap-1 text-xs text-success font-medium bg-success/10 px-1.5 py-0.5 rounded-full border border-success/50">
          <TrendingUpIcon size={14} className="text-success" />
          +7% Overall
        </div>
      </div>

      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="month"
            tick={{ fill: "#6b7280", fontSize: 8 }}
            tickLine={{ stroke: "#e5e7eb" }}
          />
          <YAxis
            domain={[60, 100]}
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
          <Line
            type="monotone"
            dataKey="overall"
            stroke="#6b7280"
            strokeWidth={2}
            dot={{ r: 2 }}
            name="Overall"
          />
          <Line
            type="monotone"
            dataKey="gdpr"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ r: 2 }}
            name="GDPR"
          />
          <Line
            type="monotone"
            dataKey="soc2"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 2 }}
            name="SOC 2"
          />
          <Line
            type="monotone"
            dataKey="hipaa"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={{ r: 2 }}
            name="HIPAA"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
