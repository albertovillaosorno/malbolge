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
#   - Live host-C reference pilot and retained-evidence integration checks.
# - Must-Not:
#   - Claim that real host-C timing measures Malbolge candidate performance.
# - Allows:
#   - Inputs: bounded generated C challenge families and injected run failures.
#   - Outputs: paired cross-difficulty raw/manifests and accepted-stage checks.
#   - Side effects: session-local ignored native executable and CSV samples.
# - Split-When:
#   - Product compiler measurements require separately trusted verifier tests.
# - Merge-When:
#   - Research reference measurement tests become a governed runner suite.
# - Summary:
#   - Tests real measured host stages and fail-closed retained trial outcomes.
# - Description:
#   - Uses pinned Clang and the original canonical challenge oracle.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_reference_study.py`.
# - Defaults:
#   - A source-reported host result is never Malbolge compiler evidence.
#

"""Bounded real host-C pilot studies, not Malbolge candidate measurements."""

# ruff: file-ignore[assert]

from __future__ import annotations

import json
import shutil
import sys
from hashlib import sha256
from typing import TYPE_CHECKING, Any, cast

import pytest

from benchmarks.arena import (
    analyze,
    evidence,
    host_c_oracle,
    reference_study,
    report_output,
)

if TYPE_CHECKING:
    from pathlib import Path

    from benchmarks.challenges import generate

REPETITIONS = 2
CAPACITY_POINTS = 4
OPTIMIZED_MODE = "-O2"
FAILED = "tool_failed"
ARTIFACT_METRIC = "artifact_bytes"
EXPECTED_ROWS = 8
FAMILY = "arithmetic-dag"
OUTPUT_FAULT = "injected short stdout write"


class _UnexpectedHostFault(IndexError):
    """Unexpected dependency errors cannot control study diagnostics."""

    def __str__(self) -> str:
        raise AssertionError("foreign dependency exception was formatted")


class _HostilePlatformName(str):
    def __format__(self, format_spec: str) -> str:
        del format_spec
        raise AssertionError("foreign host identity formatter executed")


@pytest.mark.parametrize("field", ["system", "machine", "node"])
@pytest.mark.parametrize(
    "invalid",
    [
        None,
        0,
        b"bad",
        "",
        " ",
        "host\nspoof",
        "a" * 257,
        _HostilePlatformName("bad"),
    ],
)
def test_reference_host_identity_rejects_invalid_platform_receipt_before_measurement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: str,
    invalid: object,
) -> None:
    """Untrusted machine identity cannot enter a retained study record."""
    root = tmp_path / "study"
    root.mkdir()

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("invalid platform identity reached host-C measurement")

    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(reference_study, "_write_case", forbidden)
    monkeypatch.setattr(reference_study.platform, field, lambda: invalid)
    with pytest.raises(reference_study.ReferenceStudyError, match="host identity"):
        reference_study._run_study(  # ruff: ignore[private-member-access]
            root, reference_study.StudyPlan(FAMILY, (4,), 7, 1), commit="a" * 40
        )


