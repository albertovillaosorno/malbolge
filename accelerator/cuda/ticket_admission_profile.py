# File:
#   - ticket_admission_profile.py
# Path:
#   - accelerator/cuda/ticket_admission_profile.py
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
#   - Strict product-owned CUDA ticket-admission profile loading.
# - Must-Not:
#   - Read benchmark evidence at runtime or infer missing profile fields.
# - Allows:
#   - Inputs: one tracked schema-v4 JSON profile manifest.
# - Outputs: validated immutable CUDA admission profiles.
# - Side effects: manifest file reads only.
# - Split-When:
#   - Split when another backend gains an independent manifest schema.
# - Merge-When:
#   - Merge when another module owns this exact profile-loading contract.
# - Summary:
#   - Strict CUDA ticket-admission profile manifest loader.
# - Description:
#   - Converts canonical evidence-derived JSON into typed route candidates.
# - Usage:
#   - Loaded lazily by the opt-in retained CUDA ticket executor.
# - Defaults:
#   - Missing, duplicate, unknown, or malformed fields fail closed.
#
# Related documents:
# - accelerator/cuda/ticket_admission_profiles.json
# - benchmarks/accelerator/ticket_admission_profile_manifest.py
#
# Large file:
#   - false
#

"""Strict product-owned CUDA ticket-admission profile manifest loading."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from accelerator.ticket_admission import TicketAdmissionError
from accelerator.ticket_admission import TicketAdmissionRequest
from accelerator.ticket_admission import TicketRouteCandidate
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import plan_ticket_submissions

if TYPE_CHECKING:
    from accelerator.cuda.runtime import CudaHostRuntimeIdentity
    from accelerator.cuda.runtime import CudaRuntimeIdentity
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.ticket_admission import TicketAdmissionPlan

PROFILE_SCHEMA_VERSION = 4
PROFILE_MANIFEST_PATH = Path(__file__).with_name(
    "ticket_admission_profiles.json"
)
PROFILE_ROOT_KEYS = frozenset(("profiles", "schema_version"))
PROFILE_KEYS = frozenset((
    "backend_id",
    "device_arch",
    "device_name",
    "evidence",
    "fallback_ticket_ns",
    "profile_id",
    "routes",
    "runtime",
    "sample_count",
    "workload_count",
    "workload_id",
    "workload_kind",
    "workload_sha256",
))
EVIDENCE_KEYS = frozenset((
    "benchmark_id",
    "host",
    "path",
    "raw_sha256",
    "source_commit",
    "throughput_sha256",
    "toolchain",
))
RUNTIME_KEYS = frozenset((
    "display_driver_version",
    "host_runtime",
    "identity_id",
    "minimum_driver_api_version",
    "nvrtc_major",
    "nvrtc_minor",
    "toolchain_manifest_sha256",
))
HOST_RUNTIME_KEYS = frozenset((
    "host_edition",
    "host_machine",
    "host_release",
    "host_system",
    "host_version",
    "identity_id",
    "python_implementation",
    "python_version",
))
ROUTE_KEYS = frozenset((
    "candidate_median_ns",
    "exact_results",
    "group_size",
    "mode",
    "paired_wins",
    "reference_median_ns",
))
_HEX_DIGITS = frozenset("0123456789abcdef")
_WINDOWS_SEPARATOR = "\\"
_ABSOLUTE_PREFIXES = ("/", ".")
_DIRECTORY_SUFFIX = "/"
_DISPLAY_DRIVER_MIN_COMPONENTS = 2


@dataclass(frozen=True, slots=True)
class CudaTicketAdmissionEvidence:
    """Retained provenance bound into one product admission profile."""

    benchmark_id: str
    host: str
    path: str
    raw_sha256: str
    source_commit: str
    throughput_sha256: str
    toolchain: str


@dataclass(frozen=True, slots=True)
class CudaTicketAdmissionHostRuntime:
    """Exact retained host OS and Python runtime context."""

    host_edition: str
    host_machine: str
    host_release: str
    host_system: str
    host_version: str
    identity_id: str
    python_implementation: str
    python_version: str

    def matches(self, identity: CudaHostRuntimeIdentity | None) -> bool:
        """Check one optional measured host identity.

        Returns:
            Whether every retained host/Python field matches exactly.

        """
        return identity is not None and (
            identity.host_edition == self.host_edition
            and identity.host_machine == self.host_machine
            and identity.host_release == self.host_release
            and identity.host_system == self.host_system
            and identity.host_version == self.host_version
            and identity.identity_id == self.identity_id
            and identity.python_implementation == self.python_implementation
            and identity.python_version == self.python_version
        )


@dataclass(frozen=True, slots=True)
class CudaTicketAdmissionRuntime:
    """Runtime compatibility required by one evidence-backed profile."""

    display_driver_version: str
    host_runtime: CudaTicketAdmissionHostRuntime
    identity_id: str
    minimum_driver_api_version: int
    nvrtc_major: int
    nvrtc_minor: int
    toolchain_manifest_sha256: str

    def matches(self, identity: CudaRuntimeIdentity) -> bool:
        """Check measured runtime compatibility.

        Returns:
            Whether display build, Driver API, NVRTC, protocol, and
            manifest match.

        """
        return (
            identity.display_driver_version == self.display_driver_version
            and self.host_runtime.matches(identity.host_runtime_identity)
            and identity.identity_id == self.identity_id
            and identity.driver_api_version >= self.minimum_driver_api_version
            and identity.nvrtc_major == self.nvrtc_major
            and identity.nvrtc_minor == self.nvrtc_minor
            and identity.toolchain_manifest_sha256
            == self.toolchain_manifest_sha256
        )


@dataclass(frozen=True, slots=True)
class _ProfileFields:
    backend_id: str
    device_arch: str
    device_name: str
    evidence: CudaTicketAdmissionEvidence
    fallback_ticket_ns: int
    profile_id: str
    runtime: CudaTicketAdmissionRuntime
    sample_count: int
    workload_count: int
    workload_id: str
    workload_kind: str
    workload_sha256: str


@dataclass(frozen=True, slots=True)
class _RouteContext:
    backend_id: str
    benchmark_id: str
    device_arch: str
    device_name: str
    sample_count: int
    workload_id: str


@dataclass(frozen=True, slots=True)
class CudaTicketAdmissionProfile:
    """One exact retained CUDA route-admission evidence context."""

    backend_id: str
    candidates: tuple[TicketRouteCandidate, ...]
    device_arch: str
    device_name: str
    evidence: CudaTicketAdmissionEvidence
    fallback_ticket_ns: int
    profile_id: str
    runtime: CudaTicketAdmissionRuntime
    sample_count: int
    workload_count: int
    workload_id: str
    workload_kind: str
    workload_sha256: str

    def matches(
        self,
        capability: AcceleratorCapability,
        runtime_identity: CudaRuntimeIdentity,
    ) -> bool:
        """Check one live capability against this exact device context.

        Returns:
            Whether all retained capability identities match.

        """
        return (
            capability.backend_id == self.backend_id
            and capability.device_arch == self.device_arch
            and capability.device_name == self.device_name
            and self.runtime.matches(runtime_identity)
        )

    def plan(
        self,
        capability: AcceleratorCapability,
        runtime_identity: CudaRuntimeIdentity,
        ticket_count: int,
    ) -> TicketAdmissionPlan:
        """Plan pending tickets for exact retained capability/runtime identity.

        Returns:
            Conservative fewest-chunk plan with measured-cost tie breaking.

        Raises:
            TicketAdmissionError: If capability or runtime identity mismatches.

        """
        if not self.matches(capability, runtime_identity):
            message = (
                "CUDA ticket admission profile capability/runtime mismatched"
            )
            raise TicketAdmissionError(message)
        return plan_ticket_submissions(
            TicketAdmissionRequest(
                backend_id=capability.backend_id,
                device_arch=capability.device_arch,
                device_name=capability.device_name,
                ticket_count=ticket_count,
                workload_id=self.workload_id,
            ),
            candidates=self.candidates,
            fallback_ticket_ns=self.fallback_ticket_ns,
        )


@cache
def load_cuda_ticket_admission_profiles(
    path: Path = PROFILE_MANIFEST_PATH,
) -> tuple[CudaTicketAdmissionProfile, ...]:
    """Load and validate one product-owned admission manifest.

    Returns:
        Stable manifest-order profiles after exact schema validation.

    Raises:
        TicketAdmissionError: If the document is missing or malformed.

    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        message = f"cannot read CUDA ticket admission profiles: {error}"
        raise TicketAdmissionError(message) from error
    document = _json_document(text)
    _expect_exact_keys(document, PROFILE_ROOT_KEYS, "profile document")
    schema_version = _expect_int(
        document["schema_version"],
        "profile document.schema_version",
    )
    if schema_version != PROFILE_SCHEMA_VERSION:
        message = (
            "unsupported CUDA ticket admission profile schema: "
            f"{schema_version}"
        )
        raise TicketAdmissionError(message)
    entries = _expect_array(document["profiles"], "profile document.profiles")
    if not entries:
        message = "CUDA ticket admission profile manifest must not be empty"
        raise TicketAdmissionError(message)
    profiles = tuple(
        _profile(_expect_mapping(entry, f"profile[{index}]"), index)
        for index, entry in enumerate(entries)
    )
    _validate_profile_uniqueness(profiles)
    return profiles


