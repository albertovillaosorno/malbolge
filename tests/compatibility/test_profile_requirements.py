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
#   - Python target-profile requirement and capability-preflight regressions.
# - Must-Not:
#   - Execute guest code, infer host capacity, select fallback profiles, mutate
#     canonical data, or replace Rust runtime evidence.
# - Allows:
#   - Inputs: canonical profile data, explicit requirements, and capabilities.
#   - Outputs: exact immutable objects and stable diagnostic assertions.
#   - Side effects: repository profile reads only.
# - Split-When:
#   - Split when another Python runtime family gains independent capability
#     data.
# - Merge-When:
#   - Merge when another suite owns exact Python/Rust diagnostic parity.
# - Summary:
#   - Verifies deterministic non-VM profile preflight and Rust-text parity.
# - Description:
#   - Covers current, transition, historical, malformed, and missing dimensions.
# - Usage:
#   - Runs without guest execution, external tools, network, or host probing.
# - Defaults:
#   - Uses canonical `malbolge.json` and explicit safe-Rust envelopes.
#

"""Python target-profile requirement and capability-preflight regressions."""

# jig-ignore-next-line: indivisible reviewed identifier
# ruff: file-ignore[magic-value-comparison, pytest-raises-too-broad, undocumented-public-function]

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from dataclasses import replace
import json
from pathlib import Path
from typing import cast

import pytest
from scripts.validate import profile_requirements as requirements
from scripts.validate import target_profile

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "malbolge.json"
CURRENT_ID = "malbolge-2026"
TRANSITION_ID = "malbolge-2026.1"
HISTORICAL_ID = "malbolge-1998"
CURRENT_WORDS = 14_348_907
CURRENT_TRITS = 15
HISTORICAL_WORDS = 59_049
PROFILED_BACKEND_WORDS = 3_486_784_401
PROFILED_BACKEND_TRITS = 20
CURRENT_RUNTIME_DIAGNOSTIC = (
    "MALBOLGE-PROFILE-001 profile=malbolge-2026 version=2026 "
    "required_features=byte-input,byte-output,crazy-operation,deterministic,"
    "post-instruction-encryption,rotate,self-modification,sequential-guest "
    "required_word_trits=15 required_memory_words=14348907 "
    "runtime=safe-rust-classic max_word_trits=10 max_memory_words=59049 "
    "missing=word-trits,memory-words"
)
HISTORICAL_CAPACITY_DIAGNOSTIC = (
    "MALBOLGE-PROFILE-002 profile=malbolge-1998 version=1998 "
    "constraint=historical-profile-ceiling required_memory_words=59050 "
    "profile_memory_words=59049"
)


def _document() -> target_profile.JsonObject:
    return target_profile.load_document(PROFILE_PATH)


def _requirement(
    profile_id: str = CURRENT_ID,
    *,
    required_memory_words: int | None = None,
) -> requirements.ProfileRequirement:
    memory_words = (
        CURRENT_WORDS
        if required_memory_words is None
        else required_memory_words
    )
    return requirements.build_profile_requirement(
        _document(),
        profile_id,
        required_memory_words=memory_words,
    )


def _runtime(
    *,
    capability_id: str = "runtime.test",
    features: tuple[str, ...] = requirements.NORMATIVE_PROFILE_FEATURES,
    max_memory_words: int = CURRENT_WORDS,
    max_word_trits: int = CURRENT_TRITS,
) -> requirements.RuntimeCapability:
    return requirements.build_runtime_capability(
        capability_id=capability_id,
        features=features,
        max_memory_words=max_memory_words,
        max_word_trits=max_word_trits,
    )


def test_current_requirement_is_derived_from_canonical_document() -> None:
    value = _requirement()

    assert value.profile_id == CURRENT_ID
    assert value.version == "2026"
    assert value.kind == target_profile.CURRENT_KIND
    assert value.word_trits == CURRENT_TRITS
    assert value.memory_words == CURRENT_WORDS
    assert value.required_memory_words == CURRENT_WORDS
    assert value.required_features == requirements.NORMATIVE_PROFILE_FEATURES


