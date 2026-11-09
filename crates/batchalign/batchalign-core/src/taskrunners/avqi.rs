//! Decode both recordings, dispatch acoustic measurements, and emit a metrics row.
use crate::base::{BAValue, Dispatcher, ProgressEvent, ProgressSink, Task, TaskInput, TaskRunner};
use crate::metrics::{MetricsArtifact, MetricsKind, MetricsRow, MetricsTable};
use crate::proto::avqi::{AvqiInput, AvqiOutput};
use crate::utils::{BAError, BAResult, MediaInput, prepare_pcm};
use async_trait::async_trait;
use std::sync::Arc;

pub struct AvqiTaskRunner;

#[async_trait]
impl TaskRunner for AvqiTaskRunner {
    const TASK: Task = Task::Avqi;

    async fn apply(
        &self,
        value: &mut BAValue,
        dispatcher: &dyn Dispatcher,
        sink: Arc<dyn ProgressSink>,
    ) -> BAResult<()> {
        let pair = match value {
            BAValue::AvqiMedia(pair) => pair.clone(),
            BAValue::Failed { .. } => return Ok(()),
            other => {
                return Err(BAError::Internal(format!(
                    "AVQI requires AvqiMediaInput, got {}",
                    other.kind()
                )));
            }
        };
        sink.emit(ProgressEvent::stage_started(&pair.source_id, Task::Avqi));
        let decode = |path, label| {
            prepare_pcm(&MediaInput::new(pair.source_id.clone(), path))
                .map_err(|err| BAError::Internal(format!("AVQI {label} audio: {err:#}")))
        };
        let input = AvqiInput {
            source_id: pair.source_id.clone(),
            continuous_speech: decode(pair.continuous_speech.clone(), "continuous speech")?,
            sustained_vowel: decode(pair.sustained_vowel.clone(), "sustained vowel")?,
        };
        let output: AvqiOutput = dispatcher
            .dispatch(TaskInput::Avqi(input))
            .await?
            .try_into()?;
        let json = serde_json::to_value(&output)
            .map_err(|err| BAError::Internal(format!("AVQI metrics: {err}")))?;
        let mut columns = json
            .as_object()
            .ok_or_else(|| BAError::Internal("AVQI output must be an object".into()))?
            .iter()
            .map(|(key, value)| (key.clone(), value.clone()))
            .collect::<std::collections::BTreeMap<_, _>>();
        // Paths are input metadata, not cached backend values.
        columns.insert("source_id".into(), pair.source_id.as_str().into());
        columns.insert(
            "cs_file".into(),
            pair.continuous_speech.to_string_lossy().as_ref().into(),
        );
        columns.insert(
            "sv_file".into(),
            pair.sustained_vowel.to_string_lossy().as_ref().into(),
        );
        let schema = columns.keys().cloned().collect();
        *value = BAValue::Metrics(MetricsArtifact {
            source_id: pair.source_id.clone(),
            producer: "avqi:v1".into(),
            kind: MetricsKind::Custom,
            table: MetricsTable {
                schema,
                rows: vec![MetricsRow {
                    row_kind: "avqi".into(),
                    columns,
                }],
            },
        });
        sink.emit(ProgressEvent::stage_injected(&pair.source_id, Task::Avqi));
        Ok(())
    }
}