def resolve_cuda_ticket_admission_profile(
    profiles: tuple[CudaTicketAdmissionProfile, ...],
    *,
    capability: AcceleratorCapability,
    runtime_identity: CudaRuntimeIdentity,
    workload_id: str,
) -> CudaTicketAdmissionProfile | None:
    """Resolve at most one exact profile from a validated registry.

    Returns:
        Exact capability/runtime/workload profile, or ``None`` without one.

    Raises:
        TicketAdmissionError: If workload identity is invalid or ambiguous.

    """
    if not workload_id or workload_id.strip() != workload_id:
        message = "CUDA ticket admission workload identity is invalid"
        raise TicketAdmissionError(message)
    matches = tuple(
        profile
        for profile in profiles
        if profile.workload_id == workload_id
        and profile.matches(capability, runtime_identity)
    )
    if len(matches) > 1:
        message = (
            "CUDA ticket admission registry resolved multiple exact profiles"
        )
        raise TicketAdmissionError(message)
    return None if not matches else matches[0]


def _json_document(text: str) -> dict[str, object]:
    try:
        parsed = cast(
            "object",
            json.loads(text, object_pairs_hook=_reject_duplicate_pairs),
        )
    except json.JSONDecodeError as error:
        message = f"invalid CUDA ticket admission profile JSON: {error}"
        raise TicketAdmissionError(message) from error
    return _expect_mapping(parsed, "profile document")


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            message = f"duplicate CUDA ticket admission JSON key: {key}"
            raise TicketAdmissionError(message)
        result[key] = value
    return result


