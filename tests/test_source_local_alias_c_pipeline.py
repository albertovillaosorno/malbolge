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
#   - Source-authenticated C local byte copies in real VM streams.
# - Must-Not:
#   - Add guest reads for aliases or admit guest arithmetic or stale bytes.
# - Allows:
#   - Inputs: pinned Clang C, forged JSON, binary guest stdin.
#   - Outputs: actual VM parity or fail-closed compiler refusal.
#   - Side effects: isolated temporary files.
# - Split-When:
#   - General C variable storage supersedes accumulator-local copies.
# - Merge-When:
#   - General source-byte expression lowering subsumes these identity copies.
# - Summary:
#   - A current live input can be copied into a new local without host I/O.

"""Authenticate byte-copy C declarations before reusing guest input SSA."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM


def source(
    alias: str = "int snapshot = current;",
    consumer: str = "snapshot",
    loop_alias: str = "",
    loop_consumer: str = "byte",
) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    {alias}\n"
        f"    putchar({consumer});\n"
        "    for (int i = 0; i < 4; ++i) {\n"
        "        int byte = getchar();\n"
        + (f"        {loop_alias}\n" if loop_alias else "")
        + "        if (i % 2 == 0) {\n"
        + f"            putchar({loop_consumer});\n"
        "            continue;\n"
        "        }\n"
        f"        putchar({loop_consumer});\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class SourceLocalAliasCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, compiler, layout and VM required")

    def test_compound_program_preserves_binary_inputs_across_local_copy(self) -> None:
        for index, alias, consumer in (
            (0, "int snapshot = current;", "snapshot"),
            (1, "int snapshot = current;\n    int duplicate = snapshot;", "duplicate"),
        ):
            with (
                self.subTest(index=index),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory,
            ):
                root = Path(directory)
                path = root / "alias.c"
                target = root / "alias.malbolge"
                path.write_text(source(alias, consumer), encoding="utf-8")
                compiled = helpers.StaticForBreakCPipelineTests.compile(path, target)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                for data in (
                    bytes((0, 255, 128, 1, 42, 13)),
                    hashlib.shake_256(b"C-alias-guest-2026").digest(6),
                ):
                    guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, data)
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:13\n")

    def test_loop_local_alias_keeps_each_iteration_input_live(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "loop-alias.c"
            target = root / "loop-alias.malbolge"
            path.write_text(
                source(loop_alias="int saved = byte;", loop_consumer="saved"),
                encoding="utf-8",
            )
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 13)),
                hashlib.shake_256(b"loop-C-alias-guest-2026").digest(6),
            ):
                guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:13\n")

    def test_zero_trip_and_scoped_alias_preserve_effect_order(self) -> None:
        scoped = source().replace(
            "            putchar(byte);\n            continue;",
            "            int saved = byte;\n"
            "            putchar(saved);\n"
            "            continue;",
        )
        zero = source(loop_alias="int saved = byte;", loop_consumer="saved")
        zero = zero.replace("i < 4", "i < 0")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for name, candidate, data in (
                ("scoped", scoped, bytes((0, 255, 128, 1, 42, 13))),
                ("empty", zero, bytes((128, 255))),
            ):
                with self.subTest(name=name):
                    path = root / f"{name}.c"
                    target = root / f"{name}.malbolge"
                    path.write_text(candidate, encoding="utf-8")
                    compiled = helpers.StaticForBreakCPipelineTests.compile(
                        path, target
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, data)
                    self.assertEqual(
                        guest.stderr,
                        f"malbolge-steps-v1:{len(data) * 2 + 1}\n".encode(),
                    )

    def test_loop_alias_unproved_expressions_refuse(self) -> None:
        candidates = (
            ("int saved = byte + 1;", "saved"),
            ("int saved = getchar();", "byte"),
            ("int saved = (unsigned char)byte;", "saved"),
            ("int saved = byte;\n        getchar();", "saved"),
            ("int saved = byte;", "byte"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (alias, consumer) in enumerate(candidates):
                with self.subTest(index=index):
                    path = root / f"loop-negative-{index}.c"
                    target = root / f"loop-negative-{index}.malbolge"
                    path.write_text(
                        source(loop_alias=alias, loop_consumer=consumer),
                        encoding="utf-8",
                    )
                    compiled = helpers.StaticForBreakCPipelineTests.compile(
                        path, target
                    )
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

    def test_unsupported_alias_sources_fail_closed(self) -> None:
        aliases = (
            ("int snapshot = current + 1;", "snapshot"),
            ("int snapshot = getchar();", "current"),
            ("int snapshot = (unsigned char)current;", "snapshot"),
            ("int snapshot;", "snapshot"),
            ("int snapshot = current;", "current"),
            ("int current = current;", "current"),
            ("int snapshot = byte;", "snapshot"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (alias, consumer) in enumerate(aliases):
                with self.subTest(index=index):
                    path = root / f"negative-{index}.c"
                    target = root / f"negative-{index}.malbolge"
                    path.write_text(source(alias, consumer), encoding="utf-8")
                    result = helpers.StaticForBreakCPipelineTests.compile(path, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_alias_nodes_and_missing_witness_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "alias.c"
            path.write_text(source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            nodes = normalized["nodes"]
            declaration = next(
                n
                for n in nodes
                if n["kind"] == "variable-declaration" and n.get("name") == "snapshot"
            )
            alias_id = declaration["id"]
            mutations = (
                (alias_id, "name", "spoofed"),
                (alias_id, "reference", "current@47"),
                (alias_id, "type", "i8"),
                (alias_id, "parent", 2),
                (alias_id + 1, "operation", "integral-cast"),
                (alias_id + 2, "reference", "external:getchar"),
                (alias_id + 2, "parent", 2),
                (alias_id + 2, "span", {"begin": {"byte": 0}}),
            )
            for index, mutation in enumerate(mutations):
                with self.subTest(index=index):
                    modified = copy.deepcopy(normalized)
                    node_id, field, value = mutation
                    next(n for n in modified["nodes"] if n["id"] == node_id)[field] = (
                        value
                    )
                    target = root / f"forged-{index}.malbolge"
                    result = self.adapter(modified, target, path)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())
            target = root / "no-witness.malbolge"
            missing = self.adapter(normalized, target, None)
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse(target.exists())

    @staticmethod
    def adapter(
        normalized: dict[str, object], target: Path, source_path: Path | None
    ) -> subprocess.CompletedProcess[bytes]:
        command = [
            str(ADAPTER),
            "--layout-backend",
            str(LAYOUT),
            "--output",
            str(target),
        ]
        if source_path is not None:
            command.extend(("--source", str(source_path)))
        command.append("--capsule")
        return subprocess.run(
            command,
            input=json.dumps(normalized).encode(),
            capture_output=True,
            check=False,
            timeout=30,
        )


if __name__ == "__main__":
    unittest.main()
