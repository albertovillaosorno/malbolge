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
#   - Source-proven nonexecuting C loops and live Malbolge I/O parity.
# - Must-Not:
#   - Emit dead-loop reads or trust unchecked Clang body nodes.
# - Allows:
#   - Inputs: pinned Clang C, forged AST and binary guest stdin.
#   - Outputs: guest VM oracles and explicit source/AST refusals.
#   - Side effects: isolated guest artifacts.
# - Split-When:
#   - General guest-side C loop execution replaces static iteration proof.
# - Merge-When:
#   - Finite induction boundary tests share one source proof.
# - Summary:
#   - Even dead C loop bodies are authenticated without guest execution.

"""Zero-trip source-C loops preserve the real guest-effect trace."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import tempfile
import unittest
from pathlib import Path

from tests.test_descending_static_for_c_pipeline import (
    ADAPTER,
    FRONTEND,
    LAYOUT,
    ROOT,
    VM,
    DescendingStaticForCPipelineTests,
)


def whole_program(start: int = 0, operator: str = "<", bound: int = 0) -> str:
    """Select a truly empty loop before a nontrivial guest byte stream."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = {start}; i {operator} {bound}; ++i) {{\n"
        "        int dead = getchar();\n"
        "        if (i == 0) {\n"
        "            putchar(putchar(dead));\n"
        "            continue;\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        "        int current = getchar();\n"
        "        if (i == 1) {\n"
        "            putchar(putchar(current));\n"
        "            continue;\n"
        "        }\n"
        "        if (i == 2) {\n"
        "            break;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def nested_program() -> str:
    """Shadow the outer induction inside an unreachable inner loop."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 0; i < 2; ++i) {\n"
        "        for (int i = 1; i > 1; --i) {\n"
        "            putchar(getchar());\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class ZeroTripStaticForCPipelineTests(unittest.TestCase):
    """Compare actual guest effects, never host-emulated output."""

    def setUp(self) -> None:
        """Require the real frontend, adapter, layout and normative VM."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and normative VM required")

    def test_empty_loop_before_selected_continue_and_break(self) -> None:
        """No dead-loop reads may consume bytes or write guest output."""
        streams = (
            bytes((0, 255, 128, 1)),
            hashlib.shake_256(b"zero-trip-live-c").digest(4),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (start, operator, bound) in enumerate(
                ((0, "<", 0), (1, "<=", 0), (1, "<", 0))
            ):
                with self.subTest(index=index):
                    path = root / f"zero-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(whole_program(start, operator, bound))
                    compiled = DescendingStaticForCPipelineTests.compile(path, target)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in streams:
                        # i=0 writes once, i=1 twice, i=2 reads then breaks;
                        # the trailing read contributes the final byte.
                        expected = bytes((data[0], data[1], data[1], data[3]))
                        guest = DescendingStaticForCPipelineTests.run_guest(
                            target, data
                        )
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, expected)
                        self.assertEqual(guest.stderr, b"malbolge-steps-v1:9\n")

    def test_unreachable_nested_loop_does_not_consume_input(self) -> None:
        """Inner dead source C is proven without replaying guest effects."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory) / "nested.c"
            target = path.with_suffix(".malbolge")
            path.write_text(nested_program())
            compiled = DescendingStaticForCPipelineTests.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255, 128)), bytes((42, 11, 7))):
                guest = DescendingStaticForCPipelineTests.run_guest(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:7\n")

    def test_invalid_zero_trip_body_refuses_publication(self) -> None:
        """An unexecuted loop must not hide arbitrary source-C statements."""
        sources = (
            whole_program().replace("putchar(putchar(dead));", "dead += 1;"),
            whole_program().replace("putchar(getchar());", 'puts("bad");', 1),
            whole_program().replace("int dead = getchar();", "int dead = 3;"),
            whole_program().replace("i < 0", "getchar() < 0", 1),
            whole_program().replace("i < 0", "i != 0", 1),
            whole_program().replace("++i)", "i += 2)", 1),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, source in enumerate(sources):
                with self.subTest(index=index):
                    path = root / f"unsupported-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(source)
                    result = DescendingStaticForCPipelineTests.compile(path, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_unreachable_nodes_refuse_publication(self) -> None:
        """Dead body AST changes are checked even without a guest trip."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "base.c"
            path.write_text(whole_program())
            original = DescendingStaticForCPipelineTests.normalized(path)
            nodes = original["nodes"]
            dead_loop = next(n for n in nodes if n["kind"] == "for-statement")
            dead_call = next(
                n
                for n in nodes
                if n["kind"] == "call-expression"
                and n.get("reference") == "external:getchar"
            )
            dead_condition = next(
                n
                for n in nodes
                if n["parent"] == dead_loop["id"] and n["kind"] == "binary-expression"
            )
            changes = (
                (dead_loop["id"], "parent", 999),
                (dead_loop["id"], "span.begin.byte", 0),
                (dead_call["id"], "reference", "external:putchar"),
                (dead_call["id"], "parent", 999),
                (dead_condition["id"], "operation", "<="),
                (dead_condition["id"], "span.end.byte", 0),
            )
            for index, (node_id, field, value) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    keys = field.split(".")
                    destination = node
                    for key in keys[:-1]:
                        destination = destination[key]
                    destination[keys[-1]] = value
                    target = root / f"forged-{index}.malbolge"
                    result = sp.run(
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
