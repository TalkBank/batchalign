use super::*;

#[test]
fn existing_language_outputs_match_pre_refactor_baseline() {
    // Captured from the converter at 680149583b8075503e08a7ef3a1af62971785517. This
    // covers every table language plus CJK and digit-permitting/unknown fallbacks.
    let cases: Vec<[String; 3]> =
        serde_json::from_str(include_str!("../data/number_expansion_baseline.json")).unwrap();
    assert_eq!(cases.len(), 53 * 37);
    for [lang, input, expected] in cases {
        assert_eq!(expand_number(&input, &lang), expected, "{lang}: {input}");
    }
}

#[test]
fn every_cardinal_table_entry_is_reachable_through_recognition() {
    assert_eq!(table::NUM2LANG.len(), 46);
    for (lang, entries) in table::NUM2LANG.iter() {
        for (input, expected) in entries {
            // Japanese has always preferred num2chinese over its lookup table.
            if lang == "jpn" {
                continue;
            }
            assert_eq!(expand_number(input, lang), *expected, "{lang}: {input}");
        }
    }
}

#[test]
fn portuguese_ordinals_preserve_gender_and_number() {
    for (input, expected) in [
        ("54ª", "quinquagésima quarta"),
        ("54.ª", "quinquagésima quarta"),
        ("54º", "quinquagésimo quarto"),
        ("54.º", "quinquagésimo quarto"),
        ("1ª", "primeira"),
        ("1º", "primeiro"),
        ("21ª", "vigésima primeira"),
        ("21º", "vigésimo primeiro"),
        ("54.ªs", "quinquagésimas quartas"),
        ("54ºs", "quinquagésimos quartos"),
        ("100ª", "centésima"),
        ("111º", "centésimo décimo primeiro"),
        ("500º", "quingentésimo"),
        ("655º", "sexcentésimo quinquagésimo quinto"),
        ("700ª", "septingentésima"),
        ("1000ª", "milésima"),
    ] {
        assert_eq!(expand_number(input, "por"), expected, "{input}");
        assert_eq!(
            expand_number(input, "POR"),
            expected,
            "case-insensitive language"
        );
        assert_eq!(expand_number(expected, "por"), expected, "idempotence");
    }
}

#[test]
fn all_supported_portuguese_ordinals_are_legal_chat_words() {
    use crate::asr::ChatWordText;
    use talkbank_model::model::LanguageCode;
    let lang = LanguageCode::new("por").unwrap();
    for n in 1..=1000 {
        for suffix in ["º", "ª", ".ºs", ".ªs"] {
            let input = format!("{n}{suffix}");
            let Expansion::Expanded { text, source_span } = expand(&input, "por") else {
                panic!("{input}");
            };
            assert_eq!(source_span, 0..input.len());
            for word in text.split_whitespace() {
                assert!(
                    ChatWordText::try_from_lang(word, &lang).is_ok(),
                    "{input}: {word}"
                );
            }
        }
    }
}

#[test]
fn recognition_does_not_guess_from_lookalikes_or_substrings() {
    for input in [
        "54°",
        "54a",
        "54o",
        "abc54ª",
        "54ªabc",
        "54.ªabc",
        "n.º",
        "3.14",
        "-54ª",
        "54.ª-feira",
    ] {
        assert_eq!(expand(input, "por"), Expansion::NoMatch, "{input}");
        assert_eq!(protected_prefix_len(input, "por"), None, "{input}");
    }
    assert_eq!(expand("54ª", "eng"), Expansion::NoMatch);
    assert_eq!(expand("54ª", "spa"), Expansion::NoMatch);
    assert_eq!(expand("54ª", "xxx"), Expansion::NoMatch);
}

#[test]
fn unsupported_numeric_expressions_keep_their_source_and_diagnostic() {
    for input in ["0ª", "1001ª", "999999999999999999999999999999999999.ª"] {
        assert!(
            matches!(expand(input, "por"), Expansion::Unsupported { source_span, .. } if source_span == (0..input.len()))
        );
        assert_eq!(expand_number(input, "por"), input);
        assert_eq!(protected_prefix_len(input, "por"), Some(input.len()));
    }
    let input = "5—6";
    assert!(
        matches!(expand(input, "eng"), Expansion::Expanded { source_span, .. } if source_span == (0..input.len()))
    );
}

#[test]
fn abbreviation_period_is_protected_but_sentence_period_is_not() {
    assert_eq!(
        protected_prefix_len("54.ª. então", "por"),
        Some("54.ª".len())
    );
    assert_eq!(protected_prefix_len("54.ª?", "por"), Some("54.ª".len()));
    assert_eq!(protected_prefix_len("54.ª", "eng"), None);
    assert_eq!(protected_prefix_len("54.ªs!", "por"), Some("54.ªs".len()));
}

#[test]
fn malformed_rules_fail_at_compilation() {
    for json in [
        r#"{"rules": {}, "common": ["absent"], "languages": {}}"#,
        r#"{"rules": {"bad": {"kind": "cardinal", "pattern": "["}}, "common": [], "languages": {}}"#,
        r#"{"rules": {"bad": {"kind": "cardinal", "pattern": "[0-9]+"}}, "common": [], "languages": {}}"#,
        r#"{"rules": {"bad": {"kind": "cardinal", "pattern": "(?P<value>[0-9]*)"}}, "common": [], "languages": {}}"#,
    ] {
        assert!(Rules::compile(json).is_err());
    }
}