def test_reference_host_identity_preserves_valid_native_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ordinary platform identity retains all three host provenance fields."""
    monkeypatch.setattr(reference_study.platform, "system", lambda: "Linux")
    monkeypatch.setattr(reference_study.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(reference_study.platform, "node", lambda: "build-host")
    observed = reference_study._host_identity()  # ruff: ignore[private-member-access]
    assert observed == "Linux-x86_64-build-host"


@pytest.mark.parametrize("field", ["system", "machine", "node"])
def test_reference_host_identity_types_unexpected_platform_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: str,
) -> None:
    """Foreign host probes remain typed without invoking their formatter."""
    fault = _UnexpectedHostFault("foreign platform failure")
    root = tmp_path / "study"
    root.mkdir()

    def fail_probe() -> None:
        raise fault

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("failed platform probe reached measurement")

    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(reference_study, "_write_case", forbidden)
    monkeypatch.setattr(reference_study.platform, field, fail_probe)
    with pytest.raises(reference_study.ReferenceStudyError, match="host identity") as caught:
        reference_study._run_study(  # ruff: ignore[private-member-access]
            root, reference_study.StudyPlan(FAMILY, (4,), 7, 1), commit="a" * 40
        )
    assert caught.value.__cause__ is fault


def _pilot() -> tuple[Path, dict[str, Any]]:
    path, document = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4, 8), 7, REPETITIONS),
    )
    return path, document


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),  # ruff: ignore[private-member-access]
    reason="repository pinned native Clang is unavailable",
)
def test_real_host_c_reference_pilot_links_all_trial_evidence() -> None:
    """Two real difficulty levels retain paired observed stage evidence."""
    path, document = _pilot()
    try:
        rows = document["observations"]
        assert len(rows) == EXPECTED_ROWS
        assert {row["case"]["difficulty"] for row in rows} == {4, 8}
        assert all(row["outcome"] == analyze.VERIFIED for row in rows)
        assert all(row["metrics"]["elapsed_ns"] > 0 for row in rows)
        assert all(row["metrics"]["peak_rss_bytes"] > 0 for row in rows)
        assert document["study"]["objectives"] == [
            "elapsed_ns",
            "artifact_bytes",
            "peak_rss_bytes",
        ]
        report = analyze.analyze(analyze.parse_document(json.dumps(document)))
        assert len(report["capacity_curve"]) == CAPACITY_POINTS
        linked = evidence.validate_links(
            analyze.parse_document(json.dumps(document)),
            reference_study._ROOT,  # ruff: ignore[private-member-access]
            policy=evidence.EvidencePolicy(
                require_trial_run_identity=True,
                require_budget_agreement=True,
                challenge_root=f"{path.relative_to(reference_study._ROOT)}/bundles",  # ruff: ignore[private-member-access]
                require_host_c_challenge_oracle=True,
            ),
        )
        assert linked["raw_rows_matched"] == EXPECTED_ROWS
        assert linked["trial_run_links_checked"] == EXPECTED_ROWS
        assert linked["regenerated_challenge_bundles"] == REPETITIONS
        assert linked["host_c_challenge_oracles_replayed"] == REPETITIONS
        artifacts = json.loads((path / "artifacts.json").read_text())
        assert len(artifacts) == EXPECTED_ROWS
        for artifact in artifacts.values():
            executable = reference_study._ROOT / artifact["path"]  # ruff: ignore[private-member-access]
            assert (
                sha256(executable.read_bytes()).hexdigest()
                == artifact["sha256"]
            )
    finally:
        shutil.rmtree(path)


@pytest.mark.parametrize(
    "sidecar",
    ["failures.json", "resource-controls.json", "artifacts.json", "study.json"],
)
@pytest.mark.parametrize("bad_count", [None, True, -1, 1, 1_000_000])
def test_reference_retained_sidecars_reject_incomplete_write_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    sidecar: str,
    bad_count: object,
) -> None:
    """A short or foreign host write cannot publish a successful study."""
    root = tmp_path / "study"
    root.mkdir()
    original_write = type(root).write_text

    def faulty_write(
        path: Path,
        content: str,
        encoding: str | None = None,
    ) -> int:
        if path.name == sidecar:
            _ = original_write(path, content[:1], encoding=encoding)
            return cast("int", bad_count)
        return original_write(path, content, encoding=encoding)

    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(type(root), "write_text", faulty_write)
    monkeypatch.setattr(reference_study, "_write_case", lambda *_: ([], {}))
    monkeypatch.setattr(reference_study, "_verify_report", lambda *_: None)
    monkeypatch.setattr(
        reference_study, "check_retained_artifacts", lambda *_: 0
    )
    monkeypatch.setattr(
        reference_study, "check_retained_failures", lambda *_: 0
    )
    with pytest.raises(
        reference_study.ReferenceStudyError, match="write count"
    ):
        _ = reference_study._run_study(  # ruff: ignore[private-member-access]
            root,
            reference_study.StudyPlan(FAMILY, (4,), 7, 1),
            commit="0" * 40,
        )


class _HostileHostWriteArgument:
    def __str__(self) -> str:
        raise AssertionError("foreign native-error argument was formatted")


@pytest.mark.parametrize("kind", ["binary", "text"])
@pytest.mark.parametrize(
    "fault",
    [
        OSError("native host write denied"),
        OSError(_HostileHostWriteArgument()),
        _UnexpectedHostFault("foreign host write"),
    ],
    ids=["native-os", "hostile-os-argument", "unexpected-foreign"],
)
def test_retained_host_c_writer_errors_are_typed_and_preserve_causes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    fault: Exception,
) -> None:
    """Writer faults cannot leave direct callers with untyped foreign errors."""
    path = tmp_path / "retained"

    def fail_write(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    if kind == "binary":
        monkeypatch.setattr(reference_study.Path, "write_bytes", fail_write)
    else:
        monkeypatch.setattr(reference_study.Path, "write_text", fail_write)
    with pytest.raises(reference_study.ReferenceStudyError, match="write failed") as caught:
        if kind == "binary":
            reference_study._write_retained_bytes(  # ruff: ignore[private-member-access]
                path, b"binary evidence"
            )
        else:
            reference_study._write_retained_text(  # ruff: ignore[private-member-access]
                path, "text evidence"
            )
    assert caught.value.__cause__ is fault
    if type(fault) is OSError and type(fault.args[0]) is str:
        assert "native host write denied" in str(caught.value)
    else:
        assert str(caught.value) == "host-C retained retained write failed"


def test_retained_host_c_writer_bounds_native_diagnostic_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Native error detail remains printable and bounded on a failed write."""
    path = tmp_path / "retained"
    fault = OSError("disk\n" + "x" * 1000)

    def fail_write(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(reference_study.Path, "write_bytes", fail_write)
    with pytest.raises(reference_study.ReferenceStudyError) as caught:
        reference_study._write_retained_bytes(  # ruff: ignore[private-member-access]
            path, b"bounded evidence"
        )
    message = str(caught.value)
    assert caught.value.__cause__ is fault
    assert message.startswith("host-C retained retained write failed: disk?xxx")
    assert "\n" not in message
    assert len(message) <= len("host-C retained retained write failed: ") + 256


@pytest.mark.parametrize(
    "filename",
    [
        "program.c",
        "oracle.bin",
        "manifest.json",
        "host-clang-O0-nodes-4-trial-0",
        "host-clang-O0-nodes-4-trial-0.csv",
        "host-clang-O0-nodes-4-trial-0.toml",
    ],
)
@pytest.mark.parametrize("bad_count", [None, True, -1, 1, 1_000_000])
def test_reference_evidence_rejects_incomplete_write_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    filename: str,
    bad_count: object,
) -> None:
    """No incomplete retained evidence write may be a verified trial."""
    original_bytes = type(tmp_path).write_bytes
    original_text = type(tmp_path).write_text
    matched = 0

    def faulty_bytes(path: Path, payload: bytes) -> int:
        nonlocal matched
        if path.name == filename:
            matched += 1
            _ = original_bytes(path, payload[:1])
            return cast("int", bad_count)
        return original_bytes(path, payload)

    def faulty_text(
        path: Path,
        payload: str,
        encoding: str | None = None,
    ) -> int:
        nonlocal matched
        if path.name == filename:
            matched += 1
            _ = original_text(path, payload[:1], encoding=encoding)
            return cast("int", bad_count)
        return original_text(path, payload, encoding=encoding)

    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", lambda: None
    )
    monkeypatch.setattr(
        host_c_oracle,
        "measure_reference",
        lambda *_: host_c_oracle.ReferenceMeasurement(
            10, b"fake-executable", 1024
        ),
    )
    monkeypatch.setattr(type(tmp_path), "write_bytes", faulty_bytes)
    monkeypatch.setattr(type(tmp_path), "write_text", faulty_text)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="write count"
    ):
        _ = reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1)
        )
    assert matched == 1


@pytest.mark.parametrize(
    "plan",
    [
        reference_study.StudyPlan(FAMILY, (), 7, 1),
        reference_study.StudyPlan(FAMILY, (4, 4), 7, 1),
        reference_study.StudyPlan(FAMILY, (1, 2, 3, 4, 5), 7, 1),
        reference_study.StudyPlan(FAMILY, (4,), 7, 0),
        reference_study.StudyPlan(FAMILY, (4,), 7, 6),
        reference_study.StudyPlan(FAMILY, (513,), 7, 1),
    ],
)
def test_invalid_study_plan_fails_before_creating_output(
    plan: reference_study.StudyPlan,
) -> None:
    """Rejected setup does not create an empty published study directory."""
    with pytest.raises((reference_study.ReferenceStudyError, ValueError)):
        reference_study.run_study(plan)


@pytest.mark.parametrize(
    "foreign",
    [None, {}, object()],
)
def test_direct_host_reference_rejects_foreign_plan_before_native_probe(
    foreign: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct callers cannot use a foreign plan to reach host tools."""

    def forbidden_probe() -> None:
        pytest.fail("foreign plan reached native resource admission")

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", forbidden_probe
    )
    with pytest.raises(reference_study.ReferenceStudyError, match="exact StudyPlan"):
        reference_study.run_study(cast("reference_study.StudyPlan", foreign))


@pytest.mark.parametrize(
    "foreign",
    [None, 3, [4], ("4",), (True,), ([4],), (object(),)],
)
def test_direct_host_reference_rejects_foreign_difficulties_before_native_probe(
    foreign: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed and unhashable difficulty collections fail as typed errors."""

    def forbidden_probe() -> None:
        pytest.fail("foreign difficulties reached native resource admission")

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", forbidden_probe
    )
    plan = reference_study.StudyPlan(
        FAMILY, cast("tuple[int, ...]", foreign), 7, 1
    )
    with pytest.raises(reference_study.ReferenceStudyError, match="integer tuple"):
        reference_study.run_study(plan)


