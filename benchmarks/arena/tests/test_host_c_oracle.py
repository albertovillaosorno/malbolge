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
#   - Independent host-C oracle replay integration and failure regressions.
# - Must-Not:
#   - Treat a canonical C oracle check as candidate compiler verification.
# - Allows:
#   - Inputs: test-local canonical challenge bundles and mocked child outcomes.
#   - Outputs: replay identity and fail-closed compiler execution assertions.
#   - Side effects: temporary repo-local native objects and subprocesses.
# - Split-When:
#   - Candidate target execution gains a separate verifier harness.
# - Merge-When:
#   - Challenge generator conformance owns bounded host replay directly.
# - Summary:
#   - Covers O0/O2 native replay, tampering, limits and child failures.
# - Description:
#   - Independently checks the generated oracle through pinned Clang.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_host_c_oracle.py`.
# - Defaults:
#   - Missing compiler or failed oracle never yields accepted replay.
#

"""Host-C oracle replay tests, not Malbolge candidate certification."""

# ruff: file-ignore[assert,private-member-access,import-private-name]

from __future__ import annotations

import json
import os
import sys
import time
from hashlib import sha256
from pathlib import Path
from typing import IO, Any, cast

import pytest

from benchmarks.arena import analyze, evidence, host_c_oracle
from benchmarks.arena.tests.test_challenge_bundles import (
    BUNDLE_ROOT,
    NODES,
    PREFIX,
    PROFILE,
    _study,
)
from benchmarks.challenges import generate

MISSING_ROOT_DIAGNOSTIC = "requires --challenge-root"
ORACLE_FAILURE = "host-C challenge oracle"
RUN_MISMATCH_DIAGNOSTIC = "O0 execute failed"
ZOMBIE_STATE = "Z"
LINUX_PLATFORM = "linux"
NO_CANDIDATE_SCOPE = "no candidate compiler output"
TIMEOUT_FAILURE = "timeout"


def _policy() -> evidence.EvidencePolicy:
    return evidence.EvidencePolicy(
        challenge_root=BUNDLE_ROOT,
        require_host_c_challenge_oracle=True,
    )


def _case() -> dict[str, Any]:
    return {
        "family": "arithmetic-dag",
        "version": 1,
        "seed": 7,
        "difficulty": NODES,
    }


def _digest() -> str:
    case = _case()
    generated = generate.generate(
        generate.ChallengeIdentity(
            family=case["family"],
            version=case["version"],
            seed=case["seed"],
            profile=PROFILE,
            nodes=case["difficulty"],
        )
    )
    return sha256(generated.source).hexdigest()


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),
    reason="repository pinned native Clang is unavailable",
)
def test_opt_in_native_reference_replays_two_modes_on_one_matched_case(
    tmp_path: Path,
) -> None:
    """Replay real canonical source without crediting either study algorithm."""
    document = _study(tmp_path)
    admitted = analyze.parse_document(json.dumps(document))
    checked = evidence.validate_links(admitted, tmp_path, policy=_policy())
    assert checked["regenerated_challenge_bundles"] == 1
    assert checked["host_c_challenge_oracles_replayed"] == 1
    assert checked["host_c_replay_modes"] == ["O0", "O2"]
    assert checked["host_c_replay_source_sha256"] == {PREFIX: _digest()}
    assert NO_CANDIDATE_SCOPE in checked["scope"]


@pytest.mark.parametrize("route", ["rebuild", "measure"])
@pytest.mark.parametrize("corruption", ["symlink", "oversized"])
def test_host_c_reference_executable_rejects_unsafe_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    corruption: str,
) -> None:
    """Child-created executable bytes require bounded, physical read admission."""
    external = tmp_path / "outside.bin"
    _ = external.write_bytes(b"not an admitted executable")

    def provide_invalid_artifact(directory: Path, mode: str) -> int:
        del mode
        destination = directory / "oracle-check"
        if corruption == "symlink":
            destination.symlink_to(external)
        else:
            with destination.open("wb") as stream:
                _ = stream.truncate(host_c_oracle.CHILD_FILE_BYTES + 1)
        return 1024

    monkeypatch.setattr(host_c_oracle, "_replay_mode", provide_invalid_artifact)
    identity = generate.ChallengeIdentity(
        family=_case()["family"],
        version=_case()["version"],
        seed=_case()["seed"],
        profile=PROFILE,
        nodes=NODES,
    )
    with pytest.raises(host_c_oracle.HostOracleError, match="executable"):
        if route == "rebuild":
            _ = host_c_oracle.rebuild_reference(identity, "-O0")
        else:
            _ = host_c_oracle.measure_reference(identity, "-O0")


def test_host_c_reference_executable_returns_exact_bounded_bytes(
    tmp_path: Path,
) -> None:
    """A physical compiled artifact keeps exact binary bytes including NUL."""
    binary = b"\x00\xffEXE\x7f"
    _ = (tmp_path / "oracle-check").write_bytes(binary)
    assert host_c_oracle._read_reference_executable(tmp_path) == binary


@pytest.mark.parametrize("bad_kind", ["absent", "directory", "empty"])
def test_host_c_reference_executable_requires_nonempty_regular_path(
    tmp_path: Path,
    bad_kind: str,
) -> None:
    """A path missing executable bytes cannot be reported as a benchmark."""
    destination = tmp_path / "oracle-check"
    if bad_kind == "directory":
        destination.mkdir()
    elif bad_kind == "empty":
        _ = destination.write_bytes(b"")
    with pytest.raises(host_c_oracle.HostOracleError, match="executable"):
        _ = host_c_oracle._read_reference_executable(tmp_path)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO fixture")
def test_host_c_reference_executable_rejects_fifo_without_blocking(
    tmp_path: Path,
) -> None:
    """No writer is needed to reject a replaced executable pipe."""
    fifo = tmp_path / "oracle-check"
    mkfifo = getattr(os, "mkfifo", None)
    assert callable(mkfifo)
    mkfifo(fifo)
    with pytest.raises(host_c_oracle.HostOracleError, match="executable"):
        _ = host_c_oracle._read_reference_executable(tmp_path)


def test_host_c_reference_executable_rejects_equal_byte_inode_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even same-content replacement cannot bypass inode-bound evidence."""
    target = tmp_path / "oracle-check"
    _ = target.write_bytes(b"identical compiled output")
    replacement = tmp_path / "replacement"
    _ = replacement.write_bytes(target.read_bytes())
    original_open = evidence.os.open

    def replacing_open(path: str | os.PathLike[str], flags: int) -> int:
        if Path(path) == target:
            _ = replacement.replace(target)
        return original_open(path, flags)

    monkeypatch.setattr(evidence.os, "open", replacing_open)
    with pytest.raises(host_c_oracle.HostOracleError, match="executable"):
        _ = host_c_oracle._read_reference_executable(tmp_path)


def test_host_c_reference_executable_rejects_inplace_rewrite_during_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-inode post-read mutation cannot enter retained reference bytes."""
    target = tmp_path / "oracle-check"
    _ = target.write_bytes(b"original-data")
    original_read = evidence._read_complete

    def rewriting_read(stream: IO[bytes], *, size: int, relative: str) -> bytes:
        data = original_read(stream, size=size, relative=relative)
        _ = target.write_bytes(b"changed!-data")
        return data

    monkeypatch.setattr(evidence, "_read_complete", rewriting_read)
    with pytest.raises(host_c_oracle.HostOracleError, match="executable"):
        _ = host_c_oracle._read_reference_executable(tmp_path)


