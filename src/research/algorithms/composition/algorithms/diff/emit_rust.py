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
#   - Deterministic std-only Rust emission for protected exact transforms.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Deterministic std-only Rust emission for protected exact transforms."""

from __future__ import annotations

import builtins
import io
import os
import stat
from pathlib import Path, PurePath
from secrets import token_hex
from stat import S_ISDIR, S_ISLNK, S_ISREG
from types import MemberDescriptorType
from typing import TYPE_CHECKING, cast

from algorithms.diff.exact import (
    ExactTreeError,
    read_exact_regular_file,
)
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.model import TreeSnapshot
from algorithms.diff.payload import AuthenticatedPayload
from algorithms.diff.protected import (
    ProtectedExactPlan,
    ProtectedInstruction,
    ProtectedMetadata,
    ProtectedPlanError,
    protected_plan_aad,
)
from algorithms.diff.source_binding import BoundShare, ThresholdBinding

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import IO


_RUNTIME_TEMPLATE = Path(__file__).with_name("rust_runtime.rs")
_DEFAULT_OUTPUT_PATH = Path("generated/main.rs")
_BEGIN = "// BEGIN GENERATED CONSTANTS"
_END = "// END GENERATED CONSTANTS"
_HEX_CHUNK = 64
_NUL = "\x00"
_SURROGATE_START = 0xD800
_SURROGATE_END = 0xDFFF
_PRINTABLE_ASCII_START = 0x20
_PRINTABLE_ASCII_END = 0x7E
_NATIVE_STAT_RESULT = os.stat_result
# Keep emitter input admission independent of late consumer type hooks.
_NATIVE_TYPE = type
# Read the original exception slot without later builtin name substitution.
_NATIVE_ERROR_ARGS_GETATTRIBUTE = BaseException.__getattribute__
# Do not let late builtin exception aliases promote foreign error types.
_NATIVE_EMISSION_ERROR_TYPES = (OSError, PermissionError, RuntimeError, ValueError)
_NATIVE_OS_ERROR = builtins.OSError
_NATIVE_VALUE_ERROR = builtins.ValueError
_NATIVE_RUNTIME_ERROR = builtins.RuntimeError
_NATIVE_UNICODE_ERROR = builtins.UnicodeError
_NATIVE_ATTRIBUTE_ERROR = builtins.AttributeError
_NATIVE_FILE_NOT_FOUND_ERROR = builtins.FileNotFoundError
_NATIVE_FILE_EXISTS_ERROR = builtins.FileExistsError
# Delegated validators must retain their original imported error identity.
_NATIVE_PROTECTED_PLAN_ERROR = ProtectedPlanError
_NATIVE_EXACT_TREE_ERROR = ExactTreeError
_NATIVE_STR_TYPE = str
_NATIVE_INT_TYPE = int
_NATIVE_BOOL_TYPE = bool
_NATIVE_ANY = builtins.any
_NATIVE_REVERSED = builtins.reversed
_NATIVE_LEN = len
_NATIVE_TUPLE = tuple
_NATIVE_RANGE = range
_NATIVE_ORD = ord
_NATIVE_PATH_TYPE = _NATIVE_TYPE(Path())
# Guard output classification as well as runtime-template resolution against
# mutable process-global hooks installed after the emitter was imported.
_NATIVE_OS_LSTAT = os.lstat
_NATIVE_OS_MKDIR = os.mkdir
_NATIVE_OS_REPLACE = os.replace
_NATIVE_OS_UNLINK = os.unlink
_NATIVE_OS_FSENCODE = os.fsencode
_NATIVE_PATH_STR = Path.__str__
_NATIVE_OS_FSPATH = os.fspath
_NATIVE_BYTES_TYPE = builtins.bytes
_NATIVE_ISINSTANCE = builtins.isinstance
_NATIVE_HOST_PARSER = os.path
_NATIVE_HOST_SPLITROOT = os.path.splitroot
_NATIVE_HOST_SPLITDRIVE = os.path.splitdrive
_NATIVE_HOST_JOIN = os.path.join
_NATIVE_HOST_SEP = os.path.sep
_NATIVE_HOST_ALTSEP = os.path.altsep
# A captured Path.__str__ still follows late class descriptor and os.fspath
# hooks. Freeze its full native class dependency chain before domain callbacks.
_PATH_STRING_DEPENDENCIES = (
    # A captured with_name still dispatches through mutable path factories.
    "_from_parsed_parts",
    "_from_parsed_string",
    "__getattribute__",
    "__getattr__",
    "__setattr__",
    "__str__",
    "__fspath__",
    "_str",
    "_raw_paths",
    "_drv",
    "_root",
    "_tail_cached",
    "_raw_path",
    "_tail",
    "drive",
    "root",
    "_parse_path",
    "_format_parsed_parts",
    "parser",
)
_NATIVE_PATH_STRING_HOOKS = tuple(
    (
        path_class,
        tuple(
            (name, path_class.__dict__.get(name)) for name in _PATH_STRING_DEPENDENCIES
        ),
    )
    for path_class in _NATIVE_PATH_TYPE.__mro__
    if issubclass(path_class, PurePath)
)


