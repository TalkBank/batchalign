import { languageCode } from "./languages";

/** Curated GUI choices; CLI/API engines are unchanged. */
export const ASR_LABELS: Record<string, string> = {
  AliyunAsrBackend: "Aliyun (cloud)",
  ChatWhisperBackend: "CHAT-Whisper (local)",
  FunAsrBackend: "FunASR (local)",
  FunAudioBackend: "Paraformer-zh (local)",
  GoogleGenAIBackend: "Google GenAI (cloud)",
  OpenAIWhisperBackend: "OpenAI Whisper (local)",
  Qwen3AsrBackend: "Qwen3 (local)",
  RevAI: "Rev.AI (cloud)",
};
export const ASR_NOTES: Record<string, string> = {
  AliyunAsrBackend: "Adult Cantonese",
  FunAsrBackend: "Child Cantonese",
};
const GENERAL = ["RevAI", "GoogleGenAIBackend", "OpenAIWhisperBackend", "Qwen3AsrBackend"];
const CLOUD = new Set(["AliyunAsrBackend", "GoogleGenAIBackend", "RevAI"]);
const cloudFirst = (a: string, b: string) => Number(CLOUD.has(b)) - Number(CLOUD.has(a));
export const asrLanguage = languageCode;

export function availableAsr(raw: string, available?: string[]): string[] {
  if (!asrLanguage(raw)) return [];
  return Object.keys(ASR_LABELS).filter(engine => engine === "RevAI" || !available ||
    available.includes(engine === "FunAsrBackend" ? "FunAudioBackend" : engine)).sort(cloudFirst);
}
export function recommendedAsr(raw: string, available?: string[]): string[] {
  const language = asrLanguage(raw);
  const specific = language === "eng" ? ["ChatWhisperBackend"]
    : language === "yue" ? ["AliyunAsrBackend", "FunAsrBackend"]
    : language === "zho" || language === "cmn" ? ["FunAudioBackend"] : GENERAL;
  const choices = availableAsr(raw, available);
  const recommended = specific.filter(engine => choices.includes(engine));
  if (!choices.length) return [];
  if (!recommended.some(engine => CLOUD.has(engine))) recommended.push("RevAI");
  if (!recommended.some(engine => !CLOUD.has(engine))) {
    const local = ["OpenAIWhisperBackend", "Qwen3AsrBackend"].find(engine => choices.includes(engine));
    if (local) recommended.push(local);
  }
  return recommended.sort(cloudFirst);
}
export function selectedAsr(language: string, engine?: string, available?: string[]): string {
  return engine && availableAsr(language, available).includes(engine) ? engine : "";
}