@pytest.mark.parametrize(
    "fault", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_host_c_reference_executable_preserves_admission_failure_cause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Unexpected reader faults remain typed with their original evidence."""

    def broken_reader(root: Path, relative: str, *, limit: int) -> bytes:
        del root, relative, limit
        raise fault("injected reference read failure")

    monkeypatch.setattr(evidence, "read_bounded_regular", broken_reader)
    with pytest.raises(host_c_oracle.HostOracleError, match="executable") as error:
        _ = host_c_oracle._read_reference_executable(tmp_path)
    assert type(error.value.__cause__) is fault


def test_host_c_replay_requires_canonical_bundle_preflight(
    tmp_path: Path,
) -> None:
    """Opt in without a challenge-root input fails before launching Clang."""
    document = _study(tmp_path)
    admitted = analyze.parse_document(json.dumps(document))
    with pytest.raises(evidence.EvidenceError, match=MISSING_ROOT_DIAGNOSTIC):
        evidence.validate_links(
            admitted,
            tmp_path,
            policy=evidence.EvidencePolicy(require_host_c_challenge_oracle=True),
        )


class _SpoofedDigest(str):  # ruff: ignore[subclass-builtin]
    """Untrusted hash objects may forge both directions of comparison."""

    def __eq__(self, other: object) -> bool:
        del other
        return True

    def __ne__(self, other: object) -> bool:
        del other
        return False


class _SpoofedMode(str):  # ruff: ignore[subclass-builtin]
    """Optimization-mode membership must not call foreign equality hooks."""

    def __eq__(self, other: object) -> bool:
        del other
        return True


def test_direct_host_oracle_rejects_spoofed_digest_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fake source digest must not reach either native compiler stage."""

    def forbidden(*args: object, **kwargs: object) -> int:
        del args, kwargs
        message = "host-C compiler stage reached for forged digest"
        raise AssertionError(message)

    monkeypatch.setattr(host_c_oracle, "_replay_mode", forbidden)
    with pytest.raises(host_c_oracle.HostOracleError, match="source"):
        _ = host_c_oracle.replay_one(_case(), PROFILE, _SpoofedDigest("f" * 64))


@pytest.mark.parametrize("method", ["measure_reference", "rebuild_reference"])
def test_direct_host_oracle_rejects_spoofed_mode_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
) -> None:
    """Foreign mode equality cannot approve an unregistered Clang option."""

    def forbidden(*args: object, **kwargs: object) -> int:
        del args, kwargs
        message = "host-C compiler stage reached for forged mode"
        raise AssertionError(message)

    monkeypatch.setattr(host_c_oracle, "_replay_mode", forbidden)
    identity = generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES)
    action = (
        host_c_oracle.measure_reference
        if method == "measure_reference"
        else host_c_oracle.rebuild_reference
    )
    with pytest.raises(host_c_oracle.HostOracleError, match="mode"):
        _ = action(identity, _SpoofedMode("-Wl,--fatal-warnings"))


class _HostileIdentityField:
    """Formatting foreign dataclass fields can execute arbitrary callbacks."""

    def __str__(self) -> str:
        message = "caller-owned host-C identity formatter executed"
        raise AssertionError(message)


@pytest.mark.parametrize("field", ["family", "version"])
def test_host_c_reference_rejects_hostile_identity_fields_before_generation(
    field: str,
) -> None:
    """Even nominally frozen identity records must have native field types."""
    values: dict[str, object] = {
        "family": "arithmetic-dag",
        "version": 1,
        "seed": 7,
        "profile": PROFILE,
        "nodes": NODES,
    }
    values[field] = _HostileIdentityField()
    identity = generate.ChallengeIdentity(
        family=cast("str", values["family"]),
        version=cast("int", values["version"]),
        seed=7,
        profile=PROFILE,
        nodes=NODES,
    )
    with pytest.raises(host_c_oracle.HostOracleError, match="identity"):
        _ = host_c_oracle._reference_source(identity, "-O0")


@pytest.mark.parametrize("operation", ["replay", "rebuild", "measure"])
@pytest.mark.parametrize("root_kind", ["symlink", "missing", "regular-file"])
def test_host_c_oracle_refuses_nonphysical_scratch_root_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    operation: str,
    root_kind: str,
) -> None:
    """Native oracle work requires an existing nonredirected local .temp."""
    outside = tmp_path / "external"
    outside.mkdir()
    linked = tmp_path / "invalid-root"
    if root_kind == "symlink":
        linked.symlink_to(outside, target_is_directory=True)
    elif root_kind == "regular-file":
        linked.write_bytes(b"not a directory")

    def forbidden_workspace(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("redirected host-C scratch root reached child setup")

    monkeypatch.setattr(host_c_oracle, "_TEMP", linked)
    monkeypatch.setattr(
        host_c_oracle.tempfile, "TemporaryDirectory", forbidden_workspace
    )
    identity = generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES)
    with pytest.raises(host_c_oracle.HostOracleError, match="physical"):
        if operation == "replay":
            _ = host_c_oracle.replay_one(_case(), PROFILE, _digest())
        elif operation == "rebuild":
            _ = host_c_oracle.rebuild_reference(identity, "-O0")
        else:
            _ = host_c_oracle.measure_reference(identity, "-O0")
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("operation", ["replay", "rebuild", "measure"])
@pytest.mark.parametrize("source", ["compiler", "scratch"])
@pytest.mark.parametrize("failure_type", [OSError, ValueError, RuntimeError])
def test_host_oracle_host_preflight_faults_are_typed(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    source: str,
    failure_type: type[Exception],
) -> None:
    """Host stat failures cannot launch a native oracle before preflight."""
    compiler = host_c_oracle._PINNED_CLANG
    scratch = host_c_oracle._TEMP
    original_is_file = Path.is_file
    original_lstat = Path.lstat

    def fail_compiler(path: Path) -> bool:
        if path == compiler:
            raise failure_type("injected compiler inspection failure")
        return original_is_file(path)

    def fail_scratch(path: Path) -> os.stat_result:
        if path == scratch:
            raise failure_type("injected workspace inspection failure")
        return original_lstat(path)

    def forbidden_workspace(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("host oracle reached native workspace after failed preflight")

    if source == "compiler":
        monkeypatch.setattr(Path, "is_file", fail_compiler)
    else:
        monkeypatch.setattr(Path, "lstat", fail_scratch)
    monkeypatch.setattr(
        host_c_oracle.tempfile, "TemporaryDirectory", forbidden_workspace
    )
    identity = generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES)
    with pytest.raises(host_c_oracle.HostOracleError, match="unavailable") as caught:
        if operation == "replay":
            _ = host_c_oracle.replay_one(_case(), PROFILE, _digest())
        elif operation == "rebuild":
            _ = host_c_oracle.rebuild_reference(identity, "-O0")
        else:
            _ = host_c_oracle.measure_reference(identity, "-O0")
    assert isinstance(caught.value.__cause__, failure_type)


@pytest.mark.parametrize("operation", ["replay", "rebuild", "measure"])
@pytest.mark.parametrize("filename", ["program.c", "oracle-harness.c"])
@pytest.mark.parametrize("invalid_count", [None, True, False, -1, 0, "extra"])
def test_host_oracle_never_executes_after_nonexact_source_write(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    filename: str,
    invalid_count: object,
) -> None:
    """A short or fabricated write count cannot certify canonical C bytes."""
    original_write = Path.write_bytes
    native_calls: list[str] = []

    def report_incomplete(path: Path, payload: bytes) -> int:
        written = original_write(path, payload)
        if path.name == filename:
            return cast(
                "int", len(payload) + 1 if invalid_count == "extra" else invalid_count
            )
        return written

    def pretend_native(_directory: Path, mode: str) -> int:
        native_calls.append(mode)
        return 1024

    monkeypatch.setattr(Path, "write_bytes", report_incomplete)
    monkeypatch.setattr(host_c_oracle, "_replay_mode", pretend_native)
    monkeypatch.setattr(
        host_c_oracle, "_read_reference_executable", lambda _dir: b"synthetic-artifact"
    )
    identity = generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES)
    with pytest.raises(host_c_oracle.HostOracleError, match="source write"):
        if operation == "replay":
            _ = host_c_oracle.replay_one(_case(), PROFILE, _digest())
        elif operation == "rebuild":
            _ = host_c_oracle.rebuild_reference(identity, "-O0")
        else:
            _ = host_c_oracle.measure_reference(identity, "-O0")
    assert not native_calls


@pytest.mark.parametrize("operation", ["replay", "rebuild", "measure"])
@pytest.mark.parametrize("fault", ["setup", "source-write"])
def test_direct_host_oracle_workspace_faults_are_typed(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    fault: str,
) -> None:
    """Storage failure never escapes the host-C oracle's typed error boundary."""
    error = OSError("simulated host-C workspace I/O failure")

    def fail(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise error

    if fault == "setup":
        monkeypatch.setattr(host_c_oracle.tempfile, "TemporaryDirectory", fail)
    else:
        monkeypatch.setattr(Path, "write_bytes", fail)
    identity = generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES)
    with pytest.raises(host_c_oracle.HostOracleError, match="workspace") as caught:
        if operation == "replay":
            _ = host_c_oracle.replay_one(_case(), PROFILE, _digest())
        elif operation == "rebuild":
            _ = host_c_oracle.rebuild_reference(identity, "-O0")
        else:
            _ = host_c_oracle.measure_reference(identity, "-O0")
    assert caught.value.__cause__ is error


