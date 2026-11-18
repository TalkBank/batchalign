// Included inside PyApp's distribution module. The directory is created
// before pip finishes, so only a durable completion record proves readiness.
fn ensure_complete_installation(
    root: &std::path::Path,
    python: &std::path::Path,
    install: impl FnOnce() -> anyhow::Result<()>,
) -> anyhow::Result<()> {
    use std::io::Write;
    let marker = root.join(".batchalign-install-complete");
    let mut ownership_name = root.file_name()
        .ok_or_else(|| anyhow::anyhow!("Runtime directory must have a name"))?.to_os_string();
    ownership_name.push(".batchalign-owned");
    // A sibling record survives interruption while the old runtime is removed.
    let ownership = root.with_file_name(ownership_name);
    if marker.is_file() && python.is_file() {
        return Ok(());
    }
    if root.exists() {
        // An installation-directory override can point anywhere. Only rebuild
        // a tree this launcher created; never erase unrelated existing files.
        anyhow::ensure!(ownership.is_file() || std::fs::read_dir(root)?.next().is_none(),
            "The runtime directory contains files not owned by this launcher. Choose an empty PYAPP_INSTALL_DIR_BATCHALIGN directory.");
        eprintln!("Recovering an incomplete installation. Downloaded packages will be reused.");
        // pip can leave partially copied packages with installed metadata.
        // Installing over that tree can incorrectly report them satisfied.
        std::fs::remove_dir_all(root)?;
    }
    std::fs::create_dir_all(root)?;
    let mut owner = std::fs::File::create(&ownership)?;
    owner.write_all(b"Batchalign generated runtime\n")?;
    owner.sync_all()?;
    drop(owner);
    install()?;
    anyhow::ensure!(python.is_file(), "Installation did not produce a Python executable");
    let mut record = std::fs::File::create(marker)?;
    record.write_all(b"complete\n")?;
    record.sync_all()?;
    Ok(())
}

#[cfg(test)]
mod bootstrap_state_tests {
    use super::*;
    #[test]
    fn interruption_and_failed_retry_never_count_as_complete() {
        let directory = tempfile::tempdir().unwrap();
        let root = directory.path().join("runtime");
        let python = root.join("python.exe");
        std::fs::create_dir(&root).unwrap();
        let ownership = directory.path().join("runtime.batchalign-owned");
        std::fs::write(&ownership, b"owned").unwrap();
        std::fs::write(&python, b"partial").unwrap();
        let failed = ensure_complete_installation(&root, &python, || {
            assert!(!python.exists());
            assert!(ownership.is_file());
            std::fs::write(&python, b"still partial")?;
            anyhow::bail!("download interrupted")
        });
        assert!(failed.is_err());
        assert!(!root.join(".batchalign-install-complete").exists());
        ensure_complete_installation(&root, &python, || {
            assert!(!python.exists());
            assert!(ownership.is_file());
            std::fs::write(&python, b"complete")?;
            Ok(())
        }).unwrap();
        ensure_complete_installation(&root, &python, || panic!("warm start must not install")).unwrap();
        std::fs::remove_file(&python).unwrap();
        assert!(ensure_complete_installation(&root, &python, || anyhow::bail!("repair attempted")).is_err());
    }

    #[test]
    fn an_unrelated_directory_override_is_never_erased() {
        let directory = tempfile::tempdir().unwrap();
        let root = directory.path();
        std::fs::write(root.join("transcript.cha"), b"user data").unwrap();
        let result = ensure_complete_installation(root, &root.join("python.exe"),
            || panic!("must not install into an unrelated directory"));
        assert!(result.is_err());
        assert_eq!(std::fs::read(root.join("transcript.cha")).unwrap(), b"user data");
    }
}
