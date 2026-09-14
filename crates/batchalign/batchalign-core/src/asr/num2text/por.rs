//! Portuguese ordinal rendering, including grammatical gender and plural.
//!
//! Forms through 1000 use units, tens, hundreds and milésimo. Larger ordinals
//! are explicitly unsupported instead of guessing a thousands convention.
//! References: https://ciberduvidas.iscte-iul.pt/consultorio/perguntas/ordinais-diversos/13396
//! https://ciberduvidas.iscte-iul.pt/consultorio/perguntas/a-forma-por-extenso-de-2000-e-de-outros-ordinais/16428
use super::{RenderResult, RuleKind};
use regex::Captures;

const UNITS: [&str; 10] = [
    "", "primeiro", "segundo", "terceiro", "quarto", "quinto", "sexto", "sétimo", "oitavo", "nono",
];
const TENS: [&str; 10] = [
    "",
    "décimo",
    "vigésimo",
    "trigésimo",
    "quadragésimo",
    "quinquagésimo",
    "sexagésimo",
    "septuagésimo",
    "octogésimo",
    "nonagésimo",
];
const HUNDREDS: [&str; 10] = [
    "",
    "centésimo",
    "ducentésimo",
    "tricentésimo",
    "quadringentésimo",
    "quingentésimo",
    "sexcentésimo",
    "septingentésimo",
    "octingentésimo",
    "noningentésimo",
];

pub(super) fn render(kind: RuleKind, groups: &Captures<'_>) -> RenderResult {
    if kind != RuleKind::Ordinal {
        return Err("unsupported Portuguese number expression");
    }
    let n = groups["value"]
        .parse::<usize>()
        .map_err(|_| "Portuguese ordinal exceeds supported range 1..=1000")?;
    if !(1..=1000).contains(&n) {
        return Err("Portuguese ordinal exceeds supported range 1..=1000");
    }
    let parts = if n == 1000 {
        vec!["milésimo"]
    } else {
        vec![HUNDREDS[n / 100], TENS[(n / 10) % 10], UNITS[n % 10]]
    };
    let feminine = &groups["gender"] == "ª";
    let plural = groups
        .name("plural")
        .is_some_and(|m| !m.as_str().is_empty());
    Ok(parts
        .into_iter()
        .filter(|p| !p.is_empty())
        .map(|part| {
            let mut word = part.to_owned();
            if feminine {
                word.pop();
                word.push('a');
            }
            if plural {
                word.push('s');
            }
            word
        })
        .collect::<Vec<_>>()
        .join(" "))
}