@pytest.mark.parametrize(
    "bad_case",
    [
        None,
        {},
        {"difficulty": None},
        {"difficulty": False},
        {"difficulty": "8"},
        {"difficulty": 0},
        {"family": []},
    ],
    ids=["none", "empty", "none-nodes", "bool", "text", "zero", "family-list"],
)
def test_direct_host_oracle_rejects_invalid_case_before_native_execution(
    bad_case: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed direct inputs cannot trigger Clang or leak host exceptions."""
    called = False

    def forbidden(*args: object, **kwargs: object) -> int:
        nonlocal called
        del args, kwargs
        called = True
        return 0

    monkeypatch.setattr(host_c_oracle, "_replay_mode", forbidden)
    case = _case()
    if isinstance(bad_case, dict) and bad_case:
        case.update(cast("dict[str, Any]", bad_case))
    else:
        case = cast("dict[str, Any]", bad_case)
    with pytest.raises(host_c_oracle.HostOracleError, match=r"identity|nodes"):
        host_c_oracle.replay_one(case, PROFILE, _digest())
    assert not called


@pytest.mark.parametrize("rebuild", [True, False], ids=["rebuild", "measure"])
@pytest.mark.parametrize("bad_nodes", [None, False, "8"])
def test_host_c_reference_rejects_invalid_identity_before_native_execution(
    *,
    rebuild: bool,
    bad_nodes: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bad reference identities must fail at their bounded admission gate."""
    called = False

    def forbidden(*args: object, **kwargs: object) -> int:
        nonlocal called
        del args, kwargs
        called = True
        return 0

    monkeypatch.setattr(host_c_oracle, "_replay_mode", forbidden)
    identity = generate.ChallengeIdentity(
        family="arithmetic-dag",
        version=1,
        seed=7,
        profile=PROFILE,
        nodes=cast("int", bad_nodes),
    )
    action = (
        host_c_oracle.rebuild_reference if rebuild else host_c_oracle.measure_reference
    )
    with pytest.raises(host_c_oracle.HostOracleError, match=r"identity|nodes"):
        _ = action(identity, "-O0")
    assert not called


class _HostileGeneratorFailure(generate.ChallengeError):
    """Foreign exception diagnostics must never be formatted by replay."""

    def __str__(self) -> str:
        raise AssertionError("hostile challenge error formatting invoked")


class _ForgedCanonicalBytes(bytes):
    """A foreign byte subclass could spoof canonical value equality."""

    def __eq__(self, _other: object) -> bool:
        return True

    def __ne__(self, _other: object) -> bool:
        return False


@pytest.mark.parametrize("route", ["replay", "reference"])
@pytest.mark.parametrize(
    "fault_type",
    [OSError, ValueError, RuntimeError, TypeError, AttributeError],
)
def test_host_c_canonical_generation_host_faults_are_typed(
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    fault_type: type[Exception],
) -> None:
    """Unavailable canonical generation never reaches native compilation."""
    original_digest = _digest()
    fault = fault_type("injected generator host failure")

    def fail_generate(_identity: generate.ChallengeIdentity) -> None:
        raise fault

    monkeypatch.setattr(generate, "generate", fail_generate)
    monkeypatch.setattr(host_c_oracle, "_require_local_scratch_root", lambda: None)
    with pytest.raises(host_c_oracle.HostOracleError, match="regenerat") as caught:
        if route == "replay":
            host_c_oracle._canonical_payload(_case(), PROFILE, original_digest)
        else:
            host_c_oracle._reference_source(
                generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES),
                "-O0",
            )
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("route", ["replay", "reference"])
def test_host_c_canonical_generation_does_not_format_hostile_errors(
    monkeypatch: pytest.MonkeyPatch,
    route: str,
) -> None:
    """A generator's unsafe exception formatter cannot replace typed errors."""
    original_digest = _digest()
    fault = _HostileGeneratorFailure("injected generator failure")

    def fail_generate(_identity: generate.ChallengeIdentity) -> None:
        raise fault

    monkeypatch.setattr(generate, "generate", fail_generate)
    monkeypatch.setattr(host_c_oracle, "_require_local_scratch_root", lambda: None)
    with pytest.raises(host_c_oracle.HostOracleError, match="regenerat") as caught:
        if route == "replay":
            host_c_oracle._canonical_payload(_case(), PROFILE, original_digest)
        else:
            host_c_oracle._reference_source(
                generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES),
                "-O0",
            )
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("route", ["replay", "reference"])
@pytest.mark.parametrize("field", ["source", "oracle", "manifest"])
def test_host_c_canonical_generation_rejects_foreign_byte_subclass(
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    field: str,
) -> None:
    """Only exact generated native bytes can supply executable C evidence."""
    original_digest = _digest()
    original = generate.generate(
        generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES)
    )
    payload = {
        "source": original.source,
        "oracle": original.oracle,
        "manifest": original.manifest,
    }
    payload[field] = _ForgedCanonicalBytes(b"forged")
    forged = generate.GeneratedChallenge(**payload)
    monkeypatch.setattr(generate, "generate", lambda _identity: forged)
    monkeypatch.setattr(host_c_oracle, "_require_local_scratch_root", lambda: None)
    with pytest.raises(host_c_oracle.HostOracleError, match="payload"):
        if route == "replay":
            host_c_oracle._canonical_payload(_case(), PROFILE, original_digest)
        else:
            host_c_oracle._reference_source(
                generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES),
                "-O0",
            )


@pytest.mark.parametrize("route", ["replay", "reference"])
@pytest.mark.parametrize(
    "result", [None, object(), (b"source", b"oracle", b"manifest")]
)
def test_host_c_canonical_generation_rejects_malformed_result(
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    result: object,
) -> None:
    """Canonical generator result shape must be exact before execution."""
    original_digest = _digest()
    monkeypatch.setattr(generate, "generate", lambda _identity: result)
    monkeypatch.setattr(host_c_oracle, "_require_local_scratch_root", lambda: None)
    with pytest.raises(host_c_oracle.HostOracleError, match="payload"):
        if route == "replay":
            host_c_oracle._canonical_payload(_case(), PROFILE, original_digest)
        else:
            host_c_oracle._reference_source(
                generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES),
                "-O0",
            )


def test_host_c_replay_rejects_noncanonical_source_digest() -> None:
    """No unadmitted candidate C source may run through this bounded gate."""
    with pytest.raises(host_c_oracle.HostOracleError, match="source"):
        host_c_oracle.replay_one(_case(), PROFILE, "f" * 64)


def test_host_c_replay_rejects_large_difficulty_before_execution() -> None:
    """Host execution has a smaller bounded node count than source replay."""
    case = _case()
    case["difficulty"] = host_c_oracle.MAX_REPLAY_NODES + 1
    with pytest.raises(host_c_oracle.HostOracleError, match="512-node"):
        host_c_oracle.replay_one(case, PROFILE, _digest())


