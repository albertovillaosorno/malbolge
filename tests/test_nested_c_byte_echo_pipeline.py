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
#   - Complete nested C putchar-return guest binary-I/O behavior and refusals.
# - Must-Not:
#   - Claim EOF, failed output semantics or host-emulated guest effects.
# - Allows:
#   - Inputs: pinned Clang JSON, canonical adapter and actual guest VM.
#   - Outputs: separately calculated byte-stream oracle and no-artifact rejects.
#   - Side effects: isolated temporary source files and subprocesses.
# - Split-When:
#   - General dynamic C call-return compilation covers these projections.
# - Merge-When:
#   - Source-C I/O semantic matrices subsume this expression grammar.
# - Summary:
#   - Each nested successful putchar returns the byte it just emitted.

"""Guest-execute nested putchar return forwarding with source-proven AST."""

from __future__ import annotations

import copy
import json
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


def c_source(depths: tuple[int, ...]) -> str:
    expressions = ["getchar()"]
    return (
        "#include <stdio.h>\nvoid emit(void) {\n"
        + "".join(
            "    " + "putchar(" * depth + expressions[0] + ")" * depth + ";\n"
            for depth in depths
        )
        + "}\n"
    )


class NestedCByteEchoPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and VM executables are not built")

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
            timeout=100,
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
                "nested-byte-return-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=20,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    @staticmethod
    def forged_compile(
        artifact: dict[str, object], target: Path
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                str(ADAPTER),
                "--layout-backend",
                str(LAYOUT),
                "--output",
                str(target),
                "--capsule",
            ],
            input=json.dumps(artifact, separators=(",", ":")).encode(),
            capture_output=True,
            check=False,
            timeout=30,
        )

    def test_nested_calls_emit_guest_runtime_values_in_c_evaluation_order(self) -> None:
        # Each nested output consumes the successful inner putchar return,
        # which is the same byte. No second getchar is permitted.
        cases = ((2,), (3, 1, 2), (16,), (2, 4, 3, 1, 2))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, depths in enumerate(cases):
                with self.subTest(depths=depths):
                    source = Path(folder) / f"nested-{index}.c"
                    target = Path(folder) / f"nested-{index}.malbolge"
                    source.write_text(c_source(depths))
                    result = self.compile(source, target)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(target.is_file())
                    samples = (
                        bytes((0, 255, 128, 10, 65, 254))[: len(depths)],
                        bytes((65, 10, 0, 255, 128, 1))[: len(depths)],
                    )
                    for data in samples:
                        expected = bytes(
                            byte
                            for byte, depth in zip(data, depths)
                            for _ in range(depth)
                        )
                        vm = subprocess.run(
                            [str(VM), str(target), "--input-stdin", "--report-steps"],
                            input=data,
                            check=False,
                            capture_output=True,
                            timeout=20,
                        )
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(vm.stdout, expected)
                        self.assertEqual(
                            vm.stderr,
                            f"malbolge-steps-v1:{len(depths) + sum(depths) + 1}\n".encode(),
                        )

    def test_source_effect_mutations_never_publish(self) -> None:
        bad_sources = (
            "    putchar(putchar(getchar() + 1));\n",
            "    putchar(putchar(1));\n",
            "    putchar(putchar(getchar()));\n    getchar();\n",
            "    putchar(putchar(getchar()));\n    putchar(0);\n",
            "    if (1) putchar(putchar(getchar()));\n",
            "    int value = getchar();\n    putchar(putchar(value + 1));\n",
            "    putchar(putchar(getchar()));\n    putchar(putchar(EOF));\n",
            "    " + "putchar(" * 17 + "getchar()" + ")" * 17 + ";\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, body in enumerate(bad_sources):
                with self.subTest(index=index):
                    source = Path(folder) / f"bad-{index}.c"
                    target = Path(folder) / f"bad-{index}.malbolge"
                    source.write_text(
                        "#include <stdio.h>\nvoid emit(void) {\n" + body + "}\n"
                    )
                    built = self.compile(source, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_nested_ancestry_and_source_spans_reject(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "nested-base.c"
            source.write_text(c_source((3, 2)))
            normalized = self.normalized(source)
            changes = (
                (3, ("parent",), 1),
                (6, ("parent",), 2),
                (9, ("parent",), 3),
                (12, ("parent",), 5),
                (3, ("reference",), "external:getchar"),
                (6, ("reference",), "external:getchar"),
                (9, ("reference",), "external:getchar"),
                (12, ("reference",), "external:putchar"),
                (3, ("span", "end", "column"), 99),
                (6, ("span", "end", "byte"), 99),
                (9, ("span", "begin", "column"), 99),
                (12, ("span", "begin", "byte"), 99),
                (12, ("type",), "u32"),
                (4, ("operation",), "integral-cast"),
                (5, ("reference",), "external:getchar"),
                (3, ("constant_integer",), "1"),
            )
            for index, (node_id, path, value) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    nodes = forged["nodes"]
                    assert isinstance(nodes, list)
                    node = next(node for node in nodes if node["id"] == node_id)
                    target_value = node
                    for part in path[:-1]:
                        target_value = target_value[part]
                    target_value[path[-1]] = value
                    target = Path(folder) / f"forged-{index}.malbolge"
                    result = self.forged_compile(forged, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
