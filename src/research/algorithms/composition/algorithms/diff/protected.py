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
#   - Protected exact-baseline plans with source-bound authenticated literals.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Protected exact-baseline plans with source-bound authenticated literals."""

from __future__ import annotations

import builtins
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256 as _native_sha256
from types import MemberDescriptorType
from typing import TYPE_CHECKING, cast

from algorithms.diff.admission import IdentityFile, IdentityTree
from algorithms.diff.exact import (
    _new_exact_instruction,  # pyright: ignore[reportPrivateUsage]
    _new_exact_plan,  # pyright: ignore[reportPrivateUsage]
    _new_oracle_literal,  # pyright: ignore[reportPrivateUsage]
    materialize_exact_plan,
    snapshot_tree_excluding,
)
from algorithms.diff.model import (
    ExactAuthoringPlan,
    ExactInstruction,
    ExactInstructionKind,
    FileRecord,
    OracleLiteral,
    SourceSlice,
    TreeModelError,
    TreeSnapshot,
    _oracle_literal_data,  # pyright: ignore[reportPrivateUsage]
    reserved_windows_component,
)
from algorithms.diff.model import (
    _instruction_fields as _exact_instruction_fields,  # pyright: ignore[reportPrivateUsage]
)
from algorithms.diff.model import (
    _plan_fields as _exact_plan_fields,  # pyright: ignore[reportPrivateUsage]
)
from algorithms.diff.payload import (
    AuthenticatedPayload,
    chacha20_poly1305_decrypt,
    chacha20_poly1305_encrypt,
)
from algorithms.diff.source_binding import (
    SourceBindingError,
    bind_secret,
    hkdf_expand_sha256,
    hkdf_extract_sha256,
    recover_secret,
    validate_threshold_binding,
)

if TYPE_CHECKING:
    from pathlib import Path

    from algorithms.diff.model import ExactSegment
    from algorithms.diff.source_binding import (
        SourceBindingPolicy,
        ThresholdBinding,
    )

_ZERO = 0
_ONE = 1
_PAYLOAD_KEY_BYTES = 32
_SINGLE_MESSAGE_NONCE = bytes(12)
_FRAME_BYTES = 8
_SHA256_HEX_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")
_NUL = "\x00"
_BACKSLASH = "\\"
_UNSAFE_COMPONENTS = frozenset(("", ".", ".."))
_AAD_MAGIC = b"source-bound-exact-plan-aad-v2\0"
_KEY_DOMAIN = b"source-bound-exact-plan-source-key-v1\0"
_BINDING_CONTEXT_DOMAIN = b"source-bound-exact-plan-binding-v1\0"
# Preserve authenticated metadata admission across post-import domain hooks.
_NATIVE_ANY = builtins.any
_NATIVE_SORTED = builtins.sorted
_NATIVE_SET = builtins.set
_NATIVE_TYPE = builtins.type
_NATIVE_LEN = builtins.len
_NATIVE_TUPLE = builtins.tuple
_NATIVE_ENUMERATE = builtins.enumerate
_NATIVE_BOOL = builtins.bool
_NATIVE_BYTES = builtins.bytes
_NATIVE_BYTEARRAY = builtins.bytearray
# The authoring key schedule must hash the admitted identity's original
# storage, not mutable dataclass field getters installed after import.
_IDENTITY_FILES_SLOT = cast("MemberDescriptorType", IdentityTree.__dict__["files"])
_IDENTITY_PATH_SLOT = cast("MemberDescriptorType", IdentityFile.__dict__["path"])
_IDENTITY_CANONICAL_SLOT = cast(
    "MemberDescriptorType", IdentityFile.__dict__["canonical"]
)
# AAD must serialize precisely the fields validated by tree model admission.
# Read original slots rather than caller-mutable TreeSnapshot/FileRecord getters.
_SNAPSHOT_FILES_SLOT = cast("MemberDescriptorType", TreeSnapshot.__dict__["files"])
_FILE_PATH_SLOT = cast("MemberDescriptorType", FileRecord.__dict__["path"])
_FILE_SHA256_SLOT = cast("MemberDescriptorType", FileRecord.__dict__["sha256"])
_FILE_SIZE_SLOT = cast("MemberDescriptorType", FileRecord.__dict__["size"])
_SOURCE_SLICE_OFFSET_SLOT = cast("MemberDescriptorType", SourceSlice.__dict__["offset"])
_SOURCE_SLICE_LENGTH_SLOT = cast("MemberDescriptorType", SourceSlice.__dict__["length"])
# Read nested model evidence with validators pinned before consumer hooks.
_TREE_SNAPSHOT_VALIDATOR = cast(
    "Callable[[TreeSnapshot], None]", TreeSnapshot.__dict__["__post_init__"]
)
_SOURCE_SLICE_VALIDATOR = cast(
    "Callable[[SourceSlice], None]", SourceSlice.__dict__["__post_init__"]
)
_EXACT_AUTHORING_PLAN_VALIDATOR = cast(
    "Callable[[ExactAuthoringPlan], None]",
    ExactAuthoringPlan.__dict__["__post_init__"],
)
_NATIVE_INT = builtins.int
_NATIVE_STR = builtins.str
_NATIVE_ISINSTANCE = builtins.isinstance
_NATIVE_OBJECT_NEW = object.__new__


class ProtectedPlanError(ValueError):
    """Raised when protected-plan framing or payload references are invalid."""


class ProtectedInstructionKind(StrEnum):
    """How a protected exact output instruction obtains target bytes."""

    COPY_SOURCE = "copy-source"
    PATCH_SOURCE = "patch-source"
    PAYLOAD = "payload"


