# Add or change language support

1. Identify the command and backend you are extending. Language-code recognition,
   model availability, and useful analysis quality are separate checks.
2. Check `python/batchalign/lang.py` and the backend's vendor-code conversion.
   For Stanza, inspect `backends/morphosyntax/ud/lang.py` and `stanza.py`.
3. Test representative text or audio with the selected model. Include the
   language's contractions, script, punctuation, and conversational forms.
4. For ASR, check number expansion and cleanup in the Rust core `asr/` modules.
   For morphology, check token reconciliation and typed tier alignment as well
   as the model's raw output.
5. Add regression fixtures at the responsible layer and run the appropriate
   [tests](testing.md), followed by a small CLI integration run.
6. Update [language selection](../reference/language-handling.md) and the
   language-specific reference. Record measured quality with model versions and
   corpus scope instead of inferring support from a language list.
