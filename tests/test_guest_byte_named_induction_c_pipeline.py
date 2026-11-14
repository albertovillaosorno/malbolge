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
#   - Source-backed arbitrary C loop-counter identifiers in bounded replay.
# - Must-Not:
#   - Trust a mismatched counter binding or forge guest input values.
# - Allows:
#   - Inputs: pinned C/Clang, exact original source, real binary stdin.
#   - Outputs: verified guest bytes or refusal without guest publication.
#   - Side effects: temporary generated artifacts only.
# - Split-When:
#   - General guest runtime control flow replaces bounded C replay.
# - Merge-When:
#   - Generic loop induction adopts the same provenance contract.
# - Summary:
#   - Prove named loop counters through complete source C and Malbolge VM.
# - Description:
#   - Include binary parity, descending, forged sources and Clang bindings.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - An unproved name or unsafe loop refuses publication.

"""Named C induction with real Malbolge guest output and forged refusals."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_guest_byte_stride_loop_c_pipeline as previous

ROOT = previous.ROOT
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def program(name: str, *, initial: int = 0, bound: int = 6, step: str = "+= 2") -> str:
    """Rename every bound counter reference in a full live-input C program."""
    original = previous.program(initial, "!=", bound, f"i {step}")
    return re.sub(r"\bi\b", name, original)


class GuestByteNamedInductionCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(
            path.is_file()
            for path in (
                previous.previous.total.FRONTEND,
                previous.previous.total.ADAPTER,
                previous.previous.total.LAYOUT,
                previous.previous.total.VM,
            )
        ):
            self.skipTest("pinned Clang and normative guest VM required")

    def test_long_counter_runs_complete_live_byte_program(self) -> None:
        """The original counter name is irrelevant to VM-visible byte effects."""
        inputs = (
            *(bytes((v, v ^ 255)) for v in (0, 1, 127, 128, 255)),
            *(hashlib.shake_256(bytes((93, i))).digest(2) for i in range(8)),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "named.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(program("index"))
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in inputs:
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((data[0],) * 4 + (data[1],)))
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_reverse_named_counter_reaches_real_guest(self) -> None:
        """A descending long identifier retains the exact signed step."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "reverse.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(program("position", initial=6, bound=0, step="-= 2"))
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (b"\0\xff", b"\xff\0"):
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((data[0],) * 4 + (data[1],)))

    def test_name_and_step_forms_reach_layout(self) -> None:
        """Counter lengths, step grammars and direct guards prove same C IR."""
        shapes = (
            ("j", 0, "!=", 3, "++i", None),
            ("_cursor", 0, "!=", 3, "i++", None),
            ("index", 0, "!=", 6, "i = i + 2", None),
            ("position", 6, "!=", 0, "i = i - 2", None),
            ("count_0", 0, "!=", 3, "i++", None),
            ("index", 0, "<", 6, "i += 2", None),
            ("index", 0, "<=", 6, "i += 2", None),
            ("index", 0, "!=", 6, "i += 2", "index == 2"),
            ("index", 0, "!=", 6, "i += 2", "index"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, (name, initial, op, bound, step, guard) in enumerate(shapes):
                with self.subTest(name=name, op=op, step=step, guard=guard):
                    source = Path(directory) / f"shape-{index}.c"
                    original = previous.program(initial, op, bound, step)
                    c_source = re.sub(r"\bi\b", name, original)
                    if guard is not None:
                        c_source = c_source.replace(f"{name} % 2 == 0", guard)
                    _ = source.write_text(c_source)
                    guest = source.with_suffix(".malbolge")
                    result = subprocess.run(
                        [
                            str(previous.previous.ADAPTER),
                            "--layout-backend",
                            sys.executable,
                            "--output",
                            str(guest),
                            "--source",
                            str(source),
                            "--capsule",
                        ],
                        input=json.dumps(NORMALIZED(source)).encode(),
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(
                        b"layout backend exited unsuccessfully", result.stderr
                    )
                    self.assertFalse(guest.exists())

    def test_named_counter_direct_comparison_runs_in_guest(self) -> None:
        """A direct i32 comparison uses the same proven counter binding."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "direct.c"
            guest = source.with_suffix(".malbolge")
            text = program("index").replace("index % 2 == 0", "index == 2")
            _ = source.write_text(text)
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (b"\0\xff", b"\xff\0", b"\x80\x7f"):
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((data[0],) * 4 + (data[1],)))

    def test_mismatched_source_token_and_ast_binding_refuse(self) -> None:
        """Neither source-only nor AST-only counter replacement is sound."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "original.c"
            original = program("index")
            _ = source.write_text(original)
            normalized = NORMALIZED(source)
            nodes = cast("list[dict[str, object]]", normalized["nodes"])
            self.assertTrue(any(node.get("name") == "index" for node in nodes))

            forged = copy.deepcopy(normalized)
            forged_nodes = cast("list[dict[str, object]]", forged["nodes"])
            declaration = next(
                node for node in forged_nodes if node.get("name") == "index"
            )
            declaration["name"] = "round"
            guest = Path(directory) / "forged-ast.malbolge"
            result = PROJECT(forged, guest, source)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())

            _ = source.write_text(original.replace("index % 2", "round % 2"))
            guest = Path(directory) / "forged-source.malbolge"
            result = PROJECT(normalized, guest, source)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())

            # A body token extended into a different identifier is not a
            # valid source witness for the old Clang declaration reference.
            for label, mutation in (
                ("prefix-name", original.replace("index % 2", "index2 % 2")),
                ("header-name", original.replace("index != 6", "round != 6")),
                ("declarator", original.replace("int index", "int round")),
                ("step", original.replace("index += 2", "index -= 2")),
            ):
                with self.subTest(label=label):
                    _ = source.write_text(mutation)
                    guest = Path(directory) / f"{label}.malbolge"
                    result = PROJECT(normalized, guest, source)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())

            # Names are bounded at the authenticated source-grammar edge.
            source = Path(directory) / "too-long.c"
            _ = source.write_text(program("counter_name_" * 3))
            guest = source.with_suffix(".malbolge")
            result = PROJECT(NORMALIZED(source), guest, source)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    _ = unittest.main()
