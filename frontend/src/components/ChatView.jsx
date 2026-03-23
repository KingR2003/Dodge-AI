import React, { useState } from "react";
import { postChat } from "../lib/api.js";

export default function ChatView({ onGraphUpdate }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function send() {
    const q = question.trim();
    if (!q || busy) return;

    setError(null);
    setBusy(true);
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setQuestion("");

    try {
      const data = await postChat(q);
      const answer = data?.answer || "No relevant data found";
      setMessages((prev) => [...prev, { role: "assistant", text: answer }]);
      if (data?.graph && onGraphUpdate) {
        onGraphUpdate(data.graph);
      }
    } catch (e) {
      const msg = e?.message || "Chat request failed";
      setError(msg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "No relevant data found" },
      ]);
    } finally {
      setBusy(false);
    }
  }

  const formatMessage = (text) => {
    if (!text) return "";
    // Simple bolding: **text** -> <strong>text</strong>
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div className="chat">
      <div className="chatMessages">
        {messages.length === 0 ? (
          <div className="msg">
            <div className="role">hint</div>
            <div className="text">
              {formatMessage("Ask questions like **Which products have the highest number of billing documents?** or **Trace billing document 90504248**.")}
            </div>
          </div>
        ) : null}
        {messages.map((m, idx) => (
          <div key={idx} className={`msg ${m.role === "user" ? "user" : ""}`}>
            <div className="role">{m.role}</div>
            <div className="text">{formatMessage(m.text)}</div>
          </div>
        ))}
        {error ? (
          <div className="msg" style={{ borderColor: "rgba(255,106,106,0.6)" }}>
            <div className="role">error</div>
            <div className="text">{formatMessage(error)}</div>
          </div>
        ) : null}
      </div>

      <div className="chatComposer">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={busy ? "Processing..." : "Type your question..."}
          disabled={busy}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button className="primary" onClick={send} disabled={busy}>
          {busy ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}

