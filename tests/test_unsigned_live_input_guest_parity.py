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
#   - Live-byte guest VM parity for source-proven unsigned C predicates.
# - Must-Not:
#   - Replace guest execution with host stdout or claim EOF semantics.
# - Allows:
#   - Inputs: pinned compiler tools and deterministic finite guest byte streams.
#   - Outputs: actual guest stdout against independent bounded C oracles.
#   - Side effects: ignored temporary files and local compiler subprocesses.
# - Split-When:
#   - General runtime C arithmetic admits arbitrary dynamic branches.
# - Merge-When:
#   - Shared guest compiler tests supply the same independent input oracle.
# - Summary:
#   - Recompile C and replay real Malbolge over seeded unsigned boundaries.

"""Prove finite unsigned C predicates with actual guest byte input/output."""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast, final

ROOT = Path(__file__).resolve().parents[1]
ALIAS_STEM = "unsigned_alias_induction_live_input"
NESTED_ALIAS_STEM = "unsigned_nested_alias_live_input"
NESTED_FRESH_STEM = "unsigned_nested_fresh_live_input"
HEX_STEM = "unsigned_hex_threshold_live_input"
ALGEBRA_STEM = "unsigned_byte_algebra_live_input"
MODULAR_STEM = "unsigned_modular_output_live_input"
GUARDED_STEM = "unsigned_guarded_modular_output_live_input"
NESTED_GUARDED_STEM = "unsigned_nested_guarded_live_input"
UNBRACED_GUARDED_STEM = "unsigned_unbraced_guarded_live_input"
UNBRACED_MULTILINE_STEM = "unsigned_multiline_guarded_live_input"
ELSE_IF_STEM = "unsigned_else_if_guarded_live_input"
MULTI_GUARDED_STEM = "unsigned_multiple_guarded_live_input"
NARROWED_STEM = "unsigned_narrowed_guarded_live_input"
SWITCH_STEM = "unsigned_switch_guarded_live_input"
DEAD_LITERAL_STEM = "unsigned_reflexive_dead_literal_live_input"
DEAD_PURE_STEM = "unsigned_reflexive_dead_pure_live_input"
UNSUPPORTED_MARKER = b"Unsupported"
# These signed getchar loop locals used to publish guest outputs only for
# successful reads; on exhausted stdin they emitted 0x6a instead of C23 ff.
# Their unsigned induction proofs remain historical, not EOF conversion.
SIGNED_EOF_REFUSALS = frozenset(
    {
        "unsigned_modulo_live_input",
        "unsigned_radix_live_input",
        "unsigned_short_circuit_zero_divisor",
        "triple_control_live_input",
        "triple_induction_live_input",
        "nested_mixed_induction_live_input",
        "nested_outer_induction_live_input",
        NESTED_FRESH_STEM,
        ALIAS_STEM,
        NESTED_ALIAS_STEM,
        "unsigned_wrapping_predicate_live_input",
        HEX_STEM,
        ALGEBRA_STEM,
        MODULAR_STEM,
        GUARDED_STEM,
        NESTED_GUARDED_STEM,
        UNBRACED_GUARDED_STEM,
        UNBRACED_MULTILINE_STEM,
        ELSE_IF_STEM,
        MULTI_GUARDED_STEM,
        NARROWED_STEM,
        SWITCH_STEM,
        DEAD_LITERAL_STEM,
        DEAD_PURE_STEM,
    }
)
CASES = (
    ("triple_control_live_input", 7, 16),
    ("triple_induction_live_input", 8, 18),
    ("nested_mixed_induction_live_input", 6, 14),
    ("nested_outer_induction_live_input", 6, 15),
    ("unsigned_modulo_live_input", 5, 13),
    ("unsigned_radix_live_input", 5, 13),
    ("unsigned_wrapping_predicate_live_input", 4, 10),
    ("unsigned_short_circuit_zero_divisor", 1, 3),
    (ALIAS_STEM, 1, 5),
    (NESTED_ALIAS_STEM, 1, 6),
    (NESTED_FRESH_STEM, 5, 10),
    (HEX_STEM, 4, 13),
    (ALGEBRA_STEM, 4, 17),
    (MODULAR_STEM, 4, 25),
    (GUARDED_STEM, 4, 9),
    (NESTED_GUARDED_STEM, 4, 9),
    (UNBRACED_GUARDED_STEM, 4, 9),
    (UNBRACED_MULTILINE_STEM, 4, 9),
    (ELSE_IF_STEM, 4, 9),
    (MULTI_GUARDED_STEM, 4, 13),
    (NARROWED_STEM, 4, 9),
    (SWITCH_STEM, 4, 9),
    (DEAD_LITERAL_STEM, 4, 17),
    (DEAD_PURE_STEM, 4, 17),
)
NATIVE_TOOL_ROOT = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin"
FRONTEND = NATIVE_TOOL_ROOT / "malbolge-c-frontend"
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
SOURCES = ROOT / "tests/compiler/c-frontend/accepted"
GOLDENS = ROOT / "tests/compiler/c-frontend/golden"