def test_transition_requirement_retains_exact_identity() -> None:
    value = _requirement(
        TRANSITION_ID,
        required_memory_words=HISTORICAL_WORDS,
    )

    assert value.profile_id == TRANSITION_ID
    assert value.version == "2026.1"
    assert value.kind == target_profile.VERSIONED_KIND
    assert value.word_trits == 10
    assert value.memory_words == HISTORICAL_WORDS


def test_historical_requirement_retains_exact_ceiling() -> None:
    value = _requirement(
        HISTORICAL_ID,
        required_memory_words=HISTORICAL_WORDS,
    )

    assert value.kind == target_profile.HISTORICAL_KIND
    assert value.version == "1998"
    assert value.word_trits == 10
    assert value.memory_words == HISTORICAL_WORDS


def test_safe_rust_capabilities_are_explicit() -> None:
    classic = requirements.safe_rust_classic_capability()
    profiled = requirements.safe_rust_profiled_capability()

    assert classic.capability_id == "safe-rust-classic"
    assert classic.max_word_trits == 10
    assert classic.max_memory_words == HISTORICAL_WORDS
    assert profiled.capability_id == "safe-rust-profiled"
    assert profiled.max_word_trits == PROFILED_BACKEND_TRITS
    assert profiled.max_memory_words == PROFILED_BACKEND_WORDS
    assert classic.features == requirements.NORMATIVE_PROFILE_FEATURES
    assert profiled.features == requirements.NORMATIVE_PROFILE_FEATURES


def test_profiled_runtime_capacity_does_not_follow_current_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged = deepcopy(_document())
    profiles = cast("dict[str, object]", forged["profiles"])
    current = cast("dict[str, object]", profiles[CURRENT_ID])
    forged_trits = CURRENT_TRITS + 1
    forged_words = 3**forged_trits
    cast("dict[str, object]", current["word"])["trits"] = forged_trits
    cast("dict[str, object]", current["word"])["modulus"] = forged_words
    cast("dict[str, object]", current["memory"])["words"] = forged_words
    semantics = cast("dict[str, object]", current["semantics"])
    semantics["eof_word"] = forged_words - 1
    alternate = tmp_path / "malbolge.json"
    _ = alternate.write_text(json.dumps(forged), encoding="utf-8")
    monkeypatch.setattr(target_profile, "DEFAULT_PROFILE", alternate)
    target_profile.validate_document(target_profile.load_document(alternate))

    capability = requirements.safe_rust_profiled_capability()

    assert capability.max_word_trits == PROFILED_BACKEND_TRITS
    assert capability.max_memory_words == PROFILED_BACKEND_WORDS


def test_profiled_runtime_boundary_is_largest_u32_ternary_geometry() -> None:
    """The profiled backend limit is representation capacity, not current N."""
    capability = requirements.safe_rust_profiled_capability()

    assert capability.max_memory_words == 3**capability.max_word_trits
    assert capability.max_memory_words <= (1 << 32) - 1
    assert 3 ** (capability.max_word_trits + 1) > (1 << 32) - 1


def test_current_classic_diagnostic_matches_rust_byte_for_byte() -> None:
    with pytest.raises(requirements.ProfileRequirementError) as caught:
        requirements.preflight_profile_requirement(
            _requirement(),
            requirements.safe_rust_classic_capability(),
        )

    error = caught.value
    assert (
        error.kind
        is requirements.ProfileRequirementErrorKind.RUNTIME_CAPABILITY_MISSING
    )
    assert error.code == "MALBOLGE-PROFILE-001"
    assert error.missing_dimensions == ("word-trits", "memory-words")
    assert str(error) == CURRENT_RUNTIME_DIAGNOSTIC


def test_current_profiled_capability_is_admitted() -> None:
    requirements.preflight_profile_requirement(
        _requirement(),
        requirements.safe_rust_profiled_capability(),
    )


def test_transition_classic_capability_is_admitted() -> None:
    requirements.preflight_profile_requirement(
        _requirement(
            TRANSITION_ID,
            required_memory_words=HISTORICAL_WORDS,
        ),
        requirements.safe_rust_classic_capability(),
    )