@pytest.mark.parametrize(
    ("family", "seed", "difficulties"),
    [
        (None, 7, (4,)),
        ("invalid-family", 7, (4,)),
        (FAMILY, -1, (4,)),
        (FAMILY, True, (4,)),
        (FAMILY, 7, (513,)),
    ],
)
def test_invalid_host_reference_identity_rejects_before_native_probe(
    family: object,
    seed: object,
    difficulties: tuple[int, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid generated workloads never trigger host resource discovery."""

    def forbidden_probe() -> None:
        pytest.fail("invalid challenge identity reached native resource admission")

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", forbidden_probe
    )
    plan = reference_study.StudyPlan(
        cast("str", family), difficulties, cast("int", seed), 1
    )
    with pytest.raises(ValueError):
        reference_study.run_study(plan)


@pytest.mark.parametrize("trial_count", [True, 1.5, "2", None])
def test_noninteger_trial_count_rejects_before_native_or_output_setup(
    trial_count: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign trial count must never probe resource tools or create a run."""

    def forbid_resource_probe() -> None:
        pytest.fail("malformed trial count reached native resource admission")

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", forbid_resource_probe
    )
    with pytest.raises(reference_study.ReferenceStudyError, match="trial count"):
        reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, cast("int", trial_count))
        )


@pytest.mark.parametrize(
    "invalid",
    [True, 0, b"/usr/bin/git", "", "git", "../git", "/usr/bin/git\0bad", "\ud800"],
    ids=[
        "boolean",
        "integer",
        "bytes",
        "empty",
        "relative",
        "parent",
        "nul",
        "unicode",
    ],
)
def test_reference_git_resolver_rejects_invalid_executable_before_launch(
    monkeypatch: pytest.MonkeyPatch, invalid: object
) -> None:
    """Host Git identity must use an absolute, exact, encodable path."""

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("invalid Git resolver output launched subprocess")

    monkeypatch.setattr(
        reference_study.shutil, "which", lambda *_args, **_kwargs: invalid
    )
    monkeypatch.setattr(reference_study.sp, "run", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git executable"):
        reference_study._commit()  # ruff: ignore[private-member-access]


@pytest.mark.parametrize("kind", ["symlink", "directory", "non-executable", "missing"])
def test_reference_git_rejects_nonphysical_executable_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Source provenance must not execute a linked or nonregular Git tool."""
    path = tmp_path / "git"
    if kind == "symlink":
        target = tmp_path / "genuine-git"
        _ = target.write_bytes(b"bin")
        target.chmod(0o700)
        path.symlink_to(target)
    elif kind == "directory":
        path.mkdir()
    elif kind == "non-executable":
        _ = path.write_bytes(b"bin")
        path.chmod(0o600)

    def forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        pytest.fail("untrusted physical Git executable reached child launch")

    monkeypatch.setattr(reference_study.shutil, "which", lambda *_args, **_kw: str(path))
    monkeypatch.setattr(reference_study.sp, "run", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git executable") as error:
        reference_study._commit()  # ruff: ignore[private-member-access]
    if kind == "missing":
        assert isinstance(error.value.__cause__, FileNotFoundError)


@pytest.mark.parametrize("access_result", [False, None, True, 1, "yes", object()])
def test_reference_git_requires_native_positive_executable_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, access_result: object
) -> None:
    """Only a literal successful OS executable-access receipt permits Git."""
    path = tmp_path / "git"
    _ = path.write_bytes(b"bin")
    path.chmod(0o700)
    monkeypatch.setattr(reference_study.shutil, "which", lambda *_args, **_kw: str(path))
    monkeypatch.setattr(reference_study.os, "access", lambda *_args: access_result)
    if access_result is True:
        monkeypatch.setattr(
            reference_study.sp,
            "run",
            lambda *_args, **_kw: reference_study.sp.CompletedProcess(
                ["git"], 0, stdout="a" * 40 + "\n"
            ),
        )
        assert reference_study._commit() == "a" * 40  # ruff: ignore[private-member-access]
    else:
        def forbidden(*args: object, **kwargs: object) -> object:
            del args, kwargs
            pytest.fail("invalid Git execute receipt reached child launch")

        monkeypatch.setattr(reference_study.sp, "run", forbidden)
        with pytest.raises(reference_study.ReferenceStudyError, match="Git executable"):
            reference_study._commit()  # ruff: ignore[private-member-access]


@pytest.mark.parametrize(
    "fault_type",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        _UnexpectedHostFault,
    ],
)
@pytest.mark.parametrize("site", ["status", "access"])
def test_reference_git_physical_preflight_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    site: str,
) -> None:
    """Host executable inspection faults preserve the original typed cause."""
    path = tmp_path / "git"
    _ = path.write_bytes(b"bin")
    path.chmod(0o700)
    monkeypatch.setattr(reference_study.shutil, "which", lambda *_args, **_kw: str(path))

    def broken(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise fault_type("injected host Git inspection fault")

    if site == "status":
        original_lstat = type(path).lstat

        def injected_lstat(candidate: Path) -> object:
            if candidate == path:
                return broken()
            return original_lstat(candidate)

        monkeypatch.setattr(type(path), "lstat", injected_lstat)
    else:
        monkeypatch.setattr(reference_study.os, "access", broken)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git executable") as caught:
        reference_study._commit()  # ruff: ignore[private-member-access]
    assert type(caught.value.__cause__) is fault_type


@pytest.mark.parametrize(
    "failure_type",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        _UnexpectedHostFault,
    ],
)
def test_reference_git_resolver_fault_preserves_typed_source_error(
    monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    """Host tool selection faults must not escape source identity admission."""
    message = "injected Git resolver failure"

    def broken(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure_type(message)

    monkeypatch.setattr(reference_study.shutil, "which", broken)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="Git lookup"
    ) as captured:
        reference_study._commit()  # ruff: ignore[private-member-access]
    assert type(captured.value.__cause__) is failure_type


class _HostileGitEnvironmentKey(str):
    def startswith(self, prefix: str | tuple[str, ...], *args: object) -> bool:
        del prefix, args
        raise AssertionError("foreign Git environment key method called")


@pytest.mark.parametrize("scenario", ["read-fault", "foreign-key", "foreign-value"])
def test_reference_git_environment_admission_precedes_child_launch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    scenario: str,
) -> None:
    """Host environment failures and foreign keys fail before Git is invoked."""
    executable = tmp_path / "git"
    executable.write_bytes(b"native executable")
    executable.chmod(0o700)
    fault = _UnexpectedHostFault("environment snapshot failed")

    class ForeignEnvironment(dict[str, str]):
        def items(self) -> Any:
            if scenario == "read-fault":
                raise fault
            if scenario == "foreign-key":
                return [(_HostileGitEnvironmentKey("GIT_DIR"), "redirected")]
            return [("PATH", object())]

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("invalid Git environment reached child launch")

    monkeypatch.setattr(reference_study.shutil, "which", lambda *_a, **_k: str(executable))
    monkeypatch.setattr(reference_study.os, "environ", ForeignEnvironment())
    monkeypatch.setattr(reference_study.sp, "run", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git environment") as caught:
        reference_study._commit()  # ruff: ignore[private-member-access]
    if scenario == "read-fault":
        assert caught.value.__cause__ is fault


def test_reference_git_environment_sanitizer_preserves_native_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Native environment fields survive while Git selectors are removed."""
    executable = tmp_path / "git"
    executable.write_bytes(b"native executable")
    executable.chmod(0o700)

    class NativeEnvironment(dict[str, str]):
        def items(self) -> Any:
            return [("GIT_DIR", "/malicious-redirect"), ("PATH", "/usr/bin")]

    def fake_git(*args: object, **kwargs: object) -> object:
        del args
        assert kwargs["env"] == {"PATH": "/usr/bin"}
        return reference_study.sp.CompletedProcess(
            ["git", "rev-parse", "HEAD"], 0, stdout="a" * 40 + "\n"
        )

    monkeypatch.setattr(reference_study.shutil, "which", lambda *_a, **_k: str(executable))
    monkeypatch.setattr(reference_study.os, "environ", NativeEnvironment())
    monkeypatch.setattr(reference_study.sp, "run", fake_git)
    assert reference_study._commit() == "a" * 40  # ruff: ignore[private-member-access]


@pytest.mark.parametrize("bad_output", [None, True, b"0" * 40, "missing"])
def test_reference_git_rejects_nontext_revision_receipts(
    monkeypatch: pytest.MonkeyPatch, bad_output: object
) -> None:
    """A fake subprocess's malformed receipt cannot authorize producer output."""

    def fake_run(*args: object, **kwargs: object) -> object:
        del args, kwargs
        if bad_output == "missing":
            return object()
        return type("FakeCompleted", (), {"stdout": bad_output})()

    monkeypatch.setattr(reference_study.sp, "run", fake_run)
    with pytest.raises(reference_study.ReferenceStudyError, match="source commit"):
        reference_study._commit()  # ruff: ignore[private-member-access]


@pytest.mark.parametrize("exit_status", [None, False, True, "0", 1, -1, float("nan")])
def test_reference_git_rejects_malformed_or_failed_exit_receipts(
    monkeypatch: pytest.MonkeyPatch, exit_status: object
) -> None:
    """A commit-shaped stdout string never overrides child exit failure."""
    expected = "a" * 40

    def fake_run(*args: object, **kwargs: object) -> object:
        del args, kwargs
        return reference_study.sp.CompletedProcess(
            ["git", "rev-parse", "HEAD"],
            cast("int", exit_status),
            stdout=expected + "\n",
        )

    monkeypatch.setattr(reference_study.sp, "run", fake_run)
    with pytest.raises(reference_study.ReferenceStudyError, match="source commit exit"):
        reference_study._commit()  # ruff: ignore[private-member-access]


def test_reference_git_accepts_exact_zero_exit_and_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid subprocess completion still records the exact source commit."""
    expected = "a" * 40

    def fake_run(*args: object, **kwargs: object) -> object:
        del args
        assert kwargs["check"] is True
        assert kwargs["shell"] is False
        return reference_study.sp.CompletedProcess(
            ["git", "rev-parse", "HEAD"], 0, stdout=expected + "\n"
        )

    monkeypatch.setattr(reference_study.sp, "run", fake_run)
    assert reference_study._commit() == expected  # ruff: ignore[private-member-access]


@pytest.mark.parametrize(
    "failure_type",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        reference_study.sp.SubprocessError,
        _UnexpectedHostFault,
    ],
)
def test_reference_git_process_fault_preserves_typed_source_error(
    monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    """A host runner fault must not escape as an untyped producer failure."""

    def broken(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure_type("injected Git execution failure")

    monkeypatch.setattr(reference_study.sp, "run", broken)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="cannot identify source commit"
    ) as captured:
        reference_study._commit()  # ruff: ignore[private-member-access]
    assert type(captured.value.__cause__) is failure_type


def test_host_reference_source_commit_preflight_does_not_orphan_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unavailable source revision must reject before allocating evidence."""

    def rejected_commit() -> str:
        raise reference_study.ReferenceStudyError("source commit unavailable")

    def forbidden_workspace(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("source identity failure allocated a study directory")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda plan: None)
    monkeypatch.setattr(reference_study, "_commit", rejected_commit)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", forbidden_workspace)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="source commit unavailable"
    ):
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))


