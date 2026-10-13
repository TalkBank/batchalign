//! Python's editable CHAT document API. The model and all edits stay in Rust.
mod collection;
mod document;
mod media;
mod speaker;
mod tiers;
mod utils;
mod utterance;

pub use document::CHATFile;
pub use media::Media;
pub use speaker::Speaker;
pub use utterance::Utterance;
