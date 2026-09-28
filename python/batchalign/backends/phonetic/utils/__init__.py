"""Phonetic reference generation and acoustic-phone projection.

Use ``pronunciation.Pronunciations`` to obtain reference IPA for CHAT units,
then ``projection.project_phones`` to group observed phones by those units.
The references determine boundaries; output IPA always comes from the audio.
"""
