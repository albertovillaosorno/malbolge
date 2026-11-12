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
#   - Comma expression return-value use in real guest C I/O.
# - Must-Not:
#   - Skip discarded effects, use host stdout or assume EOF parity.
# - Allows:
#   - Inputs: pinned Clang source proof and isolated binary VM stdin.
#   - Outputs: guest byte parity and unsupported-shape rejection.
#   - Side effects: temporary artifacts only.
# - Split-When:
#   - Full typed expression evaluation supersedes this bounded form.
# - Merge-When:
#   - Comma operands gain general source-verified return semantics.
# - Summary:
#   - Successful inner putchar returns its byte to the outer call.

"""Test source-C comma argument return semantics in the normative guest."""

from __future__ import annotations

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
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
    "    putchar((getchar(), putchar(getchar())));\n"
    "    putchar((putchar(getchar()), getchar()));\n"
)


class MixedCommaArgumentCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler and VM have not been built")

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
            check=False,
            capture_output=True,
            timeout=90,
        )

    @staticmethod
    def normalized(source: Path) -> dict[str, object]:
        p = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "mixed-comma-argument-v1",
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        if p.returncode:
            raise AssertionError(p.stderr)
        return json.loads(p.stdout)

    @staticmethod
    def vm(target: Path, data: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [str(VM), str(target), "--input-stdin", "--report-steps"],
            input=data,
            capture_output=True,
            check=False,
            timeout=40,
        )

    def test_comma_return_and_discarded_outputs_execute_in_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "value.c"
            target = Path(folder) / "value.malbolge"
            source.write_text(self.source(BODY))
            compiled = self.compile(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            rng = random.Random(0xC0AA_2026)
            data = [b"\x00\xff\x80\x01", b"ABCD"]
            data += [bytes(rng.getrandbits(8) for _ in range(4)) for _ in range(10)]
            with ThreadPoolExecutor(max_workers=6) as executor:
                results = executor.map(lambda sample: self.vm(target, sample), data)
                for sample, result in zip(data, results, strict=True):
                    oracle = bytes((sample[1], sample[1], sample[2], sample[3]))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, oracle)
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:9\n")

    def test_comma_argument_excess_rejects_without_guest_artifact(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "oversized.c"
            target = Path(folder) / "oversized.malbolge"
            parts = ["getchar()"] * 16 + ["putchar(getchar())"]
            source.write_text(self.source("    putchar((" + ", ".join(parts) + "));\n"))
            result = self.compile(source, target)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

    def test_unsupported_argument_effects_refuse_publication(self) -> None:
        invalid = (
            "putchar((getchar(), putchar(65)))",
            "putchar((putchar(65), getchar()))",
            "putchar((getchar(), putchar(getchar() + 1)))",
            "putchar((getchar(), (putchar(getchar()))))",
            "putchar((getchar() + 1, putchar(getchar())))",
            "putchar((getchar(), putchar(putchar(65))))",
            "putchar((getchar(), getchar() == 0))",
            "putchar((getchar(), (void)putchar(getchar())))",
            "putchar((getchar(), getchar() + 1))",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, expression in enumerate(invalid):
                with self.subTest(index=index):
                    source = Path(folder) / f"invalid-{index}.c"
                    target = Path(folder) / f"invalid-{index}.malbolge"
                    source.write_text(self.source(f"    {expression};\n"))
                    result = self.compile(source, target)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_comma_argument_ancestry_refuses_publication(self) -> None:
        changes = (
            (3, ("reference",), "external:getchar"),
            (3, ("span", "end", "byte"), 99),
            (4, ("operation",), "integral-cast"),
            (6, ("parent",), 2),
            (6, ("span", "end", "column"), 1),
            (7, ("operation",), "+"),
            (7, ("parent",), 3),
            (7, ("type",), "u32"),
            (8, ("parent",), 6),
            (11, ("parent",), 6),
            (11, ("span", "begin", "column"), 1),
            (12, ("type",), "ptr(fn()->i32)"),
            (14, ("parent",), 7),
            (17, ("parent",), 3),
            (21, ("operation",), "*"),
            (22, ("parent",), 20),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "original.c"
            source.write_text(self.source(BODY))
            original = self.normalized(source)
            for index, (node_id, path, value) in enumerate(changes):
                with self.subTest(index=index):
                    forged = copy.deepcopy(original)
                    nodes = forged["nodes"]
                    assert isinstance(nodes, list)
                    node = next(n for n in nodes if n["id"] == node_id)
                    field = node
                    for key in path[:-1]:
                        field = field[key]
                    field[path[-1]] = value
                    target = Path(folder) / f"forged-{index}.malbolge"
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
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
