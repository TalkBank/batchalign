//! Immutable participant metadata; utterances refer to these values.
use super::utils::{parse_document, validate_inline};
use pyo3::{exceptions::PyValueError, prelude::*, types::PyTuple};
use talkbank_model::WriteChat;
use talkbank_model::model::{
    Header, IDHeader, LanguageCode, LanguageCodes, Line, Participant, ParticipantEntries,
    ParticipantEntry, ParticipantName, ParticipantRole, SpeakerCode,
};

/// Immutable speaker metadata. Language and corpus are required; role defaults to Participant.
#[pyclass(frozen, from_py_object, module = "batchalign.chat")]
#[derive(Clone)]
pub struct Speaker {
    pub(super) participant: Participant,
}

#[pymethods]
impl Speaker {
    #[new]
    #[pyo3(signature = (code, *, language, corpus, role="Participant", name=None))]
    fn new(
        code: &str,
        language: &Bound<'_, PyAny>,
        corpus: &str,
        role: &str,
        name: Option<&str>,
    ) -> PyResult<Self> {
        for value in [code, corpus, role].into_iter().chain(name) {
            validate_inline(value)?;
            if value.contains('|') {
                return Err(PyValueError::new_err("speaker fields cannot contain pipes"));
            }
        }
        let languages: Vec<String> = if let Ok(value) = language.extract::<String>() {
            vec![value]
        } else {
            language.extract::<Vec<String>>()?
        };
        let languages = languages
            .iter()
            .map(LanguageCode::new)
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| PyValueError::new_err(error.to_string()))?;
        let entry = ParticipantEntry {
            speaker_code: SpeakerCode::new(code),
            name: name.map(ParticipantName::new),
            role: ParticipantRole::new(role),
        };
        let id =
            IDHeader::from_languages(LanguageCodes::new(languages), code, role).with_corpus(corpus);
        let speaker = Self {
            participant: Participant::new(entry, id),
        };
        // Use the same model validation as parsed files, including role/code vocabulary.
        let mut text = participant_headers(std::slice::from_ref(&speaker), &[])
            .iter()
            .map(WriteChat::to_chat_string)
            .collect::<Vec<_>>()
            .join("\n");
        text.push_str(&format!("\n*{code}:\txxx .\n@End\n"));
        parse_document(
            &text,
            talkbank_model::ParseValidateOptions::default().with_alignment(),
        )?;
        Ok(speaker)
    }

    #[getter]
    fn code(&self) -> &str {
        self.participant.code.as_str()
    }
    #[getter]
    fn role(&self) -> &str {
        self.participant.role.as_str()
    }
    #[getter]
    fn name(&self) -> Option<&str> {
        self.participant.name.as_ref().map(|name| name.as_str())
    }
    #[getter]
    fn corpus(&self) -> &str {
        self.participant.id.corpus.as_str()
    }
    #[getter]
    fn languages<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(
            py,
            self.participant
                .id
                .language
                .iter()
                .map(|code| code.as_str()),
        )
    }

    fn __repr__(&self) -> String {
        format!(
            "Speaker(code={:?}, corpus={:?}, role={:?})",
            self.code(),
            self.corpus(),
            self.role()
        )
    }
    fn __eq__(&self, other: &Self) -> bool {
        self.participant == other.participant
    }
}

pub(super) fn participant_headers(speakers: &[Speaker], additional: &[LanguageCode]) -> Vec<Line> {
    let mut languages = Vec::new();
    for speaker in speakers {
        for language in speaker.participant.id.language.iter() {
            if !languages.contains(language) {
                languages.push(language.clone());
            }
        }
    }
    for language in additional {
        if !languages.contains(language) {
            languages.push(language.clone());
        }
    }
    let mut lines = vec![Line::header(Header::Utf8), Line::header(Header::Begin)];
    if !speakers.is_empty() {
        lines.push(Line::header(Header::Languages {
            codes: LanguageCodes::new(languages),
        }));
        lines.push(Line::header(Header::Participants {
            entries: ParticipantEntries::new(
                speakers
                    .iter()
                    .map(|speaker| ParticipantEntry {
                        speaker_code: speaker.participant.code.clone(),
                        name: speaker.participant.name.clone(),
                        role: speaker.participant.role.clone(),
                    })
                    .collect(),
            ),
        }));
        lines.extend(
            speakers
                .iter()
                .map(|speaker| Line::header(Header::ID(speaker.participant.id.clone()))),
        );
    }
    lines
}
