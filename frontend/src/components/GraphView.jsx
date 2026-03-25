import React, { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { oneHopSubgraph, toForceGraphData } from "../lib/graph.js";

// ─── Node type registry ───────────────────────────────────────────────────────
const NODE_TYPES = [
  { type: "SalesOrder",       label: "Sales Order",   color: "#6aa9ff", prefix: "SO"   },
  { type: "Delivery",         label: "Delivery",      color: "#7ee787", prefix: "DEL"  },
  { type: "BillingDocument",  label: "Billing",       color: "#fdb022", prefix: "BILL" },
  { type: "JournalEntry",     label: "Journal Entry", color: "#c4a7e7", prefix: "JE"   },
  { type: "Customer",         label: "Customer",      color: "#ff8ccf", prefix: "CUST" },
  { type: "Product",          label: "Product",       color: "#7bdff2", prefix: "PROD" },
];

function getTypeInfo(type) {
  return NODE_TYPES.find((n) => n.type === type) ?? { color: "#cbd5e1", prefix: "" };
}

function prefixedLabel(node) {
  const raw  = String(node.id ?? "");
  const tail = raw.split(":").pop();
  const info = getTypeInfo(node.type);
  return info.prefix ? `${info.prefix}-${tail}` : tail;
}

// ─── Container size hook ──────────────────────────────────────────────────────
function useContainerSize(ref) {
  const [size, setSize] = useState({ width: 800, height: 600 });
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (cr) setSize({ width: Math.max(300, Math.floor(cr.width)), height: Math.max(300, Math.floor(cr.height)) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return size;
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function GraphView({ graph, onSelectNode }) {
  const containerRef = useRef(null);
  const fgRef        = useRef();
  // Track whether we should zoom-to-fit when the engine next stops
  const fitOnStop    = useRef(true);
  const dims         = useContainerSize(containerRef);

  const [selectedId, setSelectedId] = useState(null);
  const [hlNodes,    setHlNodes]    = useState(new Set());
  const [hlLinks,    setHlLinks]    = useState(new Set());

  useEffect(() => {
    setSelectedId(null);
    setHlNodes(new Set());
    setHlLinks(new Set());
    fitOnStop.current = true;
  }, [graph]);

  const displayedGraph = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] };
    if (!selectedId) return graph;
    return oneHopSubgraph(graph, selectedId);
  }, [graph, selectedId]);

  const forceGraphData = useMemo(() => toForceGraphData(displayedGraph), [displayedGraph]);

  // Tune forces each time data changes, reset fit flag
  useEffect(() => {
    if (!fgRef.current) return;
    fgRef.current.d3Force("charge").strength(-500);
    fgRef.current.d3Force("link").distance(110);
    fgRef.current.d3Force("center")?.strength(0.06);
    fitOnStop.current = true;
  }, [forceGraphData]);

  // ─── Node click ──────────────────────────────────────────────────────────────
  function handleNodeClick(node) {
    const id = node?.id;
    if (!id) return;

    if (selectedId === id) {
      setSelectedId(null);
      setHlNodes(new Set());
      setHlLinks(new Set());
      if (onSelectNode) onSelectNode(null);
      return;
    }

    setSelectedId(id);
    if (onSelectNode) onSelectNode(node);

    const nodeSet = new Set([id]);
    const linkSet = new Set();
    (forceGraphData.links ?? []).forEach((lnk) => {
      const src = lnk.source?.id ?? lnk.source;
      const tgt = lnk.target?.id ?? lnk.target;
      if (src === id || tgt === id) {
        nodeSet.add(src);
        nodeSet.add(tgt);
        linkSet.add(lnk);
      }
    });
    setHlNodes(nodeSet);
    setHlLinks(linkSet);
  }

  return (
    <div ref={containerRef} style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden" }}>

      {/* Legend */}
      <div style={{
        position: "absolute", top: 12, left: 12, zIndex: 10,
        background: "rgba(255,255,255,0.93)", border: "1px solid rgba(0,0,0,0.08)",
        borderRadius: 10, padding: "10px 14px",
        boxShadow: "0 4px 14px rgba(0,0,0,0.07)", backdropFilter: "blur(6px)",
      }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.6px" }}>Legend</div>
        {NODE_TYPES.map((nt) => (
          <div key={nt.type} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
            <div style={{ width: 11, height: 11, borderRadius: "50%", background: nt.color, flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: "#1e293b", fontWeight: 500 }}>{nt.label}</span>
            <span style={{ fontSize: 10, color: "#94a3b8", fontFamily: "monospace" }}>{nt.prefix}-</span>
          </div>
        ))}
      </div>

      {/* Zoom controls */}
      <div style={{ position: "absolute", bottom: 16, right: 16, display: "flex", flexDirection: "column", gap: 6, zIndex: 10 }}>
        {[
          { label: "+", title: "Zoom in",     fn: () => fgRef.current?.zoom(fgRef.current.zoom() * 1.35, 250) },
          { label: "−", title: "Zoom out",    fn: () => fgRef.current?.zoom(fgRef.current.zoom() * 0.75, 250) },
          { label: "⤢", title: "Fit to view", fn: () => { fitOnStop.current = false; fgRef.current?.zoomToFit(400, 60); } },
        ].map(({ label, title, fn }) => (
          <button key={label} title={title} onClick={fn} style={{
            width: 36, height: 36, borderRadius: "50%", padding: 0, cursor: "pointer",
            background: "rgba(255,255,255,0.95)", border: "1px solid rgba(0,0,0,0.1)",
            boxShadow: "0 2px 8px rgba(0,0,0,0.08)", fontSize: 18, fontWeight: 700,
            color: "#1e293b", display: "flex", alignItems: "center", justifyContent: "center",
          }}>{label}</button>
        ))}
      </div>

      <ForceGraph2D
        ref={fgRef}
        graphData={forceGraphData}
        width={dims.width}
        height={dims.height}
        nodeId="id"
        enableNodeDrag
        enableZoomInteraction
        enablePanInteraction
        // Pre-warm enough ticks so nodes start spread out, then let a short cooldown
        // period play out naturally (smooth settle animation)
        warmupTicks={160}
        cooldownTicks={60}
        d3AlphaDecay={0.025}        // gradual cool-down → natural settle
        d3VelocityDecay={0.4}       // moderate damping so nodes slow smoothly
        onEngineStop={() => {
          // Only auto-fit on the first run after data loads, not after user interaction
          if (fitOnStop.current && fgRef.current) {
            fitOnStop.current = false;
            fgRef.current.zoomToFit(300, 70);
          }
        }}
        linkDirectionalParticles={1}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleWidth={(lnk) => hlLinks.has(lnk) ? 3 : 1.5}
        linkWidth={(lnk) => hlLinks.has(lnk) ? 3 : 1.8}
        linkColor={(lnk) => hlLinks.has(lnk) ? "#3b82f6" : "rgba(0,0,0,0.12)"}
        onNodeClick={handleNodeClick}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label      = prefixedLabel(node);
          const isSelected = selectedId === node.id;
          const isDimmed   = hlNodes.size > 0 && !hlNodes.has(node.id);
          const { color }  = getTypeInfo(node.type);
          const BASE       = isSelected ? 11 : 8;
          const r          = BASE / globalScale;

          ctx.globalAlpha = isDimmed ? 0.2 : 1;

          // Blue glow ring when selected
          if (isSelected) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 5 / globalScale, 0, 2 * Math.PI);
            ctx.fillStyle = `${color}30`;
            ctx.fill();
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 3.5 / globalScale, 0, 2 * Math.PI);
            ctx.strokeStyle = "#3b82f6";
            ctx.lineWidth = 2.5 / globalScale;
            ctx.stroke();
          }

          // Node body
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.lineWidth = (isSelected ? 2 : 1) / globalScale;
          ctx.strokeStyle = isSelected ? "#1d4ed8" : "rgba(0,0,0,0.15)";
          ctx.stroke();

          // Label — only render once zoomed in enough
          if (label && globalScale > 0.4) {
            const fontSize = Math.max(9, 11 / globalScale);
            ctx.font = `700 ${fontSize}px "Inter","Segoe UI",sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.shadowColor = "rgba(255,255,255,0.95)";
            ctx.shadowBlur = 5;
            ctx.fillStyle = "#0f172a";
            ctx.fillText(label, node.x, node.y + r + 3 / globalScale);
            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
          }

          ctx.globalAlpha = 1;
        }}
        nodePointerAreaPaint={(node, color, ctx, globalScale) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 12 / globalScale, 0, 2 * Math.PI);
          ctx.fill();
        }}
      />
    </div>
  );
}
