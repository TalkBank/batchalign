import { useStore, type FileRow, type VerbStep } from "../store";

/** Alignment/diarization consume CHAT and locate media using its source path.
 * Comparison consumes a main CHAT; the configured gold directory or sibling
 * gold transcript is resolved by the daemon. Golds are never primary inputs.
 */
export function filterFilesForVerb(
  files: Record<string, FileRow>, fileOrder: string[], verb: VerbStep,
): string[] {
  return fileOrder.filter(id => {
    const file = files[id];
    if (!file) return false;
    return verb === "transcribe" ? file.kind === "media"
      : file.kind === "chat" && !/\.gold\.cha$/i.test(file.filename);
  });
}

export function useFilteredFiles(): string[] {
  const { activeBatchId, batches } = useStore();
  const batch = activeBatchId ? batches[activeBatchId] : null;
  if (!batch?.pipeline.length) return [];
  return filterFilesForVerb(batch.files, batch.fileOrder, batch.pipeline[0]);
}
