"""Prepare PyApp's Intel Mac Python with a current, statically linked Cryptography.

Compilation happens on the build machine. The shipped distribution needs neither
Homebrew nor a compiler, and retains Batchalign's macOS 11 deployment target.
"""

from __future__ import annotations

import gzip
import hashlib
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request


# Match the Python 3.12 distribution in the pinned PyApp 0.27 build.rs.
PYTHON_URL = "https://github.com/astral-sh/python-build-standalone/releases/download/20250311/cpython-3.12.9%2B20250311-x86_64-apple-darwin-install_only_stripped.tar.gz"
PYTHON_SHA256 = "b296808b7ae0806f63158b4d583fb416a8a9c1cc9c720efb64cce7b9aae7d5ca"
OPENSSL_VERSION = "3.5.9"
OPENSSL_URL = f"https://github.com/openssl/openssl/releases/download/openssl-{OPENSSL_VERSION}/openssl-{OPENSSL_VERSION}.tar.gz"
OPENSSL_SHA256 = "603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a"
CRYPTOGRAPHY_VERSION = "50.0.2"
CRYPTOGRAPHY_URL = "https://files.pythonhosted.org/packages/9d/af/182eb91b0df3fe75c4d9f26fe70684569566745f6ba7e5c9c73a862c5252/cryptography-50.0.2.tar.gz"
CRYPTOGRAPHY_SHA256 = "7b46165bb56eb4704e2eaaf86f3c940d19154535d9b0ca7d6d590b04060e00d5"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(url: str, expected: str, cache: Path) -> Path:
    target = cache / f"{expected}.tar.gz"
    if target.is_file() and digest(target) == expected:
        return target
    partial = target.with_suffix(".download")
    print(f"Downloading {url}", file=sys.stderr, flush=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as stream:
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
        if digest(partial) != expected:
            raise ValueError(f"SHA-256 mismatch for {url}")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return target


def extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as source:
        source.extractall(destination, filter="data")


def pack(runtime: Path, destination: Path) -> None:
    def normalize(member: tarfile.TarInfo) -> tarfile.TarInfo | None:
        if "__pycache__" in Path(member.name).parts or member.name.endswith(".pyc"):
            return None
        member.uid = member.gid = member.mtime = 0
        member.uname = member.gname = ""
        return member

    with destination.open("wb") as output, gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            archive.add(runtime / "python", arcname="python", filter=normalize)


def run(command: list[str | Path], *, cwd: Path, env: dict[str, str]) -> None:
    print("+ " + " ".join(map(str, command)), file=sys.stderr, flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True, stdout=sys.stderr)


def validate_linked_libraries(commands: str) -> None:
    # otool -L includes LC_ID_DYLIB (the extension's own install name).
    # Inspect load commands instead so only actual dependencies are checked.
    dependency_commands = {
        "LC_LOAD_DYLIB", "LC_LOAD_WEAK_DYLIB", "LC_REEXPORT_DYLIB",
        "LC_LAZY_LOAD_DYLIB", "LC_LOAD_UPWARD_DYLIB",
    }
    for block in re.split(r"(?m)^Load command \d+\s*$", commands):
        command = re.search(r"(?m)^\s*cmd\s+(\S+)\s*$", block)
        if not command or command[1] not in dependency_commands:
            continue
        name = re.search(r"(?m)^\s*name (.+) \(offset \d+\)\s*$", block)
        if not name:
            raise RuntimeError(f"Cannot read library name in {command[1]}")
        library = name[1]
        if not library.startswith(("/usr/lib/", "/System/Library/")):
            raise RuntimeError(f"Cryptography depends on a non-system library: {library}")


def build(cache: Path) -> Path:
    if sys.platform != "darwin" or platform.machine() != "x86_64":
        raise RuntimeError("This distribution must be built natively on Intel macOS")
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:20]
    output = cache / f"python-intel-{key}.tar.gz"
    checksum = output.with_suffix(".sha256")
    if output.is_file() and checksum.is_file() and digest(output) == checksum.read_text().strip():
        return output
    sources = [download(url, sha, cache) for url, sha in (
        (PYTHON_URL, PYTHON_SHA256), (OPENSSL_URL, OPENSSL_SHA256),
        (CRYPTOGRAPHY_URL, CRYPTOGRAPHY_SHA256),
    )]
    with tempfile.TemporaryDirectory(prefix="batchalign-intel-runtime-") as temporary:
        work = Path(temporary)
        runtime = work / "runtime"
        extract(sources[0], runtime)
        extract(sources[1], work / "openssl-source")
        openssl_source = work / "openssl-source" / f"openssl-{OPENSSL_VERSION}"
        openssl_prefix = work / "openssl"
        python = runtime / "python/bin/python3"
        env = {key: value for key, value in os.environ.items()
               if key not in {"PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"}}
        env.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1",
                   MACOSX_DEPLOYMENT_TARGET="11.0", OPENSSL_STATIC="1",
                   OPENSSL_DIR=str(openssl_prefix))
        for variable, tool in (("CC", "clang"), ("AR", "ar"), ("RANLIB", "ranlib")):
            env[variable] = subprocess.check_output(["xcrun", "--find", tool], text=True).strip()
        env["SDKROOT"] = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
        jobs = str(min(os.cpu_count() or 2, 4))
        # no-module keeps the legacy provider built in rather than depending on
        # an external provider directory on the build machine.
        run(["perl", "Configure", "darwin64-x86_64-cc", "no-shared", "no-module", "no-tests",
             f"--prefix={openssl_prefix}", "--openssldir=/etc/ssl", "-mmacosx-version-min=11.0"],
            cwd=openssl_source, env=env)
        run(["make", f"-j{jobs}"], cwd=openssl_source, env=env)
        run(["make", "install_sw"], cwd=openssl_source, env=env)
        wheels = work / "wheels"
        run([python, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", wheels, sources[2]], cwd=work, env=env)
        wheel, = wheels.glob("cryptography-*.whl")
        run([python, "-m", "pip", "install", "--no-compile", "--only-binary=:all:", wheel], cwd=work, env=env)
        extension, = (runtime / "python/lib/python3.12/site-packages/cryptography/hazmat/bindings").glob("_rust*.so")
        commands = subprocess.check_output(["otool", "-l", str(extension)], text=True)
        validate_linked_libraries(commands)
        minimums = re.findall(r"(?:minos|version)\s+(\d+\.\d+)(?:\.\d+)?", commands)
        # LC_BUILD_VERSION uses minos; older Mach-O headers use LC_VERSION_MIN_MACOSX.
        minimum = re.search(r"\bminos\s+(\d+)\.(\d+)", commands)
        if not minimum:
            minimum = re.search(r"LC_VERSION_MIN_MACOSX\s+cmdsize \d+\s+version (\d+)\.(\d+)", commands)
        if not minimum or tuple(map(int, minimum.groups())) > (11, 0):
            raise RuntimeError(f"Cryptography requires a newer macOS than 11.0: {minimums}")
        run([python, "-c", "import cryptography; from cryptography.hazmat.primitives.ciphers.aead import AESGCM; "
             "from cryptography.hazmat.backends.openssl.backend import backend; "
             f"assert cryptography.__version__ == '{CRYPTOGRAPHY_VERSION}'; "
             f"assert backend.openssl_version_text().startswith('OpenSSL {OPENSSL_VERSION} '); "
             "a = AESGCM(bytes(16)); n = bytes(12); p = b'Batchalign bootstrap'; "
             "assert a.decrypt(n, a.encrypt(n, p, None), None) == p; "
             "print(cryptography.__version__, backend.openssl_version_text())"], cwd=work, env=env)
        partial = output.with_suffix(".partial")
        pack(runtime, partial)
        partial.replace(output)
        checksum.write_text(digest(output) + "\n")
    return output


if __name__ == "__main__":
    print(build(Path(sys.argv[1]).resolve()))
