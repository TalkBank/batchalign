//! Editable, validated utterances with stable identity across collection edits.
use super::{
    Speaker,
    speaker::participant_headers,
    tiers::TierMap,
    utils::{parse_document, validate_inline},
};
use pyo3::{exceptions::PyValueError, prelude::*, types::PyTuple};
use talkbank_model::alignment::helpers::{TierDomain, collect_tier_items};
use talkbank_model::{
    WriteChat,
    model::{Bullet, Line, Utterance as ModelUtterance},
};

/// An editable CHAT utterance: typed speaker, main-tier text, optional millisecond timing.
#[pyclass(module = "batchalign.chat")]
pub struct Utterance {
    pub(super) speaker: Speaker,
    pub(super) ast: ModelUtterance,
}

impl Utterance {
    pub(super) fn from_ast(speaker: Speaker, mut ast: ModelUtterance) -> PyResult<Self> {
        let headers = participant_headers(
            std::slice::from_ref(&speaker),
            &super::utils::utterance_languages(&ast),
        );
        let mut text = headers
            .iter()
            .map(WriteChat::to_chat_string)
            .collect::<Vec<_>>()
            .join("\n");
        text.push_str(if ast.main.content.bullet.is_some() {
            "\n@Media:\tpython, audio\n"
        } else {
            "\n@Media:\tpython, audio, unlinked\n"
        });
        text.push_str(&ast.to_chat());
        text.push_str("@End\n");
        let parsed = parse_document(
            &text,
            talkbank_model::ParseValidateOptions::default().with_alignment(),
        )?;
        for line in parsed.lines.as_slice() {
            if let Line::Utterance(validated) = line {
                ast.utterance_language = validated.utterance_language.clone();
                ast.language_metadata = validated.language_metadata.clone();
            }
        }
        Ok(Self { speaker, ast })
    }
}

#[pymethods]
impl Utterance {
    #[new]
    #[pyo3(signature = (speaker, text, *, timing=None))]
    fn new(speaker: Speaker, text: &str, timing: Option<(u64, u64)>) -> PyResult<Self> {
        validate_inline(text)?;
        let headers = participant_headers(std::slice::from_ref(&speaker), &[]);
        let mut source = headers
            .iter()
            .map(WriteChat::to_chat_string)
            .collect::<Vec<_>>()
            .join("\n");
        source.push_str(&format!(
            "\n*{}:\t{text}\n@End\n",
            speaker.participant.code.as_str()
        ));
        let parsed = parse_document(
            &source,
            talkbank_model::ParseValidateOptions::default().with_alignment(),
        )?;
        let ast = parsed
            .lines
            .as_slice()
            .iter()
            .find_map(|line| match line {
                Line::Utterance(utterance) => Some(utterance.as_ref().clone()),
                _ => None,
            })
            .ok_or_else(|| PyValueError::new_err("text must contain one CHAT utterance"))?;
        let mut result = Self { speaker, ast };
        result.set_timing(timing)?;
        Ok(result)
    }

    #[getter]
    fn speaker(&self) -> Speaker {
        self.speaker.clone()
    }
    #[setter]
    fn set_speaker(&mut self, speaker: Speaker) -> PyResult<()> {
        let mut ast = self.ast.clone();
        ast.main.speaker = speaker.participant.code.clone();
        *self = Self::from_ast(speaker, ast)?;
        Ok(())
    }

    #[getter]
    fn text(&self) -> String {
        let mut content = self.ast.main.content.clone();
        content.bullet = None;
        content.to_content_string()
    }
    #[setter]
    fn set_text(&mut self, text: &str) -> PyResult<()> {
        let replacement = Self::new(self.speaker.clone(), text, self.timing())?;
        let mut ast = self.ast.clone();
        ast.main = replacement.ast.main;
        *self = Self::from_ast(self.speaker.clone(), ast)?;
        Ok(())
    }

    #[getter]
    fn timing(&self) -> Option<(u64, u64)> {
        self.ast
            .main
            .content
            .bullet
            .as_ref()
            .map(|bullet| (bullet.timing.start_ms, bullet.timing.end_ms))
    }
    #[setter]
    fn set_timing(&mut self, timing: Option<(u64, u64)>) -> PyResult<()> {
        if timing.is_some_and(|(start, end)| end <= start) {
            return Err(PyValueError::new_err("timing must have start < end"));
        }
        let mut ast = self.ast.clone();
        ast.main.content.bullet = timing.map(|(start, end)| Bullet::new(start, end));
        *self = Self::from_ast(self.speaker.clone(), ast)?;
        Ok(())
    }

    #[getter]
    fn words<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(
            py,
            collect_tier_items(&self.ast.main.content.content, TierDomain::Wor)
                .into_iter()
                .map(|item| item.text),
        )
    }
    #[getter]
    fn tiers(slf: PyRef<'_, Self>) -> TierMap {
        TierMap {
            utterance: slf.into(),
        }
    }
}
