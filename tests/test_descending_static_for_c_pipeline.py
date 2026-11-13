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
#   - Descending source-proven C induction with binary guest byte effects.
# - Must-Not:
#   - Host-compute guest input or accept unchecked C loop arithmetic.
# - Allows:
#   - Inputs: pinned Clang C, forged normalized JSON, binary guest stdin.
#   - Outputs: normative VM byte/step parity and explicit unsupported results.
#   - Side effects: temporary compiled guest artifacts only.
# - Split-When:
#   - General guest-side mutable loop state is available.
# - Merge-When:
#   - Other source-proven loop directions share their finite proof.
# - Summary:
#   - Reverse induction chooses control without replaying runtime bytes.

"""Descending finite C loops emit actual runtime Malbolge input and output."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

from tests.test_induction_static_for_c_pipeline import (
    ADAPTER,
    DRIVER,
    FRONTEND,
    INCLUDE,
    LAYOUT,
    RESOURCE,
    ROOT,
    VM,
)

if TYPE_CHECKING:
    from subprocess import CompletedProcess


def program(
    start: int = 4, operator: str = ">=", bound: int = 1, step: str = "i--"
) -> str:
    """Build a complete source with guarded, selected runtime reads."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = {start}; i {operator} {bound}; {step}) {{\n"
        "        int current = getchar();\n"
        "        if (i == 3 || i == 2) {\n"
        "            putchar(putchar(current));\n"
        "            continue;\n"
        "        }\n"
        "        if (i == 1) {\n"
        "            break;\n"
        "        }\n"
        "        putchar(current);\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def oracle(start: int, operator: str, bound: int, data: bytes) -> tuple[bytes, int]:
    """Simulate C control independently of the Clang projection."""
    emitted = bytearray()
    reads = 0
    for i in range(start, bound - int(operator == ">="), -1):
        current = data[reads]
        reads += 1
        if i in (3, 2):
            emitted.extend((current, current))
            continue
        if i == 1:
            break
        emitted.append(current)
        emitted.append(data[reads])
        reads += 1
    emitted.append(data[reads])
    return bytes(emitted), reads + 1


