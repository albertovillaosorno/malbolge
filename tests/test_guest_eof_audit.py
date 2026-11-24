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
#   - Positive and hostile classification of frontend/layout refusal stages.
# - Must-Not:
#   - Publish a guest or treat a failed stage as a passing guest computation.
# - Allows:
#   - Inputs: isolated temporary targets and in-memory process results.
#   - Outputs: strict stage and no-artifact regression assertions.
#   - Side effects: isolated temporary file creation only.
# - Split-When:
#   - The pipeline has a single stable diagnostic protocol for all stages.
# - Merge-When:
#   - General source compiler publication tests include stage classifier.
# - Summary:
#   - Reject malformed/ambiguous refusal diagnostics and orphan outputs.

"""A refused C source cannot be misreported as a lowerer/linker success."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.guest_eof_audit import frontend_layout_or_explicit_refusal
from tests.test_static_for_break_c_pipeline import (
    ROOT,
    guest_or_explicit_eof_refusal,
)


class GuestEofAuditTests(unittest.TestCase):
    def test_distinct_refusals_without_artifact(self) -> None:
        for message in (
            b"normalized frontend rejected: Unsupported; unlowered C for-statement",
            b"layout backend exited unsuccessfully with status 1",
        ):
            with (
                self.subTest(message=message),
                tempfile.TemporaryDirectory() as folder,
            ):
                frontend_layout_or_explicit_refusal(
                    self,
                    subprocess.CompletedProcess(["adapter"], 1, b"", message),
                    Path(folder) / "candidate.malbolge",
                )

    def test_unsupported_refusal_requires_unlowered_c_diagnostic(self) -> None:
        with (
            tempfile.TemporaryDirectory() as folder,
            self.assertRaises(AssertionError),
        ):
            frontend_layout_or_explicit_refusal(
                self,
                subprocess.CompletedProcess(
                    ["adapter"], 1, b"", b"normalized frontend rejected: Unsupported"
                ),
                Path(folder) / "candidate.malbolge",
            )

    def test_ambiguous_or_other_stage_errors_are_not_accepted(self) -> None:
        messages = (
            b"layout backend exited unsuccessfully; normalized frontend rejected",
            (
                b"normalized frontend rejected: Unsupported; unlowered C; "
                b"layout backend exited unsuccessfully"
            ),
            b"malformed normalized frontend artifact",
            b"unexpected panic",
        )
        with tempfile.TemporaryDirectory() as folder:
            for message in messages:
                with self.subTest(message=message), self.assertRaises(AssertionError):
                    frontend_layout_or_explicit_refusal(
                        self,
                        subprocess.CompletedProcess(["adapter"], 1, b"", message),
                        Path(folder) / "candidate.malbolge",
                    )

    def test_unsupported_cannot_succeed_or_publish_artifact(self) -> None:
        message = b"normalized frontend rejected: Unsupported; unlowered C loop"
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "candidate.malbolge"
            with self.assertRaises(AssertionError):
                frontend_layout_or_explicit_refusal(
                    self,
                    subprocess.CompletedProcess(["adapter"], 0, b"", message),
                    target,
                )
            _ = target.write_bytes(b"unexpected-guest")
            with self.assertRaises(AssertionError):
                frontend_layout_or_explicit_refusal(
                    self,
                    subprocess.CompletedProcess(["adapter"], 1, b"", message),
                    target,
                )


class GuestEofSourceRefusalTests(unittest.TestCase):
    """The signed-C23 source oracle must classify only precise refusals."""

    def test_exact_unsupported_refusal_preserves_no_guest_artifact(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            artifact = Path(folder) / "fixture.malbolge"
            _ = artifact.with_suffix(".c").write_text(
                "#include <stdio.h>\nvoid stream(void) { putchar(getchar()); }\n",
                encoding="utf-8",
            )
            result = subprocess.CompletedProcess(
                ["c2malbolge"],
                1,
                b"",
                b"normalized frontend rejected: Unsupported; unlowered C declaration",
            )
            self.assertFalse(guest_or_explicit_eof_refusal(self, result, artifact))
            self.assertFalse(artifact.exists())

    def test_crash_and_ambiguous_failure_cannot_pass_as_unsupported(self) -> None:
        valid = b"normalized frontend rejected: Unsupported; unlowered C declaration"
        cases = (
            (2, valid),
            (1, b"normalized frontend rejected: Unsupported"),
            (1, valid + b"; layout backend exited unsuccessfully"),
            (1, b"layout backend exited unsuccessfully"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            artifact = Path(folder) / "fixture.malbolge"
            _ = artifact.with_suffix(".c").write_text(
                "#include <stdio.h>\nvoid stream(void) { putchar(getchar()); }\n",
                encoding="utf-8",
            )
            for status, message in cases:
                with self.subTest(status=status, message=message):
                    result = subprocess.CompletedProcess(
                        ["c2malbolge"], status, b"", message
                    )
                    with self.assertRaises(AssertionError):
                        _ = guest_or_explicit_eof_refusal(self, result, artifact)

    def test_unsupported_refusal_never_leaves_guest_artifact(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as folder:
            artifact = Path(folder) / "fixture.malbolge"
            _ = artifact.with_suffix(".c").write_text(
                "#include <stdio.h>\nvoid stream(void) { putchar(getchar()); }\n",
                encoding="utf-8",
            )
            _ = artifact.write_bytes(b"unexpected guest")
            result = subprocess.CompletedProcess(
                ["c2malbolge"],
                1,
                b"",
                b"normalized frontend rejected: Unsupported; unlowered C declaration",
            )
            with self.assertRaises(AssertionError):
                _ = guest_or_explicit_eof_refusal(self, result, artifact)


if __name__ == "__main__":
    _ = unittest.main()