def test_host_reference_refuses_redirected_evidence_root_before_allocation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A symlinked .temp cannot redirect retained host-C output outside the tree."""
    outside = tmp_path / "external"
    outside.mkdir()
    link = tmp_path / "redirected-root"
    link.symlink_to(outside, target_is_directory=True)

    def forbidden_workspace(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("redirected root reached workspace allocation")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda plan: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", link)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", forbidden_workspace)
    with pytest.raises(reference_study.ReferenceStudyError, match="physical"):
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("kind", ["missing", "regular-file"])
def test_host_reference_requires_an_existing_directory_for_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kind: str,
) -> None:
    """Absent and non-directory .temp roots fail before any child is created."""
    root = tmp_path / "non-directory"
    if kind == "regular-file":
        root.write_bytes(b"not a directory")

    def forbidden_workspace(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("invalid evidence root reached workspace allocation")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda plan: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", root)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", forbidden_workspace)
    with pytest.raises(reference_study.ReferenceStudyError, match="workspace"):
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))


@pytest.mark.parametrize("error_type", [ValueError, RuntimeError, _UnexpectedHostFault])
def test_host_reference_types_workspace_root_inspection_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_type: type[Exception],
) -> None:
    """A host path-inspection error cannot escape the reference boundary."""

    def broken_lstat(path: Path) -> None:
        _ = path
        message = "injected host path inspection error"
        raise error_type(message)

    def forbidden_allocate(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("failed root inspection allocated an output directory")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda _: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    monkeypatch.setattr(reference_study.Path, "lstat", broken_lstat)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", forbidden_allocate)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="workspace root"
    ) as error:
        _ = reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1)
        )
    assert isinstance(error.value.__cause__, error_type)


@pytest.mark.parametrize(
    "error_type", [OSError, ValueError, RuntimeError, _UnexpectedHostFault]
)
@pytest.mark.parametrize("failed_stage", ["allocate", "raw", "runs", "candidates"])
def test_host_reference_workspace_failures_are_typed_and_cleanup_own_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    failed_stage: str,
    error_type: type[Exception],
) -> None:
    """Failed setup cannot leak host errors or an incomplete local study."""
    directory = tmp_path / "arena-host-c-study-setup"
    original_mkdir = reference_study.Path.mkdir

    def faulty_mkdtemp(*, prefix: str, dir: Path) -> str:
        assert prefix == "arena-host-c-study-"
        assert dir == reference_study._LOCAL  # ruff: ignore[private-member-access]
        if failed_stage == "allocate":
            raise error_type("injected workspace allocation failure")
        original_mkdir(directory)
        return str(directory)

    def faulty_mkdir(
        path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if path.parent == directory and path.name == failed_stage:
            raise error_type("injected workspace child failure")
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    def forbidden_measurement(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("uninitialized workspace started host-C measurements")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda plan: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", faulty_mkdtemp)
    monkeypatch.setattr(reference_study.Path, "mkdir", faulty_mkdir)
    monkeypatch.setattr(reference_study, "_run_study", forbidden_measurement)
    with pytest.raises(reference_study.ReferenceStudyError, match="workspace") as error:
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))
    assert isinstance(error.value.__cause__, error_type)
    assert not directory.exists()


class _UnsafeWorkspaceCleanupError(ValueError):
    def __str__(self) -> str:
        raise AssertionError("workspace cleanup exception must not be formatted")


class _UnsafeWorkspaceCleanupArgument:
    def __str__(self) -> str:
        raise AssertionError("workspace cleanup argument must not be formatted")


@pytest.mark.parametrize(
    "cleanup_error",
    [
        ValueError("injected cleanup error"),
        RuntimeError("injected cleanup error"),
        _UnsafeWorkspaceCleanupError("foreign cleanup"),
        ValueError(_UnsafeWorkspaceCleanupArgument()),
        _UnexpectedHostFault("unanticipated cleanup"),
    ],
    ids=[
        "native-value",
        "native-runtime",
        "foreign-subclass",
        "foreign-argument",
        "unexpected",
    ],
)
def test_host_reference_setup_cleanup_failure_preserves_original_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    cleanup_error: Exception,
) -> None:
    """Unexpected cleanup faults cannot hide the failed workspace setup."""
    directory = tmp_path / "allocated"
    directory.mkdir()

    def fake_mkdtemp(**kwargs: object) -> str:
        _ = kwargs
        return str(directory)

    def broken_mkdir(path: Path) -> None:
        _ = path
        message = "injected primary workspace creation failure"
        raise OSError(message)

    def broken_cleanup(path: Path) -> None:
        _ = path
        raise cleanup_error

    monkeypatch.setattr(reference_study, "_validate_plan", lambda _: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(reference_study.Path, "mkdir", broken_mkdir)
    monkeypatch.setattr(reference_study.shutil, "rmtree", broken_cleanup)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="workspace setup"
    ) as error:
        _ = reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1)
        )
    original = error.value.__cause__
    assert isinstance(original, OSError)
    note = "host-C workspace cleanup also failed"
    if type(cleanup_error) in (ValueError, RuntimeError) and (
        type(cleanup_error.args[0]) is str
    ):
        note += ": injected cleanup error"
    assert original.__notes__ == [note]


class _UnsafeHostOracleError(host_c_oracle.HostOracleError):
    def __str__(self) -> str:
        raise AssertionError("foreign host-C error must not be formatted")


@pytest.mark.parametrize(
    "oracle_failure",
    [
        _UnsafeHostOracleError("foreign host-C failure"),
        host_c_oracle.HostOracleError(_UnsafeWorkspaceCleanupArgument()),
    ],
    ids=["foreign-host-error", "host-error-with-foreign-argument"],
)
def test_host_reference_failed_arm_keeps_tool_failure_on_hostile_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    oracle_failure: host_c_oracle.HostOracleError,
) -> None:
    """Unsafe host error formatting cannot hide a failed compiler stage."""

    def reject_measurement(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise oracle_failure

    monkeypatch.setattr(reference_study, "_successful", reject_measurement)
    case = {"family": FAMILY, "version": 1, "seed": 7, "difficulty": 4}
    row, artifact, diagnostic = reference_study._measure(
        reference_study._ROOT / ".temp" / "host-C-failure-probe",
        case,
        trial=0,
        arm=(reference_study.CANDIDATE, OPTIMIZED_MODE),
    )
    assert row["outcome"] == FAILED
    assert row["verifier_verdict"] == analyze.NOT_RUN
    assert ARTIFACT_METRIC not in row["metrics"]
    assert artifact == {}
    assert diagnostic == "host-C reference failed without diagnostic"


@pytest.mark.parametrize(
    "oracle_failure",
    [
        _UnsafeHostOracleError("foreign host-C failure"),
        host_c_oracle.HostOracleError(_UnsafeWorkspaceCleanupArgument()),
    ],
    ids=["foreign-host-error", "host-error-with-foreign-argument"],
)
def test_host_reference_resource_preflight_types_hostile_oracle_error(
    monkeypatch: pytest.MonkeyPatch,
    oracle_failure: host_c_oracle.HostOracleError,
) -> None:
    """Preflight rejection preserves the cause without unsafe conversion."""

    def reject_resources() -> None:
        raise oracle_failure

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", reject_resources
    )
    with pytest.raises(
        reference_study.ReferenceStudyError, match="child limits"
    ) as error:
        reference_study._validate_plan(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1)
        )
    assert error.value.__cause__ is oracle_failure


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),  # ruff: ignore[private-member-access]
    reason="repository pinned native Clang is unavailable",
)
def test_failed_reference_arm_retains_failure_not_fabricated_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source-reported failed O2 stage remains visible to a paired study."""
    original = host_c_oracle.measure_reference

    def reject_o2(
        identity: generate.ChallengeIdentity, mode: str
    ) -> host_c_oracle.ReferenceMeasurement:
        if mode == OPTIMIZED_MODE:
            message = "injected compiler failure"
            raise host_c_oracle.HostOracleError(message)
        return original(identity, mode)

    monkeypatch.setattr(host_c_oracle, "measure_reference", reject_o2)
    path, document = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4,), 7, 1),
    )
    try:
        rows = document["observations"]
        failed = next(
            row for row in rows if row["algorithm"] == reference_study.CANDIDATE
        )
        assert failed["outcome"] == FAILED
        assert failed["verifier_verdict"] == analyze.NOT_RUN
        assert ARTIFACT_METRIC not in failed["metrics"]
        result = analyze.analyze(analyze.parse_document(json.dumps(document)))
        assert result["capacity_curve"][1]["verified"] == 0
    finally:
        shutil.rmtree(path)