def _native_path_string(path: Path) -> str:
    """Reject late path formatter substitution before any filesystem access."""
    if (
        os.fspath is not _NATIVE_OS_FSPATH
        or os.path is not _NATIVE_HOST_PARSER
        or os.path.splitroot is not _NATIVE_HOST_SPLITROOT
        or os.path.splitdrive is not _NATIVE_HOST_SPLITDRIVE
        or os.path.join is not _NATIVE_HOST_JOIN
        or os.path.sep is not _NATIVE_HOST_SEP
        or os.path.altsep is not _NATIVE_HOST_ALTSEP
        or builtins.str is not _NATIVE_STR_TYPE
        or builtins.bytes is not _NATIVE_BYTES_TYPE
        or builtins.isinstance is not _NATIVE_ISINSTANCE
        or builtins.len is not _NATIVE_LEN
        or _NATIVE_ANY(
            path_class.__dict__.get(name) is not original
            for path_class, hooks in _NATIVE_PATH_STRING_HOOKS
            for name, original in hooks
        )
    ):
        raise _NATIVE_RUST_EMISSION_ERROR("Rust transform path hooks changed")
    return _NATIVE_PATH_STR(path)


_NATIVE_PATH_STRING = _native_path_string
_NATIVE_PATH_PARENT = cast("Callable[[Path], Path]", Path.parent.fget)
_NATIVE_PATH_NAME = cast("Callable[[Path], str]", Path.name.fget)
_NATIVE_PATH_WITH_NAME = Path.with_name
_NATIVE_IS_JUNCTION = _NATIVE_PATH_TYPE.is_junction
# Path.is_junction dynamically looks up os.path.isjunction at call time.
_NATIVE_OS_PATH_ISJUNCTION = os.path.isjunction
_NATIVE_RESOLVE = _NATIVE_PATH_TYPE.resolve
_NATIVE_OS_REALPATH = os.path.realpath
_NATIVE_OS_READLINK = os.readlink
_NATIVE_OS_GETCWD = os.getcwd
_NATIVE_STAT_ISLNK = stat.S_ISLNK
# Path.resolve delegates to with_segments and native class construction, even
# when the resolver function and string formatter have not been replaced.
_PATH_RESOLUTION_DEPENDENCIES = ("with_segments", "__new__", "__init__")
_NATIVE_PATH_RESOLUTION_HOOKS = tuple(
    (
        path_class,
        tuple(
            (name, path_class.__dict__.get(name))
            for name in _PATH_RESOLUTION_DEPENDENCIES
        ),
    )
    for path_class in _NATIVE_PATH_TYPE.__mro__
    if issubclass(path_class, PurePath)
)


# Capture the native slots while importing the emitter. Late consumer hooks on
# frozen dataclass classes must not rewrite source-bound Rust constants.
def _record_slots(
    record_type: type[object], names: tuple[str, ...]
) -> tuple[MemberDescriptorType, ...]:
    return _NATIVE_TUPLE(
        cast("MemberDescriptorType", record_type.__dict__[name]) for name in names
    )


