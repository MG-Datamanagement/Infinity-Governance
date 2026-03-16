"use client";

import React, { useEffect, useState } from "react";
import ConnectorIcon from "@/app/(data-connectors)/components/ConnectorIcon";
import { ApiOwner } from "@/services/dashboardApiServices";
import { useAppStore } from "@/store/appStore";

// ─── Only MongoDB + PostgreSQL ────────────────────────────────────────────────
const CONNECTORS = [
  {
    id: "athena",
    name: "Athena",
    description: "Import Schemas, Tables, Views, and lineage to S3 from Athena.",
    iconBg: "bg-white",
    icon: "athena",
    configTitle: "Configure AWS Athena Connection",
    docsLabel: "Athena source docs",
    uriPlaceholder: "e.g. athena.us-east-1.amazonaws.com",
    defaultName: "My Athena Source",
  },
  {
    id: "cockroachdb",
    name: "CockroachDb",
    description: "Import Databases, Schemas, Tables, Views, statistics and lineage from CockroachDb.",
    iconBg: "bg-gray-50",
    icon: "cockroach",
    configTitle: "Configure CockroachDB Connection",
    docsLabel: "CockroachDB source docs",
    uriPlaceholder: "e.g. localhost:26257",
    defaultName: "My CockroachDB Source",
  },
  {
    id: "csv",
    name: "CSV",
    description: "Import metadata from a formatted CSV.",
    iconBg: "bg-green-50",
    icon: "csv",
    configTitle: "Configure CSV Connection",
    docsLabel: "CSV source docs",
    uriPlaceholder: "e.g. /path/to/file.csv",
    defaultName: "My CSV Source",
  },
  {
    id: "dynamodb",
    name: "DynamoDB",
    description: "Import Tables and metadata from AWS DynamoDB.",
    iconBg: "bg-blue-50",
    icon: "dynamodb",
    configTitle: "Configure DynamoDB Connection",
    docsLabel: "DynamoDB source docs",
    uriPlaceholder: "e.g. dynamodb.us-east-1.amazonaws.com",
    defaultName: "My DynamoDB Source",
  },
  {
    id: "glue",
    name: "Glue",
    description: "Import Databases, Tables, and metadata from AWS Glue Data Catalog.",
    iconBg: "bg-orange-50",
    icon: "glue",
    configTitle: "Configure AWS Glue Connection",
    docsLabel: "Glue source docs",
    uriPlaceholder: "e.g. glue.us-east-1.amazonaws.com",
    defaultName: "My Glue Source",
  },
  {
    id: "mongodb",
    name: "MongoDB",
    description: "Import Databases, Collections, and schema metadata from MongoDB.",
    iconBg: "bg-green-100",
    icon: "mongodb",
    configTitle: "Configure MongoDB Recipe",
    docsLabel: "MongoDB source docs",
    uriPlaceholder: "e.g. mongodb://localhost:27017",
    defaultName: "My MongoDB Source",
  },
  {
    id: "mssql",
    name: "MSSQL",
    description: "Import Databases, Schemas, Tables, Views, and procedures from Microsoft SQL Server.",
    iconBg: "bg-red-50",
    icon: "mssql",
    configTitle: "Configure MSSQL Connection",
    docsLabel: "MSSQL source docs",
    uriPlaceholder: "e.g. mssql://localhost:1433",
    defaultName: "My MSSQL Source",
  },
  {
    id: "mysql",
    name: "MySQL",
    description: "Import Databases, Tables, Views, and stored procedures from MySQL.",
    iconBg: "bg-blue-50",
    icon: "mysql",
    configTitle: "Configure MySQL Connection",
    docsLabel: "MySQL source docs",
    uriPlaceholder: "e.g. mysql://localhost:3306",
    defaultName: "My MySQL Source",
  },
  {
    id: "postgresql",
    name: "PostgreSQL",
    description: "Import Schemas, Tables, Views, Functions, and lineage from PostgreSQL.",
    iconBg: "bg-gray-100",
    icon: "postgresql",
    configTitle: "Configure PostgreSQL Recipe",
    docsLabel: "PostgreSQL source docs",
    uriPlaceholder: "e.g. postgresql://localhost:5432",
    defaultName: "My PostgreSQL Source",
  },
  {
    id: "snowflake",
    name: "Snowflake",
    description: "Import Databases, Schemas, Tables, Views, Stages, and lineage from Snowflake.",
    iconBg: "bg-blue-50",
    icon: "snowflake",
    configTitle: "Configure Snowflake Connection",
    docsLabel: "Snowflake source docs",
    uriPlaceholder: "e.g. account.snowflakecomputing.com",
    defaultName: "My Snowflake Source",
  },
];

