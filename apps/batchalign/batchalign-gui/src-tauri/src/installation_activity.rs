//! Windows pip can spend many minutes copying packages without console output.
//! Observe writes to this runtime so startup can distinguish that from a stall.

#[cfg(windows)]
use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
};

pub(crate) struct InstallationActivity {
    #[cfg(windows)]
    changed: Arc<AtomicBool>,
    #[cfg(windows)]
    _watcher: notify::RecommendedWatcher,
}

impl InstallationActivity {
    pub(crate) fn take_change(&self) -> bool {
        #[cfg(windows)]
        {
            self.changed.swap(false, Ordering::Relaxed)
        }
        #[cfg(not(windows))]
        {
            false
        }
    }
}

#[cfg(not(windows))]
pub(crate) fn watch(_runtime: &std::path::Path) -> Result<Option<InstallationActivity>, String> {
    Ok(None)
}

#[cfg(windows)]
pub(crate) fn watch(runtime: &std::path::Path) -> Result<Option<InstallationActivity>, String> {
    use notify::{EventKind, RecursiveMode, Watcher};
    let runtime = std::path::absolute(runtime).map_err(|e| e.to_string())?;
    let parent = runtime.parent().ok_or("Runtime has no parent directory")?;
    // Watch the parent: repair removes and recreates the runtime itself.
    std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    let parent = parent.canonicalize().map_err(|e| e.to_string())?;
    let runtime = runtime
        .canonicalize()
        .unwrap_or_else(|_| parent.join(runtime.file_name().unwrap()));
    let changed = Arc::new(AtomicBool::new(false));
    let signal = Arc::clone(&changed);
    let mut watcher = notify::recommended_watcher(move |event: notify::Result<notify::Event>| {
        if let Ok(event) = event {
            // Reads, unrelated runtime activity, and watcher errors are not
            // installation progress and must not keep a hung process alive.
            if matches!(
                event.kind,
                EventKind::Create(_) | EventKind::Modify(_) | EventKind::Remove(_)
            ) && event.paths.iter().any(|path| path.starts_with(&runtime))
            {
                signal.store(true, Ordering::Relaxed);
            }
        }
    })
    .map_err(|e| e.to_string())?;
    watcher
        .watch(&parent, RecursiveMode::Recursive)
        .map_err(|e| e.to_string())?;
    Ok(Some(InstallationActivity {
        changed,
        _watcher: watcher,
    }))
}

#[cfg(all(test, windows))]
mod tests {
    use super::*;
    use std::{
        fs,
        path::PathBuf,
        thread,
        time::{Duration, Instant, SystemTime, UNIX_EPOCH},
    };

    struct Fixture(PathBuf);
    impl Fixture {
        fn new() -> Self {
            let root = std::env::temp_dir().join(format!(
                "batchalign-install-watch-{}-{}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            fs::create_dir(&root).unwrap();
            Self(root)
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    fn changed(activity: &InstallationActivity) {
        let deadline = Instant::now() + Duration::from_secs(5);
        while Instant::now() < deadline {
            if activity.take_change() {
                return;
            }
            thread::sleep(Duration::from_millis(10));
        }
        panic!("Runtime filesystem changes were not observed");
    }

    fn settle(activity: &InstallationActivity) {
        let deadline = Instant::now() + Duration::from_secs(5);
        let mut quiet_since = Instant::now();
        while Instant::now() < deadline {
            if activity.take_change() {
                quiet_since = Instant::now();
            }
            if quiet_since.elapsed() >= Duration::from_millis(200) {
                return;
            }
            thread::sleep(Duration::from_millis(10));
        }
        panic!("Filesystem notifications did not settle");
    }

    #[test]
    fn silent_file_installation_and_runtime_recreation_are_progress() {
        let fixture = Fixture::new();
        let runtime = fixture.0.join("runtime");
        let activity = watch(&runtime).unwrap().unwrap();
        fs::create_dir_all(runtime.join("python/Lib/site-packages/example")).unwrap();
        changed(&activity);
        settle(&activity);
        fs::write(
            runtime.join("python/Lib/site-packages/example/module.py"),
            b"pass",
        )
        .unwrap();
        changed(&activity);
        settle(&activity);
        fs::remove_dir_all(&runtime).unwrap();
        changed(&activity);
        settle(&activity);
        fs::create_dir_all(&runtime).unwrap();
        fs::write(runtime.join("python.exe"), b"new installation").unwrap();
        changed(&activity);
    }

    #[test]
    fn unrelated_writes_and_reads_are_not_progress() {
        let fixture = Fixture::new();
        let runtime = fixture.0.join("runtime");
        fs::create_dir(&runtime).unwrap();
        fs::write(runtime.join("python.exe"), b"runtime").unwrap();
        let activity = watch(&runtime).unwrap().unwrap();
        fs::write(fixture.0.join("unrelated.log"), b"unrelated activity").unwrap();
        fs::read(runtime.join("python.exe")).unwrap();
        thread::sleep(Duration::from_millis(300));
        assert!(!activity.take_change());
    }
}