def _stored_fields(
    record: object,
    record_type: type[object],
    slots: tuple[MemberDescriptorType, ...],
) -> tuple[object, ...]:
    return _NATIVE_TUPLE(
        cast("object", slot.__get__(record, record_type)) for slot in slots
    )


_PLAN_SLOTS = _record_slots(
    ProtectedExactPlan,
    (
        "source",
        "target",
        "instructions",
        "passthrough_roots",
        "context",
        "nonce",
        "payload",
        "binding",
    ),
)
# Reuse the original protected-envelope validator, not a replaceable late
# __post_init__ attribute. Exact native records can bypass their constructor.
_NATIVE_PROTECTED_PLAN_VALIDATOR = cast(
    "Callable[[ProtectedExactPlan], None]",
    ProtectedExactPlan.__dict__["__post_init__"],
)
_PAYLOAD_SLOTS = _record_slots(AuthenticatedPayload, ("ciphertext", "tag"))
_BINDING_SLOTS = _record_slots(
    ThresholdBinding,
    (
        "context",
        "threshold",
        "minimum_anchor_files",
        "secret_length",
        "secret_commitment",
        "anchor_policy",
        "shares",
    ),
)
_ANCHOR_SLOTS = _record_slots(AnchorPolicy, (
    "window_bytes", "selection_modulus",
))
_SHARE_SLOTS = _record_slots(BoundShare, (
    "source_path", "anchor_digest", "x", "masked_share",
))


def _native_path_lstat(path: Path) -> os.stat_result:
    return _NATIVE_OS_LSTAT(_NATIVE_PATH_STRING(path))


_NATIVE_PATH_LSTAT = _native_path_lstat
_NATIVE_IO_OPEN = io.open


def _staged_output_open(path: Path) -> IO[str]:
    """Claim a new stage without calling mutable Path.open methods.

    Returns:
        Exclusive UTF-8 text stream for the new stage.

    """
    return _NATIVE_IO_OPEN(
        _NATIVE_PATH_STRING(path), "x", encoding="utf-8", newline="\n"
    )


def _output_replace(source: Path, destination: Path) -> Path:
    """Publish through the captured host rename, not mutable Path.replace.

    Returns:
        The destination path, after the host operation completes.

    """
    _NATIVE_OS_REPLACE(
        _NATIVE_PATH_STRING(source), _NATIVE_PATH_STRING(destination)
    )
    return destination


def _output_unlink(path: Path) -> None:
    """Remove only the exact staged path using the captured host unlink."""
    _NATIVE_OS_UNLINK(_NATIVE_PATH_STRING(path))


def _output_mkdir(path: Path) -> None:
    """Create parents through captured path and host directory operations."""
    chain: list[str] = []
    current = path
    while True:
        spelling = _NATIVE_PATH_STRING(current)
        chain.append(spelling)
        parent = _NATIVE_PATH_PARENT(current)
        if _NATIVE_PATH_STRING(parent) == spelling:
            break
        current = parent
    for spelling in _NATIVE_REVERSED(chain):
        try:
            _NATIVE_OS_MKDIR(spelling)
        except _NATIVE_FILE_EXISTS_ERROR:
            # The second parent-chain preflight rejects non-directories/links.
            continue


def _native_template_read(path: Path) -> str:
    with _NATIVE_IO_OPEN(
        _NATIVE_PATH_STRING(path), encoding="utf-8"
    ) as stream:
        return stream.read()


_NATIVE_TEMPLATE_READ = _native_template_read


class RustEmissionError(ValueError):
    """Raised when protected metadata cannot be emitted deterministically."""


# Native failure handling must not dispatch a later consumer error alias.
_NATIVE_RUST_EMISSION_ERROR = RustEmissionError


