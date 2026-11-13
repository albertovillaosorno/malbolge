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
#   - C assignment-style finite loop steps with live guest byte streams.
# - Must-Not:
#   - Trust unverified arithmetic or evaluate runtime bytes on the host.
# - Allows:
#   - Inputs: pinned source C, mutated normalized nodes and guest stdin.
#   - Outputs: compiled VM parity and explicit unsupported rejection.
#   - Side effects: isolated compiled guest artifacts only.
# - Split-When:
#   - Guest-side general C induction replaces static step authentication.
# - Merge-When:
#   - Other finite source-authenticated C unit-step proofs share a contract.
# - Summary:
#   - Assignment-shaped unit steps select control, not runtime byte values.

"""Source-authenticated assignment-style C loop steps reach the real VM."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import test_descending_static_for_c_pipeline as descending
from tests.test_induction_static_for_c_pipeline import (
    ADAPTER,
    FRONTEND,
    LAYOUT,
    ROOT,
    VM,
)


def program(
    *,
    initial: int = 0,
    operator: str = "<",
    bound: int = 4,
    step: str = "i = i + 1",
    first: int = 1,
    last: int = 3,
) -> str:
    """Mix source-time induction control with fresh guest input and outputs."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = {initial}; i {operator} {bound}; {step}) {{\n"
        "        int current = getchar();\n"
        f"        if (i == {first}) {{\n"
        "            putchar(putchar(current));\n"
        "            continue;\n"
        "        }\n"
        f"        if (i == {last}) {{\n"
        "            break;\n"
        "        }\n"
        "        putchar(current);\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def oracle(values: range, first: int, last: int, data: bytes) -> tuple[bytes, int]:
    """Independently model C control, preserving ordered guest byte reads."""
    emitted = bytearray()
    read = 0
    for i in values:
        current = data[read]
        read += 1
        if i == first:
            emitted.extend((current, current))
            continue
        if i == last:
            break
        emitted.append(current)
        emitted.append(data[read])
        read += 1
    emitted.append(data[read])
    return bytes(emitted), read + 1


class AssignedStepStaticForCPipelineTests(unittest.TestCase):
    """Compare actual Malbolge with a C semantics oracle."""

    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend and guest VM required")

    def test_assignment_steps_execute_live_binary_stream(self) -> None:
        """Both directions use the actual induction value and fresh reads."""
        variants = (
            (0, "<", 4, "i = i + 1", 1, 3, range(4)),
            (4, ">=", 1, "i = i - 1", 3, 1, range(4, 0, -1)),
            (1, "<=", 4, "i = i + 1", 2, 4, range(1, 5)),
            (4, ">", 0, "i = i - 1", 3, 1, range(4, 0, -1)),
            (0, "<", 0, "i = i + 1", 1, 3, range(0)),
        )
        streams = (
            bytes((0, 255, 128, 1, 42, 11, 127, 233, 16, 99)),
            hashlib.shake_256(b"assigned-step-live-stream").digest(10),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (start, op, bound, step, first, last, trips) in enumerate(
                variants
            ):
                with self.subTest(index=index):
                    path = root / f"assigned-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(
                        program(
                            initial=start,
                            operator=op,
                            bound=bound,
                            step=step,
                            first=first,
                            last=last,
                        )
                    )
                    compiled = descending.DescendingStaticForCPipelineTests.compile(
                        path, target
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in streams:
                        expected, reads = oracle(trips, first, last, data)
                        vm = descending.DescendingStaticForCPipelineTests.run_guest(
                            target, data
                        )
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(vm.stdout, expected)
                        self.assertEqual(
                            vm.stderr,
                            f"malbolge-steps-v1:{reads + len(expected) + 1}\n".encode(),
                        )

    def test_nested_opposite_assignment_steps_keep_guest_order(self) -> None:
        """A shadowed countdown uses separate, authenticated loop state."""
        source = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    for (int i = 0; i < 2; i = i + 1) {\n"
            "        for (int i = 2; i > 0; i = i - 1) {\n"
            "            putchar(getchar());\n"
            "        }\n"
            "        putchar(getchar());\n"
            "    }\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory) / "shadowed.c"
            target = path.with_suffix(".malbolge")
            path.write_text(source)
            compiled = descending.DescendingStaticForCPipelineTests.compile(
                path, target
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 11, 127)),
                hashlib.shake_256(b"shadowed-assigned-induction").digest(7),
            ):
                guest = descending.DescendingStaticForCPipelineTests.run_guest(
                    target, data
                )
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:15\n")

    def test_invalid_assignment_steps_fail_closed(self) -> None:
        """Unknown writes, wrong stride and dynamic steps cannot publish."""
        sources = (
            program(step="i = i + 2"),
            program(step="i = i - 1"),
            program(step="i = 1 + i"),
            program(step="i = i * 1"),
            program(step="i = getchar() + 1"),
            program(step="i = i + 1 + 0"),
            program(initial=4, operator=">", bound=0, step="i = i + 1"),
            program(initial=4, operator=">", bound=0, step="i = i - 2"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, source in enumerate(sources):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(source)
                    compiled = descending.DescendingStaticForCPipelineTests.compile(
                        path, target
                    )
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_step_nodes_fail_closed(self) -> None:
        """Every field in the additional assignment ancestry is checked."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "original.c"
            path.write_text(program())
            original = descending.DescendingStaticForCPipelineTests.normalized(path)
            nodes = original["nodes"]
            assignment = next(n for n in nodes if n.get("operation") == "=")
            addition = next(n for n in nodes if n.get("operation") == "+")
            rhs_read = next(
                n
                for n in nodes
                if n["parent"] == addition["id"] and n["kind"] == "cast-expression"
            )
            one = next(
                n
                for n in nodes
                if n["parent"] == addition["id"] and n["kind"] == "integer-literal"
            )
            changes = (
                (assignment["id"], "operation", "+="),
                (assignment["id"], "parent", 999),
                (assignment["id"], "span.end.byte", 1),
                (addition["id"], "operation", "-"),
                (addition["id"], "parent", 999),
                (rhs_read["id"], "operation", "integral-cast"),
                (rhs_read["id"], "span.begin.column", 1),
                (one["id"], "literal", "2"),
                (one["id"], "parent", 999),
            )
            for index, (node_id, field, value) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    keys = field.split(".")
                    target_field = node
                    for key in keys[:-1]:
                        target_field = target_field[key]
                    target_field[keys[-1]] = value
                    target = root / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(target),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
