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
#   - Exact identity and semantic evidence for the frozen history challenge.
# - Must-Not:
#   - Apply canonicalization, claim measurements, or duplicate verifier tables.
# - Allows:
#   - Inputs: every candidate index plus repository classic verifier semantics.
#   - Outputs: corpus partition, replay, and independent semantic assertions.
#   - Side effects: dynamic import of repository-owned pure modules.
# - Split-When:
#   - Another history challenge gains independent semantics.
# - Merge-When:
#   - Shared challenge tests own this exact corpus identity.
# - Summary:
#   - Lock the 10,000-observation canonicalization challenge before measurement.
# - Description:
#   - Exercises every graphical encryption start and deterministic rotate words.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Search/canonicalization policy is outside this challenge test.
#

"""Exact evidence for the frozen history-residue challenge corpus."""

import importlib.util
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Protocol, cast

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_MODULE = _ROOT / (
    "src/research/algorithms/composition/algorithms/"
    "superoptimization/history_challenge.py"
)
_CANDIDATE_COUNT = 10_000
_ENCRYPTION_COUNT = 6_580
_FIRST_GRAPHICAL = 33
_LAST_GRAPHICAL = 126
_MAX_WORD = 59_048
_ROTATE_SAMPLES = 171
_ENCRYPTION_KIND = "self-encryption"
_ROTATE_KIND = "rotate"
_ERROR = "history candidate index must be in the frozen corpus"
_COUNT_MARKER = b'"candidate_count":10000'
_CHALLENGE_MARKER = b'"challenge_id":"classic-history-residue-search-v1"'
_FORBIDDEN_MARKERS = (b"host", b"timing")


class _Observation(Protocol):
    kind: str
    subject: int
    visits: int


class _ChallengeModule(Protocol):
    HISTORY_CANDIDATE_COUNT: int
    InvalidHistoryChallengeCandidateError: type[ValueError]

    def candidate_observation(self, candidate_index: int) -> _Observation: ...

    def semantic_value(self, observation: _Observation) -> int: ...

    def workload_bytes(self) -> bytes: ...

    def workload_sha256(self) -> str: ...


def _load_challenge() -> _ChallengeModule:
    spec = importlib.util.spec_from_file_location(
        "superoptimization_history_challenge_test",
        _MODULE,
    )
    if spec is None or spec.loader is None:
        message = "history challenge module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        _ = sys.path.pop(0)
    return cast("_ChallengeModule", cast("object", module))


_CHALLENGE = _load_challenge()


def test_history_challenge_has_exact_preregistered_budget_size() -> None:
    """The frozen corpus matches the plan's evaluation budget exactly."""
    assert _CHALLENGE.HISTORY_CANDIDATE_COUNT == _CANDIDATE_COUNT
    first = _CHALLENGE.candidate_observation(0)
    last_encryption = _CHALLENGE.candidate_observation(_ENCRYPTION_COUNT - 1)
    first_rotate = _CHALLENGE.candidate_observation(_ENCRYPTION_COUNT)
    last = _CHALLENGE.candidate_observation(_CANDIDATE_COUNT - 1)
    assert (first.kind, first.subject, first.visits) == (
        _ENCRYPTION_KIND,
        _FIRST_GRAPHICAL,
        0,
    )
    assert (
        last_encryption.kind,
        last_encryption.subject,
        last_encryption.visits,
    ) == (_ENCRYPTION_KIND, _LAST_GRAPHICAL, 69)
    assert (first_rotate.kind, first_rotate.subject, first_rotate.visits) == (
        _ROTATE_KIND,
        0,
        0,
    )
    assert (last.kind, last.subject, last.visits) == (
        _ROTATE_KIND,
        _MAX_WORD,
        19,
    )


def test_history_challenge_rotate_samples_cover_endpoints() -> None:
    """The deterministic rotate sample spans the classic word domain."""
    subjects = {
        _CHALLENGE.candidate_observation(
            _ENCRYPTION_COUNT + (index * 20)
        ).subject
        for index in range(_ROTATE_SAMPLES)
    }
    assert len(subjects) == _ROTATE_SAMPLES
    assert min(subjects) == 0
    assert max(subjects) == _MAX_WORD


