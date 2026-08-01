# File:
#   - test_ticket_admission_signature_trust_manifest.py
# Path:
#   - tests/optimizer/test_ticket_admission_signature_trust_manifest.py
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
#   - Key-free detached signature trust manifest regressions.
# - Must-Not:
#   - Require CUDA, embed public keys, load providers, claim secure test
#     cryptography, or modify admission policy.
# - Allows:
#   - Inputs: synthetic manifests, paths, resolved keys, and signature items.
#   - Outputs: canonical, bounded, resolution, rotation, and failure assertions.
#   - Side effects: temporary-directory file creation only.
# - Split-When:
#   - Split when async HTTPS transports, credentials, hosted-service APIs,
#     certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact public-key manifest behavior.
# - Summary:
#   - Canonical detached signature trust manifest regressions.
# - Description:
#   - Proves metadata persistence and explicit public-key resolution fail
#     closed.
# - Usage:
#   - Runs without accelerator hardware or external key services.
# - Defaults:
#   - Uses two deterministic insecure digest keys for protocol tests only.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
#
# Large file:
#   - false
#

"""Canonical key-free detached signature trust manifest tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from json import dumps
from json import loads
from typing import TYPE_CHECKING
from typing import cast

import pytest

from accelerator import ticket_admission_telemetry_lineage_signature as sig
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust as trust,
)
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as manifest,
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
    TicketAdmissionTelemetryLineageRelation,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)

ManifestEntry = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
)
ResolvedPublicKey = manifest.TicketAdmissionTelemetryLineageResolvedPublicKey
SignatureTrustManifest = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest
)
SignatureTrustManifestError = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestError
)
build_manifest = (
    manifest.build_ticket_admission_telemetry_lineage_signature_trust_manifest
)
decode_manifest = (
    manifest.decode_ticket_admission_telemetry_lineage_signature_trust_manifest
)
encode_manifest = (
    manifest.encode_ticket_admission_telemetry_lineage_signature_trust_manifest
)
manifest_identity = (
    manifest.ticket_admission_telemetry_lineage_signature_trust_manifest_id
)
read_manifest = (
    manifest.read_ticket_admission_telemetry_lineage_signature_trust_manifest
)
resolve_manifest = (
    manifest.resolve_ticket_admission_telemetry_lineage_signature_trust_manifest
)
write_manifest = (
    manifest.write_ticket_admission_telemetry_lineage_signature_trust_manifest
)
compare_with_trust = (
    trust.compare_ticket_admission_telemetry_lineage_signatures_with_trust
)
create_signature = (
    sig.create_ticket_admission_telemetry_lineage_signature_attestation
)
signature_fingerprint = (
    sig.ticket_admission_telemetry_lineage_signature_attestation_fingerprint
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

MANIFEST_ID = "ticket-admission-telemetry-lineage-signature-trust-manifest-v1"
MANIFEST_PREFIX = f"{MANIFEST_ID}:sha256:"
OLD_ALGORITHM_ID = "test-only-public-digest-v1"
NEW_ALGORITHM_ID = "test-only-public-digest-v2"
OLD_KEY_ID = "public.test-key.2026-07"
NEW_KEY_ID = "public.test-key.2026-08"
OLD_REFERENCE_ID = "vault.public-key.2026-07"
NEW_REFERENCE_ID = "vault.public-key.2026-08"
UNKNOWN_REFERENCE_ID = "vault.public-key.unknown"
OLD_PUBLIC_KEY = b"caller-owned-old-test-public-key"
NEW_PUBLIC_KEY = b"caller-owned-new-test-public-key"
WRONG_PUBLIC_KEY = b"caller-owned-wrong-test-public-key"
PUBLIC_KEY_ASSIGNMENT = b"public_key=b"
RECORDER_ID = "recorder.test"
COMPLETED_STREAM_ID = "completed.main"
FAILED_STREAM_ID = "failed.main"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "signature-manifest-test-workload-v1"
BENCHMARK_ID = "signature-manifest-test-route-v1"
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


class _DigestSigner:
    """Insecure deterministic signer used only for protocol regression tests."""

    def __init__(self, public_key: bytes) -> None:
        self.public_key: bytes = public_key

    def __call__(
        self,
        request: sig.TicketAdmissionTelemetryLineageSignatureRequest,
    ) -> sig.TicketAdmissionTelemetryLineageSignerResult:
        signature = sha256(self.public_key + request.payload).digest()
        return sig.TicketAdmissionTelemetryLineageSignerResult(
            kind=sig.TicketAdmissionTelemetryLineageSignerResultKind.SIGNED,
            signature=signature,
        )


class _DigestVerifier:
    """Insecure deterministic verifier for protocol regression tests."""

    def __init__(self) -> None:
        self.requests: list[
            sig.TicketAdmissionTelemetryLineageVerificationRequest
        ] = []

    def __call__(
        self,
        request: sig.TicketAdmissionTelemetryLineageVerificationRequest,
    ) -> sig.TicketAdmissionTelemetryLineageVerifierResult:
        self.requests.append(request)
        expected = sha256(request.public_key + request.payload).digest()
        kind = (
            sig.TicketAdmissionTelemetryLineageVerifierResultKind.VERIFIED
            if expected == request.signature
            else sig.TicketAdmissionTelemetryLineageVerifierResultKind.INVALID
        )
        return sig.TicketAdmissionTelemetryLineageVerifierResult(kind=kind)


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


def _document(
    elapsed_ns: int | None = None,
) -> TicketAdmissionTelemetryDocument:
    attempts = TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=2),
        failed=TicketAdmissionFailureTelemetry(capacity=2),
    )
    if elapsed_ns is not None:
        _ = attempts.record_completed(_report(), elapsed_ns=elapsed_ns)
    return capture_ticket_admission_telemetry_document(attempts)


def _fingerprint(public_key: bytes) -> str:
    return sig.ticket_admission_telemetry_lineage_public_key_fingerprint(
        public_key
    )


def _manifest_fingerprint(built: SignatureTrustManifest) -> str:
    function_name = (
        "ticket_admission_telemetry_lineage_signature_trust_"
        "manifest_fingerprint"
    )
    function = cast(
        "Callable[[SignatureTrustManifest], str]",
        getattr(manifest, function_name),
    )
    return function(built)


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_fingerprint: str | None = None,
    public_key_id: str = OLD_KEY_ID,
    public_key_reference_id: str = OLD_REFERENCE_ID,
    window: tuple[int, int | None] = (GENESIS_SEQUENCE_ID, None),
) -> ManifestEntry:
    first_capture_sequence_id, last_capture_sequence_id = window
    return ManifestEntry(
        algorithm_id=algorithm_id,
        first_capture_sequence_id=first_capture_sequence_id,
        last_capture_sequence_id=last_capture_sequence_id,
        public_key_fingerprint=(
            _fingerprint(public_key)
            if public_key_fingerprint is None
            else public_key_fingerprint
        ),
        public_key_id=public_key_id,
        public_key_reference_id=public_key_reference_id,
    )


def _resolved_key(
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_id: str = OLD_KEY_ID,
    public_key_reference_id: str = OLD_REFERENCE_ID,
) -> ResolvedPublicKey:
    return ResolvedPublicKey(
        algorithm_id=algorithm_id,
        public_key=public_key,
        public_key_id=public_key_id,
        public_key_reference_id=public_key_reference_id,
    )


def _rotation_manifest(
    *,
    rotate_algorithm: bool = False,
) -> SignatureTrustManifest:
    return build_manifest((
        _entry(
            algorithm_id=(
                NEW_ALGORITHM_ID if rotate_algorithm else OLD_ALGORITHM_ID
            ),
            public_key=NEW_PUBLIC_KEY,
            public_key_id=NEW_KEY_ID,
            public_key_reference_id=NEW_REFERENCE_ID,
            window=(SUCCESSOR_SEQUENCE_ID, None),
        ),
        _entry(
            window=(GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID),
        ),
    ))


def _rotation_keys(
    *,
    rotate_algorithm: bool = False,
    old_public_key: bytes = OLD_PUBLIC_KEY,
) -> tuple[ResolvedPublicKey, ...]:
    return (
        _resolved_key(
            algorithm_id=(
                NEW_ALGORITHM_ID if rotate_algorithm else OLD_ALGORITHM_ID
            ),
            public_key=NEW_PUBLIC_KEY,
            public_key_id=NEW_KEY_ID,
            public_key_reference_id=NEW_REFERENCE_ID,
        ),
        _resolved_key(public_key=old_public_key),
    )


def _claim(  # ruff: ignore[too-many-arguments]
    capture_sequence_id: int,
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_id: str = OLD_KEY_ID,
    previous_attestation_fingerprint: str | None = None,
) -> sig.TicketAdmissionTelemetryLineageSignatureClaim:
    return sig.TicketAdmissionTelemetryLineageSignatureClaim(
        algorithm_id=algorithm_id,
        capture_sequence_id=capture_sequence_id,
        completed_stream_id=COMPLETED_STREAM_ID,
        failed_stream_id=FAILED_STREAM_ID,
        previous_attestation_fingerprint=previous_attestation_fingerprint,
        public_key_fingerprint=_fingerprint(public_key),
        public_key_id=public_key_id,
        recorder_id=RECORDER_ID,
    )


def _signature_item(
    document: TicketAdmissionTelemetryDocument,
    claim: sig.TicketAdmissionTelemetryLineageSignatureClaim,
    *,
    public_key: bytes = OLD_PUBLIC_KEY,
) -> sig.TicketAdmissionTelemetryLineageSignatureItem:
    attestation = create_signature(
        document,
        claim,
        _DigestSigner(public_key),
    )
    return sig.TicketAdmissionTelemetryLineageSignatureItem(
        attestation=attestation,
        document=document,
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
    """An empty canonical manifest resolves to empty public-key trust."""
    built = build_manifest(())
    encoded = encode_manifest(built)
    decoded = decode_manifest(encoded)
    resolved = resolve_manifest(
        decoded,
        (),
    )

    assert manifest_identity() == (MANIFEST_ID)
    assert decoded == built
    assert decoded.entries == ()
    assert decoded.schema_version == SCHEMA_VERSION
    assert resolved.trust.key_count == 0
    assert resolved.manifest_fingerprint.startswith(MANIFEST_PREFIX)


def test_entries_are_composite_sorted_and_key_free() -> None:
    """Canonical ordering uses algorithm/key identity without key bytes."""
    built = _rotation_manifest(rotate_algorithm=True)
    encoded = encode_manifest(built)

    assert tuple(
        (entry.algorithm_id, entry.public_key_id) for entry in built.entries
    ) == (
        (OLD_ALGORITHM_ID, OLD_KEY_ID),
        (NEW_ALGORITHM_ID, NEW_KEY_ID),
    )
    assert OLD_PUBLIC_KEY not in encoded
    assert NEW_PUBLIC_KEY not in encoded
    assert PUBLIC_KEY_ASSIGNMENT not in repr(built).encode("utf-8")


def test_canonical_round_trip_and_fingerprint_are_byte_stable() -> None:
    """Compact sorted JSON and its SHA-256 identity remain deterministic."""
    built = _rotation_manifest()
    encoded = encode_manifest(built)
    decoded = decode_manifest(encoded)

    assert decoded == built
    assert encode_manifest(decoded) == encoded
    assert (
        _manifest_fingerprint(built)
        == f"{MANIFEST_PREFIX}{sha256(encoded).hexdigest()}"
    )


def test_explicit_write_and_read_preserve_canonical_bytes(
    tmp_path: Path,
) -> None:
    """Atomic explicit storage preserves exact manifest bytes."""
    path = tmp_path / "signature-trust.json"
    built = _rotation_manifest()
    encoded = encode_manifest(built)

    write_manifest(
        path,
        built,
    )
    restored = read_manifest(path)

    assert path.read_bytes() == encoded
    assert restored == built
    assert tuple(tmp_path.glob(".*.tmp")) == ()


@pytest.mark.parametrize(
    ("entries", "max_entries", "message"),
    [
        (
            cast(
                "tuple[ManifestEntry, ...]",
                cast("object", []),
            ),
            1,
            "entries must use the exact immutable tuple type",
        ),
        ((), True, "entry limit must be a positive integer"),
        (
            (_entry(), _entry(public_key_id=NEW_KEY_ID)),
            1,
            "entry count exceeds",
        ),
    ],
)
def test_invalid_build_container_or_limit_fails_closed(
    entries: tuple[
        ManifestEntry,
        ...,
    ],
    max_entries: int,
    message: str,
) -> None:
    """Construction requires an exact bounded immutable tuple."""
    with pytest.raises(
        SignatureTrustManifestError,
        match=message,
    ):
        _ = build_manifest(
            entries,
            max_entries=max_entries,
        )


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (
            (
                _entry(),
                _entry(public_key=NEW_PUBLIC_KEY),
            ),
            "duplicate algorithm and public-key identity",
        ),
        (
            (
                _entry(),
                _entry(
                    public_key=NEW_PUBLIC_KEY,
                    public_key_id=NEW_KEY_ID,
                    public_key_reference_id=OLD_REFERENCE_ID,
                ),
            ),
            "duplicate public-key reference identity",
        ),
    ],
)
def test_duplicate_manifest_identity_fails_closed(
    entries: tuple[
        ManifestEntry,
        ...,
    ],
    message: str,
) -> None:
    """Composite identities and external references remain unique."""
    with pytest.raises(
        SignatureTrustManifestError,
        match=message,
    ):
        _ = build_manifest(entries)


def test_same_public_key_id_is_allowed_under_distinct_algorithms() -> None:
    """Algorithm identity is part of the persisted trust identity."""
    built = build_manifest((
        _entry(),
        _entry(
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_reference_id=NEW_REFERENCE_ID,
        ),
    ))

    assert tuple(entry.algorithm_id for entry in built.entries) == (
        OLD_ALGORITHM_ID,
        NEW_ALGORITHM_ID,
    )


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (
            _entry(algorithm_id="bad algorithm"),
            "algorithm identity must use canonical ASCII identity form",
        ),
        (
            _entry(public_key_id="bad key"),
            "public-key identity must use canonical ASCII identity form",
        ),
        (
            _entry(public_key_reference_id="bad reference"),
            (
                "public-key reference identity must use canonical ASCII "
                "identity form"
            ),
        ),
        (
            _entry(public_key_fingerprint="invalid"),
            "public-key fingerprint is malformed",
        ),
        (
            _entry(window=(True, None)),
            "first capture sequence identity must be a nonnegative integer",
        ),
        (
            _entry(window=(2, 1)),
            "last capture sequence precedes first capture sequence",
        ),
    ],
)
def test_invalid_manifest_entry_fails_closed(
    entry: ManifestEntry,
    message: str,
) -> None:
    """Malformed identities, fingerprints, and windows never persist."""
    with pytest.raises(
        SignatureTrustManifestError,
        match=message,
    ):
        _ = build_manifest((entry,))


def test_duplicate_encoded_json_key_fails_closed() -> None:
    """Duplicate JSON keys cannot alter canonical trust metadata."""
    encoded = encode_manifest(_rotation_manifest())
    duplicate = encoded.replace(
        b'{"entries":',
        b'{"entries":[],"entries":',
        1,
    )

    with pytest.raises(
        SignatureTrustManifestError,
        match="duplicate JSON key",
    ):
        _ = decode_manifest(duplicate)


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
    encoded = encode_manifest(_rotation_manifest())
    mapping = _mapping(encoded)
    max_bytes = len(encoded)
    max_entries = TWO_ENTRIES
    if mutation == UNKNOWN_MUTATION:
        mapping["unknown"] = 1
        data = _encoded_mapping(mapping)
        max_bytes = len(data)
        message = "keys are unsupported"
    elif mutation == NONCANONICAL_MUTATION:
        data = dumps(mapping, indent=2, sort_keys=True).encode("utf-8")
        max_bytes = len(data)
        message = "manifest bytes are not canonical"
    elif mutation == OVERSIZED_MUTATION:
        data = encoded
        max_bytes = len(encoded) - 1
        message = "exceeds configured byte limit"
    else:
        data = encoded
        max_entries = 1
        message = "entry count exceeds configured limit"

    with pytest.raises(
        SignatureTrustManifestError,
        match=message,
    ):
        _ = decode_manifest(
            data,
            max_bytes=max_bytes,
            max_entries=max_entries,
        )


def test_resolution_builds_manifest_bound_signature_trust() -> None:
    """Exact key coverage resolves a usable in-memory signature trust set."""
    built = _rotation_manifest(rotate_algorithm=True)
    resolved = resolve_manifest(
        built,
        _rotation_keys(rotate_algorithm=True),
    )

    assert resolved.manifest_fingerprint == (_manifest_fingerprint(built))
    assert resolved.trust.key_count == TWO_ENTRIES
    assert tuple(
        (key.algorithm_id, key.public_key_id) for key in resolved.trust.keys
    ) == (
        (OLD_ALGORITHM_ID, OLD_KEY_ID),
        (NEW_ALGORITHM_ID, NEW_KEY_ID),
    )
    rendered = repr(resolved).encode("utf-8")
    assert OLD_PUBLIC_KEY not in rendered
    assert NEW_PUBLIC_KEY not in rendered
    assert PUBLIC_KEY_ASSIGNMENT not in rendered


@pytest.mark.parametrize(
    ("public_keys", "message"),
    [
        ((_resolved_key(),), "coverage is incomplete or excessive"),
        (
            (
                *_rotation_keys(),
                _resolved_key(
                    public_key_id="public.extra",
                    public_key_reference_id=UNKNOWN_REFERENCE_ID,
                ),
            ),
            "coverage is incomplete or excessive",
        ),
    ],
)
def test_missing_or_extra_resolution_fails_closed(
    public_keys: tuple[
        ResolvedPublicKey,
        ...,
    ],
    message: str,
) -> None:
    """Resolution coverage must match manifest entries exactly."""
    with pytest.raises(
        SignatureTrustManifestError,
        match=message,
    ):
        _ = resolve_manifest(
            _rotation_manifest(),
            public_keys,
        )


def test_mismatched_reference_resolution_fails_closed() -> None:
    """A composite identity cannot resolve through a different reference."""
    public_keys = (
        _resolved_key(public_key_reference_id=UNKNOWN_REFERENCE_ID),
        _resolved_key(
            public_key=NEW_PUBLIC_KEY,
            public_key_id=NEW_KEY_ID,
            public_key_reference_id=NEW_REFERENCE_ID,
        ),
    )

    with pytest.raises(
        SignatureTrustManifestError,
        match="resolved public-key reference does not match manifest",
    ):
        _ = resolve_manifest(
            _rotation_manifest(),
            public_keys,
        )


def test_mismatched_public_key_fingerprint_fails_closed() -> None:
    """Resolved bytes must match the fingerprint persisted in the manifest."""
    with pytest.raises(
        SignatureTrustManifestError,
        match="resolved public-key fingerprint does not match manifest",
    ):
        _ = resolve_manifest(
            _rotation_manifest(),
            _rotation_keys(old_public_key=WRONG_PUBLIC_KEY),
        )


@pytest.mark.parametrize(
    ("public_keys", "message"),
    [
        (
            (
                _resolved_key(),
                _resolved_key(public_key=NEW_PUBLIC_KEY),
            ),
            "duplicate resolved algorithm and public-key identity",
        ),
        (
            (
                _resolved_key(),
                _resolved_key(
                    public_key=NEW_PUBLIC_KEY,
                    public_key_id=NEW_KEY_ID,
                    public_key_reference_id=OLD_REFERENCE_ID,
                ),
            ),
            "duplicate resolved public-key reference identity",
        ),
    ],
)
def test_duplicate_resolution_identity_fails_closed(
    public_keys: tuple[
        ResolvedPublicKey,
        ...,
    ],
    message: str,
) -> None:
    """Resolved composite identities and references remain unique."""
    with pytest.raises(
        SignatureTrustManifestError,
        match=message,
    ):
        _ = resolve_manifest(
            _rotation_manifest(),
            public_keys,
        )


@pytest.mark.parametrize(
    ("public_key", "message"),
    [
        (
            _resolved_key(algorithm_id="bad algorithm"),
            (
                "resolved algorithm identity must use canonical ASCII "
                "identity form"
            ),
        ),
        (
            _resolved_key(public_key_id="bad key"),
            (
                "resolved public-key identity must use canonical ASCII "
                "identity form"
            ),
        ),
        (
            _resolved_key(public_key_reference_id="bad reference"),
            "resolved public-key reference identity must use canonical ASCII",
        ),
        (
            ResolvedPublicKey(
                algorithm_id=OLD_ALGORITHM_ID,
                public_key=cast(
                    "bytes", cast("object", bytearray(OLD_PUBLIC_KEY))
                ),
                public_key_id=OLD_KEY_ID,
                public_key_reference_id=OLD_REFERENCE_ID,
            ),
            "public key must use the exact bytes type",
        ),
    ],
)
def test_invalid_resolved_public_key_fails_closed(
    public_key: ResolvedPublicKey,
    message: str,
) -> None:
    """Malformed resolution metadata and key containers remain invalid."""
    with pytest.raises(
        SignatureTrustManifestError,
        match=message,
    ):
        _ = resolve_manifest(
            build_manifest(()),
            (public_key,),
        )


@pytest.mark.parametrize(
    ("built", "message"),
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
            "uniquely ordered by algorithm and key",
        ),
    ],
)
def test_tampered_manifest_metadata_fails_closed(
    built: SignatureTrustManifest,
    message: str,
) -> None:
    """Manifest identity, schema, and canonical ordering are revalidated."""
    with pytest.raises(
        SignatureTrustManifestError,
        match=message,
    ):
        _ = encode_manifest(built)


def test_resolution_tuple_type_is_exact() -> None:
    """Resolution requires an immutable tuple, not a mutable list."""
    public_keys = cast(
        "tuple[ResolvedPublicKey, ...]",
        cast("object", list(_rotation_keys())),
    )

    with pytest.raises(
        SignatureTrustManifestError,
        match="resolved public keys must use the exact immutable tuple type",
    ):
        _ = resolve_manifest(
            _rotation_manifest(),
            public_keys,
        )


def test_explicit_read_rejects_missing_path(tmp_path: Path) -> None:
    """Manifest loading uses only the explicit caller path."""
    with pytest.raises(
        SignatureTrustManifestError,
        match="cannot read signature trust manifest",
    ):
        _ = read_manifest(tmp_path / "missing.json")


def test_path_type_is_exact() -> None:
    """Storage APIs reject string paths without implicit resolution."""
    path = cast("Path", cast("object", "signature-trust.json"))
    with pytest.raises(
        SignatureTrustManifestError,
        match=r"path must be a pathlib Path",
    ):
        write_manifest(
            path,
            _rotation_manifest(),
        )


def test_resolved_trust_verifies_direct_successor_rotation() -> None:
    """Resolved public keys preserve direct lineage across rotation."""
    first_document = _document(LOW_ELAPSED_NS)
    first = _signature_item(
        first_document,
        _claim(GENESIS_SEQUENCE_ID),
    )
    first_id = signature_fingerprint(first.attestation)
    second_document = _document(HIGH_ELAPSED_NS)
    second = _signature_item(
        second_document,
        _claim(
            SUCCESSOR_SEQUENCE_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=NEW_KEY_ID,
            previous_attestation_fingerprint=first_id,
        ),
        public_key=NEW_PUBLIC_KEY,
    )
    resolved = resolve_manifest(_rotation_manifest(), _rotation_keys())
    verifier = _DigestVerifier()

    comparison = compare_with_trust(
        first,
        second,
        verifier,
        trust=resolved.trust,
    )

    assert len(verifier.requests) == TWO_ENTRIES
    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert comparison.first.key_id == OLD_KEY_ID
    assert comparison.second.key_id == NEW_KEY_ID


def test_resolved_trust_supports_algorithm_and_key_rotation() -> None:
    """Resolution may rotate algorithm and public key explicitly."""
    first_document = _document(LOW_ELAPSED_NS)
    first = _signature_item(
        first_document,
        _claim(GENESIS_SEQUENCE_ID),
    )
    first_id = signature_fingerprint(first.attestation)
    second_document = _document(HIGH_ELAPSED_NS)
    second = _signature_item(
        second_document,
        _claim(
            SUCCESSOR_SEQUENCE_ID,
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=NEW_KEY_ID,
            previous_attestation_fingerprint=first_id,
        ),
        public_key=NEW_PUBLIC_KEY,
    )
    resolved = resolve_manifest(
        _rotation_manifest(rotate_algorithm=True),
        _rotation_keys(rotate_algorithm=True),
    )

    comparison = compare_with_trust(
        first,
        second,
        _DigestVerifier(),
        trust=resolved.trust,
    )

    assert comparison.relation is (
        TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR
    )
    assert comparison.first.key_id == OLD_KEY_ID
    assert comparison.second.key_id == NEW_KEY_ID
