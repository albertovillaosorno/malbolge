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
#   - Exact C arithmetic identities over a successful resident guest byte.
# - Must-Not:
#   - Evaluate guest input at compile time or accept nonidentity arithmetic.
# - Allows:
#   - Inputs: source-authenticated pinned C AST and binary guest streams.
#   - Outputs: normative VM byte parity or fail-closed refusal.
#   - Side effects: isolated compiler artifacts only.
# - Split-When:
#   - General guest runtime arithmetic supersedes algebraic byte identities.
# - Merge-When:
#   - Live byte-expression lowering owns a generalized typed SSA evaluator.
# - Summary:
#   - Authentic arithmetic identity expressions preserve actual guest bytes.

"""Whole-C guest evidence for runtime-byte-preserving integer identities."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_comma_resident_output_return_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def source(*, expression: str = "current & 255", bound: int = 3) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        if (i % 2 == 0) {\n"
        f"            putchar({expression});\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(current);\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class GuestByteIdentityArithmeticCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler and normative VM tools required")

    def test_complete_loop_preserves_real_guest_byte_through_mask(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "identity.c"
            guest = root / "identity.malbolge"
            program.write_text(source(), encoding="utf-8")
            compiled = COMPILE(program, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255)),
                bytes((255, 0)),
                *(
                    hashlib.shake_256(bytes((83, index))).digest(2)
                    for index in range(12)
                ),
            ):
                with self.subTest(data=data):
                    result = RUN(guest, data)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, bytes((data[0],) * 4 + (data[1],)))
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:8\n")

    def test_multiple_mathematically_exact_byte_identities(self) -> None:
        # Four VM witnesses cover the modulo, bitwise, multiply and shift
        # families. The following frontend-only test covers all ten shapes.
        identities = (
            "current % 256",
            "current ^ 0",
            "current * 1",
            "current >> 0",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(identities):
                with self.subTest(expression=expression):
                    program = root / f"identity-{index}.c"
                    guest = root / f"identity-{index}.malbolge"
                    program.write_text(source(expression=expression), encoding="utf-8")
                    compiled = COMPILE(program, guest)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    data = bytes((0, 255)) if index % 2 == 0 else bytes((255, 0))
                    result = RUN(guest, data)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, bytes((data[0],) * 4 + (data[1],)))
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:8\n")

    def test_all_identity_operators_pass_frontend_proof(self) -> None:
        # This uses a deliberately failing layout executable to identify
        # frontend admission without claiming that it emits any guest code.
        # Actual guest execution is independently tested above.
        identities = (
            "current & 255",
            "current % 256",
            "current | 0",
            "current ^ 0",
            "current + 0",
            "current - 0",
            "current * 1",
            "current / 1",
            "current << 0",
            "current >> 0",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(identities):
                with self.subTest(expression=expression):
                    program = root / f"operator-{index}.c"
                    guest = root / f"operator-{index}.malbolge"
                    program.write_text(source(expression=expression), encoding="utf-8")
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            sys.executable,
                            "--output",
                            str(guest),
                            "--source",
                            str(program),
                            "--capsule",
                        ],
                        input=json.dumps(NORMALIZED(program)).encode(),
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(
                        b"layout backend exited unsuccessfully", result.stderr
                    )
                    self.assertFalse(guest.exists())

    def test_nonidentities_are_not_reinterpreted_as_byte_replay(self) -> None:
        expressions = (
            "current & 254",
            "current % 255",
            "current | 1",
            "current ^ 1",
            "current + 1",
            "current - 1",
            "current * 2",
            "current / 2",
            "current << 1",
            "current >> 1",
            "current + getchar()",
            "current && 1",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(expressions):
                with self.subTest(expression=expression):
                    program = root / f"rejected-{index}.c"
                    guest = root / f"rejected-{index}.malbolge"
                    program.write_text(source(expression=expression), encoding="utf-8")
                    compiled = COMPILE(program, guest)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_ast_and_source_identity_must_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "verified.c"
            program.write_text(source(), encoding="utf-8")
            normalized = NORMALIZED(program)
            nodes = cast(list[dict[str, object]], normalized["nodes"])
            for index, node in enumerate(nodes):
                begin = cast(dict[str, dict[str, int]], node["span"])["begin"]
                if begin["line"] != 6:
                    continue
                for field in ("parent", "span"):
                    with self.subTest(node=node["id"], field=field):
                        forged = copy.deepcopy(normalized)
                        mutated = cast(list[dict[str, object]], forged["nodes"])
                        if field == "parent":
                            mutated[index]["parent"] = 2
                        else:
                            span = cast(
                                dict[str, dict[str, int]], mutated[index]["span"]
                            )
                            span["begin"]["column"] += 1
                        guest = root / f"forged-{field}-{index}.malbolge"
                        result = PROJECT(forged, guest, program)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertFalse(guest.exists())
            for field, replacement in (
                ("literal", "254"),
                ("constant_integer", "254"),
            ):
                forged = copy.deepcopy(normalized)
                changed = cast(list[dict[str, object]], forged["nodes"])
                literal = next(n for n in changed if n["kind"] == "integer-literal")
                literal[field] = replacement
                guest = root / f"forged-literal-{field}.malbolge"
                result = PROJECT(forged, guest, program)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(guest.exists())
            for spoof_index, (original, substitute) in enumerate(
                (
                    ("current & 255", "current & 254"),
                    ("current & 255", "current + 255"),
                    ("current & 255", "currenz & 255"),
                )
            ):
                alternate = root / f"source-{spoof_index}.c"
                alternate.write_text(
                    source().replace(original, substitute), encoding="utf-8"
                )
                forged = copy.deepcopy(normalized)
                cast(dict[str, object], forged["source"])["sha256"] = hashlib.sha256(
                    alternate.read_bytes()
                ).hexdigest()
                guest = root / f"forged-{spoof_index}.malbolge"
                result = PROJECT(forged, guest, alternate)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(guest.exists())
            guest = root / "missing.malbolge"
            result = PROJECT(normalized, guest, None)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
