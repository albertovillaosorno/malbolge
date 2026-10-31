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
#   - Regression tests for reproducible experiment manifest schema v1.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for reproducible experiment manifest schema v1."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from scripts.validate import experiment_manifest as validator

EXPECTED_IDS = (
    "adaptive-accelerator-resource-budgeting",
    "compact-guest-bytecode-strategy",
    "malbolge-specific-optimization-mathematics",
    "pytorch-search-orchestration",
    "search-pruning-and-state-canonicalization",
    "self-modification-state-graph-optimizer",
    "stochastic-and-guided-search",
    "superoptimization-research-program",
    "template",
)
RESOURCE_EXHAUSTED = "resource-exhausted"
RUN_COMMIT = "a" * 40
RUN_HASH = "b" * 64
CURRENT_PROFILE_FINGERPRINT = (
    "malbolge-profile-v1:sha256:"
    "e33e1488162dffdc8bad9102df8eed3f8aac294d057b4f7ad7a389906963fc50"
)
MISMATCH_FINGERPRINT = "malbolge-profile-v1:sha256:" + ("0" * 64)
PROFILE_INDEPENDENT = "profile-independent"


def _run_manifest(**overrides: str) -> str:
    values = {
        "accelerator": "none",
        "commit": RUN_COMMIT,
        "host": "windows-x86_64-test",
        "outcome": "success",
        "raw_output": "algorithms/example/out/raw.json",
        "toolchain": "python-3.14.6",
        "workload_sha256": RUN_HASH,
    }
    values.update(overrides)
    return f"""schema_version = 1

[experiment]
id = "example"
record_kind = "run"
method_class = "benchmarking"
seed = 7

[challenge]
family = "fixture"
difficulty = 1
target_profile = "malbolge-2026.2"
target_profile_fingerprint = "{CURRENT_PROFILE_FINGERPRINT}"

[budget]
seconds = 1

[verification]
required = true
oracle = "trusted-fixture"

[provenance]
implementation = "algorithms/example/"
configuration = "algorithms/example/experiment.toml"
output = "algorithms/example/out/"

[run]
commit = "{values["commit"]}"
workload_sha256 = "{values["workload_sha256"]}"
host = "{values["host"]}"
accelerator = "{values["accelerator"]}"
toolchain = "{values["toolchain"]}"
outcome = "{values["outcome"]}"
raw_output = "{values["raw_output"]}"
"""


def _expect_failure(text: str, message: str) -> None:
    try:
        _ = validator.parse_manifest(text)
    except validator.ExperimentManifestError as error:
        if message not in str(error):
            mismatch = f"unexpected manifest error: {error}"
            raise AssertionError(mismatch) from error
        return
    failure = "invalid experiment manifest unexpectedly succeeded"
    raise AssertionError(failure)


def test_manifest_file_rejects_invalid_utf8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manifest file encoding failure remains a typed validation error."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    path = tmp_path / "experiment.toml"
    _ = path.write_bytes(bytes((0x5B, 0xFF, 0x5D)))
    with pytest.raises(
        validator.ExperimentManifestError,
        match="invalid experiment manifest UTF-8",
    ):
        _ = validator.validate_repository_manifest(path)


def test_repository_experiment_manifests_are_schema_valid() -> None:
    """Every mirrored algorithm carries one valid version-one plan manifest."""
    manifests = validator.validate_repository()
    assert tuple(item.identifier for item in manifests) == EXPECTED_IDS


def test_repo_relative_manifest_path_admits_canonical_identity() -> None:
    """Relative and absolute spellings share one in-repository identity."""
    absolute = (
        validator.ROOT
        / "src/research/algorithms/domain/algorithms/template/experiment.toml"
    )
    relative = absolute.relative_to(validator.ROOT)
    assert validator.validate_repository_manifest(relative) == (
        validator.validate_repository_manifest(absolute)
    )


