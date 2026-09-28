"""Language-specific Epitran IPA references with optional user overrides."""

from __future__ import annotations

import re
import shutil
from importlib.metadata import version
from typing import Any, Mapping


def epitran_code(language: str) -> str:
    """Resolve CHAT's ISO language to Epitran's language/default-script pair."""
    from langcodes import Language
    from batchalign.lang import LanguageCode

    language = LanguageCode.from_str(language).alpha_3
    script = Language.get(language).maximize().script
    # CHAT commonly uses the Chinese macrolanguage; Epitran names Mandarin.
    language = "cmn" if language == "zho" else language
    return f"{language}-{script}"


class Pronunciations:
    """Generate comparison IPA only; the acoustic phones remain authoritative.

    The task runner passes CHAT's primary language; langcodes supplies its
    default script, e.g. ``rus`` becomes ``rus-Cyrl``.
    """

    def __init__(self, overrides: Mapping[str, str] | None = None):
        if any(
            not isinstance(word, str) or not word.strip()
            or not isinstance(ipa, str) or not ipa.strip()
            for word, ipa in (overrides or {}).items()
        ):
            raise ValueError(
                "pronunciations must map nonempty words to nonempty IPA strings"
            )
        self.overrides = {
            word.casefold(): ipa for word, ipa in (overrides or {}).items()
        }
        self.version = f"{version('epitran')}:langcodes-{version('langcodes')}"
        self._engines: dict[str, Any] = {}

    def _engine(self, language: str) -> Any:
        import epitran
        from epitran.exceptions import DatafileError

        code = epitran_code(language)
        if code not in self._engines:
            if code == "eng-Latn" and shutil.which("lex_lookup") is None:
                raise ValueError(
                    "Epitran English requires Flite's lex_lookup executable on PATH; "
                    "install it or supply IPA pronunciation overrides"
                )
            try:
                self._engines[code] = epitran.Epitran(code, tones=True)
            except (OSError, ValueError, DatafileError) as error:
                raise ValueError(
                    f"Cannot initialize Epitran {code!r}: {error}; check CHAT's "
                    "@Languages and language resources or supply IPA pronunciation overrides"
                ) from error
        return self._engines[code]

    def __call__(self, text: str, language: str) -> str:
        if text.casefold() in self.overrides:
            return self.overrides[text.casefold()]
        # CHAT group delimiters and word-form markers carry no spoken phones.
        text = re.sub(r"\[[^\]]*\]", "", text).strip("‹›<>")
        words = re.sub(r"&[-+~]", "", text).replace("+", " ").split()
        phones = []
        for word in words:
            word = re.sub(r"^&[-+~]", "", word).split("@", 1)[0]
            word = word.replace("(", "").replace(")", "").casefold()
            if word in self.overrides:
                phones.append(self.overrides[word])
                continue
            engine = self._engine(language)
            ipa = engine.transliterate(word)
            # Epitran can pass unknown orthography through unchanged. Reject
            # partial conversions instead of treating those letters as IPA.
            if not ipa.strip() or ipa != engine.strict_trans(word):
                raise ValueError(
                    f"Incomplete IPA pronunciation for {word!r} in {language!r}; "
                    "supply IPA pronunciation overrides"
                )
            phones.append(ipa)
        if not phones:
            raise ValueError(f"No spoken words in phonological unit {text!r}")
        return "".join(phones)