@pytest.mark.parametrize("failure", ["compile", "link", "execute", "timeout"])
def test_host_c_child_failure_never_becomes_oracle_acceptance(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """Compile, link, run and deadline failures all fail closed."""
    real_run = host_c_oracle._run
    triggered = False

    def inject_failure(command: list[str], cwd: Path, label: str) -> None:
        nonlocal triggered
        if not triggered and (failure in label or failure == TIMEOUT_FAILURE):
            triggered = True
            if failure == TIMEOUT_FAILURE:
                message = "host-C challenge oracle timed out"
                raise host_c_oracle.HostOracleError(message)
            message = f"host-C challenge oracle {label} failed"
            raise host_c_oracle.HostOracleError(message)
        real_run(command, cwd, label)

    monkeypatch.setattr(host_c_oracle, "_run", inject_failure)
    with pytest.raises(host_c_oracle.HostOracleError, match=ORACLE_FAILURE):
        host_c_oracle.replay_one(_case(), PROFILE, _digest())
    assert triggered


def test_child_timeout_is_reported_as_replay_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sleeping Linux child exceeds its deadline and is reaped."""
    monkeypatch.setattr(host_c_oracle, "SUBPROCESS_TIMEOUT_SECONDS", 0.2)
    with pytest.raises(host_c_oracle.HostOracleError, match="timed out"):
        host_c_oracle._run(
            [sys.executable, "-c", "import time; time.sleep(4)"],
            tmp_path,
            "O0 compile",
        )


@pytest.mark.parametrize(
    ("communicated", "waited", "final"),
    [
        (None, 0, 0),
        (False, 0, 0),
        (0, False, 0),
        (0, None, 0),
        (0, 5, 5),
        (0, 0, 5),
        (5, 0, 0),
    ],
)
def test_host_child_requires_consistent_native_exit_receipts(
    monkeypatch: pytest.MonkeyPatch,
    communicated: object,
    waited: object,
    final: object,
) -> None:
    """Neither forged success nor mismatched wait receipts can admit replay."""
    events: list[str] = []

    class ChildProbe:
        returncode: object = None

        def communicate(self, *, timeout: int) -> tuple[None, None]:
            assert timeout == host_c_oracle.SUBPROCESS_TIMEOUT_SECONDS
            events.append("communicate")
            self.returncode = communicated
            return (None, None)

        def wait(self, *, timeout: int) -> int:
            assert timeout == 1
            events.append("wait")
            self.returncode = final
            return cast("int", waited)

    monkeypatch.setattr(
        host_c_oracle,
        "_kill_child_group",
        lambda _child: events.append("group"),
    )
    with pytest.raises(host_c_oracle.HostOracleError, match="exit receipt"):
        host_c_oracle._wait_child(cast("Any", ChildProbe()), "O0 compile")
    assert events == ["communicate", "group", "wait"]


@pytest.mark.parametrize(
    "failure_type", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_host_child_wait_host_faults_are_typed(
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Failed direct child reaping cannot claim a verified host-C stage."""
    fault = failure_type("synthetic wait failure")

    class ChildProbe:
        returncode = 0

        def communicate(self, *, timeout: int) -> tuple[None, None]:
            assert timeout == host_c_oracle.SUBPROCESS_TIMEOUT_SECONDS
            return (None, None)

        def wait(self, *, timeout: int) -> int:
            assert timeout == 1
            raise fault

    monkeypatch.setattr(host_c_oracle, "_kill_child_group", lambda _child: None)
    with pytest.raises(host_c_oracle.HostOracleError, match="cleanup failed") as caught:
        host_c_oracle._wait_child(cast("Any", ChildProbe()), "O0 compile")
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("timeout", [False, True])
def test_host_cleanup_reaps_direct_child_when_group_signal_refused(
    monkeypatch: pytest.MonkeyPatch,
    *,
    timeout: bool,
) -> None:
    """Denied group termination cannot hide timeouts or abandon direct reaps."""
    import subprocess as sp  # ruff: ignore[import-outside-top-level,suspicious-subprocess-import]
    from typing import cast  # ruff: ignore[import-outside-top-level]

    events: list[str] = []

    class ChildProbe:
        returncode = 0

        def communicate(self, *, timeout: int) -> tuple[bytes, bytes]:
            events.append("communicate")
            if timeout == host_c_oracle.SUBPROCESS_TIMEOUT_SECONDS and timed_out:
                raise sp.TimeoutExpired("fake-child", timeout)
            return (b"", b"")

        def poll(self) -> None:
            events.append("poll")

        def kill(self) -> None:
            events.append("kill")

        def wait(self, *, timeout: int) -> int:
            events.append("wait")
            assert timeout > 0
            return 0

    def refuse_group(_child: object) -> None:
        raise PermissionError("group termination denied")

    timed_out = timeout
    monkeypatch.setattr(host_c_oracle, "_kill_child_group", refuse_group)
    with pytest.raises(
        host_c_oracle.HostOracleError,
        match="timed out" if timeout else "cleanup failed",
    ) as error:
        host_c_oracle._wait_child(  # ruff: ignore[private-member-access]
            cast("sp.Popen[bytes]", ChildProbe()), "O0 compile"
        )
    assert events == ["communicate", "poll", "kill", "wait"]
    if timeout:
        assert isinstance(error.value.__cause__, sp.TimeoutExpired)
        assert any("cleanup also failed" in note for note in error.value.__notes__)
    else:
        assert isinstance(error.value.__cause__, PermissionError)


def test_host_cleanup_retries_direct_reap_after_group_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A killed process group never authorizes an unbounded direct wait."""
    import subprocess as sp  # ruff: ignore[import-outside-top-level,suspicious-subprocess-import]
    from typing import cast  # ruff: ignore[import-outside-top-level]

    events: list[str] = []

    class ChildProbe:
        returncode = 0
        waits = 0

        def communicate(self, *, timeout: int) -> tuple[bytes, bytes]:
            assert timeout == host_c_oracle.SUBPROCESS_TIMEOUT_SECONDS
            events.append("communicate")
            return (b"", b"")

        def wait(self, *, timeout: int) -> int:
            assert timeout == 1
            self.waits += 1
            events.append("wait")
            if self.waits == 1:
                raise sp.TimeoutExpired("fake-child", timeout)
            return 0

        def kill(self) -> None:
            events.append("kill")

    monkeypatch.setattr(
        host_c_oracle,
        "_kill_child_group",
        lambda _child: events.append("group"),
    )
    host_c_oracle._wait_child(  # ruff: ignore[private-member-access]
        cast("sp.Popen[bytes]", ChildProbe()), "O0 compile"
    )
    assert events == ["communicate", "group", "wait", "kill", "wait"]


def test_host_child_has_real_kernel_limits(tmp_path: Path) -> None:
    """Linux enforces the resource limits before executing user code."""
    script = (
        "import resource,sys; "
        "keys=(resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE); "
        "expected=(1073741824,16,8388608); "
        "sys.exit(0 if tuple(resource.getrlimit(k)[0] for k in keys) "
        "== expected else 7)"
    )
    host_c_oracle._run([sys.executable, "-c", script], tmp_path, "limits")


def test_host_child_missing_limit_tool_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unbounded native execution cannot silently replace guarded mode."""
    monkeypatch.setattr(host_c_oracle.shutil, "which", lambda *_args, **_kwargs: None)
    with pytest.raises(host_c_oracle.HostOracleError, match="prlimit"):
        host_c_oracle._run([sys.executable, "-c", "pass"], tmp_path, "limits")


@pytest.mark.parametrize("tool", ["prlimit", "time"])
@pytest.mark.parametrize(
    "response",
    ["", "relative/bin", "bad\0name", 17, False, b"/bin/time"],
    ids=["empty", "relative", "nul", "integer", "bool", "bytes"],
)
def test_host_c_resource_preflight_rejects_noncanonical_resolver_receipts(
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    response: object,
) -> None:
    """Untrusted resolver results cannot authorize unbounded native replay."""
    original = host_c_oracle.shutil.which

    def forged(name: str, *, path: str | None = None) -> str | None:
        if name == tool:
            return cast("str", response)
        return original(name, path=path)

    monkeypatch.setattr(host_c_oracle.shutil, "which", forged)
    with pytest.raises(host_c_oracle.HostOracleError, match=tool):
        host_c_oracle.require_child_resource_controls()


@pytest.mark.parametrize("tool", ["prlimit", "time"])
@pytest.mark.parametrize(
    "failure", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_host_c_resource_preflight_types_resolver_errors(
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    failure: type[Exception],
) -> None:
    """A broken resolver is a typed preflight failure, never a raw exception."""
    original = host_c_oracle.shutil.which

    def broken(name: str, *, path: str | None = None) -> str | None:
        if name == tool:
            raise failure("host resolver unavailable")
        return original(name, path=path)

    monkeypatch.setattr(host_c_oracle.shutil, "which", broken)
    with pytest.raises(host_c_oracle.HostOracleError, match=tool) as caught:
        host_c_oracle.require_child_resource_controls()
    assert isinstance(caught.value.__cause__, failure)


@pytest.mark.parametrize("tool", ["prlimit", "time"])
@pytest.mark.parametrize("kind", ["missing", "directory", "nonexecutable", "symlink"])
def test_host_c_resource_preflight_requires_physical_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    kind: str,
) -> None:
    """Host tool must be an existing physical executable, not an unsafe path."""
    original = host_c_oracle.shutil.which
    path = tmp_path / "host-tool"
    if kind == "directory":
        path.mkdir()
    elif kind == "nonexecutable":
        _ = path.write_bytes(b"not executable")
        path.chmod(0o600)
    elif kind == "symlink":
        target = tmp_path / "regular"
        _ = target.write_bytes(b"#!/bin/sh\nexit 0\n")
        target.chmod(0o700)
        path.symlink_to(target)

    def forged(name: str, *, path: str | None = None) -> str | None:
        if name == tool:
            return str(tmp_path / "host-tool")
        return original(name, path=path)

    monkeypatch.setattr(host_c_oracle.shutil, "which", forged)
    with pytest.raises(host_c_oracle.HostOracleError, match=tool):
        host_c_oracle.require_child_resource_controls()


def test_host_child_nonzero_exit_fails_closed(tmp_path: Path) -> None:
    """Child failures remain distinct from passing oracle checks."""
    with pytest.raises(host_c_oracle.HostOracleError, match="failed"):
        host_c_oracle._run(
            [sys.executable, "-c", "raise SystemExit(7)"],
            tmp_path,
            "verification",
        )


def test_native_replay_never_compiles_invalid_retained_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retained source alteration fails canonical replay before child launch."""
    document = _study(tmp_path)
    original = tmp_path / PREFIX / "program.c"
    _ = original.write_bytes(original.read_bytes() + b"\n")
    invoked = False

    def forbidden(
        case: dict[str, Any],
        profile: str,
        source_sha256: str,
    ) -> str:
        nonlocal invoked
        _ = (case, profile, source_sha256)
        invoked = True
        return "forbidden"

    monkeypatch.setattr(host_c_oracle, "replay_one", forbidden)
    with pytest.raises(evidence.EvidenceError, match="bundle differs"):
        evidence.validate_links(
            analyze.parse_document(json.dumps(document)),
            tmp_path,
            policy=_policy(),
        )
    assert not invoked


def test_evidence_cli_opt_in_host_oracle_adds_separate_audit_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI reports host reference checks without altering Pareto outcomes."""
    document = _study(tmp_path)
    input_path = tmp_path / "study.json"
    _ = input_path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(input_path),
            "--root",
            str(tmp_path),
            "--challenge-root",
            BUNDLE_ROOT,
            "--require-host-c-challenge-oracle",
        ],
    )
    assert evidence.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["evidence_preflight"]["host_c_challenge_oracles_replayed"] == 1
    assert output["pareto_frontiers"][0]["algorithms"] == [
        "baseline",
        "candidate",
    ]


