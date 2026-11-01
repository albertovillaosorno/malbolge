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
#   - Regression tests for research algorithm lifecycle policy.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for research algorithm lifecycle policy."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Self, cast, override

if TYPE_CHECKING:
    from typing import BinaryIO

import pytest

from scripts.validate import algorithm_lifecycle as validator

if TYPE_CHECKING:
    from os import stat_result

DECISION_DATE = "2026-07-27"
SUCCESSOR = "successor-v2"

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
EVIDENCE = "docs/research/methodology/scientific-method.md"
BENEFIT = "benchmarks/research/protocol/examples/deterministic.benchmark.toml"
RESEARCH = "docs/research/algorithms/template/research.md"
EXPERIMENT = "src/research/algorithms/domain/algorithms/template/experiment.toml"


def _base(state: str) -> str:
    return f"""schema_version = 1

[algorithm]
id = "template"
state = "{state}"
research_record = "{RESEARCH}"
experiment_manifest = "{EXPERIMENT}"
"""


def _promotion() -> str:
    return f"""
[promotion]
correctness = "{EVIDENCE}"
reproducibility = "docs/research/methodology/experiment-identity.md"
maintainability = "docs/research/methodology/algorithm-lifecycle.md"
portability = "docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md"
measured_benefit = "{BENEFIT}"
"""


def _decision(**extra: str) -> str:
    lines = [
        "",
        "[decision]",
        f"decided_on = {DECISION_DATE}",
        'reason = "fixture lifecycle decision"',
        f'evidence = "{EVIDENCE}"',
    ]
    lines.extend(f'{key} = "{value}"' for key, value in extra.items())
    return "\n".join(lines) + "\n"


def _expect_failure(text: str, message: str) -> None:
    try:
        _ = validator.parse_lifecycle(text)
    except validator.AlgorithmLifecycleError as error:
        if message not in str(error):
            mismatch = f"unexpected lifecycle validation error: {error}"
            raise AssertionError(mismatch) from error
        return
    failure = "invalid lifecycle unexpectedly succeeded"
    raise AssertionError(failure)


