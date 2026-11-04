# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Exhaustive correctness evidence for exact verified-result reuse.
# - Must-Not:
#   - Claim timing or allow reuse across different candidate identities.
# - Allows:
#   - Inputs: frozen classic verifier and instrumented verifier callbacks.
#   - Outputs: exact call counts, map parity, reuse, and failure assertions.
#   - Side effects: in-memory verifier-call tracing only.
# - Split-When:
#   - Timed protocol or persistent catalogue reuse gains separate evidence.
# - Merge-When:
#   - Shared reuse tests own this exact two-pass comparison identity.
# - Summary:
#   - Prove the second identical pass reuses all 8,836 verified results.
# - Description:
#   - Every unique candidate verifies once in the reuse arm.
# - Usage:
#   - Collected before opening retained reuse measurement results.
# - Defaults:
#   - Stateful verifier drift must fail complete request-map equality.
#

"""Exhaustive runner evidence for exact repeated-batch verified-result reuse."""

import json
from hashlib import sha256
from types import SimpleNamespace
from typing import cast

import pytest
from algorithms.superoptimization import challenge
from algorithms.superoptimization import verified_block_reuse_runner as runner

_REQUESTS = 17_672
_UNIQUE = 8_836
_REUSED = 8_836
_ACCEPTED = 20
_BEST = 1
_RUNNER_ID = "classic-two-pass-verified-block-reuse-comparison-v1"
_WORKLOAD_SHA256 = (
    "d86f190a512b64724b9546c72f2ee56973292e6ef5707378f8c9a9ba2050bbc7"
)
_MAP_DRIFT = "request-quality map differs from baseline"
_MALFORMED = "quality is malformed"


def test_verified_block_reuse_halves_calls_without_map_drift() -> None:
    """Two identical passes need one independent verification per candidate."""
    result = runner.run_comparison(challenge.verified_quality)
    assert result.runner_id == _RUNNER_ID
    assert result.workload_sha256 == _WORKLOAD_SHA256
    assert result.baseline.request_count == _REQUESTS
    assert result.reused.request_count == _REQUESTS
    assert result.baseline.independent_verifier_calls == _REQUESTS
    assert result.reused.independent_verifier_calls == _UNIQUE
    assert result.reused.reused_request_count == _REUSED
    assert result.reused.unique_candidate_count == _UNIQUE
    assert result.baseline.accepted_request_count == _ACCEPTED
    assert result.reused.accepted_request_count == _ACCEPTED
    assert result.reused.best_verified_quality == _BEST
    assert result.baseline.quality_map == result.reused.quality_map
    assert (
        result.baseline.quality_map_sha256
        == result.reused.quality_map_sha256
    )


def test_reuse_strategy_verifies_every_unique_candidate_exactly_once() -> None:
    """Cache identity is the exact frozen candidate index only."""
    calls: list[int] = []

    def traced(candidate: int) -> int | None:
        calls.append(candidate)
        return challenge.verified_quality(candidate)

    result = runner.run_reuse_strategy(traced)
    assert calls == list(range(_UNIQUE))
    assert result.independent_verifier_calls == _UNIQUE
    assert result.reused_request_count == _REUSED


def test_reuse_comparison_rejects_stateful_second_pass_drift() -> None:
    """A changing verifier cannot be hidden by a cached first-pass result."""
    calls: dict[int, int] = {}

    def drifting(candidate: int) -> int | None:
        count = calls.get(candidate, 0)
        calls[candidate] = count + 1
        if candidate == 0 and count > 0:
            return 1
        return challenge.verified_quality(candidate)

    with pytest.raises(
        runner.VerifiedBlockReuseComparisonError,
        match=_MAP_DRIFT,
    ):
        _ = runner.run_comparison(drifting)


@pytest.mark.parametrize("malformed", [-1, True, "1"])
def test_reuse_runner_rejects_malformed_quality(malformed: object) -> None:
    """Cache storage cannot admit malformed verifier quality values."""
    def verifier(candidate: int) -> int | None:
        _ = candidate
        return cast("int | None", malformed)

    with pytest.raises(
        runner.VerifiedBlockReuseComparisonError,
        match=_MALFORMED,
    ):
        _ = runner.run_reuse_strategy(verifier)


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_reuse_workload_rejects_forged_json_source_identity(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    """A provider cannot hide a changed frozen corpus behind old JSON bytes."""
    original_count = challenge.CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT
    original_document = {
        "base_candidate_count": original_count,
        "base_workload_sha256": challenge.workload_sha256(),
        "passes": 2,
        "request_encoding": "two-complete-lexicographic-passes-v1",
    }
    original_text = json.dumps(
        original_document, sort_keys=True, separators=(",", ":"),
    )
    assert runner.WORKLOAD_SHA256 == sha256(
        original_text.encode("utf-8")
    ).hexdigest()

    class ForgedEncoder:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def encode(self, _value: object) -> str:
            return original_text

    def forged_writer(*_args: object, **_kwargs: object) -> str:
        return original_text

    def forged_encoder_writer(*_args: object, **_kwargs: object) -> str:
        return ForgedEncoder().encode(None)

    with monkeypatch.context() as patch:
        patch.setattr(
            challenge, "CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT", original_count + 1
        )
        selected_writer = (
            forged_encoder_writer if provider == "encoder" else forged_writer
        )
        patch.setattr(
            runner, "json", SimpleNamespace(
                JSONEncoder=ForgedEncoder if provider != "writer" else json.JSONEncoder,
                dumps=selected_writer,
            ),
        )
        with pytest.raises(
            runner.VerifiedBlockReuseComparisonError,
            match="workload JSON serializer disagrees with source",
        ):
            _ = runner.run_reuse_strategy(lambda _candidate: None)


@pytest.mark.parametrize("fault", (RuntimeError, OverflowError))
def test_reuse_workload_wraps_public_json_failures(
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """External JSON faults cannot escape as unrelated exception types."""
    failure = fault("bad provider")

    def failing_writer(*_args: object, **_kwargs: object) -> str:
        raise failure

    with monkeypatch.context() as patch:
        patch.setattr(runner, "json", SimpleNamespace(dumps=failing_writer))
        with pytest.raises(
            runner.VerifiedBlockReuseComparisonError,
            match="workload JSON serializer failed",
        ) as caught:
            _ = runner.run_reuse_strategy(lambda _candidate: None)
        assert caught.value.__cause__ is failure


def test_reuse_workload_accepts_equivalent_json_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An equivalent public writer preserves exact frozen workload identity."""
    original_writer = json.dumps

    def equivalent_writer(*args: object, **kwargs: object) -> str:
        return original_writer(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(runner, "json", SimpleNamespace(dumps=equivalent_writer))
        result = runner.run_reuse_strategy(lambda _candidate: None)
        assert result.request_count == _REQUESTS
