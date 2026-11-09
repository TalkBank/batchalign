"""Acoustic Voice Quality Index measurements using optional Praat bindings."""

from __future__ import annotations

import math
import re
import threading
from typing import Any

from batchalign.backends.base import AVQI, BatchPolicy

# praat.call uses a process-wide object list. Serialize the complete analysis
# across instances, while the pipeline can decode independent pairs concurrently.
_PRAAT_LOCK = threading.Lock()


def avqi_score(*, cpps: float, hnr: float, shimmer_local: float,
               shimmer_local_db: float, slope: float, tilt: float) -> float:
    """AVQI 03.01 coefficients; local shimmer is expressed as percent."""
    features = (cpps, hnr, shimmer_local, shimmer_local_db, slope, tilt)
    if not all(math.isfinite(value) for value in features):
        raise ValueError("AVQI requires six finite acoustic measurements")
    return (4.152 - 0.177 * cpps - 0.006 * hnr - 0.037 * shimmer_local
            + 0.941 * shimmer_local_db + 0.01 * slope + 0.093 * tilt) * 2.8902


class AvqiBackend(AVQI):
    """Praat measurements using the supplied energy-window extraction procedure.

    Uses AVQI 03.01 coefficients. This implementation's speech extraction is
    versioned separately; it is not a claim of numerical equivalence with the
    original clinical AVQI script.
    """

    def __init__(self) -> None:
        try:
            import parselmouth
        except ImportError as exc:
            raise ImportError("AVQI requires pip install 'batchalign[avqi]'") from exc
        self._version = f"parselmouth-{parselmouth.VERSION}:praat-{parselmouth.PRAAT_VERSION}"

    @property
    def name(self) -> str:
        return f"avqi:3.01:energy-windows-v1:{self._version}"

    @property
    def batch_policy(self) -> BatchPolicy:
        return BatchPolicy.one()

    def call(self, batch: list[Any], *, progress: Any = None, **kwargs: Any) -> list[Any]:
        from batchalign._core.proto import AvqiInput, AvqiOutput

        outputs = []
        with _PRAAT_LOCK:
            for item in batch:
                if not isinstance(item, AvqiInput):
                    raise TypeError(f"AvqiBackend does not handle {type(item).__name__}")
                features = self._measure(item.continuous_speech, item.sustained_vowel)
                outputs.append(AvqiOutput(
                    source_id=item.source_id, implementation=self.name, **features,
                ))
        return outputs

    @staticmethod
    def _sound(audio: Any, label: str) -> Any:
        import numpy as np
        import parselmouth

        # LTAS uses frequencies through 10 kHz; upsampling cannot restore them.
        if audio.sample_rate < 20000:
            raise ValueError(f"{label} requires a sample rate of at least 20000 Hz for 10 kHz LTAS")
        wave = np.frombuffer(audio.pcm_f32le, dtype="<f4")
        if audio.channels != 1 or len(wave) != audio.frame_count:
            raise ValueError(f"{label} requires decoded mono PCM with a matching frame count")
        if not len(wave) or not np.isfinite(wave).all() or not np.any(wave):
            raise ValueError(f"{label} is empty, silent, or contains non-finite samples")
        return parselmouth.Sound(wave.astype(np.float64), sampling_frequency=audio.sample_rate)

    @staticmethod
    def extract_voiced_segments(sound: Any) -> Any:
        """Remove silences, then retain 30 ms windows above 30% of global power."""
        from parselmouth.praat import call

        grid = call(sound, "To TextGrid (silences)", 50, 0.003, -25, 0.1, 0.1, "silence", "sounding")
        intervals = call([sound, grid], "Extract intervals where", 1, False, "does not contain", "silence")
        if not intervals:
            raise ValueError("Continuous speech has no sounding intervals")
        loud = call(intervals, "Concatenate")
        threshold = float(call(loud, "Get power in air")) * 0.3
        if not math.isfinite(threshold) or threshold <= 0:
            raise ValueError("Continuous speech has no measurable power")
        start = float(call(loud, "Get start time"))
        end = float(call(loud, "Get end time"))
        parts = []
        for index in range(int((end - start) / 0.03)):
            left = start + index * 0.03
            part = call(loud, "Extract part", left, left + 0.03, "Rectangular", 1.0, False)
            if float(call(part, "Get power in air")) > threshold:
                crossing = float(call(part, "Get nearest zero crossing", 1, 0.0025))
                if math.isfinite(crossing):
                    parts.append(part)
        if not parts:
            raise ValueError("Continuous speech has no usable voiced windows")
        return call(parts, "Concatenate")

    def _measure(self, cs_audio: Any, sv_audio: Any) -> dict[str, float]:
        from parselmouth.praat import call

        cs = self._sound(cs_audio, "Continuous speech")
        sv = self._sound(sv_audio, "Sustained vowel")
        if sv.duration < 3.0:
            raise ValueError("Sustained vowel must contain at least 3 seconds")
        # Preserve bandwidth and use one sample rate before concatenation.
        rate = max(cs.sampling_frequency, sv.sampling_frequency)
        if cs.sampling_frequency != rate:
            cs = call(cs, "Resample", rate, 50)
        if sv.sampling_frequency != rate:
            sv = call(sv, "Resample", rate, 50)
        cs = call(cs, "Filter (stop Hann band)", 0, 34, 0.1)
        sv = call(sv, "Filter (stop Hann band)", 0, 34, 0.1)
        voiced = self.extract_voiced_segments(cs)
        vowel = call(sv, "Extract part", sv.xmax - 3.0, sv.xmax, "Rectangular", 1.0, False)
        sound = call([voiced, vowel], "Concatenate")
        cepstrum = call(sound, "To PowerCepstrogram", 60, 0.002, 5000, 50)
        cpps = float(call(cepstrum, "Get CPPS", False, 0.01, 0.001, 60, 330, 0.05,
                          "Parabolic", 0.001, 0, "Straight", "Robust"))
        ltas = call(sound, "To Ltas", 1)
        slope = float(call(ltas, "Get slope", 0, 1000, 1000, 10000, "energy"))
        # Compute trend line returns a NEW Ltas object; querying the original
        # again would repeat slope. Never invent a slope+constant fallback.
        trend = call(ltas, "Compute trend line", 1, 10000)
        tilt = float(call(trend, "Get slope", 0, 1000, 1000, 10000, "energy"))
        pulses = call(sound, "To PointProcess (periodic, cc)", 50, 400)
        shimmer = 100 * float(call([sound, pulses], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6))
        shimmer_db = float(call([sound, pulses], "Get shimmer (local_dB)", 0, 0, 0.0001, 0.02, 1.3, 1.6))
        pitch = call(sound, "To Pitch (cc)", 0, 75, 15, False, 0.03, 0.45, 0.01, 0.35, 0.14, 600)
        report_pulses = call([sound, pitch], "To PointProcess (cc)")
        report = call([sound, pitch, report_pulses], "Voice report", 0, 0, 75, 600, 1.3, 1.6, 0.03, 0.45)
        match = re.search(r"Mean harmonics-to-noise ratio:\s*([-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)", report)
        if match is None:
            raise ValueError("Praat voice report has no finite harmonics-to-noise ratio")
        features = dict(cpps=cpps, hnr=float(match[1]), shimmer_local=shimmer,
                        shimmer_local_db=shimmer_db, slope=slope, tilt=tilt)
        score = avqi_score(**features)
        return dict(avqi=score, **features, voiced_cs_duration=voiced.duration, sv_duration=vowel.duration)


__all__ = ["AvqiBackend", "avqi_score"]
