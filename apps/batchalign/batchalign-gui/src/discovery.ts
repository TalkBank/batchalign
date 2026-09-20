import { invoke } from '@tauri-apps/api/core';
import type { FileRow } from './store';

export async function scanFolder(path: string): Promise<FileRow[]> {
  const summary = await invoke<{ files: Array<{
    source_id: string; stem: string; filename: string; size_bytes: number;
    duration_ms: number | null; kind: 'media' | 'chat';
  }> }>('list_folder_files', { path });
  return summary.files.map(file => ({
    source_id: file.source_id, stem: file.stem, filename: file.filename,
    sizeBytes: file.size_bytes, durationMs: file.duration_ms, kind: file.kind,
    status: 'queued', stages: [], log: [],
  }));
}
