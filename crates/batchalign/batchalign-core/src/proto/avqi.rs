//! Acoustic voice quality measurements for a continuous-speech / vowel pair.
use crate::cache::{CacheKey, hash_serialized};
use crate::utils::{PreparedAudio, SourceId};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct AvqiInput {
    pub source_id: SourceId,
    pub continuous_speech: PreparedAudio,
    pub sustained_vowel: PreparedAudio,
}

impl CacheKey for AvqiInput {
    fn hash(&self, hasher: &mut blake3::Hasher) {
        hash_serialized(&(&self.continuous_speech, &self.sustained_vowel), hasher);
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct AvqiOutput {
    pub source_id: SourceId,
    pub avqi: f64,
    pub cpps: f64,
    pub hnr: f64,
    /// Local shimmer in percent, not a proportion.
    pub shimmer_local: f64,
    pub shimmer_local_db: f64,
    pub slope: f64,
    pub tilt: f64,
    pub voiced_cs_duration: f64,
    pub sv_duration: f64,
    pub implementation: String,
}

crate::register_proto_schema!(AvqiInput);
crate::register_proto_schema!(AvqiOutput);