def _require_utf8_path(value: str, context: str) -> None:
    if _NUL in value:
        message = f"{context} must not contain NUL"
        raise ProtectedPlanError(message)
    try:
        _ = value.encode("utf-8")
    except UnicodeError as error:
        message = f"{context} must use UTF-8-encodable text"
        raise ProtectedPlanError(message) from error
    # Lexical canonicalization must not delegate to mutable pathlib methods.
    # Empty, dot, or parent components are never valid portable file labels.
    unsafe = (
        _BACKSLASH in value
        or _NATIVE_ANY(
            reserved_windows_component(component)
            for component in value.split("/")
        )
        or _NATIVE_ANY(part in _UNSAFE_COMPONENTS for part in value.split("/"))
    )
    if unsafe:
        message = f"{context} must be a canonical relative path"
        raise ProtectedPlanError(message)


def _require_optional_utf8_path(value: str | None, context: str) -> None:
    if value is not None:
        _require_utf8_path(value, context)


def _require_utf8_roots(roots: tuple[str, ...]) -> None:
    for root in roots:
        _require_utf8_path(root, "protected passthrough root")
    if roots != _NATIVE_TUPLE(_NATIVE_SORTED(_NATIVE_SET(roots))):
        message = "protected passthrough roots must be unique and sorted"
        raise ProtectedPlanError(message)
    for index, root in _NATIVE_ENUMERATE(roots):
        prefix = root + "/"
        if _NATIVE_ANY(
            other.startswith(prefix) for other in roots[index + 1 :]
        ):
            message = "protected passthrough roots must not overlap"
            raise ProtectedPlanError(message)


def _require_sha256_hex(value: object, context: str) -> None:
    if (
        _NATIVE_TYPE(value) is not _NATIVE_STR
        or _NATIVE_LEN(value) != _SHA256_HEX_LENGTH
    ):
        message = f"{context} must be 64 lowercase hex digits"
        raise ProtectedPlanError(message)
    if _NATIVE_ANY(char not in _HEX_DIGITS for char in value):
        message = f"{context} must be 64 lowercase hex digits"
        raise ProtectedPlanError(message)


def _validate_protected_segments(value: object) -> None:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = "protected instruction segments must use an immutable tuple"
        raise ProtectedPlanError(message)
    segments = cast("tuple[object, ...]", value)
    if _NATIVE_ANY(
        _NATIVE_TYPE(item) not in {SourceSlice, PayloadSlice}
        for item in segments
    ):
        message = "protected instruction contains a foreign segment record"
        raise ProtectedPlanError(message)
    for item in segments:
        try:
            if _NATIVE_TYPE(item) is SourceSlice:
                _SOURCE_SLICE_VALIDATOR(item)
            else:
                _PAYLOAD_SLICE_VALIDATOR(cast("PayloadSlice", item))
        except (AttributeError, TreeModelError) as error:
            message = "protected instruction contains an invalid native segment"
            raise ProtectedPlanError(message) from error