def _u64(value: int) -> bytes:
    if value < 0 or value >= (1 << 64):
        message = "Rust transform integer exceeds unsigned 64-bit framing"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    return value.to_bytes(8, byteorder="big")


def _frame(value: bytes) -> bytes:
    return _u64(_NATIVE_LEN(value)) + value


def _binding_bytes(binding: ThresholdBinding) -> bytes:
    (
        context, threshold, minimum_files, secret_length,
        commitment, policy, shares,
    ) = cast(
        tuple[
            bytes, int, int, int, bytes, AnchorPolicy, tuple[BoundShare, ...]
        ],
        _stored_fields(binding, ThresholdBinding, _BINDING_SLOTS),
    )
    window, modulus = cast(
        "tuple[int, int]", _stored_fields(policy, AnchorPolicy, _ANCHOR_SLOTS)
    )
    parts = [
        _frame(context),
        _u64(threshold),
        _u64(minimum_files),
        _u64(secret_length),
        _frame(commitment),
        _u64(window),
        _u64(modulus),
        _u64(_NATIVE_LEN(shares)),
    ]
    for share in shares:
        path, digest, x, masked = cast(
            "tuple[str, bytes, int, bytes]",
            _stored_fields(share, BoundShare, _SHARE_SLOTS),
        )
        parts.extend((
            _frame(path.encode("utf-8")),
            _frame(digest),
            _u64(x),
            _frame(masked),
        ))
    return b"".join(parts)


def _rust_character(character: str) -> str:
    escapes = {
        "\\": "\\\\",
        '"': '\\"',
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }
    if character in escapes:
        return escapes[character]
    scalar = _NATIVE_ORD(character)
    if _SURROGATE_START <= scalar <= _SURROGATE_END:
        message = "Rust transform profile must contain Unicode scalar values"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    if scalar < _PRINTABLE_ASCII_START or scalar > _PRINTABLE_ASCII_END:
        return f"\\u{{{scalar:x}}}"
    return character


def _rust_string(value: str) -> str:
    return '"' + "".join(_rust_character(char) for char in value) + '"'


def _hex_constant(name: str, data: bytes) -> str:
    encoded = data.hex()
    if not encoded:
        return f'const {name}: &str = "";'
    chunks = [
        encoded[offset : offset + _HEX_CHUNK]
        for offset in _NATIVE_RANGE(0, _NATIVE_LEN(encoded), _HEX_CHUNK)
    ]
    if _NATIVE_LEN(chunks) == 1:
        return f'const {name}: &str = concat!("{chunks[0]}",);'
    lines = [f"const {name}: &str = concat!("]
    lines.extend(f'    "{chunk}",' for chunk in chunks)
    lines.append(");")
    return "\n".join(lines)


def _constants(plan: ProtectedExactPlan, profile: str) -> str:
    (
        source, target, instructions, roots, context, nonce, payload, binding
    ) = cast(
        tuple[
            TreeSnapshot,
            TreeSnapshot,
            tuple[ProtectedInstruction, ...],
            tuple[str, ...],
            bytes,
            bytes,
            AuthenticatedPayload,
            ThresholdBinding,
        ],
        _stored_fields(plan, ProtectedExactPlan, _PLAN_SLOTS),
    )
    metadata = ProtectedMetadata(
        source=source,
        target=target,
        instructions=instructions,
        passthrough_roots=roots,
    )
    aad = protected_plan_aad(metadata, context=context)
    ciphertext, tag = cast(
        "tuple[bytes, bytes]",
        _stored_fields(payload, AuthenticatedPayload, _PAYLOAD_SLOTS),
    )
    return "\n".join((
        _BEGIN,
        f"const PROFILE: &str = {_rust_string(profile)};",
        _hex_constant("AAD_HEX", aad),
        _hex_constant("BINDING_HEX", _binding_bytes(binding)),
        _hex_constant("NONCE_HEX", nonce),
        _hex_constant("CIPHERTEXT_HEX", ciphertext),
        _hex_constant("TAG_HEX", tag),
        _END,
    ))


