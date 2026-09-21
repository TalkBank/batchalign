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
    pumps: Mutex<std::collections::HashMap<String, PumpHandle>>,
}

struct PumpHandle {
    identity: Arc<()>,
    cancel: tokio::sync::oneshot::Sender<()>,
}

impl AppState {
    pub async fn register_pump(
        &self,
        batch: String,
    ) -> (Arc<()>, tokio::sync::oneshot::Receiver<()>) {
        let identity = Arc::new(());
        let (cancel, receiver) = tokio::sync::oneshot::channel();
        let handle = PumpHandle {
            identity: identity.clone(),
            cancel,
        };
        if let Some(previous) = self.pumps.lock().await.insert(batch, handle) {
            let _ = previous.cancel.send(());
        }
        (identity, receiver)
    }

    pub async fn finish_pump(&self, batch: &str, identity: &Arc<()>) {
        let mut pumps = self.pumps.lock().await;
        // A replaced task may finish after its successor has registered.
        if pumps
            .get(batch)
            .is_some_and(|handle| Arc::ptr_eq(&handle.identity, identity))
        {
            pumps.remove(batch);
        }
    }
    pub fn set_child(&self, child: CommandChild) {
        *self.child.lock().unwrap_or_else(|e| e.into_inner()) = Some(child);
    }

    pub fn stop_child(&self) {
        if let Some(child) = self.child.lock().unwrap_or_else(|e| e.into_inner()).take() {
            // On Windows PyApp waits for Python rather than replacing itself
            // with exec(). Killing only the launcher leaves the daemon alive.
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                let result = std::process::Command::new("taskkill.exe")
                    .args(["/PID", &child.pid().to_string(), "/T", "/F"])
                    .creation_flags(0x08000000) // CREATE_NO_WINDOW
                    .output();
                if let Err(error) = result {
                    eprintln!("failed to stop daemon process tree: {error}");
                }
            }
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
            // A request may have loaded this handle but not subscribed yet.
            // send() discards the value when there are no current receivers.
            handle.shutdown.send_replace(true);
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
    fn late_pump_cleanup_cannot_remove_or_cancel_its_successor() {
        tauri::async_runtime::block_on(async {
            let state = AppState::new();
            let (first, cancelled) = state.register_pump("batch".into()).await;
            let (second, mut running) = state.register_pump("batch".into()).await;
            assert_eq!(cancelled.await, Ok(()));
            state.finish_pump("batch", &first).await;
            assert!(matches!(
                running.try_recv(),
                Err(tokio::sync::oneshot::error::TryRecvError::Empty)
            ));
            let (third, _) = state.register_pump("batch".into()).await;
            assert_eq!(running.await, Ok(()));
            state.finish_pump("batch", &second).await;
            assert_eq!(state.pumps.lock().await.len(), 1);
            state.finish_pump("batch", &third).await;
            assert!(state.pumps.lock().await.is_empty());
        });
    }

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
    fn a_late_subscriber_still_observes_daemon_shutdown() {
        let state = AppState::new();
        let (shutdown, receiver) = tokio::sync::watch::channel(false);
        drop(receiver);
        state.set_daemon(DaemonHandle {
            port: 43210,
            shutdown,
        });
        let request_handle = state.daemon.load_full().unwrap();
        state.failed("daemon exited".into());
        assert!(*request_handle.shutdown.subscribe().borrow());
    }

    #[test]
    fn stopping_a_managed_child_reaps_the_process() {
        use tauri_plugin_shell::{ShellExt, process::CommandEvent};
        let app = tauri::test::mock_builder()
            .plugin(tauri_plugin_shell::init())
            .build(tauri::test::mock_context(tauri::test::noop_assets()))
            .expect("build shell test app");
        #[cfg(unix)]
        let command = app.shell().command("sleep").args(["30"]);
        #[cfg(windows)]
        let command = app.shell().command("ping.exe").args(["-t", "127.0.0.1"]);
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

    #[cfg(windows)]
    #[test]
    fn stopping_a_launcher_closes_its_descendants_socket() {
        use tauri_plugin_shell::{ShellExt, process::CommandEvent};
        let app = tauri::test::mock_builder()
            .plugin(tauri_plugin_shell::init())
            .build(tauri::test::mock_context(tauri::test::noop_assets()))
            .expect("build shell test app");
        let root = std::env::temp_dir().join(format!(
            "batchalign-child-tree-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos(),
        ));
        std::fs::create_dir(&root).unwrap();
        let parent = root.join("parent.ps1");
        let listener = root.join("listener.ps1");
        std::fs::write(
            &parent,
            "& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $args[0]\n",
        )
        .unwrap();
        std::fs::write(
            &listener,
            r#"
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$listener.Start()
[Console]::WriteLine("LISTENING=" + $listener.LocalEndpoint.Port)
Start-Sleep -Seconds 30
$listener.Stop()
"#,
        )
        .unwrap();
        let (mut events, child) = app
            .shell()
            .command("powershell.exe")
            .args([
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
            ])
            .arg(&parent)
            .arg(&listener)
            .spawn()
            .expect("spawn launcher and descendant");
        let state = AppState::new();
        state.set_child(child);
        let port = tauri::async_runtime::block_on(async {
            tokio::time::timeout(std::time::Duration::from_secs(15), async {
                while let Some(event) = events.recv().await {
                    if let CommandEvent::Stdout(bytes) = event {
                        if let Some(port) = String::from_utf8_lossy(&bytes)
                            .trim()
                            .strip_prefix("LISTENING=")
                        {
                            return port.parse::<u16>().ok();
                        }
                    }
                }
                None
            })
            .await
            .ok()
            .flatten()
        });
        let address = port.map(|port| std::net::SocketAddr::from(([127, 0, 0, 1], port)));
        let listening = address.is_some_and(|address| {
            std::net::TcpStream::connect_timeout(&address, std::time::Duration::from_millis(500))
                .is_ok()
        });
        state.stop_child();
        state.stop_child();
        let _ = std::fs::remove_dir_all(root);
        assert!(
            listening,
            "descendant must be listening before launcher shutdown"
        );
        let address = address.unwrap();
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
        while std::net::TcpStream::connect_timeout(&address, std::time::Duration::from_millis(100))
            .is_ok()
        {
            assert!(
                std::time::Instant::now() < deadline,
                "daemon descendant survived launcher shutdown"
            );
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
    }
}