@dataclass(frozen=True, slots=True, init=False)
class PayloadSlice:
    """A byte range inside the authenticated literal plaintext stream."""

    offset: int
    length: int

    def __init__(self, offset: int, length: int) -> None:
        """Validate literal ranges with the captured original guard."""
        _PAYLOAD_SLICE_OFFSET_SLOT.__set__(self, offset)
        _PAYLOAD_SLICE_LENGTH_SLOT.__set__(self, length)
        _PAYLOAD_SLICE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject negative protected-payload ranges.

        Raises:
            ProtectedPlanError: Offset or length is negative.

        """
        offset, length = _payload_slice_fields(self)
        if (
            _NATIVE_TYPE(offset) is not _NATIVE_INT
            or _NATIVE_TYPE(length) is not _NATIVE_INT
        ):
            message = "payload slice coordinates must use exact integers"
            raise ProtectedPlanError(message)
        if offset < _ZERO or length < _ZERO:
            message = "payload slices require non-negative offset and length"
            raise ProtectedPlanError(message)


# Generated dataclass constructors dispatch post-init through mutable class
# attributes; capture native guards before consumer code can replace them.
_PAYLOAD_SLICE_VALIDATOR = cast(
    "Callable[[PayloadSlice], None]", PayloadSlice.__dict__["__post_init__"]
)

# The authenticated byte ranges are stored slots, never late class getters.
_PAYLOAD_SLICE_OFFSET_SLOT = cast(
    "MemberDescriptorType", PayloadSlice.__dict__["offset"]
)
_PAYLOAD_SLICE_LENGTH_SLOT = cast(
    "MemberDescriptorType", PayloadSlice.__dict__["length"]
)


def _payload_slice_fields(reference: PayloadSlice) -> tuple[int, int]:
    return (
        _PAYLOAD_SLICE_OFFSET_SLOT.__get__(reference, PayloadSlice),
        _PAYLOAD_SLICE_LENGTH_SLOT.__get__(reference, PayloadSlice),
    )


ProtectedSegment = SourceSlice | PayloadSlice


@dataclass(frozen=True, slots=True, init=False)
class ProtectedInstruction:
    """One exact output instruction with no plaintext oracle bytes."""

    output_path: str
    kind: ProtectedInstructionKind
    expected_sha256: str
    source_path: str | None = None
    payload_slice: PayloadSlice | None = None
    segments: tuple[ProtectedSegment, ...] = ()

    def __init__(
        self,
        output_path: str,
        kind: ProtectedInstructionKind,
        expected_sha256: str,
        source_path: str | None = None,
        payload_slice: PayloadSlice | None = None,
        segments: tuple[ProtectedSegment, ...] = (),
    ) -> None:
        """Validate instruction shape through the original guard."""
        _INSTRUCTION_OUTPUT_SLOT.__set__(self, output_path)
        _INSTRUCTION_KIND_SLOT.__set__(self, kind)
        _INSTRUCTION_SHA256_SLOT.__set__(self, expected_sha256)
        _INSTRUCTION_SOURCE_SLOT.__set__(self, source_path)
        _INSTRUCTION_PAYLOAD_SLOT.__set__(self, payload_slice)
        _INSTRUCTION_SEGMENTS_SLOT.__set__(self, segments)
        _PROTECTED_INSTRUCTION_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject foreign metadata or fields inconsistent with the kind.

        Raises:
            ProtectedPlanError: Metadata types or kind-specific fields are
                invalid.

        """
        _INSTRUCTION_VALIDATE_METADATA(self)
        if not _INSTRUCTION_SHAPE_IS_VALID(self):
            kind = _instruction_fields(self)[1]
            message = f"invalid protected instruction fields for {kind!r}"
            raise ProtectedPlanError(message)

    def _validate_metadata(self) -> None:
        (
            output_path,
            kind,
            expected_sha256,
            source_path,
            payload_slice,
            segments,
        ) = _instruction_fields(self)
        if (
            _NATIVE_TYPE(output_path) is not _NATIVE_STR
            or not output_path
        ):
            message = "protected instruction output path must be non-empty"
            raise ProtectedPlanError(message)
        _require_utf8_path(
            output_path, "protected instruction output path"
        )
        if _NATIVE_TYPE(kind) is not ProtectedInstructionKind:
            message = "protected instruction kind must use the exact enum type"
            raise ProtectedPlanError(message)
        _require_sha256_hex(
            expected_sha256, "protected instruction sha256"
        )
        if source_path is not None and (
            _NATIVE_TYPE(source_path) is not _NATIVE_STR
            or not source_path
        ):
            message = (
                "protected instruction source path must be non-empty or None"
            )
            raise ProtectedPlanError(message)
        _require_optional_utf8_path(
            source_path, "protected instruction source path"
        )
        if payload_slice is not None:
            if _NATIVE_TYPE(payload_slice) is not PayloadSlice:
                message = (
                    "protected instruction payload slice must use the exact record"
                )
                raise ProtectedPlanError(message)
            try:
                _PAYLOAD_SLICE_VALIDATOR(payload_slice)
            except AttributeError as error:
                message = "protected instruction contains an incomplete native payload slice"
                raise ProtectedPlanError(message) from error
        _validate_protected_segments(segments)

    def _shape_is_valid(self) -> bool:
        _, kind, _, source_path, payload_slice, segments = _instruction_fields(
            self
        )
        if kind is ProtectedInstructionKind.COPY_SOURCE:
            return (
                source_path is not None
                and payload_slice is None
                and not segments
            )
        if kind is ProtectedInstructionKind.PATCH_SOURCE:
            return (
                source_path is not None
                and payload_slice is None
                and _NATIVE_BOOL(segments)
            )
        return (
            kind is ProtectedInstructionKind.PAYLOAD
            and source_path is None
            and payload_slice is not None
            and not segments
        )


_PROTECTED_INSTRUCTION_VALIDATOR = cast(
    "Callable[[ProtectedInstruction], None]",
    ProtectedInstruction.__dict__["__post_init__"],
)

# The instruction record is part of authenticated metadata. Preserve the
# original storage descriptors before a consumer can replace class accessors.
_INSTRUCTION_OUTPUT_SLOT = cast(
    "MemberDescriptorType", ProtectedInstruction.__dict__["output_path"]
)
_INSTRUCTION_KIND_SLOT = cast(
    "MemberDescriptorType", ProtectedInstruction.__dict__["kind"]
)
_INSTRUCTION_SHA256_SLOT = cast(
    "MemberDescriptorType", ProtectedInstruction.__dict__["expected_sha256"]
)
_INSTRUCTION_SOURCE_SLOT = cast(
    "MemberDescriptorType", ProtectedInstruction.__dict__["source_path"]
)
_INSTRUCTION_PAYLOAD_SLOT = cast(
    "MemberDescriptorType", ProtectedInstruction.__dict__["payload_slice"]
)
_INSTRUCTION_SEGMENTS_SLOT = cast(
    "MemberDescriptorType", ProtectedInstruction.__dict__["segments"]
)


def _instruction_fields(instruction: ProtectedInstruction) -> tuple[
    str,
    ProtectedInstructionKind,
    str,
    str | None,
    PayloadSlice | None,
    tuple[ProtectedSegment, ...],
]:
    return (
        _INSTRUCTION_OUTPUT_SLOT.__get__(instruction, ProtectedInstruction),
        _INSTRUCTION_KIND_SLOT.__get__(instruction, ProtectedInstruction),
        _INSTRUCTION_SHA256_SLOT.__get__(instruction, ProtectedInstruction),
        _INSTRUCTION_SOURCE_SLOT.__get__(instruction, ProtectedInstruction),
        _INSTRUCTION_PAYLOAD_SLOT.__get__(instruction, ProtectedInstruction),
        _INSTRUCTION_SEGMENTS_SLOT.__get__(instruction, ProtectedInstruction),
    )


# Pin the original validators as well as field descriptors. Authoring must
# not invoke late replacement methods installed on the class by consumers.
_INSTRUCTION_VALIDATE_METADATA = cast(
    "Callable[[ProtectedInstruction], None]",
    ProtectedInstruction.__dict__["_validate_metadata"],
)
_INSTRUCTION_SHAPE_IS_VALID = cast(
    "Callable[[ProtectedInstruction], bool]",
    ProtectedInstruction.__dict__["_shape_is_valid"],
)


def _require_static_target_outside_passthrough(
    target: TreeSnapshot, roots: tuple[str, ...]
) -> None:
    if _NATIVE_ANY(
        path == root or path.startswith(root + "/")
        for record in _stored_snapshot_files(target)
        for path in (_stored_file_fields(record)[0],)
        for root in roots
    ):
        message = "protected static target conflicts with passthrough roots"
        raise ProtectedPlanError(message)


