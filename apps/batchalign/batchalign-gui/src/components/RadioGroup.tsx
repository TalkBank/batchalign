// Vertical radio group. Used by panels for engine selection etc.
import EngineLabel from "./EngineLabel";

interface Props {
  value: string;
  options: Array<[string, string]>;
  descriptions?: Record<string, string>;
  onChange?: (v: string) => void;
}

export default function RadioGroup({ value, options, descriptions, onChange }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {options.map(([v, label]) => (
        <label
          key={v}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 7,
            fontSize: "var(--fs-sm)",
            cursor: onChange ? "pointer" : "default",
          }}
        >
          <input
            type="radio"
            checked={value === v}
            onChange={() => onChange?.(v)}
            aria-label={label}
            style={{
              width: 12,
              height: 12,
              appearance: "none",
              margin: 0,
              borderRadius: "50%",
              border: "1px solid var(--gray-3)",
              background:
                value === v ? "var(--dark-blue)" : "var(--surface)",
              boxShadow:
                value === v ? "inset 0 0 0 2.5px var(--surface)" : "none",
              flexShrink: 0,
            }}
          />
          <EngineLabel label={label} />
          {descriptions?.[v] && <span style={{ color: "var(--fg-muted)", fontSize: "var(--fs-xs)" }}>{descriptions[v]}</span>}
        </label>
      ))}
    </div>
  );
}
