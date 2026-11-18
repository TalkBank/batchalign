// Included inside PyApp's distribution module. The directory is created
// before pip finishes, so only a durable completion record proves readiness.
fn ensure_complete_installation(
    root: &std::path::Path,
    python: &std::path::Path,
    install: impl FnOnce() -> anyhow::Result<()>,
) -> anyhow::Result<()> {
    use std::io::Write;
    let marker = root.join(".batchalign-install-complete");
    if marker.is_file() && python.is_file() {
        return Ok(());
    }
    if root.exists() {
        eprintln!("Recovering an incomplete installation. Downloaded packages will be reused.");
        // pip can leave partially copied packages with installed metadata.
        // Installing over that tree can incorrectly report them satisfied.
        std::fs::remove_dir_all(root)?;
    }
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
        std::fs::write(&python, b"partial").unwrap();
        let failed = ensure_complete_installation(&root, &python, || {
            assert!(!root.exists());
            std::fs::create_dir(&root)?;
            std::fs::write(&python, b"still partial")?;
            anyhow::bail!("download interrupted")
        });
        assert!(failed.is_err());
        assert!(!root.join(".batchalign-install-complete").exists());
        ensure_complete_installation(&root, &python, || {
            assert!(!root.exists());
            std::fs::create_dir(&root)?;
            std::fs::write(&python, b"complete")?;
            Ok(())
        }).unwrap();
        ensure_complete_installation(&root, &python, || panic!("warm start must not install")).unwrap();
        std::fs::remove_file(&python).unwrap();
        assert!(ensure_complete_installation(&root, &python, || anyhow::bail!("repair attempted")).is_err());
    }
}
