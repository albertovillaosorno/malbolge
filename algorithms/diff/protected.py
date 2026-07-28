# File:
#   - protected.py
# Path:
#   - algorithms/diff/protected.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Protected exact-baseline plans with source-bound authenticated literals.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Protected exact-baseline plans with source-bound authenticated literals."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from typing import TYPE_CHECKING

from algorithms.diff.exact import materialize_exact_plan
from algorithms.diff.exact import snapshot_tree_excluding
from algorithms.diff.model import ExactAuthoringPlan
from algorithms.diff.model import ExactInstruction
from algorithms.diff.model import ExactInstructionKind
from algorithms.diff.model import OracleLiteral
from algorithms.diff.model import SourceSlice
from algorithms.diff.payload import chacha20_poly1305_decrypt
from algorithms.diff.payload import chacha20_poly1305_encrypt
from algorithms.diff.source_binding import bind_secret
from algorithms.diff.source_binding import hkdf_expand_sha256
from algorithms.diff.source_binding import hkdf_extract_sha256
from algorithms.diff.source_binding import recover_secret

if TYPE_CHECKING:
    from pathlib import Path

    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.model import ExactSegment
    from algorithms.diff.model import TreeSnapshot
    from algorithms.diff.payload import AuthenticatedPayload
    from algorithms.diff.source_binding import SourceBindingPolicy
    from algorithms.diff.source_binding import ThresholdBinding

_ZERO = 0
_ONE = 1
_PAYLOAD_KEY_BYTES = 32
_SINGLE_MESSAGE_NONCE = bytes(12)
_FRAME_BYTES = 8
_AAD_MAGIC = b"source-bound-exact-plan-aad-v2\0"
_KEY_DOMAIN = b"source-bound-exact-plan-source-key-v1\0"
_BINDING_CONTEXT_DOMAIN = b"source-bound-exact-plan-binding-v1\0"


class ProtectedPlanError(ValueError):
    """Raised when protected-plan framing or payload references are invalid."""


class ProtectedInstructionKind(StrEnum):
    """How a protected exact output instruction obtains target bytes."""

    COPY_SOURCE = "copy-source"
    PATCH_SOURCE = "patch-source"
    PAYLOAD = "payload"


@dataclass(frozen=True, slots=True)
class PayloadSlice:
    """A byte range inside the authenticated literal plaintext stream."""

    offset: int
    length: int

    def __post_init__(self) -> None:
        """Reject negative protected-payload ranges.

        Raises:
            ProtectedPlanError: Offset or length is negative.

        """
        if self.offset < _ZERO or self.length < _ZERO:
            message = "payload slices require non-negative offset and length"
            raise ProtectedPlanError(message)


ProtectedSegment = SourceSlice | PayloadSlice


@dataclass(frozen=True, slots=True)
class ProtectedInstruction:
    """One exact output instruction with no plaintext oracle bytes."""

    output_path: str
    kind: ProtectedInstructionKind
    expected_sha256: str
    source_path: str | None = None
    payload_slice: PayloadSlice | None = None
    segments: tuple[ProtectedSegment, ...] = ()

    def __post_init__(self) -> None:
        """Reject ambiguous protected instruction payloads.

        Raises:
            ProtectedPlanError: Fields do not match the instruction kind.

        """
        if self.kind is ProtectedInstructionKind.COPY_SOURCE:
            valid = (
                self.source_path is not None
                and self.payload_slice is None
                and not self.segments
            )
        elif self.kind is ProtectedInstructionKind.PATCH_SOURCE:
            valid = (
                self.source_path is not None
                and self.payload_slice is None
                and bool(self.segments)
            )
        elif self.kind is ProtectedInstructionKind.PAYLOAD:
            valid = (
                self.source_path is None
                and self.payload_slice is not None
                and not self.segments
            )
        else:
            valid = False
        if not valid:
            message = f"invalid protected instruction fields for {self.kind!r}"
            raise ProtectedPlanError(message)


