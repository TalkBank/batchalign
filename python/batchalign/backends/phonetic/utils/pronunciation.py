"""Generate reference IPA for CHAT units using Piper Plus, Epitran, and CSV overrides.

Create one ``Pronunciations`` instance per backend and call it with each
spoken unit's text and the primary ISO 639-3 language supplied by CHAT::

    from batchalign.backends.phonetic.utils.pronunciation import (
        Pronunciations, load_pronunciations,
    )

    pronounce = Pronunciations(load_pronunciations("pronunciations.csv"))
    pronounce("gato", "spa")  # reference IPA from Piper Plus
    pronounce("wug", "eng")   # "wʌɡ" if present in the CSV

Each call returns one reference IPA string for the unit, including grouped
words. Feed these strings to ``projection.project_phones`` to recover unit
boundaries without replacing acoustic IPA with expected pronunciations.
Piper Plus handles its supported languages; Epitran handles the rest.
Engines load lazily and are reused. Python 3.11+ is required. Language
resources may download on first use; English needs no system G2P executable.
"""

from __future__ import annotations

import csv
import re
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any, Mapping

__all__ = ["Pronunciations", "epitran_code", "load_pronunciations"]

# Piper uses ISO 639-1; CHAT supplies ISO 639-3. Mandarin's individual
# language code has no alpha-2 equivalent in pycountry.
_PIPER_LANGUAGES = {
    "eng": "en", "jpn": "ja", "cmn": "zh", "zho": "zh", "kor": "ko",
    "spa": "es", "fra": "fr", "por": "pt", "swe": "sv",
}


def load_pronunciations(path: str | Path) -> dict[str, str]:
    """Read a UTF-8 CSV containing exactly the columns ``word`` and ``ipa``.

    Example file (the header is required)::

        word,ipa
        wug,wʌɡ
        bonjour,bɔ̃ʒuʁ
        the cat,ðəkæt

    Words may be whole CHAT phonological units. Standard CSV quoting handles
    commas. Blank lines are ignored and a UTF-8 BOM is accepted. Returns a
    case-insensitive word-to-IPA mapping for ``Pronunciations(overrides)``.
    Raises ``ValueError`` for malformed rows, empty cells, or duplicate words;
    file access errors propagate as ``OSError``.
    """
    result: dict[str, str] = {}
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as source:
            rows = csv.reader(source, strict=True)
            if next(rows, None) != ["word", "ipa"]:
                raise ValueError("pronunciation CSV must start with the header word,ipa")
            for row in rows:
                if not row:
                    continue
                if len(row) != 2 or not all(cell.strip() for cell in row):
                    raise ValueError(f"CSV line {rows.line_num}: expected nonempty word,ipa")
                word, ipa = (cell.strip() for cell in row)
                word = word.casefold()
                if word in result:
                    raise ValueError(f"CSV line {rows.line_num}: duplicate word {word!r}")
                result[word] = ipa
    except csv.Error as error:
        raise ValueError(f"Invalid pronunciation CSV: {error}") from error
    return result


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
    default script for the Epitran fallback, e.g. ``rus`` becomes ``rus-Cyrl``.
    """

    def __init__(self, overrides: Mapping[str, str] | None = None):
        if sys.version_info < (3, 11):
            raise ValueError("Phonetic pronunciation generation requires Python 3.11 or newer")
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
        self.version = (
            f"piper-{version('piper-plus-g2p')}:epitran-{version('epitran')}"
            f":langcodes-{version('langcodes')}"
        )
        self._piper_engines: dict[str, Any] = {}
        self._epitran_engines: dict[str, Any] = {}

    def _epitran_engine(self, language: str) -> Any:
        import epitran
        from epitran.exceptions import DatafileError

        code = epitran_code(language)
        if code not in self._epitran_engines:
            try:
                self._epitran_engines[code] = epitran.Epitran(code, tones=True)
            except (OSError, ValueError, DatafileError) as error:
                raise ValueError(
                    f"Cannot initialize Epitran {code!r}: {error}; check CHAT's "
                    "@Languages and language resources or supply IPA pronunciation overrides"
                ) from error
        return self._epitran_engines[code]

    def _pronounce(self, word: str, language: str) -> str:
        from batchalign.lang import LanguageCode

        language = LanguageCode.from_str(language).alpha_3
        if code := _PIPER_LANGUAGES.get(language):
            from piper_plus_g2p import get_phonemizer
            from .piper import piper_ipa, prepare_piper

            if code not in self._piper_engines:
                prepare_piper(code)
                self._piper_engines[code] = get_phonemizer(code)
            # A broken supported backend must surface its error, not silently
            # change providers (particularly back to Flite for English).
            ipa = piper_ipa(self._piper_engines[code].phonemize(word), code)
        else:
            engine = self._epitran_engine(language)
            ipa = engine.transliterate(word)
            if ipa != engine.strict_trans(word):
                raise ValueError(
                    f"Incomplete IPA pronunciation for {word!r} in {language!r}; "
                    "supply IPA pronunciation overrides"
                )
        if not ipa.strip():
            raise ValueError(f"Empty IPA pronunciation for {word!r} in {language!r}")
        return ipa

    def __call__(self, text: str, language: str) -> str:
        """Return reference IPA for a spoken CHAT unit and ISO 639-3 language.

        Whole-unit and individual-word overrides take precedence over G2P.
        CHAT group/word markers are removed before lookup. Raises ``ValueError``
        for invalid language codes, unavailable language resources, incomplete
        transliteration, or units without spoken words. Supply overrides for
        words the selected provider cannot handle.
        """
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
            phones.append(self._pronounce(word, language))
        if not phones:
            raise ValueError(f"No spoken words in phonological unit {text!r}")
        return "".join(phones)
