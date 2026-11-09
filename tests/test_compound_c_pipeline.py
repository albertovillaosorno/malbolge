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

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

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
LOOP_OUTPUT = ROOT / "tests/compiler/c-frontend/accepted/local_loop_branch_output.c"
WIDE_STREAM = (
    ROOT / "tests/compiler/c-frontend/accepted/local_loop_wide_branch_stream.c"
)


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

    def test_three_live_relocations_reach_real_guest_from_c(self) -> None:
        """Closed C arithmetic/branch, three actual relocated guest writes."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_three_relocation_branch_stream.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(3):
            next_value = (previous + current) & 255
            if next_value % 2 == 0:
                expected.append((next_value * 40 + 1) & 255)
            else:
                expected.append((next_value * 46 + 24) & 255)
            previous, current = current, next_value
        self.assertEqual(bytes(expected), bytes.fromhex("51a2fe"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "three-relocations.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/three-relocation-c-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                replay = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(replay.returncode, 0, replay.stderr)
                self.assertEqual(replay.stdout, expected)
                self.assertRegex(replay.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            invalid = Path(scratch) / "three-relocations-invalid.c"
            invalid.write_text(source.read_text().replace("next * 46U", "next / 0U"))
            rejected_guest = Path(scratch) / "rejected.malbolge"
            rejected = subprocess.run(
                [*command[:-2], str(rejected_guest), str(invalid)],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"Unsupported", rejected.stderr)
            self.assertFalse(rejected_guest.exists())

    def test_five_effect_recurrence_reaches_guest_after_layout_fix(self) -> None:
        """Project a complete stateful loop, branch and five guest bytes."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_four_relocation_five_output_branch_stream.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(5):
            next_value = (previous + current) & 255
            if next_value % 2 == 0:
                expected.append(((next_value // 2) * 241 + 68) & 255)
            else:
                expected.append(
                    ((next_value // 2) * 212 + (next_value // 8) * 119 + 52)
                    & 255
                )
            previous, current = current, next_value
        self.assertEqual(bytes(expected), bytes.fromhex("3508dc08a3"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "five-effects.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/five-effect-c-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                replay = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(replay.returncode, 0, replay.stderr)
                self.assertEqual(replay.stdout, expected)
                self.assertRegex(replay.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            invalid = Path(scratch) / "five-effects-invalid.c"
            invalid.write_text(source.read_text().replace("next / 2U", "next / 0U"))
            rejected_guest = Path(scratch) / "rejected.malbolge"
            rejected = subprocess.run(
                [*command[:-2], str(rejected_guest), str(invalid)],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"Unsupported", rejected.stderr)
            self.assertFalse(rejected_guest.exists())

    def test_original_fibonacci_two_iterations_use_guest_source_scratch(self) -> None:
        """The actual C recurrence emits two guest bytes after a forward jump."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler binaries are not built")
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        expected = reference_bytes()[:2]
        self.assertEqual(expected, bytes.fromhex("0259"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-two.c"
            source.write_text(original.replace("i < 12U", "i < 2U"))
            guest = Path(scratch) / "fibonacci-two.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/conditional-fibonacci-two-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                replay = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=45,
                )
                self.assertEqual(replay.returncode, 0, replay.stderr)
                self.assertEqual(replay.stdout, expected)
                self.assertRegex(replay.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

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
            # Typed constant/SSA admission succeeds for the full C loop;
            # only the positional guest byte-stream layout lacks a witness.
            self.assertIn(
                b"canonical typed byte bridge rejected: Layout(UnsupportedEffectTrace)",
                process.stderr,
            )
            self.assertNotIn(b"normalized frontend rejected", process.stderr)
            self.assertFalse(guest.exists(), "unwitnessed C published a guest")

    def test_three_iteration_branch_uses_guest_source_scratch(self) -> None:
        """Closed C state selects three bytes, guest computes their output."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler binaries are not built")
        original = SOURCE.read_text()
        expression = "next ^ (0x5AU ^ ((next & 4U) * 17U))"
        expected = bytes((2, 3 ^ 0x5A, 5 ^ (0x5A ^ (4 * 17))))
        self.assertEqual(expected, bytes.fromhex("02591b"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-three-scratch.c"
            source.write_text(
                original.replace("i < 12U", "i < 3U")
                .replace("next ^ 0x5AU", expression)
            )
            guest = Path(scratch) / "fibonacci-three-scratch.malbolge"
            command = [
                sys.executable, "-B", str(DRIVER), "--repository-tools",
                "--source-id", "tests/conditional-fibonacci-three-scratch-v1",
                "--capsule", "--output", str(guest), str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                replay = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied, check=False, capture_output=True,
                    timeout=30,
                )
                self.assertEqual(replay.returncode, 0, replay.stderr)
                self.assertEqual(replay.stdout, expected)
                self.assertRegex(replay.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_original_fibonacci_three_output_prefix_on_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        # The even arm emits 2; the odd arm uses source-derived XOR 0x3d.
        expected = bytes((2, 3 ^ 0x3D, 5 ^ 0x3D))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-three.c"
            _written = source.write_text(
                original.replace("i < 12U", "i < 3U").replace(
                    "next ^ 0x5AU", "next ^ 0x3DU"
                )
            )
            guest = Path(scratch) / "fibonacci-three.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/conditional-fibonacci-three-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((0xFF, 0x00, 0x80))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            # An unsupported source operation must not inherit the witness.
            altered = Path(scratch) / "fibonacci-three-unsupported.c"
            altered.write_text(source.read_text().replace("next ^ 0x3DU", "next / 0U"))
            refused_guest = Path(scratch) / "fibonacci-three-unsupported.malbolge"
            refused = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/conditional-fibonacci-three-unsupported-v1",
                    "--capsule",
                    "--output",
                    str(refused_guest),
                    str(altered),
                ],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(refused_guest.exists())

    def test_four_iteration_masked_fibonacci_emits_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        self.assertIn("putchar((int)next);", original)
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(4):
            following = (previous + current) & 255
            expected.append(following ^ (26 if following % 2 == 0 else 61))
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes((24, 62, 56, 18)))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-four-masked.c"
            source.write_text(
                original.replace("i < 12U", "i < 4U")
                .replace("putchar((int)next);", "putchar((int)(next ^ 26U));")
                .replace("next ^ 0x5AU", "next ^ 61U")
            )
            guest = Path(scratch) / "fibonacci-four-masked.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/conditional-fibonacci-four-masked-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, bytes(expected))
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            # An unsupported C effect may not inherit the source witness.
            altered = Path(scratch) / "fibonacci-four-unsupported.c"
            altered.write_text(source.read_text().replace("next ^ 61U", "next / 0U"))
            refused_guest = Path(scratch) / "fibonacci-four-unsupported.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(refused_guest), str(altered)],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(refused_guest.exists())

    def test_unmodified_fibonacci_four_byte_prefix_still_refuses(self) -> None:
        """The P0 original output prefix still lacks a verified guest."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "original-fibonacci-prefix.c"
            source.write_text(original.replace("i < 12U", "i < 4U"))
            guest = Path(scratch) / "original-fibonacci-prefix.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/original-fibonacci-prefix-four-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"Layout(UnsupportedEffectTrace)", compiled.stderr)
            self.assertFalse(guest.exists(), "unwitnessed program published a guest")

    def test_zero_prefix_conditional_loop_reaches_guest(self) -> None:
        """Real guest output may precede data relocation without host I/O."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_zero_prefix_conditional_stream.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(4):
            following = (previous + current) & 255
            if following % 2 == 0:
                expected.append(0 if following == 2 else 63)
            else:
                expected.append(84 if following == 3 else 178)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("0054b23f"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "zero-prefix.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/zero-prefix-conditional-stream-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            altered = Path(scratch) / "zero-prefix-unsupported.c"
            original = source.read_text()
            self.assertIn("next == 3U", original)
            altered.write_text(original.replace("next == 3U", "next++ == 3U"))
            refused_guest = Path(scratch) / "zero-prefix-unsupported.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(refused_guest), str(altered)],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(refused_guest.exists())

    def test_wrapping_unsigned_recurrence_four_outputs_reach_guest(self) -> None:
        """Source C's unsigned +, - and * wrap at 32 bits before masking."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_wrapping_recurrence_stream.c"
        )
        original = source.read_text()
        self.assertIn("(0U - (a + b)) * 255U", original)
        self.assertIn("(~next + 1U) + (next * 2U)", original)
        a, b = 1, 1
        expected = bytearray()
        for _ in range(4):
            following = a + b
            negated = (0 - following) & 0xFFFF_FFFF
            multiplied = negated * 255
            next_value = (multiplied & 0xFFFF_FFFF) & 255
            complement = ((~next_value) + 1) & 0xFFFF_FFFF
            sum_value = complement + (next_value * 2)
            restored = (sum_value & 0xFFFF_FFFF) & 255
            self.assertGreater(negated, 255)
            self.assertGreater(multiplied, 0xFFFF_FFFF)
            self.assertGreater(sum_value, 0xFFFF_FFFF)
            self.assertEqual((next_value, restored), (following, following))
            expected.append(
                ((restored * 29 + 251) & 255)
                if restored % 2 == 0
                else (((restored // 2) * 73 + 119) & 255)
            )
            a, b = b, restored
        self.assertEqual(bytes(expected), bytes.fromhex("35c009e3"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "wrapping-recurrence.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/unsigned-wrapping-four-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for data in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=data,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            for label, changed in {
                "unmasked-wide-local": original.replace(
                    "unsigned next = ((0U - (a + b)) * 255U) & 255U;",
                    "unsigned next = ((0U - (a + b)) * 255U);",
                ),
                "undefined-divisor": original.replace(
                    "restored / 2U", "restored / 0U"
                ),
                "side-effect": original.replace(
                    "(restored & 1U)", "(restored++ & 1U)"
                ),
                "unproven-signed-cast": original.replace(
                    "~next + 1U", "~(int)next + 1U"
                ),
            }.items():
                altered = Path(scratch) / f"wrapping-invalid-{label}.c"
                _ = altered.write_text(changed)
                refused_guest = altered.with_suffix(".malbolge")
                refused = subprocess.run(
                    [*command[:-2], str(refused_guest), str(altered)],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(refused_guest.exists(), label)

    def test_wide_conditional_loop_four_outputs_reach_guest(self) -> None:
        """Divide/multiply/mask in C, then prove four real guest bytes."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(4):
            following = (previous + current) & 255
            expected.append(
                ((following * 29 + 251) & 255)
                if following % 2 == 0
                else (((following // 2) * 73 + 119) & 255)
            )
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("35c009e3"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "wide-loop.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/wide-fibonacci-guest-four-v1",
                "--capsule",
                "--output",
                str(guest),
                str(WIDE_STREAM),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            unsupported = Path(scratch) / "wide-loop-divide-zero.c"
            unsupported.write_text(
                WIDE_STREAM.read_text().replace("next / 2U", "next / 0U")
            )
            refused_guest = Path(scratch) / "wide-loop-divide-zero.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(refused_guest), str(unsupported)],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(refused_guest.exists())

    def test_branch_selected_output_inside_bounded_loop_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = LOOP_OUTPUT.read_text()
        self.assertIn("i < 12U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for bound in (12, 7):
                # Independent unsigned C state, predicate and call sequence.
                previous, current = 1, 1
                expected = bytearray()
                for _ in range(bound):
                    following = (previous + current) & 255
                    expected.append(
                        (following ^ following)
                        if following & 1 == 0
                        else (following - following)
                    )
                    previous, current = current, following
                source = Path(scratch) / f"loop-{bound}.c"
                _written = source.write_text(
                    original.replace("i < 12U", f"i < {bound}U")
                )
                guest = Path(scratch) / f"loop-{bound}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/loop-branch-{bound}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(source),
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
                self.assertEqual(executed.stdout, bytes(expected))
                self.assertEqual(
                    executed.stderr,
                    f"malbolge-steps-v1:{bound + 1}\n".encode(),
                )

    def test_repeated_conditional_loop_output_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_repeated_output.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(3):
            following = (previous + current) & 255
            expected.append(following ^ (58 if following % 2 == 0 else 59))
            previous, current = current, following
        self.assertEqual(bytes(expected), b"88>")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "repeated-loop.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/loop-repeated-output-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            execution = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(execution.returncode, 0, execution.stderr)
            self.assertEqual(execution.stdout, bytes(expected))
            self.assertRegex(execution.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            # Shifts lie outside the source-proven arithmetic slice;
            # a modified program must not inherit the valid guest witness.
            mutated = Path(scratch) / "repeated-mutation.c"
            mutated.write_text(source.read_text().replace("next ^ 58U", "next >> 1U"))
            rejected = Path(scratch) / "repeated-mutation.malbolge"
            refused = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/loop-repeated-mutation-v1",
                    "--capsule",
                    "--output",
                    str(rejected),
                    str(mutated),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(rejected.exists())

    def test_nonadjacent_equal_loop_bytes_reach_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_nonadjacent_output.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for index in range(3):
            following = (previous + current) & 255
            expected.append((following - following) + (90 if index % 2 == 0 else 37))
            previous, current = current, following
        self.assertEqual(bytes(expected), b"Z%Z")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "nonadjacent-loop.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/loop-nonadjacent-output-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            execution = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(execution.returncode, 0, execution.stderr)
            self.assertEqual(execution.stdout, bytes(expected))
            self.assertRegex(
                execution.stderr,
                rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
            )
            # An unsupported effect must not inherit the verified guest.
            mutated = Path(scratch) / "nonadjacent-mutation.c"
            mutated.write_text(
                source.read_text().replace("next - next", "next >> next")
            )
            rejected = Path(scratch) / "nonadjacent-mutation.malbolge"
            refused = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/loop-nonadjacent-mutation-v1",
                    "--capsule",
                    "--output",
                    str(rejected),
                    str(mutated),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(rejected.exists())

    def test_three_source_effects_with_identical_bytes_reach_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_nonadjacent_output.c"
        ).read_text()
        self.assertIn("+ 90U", original)
        self.assertIn("+ 37U", original)
        # Three source-evaluated loop outputs, from both branches, converge.
        a, b = 1, 1
        expected = bytearray()
        for _ in range(3):
            next_value = (a + b) & 255
            expected.append((next_value - next_value) + 56)
            a, b = b, next_value
        self.assertEqual(bytes(expected), b"888")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "three-equal-loop.c"
            source.write_text(
                original.replace("+ 90U", "+ 56U").replace("+ 37U", "+ 56U")
            )
            guest = Path(scratch) / "three-equal-loop.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/three-equal-loop-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for input_bytes in (b"", bytes((255, 0, 128))):
                execution = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=input_bytes,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(execution.returncode, 0, execution.stderr)
                self.assertEqual(execution.stdout, expected)
                self.assertRegex(
                    execution.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )
            mutated = Path(scratch) / "three-equal-mutation.c"
            mutated.write_text(
                source.read_text().replace("next - next", "next >> next")
            )
            rejected = Path(scratch) / "three-equal-mutation.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(rejected), str(mutated)],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(rejected.exists())

    def test_separate_branch_effects_with_equal_bytes_reach_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        self.assertIn("next ^ 83U", original)
        self.assertIn("next ^ 45U", original)
        # Two different C branches and source SSA values converge on 0x38.
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(2):
            following = (previous + current) & 255
            expected.append(following ^ (58 if following % 2 == 0 else 59))
            previous, current = current, following
        self.assertEqual(bytes(expected), b"88")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "equal-branch-loop.c"
            source.write_text(
                original.replace("next ^ 83U", "next ^ 58U").replace(
                    "next ^ 45U", "next ^ 59U"
                )
            )
            guest = Path(scratch) / "equal-branch-loop.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/equal-branch-loop-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            execution = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(execution.returncode, 0, execution.stderr)
            self.assertEqual(execution.stdout, bytes(expected))
            self.assertRegex(execution.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            mutation = Path(scratch) / "unsupported-equal-branch.c"
            mutation.write_text(source.read_text().replace("next ^ 59U", "next >> 1U"))
            rejected = Path(scratch) / "unsupported-equal-branch.malbolge"
            refused = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/equal-branch-mutation-v1",
                    "--capsule",
                    "--output",
                    str(rejected),
                    str(mutation),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(rejected.exists())

    def test_distinct_conditional_loop_outputs_reach_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(2):
            following = (previous + current) & 255
            expected.append(following ^ (83 if following % 2 == 0 else 45))
            previous, current = current, following
        self.assertEqual(bytes(expected), b"Q.")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "branch-stream.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/loop-distinct-output-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
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
            self.assertEqual(executed.stdout, bytes(expected))
            self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_other_source_proven_loop_pair_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        self.assertIn("next ^ 83U", original)
        self.assertIn("next ^ 45U", original)
        # Independent Fibonacci C arithmetic: 2 ^ 0 = 2, 3 ^ 204 = 207.
        expected = bytes((2, 207))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            changed = Path(scratch) / "other-loop-pair.c"
            _written = changed.write_text(
                original.replace("next ^ 83U", "next ^ 0U").replace(
                    "next ^ 45U", "next ^ 204U"
                )
            )
            guest = Path(scratch) / "other-loop-pair.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/other-loop-pair-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(changed),
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
            self.assertEqual(executed.stdout, expected)
            self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_original_fibonacci_prefix_with_composed_guest_arithmetic(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        self.assertIn("next ^ 0x5AU", original)
        # The first original value is 2; the odd branch selects 3 ^ 54 = 53.
        expected = bytes((2, 53))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            changed = Path(scratch) / "fib-composed-pair.c"
            _written = changed.write_text(
                original.replace("i < 12U", "i < 2U").replace(
                    "next ^ 0x5AU", "next ^ 54U"
                )
            )
            guest = Path(scratch) / "fib-composed-pair.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/fib-composed-pair-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(changed),
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
            self.assertEqual(executed.stdout, expected)
            self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_unwitnessed_distinct_loop_stream_does_not_publish_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        self.assertIn("next ^ 83U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            changed = Path(scratch) / "unwitnessed-loop.c"
            _written = changed.write_text(original.replace("next ^ 83U", "next ^ 82U"))
            guest = Path(scratch) / "unwitnessed-loop.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/unwitnessed-loop-distinct-output-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(changed),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(
                b"canonical typed byte bridge rejected: Layout(UnsupportedEffectTrace)",
                compiled.stderr,
            )
            self.assertNotIn(b"normalized frontend rejected", compiled.stderr)
            self.assertFalse(guest.exists())

    def test_nonzero_conditional_loop_stream_does_not_publish_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = LOOP_OUTPUT.read_text()
        self.assertIn("next - next", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "nonzero-loop.c"
            _written = source.write_text(original.replace("next - next", "next ^ 1U"))
            guest = Path(scratch) / "nonzero.malbolge"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/unsupported-loop-stream-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"Unsupported", result.stderr)
            self.assertFalse(guest.exists())

    def test_unsupported_shift_rejects_guest_artifact(self) -> None:
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
                    "    value = value >> 2U;\n    putchar(value);",
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

    def test_masked_wide_sum_branch_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_masked_sum_output.c"
        original = source.read_text()
        self.assertIn("unsigned a = 233U;", original)
        self.assertIn("next = next ^ 3U;", original)
        # 377 and 376 exceed a byte before C's unsigned AND mask.
        cases = (
            (original, ((233 + 144) & 255) ^ 56, 31),
            (
                original.replace("unsigned a = 233U;", "unsigned a = 232U;").replace(
                    "next = next ^ 3U;", "next = next ^ 58U;"
                ),
                ((232 + 144) & 255) ^ 58,
                69,
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for index, (text, expected, steps) in enumerate(cases):
                altered = Path(scratch) / f"masked-{index}.c"
                _written = altered.write_text(text)
                guest = Path(scratch) / f"masked-{index}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/masked-sum-{index}-v1",
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
                self.assertTrue(guest.is_file())
                executed = subprocess.run(
                    [str(VM), str(guest), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, bytes([expected]))
                self.assertEqual(
                    executed.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                )

    def test_source_proven_static_loop_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_static_loop_output.c"
        original = source.read_text()
        self.assertIn("for (unsigned i = 0U; i < 8U; ++i)", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for iterations, mask in ((8, 107), (7, 91)):
                altered = Path(scratch) / f"loop-{iterations}.c"
                text = original.replace("i < 8U", f"i < {iterations}U").replace(
                    "b ^ 107U", f"b ^ {mask}U"
                )
                _written = altered.write_text(text)
                # Independent, finite unsigned-C oracle, not a compiler trace.
                a, b = 1, 1
                for _ in range(iterations):
                    next_value = (a + b) & 255
                    next_value ^= 0 if next_value % 2 == 0 else 1
                    a, b = b, next_value
                expected = b ^ mask
                self.assertEqual(expected, 65)
                guest = Path(scratch) / f"loop-{iterations}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/static-loop-{iterations}-v1",
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
                self.assertTrue(guest.is_file())
                execution = subprocess.run(
                    [str(VM), str(guest), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(execution.returncode, 0, execution.stderr)
                self.assertEqual(execution.stdout, bytes([expected]))
                self.assertEqual(execution.stderr, b"malbolge-steps-v1:31\n")

            for index, changed in enumerate(
                (
                    original.replace("i < 8U", "i < 13U"),
                    original.replace("++i", "--i"),
                    original.replace(
                        "        a = b;", "        i = i + 1U;\n        a = b;"
                    ),
                    original.replace(
                        "        a = b;", "        putchar(65);\n        a = b;"
                    ),
                )
            ):
                altered = Path(scratch) / f"unsupported-loop-{index}.c"
                _written = altered.write_text(changed)
                guest = Path(scratch) / f"unsupported-loop-{index}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/unsupported-static-loop-{index}-v1",
                        "--output",
                        str(guest),
                        str(altered),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=60,
                )
                self.assertNotEqual(compiled.returncode, 0)
                self.assertIn(b"Unsupported", compiled.stderr)
                self.assertFalse(guest.exists())

    def test_unmasked_wide_sum_and_shift_refuse_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_masked_sum_output.c"
        original = source.read_text()
        pattern = "unsigned next = (a + b) & 255U;"
        self.assertIn(pattern, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for index, changed in enumerate(
                ("unsigned next = (a + b);", "unsigned next = (a >> b) & 255U;")
            ):
                altered = Path(scratch) / f"unsupported-{index}.c"
                _written = altered.write_text(original.replace(pattern, changed))
                guest = Path(scratch) / f"unsupported-{index}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/unsupported-masked-{index}-v1",
                        "--output",
                        str(guest),
                        "--capsule",
                        str(altered),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(compiled.returncode, 0)
                self.assertIn(b"Unsupported", compiled.stderr)
                self.assertFalse(guest.exists())

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
                "putchar((int)(result >> 1U));",
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

    def test_checked_remainder_recurrence_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_remainder_recurrence_output.c"
        )
        a, b = 3, 5
        observed = []
        for _ in range(3):
            next_value = (a * b) & 255
            observed.append(next_value)
            a = (next_value % 17) ^ 1 if next_value % 2 == 0 else next_value - 1
            b = next_value
        self.assertEqual(observed, [15, 210, 190])
        self.assertEqual(a, 2)
        self.assertEqual(a ^ 67, 65)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "remainder-recurrence.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/local-remainder-recurrence-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=90
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for data in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=data,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            original = source.read_text()
            invalid = {
                "zero-divisor": original.replace("next % 17U", "next % 0U"),
                "shift": original.replace("next % 17U", "next >> 1U"),
            }
            for label, changed in invalid.items():
                altered = Path(scratch) / f"{label}-remainder.c"
                altered.write_text(changed)
                rejected = Path(scratch) / f"{label}-remainder.malbolge"
                refused = subprocess.run(
                    [*command[:-2], str(rejected), str(altered)],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertFalse(rejected.exists())

    def test_unsigned_or_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_or_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("((a * b) | 16U) & 255U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for mask, xor_key, visited, final in (
                (16, 66, [31, 248, 16], 3),
                (8, 83, [15, 120, 152], 18),
            ):
                a, b = 3, 5
                actual = []
                for _ in range(3):
                    next_value = ((a * b) | mask) & 255
                    actual.append(next_value)
                    a = (
                        ((next_value >> 3) ^ 1)
                        if (next_value & 1) == 0
                        else next_value ^ 7
                    )
                    b = next_value
                self.assertEqual(actual, visited)
                self.assertEqual(a, final)
                self.assertEqual(a ^ xor_key, 65)
                changed = original.replace("| 16U", f"| {mask}U").replace(
                    "a ^ 66U", f"a ^ {xor_key}U"
                )
                candidate = Path(scratch) / f"or-mask-{mask}.c"
                candidate.write_text(changed)
                guest = Path(scratch) / f"or-mask-{mask}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/local-or-recurrence-{mask}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, (mask, compiled.stderr))
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [
                            str(VM),
                            str(guest),
                            "--input-stdin",
                            "--report-steps",
                        ],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A")
                    self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            for label, changed in {
                "logical-or": original.replace("| 16U", "|| 16U"),
                "unmasked-wide-state": original.replace(" & 255U", ""),
                "side-effect-read": original.replace("a * b", "a * b++"),
            }.items():
                invalid = Path(scratch) / f"{label}.c"
                invalid.write_text(changed)
                guest = Path(scratch) / f"{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/local-or-{label}-invalid-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(invalid),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_relational_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_relational_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("(next & 8U) < 8U", original)
        relations = {
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
            "!=": lambda a, b: a != b,
            "==": lambda a, b: a == b,
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for operator, threshold, expected_branches in (
                ("<", 8, [False, True, True]),
                ("<=", 7, [False, True, True]),
                (">", 7, [True, False, False]),
                (">=", 8, [True, False, False]),
                ("!=", 8, [False, True, True]),
                ("==", 0, [False, True, True]),
            ):
                a, b = 3, 5
                branches = []
                for _ in range(3):
                    next_value = ((a * b) << 2) & 255
                    selected = relations[operator](next_value & 8, threshold)
                    branches.append(selected)
                    a = ((next_value >> 3) ^ 1) if selected else next_value - 1
                    b = next_value
                self.assertEqual(branches, expected_branches)
                self.assertLessEqual(a, 255)
                xor_key = a ^ 65
                changed = original.replace(
                    "(next & 8U) < 8U",
                    f"(next & 8U) {operator} {threshold}U",
                ).replace("a ^ 88U", f"a ^ {xor_key}U")
                relation_name = {
                    "<": "lt",
                    "<=": "le",
                    ">": "gt",
                    ">=": "ge",
                    "!=": "ne",
                    "==": "eq",
                }[operator]
                candidate = Path(scratch) / f"relational-{relation_name}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                command = [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    f"tests/local-relational-{relation_name}-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ]
                compiled = subprocess.run(
                    command, check=False, capture_output=True, timeout=90
                )
                self.assertEqual(compiled.returncode, 0, (operator, compiled.stderr))
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A")
                    self.assertRegex(
                        executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                    )
            for label, changed in {
                "logical-and": original.replace("< 8U", "&& 8U"),
                "increment-side-effect": original.replace(
                    "(next & 8U)", "(next++ & 8U)"
                ),
                "signed-conversion": original.replace(
                    "(next & 8U) < 8U", "((int)(next & 8U)) < 8"
                ),
            }.items():
                candidate = Path(scratch) / f"invalid-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/local-relational-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_pure_logical_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_logical_recurrence_output.c"
        )
        original = source.read_text()
        condition = "((next & 8U) < 8U) && ((b & 4U) != 0U)"
        self.assertIn(condition, original)
        variants = (
            ("and", condition, [False, True, False]),
            (
                "or",
                "((next & 8U) < 8U) || ((b & 4U) == 0U)",
                [False, True, True],
            ),
            (
                "mixed",
                "(" + condition + ") || ((next & 16U) == 16U)",
                [True, True, False],
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, replacement, expected_branches in variants:
                a, b = 3, 5
                branches = []
                for _ in range(3):
                    next_value = ((a * b) << 2) & 255
                    left = (next_value & 8) < 8
                    right = (b & 4) != 0
                    if label == "and":
                        selected = left and right
                    elif label == "or":
                        selected = left or not right
                    else:
                        selected = (left and right) or (next_value & 16) == 16
                    branches.append(selected)
                    a = ((next_value >> 3) ^ 1) if selected else next_value - 1
                    b = next_value
                self.assertEqual(branches, expected_branches, label)
                self.assertLessEqual(a, 255)
                changed = original.replace(condition, replacement).replace(
                    "a ^ 254U", f"a ^ {a ^ 65}U"
                )
                candidate = Path(scratch) / f"logical-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/logical-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(
                    compiled.returncode, 0, (label, compiled.stderr)
                )
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [
                            str(VM),
                            str(guest),
                            "--input-stdin",
                            "--report-steps",
                        ],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A", label)
                    self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            for label, changed in {
                "side-effect-in-right-operand": original.replace("b & 4U", "b++ & 4U"),
                "unsupported-bitwise-combine": original.replace(" && ", " & "),
                "unsupported-call-in-right-operand": original.replace(
                    "(b & 4U) != 0U", "(putchar(70) & 4U) != 0U"
                ),
            }.items():
                candidate = Path(scratch) / f"invalid-logical-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/logical-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_truthy_conditions_reach_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_truthy_condition_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("if ((next & 8U))", original)
        variants = (
            ("masked", "(next & 8U)", [True, False, False]),
            ("bare", "next", [True, True, True]),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, condition, expected_branches in variants:
                a, b = 3, 5
                branches = []
                for _ in range(3):
                    next_value = ((a * b) << 2) & 255
                    selected = (
                        (next_value & 8) != 0
                        if label == "masked"
                        else next_value != 0
                    )
                    branches.append(selected)
                    a = ((next_value >> 3) ^ 1) if selected else next_value - 1
                    b = next_value
                self.assertEqual(branches, expected_branches, label)
                self.assertLessEqual(a, 255)
                changed = original.replace("(next & 8U)", condition, 1).replace(
                    "a ^ 62U", f"a ^ {a ^ 65}U"
                )
                candidate = Path(scratch) / f"truthy-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/truthy-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, (label, compiled.stderr))
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A", label)
                    self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            for label, changed in {
                "increment": original.replace("next & 8U", "next++ & 8U", 1),
                "impure-call": original.replace(
                    "next & 8U", "putchar(70) & 8U", 1
                ),
                "undefined-divisor": original.replace(
                    "next & 8U", "(next & 8U) / 0U", 1
                ),
                "signed-cast": original.replace(
                    "if ((next & 8U))", "if ((int)(next & 8U))", 1
                ),
            }.items():
                candidate = Path(scratch) / f"invalid-truthy-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/truthy-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_truthy_ast_mutations_refuse_publication(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_truthy_condition_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/truthy-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        branch = next(node for node in nodes if node["kind"] == "if-statement")
        grouped = next(
            node
            for node in nodes
            if node["parent"] == branch["id"]
            and node["kind"] == "parenthesized-expression"
        )
        condition = next(
            node
            for node in nodes
            if node["parent"] == grouped["id"]
            and node["kind"] == "binary-expression"
            and node.get("operation") == "&"
        )
        condition_id = cast(int, condition["id"])
        self.assertIsInstance(condition_id, int)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, field, value in (
                ("operator", "operation", "||"),
                ("type", "type", "i32"),
                ("parent", "parent", 0),
                ("literal", "literal", "1"),
            ):
                tampered = cast(dict[str, object], json.loads(frontend.stdout))
                changed_nodes = cast(list[dict[str, object]], tampered["nodes"])
                changed_nodes[condition_id - 1][field] = value
                guest = Path(scratch) / f"invalid-truthy-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_negated_logical_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_negated_logical_recurrence_output.c"
        )
        original = source.read_text()
        condition = "!(((next & 8U) >= 8U) && ((b & 4U) != 0U))"
        self.assertIn(condition, original)
        variants = (
            ("negated-and", condition, [False, True, True]),
            (
                "double-negation",
                "!!(((next & 8U) < 8U) && ((b & 4U) != 0U))",
                [False, True, False],
            ),
            (
                "nested-not",
                "!(((next & 8U) >= 8U) || !((b & 4U) != 0U))",
                [False, True, False],
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, replacement, expected_branches in variants:
                a, b = 3, 5
                branches = []
                for _ in range(3):
                    next_value = ((a * b) << 2) & 255
                    left = (next_value & 8) >= 8
                    right = (b & 4) != 0
                    if label == "negated-and":
                        selected = not (left and right)
                    elif label == "double-negation":
                        selected = (not left) and right
                    else:
                        selected = not (left or (not right))
                    branches.append(selected)
                    a = ((next_value >> 3) ^ 1) if selected else next_value - 1
                    b = next_value
                self.assertEqual(branches, expected_branches, label)
                self.assertLessEqual(a, 255)
                changed = original.replace(condition, replacement).replace(
                    "a ^ 88U", f"a ^ {a ^ 65}U"
                )
                candidate = Path(scratch) / f"negated-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/negated-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, (label, compiled.stderr))
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A", label)
                    self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            for label, changed in {
                "increment": original.replace("b & 4U", "b++ & 4U"),
                "impure-call": original.replace(
                    "(b & 4U) != 0U", "(putchar(70) & 4U) != 0U"
                ),
                "bitwise-complement": original.replace("if (!(", "if (~(", 1),
            }.items():
                candidate = Path(scratch) / f"rejected-negated-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/negated-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_complement_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_complement_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("(~next) & 255U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, variant, xor_key, trace in (
                (
                    "single",
                    original,
                    88,
                    [(60, True, 195), (208, False, 27), (192, False, 25)],
                ),
                (
                    "double",
                    original.replace("~next", "~~next").replace("^ 88U", "^ 64U"),
                    64,
                    [(60, True, 60), (64, False, 9), (0, False, 1)],
                ),
            ):
                a, b = 3, 5
                observed: list[tuple[int, bool, int]] = []
                for _ in range(3):
                    following = ((a * b) << 2) & 255
                    take_then = (following & 8) != 0
                    if take_then:
                        complement = (~following) & 0xFFFF_FFFF
                        if label == "double":
                            complement = (~complement) & 0xFFFF_FFFF
                        a = complement & 255
                    else:
                        a = (following >> 3) ^ 1
                    b = following
                    observed.append((following, take_then, a))
                self.assertEqual(observed, trace)
                self.assertEqual(a ^ xor_key, 65)
                candidate = Path(scratch) / f"complement-{label}.c"
                _ = candidate.write_text(variant)
                guest = candidate.with_suffix(".malbolge")
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/complement-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest.is_file())
                for guest_input in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A")
                    self.assertRegex(
                        executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                    )

            for label, changed in {
                "increment": original.replace("~next", "~next++"),
                "assignment": original.replace("~next", "~(next += 1U)"),
                "undefined": original.replace("~next", "~(next / (b - b))"),
                "signed": original.replace("~next", "~(int)next"),
                "unsupported-minus": original.replace("~next", "-next"),
            }.items():
                candidate = Path(scratch) / f"invalid-complement-{label}.c"
                _ = candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/complement-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_complement_ast_mutations_fail_closed(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_complement_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/complement-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        unary = [
            node
            for node in nodes
            if node["kind"] == "unary-expression" and node.get("operation") == "~"
        ]
        self.assertEqual(len(unary), 1)
        expression = unary[0]
        expression_id = expression["id"]
        self.assertIsInstance(expression_id, int)
        operands = [node for node in nodes if node["parent"] == expression_id]
        self.assertEqual(len(operands), 1)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("operation", expression_id, "operation", "-"),
                ("result-type", expression_id, "type", "i32"),
                ("foreign-parent", expression_id, "parent", 0),
                ("extra-metadata", expression_id, "literal", "0"),
                ("operand-kind", operands[0]["id"], "kind", "call-expression"),
                ("operand-type", operands[0]["id"], "type", "i32"),
            ):
                assert isinstance(node_id, int)
                tampered = cast(dict[str, object], json.loads(frontend.stdout))
                changed_nodes = cast(list[dict[str, object]], tampered["nodes"])
                changed_nodes[node_id - 1][field] = value
                guest = Path(scratch) / f"invalid-complement-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_conditional_expression_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_conditional_expression_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("(next & 8U) != 0U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            a, b = 3, 5
            branches: list[bool] = []
            for _ in range(3):
                following = ((a * b) << 2) & 255
                take_then = (following & 8) != 0
                branches.append(take_then)
                a = ((following >> 3) ^ 1) if take_then else following - 1
                b = following
            self.assertEqual(branches, [True, False, False])
            self.assertEqual(a, 127)
            self.assertEqual(a ^ 62, 65)
            guest = Path(scratch) / "conditional.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/conditional-expression-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            for label, changed in {
                "impure-condition": original.replace("next & 8U", "next++ & 8U"),
                "impure-unselected-arm": original.replace("next - 1U", "next++ - 1U"),
                "undefined-unselected-arm": original.replace(
                    "next - 1U", "next / (b - b)"
                ),
                "unsupported-unsigned-arm": original.replace(
                    "next - 1U", "(unsigned)(next > 1U)"
                ),
            }.items():
                candidate = Path(scratch) / f"invalid-conditional-{label}.c"
                _ = candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/conditional-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_conditional_expression_ast_mutations_fail_closed(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_conditional_expression_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/conditional-ast-mutation-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        nodes = cast(list[dict[str, object]], json.loads(frontend.stdout)["nodes"])
        conditional = [
            node for node in nodes if node["kind"] == "conditional-expression"
        ]
        self.assertEqual(len(conditional), 1)
        expression = conditional[0]
        expression_id = expression["id"]
        self.assertIsInstance(expression_id, int)
        arms = [node for node in nodes if node["parent"] == expression_id]
        self.assertEqual(len(arms), 3)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("conditional-type", expression_id, "type", "i32"),
                ("conditional-operation", expression_id, "operation", "!"),
                ("condition-parent", arms[0]["id"], "parent", 0),
                ("true-arm-kind", arms[1]["id"], "kind", "call-expression"),
                ("false-arm-type", arms[2]["id"], "type", "i32"),
            ):
                assert isinstance(node_id, int)
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                tampered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"conditional-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_computed_unsigned_comparison_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_computed_condition_recurrence_output.c"
        )
        original = source.read_text()
        comparison = "((next & 31U) + (a & 7U)) >= ((b ^ 2U) + 3U)"
        self.assertIn(comparison, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, operator, expected_branches in (
                ("greater-equal", ">=", [True, False, False]),
                ("less-than", "<", [False, True, True]),
            ):
                a, b = 3, 5
                branches = []
                for _ in range(3):
                    following = ((a * b) << 2) & 255
                    lhs = (following & 31) + (a & 7)
                    rhs = (b ^ 2) + 3
                    take_then = lhs >= rhs if operator == ">=" else lhs < rhs
                    branches.append(take_then)
                    a = ((following >> 3) ^ 1) if take_then else following - 1
                    b = following
                self.assertEqual(branches, expected_branches, label)
                self.assertLessEqual(a, 255)
                variant = original.replace(
                    comparison,
                    comparison.replace(">=", operator),
                ).replace("a ^ 62U", f"a ^ {a ^ 65}U")
                candidate = Path(scratch) / f"computed-{label}.c"
                _written = candidate.write_text(variant)
                guest = candidate.with_suffix(".malbolge")
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/computed-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, (label, compiled.stderr))
                self.assertTrue(guest.is_file())
                for guest_input in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A", label)
                    self.assertRegex(
                        executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                    )
            for label, changed in {
                "impure-left": original.replace("a & 7U", "a++ & 7U"),
                "undefined-right": original.replace(
                    "(b ^ 2U) + 3U", "(b ^ 2U) / (b - b)"
                ),
                "logical-condition": original.replace(">= ((b", "|| ((b"),
            }.items():
                candidate = Path(scratch) / f"rejected-computed-{label}.c"
                _written = candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/computed-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_computed_unsigned_comparison_ast_mutations_fail_closed(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_computed_condition_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/computed-ast-mutation-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        canonical = json.loads(frontend.stdout)
        comparisons = [
            node
            for node in canonical["nodes"]
            if node["kind"] == "binary-expression" and node.get("operation") == ">="
        ]
        self.assertEqual(len(comparisons), 1)
        comparison = comparisons[0]
        right = next(
            node
            for node in canonical["nodes"]
            if node["parent"] == comparison["id"]
            and node["kind"] == "parenthesized-expression"
            and node["span"]["begin"]["byte"] > comparison["span"]["begin"]["byte"]
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, field, value in (
                ("bad-rhs-type", "type", "i32"),
                ("bad-rhs-parent", "parent", 0),
                ("bad-rhs-kind", "kind", "call-expression"),
            ):
                tampered = json.loads(frontend.stdout)
                tampered["nodes"][right["id"] - 1][field] = value
                guest = Path(scratch) / f"computed-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_negated_logical_ast_mutations_refuse_publication(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_negated_logical_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/negated-ast-mutations-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        normalized = json.loads(frontend.stdout)
        unary_positions = [
            index
            for index, node in enumerate(normalized["nodes"])
            if node["kind"] == "unary-expression" and node.get("operation") == "!"
        ]
        self.assertEqual(len(unary_positions), 1)
        index = unary_positions[0]
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, field, value in (
                ("wrong-operation", "operation", "~"),
                ("wrong-type", "type", "u32"),
                ("wrong-parent", "parent", 0),
                ("wrong-kind", "kind", "binary-expression"),
            ):
                altered = json.loads(frontend.stdout)
                altered["nodes"][index][field] = value
                guest = Path(scratch) / f"rejected-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(altered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_unsigned_shift_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_shift_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("((a * b) << 2U) & 255U", original)
        self.assertIn("(next >> 3U) ^ 1U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for left_shift, right_shift, xor_key, visited, final in (
                (2, 3, 88, [60, 80, 192], 25),
                (0, 0, 86, [15, 210, 22], 23),
                (31, 3, 64, [0, 0, 0], 1),
            ):
                a, b = 3, 5
                actual_visited = []
                for _ in range(3):
                    # C unsigned left shift reduces modulo 2**32, then masks.
                    next_value = ((a * b) << left_shift) & 0xFFFFFFFF & 255
                    actual_visited.append(next_value)
                    a = (
                        ((next_value >> right_shift) ^ 1)
                        if (next_value & 8) == 0
                        else next_value - 1
                    )
                    b = next_value
                self.assertEqual(actual_visited, visited)
                self.assertEqual(a, final)
                self.assertEqual(a ^ xor_key, 65)
                changed = (
                    original.replace("<< 2U", f"<< {left_shift}U")
                    .replace(">> 3U", f">> {right_shift}U")
                    .replace("a ^ 88U", f"a ^ {xor_key}U")
                    # Both conditional arms must produce byte-sized local
                    # stores, including the unselected unsigned underflow.
                    .replace(
                        "next - 1U",
                        "next + 1U" if left_shift == 31 else "next - 1U",
                    )
                )
                candidate = Path(scratch) / f"shift-{left_shift}-{right_shift}.c"
                candidate.write_text(changed)
                guest = Path(scratch) / f"shift-{left_shift}-{right_shift}.malbolge"
                command = [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    f"tests/local-shift-recurrence-{left_shift}-{right_shift}-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ]
                compiled = subprocess.run(
                    command, check=False, capture_output=True, timeout=90
                )
                self.assertEqual(
                    compiled.returncode,
                    0,
                    (left_shift, right_shift, compiled.stderr),
                )
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    execution = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(execution.returncode, 0, execution.stderr)
                    self.assertEqual(execution.stdout, b"A")
                    self.assertEqual(execution.stderr, b"malbolge-steps-v1:31\n")
            for label, changed in {
                "left-count-32": original.replace("<< 2U", "<< 32U"),
                "right-count-32": original.replace(">> 3U", ">> 32U"),
                "unsupported-logical-and": original.replace("next - 1U", "next && 1U"),
            }.items():
                invalid = Path(scratch) / f"{label}.c"
                invalid.write_text(changed)
                guest = Path(scratch) / f"{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/local-shift-{label}-invalid-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(invalid),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertFalse(guest.exists(), label)

    def test_checked_division_recurrence_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_division_recurrence_output.c"
        )
        a, b = 3, 5
        visited = []
        for _ in range(3):
            next_value = (a * b) & 255
            visited.append(next_value)
            a = (next_value // 17) ^ 1 if next_value % 2 == 0 else next_value - 1
            b = next_value
        self.assertEqual(visited, [15, 210, 170])
        self.assertEqual(a, 11)
        self.assertEqual(a ^ 74, 65)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "division-recurrence.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/local-division-recurrence-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=90
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for data in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=data,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            original = source.read_text()
            self.assertIn("next / 17U", original)
            invalid = {
                "zero-divisor": original.replace("next / 17U", "next / 0U"),
                "shift": original.replace("next / 17U", "next >> 1U"),
            }
            for label, changed in invalid.items():
                altered = Path(scratch) / f"{label}-division.c"
                altered.write_text(changed)
                rejected = Path(scratch) / f"{label}-division.malbolge"
                refused = subprocess.run(
                    [*command[:-2], str(rejected), str(altered)],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(rejected.exists())

    def test_checked_multiplicative_recurrence_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_multiplicative_recurrence_output.c"
        )
        a, b = 3, 5
        visited = []
        for _ in range(3):
            next_value = (a * b) & 255
            visited.append(next_value)
            a = (next_value ^ 1) if next_value % 2 == 0 else next_value - 1
            b = next_value
        self.assertEqual(visited, [15, 210, 22])
        self.assertEqual(a ^ 86, 65)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "multiply-recurrence.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/local-multiplicative-recurrence-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=90
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for data in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=data,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            original = source.read_text()
            # Unsigned arithmetic wraps, but undefined division or an
            # unproven signed cast must still refuse without a guest.
            invalid = {
                "zero-divisor": original.replace(
                    "(a * b) & 255U", "((a * b) / 0U) & 255U"
                ),
                "signed-cast": original.replace("a * b", "a * (int)b"),
            }
            for label, changed in invalid.items():
                altered = Path(scratch) / f"{label}-recurrence.c"
                altered.write_text(changed)
                rejected = Path(scratch) / f"{label}-recurrence.malbolge"
                refused = subprocess.run(
                    [*command[:-2], str(rejected), str(altered)],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(rejected.exists())

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

    def test_bounded_while_state_and_branch_stream_reach_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_while_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("while (i < 3U)", original)
        a, b = 3, 5
        taken = []
        for _ in range(3):
            following = ((a * b) << 2) & 255
            selected = (following & 8) != 0
            taken.append(selected)
            a = ((following >> 3) ^ 1) if selected else following - 1
            b = following
        self.assertEqual(taken, [True, False, False])
        self.assertEqual(a, 127)
        self.assertEqual(a ^ 62, 65)

        # The same while replay must preserve distinct selected output
        # effects, not merely a single final byte of compile-time state.
        pair_source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        self.assertIn("for (unsigned i = 0U; i < 2U; ++i)", pair_source)
        pair_source = pair_source.replace(
            "for (unsigned i = 0U; i < 2U; ++i) {",
            "unsigned i = 0U;\n    while (i < 2U) {",
        ).replace("        b = next;\n", "        b = next;\n        i = i + 1U;\n")
        previous, current = 1, 1
        expected_pair = bytearray()
        for _ in range(2):
            following = (previous + current) & 255
            expected_pair.append(following ^ (83 if following % 2 == 0 else 45))
            previous, current = current, following
        self.assertEqual(bytes(expected_pair), b"Q.")

        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            pair = Path(scratch) / "while-pair.c"
            pair.write_text(pair_source)
            for label, candidate, expected in (
                ("state", source, b"A"),
                ("stream", pair, bytes(expected_pair)),
            ):
                guest = Path(scratch) / f"while-{label}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/while-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=100,
                )
                self.assertEqual(compiled.returncode, 0, (label, compiled.stderr))
                self.assertTrue(guest.is_file(), label)
                for guest_input in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected, label)
                    self.assertRegex(
                        executed.stderr,
                        rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                    )

            for label, changed in {
                "nonterminating": original.replace("i = i + 1U", "i = i + 0U"),
                "beyond-bound": original.replace("i < 3U", "i < 13U"),
                "side-effecting-test": original.replace("i < 3U", "i++ < 3U"),
                "undefined-test": original.replace("i < 3U", "(i / 0U) < 3U"),
                "nested-loop": original.replace(
                    "i = i + 1U;", "while (i < 3U) { i = i + 1U; }"
                ),
            }.items():
                candidate = Path(scratch) / f"rejected-while-{label}.c"
                candidate.write_text(changed)
                guest = Path(scratch) / f"rejected-while-{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/while-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)

    def test_bounded_while_forged_ast_refuses_publication(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_while_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/while-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        loop = next(node for node in nodes if node["kind"] == "while-statement")
        children = [node for node in nodes if node["parent"] == loop["id"]]
        condition = next(
            node for node in children if node["kind"] == "binary-expression"
        )
        body = next(node for node in children if node["kind"] == "compound-statement")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("wrong-loop-kind", loop["id"], "kind", "for-statement"),
                ("foreign-loop-parent", loop["id"], "parent", 0),
                ("loop-extra-operation", loop["id"], "operation", "++"),
                ("condition-operation", condition["id"], "operation", ">="),
                ("condition-type", condition["id"], "type", "u32"),
                ("body-parent", body["id"], "parent", 0),
            ):
                assert isinstance(node_id, int)
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                tampered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"while-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)


    def _check_bounded_do_while_guest(self, selected_label: str) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_do_while_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("} while (i < 3U);", original)
        # Independently replay C's body-before-test semantics.
        a, b, i = 3, 5, 0
        taken = []
        while True:
            next_value = ((a * b) << 2) & 255
            branch = (next_value & 8) != 0
            taken.append(branch)
            a = ((next_value >> 3) ^ 1) if branch else next_value - 1
            b = next_value
            i += 1
            if not i < 3:
                break
        self.assertEqual(taken, [True, False, False])
        self.assertEqual(a ^ 62, 65)
        one_next = ((3 * 5) << 2) & 255
        one_a = (one_next >> 3) ^ 1
        self.assertEqual(one_a ^ 71, 65)
        pair_source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        self.assertIn("for (unsigned i = 0U; i < 2U; ++i)", pair_source)
        pair_source = (
            pair_source.replace(
                "for (unsigned i = 0U; i < 2U; ++i) {",
                "unsigned i = 0U;\n    do {",
            )
            .replace("        b = next;\n", "        b = next;\n        i = i + 1U;\n")
            .replace("    }\n}\n", "    } while (i < 2U);\n}\n")
        )
        previous, current = 1, 1
        expected_pair = bytearray()
        for _ in range(2):
            following = (previous + current) & 255
            expected_pair.append(following ^ (83 if following % 2 == 0 else 45))
            previous, current = current, following
        self.assertEqual(bytes(expected_pair), b"Q.")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed, expected in (
                ("three-trips", original, b"A"),
                ("branch-stream", pair_source, bytes(expected_pair)),
                # This test starts false, yet a do-loop executes once.
                (
                    "mandatory-first-trip",
                    original.replace("unsigned i = 0U;", "unsigned i = 3U;").replace(
                        "a ^ 62U", "a ^ 71U"
                    ),
                    b"A",
                ),
            ):
                if label != selected_label:
                    continue
                candidate = Path(scratch) / f"do-{label}.c"
                candidate.write_text(changed)
                guest = Path(scratch) / f"do-{label}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/do-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=180,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest.is_file())
                for guest_input in (b"", bytes((0, 255, 128))):
                    execution = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(execution.returncode, 0, execution.stderr)
                    self.assertEqual(execution.stdout, expected)
                    self.assertRegex(
                        execution.stderr,
                        rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                    )

    def test_bounded_do_while_three_trips_reaches_guest(self) -> None:
        self._check_bounded_do_while_guest("three-trips")

    def test_bounded_do_while_branch_stream_reaches_guest(self) -> None:
        self._check_bounded_do_while_guest("branch-stream")

    def test_bounded_do_while_mandatory_first_trip_reaches_guest(self) -> None:
        self._check_bounded_do_while_guest("mandatory-first-trip")

    def test_bounded_do_while_source_refusals(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_do_while_recurrence_output.c"
        )
        original = source.read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed in {
                "nonterminating": original.replace("i = i + 1U", "i = i + 0U"),
                "beyond-bound": original.replace("i < 3U", "i < 13U"),
                "side-effecting-test": original.replace("i < 3U", "i++ < 3U"),
                "undefined-test": original.replace("i < 3U", "(i / 0U) < 3U"),
                "nested-loop": original.replace(
                    "i = i + 1U;", "while (i < 3U) { i = i + 1U; }"
                ),
            }.items():
                candidate = Path(scratch) / f"reject-do-{label}.c"
                candidate.write_text(changed)
                guest = Path(scratch) / f"reject-do-{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/do-reject-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=45,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)

    def test_bounded_do_while_forged_ast_refuses_publication(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_do_while_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/do-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        loop = next(node for node in nodes if node["kind"] == "do-statement")
        children = [node for node in nodes if node["parent"] == loop["id"]]
        body = next(node for node in children if node["kind"] == "compound-statement")
        condition = next(
            node for node in children if node["kind"] == "binary-expression"
        )
        self.assertLess(cast(int, body["id"]), cast(int, condition["id"]))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("wrong-kind", loop["id"], "kind", "while-statement"),
                ("wrong-parent", loop["id"], "parent", 0),
                ("extra-operation", loop["id"], "operation", "++"),
                ("unsupported-condition", condition["id"], "operation", "%"),
                ("condition-type", condition["id"], "type", "u32"),
                ("body-parent", body["id"], "parent", 0),
            ):
                assert isinstance(node_id, int)
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                tampered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"do-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)


    def test_bounded_if_without_else_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_if_without_else_recurrence_output.c"
        ).read_text()
        self.assertIn("if (next & 8U) {", source)

        def oracle(mask: int, xor: int) -> tuple[bytes, list[bool]]:
            a, b, i = 3, 5, 0
            branches: list[bool] = []
            while True:
                following = ((a * b) << 2) & 255
                taken = bool(following & mask)
                branches.append(taken)
                if taken:
                    a = (following >> 3) ^ 1
                b = following
                i += 1
                if i == 3:
                    break
            return bytes((a ^ xor,)), branches

        self.assertEqual(oracle(8, 71), (b"A", [True, False, False]))
        self.assertEqual(oracle(2, 66), (b"A", [False, False, False]))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed, expected in (
                ("taken-and-skipped", source, oracle(8, 71)[0]),
                (
                    "always-skipped",
                    source.replace("next & 8U", "next & 2U").replace(
                        "a ^ 71U", "a ^ 66U"
                    ),
                    oracle(2, 66)[0],
                ),
            ):
                candidate = Path(scratch) / f"no-else-{label}.c"
                _ = candidate.write_text(changed)
                guest = Path(scratch) / f"no-else-{label}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/no-else-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=100,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest.is_file())
                for guest_input in (b"", b"\xff\x00\x80"):
                    executed = subprocess.run(
                        [
                            str(VM),
                            str(guest),
                            "--input-stdin",
                            "--report-steps",
                        ],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertRegex(
                        executed.stderr,
                        rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                    )

    def test_bounded_if_without_else_source_refusals(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_if_without_else_recurrence_output.c"
        ).read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed in {
                "extra-assignment": source.replace(
                    "a = (next >> 3U) ^ 1U;",
                    "a = (next >> 3U) ^ 1U;\n            b = 0U;",
                ),
                "hidden-effect": source.replace(
                    "a = (next >> 3U) ^ 1U;",
                    "a = (next >> 3U) ^ 1U;\n            putchar((int)next);",
                ),
                "missing-braces": source.replace(
                    "if (next & 8U) {\n"
                    + "            a = (next >> 3U) ^ 1U;\n        }",
                    "if (next & 8U) a = (next >> 3U) ^ 1U;",
                ),
                "undefined-arithmetic": source.replace(
                    "a = (next >> 3U) ^ 1U;", "a = next / 0U;"
                ),
                "unbounded": source.replace("i < 3U", "i < 13U"),
            }.items():
                candidate = Path(scratch) / f"reject-no-else-{label}.c"
                _ = candidate.write_text(changed)
                guest = Path(scratch) / f"reject-no-else-{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/no-else-reject-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=40,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)

    def test_bounded_if_without_else_forged_ast_refuses(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_if_without_else_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/no-else-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        branch = next(node for node in nodes if node["kind"] == "if-statement")
        children = [node for node in nodes if node["parent"] == branch["id"]]
        body = next(
            node for node in children if node["kind"] == "compound-statement"
        )
        body_span = cast(dict[str, object], body["span"])
        branch_span = cast(dict[str, object], branch["span"])
        self.assertEqual(body_span["end"], branch_span["end"])
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("wrong-kind", branch["id"], "kind", "while-statement"),
                ("wrong-parent", branch["id"], "parent", 0),
                ("extra-operation", branch["id"], "operation", "!"),
                ("body-parent", body["id"], "parent", 0),
                ("body-kind", body["id"], "kind", "declaration-statement"),
            ):
                assert isinstance(node_id, int)
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                tampered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"no-else-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)


    def test_zero_trip_while_skips_checked_body_and_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        ).read_text()
        self.assertIn("while (i < 3U)", original)
        self.assertIn("putchar((int)(next ^ 1U));", original)

        # Independently evaluate the C order: the first loop skips its
        # output and mutations; the second executes three complete trips.
        def oracle() -> tuple[bytes, list[int], int]:
            a, b, i = 3, 5, 3
            skipped = 0
            while i < 3:
                skipped += 1
                next_value = ((a * b) << 2) & 255
                a = ((next_value >> 3) ^ 1) if next_value & 8 else next_value - 1
                b = next_value
                i += 1
            visited: list[int] = []
            while True:
                next_value = ((a * b) << 2) & 255
                visited.append(next_value)
                a = ((next_value >> 3) ^ 1) if next_value & 8 else next_value - 1
                b = next_value
                i += 1
                if i >= 6:
                    break
            return bytes((a ^ 62,)), visited, skipped

        expected, visited, skipped = oracle()
        self.assertEqual((expected, visited, skipped), (b"A", [60, 160, 128], 0))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source in (
                ("true-shadow", original),
                ("false-shadow", original.replace("next & 8U", "next & 2U", 1)),
            ):
                candidate = Path(scratch) / f"zero-trip-{label}.c"
                candidate.write_text(source)
                guest = Path(scratch) / f"zero-trip-{label}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/zero-trip-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=100,
                )
                self.assertEqual(compiled.returncode, 0, (label, compiled.stderr))
                self.assertTrue(guest.is_file(), label)
                for guest_input in (b"", b"\xff\x00\x80"):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected, label)
                    self.assertRegex(
                        executed.stderr,
                        rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                    )

    def test_zero_trip_while_unproved_source_refuses_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        ).read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed in {
                "impure-guard": original.replace("while (i < 3U)", "while (i++ < 3U)"),
                "undefined-skipped-expression": original.replace(
                    "putchar((int)(next ^ 1U));", "putchar((int)(next / 0U));"
                ),
                "unproved-skipped-effect": original.replace(
                    "putchar((int)(next ^ 1U));", "next++;"
                ),
                "nested-skipped-loop": original.replace(
                    "putchar((int)(next ^ 1U));",
                    "while (next & 8U) { next = next - 1U; }",
                ),
            }.items():
                source = Path(scratch) / f"invalid-zero-trip-{label}.c"
                source.write_text(changed)
                guest = Path(scratch) / f"invalid-zero-trip-{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/invalid-zero-trip-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(source),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=40,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)

    def test_zero_trip_while_forged_skipped_ast_refuses_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/zero-trip-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        zero_loop = next(node for node in nodes if node["kind"] == "while-statement")
        children = [node for node in nodes if node["parent"] == zero_loop["id"]]
        condition = next(
            node for node in children if node["kind"] == "binary-expression"
        )
        body = next(node for node in children if node["kind"] == "compound-statement")
        skipped_call = next(
            node
            for node in nodes
            if node["kind"] == "call-expression"
            and cast(dict[str, dict[str, int]], node["span"])["begin"]["byte"]
            < cast(dict[str, dict[str, int]], body["span"])["end"]["byte"]
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("loop-parent", zero_loop["id"], "parent", 0),
                ("guard-type", condition["id"], "type", "u32"),
                ("skipped-body-parent", body["id"], "parent", 0),
                ("skipped-body-operation", body["id"], "operation", "++"),
                (
                    "skipped-output-callee",
                    skipped_call["id"],
                    "reference",
                    "external:puts",
                ),
            ):
                assert isinstance(node_id, int)
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                tampered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"zero-trip-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)


    def test_zero_trip_for_skips_body_and_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        ).read_text()
        self.assertEqual(original.count("while (i < 3U)"), 1)
        candidate_source = original.replace(
            "while (i < 3U)", "for (unsigned j = 0U; j < 0U; ++j)"
        )
        # C executes the do-while three times after skipping the entire
        # for body, including its output. The oracle is independent of IR.
        a, b, i = 3, 5, 3
        visited: list[int] = []
        for _ in range(3):
            next_value = ((a * b) << 2) & 255
            visited.append(next_value)
            a = ((next_value >> 3) ^ 1) if next_value & 8 else next_value - 1
            b = next_value
            i += 1
        self.assertEqual((visited, i, a ^ 62), ([60, 160, 128], 6, 65))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / "zero-trip-for.c"
            candidate.write_text(candidate_source)
            guest = Path(scratch) / "zero-trip-for.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/zero-trip-for-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=100,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", b"\xff\x00\x80"):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertRegex(
                    executed.stderr,
                    rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                )

    def test_zero_trip_for_unproved_source_and_ast_refuse(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        ).read_text()
        source = original.replace(
            "while (i < 3U)", "for (unsigned j = 0U; j < 0U; ++j)"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / "zero-trip-for.c"
            candidate.write_text(source)
            for label, changed in {
                "skipped-increment": source.replace(
                    "putchar((int)(next ^ 1U));", "next++;"
                ),
                "skipped-zero-divisor": source.replace(
                    "putchar((int)(next ^ 1U));", "putchar((int)(next / 0U));"
                ),
                "nested-skipped-loop": source.replace(
                    "putchar((int)(next ^ 1U));",
                    "while (next & 8U) { next = next - 1U; }",
                ),
                "wrong-counter": source.replace("++j)", "++i)", 1),
            }.items():
                bad = Path(scratch) / f"invalid-zero-for-{label}.c"
                bad.write_text(changed)
                guest = Path(scratch) / f"invalid-zero-for-{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/invalid-zero-for-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(bad),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=40,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/zero-for-ast-v1",
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            loop = next(node for node in nodes if node["kind"] == "for-statement")
            body = next(
                node
                for node in nodes
                if node["parent"] == loop["id"] and node["kind"] == "compound-statement"
            )
            for label, node_id, field, value in (
                ("for-parent", loop["id"], "parent", 0),
                ("for-operation", loop["id"], "operation", "+="),
                ("skipped-body-parent", body["id"], "parent", 0),
            ):
                assert isinstance(node_id, int)
                altered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                altered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"invalid-zero-for-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(altered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)


    def test_multi_assignment_conditional_recurrence_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_multi_assignment_branch_recurrence.c"
        ).read_text()
        else_arm = (
            "        } else {\n"
            "            a = next - 1U;\n"
            "            b = next;\n"
            "        }"
        )
        self.assertEqual(original.count(else_arm), 1)
        no_else = original.replace(else_arm, "        }")

        def oracle(a: int, b: int, with_else: bool) -> tuple[list[int], int]:
            visited: list[int] = []
            for _ in range(3):
                following = ((a * b) << 2) & 255
                visited.append(following)
                if following & 8:
                    a = (following >> 3) ^ 1
                    b = following ^ 2
                elif with_else:
                    a = following - 1
                    b = following
            return visited, a

        cases = (
            ("both-arms", original, 3, 5, True, 254, b"A", [60, 208, 192]),
            (
                "false-first",
                original.replace("unsigned a = 3U;", "unsigned a = 1U;")
                .replace("unsigned b = 5U;", "unsigned b = 1U;")
                .replace("a ^ 254U", "a ^ 125U"),
                1,
                1,
                True,
                125,
                b"B",
                [4, 48, 64],
            ),
            (
                "no-else-taken",
                no_else.replace("a ^ 254U", "a ^ 71U"),
                3,
                5,
                False,
                71,
                b"A",
                [60, 208, 208],
            ),
            (
                "no-else-skipped",
                no_else.replace("unsigned a = 3U;", "unsigned a = 1U;")
                .replace("unsigned b = 5U;", "unsigned b = 1U;")
                .replace("a ^ 254U", "a ^ 64U"),
                1,
                1,
                False,
                64,
                b"A",
                [4, 4, 4],
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source, a, b, with_else, mask, expected, trace in cases:
                visited, result = oracle(a, b, with_else)
                self.assertEqual(visited, trace, label)
                self.assertEqual(bytes([(result ^ mask) & 255]), expected)
                candidate = Path(scratch) / f"multi-arm-{label}.c"
                _ = candidate.write_text(source)
                guest = Path(scratch) / f"multi-arm-{label}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/multi-arm-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=120,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest.is_file(), label)
                for guest_input in (b"", b"\xff\x00\x80"):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected, label)
                    self.assertRegex(
                        executed.stderr,
                        rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                    )

    def test_multi_assignment_conditional_rejects_unproved_effects(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_multi_assignment_branch_recurrence.c"
        ).read_text()
        for label, changed in {
            "unselected-increment": original.replace("b = next ^ 2U;", "b = next++;"),
            "unselected-undefined": original.replace(
                "b = next ^ 2U;", "b = next / 0U;"
            ),
            "branch-extra-unsupported-call": original.replace(
                "b = next ^ 2U;", 'b = next ^ 2U; puts("extra");'
            ),
            "else-compound-assignment": original.replace("b = next;", "b += next;"),
            "unbraced-nested-branch": original.replace(
                "b = next;", "if (next & 1U) b = next;"
            ),
            "too-many-writes": original.replace("b = next;", "b = next;" * 17),
        }.items():
            with (
                self.subTest(label=label),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch,
            ):
                candidate = Path(scratch) / f"invalid-multi-arm-{label}.c"
                _ = candidate.write_text(changed)
                guest = Path(scratch) / "rejected.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/invalid-multi-arm-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=40,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)

    def test_multi_assignment_conditional_forged_ast_refuses(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_multi_assignment_branch_recurrence.c"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/multi-arm-ast-v1",
                    str(original),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            conditional = next(n for n in nodes if n["kind"] == "if-statement")
            arms = [
                n
                for n in nodes
                if n["kind"] == "compound-statement"
                and n["parent"] == conditional["id"]
            ]
            self.assertEqual(len(arms), 2)
            assignments = [
                [
                    n
                    for n in nodes
                    if n["kind"] == "binary-expression"
                    and n.get("operation") == "="
                    and n["parent"] == arm["id"]
                ]
                for arm in arms
            ]
            self.assertEqual(list(map(len, assignments)), [2, 2])
            then_second, else_second = assignments[0][1], assignments[1][1]
            then_left = next(
                n
                for n in nodes
                if n["parent"] == then_second["id"]
                and n["kind"] == "declaration-reference-expression"
            )
            for label, node_id, field, value in (
                ("then-second-parent", then_second["id"], "parent", conditional["id"]),
                ("else-second-parent", else_second["id"], "parent", conditional["id"]),
                ("then-second-operator", then_second["id"], "operation", "+="),
                ("then-second-reference", then_left["id"], "reference", "foreign@0"),
            ):
                assert isinstance(node_id, int)
                altered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                altered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"invalid-multi-arm-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(altered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_mixed_conditional_writes_and_output_reach_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_mixed_conditional_output.c"
        ).read_text()

        else_arm = (
            "        } else {\n"
            "            b = (next + 1U) & 255U;\n"
            "            putchar((int)(next ^ 45U));\n"
            "        }"
        )
        self.assertEqual(source.count(else_arm), 1)
        no_else = source.replace(else_arm, "        }")

        def oracle(iterations: int, *, with_else: bool) -> bytes:
            a, b, index = 1, 1, 0
            result = bytearray()
            while index < iterations:
                following = (a + b) & 255
                if (index & 1) == 0:
                    a = following
                    result.append(following ^ 83)
                elif with_else:
                    b = (following + 1) & 255
                    result.append(following ^ 45)
                index += 1
            return bytes(result)

        self.assertEqual(oracle(2, with_else=True), b"Q.")
        self.assertEqual(oracle(1, with_else=True), b"Q")
        self.assertEqual(oracle(2, with_else=False), b"Q")
        cases = (
            ("both-arms", source, 2, True),
            ("one-trip", source.replace("i < 2U", "i < 1U"), 1, True),
            ("no-else", no_else, 2, False),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, text, bound, with_else in cases:
                with self.subTest(label=label):
                    candidate = Path(scratch) / f"mixed-{label}.c"
                    _ = candidate.write_text(text)
                    guest = Path(scratch) / f"mixed-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/mixed-conditional-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=120,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for guest_input in (b"", bytes((255, 0, 128))):
                        execution = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=guest_input,
                            check=False,
                            capture_output=True,
                            timeout=30,
                        )
                        self.assertEqual(execution.returncode, 0, execution.stderr)
                        self.assertEqual(
                            execution.stdout, oracle(bound, with_else=with_else)
                        )
                        self.assertRegex(
                            execution.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_mixed_conditional_rejects_unproved_effects(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_mixed_conditional_output.c"
        ).read_text()
        variants = {
            "selected-postincrement": source.replace("a = next;", "a = next++;"),
            "unselected-postincrement": source.replace(
                "b = (next + 1U) & 255U;", "b = next++;"
            ),
            "unselected-undefined": source.replace("next ^ 45U", "next / 0U"),
            "unselected-hidden-call": source.replace(
                "putchar((int)(next ^ 45U));",
                'putchar((int)(next ^ 45U)); puts("extra");',
            ),
            "unselected-unbraced-branch": source.replace(
                "b = (next + 1U) & 255U;",
                "if (next) b = next;",
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, altered in variants.items():
                with self.subTest(label=label):
                    candidate = Path(scratch) / f"invalid-{label}.c"
                    _ = candidate.write_text(altered)
                    guest = Path(scratch) / f"invalid-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/mixed-conditional-invalid-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=45,
                    )
                    self.assertNotEqual(compiled.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_mixed_conditional_forged_ast_refuses(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_mixed_conditional_output.c"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/mixed-conditional-ast-v1",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            branch = next(n for n in nodes if n["kind"] == "if-statement")
            arms = [
                n
                for n in nodes
                if n["kind"] == "compound-statement" and n["parent"] == branch["id"]
            ]
            self.assertEqual(len(arms), 2)
            calls = [
                next(
                    n
                    for n in nodes
                    if n["kind"] == "call-expression" and n["parent"] == arm["id"]
                )
                for arm in arms
            ]
            assignments = [
                next(
                    n
                    for n in nodes
                    if n["kind"] == "binary-expression"
                    and n.get("operation") == "="
                    and n["parent"] == arm["id"]
                )
                for arm in arms
            ]
            for label, node, field, value in (
                ("then-call-parent", calls[0], "parent", branch["id"]),
                ("else-call-parent", calls[1], "parent", branch["id"]),
                ("else-write-parent", assignments[1], "parent", branch["id"]),
                ("else-call-kind", calls[1], "kind", "binary-expression"),
            ):
                with self.subTest(label=label):
                    altered = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    node_id = cast(int, node["id"])
                    altered["nodes"][node_id - 1][field] = value
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(altered).encode(),
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_nested_conditional_state_and_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_nested_conditional_output.c"
        ).read_text()
        outer_else = (
            "        } else {\n"
            "            if ((next & 1U) != 0U) {\n"
            "                b = (next + 1U) & 255U;\n"
            "                putchar((int)(next ^ 45U));\n"
            "            } else {\n"
            "                b = next;\n"
            "                putchar((int)(next ^ 44U));\n"
            "            }\n"
            "        }"
        )
        nested_else = (
            "            } else {\n"
            "                b = next;\n"
            "                putchar((int)(next ^ 44U));\n"
            "            }"
        )
        self.assertEqual(source.count(outer_else), 1)
        self.assertEqual(source.count(nested_else), 1)

        def oracle(
            *, outer_else_enabled: bool, inner_else_enabled: bool
        ) -> bytes:
            a, b, i = 1, 1, 0
            result = bytearray()
            while i < 2:
                next_value = (a + b) & 255
                if (i & 1) == 0:
                    if (next_value & 1) == 0:
                        a = next_value
                        result.append(next_value ^ 83)
                    else:
                        a = (next_value + 1) & 255
                        result.append(next_value ^ 84)
                elif outer_else_enabled:
                    if (next_value & 1) != 0:
                        b = (next_value + 1) & 255
                        result.append(next_value ^ 45)
                    elif inner_else_enabled:
                        b = next_value
                        result.append(next_value ^ 44)
                i += 1
            return bytes(result)

        self.assertEqual(
            oracle(outer_else_enabled=True, inner_else_enabled=True), b"Q."
        )
        self.assertEqual(
            oracle(outer_else_enabled=False, inner_else_enabled=True), b"Q"
        )
        self.assertEqual(
            oracle(outer_else_enabled=True, inner_else_enabled=False), b"Q."
        )
        cases = (
            ("both-nested-arms", source, True, True),
            (
                "skipped-outer-else",
                source.replace(outer_else, "        }"),
                False,
                True,
            ),
            (
                "nested-if-without-else",
                source.replace(nested_else, "            }"),
                True,
                False,
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source_text, use_outer_else, use_inner_else in cases:
                with self.subTest(label=label):
                    candidate = Path(scratch) / f"nested-{label}.c"
                    _ = candidate.write_text(source_text)
                    guest = Path(scratch) / f"nested-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/nested-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=150,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for guest_input in (b"", b"\xff\x00\x80"):
                        executed = subprocess.run(
                            [
                                str(VM),
                                str(guest),
                                "--input-stdin",
                                "--report-steps",
                            ],
                            input=guest_input,
                            check=False,
                            capture_output=True,
                            timeout=30,
                        )
                        self.assertEqual(
                            executed.returncode, 0, executed.stderr
                        )
                        self.assertEqual(
                            executed.stdout,
                            oracle(
                                outer_else_enabled=use_outer_else,
                                inner_else_enabled=use_inner_else,
                            ),
                        )
                        self.assertRegex(
                            executed.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_nested_conditional_unproved_source_refuses_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_nested_conditional_output.c"
        ).read_text()
        variants = {
            "selected-increment": source.replace("a = next;", "a = next++;"),
            "unselected-undefined": source.replace("next ^ 44U", "next / 0U"),
            "unselected-hidden-increment": source.replace(
                "b = next;", "b = next; next++;"
            ),
            "unselected-unsupported-call": source.replace(
                "b = next;", 'b = next; puts("hidden");'
            ),
            "unbraced-inner": source.replace(
                "if ((next & 1U) != 0U) {",
                "if ((next & 1U) != 0U)",
            ),
            "too-deep": source.replace(
                "a = next;",
                "if (next) { if (next) { if (next) { a = next; } } }",
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source_text in variants.items():
                with self.subTest(label=label):
                    candidate = Path(scratch) / f"nested-invalid-{label}.c"
                    _ = candidate.write_text(source_text)
                    guest = Path(scratch) / f"nested-invalid-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/nested-invalid-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=50,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_nested_conditional_forged_ast_refuses_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_nested_conditional_output.c"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/nested-conditional-ast-v1",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            nested = [n for n in nodes if n["kind"] == "if-statement"]
            self.assertEqual(len(nested), 3)
            outer = nested[0]
            first = nested[1]
            self.assertTrue(
                any(
                    n["id"] == first["parent"] and n["parent"] == outer["id"]
                    for n in nodes
                )
            )
            arm = next(
                n
                for n in nodes
                if (
                    n["kind"] == "compound-statement"
                    and n["parent"] == first["id"]
                )
            )
            write = next(
                n
                for n in nodes
                if n["kind"] == "binary-expression"
                and n.get("operation") == "="
                and n["parent"] == arm["id"]
            )
            call = next(
                n
                for n in nodes
                if n["kind"] == "call-expression" and n["parent"] == arm["id"]
            )
            for label, node, field, value in (
                ("inner-if-parent", first, "parent", outer["id"]),
                ("inner-arm-parent", arm, "parent", outer["id"]),
                ("inner-write-parent", write, "parent", first["id"]),
                ("inner-output-parent", call, "parent", first["id"]),
                ("inner-if-metadata", first, "operation", "&&"),
            ):
                with self.subTest(label=label):
                    altered = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    node_id = cast(int, node["id"])
                    altered["nodes"][node_id - 1][field] = value
                    guest = Path(scratch) / f"nested-forged-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(altered).encode(),
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)


if __name__ == "__main__":
    _ = unittest.main()