def _profile(
    document: dict[str, object],
    index: int,
) -> CudaTicketAdmissionProfile:
    context = f"profile[{index}]"
    _expect_exact_keys(document, PROFILE_KEYS, context)
    fields = _profile_fields(document, context)
    candidates = _profile_candidates(document["routes"], fields, context)
    return CudaTicketAdmissionProfile(
        backend_id=fields.backend_id,
        candidates=candidates,
        device_arch=fields.device_arch,
        device_name=fields.device_name,
        evidence=fields.evidence,
        fallback_ticket_ns=fields.fallback_ticket_ns,
        profile_id=fields.profile_id,
        runtime=fields.runtime,
        sample_count=fields.sample_count,
        workload_count=fields.workload_count,
        workload_id=fields.workload_id,
        workload_kind=fields.workload_kind,
        workload_sha256=fields.workload_sha256,
    )


def _profile_fields(
    document: dict[str, object],
    context: str,
) -> _ProfileFields:
    evidence = _evidence(
        _expect_mapping(document["evidence"], f"{context}.evidence"),
        context,
    )
    return _ProfileFields(
        backend_id=_expect_string(
            document["backend_id"],
            f"{context}.backend_id",
        ),
        device_arch=_expect_string(
            document["device_arch"],
            f"{context}.device_arch",
        ),
        device_name=_expect_string(
            document["device_name"],
            f"{context}.device_name",
        ),
        evidence=evidence,
        fallback_ticket_ns=_expect_positive_int(
            document["fallback_ticket_ns"],
            f"{context}.fallback_ticket_ns",
        ),
        profile_id=_expect_string(
            document["profile_id"],
            f"{context}.profile_id",
        ),
        runtime=_runtime(
            _expect_mapping(document["runtime"], f"{context}.runtime"),
            context,
        ),
        sample_count=_expect_positive_int(
            document["sample_count"],
            f"{context}.sample_count",
        ),
        workload_count=_expect_positive_int(
            document["workload_count"],
            f"{context}.workload_count",
        ),
        workload_id=_expect_string(
            document["workload_id"],
            f"{context}.workload_id",
        ),
        workload_kind=_expect_string(
            document["workload_kind"],
            f"{context}.workload_kind",
        ),
        workload_sha256=_expect_hex(
            document["workload_sha256"],
            length=64,
            context=f"{context}.workload_sha256",
        ),
    )


