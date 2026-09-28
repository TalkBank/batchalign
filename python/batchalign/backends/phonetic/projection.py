"""DP projection of reference word ownership onto original acoustic phones."""

from __future__ import annotations

import unicodedata
from collections import Counter

from batchalign.backends.morphosyntax.ud.dp import (
    ExtraType,
    Match,
    PayloadTarget,
    ReferenceTarget,
    align,
)


def comparison_symbols(ipa: str) -> list[str]:
    """Broad IPA comparison alphabet; preserve original tokens outside this view."""
    ipa = ipa.translate(
        str.maketrans({"g": "ɡ", "r": "ɹ", "ɚ": "əɹ", "ɝ": "əɹ", "ʌ": "ə", "ɐ": "ə"})
    )
    return [
        ch
        for ch in unicodedata.normalize("NFD", ipa)
        if not unicodedata.combining(ch)
        and not ch.isspace()
        and ch not in "ˈˌːˑʰʷʲⁿˡ.‿"
    ]


def project_phones(phones: list[str], pronunciations: list[str]) -> list[str]:
    """Assign every original phone once using BA's existing edit alignment.

    Within an edit run, pair substitutions in order. Remaining insertions
    attach to the preceding reference unit (the following unit at the start).
    Multi-symbol phones use majority ownership, with ties going to the left.
    A unit receiving no acoustic phones is unresolved, never filled from G2P.
    """
    payload = [
        PayloadTarget(symbol, index)
        for index, phone in enumerate(phones)
        for symbol in comparison_symbols(phone)
    ]
    reference = [
        ReferenceTarget(symbol, index)
        for index, pronunciation in enumerate(pronunciations)
        for symbol in comparison_symbols(pronunciation)
    ]
    if not payload or not reference:
        raise ValueError("Cannot project empty phone or pronunciation sequences")
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
    if any(not unit for unit in result):
        raise ValueError(
            "Phone alignment left an unresolved word; check transcript/pronunciations"
        )
    return result
