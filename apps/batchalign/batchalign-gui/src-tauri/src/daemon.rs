//! Sidecar daemon manager.
//!
//! Spawns the bundled `sidecar` PyApp binary (`tauri.conf.json`
//! `bundle.externalBin = ["binaries/sidecar"]`) with `--port 0
//! --host 127.0.0.1`, reads its stdout for the `DAEMON_PORT=<n>` line
//! the daemon prints on startup (see `python/batchalign/cli/daemon.py
//! :_PortAnnouncingServer`), stores the resolved port in `AppState`,
//! and emits a `daemon-ready` Tauri event so the frontend's `bridge.ts`
//! can fetch `/capabilities`.
//!
//! On any failure during startup we emit `daemon-failed` instead with a
//! reason string the GUI surfaces to the user.

use std::sync::atomic::Ordering;

use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::{Command, CommandEvent};
use tokio::sync::watch;

#[cfg(windows)]
use crate::daemon_environment::windows_environment;
use crate::daemon_protocol::{parse_port, push_tail};
use crate::installation_activity::{self, InstallationActivity};
use crate::protocol::{DaemonFailedPayload, DaemonProgressPayload, DaemonReadyPayload, events};
use crate::state::{AppState, DaemonHandle};

const SIDECAR: &str = "sidecar";

// Separate environments for different embedded sidecars.
const SIDECAR_ID: &str = env!("BATCHALIGN_SIDECAR_ID");

/// Spawn the sidecar daemon at most once. The first caller to flip the
/// `daemon_spawning` latch wins; concurrent callers (e.g. setup() and
/// bridge.ts both racing on cold start) return immediately. If the
/// spawn fails the latch is reset so a retry can occur.
pub fn spawn(app: AppHandle) {
    let state = app.state::<AppState>();
    if state
        .daemon_spawning
        .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
        .is_err()
    {
        return;
    }
    launch(app, false);
}

pub fn retry(app: AppHandle, repair: bool) -> Result<(), String> {
    let state = app.state::<AppState>();
    if let Some(port) = state.daemon_port() {
        if repair {
            return Err("The runtime is already running. Close the app before repairing it.".into());
        }
        let _ = app.emit(events::DAEMON_READY, DaemonReadyPayload { port });
        return Ok(());
    }
    state.daemon_spawning.compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
        .map_err(|_| "Installation is already in progress".to_string())?;
    launch(app, repair);
    Ok(())
}

fn launch(app: AppHandle, repair: bool) {
    app.state::<AppState>().clear_startup_error();
    tauri::async_runtime::spawn(async move {
        match start(&app, repair).await {
            Ok(_) => {}
            Err(e) => {
                app.state::<AppState>().failed(e.to_string());
                let _ = app.emit(
                    events::DAEMON_FAILED,
                    DaemonFailedPayload {
                        reason: e.to_string(),
                    },
                );
            }
        }
    });
}

fn environment(app: &AppHandle) -> Result<std::path::PathBuf, DaemonError> {
    std::env::var_os("PYAPP_INSTALL_DIR_BATCHALIGN")
        .filter(|path| !path.is_empty())
        .map(std::path::PathBuf::from)
        .map(Ok)
        .unwrap_or_else(|| {
            #[cfg(windows)]
            return app
                .path()
                .local_data_dir()
                .map(|root| windows_environment(&root, SIDECAR_ID));
            #[cfg(not(windows))]
            app.path()
                .app_local_data_dir()
                .map(|root| root.join("environments").join(SIDECAR_ID))
        })
        .map_err(|e| DaemonError::Spawn(e.to_string()))
}

fn invalidate_installation(environment: &std::path::Path) -> Result<(), DaemonError> {
    // The launcher's installation lock owns the actual rebuild. Invalidating
    // its completion record preserves configuration, transcripts and models.
    match std::fs::remove_file(environment.join(".batchalign-install-complete")) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(DaemonError::Spawn(format!("Could not prepare runtime repair: {error}"))),
    }
}

