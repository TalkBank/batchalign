//! Extract phonological units, dispatch acoustic inference, and add typed `%pho`.

use crate::base::{
    BAValue, Chat, Dispatcher, ProgressEvent, ProgressSink, ScaledProgress, Task, TaskInput,
    TaskRunner,
};
use crate::proto::phonetic::{PhoneticInput, PhoneticOutput, PhoneticUnit, PhoneticUtterance};
use crate::utils::{BAError, BAResult, prepare_pcm};
use async_trait::async_trait;
use std::sync::Arc;
use talkbank_model::alignment::helpers::{TierDomain, collect_tier_items};
use talkbank_model::{DependentTier, Line, PhoTier, PhoTierType};

pub struct PhoneticTaskRunner;

#[async_trait]
impl TaskRunner for PhoneticTaskRunner {
    const TASK: Task = Task::Phonetic;

    async fn apply(
        &self,
        value: &mut BAValue,
        dispatcher: &dyn Dispatcher,
        sink: Arc<dyn ProgressSink>,
    ) -> BAResult<()> {
        let chat = match value {
            BAValue::Chat(chat) => chat,
            BAValue::Failed { .. } => return Ok(()),
            other => {
                return Err(BAError::Validation(format!(
                    "phonetic requires CHAT, got {}",
                    other.kind()
                )));
            }
        };
        let utterances = extract_utterances(chat)?;
        if utterances.is_empty() {
            return Ok(());
        }
        let media = chat
            .media()
            .cloned()
            .or_else(|| super::media::sibling_media(chat))
            .ok_or_else(|| {
                BAError::Validation("phonetic requires @Media or sibling audio".into())
            })?;
        let input = PhoneticInput {
            source_id: chat.source_id().clone(),
            audio: prepare_pcm(&media)
                .map_err(|err| BAError::Internal(format!("audio_prep: {err:#}")))?,
            language: chat.primary_language().unwrap_or_default(),
            utterances: utterances.clone(),
        };
        sink.emit(ProgressEvent::stage_started(
            chat.source_id(),
            Task::Phonetic,
        ));
        let progress = Arc::new(ScaledProgress::new(
            sink.clone(),
            chat.source_id().clone(),
            Task::Phonetic,
            1,
        ));
        progress.start_step();
        let output: PhoneticOutput = dispatcher
            .dispatch_with_progress(TaskInput::Phonetic(input), progress)
            .await?
            .try_into()?;
        inject_tiers(chat, &utterances, output)?;
        sink.emit(ProgressEvent::stage_injected(
            chat.source_id(),
            Task::Phonetic,
        ));
        Ok(())
    }
}

fn extract_utterances(chat: &Chat) -> BAResult<Vec<PhoneticUtterance>> {
    let mut utterances = Vec::new();
    for (index, line) in chat.ast().lines.as_slice().iter().enumerate() {
        let Line::Utterance(utterance) = line else {
            continue;
        };
        if utterance
            .dependent_tiers
            .iter()
            .any(|entry| matches!(&entry.tier, DependentTier::Pho(_)))
        {
            continue;
        }
        let units: Vec<_> = collect_tier_items(&utterance.main.content.content, TierDomain::Pho)
            .into_iter()
            .map(|position| PhoneticUnit {
                pause: position.description.as_deref() == Some("pause"),
                text: position.text,
            })
            .collect();
        if units.is_empty() {
            continue;
        }
        let timing = utterance
            .main
            .content
            .bullet
            .as_ref()
            .map(|bullet| &bullet.timing)
            .filter(|timing| timing.end_ms > timing.start_ms)
            .ok_or_else(|| {
                BAError::Validation(format!(
                    "phonetic: line {} needs an utterance timing bullet; run utr first",
                    index + 1
                ))
            })?;
        utterances.push(PhoneticUtterance {
            index,
            start_ms: timing.start_ms,
            end_ms: timing.end_ms,
            units,
        });
    }
    Ok(utterances)
}

