# File:
#   - test_ticket_admission_telemetry_lineage_trust_manifest.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry_lineage_trust_manifest.py
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
#   - Secret-free lineage trust manifest and resolution regressions.
# - Must-Not:
#   - Require CUDA, persist secrets, load providers, or modify admission policy.
# - Allows:
#   - Inputs: synthetic manifests, paths, secrets, and lineage items.
#   - Outputs: canonical, bounded, resolution, rotation, and failure assertions.
#   - Side effects: temporary-directory file creation only.
# - Split-When:
#   - Split when concrete signature algorithms, PKI, or asynchronous providers
#     gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact trust-manifest behavior.
# - Summary:
#   - Canonical secret-free trust manifest regressions.
# - Description:
#   - Proves metadata persistence and explicit secret resolution fail closed.
# - Usage:
#   - Runs without accelerator hardware or external key services.
# - Defaults:
#   - Uses two deterministic key references and caller-owned secrets.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
#
# Large file:
#   - false
#

"""Canonical secret-free telemetry lineage trust manifest tests."""

from __future__ import annotations

from dataclasses import replace
from json import dumps
from json import loads
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission_telemetry_lineage import (
        TicketAdmissionTelemetryLineageAttestation,
    )
    from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
        TicketAdmissionTelemetryLineageTrustManifest,
    )
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator.ticket_admission import TicketAdmissionRequest
from accelerator.ticket_admission import TicketRouteCandidate
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import plan_ticket_submissions_with_report
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionAttemptTelemetry,
)
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionFailureTelemetry,
)
from accelerator.ticket_admission_telemetry import TicketAdmissionTelemetry
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageClaim,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageItem,
)
from accelerator.ticket_admission_telemetry_lineage import (
    create_ticket_admission_telemetry_lineage_attestation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    ticket_admission_telemetry_lineage_attestation_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    TicketAdmissionTelemetryLineageTrustError,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    compare_ticket_admission_telemetry_lineage_with_trust,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    verify_ticket_admission_telemetry_lineage_with_trust,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    TicketAdmissionTelemetryLineageResolvedSecret,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    TicketAdmissionTelemetryLineageTrustManifestEntry,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    TicketAdmissionTelemetryLineageTrustManifestError,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    build_ticket_admission_telemetry_lineage_trust_manifest,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    decode_ticket_admission_telemetry_lineage_trust_manifest,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    encode_ticket_admission_telemetry_lineage_trust_manifest,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    read_ticket_admission_telemetry_lineage_trust_manifest,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    resolve_ticket_admission_telemetry_lineage_trust_manifest,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    ticket_admission_telemetry_lineage_trust_manifest_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    ticket_admission_telemetry_lineage_trust_manifest_id,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    write_ticket_admission_telemetry_lineage_trust_manifest,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)

MANIFEST_ID = "ticket-admission-telemetry-lineage-trust-manifest-v1"
MANIFEST_PREFIX = f"{MANIFEST_ID}:sha256:"
OLD_KEY_ID = "local.lineage-key.2026-07"
NEW_KEY_ID = "local.lineage-key.2026-08"
OLD_REFERENCE_ID = "vault.lineage-key.2026-07"
NEW_REFERENCE_ID = "vault.lineage-key.2026-08"
UNKNOWN_REFERENCE_ID = "vault.lineage-key.unknown"
OLD_SECRET = b"old-caller-owned-lineage-secret!!"
NEW_SECRET = b"new-caller-owned-lineage-secret!!"
WRONG_SECRET = b"wrong-caller-owned-lineage-key!!"
SECRET_FIELD_NAME = b"secret_key"
RECORDER_ID = "recorder.test"
COMPLETED_STREAM_ID = "completed.main"
FAILED_STREAM_ID = "failed.main"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "lineage-manifest-test-workload-v1"
BENCHMARK_ID = "lineage-manifest-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
LOW_ELAPSED_NS = 70
HIGH_ELAPSED_NS = 90
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_ENTRIES = 2
SCHEMA_VERSION = 1
UNKNOWN_MUTATION = "unknown"
NONCANONICAL_MUTATION = "noncanonical"
OVERSIZED_MUTATION = "oversized"
ENTRY_LIMIT_MUTATION = "entry-limit"


