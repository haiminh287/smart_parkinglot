import { useState, useEffect } from "react";
import webLogger from "@/lib/webLogger";

/**
 * DevLogPanel — floating dev tool (bottom-right corner)
 * Shows live entry count, lets you download the full session log or clear it.
 * Only renders in dev mode (import.meta.env.DEV).
 */
export function DevLogPanel() {
  const [count, setCount] = useState(0);
  const [expanded, setExpanded] = useState(false);

  // Refresh count every 2 s
  useEffect(() => {
    const id = setInterval(() => setCount(webLogger.count()), 2000);
    return () => clearInterval(id);
  }, []);

  if (!import.meta.env.DEV) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: 12,
        right: 12,
        zIndex: 99999,
        fontFamily: "monospace",
        fontSize: 12,
        userSelect: "none",
      }}
    >
      {expanded ? (
        <div
          style={{
            background: "#0f172a",
            color: "#e2e8f0",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "8px 10px",
            minWidth: 220,
            boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 6,
            }}
          >
            <span style={{ color: "#38bdf8", fontWeight: "bold" }}>
              📋 Dev Logs
            </span>
            <button
              onClick={() => setExpanded(false)}
              style={{
                background: "none",
                border: "none",
                color: "#94a3b8",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              ✕
            </button>
          </div>

          <div style={{ color: "#94a3b8", marginBottom: 8 }}>
            {count} entries this session
          </div>

          <button
            onClick={() => webLogger.download()}
            style={{
              display: "block",
              width: "100%",
              marginBottom: 6,
              padding: "4px 8px",
              background: "#0ea5e9",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            ⬇ Download .log
          </button>

          <button
            onClick={() => {
              webLogger.clear();
              setCount(0);
            }}
            style={{
              display: "block",
              width: "100%",
              padding: "4px 8px",
              background: "#334155",
              color: "#e2e8f0",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            🗑 Clear
          </button>
        </div>
      ) : (
        <button
          onClick={() => setExpanded(true)}
          title="Dev Logs"
          style={{
            background: "#0f172a",
            color: "#38bdf8",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "4px 10px",
            cursor: "pointer",
            fontSize: 12,
            boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
          }}
        >
          📋 {count}
        </button>
      )}
    </div>
  );
}