def nested_program() -> str:
    """Mix forward outer and reverse inner induction with runtime bytes."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 0; i < 2; ++i) {\n"
        "        for (int i = 2; i > 0; --i) {\n"
        "            putchar(getchar());\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class DescendingStaticForCPipelineTests(unittest.TestCase):
    """Check whole-program compiler and VM output, plus trust refusal."""

    def setUp(self) -> None:
        """Require pinned source frontend, adapter, backend and guest VM."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and normative VM required")

    @staticmethod
    def compile(source: Path, target: Path) -> CompletedProcess[bytes]:
        """Compile actual C through the repository-selected guest pipeline."""
        return sp.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--capsule",
                "--output",
                str(target),
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=90,
        )

    @staticmethod
    def run_guest(target: Path, data: bytes) -> CompletedProcess[bytes]:
        """Execute an actual capsule on the normative VM."""
        return sp.run(
            [str(VM), str(target), "--input-stdin", "--report-steps"],
            input=data,
            capture_output=True,
            check=False,
            timeout=30,
        )

    @staticmethod
    def normalized(source: Path) -> dict[str, object]:
        """Get the exact pinned Clang normalized evidence."""
        result = sp.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "descending",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_reverse_unit_step_spellings(self) -> None:
        """Exercise both bounds and each canonical unit decrement spelling."""
        self.assert_reverse_parity(
            (
                (4, ">=", 1, "i--"),
                (4, ">", 0, "--i"),
                (4, ">=", 1, "i -= 1"),
            )
        )

    def test_reverse_short_loop_bounds(self) -> None:
        """Preserve one-, two- and three-trip descending induction values."""
        self.assert_reverse_parity(
            (
                (3, ">=", 1, "i--"),
                (2, ">", 0, "--i"),
                (1, ">=", 1, "i -= 1"),
            )
        )

    def test_reverse_nonzero_lower_bound(self) -> None:
        """A nonzero bound stops a descending loop before zero."""
        self.assert_reverse_parity(((9, ">", 7, "i--"),))

    def assert_reverse_parity(
        self, cases: tuple[tuple[int, str, int, str], ...]
    ) -> None:
        """Compile each C program and compare two binary guest oracles."""
        streams = (
            bytes((0, 255, 128, 1, 42, 9, 27, 45, 200, 7, 3, 99)),
            hashlib.shake_256(b"descending-seed-0xdec1").digest(12),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (start, operator, bound, step) in enumerate(cases):
                with self.subTest(case=index):
                    path = root / f"source-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(
                        program(start, operator, bound, step), encoding="utf-8"
                    )
                    result = self.compile(path, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for stream in streams:
                        expected, reads = oracle(start, operator, bound, stream)
                        guest = self.run_guest(target, stream)
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, expected)
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{reads + len(expected) + 1}\n".encode(),
                        )

    def test_mixed_nested_loop_directions(self) -> None:
        """Reverse shadowing stays within its inner loop and fresh reads."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            path = Path(directory) / "nested.c"
            target = path.with_suffix(".malbolge")
            path.write_text(nested_program(), encoding="utf-8")
            result = self.compile(path, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (
                bytes((0, 255, 2, 128, 1, 42, 9)),
                hashlib.shake_256(b"mixed-reverse").digest(7),
            ):
                guest = self.run_guest(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:15\n")

    def test_unsupported_reverse_loops_do_not_publish(self) -> None:
        """Invalid direction, induction value and strides fail closed."""
        sources = (
            program(start=0),
            program(start=10),
            program(start=4, operator="<", bound=1),
            program(start=4, operator="<=", bound=1),
            program(start=4, operator="!=", bound=1),
            program(start=4, operator=">", bound=4),
            program(start=4, operator=">=", bound=5),
            program(step="i++"),
            program(step="--i").replace("--i", "++i"),
            program(step="i -= 2"),
            program().replace("int i = 4", "int i = getchar()"),
            program().replace("i >= 1", "getchar() >= 1"),
            program().replace("int i = 4", "int i = 0x4"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, source in enumerate(sources):
                with self.subTest(index=index):
                    path = root / f"unsupported-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(source, encoding="utf-8")
                    self.assertNotEqual(self.compile(path, target).returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_reverse_ast_refuses(self) -> None:
        """Mutated loop metadata cannot silently publish guest output."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "source.c"
            source.write_text(program(), encoding="utf-8")
            original = self.normalized(source)
            nodes = original["nodes"]
            loop = next(n for n in nodes if n["kind"] == "for-statement")
            condition = next(
                n
                for n in nodes
                if n["parent"] == loop["id"] and n["kind"] == "binary-expression"
            )
            step = next(
                n
                for n in nodes
                if n["parent"] == loop["id"] and n.get("operation") == "--"
            )
            initial = next(n for n in nodes if n.get("literal") == "4")
            bound = next(
                n
                for n in nodes
                if n["parent"] == condition["id"] and n["kind"] == "integer-literal"
            )
            mutations = (
                (condition["id"], "operation", "<"),
                (condition["id"], "operation", "<="),
                (condition["id"], "operation", "=="),
                (condition["id"], "span.end.byte", 0),
                (step["id"], "operation", "++"),
                (step["id"], "parent", condition["id"]),
                (initial["id"], "literal", "5"),
                (initial["id"], "constant_integer", "5"),
                (bound["id"], "literal", "0"),
                (bound["id"], "span.begin.column", 0),
            )
            for index, (node_id, field, value) in enumerate(mutations):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    location = node
                    keys = field.split(".")
                    for key in keys[:-1]:
                        location = location[key]
                    location[keys[-1]] = value
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