def test_historical_classic_capability_is_admitted() -> None:
    requirements.preflight_profile_requirement(
        _requirement(
            HISTORICAL_ID,
            required_memory_words=HISTORICAL_WORDS,
        ),
        requirements.safe_rust_classic_capability(),
    )


def test_historical_capacity_diagnostic_matches_rust_byte_for_byte() -> None:
    requirement = _requirement(
        HISTORICAL_ID,
        required_memory_words=HISTORICAL_WORDS + 1,
    )

    with pytest.raises(requirements.ProfileRequirementError) as caught:
        requirements.preflight_profile_requirement(
            requirement,
            requirements.safe_rust_classic_capability(),
        )

    error = caught.value
    assert (
        error.kind
        is requirements.ProfileRequirementErrorKind.PROFILE_CAPACITY_EXCEEDED
    )
    assert error.code == "MALBOLGE-PROFILE-002"
    assert error.missing_dimensions == ()
    assert str(error) == HISTORICAL_CAPACITY_DIAGNOSTIC


def test_current_capacity_diagnostic_names_profile_ceiling() -> None:
    requirement = _requirement(required_memory_words=CURRENT_WORDS + 1)

    with pytest.raises(requirements.ProfileRequirementError) as caught:
        requirements.preflight_profile_requirement(
            requirement,
            requirements.safe_rust_profiled_capability(),
        )

    assert "constraint=profile-capacity-ceiling" in str(caught.value)
    assert "profile_memory_words=14348907" in str(caught.value)


def test_profile_capacity_failure_precedes_runtime_failure() -> None:
    requirement = _requirement(required_memory_words=CURRENT_WORDS + 1)
    runtime = _runtime(max_memory_words=1, max_word_trits=1)

    with pytest.raises(requirements.ProfileRequirementError) as caught:
        requirements.preflight_profile_requirement(requirement, runtime)

    assert (
        caught.value.kind
        is requirements.ProfileRequirementErrorKind.PROFILE_CAPACITY_EXCEEDED
    )
    assert caught.value.code == "MALBOLGE-PROFILE-002"


def test_word_width_missing_dimension_is_exact() -> None:
    runtime = _runtime(max_word_trits=13)

    with pytest.raises(requirements.ProfileRequirementError) as caught:
        requirements.preflight_profile_requirement(_requirement(), runtime)

    assert caught.value.missing_dimensions == ("word-trits",)
    assert str(caught.value).endswith("missing=word-trits")


def test_memory_missing_dimension_is_exact() -> None:
    runtime = _runtime(max_memory_words=CURRENT_WORDS - 1)

    with pytest.raises(requirements.ProfileRequirementError) as caught:
        requirements.preflight_profile_requirement(_requirement(), runtime)

    assert caught.value.missing_dimensions == ("memory-words",)
    assert str(caught.value).endswith("missing=memory-words")


def test_missing_feature_follows_geometry_dimensions() -> None:
    features = requirements.NORMATIVE_PROFILE_FEATURES[:-1]
    runtime = _runtime(
        features=features,
        max_memory_words=HISTORICAL_WORDS,
        max_word_trits=10,
    )

    with pytest.raises(requirements.ProfileRequirementError) as caught:
        requirements.preflight_profile_requirement(_requirement(), runtime)

    assert caught.value.missing_dimensions == (
        "word-trits",
        "memory-words",
        "sequential-guest",
    )


def test_runtime_feature_subset_is_allowed_when_canonical() -> None:
    value = _runtime(features=requirements.NORMATIVE_PROFILE_FEATURES[:3])

    assert value.features == requirements.NORMATIVE_PROFILE_FEATURES[:3]


def test_runtime_feature_order_must_be_canonical() -> None:
    reversed_features = tuple(reversed(requirements.NORMATIVE_PROFILE_FEATURES))

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="not canonically ordered",
    ):
        _ = _runtime(features=reversed_features)


