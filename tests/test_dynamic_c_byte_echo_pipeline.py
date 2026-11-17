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
#   - End-to-end source-C dynamic byte echo under successful input.
# - Must-Not:
#   - Claim EOF equivalence or substitute host-produced bytes for VM output.
# - Allows:
#   - Inputs: pinned native C frontend, typed bridge and VM.
#   - Outputs: verified guest identity output for provided binary input.
#   - Side effects: isolated compiler and VM subprocesses.
# - Split-When:
#   - Dynamic C byte-stream control becomes independently supported.
# - Merge-When:
#   - General source-C runtime I/O subsumes this slice.
# - Summary:
#   - A real C input call reaches a real guest input instruction.

"""Prove source C getchar-to-putchar identities in the normative guest VM."""

from __future__ import annotations

import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
TOOLS = (
    ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend",
    ROOT / ".cache/rust/target/debug/c2malbolge_json",
    ROOT / ".cache/rust/target/debug/malbolge_layout",
    ROOT / ".cache/rust/target/debug/malbolge",
)


class DynamicCByteEchoPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in TOOLS):
            self.skipTest("pinned C compiler and VM binaries are not built")

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

    def test_unsigned_counter_selects_live_byte_replay(self) -> None:
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/unsigned_conditional_live_input.c"
        )
        golden = (
            ROOT
            / "tests/compiler/c-frontend/golden/unsigned_conditional_live_input.json"
        )
        frontend = subprocess.run(
            [
                str(TOOLS[0]),
                "--guest-include",
                str(ROOT / "src/runtime/guest-c-library/contract/include"),
                "--resource-dir",
                str(ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"),
                "--source-id",
                source.name,
                str(source),
            ],
            capture_output=True,
            check=False,
            timeout=15,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        self.assertEqual(frontend.stdout, golden.read_bytes())

        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            guest = Path(folder) / "unsigned-branch.malbolge"
            built = self.compile(source, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue(guest.is_file())
            seed = random.Random(0xA159)
            samples = [
                bytes((0, 255, 128, 1)),
                b"ABCD",
                bytes(seed.randrange(256) for _ in range(4)),
            ]
            for sample in samples:
                with self.subTest(sample=sample):
                    run = subprocess.run(
                        [str(TOOLS[3]), str(guest), "--input-stdin", "--report-steps"],
                        input=sample,
                        capture_output=True,
                        check=False,
                        timeout=20,
                    )
                    self.assertEqual(run.returncode, 0, run.stderr)
                    # Original C takes four independent reads; only the
                    # counter-selected third successful byte is written twice.
                    self.assertEqual(run.stdout, sample[:3] + sample[2:3] + sample[3:4])
                    self.assertIn(b"malbolge-steps-v1:10", run.stderr)

            invalid = source.read_text().replace("i == 2U", "current == 2U")
            invalid_source = Path(folder) / "dynamic-branch.c"
            invalid_guest = Path(folder) / "dynamic-branch.malbolge"
            invalid_source.write_text(invalid)
            refused = self.compile(invalid_source, invalid_guest)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(invalid_guest.exists())

    @staticmethod
    def source(calls: int) -> str:
        return (
            "#include <stdio.h>\n"
            "void emit(void) {\n" + "    putchar(getchar());\n" * calls + "}\n"
        )

    @staticmethod
    def local_source() -> str:
        return (
            "#include <stdio.h>\n"
            "void emit(void) {\n"
            "    int first = getchar();\n"
            "    putchar(first);\n"
            "}\n"
        )

    def test_direct_signed_byte_echo_refuses_without_eof_lowering(self) -> None:
        # Full-input success on a finite vector does not make the same
        # source C correct when stdin ends early. Preserve the successful-u8
        # MCTI/MCTR bridge separately; the public C path must first realize
        # C's defined EOF-to-unsigned-char conversion or refuse to publish.
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for count in (1, 3, 16):
                with self.subTest(count=count):
                    source = Path(folder) / f"echo-{count}.c"
                    target = Path(folder) / f"echo-{count}.malbolge"
                    source.write_text(self.source(count))
                    built = self.compile(source, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertIn(
                        b"normalized frontend rejected: Unsupported", built.stderr
                    )
                    self.assertFalse(target.exists())

    def test_source_local_signed_echo_refuses_without_eof_lowering(self) -> None:
        # Successful finite input does not justify publishing a C local echo:
        # the signed getchar result is -1 after early EOF, not the guest
        # profile sentinel's low byte. Preserve both earlier C shapes as
        # no-artifact regression witnesses.
        sources = (
            (
                "#include <stdio.h>\n"
                "void emit(void) {\n"
                "    int first = getchar();\n"
                "    putchar(first);\n"
                "    putchar(getchar());\n"
                "    int second = getchar();\n"
                "    putchar(second);\n"
                "}\n"
            ),
            "#include <stdio.h>\n"
            "void emit(void) {\n"
            + "".join(
                f"    int byte_{i} = getchar();\n    putchar(byte_{i});\n"
                for i in range(16)
            )
            + "}\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, contents in enumerate(sources):
                with self.subTest(index=index):
                    source = Path(folder) / f"local-{index}.c"
                    target = Path(folder) / f"local-{index}.malbolge"
                    source.write_text(contents)
                    built = self.compile(source, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertIn(b"Unsupported", built.stderr)
                    self.assertFalse(target.exists())

    def test_repeated_local_signed_echo_refuses_at_eof(self) -> None:
        # A repeated C signed local output remains EOF-observable. Refuse
        # publication instead of treating successful input as the contract.
        source_text = (
            "#include <stdio.h>\n"
            "void emit(void) {\n"
            "    int first = getchar();\n"
            "    putchar(first);\n"
            "    putchar(first);\n"
            "    putchar(getchar());\n"
            "    int second = getchar();\n"
            "    putchar(second);\n"
            "    putchar(second);\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "repeated-local.c"
            target = Path(folder) / "repeated-local.malbolge"
            source.write_text(source_text)
            built = self.compile(source, target)
            self.assertNotEqual(built.returncode, 0)
            self.assertIn(b"Unsupported", built.stderr)
            self.assertFalse(target.exists())

    def test_repeated_local_excess_outputs_refuses(self) -> None:
        # Never publish a 257th live-source output instruction.
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "replay-257.c"
            target = Path(folder) / "replay-257.malbolge"
            source.write_text(
                "#include <stdio.h>\n"
                "void emit(void) {\n"
                "    int first = getchar();\n" + "    putchar(first);\n" * 257 + "}\n"
            )
            built = self.compile(source, target)
            self.assertNotEqual(built.returncode, 0)
            self.assertIn(b"Unsupported", built.stderr)
            self.assertFalse(target.exists())

    def test_repeated_local_rejects_stale_and_effectful_uses(self) -> None:
        source = self.local_source().replace(
            "    putchar(first);\n",
            "    putchar(first);\n    putchar(first);\n",
        )
        candidates = (
            source.replace(
                "    putchar(first);\n    putchar(first);",
                "    putchar(first);\n    putchar(getchar());\n    putchar(first);",
            ),
            source.replace(
                "    putchar(first);\n    putchar(first);",
                "    putchar(first);\n    first = getchar();\n    putchar(first);",
            ),
            source.replace(
                "    putchar(first);\n    putchar(first);",
                "    putchar(first);\n    putchar(first + 1);",
            ),
            source.replace(
                "    putchar(first);\n    putchar(first);",
                "    putchar(first);\n    putchar(0);",
            ),
            source.replace(
                "    putchar(first);\n    putchar(first);",
                "    putchar(first);\n    putchar((unsigned char)first);",
            ),
            source.replace(
                "    putchar(first);\n    putchar(first);",
                "    putchar(first);\n    putchar(first + getchar());",
            ),
            source.replace(
                "    putchar(first);\n    putchar(first);",
                "    putchar(first);\n    int other = first;\n    putchar(other);",
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, text in enumerate(candidates):
                with self.subTest(index=index):
                    path = Path(folder) / f"stale-{index}.c"
                    target = Path(folder) / f"stale-{index}.malbolge"
                    path.write_text(text)
                    built = self.compile(path, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertIn(b"Unsupported", built.stderr)
                    self.assertFalse(target.exists())

    def test_repeated_local_forged_second_output_refuses(self) -> None:
        source_text = self.local_source().replace(
            "    putchar(first);\n",
            "    putchar(first);\n    putchar(first);\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "repeated-local-forgery.c"
            source.write_text(source_text)
            frontend = subprocess.run(
                [
                    str(TOOLS[0]),
                    "--guest-include",
                    str(ROOT / "src/runtime/guest-c-library/contract/include"),
                    "--resource-dir",
                    str(ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"),
                    "--source-id",
                    "tests/repeated-local-forgery-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=15,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            artifact = json.loads(frontend.stdout)
            self.assertEqual(len(artifact["nodes"]), 17)
            mutations = (
                ("new-input", 12, "reference", "external:getchar"),
                ("wrong-parent", 13, "parent", 7),
                ("wrong-cast", 15, "operation", "integral-cast"),
                ("stale-local", 16, "reference", "other@45"),
                ("extra-effect", 12, "operation", "other"),
                ("wrong-result", 12, "type", "void"),
                ("wrong-call-id", 12, "id", 77),
                ("wrong-callee-type", 14, "type", "fn()->i32"),
            )
            for label, index, field, replacement in mutations:
                with self.subTest(label=label):
                    forged = json.loads(frontend.stdout)
                    forged["nodes"][index][field] = replacement
                    target = Path(folder) / f"forged-{label}.malbolge"
                    run = subprocess.run(
                        [
                            str(TOOLS[1]),
                            "--layout-backend",
                            str(TOOLS[2]),
                            "--output",
                            str(target),
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertNotEqual(run.returncode, 0, run.stderr)
                    self.assertIn(b"Unsupported", run.stderr)
                    self.assertFalse(target.exists())
            for index, side, coordinate in (
                (12, "begin", "byte"),
                (12, "end", "column"),
                (15, "end", "byte"),
                (16, "begin", "column"),
                (16, "end", "line"),
            ):
                with self.subTest(index=index, side=side, coordinate=coordinate):
                    forged = json.loads(frontend.stdout)
                    forged["nodes"][index]["span"][side][coordinate] += 1
                    target = Path(folder) / f"span-{index}-{side}-{coordinate}.malbolge"
                    run = subprocess.run(
                        [
                            str(TOOLS[1]),
                            "--layout-backend",
                            str(TOOLS[2]),
                            "--output",
                            str(target),
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertNotEqual(run.returncode, 0, run.stderr)
                    self.assertIn(b"Unsupported", run.stderr)
                    self.assertFalse(target.exists())

    def test_source_bound_and_excess_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "echo-128.c"
            target = Path(folder) / "echo-128.malbolge"
            source.write_text(self.source(128))
            built = self.compile(source, target)
            # At 128 reads, EOF can occur on any call; the bound is not a
            # source-C promise of 128 successful bytes. Refuse both counts.
            self.assertNotEqual(built.returncode, 0)
            self.assertIn(b"Unsupported", built.stderr)
            self.assertFalse(target.exists())

            over_source = Path(folder) / "echo-129.c"
            over_target = Path(folder) / "echo-129.malbolge"
            over_source.write_text(self.source(129))
            refused = self.compile(over_source, over_target)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(over_target.exists())

    def test_normalized_call_forgeries_refuse_before_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "echo.c"
            source.write_text(self.source(1))
            frontend = subprocess.run(
                [
                    str(TOOLS[0]),
                    "--guest-include",
                    str(ROOT / "src/runtime/guest-c-library/contract/include"),
                    "--resource-dir",
                    str(ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"),
                    "--source-id",
                    "tests/source-byte-echo-forgery-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=15,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            artifact = json.loads(frontend.stdout)
            self.assertEqual(len(artifact["nodes"]), 8)
            changes = (
                ("outer-reference", 2, "reference", "external:getchar"),
                ("input-reference", 5, "reference", "external:putchar"),
                ("input-ancestor", 5, "parent", 2),
                ("callee-ancestor", 7, "parent", 3),
                ("input-kind", 5, "kind", "integer-literal"),
                ("input-type", 5, "type", "u32"),
                ("input-hidden-effect", 5, "operation", "other"),
                ("output-hidden-effect", 2, "operation", "other"),
                ("nested-cast", 6, "operation", "integral-cast"),
                ("output-call-id", 2, "id", 99),
                ("input-call-id", 5, "id", 99),
                ("callee-type", 7, "type", "fn(i32)->i32"),
                ("output-discard", 2, "type", "void"),
            )
            for label, node_index, field, wrong in changes:
                with self.subTest(label=label):
                    corrupted = json.loads(frontend.stdout)
                    corrupted["nodes"][node_index][field] = wrong
                    target = Path(folder) / f"forgery-{label}.malbolge"
                    result = subprocess.run(
                        [
                            str(TOOLS[1]),
                            "--layout-backend",
                            str(TOOLS[2]),
                            "--output",
                            str(target),
                        ],
                        input=json.dumps(corrupted).encode(),
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b"Unsupported", result.stderr)
                    self.assertFalse(target.exists())
            for node_index, endpoint, coordinate in (
                (2, "begin", "byte"),
                (2, "end", "column"),
                (5, "begin", "column"),
                (5, "end", "byte"),
                (6, "end", "byte"),
                (7, "begin", "line"),
            ):
                with self.subTest(
                    node=node_index, endpoint=endpoint, coordinate=coordinate
                ):
                    corrupted = json.loads(frontend.stdout)
                    point = corrupted["nodes"][node_index]["span"][endpoint]
                    point[coordinate] += 1
                    target = (
                        Path(folder)
                        / f"span-{node_index}-{endpoint}-{coordinate}.malbolge"
                    )
                    result = subprocess.run(
                        [
                            str(TOOLS[1]),
                            "--layout-backend",
                            str(TOOLS[2]),
                            "--output",
                            str(target),
                        ],
                        input=json.dumps(corrupted).encode(),
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b"Unsupported", result.stderr)
                    self.assertFalse(target.exists())

    def test_local_capture_source_negatives_refuse(self) -> None:
        source = self.local_source()
        candidates = (
            source.replace("putchar(first);", "putchar(first + 1);"),
            source.replace("putchar(first);", "putchar(0);"),
            source.replace(
                "putchar(first);", "first = getchar();\n    putchar(first);"
            ),
            source.replace(
                "putchar(first);",
                "putchar(first);\n    putchar(getchar());\n    putchar(first);",
            ),
            source.replace("int first", "unsigned int first"),
            source.replace("putchar(first);", "putchar((unsigned char)first);"),
            source.replace(
                "putchar(first);", "putchar(getchar());\n    putchar(first);"
            ),
            (
                "#include <stdio.h>\n"
                "void emit(void) {\n"
                "    int first = getchar();\n"
                "    int second = getchar();\n"
                "    putchar(first);\n"
                "    putchar(second);\n"
                "}\n"
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, contents in enumerate(candidates):
                with self.subTest(index=index):
                    path = Path(folder) / f"unlowered-local-{index}.c"
                    target = Path(folder) / f"unlowered-local-{index}.malbolge"
                    path.write_text(contents)
                    built = self.compile(path, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertIn(b"Unsupported", built.stderr)
                    self.assertFalse(target.exists())

    def test_local_capture_clang_forgeries_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            source = Path(folder) / "local.c"
            source.write_text(self.local_source())
            frontend = subprocess.run(
                [
                    str(TOOLS[0]),
                    "--guest-include",
                    str(ROOT / "src/runtime/guest-c-library/contract/include"),
                    "--resource-dir",
                    str(ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"),
                    "--source-id",
                    "tests/source-byte-local-forgery-v1",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=15,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            artifact = json.loads(frontend.stdout)
            self.assertEqual(len(artifact["nodes"]), 12)
            changes = (
                ("decl-kind", 2, "kind", "compound-statement"),
                ("decl-parent", 2, "parent", 1),
                ("variable-kind", 3, "kind", "parameter-declaration"),
                ("variable-name", 3, "name", "other"),
                ("variable-reference", 3, "reference", "first@44"),
                ("variable-type", 3, "type", "u32"),
                ("variable-storage", 3, "storage_duration", "static"),
                ("input-parent", 4, "parent", 2),
                ("input-reference", 4, "reference", "external:putchar"),
                ("input-cast", 5, "operation", "lvalue-to-rvalue"),
                ("input-callee", 6, "reference", "external:putchar"),
                ("output-parent", 7, "parent", 3),
                ("output-reference", 7, "reference", "external:getchar"),
                ("value-cast", 10, "operation", "integral-cast"),
                ("value-parent", 10, "parent", 9),
                ("value-reference", 11, "reference", "other@45"),
                ("value-type", 11, "type", "u32"),
            )
            for label, node_index, field, wrong in changes:
                with self.subTest(label=label):
                    corrupted = json.loads(frontend.stdout)
                    corrupted["nodes"][node_index][field] = wrong
                    target = Path(folder) / f"forge-local-{label}.malbolge"
                    result = subprocess.run(
                        [
                            str(TOOLS[1]),
                            "--layout-backend",
                            str(TOOLS[2]),
                            "--output",
                            str(target),
                        ],
                        input=json.dumps(corrupted).encode(),
                        check=False,
                        capture_output=True,
                        timeout=15,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b"Unsupported", result.stderr)
                    self.assertFalse(target.exists())
            for node_index, endpoint, coordinate in (
                (2, "end", "byte"),
                (3, "begin", "column"),
                (4, "begin", "byte"),
                (4, "end", "column"),
                (7, "begin", "line"),
                (7, "end", "byte"),
                (10, "begin", "byte"),
                (11, "end", "column"),
            ):
                with self.subTest(
                    node=node_index, endpoint=endpoint, coordinate=coordinate
                ):
                    corrupted = json.loads(frontend.stdout)
                    corrupted["nodes"][node_index]["span"][endpoint][coordinate] += 1
                    target = (
                        Path(folder)
                        / f"forge-span-{node_index}-{endpoint}-{coordinate}.malbolge"
                    )
                    result = subprocess.run(
                        [
                            str(TOOLS[1]),
                            "--layout-backend",
                            str(TOOLS[2]),
                            "--output",
                            str(target),
                        ],
                        input=json.dumps(corrupted).encode(),
                        check=False,
                        capture_output=True,
                        timeout=15,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b"Unsupported", result.stderr)
                    self.assertFalse(target.exists())

    def test_unimplemented_input_arithmetic_and_extra_effects_refuse(self) -> None:
        candidates = (
            self.source(1).replace("getchar()", "getchar() + 1"),
            self.source(1).replace(
                "putchar(getchar());",
                "putchar(getchar());\n    getchar();",
            ),
            self.source(1).replace(
                "putchar(getchar());", "putchar(0);\n    getchar();"
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            for index, contents in enumerate(candidates):
                with self.subTest(index=index):
                    source = Path(folder) / f"invalid-{index}.c"
                    target = Path(folder) / f"invalid-{index}.malbolge"
                    source.write_text(contents)
                    built = self.compile(source, target)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertIn(b"Unsupported", built.stderr)
                    self.assertFalse(target.exists())
