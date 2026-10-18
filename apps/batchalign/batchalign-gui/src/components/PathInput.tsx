// Mono-font path input + a "choose…" button. Wraps Tauri dialog plugin
// (open) so it works in dev and bundle paths identically.

import { open } from "@tauri-apps/plugin-dialog";
import type { ReactNode } from "react";

interface Props {
  value: string;
  onChange?: (path: string) => void;
  directory?: boolean;
  onChoose?: (path: string) => void;
  disabled?: boolean;
  children?: ReactNode;
}

export default function PathInput({ value, onChange, onChoose, directory, disabled, children }: Props) {
  const choose = async () => {
    const selected = await open({
      directory: !!directory,
      multiple: false,
    });
    if (typeof selected === "string") (onChoose ?? onChange)?.(selected);
  };
  return (
    <div style={{ display: "flex", gap: 6 }}>
      <input
        className="ba-input ba-input--mono"
        value={value}
        readOnly={!onChange}
        disabled={disabled}
        onChange={(e) => onChange?.(e.target.value)}
        style={{ flex: 1, minWidth: 0 }}
      />
      <button
        type="button"
        className="ba-btn ba-btn--sm"
        onClick={choose}
        disabled={disabled}
        style={{ padding: "3px 10px" }}
      >
        choose…
      </button>
      {children}
    </div>
  );
}