def test_runtime_features_reject_duplicates() -> None:
    features = (
        requirements.NORMATIVE_PROFILE_FEATURES[0],
        requirements.NORMATIVE_PROFILE_FEATURES[0],
    )

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="duplicates",
    ):
        _ = _runtime(features=features)


def test_runtime_features_reject_unhashable_foreign_member() -> None:
    foreign = cast("str", cast("object", []))
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="unsupported feature",
    ):
        _ = _runtime(features=(foreign,))


def test_runtime_features_reject_unknown_feature() -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="unsupported feature",
    ):
        _ = _runtime(features=("host-filesystem",))


def test_runtime_features_require_exact_tuple() -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="exact immutable tuple",
    ):
        _ = _runtime(
            features=cast(
                "tuple[str, ...]",
                cast("object", list(requirements.NORMATIVE_PROFILE_FEATURES)),
            )
        )


@pytest.mark.parametrize(
    "capability_id",
    ["", "bad capability", cast("str", object())],
)
def test_runtime_identity_requires_canonical_ascii(capability_id: str) -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="canonical ASCII identity",
    ):
        _ = _runtime(capability_id=capability_id)


@pytest.mark.parametrize("value", [0, -1, True])
def test_runtime_memory_limit_requires_positive_integer(value: int) -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="positive integer",
    ):
        _ = _runtime(max_memory_words=value)


@pytest.mark.parametrize("value", [0, -1, True])
def test_runtime_word_limit_requires_positive_integer(value: int) -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="positive integer",
    ):
        _ = _runtime(max_word_trits=value)


def test_zero_required_memory_matches_rust_preflight_domain() -> None:
    requirement = _requirement(required_memory_words=0)
    assert requirement.required_memory_words == 0
    requirements.preflight_profile_requirement(
        requirement,
        requirements.safe_rust_profiled_capability(),
    )


@pytest.mark.parametrize("required_memory_words", [-1, True])
def test_required_memory_requires_non_negative_integer(
    required_memory_words: int,
) -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="non-negative integer",
    ):
        _ = requirements.build_profile_requirement(
            _document(),
            CURRENT_ID,
            required_memory_words=required_memory_words,
        )


@pytest.mark.parametrize(
    "profile_id",
    ["", "bad profile", cast("str", object())],
)
def test_profile_identity_requires_canonical_ascii(profile_id: str) -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="canonical ASCII identity",
    ):
        _ = requirements.build_profile_requirement(
            _document(),
            profile_id,
            required_memory_words=1,
        )


def test_unknown_profile_never_falls_back() -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="unknown profile identity",
    ):
        _ = requirements.build_profile_requirement(
            _document(),
            "malbolge-current-ish",
            required_memory_words=1,
        )


def test_invalid_canonical_document_fails_before_requirement_build() -> None:
    document = _document()
    document["schema_version"] = 999

    with pytest.raises(target_profile.ProfileValidationError):
        _ = requirements.build_profile_requirement(
            document,
            CURRENT_ID,
            required_memory_words=1,
        )


def test_requirement_build_does_not_mutate_document() -> None:
    document = _document()
    before = deepcopy(document)

    _ = requirements.build_profile_requirement(
        document,
        CURRENT_ID,
        required_memory_words=1,
    )

    assert document == before


def test_requirement_and_runtime_are_immutable() -> None:
    requirement = _requirement()
    runtime = _runtime()

    requirement_field = "profile_id"
    runtime_field = "max_memory_words"
    with pytest.raises(FrozenInstanceError):
        setattr(requirement, requirement_field, HISTORICAL_ID)
    with pytest.raises(FrozenInstanceError):
        setattr(runtime, runtime_field, 1)


def test_preflight_rejects_foreign_requirement_type() -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="exact immutable type",
    ):
        requirements.preflight_profile_requirement(
            cast("requirements.ProfileRequirement", object()),
            _runtime(),
        )


def test_preflight_rejects_foreign_runtime_type() -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="exact immutable type",
    ):
        requirements.preflight_profile_requirement(
            _requirement(),
            cast("requirements.RuntimeCapability", object()),
        )


