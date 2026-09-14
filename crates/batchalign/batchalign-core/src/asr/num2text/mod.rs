//! JSON-driven recognition with language-specific number rendering.
//!
//! Language rules run in their listed order, followed by common rules. Patterns
//! use named captures and are anchored here, rather than relying on each JSON
//! author to remember anchors. The same compiled rule protects numeric punctuation
//! during ASR tokenization and recognizes the resulting complete token.
mod cjk;
mod common;
mod eng;
#[cfg(test)]
mod legacy_tests;
mod por;
mod table;
#[cfg(test)]
mod tests;

use regex::{Captures, Regex};
use serde::Deserialize;
use std::{collections::BTreeMap, ops::Range, sync::LazyLock};

pub(super) use common::language_percent_word;
type RenderResult = Result<String, &'static str>;

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum RuleKind {
    Cardinal,
    Ordinal,
    Decade,
    DigitGroups,
    HyphenCompound,
    Currency,
}

#[derive(Clone, Copy, Debug, Default, Deserialize)]
#[serde(rename_all = "snake_case")]
enum Renderer {
    #[default]
    Table,
    English,
    Portuguese,
    Simplified,
    Traditional,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RuleSpec {
    kind: RuleKind,
    pattern: String,
    #[serde(default)]
    protect_punctuation: bool,
}

#[derive(Default, Deserialize)]
#[serde(deny_unknown_fields)]
struct LanguageSpec {
    renderer: Renderer,
    #[serde(default)]
    rules: Vec<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RuleFile {
    rules: BTreeMap<String, RuleSpec>,
    common: Vec<String>,
    languages: BTreeMap<String, LanguageSpec>,
}

struct Rule {
    kind: RuleKind,
    full: Regex,
    prefix: Option<Regex>,
}
struct Rules {
    rules: BTreeMap<String, Rule>,
    common: Vec<String>,
    languages: BTreeMap<String, LanguageSpec>,
}

impl Rules {
    fn compile(json: &str) -> Result<Self, String> {
        let file: RuleFile = serde_json::from_str(json).map_err(|e| e.to_string())?;
        let mut rules = BTreeMap::new();
        for (name, spec) in file.rules {
            let full =
                Regex::new(&format!(r"\A(?:{})\z", spec.pattern)).map_err(|e| e.to_string())?;
            if full.is_match("") {
                return Err(format!("{name}: numeric rule must consume text"));
            }
            let required: &[&str] = match spec.kind {
                RuleKind::HyphenCompound => &["value", "rest"],
                RuleKind::Currency => &["value", "symbol"],
                _ => &["value"],
            };
            for capture in required {
                if !full.capture_names().flatten().any(|n| n == *capture) {
                    return Err(format!("{name}: missing capture {capture}"));
                }
            }
            let prefix = if spec.protect_punctuation {
                Some(Regex::new(&format!(r"\A(?:{})", spec.pattern)).map_err(|e| e.to_string())?)
            } else {
                None
            };
            rules.insert(
                name,
                Rule {
                    kind: spec.kind,
                    full,
                    prefix,
                },
            );
        }
        for name in file
            .common
            .iter()
            .chain(file.languages.values().flat_map(|l| &l.rules))
        {
            if !rules.contains_key(name) {
                return Err(format!("unknown numeric rule {name}"));
            }
        }
        // Portuguese ordinal rendering requires gender to be captured, not inferred.
        for lang in file.languages.values() {
            if matches!(lang.renderer, Renderer::Portuguese) {
                for name in &lang.rules {
                    let rule = &rules[name];
                    if rule.kind == RuleKind::Ordinal
                        && !rule.full.capture_names().flatten().any(|n| n == "gender")
                    {
                        return Err(format!("{name}: missing Portuguese gender capture"));
                    }
                }
            }
        }
        Ok(Self {
            rules,
            common: file.common,
            languages: file.languages,
        })
    }