def test_history_challenge_semantics_repeat_at_safe_periods() -> None:
    """Challenge semantics expose repeated histories without canonicalizer."""
    encryption_zero = _CHALLENGE.candidate_observation(0)
    encryption_repeat = _CHALLENGE.candidate_observation(68)
    rotate_zero = _CHALLENGE.candidate_observation(_ENCRYPTION_COUNT)
    rotate_ten = _CHALLENGE.candidate_observation(_ENCRYPTION_COUNT + 10)
    assert _CHALLENGE.semantic_value(encryption_zero) == (
        _CHALLENGE.semantic_value(encryption_repeat)
    )
    assert _CHALLENGE.semantic_value(rotate_zero) == (
        _CHALLENGE.semantic_value(rotate_ten)
    )


@pytest.mark.parametrize("candidate_index", [-1, _CANDIDATE_COUNT, True])
def test_history_challenge_rejects_foreign_indices(
    candidate_index: object,
) -> None:
    """Index admission is exact, bounded, and never accepts bool."""
    with pytest.raises(
        _CHALLENGE.InvalidHistoryChallengeCandidateError,
        match=_ERROR,
    ):
        _ = _CHALLENGE.candidate_observation(cast("int", candidate_index))


def test_history_challenge_workload_identity_is_canonical() -> None:
    """Workload digest excludes environment and measurement data."""
    payload = _CHALLENGE.workload_bytes()
    digest = _CHALLENGE.workload_sha256()
    assert sha256(payload).hexdigest() == digest
    assert _COUNT_MARKER in payload
    assert _CHALLENGE_MARKER in payload
    assert all(marker not in payload for marker in _FORBIDDEN_MARKERS)


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_history_workload_rejects_substituted_json_providers(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    """Frozen source identity cannot be rewritten by a public JSON provider."""
    baseline = _CHALLENGE.workload_bytes()
    forged = baseline.decode().replace(
        '"candidate_count":10000', '"candidate_count":9999',
    )
    assert forged.encode() != baseline

    class ForgedEncoder:
        def __init__(self, **_options: object) -> None:
            pass

        def encode(self, _document: object) -> str:
            return forged

    with monkeypatch.context() as patch:
        if provider in ("encoder", "joint"):
            patch.setattr(json, "JSONEncoder", ForgedEncoder)
        if provider in ("writer", "joint"):
            patch.setattr(json, "dumps", lambda *_args, **_kwargs: forged)
        with pytest.raises(
            _CHALLENGE.InvalidHistoryChallengeCandidateError,
            match="workload JSON serializer disagrees with source",
        ):
            _ = _CHALLENGE.workload_bytes()


@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_history_workload_contains_json_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    """Faulty public providers do not leak untyped provenance exceptions."""
    class FailingEncoder:
        def __init__(self, **_options: object) -> None:
            raise RuntimeError("encoder failure")

    def failing_writer(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("writer failure")

    with monkeypatch.context() as patch:
        if provider == "writer":
            patch.setattr(json, "dumps", failing_writer)
        else:
            patch.setattr(json, "JSONEncoder", FailingEncoder)
        with pytest.raises(
            _CHALLENGE.InvalidHistoryChallengeCandidateError,
            match="workload JSON serializer failed",
        ) as captured:
            _ = _CHALLENGE.workload_bytes()
        assert isinstance(captured.value.__cause__, RuntimeError)


def test_history_workload_accepts_equivalent_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equivalent public adapters retain the source-bound workload identity."""
    baseline = _CHALLENGE.workload_bytes()
    native_encoder = json.JSONEncoder

    class EquivalentEncoder(native_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert _CHALLENGE.workload_bytes() == baseline
        assert _CHALLENGE.workload_sha256() == sha256(baseline).hexdigest()
