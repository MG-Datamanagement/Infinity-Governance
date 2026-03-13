"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  Search,
  ChevronDown,
  ChevronUp,
  MoreHorizontal,
  X,
  Sparkles,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import {
  dashboardApiServices,
  LineageVisualResponse,
  LineageApiNode,
} from "@/services/dashboardApiServices";

// ─── Internal types ───────────────────────────────────────────────────────────

type NodeType = "table" | "view" | "dashboard";
type QualityStatus = "healthy" | "warning" | "error";

interface InternalColumn {
  id: string;
  name: string;
  data_type: string;
  is_primary_key: boolean;
  is_nullable: boolean;
}

interface InternalTag {
  id: string;
  name: string;
  color: string | null;
}

interface InternalNode {
  id: string;
  type: NodeType;
  label: string;
  fullName: string;
  database: string;
  schema: string;
  sourceName: string;
  sourceType: string;
  columns: InternalColumn[];
  columnCount: number;
  tags: InternalTag[];
  qualityStatus: QualityStatus;
  isCenter?: boolean;
  x: number;
  y: number;
}

interface InternalEdge {
  from: string;
  to: string;
  isSecondary?: boolean;
}

interface NodeRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

// ─── Layout constants ─────────────────────────────────────────────────────────

const CARD_W = 210;
const CENTER_W = 248;
const CARD_H_EST = 116;
const GAP_Y = 28;
const COL_GAP = 110;

// ─── API → internal mapper ────────��───────────────────────────────────────────

function mapNode(
    apiNode: LineageApiNode,
    x: number,
    y: number,
    isCenter = false,
): InternalNode {
  return {
    id: apiNode.id,
    type: apiNode.type ?? "table",
    label: apiNode.table_name,
    fullName: apiNode.full_name,
    database: apiNode.database_name ?? "",
    schema: apiNode.schema_name ?? "",
    sourceName: apiNode.source?.name ?? "",
    sourceType: apiNode.source?.source_type ?? "",
    columns: (apiNode.columns ?? []).map((c) => ({
      id: c.id,
      name: c.name,
      data_type: c.data_type,
      is_primary_key: c.is_primary_key,
      is_nullable: c.is_nullable,
    })),
    columnCount: apiNode.columns?.length ?? 0,
    tags: (apiNode.tags ?? []).map((t) => ({
      id: t.id,
      name: t.name,
      color: t.color,
    })),
    qualityStatus: apiNode.status ?? "healthy",
    isCenter,
    x,
    y,
  };
}