    fn for_language(&self, lang: &str) -> impl Iterator<Item = &Rule> {
        self.languages
            .get(lang)
            .into_iter()
            .flat_map(|l| &l.rules)
            .chain(&self.common)
            .map(|name| &self.rules[name])
    }

    fn renderer(&self, lang: &str) -> Renderer {
        self.languages
            .get(lang)
            .map(|l| l.renderer)
            .unwrap_or_default()
    }
}

#[allow(clippy::expect_used)]
static RULES: LazyLock<Rules> = LazyLock::new(|| {
    Rules::compile(include_str!("../data/number_rules.json"))
        .expect("invalid embedded number rules")
});

/// Recognition is separate from rendering: unsupported numeric syntax stays
/// distinguishable from ordinary text. Spans are byte offsets into the input.
#[derive(Debug, PartialEq, Eq)]
pub(super) enum Expansion {
    NoMatch,
    Expanded {
        source_span: Range<usize>,
        text: String,
    },
    Unsupported {
        source_span: Range<usize>,
        reason: &'static str,
    },
}

struct RecognizedNumber<'a> {
    source_span: Range<usize>,
    kind: RuleKind,
    groups: Captures<'a>,
}

fn recognize<'a>(text: &'a str, lang: &str) -> Option<RecognizedNumber<'a>> {
    RULES.for_language(lang).find_map(|rule| {
        rule.full.captures(text).map(|groups| RecognizedNumber {
            source_span: 0..text.len(),
            kind: rule.kind,
            groups,
        })
    })
}

pub(super) fn expand(text: &str, lang: &str) -> Expansion {
    let lang = lang.to_ascii_lowercase();
    // Preserve the previous dash normalization, but retain original byte spans.
    let normalized = text.replace(['—', '–'], "-");
    let Some(number) = recognize(&normalized, &lang) else {
        return Expansion::NoMatch;
    };
    let renderer = RULES.renderer(&lang);
    let rendered = match (renderer, number.kind) {
        (Renderer::English, RuleKind::Ordinal | RuleKind::Decade) => {
            eng::render(number.kind, &number.groups)
        }
        (Renderer::Portuguese, RuleKind::Ordinal) => por::render(number.kind, &number.groups),
        _ => common::render(number.kind, &number.groups, &lang, renderer),
    };
    let source_span = if normalized == text {
        number.source_span
    } else {
        0..text.len()
    };
    match rendered {
        Ok(text) => Expansion::Expanded { source_span, text },
        Err(reason) => Expansion::Unsupported {
            source_span,
            reason,
        },
    }
}

/// Convenience API for a complete token. Unsupported input stays visible to
/// downstream CHAT validation; it is never silently discarded or guessed.
pub fn expand_number(word: &str, lang: &str) -> String {
    match expand(word, lang) {
        Expansion::Expanded { text, .. } => text,
        Expansion::Unsupported { reason, .. } => {
            tracing::debug!(word, lang, reason, "unsupported numeric expression");
            word.replace(['—', '–'], "-")
        }
        Expansion::NoMatch => word.replace(['—', '–'], "-"),
    }
}

/// At a token boundary, recognize an expression whose internal punctuation must
/// survive generic splitting. A trailing sentence separator remains unconsumed.
/// This operates on raw ASR text, before word expansion and CHAT construction.
pub(super) fn protected_prefix_len(text: &str, lang: &str) -> Option<usize> {
    let lang = lang.to_ascii_lowercase();
    RULES
        .for_language(&lang)
        .filter_map(|rule| rule.prefix.as_ref())
        .find_map(|regex| {
            let matched = regex.find(text)?;
            let end = matched.end();
            let boundary = text[end..].chars().next();
            if boundary.is_none_or(|ch| {
                ch.is_whitespace() || super::prepare::normalized_split_separator(ch).is_some()
            }) {
                Some(end)
            } else {
                None
            }
        })
}
