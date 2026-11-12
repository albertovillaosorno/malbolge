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
#   - C switch-case continue targeting its enclosing bounded loop.
# - Must-Not:
#   - Publish unverified guest output or discard hidden source effects.
# - Allows:
#   - Inputs: pinned C sources and forged normalized Clang nodes.
#   - Outputs: real guest Fibonacci bytes or explicit rejection.
#   - Side effects: isolated compilation and normative VM replay.
# - Split-When:
#   - Dynamic guest C control flow has its own execution verifier.
# - Merge-When:
#   - General C switch and loop tests subsume this source proof.
# - Summary:
#   - Prove selected and skipped continue in complete C switch arms.

"""Real guest and source-integrity regression for switch-to-loop continue."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/local_switch_continue_fibonacci.c"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"


def independent_oracle() -> bytes:
    a, b = 1, 1
    result = bytearray()
    for _ in range(12):
        following = (a + b) & 255
        if following & 1:
            result.append((following ^ 26) & 31)
        else:
            result.append(following & 31)
        a, b = b, following
    return bytes(result)


class SwitchContinuePipelineTests(unittest.TestCase):
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
                "tests/switch-continue-c-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=120,
        )

    def test_complete_switch_continue_guest(self) -> None:
        expected = independent_oracle()
        self.assertEqual(expected, bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            guest = Path(directory) / "switch-continue.malbolge"
            result = self.compile(SOURCE, guest)
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

    def test_continue_in_default_arm_replays_guest(self) -> None:
        original = SOURCE.read_text()
        self.assertEqual(original.count("            continue;"), 1)
        self.assertEqual(original.count("            break;"), 1)
        source_text = original.replace("            continue;", "            ENTRY;")
        source_text = source_text.replace("            break;", "            continue;")
        source_text = source_text.replace("            ENTRY;", "            break;")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "default-continues.c"
            source.write_text(source_text)
            guest = source.with_suffix(".malbolge")
            result = self.compile(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for supplied in (b"", bytes((255, 0, 128))):
                run = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, independent_oracle())
                self.assertEqual(run.stderr, b"malbolge-steps-v1:47\n")

    def test_unsupported_effects_and_dead_suffix_refuse(self) -> None:
        original = SOURCE.read_text()
        variants = {
            "dead-output": original.replace(
                "            continue;",
                "            continue;\n            putchar(66);",
            ),
            "dead-write": original.replace(
                "            continue;", "            continue;\n            ++next;"
            ),
            "hidden-input": original.replace(
                "            continue;", "            getchar();\n            continue;"
            ),
            "undefined-selected": original.replace("next & 31U", "next / 0U"),
            "unsupported-jump": original.replace(
                "            continue;", "            goto absent;"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for name, text in variants.items():
                with self.subTest(name=name):
                    source = Path(directory) / f"{name}.c"
                    guest = source.with_suffix(".malbolge")
                    source.write_text(text)
                    result = self.compile(source, guest)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_continue_nodes_refuse(self) -> None:
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/switch-continue-ast-v1",
                str(SOURCE),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        artifact = json.loads(frontend.stdout)
        continuation = next(
            node for node in artifact["nodes"] if node["kind"] == "continue-statement"
        )
        for field, value in (
            ("parent", 0),
            ("kind", "break-statement"),
            ("operation", "="),
            ("type", "u32"),
        ):
            with self.subTest(field=field):
                forged = json.loads(frontend.stdout)
                forged["nodes"][continuation["id"] - 1][field] = value
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