def _require_unique_instruction_outputs(
    instructions: tuple[ProtectedInstruction, ...],
) -> None:
    paths = _NATIVE_TUPLE(_instruction_fields(item)[0] for item in instructions)
    if _NATIVE_LEN(paths) != _NATIVE_LEN(_NATIVE_SET(paths)):
        message = "protected instructions require unique output paths"
        raise ProtectedPlanError(message)


def _require_instructions_match_target(
    instructions: tuple[ProtectedInstruction, ...], target: TreeSnapshot
) -> None:
    authored_outputs = _NATIVE_TUPLE(
        (_instruction_fields(item)[0], _instruction_fields(item)[2])
        for item in instructions
    )
    target_outputs = _NATIVE_TUPLE(
        _stored_file_fields(item)[:2] for item in _stored_snapshot_files(target)
    )
    if authored_outputs != target_outputs:
        message = "protected instructions must match the target snapshot"
        raise ProtectedPlanError(message)


@dataclass(frozen=True, slots=True, init=False)
class ProtectedMetadata:
    """Authenticated static metadata for one protected exact plan."""

    source: TreeSnapshot
    target: TreeSnapshot
    instructions: tuple[ProtectedInstruction, ...]
    passthrough_roots: tuple[str, ...] = ()

    def __init__(
        self,
        source: TreeSnapshot,
        target: TreeSnapshot,
        instructions: tuple[ProtectedInstruction, ...],
        passthrough_roots: tuple[str, ...] = (),
    ) -> None:
        """Admit metadata with the original immutable-record validator."""
        _METADATA_SOURCE_SLOT.__set__(self, source)
        _METADATA_TARGET_SLOT.__set__(self, target)
        _METADATA_INSTRUCTIONS_SLOT.__set__(self, instructions)
        _METADATA_ROOTS_SLOT.__set__(self, passthrough_roots)
        _PROTECTED_METADATA_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require exact immutable authenticated metadata records.

        Raises:
            ProtectedPlanError: Metadata is mutable, foreign, or malformed.

        """
        source, target, instructions, roots = _metadata_fields(self)
        if (
            _NATIVE_TYPE(source) is not TreeSnapshot
            or _NATIVE_TYPE(target) is not TreeSnapshot
        ):
            message = "protected metadata snapshots must use exact TreeSnapshot records"
            raise ProtectedPlanError(message)
        if _NATIVE_TYPE(instructions) is not _NATIVE_TUPLE or _NATIVE_ANY(
            _NATIVE_TYPE(item) is not ProtectedInstruction
            for item in instructions
        ):
            message = "protected metadata instructions must be exact immutable records"
            raise ProtectedPlanError(message)
        try:
            for snapshot in (source, target):
                _TREE_SNAPSHOT_VALIDATOR(snapshot)
            for instruction in instructions:
                _PROTECTED_INSTRUCTION_VALIDATOR(instruction)
        except (AttributeError, TreeModelError) as error:
            message = "protected metadata contains invalid or incomplete native evidence"
            raise ProtectedPlanError(message) from error
        _require_unique_instruction_outputs(instructions)
        _require_instructions_match_target(instructions, target)
        if _NATIVE_TYPE(roots) is not _NATIVE_TUPLE:
            message = "protected passthrough roots must use an immutable tuple"
            raise ProtectedPlanError(message)
        if _NATIVE_ANY(
            _NATIVE_TYPE(root) is not _NATIVE_STR or not root
            for root in roots
        ):
            message = "protected passthrough roots must be non-empty strings"
            raise ProtectedPlanError(message)
        _require_utf8_roots(roots)
        _require_static_target_outside_passthrough(target, roots)


_PROTECTED_METADATA_VALIDATOR = cast(
    "Callable[[ProtectedMetadata], None]", ProtectedMetadata.__dict__["__post_init__"]
)

# Store original metadata descriptors before later consumer code can replace
# class getters used by framing or the direct-construction trust boundary.
_METADATA_SOURCE_SLOT = cast(
    "MemberDescriptorType", ProtectedMetadata.__dict__["source"]
)
_METADATA_TARGET_SLOT = cast(
    "MemberDescriptorType", ProtectedMetadata.__dict__["target"]
)
_METADATA_INSTRUCTIONS_SLOT = cast(
    "MemberDescriptorType", ProtectedMetadata.__dict__["instructions"]
)
_METADATA_ROOTS_SLOT = cast(
    "MemberDescriptorType", ProtectedMetadata.__dict__["passthrough_roots"]
)


def _metadata_fields(metadata: ProtectedMetadata) -> tuple[
    TreeSnapshot,
    TreeSnapshot,
    tuple[ProtectedInstruction, ...],
    tuple[str, ...],
]:
    return (
        _METADATA_SOURCE_SLOT.__get__(metadata, ProtectedMetadata),
        _METADATA_TARGET_SLOT.__get__(metadata, ProtectedMetadata),
        _METADATA_INSTRUCTIONS_SLOT.__get__(metadata, ProtectedMetadata),
        _METADATA_ROOTS_SLOT.__get__(metadata, ProtectedMetadata),
    )


@dataclass(frozen=True, slots=True, init=False)
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

    def __init__(
        self,
        source: TreeSnapshot,
        target: TreeSnapshot,
        instructions: tuple[ProtectedInstruction, ...],
        passthrough_roots: tuple[str, ...],
        context: bytes,
        nonce: bytes,
        payload: AuthenticatedPayload,
        binding: ThresholdBinding,
    ) -> None:
        """Admit the authenticated envelope with the original guard."""
        _PLAN_SOURCE_SLOT.__set__(self, source)
        _PLAN_TARGET_SLOT.__set__(self, target)
        _PLAN_INSTRUCTIONS_SLOT.__set__(self, instructions)
        _PLAN_ROOTS_SLOT.__set__(self, passthrough_roots)
        _PLAN_CONTEXT_SLOT.__set__(self, context)
        _PLAN_NONCE_SLOT.__set__(self, nonce)
        _PLAN_PAYLOAD_SLOT.__set__(self, payload)
        _PLAN_BINDING_SLOT.__set__(self, binding)
        _PROTECTED_EXACT_PLAN_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require exact immutable protected-plan envelope types.

        Raises:
            ProtectedPlanError: Plan envelope metadata is foreign or malformed.

        """
        (
            source,
            target,
            instructions,
            passthrough_roots,
            context,
            nonce,
            payload,
            binding,
        ) = _plan_fields(self)
        _ = _new_protected_metadata(
            source=source,
            target=target,
            instructions=instructions,
            passthrough_roots=passthrough_roots,
        )
        if _NATIVE_TYPE(context) is not _NATIVE_BYTES or not context:
            message = "protected plan context must use non-empty exact bytes"
            raise ProtectedPlanError(message)
        if _NATIVE_TYPE(nonce) is not _NATIVE_BYTES or _NATIVE_LEN(
            nonce
        ) != _NATIVE_LEN(_SINGLE_MESSAGE_NONCE):
            message = "protected plan nonce must use exact 12-byte input"
            raise ProtectedPlanError(message)
        if _NATIVE_TYPE(payload) is not AuthenticatedPayload:
            message = (
                "protected plan payload must use the exact authenticated type"
            )
            raise ProtectedPlanError(message)
        try:
            _ = validate_threshold_binding(binding)
        except SourceBindingError as error:
            # Only the exact known exception may contribute a diagnostic
            # message. A foreign subclass can execute code from __str__.
            detail = _NATIVE_TYPE(error).__name__
            if _NATIVE_TYPE(error) is SourceBindingError:
                # Read native exception storage, not a mutable class getter.
                arguments = cast(
                    "tuple[object, ...]",
                    BaseException.__getattribute__(  # ruff: ignore[unnecessary-dunder-call]
                        error, "args"
                    ),
                )
                if (
                    _NATIVE_LEN(arguments) == _ONE
                    and _NATIVE_TYPE(arguments[0]) is _NATIVE_STR
                ):
                    detail = arguments[0]
            message = f"protected plan binding is invalid: {detail}"
            raise ProtectedPlanError(message) from error