_GENERATED_HEADER = (
    "// Copyright:\n"
    "//   - Copyright © 2026 Alberto Villa Osorno.\n"
    "// SPDX-License-Identifier:\n"
    "//   - Apache-2.0\n"
    "// Confidential:\n"
    "//   - false\n"
    "// License-File:\n"
    "//   - LICENSE\n"
    "//\n"
    "// Boundary-Contract:\n"
    "// - Owns:\n"
    "//   - One generated exact source-bound transformation.\n"
    "// - Must-Not:\n"
    "//   - Materialize target bytes without admitted source evidence.\n"
    "//   - Be hand-edited; regenerate it through the owning recipe.\n"
    "// - Allows:\n"
    "//   - Inputs: one admitted source tree and output directory.\n"
    "//   - Outputs: one authenticated deterministic target tree.\n"
    "//   - Side effects: transactional target publication.\n"
    "// - Split-When:\n"
    "//   - Split when another transform has a distinct source contract.\n"
    "// - Merge-When:\n"
    "//   - Merge only when source identity and target semantics match.\n"
    "// - Summary:\n"
    "//   - Generated standalone source-bound exact transform.\n"
    "// - Description:\n"
    "//   - Recovers protected target bytes from admitted source evidence.\n"
    "// - Usage:\n"
    "//   - `<transform> <source-root> <output-root>`.\n"
    "// - Defaults:\n"
    "//   - Fails closed before publishing mismatched or partial output.\n"
    "//\n"
    "\n"
)


def _runtime_template_text() -> str:
    try:
        return _NATIVE_TEMPLATE_READ(_RUNTIME_TEMPLATE)
    except (_NATIVE_OS_ERROR, _NATIVE_UNICODE_ERROR) as error:
        reason = _safe_emission_error_detail(error)
        message = f"Rust runtime template read failed: {reason}"
        raise _NATIVE_RUST_EMISSION_ERROR(message) from error


def _validate_emission_inputs(
    plan: object, profile: object, output_path: object
) -> None:
    if _NATIVE_TYPE(plan) is not ProtectedExactPlan:
        message = (
            "Rust emission plan must use the exact ProtectedExactPlan type"
        )
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    if _NATIVE_TYPE(profile) is not _NATIVE_STR_TYPE or not profile:
        message = "Rust transform profile must use a non-empty exact string"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    _validate_output_path(output_path)
    # A slotted native plan can be allocated without running __init__. Check
    # nested binding, metadata and required slots before reading the template.
    try:
        _NATIVE_PROTECTED_PLAN_VALIDATOR(plan)
    except (_NATIVE_PROTECTED_PLAN_ERROR, _NATIVE_ATTRIBUTE_ERROR) as error:
        message = "Rust emission requires a valid native protected plan"
        raise _NATIVE_RUST_EMISSION_ERROR(message) from error


def _validate_output_path(output_path: object) -> None:
    # A subclass can override path conversion and publication operations.
    # Reject it before evaluating its string or filesystem representation.
    if _NATIVE_TYPE(output_path) is not _NATIVE_PATH_TYPE:
        message = "Rust transform output path must use exact pathlib Path"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    if _NUL in _NATIVE_PATH_STRING(output_path):
        message = "Rust transform output path must not contain NUL"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    try:
        _ = _NATIVE_OS_FSENCODE(_NATIVE_PATH_STRING(output_path))
    except (_NATIVE_UNICODE_ERROR, _NATIVE_VALUE_ERROR) as error:
        message = "Rust transform output path is not filesystem-encodable"
        raise _NATIVE_RUST_EMISSION_ERROR(message) from error