def independent_c_oracle(stem: str, data: bytes) -> bytes:
    """Only successful getchar bytes; C unsigned operations use 32 bits."""
    if stem == NESTED_FRESH_STEM:
        # One initial local is unused; four nested reads are the only outputs.
        return data[1:]
    output = bytearray()
    for counter, byte in enumerate(data, start=1):
        if stem == "triple_control_live_input":
            # Continue duplicates read three; the later inner break skips
            # column two, but the next outer row still runs.
            copies = 2 if counter == 3 else 1
        elif stem == "triple_induction_live_input":
            # Plane two, row one, column two is the sixth live read.
            copies = 2 if counter == 6 else 1
        elif stem == "nested_mixed_induction_live_input":
            # The second outer row, first inner column is trip number three.
            copies = 2 if counter == 3 else 1
        elif stem == "nested_outer_induction_live_input":
            # Two inner trips per outer row. Only row two repeats its bytes.
            copies = 2 if (counter - 1) // 2 == 1 else 1
        elif stem in {
            GUARDED_STEM,
            NESTED_GUARDED_STEM,
            UNBRACED_GUARDED_STEM,
            UNBRACED_MULTILINE_STEM,
            ELSE_IF_STEM,
            NARROWED_STEM,
            SWITCH_STEM,
        }:
            # Every nested byte guard preserves the live byte on the active
            # source-C path, including NUL and high-bit inputs.
            copies = 1
        elif stem == MULTI_GUARDED_STEM:
            # Each active C arm writes the resident byte exactly twice.
            copies = 2
        elif stem == MODULAR_STEM:
            # Signed negative, multiplication, bitwise and additive modulo.
            copies = 5
        elif stem in {ALGEBRA_STEM, DEAD_LITERAL_STEM, DEAD_PURE_STEM}:
            # XOR and reflexive predicates select only live byte outputs.
            copies = 3
        elif stem == HEX_STEM:
            # Every successful getchar value lies in [0, 255] < C23 0x100.
            copies = 2
        elif stem == NESTED_ALIAS_STEM:
            # Two induction levels preserve the same live byte and its alias.
            copies = 4
        elif stem == ALIAS_STEM:
            # Both local identities refer to the same one guest input byte.
            copies = 3
        elif stem == "unsigned_short_circuit_zero_divisor":
            # i == 1U makes the RHS undefined division unreachable.
            copies = 1
        elif stem in {"unsigned_modulo_live_input", "unsigned_radix_live_input"}:
            copies = 2 if counter % 2 == 0 else 1
        elif stem == "unsigned_wrapping_predicate_live_input":
            # C's subtraction converts to u32 before the > 99U comparison.
            copies = 2 if (counter - 2) % (1 << 32) > 99 else 1
        else:
            raise ValueError(f"no independent C oracle for {stem}")
        output.extend((byte,) * copies)
    return bytes(output)


def cases_for_length(length: int) -> list[bytes]:
    rng = random.Random(0x26B017 + length)
    binary_pattern = (0x00, 0xFF, 0x80, 0x01, 0x7F, 0x32, 0xA8, 0x5C)
    boundaries = [
        bytes(range(65, 65 + length)),
        bytes(binary_pattern[index % len(binary_pattern)] for index in range(length)),
        bytes([0x00] * length),
        bytes([0xFF] * length),
        bytes([0x80] * length),
    ]
    return boundaries + [rng.randbytes(length) for _ in range(24)]


