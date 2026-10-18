import { useId, useState } from "react";
import { languageCode, languageSuggestions } from "../languages";

export default function LanguageInput({ value, onChange, label = "language" }: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [touched, setTouched] = useState(false);
  const [active, setActive] = useState(-1);
  const suggestions = languageSuggestions(value);
  const invalid = !languageCode(value) && (touched || value.trim().length >= 3);
  const choose = (code: string) => {
    onChange(code);
    setOpen(false);
    setActive(-1);
  };
  return (
    <div style={{ position: "relative", width: "100%", maxWidth: 440 }}>
      <input
        className="ba-input"
        role="combobox"
        aria-label={label}
        aria-autocomplete="list"
        aria-expanded={open && suggestions.length > 0}
        aria-controls={`${id}-list`}
        aria-activedescendant={open && active >= 0 ? `${id}-${active}` : undefined}
        aria-invalid={invalid}
        aria-describedby={invalid ? `${id}-error` : undefined}
        autoCorrect="off"
        autoCapitalize="none"
        autoComplete="off"
        spellCheck={false}
        placeholder="click and enter a three-letter language code."
        value={value}
        style={{ width: "100%" }}
        onFocus={() => setOpen(true)}
        onBlur={() => { setOpen(false); setTouched(true); }}
        onChange={event => { onChange(event.target.value); setOpen(true); setActive(-1); }}
        onKeyDown={event => {
          if (event.key === "Escape") { setOpen(false); setActive(-1); }
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true);
            setActive(index => Math.max(0, Math.min(suggestions.length - 1, index + (event.key === "ArrowDown" ? 1 : -1))));
          }
          if (event.key === "Enter" && open && suggestions[active]) {
            event.preventDefault();
            choose(suggestions[active][0]);
          }
        }}
      />
      {open && suggestions.length > 0 && (
        <div id={`${id}-list`} role="listbox" aria-label="Language codes" style={{
          position: "absolute", top: "100%", left: 0, right: 0, zIndex: 20,
          background: "var(--surface)", border: "1px solid var(--gray-2)",
          borderRadius: 6, maxHeight: 240, overflowY: "auto", boxShadow: "0 4px 12px #0002",
        }}>
          {suggestions.map(([code, name], index) => (
            <div key={code} id={`${id}-${index}`} role="option" aria-selected={index === active}
              onMouseDown={event => event.preventDefault()}
              onClick={() => choose(code)}
              style={{ padding: "6px 10px", cursor: "pointer", background: index === active ? "var(--gray-1)" : undefined }}>
              <span className="ba-mono">{code}</span> — {name}
            </div>
          ))}
        </div>
      )}
      {invalid && <div id={`${id}-error`} role="alert" style={{ fontSize: "var(--fs-sm)", marginTop: 4 }}>
        Enter a valid three-letter language code, such as eng, zho, or yue.
      </div>}
    </div>
  );
}
