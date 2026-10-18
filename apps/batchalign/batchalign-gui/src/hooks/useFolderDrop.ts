import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { openFolder } from "../folders";

export function useFolderDrop() {
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  useEffect(() => {
    let disposed = false;
    const unlisteners: Array<() => void> = [];
    async function subscribe<T>(name: string, callback: (payload: T) => void) {
      const off = await listen<T>(name, ({ payload }) => { if (!disposed) callback(payload); });
      if (disposed) off();
      else unlisteners.push(off);
    }
    void Promise.all([
      subscribe("tauri://drag-enter", () => setDragging(true)),
      subscribe("tauri://drag-leave", () => setDragging(false)),
      subscribe<{ paths: string[] }>("tauri://drag-drop", ({ paths }) => {
        setDragging(false);
        setError(null);
        void (async () => {
          try {
            if (!disposed && paths[0]) await openFolder(paths[0]);
          } catch (error) { if (!disposed) setError(String(error)); }
        })();
      }),
    ]).catch(error => { if (!disposed) setError(String(error)); });
    // Prevent WebKit from navigating away when a file is dropped.
    const prevent = (event: DragEvent) => event.preventDefault();
    window.addEventListener("dragover", prevent);
    window.addEventListener("drop", prevent);
    return () => {
      disposed = true;
      unlisteners.forEach(off => off());
      window.removeEventListener("dragover", prevent);
      window.removeEventListener("drop", prevent);
    };
  }, []);
  return { error, dragging };
}
