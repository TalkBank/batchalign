//! Ordered utterance editing, retaining unrelated headers in file order.
use super::{Speaker, Utterance, utils::sequence_index};
use pyo3::{exceptions::PyValueError, prelude::*, types::PyList};
use talkbank_model::model::{LanguageCode, Line};

pub(super) enum Entry {
    Header(Line),
    Utterance(Py<Utterance>),
}

#[pyclass(module = "batchalign.chat")]
#[derive(Default)]
pub(super) struct UtteranceCollection {
    pub(super) entries: Vec<Entry>,
}

impl UtteranceCollection {
    pub(super) fn positions(&self) -> Vec<usize> {
        self.entries
            .iter()
            .enumerate()
            .filter_map(|(index, entry)| matches!(entry, Entry::Utterance(_)).then_some(index))
            .collect()
    }

    pub(super) fn languages(&self, py: Python<'_>) -> PyResult<Vec<LanguageCode>> {
        let mut languages = Vec::new();
        for speaker in self.speakers(py)? {
            for language in speaker.participant.id.language.iter() {
                if !languages.contains(language) {
                    languages.push(language.clone());
                }
            }
        }
        for entry in &self.entries {
            if let Entry::Utterance(utterance) = entry {
                for language in super::utils::utterance_languages(&utterance.borrow(py).ast) {
                    if !languages.contains(&language) {
                        languages.push(language);
                    }
                }
            }
        }
        Ok(languages)
    }

    pub(super) fn speakers(&self, py: Python<'_>) -> PyResult<Vec<Speaker>> {
        let mut speakers: Vec<Speaker> = Vec::new();
        for entry in &self.entries {
            if let Entry::Utterance(utterance) = entry {
                let speaker = utterance.borrow(py).speaker.clone();
                if let Some(existing) = speakers
                    .iter()
                    .find(|other| other.participant.code == speaker.participant.code)
                {
                    if existing.participant != speaker.participant {
                        return Err(PyValueError::new_err(format!(
                            "conflicting metadata for speaker {}",
                            speaker.participant.code
                        )));
                    }
                } else {
                    speakers.push(speaker);
                }
            }
        }
        Ok(speakers)
    }
}

#[pymethods]
impl UtteranceCollection {
    fn __len__(&self) -> usize {
        self.positions().len()
    }

    fn __getitem__(&self, py: Python<'_>, index: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        let utterances: Vec<_> = self
            .entries
            .iter()
            .filter_map(|entry| match entry {
                Entry::Utterance(utterance) => Some(utterance.clone_ref(py)),
                _ => None,
            })
            .collect();
        Ok(PyList::new(py, utterances)?
            .as_any()
            .get_item(index)?
            .unbind())
    }

    fn __iter__(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let utterances: Vec<_> = self
            .entries
            .iter()
            .filter_map(|entry| match entry {
                Entry::Utterance(utterance) => Some(utterance.clone_ref(py)),
                _ => None,
            })
            .collect();
        Ok(PyList::new(py, utterances)?
            .call_method0("__iter__")?
            .unbind())
    }

    fn append(&mut self, py: Python<'_>, utterance: Py<Utterance>) -> PyResult<()> {
        self.entries.push(Entry::Utterance(utterance));
        if let Err(error) = self.speakers(py) {
            self.entries.pop();
            return Err(error);
        }
        Ok(())
    }

    fn insert(&mut self, py: Python<'_>, index: isize, utterance: Py<Utterance>) -> PyResult<()> {
        let positions = self.positions();
        let len = positions.len() as isize;
        let index = if index < 0 {
            (len + index).max(0)
        } else {
            index.min(len)
        } as usize;
        let position = positions.get(index).copied().unwrap_or(self.entries.len());
        self.entries.insert(position, Entry::Utterance(utterance));
        if let Err(error) = self.speakers(py) {
            self.entries.remove(position);
            return Err(error);
        }
        Ok(())
    }

    fn __setitem__(
        &mut self,
        py: Python<'_>,
        index: isize,
        utterance: Py<Utterance>,
    ) -> PyResult<()> {
        let positions = self.positions();
        let position = positions[sequence_index(index, positions.len())?];
        let previous = std::mem::replace(&mut self.entries[position], Entry::Utterance(utterance));
        if let Err(error) = self.speakers(py) {
            self.entries[position] = previous;
            return Err(error);
        }
        Ok(())
    }

    fn __delitem__(&mut self, index: isize) -> PyResult<()> {
        let positions = self.positions();
        self.entries
            .remove(positions[sequence_index(index, positions.len())?]);
        Ok(())
    }

    #[pyo3(signature = (index=-1))]
    fn pop(&mut self, index: isize) -> PyResult<Py<Utterance>> {
        let positions = self.positions();
        match self
            .entries
            .remove(positions[sequence_index(index, positions.len())?])
        {
            Entry::Utterance(utterance) => Ok(utterance),
            Entry::Header(_) => unreachable!("positions only contains utterances"),
        }
    }

    fn clear(&mut self) {
        self.entries
            .retain(|entry| matches!(entry, Entry::Header(_)));
    }
}
