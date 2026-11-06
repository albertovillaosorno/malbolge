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
LOOP_OUTPUT = ROOT / "tests/compiler/c-frontend/accepted/local_loop_branch_output.c"


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
            # Typed constant/SSA admission succeeds for the full C loop;
            # only the positional guest byte-stream layout lacks a witness.
            self.assertIn(
                b"canonical typed byte bridge rejected: Layout(UnsupportedEffectTrace)",
                process.stderr,
            )
            self.assertNotIn(b"normalized frontend rejected", process.stderr)
            self.assertFalse(guest.exists(), "unwitnessed C published a guest")

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
            altered.write_text(
                source.read_text().replace("next ^ 0x3DU", "next / 0U")
            )
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
                self.assertRegex(
                    executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )
            # An unsupported C effect may not inherit the source witness.
            altered = Path(scratch) / "fibonacci-four-unsupported.c"
            altered.write_text(source.read_text().replace("next ^ 61U", "next / 0U"))
            refused_guest = Path(scratch) / "fibonacci-four-unsupported.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(refused_guest), str(altered)],
                check=False, capture_output=True, timeout=180,
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
            mutated.write_text(
                source.read_text().replace("next ^ 58U", "next >> 1U")
            )
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
            mutation.write_text(
                source.read_text().replace("next ^ 59U", "next >> 1U")
            )
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
            ROOT
            / "tests/compiler/c-frontend/accepted/"
            "local_remainder_recurrence_output.c"
        )
        a, b = 3, 5
        observed = []
        for _ in range(3):
            next_value = (a * b) & 255
            observed.append(next_value)
            a = (
                (next_value % 17) ^ 1
                if next_value % 2 == 0
                else next_value - 1
            )
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

    def test_unsigned_shift_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/"
            "local_shift_recurrence_output.c"
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
                    # An unreachable unsigned subtraction underflow is outside
                    # the current checked-subtraction projection.
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
                "unsupported-or": original.replace("next - 1U", "next | 1U"),
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
            ROOT
            / "tests/compiler/c-frontend/accepted/"
            "local_division_recurrence_output.c"
        )
        a, b = 3, 5
        visited = []
        for _ in range(3):
            next_value = (a * b) & 255
            visited.append(next_value)
            a = (
                (next_value // 17) ^ 1
                if next_value % 2 == 0
                else next_value - 1
            )
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
            ROOT
            / "tests/compiler/c-frontend/accepted/"
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
            # Shifts are outside the closed evaluator. An unsigned overflow
            # would be defined by C, but is deliberately outside this checked
            # (nonwrapping) constant-propagation slice.
            invalid = {
                "shift": original.replace("a * b", "a >> b"),
                "overflow": original.replace("a = 3U", "a = 255U")
                .replace("b = 5U", "b = 255U")
                .replace("(a * b) & 255U", "(((a * b) * (a * b)) * a) & 255U"),
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


if __name__ == "__main__":
    _ = unittest.main()
