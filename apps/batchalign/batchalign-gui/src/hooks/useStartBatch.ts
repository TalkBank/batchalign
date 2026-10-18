import { selectedAsr } from "../asrEngines";
import { invoke } from "@tauri-apps/api/core";
import { submitDesktopJob, fetchJobStatus } from "../api";
import { useStore, getAppState, dispatch } from "../store";
import { filterFilesForVerb } from "./useFilteredFiles";
import { buildDesktopRequest } from "../desktop";

// Synchronous latch closes the gap before React renders the running state.
const submitting = new Set<string>();

export async function startBatch(batchId: string): Promise<void> {
  const { batches, settings, capabilities } = getAppState();
  const batch = batches[batchId];
  if (!batch || batch.needsDiscovery || !batch.pipeline.length || batch.state === "running" || submitting.has(batchId)) return;
  const request = buildDesktopRequest(batch, settings, capabilities?.backends_by_task["ASR"]);
  if (!request.source_ids.length || (batch.pipeline.includes("transcribe") && !selectedAsr(
    (batch.config.transcribe.lang as string) || "", batch.config.transcribe.engine as string,
    getAppState().capabilities?.backends_by_task["ASR"],
  ))) return;
  submitting.add(batchId);
  const files = request.source_ids.map(id => ({
    ...batch.files[id], status: "queued" as const, log: [],
    stages: batch.pipeline.map(verb => ({ verb, state: "queued" as const, pct: 0 })),
  }));
  dispatch({ type: "BATCH_STARTED", batchId, jobId: "", files });
  let jobId = "";
  try {
    const job = await submitDesktopJob(request);
    jobId = job.job_id;
    dispatch({ type: "BATCH_STARTED", batchId, jobId, files });
    // Status remains authoritative even if an SSE connection closes early.
    // A progress transport problem must never mark the daemon itself failed.
    void invoke("start_batch_pump", { batchId, jobId }).catch(console.error);
    let consecutivePollFailures = 0;
    while (getAppState().batches[batchId]?.jobId === jobId) {
      let status;
      try {
        status = await fetchJobStatus(jobId);
        consecutivePollFailures = 0;
      } catch (error) {
        // Retry only reads: resubmitting the job could duplicate writes while
        // the daemon is still processing it. Bound retries for a dead daemon.
        if (++consecutivePollFailures >= 5) throw error;
        await new Promise(resolve => setTimeout(resolve, 500 * consecutivePollFailures));
        continue;
      }
      if (["completed", "failed", "cancelled"].includes(status.state)) {
        dispatch({ type: "BATCH_FINISHED", batchId, jobId,
          error: status.state === "completed" ? null : status.error || `job ${status.state}` });
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  } catch (error) {
    dispatch({ type: "BATCH_FINISHED", batchId, jobId, error: String(error) });
  } finally {
    submitting.delete(batchId);
  }
}

export function useStartBatch() {
  const { activeBatchId, batches, daemon } = useStore();
  const batch = activeBatchId ? batches[activeBatchId] : null;
  const visibleIds = batch?.pipeline[0]
    ? filterFilesForVerb(batch.files, batch.fileOrder, batch.pipeline[0]) : [];
  const asrReady = !batch?.pipeline.includes("transcribe") || !!selectedAsr(
    (batch.config.transcribe.lang as string) || "", batch.config.transcribe.engine as string,
    useStore.getState().capabilities?.backends_by_task["ASR"],
  );
  return {
    canStart: asrReady && !!batch && !batch.needsDiscovery && daemon.ready && visibleIds.length > 0 && batch.pipeline.length > 0,
    isRunning: batch?.state === "running",
    start: async () => { if (batch) await startBatch(batch.id); },
  };
}