ALL_GENERATOR_FAMILIES = (
    "arithmetic-dag",
    "linear-mix",
    "branch-mix",
    "memory-walk",
    "call-chain",
    "pointer-walk",
    "alias-walk",
    "stream-state",
    "sort-reduce",
    "graph-reduce",
    "binary-tree",
    "grid-accumulate",
    "layout-chain",
    "ternary-fold",
    "nested-state",
    "composed-pipeline",
)


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),
    reason="repository pinned native Clang is unavailable",
)
@pytest.mark.parametrize("family", ALL_GENERATOR_FAMILIES)
def test_every_challenge_family_replays_its_native_entry_oracle(
    family: str,
) -> None:
    """All sixteen current families have O0/O2 checked C entry semantics."""
    case = {"family": family, "version": 1, "seed": 11, "difficulty": 8}
    generated = generate.generate(
        generate.ChallengeIdentity(
            family=family,
            version=1,
            seed=11,
            profile=PROFILE,
            nodes=8,
        )
    )
    digest = sha256(generated.source).hexdigest()
    assert host_c_oracle.replay_one(case, PROFILE, digest) == digest


def test_replay_executes_compiled_oracle_instead_of_only_matching_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The expected source hash alone cannot satisfy an incorrect C result."""

    def wrong_harness(oracle: bytes) -> bytes:
        _ = oracle
        return (
            b"#include <stdint.h>\n"
            b"uint32_t malbolge_challenge(void);\n"
            b"int main(void) { return 1; }\n"
        )

    monkeypatch.setattr(host_c_oracle, "_harness", wrong_harness)
    with pytest.raises(host_c_oracle.HostOracleError, match="O0 execute failed"):
        host_c_oracle.replay_one(_case(), PROFILE, _digest())


def test_native_replay_case_count_rejected_before_compiler_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A large multi-case study cannot spawn an unbounded compiler batch."""
    observations = [
        {
            "case": {
                "family": "arithmetic-dag",
                "version": 1,
                "seed": seed,
                "difficulty": NODES,
            }
        }
        for seed in range(host_c_oracle.MAX_REPLAY_CASES + 1)
    ]
    document = {
        "observations": observations,
        "study": {"target_profile": PROFILE},
    }
    invoked = False

    def forbidden(
        case: dict[str, Any],
        profile: str,
        source_sha256: str,
    ) -> str:
        nonlocal invoked
        _ = (case, profile, source_sha256)
        invoked = True
        return "unexpected"

    monkeypatch.setattr(host_c_oracle, "replay_one", forbidden)
    with pytest.raises(evidence.EvidenceError, match="16 distinct cases"):
        evidence._replay_host_c_challenges(document, {}, BUNDLE_ROOT)
    assert not invoked


def test_native_replay_node_limit_checked_before_compiler_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Study-wide over-budget source complexity rejects before any launch."""
    case = {
        "family": "arithmetic-dag",
        "version": 1,
        "seed": 7,
        "difficulty": host_c_oracle.MAX_REPLAY_NODES + 1,
    }
    document = {
        "observations": [{"case": case}],
        "study": {"target_profile": PROFILE},
    }
    invoked = False

    def forbidden(
        candidate: dict[str, Any],
        profile: str,
        source_sha256: str,
    ) -> str:
        nonlocal invoked
        _ = (candidate, profile, source_sha256)
        invoked = True
        return "unexpected"

    monkeypatch.setattr(host_c_oracle, "replay_one", forbidden)
    with pytest.raises(evidence.EvidenceError, match="exceeds 512 nodes"):
        evidence._replay_host_c_challenges(document, {}, BUNDLE_ROOT)
    assert not invoked


def test_evidence_cli_replay_failure_prints_no_pareto_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Even a correctly linked manifest cannot bypass failing host replay."""
    document = _study(tmp_path)
    input_path = tmp_path / "study.json"
    _ = input_path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(input_path),
            "--root",
            str(tmp_path),
            "--challenge-root",
            BUNDLE_ROOT,
            "--require-host-c-challenge-oracle",
        ],
    )

    def wrong_harness(oracle: bytes) -> bytes:
        _ = oracle
        return b"int main(void) { return 1; }\n"

    monkeypatch.setattr(host_c_oracle, "_harness", wrong_harness)
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    result = capsys.readouterr()
    assert not result.out
    assert RUN_MISMATCH_DIAGNOSTIC in result.err


def _check_grandchild_stopped(pid: int) -> None:
    """Check a descendant stops before accepting group cleanup.

    Raises:
        AssertionError: The known grandchild survives a bounded wait.

    """
    proc = Path(f"/proc/{pid}/stat")
    for _ in range(25):
        try:
            state = proc.read_text(encoding="ascii").split(") ", maxsplit=1)[1][0]
        except ProcessLookupError, FileNotFoundError:
            return
        if state == ZOMBIE_STATE:
            return
        time.sleep(0.02)
    os.kill(pid, host_c_oracle.GROUP_TERMINATION_SIGNAL)
    message = "native child descendant escaped its assigned group"
    raise AssertionError(message)


@pytest.mark.skipif(sys.platform != LINUX_PLATFORM, reason="Linux proc child state")
@pytest.mark.parametrize("timeout", [False, True])
def test_host_c_group_termination_reaps_spawned_descendants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    timeout: bool,
) -> None:
    """Success and timeout both stop ordinary descendants of native stages."""
    marker = tmp_path / "grandchild.pid"
    grandchild = (
        "import os,time; "
        f"open({str(marker)!r}, 'w').write(str(os.getpid())); "
        "time.sleep(10)"
    )
    parent = (
        "import pathlib,subprocess,sys,time; "
        f"subprocess.Popen([sys.executable,'-c',{grandchild!r}]); "
        f"p=pathlib.Path({str(marker)!r}); "
        "[(time.sleep(0.01)) for _ in range(200) if not p.exists()]; "
        "time.sleep(2)"
        if timeout
        else "import pathlib,subprocess,sys,time; "
        f"subprocess.Popen([sys.executable,'-c',{grandchild!r}]); "
        f"p=pathlib.Path({str(marker)!r}); "
        "[(time.sleep(0.01)) for _ in range(200) if not p.exists()]"
    )
    if timeout:
        monkeypatch.setattr(host_c_oracle, "SUBPROCESS_TIMEOUT_SECONDS", 0.6)
        with pytest.raises(host_c_oracle.HostOracleError, match="timed out"):
            host_c_oracle._run([sys.executable, "-c", parent], tmp_path, "descendant")
    else:
        host_c_oracle._run([sys.executable, "-c", parent], tmp_path, "descendant")
    assert marker.exists()
    _check_grandchild_stopped(int(marker.read_text()))


def test_host_c_cpu_resource_limit_interrupts_busy_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Linux kernel enforces the CPU ceiling, not only wall time."""
    monkeypatch.setattr(host_c_oracle, "CHILD_CPU_SECONDS", 1)
    monkeypatch.setattr(host_c_oracle, "SUBPROCESS_TIMEOUT_SECONDS", 5)
    with pytest.raises(host_c_oracle.HostOracleError, match="failed"):
        host_c_oracle._run(
            [sys.executable, "-c", "while True: pass"],
            tmp_path,
            "CPU budget",
        )


def test_host_c_file_size_resource_limit_blocks_oversized_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The child cannot write a file beyond the configured kernel limit."""
    max_bytes = 1024
    monkeypatch.setattr(host_c_oracle, "CHILD_FILE_BYTES", max_bytes)
    output = tmp_path / "over-limit.dat"
    script = (
        f"with open({str(output)!r}, 'wb') as writer:\n    writer.write(b'x' * 4096)\n"
    )
    with pytest.raises(host_c_oracle.HostOracleError, match="failed"):
        host_c_oracle._run([sys.executable, "-c", script], tmp_path, "fsize")
    assert output.stat().st_size <= max_bytes


def test_host_c_child_rss_is_kernel_observed_not_reported_magic(
    tmp_path: Path,
) -> None:
    """A real child allocates memory and reports a kernel byte peak."""
    script = "payload=bytearray(16 * 1024 * 1024); assert payload[-1] == 0"
    peak = host_c_oracle._run(
        [sys.executable, "-c", script],
        tmp_path,
        "RSS check",
    )
    minimum_bytes = 16 * 1024 * 1024
    assert minimum_bytes <= peak <= host_c_oracle.CHILD_VIRTUAL_MEMORY_MIB * 1024 * 1024


@pytest.mark.parametrize("invalid", [b"", b"0", b"unknown", b"2" * 40])
def test_host_c_rejects_missing_or_malformed_rss_reports(
    tmp_path: Path,
    invalid: bytes,
) -> None:
    """Malformed external measurement cannot silently become a zero cost."""
    report = tmp_path / "invalid-stage-rss.txt"
    _ = report.write_bytes(invalid)
    with pytest.raises(host_c_oracle.HostOracleError, match="RSS observation"):
        host_c_oracle._read_stage_rss(report)


