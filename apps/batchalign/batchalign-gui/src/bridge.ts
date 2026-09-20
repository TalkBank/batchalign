// Each mounted app owns its listeners. Cleanup is synchronous even while
// native listener registration or daemon startup is still pending.
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import {
  TauriEvents,
  type DaemonFailedPayload,
  type DaemonProgressPayload,
  type DaemonReadyPayload,
  type ProgressV2Payload,
} from "./protocol/events";
import { dispatch } from "./store";
import { fetchCapabilities, setBaseUrl } from "./api";

export function bootBridge(): () => void {
  let disposed = false;
  let connectedPort: number | null = null;
  let generation = 0;
  const unlisteners: Array<() => void> = [];

  function failed(reason: string) {
    if (disposed) return;
    generation++;
    connectedPort = null;
    dispatch({ type: "DAEMON_FAILED", reason });
  }

  async function ready(port: number) {
    if (disposed || connectedPort === port) return;
    connectedPort = port;
    const requestGeneration = ++generation;
    setBaseUrl(`http://127.0.0.1:${port}`);
    dispatch({ type: "DAEMON_READY", port });
    try {
      const capabilities = await fetchCapabilities();
      if (!disposed && generation === requestGeneration) {
        dispatch({ type: "CAPABILITIES_LOADED", capabilities });
      }
    } catch (err) {
      if (!disposed && generation === requestGeneration) {
        failed(`capabilities fetch failed: ${err}`);
      }
    }
  }

  async function subscribe<T>(event: string, callback: (payload: T) => void) {
    const off = await listen<T>(event, ({ payload }) => {
      if (!disposed) callback(payload);
    });
    if (disposed) off();
    else unlisteners.push(off);
  }

  async function start() {
    try {
      await Promise.all([
        subscribe<DaemonReadyPayload>(TauriEvents.daemonReady, ({ port }) => { void ready(port); }),
        subscribe<DaemonFailedPayload>(TauriEvents.daemonFailed, ({ reason }) => failed(reason)),
        subscribe<DaemonProgressPayload>(TauriEvents.daemonProgress, ({ line }) => {
          dispatch({ type: "DAEMON_PROGRESS", line });
        }),
        subscribe<ProgressV2Payload>(TauriEvents.progressV2, (payload) => {
          dispatch({ type: "PROGRESS_V2", batchId: payload.batchId, event: payload.event });
        }),
      ]);
      if (disposed) return;
      // setup() may have announced readiness before the webview mounted.
      // The command's returned port is as authoritative as the event.
      const port = await invoke<number>("ensure_daemon");
      await ready(port);
    } catch (err) {
      if (!String(err).includes("daemon still starting")) {
        failed(`ensure_daemon invoke failed: ${err}`);
      }
    }
  }
  void start();

  return () => {
    disposed = true;
    generation++;
    for (const off of unlisteners.splice(0)) off();
  };
}