function buildGraph(data: LineageVisualResponse): {
  nodes: InternalNode[];
  edges: InternalEdge[];
} {
  const ups = data.upstreams ?? [];
  const downs = data.downstreams ?? [];

  const COL1_X = 0;
  const COL2_X = CARD_W + COL_GAP;
  const COL3_X = COL2_X + CENTER_W + COL_GAP;
  const COL4_X = COL3_X + CARD_W + COL_GAP;

  // Center y — align with middle of upstream list
  const upH = ups.length * (CARD_H_EST + GAP_Y);
  const centerY = Math.max(0, upH / 2 - CARD_H_EST / 2);

  // Separate downstream into views vs dashboards
  const dsViews = downs.filter((n) => n.type === "view");
  const dsDash = downs.filter((n) => n.type !== "view" && n.type !== "table");
  const dsOther = downs.filter(
      (n) => n.type === "table" && n.id !== data.root.id,
  );
  const dsRight = [...dsViews, ...dsOther]; // col 3
  const dsFar = dsDash; // col 4

  const nodes: InternalNode[] = [];

  // center
  nodes.push(mapNode(data.root, COL2_X, centerY, true));

  // upstreams
  ups.forEach((n, i) =>
      nodes.push(mapNode(n, COL1_X, i * (CARD_H_EST + GAP_Y))),
  );

  // col-3 downstreams
  dsRight.forEach((n, i) =>
      nodes.push(mapNode(n, COL3_X, i * (CARD_H_EST + GAP_Y))),
  );

  // col-4 downstreams
  dsFar.forEach((n, i) =>
      nodes.push(mapNode(n, COL4_X, i * (CARD_H_EST + GAP_Y))),
  );

  // edges
  const edges: InternalEdge[] = [];
  const rootId = data.root.id;

  ups.forEach((n) => edges.push({ from: n.id, to: rootId }));

  downs.forEach((n) => {
    const isView = n.type === "view";
    edges.push({
      from: rootId,
      to: n.id,
      isSecondary: !isView,
    });
    // if there's a view, chain dashboards from it
    if (!isView && dsViews.length > 0) {
      dsViews.forEach((v) =>
          edges.push({ from: v.id, to: n.id, isSecondary: false }),
      );
    }
  });

  // deduplicate edges
  const seen = new Set<string>();
  const uniqueEdges = edges.filter((e) => {
    const key = `${e.from}->${e.to}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return { nodes, edges: uniqueEdges };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function typeIcon(type: NodeType) {
  if (type === "table")
    return (
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 9h18M3 15h18M9 3v18" />
        </svg>
    );
  if (type === "view")
    return (
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="3" />
          <path d="M2.458 12C3.732 7.943 7.523 5 12 5s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S3.732 16.057 2.458 12z" />
        </svg>
    );
  return (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
      </svg>
  );
}

function colTypeIcon(dataType: string) {
  const t = dataType.toLowerCase();
  if (t.includes("int") || t.includes("number") || t.includes("float") || t.includes("numeric"))
    return <span className="text-blue-400 font-bold text-[10px]">N</span>;
  if (t.includes("bool"))
    return <span className="text-purple-400 font-bold text-[10px]">B</span>;
  if (t.includes("date") || t.includes("time") || t.includes("string") && t.includes("time"))
    return <span className="text-yellow-500 font-bold text-[10px]">D</span>;
  if (t.includes("bytes") || t.includes("byte"))
    return <span className="text-gray-400 font-bold text-[10px]">#</span>;
  if (t.includes("array"))
    return <span className="text-orange-400 font-bold text-[10px]">[ ]</span>;
  return <span className="text-green-500 font-bold text-[10px]">A</span>;
}

function qualityDot(status: QualityStatus) {
  if (status === "healthy")
    return (
        <span className="w-4 h-4 rounded-full border-2 border-green-400 flex items-center justify-center">
        <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
      </span>
    );
  if (status === "error")
    return (
        <span className="w-4 h-4 rounded-full bg-red-100 border border-red-300 flex items-center justify-center text-red-500 text-[9px] font-black">!</span>
    );
  return (
      <span className="w-4 h-4 rounded-full bg-yellow-100 border border-yellow-300 flex items-center justify-center text-yellow-500 text-[9px] font-black">!</span>
  );
}

// Parse a data_type string like "SchemaFieldDataTypeClass({'type': StringTypeClass({})})"
// into something readable
function parseDataType(raw: string): string {
  const inner = raw.match(/type['"]?\s*:\s*([A-Za-z]+)/);
  if (inner) {
    return inner[1]
        .replace("TypeClass", "")
        .replace("Class", "")
        .toLowerCase();
  }
  return raw.length > 20 ? raw.slice(0, 18) + "…" : raw;
}

// Pick a tag pill color based on tag name
function tagPillClass(name: string): string {
  const n = name.toLowerCase();
  if (n === "pii" || n === "phi")
    return "bg-red-50 text-red-600 border-red-200";
  if (n === "financial" || n === "finance")
    return "bg-yellow-50 text-yellow-700 border-yellow-200";
  if (n === "gdpr" || n === "hipaa" || n === "sox")
    return "bg-blue-50 text-blue-700 border-blue-200";
  return "bg-gray-100 text-gray-600 border-gray-200";
}

// ─── Node Card ────────────────────────────────────────────────────────────────

interface NodeCardProps {
  node: InternalNode;
  isSelected: boolean;
  onClick: () => void;
}

function NodeCard({ node, isSelected, onClick }: NodeCardProps) {
  const [expanded, setExpanded] = useState(!!node.isCenter);
  const [colSearch, setColSearch] = useState("");

  const isCenter = !!node.isCenter;
  const filteredCols = node.columns.filter((c) =>
      c.name.toLowerCase().includes(colSearch.toLowerCase()),
  );

  return (
      <div
          onClick={onClick}
          className={[
            "select-none cursor-pointer rounded-xl border bg-white transition-all w-full",
            isCenter
                ? "border-indigo-300 shadow-lg ring-2 ring-indigo-200/60"
                : isSelected
                    ? "border-indigo-300 shadow-md ring-2 ring-indigo-400/50"
                    : "border-gray-200 shadow-sm hover:border-gray-300 hover:shadow-md",
          ].join(" ")}
      >
        {/* ── Header ── */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
          <div className="flex items-center gap-1.5 min-w-0">
          <span className={`flex-shrink-0 ${isCenter ? "text-indigo-500" : "text-gray-400"}`}>
            {typeIcon(node.type)}
          </span>
            {(node.database || node.sourceName) && (
                <span className="text-[10px] text-gray-400 truncate">
              {node.sourceName
                  ? `${node.sourceName.toUpperCase()} › ${node.schema || node.database}`
                  : `${node.database} › ${node.schema}`}
            </span>
            )}
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            {node.tags.slice(0, 2).map((tag) => (
                <span
                    key={tag.id}
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wide ${tagPillClass(tag.name)}`}
                >
              {tag.name}
            </span>
            ))}
            {qualityDot(node.qualityStatus)}
            <button
                className="text-gray-300 hover:text-gray-500 transition-colors ml-0.5"
                onClick={(e) => e.stopPropagation()}
            >
              <MoreHorizontal size={13} />
            </button>
          </div>
        </div>

        {/* ── Title ── */}
        <div className="px-3 pt-2 pb-1">
          <p className={`font-bold truncate ${isCenter ? "text-indigo-700 text-sm" : "text-gray-800 text-xs"}`}>
            {node.label}
          </p>
          {node.sourceType && (
              <p className="text-[10px] text-gray-400 truncate capitalize mt-0.5">
                {node.sourceType}
              </p>
          )}
        </div>

        {/* ── DQ Issue ── */}
        {node.qualityStatus === "error" && (
            <div className="mx-3 mb-2 flex items-center gap-1 text-[10px] text-red-500 bg-red-50 border border-red-100 rounded-lg px-2 py-1">
              <X size={10} />
              Data quality issue
            </div>
        )}

        {/* ── Columns toggle ── */}
        <div
            className="px-3 pb-2 flex items-center justify-between cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((v) => !v);
            }}
        >
        <span className="text-[11px] text-gray-500 font-medium">
          Columns <span className="font-bold text-gray-700">{node.columnCount}</span>
        </span>
          {expanded ? (
              <ChevronUp size={12} className="text-gray-400" />
          ) : (
              <ChevronDown size={12} className="text-gray-400" />
          )}
        </div>

        {/* ── Columns list ── */}
        {expanded && (
            <div className="border-t border-gray-100">
              {isCenter && (
                  <div className="px-3 py-1.5 border-b border-gray-100">
                    <div className="relative">
                      <Search size={10} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-300" />
                      <input
                          className="w-full text-[11px] pl-5 pr-2 py-1 border border-gray-100 rounded-md bg-gray-50 placeholder-gray-300 focus:outline-none"
                          placeholder="Find column"
                          value={colSearch}
                          onChange={(e) => setColSearch(e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                  </div>
              )}
              <ul className="max-h-44 overflow-y-auto">
                {filteredCols.length === 0 ? (
                    <li className="px-3 py-2 text-[11px] text-gray-300 italic">No columns</li>
                ) : (
                    filteredCols.map((col) => (
                        <li
                            key={col.id}
                            className="flex items-center gap-2 px-3 py-1.5 hover:bg-indigo-50/60 transition-colors"
                        >
                  <span className="w-5 text-center flex-shrink-0">
                    {colTypeIcon(col.data_type)}
                  </span>
                          <span className="text-[11px] text-gray-700 truncate flex-1">{col.name}</span>
                          <span className="text-[9px] text-gray-300 flex-shrink-0 font-mono">
                    {parseDataType(col.data_type)}
                  </span>
                        </li>
                    ))
                )}
              </ul>
            </div>
        )}
      </div>
  );
}