def _report() -> TicketAdmissionReport:
    request = TicketAdmissionRequest(
        backend_id=BACKEND_ID,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        ticket_count=TICKET_COUNT,
        workload_id=WORKLOAD_ID,
    )
    candidate = TicketRouteCandidate(
        backend_id=BACKEND_ID,
        benchmark_id=BENCHMARK_ID,
        candidate_median_ns=CANDIDATE_NS,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        exact_results=True,
        group_size=TICKET_COUNT,
        mode=TicketSubmissionMode.SYNCHRONOUS,
        paired_wins=15,
        reference_median_ns=REFERENCE_NS,
        sample_count=15,
        workload_id=WORKLOAD_ID,
    )
    return plan_ticket_submissions_with_report(
        request,
        candidates=(candidate,),
        fallback_ticket_ns=100,
    )


def _attempts() -> TicketAdmissionAttemptTelemetry:
    return TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=2),
        failed=TicketAdmissionFailureTelemetry(capacity=2),
    )


def _document(
    elapsed_ns: int | None = None,
) -> TicketAdmissionTelemetryDocument:
    attempts = _attempts()
    if elapsed_ns is not None:
        _ = attempts.record_completed(_report(), elapsed_ns=elapsed_ns)
    return capture_ticket_admission_telemetry_document(attempts)


def _claim(
    capture_sequence_id: int,
    key_id: str,
    previous_attestation_fingerprint: str | None = None,
) -> TicketAdmissionTelemetryLineageClaim:
    return TicketAdmissionTelemetryLineageClaim(
        capture_sequence_id=capture_sequence_id,
        completed_stream_id=COMPLETED_STREAM_ID,
        failed_stream_id=FAILED_STREAM_ID,
        key_id=key_id,
        previous_attestation_fingerprint=previous_attestation_fingerprint,
        recorder_id=RECORDER_ID,
    )


def _attestation(
    document: TicketAdmissionTelemetryDocument,
    claim: TicketAdmissionTelemetryLineageClaim,
    secret_key: bytes,
) -> TicketAdmissionTelemetryLineageAttestation:
    return create_ticket_admission_telemetry_lineage_attestation(
        document,
        claim,
        secret_key=secret_key,
    )