@dataclass(frozen=True, slots=True)
class ProtectedMetadata:
    """Authenticated static metadata for one protected exact plan."""

    source: TreeSnapshot
    target: TreeSnapshot
    instructions: tuple[ProtectedInstruction, ...]
    passthrough_roots: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProtectedExactPlan:
    """Exact metadata with authenticated source-bound literals."""

    source: TreeSnapshot
    target: TreeSnapshot
    instructions: tuple[ProtectedInstruction, ...]
    passthrough_roots: tuple[str, ...]
    context: bytes
    nonce: bytes
    payload: AuthenticatedPayload
    binding: ThresholdBinding


@dataclass(slots=True)
class _PayloadBuilder:
    data: bytearray

    def append(self, literal: bytes) -> PayloadSlice:
        """Append literal bytes.

        Returns:
            Deterministic range of the appended bytes.

        """
        start = len(self.data)
        self.data.extend(literal)
        return PayloadSlice(offset=start, length=len(literal))


def _frame_bytes(value: bytes) -> bytes:
    return len(value).to_bytes(_FRAME_BYTES, byteorder="big") + value


def _frame_text(value: str) -> bytes:
    return _frame_bytes(value.encode("utf-8"))


def _u64(value: int) -> bytes:
    if value < _ZERO or value >= (1 << 64):
        message = "protected-plan integer exceeds unsigned 64-bit framing"
        raise ProtectedPlanError(message)
    return value.to_bytes(_FRAME_BYTES, byteorder="big")


def _snapshot_bytes(snapshot: TreeSnapshot) -> bytes:
    parts = [_u64(len(snapshot.files))]
    for record in snapshot.files:
        parts.extend((
            _frame_text(record.path),
            _frame_text(record.sha256),
            _u64(record.size),
        ))
    return b"".join(parts)


def _segment_bytes(segment: ProtectedSegment) -> bytes:
    if isinstance(segment, SourceSlice):
        return b"S" + _u64(segment.offset) + _u64(segment.length)
    return b"P" + _u64(segment.offset) + _u64(segment.length)


def _instruction_bytes(instruction: ProtectedInstruction) -> bytes:
    if instruction.kind is ProtectedInstructionKind.COPY_SOURCE:
        kind = b"C"
    elif instruction.kind is ProtectedInstructionKind.PATCH_SOURCE:
        kind = b"P"
    else:
        kind = b"L"
    source_path = (
        b"\x00"
        if instruction.source_path is None
        else b"\x01" + _frame_text(instruction.source_path)
    )
    payload_slice = (
        b"\x00"
        if instruction.payload_slice is None
        else (
            b"\x01"
            + _u64(instruction.payload_slice.offset)
            + _u64(instruction.payload_slice.length)
        )
    )
    segments = b"".join(_segment_bytes(item) for item in instruction.segments)
    return b"".join((
        kind,
        _frame_text(instruction.output_path),
        _frame_text(instruction.expected_sha256),
        source_path,
        payload_slice,
        _u64(len(instruction.segments)),
        segments,
    ))


def _roots_bytes(roots: tuple[str, ...]) -> bytes:
    return b"".join((_u64(len(roots)), *(_frame_text(root) for root in roots)))


def protected_plan_aad(
    metadata: ProtectedMetadata,
    *,
    context: bytes,
) -> bytes:
    """Serialize deterministic authenticated metadata for one protected plan.

    Returns:
        Stable binary AAD independent of ciphertext and source-binding shares.

    Raises:
        ProtectedPlanError: Context is empty.

    """
    if not context:
        message = "protected-plan context must be non-empty"
        raise ProtectedPlanError(message)
    instruction_bytes = b"".join(
        _instruction_bytes(instruction) for instruction in metadata.instructions
    )
    return b"".join((
        _AAD_MAGIC,
        _frame_bytes(context),
        _frame_bytes(_snapshot_bytes(metadata.source)),
        _frame_bytes(_snapshot_bytes(metadata.target)),
        _roots_bytes(metadata.passthrough_roots),
        _u64(len(metadata.instructions)),
        instruction_bytes,
    ))