@pytest.mark.parametrize(
    "invalid",
    [b"1", b"1\r\n", b"1\n\n", b" 1\n", b"1 \n", b"+1\n"],
)
def test_host_c_rss_rejects_noncanonical_gnu_time_bytes(
    tmp_path: Path,
    invalid: bytes,
) -> None:
    """Only one newline-terminated decimal count is GNU-time evidence."""
    report = tmp_path / "rss.txt"
    _ = report.write_bytes(invalid)
    with pytest.raises(host_c_oracle.HostOracleError, match="RSS observation"):
        host_c_oracle._read_stage_rss(report)


@pytest.mark.parametrize("fault", [ValueError, RuntimeError, TypeError, AttributeError])
def test_host_c_rss_read_fault_is_typed_with_original_cause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Malformed evidence-reader methods cannot escape the host-C boundary."""

    def refuse_read(root: Path, relative: str, *, limit: int) -> bytes:
        del root, relative, limit
        raise fault("injected RSS evidence reader fault")

    monkeypatch.setattr(evidence, "read_bounded_regular", refuse_read)
    with pytest.raises(host_c_oracle.HostOracleError, match="RSS observation") as error:
        _ = host_c_oracle._read_stage_rss(tmp_path / "rss.txt")
    assert type(error.value.__cause__) is fault


@pytest.mark.parametrize("primary_fails", [False, True])
def test_host_c_rss_temp_cleanup_is_typed_and_preserves_primary_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    primary_fails: bool,
) -> None:
    """A refused temporary RSS unlink must not erase an earlier stage error."""
    original_unlink = Path.unlink

    def refuse_rss_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path.name.startswith("host-c-stage-rss-"):
            raise PermissionError("injected RSS temp cleanup failure")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", refuse_rss_unlink)
    if primary_fails:

        def reject_rss(path: Path) -> int:
            del path
            raise host_c_oracle.HostOracleError("primary RSS validation failure")

        monkeypatch.setattr(host_c_oracle, "_read_stage_rss", reject_rss)
    with pytest.raises(host_c_oracle.HostOracleError) as error:
        _ = host_c_oracle._run([sys.executable, "-c", "pass"], tmp_path, "RSS cleanup")
    if primary_fails:
        assert "primary RSS validation failure" in str(error.value)
        assert any("cleanup also failed" in note for note in error.value.__notes__)
    else:
        assert "RSS receipt cleanup" in str(error.value)
        assert isinstance(error.value.__cause__, PermissionError)


@pytest.mark.parametrize("fault", [OSError, ValueError, RuntimeError])
def test_host_c_rss_temp_descriptor_close_fault_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Even unexpected descriptor cleanup faults cannot start a false run."""
    original_close = host_c_oracle.os.close

    def close_and_refuse(descriptor: int) -> None:
        original_close(descriptor)
        raise fault("injected stage descriptor close failure")

    monkeypatch.setattr(host_c_oracle.os, "close", close_and_refuse)
    with pytest.raises(
        host_c_oracle.HostOracleError, match="descriptor close"
    ) as error:
        _ = host_c_oracle._run([sys.executable, "-c", "pass"], tmp_path, "RSS")
    assert type(error.value.__cause__) is fault
    assert not list(tmp_path.glob("host-c-stage-rss-*"))


@pytest.mark.parametrize("fault", [OSError, ValueError, RuntimeError])
def test_host_c_rss_temp_creation_fault_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Stage receipt initialization failures never bypass the typed CLI."""

    def refuse_temp(*args: Any, **kwargs: Any) -> tuple[int, str]:
        del args, kwargs
        raise fault("injected RSS temp creation failure")

    monkeypatch.setattr(host_c_oracle.tempfile, "mkstemp", refuse_temp)
    with pytest.raises(host_c_oracle.HostOracleError, match="temporary") as error:
        _ = host_c_oracle._run([sys.executable, "-c", "pass"], tmp_path, "RSS")
    assert type(error.value.__cause__) is fault


def test_host_c_rss_rejects_impossible_peak_above_address_space_limit(
    tmp_path: Path,
) -> None:
    """A reported per-child resident peak cannot exceed its address limit."""
    maximum = (
        host_c_oracle.CHILD_VIRTUAL_MEMORY_MIB
        * host_c_oracle.MIB_BYTES
        // host_c_oracle.KIB_BYTES
    )
    report = tmp_path / "rss.txt"
    _ = report.write_bytes(f"{maximum}\n".encode("ascii"))
    assert host_c_oracle._read_stage_rss(report) == maximum * 1024
    _ = report.write_bytes(f"{maximum + 1}\n".encode("ascii"))
    with pytest.raises(host_c_oracle.HostOracleError, match="outside child limits"):
        host_c_oracle._read_stage_rss(report)


def test_host_c_rss_does_not_follow_linked_receipt(tmp_path: Path) -> None:
    """Source-reported RSS cannot be substituted through a symlink."""
    target = tmp_path / "outside.txt"
    _ = target.write_bytes(b"10\n")
    report = tmp_path / "rss.txt"
    report.symlink_to(target)
    with pytest.raises(host_c_oracle.HostOracleError, match="RSS observation"):
        host_c_oracle._read_stage_rss(report)


@pytest.mark.skipif(
    not hasattr(os, "mkfifo") or not getattr(os, "O_NONBLOCK", 0),
    reason="requires nonblocking POSIX file admission",
)
def test_host_c_rss_rejects_fifo_without_opening_writer(tmp_path: Path) -> None:
    """A substituted pipe must fail admission without waiting for a writer."""
    report = tmp_path / "rss.txt"
    mkfifo = getattr(os, "mkfifo", None)
    assert callable(mkfifo)
    mkfifo(report)
    with pytest.raises(host_c_oracle.HostOracleError, match="RSS observation"):
        host_c_oracle._read_stage_rss(report)


def test_host_c_rss_measurement_tool_missing_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reference verification never substitutes an absent RSS measurement."""
    original = host_c_oracle.shutil.which

    def without_time(name: str, *, path: str | None = None) -> str | None:
        return (
            None
            if name == host_c_oracle.RSS_MEASUREMENT_TOOL
            else original(name, path=path)
        )

    monkeypatch.setattr(host_c_oracle.shutil, "which", without_time)
    with pytest.raises(host_c_oracle.HostOracleError, match="GNU time"):
        host_c_oracle._run([sys.executable, "-c", "pass"], tmp_path, "RSS")


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM
    or host_c_oracle.shutil.which("prlimit", path=os.defpath) is None
    or host_c_oracle.shutil.which("time", path=os.defpath) is None,
    reason="requires system Linux prlimit and GNU time",
)
def test_hostile_path_cannot_impostor_kernel_limiter_or_rss_meter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fake PATH wrappers cannot impersonate real rlimits or metering."""
    for name in (
        host_c_oracle.RESOURCE_LIMIT_TOOL,
        host_c_oracle.RSS_MEASUREMENT_TOOL,
    ):
        fake = tmp_path / name
        fake.write_text("#!/bin/sh\nexit 0\n", encoding="ascii")
        fake.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path))
    child = tmp_path / "real-child-executed"
    assert host_c_oracle._limited_command([sys.executable])[0] != str(
        tmp_path / host_c_oracle.RESOURCE_LIMIT_TOOL
    )
    script = (
        "import pathlib,resource,sys; "
        "keys=(resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE); "
        "expected=(1073741824,16,8388608); "
        "sys.exit(7) if tuple(resource.getrlimit(k)[0] for k in keys) "
        "!= expected else pathlib.Path(sys.argv[1]).write_text('real')"
    )
    peak = host_c_oracle._run(
        [sys.executable, "-c", script, str(child)],
        tmp_path,
        "hostile PATH",
    )
    assert child.read_text(encoding="ascii") == "real"
    assert 0 < peak <= host_c_oracle.CHILD_VIRTUAL_MEMORY_MIB * 1024 * 1024


class _HostileCleanupArgument:
    def __str__(self) -> str:
        raise AssertionError("foreign cleanup argument formatter executed")


@pytest.mark.parametrize(
    "error_class",
    [
        host_c_oracle.HostOracleError,
        OSError,
        PermissionError,
        ValueError,
        TypeError,
        RuntimeError,
        AttributeError,
    ],
)
def test_host_c_cleanup_diagnostic_never_formats_foreign_native_arguments(
    error_class: type[Exception],
) -> None:
    """Even exact built-in error types can carry hostile argument objects."""
    error = error_class(_HostileCleanupArgument())
    assert host_c_oracle._cleanup_error_detail(error) == error_class.__name__


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            host_c_oracle.HostOracleError("native cleanup denied"),
            "native cleanup denied",
        ),
        (OSError(13, "permission denied"), "[Errno 13] permission denied"),
        (ValueError("failed stage"), "failed stage"),
    ],
)
def test_host_c_cleanup_diagnostic_retains_native_error_text(
    error: Exception, expected: str
) -> None:
    """Only directly held native arguments can enter cleanup diagnostics."""
    assert host_c_oracle._cleanup_error_detail(error) == expected


def test_host_c_cleanup_diagnostic_rejects_foreign_errno_argument() -> None:
    """Native OSError cannot include a hostile strerror value in a note."""
    error = OSError(13, _HostileCleanupArgument())
    assert host_c_oracle._cleanup_error_detail(error) == type(error).__name__


def test_host_c_cleanup_diagnostic_bounds_and_sanitizes_native_message() -> None:
    """A very long native error does not inject multiline cleanup annotations."""
    error = host_c_oracle.HostOracleError("host\n" + "x" * 1000)
    detail = host_c_oracle._cleanup_error_detail(error)
    assert detail.startswith("host?xxx")
    assert len(detail) == host_c_oracle.MAX_CLEANUP_DETAIL_CHARS
    assert "\n" not in detail


def test_host_c_child_cleanup_note_preserves_timeout_with_foreign_native_argument(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed owned cleanup error cannot conceal the primary timeout."""
    import subprocess as sp  # ruff: ignore[import-outside-top-level,suspicious-subprocess-import]

    class ChildProbe:
        def communicate(self, *, timeout: int) -> None:
            raise sp.TimeoutExpired("host-child", timeout)

    cleanup = host_c_oracle.HostOracleError(_HostileCleanupArgument())

    def fail_cleanup(_child: object) -> int:
        raise cleanup

    monkeypatch.setattr(host_c_oracle, "_finish_child", fail_cleanup)
    with pytest.raises(host_c_oracle.HostOracleError, match="timed out") as caught:
        host_c_oracle._wait_child(cast("Any", ChildProbe()), "O0 compile")
    assert isinstance(caught.value.__cause__, sp.TimeoutExpired)
    assert any("HostOracleError" in note for note in caught.value.__notes__)