def _profile_candidates(
    value: object,
    fields: _ProfileFields,
    context: str,
) -> tuple[TicketRouteCandidate, ...]:
    entries = _expect_array(value, f"{context}.routes")
    if not entries:
        message = f"{context}.routes must not be empty"
        raise TicketAdmissionError(message)
    route_context = _RouteContext(
        backend_id=fields.backend_id,
        benchmark_id=fields.evidence.benchmark_id,
        device_arch=fields.device_arch,
        device_name=fields.device_name,
        sample_count=fields.sample_count,
        workload_id=fields.workload_id,
    )
    candidates = tuple(
        _route_candidate(
            _expect_mapping(entry, f"{context}.routes[{index}]"),
            route_context=route_context,
            context=f"{context}.routes[{index}]",
        )
        for index, entry in enumerate(entries)
    )
    _validate_route_uniqueness(candidates, context)
    return candidates


def _runtime(
    document: dict[str, object],
    profile_context: str,
) -> CudaTicketAdmissionRuntime:
    context = f"{profile_context}.runtime"
    _expect_exact_keys(document, RUNTIME_KEYS, context)
    return CudaTicketAdmissionRuntime(
        display_driver_version=_expect_display_driver_version(
            document["display_driver_version"],
            f"{context}.display_driver_version",
        ),
        host_runtime=_host_runtime(
            _expect_mapping(
                document["host_runtime"], f"{context}.host_runtime"
            ),
            context,
        ),
        identity_id=_expect_string(
            document["identity_id"],
            f"{context}.identity_id",
        ),
        minimum_driver_api_version=_expect_positive_int(
            document["minimum_driver_api_version"],
            f"{context}.minimum_driver_api_version",
        ),
        nvrtc_major=_expect_positive_int(
            document["nvrtc_major"],
            f"{context}.nvrtc_major",
        ),
        nvrtc_minor=_expect_nonnegative_int(
            document["nvrtc_minor"],
            f"{context}.nvrtc_minor",
        ),
        toolchain_manifest_sha256=_expect_hex(
            document["toolchain_manifest_sha256"],
            length=64,
            context=f"{context}.toolchain_manifest_sha256",
        ),
    )


