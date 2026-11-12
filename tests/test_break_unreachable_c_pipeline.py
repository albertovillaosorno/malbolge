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
#   - Full C do-break unreachable output guest parity and refusal evidence.
# - Must-Not:
#   - Publish unexecuted C effects or replace guest execution with host output.
# - Allows:
#   - Inputs: pinned Clang source and normalized AST integrity mutations.
#   - Outputs: exact normative guest bytes or no artifact on failure.
#   - Side effects: temporary compilation and guest VM replay.
# - Split-When:
#   - Dynamic guest C control flow supersedes source-state projection.
# - Merge-When:
#   - General loop-exit tests cover unreachable lexical siblings.
# - Summary:
#   - A source-backed break skips both a putchar and a post-test condition.

"""Selected inner-loop break skips a lexical C output and do predicate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "tests/compiler/c-frontend/accepted/local_do_break_unreachable_fibonacci.c"
)
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"


def independent_oracle() -> bytes:
    previous, current = 1, 1
    output = bytearray()
    for _ in range(12):
        following = (previous + current) & 255
        previous, current = current, following
        if following & 1:
            output.append((following ^ 26) & 31)
        else:
            output.append(following & 31)
    return bytes(output)


class BreakUnreachablePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(p.is_file() for p in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler binaries not built")

    @staticmethod
    def compile(source: Path, guest: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/do-break-unreachable-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=120,
            env={**os.environ, "TMPDIR": str(ROOT / ".temp")},
        )

    def assert_guest_oracle(self, source: Path) -> None:
        expected = independent_oracle()
        self.assertEqual(expected, bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            guest = Path(folder) / "do-break-unreachable.malbolge"
            compiled = self.compile(source, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for stdin in (b"", bytes((255, 0, 128))):
                result = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=stdin,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)
                self.assertEqual(result.stderr, b"malbolge-steps-v1:47\n")

    def test_break_skips_lexical_output_and_do_predicate(self) -> None:
        self.assert_guest_oracle(SOURCE)

    def test_inverted_break_preserves_ordered_twelve_byte_guest(self) -> None:
        original = SOURCE.read_text()
        inverted = (
            original.replace("if ((next & 1U) != 0U)", "if ((next & 1U) == 0U)")
            .replace("putchar((int)((next ^ 0x1AU) & 31U));", "FIRST_OUTPUT;")
            .replace(
                "putchar((int)(next & 31U));", "putchar((int)((next ^ 0x1AU) & 31U));"
            )
            .replace("FIRST_OUTPUT;", "putchar((int)(next & 31U));")
            .replace(
                "((next & 1U) ? (1U / 0U) : 0U)",
                "((next & 1U) ? 0U : (1U / 0U))",
            )
        )
        self.assertNotEqual(original, inverted)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "inverted-break.c"
            source.write_text(inverted)
            self.assert_guest_oracle(source)

    def test_unsupported_source_mutations_never_publish(self) -> None:
        original = SOURCE.read_text()
        suffix = "            putchar((int)(next & 31U));"
        variants = {
            "hidden-input": original.replace(suffix, "            getchar();"),
            "dead-second-output": original.replace(
                suffix, suffix + "\n            putchar((int)(next & 31U));"
            ),
            "dead-state-write": original.replace(
                suffix, suffix + "\n            next += 1U;"
            ),
            "undefined-output": original.replace(
                suffix, "            putchar((int)(1U / 0U));"
            ),
            "selected-undefined-predicate": original.replace(
                "(1U / 0U) : 0U", "0U : (1U / 0U)"
            ),
            "break-replaced-input": original.replace(
                "                break;",
                "                getchar();\n                break;",
            ),
            "break-after-undefined": original.replace(
                "                break;",
                "                (void)(1U / 0U);\n                break;",
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for name, content in variants.items():
                with self.subTest(name=name):
                    self.assertNotEqual(content, original)
                    source = Path(folder) / f"{name}.c"
                    source.write_text(content)
                    guest = source.with_suffix(".malbolge")
                    compiled = self.compile(source, guest)
                    self.assertNotEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertFalse(guest.is_file())

    def test_forged_unreachable_output_ast_rejects_artifact(self) -> None:
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/do-break-unreachable-ast-v1",
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        baseline = json.loads(frontend.stdout)
        break_end = next(
            node["span"]["end"]["byte"]
            for node in baseline["nodes"]
            if node["kind"] == "break-statement"
        )
        tail = next(
            node
            for node in baseline["nodes"]
            if node["kind"] == "call-expression"
            and node["span"]["begin"]["byte"] > break_end
        )
        for field, mutation in (
            ("parent", 0),
            ("reference", "external:getchar"),
            ("kind", "binary-expression"),
            ("type", "u32"),
            ("span.begin.byte", tail["span"]["begin"]["byte"] + 1),
            ("span.begin.column", tail["span"]["begin"]["column"] + 1),
            ("span.end.byte", tail["span"]["end"]["byte"] + 1),
            ("span.end.column", tail["span"]["end"]["column"] + 1),
        ):
            with self.subTest(field=field):
                data = json.loads(frontend.stdout)
                node = data["nodes"][tail["id"] - 1]
                if field.startswith("span."):
                    _, part, position = field.split(".")
                    node["span"][part][position] = mutation
                else:
                    node[field] = mutation
                with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
                    guest = Path(folder) / "forged.malbolge"
                    compiled = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(data).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertFalse(guest.is_file())


if __name__ == "__main__":
    unittest.main()
