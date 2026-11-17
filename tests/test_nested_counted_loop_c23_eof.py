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
#   - Nested and transformed signed loop-local EOF publication regression.
# - Must-Not:
#   - Accept successful-byte-only guest output as C23 EOF equivalence.
# - Allows:
#   - Inputs: five frozen binary vectors and canonical full C23 loop sources.
#   - Outputs: native O0/O2 and actual guest parity or typed no-publication.
#   - Side effects: isolated temporary compilers and bounded normative VM.
# - Split-When:
#   - General guest signed EOF conversion subsumes this bounded test.
# - Merge-When:
#   - Counted-loop signed EOF parity has one shared native-C witness.
# - Summary:
#   - Nested putchar and identity expressions cannot erase signed EOF.

"""Check C23 EOF in complete counted loops against real guest behavior."""

from __future__ import annotations

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
VECTORS: Final = (
    b"",
    b"\x00",
    b"\xff",
    b"\x01\x80",
    b"\x00\xff\x81",
)
# Cases are full source-C programs, not snippets spliced into a host oracle.
CASES: Final = (
    ("nested-two", 2, "putchar(putchar(current));"),
    ("nested-three", 3, "putchar(putchar(current));"),
    ("identity-add", 2, "putchar(current + 0);"),
    ("unsigned-cast", 2, "putchar((unsigned char)current);"),
    ("selected-nested", 3, "putchar(putchar(current));"),
)


def source_for_case(name: str, trips: int, output: str) -> str:
    """Keep exactly the source and Clang parent structure under test."""
    statement = f"        {output}\n"
    if name == "selected-nested":
        statement = f"        if (i == 1U) {{\n            {output}\n        }}\n"
    return (
        "#include <stdio.h>\n"
        "void emit(void) {\n"
        f"    for (unsigned i = 0U; i < {trips}U; ++i) {{\n"
        "        int current = getchar();\n"
        f"{statement}"
        "    }\n"
        "}\n"
    )


def oracle(name: str, trips: int, data: bytes) -> bytes:
    """Model C23 getchar EOF and putchar's unsigned-char conversion."""
    output = bytearray()
    for index in range(trips):
        if name == "selected-nested" and index != 1:
            continue
        value = data[index] if index < len(data) else 255
        repeats = 2 if name.startswith("nested") or name == "selected-nested" else 1
        output.extend([value] * repeats)
    return bytes(output)


@final
class NestedCountedLoopSignedEofTests(unittest.TestCase):
    def test_native_c23_or_real_guest_or_no_publication(self) -> None:
        if not all(path.is_file() for path in (CLANG, DRIVER, VM)):
            self.skipTest("pinned Clang, compiler bridge and profile VM required")
        env = os.environ.copy()
        llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
        )
        for name, trips, output in CASES:
            with (
                self.subTest(case=name),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw,
            ):
                folder = Path(raw)
                source = folder / "nested-signed-eof.c"
                _ = source.write_text(
                    source_for_case(name, trips, output), encoding="utf-8"
                )
                wrapper = folder / "main.c"
                _ = wrapper.write_text(
                    f'#include "{source}"\nint main(void) {{ emit(); return 0; }}\n',
                    encoding="utf-8",
                )
                expected = {data: oracle(name, trips, data) for data in VECTORS}
                for opt in ("-O0", "-O2"):
                    native = folder / f"native-{opt[2:]}"
                    built = subprocess.run(
                        [
                            str(CLANG),
                            "-std=c23",
                            opt,
                            "-Wall",
                            "-Wextra",
                            "-Werror",
                            "-fsanitize=undefined",
                            "-fno-sanitize-recover=all",
                            str(wrapper),
                            "-o",
                            str(native),
                        ],
                        env=env,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(built.returncode, 0, built.stderr)
                    for data in VECTORS:
                        run = subprocess.run(
                            [str(native)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, expected[data])
                target = folder / "guest.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--capsule",
                        "--max-wall-seconds",
                        "70",
                        "--output",
                        str(target),
                        str(source),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=75,
                )
                if compiled.returncode != 0:
                    self.assertIn(b"Unsupported", compiled.stderr)
                    self.assertFalse(target.exists(), "refusal published a guest")
                    continue
                self.assertTrue(target.is_file(), "compiler claimed no guest")
                for data in VECTORS:
                    guest = subprocess.run(
                        [
                            str(VM),
                            str(target),
                            "--input-stdin",
                            "--report-steps",
                            "--max-steps",
                            "10000",
                        ],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, expected[data])
                    self.assertIn(b"malbolge-steps-v1:", guest.stderr)


if __name__ == "__main__":
    _ = unittest.main()
