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
#   - Complete C if-continue source proof and real guest-output regression.
# - Must-Not:
#   - Execute skipped C output on the host or silently ignore hidden calls.
# - Allows:
#   - Inputs: pinned Clang source and normalized AST integrity mutations.
#   - Outputs: exact normative guest bytes or no artifact on failure.
#   - Side effects: temporary local compilation and guest VM replay.
# - Split-When:
#   - Dynamic guest control flow replaces source-state projection.
# - Merge-When:
#   - General loop-exit testing covers unreachable source siblings.
# - Summary:
#   - A selected continue skips one authenticated lexical output statement.

"""Source-checked unreachable sibling output in a full Fibonacci C guest."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/local_if_continue_fibonacci.c"
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
            continue
        output.append(following & 31)
    return bytes(output)


class ConditionalContinuePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
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
                "tests/if-continue-complete-c-v1",
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
            guest = Path(folder) / "if-continue.malbolge"
            compiled = self.compile(source, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                execution = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(execution.returncode, 0, execution.stderr)
                self.assertEqual(execution.stdout, expected)
                self.assertEqual(execution.stderr, b"malbolge-steps-v1:47\n")

    def test_complete_conditional_continue_guest(self) -> None:
        self.assert_guest_oracle(SOURCE)

    def test_inverted_conditional_still_skips_one_output(self) -> None:
        original = SOURCE.read_text()
        inverted = (
            original.replace("if ((next & 1U) != 0U)", "if ((next & 1U) == 0U)")
            .replace("putchar((int)((next ^ 0x1AU) & 31U));", "FIRST_OUTPUT;")
            .replace(
                "putchar((int)(next & 31U));", "putchar((int)((next ^ 0x1AU) & 31U));"
            )
            .replace("FIRST_OUTPUT;", "putchar((int)(next & 31U));")
        )
        self.assertNotEqual(inverted, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "inverted-continue.c"
            source.write_text(inverted)
            self.assert_guest_oracle(source)

    def test_hidden_and_unproved_siblings_never_publish(self) -> None:
        original = SOURCE.read_text()
        tail = "        putchar((int)(next & 31U));"
        variants = {
            "hidden-getchar": original.replace(tail, "        getchar();"),
            "second-dead-output": original.replace(
                tail, tail + "\n        putchar((int)(next & 31U));"
            ),
            "dead-assignment": original.replace(tail, "        next += 1U;\n" + tail),
            "undefined-dead-output": original.replace(
                tail, "        putchar((int)(1U / 0U));"
            ),
            "undefined-selected-output": original.replace(
                "(next ^ 0x1AU) & 31U", "1U / 0U"
            ),
            "hidden-branch-input": original.replace(
                "            continue;", "            getchar();\n            continue;"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for name, source_text in variants.items():
                with self.subTest(name=name):
                    self.assertNotEqual(source_text, original)
                    source = Path(folder) / f"{name}.c"
                    source.write_text(source_text)
                    guest = source.with_suffix(".malbolge")
                    result = self.compile(source, guest)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_unreachable_output_refuses_without_guest(self) -> None:
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/if-continue-normalized-v1",
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        baseline = json.loads(frontend.stdout)
        tail = next(
            node
            for node in baseline["nodes"]
            if node["kind"] == "call-expression"
            and node["span"]["begin"]["line"]
            > next(
                other["span"]["begin"]["line"]
                for other in baseline["nodes"]
                if other["kind"] == "continue-statement"
            )
        )
        for field, mutation in (
            ("parent", 0),
            ("reference", "external:getchar"),
            ("type", "u32"),
            ("kind", "binary-expression"),
            ("span.end.column", tail["span"]["end"]["column"] + 1),
            ("span.end.byte", tail["span"]["end"]["byte"] + 1),
        ):
            with self.subTest(field=field):
                artifact = json.loads(frontend.stdout)
                node = artifact["nodes"][tail["id"] - 1]
                if field.startswith("span."):
                    _, section, position = field.split(".")
                    node["span"][section][position] = mutation
                else:
                    node[field] = mutation
                with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
                    guest = Path(folder) / "forged.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(artifact).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