_PROTECTED_EXACT_PLAN_VALIDATOR = cast(
    "Callable[[ProtectedExactPlan], None]", ProtectedExactPlan.__dict__["__post_init__"]
)

# Read the original plan storage slots across authoring and recovery. Mutable
# class getters and descriptors must not replace authenticated plan evidence.
_PLAN_SOURCE_SLOT = cast(
    "MemberDescriptorType", ProtectedExactPlan.__dict__["source"]
)
_PLAN_TARGET_SLOT = cast(
    "MemberDescriptorType", ProtectedExactPlan.__dict__["target"]
)
_PLAN_INSTRUCTIONS_SLOT = cast(
    "MemberDescriptorType", ProtectedExactPlan.__dict__["instructions"]
)
_PLAN_ROOTS_SLOT = cast(
    "MemberDescriptorType", ProtectedExactPlan.__dict__["passthrough_roots"]
)
_PLAN_CONTEXT_SLOT = cast(
    "MemberDescriptorType", ProtectedExactPlan.__dict__["context"]
)
_PLAN_NONCE_SLOT = cast(
    "MemberDescriptorType", ProtectedExactPlan.__dict__["nonce"]
)
_PLAN_PAYLOAD_SLOT = cast(
    "MemberDescriptorType", ProtectedExactPlan.__dict__["payload"]
)
_PLAN_BINDING_SLOT = cast(
    "MemberDescriptorType", ProtectedExactPlan.__dict__["binding"]
)


def _plan_fields(plan: ProtectedExactPlan) -> tuple[
    TreeSnapshot,
    TreeSnapshot,
    tuple[ProtectedInstruction, ...],
    tuple[str, ...],
    bytes,
    bytes,
    AuthenticatedPayload,
    ThresholdBinding,
]:
    return (
        _PLAN_SOURCE_SLOT.__get__(plan, ProtectedExactPlan),
        _PLAN_TARGET_SLOT.__get__(plan, ProtectedExactPlan),
        _PLAN_INSTRUCTIONS_SLOT.__get__(plan, ProtectedExactPlan),
        _PLAN_ROOTS_SLOT.__get__(plan, ProtectedExactPlan),
        _PLAN_CONTEXT_SLOT.__get__(plan, ProtectedExactPlan),
        _PLAN_NONCE_SLOT.__get__(plan, ProtectedExactPlan),
        _PLAN_PAYLOAD_SLOT.__get__(plan, ProtectedExactPlan),
        _PLAN_BINDING_SLOT.__get__(plan, ProtectedExactPlan),
    )


@dataclass(slots=True, init=False)
class _PayloadBuilder:
    data: bytearray

    def __init__(self, data: bytearray) -> None:
        """Store the literal buffer without class-level setter dispatch."""
        _PAYLOAD_BUILDER_DATA_SLOT.__set__(self, data)

    def append(self, literal: bytes) -> PayloadSlice:
        """Append literal bytes.

        Returns:
            Deterministic range of the appended bytes.

        """
        buffer = cast(
            "bytearray", _PAYLOAD_BUILDER_DATA_SLOT.__get__(self, _PayloadBuilder)
        )
        start = _NATIVE_LEN(buffer)
        buffer.extend(literal)
        return _new_payload_slice(offset=start, length=_NATIVE_LEN(literal))