def _metadata(
    source: TreeSnapshot,
    target: TreeSnapshot,
    instructions: tuple[ProtectedInstruction, ...],
    *,
    passthrough_roots: tuple[str, ...],
) -> ProtectedMetadata:
    return ProtectedMetadata(
        source=source,
        target=target,
        instructions=instructions,
        passthrough_roots=passthrough_roots,
    )


def _protected_segment(
    segment: ExactSegment,
    builder: _PayloadBuilder,
) -> ProtectedSegment:
    if isinstance(segment, SourceSlice):
        return segment
    return builder.append(segment.data)


def _protect_instruction(
    instruction: ExactInstruction,
    builder: _PayloadBuilder,
) -> ProtectedInstruction:
    if instruction.kind is ExactInstructionKind.COPY_SOURCE:
        return ProtectedInstruction(
            output_path=instruction.output_path,
            kind=ProtectedInstructionKind.COPY_SOURCE,
            expected_sha256=instruction.expected_sha256,
            source_path=instruction.source_path,
        )
    if instruction.kind is ExactInstructionKind.PATCH_SOURCE:
        return ProtectedInstruction(
            output_path=instruction.output_path,
            kind=ProtectedInstructionKind.PATCH_SOURCE,
            expected_sha256=instruction.expected_sha256,
            source_path=instruction.source_path,
            segments=tuple(
                _protected_segment(segment, builder)
                for segment in instruction.segments
            ),
        )
    if instruction.literal is None:
        message = "literal instruction lost authoring bytes before protection"
        raise ProtectedPlanError(message)
    return ProtectedInstruction(
        output_path=instruction.output_path,
        kind=ProtectedInstructionKind.PAYLOAD,
        expected_sha256=instruction.expected_sha256,
        payload_slice=builder.append(instruction.literal),
    )


def _source_identity_digest(reference_identity: IdentityTree) -> bytes:
    digest = hashlib.sha256()
    digest.update(b"source-bound-exact-plan-identity-v1\0")
    digest.update(_u64(len(reference_identity.files)))
    for identity_file in reference_identity.files:
        digest.update(_frame_text(identity_file.path))
        digest.update(_frame_bytes(identity_file.canonical))
    return digest.digest()


def _derive_payload_key(
    reference_identity: IdentityTree,
    *,
    plaintext: bytes,
    aad: bytes,
    context: bytes,
) -> bytes:
    source_material = _source_identity_digest(reference_identity)
    aad_digest = hashlib.sha256(aad).digest()
    plaintext_digest = hashlib.sha256(plaintext).digest()
    salt = hashlib.sha256(
        _KEY_DOMAIN + _frame_bytes(context) + _frame_bytes(aad_digest)
    ).digest()
    pseudorandom_key = hkdf_extract_sha256(salt, source_material)
    info = b"literal-payload-key-v2" + _frame_bytes(plaintext_digest)
    return hkdf_expand_sha256(
        pseudorandom_key,
        info,
        _PAYLOAD_KEY_BYTES,
    )


def _binding_context(aad: bytes, context: bytes) -> bytes:
    digest = hashlib.sha256()
    digest.update(_BINDING_CONTEXT_DOMAIN)
    digest.update(_frame_bytes(context))
    digest.update(_frame_bytes(hashlib.sha256(aad).digest()))
    return digest.digest()


def protect_exact_plan(
    plan: ExactAuthoringPlan,
    reference_identity: IdentityTree,
    *,
    binding_policy: SourceBindingPolicy,
    context: bytes,
) -> ProtectedExactPlan:
    """Protect all exact-plan oracle literals behind source-bound AEAD material.

    One plan derives one 256-bit payload key from canonical source evidence,
    authenticated metadata, and the literal-stream digest. The all-zero nonce
    is therefore never reused for a different plaintext under the same derived
    key inside this deterministic construction.

    Returns:
        Deterministic exact plan containing no plaintext oracle literals.

    """
    builder = _PayloadBuilder(bytearray())
    instructions = tuple(
        _protect_instruction(instruction, builder)
        for instruction in plan.instructions
    )
    plaintext = bytes(builder.data)
    metadata = _metadata(
        plan.source,
        plan.target,
        instructions,
        passthrough_roots=plan.passthrough_roots,
    )
    aad = protected_plan_aad(metadata, context=context)
    key = _derive_payload_key(
        reference_identity,
        plaintext=plaintext,
        aad=aad,
        context=context,
    )
    payload = chacha20_poly1305_encrypt(
        key,
        _SINGLE_MESSAGE_NONCE,
        plaintext,
        aad=aad,
    )
    binding = bind_secret(
        reference_identity,
        key,
        policy=binding_policy,
        context=_binding_context(aad, context),
    )
    return ProtectedExactPlan(
        source=plan.source,
        target=plan.target,
        instructions=instructions,
        passthrough_roots=plan.passthrough_roots,
        context=context,
        nonce=_SINGLE_MESSAGE_NONCE,
        payload=payload,
        binding=binding,
    )


