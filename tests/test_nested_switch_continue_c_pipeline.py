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
#   - Nested switch continuation and ordered state update guest proof.
# - Must-Not:
#   - Hide unselected effects or publish a guest from forged Clang nodes.
# - Allows:
#   - Inputs: pinned C source and mutated normalized JSON.
#   - Outputs: actual VM bytes and explicit unsupported diagnostics.
#   - Side effects: isolated compiler and guest processes.
# - Split-When:
#   - General C switch/loop verification subsumes this source slice.
# - Merge-When:
#   - An independent dynamic C control-flow oracle replaces finite replay.
# - Summary:
#   - Prove nested continue with case-local recurrence updates and real I/O.

# Regression of a complete C program, not host-computed guest stdout.
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "tests/compiler/c-frontend/accepted/local_nested_switch_continue_fibonacci.c"
)
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"


def independent_oracle() -> bytes:
    a, b = 1, 1
    output = bytearray()
    seen = set()
    for _ in range(12):
        following = (a + b) & 255
        outer, inner = following & 2, following & 1
        seen.add((outer, inner))
        if inner == 0:
            output.append(following & 31)
        else:
            output.append((following ^ 26) & 31)
        # The source updates both locals in the selected inner switch case.
        # This oracle makes the selected continuation carry real state.
        a, b = b, following
    assert seen == {(0, 0), (0, 1), (2, 0), (2, 1)}
    return bytes(output)


class NestedSwitchContinuePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(p.is_file() for p in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler binaries not built")

    def compile(self, source: Path, guest: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/nested-switch-continue-c-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=120,
        )

    def assert_real_guest(self, source: Path) -> None:
        expected = independent_oracle()
        self.assertEqual(expected, bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            guest = Path(directory) / "nested-switch-continue.malbolge"
            result = self.compile(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                run = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected)
                self.assertEqual(run.stderr, b"malbolge-steps-v1:47\n")

    def test_complete_nested_continue_guest(self) -> None:
        self.assert_real_guest(SOURCE)

    def test_continue_in_both_inner_default_arms(self) -> None:
        original = SOURCE.read_text()
        self.assertEqual(original.count("                continue;"), 2)
        self.assertEqual(original.count("                break;"), 2)
        changed = re.sub(
            r"(?m)^( {16})(continue|break);$",
            lambda match: (
                match.group(1)
                + ("break;" if match.group(2) == "continue" else "continue;")
            ),
            original,
        )
        self.assertNotEqual(changed, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "inner-default-continues.c"
            source.write_text(changed)
            self.assert_real_guest(source)

    def test_dead_effects_and_unsupported_source_refuse(self) -> None:
        original = SOURCE.read_text()
        variants = {
            "dead-output": original.replace(
                "                continue;",
                "                continue;\n                putchar(90);",
            ),
            "dead-write": original.replace(
                "                continue;",
                "                continue;\n                b = 0U;",
            ),
            "hidden-input": original.replace(
                "                continue;",
                "                getchar();\n                continue;",
            ),
            "after-inner-switch": original.replace(
                "            }\n            break;",
                "            }\n            putchar(99);\n            break;",
            ),
            "unselected-input": original.replace(
                "            default:\n                putchar",
                "            default:\n                getchar();\n                putchar",
            ),
            "selected-zero-division": original.replace("next & 31U", "next / 0U"),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for name, content in variants.items():
                with self.subTest(name=name):
                    source = Path(directory) / f"{name}.c"
                    source.write_text(content)
                    guest = source.with_suffix(".malbolge")
                    result = self.compile(source, guest)
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(guest.exists())

    def test_forged_nested_continuation_and_outer_break_refuse(self) -> None:
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/nested-switch-continue-ast-v1",
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        artifact = json.loads(frontend.stdout)
        continues = [
            node for node in artifact["nodes"] if node["kind"] == "continue-statement"
        ]
        self.assertEqual(len(continues), 2)
        outer_breaks = [
            node
            for node in artifact["nodes"]
            if node["kind"] == "break-statement"
            and node["span"]["begin"]["column"] == 13
        ]
        self.assertEqual(len(outer_breaks), 2)
        for node in continues + outer_breaks:
            for field in ("parent", "kind", "operation", "span"):
                with self.subTest(node=node["id"], field=field):
                    forged = json.loads(frontend.stdout)
                    target = forged["nodes"][node["id"] - 1]
                    if field == "parent":
                        target["parent"] = 0
                    elif field == "kind":
                        target["kind"] = "null-statement"
                    elif field == "operation":
                        target["operation"] = "="
                    else:
                        target["span"]["begin"]["column"] += 1
                    with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
                        output = Path(directory) / "forged.malbolge"
                        result = subprocess.run(
                            [
                                str(ADAPTER),
                                "--layout-backend",
                                str(LAYOUT),
                                "--output",
                                str(output),
                                "--capsule",
                            ],
                            input=json.dumps(forged).encode(),
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertNotEqual(result.returncode, 0, result.stderr)
                        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
