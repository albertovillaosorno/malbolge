# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Canonical backend-neutral durable state for evaluated-search prefixes.
# - Must-Not:
#   - Persist accelerator identity or grant candidate acceptance authority.
# - Allows:
#   - Inputs: validated search requests, batches, and completed evidence prefix.
#   - Outputs: canonical checkpoint bytes and validated restored state.
#   - Side effects: none.
# - Split-When:
#   - Split when an algorithm needs state beyond completed candidate evidence.
# - Merge-When:
#   - Merge when evaluated-search execution owns identical durable state.
# - Summary:
#   - Portable evaluated-search checkpoint codec.
# - Description:
#   - Binds completed evidence to exact request and candidate-batch identity.
# - Usage:
#   - Encode after a durable evaluation prefix and decode before resume.
# - Defaults:
#   - Unknown, noncanonical, mismatched, or mutable state fails closed.
#

"""Canonical backend-neutral checkpoint state for evaluated search."""

from __future__ import annotations

from base64 import b64decode
from base64 import b64encode
from binascii import Error as BinasciiError
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Never
from typing import TYPE_CHECKING
from typing import cast

from accelerator.work_ports import CandidateEvidence

if TYPE_CHECKING:
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import SearchRequest

SEARCH_CHECKPOINT_CODEC_ID = "evaluated-search-prefix-evidence-v1"
SEARCH_CHECKPOINT_SCHEMA = "evaluated-search-checkpoint-v1"
_BATCH_FINGERPRINT_PREFIX = b"evaluated-search-batch-v1\0"

type JsonValue = str | int | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class SearchCheckpointError(ValueError):
    """Durable evaluated-search state is malformed or incompatible."""


@dataclass(frozen=True, slots=True)
class SearchCheckpointState:
    """Validated completed prefix for one exact evaluated-search batch."""

    completed_evidence: tuple[CandidateEvidence, ...]
    completed_units: int
    total_units: int


def search_checkpoint_codec_id() -> str:
    """Return the stable state-codec identity used by progress checkpoints.

    Returns:
        Stable codec identity for the outer portable-checkpoint envelope.

    """
    return SEARCH_CHECKPOINT_CODEC_ID


def _fail(message: str) -> Never:
    raise SearchCheckpointError(message)


def _batch_fingerprint(batch: CandidateEvaluationBatch) -> str:
    validated = batch.validated()
    digest = sha256(_BATCH_FINGERPRINT_PREFIX)
    evaluator_id = validated.evaluator_id.encode("utf-8")
    digest.update(len(evaluator_id).to_bytes(8, "big"))
    digest.update(evaluator_id)
    for item in validated.items:
        admitted = item.validated()
        logical_id = admitted.logical_id.encode("utf-8")
        digest.update(len(logical_id).to_bytes(8, "big"))
        digest.update(logical_id)
        digest.update(len(admitted.payload).to_bytes(8, "big"))
        digest.update(admitted.payload)
    return "sha256:" + digest.hexdigest()


def _problem_fingerprint(request: SearchRequest) -> str:
    return "sha256:" + sha256(request.problem).hexdigest()


def _validate_evidence_item(
    batch: CandidateEvaluationBatch,
    index: int,
    item: object,
) -> None:
    if type(item) is not CandidateEvidence:
        _fail("search checkpoint evidence item has wrong type")
    admitted = item
    if type(admitted.logical_id) is not str:
        _fail("search checkpoint evidence logical ID must use exact str type")
    if type(admitted.payload) is not bytes:
        _fail("search checkpoint evidence payload must use immutable bytes")
    expected = batch.items[index].logical_id
    if admitted.logical_id != expected:
        _fail("search checkpoint evidence is not an exact batch prefix")


def _validate_evidence_prefix(
    batch: CandidateEvaluationBatch,
    evidence: tuple[CandidateEvidence, ...],
) -> tuple[CandidateEvidence, ...]:
    if type(evidence) is not tuple:
        _fail("search checkpoint evidence must use an immutable tuple")
    if len(evidence) > len(batch.items):
        _fail("search checkpoint evidence exceeds candidate batch")
    for index, item in enumerate(evidence):
        _validate_evidence_item(batch, index, item)
    return evidence


def _evidence_document(item: CandidateEvidence) -> JsonObject:
    return {
        "logical_id": item.logical_id,
        "payload_base64": b64encode(item.payload).decode("ascii"),
    }


def _document(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: tuple[CandidateEvidence, ...],
) -> JsonObject:
    validated_request = request.validated()
    validated_batch = batch.validated()
    completed = _validate_evidence_prefix(validated_batch, evidence)
    return {
        "algorithm_id": validated_request.algorithm_id,
        "batch_fingerprint": _batch_fingerprint(validated_batch),
        "codec": SEARCH_CHECKPOINT_CODEC_ID,
        "completed_evidence": [
            _evidence_document(item) for item in completed
        ],
        "completed_units": len(completed),
        "evaluation_budget": validated_request.evaluation_budget,
        "evaluator_id": validated_batch.evaluator_id,
        "problem_sha256": _problem_fingerprint(validated_request),
        "schema": SEARCH_CHECKPOINT_SCHEMA,
        "seed": validated_request.seed,
        "total_units": len(validated_batch.items),
    }


