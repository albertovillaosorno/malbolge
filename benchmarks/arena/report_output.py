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
#   - Checked one-record JSON publication through operator stdout.
# - Must-Not:
#   - Assert rollback of already-emitted output or authenticate measurements.
# - Allows:
#   - Inputs: complete report object and explicit text-record output stream.
#   - Outputs: one newline-terminated JSON record or typed output failure.
#   - Side effects: one text write followed by mandatory text flush.
# - Split-When:
#   - A persistent streaming transport needs framing and atomicity semantics.
# - Merge-When:
#   - The top-level CLI owns complete output publication contracts.
# - Summary:
#   - Rejects short or fabricated write counts and flush failures.
# - Description:
#   - Makes operator command success depend on observed output completion.
# - Usage:
#   - Called by both arena CLIs after complete preflight and analysis.
# - Defaults:
#   - No stdout completion is claimed when the stream fails.
#

"""Checked arena JSON report stdout publication, without rollback claims."""

from __future__ import annotations

import json
from typing import Any, Never, Protocol

# Publication receipts must use native length and Unicode scanner semantics.
_NATIVE_TYPE = type
_NATIVE_GETATTR = getattr
_NATIVE_LEN = len
_NATIVE_ANY = any
_NATIVE_SET = set
_NATIVE_ID = id
_NATIVE_ORD = ord

# Retain a bound stdlib iterator before a runtime provider can replace the
# public JSONEncoder class or either encoding method. The reported record
# must agree byte-for-byte with this independently invoked canonical path.
_CANONICAL_JSON_CHUNKS = json.JSONEncoder(
    sort_keys=True, indent=2, allow_nan=False
).iterencode
# Both JSONEncoder's C and Python iterators consult the same module-global
# ASCII string escaper. Preserve its native provider to prevent a shared
# runtime substitution from making three agreeing but forged JSON records.
_CANONICAL_ASCII_ESCAPER = json.encoder.encode_basestring_ascii
# The private runtime factories are not exported by stdlib typing stubs.
_C_FACTORY_NAME = "c_make_encoder"
_PY_FACTORY_NAME = "_make_iterencode"
# Each iterencode path also resolves its own mutable module factory. A joint
# factory substitution can otherwise make both encoder paths forge the same
# value without replacing the string escaper.
_CANONICAL_C_ENCODER_FACTORY = _NATIVE_GETATTR(json.encoder, _C_FACTORY_NAME)
_CANONICAL_PY_ITERATOR_FACTORY = _NATIVE_GETATTR(json.encoder, _PY_FACTORY_NAME)


class TextReportStream(Protocol):
    """Minimal text-stream contract accepted by the arena operator."""

    def write(self, record: str, /) -> int:
        """Write text and return the exact number of accepted characters."""
        ...

    def flush(self) -> None:
        """Flush the text record or fail."""
        ...


class ReportOutputError(ValueError):
    """Operator output did not confirm a complete flushed JSON record."""


def _fail(message: str) -> Never:
    raise ReportOutputError(message)


def _flush_complete(stream: TextReportStream) -> None:
    """Require successful, canonical text-stream flush completion.

    Raises:
        ReportOutputError: Flush raised or returned a non-void result.

    """
    try:
        flushed = stream.flush()
    except Exception as error:
        # A stream can raise any ordinary exception; do not format its hooks.
        message = "arena report stdout flush failed"
        raise ReportOutputError(message) from error
    if flushed is not None:
        _fail("arena report stdout flush returned noncanonical completion")


def _native_scalar_text(value: object) -> bool:
    """Accept native Unicode strings without unpaired UTF-16 surrogates.

    Returns:
        Whether this is a complete Unicode scalar-value sequence.

    """
    return _NATIVE_TYPE(value) is str and not _NATIVE_ANY(
        0xD800 <= _NATIVE_ORD(character) <= 0xDFFF for character in value
    )


