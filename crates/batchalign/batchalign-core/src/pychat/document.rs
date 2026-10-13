//! Document construction, derived metadata, and text stream I/O.
use super::{
    Media, Speaker, Utterance,
    collection::{Entry, UtteranceCollection},
    speaker::participant_headers,
    utils::parse_document,
};
use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyList, PyString, PyTuple},
};
use talkbank_model::{
    WriteChat,
    model::{Header, Line},
};

/// A Rust-owned CHAT document with editable utterances and derived participant headers.
#[pyclass(module = "batchalign.chat")]
pub struct CHATFile {
    utterances: Py<UtteranceCollection>,
}

#[pymethods]
impl CHATFile {
    #[staticmethod]
    /// Create an empty editable document.
    fn new(py: Python<'_>) -> PyResult<Self> {
        Ok(Self {
            utterances: Py::new(py, UtteranceCollection::default())?,
        })
    }

    #[staticmethod]
    /// Parse CHAT text or a list of text lines, validating content and tier alignment.
    fn parse(py: Python<'_>, lines: &Bound<'_, PyAny>) -> PyResult<Self> {
        let text = if lines.is_instance_of::<PyString>() {
            lines.extract::<String>()?
        } else {
            let lines = lines.cast::<PyList>()?.extract::<Vec<String>>()?;
            lines
                .iter()
                .map(|line| line.trim_end_matches(['\r', '\n']))
                .collect::<Vec<_>>()
                .join("\n")
                + "\n"
        };
        let ast = parse_document(
            &text,
            talkbank_model::ParseValidateOptions::default().with_alignment(),
        )?;
        let begin = ast.lines.as_slice().iter().any(|line| {
            matches!(line, Line::Header { header, .. } if matches!(header.as_ref(), Header::Begin))
        });
        let end = ast.lines.as_slice().iter().any(|line| {
            matches!(line, Line::Header { header, .. } if matches!(header.as_ref(), Header::End))
        });
        if !begin || !end {
            return Err(PyValueError::new_err(
                "CHAT requires @Begin and @End headers",
            ));
        }
        let mut entries = Vec::new();
        for line in ast.lines.as_slice() {
            match line {
                Line::Utterance(utterance) => {
                    let participant =
                        ast.participants
                            .get(&utterance.main.speaker)
                            .ok_or_else(|| {
                                PyValueError::new_err(
                                    "utterance speaker has no participant metadata",
                                )
                            })?;
                    entries.push(Entry::Utterance(Py::new(
                        py,
                        Utterance {
                            speaker: Speaker {
                                participant: participant.clone(),
                            },
                            ast: utterance.as_ref().clone(),
                        },
                    )?));
                }
                Line::Header { header, .. }
                    if matches!(
                        header.as_ref(),
                        Header::Utf8
                            | Header::Begin
                            | Header::End
                            | Header::Languages { .. }
                            | Header::Participants { .. }
                            | Header::ID(_)
                    ) => {}
                _ => entries.push(Entry::Header(line.clone())),
            }
        }
        Ok(Self {
            utterances: Py::new(py, UtteranceCollection { entries })?,
        })
    }

    #[staticmethod]
    /// Read from an open text stream without closing it.
    fn read(py: Python<'_>, fd: &Bound<'_, PyAny>) -> PyResult<Self> {
        Self::parse(py, &fd.call_method0("read")?)
    }

    #[getter]
    fn utterances(&self, py: Python<'_>) -> Py<UtteranceCollection> {
        self.utterances.clone_ref(py)
    }

    #[getter]
    fn media(&self, py: Python<'_>) -> Option<Media> {
        self.utterances
            .borrow(py)
            .entries
            .iter()
            .find_map(|entry| match entry {
                Entry::Header(Line::Header { header, .. }) => match header.as_ref() {
                    Header::Media(header) => Some(Media {
                        header: header.clone(),
                    }),
                    _ => None,
                },
                _ => None,
            })
    }

    #[setter]
    fn set_media(&self, py: Python<'_>, media: Option<Media>) {
        let mut collection = self.utterances.borrow_mut(py);
        let position = collection.entries.iter().position(|entry| matches!(entry,
            Entry::Header(Line::Header { header, .. }) if matches!(header.as_ref(), Header::Media(_))));
        match (position, media) {
            (Some(index), Some(media)) => {
                collection.entries[index] = Entry::Header(Line::header(Header::Media(media.header)))
            }
            (Some(index), None) => {
                collection.entries.remove(index);
            }
            (None, Some(media)) => collection
                .entries
                .insert(0, Entry::Header(Line::header(Header::Media(media.header)))),
            (None, None) => {}
        }
    }

    #[getter]
    fn speakers<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(
            py,
            self.utterances
                .borrow(py)
                .speakers(py)?
                .into_iter()
                .map(|speaker| Py::new(py, speaker))
                .collect::<PyResult<Vec<_>>>()?,
        )
    }

    #[getter]
    fn languages<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(
            py,
            self.utterances
                .borrow(py)
                .languages(py)?
                .iter()
                .map(|code| code.as_str()),
        )
    }

    #[getter]
    fn corpora<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let mut corpora = Vec::new();
        for speaker in self.utterances.borrow(py).speakers(py)? {
            let corpus = speaker.participant.id.corpus.as_str().to_owned();
            if !corpora.contains(&corpus) {
                corpora.push(corpus);
            }
        }
        PyTuple::new(py, corpora)
    }

    fn __len__(&self, py: Python<'_>) -> usize {
        self.utterances.borrow(py).positions().len()
    }

    /// Derive headers, validate the document, and return canonical CHAT text.
    fn stringify(&self, py: Python<'_>) -> PyResult<String> {
        let utterances = self.utterances.borrow(py);
        let speakers = utterances.speakers(py)?;
        let languages = utterances.languages(py)?;
        let mut lines = participant_headers(&speakers, &languages);
        for entry in &utterances.entries {
            lines.push(match entry {
                Entry::Header(line) => line.clone(),
                Entry::Utterance(utterance) => {
                    let mut ast = utterance.borrow(py).ast.clone();
                    if let Some(language) = ast.utterance_language.code()
                        && Some(language) != languages.first()
                    {
                        ast.main.content.language_code = Some(language.clone());
                    }
                    Line::utterance(ast)
                }
            });
        }
        lines.push(Line::header(Header::End));
        let text = talkbank_model::model::ChatFile::new(lines).to_chat_string();
        parse_document(
            &text,
            talkbank_model::ParseValidateOptions::default().with_alignment(),
        )?;
        Ok(text)
    }

    fn __str__(&self, py: Python<'_>) -> PyResult<String> {
        self.stringify(py)
    }

    /// Write validated CHAT to an open text stream without closing it.
    fn write(&self, py: Python<'_>, fd: &Bound<'_, PyAny>) -> PyResult<()> {
        fd.call_method1("write", (self.stringify(py)?,))?;
        Ok(())
    }
}