def _payload_slice(plaintext: bytes, reference: PayloadSlice) -> bytes:
    end = reference.offset + reference.length
    if end > len(plaintext):
        message = "protected payload slice exceeds authenticated plaintext"
        raise ProtectedPlanError(message)
    return plaintext[reference.offset : end]


def _exact_segment(
    segment: ProtectedSegment,
    plaintext: bytes,
) -> ExactSegment:
    if isinstance(segment, SourceSlice):
        return segment
    return OracleLiteral(_payload_slice(plaintext, segment))


def _exact_instruction(
    instruction: ProtectedInstruction,
    plaintext: bytes,
) -> ExactInstruction:
    if instruction.kind is ProtectedInstructionKind.COPY_SOURCE:
        return ExactInstruction(
            output_path=instruction.output_path,
            kind=ExactInstructionKind.COPY_SOURCE,
            expected_sha256=instruction.expected_sha256,
            source_path=instruction.source_path,
        )
    if instruction.kind is ProtectedInstructionKind.PATCH_SOURCE:
        return ExactInstruction(
            output_path=instruction.output_path,
            kind=ExactInstructionKind.PATCH_SOURCE,
            expected_sha256=instruction.expected_sha256,
            source_path=instruction.source_path,
            segments=tuple(
                _exact_segment(segment, plaintext)
                for segment in instruction.segments
            ),
        )
    if instruction.payload_slice is None:
        message = "protected payload instruction lost its payload range"
        raise ProtectedPlanError(message)
    return ExactInstruction(
        output_path=instruction.output_path,
        kind=ExactInstructionKind.LITERAL_ORACLE,
        expected_sha256=instruction.expected_sha256,
        literal=_payload_slice(plaintext, instruction.payload_slice),
    )


def recover_exact_plan(
    plan: ProtectedExactPlan,
    candidate_identity: IdentityTree,
) -> ExactAuthoringPlan:
    """Recover authenticated local literals only after source binding succeeds.

    Returns:
        In-memory exact plan suitable for transactional materialization.

    """
    metadata = _metadata(
        plan.source,
        plan.target,
        plan.instructions,
        passthrough_roots=plan.passthrough_roots,
    )
    aad = protected_plan_aad(metadata, context=plan.context)
    key = recover_secret(plan.binding, candidate_identity)
    plaintext = chacha20_poly1305_decrypt(
        key,
        plan.nonce,
        plan.payload,
        aad=aad,
    )
    instructions = tuple(
        _exact_instruction(instruction, plaintext)
        for instruction in plan.instructions
    )
    return ExactAuthoringPlan(
        source=plan.source,
        target=plan.target,
        instructions=instructions,
        passthrough_roots=plan.passthrough_roots,
    )


def materialize_protected_exact_plan(
    source_root: Path,
    candidate_identity: IdentityTree,
    *,
    plan: ProtectedExactPlan,
    output_root: Path,
) -> None:
    """Recover and authenticate literals before publishing exact output.

    Raises:
        ProtectedPlanError: The exact source snapshot changed.

    """
    if (
        snapshot_tree_excluding(source_root, plan.passthrough_roots)
        != plan.source
    ):
        message = "source tree does not match protected exact source snapshot"
        raise ProtectedPlanError(message)
    exact = recover_exact_plan(plan, candidate_identity)
    materialize_exact_plan(source_root, exact, output_root)
