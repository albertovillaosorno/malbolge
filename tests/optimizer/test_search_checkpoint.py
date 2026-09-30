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
#   - Regression evidence for backend-neutral evaluated-search checkpoints.
# - Must-Not:
#   - Claim product resume integration or candidate acceptance authority.
# - Allows:
#   - Inputs: deterministic search requests, batches, and evidence prefixes.
#   - Outputs: exact round-trip and fail-closed compatibility assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when algorithm-specific resume execution needs its own fixtures.
# - Merge-When:
#   - Merge when another suite owns the same search checkpoint codec contract.
# - Summary:
#   - Evaluated-search checkpoint codec regressions.
# - Description:
#   - Proves canonical state survives backend changes and rejects drift.
# - Usage:
#   - Runs with the optimizer Python validation suite.
# - Defaults:
#   - Mismatched, mutable, malformed, or noncanonical state is rejected.
#

"""Regression tests for backend-neutral evaluated-search checkpoints."""

from __future__ import annotations

from dataclasses import replace
import json
from typing import cast

from accelerator.search_checkpoint import SEARCH_CHECKPOINT_CODEC_ID
from accelerator.search_checkpoint import SearchCheckpointError
from accelerator.search_checkpoint import decode_search_checkpoint
from accelerator.search_checkpoint import encode_search_checkpoint
from accelerator.search_checkpoint import search_checkpoint_codec_id
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateEvidence
from accelerator.work_ports import CandidateWorkItem
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import indexed_candidate_items_from_rotated_u32le
import pytest

ALGORITHM_ID = "checkpoint-test-search-v1"
BACKEND_FIELD = "backend"
DEVICE_FIELD = "device"
EVALUATOR_ID = "checkpoint-test-evaluator-v1"


def _request() -> SearchRequest:
    return SearchRequest(
        algorithm_id=ALGORITHM_ID,
        evaluation_budget=3,
        problem=b"problem-v1",
        seed=17,
    )


def _batch() -> CandidateEvaluationBatch:
    return CandidateEvaluationBatch(
        evaluator_id=EVALUATOR_ID,
        items=(
            CandidateWorkItem(logical_id="candidate-0", payload=b"alpha"),
            CandidateWorkItem(logical_id="candidate-1", payload=b"beta"),
            CandidateWorkItem(logical_id="candidate-2", payload=b"gamma"),
        ),
    )


def _evidence() -> tuple[CandidateEvidence, ...]:
    return (
        CandidateEvidence(logical_id="candidate-0", payload=b"evidence-a"),
        CandidateEvidence(logical_id="candidate-1", payload=b"evidence-b"),
    )


def test_search_checkpoint_round_trip_is_backend_neutral() -> None:
    """Exact evidence bytes restore without carrying backend identity."""
    request = _request()
    batch = _batch()
    evidence = _evidence()

    encoded = encode_search_checkpoint(request, batch, evidence)
    restored = decode_search_checkpoint(encoded, request, batch)
    document = cast("dict[str, object]", json.loads(encoded))

    assert search_checkpoint_codec_id() == SEARCH_CHECKPOINT_CODEC_ID
    assert restored.completed_evidence == evidence
    assert restored.completed_units == len(evidence)
    assert restored.total_units == len(batch.items)
    assert BACKEND_FIELD not in document
    assert DEVICE_FIELD not in document
    assert encode_search_checkpoint(request, batch, evidence) == encoded


def test_search_checkpoint_supports_packed_indexed_batches() -> None:
    """Packed candidate storage restores through the same portable codec."""
    request = _request()
    batch = CandidateEvaluationBatch(
        evaluator_id=EVALUATOR_ID,
        items=indexed_candidate_items_from_rotated_u32le(
            logical_id_prefix="candidate-",
            logical_indices_u32le=(
                (0).to_bytes(4, "little")
                + (1).to_bytes(4, "little")
                + (2).to_bytes(4, "little")
            ),
            payload_width=1,
            payloads=b"abc",
        ),
    )
    evidence = (CandidateEvidence(logical_id="candidate-0", payload=b"x"),)
    tuple_batch = CandidateEvaluationBatch(
        evaluator_id=EVALUATOR_ID,
        items=(
            CandidateWorkItem(logical_id="candidate-0", payload=b"a"),
            CandidateWorkItem(logical_id="candidate-1", payload=b"b"),
            CandidateWorkItem(logical_id="candidate-2", payload=b"c"),
        ),
    )

    encoded = encode_search_checkpoint(request, batch, evidence)
    restored = decode_search_checkpoint(encoded, request, batch)

    assert restored.completed_evidence == evidence
    assert restored.total_units == len(batch.items)
    assert encode_search_checkpoint(request, tuple_batch, evidence) == encoded


