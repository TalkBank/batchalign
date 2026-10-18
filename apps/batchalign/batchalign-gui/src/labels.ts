import type { VerbStep } from "./store";

export const commandLabel = (verb: VerbStep): string => verb === "diarize" ? "speaker" : verb;
