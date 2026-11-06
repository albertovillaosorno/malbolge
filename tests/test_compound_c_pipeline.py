# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Reproducible complete-C Fibonacci pipeline failure and guest oracle.
# - Must-Not:
#   - Claim unsupported C variables/branches/loops have guest semantics.
# - Allows:
#   - Inputs: a tracked stateful C program and exact pinned compiler binaries.
#   - Outputs: an identified unsupported semantic stage, with no guest artifact.
#   - Side effects: project-local temporary output only.
# - Split-When:
#   - Production C control-flow lowering has a validated end-to-end witness.
# - Merge-When:
#   - The general C semantic matrix subsumes this first full-program repro.
# - Summary:
#   - Local storage metadata is valid JSON, but local state is not yet lowered.
# - Description:
#   - The independently computed oracle remains a future positive VM target.
# - Usage:
#   - python3.14 -B -m unittest tests.test_compound_c_pipeline -v
# - Defaults:
#   - No fake output on host, no guest artifact on compiler refusal.

"""Complete Fibonacci blocker and source-bound initialized local VM parity."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/conditional_fibonacci.c"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
EXPECTED = bytes.fromhex("02595f08574f226d0390b323")


def reference_bytes() -> bytes:
    """Reference the bounded unsigned-C arithmetic, not compiler output."""
    previous, current = 1, 1
    output = bytearray()
    for _ in range(12):
        following = (previous + current) & 0xFF
        output.append(following if following % 2 == 0 else following ^ 0x5A)
        previous, current = current, following
    return bytes(output)


class CompoundCPipelineTests(unittest.TestCase):
    def test_fibonacci_branch_oracle_is_independent_and_stable(self) -> None:
        self.assertEqual(reference_bytes(), EXPECTED)
        self.assertEqual(len(EXPECTED), 12)

    def test_whole_program_rejection_or_guest_parity(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        if not RESOURCE.is_dir() or not GUEST_INCLUDE.is_dir():
            self.skipTest("pinned Clang resources or includes are absent")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "fibonacci.malbolge"
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--frontend",
                    str(FRONTEND),
                    "--json-adapter",
                    str(ADAPTER),
                    "--layout-backend",
                    str(LAYOUT),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/conditional-fibonacci-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(SOURCE),
                ],
                check=False,
                capture_output=True,
                timeout=20,
            )
            if process.returncode == 0:
                # Future implementation must pass an actual normative VM
                # replay. The host oracle never substitutes for guest output.
                self.assertTrue(guest.is_file())
                execution = subprocess.run(
                    [str(VM), str(guest), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(execution.returncode, 0, execution.stderr)
                self.assertEqual(execution.stdout, reference_bytes())
                self.assertRegex(
                    execution.stderr,
                    rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                )
                return
            # Until C-state lowering exists, require a typed refusal and
            # no output artifact rather than a host-side fake guest trace.
            declaration_line = next(
                number
                for number, line in enumerate(SOURCE.read_text().splitlines(), 1)
                if "unsigned a = 1U;" in line
            )
            self.assertIn(
                (
                    "normalized frontend rejected: Unsupported; "
                    "unlowered C declaration-statement "
                    f"at {declaration_line}:5 "
                ).encode(),
                process.stderr,
            )
            self.assertNotIn(b"Malformed", process.stderr)
            self.assertFalse(guest.exists(), "unsupported C published a guest")

    def test_unsupported_multiplication_rejects_guest_artifact(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_initialized_output.c"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            altered = Path(scratch) / "changed.c"
            text = source.read_text()
            self.assertIn("    putchar(value);", text)
            _written = altered.write_text(
                text.replace(
                    "    putchar(value);",
                    "    value = value * 2U;\n    putchar(value);",
                )
            )
            guest = Path(scratch) / "invalid.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/mutated-local-output-v1",
                    "--output",
                    str(guest),
                    str(altered),
                ],
                check=False,
                capture_output=True,
                timeout=20,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"Unsupported", compiled.stderr)
            self.assertFalse(guest.exists())

    def _assert_constant_branch_guest(self, stem: str, second: int) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / f"tests/compiler/c-frontend/accepted/{stem}.c"
        value = 60 + second
        expected = value ^ (3 if (value & 1) == 0 else 2)
        self.assertEqual(expected, 65)
        source_id = "tests/" + stem.replace("_", "-") + "-v1"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "conditional.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    source_id,
                    "--output",
                    str(guest),
                    "--capsule",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, bytes([expected]))
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")

    def test_source_proven_if_then_reaches_real_guest_output(self) -> None:
        self._assert_constant_branch_guest("local_conditional_output", 6)

    def test_source_proven_if_else_reaches_real_guest_output(self) -> None:
        self._assert_constant_branch_guest("local_conditional_else_output", 7)

    def test_expression_argument_branches_reach_real_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_expression_output.c"
        original = source.read_text()
        self.assertIn("unsigned b = 6U;", original)
        self.assertIn("result = result ^ 1U;", original)
        # Independent arithmetic: true (66 ^ 0) ^ 3 => 65;
        # false (67 ^ 0) ^ 1 => 66. Both paths must perform C arithmetic.
        cases = (
            (original, (60 + 6) ^ 0 ^ 3),
            (
                original.replace("unsigned b = 6U;", "unsigned b = 7U;")
                .replace("result = result ^ 1U;", "result = result ^ 0U;")
                .replace(
                    "putchar((int)(result ^ 3U));", "putchar((int)(result ^ 1U));"
                ),
                (60 + 7) ^ 0 ^ 1,
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for index, (text, expected) in enumerate(cases):
                altered = Path(scratch) / f"expression-{index}.c"
                _written = altered.write_text(text)
                guest = Path(scratch) / f"expression-{index}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/checked-expression-{index}-v1",
                        "--output",
                        str(guest),
                        "--capsule",
                        str(altered),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                executed = subprocess.run(
                    [str(VM), str(guest), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, bytes([expected]))
                self.assertEqual(
                    executed.stderr,
                    f"malbolge-steps-v1:{31 if index == 0 else 69}\n".encode(),
                )

            unsupported = original.replace(
                "putchar((int)(result ^ 3U));",
                "putchar((int)(result * 3U));",
            )
            altered = Path(scratch) / "unsupported-expression.c"
            _written = altered.write_text(unsupported)
            guest = Path(scratch) / "unsupported-expression.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/unsupported-expression-v1",
                    "--output",
                    str(guest),
                    str(altered),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"Unsupported", compiled.stderr)
            self.assertFalse(guest.exists())

    def test_multi_local_constant_flow_reaches_real_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_multi_output.c"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "multi-local.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/local-multi-output-v1",
                    "--output",
                    str(guest),
                    "--capsule",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            # (60 + 8) ^ 3 - 6 comes from distinct source-bound locals.
            self.assertEqual(executed.stdout, b"A")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")

    def test_ordered_arithmetic_reaches_real_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_arithmetic_output.c"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "local-arithmetic.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/local-arithmetic-output-v1",
                    "--output",
                    str(guest),
                    "--capsule",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            # (60 + 8) ^ 3 - 6 = 65, not a copied source literal.
            self.assertEqual(executed.stdout, b"A")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")

    def test_ordered_literal_reassignment_reaches_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_reassigned_output.c"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "local-reassignment.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/local-reassigned-output-v1",
                    "--output",
                    str(guest),
                    "--capsule",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            # Neither 0 from the initializer nor 66 from the first write.
            self.assertEqual(executed.stdout, b"A")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")

    def test_automatic_unsigned_local_reaches_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_initialized_output.c"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "local-output.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/local-initialized-output-v1",
                    "--output",
                    str(guest),
                    "--capsule",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"A")
            self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")


if __name__ == "__main__":
    _ = unittest.main()
