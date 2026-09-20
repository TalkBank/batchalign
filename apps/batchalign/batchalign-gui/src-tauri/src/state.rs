//! App-managed Tauri state: the daemon handle.
//!
//! Lock-free via `arc-swap` (per chatter-gui convention). The handle is
//! populated by `daemon::spawn()` once the sidecar prints
//! `DAEMON_PORT=<n>` to stdout, and consumed by every HTTP-proxy command.

use std::sync::Arc;
use std::sync::Mutex as StdMutex;
use std::sync::atomic::AtomicBool;
use tauri_plugin_shell::process::CommandChild;

use arc_swap::ArcSwapOption;
use tokio::sync::Mutex;

#[derive(Debug)]
pub struct DaemonHandle {
    pub port: u16,
    /// Set true once the daemon has shut down (clean or crashed) so
    /// further requests fail fast instead of hanging on a dead socket.
    pub shutdown: tokio::sync::watch::Sender<bool>,
}

#[derive(Default)]
pub struct AppState {
    pub daemon: ArcSwapOption<DaemonHandle>,
    /// Latch flipped to `true` by the first `daemon::spawn()` caller
    /// (compare_exchange). Subsequent callers — typically `bridge.ts`
    /// invoking `ensure_daemon` while the setup() spawn is still in
    /// flight — see `true` and bail without launching a second sidecar.
    pub daemon_spawning: AtomicBool,
    child: StdMutex<Option<CommandChild>>,
    startup_error: StdMutex<Option<String>>,
    /// Per-batch SSE pump cancellers. A new batch start replaces the
    /// previous canceller for that batch (rare; the GUI runs at most
    /// one job per tab).
    pub pumps: Mutex<std::collections::HashMap<String, tokio::sync::oneshot::Sender<()>>>,
}

impl AppState {
    pub fn set_child(&self, child: CommandChild) {
        *self.child.lock().unwrap_or_else(|e| e.into_inner()) = Some(child);
    }

    pub fn stop_child(&self) {
        if let Some(child) = self.child.lock().unwrap_or_else(|e| e.into_inner()).take() {
            let _ = child.kill();
        }
    }

    pub fn startup_error(&self) -> Option<String> {
        self.startup_error
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .clone()
    }

    pub fn clear_startup_error(&self) {
        *self.startup_error.lock().unwrap_or_else(|e| e.into_inner()) = None;
    }

    pub fn failed(&self, reason: String) {
        *self.startup_error.lock().unwrap_or_else(|e| e.into_inner()) = Some(reason);
        if let Some(handle) = self.daemon.swap(None) {
            let _ = handle.shutdown.send(true);
        }
        self.daemon_spawning
            .store(false, std::sync::atomic::Ordering::Release);
    }

    pub fn new() -> Self {
        Self::default()
    }

    pub fn daemon_port(&self) -> Option<u16> {
        self.daemon.load().as_deref().map(|h| h.port)
    }

    pub fn set_daemon(&self, handle: DaemonHandle) {
        self.daemon.store(Some(Arc::new(handle)));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::Ordering;

    #[test]
    fn failure_is_observable_after_the_readiness_event_was_missed() {
        let state = AppState::new();
        let (shutdown, receiver) = tokio::sync::watch::channel(false);
        state.set_daemon(DaemonHandle {
            port: 43210,
            shutdown,
        });
        state.daemon_spawning.store(true, Ordering::Release);
        state.failed("bootstrap failed".into());
        assert_eq!(state.daemon_port(), None);
        assert_eq!(state.startup_error().as_deref(), Some("bootstrap failed"));
        assert!(*receiver.borrow());
        assert!(!state.daemon_spawning.load(Ordering::Acquire));
        state.clear_startup_error();
        assert_eq!(state.startup_error(), None);
    }

    #[test]
    fn stopping_a_managed_child_reaps_the_process() {
        use tauri_plugin_shell::process::{Command, CommandEvent};
        #[cfg(unix)]
        let command = Command::new("sleep").args(["30"]);
        #[cfg(windows)]
        let command = Command::new("ping.exe").args(["-t", "127.0.0.1"]);
        let (mut events, child) = command.spawn().expect("spawn test child");
        let state = AppState::new();
        state.set_child(child);
        state.stop_child();
        state.stop_child(); // idempotent during app shutdown and error cleanup
        tauri::async_runtime::block_on(async {
            tokio::time::timeout(std::time::Duration::from_secs(5), async {
                while let Some(event) = events.recv().await {
                    if matches!(event, CommandEvent::Terminated(_)) {
                        return;
                    }
                }
                panic!("child output closed without termination");
            })
            .await
            .expect("managed child must terminate promptly");
        });
    }
}
