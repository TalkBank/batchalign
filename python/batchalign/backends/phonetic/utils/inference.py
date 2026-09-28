"""Windowing and length-aware inference for the pinned PhoneticXeus model.

``group_utterances(utterances)`` returns lists of original utterance positions,
using Whisper FA's approximately 20-second span limit. A long utterance stays
whole; a gap over two seconds or backwards timing starts a new group.

``transcribe_batch(model, waveforms)`` accepts unpadded, mono 16 kHz tensors and
returns one list of original phone tokens per waveform, in input order. It
normalizes each waveform independently, pads the batch, passes real lengths to
the encoder, and discards padded frames before greedy CTC decoding. The model
must be in eval mode. Calls must be serialized: the pinned frontend's global
normalization is temporarily disabled in favor of per-waveform normalization.
The encoder masks attention, but its convolution branches do not mask padding;
batching can therefore change some phone decisions near a window's edge.
"""

from __future__ import annotations

from typing import Any


def group_utterances(utterances: list[Any]) -> list[list[int]]:
    groups: list[list[int]] = []
    for index, utterance in enumerate(utterances):
        if groups:
            current = groups[-1]
            first = utterances[current[0]]
            previous = utterances[current[-1]]
            if (
                utterance.end_ms - first.start_ms <= 20_000
                and utterance.start_ms - previous.end_ms <= 2_000
                and utterance.start_ms >= previous.start_ms
                and utterance.end_ms >= previous.end_ms
            ):
                current.append(index)
                continue
        groups.append([index])
    return groups


def transcribe_batch(model: Any, waveforms: list[Any]) -> list[list[str]]:
    import torch
    from torch.nn import functional as F
    from torch.nn.utils.rnn import pad_sequence

    if not waveforms:
        return []
    core = model.model
    frontend = core.frontend
    normalize = frontend.normalize_audio
    with torch.inference_mode():
        waves = [wave.to(device=model.device, dtype=model.dtype) for wave in waveforms]
        # Upstream F.layer_norm(x, x.shape) mixes rows and includes padding.
        # Match single-utterance normalization before introducing either.
        if normalize:
            waves = [F.layer_norm(wave, wave.shape) for wave in waves]
        lengths = torch.tensor([len(wave) for wave in waves], device=model.device)
        speech = pad_sequence(waves, batch_first=True)
        frontend.normalize_audio = False
        try:
            encoded, frame_lengths = core.encode(speech, lengths)
        finally:
            frontend.normalize_audio = normalize
        if isinstance(encoded, tuple):
            encoded = encoded[0]
        ids = core.ctc.ctc_lo(encoded).argmax(dim=-1)
        outputs = []
        for row, length in zip(ids, frame_lengths):
            collapsed = row[:int(length)].unique_consecutive().tolist()
            tokens = [core.token_list[index] for index in collapsed if index != core.blank_id]
            outputs.append([
                token for token in tokens
                if token and not (token.startswith("<") and token.endswith(">"))
            ])
        return outputs
