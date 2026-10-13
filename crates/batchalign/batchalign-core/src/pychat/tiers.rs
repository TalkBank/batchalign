//! Live dependent-tier mapping; edits are parsed and validated before commit.
use super::{
    Utterance,
    speaker::participant_headers,
    utils::{parse_document, validate_inline},
};
use pyo3::{
    exceptions::{PyKeyError, PyValueError},
    prelude::*,
    types::PyTuple,
};
use talkbank_model::WriteChat;
use talkbank_model::model::Line;

#[pyclass(module = "batchalign.chat")]
pub(super) struct TierMap {
    pub(super) utterance: Py<Utterance>,
}

#[pymethods]
impl TierMap {
    fn __len__(&self, py: Python<'_>) -> usize {
        self.utterance.borrow(py).ast.dependent_tiers.len()
    }

    fn __getitem__(&self, py: Python<'_>, key: &str) -> PyResult<String> {
        let utterance = self.utterance.borrow(py);
        let tier = utterance
            .ast
            .dependent_tiers
            .iter()
            .find(|tier| tier.kind() == key)
            .ok_or_else(|| PyKeyError::new_err(key.to_owned()))?;
        let text = tier.to_chat_string();
        Ok(text
            .split_once(':')
            .map(|(_, value)| value.trim_start_matches('\t').to_owned())
            .unwrap_or_default())
    }

    fn __iter__(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let utterance = self.utterance.borrow(py);
        Ok(PyTuple::new(
            py,
            utterance.ast.dependent_tiers.iter().map(|tier| tier.kind()),
        )?
        .call_method0("__iter__")?
        .unbind())
    }

    fn __setitem__(&self, py: Python<'_>, key: &str, value: &str) -> PyResult<()> {
        validate_inline(value)?;
        if key.is_empty()
            || !key
                .chars()
                .all(|ch| ch.is_ascii_lowercase() || ch.is_ascii_digit())
        {
            return Err(PyValueError::new_err(
                "tier key must be a label such as 'pho' without '%'",
            ));
        }
        let mut utterance = self.utterance.borrow_mut(py);
        let headers = participant_headers(
            std::slice::from_ref(&utterance.speaker),
            &super::utils::utterance_languages(&utterance.ast),
        );
        let mut source = headers
            .iter()
            .map(WriteChat::to_chat_string)
            .collect::<Vec<_>>()
            .join("\n");
        source.push_str("\n@Media:\tpython, audio\n");
        source.push_str(&utterance.ast.main.to_chat_string());
        source.push_str(&format!("\n%{key}:\t{value}\n@End\n"));
        let parsed = parse_document(&source, talkbank_model::ParseValidateOptions::default())?;
        let tier = parsed
            .lines
            .as_slice()
            .iter()
            .find_map(|line| match line {
                Line::Utterance(utterance) => utterance.dependent_tiers.first().cloned(),
                _ => None,
            })
            .ok_or_else(|| PyValueError::new_err("expected one dependent tier"))?;
        let mut ast = utterance.ast.clone();
        if let Some(existing) = ast
            .dependent_tiers
            .iter_mut()
            .find(|tier| tier.kind() == key)
        {
            *existing = tier;
        } else {
            ast.dependent_tiers.push(tier);
        }
        *utterance = Utterance::from_ast(utterance.speaker.clone(), ast)?;
        Ok(())
    }

    fn __delitem__(&self, py: Python<'_>, key: &str) -> PyResult<()> {
        let mut utterance = self.utterance.borrow_mut(py);
        let mut ast = utterance.ast.clone();
        let index = ast
            .dependent_tiers
            .iter()
            .position(|tier| tier.kind() == key)
            .ok_or_else(|| PyKeyError::new_err(key.to_owned()))?;
        ast.dependent_tiers.remove(index);
        *utterance = Utterance::from_ast(utterance.speaker.clone(), ast)?;
        Ok(())
    }
}
