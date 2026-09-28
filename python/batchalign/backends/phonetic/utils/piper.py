"""Convert Piper Plus 0.2.0's language-specific tokens to reference IPA.

``piper_ipa(tokens, language)`` takes ``phonemizer.phonemize(text)`` output and
its Piper language code, e.g. ``piper_ipa(["n", "i", "tone3"], "zh")`` returns
``"ni˨˩˦"``. Most tokens are already IPA. Mandarin tone labels and Japanese
OpenJTalk labels need conversion; Japanese prosody/boundary markers are omitted.
These are reference pronunciations only, never replacements for acoustic IPA.
"""

__all__ = ["piper_ipa", "prepare_piper"]

_JAPANESE = {
    "N": "ɴ", "N_m": "m", "N_n": "n", "N_ng": "ŋ", "N_uvular": "ɴ",
    "ch": "tɕ", "sh": "ɕ", "ts": "ts", "j": "dʑ", "y": "j",
    "r": "ɾ", "f": "ɸ", "u": "ɯ", "I": "i̥", "U": "ɯ̥", "g": "ɡ",
    "ky": "kʲ", "gy": "ɡʲ", "kw": "kʷ", "gw": "ɡʷ", "ty": "tʲ",
    "dy": "dʲ", "py": "pʲ", "by": "bʲ", "zy": "ʑ", "hy": "ç",
    "ny": "nʲ", "my": "mʲ", "ry": "ɾʲ",
}
_JAPANESE_MARKERS = {"_", "#", "[", "]", "^", "$", "?", "?!", "?.", "?~"}
_TONES = {"tone1": "˥", "tone2": "˧˥", "tone3": "˨˩˦", "tone4": "˥˩", "tone5": ""}


def prepare_piper(language: str) -> None:
    """Download missing NLTK resources before English/Korean G2P first use.

    Honor NLTK's configured data directory (including ``NLTK_DATA``). g2p-en
    checks the legacy tagger at import, while current NLTK uses the English
    JSON tagger at runtime; both must be available. Other languages need no
    NLTK setup. Download failures propagate instead of selecting Epitran.
    """
    if language not in {"en", "ko"}:
        return
    if language == "ko":
        from importlib.util import find_spec
        import sys

        # g2pk2 otherwise tries to run pip itself at inference time.
        module = "eunjeon" if sys.platform == "win32" else "mecab"
        if find_spec(module) is None:
            raise ImportError("Korean G2P requires the complete batchalign[phonetic] extra")
    import nltk

    resources = [("cmudict", "corpora/cmudict.zip")]
    if language == "en":
        resources += [
            ("averaged_perceptron_tagger", "taggers/averaged_perceptron_tagger.zip"),
            ("averaged_perceptron_tagger_eng", "taggers/averaged_perceptron_tagger_eng/"),
        ]
    for package, resource in resources:
        try:
            nltk.data.find(resource)
        except LookupError:
            nltk.download(
                package, download_dir=nltk.data.path[0], quiet=True, raise_on_error=True
            )


def piper_ipa(tokens: list[str], language: str) -> str:
    """Return IPA, resolving Piper labels before shared DP comparison.

    Japanese ``cl`` (geminate closure) repeats the following consonant.
    Mandarin neutral tone has no fixed pitch contour and is left unmarked.
    Raises ``ValueError`` for an unresolved closure or unknown label.
    """
    if language == "ja":
        phones = [_JAPANESE.get(t, t) for t in tokens if t not in _JAPANESE_MARKERS]
        for index, phone in enumerate(phones):
            if phone == "cl":
                if index + 1 == len(phones) or phones[index + 1] == "cl":
                    raise ValueError("Piper Japanese returned an unresolved geminate closure")
                phones[index] = phones[index + 1][0]
    elif language == "zh":
        phones = [_TONES.get(t, t) for t in tokens]
    else:
        phones = [{"rr": "r", "y_vowel": "y"}.get(t, t) for t in tokens]
    if any("_" in phone or phone.startswith("tone") for phone in phones):
        raise ValueError("Piper returned an unknown phoneme label")
    return "".join(phones)
