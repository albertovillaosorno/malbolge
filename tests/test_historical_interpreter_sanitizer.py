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
#   - Executable regression evidence for the historical sanitizer harness.
# - Must-Not:
#   - Normalize raw addresses or make historical memory errors normative.
# - Allows:
#   - Inputs: pinned source, Clang, manifest, and reviewed normalized evidence.
#   - Outputs: exact schema, identity, and reproduced result assertions.
#   - Side effects: temporary sanitizer build files removed by the harness.
# - Split-When:
#   - Split when another host sanitizer configuration gains its own evidence.
# - Merge-When:
#   - Merge when another suite owns the same end-to-end sanitizer boundary.
# - Summary:
#   - Reproduces clean and H-003 historical interpreter sanitizer outcomes.
# - Description:
#   - Verifies source identity and normalized ASan/UBSan findings.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Tool absence skips execution; malformed or drifting evidence fails.
#

"""Historical interpreter sanitizer harness regression tests."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import TYPE_CHECKING

import pytest

from scripts.validate import historical_interpreter_sanitizer as harness

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED_CASES = (
    "clean-interpreter-roundtrip",
    "empty-source-overread",
    "one-word-source-overread",
)


def test_sanitizer_manifest_and_source_identity_are_exact() -> None:
    """Manifest order and immutable source identity remain reviewed."""
    cases = harness.load_cases()
    assert tuple(case.identifier for case in cases) == EXPECTED_CASES
    source = harness.SOURCE.read_bytes()
    assert sha256(source).hexdigest() == harness.SOURCE_SHA256
    evidence = harness.load_evidence()
    assert evidence["schema_version"] == harness.SCHEMA_VERSION
    assert evidence["source_sha256"] == harness.SOURCE_SHA256


@pytest.mark.parametrize(
    "identifier",
    [
        "../escaped",
        "child/escaped",
        r"child\escaped",
        "C:escape",
        ".hidden",
        "NUL",
        "con.copy",
        "x" * 129,
    ],
)
def test_sanitizer_rejects_unsafe_case_ids_before_file_creation(
    identifier: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unchecked fixture IDs must not select filenames outside the sandbox."""
    document = {
        "schema_version": harness.SCHEMA_VERSION,
        "source_root": "tests/compatibility/specification",
        "cases": [{
            "id": identifier,
            "source_hex": "44",
            "input_hex": "",
        }],
    }
    cases = tmp_path / "cases.json"
    _ = cases.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(harness, "CASES", cases)
    with pytest.raises(
        harness.SanitizerHarnessError,
        match="portable filename stem",
    ):
        _ = harness.load_cases()
    with pytest.raises(
        harness.SanitizerHarnessError,
        match="portable filename stem",
    ):
        _ = harness.SanitizerCase(
            identifier=identifier,
            input_bytes=b"",
            source_bytes=b"D",
        )


def test_sanitizer_rejects_case_insensitive_fixture_name_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case-only aliases cannot overwrite one another on Windows hosts."""
    document = {
        "schema_version": harness.SCHEMA_VERSION,
        "source_root": "tests/compatibility/specification",
        "cases": [
            {"id": identifier, "source_hex": "44", "input_hex": ""}
            for identifier in ("roundtrip", "RoundTrip")
        ],
    }
    cases = tmp_path / "cases.json"
    _ = cases.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(harness, "CASES", cases)
    with pytest.raises(
        harness.SanitizerHarnessError,
        match="duplicate sanitizer case: RoundTrip",
    ):
        _ = harness.load_cases()


def test_sanitizer_case_allows_safe_portable_filename_stem() -> None:
    """Portable punctuation remains admissible in fixture names."""
    identifier = "case_2.part-b"
    case = harness.SanitizerCase(
        identifier=identifier,
        input_bytes=b"",
        source_bytes=b"D",
    )
    assert case.identifier == identifier


def test_sanitizer_evidence_rejects_invalid_utf8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reviewed evidence encoding failure remains a typed harness error."""
    evidence = tmp_path / "evidence.json"
    _ = evidence.write_bytes(bytes((0x7b, 0xff, 0x7d)))
    monkeypatch.setattr(harness, "EVIDENCE", evidence)
    with pytest.raises(harness.SanitizerHarnessError, match="cannot load"):
        _ = harness.load_evidence()


def test_sanitizer_evidence_rejects_duplicate_json_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reviewed sanitizer evidence rejects ambiguous JSON identities."""
    evidence = tmp_path / "evidence.json"
    _ = evidence.write_text(
        '{"schema_version":1,"schema_version":1}',
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setattr(harness, "EVIDENCE", evidence)
    with pytest.raises(
        harness.SanitizerHarnessError,
        match="duplicate sanitizer JSON key: schema_version",
    ):
        _ = harness.load_evidence()


def test_sanitizer_harness_reproduces_reviewed_findings() -> None:
    """Pinned Clang reproduces clean output and both H-003 findings."""
    if not harness.is_supported():
        pytest.skip("pinned Windows sanitizer toolchain is unavailable")
    assert harness.run_harness() == harness.load_evidence()
