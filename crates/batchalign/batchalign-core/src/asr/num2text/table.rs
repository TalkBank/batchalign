//! Existing cardinal tables and integer decomposition.
use std::{collections::BTreeMap, sync::LazyLock};

/// Language-specific number-to-word tables loaded from JSON at compile time.
///
/// Keys are ISO 639-3 language codes. Values are BTreeMaps where keys are
/// number strings (e.g. "1", "21", "100") and values are word forms.
// Data is compile-time-constant: `include_str!` embeds the JSON at build time.
#[allow(clippy::unwrap_used)]
pub(super) static NUM2LANG: LazyLock<BTreeMap<String, BTreeMap<String, String>>> =
    LazyLock::new(|| serde_json::from_str(include_str!("../data/num2lang.json")).unwrap());

pub(super) fn cardinal(word: &str, lang: &str) -> Option<String> {
    let table = NUM2LANG.get(lang)?;
    table.get(word).cloned().or_else(|| {
        word.parse::<u64>()
            .ok()
            .and_then(|n| decompose_with_table(n, table))
    })
}

/// Decompose a number into words using a lookup table.
///
/// Strategy: greedily subtract the largest table entry that fits,
/// building up the word form. E.g., 1234 → "one thousand two hundred
/// thirty-four" (if table has 1000, 200, 34 or 30+4).
fn decompose_with_table(mut n: u64, table: &BTreeMap<String, String>) -> Option<String> {
    if n == 0 {
        return table.get("0").cloned();
    }

    // Build a sorted list of (numeric_key, word) pairs, largest first
    let mut entries: Vec<(u64, &str)> = table
        .iter()
        .filter_map(|(k, v)| k.parse::<u64>().ok().map(|num| (num, v.as_str())))
        .filter(|(num, _)| *num > 0)
        .collect();
    entries.sort_by_key(|b| std::cmp::Reverse(b.0));

    let mut parts: Vec<String> = Vec::new();

    for &(key_num, word_form) in &entries {
        if key_num == 0 {
            continue;
        }
        if key_num <= n {
            if key_num >= 100 {
                // For hundreds/thousands: "two hundred", "three thousand"
                let multiplier = n / key_num;
                let remainder = n % key_num;
                if multiplier > 1 {
                    // Recursively expand the multiplier
                    if let Some(mult_word) = decompose_with_table(multiplier, table) {
                        parts.push(format!("{mult_word} {word_form}"));
                    } else {
                        // Can't expand multiplier — bail
                        return None;
                    }
                } else {
                    parts.push(word_form.to_string());
                }
                n = remainder;
                if n == 0 {
                    break;
                }
            } else {
                // For units/teens/tens: exact match
                parts.push(word_form.to_string());
                n -= key_num;
                if n == 0 {
                    break;
                }
            }
        }
    }

    if n > 0 {
        // Couldn't fully decompose
        return None;
    }

    if parts.is_empty() {
        return None;
    }

    Some(parts.join(" "))
}
