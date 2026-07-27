# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Validate traceability from mathematical equations to executable tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
import tomllib
from typing import Never
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "math" / "specification" / "correspondence.toml"
SPECIFICATION_ROOT = ROOT / "math" / "specification"
SCHEMA_VERSION = 1
PARENT_SEGMENT = ".."
LABEL_PATTERN = re.compile(r"\\label\{(eq:[^}]+)\}")
ENTRY_KEYS = frozenset({
    "domain",
    "evidence",
    "id",
    "label",
    "mechanism",
    "tex",
})
TOP_LEVEL_KEYS = frozenset({"correspondence", "schema_version"})


class CorrespondenceError(ValueError):
    """Invalid mathematical correspondence manifest or evidence reference."""


@dataclass(frozen=True, slots=True)
class Evidence:
    """One executable test function proving part of an equation domain."""

    path: str
    test: str


@dataclass(frozen=True, slots=True)
class Correspondence:
    """One normative equation and its explicit executable correspondence."""

    domain: str
    evidence: tuple[Evidence, ...]
    identifier: str
    label: str
    mechanism: str
    tex: str


def _fail(message: str) -> Never:
    raise CorrespondenceError(message)


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(f"{context} must be a table")
    raw = cast("dict[object, object]", value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            _fail(f"{context} contains a non-string key")
        result[key] = item
    return result


def _array(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        _fail(f"{context} must be an array")
    return cast("list[object]", value)


def _string(value: object, context: str) -> str:
    if type(value) is not str or not value:
        _fail(f"{context} must be a non-empty string")
    return value


def _integer(value: object, context: str) -> int:
    if type(value) is not int:
        _fail(f"{context} must be an integer")
    return value


def _exact_keys(
    value: dict[str, object],
    expected: frozenset[str],
    context: str,
) -> None:
    observed = frozenset(value)
    if observed == expected:
        return
    message = " ".join((
        f"{context} keys differ:",
        f"missing={sorted(expected - observed)},",
        f"unknown={sorted(observed - expected)}",
    ))
    _fail(message)


def _repository_path(raw: str, context: str) -> Path:
    relative = Path(raw)
    if relative.is_absolute() or PARENT_SEGMENT in relative.parts:
        _fail(f"{context} must be repository-relative: {raw}")
    resolved = ROOT / relative
    if not resolved.is_file():
        _fail(f"{context} does not exist: {raw}")
    return resolved


def _evidence(raw: object, context: str) -> Evidence:
    reference = _string(raw, context)
    path, separator, test = reference.partition("::")
    if not separator or not path or not test:
        _fail(f"{context} must use tests/path::test_name")
    if not path.startswith("tests/"):
        _fail(f"{context} must reference tests/: {path}")
    return Evidence(path=path, test=test)


def _entry(value: object, index: int) -> Correspondence:
    context = f"correspondence[{index}]"
    item = _mapping(value, context)
    _exact_keys(item, ENTRY_KEYS, context)
    evidence_values = _array(item["evidence"], f"{context}.evidence")
    if not evidence_values:
        _fail(f"{context}.evidence must not be empty")
    return Correspondence(
        domain=_string(item["domain"], f"{context}.domain"),
        evidence=tuple(
            _evidence(evidence, f"{context}.evidence[{evidence_index}]")
            for evidence_index, evidence in enumerate(evidence_values)
        ),
        identifier=_string(item["id"], f"{context}.id"),
        label=_string(item["label"], f"{context}.label"),
        mechanism=_string(item["mechanism"], f"{context}.mechanism"),
        tex=_string(item["tex"], f"{context}.tex"),
    )


def _parse(text: str) -> tuple[Correspondence, ...]:
    try:
        parsed = cast("object", tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        _fail(f"invalid TOML: {error}")
    document = _mapping(parsed, "manifest")
    _exact_keys(document, TOP_LEVEL_KEYS, "manifest")
    version = _integer(document["schema_version"], "manifest.schema_version")
    if version != SCHEMA_VERSION:
        _fail(f"unsupported correspondence schema: {version}")
    values = _array(document["correspondence"], "manifest.correspondence")
    if not values:
        _fail("manifest.correspondence must not be empty")
    return tuple(_entry(value, index) for index, value in enumerate(values))


def _equation_labels() -> frozenset[str]:
    labels: set[str] = set()
    for source in sorted(SPECIFICATION_ROOT.rglob("*.tex")):
        text = source.read_text(encoding="utf-8")
        for match in LABEL_PATTERN.finditer(text):
            label = match.group(1)
            if label in labels:
                _fail(f"duplicate mathematical equation label: {label}")
            labels.add(label)
    return frozenset(labels)


def _test_exists(evidence: Evidence) -> bool:
    path = _repository_path(evidence.path, "evidence path")
    text = path.read_text(encoding="utf-8")
    function = re.escape(evidence.test)
    pattern = re.compile(rf"(?:fn|def)\s+{function}\s*\(")
    return pattern.search(text) is not None


def _record_unique(value: str, seen: set[str], context: str) -> None:
    if value in seen:
        _fail(f"duplicate {context}: {value}")
    seen.add(value)


def _validate_entry_references(
    entries: tuple[Correspondence, ...],
) -> frozenset[str]:
    identifiers: set[str] = set()
    labels: set[str] = set()
    for entry in entries:
        _record_unique(entry.identifier, identifiers, "correspondence id")
        _record_unique(entry.label, labels, "correspondence label")
        source = _repository_path(entry.tex, "equation source")
        marker = rf"\label{{{entry.label}}}"
        if source.read_text(encoding="utf-8").count(marker) != 1:
            _fail(f"equation label is not unique in source: {entry.label}")
        for evidence in entry.evidence:
            if not _test_exists(evidence):
                _fail(
                    f"evidence test not found: {evidence.path}::{evidence.test}"
                )
    return frozenset(labels)


def _validate_label_closure(manifest_labels: frozenset[str]) -> None:
    equation_labels = _equation_labels()
    if equation_labels == manifest_labels:
        return
    message = " ".join((
        "equation/manifest labels differ:",
        f"unmapped={sorted(equation_labels - manifest_labels)},",
        f"unknown={sorted(manifest_labels - equation_labels)}",
    ))
    _fail(message)


def validate_text(text: str) -> tuple[Correspondence, ...]:
    """Validate one manifest text against current math and test sources.

    Returns:
        Stable correspondence entries after all traceability checks succeed.

    """
    entries = _parse(text)
    manifest_labels = _validate_entry_references(entries)
    _validate_label_closure(manifest_labels)
    return entries


def validate_repository() -> tuple[Correspondence, ...]:
    """Validate the checked-in mathematical correspondence manifest.

    Returns:
        Stable correspondence entries after all repository checks succeed.

    """
    return validate_text(MANIFEST.read_text(encoding="utf-8"))


def main() -> int:
    """Validate equation/test traceability and return process status.

    Returns:
        Zero for a closed correspondence graph, otherwise one.

    """
    try:
        entries = validate_repository()
    except (OSError, CorrespondenceError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(
        f"mathematical correspondence valid: {len(entries)} equations\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