_PAYLOAD_BUILDER_DATA_SLOT = cast(
    "MemberDescriptorType", _PayloadBuilder.__dict__["data"]
)


# Protected authoring can invoke domain/payload callbacks before building each
# record. Pin the original allocation and slot-writing initializers so late
# class hooks cannot change the authenticated key, slices, or instruction map.
_PAYLOAD_SLICE_INIT = cast(
    "Callable[[PayloadSlice, int, int], None]", PayloadSlice.__dict__["__init__"]
)
_PROTECTED_INSTRUCTION_INIT = cast(
    "Callable[..., None]", ProtectedInstruction.__dict__["__init__"]
)
_PROTECTED_METADATA_INIT = cast(
    Callable[
        [
            ProtectedMetadata,
            TreeSnapshot,
            TreeSnapshot,
            tuple[ProtectedInstruction, ...],
            tuple[str, ...],
        ],
        None,
    ],
    ProtectedMetadata.__dict__["__init__"],
)
_PROTECTED_PLAN_INIT = cast(
    "Callable[..., None]", ProtectedExactPlan.__dict__["__init__"]
)
_PAYLOAD_BUILDER_INIT = cast(
    "Callable[[_PayloadBuilder, bytearray], None]",
    _PayloadBuilder.__dict__["__init__"],
)
_PAYLOAD_BUILDER_APPEND = cast(
    "Callable[[_PayloadBuilder, bytes], PayloadSlice]",
    _PayloadBuilder.__dict__["append"],
)


def _new_payload_slice(offset: int, length: int) -> PayloadSlice:
    record = _NATIVE_OBJECT_NEW(PayloadSlice)
    _PAYLOAD_SLICE_INIT(record, offset, length)
    return record


def _new_protected_instruction(
    output_path: str,
    kind: ProtectedInstructionKind,
    expected_sha256: str,
    source_path: str | None = None,
    payload_slice: PayloadSlice | None = None,
    segments: tuple[ProtectedSegment, ...] = (),
) -> ProtectedInstruction:
    record = _NATIVE_OBJECT_NEW(ProtectedInstruction)
    _PROTECTED_INSTRUCTION_INIT(
        record, output_path, kind, expected_sha256, source_path, payload_slice, segments
    )
    return record


def _new_protected_metadata(
    source: TreeSnapshot,
    target: TreeSnapshot,
    instructions: tuple[ProtectedInstruction, ...],
    passthrough_roots: tuple[str, ...] = (),
) -> ProtectedMetadata:
    record = _NATIVE_OBJECT_NEW(ProtectedMetadata)
    _PROTECTED_METADATA_INIT(
        record, source, target, instructions, passthrough_roots
    )
    return record


def _new_protected_exact_plan(
    source: TreeSnapshot,
    target: TreeSnapshot,
    instructions: tuple[ProtectedInstruction, ...],
    passthrough_roots: tuple[str, ...],
    context: bytes,
    nonce: bytes,
    payload: AuthenticatedPayload,
    binding: ThresholdBinding,
) -> ProtectedExactPlan:
    record = _NATIVE_OBJECT_NEW(ProtectedExactPlan)
    _PROTECTED_PLAN_INIT(
        record,
        source,
        target,
        instructions,
        passthrough_roots,
        context,
        nonce,
        payload,
        binding,
    )
    return record


def _new_payload_builder(data: bytearray) -> _PayloadBuilder:
    builder = _NATIVE_OBJECT_NEW(_PayloadBuilder)
    _PAYLOAD_BUILDER_INIT(builder, data)
    return builder


def _payload_builder_bytes(builder: _PayloadBuilder) -> bytes:
    """Snapshot the original stored literal buffer after collection."""
    return _NATIVE_BYTES(
        cast("bytearray", _PAYLOAD_BUILDER_DATA_SLOT.__get__(builder, _PayloadBuilder))
    )


def _frame_bytes(value: bytes) -> bytes:
    return _NATIVE_LEN(value).to_bytes(_FRAME_BYTES, byteorder="big") + value


def _frame_text(value: str) -> bytes:
    return _frame_bytes(value.encode("utf-8"))


def _u64(value: int) -> bytes:
    if value < _ZERO or value >= (1 << 64):
        message = "protected-plan integer exceeds unsigned 64-bit framing"
        raise ProtectedPlanError(message)
    return value.to_bytes(_FRAME_BYTES, byteorder="big")


def _stored_snapshot_files(snapshot: TreeSnapshot) -> tuple[FileRecord, ...]:
    return cast(
        "tuple[FileRecord, ...]", _SNAPSHOT_FILES_SLOT.__get__(snapshot, TreeSnapshot)
    )


def _stored_file_fields(record: FileRecord) -> tuple[str, str, int]:
    return (
        cast("str", _FILE_PATH_SLOT.__get__(record, FileRecord)),
        cast("str", _FILE_SHA256_SLOT.__get__(record, FileRecord)),
        cast("int", _FILE_SIZE_SLOT.__get__(record, FileRecord)),
    )


def _snapshot_bytes(snapshot: TreeSnapshot) -> bytes:
    files = _stored_snapshot_files(snapshot)
    parts = [_u64(_NATIVE_LEN(files))]
    for record in files:
        path, sha256, size = _stored_file_fields(record)
        parts.extend((_frame_text(path), _frame_text(sha256), _u64(size)))
    return b"".join(parts)


def _segment_bytes(segment: ProtectedSegment) -> bytes:
    if _NATIVE_ISINSTANCE(segment, SourceSlice):
        offset = cast("int", _SOURCE_SLICE_OFFSET_SLOT.__get__(segment, SourceSlice))
        length = cast("int", _SOURCE_SLICE_LENGTH_SLOT.__get__(segment, SourceSlice))
        return b"S" + _u64(offset) + _u64(length)
    offset, length = _payload_slice_fields(segment)
    return b"P" + _u64(offset) + _u64(length)