def emit_rust_transform(
    plan: ProtectedExactPlan,
    profile: str,
    output_path: Path = _DEFAULT_OUTPUT_PATH,
) -> str:
    """Render one standalone Rust exact-transform source file.

    Returns:
        Deterministic UTF-8 Rust source with protected metadata embedded as hex.

    Raises:
        RustEmissionError: Profile/template state is invalid.

    """
    _validate_emission_inputs(plan, profile, output_path)
    template = _runtime_template_text()
    module_start = template.find("//! ")
    if module_start < 0:
        message = "Rust runtime template lost module summary"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    body_template = template[module_start:]
    start = body_template.find(_BEGIN)
    end = body_template.find(_END)
    if start < 0 or end < start:
        message = "Rust runtime template lost generated-constant markers"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    end += _NATIVE_LEN(_END)
    body = (
        body_template[:start] + _constants(plan, profile) + body_template[end:]
    )
    rendered = _GENERATED_HEADER + body
    return rendered.replace("\r\n", "\n")


def _safe_emission_error_detail(error: Exception) -> str:
    """Render only native failure reasons, without calling foreign string hooks.

    Returns:
        Exact native single-string reason or the exception class name.

    """
    if (
        _NATIVE_TYPE(error) is _NATIVE_RUST_EMISSION_ERROR
        or _NATIVE_TYPE(error) in _NATIVE_EMISSION_ERROR_TYPES
    ):
        # Exact native error classes can acquire late instance accessors.
        # Read the BaseException slot without invoking the mutable getter.
        arguments = cast(
            "tuple[object, ...]",
            _NATIVE_ERROR_ARGS_GETATTRIBUTE(  # ruff: ignore[unnecessary-dunder-call]
                error, "args"
            ),
        )
        if _NATIVE_LEN(arguments) == 1:
            reason = arguments[0]
            if _NATIVE_TYPE(reason) is _NATIVE_STR_TYPE:
                return reason
    return _NATIVE_TYPE(error).__name__


def _require_native_output_status(
    receipt: object, description: str
) -> os.stat_result:
    """Reject foreign output status before trusting its file-mode claims.

    Returns:
        Exact native filesystem status.

    Raises:
        RustEmissionError: The status does not come from the host runtime.

    """
    if _NATIVE_TYPE(receipt) is not _NATIVE_STAT_RESULT:
        message = f"Rust output {description} requires native filesystem status"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    return receipt


def _output_mode(path: Path, description: str) -> int | None:
    try:
        receipt = _NATIVE_PATH_LSTAT(path)
    except _NATIVE_FILE_NOT_FOUND_ERROR:
        return None
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_emission_error_detail(error)
        message = f"Rust output {description} status failed: {path}: {detail}"
        raise _NATIVE_RUST_EMISSION_ERROR(message) from error
    return _require_native_output_status(receipt, description).st_mode


def _output_redirects(path: Path, mode: int) -> bool:
    if os.path.isjunction is not _NATIVE_OS_PATH_ISJUNCTION:
        message = "Rust output junction hooks changed"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    try:
        if S_ISLNK(mode):
            return True
        junction = _NATIVE_IS_JUNCTION(path)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_emission_error_detail(error)
        message = f"Rust output junction status failed: {path}: {detail}"
        raise _NATIVE_RUST_EMISSION_ERROR(message) from error
    if _NATIVE_TYPE(junction) is not _NATIVE_BOOL_TYPE:
        message = "Rust output junction status requires native boolean"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    return junction


def _validate_output_leaf(output_path: Path) -> None:
    mode = _output_mode(output_path, "file")
    if mode is None:
        return
    if _output_redirects(output_path, mode) or not S_ISREG(mode):
        message = (
            f"Rust output path must be a regular non-linked file: {output_path}"
        )
        raise _NATIVE_RUST_EMISSION_ERROR(message)


def _validate_output_parent(path: Path, mode: int | None) -> None:
    if mode is None:
        return
    if _output_redirects(path, mode):
        message = f"Rust output parent must not be linked: {path}"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    if not S_ISDIR(mode):
        message = f"Rust output parent must be a directory: {path}"
        raise _NATIVE_RUST_EMISSION_ERROR(message)


def _validate_output_parent_chain(parent: Path) -> None:
    candidate = parent
    while True:
        _validate_output_parent(candidate, _output_mode(candidate, "parent"))
        ancestor = _NATIVE_PATH_PARENT(candidate)
        if _NATIVE_PATH_STRING(ancestor) == _NATIVE_PATH_STRING(candidate):
            return
        candidate = ancestor


