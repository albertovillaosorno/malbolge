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
from typing import Any

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
            policy=evidence.EvidencePolicy(
                require_host_c_challenge_oracle=True
            ),
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
    monkeypatch.setattr(
        host_c_oracle.shutil, "which", lambda *_args, **_kwargs: None
    )
    with pytest.raises(host_c_oracle.HostOracleError, match="prlimit"):
        host_c_oracle._run([sys.executable, "-c", "pass"], tmp_path, "limits")


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
    assert (
        output["evidence_preflight"]["host_c_challenge_oracles_replayed"] == 1
    )
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
    with pytest.raises(
        host_c_oracle.HostOracleError, match="O0 execute failed"
    ):
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
            state = proc.read_text(encoding="ascii").split(") ", maxsplit=1)[1][
                0
            ]
        except ProcessLookupError, FileNotFoundError:
            return
        if state == ZOMBIE_STATE:
            return
        time.sleep(0.02)
    os.kill(pid, host_c_oracle.GROUP_TERMINATION_SIGNAL)
    message = "native child descendant escaped its assigned group"
    raise AssertionError(message)


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM, reason="Linux proc child state"
)
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
            host_c_oracle._run(
                [sys.executable, "-c", parent], tmp_path, "descendant"
            )
    else:
        host_c_oracle._run(
            [sys.executable, "-c", parent], tmp_path, "descendant"
        )
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
        f"with open({str(output)!r}, 'wb') as writer:\n"
        "    writer.write(b'x' * 4096)\n"
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
    assert (
        minimum_bytes
        <= peak
        <= host_c_oracle.CHILD_VIRTUAL_MEMORY_MIB * 1024 * 1024
    )


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
