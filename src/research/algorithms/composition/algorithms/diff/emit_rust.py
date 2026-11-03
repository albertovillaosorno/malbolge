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

import io
import os
from pathlib import Path
from secrets import token_hex
from stat import S_ISDIR
from stat import S_ISLNK
from stat import S_ISREG
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff.exact import ExactTreeError
from algorithms.diff.exact import read_exact_regular_file
from algorithms.diff.protected import ProtectedExactPlan
from algorithms.diff.protected import ProtectedMetadata
from algorithms.diff.protected import protected_plan_aad

if TYPE_CHECKING:
    from typing import IO

    from algorithms.diff.source_binding import ThresholdBinding

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
_NATIVE_STR_TYPE = str
_NATIVE_INT_TYPE = int
_NATIVE_BOOL_TYPE = bool
_NATIVE_LEN = len
_NATIVE_RANGE = range
_NATIVE_ORD = ord
_NATIVE_PATH_TYPE = _NATIVE_TYPE(Path())
# Guard output classification as well as runtime-template resolution against
# mutable process-global hooks installed after the emitter was imported.
_NATIVE_OS_LSTAT = os.lstat
_NATIVE_OS_FSENCODE = os.fsencode
_NATIVE_PATH_STRING = Path.__str__
_NATIVE_IS_JUNCTION = _NATIVE_PATH_TYPE.is_junction
_NATIVE_RESOLVE = _NATIVE_PATH_TYPE.resolve


def _native_path_lstat(path: Path) -> os.stat_result:
    return _NATIVE_OS_LSTAT(_NATIVE_PATH_STRING(path))


_NATIVE_PATH_LSTAT = _native_path_lstat
_NATIVE_IO_OPEN = io.open


def _native_template_read(path: Path) -> str:
    with _NATIVE_IO_OPEN(
        _NATIVE_PATH_STRING(path), encoding="utf-8"
    ) as stream:
        return stream.read()


_NATIVE_TEMPLATE_READ = _native_template_read


class RustEmissionError(ValueError):
    """Raised when protected metadata cannot be emitted deterministically."""


def _u64(value: int) -> bytes:
    if value < 0 or value >= (1 << 64):
        message = "Rust transform integer exceeds unsigned 64-bit framing"
        raise RustEmissionError(message)
    return value.to_bytes(8, byteorder="big")


def _frame(value: bytes) -> bytes:
    return _u64(_NATIVE_LEN(value)) + value