def _instruction_bytes(instruction: ProtectedInstruction) -> bytes:
    (
        output_path,
        kind_value,
        expected_sha256,
        source_value,
        slice_reference,
        instruction_segments,
    ) = _instruction_fields(instruction)
    if kind_value is ProtectedInstructionKind.COPY_SOURCE:
        kind = b"C"
    elif kind_value is ProtectedInstructionKind.PATCH_SOURCE:
        kind = b"P"
    else:
        kind = b"L"
    source_path = (
        b"\x00" if source_value is None else b"\x01" + _frame_text(source_value)
    )
    if slice_reference is None:
        payload_slice = b"\x00"
    else:
        offset, length = _payload_slice_fields(slice_reference)
        payload_slice = b"\x01" + _u64(offset) + _u64(length)
    segments = b"".join(_segment_bytes(item) for item in instruction_segments)
    return b"".join((
        kind,
        _frame_text(output_path),
        _frame_text(expected_sha256),
        source_path,
        payload_slice,
        _u64(_NATIVE_LEN(instruction_segments)),
        segments,
    ))


def _roots_bytes(roots: tuple[str, ...]) -> bytes:
    return b"".join((
        _u64(_NATIVE_LEN(roots)),
        *(_frame_text(root) for root in roots),
    ))


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
    if _NATIVE_TYPE(metadata) is not ProtectedMetadata:
        message = "protected metadata must use the exact ProtectedMetadata type"
        raise ProtectedPlanError(message)
    try:
        _PROTECTED_METADATA_VALIDATOR(metadata)
    except AttributeError as error:
        message = "protected metadata has incomplete native evidence"
        raise ProtectedPlanError(message) from error
    if _NATIVE_TYPE(context) is not _NATIVE_BYTES or not context:
        message = "protected-plan context must be non-empty exact bytes"
        raise ProtectedPlanError(message)
    source, target, instructions, roots = _metadata_fields(metadata)
    instruction_bytes = b"".join(
        _instruction_bytes(instruction) for instruction in instructions
    )
    return b"".join((
        _AAD_MAGIC,
        _frame_bytes(context),
        _frame_bytes(_snapshot_bytes(source)),
        _frame_bytes(_snapshot_bytes(target)),
        _roots_bytes(roots),
        _u64(_NATIVE_LEN(instructions)),
        instruction_bytes,
    ))


def _metadata(
    source: TreeSnapshot,
    target: TreeSnapshot,
    instructions: tuple[ProtectedInstruction, ...],
    *,
    passthrough_roots: tuple[str, ...],
) -> ProtectedMetadata:
    return _new_protected_metadata(
        source=source,
        target=target,
        instructions=instructions,
        passthrough_roots=passthrough_roots,
    )


def _protected_segment(
    segment: ExactSegment,
    builder: _PayloadBuilder,
) -> ProtectedSegment:
    if _NATIVE_TYPE(segment) is SourceSlice:
        return segment
    return _PAYLOAD_BUILDER_APPEND(
        builder, _oracle_literal_data(cast("OracleLiteral", segment))
    )


def _protect_instruction(
    instruction: ExactInstruction,
    builder: _PayloadBuilder,
) -> ProtectedInstruction:
    (
        output_path,
        kind,
        expected_sha256,
        source_path,
        literal,
        segments,
    ) = _exact_instruction_fields(instruction)
    if kind is ExactInstructionKind.COPY_SOURCE:
        return _new_protected_instruction(
            output_path=output_path,
            kind=ProtectedInstructionKind.COPY_SOURCE,
            expected_sha256=expected_sha256,
            source_path=source_path,
        )
    if kind is ExactInstructionKind.PATCH_SOURCE:
        return _new_protected_instruction(
            output_path=output_path,
            kind=ProtectedInstructionKind.PATCH_SOURCE,
            expected_sha256=expected_sha256,
            source_path=source_path,
            segments=_NATIVE_TUPLE(
                _protected_segment(segment, builder) for segment in segments
            ),
        )
    if literal is None:
        message = "literal instruction lost authoring bytes before protection"
        raise ProtectedPlanError(message)
    return _new_protected_instruction(
        output_path=output_path,
        kind=ProtectedInstructionKind.PAYLOAD,
        expected_sha256=expected_sha256,
        payload_slice=_PAYLOAD_BUILDER_APPEND(builder, literal),
    )


def _source_identity_digest(reference_identity: IdentityTree) -> bytes:
    digest = _native_sha256()
    digest.update(b"source-bound-exact-plan-identity-v1\0")
    files = cast(
        "tuple[IdentityFile, ...]",
        _IDENTITY_FILES_SLOT.__get__(reference_identity, IdentityTree),
    )
    digest.update(_u64(_NATIVE_LEN(files)))
    for identity_file in files:
        path = cast("str", _IDENTITY_PATH_SLOT.__get__(identity_file, IdentityFile))
        canonical = cast(
            "bytes", _IDENTITY_CANONICAL_SLOT.__get__(identity_file, IdentityFile)
        )
        digest.update(_frame_text(path))
        digest.update(_frame_bytes(canonical))
    return digest.digest()