pub fn repair_and_restart(app: AppHandle) -> Result<(), String> {
    let root = environment(&app).map_err(|error| error.to_string())?;
    invalidate_installation(&root).map_err(|error| error.to_string())?;
    app.state::<AppState>().stop_child();
    // A new application process owns the replacement runtime. No old pipe
    // watcher can mistake intentional shutdown for failure of that runtime.
    app.restart()
}

async fn start(app: &AppHandle, repair: bool) -> Result<(), DaemonError> {
    let environment = environment(app)?;

    if repair {
        invalidate_installation(&environment)?;
    }

    let activity = installation_activity::watch(&environment).unwrap_or_else(|error| {
        eprintln!("Could not observe runtime installation progress: {error}");
        None
    });

    // Build the sidecar command. `Command::new_sidecar` resolves to the
    // platform-suffixed binary that the Tauri bundler placed in the
    // app resources (e.g. `binaries/sidecar-aarch64-apple-darwin`).
    // The PyApp-bundled sidecar IS the daemon — `run_pyapp_entry`
    // prepends "daemon" to argv internally (see
    // python/batchalign/cli/daemon.py:run_pyapp_entry). Passing "daemon"
    // here would duplicate the subcommand and Typer rejects it with
    // "Got unexpected extra argument(s) (daemon)".
    let cmd: Command = app
        .shell()
        .sidecar(SIDECAR)
        .map_err(|e| DaemonError::Spawn(e.to_string()))?
        // Trust local filesystem paths in `InputSpec`. The daemon's
        // `_paths_allowed()` (python/batchalign/api.py:235) requires
        // BATCHALIGN_API_ALLOW_PATHS=1 to honor `path` inputs. Because
        // the GUI's process boundary IS the user's machine — files
        // come from a Tauri folder picker, not arbitrary network
        // clients — there is no remote-trust concern; enabling paths
        // is the whole point of the desktop integration.
        .env("BATCHALIGN_API_ALLOW_PATHS", "1")
        .env("PYAPP_INSTALL_DIR_BATCHALIGN", environment)
        .args([
            "--port",
            "0",
            "--host",
            "127.0.0.1",
            "--log-level",
            "info",
            "--no-access-log",
        ]);

    let (mut rx, child) = cmd.spawn().map_err(|e| DaemonError::Spawn(e.to_string()))?;

    // Read the daemon's stdout until "DAEMON_PORT=<n>" appears or it dies.
    app.state::<AppState>().set_child(child);
    let port = match wait_for_port(app, &mut rx, activity.as_ref()).await {
        Ok(port) => port,
        Err(error) => {
            app.state::<AppState>().stop_child();
            return Err(error);
        }
    };
    let (shutdown_tx, _shutdown_rx) = watch::channel(false);

    // Store the handle BEFORE emitting daemon-ready so any frontend code
    // that immediately calls `daemon_port` (or fetches capabilities) sees
    // the populated state.
    let state = app.state::<AppState>();
    state.set_daemon(DaemonHandle {
        port,
        shutdown: shutdown_tx,
    });

    let _ = app.emit(events::DAEMON_READY, DaemonReadyPayload { port });

    // Keep draining stdout/stderr for the lifetime of the daemon so the
    // child's pipes never block. We surface unexpected exits as
    // `daemon-failed` so the GUI can show a recovery state.
    let app_handle = app.clone();
    tauri::async_runtime::spawn(async move {
        drain_child(&app_handle, rx).await;
    });

    Ok(())
}