def _host_runtime(
    document: dict[str, object],
    runtime_context: str,
) -> CudaTicketAdmissionHostRuntime:
    context = f"{runtime_context}.host_runtime"
    _expect_exact_keys(document, HOST_RUNTIME_KEYS, context)
    return CudaTicketAdmissionHostRuntime(
        host_edition=_expect_string(
            document["host_edition"],
            f"{context}.host_edition",
        ),
        host_machine=_expect_string(
            document["host_machine"],
            f"{context}.host_machine",
        ),
        host_release=_expect_string(
            document["host_release"],
            f"{context}.host_release",
        ),
        host_system=_expect_string(
            document["host_system"],
            f"{context}.host_system",
        ),
        host_version=_expect_string(
            document["host_version"],
            f"{context}.host_version",
        ),
        identity_id=_expect_string(
            document["identity_id"],
            f"{context}.identity_id",
        ),
        python_implementation=_expect_string(
            document["python_implementation"],
            f"{context}.python_implementation",
        ),
        python_version=_expect_string(
            document["python_version"],
            f"{context}.python_version",
        ),
    )


def _evidence(
    document: dict[str, object],
    profile_context: str,
) -> CudaTicketAdmissionEvidence:
    context = f"{profile_context}.evidence"
    _expect_exact_keys(document, EVIDENCE_KEYS, context)
    path = _expect_string(document["path"], f"{context}.path")
    if (
        _WINDOWS_SEPARATOR in path
        or path.startswith(_ABSOLUTE_PREFIXES)
        or not path.endswith(_DIRECTORY_SUFFIX)
    ):
        message = (
            f"{context}.path must be a normalized repository-relative directory"
        )
        raise TicketAdmissionError(message)
    return CudaTicketAdmissionEvidence(
        benchmark_id=_expect_string(
            document["benchmark_id"],
            f"{context}.benchmark_id",
        ),
        host=_expect_string(document["host"], f"{context}.host"),
        path=path,
        raw_sha256=_expect_hex(
            document["raw_sha256"],
            length=64,
            context=f"{context}.raw_sha256",
        ),
        source_commit=_expect_hex(
            document["source_commit"],
            length=40,
            context=f"{context}.source_commit",
        ),
        throughput_sha256=_expect_hex(
            document["throughput_sha256"],
            length=64,
            context=f"{context}.throughput_sha256",
        ),
        toolchain=_expect_string(
            document["toolchain"],
            f"{context}.toolchain",
        ),
    )


def _route_candidate(
    document: dict[str, object],
    *,
    route_context: _RouteContext,
    context: str,
) -> TicketRouteCandidate:
    _expect_exact_keys(document, ROUTE_KEYS, context)
    mode_text = _expect_string(document["mode"], f"{context}.mode")
    try:
        mode = TicketSubmissionMode(mode_text)
    except ValueError as error:
        message = f"{context}.mode is unsupported: {mode_text}"
        raise TicketAdmissionError(message) from error
    return TicketRouteCandidate(
        backend_id=route_context.backend_id,
        benchmark_id=route_context.benchmark_id,
        candidate_median_ns=_expect_positive_int(
            document["candidate_median_ns"],
            f"{context}.candidate_median_ns",
        ),
        device_arch=route_context.device_arch,
        device_name=route_context.device_name,
        exact_results=_expect_bool(
            document["exact_results"],
            f"{context}.exact_results",
        ),
        group_size=_expect_positive_int(
            document["group_size"],
            f"{context}.group_size",
        ),
        mode=mode,
        paired_wins=_expect_nonnegative_int(
            document["paired_wins"],
            f"{context}.paired_wins",
        ),
        reference_median_ns=_expect_positive_int(
            document["reference_median_ns"],
            f"{context}.reference_median_ns",
        ),
        sample_count=route_context.sample_count,
        workload_id=route_context.workload_id,
    ).validated()


