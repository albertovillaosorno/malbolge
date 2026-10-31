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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Validate traceability from mathematical equations to executable tests.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Validate traceability from mathematical equations to executable tests."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from pathlib import PureWindowsPath
import re
from stat import S_ISDIR
from stat import S_ISLNK
from stat import S_ISREG
import sys
import tomllib
from typing import Never
from typing import cast

from scripts.repository_root import repository_root

ROOT = repository_root(Path(__file__))
MANIFEST = (
    ROOT
    / "src/specification/formal-model/math/specification"
    / "correspondence.toml"
)
MATH_ROOT = ROOT / "src/specification/formal-model/math"
SCHEMA_VERSION = 1
MAX_CORRESPONDENCE_SOURCE_BYTES = 4 * 1024 * 1024
TEX_EXTENSION = ".tex"
PARENT_SEGMENT = ".."
ALGORITHMS_SEGMENT = "algorithms"
TESTS_SEGMENT = "tests"
RESEARCH_TEST_PATH_PARTS = 4
LABEL_PATTERN = re.compile(r"\\label\{(eq:[^}]+)\}")
ENTRY_KEYS = frozenset(
    {
        "domain",
        "evidence",
        "id",
        "label",
        "mechanism",
        "tex",
    }
)
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
    message = " ".join(
        (
            f"{context} keys differ:",
            f"missing={sorted(expected - observed)},",
            f"unknown={sorted(observed - expected)}",
        )
    )
    _fail(message)


def _require_physical_member(
    path: Path,
    context: str,
    relative: Path,
    *,
    directory: bool,
) -> None:
    """Check one physical component without following aliases."""
    try:
        status = path.lstat()
    except FileNotFoundError:
        _fail(f"{context} does not exist: {relative.as_posix()}")
    except OSError as error:
        _fail(f"{context} status failed: {error}")
    if S_ISLNK(status.st_mode) or path.is_junction():
        _fail(f"{context} must not redirect: {relative.as_posix()}")
    admitted = (
        S_ISDIR(status.st_mode) if directory else S_ISREG(status.st_mode)
    )
    if not admitted:
        _fail(f"{context} must be a physical regular artifact: {path}")


def _physical_repository_path(
    path: Path,
    context: str,
    *,
    directory: bool,
) -> None:
    """Reject aliases and special files throughout an evidence path."""
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        _fail(f"{context} must stay inside repository root: {path}")
    if PARENT_SEGMENT in relative.parts:
        _fail(f"{context} must not escape repository root: {path}")
    if not relative.parts:
        _fail(f"{context} must name a regular repository file: {path}")
    current = ROOT
    for index, component in enumerate(relative.parts):
        current /= component
        is_parent = index != len(relative.parts) - 1
        _require_physical_member(
            current, context, relative, directory=is_parent or directory
        )


def _source_fingerprint(
    status: os.stat_result,
    context: str,
) -> tuple[int, ...]:
    """Validate a regular source and capture mutation-sensitive identity.

    Returns:
        Device, inode, byte count, and modification/change timestamps.

    """
    if not S_ISREG(status.st_mode):
        _fail(f"{context} must be a physical regular artifact")
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _read_source_descriptor(
    path: Path,
    context: str,
    descriptor: int,
    *,
    expected: tuple[int, ...],
) -> bytes:
    """Verify that one opened source remains the same named regular file.

    Returns:
        The exact stable physical bytes read from that descriptor.

    """
    with os.fdopen(descriptor, "rb") as stream:
        if _source_fingerprint(os.fstat(stream.fileno()), context) != expected:
            _fail(f"{context} changed before read")
        payload = stream.read(MAX_CORRESPONDENCE_SOURCE_BYTES + 1)
        if len(payload) != expected[2]:
            _fail(f"{context} changed during read or exceeds byte limit")
        if (
            _source_fingerprint(os.fstat(stream.fileno()), context) != expected
            or _source_fingerprint(path.lstat(), context) != expected
        ):
            _fail(f"{context} changed during read")
        _physical_repository_path(path, context, directory=False)
        return payload


def _read_source_bytes(path: Path, context: str) -> bytes:
    """Read bounded, unredirected source bytes with physical admission.

    Returns:
        Exact source bytes from one stable, named regular file.

    """
    _physical_repository_path(path, context, directory=False)
    admitted = path.lstat()
    expected = _source_fingerprint(admitted, context)
    if admitted.st_size > MAX_CORRESPONDENCE_SOURCE_BYTES:
        _fail(f"{context} exceeds byte limit")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags)
    return _read_source_descriptor(
        path, context, descriptor, expected=expected
    )