def encode_search_checkpoint(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    evidence: tuple[CandidateEvidence, ...],
) -> bytes:
    """Encode one exact completed evaluated-search prefix.

    Returns:
        Canonical compact UTF-8 JSON suitable for a portable checkpoint payload.

    """
    text = json.dumps(
        _document(request, batch, evidence),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (text + "\n").encode("utf-8")


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate search checkpoint key: {key}")
        result[key] = cast("JsonValue", value)
    return result


def _mapping(value: object, context: str) -> JsonObject:
    if not isinstance(value, dict):
        _fail(f"{context} must be an object")
    raw = cast("dict[object, object]", value)
    result: JsonObject = {}
    for key, item in raw.items():
        if type(key) is not str:
            _fail(f"{context} contains a non-string key")
        result[key] = cast("JsonValue", item)
    return result


def _exact_keys(document: JsonObject, expected: frozenset[str]) -> None:
    actual = frozenset(document)
    if missing := sorted(expected - actual):
        _fail("missing search checkpoint keys: " + ",".join(missing))
    if unknown := sorted(actual - expected):
        _fail("unknown search checkpoint keys: " + ",".join(unknown))


def _string(document: JsonObject, key: str) -> str:
    value = document[key]
    if type(value) is not str or not value:
        _fail(f"search checkpoint {key} must be a non-empty string")
    return value


def _integer(document: JsonObject, key: str) -> int:
    value = document[key]
    if type(value) is not int or value < 0:
        _fail(f"search checkpoint {key} must be a non-negative integer")
    return value


def _payload_text(document: JsonObject) -> str:
    value = document["payload_base64"]
    if type(value) is not str:
        _fail("search checkpoint payload_base64 must use the exact string type")
    return value


def _decode_evidence(value: JsonValue) -> tuple[CandidateEvidence, ...]:
    if type(value) is not list:
        _fail("search checkpoint completed_evidence must be an array")
    result: list[CandidateEvidence] = []
    for raw_item in value:
        item = _mapping(raw_item, "search checkpoint evidence")
        _exact_keys(item, frozenset({"logical_id", "payload_base64"}))
        encoded = _payload_text(item)
        try:
            payload = b64decode(encoded, validate=True)
        except (BinasciiError, ValueError) as error:
            _fail(f"search checkpoint payload_base64 is invalid: {error}")
        if b64encode(payload).decode("ascii") != encoded:
            _fail("search checkpoint payload_base64 is not canonical")
        result.append(
            CandidateEvidence(
                logical_id=_string(item, "logical_id"),
                payload=payload,
            )
        )
    return tuple(result)


_TOP_LEVEL_KEYS = frozenset({
    "algorithm_id",
    "batch_fingerprint",
    "codec",
    "completed_evidence",
    "completed_units",
    "evaluation_budget",
    "evaluator_id",
    "problem_sha256",
    "schema",
    "seed",
    "total_units",
})


def _decode_document(payload: bytes) -> JsonObject:
    if type(payload) is not bytes:
        _fail("search checkpoint must use exact immutable bytes")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        _fail(f"invalid search checkpoint UTF-8: {error}")
    try:
        parsed = cast(
            "object",
            json.loads(text, object_pairs_hook=_reject_duplicate_pairs),
        )
    except SearchCheckpointError:
        raise
    except ValueError as error:
        _fail(f"invalid search checkpoint JSON: {error}")
    document = _mapping(parsed, "search checkpoint")
    _exact_keys(document, _TOP_LEVEL_KEYS)
    return document


def _validate_document_identity(
    document: JsonObject,
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> None:
    expected = _document(request, batch, ())
    for key in (
        "algorithm_id",
        "batch_fingerprint",
        "codec",
        "evaluation_budget",
        "evaluator_id",
        "problem_sha256",
        "schema",
        "seed",
        "total_units",
    ):
        if document[key] != expected[key]:
            _fail(f"search checkpoint {key} does not match current search")


def decode_search_checkpoint(
    payload: bytes,
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> SearchCheckpointState:
    """Decode and validate one exact evaluated-search prefix checkpoint.

    Returns:
        Restored backend-neutral evidence prefix for the exact request and
        batch.

    """
    document = _decode_document(payload)
    _validate_document_identity(document, request, batch)
    evidence = _decode_evidence(document["completed_evidence"])
    validated_batch = batch.validated()
    completed = _validate_evidence_prefix(validated_batch, evidence)
    if _integer(document, "completed_units") != len(completed):
        _fail("search checkpoint completed_units does not match evidence")
    if _integer(document, "total_units") != len(validated_batch.items):
        _fail("search checkpoint total_units does not match candidate batch")
    if encode_search_checkpoint(request, validated_batch, completed) != payload:
        _fail("search checkpoint is not canonical")
    return SearchCheckpointState(
        completed_evidence=completed,
        completed_units=len(completed),
        total_units=len(validated_batch.items),
    )