def _prepare_output_path(output_path: Path) -> Path:
    _validate_output_leaf(output_path)
    parent = _NATIVE_PATH_PARENT(output_path)
    _validate_output_parent_chain(parent)
    try:
        _output_mkdir(parent)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        message = (
            "Rust output parent creation failed: "
            f"{parent}: {_safe_emission_error_detail(error)}"
        )
        raise _NATIVE_RUST_EMISSION_ERROR(message) from error
    _validate_output_parent_chain(parent)
    return output_path


def _temporary_output_path(output_path: Path) -> Path:
    # Even the original with_name implementation dynamically resolves class
    # factories, so recheck immediately before and after stage construction.
    _require_native_host_realpath()
    _ = _NATIVE_PATH_STRING(output_path)
    name = f".{_NATIVE_PATH_NAME(output_path)}.{token_hex(8)}.tmp"
    _require_native_host_realpath()
    temporary = _NATIVE_PATH_WITH_NAME(output_path, name)
    _require_native_host_realpath()
    if _NATIVE_TYPE(temporary) is not _NATIVE_PATH_TYPE:
        message = "Rust temporary output requires native Path"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    _ = _NATIVE_PATH_STRING(temporary)
    return temporary


def _cleanup_owned_temporary(path: Path) -> str | None:
    try:
        _output_unlink(path)
    except _NATIVE_FILE_NOT_FOUND_ERROR:
        return None
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        return _safe_emission_error_detail(error)
    return None


def _write_complete_staged_source(stream: IO[str], source: str) -> None:
    written = stream.write(source)
    if (
        _NATIVE_TYPE(written) is not _NATIVE_INT_TYPE
        or written != _NATIVE_LEN(source)
    ):
        message = "Rust staging write reported a short or invalid count"
        raise _NATIVE_VALUE_ERROR(message)


def _claim_and_write_temporary(path: Path, source: str) -> None:
    owned = False
    try:
        with _staged_output_open(path) as stream:
            owned = True
            _write_complete_staged_source(stream, source)
            stream.flush()
    except (_NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR):
        if owned:
            _ = _cleanup_owned_temporary(path)
        raise


def _raise_publication_error(
    error: OSError | ValueError | RuntimeError,
    *,
    cleanup_error: str | None = None,
) -> None:
    detail = _safe_emission_error_detail(error)
    message = f"Rust transform publication failed: {detail}"
    if cleanup_error is not None:
        message = f"{message}; temporary cleanup failed: {cleanup_error}"
    raise _NATIVE_RUST_EMISSION_ERROR(message) from error


def _verify_rust_source_bytes(path: Path, expected: bytes, phase: str) -> None:
    """Reattest the physical UTF-8 source before trusting publication.

    Raises:
        RustEmissionError: The staged or published bytes are untrustworthy.

    """
    try:
        actual = read_exact_regular_file(path, f"{phase} Rust source")
    except _NATIVE_EXACT_TREE_ERROR as error:
        detail = _safe_emission_error_detail(error)
        message = f"{phase} Rust source verification failed: {detail}"
        raise _NATIVE_RUST_EMISSION_ERROR(message) from error
    if actual != expected:
        message = f"{phase} Rust source differs from rendered bytes: {path}"
        raise _NATIVE_RUST_EMISSION_ERROR(message)