def _admit_native_json(report: object) -> None:
    """Require a native report object and reject caller-owned JSON subclasses.

    Exact native containers avoid user-overridden iteration and comparison.
    Already visited objects are skipped to terminate cyclic-graph preflight;
    json.dumps still detects and rejects actual cycles.

    Raises:
        TypeError: A value or mapping key is not an exact JSON-native type.

    """
    if _NATIVE_TYPE(report) is not dict:
        message = "arena report requires an exact native JSON object root"
        raise TypeError(message)
    pending: list[object] = [report]
    seen: set[int] = _NATIVE_SET()
    while pending:
        value = pending.pop()
        kind = _NATIVE_TYPE(value)
        # Type identity cannot dispatch caller-owned metaclass equality.
        if kind is dict or kind is list or kind is tuple:
            identity = _NATIVE_ID(value)
            if identity in seen:
                continue
            seen.add(identity)
        if _NATIVE_TYPE(value) is dict:
            for key, child in value.items():
                if not _native_scalar_text(key):
                    message = "arena report requires native Unicode JSON keys"
                    raise TypeError(message)
                pending.append(child)
        elif _NATIVE_TYPE(value) is list or _NATIVE_TYPE(value) is tuple:
            pending.extend(value)
        elif kind is str:
            if not _native_scalar_text(value):
                message = "arena report requires Unicode scalar string values"
                raise TypeError(message)
        elif value is None or kind is int or kind is float or kind is bool:
            continue
        else:
            message = "arena report requires native JSON values and containers"
            raise TypeError(message)


def _require_source_json_providers() -> None:
    """Reject any replaced JSON encoding primitive before report publication.

    Raises:
        ValueError: A canonical provider no longer matches its native source.

    """
    if (
        json.encoder.encode_basestring_ascii is not _CANONICAL_ASCII_ESCAPER
        or _NATIVE_GETATTR(json.encoder, _C_FACTORY_NAME)
        is not _CANONICAL_C_ENCODER_FACTORY
        or _NATIVE_GETATTR(json.encoder, _PY_FACTORY_NAME)
        is not _CANONICAL_PY_ITERATOR_FACTORY
    ):
        message = "arena report JSON source encoder provider changed"
        raise ValueError(message)


def _serialize_canonical_report(report: dict[str, Any]) -> str:
    """Corroborate canonical JSON and providers throughout serialization.

    Returns:
        Exact report text; no trailing record delimiter.

    """
    # Fully render strict JSON before touching stdout: even nested nonfinite
    # costs must not produce an invalid but apparently successful report.
    _admit_native_json(report)
    _require_source_json_providers()
    # Capture the report before invoking the replaceable public serializer.
    # It could mutate an otherwise native dict/list graph in place; if we
    # rendered source JSON afterward, all encoders could agree on the forged
    # post-mutation contents instead of the caller's original report.
    independent = "".join(_CANONICAL_JSON_CHUNKS(report))
    _require_source_json_providers()
    serialized = json.dumps(report, sort_keys=True, indent=2, allow_nan=False)
    # The replaceable writer can swap shared native iterator factories
    # or the ASCII escaper *during* its own call. Reattest before asking
    # later encoders to corroborate its result.
    _require_source_json_providers()
    if _NATIVE_TYPE(serialized) is not str:
        message = "arena report JSON encoder returned nonnative text"
        raise TypeError(message)
    # An exact string alone is not evidence that a serializer returned
    # this report: independently invoke the canonical encoder contract
    # before publishing even one byte to the output stream.
    canonical = json.JSONEncoder(
        sort_keys=True, indent=2, allow_nan=False
    ).encode(report)
    _require_source_json_providers()
    if _NATIVE_TYPE(canonical) is not str or serialized != canonical:
        message = "arena report JSON encoder returned a noncanonical record"
        raise ValueError(message)
    # json.dumps and json.JSONEncoder normally share a single replaceable
    # class. Agreement between both is not independent when that class is
    # substituted or its encoder methods are modified after module import.
    if _NATIVE_TYPE(independent) is not str or serialized != independent:
        message = "arena report JSON differs from canonical source encoding"
        raise ValueError(message)
    return serialized


def publish(report: dict[str, Any], stream: TextReportStream) -> None:
    """Write one complete JSON record with strict stream admission.

    Raises:
        ReportOutputError: The writer or flush did not complete the record.

    """
    try:
        record = _serialize_canonical_report(report) + "\n"
    except Exception as error:
        # A serializer dependency may fail unexpectedly; never format hooks
        # on a foreign failure or accept forged text before touching stdout.
        message = "arena report JSON serialization failed"
        raise ReportOutputError(message) from error
    try:
        written = stream.write(record)
    except Exception as error:
        # Preserve the original exception without invoking its __str__ hook.
        message = "arena report stdout write failed"
        raise ReportOutputError(message) from error
    if _NATIVE_TYPE(written) is not int or written != _NATIVE_LEN(record):
        _fail("arena report stdout write did not accept exact text length")
    _flush_complete(stream)
