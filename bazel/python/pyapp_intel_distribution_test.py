import hashlib
import io
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from bazel.python.pyapp_intel_distribution import (
    build, digest, download, extract, pack, validate_linked_libraries,
)


class DistributionTests(unittest.TestCase):
    def test_extension_install_name_is_not_an_external_dependency(self):
        validate_linked_libraries("""/tmp/_rust.abi3.so:
Load command 0
          cmd LC_ID_DYLIB
      cmdsize 80
         name @rpath/cryptography.hazmat.bindings._rust.abi3.so (offset 24)
Load command 1
          cmd LC_LOAD_DYLIB
      cmdsize 56
         name /usr/lib/libSystem.B.dylib (offset 24)
Load command 2
          cmd LC_LOAD_WEAK_DYLIB
      cmdsize 96
         name /System/Library/Frameworks/Security.framework/Versions/A/Security (offset 24)
""")

    def test_actual_non_system_dependencies_are_rejected(self):
        for command in ("LC_LOAD_DYLIB", "LC_LOAD_WEAK_DYLIB", "LC_REEXPORT_DYLIB",
                        "LC_LAZY_LOAD_DYLIB", "LC_LOAD_UPWARD_DYLIB"):
            for library in ("@rpath/cryptography.hazmat.bindings._rust.abi3.so",
                            "@rpath/libcrypto.3.dylib", "/usr/local/opt/openssl/lib/libcrypto.3.dylib"):
                with self.subTest(command=command, library=library):
                    with self.assertRaisesRegex(RuntimeError, "non-system library"):
                        validate_linked_libraries(
                            f"Load command 0\n cmd {command}\n name {library} (offset 24)\n")

    def test_dependency_without_a_readable_name_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Cannot read library name"):
            validate_linked_libraries("Load command 0\n cmd LC_LOAD_DYLIB\n")

    def test_runtime_archive_round_trip_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "build with spaces"
            executable = runtime / "python/bin/python3"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"runtime executable")
            executable.chmod(0o755)
            bytecode = runtime / "python/lib/__pycache__/module.pyc"
            bytecode.parent.mkdir(parents=True)
            bytecode.write_bytes(b"build-machine path")
            first, second = root / "first.tar.gz", root / "second.tar.gz"
            pack(runtime, first)
            os.utime(executable, (100, 100))
            pack(runtime, second)
            self.assertEqual(digest(first), digest(second))
            with tarfile.open(first) as archive:
                self.assertNotIn("python/lib/__pycache__/module.pyc", archive.getnames())
                member = archive.getmember("python/bin/python3")
                self.assertEqual(member.mode, stat.S_IMODE(executable.stat().st_mode))
                self.assertEqual((member.uid, member.gid, member.mtime), (0, 0, 0))
            installed = root / "relocated runtime"
            extract(first, installed)
            self.assertEqual((installed / "python/bin/python3").read_bytes(), b"runtime executable")

    def test_download_checks_hash_and_repairs_corrupt_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.write_bytes(b"verified source archive")
            expected = hashlib.sha256(source.read_bytes()).hexdigest()
            cache = root / "cache"
            cache.mkdir()
            cached = download(source.as_uri(), expected, cache)
            cached.write_bytes(b"corrupted cache")
            self.assertEqual(download(source.as_uri(), expected, cache).read_bytes(), source.read_bytes())
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                download(source.as_uri(), "0" * 64, cache)
            self.assertFalse((cache / ("0" * 64 + ".tar.gz")).exists())
            self.assertFalse(list(cache.glob("*.download")))

    def test_archive_cannot_escape_extraction_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "unsafe.tar"
            with tarfile.open(source, "w") as archive:
                member = tarfile.TarInfo("../escaped")
                member.size = 4
                archive.addfile(member, io.BytesIO(b"data"))
            with self.assertRaises(tarfile.FilterError):
                extract(source, root / "destination")
            self.assertFalse((root / "escaped").exists())

    def test_native_build_rejects_other_platforms(self):
        with patch("sys.platform", "win32"):
            with self.assertRaisesRegex(RuntimeError, "natively on Intel macOS"):
                build(Path("must-not-be-created"))


if __name__ == "__main__":
    unittest.main()