def _repository_manifest_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Clone one canonical template under a detached repository-shaped root.

    Returns:
        A physical and schema-valid experiment manifest path.

    """
    relative = Path(
        "src/research/algorithms/domain/algorithms/template/experiment.toml"
    )
    original = validator.ROOT / relative
    fixture = tmp_path / relative
    fixture.parent.mkdir(parents=True)
    _ = fixture.write_bytes(original.read_bytes())
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    return fixture


def test_repository_manifest_rejects_symlink_leaf_and_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid schema and provenance cannot authorize a linked manifest path."""
    source = _repository_manifest_fixture(tmp_path, monkeypatch)
    alias = source.with_name("linked.toml")
    linked_dir = tmp_path / "linked-directory"
    try:
        alias.symlink_to(source)
        linked_dir.symlink_to(source.parent, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unsupported: {error}")
    for redirected in (alias, linked_dir / source.name):
        with pytest.raises(
            validator.ExperimentManifestError, match=r"redirect|regular"
        ):
            _ = validator.validate_repository_manifest(redirected)


def test_repository_manifest_rejects_external_alias_to_valid_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An outside symlink cannot be canonicalized into repository authority."""
    source = _repository_manifest_fixture(tmp_path, monkeypatch)
    external = tmp_path.parent / f"{tmp_path.name}-external-link.toml"
    try:
        external.symlink_to(source)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unsupported: {error}")
    try:
        with pytest.raises(
            validator.ExperimentManifestError, match="escapes repository"
        ):
            _ = validator.validate_repository_manifest(external)
    finally:
        external.unlink(missing_ok=True)


def test_repository_manifest_rejects_parent_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parent segments are not accepted as evidence path canonicalization."""
    source = _repository_manifest_fixture(tmp_path, monkeypatch)
    alternate = source.parent / ".." / source.parent.name / source.name
    with pytest.raises(
        validator.ExperimentManifestError, match="must not traverse parents"
    ):
        _ = validator.validate_repository_manifest(alternate)


def test_manifest_reader_rejects_nonregular_missing_and_oversized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bounded regular admission rejects a directory, missing source or size."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    with pytest.raises(validator.ExperimentManifestError, match="not found"):
        _ = validator.validate_repository_manifest(tmp_path)
    with pytest.raises(validator.ExperimentManifestError, match="not found"):
        _ = validator.validate_repository_manifest(tmp_path / "missing.toml")
    oversized = tmp_path / "oversized.toml"
    with oversized.open("wb") as stream:
        _ = stream.truncate(validator.MAX_MANIFEST_BYTES + 1)
    with pytest.raises(validator.ExperimentManifestError, match="byte limit"):
        _ = validator.validate_repository_manifest(oversized)


def test_repository_manifest_refuses_fifo_without_blocking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repository admission excludes a writerless FIFO before opening it."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    mkfifo = cast("Callable[[Path], None] | None", getattr(os, "mkfifo", None))
    if mkfifo is None:
        pytest.skip("FIFO not supported on this platform")
    fifo = tmp_path / "source.fifo"
    mkfifo(fifo)
    with pytest.raises(validator.ExperimentManifestError, match="not found"):
        _ = validator.validate_repository_manifest(fifo)


def test_manifest_reader_rejects_same_byte_swap_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing a regular file before descriptor opening invalidates it."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    replacement = tmp_path / "replacement.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    _ = replacement.write_bytes(source.read_bytes())
    real_open = os.open
    swapped = False

    def swap_on_open(path: Path, flags: int) -> int:
        nonlocal swapped
        if path == source:
            _ = replacement.replace(source)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_on_open)
    with pytest.raises(validator.ExperimentManifestError, match="changed before read"):
        _ = validator.validate_repository_manifest(source)
    assert swapped


def test_manifest_reader_rejects_same_byte_swap_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An identically formatted replacement does not validate stale bytes."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    replacement = tmp_path / "replacement.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    _ = replacement.write_bytes(source.read_bytes())
    real_open = os.open
    real_lstat = Path.lstat
    opened = swapped = False

    def track_open(path: Path, flags: int) -> int:
        nonlocal opened
        descriptor = real_open(path, flags)
        if path == source:
            opened = True
        return descriptor

    def swap_at_recheck(path: Path) -> os.stat_result:
        nonlocal swapped
        if path == source and opened and not swapped:
            _ = replacement.replace(source)
            swapped = True
        return real_lstat(path)

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(Path, "lstat", swap_at_recheck)
    with pytest.raises(validator.ExperimentManifestError, match="changed during read"):
        _ = validator.validate_repository_manifest(source)
    assert swapped


