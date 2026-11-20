# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Source-C signed second getchar/putchar guest EOF publication parity.
# - Must-Not:
#   - Replace signed EOF with a byte-only fixture or infer guest output on host.
# - Allows:
#   - Inputs: independent native C23 and same compiled source, binary stdin.
#   - Outputs: signed EOF-to-u8 parity and rejection of altered C effect traces.
#   - Side effects: bounded subprocesses in temporary filesystem.
# - Split-When:
#   - General C23 signed I/O compilation subsumes this bounded closed grammar.
# - Merge-When:
#   - The P2 mutable checksum guest implements genuine EOF-dependent control.
# - Summary:
#   - Independent Clang and guest agree on two real reads and EOF conversion.

"""C23 signed double-read publication, not the still-unlinked EOF checksum."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

ROOT: Final = Path(__file__).resolve().parents[1]
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
FRONTEND: Final = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
)
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LOCAL_SOURCE: Final = (
    "#include <stdio.h>\n"
    "void emit(void) { getchar(); int current = getchar(); "
    "putchar(current); }\n"
)
SOURCE: Final = "#include <stdio.h>\nvoid emit(void) { getchar(); putchar(getchar()); }\n"
VECTORS: Final = (
    ("empty", b"", b"\xff"),
    ("first-only", b"\x00", b"\xff"),
    ("nul", b"\x81\x00", b"\x00"),
    ("high-byte", b"\x00\xff", b"\xff"),
    ("trailing", b"\xff\x80\x00", b"\x80"),
)


@final
class SignedSecondEchoPublicationTests(unittest.TestCase):
    def test_source_c23_native_and_normative_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory)
            source = path / "source.c"
            source.write_text(SOURCE, encoding="utf-8")
            wrapper = path / "entry.c"
            wrapper.write_text('#include "source.c"\nint main(void) { emit(); return 0; }\n', encoding="utf-8")
            env = os.environ.copy()
            llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                item for item in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if item
            )
            for optimization in ("-O0", "-O2"):
                binary = path / f"native-{optimization[2:]}"
                compiled = subprocess.run(
                    [str(CLANG), "-std=c23", optimization, "-Wall", "-Wextra", "-Werror",
                     "-fsanitize=undefined", "-fno-sanitize-recover=all",
                     str(wrapper), "-o", str(binary)],
                    capture_output=True, env=env, check=False, timeout=20,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                for label, stdin, expected in VECTORS:
                    with self.subTest(oracle=optimization, stream=label):
                        run = subprocess.run([str(binary)], input=stdin, capture_output=True,
                                             check=False, timeout=15)
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, expected)

            target = path / "second.malbolge"
            compiler = subprocess.run(
                [sys.executable, "-B", str(DRIVER), "--repository-tools", "--capsule",
                 "--max-wall-seconds", "75", "--output", str(target), str(source)],
                capture_output=True, check=False, timeout=85,
            )
            self.assertEqual(compiler.returncode, 0, compiler.stderr)
            self.assertTrue(target.is_file())
            for label, stdin, expected in VECTORS:
                with self.subTest(guest=label):
                    guest = subprocess.run(
                        [str(VM), str(target), "--input-stdin", "--max-steps", "1000",
                         "--report-steps"],
                        input=stdin,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected)
                    self.assertIn(b"malbolge-steps-v1:81", guest.stderr)

    def test_second_signed_input_through_automatic_local(self) -> None:
        """The second read remains live across a genuine C23 int local."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory)
            source = path / "local.c"
            source.write_text(LOCAL_SOURCE, encoding="utf-8")
            wrapper = path / "main.c"
            wrapper.write_text(
                '#include "local.c"\nint main(void) { emit(); return 0; }\n',
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            for optimization in ("-O0", "-O2"):
                native = path / f"native-{optimization[2:]}"
                built = subprocess.run(
                    [str(CLANG), "-std=c23", optimization, "-Wall", "-Wextra",
                     "-Werror", "-fsanitize=undefined",
                     "-fno-sanitize-recover=all",
                     str(wrapper), "-o", str(native)],
                    capture_output=True, env=env, check=False, timeout=20,
                )
                self.assertEqual(built.returncode, 0, built.stderr)
                for label, stdin, expected in VECTORS:
                    with self.subTest(native=optimization, stream=label):
                        result = subprocess.run(
                            [str(native)], input=stdin, capture_output=True,
                            check=False, timeout=10,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout, expected)
            target = path / "local.malbolge"
            compiled = subprocess.run(
                [sys.executable, "-B", str(DRIVER), "--repository-tools",
                 "--capsule", "--max-wall-seconds", "75", "--output",
                 str(target), str(source)],
                capture_output=True, check=False, timeout=85,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(target.is_file())
            for label, stdin, expected in (VECTORS[0], VECTORS[2], VECTORS[4]):
                with self.subTest(guest=label):
                    guest = subprocess.run(
                        [str(VM), str(target), "--input-stdin", "--max-steps",
                         "1000", "--report-steps"],
                        input=stdin,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected)
                    self.assertIn(b"malbolge-steps-v1:81", guest.stderr)

    def test_local_alias_refuses_tampered_source_and_clang_nodes(self) -> None:
        """Neither source edits nor forged local bindings may publish code."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory)
            source = path / "local.c"
            target = path / "forged.malbolge"
            variants = (
                LOCAL_SOURCE.replace(
                    "putchar(current)", "putchar(current + 1)"
                ),
                LOCAL_SOURCE.replace(
                    "putchar(current)", "getchar(); putchar(current)"
                ),
                LOCAL_SOURCE.replace("putchar(current)", "putchar(getchar())"),
                LOCAL_SOURCE.replace(
                    "int current = getchar()", "int current = 0"
                ),
            )
            for index, variant in enumerate(variants):
                with self.subTest(unsafe_source=index):
                    source.write_text(variant, encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, "-B", str(DRIVER),
                         "--repository-tools", "--capsule",
                         "--max-wall-seconds", "30", "--output",
                         str(target), str(source)],
                        capture_output=True, check=False, timeout=40,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())
            source.write_text(LOCAL_SOURCE, encoding="utf-8")
            normalized = subprocess.run(
                [str(FRONTEND), "--guest-include",
                 str(ROOT / "src/runtime/guest-c-library/contract/include"),
                 "--resource-dir",
                 str(ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"),
                 "--source-id", "local-proof", str(source)],
                capture_output=True, check=False, timeout=15,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            for node_id, field, invalid in (
                (6, "reference", "current@0"),
                (14, "reference", "current@1"),
                (6, "storage_duration", "static"),
                (13, "operation", "int-to-bool"),
            ):
                with self.subTest(forged_node=node_id + 1, field=field):
                    artifact = json.loads(normalized.stdout)
                    artifact["nodes"][node_id][field] = invalid
                    result = subprocess.run(
                        [str(ADAPTER), "--layout-backend",
                         str(path / "unavailable-backend"),
                         "--output", str(target), "--source", str(source)],
                        input=json.dumps(artifact).encode(),
                        capture_output=True, check=False, timeout=15,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(
                        b"normalized frontend rejected", result.stderr
                    )
                    self.assertFalse(target.exists())

    def test_extra_input_is_not_silently_dropped(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory)
            source = path / "extra.c"
            source.write_text(
                SOURCE.replace("getchar(); putchar", "getchar(); getchar(); putchar"),
                encoding="utf-8",
            )
            target = path / "untrusted.malbolge"
            compiler = subprocess.run(
                [sys.executable, "-B", str(DRIVER), "--repository-tools", "--capsule",
                 "--max-wall-seconds", "30", "--output", str(target), str(source)],
                capture_output=True, check=False, timeout=40,
            )
            self.assertNotEqual(compiler.returncode, 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
