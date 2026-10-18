import { scanFolder } from "./discovery";
import { dispatch, getAppState, type Batch } from "./store";

export async function openFolder(path: string) {
  const checkIdle = () => {
    if (Object.values(getAppState().batches).some(batch => batch.state === "running")) {
      throw new Error("Wait for the current batch to finish before opening another folder.");
    }
  };
  checkIdle();
  const rows = await scanFolder(path);
  checkIdle();
  const files = Object.fromEntries(rows.map(file => [file.source_id, file]));
  const fileOrder = rows.map(file => file.source_id);

  const batchId = `b-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 6)}`;
  const name = path.split(/[\\/]/).pop() ?? "batch";
  const batch: Batch = {
    id: batchId,
    name,
    folderPath: path,
    inPlace: true,
    outputPath: null,
    pipeline: [],
    config: {
      transcribe: {},
      diarize: {},
      align: {},
      morphotag: {},
      translate: {},
      compare: {},
    },
    files,
    fileOrder,
    state: "idle",
    jobId: null,
    startedAt: null,
    finishedAt: null,
    expandedFileId: null,
  };
  // The GUI shows one folder at a time. Replace it only after a successful scan.
  for (const id of getAppState().tabOrder) dispatch({ type: "BATCH_CLOSED", batchId: id });
  dispatch({ type: "BATCH_OPENED", batch });
}