def test_direct_lifecycle_toml_admits_only_bounded_exact_utf8() -> None:
    """Direct TOML entry points use the same bounded wire-text boundary."""

    class _ForgedText(str):  # ruff: ignore[subclass-builtin]
        """An in-memory string with caller-controlled inherited behavior."""

        __slots__ = ()

    source = _base(validator.EXPERIMENTAL)
    if not source.endswith("\n"):
        source += "\n"
    limit = validator.MAX_LIFECYCLE_BYTES
    exact = source + "#" + "x" * (limit - len(source) - 1)
    assert validator.parse_lifecycle(exact)
    with pytest.raises(validator.AlgorithmLifecycleError, match="byte limit"):
        validator.parse_lifecycle(exact + "x")
    with pytest.raises(validator.AlgorithmLifecycleError, match="byte limit"):
        validator.parse_lifecycle(source + "#" + "é" * (limit // 2))
    with pytest.raises(validator.AlgorithmLifecycleError, match="UTF-8"):
        validator.parse_lifecycle(source + "#\ud800")
    with pytest.raises(validator.AlgorithmLifecycleError, match="exact str"):
        validator.parse_lifecycle(_ForgedText(source))


def test_lifecycle_nested_array_parser_capacity_is_typed() -> None:
    """Deep but bounded TOML must not leak raw host RecursionError."""
    nested = "[" * 1000 + "1" + "]" * 1000
    text = _base(validator.EXPERIMENTAL) + "\nparser_probe = " + nested + "\n"
    _expect_failure(text, "invalid TOML exceeds host parser capacity")


def test_lifecycle_decimal_digit_limit_fails_typed() -> None:
    """Host parser capacity cannot escape as a raw integer ValueError."""
    limit = sys.get_int_max_str_digits()
    if limit == 0 or limit > 20_000:
        pytest.skip("host decimal token limit unavailable")
    text = _base(validator.EXPERIMENTAL).replace(
        "schema_version = 1", "schema_version = " + "9" * (limit + 1)
    )
    _expect_failure(text, "invalid TOML exceeds host parser capacity")


def test_lifecycle_file_rejects_invalid_utf8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lifecycle file encoding failure remains a typed validation error."""
    path = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    _ = path.write_bytes(bytes((0x5B, 0xFF, 0x5D)))
    with pytest.raises(
        validator.AlgorithmLifecycleError,
        match="invalid algorithm lifecycle UTF-8",
    ):
        _ = validator.validate_repository_lifecycle(path)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
@pytest.mark.parametrize("operation", ("lstat", "open", "fdopen", "fstat", "read"))
def test_lifecycle_manifest_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """Malformed filesystem errors cannot bypass lifecycle file admission."""
    manifest = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    if operation == "lstat":
        original_lstat = Path.lstat

        def fail_lstat(path: Path) -> os.stat_result:
            if path == manifest:
                raise fault_type("injected lifecycle lstat fault")
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    elif operation == "open":
        original_open = os.open

        def fail_open(path: Path, flags: int) -> int:
            if path == manifest:
                raise fault_type("injected lifecycle open fault")
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", fail_open)
    elif operation == "fdopen":

        def fail_fdopen(_descriptor: int, _mode: str) -> object:
            raise fault_type("injected lifecycle fdopen fault")

        monkeypatch.setattr(os, "fdopen", fail_fdopen)
    elif operation == "fstat":

        def fail_fstat(_descriptor: int) -> os.stat_result:
            raise fault_type("injected lifecycle fstat fault")

        monkeypatch.setattr(os, "fstat", fail_fstat)
    else:

        def fail_read(_stream: BinaryIO, _status: os.stat_result, _path: Path) -> bytes:
            raise fault_type("injected lifecycle read fault")

        monkeypatch.setattr(validator, "_read_lifecycle_bytes", fail_read)
    with pytest.raises(
        validator.AlgorithmLifecycleError,
        match="algorithm lifecycle manifest cannot be read",
    ):
        _ = validator.validate_repository_lifecycle(manifest)


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
def test_lifecycle_fdopen_failure_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """An incomplete lifecycle stream wrapper releases the file descriptor."""
    manifest = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    original_open = os.open
    opened: list[int] = []

    def track_open(path: Path, flags: int) -> int:
        descriptor = original_open(path, flags)
        if path == manifest:
            opened.append(descriptor)
        return descriptor

    def fail_fdopen(_descriptor: int, _mode: str) -> object:
        raise fault_type("injected lifecycle fdopen fault")

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    with pytest.raises(validator.AlgorithmLifecycleError):
        _ = validator.validate_repository_lifecycle(manifest)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
def test_lifecycle_evidence_host_fault_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Host descriptor walk failure must not leak from evidence checking."""
    root = tmp_path / "root"
    proof = root / "docs/proof.md"
    proof.parent.mkdir(parents=True)
    _ = proof.write_text("evidence", encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", root)

    def fail_walk(_parts: tuple[str, ...]) -> None:
        raise fault_type("injected evidence descriptor fault")

    monkeypatch.setattr(validator, "_evidence_descriptor_walk", fail_walk)
    with pytest.raises(
        validator.AlgorithmLifecycleError, match="evidence not admitted"
    ):
        validator._require_existing(  # pyright: ignore[reportPrivateUsage]
            "docs/proof.md", "research record"
        )


def test_every_research_mirror_has_explicit_experimental_lifecycle() -> None:
    """All current research mirrors declare lifecycle state explicitly."""
    records = validator.validate_repository()
    assert tuple(record.identifier for record in records) == EXPECTED_IDS
    assert {record.state for record in records} == {validator.EXPERIMENTAL}


@pytest.mark.parametrize("field", ("research_record", "experiment_manifest"))
def test_lifecycle_paths_reject_toml_escaped_nul(field: str) -> None:
    """NUL cannot reach evidence path admission as an unhandled host error."""
    value = RESEARCH if field == "research_record" else EXPERIMENT
    text = _base(validator.EXPERIMENTAL).replace(
        f'{field} = "{value}"', f'{field} = "docs/\\u0000evidence"'
    )
    _expect_failure(text, "must not contain NUL")


def test_lifecycle_rejects_windows_drive_relative_path() -> None:
    """Drive-relative Windows syntax cannot redirect lifecycle evidence."""
    text = _base(validator.EXPERIMENTAL).replace(
        f'research_record = "{RESEARCH}"',
        'research_record = "D:escape"',
    )
    _expect_failure(text, "must be repository-relative")


@pytest.mark.parametrize(
    "reserved",
    (
        "docs/research/method.md:metadata",
        "docs/NUL.txt",
        "docs/CON/evidence.md",
        "docs/results.",
        "docs/results ",
    ),
)
def test_lifecycle_rejects_windows_reserved_evidence_name(reserved: str) -> None:
    """A retained negative result cannot alias an NTFS stream or device."""
    _expect_failure(
        _base(validator.REJECTED) + _decision(negative_results=reserved),
        "Windows-reserved",
    )


@pytest.mark.parametrize(
    ("state", "field", "original", "additional"),
    (
        (validator.EXPERIMENTAL, "research_record", RESEARCH, ""),
        (validator.EXPERIMENTAL, "experiment_manifest", EXPERIMENT, ""),
        (validator.PROMOTION_CANDIDATE, "correctness", EVIDENCE, _promotion()),
        (
            validator.REJECTED,
            "evidence",
            EVIDENCE,
            _decision(negative_results=EVIDENCE),
        ),
        (
            validator.REJECTED,
            "negative_results",
            EVIDENCE,
            _decision(negative_results=EVIDENCE),
        ),
    ),
)
def test_lifecycle_rejects_host_dependent_backslash_paths(
    state: str,
    field: str,
    original: str,
    additional: str,
) -> None:
    """Research evidence must name the same path on Linux and Windows."""
    source = _base(state) + additional
    existing = f'{field} = "{original}"'
    assert existing in source
    alias = original.replace("/", "\\")
    _expect_failure(
        source.replace(existing, f"{field} = '{alias}'", 1),
        "must use forward slashes",
    )


def test_promotion_candidate_requires_all_five_evidence_gates() -> None:
    """Promotion eligibility is evidence-linked rather than boolean asserted."""
    valid = _base(validator.PROMOTION_CANDIDATE) + _promotion()
    record = validator.parse_lifecycle(valid)
    assert record.promotion is not None
    assert record.promotion.measured_benefit == BENEFIT

    missing = valid.replace(f'measured_benefit = "{BENEFIT}"\n', "")
    _expect_failure(missing, "measured_benefit must be a non-empty string")


def test_promoted_state_requires_evidence_and_durable_decision() -> None:
    """Promotion requires both gate evidence and an explicit decision record."""
    text = _base(validator.PROMOTED) + _promotion() + _decision()
    record = validator.parse_lifecycle(text)
    assert record.promotion is not None
    assert record.decision is not None
    assert record.decision.decided_on.isoformat() == DECISION_DATE

    _expect_failure(
        _base(validator.PROMOTED) + _promotion(),
        "promoted requires a decision table",
    )


def test_rejection_requires_retained_negative_results() -> None:
    """Rejected algorithms preserve negative evidence."""
    text = _base(validator.REJECTED) + _decision(negative_results=BENEFIT)
    record = validator.parse_lifecycle(text)
    assert record.decision is not None
    assert record.decision.negative_results == BENEFIT

    _expect_failure(
        _base(validator.REJECTED) + _decision(),
        "rejected lifecycle state requires retained negative_results",
    )


@pytest.mark.parametrize("decided_on", ("2026-07-27T12:34:56", "2026-07-27T12:34:56Z"))
def test_lifecycle_decision_requires_exact_local_date(decided_on: str) -> None:
    """A TOML timestamp must not masquerade as the schema's local date."""
    text = (_base(validator.REJECTED) + _decision(negative_results=BENEFIT)).replace(
        f"decided_on = {DECISION_DATE}", f"decided_on = {decided_on}"
    )
    _expect_failure(text, "decided_on must be a TOML local date")


def test_retirement_requires_prior_gate_history_and_successor_identity() -> None:
    """Retired algorithms keep promotion evidence and name their successor."""
    text = _base(validator.RETIRED) + _promotion() + _decision(superseded_by=SUCCESSOR)
    record = validator.parse_lifecycle(text)
    assert record.promotion is not None
    assert record.decision is not None
    assert record.decision.superseded_by == SUCCESSOR

    _expect_failure(
        _base(validator.RETIRED) + _promotion() + _decision(),
        "retired lifecycle state requires superseded_by",
    )


def test_experimental_state_cannot_smuggle_promotion_or_decision_claims() -> None:
    """Experimental records do not masquerade as already promoted work."""
    _expect_failure(
        _base(validator.EXPERIMENTAL) + _promotion(),
        "experimental must not contain promotion evidence",
    )
    _expect_failure(
        _base(validator.EXPERIMENTAL) + _decision(),
        "experimental must not contain a decision table",
    )


def test_superseded_by_is_reserved_for_retired_state() -> None:
    """Promotion and rejection cannot silently encode retirement."""
    text = _base(validator.PROMOTED) + _promotion() + _decision(superseded_by="other")
    _expect_failure(text, "superseded_by is valid only for retired")


def _fixture_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lifecycle: str,
) -> Path:
    """Create a small complete repository for lifecycle evidence admission.

    Returns:
        The canonical lifecycle manifest location.

    """
    root = tmp_path / "repository"
    experiment = root / EXPERIMENT
    experiment.parent.mkdir(parents=True)
    _ = experiment.write_text("schema_version = 1\n")
    research = root / RESEARCH
    research.parent.mkdir(parents=True)
    _ = research.write_text("# Research\n")
    manifest = experiment.parent / "lifecycle.toml"
    _ = manifest.write_text(lifecycle)
    monkeypatch.setattr(validator, "ROOT", root)
    return manifest


@pytest.mark.parametrize("linked_parent", [False, True])
def test_lifecycle_evidence_cannot_redirect_outside_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    linked_parent: bool,
) -> None:
    """A linked evidence leaf or parent is not repository-owned evidence."""
    decision = _decision(negative_results="evidence/proof.md").replace(
        EVIDENCE, "evidence/proof.md"
    )
    manifest = _fixture_repository(
        tmp_path, monkeypatch, _base(validator.REJECTED) + decision
    )
    root = manifest.parents[6]
    outside = tmp_path / "outside"
    outside.mkdir()
    _ = (outside / "proof.md").write_text("unrelated outside evidence\n")
    if linked_parent:
        (root / "evidence").symlink_to(outside, target_is_directory=True)
    else:
        (root / "evidence").mkdir()
        (root / "evidence/proof.md").symlink_to(outside / "proof.md")
    with pytest.raises(validator.AlgorithmLifecycleError, match="evidence"):
        _ = validator.validate_repository_lifecycle(manifest)


def test_lifecycle_manifest_cannot_redirect_to_another_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lifecycle file itself must not be a symlink to foreign content."""
    manifest = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    source = tmp_path / "other.toml"
    _ = source.write_text(manifest.read_text())
    manifest.unlink()
    manifest.symlink_to(source)
    with pytest.raises(validator.AlgorithmLifecycleError, match="lifecycle"):
        _ = validator.validate_repository_lifecycle(manifest)


def test_lifecycle_rejects_post_status_symlink_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A link switched after lstat cannot substitute equal TOML bytes."""
    manifest = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    replacement = tmp_path / "replacement.toml"
    _ = replacement.write_text(manifest.read_text())
    original_lstat = Path.lstat
    changed = False

    def swap_after_status(candidate: Path) -> stat_result:
        nonlocal changed
        status = original_lstat(candidate)
        if candidate == manifest and not changed:
            manifest.unlink()
            manifest.symlink_to(replacement)
            changed = True
        return status

    monkeypatch.setattr(Path, "lstat", swap_after_status)
    with pytest.raises(validator.AlgorithmLifecycleError, match="lifecycle"):
        _ = validator.validate_repository_lifecycle(manifest)
    assert changed


def test_lifecycle_rejects_oversized_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A manifest above its size ceiling must fail before TOML decoding."""
    manifest = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    _ = manifest.write_bytes(b"#" * (validator.MAX_LIFECYCLE_BYTES + 1))
    with pytest.raises(validator.AlgorithmLifecycleError, match="size limit"):
        _ = validator.validate_repository_lifecycle(manifest)


def test_lifecycle_outside_repository_rejected_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A direct validator call must not read foreign lifecycle bytes."""
    _ = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    foreign = tmp_path / "outside/lifecycle.toml"
    foreign.parent.mkdir()
    _ = foreign.write_text(_base(validator.EXPERIMENTAL))

    def unexpected_read(_path: Path) -> str:
        raise AssertionError("outside lifecycle file read before path admission")

    monkeypatch.setattr(validator, "_read_utf8", unexpected_read)
    with pytest.raises(validator.AlgorithmLifecycleError, match="registered research"):
        _ = validator.validate_repository_lifecycle(foreign)


def test_lifecycle_noncanonical_leaf_rejected_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second TOML file cannot impersonate lifecycle.toml in one algorithm."""
    canonical = _fixture_repository(
        tmp_path, monkeypatch, _base(validator.EXPERIMENTAL)
    )
    foreign = canonical.with_name("other.toml")
    _ = foreign.write_text(canonical.read_text())

    def unexpected_read(_path: Path) -> str:
        raise AssertionError("noncanonical lifecycle file read before admission")

    monkeypatch.setattr(validator, "_read_utf8", unexpected_read)
    with pytest.raises(
        validator.AlgorithmLifecycleError, match="canonical lifecycle.toml"
    ):
        _ = validator.validate_repository_lifecycle(foreign)


def test_lifecycle_parent_link_is_rejected_during_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A linked algorithm directory cannot supply a lifecycle identity."""
    manifest = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    original = manifest.parent
    outside = tmp_path / "outside-algorithm"
    _ = original.rename(outside)
    original.symlink_to(outside, target_is_directory=True)

    def unexpected_read(_path: Path) -> str:
        raise AssertionError("linked lifecycle parent read before discovery")

    monkeypatch.setattr(validator, "_read_utf8", unexpected_read)
    with pytest.raises(OSError, match="research directory must not redirect"):
        _ = validator.validate_repository_lifecycle(manifest)


@pytest.mark.parametrize(
    "fault_type",
    [validator.tomllib.TOMLDecodeError, ValueError, TypeError, RuntimeError],
)
def test_lifecycle_parser_does_not_format_foreign_errors(
    monkeypatch: pytest.MonkeyPatch, fault_type: type[Exception]
) -> None:
    """Foreign TOML exceptions cannot execute hooks during typed admission."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("lifecycle decoder exception formatter executed")

    foreign = type("ForeignLifecycleTOMLFault", (fault_type,), {"__str__": unsafe_str})
    fault = (
        foreign("decoder fault", "[invalid", 1)
        if fault_type is validator.tomllib.TOMLDecodeError
        else foreign("decoder fault")
    )

    def fail_parser(_text: str) -> None:
        raise fault

    monkeypatch.setattr(validator.tomllib, "loads", fail_parser)
    with pytest.raises(
        validator.AlgorithmLifecycleError, match="invalid TOML"
    ) as caught:
        validator.parse_lifecycle(_base(validator.EXPERIMENTAL))
    assert caught.value.__cause__ is fault


def test_lifecycle_native_toml_parser_retains_source_diagnostics() -> None:
    """Plain TOML syntax errors keep the native position and cause."""
    with pytest.raises(
        validator.AlgorithmLifecycleError, match="invalid TOML"
    ) as caught:
        validator.parse_lifecycle("[broken\n")
    assert type(caught.value.__cause__) is validator.tomllib.TOMLDecodeError
    assert "line" in str(caught.value)


@pytest.mark.parametrize("position", ["root", "table", "key"])
def test_lifecycle_parser_rejects_foreign_mapping_receipts(
    monkeypatch: pytest.MonkeyPatch, position: str
) -> None:
    """Untrusted mapping or key subclasses cannot execute iteration hooks."""

    class ForeignMap(dict[str, object]):
        def items(self):  # type: ignore[override]
            raise AssertionError("foreign lifecycle map iteration executed")

    class ForeignKey(str):
        __hash__ = str.__hash__

        def __str__(self) -> str:
            raise AssertionError("foreign lifecycle key formatter executed")

    native = validator.tomllib.loads(_base(validator.EXPERIMENTAL))
    if position == "root":
        forged: object = ForeignMap(native)
    elif position == "table":
        forged = {**native, "algorithm": ForeignMap(native["algorithm"])}
    else:
        forged = {**native, ForeignKey("unexpected"): "value"}
    monkeypatch.setattr(validator.tomllib, "loads", lambda _text: forged)
    with pytest.raises(validator.AlgorithmLifecycleError, match="lifecycle"):
        validator.parse_lifecycle(_base(validator.EXPERIMENTAL))


@pytest.mark.parametrize("phase", ["manifest", "evidence"])
@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_lifecycle_host_failures_never_format_foreign_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    fault_type: type[Exception],
) -> None:
    """File and evidence admission preserve causes without foreign __str__."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("lifecycle host exception formatter executed")

    foreign = type("ForeignLifecycleHostFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe filesystem diagnostic")
    if phase == "manifest":
        path = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
        original_lstat = Path.lstat

        def fail_lstat(candidate: Path) -> os.stat_result:
            if candidate == path:
                raise fault
            return original_lstat(candidate)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
        with pytest.raises(
            validator.AlgorithmLifecycleError, match="manifest cannot be read"
        ) as caught:
            validator.validate_repository_lifecycle(path)
    else:
        root = tmp_path / "root"
        root.mkdir()
        monkeypatch.setattr(validator, "ROOT", root)

        def fail_evidence(_parts: tuple[str, ...]) -> None:
            raise fault

        monkeypatch.setattr(validator, "_evidence_descriptor_walk", fail_evidence)
        with pytest.raises(
            validator.AlgorithmLifecycleError, match="evidence not admitted"
        ) as caught:
            validator._require_existing(  # pyright: ignore[reportPrivateUsage]
                "docs/proof.md", "research record"
            )
    assert caught.value.__cause__ is fault


def test_lifecycle_utf8_error_preserves_decoder_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An invalid lifecycle encoding retains the native decoding exception."""
    source = _fixture_repository(tmp_path, monkeypatch, _base(validator.EXPERIMENTAL))
    _ = source.write_bytes(b"\xff")
    with pytest.raises(
        validator.AlgorithmLifecycleError, match="invalid algorithm lifecycle UTF-8"
    ) as caught:
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]
    assert type(caught.value.__cause__) is UnicodeDecodeError
    assert "position 0" in str(caught.value)


def test_lifecycle_rejects_foreign_byte_receipt_before_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An untrusted reader cannot dispatch a custom bytes decoder."""

    class ForeignBytes(bytes):
        def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
            del encoding, errors
            raise AssertionError("foreign lifecycle byte decoder executed")

    monkeypatch.setattr(
        validator, "_read_lifecycle_file", lambda _path: ForeignBytes(b"valid")
    )
    with pytest.raises(validator.AlgorithmLifecycleError, match="native byte receipt"):
        _ = validator._read_utf8(  # pyright: ignore[reportPrivateUsage]
            Path("untrusted/lifecycle.toml")
        )


@pytest.mark.parametrize("fault_type", [OSError, validator.AlgorithmLifecycleError])
def test_lifecycle_cli_never_formats_foreign_exceptions(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """A hostile exception formatter cannot escape lifecycle CLI handling."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign lifecycle CLI formatter executed")

    foreign = type("ForeignLifecycleCliError", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("untrusted host detail")

    def fail_validate() -> None:
        raise fault

    monkeypatch.setattr(validator, "validate_repository", fail_validate)
    assert validator.main() == 1
    report = capsys.readouterr()
    assert "ForeignLifecycleCliError" in report.err
    assert not report.out


@pytest.mark.parametrize("phase", ["admitted", "opened", "after", "visible"])
def test_lifecycle_forged_manifest_stat_receipt_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Path and descriptor stat values cannot invoke foreign field hooks."""
    path = tmp_path / "lifecycle.toml"
    _ = path.write_text(_base(validator.EXPERIMENTAL))

    class ForeignStat:
        @override
        def __getattribute__(self, name: str) -> object:
            del self, name
            raise AssertionError("foreign stat field hook executed")

    native_lstat = Path.lstat
    native_fstat = os.fstat
    lstat_calls = 0
    fstat_calls = 0

    def forged_lstat(target: Path) -> os.stat_result:
        nonlocal lstat_calls
        if target == path:
            lstat_calls += 1
            if (phase == "admitted" and lstat_calls == 1) or (
                phase == "visible" and lstat_calls == 2
            ):
                return cast("os.stat_result", cast("object", ForeignStat()))
        return native_lstat(target)

    def forged_fstat(fd: int) -> os.stat_result:
        nonlocal fstat_calls
        fstat_calls += 1
        if (phase == "opened" and fstat_calls == 1) or (
            phase == "after" and fstat_calls == 2
        ):
            return cast("os.stat_result", cast("object", ForeignStat()))
        return native_fstat(fd)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    monkeypatch.setattr(os, "fstat", forged_fstat)
    with pytest.raises(validator.AlgorithmLifecycleError, match="native stat"):
        _ = validator._read_utf8(path)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("descriptor", [True, False, -1, 3.0])
def test_lifecycle_forged_manifest_open_descriptor_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, descriptor: object
) -> None:
    """A failed native-fd admission must never close an unowned descriptor."""
    path = tmp_path / "lifecycle.toml"
    _ = path.write_text(_base(validator.EXPERIMENTAL))
    native_open = os.open

    def forged_open(target: Path, flags: int) -> int:
        if target == path:
            return cast("int", descriptor)
        return native_open(target, flags)

    monkeypatch.setattr(os, "open", forged_open)
    with pytest.raises(validator.AlgorithmLifecycleError, match="native descriptor"):
        _ = validator._read_utf8(path)  # pyright: ignore[reportPrivateUsage]


class _LifecycleReadStream:
    """Own a real source fd and forge a single stream return value."""

    def __init__(self, wrapped: BinaryIO, payload: object, fd: object = None) -> None:
        self.wrapped: BinaryIO = wrapped
        self.payload: object = payload
        self.fd: object = fd

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        del args
        self.wrapped.close()

    def fileno(self) -> int:
        return cast("int", self.fd if self.fd is not None else self.wrapped.fileno())

    def read(self, size: int) -> bytes:
        del size
        return cast("bytes", self.payload)


@pytest.mark.parametrize("kind", ["text", "list", "subclass"])
def test_lifecycle_forged_manifest_read_receipt_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Source bytes must be exact native bytes before any length inspection."""
    path = tmp_path / "lifecycle.toml"
    source = _base(validator.EXPERIMENTAL).encode()
    _ = path.write_bytes(source)
    native_fdopen = os.fdopen

    class ForeignBytes(bytes):
        @override
        def __len__(self) -> int:
            raise AssertionError("foreign byte length hook executed")

    payloads: dict[str, object] = {
        "text": source.decode(),
        "list": list(source),
        "subclass": ForeignBytes(source),
    }

    def forged_fdopen(descriptor: int, mode: str) -> BinaryIO:
        wrapped = cast("BinaryIO", native_fdopen(descriptor, mode))
        return cast(
            "BinaryIO", cast("object", _LifecycleReadStream(wrapped, payloads[kind]))
        )

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    with pytest.raises(validator.AlgorithmLifecycleError, match="native byte"):
        _ = validator._read_utf8(path)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("descriptor", [True, -1, 3.0])
def test_lifecycle_forged_manifest_stream_descriptor_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, descriptor: object
) -> None:
    """A forged stream fileno cannot serve as native descriptor evidence."""
    path = tmp_path / "lifecycle.toml"
    source = _base(validator.EXPERIMENTAL).encode()
    _ = path.write_bytes(source)
    native_fdopen = os.fdopen

    def forged_fdopen(fd: int, mode: str) -> BinaryIO:
        wrapped = cast("BinaryIO", native_fdopen(fd, mode))
        return cast(
            "BinaryIO",
            cast("object", _LifecycleReadStream(wrapped, source, descriptor)),
        )

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    with pytest.raises(validator.AlgorithmLifecycleError, match="native descriptor"):
        _ = validator._read_utf8(path)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("phase", ["root", "directory", "leaf"])
@pytest.mark.parametrize("descriptor", [True, -1])
def test_lifecycle_forged_evidence_open_descriptor_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, descriptor: object
) -> None:
    """Directory-relative evidence walks never accept or close fake fds."""
    root = tmp_path / "repo"
    proof = root / "docs" / "proof.md"
    proof.parent.mkdir(parents=True)
    _ = proof.write_text("evidence")
    monkeypatch.setattr(validator, "ROOT", root)
    native_open = os.open

    def forged_open(
        path: str | os.PathLike[str], flags: int, *, dir_fd: int | None = None
    ) -> int:
        if (
            (phase == "root" and path == root)
            or (phase == "directory" and path == "docs")
            or (phase == "leaf" and path == "proof.md")
        ):
            return cast("int", descriptor)
        return native_open(path, flags, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", forged_open)
    with pytest.raises(validator.AlgorithmLifecycleError, match="native descriptor"):
        validator._evidence_descriptor_walk(  # pyright: ignore[reportPrivateUsage]
            ("docs", "proof.md")
        )


@pytest.mark.parametrize("phase", ["opened", "visible"])
def test_lifecycle_forged_evidence_stat_receipt_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Descriptor and path evidence identities require native status results."""
    root = tmp_path / "repo"
    proof = root / "docs" / "proof.md"
    proof.parent.mkdir(parents=True)
    _ = proof.write_text("evidence")
    monkeypatch.setattr(validator, "ROOT", root)
    native_fstat = os.fstat
    native_stat = os.stat

    def forged_fstat(fd: int) -> os.stat_result:
        if phase == "opened":
            return cast("os.stat_result", object())
        return native_fstat(fd)

    def forged_stat(
        path: str | os.PathLike[str],
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        if phase == "visible" and path == "proof.md":
            return cast("os.stat_result", object())
        return native_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "fstat", forged_fstat)
    monkeypatch.setattr(os, "stat", forged_stat)
    with pytest.raises(validator.AlgorithmLifecycleError, match="native stat"):
        validator._require_existing(  # pyright: ignore[reportPrivateUsage]
            "docs/proof.md", "research record"
        )


@pytest.mark.parametrize("phase", ["status", "symlink", "junction"])
def test_lifecycle_forged_evidence_fallback_receipt_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Portable fallback file checks reject forged stat and redirect values."""
    root = tmp_path / "repo"
    proof = root / "docs" / "proof.md"
    proof.parent.mkdir(parents=True)
    _ = proof.write_text("evidence")
    monkeypatch.setattr(validator, "ROOT", root)
    native_lstat = Path.lstat
    native_symlink = Path.is_symlink
    native_junction = Path.is_junction

    def forged_lstat(path: Path) -> os.stat_result:
        if phase == "status" and path == proof:
            return cast("os.stat_result", object())
        return native_lstat(path)

    def forged_symlink(path: Path) -> bool:
        if phase == "symlink" and path == proof:
            return cast("bool", object())
        return native_symlink(path)

    def forged_junction(path: Path) -> bool:
        if phase == "junction" and path == proof:
            return cast("bool", object())
        return native_junction(path)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    monkeypatch.setattr(Path, "is_symlink", forged_symlink)
    monkeypatch.setattr(Path, "is_junction", forged_junction)
    with pytest.raises(validator.AlgorithmLifecycleError, match="native"):
        validator._evidence_fallback(  # pyright: ignore[reportPrivateUsage]
            ("docs", "proof.md")
        )