TAMPER_BYTES = "bytes"
TAMPER_SIZE = "size"
TAMPER_PATH = "path"
TAMPER_MISSING = "missing"
TAMPER_EXTRA = "extra"
TAMPER_SYMLINK = "symlink"


def _tamper_size(document: dict[str, Any], manifest: str) -> None:
    for row in document["observations"]:
        if row["experiment_manifest"] == manifest:
            row["metrics"][ARTIFACT_METRIC] += 1


def _tamper_record(
    tamper: str,
    document: dict[str, Any],
    reference: dict[str, str],
    *,
    manifest: str,
) -> None:
    executable = reference_study._ROOT / reference["path"]  # ruff: ignore[private-member-access]
    if tamper == TAMPER_BYTES:
        original = executable.read_bytes()
        _ = executable.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    elif tamper == TAMPER_SIZE:
        _tamper_size(document, manifest)
    elif tamper == TAMPER_PATH:
        reference["path"] = ".temp/unrelated-executable"
    elif tamper == TAMPER_SYMLINK:
        other = executable.parent / "alternate-file"
        _ = other.write_bytes(executable.read_bytes())
        executable.unlink()
        executable.symlink_to(other)


def _tamper(
    tamper: str,
    document: dict[str, Any],
    artifacts: dict[str, dict[str, str]],
) -> None:
    name = next(iter(artifacts))
    if tamper == TAMPER_MISSING:
        _ = artifacts.pop(name)
    elif tamper == TAMPER_EXTRA:
        artifacts["extra-trial"] = artifacts[name].copy()
    else:
        _tamper_record(tamper, document, artifacts[name], manifest=name)


