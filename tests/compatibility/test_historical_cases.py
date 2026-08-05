# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Executable integrity of the historical compatibility case registry.
# - Must-Not:
#   - Reimplement VM semantics or accept unreferenced catalogue claims.
# - Allows:
#   - Inputs: the checked-in TOML registry and referenced test sources.
#   - Outputs: exact issue coverage, fixture, and evidence assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another registry version gains an independent schema.
# - Merge-When:
#   - Merge when another suite owns identical historical-case integrity.
# - Summary:
#   - Binds every H-001 through H-010 case to executable evidence.
# - Description:
#   - Proves IDs, issues, fixtures, and named test functions resolve exactly.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Missing, duplicate, malformed, or decorative evidence fails closed.
#

"""Historical compatibility registry integrity tests."""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "tests/compatibility/specification/cases.toml"
EXPECTED_ISSUES = {f"H-{number:03d}" for number in range(1, 11)}
EVIDENCE = re.compile(
    r"^(?P<path>tests/[A-Za-z0-9_./-]+\.(?:rs|py))::"
    r"(?P<function>[a-z][a-z0-9_]*)$"
)


def _cases() -> list[dict[str, object]]:
    document = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))
    cases = document.get("case")
    assert isinstance(cases, list)
    assert cases
    assert all(isinstance(case, dict) for case in cases)
    return cases


def _matches_function_signature(line: str, name: str) -> bool:
    stripped = line.strip()
    prefixes = ("fn ", "def ", "pub fn ", "async fn ", "pub async fn ")
    for prefix in prefixes:
        signature = prefix + name
        if stripped.startswith(signature):
            remainder = stripped.removeprefix(signature)
            return remainder.startswith(("(", "<"))
    return False


def _function_exists(path: Path, name: str) -> bool:
    source = path.read_text(encoding="utf-8")
    return any(
        _matches_function_signature(line, name)
        for line in source.splitlines()
    )


def test_historical_registry_covers_every_catalogue_issue() -> None:
    """The registry covers exactly H-001 through H-010 with unique case IDs."""
    cases = _cases()
    identifiers = [case.get("id") for case in cases]
    assert all(isinstance(identifier, str) for identifier in identifiers)
    assert len(identifiers) == len(set(identifiers))
    issues = {case.get("issue") for case in cases}
    assert issues == EXPECTED_ISSUES


def test_historical_registry_references_real_fixtures_and_tests() -> None:
    """Every fixture and named evidence function resolves."""
    for case in _cases():
        source = case.get("source")
        if source is not None:
            assert isinstance(source, str)
            assert (REGISTRY.parent / source).is_file()
        evidence = case.get("evidence")
        assert isinstance(evidence, list)
        assert evidence
        assert len(evidence) == len(set(evidence))
        for reference in evidence:
            assert isinstance(reference, str)
            matched = EVIDENCE.fullmatch(reference)
            assert matched is not None
            path = ROOT / matched.group("path")
            assert path.is_file()
            assert _function_exists(path, matched.group("function"))
