"""Group observed IPA phones into transcript units using reference IPA.

Use ``project_phones(phones, pronunciations)``::

    from batchalign.backends.phonetic.utils.projection import project_phones

    project_phones(["ð", "ə", "t", "æ", "t"], ["ðə", "kæt"])
    # ["ðə", "tæt"]: the observed substitution survives unchanged.

Pass the acoustic model's original phone tokens and one reference IPA string
per spoken CHAT unit, in transcript order. References can come from
``pronunciation.Pronunciations`` or the caller. Handle pauses separately;
do not pass them as spoken units. No G2P or audio model is loaded here.
"""

from __future__ import annotations

import unicodedata
from collections import Counter

from batchalign.utils.dp import (
    ExtraType,
    Match,
    PayloadTarget,
    ReferenceTarget,
    align,
)


# CHAT's single-character marker for an uncoded item on the %pho tier.
# https://talkbank.org/0info/manuals/CHAT.html (Special Form Markers)
UNRESOLVED = "…"

__all__ = ["project_phones", "comparison_symbols", "UNRESOLVED"]


def comparison_symbols(ipa: str) -> list[str]:
    """IPA segments for DP, retaining contrastive diacritics and modifiers.

    Canonical Unicode equivalents compare equally. Stress and syllable/word
    separators do not own phones; tied affricates remain a single segment.
    There are no language-specific vowel or rhotic equivalences.
    """
    symbols: list[str] = []
    tied = False
    for ch in unicodedata.normalize("NFD", ipa.replace("g", "ɡ")):
        if ch.isspace() or ch in "ˈˌ.‿":
            continue
        if symbols and (unicodedata.combining(ch) or ch in "ːˑʰʷʲⁿˡ˞ˠˤʼ" or tied):
            symbols[-1] += ch
        else:
            symbols.append(ch)
        tied = ch in "\u0361\u035c"
    return symbols


def project_phones(phones: list[str], pronunciations: list[str]) -> list[str]:
    """Assign every original phone once using BA's existing edit alignment.

    Args:
        phones: Observed IPA tokens in audio order. A token can contain
            multiple symbols or diacritics; it is never split in the output.
        pronunciations: Reference IPA, one string per spoken transcript unit.

    Returns:
        One observed IPA string per reference unit, or ``UNRESOLVED`` (``…``)
        when no phones align to it. An empty acoustic sequence produces only
        these placeholders. Removing placeholders and concatenating the result
        equals ``"".join(phones)`` exactly. Inputs are not mutated.

    Raises:
        ValueError: A reference has no comparison symbols, a token cannot be
            assigned, or assignments cross unit boundaries.

    Within an edit run, pair substitutions in order. Remaining insertions
    attach to the preceding reference unit (the following unit at the start).
    Multi-symbol phones use majority ownership, with ties going to the left.
    A unit receiving no acoustic phones is marked unresolved, never filled
    from G2P. The placeholder means uncoded, not an observed pause.
    """
    payload = [
        PayloadTarget(symbol, index)
        for index, phone in enumerate(phones)
        for symbol in comparison_symbols(phone)
    ]
    reference_symbols = [comparison_symbols(ipa) for ipa in pronunciations]
    if not reference_symbols or any(not symbols for symbols in reference_symbols):
        raise ValueError("Cannot project empty pronunciation sequences")
    reference = [
        ReferenceTarget(symbol, index)
        for index, symbols in enumerate(reference_symbols)
        for symbol in symbols
    ]
    edits = align(payload, reference, tqdm=False)
    votes: list[list[int]] = [[] for _ in phones]
    previous = reference[0].payload
    offset = 0
    while offset < len(edits):
        edit = edits[offset]
        if isinstance(edit, Match):
            votes[edit.payload].append(edit.reference_payload)
            previous = edit.reference_payload
            offset += 1
            continue
        inserted, deleted = [], []
        while offset < len(edits) and not isinstance(edits[offset], Match):
            extra = edits[offset]
            (inserted if extra.extra_type == ExtraType.PAYLOAD else deleted).append(
                extra.payload
            )
            offset += 1
        for index, phone in enumerate(inserted):
            owner = deleted[min(index, len(deleted) - 1)] if deleted else previous
            votes[phone].append(owner)
        if deleted:
            previous = deleted[-1]
    result = [""] * len(pronunciations)
    previous = 0
    for phone, owners in zip(phones, votes):
        if not owners:
            raise ValueError(f"Phone {phone!r} has no comparison symbols")
        counts = Counter(owners)
        owner = min(counts, key=lambda unit: (-counts[unit], unit))
        if owner < previous:
            raise ValueError("Phone projection crossed a word boundary")
        result[owner] += phone
        previous = owner
    return [unit or UNRESOLVED for unit in result]