@pytest.mark.parametrize("check", ["artifacts", "failures"])
@pytest.mark.parametrize(
    "document",
    [
        None,
        {},
        {"observations": [None]},
        {"observations": [{"outcome": "unexpected", "experiment_manifest": "runs/a.toml"}]},
        {"observations": [{"outcome": "verified", "experiment_manifest": object()}]},
    ],
    ids=[
        "missing-document",
        "missing-observations",
        "foreign-row",
        "unsupported-outcome",
        "foreign-manifest",
    ],
)
def test_direct_retained_checks_reject_unadmitted_trial_rows(
    check: str,
    document: object,
) -> None:
    """Direct checks must reject malformed trial maps as typed failures."""
    checker = (
        reference_study.check_retained_artifacts
        if check == "artifacts"
        else reference_study.check_retained_failures
    )
    with pytest.raises(reference_study.ReferenceStudyError):
        _ = checker(cast("dict[str, Any]", document), {})


class _ForgedTrialKey(str):  # ruff: ignore[subclass-builtin]
    """Foreign dictionary keys can run attacker-defined equality methods."""

    def __eq__(self, other: object) -> bool:
        del other
        message = "retained trial key equality hook executed"
        raise AssertionError(message)

    __hash__ = str.__hash__


@pytest.mark.parametrize("check", ["artifacts", "failures"])
def test_direct_retained_checks_reject_foreign_observation_keys(
    check: str,
) -> None:
    """Reject foreign keys before accessing the observations dictionary."""
    document: dict[str, Any] = {
        _ForgedTrialKey("observations"): [],
    }
    checker = (
        reference_study.check_retained_artifacts
        if check == "artifacts"
        else reference_study.check_retained_failures
    )
    with pytest.raises(reference_study.ReferenceStudyError):
        _ = checker(document, {})


@pytest.mark.parametrize("check", ["artifacts", "failures"])
def test_direct_retained_checks_reject_foreign_sidecar_container(check: str) -> None:
    """An empty list cannot substitute for an empty retained metadata map."""
    checker = (
        reference_study.check_retained_artifacts
        if check == "artifacts"
        else reference_study.check_retained_failures
    )
    with pytest.raises(reference_study.ReferenceStudyError):
        _ = checker({"observations": []}, cast("Any", []))


@pytest.mark.parametrize("check", ["artifacts", "failures"])
def test_direct_retained_checks_reject_sidecar_foreign_keys(check: str) -> None:
    """Retained sidecars must not execute caller-defined key equality."""
    manifest = "runs/forged.toml"
    outcome = analyze.VERIFIED if check == "artifacts" else FAILED
    document = {"observations": [
        {"outcome": outcome, "experiment_manifest": manifest},
    ]}
    payload: object = {"path": "unused", "sha256": "unused"}
    if check == "failures":
        payload = "compiler rejected"
    sidecar = {_ForgedTrialKey(manifest): payload}
    checker = (
        reference_study.check_retained_artifacts
        if check == "artifacts"
        else reference_study.check_retained_failures
    )
    with pytest.raises(reference_study.ReferenceStudyError):
        _ = checker(document, cast("Any", sidecar))


def test_direct_retained_artifacts_reject_non_mapping_artifact_entry() -> None:
    """An artifact leaf must be a native metadata map before I/O."""
    manifest = "runs/missing-metadata.toml"
    document = {"observations": [{
        "outcome": analyze.VERIFIED,
        "experiment_manifest": manifest,
    }]}
    with pytest.raises(reference_study.ReferenceStudyError):
        _ = reference_study.check_retained_artifacts(
            document, cast("Any", {manifest: []})
        )


@pytest.mark.parametrize(
    "metrics",
    [None, {}, {"artifact_bytes": True}, {"artifact_bytes": "1"}],
    ids=["missing", "no-size", "boolean-size", "text-size"],
)
def test_direct_retained_artifacts_preflight_verified_metrics_before_io(
    monkeypatch: pytest.MonkeyPatch,
    metrics: object,
) -> None:
    """Unadmitted metrics cannot trigger retained artifact filesystem access."""
    manifest = ".temp/arena-host-c-study-check/runs/one.toml"
    row: dict[str, Any] = {
        "experiment_manifest": manifest,
        "outcome": analyze.VERIFIED,
        "metrics": metrics,
    }

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("unadmitted metrics reached artifact byte inspection")

    monkeypatch.setattr(reference_study, "_checked_artifact", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="metrics"):
        _ = reference_study.check_retained_artifacts(
            {"observations": [row]},
            {manifest: {"path": "unused", "sha256": "unused"}},
        )