async fn wait_for_port(
    app: &AppHandle,
    rx: &mut tauri::async_runtime::Receiver<CommandEvent>,
    activity: Option<&InstallationActivity>,
) -> Result<u16, DaemonError> {
    // To keep the user from thinking the app froze during that window,
    // every stderr line is forwarded to the frontend as a
    // `daemon-progress` event; the overlay surfaces the latest line
    // (e.g. "Collecting torch", "Installing collected packages …") so
    // there's visible motion the whole time.
    // Active downloads may take longer than 15 minutes. Bound both a stalled
    // installer and the total attempt, instead of killing a progressing one.
    let started = std::time::Instant::now();
    let mut last_progress = started;
    let mut last_file_progress_message = started;
    let mut tail: Vec<String> = Vec::new();
    loop {
        if activity.is_some_and(InstallationActivity::take_change) {
            last_progress = std::time::Instant::now();
            if last_file_progress_message.elapsed() >= std::time::Duration::from_secs(30) {
                let _ = app.emit(events::DAEMON_PROGRESS, DaemonProgressPayload {
                    line: "Preparing Batchalign dependencies…".to_owned(),
                });
                last_file_progress_message = last_progress;
            }
        }
        if started.elapsed() >= std::time::Duration::from_secs(3600)
            || last_progress.elapsed() >= std::time::Duration::from_secs(900) {
            break;
        }
        let evt = match tokio::time::timeout(std::time::Duration::from_millis(500), rx.recv()).await
        {
            Ok(Some(evt)) => evt,
            Ok(None) => {
                return Err(DaemonError::EarlyExit(format!(
                    "stdout closed before announcing port. last output:\n{}",
                    tail.join("\n"),
                )));
            }
            Err(_) => continue, // poll again
        };
        match evt {
            CommandEvent::Stdout(line) => {
                last_progress = std::time::Instant::now();
                let text = String::from_utf8_lossy(&line).into_owned();
                let trimmed = text.trim();
                eprintln!("[daemon stdout] {trimmed}");
                push_tail(&mut tail, &text);
                if !trimmed.is_empty() {
                    let _ = app.emit(
                        events::DAEMON_PROGRESS,
                        DaemonProgressPayload {
                            line: trimmed.to_owned(),
                        },
                    );
                }
                if let Some(port) = parse_port(trimmed) {
                    return Ok(port);
                }
            }
            CommandEvent::Stderr(line) => {
                last_progress = std::time::Instant::now();
                let text = String::from_utf8_lossy(&line).into_owned();
                let trimmed = text.trim_end();
                eprintln!("[daemon stderr] {trimmed}");
                push_tail(&mut tail, &text);
                if !trimmed.is_empty() {
                    let _ = app.emit(
                        events::DAEMON_PROGRESS,
                        DaemonProgressPayload {
                            line: trimmed.to_owned(),
                        },
                    );
                }
                // Fallback: newer uvicorn versions moved `Server.servers`,
                // breaking `_PortAnnouncingServer.startup`'s stdout
                // announcement (the override swallows AttributeError and
                // silently returns). Recognize uvicorn's stable startup
                // log line "Uvicorn running on http://127.0.0.1:<port>"
                // as a secondary port announcement.
                if let Some(port) = parse_port(trimmed) {
                    eprintln!("[daemon  match] port={port} via uvicorn log");
                    return Ok(port);
                }
            }
            CommandEvent::Error(e) => {
                eprintln!("[daemon  error] {e}");
                return Err(DaemonError::EarlyExit(format!(
                    "{e}. last output:\n{}",
                    tail.join("\n"),
                )));
            }
            CommandEvent::Terminated(payload) => {
                eprintln!(
                    "[daemon   exit] code={:?} signal={:?}",
                    payload.code, payload.signal,
                );
                return Err(DaemonError::EarlyExit(format!(
                    "daemon exited (code={:?}) before announcing port. last output:\n{}",
                    payload.code,
                    tail.join("\n"),
                )));
            }
            _ => {}
        }
    }
    Err(DaemonError::PortTimeout(tail.join("\n")))
}