def _read_source_text(path: Path, context: str) -> str:
    try:
        payload = _read_source_bytes(path, context)
        return payload.decode("utf-8")
    except UnicodeDecodeError as error:
        _fail(f"invalid {context} UTF-8: {error}")
    except OSError as error:
        _fail(f"cannot read {context}: {error}")


def _admit_tex_candidate(parent: Path, name: str) -> Path | None:
    """Admit a TeX file or reject a linked non-TeX directory.

    Returns:
        A physical TeX file, or ``None`` for other regular files.

    """
    candidate = parent / name
    if candidate.suffix == TEX_EXTENSION:
        _physical_repository_path(candidate, "equation source", directory=False)
        return candidate
    if candidate.is_symlink() and candidate.is_dir():
        _fail(f"mathematics directory must not redirect: {candidate}")
    return None


def _append_tex_candidates(
    parent: Path,
    filenames: list[str],
    sources: list[Path],
) -> None:
    """Collect admitted TeX files from one physical directory."""
    for name in filenames:
        candidate = _admit_tex_candidate(parent, name)
        if candidate is not None:
            sources.append(candidate)


def _tex_sources() -> tuple[Path, ...]:
    _physical_repository_path(MATH_ROOT, "mathematics root", directory=True)
    sources: list[Path] = []

    def fail_walk(error: OSError) -> None:
        _fail(f"mathematics evidence scan failed: {error}")

    for parent, directories, filenames in MATH_ROOT.walk(on_error=fail_walk):
        _physical_repository_path(
            parent, "mathematics directory", directory=True
        )
        for name in directories:
            _physical_repository_path(
                parent / name, "mathematics directory", directory=True
            )
        _append_tex_candidates(parent, filenames, sources)
    return tuple(sorted(sources))


def _repository_path(raw: str, context: str) -> Path:
    relative = Path(raw)
    windows_relative = PureWindowsPath(raw)
    native_admitted = (
        not relative.is_absolute() and PARENT_SEGMENT not in relative.parts
    )
    windows_admitted = (
        not windows_relative.drive
        and not windows_relative.root
        and PARENT_SEGMENT not in windows_relative.parts
    )
    if not native_admitted or not windows_admitted:
        _fail(f"{context} must be repository-relative: {raw}")
    resolved = ROOT / relative
    _physical_repository_path(resolved, context, directory=False)
    return resolved


def evidence_path_allowed(path: str) -> bool:
    """Return whether an evidence path belongs to an executable test owner.

    Returns:
        True for repository integration tests or research-mirror test files.

    """
    if path.startswith(f"{TESTS_SEGMENT}/"):
        return True
    parts = Path(path).parts
    return (
        len(parts) >= RESEARCH_TEST_PATH_PARTS
        and parts[0] == ALGORITHMS_SEGMENT
        and parts[2] == TESTS_SEGMENT
    )


def _evidence(raw: object, context: str) -> Evidence:
    reference = _string(raw, context)
    path, separator, test = reference.partition("::")
    if not separator or not path or not test:
        _fail(f"{context} must use tests/path::test_name")
    if not evidence_path_allowed(path):
        _fail(f"{context} must reference a repository test surface: {path}")
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
    for source in _tex_sources():
        text = _read_source_text(source, "equation source")
        for match in LABEL_PATTERN.finditer(text):
            label = match.group(1)
            if label in labels:
                _fail(f"duplicate mathematical equation label: {label}")
            labels.add(label)
    return frozenset(labels)


def _test_exists(evidence: Evidence) -> bool:
    path = _repository_path(evidence.path, "evidence path")
    text = _read_source_text(path, "evidence path")
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
        if _read_source_text(source, "equation source").count(marker) != 1:
            _fail(f"equation label is not unique in source: {entry.label}")
        for evidence in entry.evidence:
            if not _test_exists(evidence):
                source = f"{evidence.path}::{evidence.test}"
                _fail(f"evidence test not found: {source}")
    return frozenset(labels)


def _validate_label_closure(manifest_labels: frozenset[str]) -> None:
    equation_labels = _equation_labels()
    if equation_labels == manifest_labels:
        return
    message = " ".join(
        (
            "equation/manifest labels differ:",
            f"unmapped={sorted(equation_labels - manifest_labels)},",
            f"unknown={sorted(manifest_labels - equation_labels)}",
        )
    )
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
    _physical_repository_path(
        MANIFEST, "correspondence manifest", directory=False
    )
    return validate_text(_read_source_text(MANIFEST, "correspondence manifest"))


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
