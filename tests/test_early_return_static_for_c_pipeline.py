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
#   - Early void-return source proof and normative guest byte-stream parity.
# - Must-Not:
#   - Drop unchecked dead source, replay stdin on the host or trust forged AST.
# - Allows:
#   - Inputs: pinned C source, binary guest stdin and forged normalized nodes.
#   - Outputs: real Malbolge output parity or no published guest artifact.
#   - Side effects: isolated temporary artifacts.
# - Split-When:
#   - General guest runtime C returns supersede finite source proof.
# - Merge-When:
#   - Source-authenticated C control lowering owns the complete return proof.
# - Summary:
#   - A selected return exits the entire C function, not just one loop.

"""Finite source-proven C returns halt the actual normative Malbolge guest."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_static_for_break_c_pipeline import (
    ADAPTER,
    DRIVER,
    FRONTEND,
    INCLUDE,
    LAYOUT,
    RESOURCE,
    ROOT,
    VM,
)


def source(predicate: str = "i == 2") -> str:
    """Return on a selected source-proven trip, leaving a dead C suffix."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 0; i < 4; i++) {\n"
        "        int current = getchar();\n"
        f"        if ({predicate}) {{\n"
        "            putchar(putchar(current));\n"
        "            return;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def nested_source() -> str:
    """The inner return must terminate both loops and the outer suffix."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    for (int i = 0; i < 2; i++) {\n"
        "        for (int i = 0; i < 3; i++) {\n"
        "            int current = getchar();\n"
        "            if (i == 1) {\n"
        "                putchar(putchar(current));\n"
        "                return;\n"
        "            }\n"
        "            putchar(current);\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class EarlyReturnStaticForCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(x.is_file() for x in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler, layout and normative VM required")

    @staticmethod
    def compile(source_path: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--capsule",
                "--output",
                str(target),
                str(source_path),
            ],
            capture_output=True,
            check=False,
            timeout=120,
            env={**os.environ, "TMPDIR": str(source_path.parent)},
        )

    @staticmethod
    def normalize(path: Path) -> dict:
        result = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/early-return-c-v1",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=30,
            env={**os.environ, "TMPDIR": str(path.parent)},
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_selected_and_unselected_returns_match_binary_guest_oracles(self) -> None:
        streams = (
            bytes((0, 255, 128, 1, 42, 9)),
            hashlib.shake_256(b"early-void-return-2330").digest(6),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for predicate in ("i == 2", "i == 8"):
                path = root / f"return-{predicate[-1]}.c"
                target = path.with_suffix(".malbolge")
                path.write_text(source(predicate), encoding="utf-8")
                result = self.compile(path, target)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(target.is_file())
                for data in streams:
                    with self.subTest(predicate=predicate, data=data):
                        result = subprocess.run(
                            [
                                str(VM), str(target), "--input-stdin",
                                "--report-steps",
                            ],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        if predicate == "i == 2":
                            expected = bytes((data[0], data[1], data[2], data[2]))
                            reads = 3
                        else:
                            expected = data[:5]
                            reads = 5
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout, expected)
                        self.assertEqual(
                            result.stderr,
                            f"malbolge-steps-v1:{reads + len(expected) + 1}\n".encode(),
                        )

    def test_nested_return_exits_both_loops(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "nested.c"
            target = path.with_suffix(".malbolge")
            path.write_text(nested_source(), encoding="utf-8")
            result = self.compile(path, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (
                bytes((255, 0, 128, 1, 42, 9)),
                hashlib.shake_256(b"nested-return-2330").digest(6),
            ):
                guest = subprocess.run(
                    [str(VM), str(target), "--input-stdin", "--report-steps"],
                    input=data,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, bytes((data[0], data[1], data[1])))
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:6\n")


    def test_direct_if_returns_and_unreachable_zero_trip(self) -> None:
        """Return proof respects static top-level arms and zero-trip loops."""
        conditional = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    putchar(getchar());\n"
            "    if ({predicate}) {\n"
            "        putchar(putchar(getchar()));\n"
            "        return;\n"
            "    }\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        direct = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    putchar(getchar());\n"
            "    return;\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        cases = (
            ("selected", conditional.replace("{predicate}", "1"), (0, 1, 1), 2),
            ("unselected", conditional.replace("{predicate}", "0"), (0, 1), 2),
            ("direct", direct, (0,), 1),
            ("zero-trip", source().replace("i < 4", "i < 0"), (0,), 1),
        )
        samples = (
            bytes((0, 255, 128, 42, 1)),
            hashlib.shake_256(b"dead-return-2330").digest(5),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for label, candidate, indexes, reads in cases:
                with self.subTest(label=label):
                    source_path = root / f"{label}.c"
                    target = source_path.with_suffix(".malbolge")
                    source_path.write_text(candidate, encoding="utf-8")
                    result = self.compile(source_path, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in samples:
                        guest = subprocess.run(
                            [
                                str(VM), str(target), "--input-stdin",
                                "--report-steps",
                            ],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        expected = bytes(data[index] for index in indexes)
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(guest.stdout, expected)
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{reads + len(expected) + 1}\n".encode(),
                        )

    def test_guest_dependent_and_unsupported_dead_effects_refuse(self) -> None:
        original = source()
        invalid = (
            original.replace("if (i == 2)", "if (current)"),
            original.replace("return;", "return (void)getchar();"),
            original.replace("return;", "return 3;"),
            original.replace("putchar(getchar());\n}", "putchar(getchar() + 1);\n}"),
            original.replace("return;", "return;\n            getchar();"),
            original.replace("putchar(current);\n    }", "putchar(current + 1);\n    }"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, candidate in enumerate(invalid):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(candidate, encoding="utf-8")
                    result = self.compile(path, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_return_metadata_refuses_before_guest_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "original.c"
            path.write_text(source(), encoding="utf-8")
            artifact = self.normalize(path)
            returns = [x for x in artifact["nodes"] if x["kind"] == "return-statement"]
            self.assertEqual(len(returns), 1)
            selected = returns[0]
            variants = (
                ("parent", 0),
                ("kind", "break-statement"),
                ("type", "i32"),
                ("operation", "++"),
                ("reference", "external:getchar"),
                ("span.begin.byte", selected["span"]["begin"]["byte"] + 1),
                ("span.begin.column", selected["span"]["begin"]["column"] + 1),
                ("span.end.byte", selected["span"]["end"]["byte"] + 1),
                ("span.end.column", selected["span"]["end"]["column"] + 1),
            )
            for index, (field, value) in enumerate(variants):
                with self.subTest(field=field):
                    forged = copy.deepcopy(artifact)
                    node = next(x for x in forged["nodes"] if x["id"] == selected["id"])
                    target = node
                    parts = field.split(".")
                    for part in parts[:-1]:
                        target = target[part]
                    target[parts[-1]] = value
                    guest = root / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                        env={**os.environ, "TMPDIR": str(root)},
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
