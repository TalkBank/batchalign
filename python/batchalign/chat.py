"""Typed CHAT documents backed by Rust.

Construct :class:`Speaker` and :class:`Utterance` values, then edit
``CHATFile.utterances``. Document participant headers are derived automatically.
See the book's Python CHAT API reference for ownership and validation details.
"""

from batchalign._core import CHATFile, Media, Speaker, Utterance

__all__ = ["CHATFile", "Media", "Speaker", "Utterance"]