def test_host_c_child_cleanup_note_never_formats_foreign_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hostile child cleanup formatter cannot erase a timeout diagnosis."""
    import subprocess as sp  # ruff: ignore[import-outside-top-level,suspicious-subprocess-import]

    class ForeignCleanupError(host_c_oracle.HostOracleError):
        def __str__(self) -> str:
            raise AssertionError("foreign host-C child cleanup formatter executed")

    cleanup = ForeignCleanupError("cleanup denied")

    class ChildProbe:
        def communicate(self, *, timeout: int) -> None:
            raise sp.TimeoutExpired("host-child", timeout)

    def fail_cleanup(_child: object) -> int:
        raise cleanup

    monkeypatch.setattr(host_c_oracle, "_finish_child", fail_cleanup)
    with pytest.raises(host_c_oracle.HostOracleError, match="timed out") as caught:
        host_c_oracle._wait_child(cast("Any", ChildProbe()), "O0 compile")
    assert isinstance(caught.value.__cause__, sp.TimeoutExpired)
    assert any("ForeignCleanupError" in note for note in caught.value.__notes__)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_host_c_rss_cleanup_note_never_formats_foreign_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A hostile RSS unlink error cannot mask the primary host-C rejection."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign host-C RSS cleanup formatter executed")

    foreign = type("ForeignHostRssCleanup", (fault_type,), {"__str__": unsafe_str})
    cleanup = foreign("RSS cleanup refused")
    primary = host_c_oracle.HostOracleError("primary host-C stage failure")
    original_unlink = Path.unlink

    def fail_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path.name.startswith("host-c-stage-rss-"):
            raise cleanup
        original_unlink(path, missing_ok=missing_ok)

    def fail_stage(_child: object, _label: str) -> None:
        raise primary

    monkeypatch.setattr(host_c_oracle, "_limited_command", lambda command: command)
    monkeypatch.setattr(host_c_oracle, "_system_tool", lambda _name: "/usr/bin/time")
    monkeypatch.setattr(host_c_oracle.sp, "Popen", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(host_c_oracle, "_wait_child", fail_stage)
    monkeypatch.setattr(Path, "unlink", fail_unlink)
    try:
        with pytest.raises(
            host_c_oracle.HostOracleError, match="primary host-C"
        ) as caught:
            _ = host_c_oracle._bounded_child(["fake"], tmp_path, "RSS")
        assert caught.value is primary
        assert any("ForeignHostRssCleanup" in note for note in caught.value.__notes__)
    finally:
        monkeypatch.setattr(Path, "unlink", original_unlink)
        for artifact in tmp_path.glob("host-c-stage-rss-*"):
            artifact.unlink()


def test_host_c_native_child_cleanup_note_retains_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native typed cleanup diagnostics remain useful to the caller."""
    import subprocess as sp  # ruff: ignore[import-outside-top-level,suspicious-subprocess-import]

    class ChildProbe:
        def communicate(self, *, timeout: int) -> None:
            raise sp.TimeoutExpired("host-child", timeout)

    def fail_cleanup(_child: object) -> int:
        raise host_c_oracle.HostOracleError("native child cleanup denied")

    monkeypatch.setattr(host_c_oracle, "_finish_child", fail_cleanup)
    with pytest.raises(host_c_oracle.HostOracleError, match="timed out") as caught:
        host_c_oracle._wait_child(cast("Any", ChildProbe()), "O0 compile")
    assert any("native child cleanup denied" in note for note in caught.value.__notes__)