def test_search_checkpoint_accepts_empty_evidence_payload() -> None:
    """An exact completed candidate may have an empty evidence payload."""
    request = _request()
    batch = _batch()
    evidence = (CandidateEvidence(logical_id="candidate-0", payload=b""),)

    encoded = encode_search_checkpoint(request, batch, evidence)
    restored = decode_search_checkpoint(encoded, request, batch)

    assert restored.completed_evidence == evidence


def test_search_checkpoint_accepts_empty_completed_prefix() -> None:
    """A checkpoint before the first completed candidate is canonical."""
    request = _request()
    batch = _batch()
    encoded = encode_search_checkpoint(request, batch, ())

    restored = decode_search_checkpoint(encoded, request, batch)

    assert restored.completed_evidence == ()
    assert restored.completed_units == 0
    assert restored.total_units == len(batch.items)


def test_search_checkpoint_rejects_request_and_batch_drift() -> None:
    """Source search identity and exact candidate bytes remain bound."""
    request = _request()
    batch = _batch()
    encoded = encode_search_checkpoint(request, batch, _evidence())
    changed_request = replace(request, problem=b"problem-v2")
    changed_batch = replace(
        batch,
        items=(
            batch.items[0],
            CandidateWorkItem(logical_id="candidate-1", payload=b"changed"),
            batch.items[2],
        ),
    )

    with pytest.raises(SearchCheckpointError, match="problem_sha256"):
        _ = decode_search_checkpoint(encoded, changed_request, batch)
    with pytest.raises(SearchCheckpointError, match="batch_fingerprint"):
        _ = decode_search_checkpoint(encoded, request, changed_batch)


def test_search_checkpoint_rejects_foreign_evidence_identity_type() -> None:
    """Direct evidence identity aliases cannot bypass exact string admission."""
    request = _request()
    batch = _batch()
    invalid = CandidateEvidence(
        logical_id=cast("str", cast("object", 0)),
        payload=b"evidence",
    )

    with pytest.raises(SearchCheckpointError, match="exact str type"):
        _ = encode_search_checkpoint(request, batch, (invalid,))


def test_search_checkpoint_rejects_nonprefix_and_mutable_evidence() -> None:
    """Only an immutable request-order evidence prefix can be persisted."""
    request = _request()
    batch = _batch()
    wrong_order = tuple(reversed(_evidence()))

    with pytest.raises(SearchCheckpointError, match="exact batch prefix"):
        _ = encode_search_checkpoint(request, batch, wrong_order)
    with pytest.raises(SearchCheckpointError, match="immutable tuple"):
        _ = encode_search_checkpoint(
            request,
            batch,
            cast(
                "tuple[CandidateEvidence, ...]",
                cast("object", list(_evidence())),
            ),
        )
    mutable = CandidateEvidence(
        logical_id="candidate-0",
        payload=cast("bytes", cast("object", bytearray(b"mutable"))),
    )
    with pytest.raises(SearchCheckpointError, match="immutable bytes"):
        _ = encode_search_checkpoint(request, batch, (mutable,))


def test_search_checkpoint_rejects_boolean_completed_count() -> None:
    """Boolean aliases cannot satisfy integer progress counters."""
    request = _request()
    batch = _batch()
    encoded = encode_search_checkpoint(request, batch, _evidence())
    document = cast("dict[str, object]", json.loads(encoded))
    document["completed_units"] = True
    payload = (
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()

    with pytest.raises(SearchCheckpointError, match="non-negative integer"):
        _ = decode_search_checkpoint(payload, request, batch)


def test_search_checkpoint_rejects_corrupt_and_noncanonical_json() -> None:
    """Malformed payloads and alternate JSON spellings fail closed."""
    request = _request()
    batch = _batch()
    encoded = encode_search_checkpoint(request, batch, _evidence())
    document = cast("dict[str, object]", json.loads(encoded))
    evidence = cast("list[dict[str, object]]", document["completed_evidence"])
    evidence[0]["payload_base64"] = "***"
    malformed = (
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()

    with pytest.raises(SearchCheckpointError, match="payload_base64"):
        _ = decode_search_checkpoint(malformed, request, batch)

    noncanonical = json.dumps(
        cast("dict[str, object]", json.loads(encoded)),
        sort_keys=True,
        indent=2,
    ).encode()
    with pytest.raises(SearchCheckpointError, match="not canonical"):
        _ = decode_search_checkpoint(noncanonical, request, batch)

    duplicate = encoded.replace(
        b'"seed":17,',
        b'"seed":17,"seed":17,',
        1,
    )
    with pytest.raises(SearchCheckpointError, match="duplicate"):
        _ = decode_search_checkpoint(duplicate, request, batch)

    with pytest.raises(SearchCheckpointError, match="exact immutable bytes"):
        _ = decode_search_checkpoint(
            cast("bytes", cast("object", bytearray(encoded))),
            request,
            batch,
        )