def test_preflight_contains_unavailable_canonical_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requirement = _requirement(required_memory_words=1)
    missing = tmp_path / "missing-malbolge.json"
    monkeypatch.setattr(target_profile, "DEFAULT_PROFILE", missing)

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="canonical profile authority is unavailable or invalid",
    ):
        requirements.preflight_profile_requirement(requirement, _runtime())


def test_preflight_contains_invalid_canonical_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requirement = _requirement(required_memory_words=1)
    invalid = tmp_path / "malbolge.json"
    _ = invalid.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(target_profile, "DEFAULT_PROFILE", invalid)

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="canonical profile authority is unavailable or invalid",
    ):
        requirements.preflight_profile_requirement(requirement, _runtime())


def test_preflight_revalidates_tampered_requirement() -> None:
    tampered = replace(
        _requirement(),
        required_features=("byte-input",),
    )

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="normative feature set",
    ):
        requirements.preflight_profile_requirement(tampered, _runtime())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kind", target_profile.HISTORICAL_KIND),
        ("version", "forged-version"),
        ("word_trits", CURRENT_TRITS + 1),
        ("memory_words", CURRENT_WORDS + 1),
    ],
)
def test_preflight_rejects_tampered_canonical_profile_fields(
    field: str, value: object
) -> None:
    tampered = replace(_requirement(), **{field: value})

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="must match canonical profile authority",
    ):
        requirements.preflight_profile_requirement(tampered, _runtime())


def test_preflight_cannot_inflate_historical_profile_capacity() -> None:
    historical = requirements.build_profile_requirement(
        _document(),
        HISTORICAL_ID,
        required_memory_words=HISTORICAL_WORDS + 1,
    )
    forged = replace(historical, memory_words=HISTORICAL_WORDS + 1)
    oversized_runtime = _runtime(
        max_memory_words=HISTORICAL_WORDS + 1,
        max_word_trits=historical.word_trits,
    )

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="must match canonical profile authority",
    ):
        requirements.preflight_profile_requirement(forged, oversized_runtime)


def test_preflight_rejects_valid_noncanonical_profile_document() -> None:
    forged = deepcopy(_document())
    profiles = cast("dict[str, object]", forged["profiles"])
    current = cast("dict[str, object]", profiles[CURRENT_ID])
    forged_trits = CURRENT_TRITS + 1
    forged_words = 3**forged_trits
    cast("dict[str, object]", current["word"])["trits"] = forged_trits
    cast("dict[str, object]", current["word"])["modulus"] = forged_words
    cast("dict[str, object]", current["memory"])["words"] = forged_words
    semantics = cast("dict[str, object]", current["semantics"])
    semantics["eof_word"] = forged_words - 1
    target_profile.validate_document(forged)
    requirement = requirements.build_profile_requirement(
        forged,
        CURRENT_ID,
        required_memory_words=1,
    )
    runtime = _runtime(
        max_memory_words=forged_words,
        max_word_trits=forged_trits,
    )

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="must match canonical profile authority",
    ):
        requirements.preflight_profile_requirement(requirement, runtime)


def test_preflight_rejects_direct_unknown_profile_identity() -> None:
    forged = replace(_requirement(), profile_id="malbolge-invented")

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="unknown profile identity",
    ):
        requirements.preflight_profile_requirement(forged, _runtime())


def test_preflight_revalidates_tampered_runtime() -> None:
    tampered = replace(
        _runtime(),
        features=tuple(reversed(requirements.NORMATIVE_PROFILE_FEATURES)),
    )

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="not canonically ordered",
    ):
        requirements.preflight_profile_requirement(_requirement(), tampered)


@pytest.mark.parametrize(
    "runtime",
    [
        replace(
            requirements.safe_rust_classic_capability(),
            max_memory_words=CURRENT_WORDS,
            max_word_trits=CURRENT_TRITS,
        ),
        replace(
            requirements.safe_rust_profiled_capability(),
            max_memory_words=CURRENT_WORDS - 1,
        ),
    ],
)
def test_preflight_rejects_forged_reserved_runtime(
    runtime: requirements.RuntimeCapability,
) -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="reserved runtime fields must match canonical runtime authority",
    ):
        requirements.preflight_profile_requirement(_requirement(), runtime)


