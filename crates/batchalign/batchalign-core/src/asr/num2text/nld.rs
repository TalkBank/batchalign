//! Dutch ordinals through 1000, using the existing cardinal table below 100.
//!
//! Hundreds join directly to the ordinal remainder; exact hundreds and duizend
//! take -ste. Never use the shared greedy cardinal decomposition here, since it
//! introduces spaces inside Dutch compounds.
//! Reference: https://taaladvies.net/aaneenschrijven-van-telwoorden-algemeen/
use super::{RenderResult, table};
use regex::Captures;

pub(super) fn render(groups: &Captures<'_>) -> RenderResult {
    let n = groups["value"]
        .parse::<usize>()
        .map_err(|_| "Dutch ordinal exceeds supported range 1..=1000")?;
    if !(1..=1000).contains(&n) {
        return Err("Dutch ordinal exceeds supported range 1..=1000");
    }
    ordinal(n)
}

fn ordinal(n: usize) -> RenderResult {
    match n {
        1 => Ok("eerste".into()),
        3 => Ok("derde".into()),
        8 => Ok("achtste".into()),
        100..=999 if n % 100 != 0 => {
            let head = table::cardinal(&(n / 100 * 100).to_string(), "nld")
                .ok_or("missing Dutch hundred")?;
            Ok(format!("{head}{}", ordinal(n % 100)?))
        }
        _ => {
            let cardinal =
                table::cardinal(&n.to_string(), "nld").ok_or("missing Dutch cardinal")?;
            let suffix = if n < 20 { "de" } else { "ste" };
            Ok(format!("{cardinal}{suffix}"))
        }
    }
}