def _item(
    document: TicketAdmissionTelemetryDocument,
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> TicketAdmissionTelemetryLineageItem:
    return TicketAdmissionTelemetryLineageItem(
        attestation=attestation,
        document=document,
    )


def _entry(
    key_id: str,
    key_reference_id: str,
    window: tuple[int, int | None],
) -> TicketAdmissionTelemetryLineageTrustManifestEntry:
    first_capture_sequence_id, last_capture_sequence_id = window
    return TicketAdmissionTelemetryLineageTrustManifestEntry(
        first_capture_sequence_id=first_capture_sequence_id,
        key_id=key_id,
        key_reference_id=key_reference_id,
        last_capture_sequence_id=last_capture_sequence_id,
    )


def _secret(
    key_id: str,
    key_reference_id: str,
    secret_key: bytes,
) -> TicketAdmissionTelemetryLineageResolvedSecret:
    return TicketAdmissionTelemetryLineageResolvedSecret(
        key_id=key_id,
        key_reference_id=key_reference_id,
        secret_key=secret_key,
    )


def _rotation_manifest() -> TicketAdmissionTelemetryLineageTrustManifest:
    return build_ticket_admission_telemetry_lineage_trust_manifest(
        (
            _entry(
                NEW_KEY_ID,
                NEW_REFERENCE_ID,
                (SUCCESSOR_SEQUENCE_ID, None),
            ),
            _entry(
                OLD_KEY_ID,
                OLD_REFERENCE_ID,
                (GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID),
            ),
        )
    )


def _rotation_secrets(
    *,
    old_secret: bytes = OLD_SECRET,
) -> tuple[TicketAdmissionTelemetryLineageResolvedSecret, ...]:
    return (
        _secret(NEW_KEY_ID, NEW_REFERENCE_ID, NEW_SECRET),
        _secret(OLD_KEY_ID, OLD_REFERENCE_ID, old_secret),
    )


def _mapping(encoded: bytes) -> dict[str, object]:
    return cast("dict[str, object]", loads(encoded.decode("utf-8")))


def _encoded_mapping(mapping: dict[str, object]) -> bytes:
    text = dumps(
        mapping,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{text}\n".encode()


def test_empty_manifest_round_trip_and_resolution_are_stable() -> None:
    """An empty canonical manifest is valid and resolves to empty trust."""
    manifest = build_ticket_admission_telemetry_lineage_trust_manifest(())
    encoded = encode_ticket_admission_telemetry_lineage_trust_manifest(manifest)
    decoded = decode_ticket_admission_telemetry_lineage_trust_manifest(encoded)
    resolved = resolve_ticket_admission_telemetry_lineage_trust_manifest(
        decoded,
        (),
    )

    assert ticket_admission_telemetry_lineage_trust_manifest_id() == MANIFEST_ID
    assert decoded == manifest
    assert decoded.entries == ()
    assert decoded.schema_version == SCHEMA_VERSION
    assert resolved.trust.key_count == 0
    assert resolved.manifest_fingerprint.startswith(MANIFEST_PREFIX)
    assert resolved.manifest_fingerprint == (
        ticket_admission_telemetry_lineage_trust_manifest_fingerprint(manifest)
    )


def test_manifest_entries_are_sorted_and_secret_free() -> None:
    """Canonical metadata ordering never stores key material."""
    manifest = _rotation_manifest()
    encoded = encode_ticket_admission_telemetry_lineage_trust_manifest(manifest)

    assert tuple(entry.key_id for entry in manifest.entries) == (
        OLD_KEY_ID,
        NEW_KEY_ID,
    )
    assert OLD_SECRET not in encoded
    assert NEW_SECRET not in encoded
    assert SECRET_FIELD_NAME not in encoded
    assert SECRET_FIELD_NAME not in repr(manifest).encode("utf-8")


def test_manifest_canonical_round_trip_is_byte_stable() -> None:
    """Sorted compact JSON decodes and re-encodes byte-for-byte."""
    manifest = _rotation_manifest()
    encoded = encode_ticket_admission_telemetry_lineage_trust_manifest(manifest)

    decoded = decode_ticket_admission_telemetry_lineage_trust_manifest(encoded)

    assert decoded == manifest
    assert (
        encode_ticket_admission_telemetry_lineage_trust_manifest(decoded)
        == encoded
    )


def test_explicit_write_and_read_preserve_canonical_manifest(
    tmp_path: Path,
) -> None:
    """Explicit atomic storage preserves exact canonical metadata bytes."""
    path = tmp_path / "lineage-trust.json"
    manifest = _rotation_manifest()
    encoded = encode_ticket_admission_telemetry_lineage_trust_manifest(manifest)

    write_ticket_admission_telemetry_lineage_trust_manifest(path, manifest)
    restored = read_ticket_admission_telemetry_lineage_trust_manifest(path)

    assert path.read_bytes() == encoded
    assert restored == manifest
    assert tuple(tmp_path.glob(".*.tmp")) == ()


@pytest.mark.parametrize(
    ("entries", "max_entries", "message"),
    [
        (
            cast(
                "tuple[TicketAdmissionTelemetryLineageTrustManifestEntry, ...]",
                cast("object", []),
            ),
            1,
            "entries must use the exact immutable tuple type",
        ),
        ((), True, "entry limit must be a positive integer"),
        (
            (
                _entry(OLD_KEY_ID, OLD_REFERENCE_ID, (0, None)),
                _entry(NEW_KEY_ID, NEW_REFERENCE_ID, (1, None)),
            ),
            1,
            "entry count exceeds configured limit",
        ),
    ],
)
def test_invalid_build_container_or_limit_fails_closed(
    entries: tuple[TicketAdmissionTelemetryLineageTrustManifestEntry, ...],
    max_entries: int,
    message: str,
) -> None:
    """Manifest construction requires an exact bounded immutable tuple."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match=message,
    ):
        _ = build_ticket_admission_telemetry_lineage_trust_manifest(
            entries,
            max_entries=max_entries,
        )


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (
            (
                _entry(OLD_KEY_ID, OLD_REFERENCE_ID, (0, None)),
                _entry(OLD_KEY_ID, NEW_REFERENCE_ID, (1, None)),
            ),
            "duplicate key identity",
        ),
        (
            (
                _entry(OLD_KEY_ID, OLD_REFERENCE_ID, (0, None)),
                _entry(NEW_KEY_ID, OLD_REFERENCE_ID, (1, None)),
            ),
            "duplicate key reference identity",
        ),
    ],
)
def test_duplicate_manifest_identity_fails_closed(
    entries: tuple[TicketAdmissionTelemetryLineageTrustManifestEntry, ...],
    message: str,
) -> None:
    """Key and reference identities remain one-to-one in a manifest."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match=message,
    ):
        _ = build_ticket_admission_telemetry_lineage_trust_manifest(entries)


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (
            _entry("bad key", OLD_REFERENCE_ID, (0, None)),
            "key identity must use canonical ASCII identity form",
        ),
        (
            _entry(OLD_KEY_ID, "bad reference", (0, None)),
            "key reference identity must use canonical ASCII identity form",
        ),
        (
            _entry(OLD_KEY_ID, OLD_REFERENCE_ID, (True, None)),
            "first capture sequence identity must be a nonnegative integer",
        ),
        (
            _entry(OLD_KEY_ID, OLD_REFERENCE_ID, (2, 1)),
            "last capture sequence precedes first capture sequence",
        ),
    ],
)
def test_invalid_manifest_entry_fails_closed(
    entry: TicketAdmissionTelemetryLineageTrustManifestEntry,
    message: str,
) -> None:
    """Malformed identities and capture windows never enter a manifest."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match=message,
    ):
        _ = build_ticket_admission_telemetry_lineage_trust_manifest((entry,))


def test_duplicate_encoded_key_fails_closed() -> None:
    """Duplicate JSON keys cannot alter canonical trust metadata."""
    encoded = encode_ticket_admission_telemetry_lineage_trust_manifest(
        _rotation_manifest()
    )
    duplicate = encoded.replace(
        b'{"entries":',
        b'{"entries":[],"entries":',
        1,
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match="duplicate JSON key",
    ):
        _ = decode_ticket_admission_telemetry_lineage_trust_manifest(duplicate)


@pytest.mark.parametrize(
    "mutation",
    [
        UNKNOWN_MUTATION,
        NONCANONICAL_MUTATION,
        OVERSIZED_MUTATION,
        ENTRY_LIMIT_MUTATION,
    ],
)
def test_noncanonical_or_bounded_decode_input_fails_closed(
    mutation: str,
) -> None:
    """Unknown, reformatted, and over-limit manifests remain untrusted."""
    encoded = encode_ticket_admission_telemetry_lineage_trust_manifest(
        _rotation_manifest()
    )
    mapping = _mapping(encoded)
    max_bytes = len(encoded)
    max_entries = TWO_ENTRIES
    if mutation == UNKNOWN_MUTATION:
        mapping["unknown"] = 1
        data = _encoded_mapping(mapping)
        max_bytes = len(data)
        match = "keys are unsupported"
    elif mutation == NONCANONICAL_MUTATION:
        data = dumps(mapping, indent=2, sort_keys=True).encode("utf-8")
        max_bytes = len(data)
        match = "manifest bytes are not canonical"
    elif mutation == OVERSIZED_MUTATION:
        data = encoded
        max_bytes = len(encoded) - 1
        match = "exceeds configured byte limit"
    else:
        data = encoded
        max_entries = 1
        match = "entry count exceeds configured limit"

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match=match,
    ):
        _ = decode_ticket_admission_telemetry_lineage_trust_manifest(
            data,
            max_bytes=max_bytes,
            max_entries=max_entries,
        )


def test_resolution_builds_manifest_bound_rotation_trust() -> None:
    """Exact secret coverage resolves a usable rotation-aware trust set."""
    manifest = _rotation_manifest()
    resolved = resolve_ticket_admission_telemetry_lineage_trust_manifest(
        manifest,
        _rotation_secrets(),
    )

    assert resolved.manifest_fingerprint == (
        ticket_admission_telemetry_lineage_trust_manifest_fingerprint(manifest)
    )
    assert resolved.trust.key_count == TWO_ENTRIES
    assert tuple(key.key_id for key in resolved.trust.keys) == (
        OLD_KEY_ID,
        NEW_KEY_ID,
    )
    rendered = repr(resolved).encode("utf-8")
    assert OLD_SECRET not in rendered
    assert NEW_SECRET not in rendered
    assert SECRET_FIELD_NAME not in rendered


def test_resolved_rotation_verifies_direct_successor_across_keys() -> None:
    """Manifest-resolved keys preserve direct lineage across rotation."""
    first_document = _document(LOW_ELAPSED_NS)
    first_attestation = _attestation(
        first_document,
        _claim(GENESIS_SEQUENCE_ID, OLD_KEY_ID),
        OLD_SECRET,
    )
    first_fingerprint = (
        ticket_admission_telemetry_lineage_attestation_fingerprint(
            first_attestation
        )
    )
    second_document = _document(HIGH_ELAPSED_NS)
    second_attestation = _attestation(
        second_document,
        _claim(
            SUCCESSOR_SEQUENCE_ID,
            NEW_KEY_ID,
            first_fingerprint,
        ),
        NEW_SECRET,
    )
    resolved = resolve_ticket_admission_telemetry_lineage_trust_manifest(
        _rotation_manifest(),
        _rotation_secrets(),
    )

    comparison = compare_ticket_admission_telemetry_lineage_with_trust(
        _item(first_document, first_attestation),
        _item(second_document, second_attestation),
        resolved.trust,
    )

    assert comparison.common_recorder_lineage
    assert comparison.direct_chain_link
    assert comparison.first.key_id == OLD_KEY_ID
    assert comparison.second.key_id == NEW_KEY_ID


@pytest.mark.parametrize(
    ("secrets", "message"),
    [
        (
            (_secret(OLD_KEY_ID, OLD_REFERENCE_ID, OLD_SECRET),),
            "coverage is incomplete or excessive",
        ),
        (
            (
                *_rotation_secrets(),
                _secret(
                    "local.lineage-key.extra",
                    UNKNOWN_REFERENCE_ID,
                    WRONG_SECRET,
                ),
            ),
            "coverage is incomplete or excessive",
        ),
    ],
)
def test_missing_or_extra_resolution_fails_closed(
    secrets: tuple[TicketAdmissionTelemetryLineageResolvedSecret, ...],
    message: str,
) -> None:
    """Resolution coverage must match manifest entries exactly."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match=message,
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_manifest(
            _rotation_manifest(),
            secrets,
        )