def test_forged_classic_runtime_cannot_admit_current_profile() -> None:
    forged = replace(
        requirements.safe_rust_classic_capability(),
        max_memory_words=CURRENT_WORDS,
        max_word_trits=CURRENT_TRITS,
    )

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="reserved runtime fields must match canonical runtime authority",
    ):
        requirements.preflight_profile_requirement(_requirement(), forged)


def test_repeated_failure_text_is_deterministic() -> None:
    requirement = _requirement()
    runtime = requirements.safe_rust_classic_capability()
    messages: list[str] = []

    for _ in range(2):
        with pytest.raises(requirements.ProfileRequirementError) as caught:
            requirements.preflight_profile_requirement(requirement, runtime)
        messages.append(str(caught.value))

    assert messages == [CURRENT_RUNTIME_DIAGNOSTIC, CURRENT_RUNTIME_DIAGNOSTIC]


def test_error_retains_exact_requirement_and_runtime() -> None:
    requirement = _requirement()
    runtime = requirements.safe_rust_classic_capability()

    with pytest.raises(requirements.ProfileRequirementError) as caught:
        requirements.preflight_profile_requirement(requirement, runtime)

    assert caught.value.requirement is requirement
    assert caught.value.runtime is runtime


def test_direct_error_construction_requires_exact_canonical_contract() -> None:
    requirement = _requirement()
    runtime = requirements.safe_rust_classic_capability()
    foreign_kind: object = "runtime-capability-missing"
    mutable_dimensions: object = ["word-trits", "memory-words"]
    runtime_missing_kind = (
        requirements.ProfileRequirementErrorKind.RUNTIME_CAPABILITY_MISSING
    )

    cases = (
        (
            lambda: requirements.ProfileRequirementError(
                cast(
                    "requirements.ProfileRequirementErrorKind",
                    cast("object", foreign_kind),
                ),
                requirement,
                runtime,
                missing_dimensions=("word-trits", "memory-words"),
            ),
            "diagnostic kind must use the exact enum type",
        ),
        (
            lambda: requirements.ProfileRequirementError(
                runtime_missing_kind,
                requirement,
                runtime,
                missing_dimensions=cast(
                    "tuple[str, ...]",
                    cast("object", mutable_dimensions),
                ),
            ),
            "missing dimensions must use the exact immutable tuple",
        ),
        (
            lambda: requirements.ProfileRequirementError(
                runtime_missing_kind,
                requirement,
                runtime,
                missing_dimensions=("memory-words", "word-trits"),
            ),
            "missing dimensions do not match the preflight rejection",
        ),
        (
            lambda: requirements.ProfileRequirementError(
                runtime_missing_kind,
                requirement,
                runtime,
                missing_dimensions=("unknown",),
            ),
            "missing dimensions do not match the preflight rejection",
        ),
    )
    for construct, message in cases:
        with pytest.raises(
            requirements.ProfileRequirementValidationError,
            match=message,
        ):
            _ = construct()


def test_direct_error_construction_rejects_admitted_pair() -> None:
    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="requires a rejected profile preflight",
    ):
        _ = requirements.ProfileRequirementError(
            requirements.ProfileRequirementErrorKind.RUNTIME_CAPABILITY_MISSING,
            _requirement(),
            requirements.safe_rust_profiled_capability(),
            missing_dimensions=(),
        )


def test_direct_error_preserves_profile_capacity_precedence() -> None:
    requirement = _requirement(required_memory_words=CURRENT_WORDS + 1)
    runtime = _runtime(max_memory_words=1, max_word_trits=1)

    with pytest.raises(
        requirements.ProfileRequirementValidationError,
        match="kind does not match the preflight rejection",
    ):
        _ = requirements.ProfileRequirementError(
            requirements.ProfileRequirementErrorKind.RUNTIME_CAPABILITY_MISSING,
            requirement,
            runtime,
            missing_dimensions=("word-trits", "memory-words"),
        )