fn inject_tiers(
    chat: &mut Chat,
    inputs: &[PhoneticUtterance],
    output: PhoneticOutput,
) -> BAResult<()> {
    if inputs.len() != output.utterances.len() {
        return Err(BAError::Worker(
            "phonetic: utterance/output count mismatch".into(),
        ));
    }
    // Validate every result before changing the original AST.
    let mut revised = Chat::from_validated_ast(chat.ast().clone(), chat.source_id().clone());
    if let Some(media) = chat.media().cloned() {
        revised = revised.with_media(media);
    }
    for (input, result) in inputs.iter().zip(output.utterances) {
        if result.index != input.index || result.ipa.len() != input.units.len() {
            return Err(BAError::Worker(
                "phonetic: result unit ownership mismatch".into(),
            ));
        }
        for (unit, ipa) in input.units.iter().zip(&result.ipa) {
            if (unit.pause && ipa != &unit.text)
                || ipa.is_empty()
                || ipa.chars().any(|ch| ch.is_whitespace() || ch.is_control())
            {
                return Err(BAError::Worker(format!(
                    "phonetic: invalid IPA unit {ipa:?}"
                )));
            }
        }
        let Line::Utterance(utterance) = &mut revised.ast_mut().lines.as_mut_slice()[input.index]
        else {
            unreachable!()
        };
        utterance
            .dependent_tiers
            .push(DependentTier::Pho(PhoTier::from_tokens(PhoTierType::Pho, result.ipa)).into());
    }
    revised.validate_stage_output(Task::Phonetic)?;
    *chat = revised;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::proto::phonetic::PhoneticResult;
    use crate::utils::SourceId;

    fn chat(content: &str) -> Chat {
        let linkage = if content.contains('\u{15}') {
            "audio"
        } else {
            "audio, unlinked"
        };
        Chat::parse(&format!("@UTF8\n@Begin\n@Languages:\teng\n@Participants:\tPAR Participant\n@ID:\teng|test|PAR|||||Participant|||\n@Media:\tsample, {linkage}\n{content}@End\n"), SourceId::try_new("test.cha").unwrap()).unwrap()
    }

    #[test]
    fn extracts_phonological_positions_including_retraces_and_pauses() {
        let source = chat("*PAR:\t<the cat> [/] the (.) dog . \u{15}0_1000\u{15}\n");
        let utterances = extract_utterances(&source).unwrap();
        let texts: Vec<_> = utterances[0]
            .units
            .iter()
            .map(|unit| unit.text.as_str())
            .collect();
        assert_eq!(texts, ["the", "cat", "the", "(.)", "dog"]);
        assert!(utterances[0].units[3].pause);
    }

    #[test]
    fn preserves_existing_pho_without_requiring_timing() {
        let source = chat("*PAR:\tcat .\n%pho:\tkæt\n");
        assert!(extract_utterances(&source).unwrap().is_empty());
    }

    #[test]
    fn phonological_groups_and_replacements_use_original_spoken_positions() {
        let source = chat("*PAR:\t‹the cat› dog [: dogs] &-um &+ca . \u{15}0_1000\u{15}\n");
        let utterances = extract_utterances(&source).unwrap();
        let texts: Vec<_> = utterances[0]
            .units
            .iter()
            .map(|unit| unit.text.as_str())
            .collect();
        assert_eq!(texts, ["‹the cat›", "dog", "&-um", "&+ca"]);
    }

    #[test]
    fn validates_all_results_before_mutating_chat() {
        let mut source =
            chat("*PAR:\tcat . \u{15}0_1000\u{15}\n*PAR:\tdog . \u{15}1000_2000\u{15}\n");
        let before = source.to_chat();
        let inputs = extract_utterances(&source).unwrap();
        let output = PhoneticOutput {
            source_id: source.source_id().clone(),
            utterances: vec![
                PhoneticResult {
                    index: inputs[0].index,
                    ipa: vec!["kæt".into()],
                },
                PhoneticResult {
                    index: inputs[1].index,
                    ipa: vec![],
                },
            ],
        };
        assert!(inject_tiers(&mut source, &inputs, output).is_err());
        assert_eq!(source.to_chat(), before);
    }

    #[test]
    fn inserts_roundtrippable_ipa_without_changing_main_tier() {
        let mut source = chat("*PAR:\tcat . \u{15}0_1000\u{15}\n");
        let inputs = extract_utterances(&source).unwrap();
        let output = PhoneticOutput {
            source_id: source.source_id().clone(),
            utterances: vec![PhoneticResult {
                index: inputs[0].index,
                ipa: vec!["kʰæ̃t".into()],
            }],
        };
        inject_tiers(&mut source, &inputs, output).unwrap();
        let serialized = source.to_chat();
        assert!(serialized.contains("%pho:\tkʰæ̃t"));
        assert!(serialized.contains("*PAR:\tcat ."));
        Chat::parse(&serialized, source.source_id().clone()).unwrap();
    }
}