def test_retained_artifact_check_rejects_duplicate_verified_manifests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A direct map check cannot collapse two successes into one file claim."""
    manifest = "runs/duplicate.toml"
    row = {"experiment_manifest": manifest, "outcome": analyze.VERIFIED}

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("duplicate manifest reached artifact filesystem verification")

    monkeypatch.setattr(reference_study, "_checked_artifact", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="duplicate"):
        reference_study.check_retained_artifacts(
            {"observations": [row, row.copy()]},
            {manifest: {"path": "not-checked", "sha256": "not-checked"}},
        )


def test_retained_failures_reject_duplicate_failure_manifests() -> None:
    """One diagnostic entry cannot stand in for two reported failed trials."""
    manifest = "runs/duplicate.toml"
    row = {"experiment_manifest": manifest, "outcome": FAILED}
    with pytest.raises(reference_study.ReferenceStudyError, match="duplicate"):
        reference_study.check_retained_failures(
            {"observations": [row, row.copy()]},
            {manifest: "compiler exited without output"},
        )


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),  # ruff: ignore[private-member-access]
    reason="repository pinned native Clang is unavailable",
)
@pytest.mark.parametrize(
    "tamper",
    [
        TAMPER_BYTES,
        TAMPER_SIZE,
        TAMPER_PATH,
        TAMPER_MISSING,
        TAMPER_EXTRA,
        TAMPER_SYMLINK,
    ],
)
def test_reference_artifact_audit_rejects_retained_drift(tamper: str) -> None:
    """Source-reported native hashes and sizes reject mutated binaries."""
    path, document = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4,), 7, 1),
    )
    try:
        artifacts = json.loads((path / "artifacts.json").read_text())
        assert (
            reference_study.check_retained_artifacts(document, artifacts)
            == REPETITIONS
        )
        _tamper(tamper, document, artifacts)
        with pytest.raises(reference_study.ReferenceStudyError, match="host-C"):
            reference_study.check_retained_artifacts(document, artifacts)
    finally:
        shutil.rmtree(path)


class _UnsafeArtifactEvidenceError(evidence.EvidenceError):
    def __str__(self) -> str:
        raise AssertionError("artifact error formatting is untrusted")


@pytest.mark.parametrize(
    "failure",
    [
        _UnsafeArtifactEvidenceError("foreign evidence"),
        OSError(_UnsafeWorkspaceCleanupArgument()),
        evidence.EvidenceError("native evidence read failure"),
    ],
    ids=[
        "foreign-evidence-error",
        "native-os-error-with-foreign-argument",
        "native-evidence-message",
    ],
)
def test_direct_artifact_failure_never_formats_foreign_exception(
    monkeypatch: pytest.MonkeyPatch,
    failure: evidence.EvidenceError | OSError,
) -> None:
    """An evidence read error remains a typed artifact rejection."""

    def reject_read(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure

    monkeypatch.setattr(evidence, "read_bounded_regular", reject_read)
    row = {
        "experiment_manifest": ".temp/probe/runs/candidate.toml",
        "metrics": {"artifact_bytes": 1},
    }
    entry = {
        "path": ".temp/probe/candidates/candidate",
        "sha256": "a" * analyze.SHA256_HEX_LENGTH,
    }
    with pytest.raises(
        reference_study.ReferenceStudyError, match="cannot be admitted"
    ) as caught:
        reference_study._checked_artifact(row, entry)
    assert caught.value.__cause__ is failure
    if type(failure) is evidence.EvidenceError:
        assert str(caught.value).endswith(": native evidence read failure")


@pytest.mark.parametrize(
    "fault_type", [ValueError, RuntimeError, TypeError, _UnexpectedHostFault]
)
def test_retained_artifact_types_unexpected_reader_dependency_faults(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Unexpected reader faults remain typed without foreign formatting."""
    fault = fault_type("unanticipated retained artifact read failure")

    def fail_read(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(evidence, "read_bounded_regular", fail_read)
    row = {
        "experiment_manifest": ".temp/probe/runs/candidate.toml",
        "metrics": {"artifact_bytes": 1},
    }
    entry = {
        "path": ".temp/probe/candidates/candidate",
        "sha256": "a" * analyze.SHA256_HEX_LENGTH,
    }
    with pytest.raises(
        reference_study.ReferenceStudyError, match="cannot be admitted"
    ) as caught:
        reference_study._checked_artifact(row, entry)
    assert caught.value.__cause__ is fault


class _UnsafeCliStudyError(reference_study.ReferenceStudyError):
    def __str__(self) -> str:
        raise AssertionError("CLI study exception formatting is untrusted")


class _UnsafeCliReportError(report_output.ReportOutputError):
    def __str__(self) -> str:
        raise AssertionError("CLI report exception formatting is untrusted")


@pytest.mark.parametrize(
    ("stage", "failure"),
    [
        ("study", _UnsafeCliStudyError("foreign study")),
        (
            "study",
            reference_study.ReferenceStudyError(_UnsafeWorkspaceCleanupArgument()),
        ),
        ("study", reference_study.ReferenceStudyError("native study failure")),
        ("publish", _UnsafeCliReportError("foreign report")),
        (
            "publish",
            report_output.ReportOutputError(_UnsafeWorkspaceCleanupArgument()),
        ),
    ],
    ids=[
        "foreign-study",
        "native-study-argument",
        "native-study-message",
        "foreign-publish",
        "native-publish-argument",
    ],
)
def test_reference_cli_never_formats_foreign_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stage: str,
    failure: Exception,
) -> None:
    """Both CLI error boundaries exit 2 without running untrusted hooks."""

    def reject(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure

    monkeypatch.setattr(sys, "argv", ["reference-study", FAMILY])
    if stage == "study":
        monkeypatch.setattr(reference_study, "run_study", reject)
    else:
        monkeypatch.setattr(reference_study, "run_study", _fake_study_for_stdout)
        monkeypatch.setattr(report_output, "publish", reject)
    with pytest.raises(SystemExit) as caught:
        reference_study.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "host-C reference study:" in output.err
    if type(failure) is reference_study.ReferenceStudyError and (
        type(failure.args[0]) is str
    ):
        assert "native study failure" in output.err


class _UnexpectedCliDependencyFault(Exception):
    def __str__(self) -> str:
        raise AssertionError("unexpected dependency fault cannot be formatted")


@pytest.mark.parametrize("stage", ["study", "publish"])
@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("unexpected runtime dependency"),
        TypeError("unexpected type dependency"),
        _UnexpectedCliDependencyFault("opaque dependency fault"),
    ],
    ids=["runtime", "type", "foreign-format-hook"],
)
def test_reference_cli_unexpected_dependency_fault_is_status_two_without_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stage: str,
    failure: Exception,
) -> None:
    """Unknown ordinary dependency errors must not escape the operator gate."""

    def reject(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure

    monkeypatch.setattr(sys, "argv", ["reference-study", FAMILY])
    if stage == "study":
        monkeypatch.setattr(reference_study, "run_study", reject)
    else:
        monkeypatch.setattr(reference_study, "run_study", _fake_study_for_stdout)
        monkeypatch.setattr(report_output, "publish", reject)
    with pytest.raises(SystemExit) as caught:
        reference_study.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert output.err == "host-C reference study: error details unavailable\n"


def _fake_study_for_stdout(
    plan: reference_study.StudyPlan,
) -> tuple[Path, dict[str, Any]]:
    """Avoid rerunning native Clang for an unrelated stdout framing check.

    Returns:
        A path and documented observation count for the operator summary.

    """
    _ = plan
    return (
        reference_study._ROOT / ".temp" / "host-c-output-probe",  # ruff: ignore[private-member-access]
        {"observations": [{"trial": 0}, {"trial": 1}]},
    )


def test_reference_cli_output_is_checked_and_complete(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A healthy operator stream emits exactly one complete JSON object."""
    monkeypatch.setattr(reference_study, "run_study", _fake_study_for_stdout)
    monkeypatch.setattr(sys, "argv", ["reference-study", FAMILY])
    assert reference_study.main() == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["observations"] == REPETITIONS
    assert observed["study"].endswith("/host-c-output-probe/study.json")


def test_reference_cli_rejects_unflushed_or_truncated_operator_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Publishing failure cannot be reported as a successful command."""
    monkeypatch.setattr(reference_study, "run_study", _fake_study_for_stdout)
    monkeypatch.setattr(sys, "argv", ["reference-study", FAMILY])

    def broken_publisher(
        report: dict[str, Any],
        stream: report_output.TextReportStream,
    ) -> None:
        _ = (report, stream)
        message = OUTPUT_FAULT
        raise report_output.ReportOutputError(message)

    monkeypatch.setattr(report_output, "publish", broken_publisher)
    with pytest.raises(SystemExit, match="2"):
        reference_study.main()
    result = capsys.readouterr()
    assert not result.out
    assert OUTPUT_FAULT in result.err


def test_reference_study_refuses_missing_kernel_limit_launcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No purportedly protected host study can start without prlimit."""
    monkeypatch.setattr(
        host_c_oracle.shutil, "which", lambda *_args, **_kwargs: None
    )
    with pytest.raises(
        reference_study.ReferenceStudyError, match="child limits"
    ):
        reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1),
        )


def test_reference_resource_admission_types_unexpected_dependency_fault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign host-resource probe fault must not escape direct admission."""
    fault = _UnexpectedHostFault("unexpected child resource probe fault")

    def fail_probe() -> None:
        raise fault

    monkeypatch.setattr(host_c_oracle, "require_child_resource_controls", fail_probe)
    with pytest.raises(reference_study.ReferenceStudyError, match="child limits") as caught:
        reference_study._validate_plan(  # ruff: ignore[private-member-access]
            reference_study.StudyPlan(FAMILY, (4,), 7, 1)
        )
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_host_reference_workspace_cleanup_never_dispatches_primary_add_note(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fault_type: type[Exception],
) -> None:
    """Foreign primary hooks cannot conceal a failed workspace setup."""
    directory = tmp_path / "allocated"
    directory.mkdir()

    class HostilePrimary(fault_type):
        def add_note(self, note: str) -> None:
            del note
            raise AssertionError("foreign primary error add_note hook invoked")

    primary = HostilePrimary("primary workspace setup fault")
    cleanup = ValueError("cleanup failed")

    def fake_mkdtemp(**kwargs: object) -> str:
        del kwargs
        return str(directory)

    def broken_mkdir(path: Path) -> None:
        del path
        raise primary

    def broken_cleanup(path: Path) -> None:
        del path
        raise cleanup

    monkeypatch.setattr(reference_study, "_validate_plan", lambda _: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(reference_study.Path, "mkdir", broken_mkdir)
    monkeypatch.setattr(reference_study.shutil, "rmtree", broken_cleanup)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="workspace setup"
    ) as caught:
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))
    assert caught.value.__cause__ is primary
    assert primary.__notes__ == ["host-C workspace cleanup also failed: cleanup failed"]


