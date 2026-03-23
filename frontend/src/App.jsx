import React, { useEffect, useMemo, useState } from "react";
import { fetchGraph } from "./lib/api.js";
import GraphView from "./components/GraphView.jsx";
import ChatView from "./components/ChatView.jsx";
import NodeDetails from "./components/NodeDetails.jsx";

export default function App() {
  const [graph, setGraph] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  const [billingDocInput, setBillingDocInput] = useState("");
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [graphError, setGraphError] = useState(null);

  const graphDocValue = useMemo(() => billingDocInput.trim(), [billingDocInput]);

  async function loadGraph({ billing_document } = {}) {
    setGraphError(null);
    setLoadingGraph(true);
    try {
      const data = await fetchGraph({
        billing_document: billing_document || undefined,
        include_journal_entry: false,
        include_payments: false,
      });
      setGraph(data);
      setSelectedNode(null);
    } catch (e) {
      setGraphError(e?.message || "Failed to load graph");
    } finally {
      setLoadingGraph(false);
    }
  }

  useEffect(() => {
    // Load a default graph on first render.
    loadGraph({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="app">
      <div className="topbar">
        <h1>SAP O2C Graph Explorer</h1>
      </div>

      <div className="content">
        <div className="leftCol">
          <div className="panel" style={{ flex: 1, minHeight: 0 }}>
            <div className="panelHeader">
              <div className="title">Graph</div>
              <div className="row" style={{ alignItems: "center" }}>
                <input
                  type="text"
                  value={billingDocInput}
                  onChange={(e) => setBillingDocInput(e.target.value)}
                  placeholder="billing document (optional)"
                  aria-label="billing document"
                  style={{ width: 240 }}
                />
                <button
                  className="primary"
                  onClick={() => loadGraph({ billing_document: graphDocValue || undefined })}
                  disabled={loadingGraph}
                >
                  {loadingGraph ? "Loading..." : "Load"}
                </button>
              </div>
            </div>

            <div className="panelBody" style={{ padding: 0 }}>
              {graphError ? (
                <div style={{ padding: 12, color: "rgba(255,106,106,0.9)" }}>{graphError}</div>
              ) : null}
              {!graphError && !graph ? (
                <div style={{ padding: 12, color: "rgba(255,255,255,0.75)" }}>Loading graph...</div>
              ) : null}
              <div style={{ width: "100%", height: "100%", overflow: "hidden" }}>
                <GraphView
                  graph={graph}
                  onSelectNode={(n) => setSelectedNode(n)}
                />
              </div>
            </div>
          </div>

          <div className="panel" style={{ flex: 0.6, minHeight: 0 }}>
            <div className="panelHeader">
              <div className="title">Node Details</div>
              {selectedNode ? (
                <button onClick={() => setSelectedNode(null)}>Clear</button>
              ) : null}
            </div>
            <div className="panelBody">
              <NodeDetails node={selectedNode} onClear={() => setSelectedNode(null)} />
            </div>
          </div>
        </div>

        <div className="panel" style={{ height: "100%" }}>
          <div className="panelHeader">
            <div className="title">Chat</div>
          </div>
          <div className="panelBody" style={{ padding: 0 }}>
            <ChatView onGraphUpdate={(g) => setGraph(g)} />
          </div>
        </div>
      </div>
    </div>
  );
}

