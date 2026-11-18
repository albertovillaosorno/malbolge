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
#   - End-to-end C23 signed self-subtraction branch with real guest effects.
# - Must-Not:
#   - Confuse a source-time identity proof with runtime guest branching.
# - Allows:
#   - Inputs: one frozen C source, five binary inputs and source mutations.
#   - Outputs: exact native/guest parity or explicit no-artifact refusal.
#   - Side effects: temporary native binaries and compiler outputs.
# - Split-When:
#   - A general C23 signed-EOF CFG oracle replaces this bounded proof.
# - Merge-When:
#   - P2 mutable checksum acceptance subsumes this static branch witness.
# - Summary:
#   - Prove source authentication, real signed guest input and safe refusal.

"""EOF-safe algebraic source guard that preserves a real guest read."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

ROOT: Final = Path(__file__).resolve().parents[1]
SOURCE: Final = (
    ROOT / "tests/compiler/c-frontend/accepted/signed_reflexive_guard_output.c"
)
FRONTEND: Final = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
)
CLANG: Final = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
ADAPTER: Final = ROOT / ".cache/rust/target/debug/c2malbolge_json"
DRIVER: Final = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
VM: Final = ROOT / ".cache/rust/target/debug/malbolge"
VECTORS: Final = (b"", b"\x00", b"\xff", b"\x00\x80\xff", b"\x05\x00\x81")
EXPECTED: Final = b"\x0b"


def environment() -> dict[str, str]:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(ROOT / ".dependencies/llvm/22.1.8/lib")
    return env


def normalize(source: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            str(FRONTEND),
            "--guest-include",
            str(ROOT / "src/runtime/guest-c-library/contract/include"),
            "--resource-dir",
            str(ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"),
            "--source-id",
            source.name,
            str(source),
        ],
        env=environment(),
        capture_output=True,
        check=False,
        timeout=20,
    )


def compile_guest(source: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(DRIVER),
            "--repository-tools",
            "--capsule",
            "--max-wall-seconds",
            "190",
            "--output",
            str(target),
            str(source),
        ],
        env=environment(),
        capture_output=True,
        check=False,
        timeout=195,
    )


@final
class SignedGuardedSourceGuestTests(unittest.TestCase):
    def test_source_typed_projection_and_mutated_branch_refusal(self) -> None:
        self.assertEqual(len(VECTORS), 5)
        self.assertTrue(all(path.is_file() for path in (CLANG, FRONTEND, ADAPTER, VM)))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            directory = Path(raw)
            original = normalize(SOURCE)
            self.assertEqual(original.returncode, 0, original.stderr)
            artifact = directory / "would-publish.malbolge"
            typed = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    "/bin/false",
                    "--output",
                    str(artifact),
                    "--source",
                    str(SOURCE),
                ],
                input=original.stdout,
                capture_output=True,
                check=False,
                timeout=20,
            )
            self.assertNotEqual(typed.returncode, 0)
            self.assertIn(b"layout backend exited unsuccessfully", typed.stderr)
            self.assertFalse(artifact.exists())
            replacements = (
                (b"current - current", b"current - (current + 1)"),
                (b"== 0", b"== 1"),
                (b"putchar(11);", b"putchar(current);"),
                (b"putchar(5);", b"putchar(current);"),
                (b"putchar(11);", b"putchar(11); putchar(11);"),
            )
            for index, (before, after) in enumerate(replacements):
                with self.subTest(mutation=index):
                    mutated = directory / f"mutated-{index}.c"
                    content = SOURCE.read_bytes()
                    self.assertEqual(content.count(before), 1)
                    mutated.write_bytes(content.replace(before, after))
                    normalized = normalize(mutated)
                    self.assertEqual(normalized.returncode, 0, normalized.stderr)
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            "/bin/false",
                            "--output",
                            str(artifact),
                            "--source",
                            str(mutated),
                        ],
                        input=normalized.stdout,
                        capture_output=True,
                        check=False,
                        timeout=20,
                    )
                    self.assertIn(b"normalized frontend rejected", refused.stderr)
                    self.assertFalse(artifact.exists())
            # A valid normalized AST from a different source must also refuse.
            forged = directory / "same-ast-new-source.c"
            forged.write_bytes(
                SOURCE.read_bytes().replace(b"putchar(5);", b"putchar(6);")
            )
            refused = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    "/bin/false",
                    "--output",
                    str(artifact),
                    "--source",
                    str(forged),
                ],
                input=original.stdout,
                capture_output=True,
                check=False,
                timeout=20,
            )
            self.assertIn(b"normalized frontend rejected", refused.stderr)
            self.assertFalse(artifact.exists())

    def test_forged_clang_nodes_refuse_without_publication(self) -> None:
        normalized = normalize(SOURCE)
        self.assertEqual(normalized.returncode, 0, normalized.stderr)
        original = json.loads(normalized.stdout)
        nodes = original["nodes"]
        self.assertEqual(len(nodes), 26)
        cases = (
            (12, "reference", "different@45"),
            (14, "reference", "different@45"),
            (10, "operation", "+"),
            (8, "operation", "!="),
            (4, "reference", "external:putchar"),
            (20, "constant_integer", "12"),
            (25, "constant_integer", "6"),
            (16, "parent", 2),
            (22, "parent", 2),
            # Structural AST nodes may not carry declarator or literal
            # metadata: the authenticated source has no such effects.
            (1, "constant_integer", "0"),
            (7, "inline_specified", True),
            (16, "storage_class", "static"),
            (21, "storage_duration", "automatic"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            destination = Path(raw) / "forged.malbolge"
            for index, key, replacement in cases:
                with self.subTest(node_id=index + 1, field=key):
                    altered = json.loads(normalized.stdout)
                    altered["nodes"][index][key] = replacement
                    payload = json.dumps(altered, separators=(",", ":")).encode()
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            "/bin/false",
                            "--output",
                            str(destination),
                            "--source",
                            str(SOURCE),
                        ],
                        input=payload,
                        capture_output=True,
                        check=False,
                        timeout=20,
                    )
                    self.assertIn(b"normalized frontend rejected", refused.stderr)
                    self.assertFalse(destination.exists())

    def test_reflexive_truth_variants_preserve_signed_eof(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            directory = Path(raw)
            content = SOURCE.read_bytes()
            for operator in (b"-", b"^"):
                for comparison in (b"==", b"!="):
                    with self.subTest(operator=operator, comparison=comparison):
                        variant = directory / (
                            f"variant-{'sub' if operator == b'-' else 'xor'}"
                            f"-{'eq' if comparison == b'==' else 'ne'}.c"
                        )
                        alternate = content.replace(
                            b"current - current", b"current " + operator + b" current"
                        ).replace(b"== 0", comparison + b" 0")
                        variant.write_bytes(alternate)
                        normalized = normalize(variant)
                        self.assertEqual(normalized.returncode, 0, normalized.stderr)
                        target = directory / "not-published.malbolge"
                        typed = subprocess.run(
                            [
                                str(ADAPTER),
                                "--layout-backend",
                                "/bin/false",
                                "--output",
                                str(target),
                                "--source",
                                str(variant),
                            ],
                            input=normalized.stdout,
                            capture_output=True,
                            check=False,
                            timeout=20,
                        )
                        self.assertIn(
                            b"layout backend exited unsuccessfully", typed.stderr
                        )
                        self.assertFalse(target.exists())
                        expected = EXPECTED if comparison == b"==" else b"\x05"
                        wrapper = directory / "main.c"
                        wrapper.write_text(
                            f'#include "{variant}"\nint main(void) {{ emit(); return 0; }}\n',
                            encoding="utf-8",
                        )
                        for optimization in ("-O0", "-O2"):
                            native = directory / "native"
                            built = subprocess.run(
                                [
                                    str(CLANG),
                                    "-std=c23",
                                    optimization,
                                    "-Wall",
                                    "-Wextra",
                                    "-Werror",
                                    "-fsanitize=undefined",
                                    "-fno-sanitize-recover=all",
                                    str(wrapper),
                                    "-o",
                                    str(native),
                                ],
                                env=environment(),
                                capture_output=True,
                                check=False,
                                timeout=20,
                            )
                            self.assertEqual(built.returncode, 0, built.stderr)
                            for stream in VECTORS:
                                run = subprocess.run(
                                    [str(native)],
                                    input=stream,
                                    capture_output=True,
                                    check=False,
                                    timeout=10,
                                )
                                self.assertEqual(run.returncode, 0, run.stderr)
                                self.assertEqual(run.stdout, expected)

    def test_xor_inequality_reaches_other_guest_arm(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            directory = Path(raw)
            alternate = directory / "xor-inequality.c"
            alternate.write_bytes(
                SOURCE.read_bytes()
                .replace(b"current - current", b"current ^ current")
                .replace(b"== 0", b"!= 0")
            )
            guest = directory / "xor-inequality.malbolge"
            compiled = compile_guest(alternate, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for stream in VECTORS:
                with self.subTest(stream=stream):
                    run = subprocess.run(
                        [
                            str(VM),
                            str(guest),
                            "--input-stdin",
                            "--report-steps",
                            "--max-steps",
                            "100000",
                        ],
                        input=stream,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, b"\x05")
                    self.assertIn(b"malbolge-steps-v1:", run.stderr)

    def test_native_c23_and_real_guest_parity(self) -> None:
        self.assertEqual(
            hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "8adfe1bb744cd7ef9cfbfc9846a03317376ab43d6c0832bae7c7c95565945f72",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as raw:
            directory = Path(raw)
            wrapper = directory / "main.c"
            wrapper.write_text(
                f'#include "{SOURCE}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            for optimization in ("-O0", "-O2"):
                native = directory / f"native-{optimization[2:]}"
                built = subprocess.run(
                    [
                        str(CLANG),
                        "-std=c23",
                        optimization,
                        "-Wall",
                        "-Wextra",
                        "-Werror",
                        "-fsanitize=undefined",
                        "-fno-sanitize-recover=all",
                        str(wrapper),
                        "-o",
                        str(native),
                    ],
                    env=environment(),
                    capture_output=True,
                    check=False,
                    timeout=20,
                )
                self.assertEqual(built.returncode, 0, built.stderr)
                for stream in VECTORS:
                    with self.subTest(mode=optimization, stream=stream):
                        run = subprocess.run(
                            [str(native)],
                            input=stream,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, EXPECTED)
            guest = directory / "signed-reflexive.malbolge"
            compiled = compile_guest(SOURCE, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for stream in VECTORS:
                with self.subTest(guest_stream=stream):
                    run = subprocess.run(
                        [
                            str(VM),
                            str(guest),
                            "--input-stdin",
                            "--report-steps",
                            "--max-steps",
                            "100000",
                        ],
                        input=stream,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, EXPECTED)
                    self.assertIn(b"malbolge-steps-v1:", run.stderr)


if __name__ == "__main__":
    _ = unittest.main()
