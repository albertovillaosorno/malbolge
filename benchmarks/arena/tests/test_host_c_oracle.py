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

from hashlib import sha256
import json
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Any
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import evidence
from benchmarks.arena import host_c_oracle
from benchmarks.arena.tests.test_challenge_bundles import BUNDLE_ROOT
from benchmarks.arena.tests.test_challenge_bundles import NODES
from benchmarks.arena.tests.test_challenge_bundles import PREFIX
from benchmarks.arena.tests.test_challenge_bundles import PROFILE
from benchmarks.arena.tests.test_challenge_bundles import _study
from benchmarks.challenges import generate

if TYPE_CHECKING:
    from pathlib import Path

MISSING_ROOT_DIAGNOSTIC = "requires --challenge-root"
ORACLE_FAILURE = "host-C challenge oracle"
RUN_MISMATCH_DIAGNOSTIC = "O0 execute failed"
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
    """A timed-out direct compiler child fails instead of being trusted."""

    def timeout(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[bytes]:
        _ = (command, kwargs)
        raise subprocess.TimeoutExpired(["compiler"], 1)

    monkeypatch.setattr(host_c_oracle.sp, "run", timeout)
    with pytest.raises(host_c_oracle.HostOracleError, match="did not complete"):
        host_c_oracle._run(["dummy"], tmp_path, "O0 compile")


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