def test_manifest_reader_rejects_in_place_change_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same-inode rewrite after byte collection invalidates source evidence."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    real_open = os.open
    real_lstat = Path.lstat
    opened = modified = False

    def track_open(path: Path, flags: int) -> int:
        nonlocal opened
        descriptor = real_open(path, flags)
        if path == source:
            opened = True
        return descriptor

    def modify_at_recheck(path: Path) -> os.stat_result:
        nonlocal modified
        if path == source and opened and not modified:
            with source.open("r+b") as stream:
                _ = stream.write(b"x")
            os.utime(source, ns=(0, 0))
            modified = True
        return real_lstat(path)

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(Path, "lstat", modify_at_recheck)
    with pytest.raises(validator.ExperimentManifestError, match="changed during read"):
        _ = validator.validate_repository_manifest(source)
    assert modified


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_repository_manifest_inspection_failures_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Malformed host filesystem failures cannot escape public admission."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    real_is_file = Path.is_file

    def fault_is_file(path: Path) -> bool:
        if path == source:
            raise fault_type("injected is_file fault")
        return real_is_file(path)

    monkeypatch.setattr(Path, "is_file", fault_is_file)
    with pytest.raises(
        validator.ExperimentManifestError,
        match="experiment manifest cannot be inspected",
    ):
        _ = validator.validate_repository_manifest(source)


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
@pytest.mark.parametrize(
    "operation", ("lstat", "is_symlink", "is_junction", "open", "fstat", "fdopen")
)
def test_manifest_reader_host_failures_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """An untrusted host failure cannot bypass the manifest error boundary."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    if operation in {"lstat", "is_symlink", "is_junction"}:
        original = {
            "lstat": Path.lstat,
            "is_symlink": Path.is_symlink,
            "is_junction": Path.is_junction,
        }[operation]

        def fault_path(path: Path) -> os.stat_result | bool:
            if path == source:
                raise fault_type(f"injected {operation} fault")
            return original(path)

        monkeypatch.setattr(Path, operation, fault_path)
    elif operation == "open":
        original_open = os.open

        def fault_open(path: Path, flags: int) -> int:
            if path == source:
                raise fault_type("injected open fault")
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", fault_open)
    elif operation == "fstat":

        def fault_fstat(_descriptor: int) -> os.stat_result:
            raise fault_type("injected fstat fault")

        monkeypatch.setattr(os, "fstat", fault_fstat)
    else:

        def fault_fdopen(_descriptor: int, _mode: str) -> object:
            raise fault_type("injected fdopen fault")

        monkeypatch.setattr(os, "fdopen", fault_fdopen)
    with pytest.raises(
        validator.ExperimentManifestError,
        match="experiment manifest cannot be read",
    ):
        _ = validator.validate_repository_manifest(source)


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
def test_manifest_fdopen_failure_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A failed stream wrapper must not leak the private opened descriptor."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    real_open = os.open
    opened: list[int] = []

    def track_open(path: Path, flags: int) -> int:
        descriptor = real_open(path, flags)
        if path == source:
            opened.append(descriptor)
        return descriptor

    def fault_fdopen(_descriptor: int, _mode: str) -> object:
        raise fault_type("injected fdopen fault")

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(os, "fdopen", fault_fdopen)
    with pytest.raises(validator.ExperimentManifestError):
        _ = validator.validate_repository_manifest(source)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


def test_direct_experiment_toml_admits_only_bounded_exact_utf8() -> None:
    """Direct TOML entry points use the same bounded wire-text boundary."""

    class _ForgedText(str):  # ruff: ignore[subclass-builtin]
        """An in-memory string with caller-controlled inherited behavior."""

        __slots__ = ()

    source = _run_manifest()
    if not source.endswith("\n"):
        source += "\n"
    limit = validator.MAX_MANIFEST_BYTES
    exact = source + "#" + "x" * (limit - len(source) - 1)
    assert validator.parse_manifest(exact)
    with pytest.raises(validator.ExperimentManifestError, match="byte limit"):
        validator.parse_manifest(exact + "x")
    with pytest.raises(validator.ExperimentManifestError, match="byte limit"):
        validator.parse_manifest(source + "#" + "é" * (limit // 2))
    with pytest.raises(validator.ExperimentManifestError, match="UTF-8"):
        validator.parse_manifest(source + "#\ud800")
    with pytest.raises(validator.ExperimentManifestError, match="exact str"):
        validator.parse_manifest(_ForgedText(source))


def test_manifest_nested_array_parser_capacity_is_typed() -> None:
    """Deep but bounded TOML must not leak raw host RecursionError."""
    nested = "[" * 1000 + "1" + "]" * 1000
    text = _run_manifest() + "\nparser_probe = " + nested + "\n"
    _expect_failure(text, "invalid TOML exceeds host parser capacity")


def test_manifest_oversized_decimal_token_fails_typed() -> None:
    """Host parser digit limits cannot leak untyped ValueErrors."""
    limit = sys.get_int_max_str_digits()
    if limit == 0 or limit > 20_000:
        pytest.skip("host decimal digit limit unavailable")
    text = _run_manifest().replace("seconds = 1", "seconds = " + "9" * (limit + 1))
    _expect_failure(text, "invalid TOML exceeds host parser capacity")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("implementation", "algorithms/example/"),
        ("configuration", "algorithms/example/experiment.toml"),
        ("output", "algorithms/example/out/"),
        ("raw_output", "algorithms/example/out/raw.json"),
    ),
)
def test_manifest_paths_reject_toml_escaped_nul(field: str, value: str) -> None:
    """Escaped NUL path segments fail typed admission before consumers use them."""
    text = _run_manifest().replace(
        f'{field} = "{value}"', f'{field} = "algorithms/\\u0000invalid"'
    )
    _expect_failure(text, "must not contain NUL")


def test_manifest_rejects_windows_drive_relative_path() -> None:
    """Drive-relative Windows syntax cannot redirect retained run output."""
    _expect_failure(
        _run_manifest(raw_output="D:escape"),
        "must be repository-relative",
    )


def test_recorded_run_requires_exact_commit_and_workload_hash() -> None:
    """Recorded evidence cannot omit exact source and workload identity."""
    _expect_failure(
        _run_manifest(commit="short"),
        "lowercase 40-hex Git commit",
    )
    _expect_failure(
        _run_manifest(workload_sha256="short"),
        "lowercase SHA-256 hex",
    )


def test_recorded_run_retains_negative_outcome_identity() -> None:
    """A non-success run remains a valid recorded experiment outcome."""
    manifest = validator.parse_manifest(_run_manifest(outcome=RESOURCE_EXHAUSTED))
    assert manifest.run is not None
    assert manifest.run.outcome == RESOURCE_EXHAUSTED


def test_recorded_run_rejects_unknown_outcome() -> None:
    """Unknown run outcomes fail closed."""
    _expect_failure(_run_manifest(outcome="lucky"), "unsupported run outcome")


def test_plan_requires_positive_stopping_bound() -> None:
    """A research plan without a positive budget is not reconstructible."""
    text = _run_manifest().replace("seconds = 1", "seconds = 0")
    _expect_failure(text, "positive integer stopping bound")


def test_verification_cannot_be_disabled_by_manifest() -> None:
    """Research configuration cannot make semantic verification optional."""
    text = _run_manifest().replace("required = true", "required = false")
    _expect_failure(text, "verification.required must be true")


def test_plan_cannot_smuggle_recorded_run_metadata() -> None:
    """A plan does not masquerade as already observed run evidence."""
    text = _run_manifest().replace('record_kind = "run"', 'record_kind = "plan"')
    _expect_failure(text, "plan experiment manifest must not contain a run table")


def test_canonical_target_profile_requires_fingerprint() -> None:
    """Canonical IDs cannot appear in manifests without immutable identity."""
    text = _run_manifest().replace(
        f'target_profile_fingerprint = "{CURRENT_PROFILE_FINGERPRINT}"\n',
        "",
    )
    _expect_failure(text, "target_profile_fingerprint is required")


def test_canonical_target_profile_mismatch_is_deterministic() -> None:
    """A stale artifact binding uses the shared profile mismatch diagnostic."""
    text = _run_manifest().replace(
        CURRENT_PROFILE_FINGERPRINT,
        MISMATCH_FINGERPRINT,
    )
    expected = " ".join(
        (
            "MALBOLGE-PROFILE-ID-001",
            "profile=malbolge-2026.2",
            f"expected={MISMATCH_FINGERPRINT}",
            f"observed={CURRENT_PROFILE_FINGERPRINT}",
        )
    )
    _expect_failure(text, expected)


def test_unknown_target_profile_never_falls_back() -> None:
    """Unknown artifact target identity cannot select a nearby profile."""
    text = _run_manifest().replace(
        'target_profile = "malbolge-2026.2"',
        'target_profile = "malbolge-current-ish"',
    )
    _expect_failure(text, "unsupported manifest challenge target profile")


def test_noncanonical_target_scope_forbids_profile_fingerprint() -> None:
    """Meta scopes cannot masquerade as canonical profile identities."""
    text = _run_manifest().replace(
        'target_profile = "malbolge-2026.2"',
        'target_profile = "profile-independent"',
    )
    _expect_failure(text, "must be absent for noncanonical target scope")


def test_profile_independent_scope_is_valid_without_fingerprint() -> None:
    """A declared profile-independent experiment remains explicitly unbound."""
    text = (
        _run_manifest()
        .replace(
            'target_profile = "malbolge-2026.2"',
            'target_profile = "profile-independent"',
        )
        .replace(
            f'target_profile_fingerprint = "{CURRENT_PROFILE_FINGERPRINT}"\n',
            "",
        )
    )

    manifest = validator.parse_manifest(text)

    assert manifest.target_profile == PROFILE_INDEPENDENT
    assert manifest.target_profile_fingerprint is None
