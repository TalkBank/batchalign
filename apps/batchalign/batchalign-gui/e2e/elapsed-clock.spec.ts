import { expect, test } from "@playwright/test";

test("elapsed clock advances without progress events", async ({ page }) => {
  await page.addInitScript({
    content: `
      const callbacks = new Map();
      let callbackId = 0;
      window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {
        unregisterListener: (_event, id) => callbacks.delete(id),
      };
      window.__TAURI_INTERNALS__ = {
        invoke: async (command, args) => {
          if (command === "plugin:event|listen") return args.handler;
          if (command === "plugin:event|unlisten") return null;
          if (command === "ensure_daemon") return new Promise(() => {});
          return null;
        },
        transformCallback: (callback) => {
          const id = ++callbackId;
          callbacks.set(id, callback);
          return id;
        },
        metadata: { plugins: {} },
      };
    `,
  });
  await page.goto("/");

  await page.evaluate(async () => {
    const { dispatch } = await import("/src/store.ts");
    const sourceId = "clock-test.wav";
    const queuedId = "waiting-test.wav";
    const file = (id: string, status: "queued" | "running") => ({
      source_id: id,
      stem: id.replace(".wav", ""),
      filename: id,
      sizeBytes: 1,
      durationMs: null,
      kind: "media" as const,
      status,
      stages: [],
      log: [],
    });
    dispatch({
      type: "BATCH_OPENED",
      batch: {
        id: "clock-test",
        name: "clock-test",
        folderPath: "/clock-test",
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
        files: {
          [sourceId]: file(sourceId, "running"),
          [queuedId]: file(queuedId, "queued"),
        },
        fileOrder: [sourceId, queuedId],
        state: "running",
        jobId: "clock-test",
        startedAt: Date.now(),
        finishedAt: null,
        expandedFileId: null,
      },
    });
  });

  const elapsed = page
    .getByText("elapsed", { exact: true })
    .locator("xpath=following-sibling::div");
  const initial = await elapsed.textContent();
  await expect.poll(() => elapsed.textContent(), { timeout: 4_000 }).not.toBe(initial);

  await expect(page.getByText("0 of 2 processing", { exact: true })).toBeVisible();
  await page.evaluate(async () => {
    const { dispatch } = await import("/src/store.ts");
    dispatch({
      type: "PROGRESS_V2",
      batchId: "clock-test",
      event: {
        source_id: "clock-test.wav",
        task: null,
        kind: "SourceCompleted",
        completed: 1,
        total: 1,
        label: null,
      },
    });
  });
  await expect(page.getByText("1 of 2 processing", { exact: true })).toBeVisible();
});
