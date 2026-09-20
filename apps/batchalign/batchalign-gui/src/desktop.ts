import { type Batch, type SettingsState, type VerbConfig, type VerbStep } from './store';
import { filterFilesForVerb } from './hooks/useFilteredFiles';

export function buildRecipeKwargs(
  verb: VerbStep,
  config: VerbConfig,
): Record<string, unknown> {
  switch (verb) {
    case "transcribe": {
      const engine = (config.engine as string) || "WhisperBackend";
      const lang = (config.lang as string) || "eng";
      const speakers = (config.speakers as number) ?? 2;
      const diarize = (config.diarize as boolean) ?? true;
      const nativeSpeaker = engine === "RevAI" || engine === "GoogleGenAIBackend";
      const asrKwargs: Record<string, unknown> = { language: lang };
      if (nativeSpeaker) asrKwargs.num_speakers = speakers;
      const out: Record<string, unknown> = {
        asr_backend: { kind: engine, kwargs: asrKwargs },
      };
      if (diarize) {
        if (nativeSpeaker) {
          out.diarize = true;
        } else {
          out.speaker_backend = {
            kind: (config.diarize_engine as string) || "PyannoteBackend",
            kwargs: { num_speakers: speakers },
          };
        }
      }
      return out;
    }
    case "diarize":
      return {
        speaker_backend: {
          kind: (config.engine as string) || "PyannoteBackend",
          kwargs: { num_speakers: (config.speakers as number) ?? 0 },
        },
      };
    case "align":
      return {
        fa_backend: {
          kind: (config.aligner as string) || "Wav2Vec2FaBackend",
          kwargs: {},
        },
      };
    case "morphotag":
      return {
        stanza_backend: {
          kind: "StanzaBackend",
          kwargs: { retokenize: (config.retokenize as boolean) ?? true },
        },
      };
    case "translate":
      return {
        translate_backend: {
          kind: (config.engine as string) || "GoogleTranslateBackend",
          kwargs: { target: (config.target as string) || "eng" },
        },
      };
    case "compare":
      return {
        stanza_backend: {
          kind: "StanzaBackend",
          kwargs: { lang: (config.lang as string) || "eng" },
        },
      };
  }
}


export function buildDesktopRequest(batch: Batch, settings: SettingsState) {
  return {
    folder: batch.folderPath,
    source_ids: filterFilesForVerb(batch.files, batch.fileOrder, batch.pipeline[0]),
    steps: batch.pipeline.map(recipe => ({
      recipe,
      kwargs: buildRecipeKwargs(recipe, batch.config[recipe]),
      gold_path: recipe === 'compare' ? batch.config.compare.gold_path || null : null,
      use_cache: batch.config[recipe].use_cache ?? true,
      strip_word_timing: recipe === 'align' && batch.config.align.write_wor === false,
    })),
    in_place: batch.inPlace,
    output_path: batch.outputPath,
    workers: settings.defaultWorkers,
    force_cpu: settings.forceCpu,
  };
}