def _validate_route_uniqueness(
    candidates: tuple[TicketRouteCandidate, ...],
    context: str,
) -> None:
    seen: set[tuple[TicketSubmissionMode, int]] = set()
    for candidate in candidates:
        key = (candidate.mode, candidate.group_size)
        if key in seen:
            message = (
                f"{context}.routes duplicates "
                f"{candidate.mode.value}/{candidate.group_size}"
            )
            raise TicketAdmissionError(message)
        seen.add(key)


def _validate_profile_uniqueness(
    profiles: tuple[CudaTicketAdmissionProfile, ...],
) -> None:
    identifiers: set[str] = set()
    contexts: set[tuple[str, str, str, str, CudaTicketAdmissionRuntime]] = set()
    for profile in profiles:
        if profile.profile_id in identifiers:
            message = (
                f"duplicate CUDA ticket admission profile: {profile.profile_id}"
            )
            raise TicketAdmissionError(message)
        identifiers.add(profile.profile_id)
        context = (
            profile.backend_id,
            profile.device_arch,
            profile.device_name,
            profile.workload_id,
            profile.runtime,
        )
        if context in contexts:
            message = (
                "duplicate CUDA ticket admission capability/workload/"
                "runtime context"
            )
            raise TicketAdmissionError(message)
        contexts.add(context)


def _expect_mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        message = f"{context} must be an object"
        raise TicketAdmissionError(message)
    raw = cast("dict[object, object]", value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            message = f"{context} contains a non-string key"
            raise TicketAdmissionError(message)
        result[key] = item
    return result


def _expect_array(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        message = f"{context} must be an array"
        raise TicketAdmissionError(message)
    return cast("list[object]", value)


def _expect_string(value: object, context: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        message = f"{context} must be a trimmed non-empty string"
        raise TicketAdmissionError(message)
    return value


def _expect_int(value: object, context: str) -> int:
    if type(value) is not int:
        message = f"{context} must be an integer"
        raise TicketAdmissionError(message)
    return value


def _expect_positive_int(value: object, context: str) -> int:
    observed = _expect_int(value, context)
    if observed <= 0:
        message = f"{context} must be positive"
        raise TicketAdmissionError(message)
    return observed


def _expect_nonnegative_int(value: object, context: str) -> int:
    observed = _expect_int(value, context)
    if observed < 0:
        message = f"{context} must be non-negative"
        raise TicketAdmissionError(message)
    return observed


def _expect_bool(value: object, context: str) -> bool:
    if type(value) is not bool:
        message = f"{context} must be boolean"
        raise TicketAdmissionError(message)
    return value


def _expect_display_driver_version(value: object, context: str) -> str:
    observed = _expect_string(value, context)
    components = observed.split(".")
    if len(components) < _DISPLAY_DRIVER_MIN_COMPONENTS or not all(
        component and component.isdigit() for component in components
    ):
        message = f"{context} must be a dotted numeric version"
        raise TicketAdmissionError(message)
    return observed


def _expect_hex(value: object, *, length: int, context: str) -> str:
    observed = _expect_string(value, context)
    if len(observed) != length or any(
        char not in _HEX_DIGITS for char in observed
    ):
        message = f"{context} must be {length} lowercase hexadecimal characters"
        raise TicketAdmissionError(message)
    return observed


def _expect_exact_keys(
    document: dict[str, object],
    expected: frozenset[str],
    context: str,
) -> None:
    observed = frozenset(document)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if not missing and not unknown:
        return
    details: list[str] = []
    if missing:
        details.append(f"missing {", ".join(missing)}")
    if unknown:
        details.append(f"unknown {", ".join(unknown)}")
    message = f"{context} keys are invalid: {"; ".join(details)}"
    raise TicketAdmissionError(message)