def test_mismatched_reference_resolution_fails_closed() -> None:
    """A key identity cannot resolve through a different opaque reference."""
    secrets = (
        _secret(OLD_KEY_ID, UNKNOWN_REFERENCE_ID, OLD_SECRET),
        _secret(NEW_KEY_ID, NEW_REFERENCE_ID, NEW_SECRET),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match="resolved key reference does not match manifest",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_manifest(
            _rotation_manifest(),
            secrets,
        )


@pytest.mark.parametrize(
    ("secrets", "message"),
    [
        (
            (
                _secret(OLD_KEY_ID, OLD_REFERENCE_ID, OLD_SECRET),
                _secret(OLD_KEY_ID, NEW_REFERENCE_ID, NEW_SECRET),
            ),
            "duplicate resolved key identity",
        ),
        (
            (
                _secret(OLD_KEY_ID, OLD_REFERENCE_ID, OLD_SECRET),
                _secret(NEW_KEY_ID, OLD_REFERENCE_ID, NEW_SECRET),
            ),
            "duplicate resolved key reference identity",
        ),
    ],
)
def test_duplicate_resolution_identity_fails_closed(
    secrets: tuple[TicketAdmissionTelemetryLineageResolvedSecret, ...],
    message: str,
) -> None:
    """Resolved key and reference identities remain one-to-one."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match=message,
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_manifest(
            _rotation_manifest(),
            secrets,
        )


def test_wrong_resolved_secret_fails_on_attestation_verification() -> None:
    """Opaque resolution does not claim cryptographic secret correctness."""
    resolved = resolve_ticket_admission_telemetry_lineage_trust_manifest(
        _rotation_manifest(),
        _rotation_secrets(old_secret=WRONG_SECRET),
    )
    document = _document()
    attestation = _attestation(
        document,
        _claim(GENESIS_SEQUENCE_ID, OLD_KEY_ID),
        OLD_SECRET,
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustError,
        match="authentication failed",
    ):
        _ = verify_ticket_admission_telemetry_lineage_with_trust(
            _item(document, attestation),
            resolved.trust,
        )


@pytest.mark.parametrize(
    ("manifest", "message"),
    [
        (
            replace(_rotation_manifest(), manifest_id="unsupported"),
            "manifest identity is unsupported",
        ),
        (
            replace(_rotation_manifest(), schema_version=2),
            "manifest schema is unsupported",
        ),
        (
            replace(
                _rotation_manifest(),
                entries=tuple(reversed(_rotation_manifest().entries)),
            ),
            "manifest entries must be uniquely ordered by key",
        ),
    ],
)
def test_tampered_manifest_metadata_fails_closed(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
    message: str,
) -> None:
    """Manifest identity, schema, and canonical ordering are revalidated."""
    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match=message,
    ):
        _ = encode_ticket_admission_telemetry_lineage_trust_manifest(manifest)


def test_resolution_tuple_type_is_exact() -> None:
    """Secret resolution requires an immutable tuple, not a mutable list."""
    secrets = cast(
        "tuple[TicketAdmissionTelemetryLineageResolvedSecret, ...]",
        cast("object", list(_rotation_secrets())),
    )

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match="resolved secrets must use the exact immutable tuple type",
    ):
        _ = resolve_ticket_admission_telemetry_lineage_trust_manifest(
            _rotation_manifest(),
            secrets,
        )


def test_explicit_read_rejects_missing_path(tmp_path: Path) -> None:
    """Manifest loading uses only the explicit caller path."""
    path = tmp_path / "missing-lineage-trust.json"

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match="cannot read trust manifest",
    ):
        _ = read_ticket_admission_telemetry_lineage_trust_manifest(path)


def test_path_type_is_exact() -> None:
    """Storage APIs reject string paths without implicit resolution."""
    path = cast("Path", cast("object", "lineage-trust.json"))

    with pytest.raises(
        TicketAdmissionTelemetryLineageTrustManifestError,
        match=r"path must be a pathlib Path",
    ):
        write_ticket_admission_telemetry_lineage_trust_manifest(
            path,
            _rotation_manifest(),
        )