class _ForgedArtifactLength(bytes):
    """Foreign bytes may lie about their native buffer length."""

    def __len__(self) -> int:
        return 1


@pytest.mark.parametrize("receipt_type", ["forged-length", "oversized"])
def test_retained_artifact_rejects_foreign_or_oversized_evidence_receipt(
    monkeypatch: pytest.MonkeyPatch, receipt_type: str
) -> None:
    """A replaced bounded reader cannot authenticate fabricated artifact sizes."""
    monkeypatch.setattr(reference_study, "MAX_ARTIFACT_BYTES", 4)
    actual = (
        _ForgedArtifactLength(b"forged")
        if receipt_type == "forged-length"
        else b"longer"
    )
    claimed_size = 1 if receipt_type == "forged-length" else len(actual)
    row = {
        "experiment_manifest": ".temp/probe/runs/candidate.toml",
        "metrics": {"artifact_bytes": claimed_size},
    }
    entry = {
        "path": ".temp/probe/candidates/candidate",
        "sha256": sha256(actual).hexdigest(),
    }
    monkeypatch.setattr(
        evidence, "read_bounded_regular", lambda *_args, **_kwargs: actual
    )
    with pytest.raises(
        reference_study.ReferenceStudyError, match="exact bounded bytes"
    ):
        reference_study._checked_artifact(row, entry)


def test_retained_artifact_native_bounded_reader_receipt_remains_admissible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A genuine byte string retains its normal digest and size identity."""
    raw = b"valid"
    monkeypatch.setattr(reference_study, "MAX_ARTIFACT_BYTES", len(raw))
    monkeypatch.setattr(
        evidence, "read_bounded_regular", lambda *_args, **_kwargs: raw
    )
    reference_study._checked_artifact(
        {
            "experiment_manifest": ".temp/probe/runs/candidate.toml",
            "metrics": {"artifact_bytes": len(raw)},
        },
        {
            "path": ".temp/probe/candidates/candidate",
            "sha256": sha256(raw).hexdigest(),
        },
    )


class _ForeignReferenceInteger(int):
    """Numeric subclasses must not decide whether a measurement is successful."""

    def __gt__(self, other: object) -> bool:
        del other
        raise AssertionError("foreign host-C elapsed comparison executed")


class _ForeignExecutableBytes(bytes):
    """Artifact subclasses must not forge the recorded compiled size."""

    def __len__(self) -> int:
        return 1


@pytest.mark.parametrize(
    "measurement",
    [
        object(),
        host_c_oracle.ReferenceMeasurement(_ForeignReferenceInteger(1), b"C", 1024),
        host_c_oracle.ReferenceMeasurement(0, b"C", 1024),
        host_c_oracle.ReferenceMeasurement(
            reference_study.BUDGET_SECONDS * 1_000_000_000 + 1, b"C", 1024
        ),
        host_c_oracle.ReferenceMeasurement(1, b"C", 0),
        host_c_oracle.ReferenceMeasurement(
            1, b"C", reference_study.BUDGET_MEMORY_MIB * 1_048_576 + 1
        ),
        host_c_oracle.ReferenceMeasurement(1, b"C", True),
        host_c_oracle.ReferenceMeasurement(1, b"", 1024),
        host_c_oracle.ReferenceMeasurement(1, _ForeignExecutableBytes(b"forged"), 1024),
        host_c_oracle.ReferenceMeasurement(1, b"longer", 1024),
    ],
)
def test_host_c_measurement_receipt_rejects_foreign_or_invalid_data_before_write(
    monkeypatch: pytest.MonkeyPatch, measurement: object
) -> None:
    """Never publish artifacts or report costs from untrusted native measurements."""
    monkeypatch.setattr(reference_study, "MAX_ARTIFACT_BYTES", 4)
    monkeypatch.setattr(host_c_oracle, "measure_reference", lambda *_args: measurement)

    def forbid_write(*_args: object, **_kwargs: object) -> None:
        pytest.fail("invalid measurement reached artifact publication")

    monkeypatch.setattr(reference_study, "_write_retained_bytes", forbid_write)
    with pytest.raises(reference_study.ReferenceStudyError, match="measurement receipt"):
        reference_study._successful(
            reference_study._ROOT,
            cast("generate.ChallengeIdentity", object()),
            "candidate",
            mode="-O0",
        )


def test_host_c_measurement_receipt_accepts_exact_bounded_native_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid native measurement receipts retain cost and binary identities."""
    receipt = host_c_oracle.ReferenceMeasurement(10, b"good", 1024)
    captured: list[bytes] = []
    monkeypatch.setattr(reference_study, "MAX_ARTIFACT_BYTES", len(receipt.executable))
    monkeypatch.setattr(host_c_oracle, "measure_reference", lambda *_args: receipt)
    monkeypatch.setattr(
        reference_study,
        "_write_retained_bytes",
        lambda _path, payload: captured.append(payload),
    )
    metrics, artifact = reference_study._successful(
        reference_study._ROOT,
        cast("generate.ChallengeIdentity", object()),
        "candidate",
        mode="-O0",
    )
    assert captured == [b"good"]
    assert metrics == {"elapsed_ns": 10, "artifact_bytes": 4, "peak_rss_bytes": 1024}
    assert artifact["sha256"] == sha256(b"good").hexdigest()
