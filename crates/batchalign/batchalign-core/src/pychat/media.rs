//! Typed media declarations, independent of document timing while editing.
use pyo3::{exceptions::PyValueError, prelude::*};
use talkbank_model::model::{MediaFilename, MediaHeader, MediaStatus, MediaType};

/// Immutable CHAT media basename, modality, and optional linkage status.
#[pyclass(frozen, from_py_object, module = "batchalign.chat")]
#[derive(Clone)]
pub struct Media {
    pub(super) header: MediaHeader,
}

#[pymethods]
impl Media {
    #[new]
    #[pyo3(signature = (filename, *, media_type="audio", status=None))]
    fn new(filename: &str, media_type: &str, status: Option<&str>) -> PyResult<Self> {
        let filename = MediaFilename::parse(filename)
            .map_err(|error| PyValueError::new_err(error.to_string()))?;
        let media_type = match media_type {
            "audio" => MediaType::Audio,
            "video" => MediaType::Video,
            "missing" => MediaType::Missing,
            _ => {
                return Err(PyValueError::new_err(
                    "media_type must be 'audio', 'video', or 'missing'",
                ));
            }
        };
        let mut header = MediaHeader::new(filename, media_type);
        header.status = match status {
            None => None,
            Some("missing") => Some(MediaStatus::Missing),
            Some("unlinked") => Some(MediaStatus::Unlinked),
            Some("notrans") => Some(MediaStatus::Notrans),
            _ => {
                return Err(PyValueError::new_err(
                    "status must be None, 'missing', 'unlinked', or 'notrans'",
                ));
            }
        };
        Ok(Self { header })
    }

    #[getter]
    fn filename(&self) -> &str {
        self.header.filename.as_str()
    }
    #[getter]
    fn media_type(&self) -> &str {
        self.header.media_type.as_str()
    }
    #[getter]
    fn status(&self) -> Option<&str> {
        self.header.status.as_ref().map(MediaStatus::as_str)
    }
    fn __eq__(&self, other: &Self) -> bool {
        self.header == other.header
    }
    fn __repr__(&self) -> String {
        format!(
            "Media(filename={:?}, media_type={:?}, status={:?})",
            self.filename(),
            self.media_type(),
            self.status()
        )
    }
}
