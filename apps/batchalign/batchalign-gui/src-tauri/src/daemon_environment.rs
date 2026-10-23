//! Leave room for Python's nested package files under Windows' MAX_PATH.

use std::path::{Path, PathBuf};

pub fn windows_environment(local_data: &Path, sidecar_id: &str) -> PathBuf {
    // PyTorch ships deeply nested headers. Avoid the bundle identifier and
    // "environments" directory, and use 128 bits of the sidecar SHA-256 as
    // the cache key, leaving room for Python's own directory hierarchy.
    local_data
        .join("Batchalign")
        .join("r")
        .join(&sidecar_id[..32])
}

#[cfg(test)]
mod tests {
    use super::*;

    const ID: &str = "a35fa67f581265876d59cfc3cd20afacac0aabac57c4d9b45f318c4e276b4bdc";

    #[test]
    fn torch_headers_fit_without_windows_long_paths() {
        for user in ["macw", "abcdefghijklmnopqrst"] {
            let root =
                windows_environment(Path::new(&format!(r"C:\Users\{user}\AppData\Local")), ID);
            for header in [
                r"torch\include\ATen\native\transformers\cuda\mem_eff_attention\iterators\default_warp_iterator_from_smem.h",
                r"torch\include\kai\ukernels\matmul\matmul_clamp_f32_qsi8d32p_qsi4c32p\kai_matmul_clamp_f32_qsi8d32p1vlx4_qsi4c32p4vlx4_1vlx4vl_sme2_mopa.h",
            ] {
                let path = format!(r"{}\python\Lib\site-packages\{header}", root.display());
                // MAX_PATH counts UTF-16 code units, including the final NUL.
                assert!(path.encode_utf16().count() + 1 <= 260, "{path}");
            }
        }
    }

    #[test]
    fn sidecar_fingerprints_separate_same_version_builds() {
        let root = Path::new("local-data");
        assert_ne!(
            windows_environment(root, ID),
            windows_environment(root, &"b".repeat(64))
        );
        assert_eq!(windows_environment(root, ID).file_name().unwrap().len(), 32);
    }
}
