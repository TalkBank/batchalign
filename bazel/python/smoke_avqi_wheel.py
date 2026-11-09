"""Install a wheel's AVQI extra into a blank venv and exercise packaged audio processing.

Usage: python3 bazel/python/smoke_avqi_wheel.py path/to/batchalign.whl
Requires network access to install the wheel's declared dependencies.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import venv
import wave


def write_audio(path: Path, frequency: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    rate = 22050
    samples = []
    for i in range(rate * 4):
        t = i / rate
        phase = 2 * math.pi * frequency * t + 0.03 * math.sin(2 * math.pi * 5 * t)
        signal = sum(math.sin(h * phase) / h for h in range(1, 15))
        signal = signal * 0.18 * (1 + 0.05 * math.sin(2 * math.pi * 7 * t))
        samples.append(int(32767 * (signal + rng.gauss(0, 0.002))))
    with wave.open(str(path), "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(rate)
        sound.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    env = {k: v for k, v in os.environ.items() if k not in {
        "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PIP_TARGET", "PIP_PREFIX", "PIP_USER",
    }}
    with tempfile.TemporaryDirectory(prefix="batchalign-avqi-install-") as temporary:
        root = Path(temporary)
        venv.EnvBuilder(with_pip=True).create(root / "venv")
        scripts = root / "venv" / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        cli = scripts / ("batchalign.exe" if os.name == "nt" else "batchalign")

        def run(*command: object) -> None:
            subprocess.run([str(part) for part in command], cwd=root, env=env, check=True)

        run(python, "-I", "-c", "import importlib.util; assert importlib.util.find_spec('batchalign') is None")
        run(python, "-I", "-m", "pip", "--isolated", "install", f"{wheel}[avqi]")
        run(python, "-I", "-m", "pip", "--isolated", "check")
        run(python, "-I", "-c", """
import pathlib, sys, batchalign, parselmouth
from batchalign._core.proto import AvqiInput, AvqiOutput
assert pathlib.Path(batchalign.__file__).resolve().is_relative_to(pathlib.Path(sys.prefix).resolve())
assert batchalign.AvqiMediaInput and batchalign.AvqiBackend()
print('Installed package:', batchalign.__file__)
print('Praat bindings:', parselmouth.__version__)
""")
        run(cli, "avqi", "--help")
        for person in ("speaker A", "speaker B"):
            write_audio(root / "sv" / person / "visit" / "sample.sv.wav", 130)
            write_audio(root / "cs" / person / "visit" / "sample.cs.wav", 155)
        run(cli, "--plain", "--parallel", "2", "avqi", root / "sv", root / "cs", "-o", root / "results")
        with (root / "results" / "avqi.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        assert [r["source_id"] for r in rows] == ["speaker A/visit/sample", "speaker B/visit/sample"]
        for row in rows:
            assert row["success"] == "True", row
            for key in ("avqi", "cpps", "hnr", "shimmer_local", "shimmer_local_db", "slope", "tilt"):
                assert math.isfinite(float(row[key])), row
        print(f"PASS: blank install, dependency check, native imports, and {len(rows)} mirrored AVQI pairs on Python {sys.version.split()[0]}")


if __name__ == "__main__":
    main()
