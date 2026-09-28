//! Acoustic phonetic transcription. CHAT unit ownership survives inference.

use crate::cache::{CacheKey, hash_serialized};
use crate::utils::{PreparedAudio, SourceId};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct PhoneticUnit {
    /// Original spoken text, or a CHAT pause to preserve structurally.
    pub text: String,
    pub pause: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct PhoneticUtterance {
    /// Line index in the source AST; results must echo it in order.
    pub index: usize,
    pub start_ms: u64,
    pub end_ms: u64,
    pub units: Vec<PhoneticUnit>,
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct PhoneticInput {
    pub source_id: SourceId,
    pub audio: PreparedAudio,
    pub language: String,
    pub utterances: Vec<PhoneticUtterance>,
}

impl CacheKey for PhoneticInput {
    fn hash(&self, hasher: &mut blake3::Hasher) {
        // Crop bounds and unit ownership affect both inference and projection.
        hash_serialized(&(&self.audio, &self.language, &self.utterances), hasher);
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct PhoneticResult {
    pub index: usize,
    /// One IPA string per input unit; pauses must be echoed unchanged.
    pub ipa: Vec<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct PhoneticOutput {
    pub source_id: SourceId,
    pub utterances: Vec<PhoneticResult>,
}

crate::register_proto_schema!(PhoneticUnit);
crate::register_proto_schema!(PhoneticUtterance);
crate::register_proto_schema!(PhoneticInput);
crate::register_proto_schema!(PhoneticResult);
crate::register_proto_schema!(PhoneticOutput);

#[cfg(test)]
mod tests {
    use super::*;

    fn digest(input: &PhoneticInput) -> blake3::Hash {
        let mut hasher = blake3::Hasher::new();
        input.hash(&mut hasher);
        hasher.finalize()
    }

    #[test]
    fn cache_tracks_audio_windows_and_reference_but_not_source_path() {
        let mut input = PhoneticInput {
            source_id: SourceId::try_new("a.cha").unwrap(),
            audio: PreparedAudio {
                pcm_f32le: vec![0; 64],
                sample_rate: 16000,
                channels: 1,
                frame_count: 16,
            },
            language: "eng".into(),
            utterances: vec![PhoneticUtterance {
                index: 0,
                start_ms: 0,
                end_ms: 1,
                units: vec![PhoneticUnit {
                    text: "cat".into(),
                    pause: false,
                }],
            }],
        };
        let original = digest(&input);
        input.source_id = SourceId::try_new("b.cha").unwrap();
        assert_eq!(digest(&input), original);
        input.utterances[0].end_ms = 2;
        assert_ne!(digest(&input), original);
        input.utterances[0].end_ms = 1;
        input.utterances[0].units[0].text = "dog".into();
        assert_ne!(digest(&input), original);
        input.utterances[0].units[0].text = "cat".into();
        input.audio.pcm_f32le[0] = 1;
        assert_ne!(digest(&input), original);
    }
}
