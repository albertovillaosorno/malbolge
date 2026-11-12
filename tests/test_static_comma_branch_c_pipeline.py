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
#   - Source-proven comma argument effects inside literal C branches.
# - Must-Not:
#   - Replay input on the host or skip verification of inactive effects.
# - Allows:
#   - Inputs: pinned C frontend and bounded successful-byte VM inputs.
#   - Outputs: guest effect parity and refusal for unsupported provenance.
#   - Side effects: isolated compilation products under temporary storage.
# - Split-When:
#   - Dynamic C condition execution replaces static branch projection.
# - Merge-When:
#   - Adjacent branch suite owns comma-output ancestry.
# - Summary:
#   - Checks ordered source-C comma effects across constant branch arms.

"""Guest VM and Clang provenance tests for comma-output static branches."""

from __future__ import annotations

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"

BODY = (
    "    int first = getchar();\n"
    "    if (1) {\n"
    "        putchar((putchar(first), first));\n"
    "        putchar((getchar(), putchar(getchar())));\n"
    "    } else {\n"
    "        putchar((getchar(), getchar()));\n"
    "    }\n"
)


class StaticCommaBranchCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout and guest VM required")

    @staticmethod
    def source(body: str) -> str:
        return "#include <stdio.h>\nvoid stream(void) {\n" + body + "}\n"

    @staticmethod
    def compile(source: Path, target: Path) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
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
    def normalized(source: Path) -> dict[str, object]:
        result = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "static-comma-branch",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_multiline_selected_comma_effects_match_real_guest_oracles(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "selected.c"
            target = Path(directory) / "selected.malbolge"
            source.write_text(self.source(BODY))
            built = self.compile(source, target)
            self.assertEqual(built.returncode, 0, built.stderr)
            rng = random.Random(0xC0_11_2026)
            samples = [b"\x00\xff\x80", b"\xff\x00\x01", b"ABC"]
            samples += [bytes(rng.getrandbits(8) for _ in range(3)) for _ in range(7)]
            for sample in samples:
                with self.subTest(sample=sample):
                    guest = subprocess.run(
                        [str(VM), str(target), "--input-stdin", "--report-steps"],
                        input=sample,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes((sample[0], sample[0], sample[2], sample[2])),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:8\n")

    def test_unproved_comma_branches_never_publish(self) -> None:
        invalid = (
            "    if (getchar()) putchar((getchar(), getchar()));\n",
            "    if (2) putchar((getchar(), getchar()));\n",
            "    if (1) putchar((getchar(), 65));\n",
            "    if (1) putchar((getchar(), getchar() + 1));\n",
            "    if (0) putchar((getchar(), getchar() + 1));\n",
            "    if (1) putchar((getchar(), unknown()));\n",
            (
                "    if (1) {\n        putchar((getchar(), getchar()));\n"
                "        putchar(65);\n    }\n"
            ),
            (
                "    int first = getchar();\n"
                "    if (1) {\n        putchar((getchar(), getchar()));\n"
                "        putchar(first);\n    }\n"
            ),
            ("    int first = getchar();\n    if (1) putchar((getchar(), first));\n"),
            (
                "    if (0) {\n        putchar((getchar(), getchar()));\n"
                "    } else {\n        putchar(65);\n    }\n"
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, body in enumerate(invalid):
                with self.subTest(index=index):
                    source = Path(directory) / f"unsupported-{index}.c"
                    target = Path(directory) / f"unsupported-{index}.malbolge"
                    source.write_text(self.source(body))
                    built = self.compile(source, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(target.exists())

    def test_comma_branch_clang_forgery_never_publishes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "valid.c"
            source.write_text(self.source(BODY))
            normalized = self.normalized(source)
            nodes = normalized["nodes"]
            commas = [node for node in nodes if node["kind"] == "binary-expression"]
            self.assertGreaterEqual(len(commas), 3)
            calls = [
                node
                for node in nodes
                if node["kind"] == "call-expression"
                and node["reference"] == "external:putchar"
            ]
            self.assertGreaterEqual(len(calls), 5)
            changes = (
                (commas[0]["id"], "parent", 1),
                (commas[0]["id"], "operation", "+"),
                (commas[0]["id"], "span.end.byte", 200),
                (commas[0]["id"], "span.begin.column", 3),
                (commas[1]["id"], "parent", 1),
                (commas[1]["id"], "span.end.column", 8),
                (commas[2]["id"], "operation", "-"),
                (calls[0]["id"], "parent", 1),
                (calls[0]["id"], "reference", "external:getchar"),
                (calls[1]["id"], "span.end.line", 3),
                (calls[2]["id"], "span.begin.byte", 1),
                (calls[-1]["id"], "parent", 2),
            )
            for index, (node_id, field, replacement) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(n for n in forged["nodes"] if n["id"] == node_id)
                    target_field = node
                    for part in field.split(".")[:-1]:
                        target_field = target_field[part]
                    target_field[field.split(".")[-1]] = replacement
                    target = Path(directory) / f"forged-{index}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(target),
                            "--capsule",
                        ],
                        input=json.dumps(forged, separators=(",", ":")).encode(),
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
