// Centered dropzone for the empty state. "Open folder…" button uses the
// Tauri dialog plugin; the parent then dispatches BATCH_OPENED.

import { open } from "@tauri-apps/plugin-dialog";
import { openFolder } from "../folders";
import { useState } from "react";

// No default pipeline — the user chooses every step themselves so the
// chain reflects exactly what they intend to run. PipelineBlock renders
// an "+ add command" affordance for the empty case.

export default function DropZone({ dragging = false }: { dragging?: boolean }) {
  const [error, setError] = useState<string | null>(null);

  const onOpen = async () => {
    try {
      setError(null);
      const selected = await open({ directory: true, multiple: false });
      if (typeof selected === "string") await openFolder(selected);
    } catch (error) { setError(String(error)); }
  };


  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 40,
      }}
    >
      <div
        style={{
          width: 520,
          background: dragging ? "var(--bg-tinted)" : "var(--bg)",
          border: `2px dashed ${dragging ? "var(--dark-blue)" : "var(--gray-2)"}`,
          boxShadow: dragging ? "0 0 0 4px var(--gray-1)" : "none",
          transition: "background 120ms, border-color 120ms, box-shadow 120ms",
          borderRadius: "var(--r-1)",
          padding: "36px 28px 28px",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 28,
            color: dragging ? "var(--dark-blue)" : "var(--gray-3)",
            lineHeight: 1,
            marginBottom: 14,
          }}
        >
          ↓
        </div>
        <div
          style={{
            fontFamily: "var(--font-sans)",
            fontWeight: 600,
            fontSize: 22,
            color: "var(--fg)",
            lineHeight: 1.15,
            marginBottom: 6,
          }}
        >
          drop a folder
        </div>
        <div
          style={{
            fontSize: "var(--fs-sm)",
            color: "var(--fg-muted)",
            marginBottom: 22,
          }}
        >
          folders are searched recursively.
        </div>
        <button
          type="button"
          className="ba-btn ba-btn--primary"
          onClick={onOpen}
          style={{ minWidth: 160 }}
        >
          open folder…
        </button>
        {error && <p role="alert">Could not open folder: {error}</p>}
      </div>
    </div>
  );
}