def _require_native_host_realpath() -> None:
    """Pin the resolver's host and pathlib dependencies before resolution.

    Raises:
        RustEmissionError: Native path resolution dependencies changed.

    """
    if (
        os.path.realpath is not _NATIVE_OS_REALPATH
        or os.lstat is not _NATIVE_OS_LSTAT
        or os.readlink is not _NATIVE_OS_READLINK
        or os.getcwd is not _NATIVE_OS_GETCWD
        or stat.S_ISLNK is not _NATIVE_STAT_ISLNK
        or os.path is not _NATIVE_HOST_PARSER
        or os.path.splitroot is not _NATIVE_HOST_SPLITROOT
        or os.path.splitdrive is not _NATIVE_HOST_SPLITDRIVE
        or os.path.join is not _NATIVE_HOST_JOIN
        or os.path.sep is not _NATIVE_HOST_SEP
        or os.path.altsep is not _NATIVE_HOST_ALTSEP
        or builtins.str is not _NATIVE_STR_TYPE
        or builtins.bytes is not _NATIVE_BYTES_TYPE
        or builtins.isinstance is not _NATIVE_ISINSTANCE
        or builtins.len is not _NATIVE_LEN
        or _NATIVE_ANY(
            path_class.__dict__.get(name) is not original
            for path_class, hooks in _NATIVE_PATH_RESOLUTION_HOOKS
            for name, original in hooks
        )
    ):
        message = "Rust output path resolution hooks changed"
        raise _NATIVE_RUST_EMISSION_ERROR(message)


def _require_output_not_runtime_template(output_path: Path) -> None:
    """Protect the source template needed for future deterministic emission.

    Raises:
        RustEmissionError: The selected path may overwrite the source template.

    """
    _validate_output_path(output_path)
    _require_native_host_realpath()
    try:
        output = _NATIVE_RESOLVE(output_path)
        template = _NATIVE_RESOLVE(_RUNTIME_TEMPLATE)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        message = "Rust output path resolution failed"
        raise _NATIVE_RUST_EMISSION_ERROR(message) from error
    _require_native_host_realpath()
    if (
        _NATIVE_TYPE(output) is not _NATIVE_PATH_TYPE
        or _NATIVE_TYPE(template) is not _NATIVE_PATH_TYPE
    ):
        message = "Rust output path resolution requires native Path"
        raise _NATIVE_RUST_EMISSION_ERROR(message)
    if _NATIVE_PATH_STRING(output) == _NATIVE_PATH_STRING(template):
        message = "Rust output must not overwrite its runtime template"
        raise _NATIVE_RUST_EMISSION_ERROR(message)


def write_rust_transform(
    plan: ProtectedExactPlan,
    profile: str,
    output_path: Path,
) -> None:
    """Write one generated transform atomically.

    Raises:
        RustEmissionError: Emission or publication validation fails. A late
            mutation after rename may leave an untrusted output file present.

    """
    _require_output_not_runtime_template(output_path)
    source = emit_rust_transform(plan, profile, output_path)
    prepared_output = _prepare_output_path(output_path)
    temporary = _temporary_output_path(prepared_output)
    try:
        _claim_and_write_temporary(temporary, source)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        _raise_publication_error(error)
    expected = source.encode("utf-8")
    try:
        _verify_rust_source_bytes(temporary, expected, "staged")
        _validate_output_leaf(prepared_output)
        _validate_output_parent_chain(_NATIVE_PATH_PARENT(prepared_output))
        published = _output_replace(temporary, prepared_output)
        if (
            _NATIVE_TYPE(published) is not _NATIVE_PATH_TYPE
            or _NATIVE_PATH_STRING(published) != (
                _NATIVE_PATH_STRING(prepared_output)
            )
        ):
            message = "published Rust source returned an invalid rename receipt"
            raise _NATIVE_RUST_EMISSION_ERROR(message)
        if _output_mode(temporary, "temporary") is not None:
            message = "published Rust source left the temporary file in place"
            raise _NATIVE_RUST_EMISSION_ERROR(message)
        _verify_rust_source_bytes(prepared_output, expected, "published")
    except _NATIVE_RUST_EMISSION_ERROR as error:
        cleanup_error = _cleanup_owned_temporary(temporary)
        if cleanup_error is not None:
            detail = _safe_emission_error_detail(error)
            message = f"{detail}; temporary cleanup failed: {cleanup_error}"
            raise _NATIVE_RUST_EMISSION_ERROR(message) from error
        raise
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        cleanup_error = _cleanup_owned_temporary(temporary)
        _raise_publication_error(error, cleanup_error=cleanup_error)