def check_native_nested_bytes(executable: Path, count: int, *, fresh: bool) -> None:
    """Verify seeded byte vectors against the independent native C23 run."""
    for data in cases_for_length(count):
        result = subprocess.run(
            [str(executable)],
            input=data,
            capture_output=True,
            check=False,
            timeout=10,
        )
        expected = data[1:] if fresh else data[:1] * 4
        assert result.returncode == 0, (executable, data.hex(), result.stderr)
        assert result.stdout == expected, (
            executable,
            data.hex(),
            result.stdout.hex(),
            expected.hex(),
        )


@final
class UnsignedLiveGuestParityTests(unittest.TestCase):
    def _check_signed_eof_refusal(self, stem: str) -> None:
        """C23 native outputs agree; incomplete guest EOF must not publish."""
        required = (FRONTEND, ADAPTER, LAYOUT, CLANG)
        if not all(path.is_file() for path in required):
            self.skipTest("pinned C23 and guest compiler tools missing")
        source = SOURCES / f"{stem}.c"
        count = next(size for name, size, _ in CASES if name == stem)
        env = dict(os.environ)
        library = str(ROOT / ".dependencies/llvm/22.1.8/lib")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (library, env.get("LD_LIBRARY_PATH", "")) if part
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            folder = Path(temporary)
            output = folder / "output.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    str(source),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                check=False,
                timeout=45,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(UNSUPPORTED_MARKER, compiled.stderr)
            self.assertFalse(output.exists())

            wrapper = folder / "oracle.c"
            _ = wrapper.write_text(
                f'#include "{source}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            witnesses: list[tuple[bytes, ...]] = []
            inputs = (b"", *cases_for_length(count)[:5])
            for optimization in ("-O0", "-O2"):
                native = folder / f"native-{optimization[2:]}"
                built = subprocess.run(
                    [
                        str(CLANG),
                        "-std=c23",
                        optimization,
                        "-fsanitize=undefined",
                        "-fno-sanitize-recover=all",
                        str(wrapper),
                        "-o",
                        str(native),
                    ],
                    env=env,
                    capture_output=True,
                    check=False,
                    timeout=45,
                )
                self.assertEqual(built.returncode, 0, built.stderr)
                observed_outputs = []
                for data in inputs:
                    result = subprocess.run(
                        [str(native)],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if len(data) == count:
                        self.assertEqual(
                            result.stdout, independent_c_oracle(stem, data)
                        )
                    observed_outputs.append(result.stdout)
                witnesses.append(tuple(observed_outputs))
            self.assertEqual(witnesses[0], witnesses[1])

    def test_generated_input_vectors_are_full_length(self) -> None:
        # Duplicate stems could silently overwrite test artifacts and make a
        # repeated fixture look like multiple independent guest witnesses.
        stems = [stem for stem, _, _ in CASES]
        self.assertEqual(len(stems), len(set(stems)))
        with self.assertRaisesRegex(ValueError, "no independent C oracle"):
            _ = independent_c_oracle("unregistered_fixture", b"A")
        # Include a longer future stream to catch fixed-width vector tables.
        lengths = {count for _, count, _ in CASES}
        lengths.add(17)
        for length in sorted(lengths):
            with self.subTest(length=length):
                self.assertEqual(len(cases_for_length(length)), 29)
                self.assertTrue(
                    all(len(data) == length for data in cases_for_length(length))
                )

    def test_golden_source_identity(self) -> None:
        for stem, _, _ in CASES:
            with self.subTest(stem=stem):
                source = SOURCES / f"{stem}.c"
                golden = GOLDENS / f"{stem}.json"
                parsed = cast(
                    dict[str, dict[str, str]],
                    json.loads(golden.read_text(encoding="utf-8")),
                )
                self.assertEqual(parsed["source"]["id"], source.name)
                self.assertEqual(
                    parsed["source"]["sha256"],
                    hashlib.sha256(source.read_bytes()).hexdigest(),
                )
                self.assertEqual(parsed["clang"]["version"], "22.1.8")

    def test_reachable_zero_division_refuses_publication(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("repository-pinned compiler executables missing")
        source = ROOT / "tests/compiler/c-frontend/rejected"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            output = Path(directory) / "unreachable-division.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    str(source / "unsigned_reachable_zero_divisor.c"),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"Unsupported", compiled.stderr)
            self.assertFalse(output.exists())

    def test_nested_stale_guest_alias_refuses_publication(self) -> None:
        """Reject stale guest-state reuse before any target publication."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("repository-pinned compiler executables missing")
        source = ROOT / "tests/compiler/c-frontend/rejected"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            output = Path(directory) / "nested-stale-alias.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    str(source / "unsigned_nested_stale_alias.c"),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                check=False,
                timeout=40,
            )
            assert compiled.returncode != 0
            assert UNSUPPORTED_MARKER in compiled.stderr
            assert not output.exists()

    def test_nested_alias_native_c23_oracles(self) -> None:
        """Cross-check three original C programs with UBSan at O0 and O2."""
        if not CLANG.is_file():
            self.skipTest("pinned C23 Clang executable missing")
        # The stale source is valid C: it must still print its first byte.
        # A guest compiler without independent local storage must refuse it.
        sources = (
            (SOURCES / "unsigned_nested_alias_live_input.c", 1, False),
            (SOURCES / "unsigned_nested_fresh_live_input.c", 5, True),
            (
                ROOT
                / "tests/compiler/c-frontend/rejected"
                / "unsigned_nested_stale_alias.c",
                5,
                False,
            ),
        )
        env = dict(os.environ)
        llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            folder = Path(temporary)
            for source, count, fresh in sources:
                wrapper = folder / "oracle.c"
                _ = wrapper.write_text(
                    f'#include "{source}"\nint main(void) {{ emit(); return 0; }}\n',
                    encoding="utf-8",
                )
                for optimization in ("-O0", "-O2"):
                    output = folder / f"oracle-{optimization[2:]}"
                    built = subprocess.run(
                        [
                            str(CLANG),
                            "-std=c23",
                            optimization,
                            "-fsanitize=undefined",
                            "-fno-sanitize-recover=all",
                            str(wrapper),
                            "-o",
                            str(output),
                        ],
                        env=env,
                        capture_output=True,
                        check=False,
                        timeout=45,
                    )
                    assert built.returncode == 0, built.stderr
                    check_native_nested_bytes(output, count, fresh=fresh)

    def test_hex_threshold_seeded_native_and_guest_parity(self) -> None:
        """Require native C23 parity and reject incomplete signed EOF output."""
        self._check_signed_eof_refusal(HEX_STEM)

    def test_hex_boundary_condition_refuses_guest_publication(self) -> None:
        """An input-dependent 255 boundary must not become a static guest arm."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, CLANG)):
            self.skipTest("pinned compiler and C23 Clang executables missing")
        original = (SOURCES / f"{HEX_STEM}.c").read_bytes()
        condition = b"if (current < 0x100)"
        self.assertEqual(original.count(condition), 1)
        changed = original.replace(condition, b"if (current < 0x0FF)")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            folder = Path(temporary)
            source = folder / "byte-boundary.c"
            _ = source.write_bytes(changed)
            guest = folder / "byte-boundary.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    str(source),
                    "--output",
                    str(guest),
                ],
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(UNSUPPORTED_MARKER, compiled.stderr)
            self.assertFalse(guest.exists())

            wrapper = folder / "native-oracle.c"
            _ = wrapper.write_text(
                f'#include "{source}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            data = bytes((0xFF, 0x00, 0x80, 0xFE))
            expected = bytes((0xFF, 0x00, 0x00, 0x80, 0x80, 0xFE, 0xFE))
            env = dict(os.environ)
            llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
            )
            for optimization in ("-O0", "-O2"):
                native = folder / f"boundary-{optimization[2:]}"
                built = subprocess.run(
                    [
                        str(CLANG),
                        "-std=c23",
                        optimization,
                        "-fsanitize=undefined",
                        "-fno-sanitize-recover=all",
                        str(wrapper),
                        "-o",
                        str(native),
                    ],
                    env=env,
                    capture_output=True,
                    check=False,
                    timeout=45,
                )
                self.assertEqual(built.returncode, 0, built.stderr)
                observed = subprocess.run(
                    [str(native)],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                with self.subTest(optimization=optimization):
                    self.assertEqual(observed.returncode, 0, observed.stderr)
                    self.assertEqual(observed.stdout, expected)

    def test_byte_algebra_c23_native_and_real_guest_parity(self) -> None:
        """Require native C23 parity and reject incomplete signed EOF output."""
        self._check_signed_eof_refusal(ALGEBRA_STEM)

    def test_multiple_guarded_c23_native_and_guest_parity(self) -> None:
        """Require native C23 parity and reject incomplete signed EOF output."""
        self._check_signed_eof_refusal(MULTI_GUARDED_STEM)

    def test_multiple_guarded_unequal_effects_refuse_guest(self) -> None:
        """Never erase an unbalanced branch or an extra runtime read."""
        prerequisites = (FRONTEND, ADAPTER, LAYOUT)
        if not all(path.is_file() for path in prerequisites):
            self.skipTest("pinned compiler tools missing")
        original = (SOURCES / f"{MULTI_GUARDED_STEM}.c").read_bytes()
        odd_output = b"putchar(current | 1);"
        even_output = b"putchar(current & -2);"
        self.assertEqual(original.count(odd_output), 2)
        self.assertEqual(original.count(even_output), 2)
        controls = (
            # The true branch would consume another guest byte and write it.
            (
                "hidden-read",
                original.replace(
                    odd_output,
                    b"putchar(getchar());",
                    1,
                ),
            ),
            # Both arms are individually byte-preserving, but their ordered
            # output counts differ for odd and even inputs.
            (
                "unequal-count",
                original.replace(
                    even_output + b"\n",
                    b"",
                    1,
                ),
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            folder = Path(temporary)
            for stem, source_bytes in controls:
                source = folder / f"{stem}.c"
                _ = source.write_bytes(source_bytes)
                guest = folder / f"{stem}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--capsule",
                        str(source),
                        "--output",
                        str(guest),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=120,
                )
                with self.subTest(control=stem):
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertIn(UNSUPPORTED_MARKER, compiled.stderr)
                    self.assertFalse(guest.exists())

    def test_unbraced_guarded_c23_native_and_guest_parity(self) -> None:
        """Replay source-proven same-line odd/even C output arms."""
        self._check_unbraced_guarded_c23_native_and_guest_parity(UNBRACED_GUARDED_STEM)

    def test_multiline_guarded_c23_native_and_guest_parity(self) -> None:
        """Replay source-proven multiline odd/even C output arms."""
        self._check_unbraced_guarded_c23_native_and_guest_parity(
            UNBRACED_MULTILINE_STEM
        )

    def test_else_if_guarded_c23_native_and_guest_parity(self) -> None:
        """Replay three path-sensitive C arms from a multiline else-if."""
        self._check_unbraced_guarded_c23_native_and_guest_parity(ELSE_IF_STEM)

    def test_else_if_inner_arm_nonidentity_refuses_guest(self) -> None:
        """The second guarded C path cannot change bytes without guest ALU."""
        prerequisites = (FRONTEND, ADAPTER, LAYOUT, CLANG)
        if not all(path.is_file() for path in prerequisites):
            self.skipTest("pinned native and guest compiler tools missing")
        source = SOURCES / f"{ELSE_IF_STEM}.c"
        original = source.read_bytes()
        self.assertEqual(original.count(b"current | 2"), 1)
        changed = original.replace(b"current | 2", b"current ^ 2", 1)
        env = dict(os.environ)
        llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            folder = Path(temporary)
            mutated = folder / "changed-inner.c"
            _ = mutated.write_bytes(changed)
            guest = folder / "changed-inner.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    str(mutated),
                    "--output",
                    str(guest),
                ],
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(UNSUPPORTED_MARKER, compiled.stderr)
            self.assertFalse(guest.exists())
            wrapper = folder / "oracle.c"
            _ = wrapper.write_text(
                f'#include "{mutated}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            for optimization in ("-O0", "-O2"):
                native = folder / f"native-{optimization[2:]}"
                built = subprocess.run(
                    [
                        str(CLANG),
                        "-std=c23",
                        optimization,
                        "-fsanitize=undefined",
                        "-fno-sanitize-recover=all",
                        str(wrapper),
                        "-o",
                        str(native),
                    ],
                    env=env,
                    capture_output=True,
                    check=False,
                    timeout=45,
                )
                self.assertEqual(built.returncode, 0, built.stderr)
                for data in cases_for_length(4):
                    observed = subprocess.run(
                        [str(native)],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    expected = bytes(
                        (byte & ~2) if byte & 2 and not byte & 1 else byte
                        for byte in data
                    )
                    with self.subTest(optimization=optimization, data=data.hex()):
                        self.assertEqual(observed.returncode, 0, observed.stderr)
                        self.assertEqual(observed.stdout, expected)

    def _check_unbraced_guarded_c23_native_and_guest_parity(self, stem: str) -> None:
        """Do not publish source-unrolled signed EOF outputs."""
        self._check_signed_eof_refusal(stem)

    def test_nested_guarded_c23_native_and_guest_parity(self) -> None:
        """Require native C23 parity and reject incomplete signed EOF output."""
        self._check_signed_eof_refusal(NESTED_GUARDED_STEM)

    def test_guarded_modular_c23_native_and_guest_parity(self) -> None:
        """Require native C23 parity and reject incomplete signed EOF output."""
        self._check_signed_eof_refusal(GUARDED_STEM)

    def test_narrowed_guarded_c23_native_and_guest_parity(self) -> None:
        """Require native C23 parity and reject incomplete signed EOF output."""
        self._check_signed_eof_refusal(NARROWED_STEM)

    def test_switch_guarded_c23_native_and_guest_parity(self) -> None:
        """Require native C23 parity and reject incomplete signed EOF output."""
        self._check_signed_eof_refusal(SWITCH_STEM)

    def test_pure_output_c23_oracles(self) -> None:
        """Compare selected pure-C output with two native C23 optimizers."""
        if not CLANG.is_file():
            self.skipTest("repository-pinned native C23 clang missing")
        for stem in (MODULAR_STEM, DEAD_LITERAL_STEM, DEAD_PURE_STEM):
            source = SOURCES / f"{stem}.c"
            env = dict(os.environ)
            llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
            )
            with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
                folder = Path(temporary)
                wrapper = folder / "oracle.c"
                _ = wrapper.write_text(
                    f'#include "{source}"\nint main(void) {{ emit(); return 0; }}\n',
                    encoding="utf-8",
                )
                for optimization in ("-O0", "-O2"):
                    native = folder / f"native-{optimization[2:]}"
                    built = subprocess.run(
                        [
                            str(CLANG),
                            "-std=c23",
                            optimization,
                            "-fsanitize=undefined",
                            "-fno-sanitize-recover=all",
                            str(wrapper),
                            "-o",
                            str(native),
                        ],
                        env=env,
                        capture_output=True,
                        check=False,
                        timeout=45,
                    )
                    self.assertEqual(built.returncode, 0, built.stderr)
                    for data in cases_for_length(4):
                        with self.subTest(optimization=optimization, stdin=data.hex()):
                            observed = subprocess.run(
                                [str(native)],
                                input=data,
                                capture_output=True,
                                check=False,
                                timeout=10,
                            )
                            self.assertEqual(observed.returncode, 0, observed.stderr)
                            self.assertEqual(
                                observed.stdout,
                                independent_c_oracle(stem, data),
                            )

    def test_dead_literal_changed_branch_refuses_guest_publication(self) -> None:
        """Never erase a reachable constant C output in real compilation."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned compiler executable missing")
        rejected = ROOT / "tests/compiler/c-frontend/rejected"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for kind in ("selected", "dynamic"):
                for expression in ("literal", "pure"):
                    source = (
                        rejected
                        / f"unsigned_reflexive_{kind}_{expression}_live_input.c"
                    )
                    guest = Path(temporary) / f"{kind}-{expression}.malbolge"
                    attempt = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            str(source),
                            "--output",
                            str(guest),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    with self.subTest(kind=kind, expression=expression):
                        self.assertNotEqual(attempt.returncode, 0)
                        self.assertIn(UNSUPPORTED_MARKER, attempt.stderr)
                        self.assertFalse(guest.exists())

    def test_unsupported_modular_output_refuses_guest_publication(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("repository-pinned compiler executables missing")
        rejected = ROOT / "tests/compiler/c-frontend/rejected"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for stem in (
                "unsigned_nonmodular_output_live_input",
                "unsigned_overflowing_output_live_input",
            ):
                with self.subTest(stem=stem):
                    guest = Path(temporary) / f"{stem}.malbolge"
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            str(rejected / f"{stem}.c"),
                            "--output",
                            str(guest),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(UNSUPPORTED_MARKER, result.stderr)
                    self.assertFalse(guest.exists())

    def _check_seeded_guest_parity(
        self, cases: tuple[tuple[str, int, int], ...]
    ) -> None:
        prerequisites = (FRONTEND, ADAPTER, LAYOUT, VM)
        if not all(path.is_file() for path in prerequisites):
            self.skipTest("repository-pinned C and guest executables missing")
        if not GUEST_INCLUDE.is_dir() or not RESOURCE.is_dir():
            self.skipTest("repository-pinned C frontend resource dirs missing")

        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for stem, count, expected_steps in cases:
                with self.subTest(stem=stem):
                    guest = Path(directory) / f"{stem}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            str(SOURCES / f"{stem}.c"),
                            "--output",
                            str(guest),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    if stem in SIGNED_EOF_REFUSALS:
                        self.assertNotEqual(compiled.returncode, 0)
                        self.assertIn(UNSUPPORTED_MARKER, compiled.stderr)
                        self.assertFalse(guest.exists())
                        continue
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    # The trusted adaptive-width selector keeps the entire
                    # seeded guest replay affordable. Also retain a canonical
                    # N15 binary boundary for each compiled source, so the
                    # narrower proof is not the only execution evidence.
                    canonical_env = dict(os.environ)
                    canonical_env["MALBOLGE_PROFILE_ADAPTIVE_WIDTH"] = "0"
                    adaptive_env = dict(canonical_env)
                    adaptive_env["MALBOLGE_PROFILE_ADAPTIVE_WIDTH"] = "1"
                    for index, data in enumerate(cases_for_length(count)):
                        modes = [("adaptive", adaptive_env)]
                        if index == 1:
                            modes.append(("canonical", canonical_env))
                        for mode, environment in modes:
                            with self.subTest(stdin=data.hex(), mode=mode):
                                result = subprocess.run(
                                    [
                                        str(VM),
                                        str(guest),
                                        "--input-stdin",
                                        "--report-steps",
                                    ],
                                    env=environment,
                                    input=data,
                                    capture_output=True,
                                    check=False,
                                    timeout=30,
                                )
                                self.assertEqual(result.returncode, 0, result.stderr)
                                self.assertEqual(
                                    result.stdout, independent_c_oracle(stem, data)
                                )
                                expected_report = (
                                    f"malbolge-steps-v1:{expected_steps}\n".encode()
                                )
                                self.assertEqual(result.stderr, expected_report)

    def test_seeded_guest_parity_nested_loops(self) -> None:
        self._check_seeded_guest_parity(CASES[:4])

    def test_seeded_guest_parity_unsigned_arithmetic(self) -> None:
        self._check_seeded_guest_parity(CASES[4:8])

    def test_seeded_guest_parity_aliases_and_byte_algebra(self) -> None:
        self._check_seeded_guest_parity(CASES[8:-3])

    def test_seeded_guest_parity_modular_output(self) -> None:
        self._check_seeded_guest_parity(CASES[-3:-2])

    def test_seeded_guest_parity_dead_literal(self) -> None:
        self._check_seeded_guest_parity(CASES[-2:-1])

    def test_seeded_guest_parity_dead_pure_arithmetic(self) -> None:
        self._check_seeded_guest_parity(CASES[-1:])


if __name__ == "__main__":
    _ = unittest.main()
