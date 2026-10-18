/** Keep deployment details secondary to the engine name. */
export default function EngineLabel({ label }: { label: string }) {
  const match = label.match(/^(.*) (\((?:local|cloud)\))$/);
  return match ? <span>{match[1]} <span style={{ color: "var(--fg-muted)" }}>{match[2]}</span></span> : <span>{label}</span>;
}
