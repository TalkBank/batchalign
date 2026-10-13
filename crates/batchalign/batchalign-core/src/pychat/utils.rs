//! Flat boundary utilities shared by the Python CHAT types.
use pyo3::{
    exceptions::{PyIndexError, PyValueError},
    prelude::*,
};
use talkbank_model::ParseValidateOptions;
use talkbank_model::model::ChatFile;
use talkbank_transform::parse_and_validate;

pub(super) fn parse_document(text: &str, options: ParseValidateOptions) -> PyResult<ChatFile> {
    let mut ast = parse_and_validate(text, ParseValidateOptions::default()).map_err(|error| {
        let message = match error {
            talkbank_transform::PipelineError::Parse(errors) => errors.to_string(),
            other => other.to_string(),
        };
        PyValueError::new_err(message)
    })?;
    let empty = !ast
        .lines
        .as_slice()
        .iter()
        .any(|line| matches!(line, talkbank_model::model::Line::Utterance(_)));
    let errors = talkbank_model::pipeline::validate_chat_file_with_options(&mut ast, &options)
        .err()
        .unwrap_or_default();
    let errors: Vec<_> = errors
        .into_iter()
        .filter(|error| {
            // Empty drafts have no speakers from which to derive these two headers.
            let draft_header = empty
                && error.code == talkbank_model::ErrorCode::MissingRequiredHeader
                && (error.message.contains("@Languages")
                    || error.message.contains("@Participants"));
            error.severity == talkbank_model::Severity::Error && !draft_header
        })
        .collect();
    if !errors.is_empty() {
        return Err(PyValueError::new_err(
            errors
                .iter()
                .map(ToString::to_string)
                .collect::<Vec<_>>()
                .join("\n"),
        ));
    }
    Ok(ast)
}

pub(super) fn validate_inline(value: &str) -> PyResult<()> {
    if value.chars().any(char::is_control) {
        return Err(PyValueError::new_err(
            "CHAT inline values cannot contain control characters",
        ));
    }
    Ok(())
}

pub(super) fn sequence_index(index: isize, len: usize) -> PyResult<usize> {
    let index = if index < 0 {
        len as isize + index
    } else {
        index
    };
    if index < 0 || index as usize >= len {
        Err(PyIndexError::new_err("utterance index out of range"))
    } else {
        Ok(index as usize)
    }
}

/// Read resolved languages through the model's traversal metadata, not raw text.
pub(super) fn utterance_languages(
    utterance: &talkbank_model::model::Utterance,
) -> Vec<talkbank_model::model::LanguageCode> {
    let mut languages = Vec::new();
    if let Some(language) = utterance
        .main
        .content
        .language_code
        .as_ref()
        .or(utterance.utterance_language.code())
    {
        languages.push(language.clone());
    }
    if let Some(metadata) = utterance.computed_language_metadata() {
        for word in metadata.word_languages.iter() {
            for language in word.languages.languages() {
                if !languages.contains(language) {
                    languages.push(language.clone());
                }
            }
        }
    }
    languages
}