async fn drain_child(app: &AppHandle, mut rx: tauri::async_runtime::Receiver<CommandEvent>) {
    while let Some(evt) = rx.recv().await {
        match evt {
            CommandEvent::Stdout(line) => {
                eprintln!(
                    "[daemon stdout] {}",
                    String::from_utf8_lossy(&line).trim_end(),
                );
            }
            CommandEvent::Stderr(line) => {
                eprintln!(
                    "[daemon stderr] {}",
                    String::from_utf8_lossy(&line).trim_end(),
                );
            }
            CommandEvent::Terminated(payload) => {
                let reason = format!("daemon exited (code={:?})", payload.code);
                let state = app.state::<AppState>();
                state.stop_child();
                state.failed(reason.clone());
                let _ = app.emit(events::DAEMON_FAILED, DaemonFailedPayload { reason });
                break;
            }
            CommandEvent::Error(e) => {
                eprintln!("[daemon  error] {e}");
                let state = app.state::<AppState>();
                state.stop_child();
                state.failed(e.clone());
                let _ = app.emit(events::DAEMON_FAILED, DaemonFailedPayload { reason: e });
                break;
            }
            _ => {}
        }
    }
    let state = app.state::<AppState>();
    if state.daemon_port().is_some() {
        let reason = "daemon output channel closed unexpectedly".to_string();
        state.stop_child();
        state.failed(reason.clone());
        let _ = app.emit(events::DAEMON_FAILED, DaemonFailedPayload { reason });
    }
}

/// Idempotent ensure-daemon: if the sidecar is already running, return
/// its port. If a spawn is already in flight (lib.rs's setup() always
/// fires one), wait for it. Only kick off a new spawn when no prior
/// attempt has been made — `spawn()`'s compare_exchange would no-op
/// the duplicate anyway, but checking here lets us return early without
/// the 5-second poll.
pub async fn ensure(app: AppHandle) -> Result<u16, String> {
    let state = app.state::<AppState>();
    if let Some(port) = state.daemon_port() {
        return Ok(port);
    }
    // setup() can fail before the webview registers listeners. Preserve the
    // cause so that ensure does not turn that failure into a 15-minute hang.
    if let Some(reason) = state.startup_error() {
        return Err(reason);
    }
    spawn(app.clone());
    // Best-effort: poll for up to a few seconds to surface the port
    // synchronously if it lands fast. Past the deadline the frontend
    // can still observe completion via the `daemon-ready` event.
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
    while std::time::Instant::now() < deadline {
        if let Some(port) = state.daemon_port() {
            return Ok(port);
        }
        if let Some(reason) = state.startup_error() {
            return Err(reason);
        }
        tokio::time::sleep(std::time::Duration::from_millis(50)).await;
    }
    Err("daemon still starting; listen for `daemon-ready`".into())
}

#[derive(Debug, thiserror::Error)]
pub enum DaemonError {
    #[error("failed to spawn sidecar: {0}")]
    Spawn(String),
    #[error("daemon exited before announcing port: {0}")]
    EarlyExit(String),
    #[error("Setup stopped after 15 minutes without progress or one hour overall. Check your internet connection and free disk space, then retry. If setup remains broken, choose Repair installation. Last output:\n{0}")]
    PortTimeout(String),
}

#[cfg(test)]
mod recovery_tests {
    use super::invalidate_installation;

    #[test]
    fn repair_invalidates_only_completion_and_can_be_repeated() {
        let root = std::env::temp_dir().join(format!("batchalign-repair-{}-{}",
            std::process::id(), std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        let runtime = root.join("runtime");
        std::fs::create_dir_all(&runtime).unwrap();
        std::fs::write(runtime.join(".batchalign-install-complete"), b"complete").unwrap();
        std::fs::write(runtime.join("python.exe"), b"runtime").unwrap();
        std::fs::write(root.join("credentials.ini"), b"preserve").unwrap();
        invalidate_installation(&runtime).unwrap();
        invalidate_installation(&runtime).unwrap();
        assert!(!runtime.join(".batchalign-install-complete").exists());
        assert_eq!(std::fs::read(runtime.join("python.exe")).unwrap(), b"runtime");
        assert_eq!(std::fs::read(root.join("credentials.ini")).unwrap(), b"preserve");
        std::fs::remove_dir_all(root).unwrap();
    }
}
