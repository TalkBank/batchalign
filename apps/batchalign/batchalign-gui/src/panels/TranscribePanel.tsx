import { ASR_LABELS, ASR_NOTES, availableAsr, recommendedAsr, selectedAsr } from "../asrEngines";
// transcribe panel — picks language, engine, speaker count, diarize.
// Engines list comes from the live daemon's `/capabilities` ASR set.

import { useStore, type VerbConfig } from "../store";
import LanguageInput from "../components/LanguageInput";
import EngineLabel from "../components/EngineLabel";
import FieldRow from "../components/FieldRow";
import RadioGroup from "../components/RadioGroup";
import Toggle from "../components/Toggle";

interface Props {
  batchId: string;
  config: VerbConfig;
}

const PRETTY_SPEAKER: Record<string, string> = {
  PyannoteAIBackend: "pyannoteAI (cloud)",
  PyannoteBackend: "Pyannote (local)",
};

export default function TranscribePanel({ batchId, config }: Props) {
  const { capabilities, dispatch } = useStore();
  const lang = (config.lang as string) ?? "";
  const asrEngines = availableAsr(lang, capabilities?.backends_by_task["ASR"]);
  const recommended = recommendedAsr(lang, capabilities?.backends_by_task["ASR"]);
  const speakerEngines = (
    capabilities?.backends_by_task["Speaker"] ??
    ["PyannoteAIBackend", "PyannoteBackend"]
  ).filter((name) => name.startsWith("Pyannote"));

  const set = (patch: VerbConfig) =>
    dispatch({
      type: "VERB_CONFIG_CHANGED",
      batchId,
      verb: "transcribe",
      patch,
    });

  const speakers = (config.speakers as number) ?? 2;
  const engine = selectedAsr(lang, config.engine as string, capabilities?.backends_by_task["ASR"]);
  const diarize = (config.diarize as boolean) ?? true;
  const nativeSpeaker = engine === "RevAI" || engine === "GoogleGenAIBackend";
  const diarizeEngine =
    (config.diarize_engine as string) ?? "PyannoteAIBackend";

  return (
    <div>
      <FieldRow label="language">
        <LanguageInput value={lang} onChange={value => set({ lang: value })} />
      </FieldRow>
      <FieldRow label="speakers">
        <input
          className="ba-input ba-num"
          type="number"
          value={speakers}
          onChange={(e) => set({ speakers: Number(e.target.value) })}
          style={{ width: 70 }}
        />
      </FieldRow>
      <FieldRow label="engine">
        {!asrEngines.length && <span>Enter a language to see recommended engines.</span>}
        {recommended.length > 0 && <div role="group" aria-label="Recommended engines" style={{
          background: "var(--gray-1)", borderRadius: 8, padding: "10px 12px", marginBottom: 10,
        }}>
          <div style={{ fontSize: "var(--fs-xs)", color: "var(--fg-muted)", marginBottom: 6 }}>Recommended</div>
          <RadioGroup value={engine} options={recommended.map(e => [e, ASR_LABELS[e]])}
            descriptions={ASR_NOTES} onChange={value => set({ engine: value })} />
        </div>}
        <RadioGroup
          value={engine}
          options={asrEngines.filter(e => !recommended.includes(e)).map(e => [e, ASR_LABELS[e]])}
          onChange={value => set({ engine: value })}
        />
      </FieldRow>
      <FieldRow label="Speaker recognition">
        <Toggle on={diarize} onChange={(on) => set({ diarize: on })} />
      </FieldRow>
      {diarize && engine && !nativeSpeaker && (
        <FieldRow label="Recognition engine">
          <RadioGroup
            value={diarizeEngine}
            options={speakerEngines.map((name) => [
              name,
              PRETTY_SPEAKER[name] ?? name,
            ])}
            onChange={(value) => set({ diarize_engine: value })}
          />
        </FieldRow>
      )}
      {diarize && engine && nativeSpeaker && (
        <FieldRow label="Recognition engine">
          <EngineLabel label={ASR_LABELS[engine] ?? engine} />
        </FieldRow>
      )}
    </div>
  );
}