def test_host_c_child_cleanup_bypasses_hostile_primary_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign primary BaseException cannot hijack cleanup annotation."""

    class HostilePrimary(BaseException):
        def add_note(self, note: str) -> None:
            del note
            raise AssertionError("foreign host-C primary note hook invoked")

    primary = HostilePrimary("primary child fault")
    cleanup = host_c_oracle.HostOracleError("cleanup failed")

    class ChildProbe:
        def communicate(self, *, timeout: int) -> None:
            del timeout
            raise primary

    def fail_cleanup(_child: object) -> int:
        raise cleanup

    monkeypatch.setattr(host_c_oracle, "_finish_child", fail_cleanup)
    with pytest.raises(HostilePrimary) as caught:
        host_c_oracle._wait_child(cast("Any", ChildProbe()), "O0 compile")
    assert caught.value is primary
    assert any("cleanup also failed" in note for note in primary.__notes__)


@pytest.mark.parametrize("kind", [OSError, ValueError, RuntimeError])
def test_host_c_rss_cleanup_bypasses_hostile_primary_note(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: type[Exception],
) -> None:
    """Foreign primary hooks cannot erase a failed RSS measurement."""

    class HostilePrimary(kind):
        def add_note(self, note: str) -> None:
            del note
            raise AssertionError("foreign host-C RSS primary note hook invoked")

    primary = HostilePrimary("primary stage fault")
    cleanup = PermissionError("secondary receipt cleanup failed")
    original_unlink = Path.unlink

    def fail_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path.name.startswith("host-c-stage-rss-"):
            raise cleanup
        original_unlink(path, missing_ok=missing_ok)

    def fail_stage(_child: object, _label: str) -> None:
        raise primary

    monkeypatch.setattr(host_c_oracle, "_limited_command", lambda command: command)
    monkeypatch.setattr(host_c_oracle, "_system_tool", lambda _name: "/usr/bin/time")
    monkeypatch.setattr(host_c_oracle.sp, "Popen", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(host_c_oracle, "_wait_child", fail_stage)
    monkeypatch.setattr(Path, "unlink", fail_unlink)
    try:
        with pytest.raises(HostilePrimary) as caught:
            host_c_oracle._bounded_child(["fake"], tmp_path, "RSS")
        assert caught.value is primary
        assert any("cleanup also failed" in note for note in primary.__notes__)
    finally:
        monkeypatch.setattr(Path, "unlink", original_unlink)
        for artifact in tmp_path.glob("host-c-stage-rss-*"):
            artifact.unlink()


@pytest.mark.parametrize("operation", ["replay", "rebuild", "measure"])
@pytest.mark.parametrize("stage", ["workspace", "source-write", "workspace-cleanup"])
def test_host_c_direct_workspaces_contain_unexpected_host_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    stage: str,
) -> None:
    """Unexpected ordinary storage faults cannot escape public oracle routes."""

    class ForeignWorkspaceFault(LookupError):
        def __str__(self) -> str:
            raise AssertionError("foreign workspace exception formatted")

    fault = ForeignWorkspaceFault("untrusted dependency details")
    original_write = Path.write_bytes

    def fail_workspace(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    def fail_write(path: Path, payload: bytes) -> int:
        if path.name == "program.c":
            raise fault
        return original_write(path, payload)

    class FailingCleanup:
        def __enter__(self) -> str:
            return str(tmp_path)

        def __exit__(self, *_args: object) -> None:
            raise fault

    if stage == "workspace":
        monkeypatch.setattr(
            host_c_oracle.tempfile, "TemporaryDirectory", fail_workspace
        )
    elif stage == "source-write":
        monkeypatch.setattr(Path, "write_bytes", fail_write)
    else:
        monkeypatch.setattr(
            host_c_oracle.tempfile,
            "TemporaryDirectory",
            lambda **_kwargs: FailingCleanup(),
        )
        monkeypatch.setattr(host_c_oracle, "_replay_mode", lambda *_args: 1024)
        monkeypatch.setattr(
            host_c_oracle, "_read_reference_executable", lambda _dir: b"checked"
        )
    identity = generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES)
    with pytest.raises(host_c_oracle.HostOracleError, match="workspace") as caught:
        if operation == "replay":
            host_c_oracle.replay_one(_case(), PROFILE, _digest())
        elif operation == "rebuild":
            host_c_oracle.rebuild_reference(identity, "-O0")
        else:
            host_c_oracle.measure_reference(identity, "-O0")
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("operation", ["replay", "rebuild", "measure"])
def test_host_c_workspace_cleanup_cannot_mask_primary_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """A second workspace cleanup fault must preserve the true replay failure."""

    class ForeignCleanupFault(LookupError):
        def __str__(self) -> str:
            raise AssertionError("foreign workspace cleanup formatter executed")

    primary = host_c_oracle.HostOracleError("native oracle stage failed")
    cleanup = ForeignCleanupFault("untrusted cleanup details")

    class FailingCleanup:
        def __enter__(self) -> str:
            return str(tmp_path)

        def __exit__(self, *_args: object) -> None:
            raise cleanup

    def fail_replay(_directory: Path, _mode: str) -> int:
        raise primary

    def fake_workspace(**_kwargs: object) -> FailingCleanup:
        return FailingCleanup()

    monkeypatch.setattr(host_c_oracle.tempfile, "TemporaryDirectory", fake_workspace)
    monkeypatch.setattr(host_c_oracle, "_replay_mode", fail_replay)
    identity = generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES)
    with pytest.raises(
        host_c_oracle.HostOracleError, match="native oracle stage"
    ) as caught:
        if operation == "replay":
            host_c_oracle.replay_one(_case(), PROFILE, _digest())
        elif operation == "rebuild":
            host_c_oracle.rebuild_reference(identity, "-O0")
        else:
            host_c_oracle.measure_reference(identity, "-O0")
    assert caught.value is primary
    assert any("ForeignCleanupFault" in note for note in primary.__notes__)


class _ForeignHostTransportFault(LookupError):
    def __str__(self) -> str:
        raise AssertionError("foreign child transport fault formatter executed")


@pytest.mark.parametrize("source", ["receipt-creation", "child-start"])
def test_host_c_child_setup_rejects_unexpected_dependency_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    """Unknown ordinary host setup failures cannot leak outside the replay API."""
    fault = _ForeignHostTransportFault("untrusted host details")
    monkeypatch.setattr(host_c_oracle, "_limited_command", lambda command: command)
    monkeypatch.setattr(host_c_oracle, "_system_tool", lambda _name: "/usr/bin/time")

    def fail_start(*_args: object, **_kwargs: object) -> None:
        raise fault

    if source == "receipt-creation":
        monkeypatch.setattr(host_c_oracle.tempfile, "mkstemp", fail_start)
    else:
        monkeypatch.setattr(host_c_oracle.sp, "Popen", fail_start)
    with pytest.raises(
        host_c_oracle.HostOracleError, match="temporary|could not start"
    ) as caught:
        host_c_oracle._bounded_child(["fake"], tmp_path, "compile")
    assert caught.value.__cause__ is fault
    assert not list(tmp_path.glob("host-c-stage-rss-*"))


def test_host_c_child_communication_fault_still_reaps_direct_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unknown communicate failure remains typed after child cleanup."""
    fault = _ForeignHostTransportFault("untrusted child transport details")
    events: list[str] = []

    class ChildProbe:
        returncode = 0

        def communicate(self, *, timeout: int) -> None:
            del timeout
            events.append("communicate")
            raise fault

    def reap(_child: object) -> int:
        events.append("reap")
        return 0

    monkeypatch.setattr(host_c_oracle, "_finish_child", reap)
    with pytest.raises(
        host_c_oracle.HostOracleError, match="transport failed"
    ) as caught:
        host_c_oracle._wait_child(cast("Any", ChildProbe()), "compile")
    assert caught.value.__cause__ is fault
    assert events == ["communicate", "reap"]


def test_host_c_unexpected_group_fault_still_kills_and_reaps_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unknown group signal exception cannot skip direct-child fallback."""
    fault = _ForeignHostTransportFault("untrusted group signal details")
    events: list[str] = []

    class ChildProbe:
        returncode = 0

        def poll(self) -> None:
            events.append("poll")

        def kill(self) -> None:
            events.append("kill")

        def wait(self, *, timeout: int) -> int:
            assert timeout == 1
            events.append("wait")
            return 0

    def fail_group(_child: object) -> None:
        events.append("group")
        raise fault

    monkeypatch.setattr(host_c_oracle, "_kill_child_group", fail_group)
    with pytest.raises(host_c_oracle.HostOracleError, match="cleanup failed") as caught:
        host_c_oracle._finish_child(cast("Any", ChildProbe()))
    assert caught.value.__cause__ is fault
    assert events == ["group", "poll", "kill", "wait"]


@pytest.mark.parametrize("primary_failure", [False, True])
def test_host_c_unexpected_rss_unlink_fault_retains_primary_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    primary_failure: bool,
) -> None:
    """Foreign receipt cleanup faults are typed without erasing child errors."""
    fault = _ForeignHostTransportFault("untrusted RSS receipt cleanup")
    primary = host_c_oracle.HostOracleError("original child transport rejection")
    original_unlink = Path.unlink

    def fail_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path.name.startswith("host-c-stage-rss-"):
            raise fault
        original_unlink(path, missing_ok=missing_ok)

    def finish(_child: object, _label: str) -> None:
        if primary_failure:
            raise primary

    monkeypatch.setattr(host_c_oracle, "_limited_command", lambda command: command)
    monkeypatch.setattr(host_c_oracle, "_system_tool", lambda _name: "/usr/bin/time")
    monkeypatch.setattr(host_c_oracle.sp, "Popen", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(host_c_oracle, "_wait_child", finish)
    monkeypatch.setattr(host_c_oracle, "_read_stage_rss", lambda _path: 1024)
    monkeypatch.setattr(Path, "unlink", fail_unlink)
    try:
        with pytest.raises(host_c_oracle.HostOracleError) as caught:
            host_c_oracle._bounded_child(["fake"], tmp_path, "compile")
        if primary_failure:
            assert caught.value is primary
            assert any(
                "_ForeignHostTransportFault" in note for note in primary.__notes__
            )
        else:
            assert "receipt cleanup failed" in str(caught.value)
            assert caught.value.__cause__ is fault
    finally:
        monkeypatch.setattr(Path, "unlink", original_unlink)
        for report in tmp_path.glob("host-c-stage-rss-*"):
            report.unlink()


@pytest.mark.parametrize(
    "boundary",
    ["compiler", "scratch", "resource-tool", "canonical", "rss-read", "artifact-read"],
)
def test_host_c_preflight_contains_unexpected_foreign_dependency_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
) -> None:
    """Foreign ordinary dependency faults must reject before host-C admission."""
    fault = _ForeignHostTransportFault("foreign preflight details")

    def fail(*_args: object, **_kwargs: object) -> None:
        raise fault

    if boundary == "compiler":
        original = Path.is_file

        def compiler_probe(path: Path) -> bool:
            if path == host_c_oracle._PINNED_CLANG:
                raise fault
            return original(path)

        monkeypatch.setattr(Path, "is_file", compiler_probe)
        action = host_c_oracle._require_local_scratch_root
    elif boundary == "scratch":
        original_lstat = Path.lstat

        def scratch_probe(path: Path) -> os.stat_result:
            if path == host_c_oracle._TEMP:
                raise fault
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", scratch_probe)
        action = host_c_oracle._require_local_scratch_root
    elif boundary == "resource-tool":
        monkeypatch.setattr(host_c_oracle.shutil, "which", fail)
        action = lambda: host_c_oracle._system_tool("prlimit")
    elif boundary == "canonical":
        monkeypatch.setattr(generate, "generate", fail)
        identity = generate.ChallengeIdentity("arithmetic-dag", 1, 7, PROFILE, NODES)
        action = lambda: host_c_oracle._generate_canonical(identity, scope="reference")
    elif boundary == "rss-read":
        monkeypatch.setattr(evidence, "read_bounded_regular", fail)
        action = lambda: host_c_oracle._read_stage_rss(tmp_path / "rss.txt")
    else:
        monkeypatch.setattr(evidence, "read_bounded_regular", fail)
        action = lambda: host_c_oracle._read_reference_executable(tmp_path)
    with pytest.raises(host_c_oracle.HostOracleError) as caught:
        action()
    assert caught.value.__cause__ is fault