// ─── SVG Edge Layer ────────��──────────────────────────────────────────────────

interface EdgeLayerProps {
  edges: InternalEdge[];
  positions: Record<string, NodeRect>;
}

function EdgeLayer({ edges, positions }: EdgeLayerProps) {
  return (
      <svg
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "5000px",
            height: "5000px",
            overflow: "visible",
            pointerEvents: "none",
          }}
      >
        <defs>
          <marker id="lng-arrow-p" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#6366f1" />
          </marker>
          <marker id="lng-arrow-s" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#9ca3af" />
          </marker>
        </defs>

        {edges.map((edge, i) => {
          const from = positions[edge.from];
          const to = positions[edge.to];
          if (!from || !to) return null;

          const x1 = from.x + from.w;
          const y1 = from.y + from.h / 2;
          const x2 = to.x;
          const y2 = to.y + to.h / 2;
          const cx = (x1 + x2) / 2;

          const color = edge.isSecondary ? "#9ca3af" : "#6366f1";
          const marker = edge.isSecondary ? "url(#lng-arrow-s)" : "url(#lng-arrow-p)";

          return (
              <path
                  key={i}
                  d={`M${x1},${y1} C${cx},${y1} ${cx},${y2} ${x2},${y2}`}
                  fill="none"
                  stroke={color}
                  strokeWidth={edge.isSecondary ? 1.5 : 2}
                  strokeDasharray={edge.isSecondary ? "6 4" : undefined}
                  markerEnd={marker}
                  opacity={0.85}
              />
          );
        })}
      </svg>
  );
}

