# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Stable teaching C/guest pair identities and real VM replay.
# - Must-Not:
#   - Replace guest execution with a host C run or loosen digest comparisons.
# - Allows:
#   - Inputs: retained example files and repository-pinned local tools.
#   - Outputs: byte-exact regeneration, digest and guest-stdout evidence.
#   - Side effects: temporary compiler output under project-local .temp.
# - Split-When:
#   - The fixed challenge corpus introduces a separate fixture family.
# - Merge-When:
#   - A shared corpus runner can verify identical source/artifact contracts.
# - Summary:
#   - Replay checked-in Malbolge programs and their C compiler provenance.
# - Description:
#   - Compiler output identity and normative guest behavior are separate tests.
# - Usage:
#   - python3.14 -B -m unittest tests.test_versioned_example_corpus -v
# - Defaults:
#   - Portable digest check always runs; tool-dependent tests skip if absent.

"""Retained C-to-guest examples must be executable and reproducible."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import final

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs/technical/examples/corpus"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
BIN_ROOT = Path(
    os.environ.get("MALBOLGE_CORPUS_BIN_ROOT", str(ROOT / ".cache/rust/target/debug"))
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"


@dataclass(frozen=True, slots=True)
class Case:
    stem: str
    source_sha256: str
    capsule_sha256: str
    stdout: bytes
    steps: int
    size: int

    @property
    def source(self) -> Path:
        return CORPUS / f"{self.stem}.c"

    @property
    def capsule(self) -> Path:
        return CORPUS / f"{self.stem}.malbolge"


CASES = (
    Case(
        "emit-qp",
        "9d99117ec1218be5102aef819fc872e098fcfea7f7efede831c765e5104886f3",
        "4112557f6f320f8827278ff8b623fddba73812c49801569093e815f27a9fa2b8",
        b"Q.",
        8,
        1111,
    ),
    Case(
        "emit-zph",
        "94e5a35dcf0df2da9676ef630c0e1dc0e1926962c4b951adf0f80cec7558dcb4",
        "44ef08f92ac1c352ff5df820e63d4830664b6f7a569cd6e0f5504deb4cba9eb8",
        b"Z%H",
        8,
        1111,
    ),
    Case(
        "emit-t4",
        "34d1144628330399658b36bfe57e2d34cf71f40ad46645ec075a6390ea45fb1a",
        "9ee602682624425da80c13786df338c80df15a65e1df083613c37100ed81f72d",
        b"T=4>",
        21,
        1215,
    ),
    Case(
        "emit-qesc79",
        "5a753a10b51b5211022694a2b3f9c45fe4afb92cd8e0ebf7f9cc37876953688d",
        "09be18cd3358663cf7c8434f4b4c910f9ae2a87f0e6b799238372d2110fae2b6",
        b'Q"\x1b79',
        23,
        1231,
    ),
    Case(
        "emit-qop6",
        "91f7d5bdcb226014082d80e3d15a944811366506d5ecd0ce24441699235f434e",
        "bcf659b66b69e7dac57505ac70a516451b60393bc9a2510d6fd6a59d897b7a76",
        bytes((0x51, 0x1C, 0x4F, 0x1D, 0x50, 0x1B)),
        15,
        1167,
    ),
    Case(
        "emit-seven",
        "1bf0848c18f712c2e7b87e0305563a73cb9299aa45cc74d463e4f6098db19140",
        "4f0c732c3b55dd48b12795044f106989ffc84cd7839bcbff1e11c1b9643b99f8",
        bytes((0x36, 0x3E, 0x35, 0x02, 0x54, 0x1F, 0x18)),
        21,
        1215,
    ),
    Case(
        "emit-eight",
        "5971c3577e8087ed2a895790fefc2a8b3b4c931445c03a7d06de451e3e1fa711",
        "59106439d2b0c203a6f934952adcd10b1d0dae7049df62fb708da48203e8a578",
        bytes((0x53, 0x20, 0x17, 0x3C, 0x36, 0x01, 0x52, 0x06)),
        21,
        1215,
    ),
    Case(
        "emit-nine",
        "45229743a0d515e503b190695307694985a7ba47c2dc74f616839e8bf680f430",
        "1d09fccde1f7d346ebc7e72439b82544da2dda37ff2a6e93b020996189e7bbeb",
        bytes((0x54, 0x3D, 0x8D, 0xD1, 0xC0, 0xB4, 0xBF, 0xD2, 0xA2)),
        21,
        1215,
    ),
    Case(
        "emit-ten",
        "eeacae21350d6c88dbfbd8be4b1d1294e04be60868324463b8a97e24a5553675",
        "7befd3c590d03e94889bc93348bb37c51358f4b719dc2f371e07f918130386b0",
        bytes((0x51, 0x22, 0xFD, 0xCE, 0xA5, 0x98, 0xBA, 0xB6, 0x87, 0xCB)),
        23,
        1231,
    ),
    Case(
        "emit-eleven",
        "4a42a412d63b0131f9d6c613b4f6dedca7fc2a01fd94433add89e5c873853c39",
        "6b7381c638e959fa3f1cca6376317340c4278c4611bc518aa54b4ce2fcc6d8af",
        bytes((0x50, 0x1D, 0x1A, 0x36, 0x05, 0xB4, 0xBA, 0xB3, 0x84, 0xCF, 0x9E)),
        24,
        1239,
    ),
    Case(
        "emit-twelve",
        "f5e8963f704c59cc34e15b217d30f69c2b1816c1bf1e5b20369392b3b1085fc7",
        "5bc03bb8ce1d9ab95a9aad99d387d4752f148c5be30dcab7919ffd53fbc52a34",
        bytes((0x51, 0x37, 0x34, 0x38, 0xFB, 0xCE, 0x9F, 0x98, 0xB8, 0xB4, 0x83, 0xCD)),
        27,
        1263,
    ),
    Case(
        "emit-thirteen",
        "59a96352ab35a582e2424d15818ce59c105fc8222cd3b07394c1486e3ed32e0e",
        "10b08a4c61f6e5a28f9ef1e01809cdc455178b0523328205bb101325c7a78bc5",
        bytes(
            (
                0x42,
                0x43,
                0x30,
                0x16,
                0x54,
                0x09,
                0xBF,
                0xC6,
                0xC8,
                0x87,
                0xE3,
                0xAB,
                0xA4,
            )
        ),
        29,
        1279,
    ),
    Case(
        "emit-fourteen",
        "923b7245d13803ffbb1615b4f9684fd076a618f4e25d80861ab1e0fe2a807c14",
        "e3ea5ad67954382872f2f2a6dbd03dfb497a91a52a1fbe04d2aa92afd9e7b438",
        bytes(
            (
                0x59,
                0x45,
                0x2C,
                0x48,
                0x53,
                0x17,
                0x4C,
                0x4F,
                0x3D,
                0x40,
                0x5B,
                0x31,
                0x19,
                0x34,
            )
        ),
        31,
        1295,
    ),
)


def has_executables(*paths: Path) -> bool:
    return all(path.is_file() and os.access(path, os.X_OK) for path in paths)


@final
class VersionedExampleCorpusTests(unittest.TestCase):
    def test_retained_source_and_artifact_digests(self) -> None:
        for case in CASES:
            with self.subTest(example=case.stem):
                self.assertTrue(case.source.is_file())
                self.assertTrue(case.capsule.is_file())
                self.assertEqual(
                    hashlib.sha256(case.source.read_bytes()).hexdigest(),
                    case.source_sha256,
                )
                self.assertEqual(
                    hashlib.sha256(case.capsule.read_bytes()).hexdigest(),
                    case.capsule_sha256,
                )
                self.assertEqual(case.capsule.stat().st_size, case.size)

    def test_retained_guest_runs_under_normative_vm(self) -> None:
        if not has_executables(VM):
            self.skipTest("repository VM binary is not built")
        for case in CASES:
            with self.subTest(example=case.stem):
                result = subprocess.run(
                    [str(VM), str(case.capsule), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, case.stdout)
                self.assertEqual(
                    result.stderr, f"malbolge-steps-v1:{case.steps}\n".encode()
                )

    def test_pinned_c_frontend_reproduces_the_retained_capsules(self) -> None:
        if (
            not has_executables(FRONTEND, ADAPTER, LAYOUT)
            or not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
        ):
            if "MALBOLGE_CORPUS_BIN_ROOT" in os.environ:
                self.fail("explicitly selected compiler binaries are missing")
            self.skipTest("pinned native compiler stages are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp_dir:
            for case in CASES:
                with self.subTest(example=case.stem):
                    output = Path(temp_dir) / f"{case.stem}.malbolge"
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--frontend",
                            str(FRONTEND),
                            "--json-adapter",
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--guest-include",
                            str(GUEST_INCLUDE),
                            "--resource-dir",
                            str(RESOURCE),
                            "--source-id",
                            f"corpus/{case.stem}-v1",
                            "--capsule",
                            "--output",
                            str(output),
                            str(case.source),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=150,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(output.read_bytes(), case.capsule.read_bytes())
