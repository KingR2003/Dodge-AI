import React from "react";

const TYPE_COLORS = {
  SalesOrder:      "#6aa9ff",
  Delivery:        "#7ee787",
  BillingDocument: "#fdb022",
  JournalEntry:    "#c4a7e7",
  Customer:        "#ff8ccf",
  Product:         "#7bdff2",
};

/** Format camelCase / snake_case keys into readable labels */
function formatKey(key) {
  return key
    .replace(/_/g, " ")
    .replace(/([A-Z])/g, " $1")
    .replace(/^\w/, (c) => c.toUpperCase())
    .trim();
}

export default function NodeDetails({ node, onClear }) {
  if (!node) {
    return (
      <div style={{ color: "#94a3b8", fontSize: 14, lineHeight: 1.7 }}>
        Click a node in the graph to see its details.<br />
        Click again to collapse back to the full graph.
      </div>
    );
  }

  const dotColor = TYPE_COLORS[node.type] ?? "#cbd5e1";
  const meta     = node.metadata ?? {};
  const entries  = Object.entries(meta).filter(([, v]) => v != null && v !== "");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 13, height: 13, borderRadius: "50%", flexShrink: 0,
          background: dotColor, boxShadow: `0 0 0 2.5px ${dotColor}44`,
        }} />
        <span style={{ fontWeight: 700, fontSize: 15, color: "#0f172a", flex: 1 }}>
          {node.type}
        </span>
        {onClear && (
          <button onClick={onClear} style={{ fontSize: 11, padding: "4px 10px", flexShrink: 0 }}>
            Clear
          </button>
        )}
      </div>

      {/* ID badge */}
      <div style={{
        fontFamily: "monospace", fontSize: 11.5, color: "#475569",
        background: "#f1f5f9", border: "1px solid rgba(0,0,0,0.06)",
        borderRadius: 6, padding: "5px 10px", wordBreak: "break-all", lineHeight: 1.5,
      }}>
        {node.id}
      </div>

      {/* Metadata fields */}
      {entries.length > 0 ? (
        <div style={{
          display: "flex", flexDirection: "column", gap: 0,
          overflowY: "auto", maxHeight: 220,
          border: "1px solid rgba(0,0,0,0.06)", borderRadius: 8,
        }}>
          {entries.map(([k, v], i) => (
            <div key={k} style={{
              display: "flex", flexDirection: "column",
              padding: "8px 12px",
              background: i % 2 === 0 ? "#ffffff" : "#f8fafc",
              borderBottom: i < entries.length - 1 ? "1px solid rgba(0,0,0,0.05)" : "none",
            }}>
              <span style={{
                fontSize: 10.5, fontWeight: 700, color: "#64748b",
                textTransform: "uppercase", letterSpacing: "0.4px", marginBottom: 2,
              }}>
                {formatKey(k)}
              </span>
              <span style={{
                fontSize: 13, color: "#0f172a", wordBreak: "break-word",
                lineHeight: 1.4,
              }}>
                {String(v)}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ color: "#94a3b8", fontSize: 13 }}>No metadata available.</div>
      )}
    </div>
  );
}
