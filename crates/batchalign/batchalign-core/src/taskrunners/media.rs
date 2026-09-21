//! Shared media lookup for audio-backed CHAT tasks.

use crate::base::Chat;
use crate::utils::MediaInput;
use std::path::Path;

const SIBLING_MEDIA_EXTS: &[&str] = &[
    "wav", "mp3", "mp4", "m4a", "flac", "ogg", "aac", "wma", "mov", "m4v", "avi", "mpg", "mpeg",
];

/// Resolve media for CHAT loaded from disk. Prefer the typed `@Media`
/// basename, then fall back to the transcript's own stem.
pub(super) fn sibling_media(chat: &Chat) -> Option<MediaInput> {
    let chat_path = Path::new(chat.source_id().as_str());
    let mut stems = Vec::new();
    if let (Some(parent), Some(header)) = (chat_path.parent(), chat.ast().media.as_deref()) {
        stems.push(parent.join(header.filename.as_str()));
    }
    stems.push(chat_path.with_extension(""));

    for stem in stems {
        for ext in SIBLING_MEDIA_EXTS {
            for candidate_ext in [ext.to_string(), ext.to_ascii_uppercase()] {
                // @Media is a basename, so preserve dots within that name.
                let mut filename = stem.as_os_str().to_os_string();
                filename.push(format!(".{candidate_ext}"));
                let candidate = std::path::PathBuf::from(filename);
                if candidate.is_file() {
                    return Some(MediaInput::new(chat.source_id().clone(), candidate));
                }
            }
        }
    }
    None
}
