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
