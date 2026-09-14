use super::table::NUM2LANG;
use super::*;

#[test]
fn test_non_digit_passthrough() {
    assert_eq!(expand_number("hello", "eng"), "hello");
    assert_eq!(expand_number("abc123", "eng"), "abc123");
}

#[test]
fn test_english_basic() {
    assert_eq!(expand_number("5", "eng"), "five");
    assert_eq!(expand_number("1", "eng"), "one");
    assert_eq!(expand_number("10", "eng"), "ten");
    assert_eq!(expand_number("99", "eng"), "ninety-nine");
}

#[test]
fn test_english_hundreds() {
    let result = expand_number("100", "eng");
    assert!(
        result.contains("hundred") || result.contains("one hundred"),
        "got: {result}"
    );
}

#[test]
fn test_spanish() {
    assert_eq!(expand_number("1", "spa"), "uno");
    assert_eq!(expand_number("5", "spa"), "cinco");
}

#[test]
fn test_chinese_simplified() {
    assert_eq!(expand_number("5", "zho"), "五");
    assert_eq!(expand_number("42", "zho"), "四十二");
    assert_eq!(expand_number("1000", "zho"), "一千");
}

#[test]
fn test_japanese() {
    assert_eq!(expand_number("5", "jpn"), "五");
    assert_eq!(expand_number("10000", "jpn"), "一萬"); // traditional
}

#[test]
fn test_dash_separated() {
    // "21-22" → expand each part
    let result = expand_number("21-22", "eng");
    assert!(result.contains(' '), "expected space-separated: {result}");
}

#[test]
fn test_em_dash_normalized() {
    let result = expand_number("5—6", "eng");
    assert!(result.contains("five"), "got: {result}");
    assert!(result.contains("six"), "got: {result}");
}

#[test]
fn test_unknown_language_passthrough() {
    assert_eq!(expand_number("42", "xxx"), "42");
}

#[test]
fn test_num2lang_tables_loaded() {
    // Verify all 13 languages are present (12 original + Malayalam
    // added 2026-04-26 to address the Whisper-Hub digit emission bug).
    let expected = [
        "deu", "ell", "eng", "eus", "fra", "hrv", "ind", "jpn", "mal", "nld", "por", "spa", "tha",
    ];
    for lang in &expected {
        assert!(NUM2LANG.contains_key(*lang), "missing language: {lang}");
    }
}

/// Regression test for the 2026-04-26 Whisper-Hub Malayalam digit
/// bug. HuggingFace Whisper fine-tunes (e.g.,
/// `thennal/whisper-medium-ml`) transcribe spoken numbers as Arabic
/// digits ("3") rather than Malayalam script. CHAT validation then
/// rejects with E220 ("numeric digits not allowed in language(s)
/// `mal`"). The `num2words` Python library has no Malayalam
/// backend, so the Python expansion path returned the digit
/// unchanged. Covered here at the Rust `NUM2LANG` layer so the
/// digit is expanded before it ever reaches the validator.
#[test]
fn malayalam_single_digits_expand_to_script() {
    assert_eq!(expand_number("0", "mal"), "പൂജ്യം");
    assert_eq!(expand_number("1", "mal"), "ഒന്ന്");
    assert_eq!(expand_number("3", "mal"), "മൂന്ന്");
    assert_eq!(expand_number("9", "mal"), "ഒമ്പത്");
}

#[test]
fn malayalam_anchor_decades_and_hundreds() {
    // Anchor entries the decompose path relies on for higher numbers.
    assert_eq!(expand_number("10", "mal"), "പത്ത്");
    assert_eq!(expand_number("20", "mal"), "ഇരുപത്");
    assert_eq!(expand_number("100", "mal"), "നൂറ്");
}

#[test]
fn test_empty_string() {
    assert_eq!(expand_number("", "eng"), "");
}

// --- currency expansion ---

#[test]
fn test_dollar_prefix() {
    let result = expand_number("$5", "eng");
    assert!(
        result.contains("five") && result.contains("dollars"),
        "got: {result}"
    );
}

#[test]
fn test_dollar_large() {
    let result = expand_number("$100", "eng");
    assert!(
        result.contains("hundred") && result.contains("dollars"),
        "got: {result}"
    );
}

#[test]
fn test_dollar_no_digits_in_output() {
    // The key requirement: currency-prefixed numbers must not contain
    // raw digits in the output (which would trigger E220).
    let result = expand_number("$5", "eng");
    assert!(
        !result.chars().any(|c| c.is_ascii_digit()),
        "output should not contain digits: {result}"
    );
}

#[test]
fn test_euro_prefix() {
    let result = expand_number("€50", "eng");
    assert!(
        result.contains("fifty") && result.contains("euros"),
        "got: {result}"
    );
}

#[test]
fn test_euro_suffix() {
    let result = expand_number("50€", "eng");
    assert!(
        result.contains("fifty") && result.contains("euros"),
        "got: {result}"
    );
}

#[test]
fn test_pound_prefix() {
    let result = expand_number("£5", "eng");
    assert!(
        result.contains("five") && result.contains("pounds"),
        "got: {result}"
    );
}

#[test]
fn test_yen_prefix() {
    let result = expand_number("¥1000", "jpn");
    assert!(
        result.contains("千") && result.contains("yen"),
        "got: {result}"
    );
}

