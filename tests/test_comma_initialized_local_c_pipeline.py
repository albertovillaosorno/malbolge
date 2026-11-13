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
#   - Live source-C comma initializers with ordered guest input/output effects.
# - Must-Not:
#   - Fold guest inputs, assume EOF, or resurrect overwritten C local storage.
# - Allows:
#   - Inputs: pinned Clang C and binary guest stdin.
#   - Outputs: normative VM parity and rejected forged source/Clang ancestry.
#   - Side effects: isolated temporary artifacts only.
# - Split-When:
#   - General source-C expression lowering subsumes comma initializer proof.
# - Merge-When:
#   - The source-local input grammar gains a common expression evaluator.
# - Summary:
#   - Authenticate left-to-right C comma initializer effects in guest bytecode.
# - Description:
#   - Check real guest I/O parity and reject forged comma initialization.
# - Usage:
#   - python3.14 -B -m unittest tests.test_comma_initialized_local_c_pipeline
# - Defaults:
#   - No EOF, output-failure, general storage or dependent control support.

"""Complete source-C comma initializer streams execute on the actual guest."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests.test_source_local_alias_c_pipeline import (
    SourceLocalAliasCPipelineTests,
)
from tests.test_static_for_break_c_pipeline import (
    ADAPTER,
    FRONTEND,
    LAYOUT,
    ROOT,
    VM,
    StaticForBreakCPipelineTests,
)

COMPILE = StaticForBreakCPipelineTests.compile
PROJECT = SourceLocalAliasCPipelineTests.adapter
TRIPLE = "(getchar(), putchar(putchar(getchar())), getchar())"
SEED_PREFIX = b"comma-initialized-local-"


def program(*, initializer: str = "(putchar(getchar()), getchar())") -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    int seen = {initializer};\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        "        if (i % 2 == 0) {\n"
        "            putchar(seen);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(seen);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class CommaInitializedLocalCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned Clang, adapter, layout and VM required")

    def test_complete_branch_loop_binary_guest_parity(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "whole.c", root / "whole.malbolge"
            _ = source.write_text(program(), encoding="utf-8")
            result = COMPILE(source, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            streams = (
                bytes((0, 255, 128)),
                bytes((255, 0, 1)),
                bytes((128, 7, 0)),
                *(
                    hashlib.shake_256(SEED_PREFIX + bytes((i,))).digest(3)
                    for i in range(16)
                ),
            )
            for data in streams:
                with self.subTest(data=data):
                    guest = StaticForBreakCPipelineTests.vm(target, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes((data[0], data[1], data[1], data[1], data[2])),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:9\n")

    def test_three_operand_comma_and_nested_successful_returns(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "triple.c", root / "triple.malbolge"
            _ = source.write_text(
                program(initializer=TRIPLE),
                encoding="utf-8",
            )
            compiled = COMPILE(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1)),
                bytes((255, 0, 1, 128)),
                hashlib.shake_256(b"triple-comma-effects").digest(4),
            ):
                guest = StaticForBreakCPipelineTests.vm(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(
                    guest.stdout,
                    bytes((data[1],) * 2 + (data[2],) * 3 + (data[3],)),
                )
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:11\n")

    def test_scoped_branch_and_counted_loop_effects(self) -> None:
        for selected in (0, 1):
            with (
                self.subTest(selected=selected),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory,
            ):
                root = Path(directory)
                source = root / "scoped.c"
                target = root / "scoped.malbolge"
                _ = source.write_text(
                    "#include <stdio.h>\n"
                    + "void stream(void) {\n"
                    + "    int anchor = getchar();\n"
                    + f"    if ({selected}) {{\n"
                    + "        int seen = (putchar(getchar()), getchar());\n"
                    + "        putchar(seen);\n"
                    + "    } else {\n"
                    + "        putchar(anchor);\n"
                    + "    }\n"
                    + "    for (int i = 0; i < 2; ++i) {\n"
                    + "        int stage = (getchar(), putchar(getchar()));\n"
                    + "        putchar(stage);\n"
                    + "    }\n"
                    + "    putchar(getchar());\n"
                    + "}\n",
                    encoding="utf-8",
                )
                compiled = COMPILE(source, target)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                count = 8 if selected else 6
                for data in (
                    bytes((0, 255, 128, 1, 42, 7, 254, 3))[:count],
                    hashlib.shake_256(
                        b"scoped-comma-local-" + bytes((selected,))
                    ).digest(count),
                ):
                    guest = StaticForBreakCPipelineTests.vm(target, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    skipped_prefix = (data[0], data[2], data[2])
                    expected = (
                        bytes(
                            (
                                data[1],
                                data[2],
                                data[4],
                                data[4],
                                data[6],
                                data[6],
                                data[7],
                            )
                        )
                        if selected
                        else bytes(
                            skipped_prefix + (data[4], data[4], data[5]),
                        )
                    )
                    self.assertEqual(guest.stdout, expected)
                    steps = count + len(expected) + 1
                    self.assertEqual(
                        guest.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                    )

    def test_source_witness_cannot_hide_extra_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            original = root / "original.c"
            _ = original.write_text(program(), encoding="utf-8")
            normalized = StaticForBreakCPipelineTests.normalized(original)
            modified_source = program().replace(
                "(putchar(getchar()), getchar())",
                "(getchar()         , getchar())",
            )
            self.assertEqual(len(modified_source), len(program()))
            forged = root / "forged.c"
            _ = forged.write_text(modified_source, encoding="utf-8")
            candidate = copy.deepcopy(normalized)
            source_record = cast(dict[str, object], candidate["source"])
            source_record["sha256"] = hashlib.sha256(
                modified_source.encode()
            ).hexdigest()
            target = root / "forged.malbolge"
            result = PROJECT(candidate, target, forged)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

            missing = root / "missing.malbolge"
            result = PROJECT(normalized, missing, None)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(missing.exists())

    def test_unsupported_initializer_refuses_publication(self) -> None:
        variants = (
            "(putchar(getchar()), getchar() + 1)",
            "(putchar(getchar()), 42)",
            "(putchar(getchar()), seen)",
            "(fputc(getchar(), stdout), getchar())",
            "(putchar(getchar()) + 1, getchar())",
            "(putchar(getchar()), getchar(), seen)",
            "(putchar(getchar()), (unsigned char)getchar())",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, initializer in enumerate(variants):
                with self.subTest(initializer=initializer):
                    source = root / f"bad-{index}.c"
                    target = root / f"bad-{index}.malbolge"
                    _ = source.write_text(
                        program(initializer=initializer), encoding="utf-8"
                    )
                    result = COMPILE(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_previous_input_is_stale_after_comma_initialization(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, initializer in enumerate(
                ("(getchar(), getchar())", "(putchar(getchar()), getchar())")
            ):
                with self.subTest(initializer=initializer):
                    source = root / f"stale-{index}.c"
                    target = root / f"stale-{index}.malbolge"
                    _ = source.write_text(
                        "#include <stdio.h>\n"
                        + "void stream(void) {\n"
                        + "    int before = getchar();\n"
                        + f"    int seen = {initializer};\n"
                        + "    putchar(before);\n"
                        + "    putchar(seen);\n"
                        + "}\n",
                        encoding="utf-8",
                    )
                    result = COMPILE(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_clang_nodes_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            _ = source.write_text(program(), encoding="utf-8")
            original = StaticForBreakCPipelineTests.normalized(source)
            for index, (node, field, value) in enumerate(
                (
                    (4, "parent", 2),
                    (5, "kind", "binary-expression"),
                    (5, "operation", ","),
                    (6, "parent", 4),
                    (6, "operation", "+"),
                    (7, "parent", 5),
                    (7, "reference", "external:getchar"),
                    (8, "operation", "lvalue-to-rvalue"),
                    (10, "reference", "external:putchar"),
                    (13, "reference", "external:putchar"),
                )
            ):
                with self.subTest(node=node, field=field, value=value):
                    forged = copy.deepcopy(original)
                    nodes = cast(list[dict[str, object]], forged["nodes"])
                    nodes[node - 1][field] = value
                    target = root / f"forged-{index}.malbolge"
                    # The adapter never publishes an artifact on a false proof.
                    result = PROJECT(forged, target, source)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())
