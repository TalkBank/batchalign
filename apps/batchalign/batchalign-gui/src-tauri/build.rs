use sha2::{Digest, Sha256};
use std::io::Read;

fn main() {
    println!("cargo:rerun-if-env-changed=BATCHALIGN_BUILD_HASH");
    let stamp =
        std::env::var("BATCHALIGN_BUILD_HASH").unwrap_or_else(|_| "dev-unstamped".to_string());
    println!("cargo:rustc-env=BATCHALIGN_BUILD_HASH={stamp}");

    // PyApp's own key does not identify the embedded wheel contents/extras.
    // Fingerprint the staged binary so a warm launch reuses exactly its own
    // environment, including for two builds at the same version or dirty SHA.
    let target = std::env::var("TARGET").expect("Cargo target");
    let suffix = if target.contains("windows") {
        ".exe"
    } else {
        ""
    };
    let path = std::path::Path::new("binaries").join(format!("sidecar-{target}{suffix}"));
    println!("cargo:rerun-if-changed={}", path.display());
    let mut file =
        std::fs::File::open(&path).expect("Bazel must stage the sidecar before building Tauri");
    let mut hash = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let count = file.read(&mut buffer).expect("read staged sidecar");
        if count == 0 {
            break;
        }
        hash.update(&buffer[..count]);
    }
    println!(
        "cargo:rustc-env=BATCHALIGN_SIDECAR_ID={:x}",
        hash.finalize()
    );
    println!("cargo:rerun-if-env-changed=BATCHALIGN_TAURI_TEST");
    if target.ends_with("windows-msvc") && std::env::var_os("BATCHALIGN_TAURI_TEST").is_some() {
        // Tauri normally embeds Common Controls v6 only in the application
        // resource. lib test executables also need it: mock_builder otherwise
        // fails in the Windows loader with STATUS_ENTRYPOINT_NOT_FOUND.
        // https://github.com/tauri-apps/tauri/issues/13419
        let manifest = std::env::current_dir()
            .expect("crate directory")
            .join("tests.manifest");
        println!("cargo:rerun-if-changed=tests.manifest");
        println!("cargo:rustc-link-arg=/MANIFEST:EMBED");
        println!("cargo:rustc-link-arg=/MANIFESTINPUT:{}", manifest.display());
        tauri_build::try_build(
            tauri_build::Attributes::new()
                .windows_attributes(tauri_build::WindowsAttributes::new_without_app_manifest()),
        )
        .expect("build native test resources");
    } else {
        tauri_build::build();
    }
}
