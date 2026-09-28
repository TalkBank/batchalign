"""Packaged English pronunciation lookup with optional IPA overrides."""

from __future__ import annotations

import re
from importlib.metadata import version
from typing import Mapping

# Comparison pronunciations only: acoustic IPA is never rewritten with these.
ARPABET_IPA = dict(
    zip(
        "AA AE AH AO AW AY B CH D DH EH ER EY F G HH IH IY JH K L M N NG OW OY P R S SH T TH UH UW V W Y Z ZH".split(),
        "ɑ æ ə ɔ aʊ aɪ b tʃ d ð ɛ ɚ eɪ f ɡ h ɪ i dʒ k l m n ŋ oʊ ɔɪ p ɹ s ʃ t θ ʊ u v w j z ʒ".split(),
    )
)


class Pronunciations:
    """Resolve each CHAT phonological unit without an external G2P executable."""

    def __init__(self, overrides: Mapping[str, str] | None = None):
        self.overrides = {
            word.casefold(): ipa for word, ipa in (overrides or {}).items()
        }
        if any(
            not word or not isinstance(ipa, str) or not ipa.strip()
            for word, ipa in self.overrides.items()
        ):
            raise ValueError(
                "pronunciations must map nonempty words to nonempty IPA strings"
            )
        self._dictionary = None
        self.version = version("cmudict")

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
            if language not in {"eng", "en"}:
                raise ValueError(
                    f"No pronunciation for {word!r} in {language!r}; supply IPA pronunciation overrides"
                )
            if self._dictionary is None:
                import cmudict

                self._dictionary = cmudict.dict()
            alternatives = self._dictionary.get(word)
            if not alternatives:
                raise ValueError(
                    f"No pronunciation for {word!r}; supply an IPA pronunciation override"
                )
            # Stable first pronunciation; the acoustic phones remain authoritative.
            phones.append(
                "".join(ARPABET_IPA[phone.rstrip("012")] for phone in alternatives[0])
            )
        if not phones:
            raise ValueError(f"No spoken words in phonological unit {text!r}")
        return "".join(phones)