// ─── Depth / Direction Controls ───────────────────────────────────────────────

interface DepthControlProps {
  depth: number;
  direction: "upstream" | "downstream" | "both";
  onChange: (depth: number, direction: "upstream" | "downstream" | "both") => void;
}

function DepthControl({ depth, direction, onChange }: DepthControlProps) {
  return (
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-gray-500 font-medium">Depth</span>
        {[1, 2, 3, 4].map((d) => (
            <button
                key={d}
                onClick={() => onChange(d, direction)}
                className={`w-6 h-6 rounded-md text-[11px] font-bold border transition-colors ${
                    depth === d
                        ? "bg-indigo-600 text-white border-indigo-600"
                        : "bg-white text-gray-500 border-gray-200 hover:border-indigo-300"
                }`}
            >
              {d}
            </button>
        ))}
        <span className="ml-2 text-[11px] text-gray-500 font-medium">Direction</span>
        {(["both", "upstream", "downstream"] as const).map((d) => (
            <button
                key={d}
                onClick={() => onChange(depth, d)}
                className={`px-2 py-0.5 rounded-md text-[10px] font-bold border capitalize transition-colors ${
                    direction === d
                        ? "bg-indigo-600 text-white border-indigo-600"
                        : "bg-white text-gray-500 border-gray-200 hover:border-indigo-300"
                }`}
            >
              {d}
            </button>
        ))}
      </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

interface DatasetLineageProps {
  datasetId: string;
  datasetName: string;
}

export default function DatasetLineage({ datasetId, datasetName }: DatasetLineageProps) {
  // ── API state ──
  const [apiData, setApiData] = useState<LineageVisualResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [depth, setDepth] = useState(2);
  const [direction, setDirection] = useState<"upstream" | "downstream" | "both">("both");

  // ── Canvas state ──
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.85);
  const [pan, setPan] = useState({ x: 60, y: 40 });
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0 });
  const panOrigin = useRef({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [nodeHeights, setNodeHeights] = useState<Record<string, number>>({});

  // ── Fetch ──────────────────────────────────────��───────────────────────────

  useEffect(() => {
    if (!datasetId) return;
    setIsLoading(true);
    setError(null);
    setNodeHeights({});

    dashboardApiServices
        .fetchLineageVisual(datasetId, depth, direction)
        .then((data) => {
          setApiData(data);
          setSelectedNode(data.root.id);
        })
        .catch((err) => {
          console.error("Lineage fetch failed:", err);
          setError("Failed to load lineage data.");
        })
        .finally(() => setIsLoading(false));
  }, [datasetId, depth, direction]);

  // ── Derived graph ──────────────────────────────────────────────────────────

  const { nodes, edges } = apiData
      ? buildGraph(apiData)
      : { nodes: [], edges: [] };

  const visibleNodes = search.trim()
      ? nodes.filter(
          (n) =>
              n.label.toLowerCase().includes(search.toLowerCase()) ||
              n.sourceName.toLowerCase().includes(search.toLowerCase()) ||
              n.columns.some((c) => c.name.toLowerCase().includes(search.toLowerCase())),
      )
      : nodes;

  const positions: Record<string, NodeRect> = {};
  nodes.forEach((n) => {
    positions[n.id] = {
      x: n.x,
      y: n.y,
      w: n.isCenter ? CENTER_W : CARD_W,
      h: nodeHeights[n.id] ?? CARD_H_EST,
    };
  });

  // ── Pan / zoom handlers ────────────────────────────────────────────────────

  const onMouseDown = useCallback(
      (e: React.MouseEvent) => {
        if ((e.target as HTMLElement).closest(".lng-node")) return;
        setIsPanning(true);
        panStart.current = { x: e.clientX, y: e.clientY };
        panOrigin.current = { ...pan };
      },
      [pan],
  );

  const onMouseMove = useCallback(
      (e: React.MouseEvent) => {
        if (!isPanning) return;
        setPan({
          x: panOrigin.current.x + (e.clientX - panStart.current.x),
          y: panOrigin.current.y + (e.clientY - panStart.current.y),
        });
      },
      [isPanning],
  );

  const onMouseUp = useCallback(() => setIsPanning(false), []);

  const onWheel = useCallback((e: React.WheelEvent) => {
    // Never zoom when scrolling inside a node card (column list)
    if ((e.target as HTMLElement).closest(".lng-node")) return;
    e.preventDefault();
    setScale((s) => Math.min(2, Math.max(0.25, s - e.deltaY * 0.001)));
  }, []);

  const resetView = () => {
    setScale(0.85);
    setPan({ x: 60, y: 40 });
  };

  // ── Total node count (upstream + root + downstream) ────────────────────────
  const totalNodes = nodes.length;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
      <div className="relative w-full h-full flex flex-col overflow-hidden bg-[#f8f9fb] rounded-xl">

        {/* ── Top bar ── */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 bg-white flex-shrink-0 z-10 gap-3 flex-wrap">
          {/* Search */}
          <div className="relative w-48 flex-shrink-0">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
                className="w-full text-xs pl-7 pr-3 py-1.5 border border-gray-200 rounded-lg bg-gray-50 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-400/30 focus:border-indigo-300 transition-all"
                placeholder="Search nodes..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Title pill */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-50 border border-indigo-200 flex-shrink-0">
            <svg className="w-3.5 h-3.5 text-indigo-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M3 9h18M3 15h18M9 3v18" />
            </svg>
            <span className="text-xs font-semibold text-indigo-700">
            Lineage for <span className="font-bold">{datasetName}</span>
          </span>
            {!isLoading && (
                <span className="text-[10px] text-indigo-400 font-medium">
              · {totalNodes} nodes
            </span>
            )}
            <button className="text-indigo-300 hover:text-indigo-500 ml-1">
              <MoreHorizontal size={13} />
            </button>
          </div>

          {/* Depth / direction controls */}
          <DepthControl
              depth={depth}
              direction={direction}
              onChange={(d, dir) => {
                setDepth(d);
                setDirection(dir);
              }}
          />
        </div>

        {/* ── Canvas ── */}
        <div
            ref={containerRef}
            className="flex-1 relative overflow-hidden"
            style={{
              cursor: isPanning ? "grabbing" : "grab",
              backgroundImage: "radial-gradient(circle, #d1d5db 1px, transparent 1px)",
              backgroundSize: "24px 24px",
            }}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={onMouseUp}
            onWheel={onWheel}
        >
          {/* Loading */}
          {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/70 z-20">
                <div className="flex flex-col items-center gap-3">
                  <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                  <p className="text-sm text-gray-500 font-medium">Building lineage graph…</p>
                </div>
              </div>
          )}

          {/* Error */}
          {error && !isLoading && (
              <div className="absolute inset-0 flex items-center justify-center z-20">
                <div className="flex flex-col items-center gap-3 text-center px-8">
                  <AlertTriangle className="w-10 h-10 text-yellow-400" />
                  <p className="text-sm font-semibold text-gray-700">{error}</p>
                  <button
                      onClick={() => {
                        setError(null);
                        setIsLoading(true);
                        dashboardApiServices
                            .fetchLineageVisual(datasetId, depth, direction)
                            .then((d) => { setApiData(d); setSelectedNode(d.root.id); })
                            .catch(() => setError("Failed to load lineage data."))
                            .finally(() => setIsLoading(false));
                      }}
                      className="text-xs px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                  >
                    Retry
                  </button>
                </div>
              </div>
          )}

          {/* Empty */}
          {!isLoading && !error && nodes.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center z-10">
                <div className="text-center">
                  <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-3">
                    <svg className="w-7 h-7 text-gray-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-gray-400">No lineage data available</p>
                  <p className="text-xs text-gray-300 mt-1">This table has no upstream or downstream connections.</p>
                </div>
              </div>
          )}

          {/* Graph */}
          {!isLoading && !error && nodes.length > 0 && (
              <div
                  style={{
                    transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
                    transformOrigin: "0 0",
                    position: "absolute",
                    willChange: "transform",
                  }}
              >
                <EdgeLayer edges={edges} positions={positions} />

                {visibleNodes.map((node) => (
                    <div
                        key={node.id}
                        className="lng-node"
                        ref={(el) => {
                          if (el && el.offsetHeight !== nodeHeights[node.id]) {
                            setNodeHeights((prev) => ({ ...prev, [node.id]: el.offsetHeight }));
                          }
                        }}
                        style={{
                          position: "absolute",
                          left: node.x,
                          top: node.y,
                          width: node.isCenter ? CENTER_W : CARD_W,
                        }}
                    >
                      <NodeCard
                          node={node}
                          isSelected={selectedNode === node.id}
                          onClick={() =>
                              setSelectedNode(node.id === selectedNode ? null : node.id)
                          }
                      />
                    </div>
                ))}
              </div>
          )}
        </div>

        {/* ── Legend ── */}
        <div className="absolute bottom-14 left-4 bg-white border border-gray-200 rounded-xl shadow-sm px-4 py-3 text-[11px] text-gray-500 pointer-events-none z-10 min-w-[172px]">
          <p className="font-bold text-gray-700 mb-2 uppercase tracking-wide text-[10px]">Legend</p>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2"><span className="text-gray-500">{typeIcon("table")}</span> Table</div>
            <div className="flex items-center gap-2"><span className="text-gray-500">{typeIcon("view")}</span> View</div>
            <div className="flex items-center gap-2"><span className="text-gray-500">{typeIcon("dashboard")}</span> Dashboard / Explore</div>
            <div className="flex items-center gap-2">
              <span className="w-8 h-0.5 bg-indigo-500 rounded inline-block" /> Data flow
            </div>
            <div className="flex items-center gap-2">
              <span className="w-8 border-t border-dashed border-gray-400 inline-block" /> Secondary flow
            </div>
            <div className="flex items-center gap-2">
              <span className="w-4 h-4 rounded-full bg-red-100 border border-red-300 flex items-center justify-center text-red-500 text-[9px] font-black">!</span>
              Data quality issue
            </div>
          </div>
          <p className="font-bold text-gray-700 mt-3 mb-1.5 uppercase tracking-wide text-[10px]">Controls</p>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <kbd className="bg-gray-100 border border-gray-200 rounded px-1 py-0.5 text-[9px] font-mono">Scroll</kbd>
              <span>Zoom in/out</span>
            </div>
            <div className="flex items-center gap-2">
              <kbd className="bg-gray-100 border border-gray-200 rounded px-1 py-0.5 text-[9px] font-mono">Space</kbd>
              <span>+ Drag to pan</span>
            </div>
            <div className="flex items-center gap-2">
              <Sparkles size={11} className="text-indigo-400" />
              <span>Hover node for AI summary</span>
            </div>
          </div>
        </div>

        {/* ── Zoom controls ── */}
        <div className="absolute bottom-4 right-4 flex flex-col gap-1 z-10">
          <button
              onClick={() => setScale((s) => Math.min(2, s + 0.1))}
              className="w-8 h-8 bg-white border border-gray-200 rounded-lg shadow-sm flex items-center justify-center text-gray-500 hover:bg-gray-50 transition-colors"
          >
            <ZoomIn size={14} />
          </button>
          <button
              onClick={() => setScale((s) => Math.max(0.25, s - 0.1))}
              className="w-8 h-8 bg-white border border-gray-200 rounded-lg shadow-sm flex items-center justify-center text-gray-500 hover:bg-gray-50 transition-colors"
          >
            <ZoomOut size={14} />
          </button>
          <button
              onClick={resetView}
              className="w-8 h-8 bg-white border border-gray-200 rounded-lg shadow-sm flex items-center justify-center text-gray-500 hover:bg-gray-50 transition-colors"
          >
            <RotateCcw size={14} />
          </button>
          <button className="w-8 h-8 bg-white border border-gray-200 rounded-lg shadow-sm flex items-center justify-center text-gray-500 hover:bg-gray-50 transition-colors">
            <Maximize2 size={14} />
          </button>
        </div>
      </div>
  );
}