#[test]
fn test_currency_spanish() {
    let result = expand_number("$13", "spa");
    assert!(result.contains("dollars"), "got: {result}");
    assert!(
        !result.contains("13"),
        "digits should be expanded: {result}"
    );
}

#[test]
fn test_dollar_sign_alone_passthrough() {
    // "$" with no digits should pass through
    assert_eq!(expand_number("$", "eng"), "$");
}

#[test]
fn test_dollar_non_digit_passthrough() {
    // "$abc" should pass through
    assert_eq!(expand_number("$abc", "eng"), "$abc");
}

#[test]
fn test_german() {
    assert_eq!(expand_number("1", "deu"), "eins");
    assert_eq!(expand_number("10", "deu"), "zehn");
}

#[test]
fn test_french() {
    assert_eq!(expand_number("1", "fra"), "un");
    assert_eq!(expand_number("5", "fra"), "cinq");
}

// --- decomposition regression tests ---

#[test]
fn test_twelve_not_onetwo() {
    // Previously broken: substring replacement produced "onetwo"
    assert_eq!(expand_number("12", "eng"), "twelve");
}

#[test]
fn test_thirteen_spanish() {
    assert_eq!(expand_number("13", "spa"), "trece");
}

#[test]
fn test_large_number_english() {
    let result = expand_number("10000", "eng");
    // Should decompose: 10 * 1000 = "ten thousand"
    assert!(
        result.contains("thousand"),
        "10000 should contain 'thousand': {result}"
    );
    assert!(
        !result.chars().any(|c| c.is_ascii_digit()),
        "should not contain digits: {result}"
    );
}

#[test]
fn test_250_english() {
    let result = expand_number("250", "eng");
    assert!(
        result.contains("two hundred") && result.contains("fifty"),
        "250 should be 'two hundred fifty': {result}"
    );
}

#[test]
fn test_1234_english() {
    let result = expand_number("1234", "eng");
    assert!(
        !result.chars().any(|c| c.is_ascii_digit()),
        "should not contain digits: {result}"
    );
}

#[test]
fn test_dollar_12_now_works() {
    // The original production failure: "$12" in Spanish
    let result = expand_number("$12", "spa");
    assert!(
        !result.contains("12"),
        "$12 in Spanish should not contain raw digits: {result}"
    );
    assert!(
        result.contains("dollars"),
        "should contain currency word: {result}"
    );
}

#[test]
fn test_dollar_10000_english() {
    let result = expand_number("$10000", "eng");
    assert!(
        result.contains("thousand") && result.contains("dollars"),
        "got: {result}"
    );
}

// --- property tests ---

use proptest::prelude::*;

fn known_lang() -> impl Strategy<Value = &'static str> {
    prop_oneof![
        Just("eng"),
        Just("spa"),
        Just("fra"),
        Just("deu"),
        Just("zho"),
        Just("jpn"),
    ]
}

proptest! {
    /// Non-digit strings always pass through unchanged.
    #[test]
    fn non_digit_passthrough(word in "[a-zA-Z]{1,8}", lang in known_lang()) {
        let result = expand_number(&word, lang);
        prop_assert_eq!(result, word);
    }

    /// Idempotence: expand(expand(x)) == expand(x).
    /// Once expanded to words, re-expansion is a no-op (no digits).
    #[test]
    fn expand_is_idempotent(n in 0..1000u32, lang in known_lang()) {
        let s = n.to_string();
        let once = expand_number(&s, lang);
        let twice = expand_number(&once, lang);
        prop_assert_eq!(
            &once, &twice,
            "Not idempotent: '{}' -> '{}' -> '{}'", s, once, twice
        );
    }

    /// Small numbers (1-9) in known languages produce non-digit output.
    #[test]
    fn single_digit_expanded(n in 1..10u32, lang in known_lang()) {
        let s = n.to_string();
        let result = expand_number(&s, lang);
        prop_assert!(
            !result.chars().all(|c| c.is_ascii_digit()),
            "Digit {} not expanded for lang {}: '{}'", n, lang, result
        );
    }

    /// Empty string always returns empty string.
    #[test]
    fn empty_passthrough(_lang in known_lang()) {
        prop_assert_eq!(expand_number("", "eng"), "");
    }
}

// ── Ordinal and decade expansion (English-only) ──────────────────

#[test]
fn expand_number_handles_english_ordinals() {
    assert_eq!(expand_number("13th", "eng"), "thirteenth");
    assert_eq!(expand_number("1st", "eng"), "first");
    assert_eq!(expand_number("21st", "eng"), "twenty-first");
    assert_eq!(expand_number("3rd", "eng"), "third");
}

#[test]
fn expand_number_handles_english_decades() {
    assert_eq!(expand_number("1950s", "eng"), "nineteen fifties");
    assert_eq!(expand_number("80s", "eng"), "eighties");
}

#[test]
fn expand_number_leaves_non_english_ordinals_unchanged() {
    // Spanish ASR rarely emits suffix-form ordinals, but if one
    // arrives we don't have a Rust expander; passthrough is the
    // honest behaviour. Validator E220 catches it if the lang
    // doesn't permit digits.
    assert_eq!(expand_number("13th", "spa"), "13th");
    assert_eq!(expand_number("1950s", "spa"), "1950s");
}
