//! Shared expression handlers. Recognition and capture boundaries come from JSON.
use super::{RenderResult, Renderer, RuleKind, cjk, table};
use regex::Captures;

pub(super) fn cardinal(value: &str, lang: &str, renderer: Renderer) -> Option<String> {
    match renderer {
        Renderer::Simplified | Renderer::Traditional => {
            cjk::cardinal(value, renderer).or_else(|| table::cardinal(value, lang))
        }
        _ => table::cardinal(value, lang),
    }
}

pub(super) fn render(
    kind: RuleKind,
    groups: &Captures<'_>,
    lang: &str,
    renderer: Renderer,
) -> RenderResult {
    let expand = |value: &str| cardinal(value, lang, renderer).unwrap_or_else(|| value.to_owned());
    match kind {
        RuleKind::Cardinal => cardinal(&groups["value"], lang, renderer)
            .ok_or("no cardinal rendering for this language or magnitude"),
        RuleKind::DigitGroups => Ok(groups["value"]
            .split('-')
            .map(expand)
            .collect::<Vec<_>>()
            .join(" ")),
        RuleKind::HyphenCompound => {
            if talkbank_model::validation::language_allows_numbers(lang) {
                return Err("language permits digits in compounds");
            }
            let value = &groups["value"];
            let expanded = expand(value);
            if expanded == value {
                return Err("no cardinal rendering for compound");
            }
            Ok(format!("{expanded}-{}", &groups["rest"]))
        }
        RuleKind::Currency => {
            // Preserve the historical currency vocabulary, including its English
            // labels for non-English transcripts. Localizing it is a separate change.
            let currency = match &groups["symbol"] {
                "$" => "dollars",
                "€" => "euros",
                "£" => "pounds",
                "¥" => "yen",
                "₹" => "rupees",
                "₩" => "won",
                "₽" => "rubles",
                _ => return Err("unsupported currency"),
            };
            Ok(format!("{} {currency}", expand(&groups["value"])))
        }
        _ => Err("language has no renderer for this number expression"),
    }
}

/// Per-language word for "percent", used when an ASR provider emits a bare
/// `%`-suffixed numeric token (e.g. Rev.AI returning `"80%"`). The Rust
/// post-processor strips `%`, expands the digit part, and appends the
/// language-specific percent word so the output reaches the CHAT tier as
/// legal main-tier word content (`%` is the CHAT dep-tier sigil and cannot
/// appear on the main tier in any language).
///
/// Tracked by ISO 639-3 code. Languages not listed here fall back to the
/// English word; a future extension can delete that fallback once the
/// remaining coverage gaps are audited. (Decision N1 from the
/// 2026-04-22 ASR-normalization design, operator-local.)
const PERCENT_WORD_BY_LANG: &[(&str, &str)] = &[
    ("eng", "percent"),
    ("fra", "pour_cent"),
    ("spa", "por_ciento"),
    ("deu", "Prozent"),
    ("ita", "per_cento"),
    ("por", "por_cento"),
    ("nld", "procent"),
    ("jpn", "パーセント"),
    ("zho", "百分"),
    ("cmn", "百分"),
    ("yue", "百分"),
];

/// Language-specific CHAT word for the percent symbol.
///
/// Returns the per-language word to substitute when `%` is stripped from an
/// ASR token, or `None` if no mapping is known. Callers fall back to a
/// reasonable default (typically eng) rather than panicking on unmapped
/// languages — the goal is that the CHAT output is never worse than it
/// would have been without the normalizer.
pub fn language_percent_word(lang: &str) -> Option<&'static str> {
    let lower = lang.to_lowercase();
    PERCENT_WORD_BY_LANG
        .iter()
        .find(|(l, _)| *l == lower.as_str())
        .map(|(_, w)| *w)
}