const TIMEZONES = [
  "Asia/Calcutta",
  "Asia/Kolkata",
  "UTC",
  "America/New_York",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Asia/Tokyo",
  "Asia/Singapore",
  "Australia/Sydney",
];

// ─── Stepper ──────────────────────────────────────────────────────────────────
const STEPS = ["Choose Data Source", "Configure Connection", "Sync Schedule", "Finish up"];

const Stepper: React.FC<{ current: number }> = ({ current }) => (
  <div className="flex items-center justify-between px-6 pt-6 pb-5 border-b border-gray-100">
    {STEPS.map((label, idx) => {
      const step = idx + 1;
      const done = step < current;
      const active = step === current;
      return (
        <React.Fragment key={label}>
          <div className="flex flex-col items-center gap-1.5 min-w-[80px]">
            <div
              className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all ${done
                ? "bg-indigo-600 border-indigo-600 text-white"
                : active
                  ? "border-indigo-600 text-indigo-600 bg-white"
                  : "border-gray-200 text-gray-400 bg-white"
                }`}
            >
              {done ? (
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                step
              )}
            </div>
            <span
              className={`text-xs font-medium text-center leading-tight ${active ? "text-indigo-600" : done ? "text-gray-500" : "text-gray-400"
                }`}
            >
              {label}
            </span>
          </div>
          {idx < STEPS.length - 1 && (
            <div
              className={`flex-1 h-0.5 mx-2 mb-5 transition-all ${done ? "bg-indigo-500" : "bg-gray-200"
                }`}
            />
          )}
        </React.Fragment>
      );
    })}
  </div>
);

// ─── Modal footer ─────────────────────────────────────────────────────────────
const Footer: React.FC<{
  onPrev?: () => void;
  onNext?: () => void;
  nextLabel?: string;
  nextDisabled?: boolean;
  extraButtons?: React.ReactNode;
}> = ({ onPrev, onNext, nextLabel = "Next", nextDisabled, extraButtons }) => (
  <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 flex-shrink-0">
    <button
      onClick={onPrev}
      disabled={!onPrev}
      className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
    >
      Previous
    </button>
    <div className="flex items-center gap-2">
      {extraButtons}
      <button
        onClick={onNext}
        disabled={nextDisabled}
        className="px-5 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
      >
        {nextLabel}
      </button>
    </div>
  </div>
);

// ─── Step 1: Choose Data Source ───────────────────────────────────────────────
const Step1: React.FC<{
  selected: string | null;
  onSelect: (id: string) => void;
}> = ({ selected, onSelect }) => {
  const [search, setSearch] = useState("");
  const filtered = CONNECTORS.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase())
  );
  return (
    <div className="flex-1 overflow-y-auto px-6 py-5">
      <div className="relative mb-5">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search data sources..."
          className="pl-9 pr-4 py-2.5 border border-indigo-400 rounded-lg text-sm bg-white w-full text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-400/30 focus:border-indigo-500 transition-all shadow-sm"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        {filtered.map((c) => {
          const isSelected = selected === c.id;
          return (
            <button
              key={c.id}
              onClick={() => onSelect(c.id)}
              className={`flex items-start gap-3 p-4 rounded-xl border text-left transition-all duration-150 ${isSelected
                ? "border-indigo-500 bg-indigo-50 shadow-sm"
                : "border-gray-200 bg-white hover:border-indigo-300 hover:bg-gray-50"
                }`}
            >
              <div className={`w-10 h-10 rounded-lg ${c.iconBg} flex items-center justify-center flex-shrink-0`}>
                <ConnectorIcon icon={c.icon} className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <p className={`text-sm font-semibold ${isSelected ? "text-indigo-700" : "text-gray-800"}`}>
                  {c.name}
                </p>
                <p className="text-xs text-gray-500 mt-0.5 leading-snug">{c.description}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

// ─── Step 2: Configure Connection ─────────────────────────────────────────────
const Step2: React.FC<{
  connector: typeof CONNECTORS[0];
  config: any //{ uri: string; username: string; password: string; schemaInference: boolean; randomSampling: boolean; maxSchemaSize: string; yamlMode: boolean };
  onChange: (k: string, v: string | boolean) => void;
}> = ({ connector, config, onChange }) => (
  <div className="flex-1 overflow-y-auto px-6 py-5">
    <div className="flex items-start justify-between mb-5">
      <div>
        <h2 className="text-base font-bold text-gray-900">{connector.configTitle}</h2>
        <p className="text-xs text-gray-400 mt-0.5">
          For more information, see the{" "}
          <a href="#" className="text-indigo-600 hover:underline">{connector.docsLabel}</a>.
        </p>
      </div>
      <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs font-medium">
        <button
          onClick={() => onChange("yamlMode", false)}
          className={`px-3 py-1.5 transition-colors ${!config.yamlMode ? "bg-gray-100 text-gray-800" : "bg-white text-gray-500 hover:bg-gray-50"}`}
        >
          Form View
        </button>
        <button
          onClick={() => onChange("yamlMode", true)}
          className={`px-3 py-1.5 transition-colors ${config.yamlMode ? "bg-gray-100 text-gray-800" : "bg-white text-gray-500 hover:bg-gray-50"}`}
        >
          YAML View
        </button>
      </div>
    </div>

    {config.yamlMode ? (
      <textarea
        className="w-full h-56 font-mono text-xs border border-gray-200 rounded-lg p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-none"
        defaultValue={`source:\n  type: ${connector.id}\n  config:\n    connect_uri: "${config.uri || connector.uriPlaceholder}"\n    username: "${config.username}"\n    password: "***"`}
      />
    ) : (
      <div className="space-y-4">
        {connector.id !== 'athena' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Connection URI</label>
            <input
              type="text"
              value={config.uri}
              onChange={(e) => onChange("uri", e.target.value)}
              placeholder={connector.uriPlaceholder}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Username</label>
            <input
              type="text"
              value={config.username}
              onChange={(e) => onChange("username", e.target.value)}
              placeholder="e.g. admin"
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
            <input
              type="password"
              value={config.password}
              onChange={(e) => onChange("password", e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
          </div>
        </div>

        {connector.id === 'athena' && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">AWS Region</label>
                <input
                  type="text"
                  value={config.aws_region}
                  onChange={(e) => onChange("aws_region", e.target.value)}
                  placeholder="e.g. us-east-1"
                  className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Work Group</label>
                <input
                  type="text"
                  value={config.work_group}
                  onChange={(e) => onChange("work_group", e.target.value)}
                  placeholder="e.g. primary"
                  className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">S3 Staging Directory</label>
              <input
                type="text"
                value={config.s3_staging_dir}
                onChange={(e) => onChange("s3_staging_dir", e.target.value)}
                placeholder="e.g. s3://athena-query-results-tmp-123/"
                className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />
            </div>
          </>
        )}

        <div>
          <p className="text-sm font-semibold text-gray-800 mb-3">Options (recommended)</p>
          <div className="space-y-3">
            {[
              { key: "schemaInference", label: "Enable Schema Inference", desc: "Infer schema from data samples", value: config.schemaInference },
              { key: "randomSampling", label: "Use Random Sampling", desc: "Sample random rows for profiling", value: config.randomSampling },
            ].map((opt) => (
              <label key={opt.key} className="flex items-start justify-between cursor-pointer gap-4">
                <div>
                  <p className="text-sm text-gray-700 font-medium">{opt.label}</p>
                  <p className="text-xs text-gray-400">{opt.desc}</p>
                </div>
                <input
                  type="checkbox"
                  checked={opt.value}
                  onChange={(e) => onChange(opt.key, e.target.checked)}
                  className="w-4 h-4 mt-0.5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 flex-shrink-0 accent-indigo-600"
                />
              </label>
            ))}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Max Schema Size</label>
              <input
                type="text"
                value={config.maxSchemaSize}
                onChange={(e) => onChange("maxSchemaSize", e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              />
            </div>
          </div>
        </div>
      </div>
    )}
  </div>
);

// ─── Step 3: Sync Schedule ────────────────────────────────────────────────────
type Frequency = "Hourly" | "Daily" | "Weekly";

const Step3: React.FC<{
  schedule: { enabled: boolean; frequency: Frequency; hour: string; minute: string; timezone: string };
  onChange: (k: string, v: string | boolean) => void;
}> = ({ schedule, onChange }) => {
  const summary =
    schedule.frequency === "Hourly"
      ? "Runs every hour"
      : schedule.frequency === "Daily"
        ? `Runs daily at ${schedule.hour}:${schedule.minute}`
        : `Runs weekly at ${schedule.hour}:${schedule.minute}`;

  return (
    <div className="flex-1 overflow-y-auto px-6 py-5">
      <h2 className="text-base font-bold text-gray-900 mb-1">Configure an Ingestion Schedule</h2>
      <p className="text-xs text-gray-400 mb-5">Set up how often you want to sync metadata from this source.</p>

      {/* Toggle */}
      <label className="flex items-center gap-3 cursor-pointer mb-5">
        <button
          onClick={() => onChange("enabled", !schedule.enabled)}
          className={`relative inline-flex h-6 w-11 rounded-full transition-colors ${schedule.enabled ? "bg-indigo-600" : "bg-gray-200"}`}
        >
          <span className={`inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform mt-0.5 ${schedule.enabled ? "translate-x-5" : "translate-x-0.5"}`} />
        </button>
        <span className="text-sm font-medium text-gray-700">Run on a schedule (Recommended)</span>
      </label>

      {schedule.enabled && (
        <div className="space-y-4">
          <div>
            <p className="text-xs font-semibold text-red-500 mb-2">* Schedule</p>
            <div className="flex gap-2 mb-3">
              {(["Hourly", "Daily", "Weekly"] as Frequency[]).map((f) => (
                <button
                  key={f}
                  onClick={() => onChange("frequency", f)}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-lg border text-sm font-medium transition-all ${schedule.frequency === f
                    ? "bg-indigo-600 border-indigo-600 text-white"
                    : "bg-white border-gray-200 text-gray-600 hover:border-gray-300"
                    }`}
                >
                  {f === "Hourly" && (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                  )}
                  {f === "Daily" && (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                  )}
                  {f === "Weekly" && (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                  )}
                  {f}
                </button>
              ))}
            </div>

            {schedule.frequency !== "Hourly" && (
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm text-gray-500">Run at</span>
                <input
                  type="text"
                  value={schedule.hour}
                  onChange={(e) => onChange("hour", e.target.value.padStart(2, "0").slice(-2))}
                  maxLength={2}
                  className="w-14 px-2 py-1.5 border border-gray-200 rounded-lg text-sm text-center text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
                <span className="text-gray-400">:</span>
                <input
                  type="text"
                  value={schedule.minute}
                  onChange={(e) => onChange("minute", e.target.value.padStart(2, "0").slice(-2))}
                  maxLength={2}
                  className="w-14 px-2 py-1.5 border border-gray-200 rounded-lg text-sm text-center text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
                <span className="text-sm text-gray-400">
                  {schedule.frequency === "Daily" ? "every day" : "every week"}
                </span>
              </div>
            )}

            <div className="inline-flex items-center gap-1.5 bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-1.5">
              <svg className="w-3.5 h-3.5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-xs text-indigo-600 font-medium">{summary}</span>
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold text-red-500 mb-1.5">* Timezone</p>
            <select
              value={schedule.timezone}
              onChange={(e) => onChange("timezone", e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Step 4: Finish Up ────────────────────────────────────────────────────────
const Step4: React.FC<{
  connector: typeof CONNECTORS[0];
  config: { uri: string };
  schedule: { frequency: string; hour: string; minute: string; timezone: string };
  finish: { name: string; piiEnabled: boolean; piiApproval: boolean; failureEmail: string; owner_id: string };
  owners: ApiOwner[];
  onChange: (k: string, v: string | boolean) => void;
}> = ({ connector, config, schedule, finish, owners, onChange }) => {
  const scheduleStr = `Every ${schedule.frequency.toLowerCase()} at ${schedule.hour}:${schedule.minute}`;

  return (
    <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      {/* Configuration Summary */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 bg-gray-50 border-b border-gray-100">
          <svg className="w-4 h-4 text-green-500" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
          </svg>
          <span className="text-sm font-semibold text-gray-800">Configuration Summary</span>
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-4 p-4">
          <div>
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">Source Type</p>
            <div className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded ${connector.iconBg} flex items-center justify-center`}>
                <ConnectorIcon icon={connector.icon} className="w-4 h-4" />
              </div>
              <span className="text-sm font-medium text-gray-800">{connector.name}</span>
            </div>
          </div>
          {connector.id !== 'athena' && (
            <div>
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">Connection URI</p>
              <span className="text-sm text-gray-500">{config.uri || "Not configured"}</span>
            </div>
          )}
          <div>
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">Schedule</p>
            <div className="flex items-center gap-1.5 text-sm text-gray-600">
              <svg className="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {scheduleStr}
            </div>
          </div>
          <div>
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">Timezone</p>
            <span className="text-sm text-gray-600">{schedule.timezone}</span>
          </div>
        </div>
      </div>

      {/* Name */}
      <div>
        <label className="block text-sm font-semibold text-red-500 mb-0.5">* Name</label>
        <p className="text-xs text-gray-400 mb-1.5">Give this data source a name</p>
        <input
          type="text"
          value={finish.name}
          onChange={(e) => onChange("name", e.target.value)}
          placeholder={connector.defaultName}
          className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
        />
      </div>

      {/* Owners */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-1.5">* Owner</label>
        <p className="text-xs text-gray-400 mb-1.5">Select the primary owner for this data source</p>
        <select
          value={finish.owner_id}
          onChange={(e) => onChange("owner_id", e.target.value)}
          className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all cursor-pointer"
        >
          <option value="">Select an owner</option>
          {owners.map((owner) => (
            <option key={owner.id} value={owner.id}>
              {owner.name}
            </option>
          ))}
        </select>
      </div>

      {/* PII Detection Settings */}
      <div>
        <div className="flex items-center gap-1.5 mb-1">
          <svg className="w-4 h-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <p className="text-sm font-semibold text-gray-800">PII Detection Settings</p>
        </div>
        <p className="text-xs text-gray-400 mb-3">Control how sensitive data is detected and handled during ingestion.</p>

        <div className="border border-gray-200 rounded-xl divide-y divide-gray-100">
          {[
            {
              key: "piiEnabled",
              label: "Enable PII detection during ingestion",
              desc: "Scan columns for personally identifiable information and apply classification tags automatically.",
              value: finish.piiEnabled,
            },
            {
              key: "piiApproval",
              label: "Require approval for PII actions",
              desc: "Pause ingestion at PII detection steps and wait for a human to review and approve before proceeding.",
              value: finish.piiApproval,
            },
          ].map((opt) => (
            <label key={opt.key} className="flex items-start gap-3 p-4 cursor-pointer">
              <input
                type="checkbox"
                checked={opt.value}
                onChange={(e) => onChange(opt.key, e.target.checked)}
                className="w-4 h-4 mt-0.5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 accent-indigo-600 flex-shrink-0"
              />
              <div>
                <p className="text-sm font-medium text-gray-700">{opt.label}</p>
                <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{opt.desc}</p>
              </div>
            </label>
          ))}
        </div>

        {finish.piiEnabled && finish.piiApproval && (
          <div className="mt-3 flex items-start gap-2 bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2.5">
            <svg className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <div>
              <p className="text-xs font-semibold text-yellow-800">Human-in-the-loop mode</p>
              <p className="text-xs text-yellow-700 mt-0.5 leading-relaxed">
                PII will be detected during ingestion and flagged for your review. The pipeline will pause and wait for your approval before applying tags or policies.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Failure Notifications */}
      <div>
        <div className="flex items-center gap-1.5 mb-1">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <p className="text-sm font-medium text-gray-700">Failure Notifications</p>
        </div>
        <p className="text-xs text-gray-400 mb-2">Enter email addresses to notify when an ingestion run fails. Separate multiple emails with commas.</p>
        <input
          type="text"
          value={finish.failureEmail}
          onChange={(e) => onChange("failureEmail", e.target.value)}
          placeholder="e.g. data-team@company.com, oncall@company.com"
          className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
        />
        <div className="mt-2 flex items-start gap-1.5 bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2">
          <svg className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-xs text-yellow-700">
            Notifications are sent <strong>only on failures</strong>, not on every successful run. Leave blank to disable failure alerts.
          </p>
        </div>
      </div>
    </div>
  );
};

// ─── Main Modal ───────────────────────────────────────────────────────────────
interface AddDataSourceModalProps {
  onClose: () => void;
  onSuccess?: (jobId: string, sourceName: string) => void;
}

const AddDataSourceModal: React.FC<AddDataSourceModalProps> = ({ onClose, onSuccess }) => {
  const [step, setStep] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [config, setConfig] = useState({
    uri: "", username: "", password: "",
    aws_region: "", work_group: "", s3_staging_dir: "",
    schemaInference: true, randomSampling: true, maxSchemaSize: "300", yamlMode: false,
  });
  const [schedule, setSchedule] = useState({
    enabled: true, frequency: "Daily" as Frequency, hour: "00", minute: "00", timezone: "Asia/Calcutta",
  });
  const [finish, setFinish] = useState({
    name: "", piiEnabled: true, piiApproval: true, failureEmail: "", owner_id: "",
  });
  const [owners, setOwners] = useState<ApiOwner[]>([]);
  const { setAddDsConfig } = useAppStore()

  useEffect(() => {
    const fetchOwners = async () => {
      try {
        const { dashboardApiServices } = await import("@/services/dashboardApiServices");
        const list = await dashboardApiServices.fetchOwnersList();
        setOwners(list);
        if (list.length > 0 && !finish.owner_id) {
          setFinish(p => ({ ...p, owner_id: list[0].id }));
        }
      } catch (err) {
        console.error("Failed to fetch owners", err);
      }
    };
    fetchOwners();
  }, []);

  const connector = CONNECTORS.find((c) => c.id === selectedId) ?? CONNECTORS[0];

  const updateConfig = (k: string, v: string | boolean) => setConfig((p: any) => ({ ...p, [k]: v }));
  const updateSchedule = (k: string, v: string | boolean) => setSchedule((p: any) => ({ ...p, [k]: v }));
  const updateFinish = (k: string, v: string | boolean) => setFinish((p: any) => ({ ...p, [k]: v }));

  const next = () => setStep((s: number) => Math.min(s + 1, 4));
  const prev = () => setStep((s: number) => Math.max(s - 1, 1));

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!selectedId) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      let payload: any = {
        name: finish.name || connector.defaultName,
        source_type: selectedId,
        description: finish.name || `Source for ${connector.name}`,
        schedule: `${schedule.hour}:${schedule.minute} ${schedule.timezone === 'Asia/Calcutta' ? 'GMT+5:30' : schedule.timezone}`,
        owner_id: finish.owner_id,
      };

      if (selectedId === 'postgresql') {
        payload.source_type = 'postgres';

        // Parse URI if it looks like one: postgresql://user:pass@host:port/db
        let hostPort = config.uri || "host.docker.internal:5432";
        let dbName = "test";

        if (config.uri && config.uri.includes("://")) {
          try {
            const url = new URL(config.uri.replace("postgresql://", "http://"));
            hostPort = url.host;
            dbName = url.pathname.slice(1).split('?')[0] || "test";
          } catch (e) {
            console.error("Failed to parse URI for PostgreSQL", e);
          }
        }

        payload.connection_details = {
          host_port: hostPort,
          database: dbName,
          username: config.username,
          password: config.password,
        };
        payload.include_views = true;
        payload.include_tables = true;
        payload.schema_pattern = ["public"];
        payload.table_pattern = [".*"];
      } else if (selectedId === 'mongodb') {
        payload.connection_details = {
          connect_uri: config.uri,
          username: config.username,
          password: config.password,
          enableSchemaInference: config.schemaInference,
          useRandomSampling: config.randomSampling,
          maxSchemaSize: parseInt(config.maxSchemaSize) || 300,
        };
        payload.include_views = false;
        payload.include_tables = true;
      } else if (selectedId === 'athena') {
        payload.connection_details = {
          username: config.username,
          password: config.password,
          aws_region: config.aws_region,
          work_group: config.work_group,
          s3_staging_dir: config.s3_staging_dir,
        };
      }

      const { dashboardApiServices } = await import("@/services/dashboardApiServices");
      const createdSource = await dashboardApiServices.createDataSource(selectedId as any, payload);

      // Trigger ingestion after creation
      let jobId = "";
      if (createdSource && (createdSource.id || createdSource.source_id)) {
        const sourceId = createdSource.id || createdSource.source_id;
        if (sourceId) {
          const ingestRes = await dashboardApiServices.ingestSource(sourceId);
          jobId = ingestRes.job_id;
          setAddDsConfig({...config, ...finish, sourceId, jobId})
        }
      }

      if (onSuccess && jobId) {
        onSuccess(jobId, finish.name || connector.defaultName);
      } else {
        onClose();
      }
    } catch (err: any) {
      setSubmitError(err.message || "Failed to create data source");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Title bar */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3 flex-shrink-0">
          <h2 className="text-lg font-bold text-gray-900">Connect Data Source</h2>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Stepper */}
        <Stepper current={step} />

        {/* Error message */}
        {submitError && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 text-red-600 text-xs rounded-lg flex items-center gap-2">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {submitError}
          </div>
        )}

        {/* Step content */}
        {step === 1 && (
          <Step1 selected={selectedId} onSelect={(id) => setSelectedId(id)} />
        )}
        {step === 2 && (
          <Step2 connector={connector} config={config} onChange={updateConfig} />
        )}
        {step === 3 && (
          <Step3 schedule={schedule} onChange={updateSchedule} />
        )}
        {step === 4 && (
          <Step4
            connector={connector}
            config={config}
            schedule={schedule}
            finish={finish}
            owners={owners}
            onChange={updateFinish}
          />
        )}

        {/* Footer */}
        {step < 4 ? (
          <Footer
            onPrev={step > 1 ? prev : undefined}
            onNext={next}
            nextDisabled={step === 1 && !selectedId}
          />
        ) : (
          <Footer
            onPrev={prev}
            onNext={handleSubmit}
            nextLabel={isSubmitting ? "Saving..." : "Save & Run"}
            nextDisabled={isSubmitting}
            extraButtons={
              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                {isSubmitting ? "Saving..." : "Save"}
              </button>
            }
          />
        )}
      </div>
    </div>
  );
};

export default AddDataSourceModal;