def _derive_payload_key(
    reference_identity: IdentityTree,
    *,
    plaintext: bytes,
    aad: bytes,
    context: bytes,
) -> bytes:
    source_material = _source_identity_digest(reference_identity)
    aad_digest = _native_sha256(aad).digest()
    plaintext_digest = _native_sha256(plaintext).digest()
    salt = _native_sha256(
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
    digest = _native_sha256()
    digest.update(_BINDING_CONTEXT_DOMAIN)
    digest.update(_frame_bytes(context))
    digest.update(_frame_bytes(_native_sha256(aad).digest()))
    return digest.digest()


def _validate_protect_inputs(
    plan: object, reference_identity: object, context: object
) -> None:
    if _NATIVE_TYPE(plan) is not ExactAuthoringPlan:
        message = "protected authoring plan must use the exact ExactAuthoringPlan type"
        raise ProtectedPlanError(message)
    try:
        _EXACT_AUTHORING_PLAN_VALIDATOR(plan)
    except (AttributeError, TreeModelError) as error:
        message = "protected authoring plan contains invalid native exact evidence"
        raise ProtectedPlanError(message) from error
    if _NATIVE_TYPE(reference_identity) is not IdentityTree:
        message = "protected reference must use the exact IdentityTree type"
        raise ProtectedPlanError(message)
    if _NATIVE_TYPE(context) is not _NATIVE_BYTES or not context:
        message = "protected authoring context must use non-empty exact bytes"
        raise ProtectedPlanError(message)


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
    _validate_protect_inputs(plan, reference_identity, context)
    source, target, exact_instructions, passthrough_roots = _exact_plan_fields(plan)
    builder = _new_payload_builder(_NATIVE_BYTEARRAY())
    instructions = _NATIVE_TUPLE(
        _protect_instruction(instruction, builder)
        for instruction in exact_instructions
    )
    plaintext = _payload_builder_bytes(builder)
    metadata = _metadata(
        source,
        target,
        instructions,
        passthrough_roots=passthrough_roots,
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
    return _new_protected_exact_plan(
        source=source,
        target=target,
        instructions=instructions,
        passthrough_roots=passthrough_roots,
        context=context,
        nonce=_SINGLE_MESSAGE_NONCE,
        payload=payload,
        binding=binding,
    )


def _payload_slice(plaintext: bytes, reference: PayloadSlice) -> bytes:
    offset, length = _payload_slice_fields(reference)
    end = offset + length
    if end > _NATIVE_LEN(plaintext):
        message = "protected payload slice exceeds authenticated plaintext"
        raise ProtectedPlanError(message)
    return plaintext[offset:end]


def _exact_segment(
    segment: ProtectedSegment,
    plaintext: bytes,
) -> ExactSegment:
    if _NATIVE_ISINSTANCE(segment, SourceSlice):
        return segment
    return _new_oracle_literal(_payload_slice(plaintext, segment))


def _exact_instruction(
    instruction: ProtectedInstruction,
    plaintext: bytes,
) -> ExactInstruction:
    (
        output_path,
        kind,
        expected_sha256,
        source_path,
        payload_slice,
        segments,
    ) = _instruction_fields(instruction)
    if kind is ProtectedInstructionKind.COPY_SOURCE:
        return _new_exact_instruction(
            output_path=output_path,
            kind=ExactInstructionKind.COPY_SOURCE,
            expected_sha256=expected_sha256,
            source_path=source_path,
        )
    if kind is ProtectedInstructionKind.PATCH_SOURCE:
        return _new_exact_instruction(
            output_path=output_path,
            kind=ExactInstructionKind.PATCH_SOURCE,
            expected_sha256=expected_sha256,
            source_path=source_path,
            segments=_NATIVE_TUPLE(
                _exact_segment(segment, plaintext)
                for segment in segments
            ),
        )
    if payload_slice is None:
        message = "protected payload instruction lost its payload range"
        raise ProtectedPlanError(message)
    return _new_exact_instruction(
        output_path=output_path,
        kind=ExactInstructionKind.LITERAL_ORACLE,
        expected_sha256=expected_sha256,
        literal=_payload_slice(plaintext, payload_slice),
    )


def _require_protected_exact_plan(value: object) -> ProtectedExactPlan:
    if _NATIVE_TYPE(value) is not ProtectedExactPlan:
        message = "protected plan must use the exact ProtectedExactPlan type"
        raise ProtectedPlanError(message)
    try:
        _PROTECTED_EXACT_PLAN_VALIDATOR(value)
    except AttributeError as error:
        message = "protected plan has incomplete native envelope evidence"
        raise ProtectedPlanError(message) from error
    return value


def recover_exact_plan(
    plan: ProtectedExactPlan,
    candidate_identity: IdentityTree,
) -> ExactAuthoringPlan:
    """Recover authenticated local literals only after source binding succeeds.

    Returns:
        In-memory exact plan suitable for transactional materialization.

    """
    plan = _require_protected_exact_plan(plan)
    (
        source,
        target,
        protected_instructions,
        passthrough_roots,
        context,
        nonce,
        payload,
        binding,
    ) = _plan_fields(plan)
    metadata = _metadata(
        source,
        target,
        protected_instructions,
        passthrough_roots=passthrough_roots,
    )
    aad = protected_plan_aad(metadata, context=context)
    key = recover_secret(binding, candidate_identity)
    plaintext = chacha20_poly1305_decrypt(key, nonce, payload, aad=aad)
    instructions = _NATIVE_TUPLE(
        _exact_instruction(instruction, plaintext)
        for instruction in protected_instructions
    )
    return _new_exact_plan(
        source=source,
        target=target,
        instructions=instructions,
        passthrough_roots=passthrough_roots,
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
    plan = _require_protected_exact_plan(plan)
    source, _, _, passthrough_roots, _, _, _, _ = _plan_fields(plan)
    if snapshot_tree_excluding(source_root, passthrough_roots) != source:
        message = "source tree does not match protected exact source snapshot"
        raise ProtectedPlanError(message)
    exact = recover_exact_plan(plan, candidate_identity)
    materialize_exact_plan(source_root, exact, output_root)
