//! Preserve the existing CJK script selection and converter.
use super::super::num2chinese::{ChineseScript, num2chinese};
use super::Renderer;

pub(super) fn cardinal(value: &str, renderer: Renderer) -> Option<String> {
    let n = value.parse::<u64>().ok()?;
    let script = match renderer {
        Renderer::Simplified => ChineseScript::Simplified,
        Renderer::Traditional => ChineseScript::Traditional,
        _ => return None,
    };
    Some(num2chinese(n, script))
}