def _binding_bytes(binding: ThresholdBinding) -> bytes:
    parts = [
        _frame(binding.context),
        _u64(binding.threshold),
        _u64(binding.minimum_anchor_files),
        _u64(binding.secret_length),
        _frame(binding.secret_commitment),
        _u64(binding.anchor_policy.window_bytes),
        _u64(binding.anchor_policy.selection_modulus),
        _u64(_NATIVE_LEN(binding.shares)),
    ]
    for share in binding.shares:
        parts.extend((
            _frame(share.source_path.encode("utf-8")),
            _frame(share.anchor_digest),
            _u64(share.x),
            _frame(share.masked_share),
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
        raise RustEmissionError(message)
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
    metadata = ProtectedMetadata(
        source=plan.source,
        target=plan.target,
        instructions=plan.instructions,
        passthrough_roots=plan.passthrough_roots,
    )
    aad = protected_plan_aad(metadata, context=plan.context)
    return "\n".join((
        _BEGIN,
        f"const PROFILE: &str = {_rust_string(profile)};",
        _hex_constant("AAD_HEX", aad),
        _hex_constant("BINDING_HEX", _binding_bytes(plan.binding)),
        _hex_constant("NONCE_HEX", plan.nonce),
        _hex_constant("CIPHERTEXT_HEX", plan.payload.ciphertext),
        _hex_constant("TAG_HEX", plan.payload.tag),
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
    except (OSError, UnicodeError) as error:
        reason = _safe_emission_error_detail(error)
        message = f"Rust runtime template read failed: {reason}"
        raise RustEmissionError(message) from error


def _validate_emission_inputs(
    plan: object, profile: object, output_path: object
) -> None:
    if _NATIVE_TYPE(plan) is not ProtectedExactPlan:
        message = (
            "Rust emission plan must use the exact ProtectedExactPlan type"
        )
        raise RustEmissionError(message)
    if _NATIVE_TYPE(profile) is not _NATIVE_STR_TYPE or not profile:
        message = "Rust transform profile must use a non-empty exact string"
        raise RustEmissionError(message)
    _validate_output_path(output_path)


def _validate_output_path(output_path: object) -> None:
    # A subclass can override path conversion and publication operations.
    # Reject it before evaluating its string or filesystem representation.
    if _NATIVE_TYPE(output_path) is not _NATIVE_PATH_TYPE:
        message = "Rust transform output path must use exact pathlib Path"
        raise RustEmissionError(message)
    if _NUL in _NATIVE_PATH_STRING(output_path):
        message = "Rust transform output path must not contain NUL"
        raise RustEmissionError(message)
    try:
        _ = _NATIVE_OS_FSENCODE(_NATIVE_PATH_STRING(output_path))
    except (UnicodeError, ValueError) as error:
        message = "Rust transform output path is not filesystem-encodable"
        raise RustEmissionError(message) from error


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
        raise RustEmissionError(message)
    body_template = template[module_start:]
    start = body_template.find(_BEGIN)
    end = body_template.find(_END)
    if start < 0 or end < start:
        message = "Rust runtime template lost generated-constant markers"
        raise RustEmissionError(message)
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
    if _NATIVE_TYPE(error) in {
        RustEmissionError,
        OSError,
        PermissionError,
        RuntimeError,
        ValueError,
    }:
        arguments = cast("tuple[object, ...]", error.args)
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
        raise RustEmissionError(message)
    return receipt


def _output_mode(path: Path, description: str) -> int | None:
    try:
        receipt = _NATIVE_PATH_LSTAT(path)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, RuntimeError) as error:
        detail = _safe_emission_error_detail(error)
        message = f"Rust output {description} status failed: {path}: {detail}"
        raise RustEmissionError(message) from error
    return _require_native_output_status(receipt, description).st_mode


def _output_redirects(path: Path, mode: int) -> bool:
    try:
        if S_ISLNK(mode):
            return True
        junction = _NATIVE_IS_JUNCTION(path)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _safe_emission_error_detail(error)
        message = f"Rust output junction status failed: {path}: {detail}"
        raise RustEmissionError(message) from error
    if _NATIVE_TYPE(junction) is not _NATIVE_BOOL_TYPE:
        message = "Rust output junction status requires native boolean"
        raise RustEmissionError(message)
    return junction


def _validate_output_leaf(output_path: Path) -> None:
    mode = _output_mode(output_path, "file")
    if mode is None:
        return
    if _output_redirects(output_path, mode) or not S_ISREG(mode):
        message = (
            f"Rust output path must be a regular non-linked file: {output_path}"
        )
        raise RustEmissionError(message)


def _validate_output_parent(path: Path, mode: int | None) -> None:
    if mode is None:
        return
    if _output_redirects(path, mode):
        message = f"Rust output parent must not be linked: {path}"
        raise RustEmissionError(message)
    if not S_ISDIR(mode):
        message = f"Rust output parent must be a directory: {path}"
        raise RustEmissionError(message)


def _validate_output_parent_chain(parent: Path) -> None:
    candidate = parent
    while True:
        _validate_output_parent(candidate, _output_mode(candidate, "parent"))
        ancestor = candidate.parent
        if ancestor == candidate:
            return
        candidate = ancestor


def _prepare_output_path(output_path: Path) -> Path:
    _validate_output_leaf(output_path)
    _validate_output_parent_chain(output_path.parent)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError, RuntimeError) as error:
        message = (
            "Rust output parent creation failed: "
            f"{output_path.parent}: {_safe_emission_error_detail(error)}"
        )
        raise RustEmissionError(message) from error
    _validate_output_parent_chain(output_path.parent)
    return output_path


def _temporary_output_path(output_path: Path) -> Path:
    return output_path.with_name(f".{output_path.name}.{token_hex(8)}.tmp")


def _cleanup_owned_temporary(path: Path) -> str | None:
    try:
        path.unlink()
    except FileNotFoundError:
        return None
    except (OSError, ValueError, RuntimeError) as error:
        return _safe_emission_error_detail(error)
    return None


def _write_complete_staged_source(stream: IO[str], source: str) -> None:
    written = stream.write(source)
    if (
        _NATIVE_TYPE(written) is not _NATIVE_INT_TYPE
        or written != _NATIVE_LEN(source)
    ):
        message = "Rust staging write reported a short or invalid count"
        raise ValueError(message)


def _claim_and_write_temporary(path: Path, source: str) -> None:
    owned = False
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            owned = True
            _write_complete_staged_source(stream, source)
            stream.flush()
    except OSError, ValueError, RuntimeError:
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
    raise RustEmissionError(message) from error


def _verify_rust_source_bytes(path: Path, expected: bytes, phase: str) -> None:
    """Reattest the physical UTF-8 source before trusting publication.

    Raises:
        RustEmissionError: The staged or published bytes are untrustworthy.

    """
    try:
        actual = read_exact_regular_file(path, f"{phase} Rust source")
    except ExactTreeError as error:
        detail = _safe_emission_error_detail(error)
        message = f"{phase} Rust source verification failed: {detail}"
        raise RustEmissionError(message) from error
    if actual != expected:
        message = f"{phase} Rust source differs from rendered bytes: {path}"
        raise RustEmissionError(message)


def _require_output_not_runtime_template(output_path: Path) -> None:
    """Protect the source template needed for future deterministic emission.

    Raises:
        RustEmissionError: The selected path may overwrite the source template.

    """
    _validate_output_path(output_path)
    try:
        output = _NATIVE_RESOLVE(output_path)
        template = _NATIVE_RESOLVE(_RUNTIME_TEMPLATE)
    except (OSError, ValueError, RuntimeError) as error:
        message = "Rust output path resolution failed"
        raise RustEmissionError(message) from error
    if (
        _NATIVE_TYPE(output) is not _NATIVE_PATH_TYPE
        or _NATIVE_TYPE(template) is not _NATIVE_PATH_TYPE
    ):
        message = "Rust output path resolution requires native Path"
        raise RustEmissionError(message)
    if output == template:
        message = "Rust output must not overwrite its runtime template"
        raise RustEmissionError(message)


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
    except (OSError, ValueError, RuntimeError) as error:
        _raise_publication_error(error)
    expected = source.encode("utf-8")
    try:
        _verify_rust_source_bytes(temporary, expected, "staged")
        _validate_output_leaf(prepared_output)
        _validate_output_parent_chain(prepared_output.parent)
        published = temporary.replace(prepared_output)
        if (
            _NATIVE_TYPE(published) is not _NATIVE_PATH_TYPE
            or published != prepared_output
        ):
            message = "published Rust source returned an invalid rename receipt"
            raise RustEmissionError(message)
        if _output_mode(temporary, "temporary") is not None:
            message = "published Rust source left the temporary file in place"
            raise RustEmissionError(message)
        _verify_rust_source_bytes(prepared_output, expected, "published")
    except RustEmissionError as error:
        cleanup_error = _cleanup_owned_temporary(temporary)
        if cleanup_error is not None:
            detail = _safe_emission_error_detail(error)
            message = f"{detail}; temporary cleanup failed: {cleanup_error}"
            raise RustEmissionError(message) from error
        raise
    except (OSError, ValueError, RuntimeError) as error:
        cleanup_error = _cleanup_owned_temporary(temporary)
        _raise_publication_error(error, cleanup_error=cleanup_error)
