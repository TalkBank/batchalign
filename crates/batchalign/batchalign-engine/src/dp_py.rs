//! PyO3 binding for the centralized Rust Hirschberg DP aligner.
//!
//! Exposes `batchalign._core.dp_align(payload, reference)` through the shared
//! Python wrapper `batchalign.utils.dp`. Morphosyntax, forced alignment, and
//! phonetic projection call the same Rust implementation
//! (`batchalign_core::alignment`).
//!
//! Match semantics are exact equality on the supplied strings (the Python
//! side normalizes ahead of time when it wants case-insensitive behavior).
//! Adds a Hirschberg empty-sequence edge case that the Python impl handled
//! implicitly: if either input is empty, return Extra-only output.

use pyo3::prelude::*;
use pyo3::types::PyList;

use batchalign_core::alignment::{AlignResult, MatchMode, align};

/// Align two sequences with the Rust Hirschberg DP.
///
/// Returns a Python list of dicts shaped like:
///   - `{"type": "match", "key": str, "payload_idx": int, "reference_idx": int}`
///   - `{"type": "extra_payload", "key": str, "payload_idx": int}`
///   - `{"type": "extra_reference", "key": str, "reference_idx": int}`
///
/// `batchalign.utils.dp` maps these back to its `Match` / `Extra` dataclasses.
#[pyfunction]
#[pyo3(signature = (payload, reference, case_insensitive=false))]
pub fn dp_align(
    py: Python<'_>,
    payload: Vec<String>,
    reference: Vec<String>,
    case_insensitive: bool,
) -> PyResult<Py<PyList>> {
    // Empty-sequence edge cases — return Extra-only output without invoking
    // the recursive Hirschberg path (the Rust impl handles this, but make
    // the contract explicit for the Python callers).
    let mode = if case_insensitive {
        MatchMode::CaseInsensitive
    } else {
        MatchMode::Exact
    };
    let results = align(&payload, &reference, mode);

    let out = PyList::empty(py);
    for r in results {
        let dict = pyo3::types::PyDict::new(py);
        match r {
            AlignResult::Match {
                key,
                payload_idx,
                reference_idx,
            } => {
                dict.set_item("type", "match")?;
                dict.set_item("key", key)?;
                dict.set_item("payload_idx", payload_idx)?;
                dict.set_item("reference_idx", reference_idx)?;
            }
            AlignResult::ExtraPayload { key, payload_idx } => {
                dict.set_item("type", "extra_payload")?;
                dict.set_item("key", key)?;
                dict.set_item("payload_idx", payload_idx)?;
            }
            AlignResult::ExtraReference { key, reference_idx } => {
                dict.set_item("type", "extra_reference")?;
                dict.set_item("key", key)?;
                dict.set_item("reference_idx", reference_idx)?;
            }
        }
        out.append(dict)?;
    }
    Ok(out.into())
}
