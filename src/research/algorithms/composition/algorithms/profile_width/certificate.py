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
#   - Research-only finite width-relation checking and width selection.
# - Must-Not:
#   - Change runtime profiles or claim trusted-verifier authority.
# - Allows:
#   - Inputs: explicit finite systems, relations, and width certificate results.
#   - Outputs: deterministic certificate validity and fail-closed width choice.
#   - Side effects: none.
# - Split-When:
#   - A trusted product verifier or serialized certificate format is promoted.
# - Merge-When:
#   - Another research module owns the same finite lockstep certificate logic.
# - Summary:
#   - Experimental finite profile-width certificate checker and selector.
# - Description:
#   - Checks initial coverage, observations, lockstep edges, and width results.
# - Usage:
#   - Mathematical evidence exercises this module before any product promotion.
# - Defaults:
#   - Missing surfaces or width results fail closed to the canonical width.
#

"""Research-only finite profile-width certificate checking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Mapping

MINIMUM_WIDTH: Final = 10
CANONICAL_WIDTH: Final = 14
CERTIFICATE_SCHEMA_VERSION: Final = 1
_CERTIFICATE_KEYS: Final = frozenset(
    {
        "schema_version",
        "subject_id",
        "wide_width",
        "narrow_width",
        "input_ids",
        "observation_fields",
        "wide",
        "narrow",
        "relation",
    }
)


type WidthRelation = frozenset[tuple[str, str]]
type WidthCertificateDecision = FiniteWidthCertificate | bool
type JsonValue = (
    bool | int | str | list[JsonValue] | dict[str, JsonValue] | None
)


@dataclass(frozen=True, slots=True)
class FiniteSystem:
    """One explicit deterministic finite system used by a width certificate."""

    initial: Mapping[str, str]
    observation: Mapping[str, tuple[int, ...]]
    successor: Mapping[str, str | None]


@dataclass(frozen=True, slots=True)
class FiniteWidthCertificate:
    """One parsed research-only finite profile-width certificate."""

    input_ids: tuple[str, ...]
    observation_fields: tuple[str, ...]
    narrow_width: int
    relation: WidthRelation
    subject_id: str
    wide_width: int
    wide: FiniteSystem
    narrow: FiniteSystem


def _exact_int(value: JsonValue) -> int | None:
    return value if type(value) is int else None


def _string(value: JsonValue) -> str | None:
    return value if isinstance(value, str) and value else None


def _exact_object(
    value: JsonValue,
    expected: frozenset[str],
) -> dict[str, JsonValue] | None:
    if not isinstance(value, dict) or frozenset(value) != expected:
        return None
    return value


def _parse_string_map(value: JsonValue) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    parsed: dict[str, str] = {}
    for key, item in value.items():
        parsed_item = _string(item)
        if parsed_item is None:
            return None
        parsed[key] = parsed_item
    return parsed


def _integer_tuple(value: JsonValue) -> tuple[int, ...] | None:
    if not isinstance(value, list):
        return None
    parsed = tuple(_exact_int(item) for item in value)
    if any(item is None for item in parsed):
        return None
    return tuple(item for item in parsed if item is not None)


def _parse_observations(
    value: JsonValue,
) -> dict[str, tuple[int, ...]] | None:
    if not isinstance(value, dict):
        return None
    parsed: dict[str, tuple[int, ...]] = {}
    for key, items in value.items():
        observation = _integer_tuple(items)
        if observation is None:
            return None
        parsed[key] = observation
    return parsed


def _parse_successors(value: JsonValue) -> dict[str, str | None] | None:
    if not isinstance(value, dict):
        return None
    parsed: dict[str, str | None] = {}
    for key, item in value.items():
        if item is None:
            parsed[key] = None
            continue
        parsed_item = _string(item)
        if parsed_item is None:
            return None
        parsed[key] = parsed_item
    return parsed


def _parse_system(value: JsonValue) -> FiniteSystem | None:
    expected = frozenset({"initial", "observation", "successor"})
    raw = _exact_object(value, expected)
    if raw is None:
        return None
    initial = _parse_string_map(raw["initial"])
    observation = _parse_observations(raw["observation"])
    successor = _parse_successors(raw["successor"])
    if initial is None or observation is None or successor is None:
        return None
    return FiniteSystem(
        initial=initial,
        observation=observation,
        successor=successor,
    )


def _parse_unique_strings(value: JsonValue) -> tuple[str, ...] | None:
    if not isinstance(value, list) or not value:
        return None
    parsed = tuple(_string(item) for item in value)
    strings = tuple(item for item in parsed if item is not None)
    valid = len(strings) == len(parsed) and len(set(strings)) == len(strings)
    return strings if valid else None


def _parse_relation_pair(value: JsonValue) -> tuple[str, str] | None:
    relation_pair_size = 2
    if not isinstance(value, list) or len(value) != relation_pair_size:
        return None
    wide_state = _string(value[0])
    narrow_state = _string(value[1])
    if wide_state is None or narrow_state is None:
        return None
    return wide_state, narrow_state


def _parse_relation(value: JsonValue) -> WidthRelation | None:
    if not isinstance(value, list) or not value:
        return None
    parsed = tuple(_parse_relation_pair(item) for item in value)
    pairs = tuple(pair for pair in parsed if pair is not None)
    valid = len(pairs) == len(parsed) and len(set(pairs)) == len(pairs)
    return frozenset(pairs) if valid else None


def _certificate_parts_valid(
    parts: tuple[object | None, ...],
) -> bool:
    return all(part is not None for part in parts)


def parse_finite_width_certificate(
    value: JsonValue,
) -> FiniteWidthCertificate | None:
    """Parse one strict schema-v1 research certificate or fail closed.

    Returns:
        The parsed certificate, or None when schema or values are invalid.

    """
    raw = _exact_object(value, _CERTIFICATE_KEYS)
    if raw is None:
        return None
    schema_version = _exact_int(raw["schema_version"])
    subject_id = _string(raw["subject_id"])
    wide_width = _exact_int(raw["wide_width"])
    narrow_width = _exact_int(raw["narrow_width"])
    input_ids = _parse_unique_strings(raw["input_ids"])
    observation_fields = _parse_unique_strings(raw["observation_fields"])
    wide = _parse_system(raw["wide"])
    narrow = _parse_system(raw["narrow"])
    relation = _parse_relation(raw["relation"])
    if (
        schema_version != CERTIFICATE_SCHEMA_VERSION
        or not _certificate_parts_valid(
            (
                subject_id,
                wide_width,
                narrow_width,
                input_ids,
                observation_fields,
                wide,
                narrow,
                relation,
            )
        )
    ):
        return None
    return FiniteWidthCertificate(
        input_ids=cast("tuple[str, ...]", input_ids),
        observation_fields=cast("tuple[str, ...]", observation_fields),
        narrow_width=cast("int", narrow_width),
        relation=cast("WidthRelation", relation),
        subject_id=cast("str", subject_id),
        wide_width=cast("int", wide_width),
        wide=cast("FiniteSystem", wide),
        narrow=cast("FiniteSystem", narrow),
    )


def finite_width_certificate_valid(certificate: FiniteWidthCertificate) -> bool:
    """Check one parsed certificate without granting product authority.

    Returns:
        True only for checked widths, exact input coverage, and a closed
        relation.

    """
    widths_valid = (
        MINIMUM_WIDTH <= certificate.narrow_width < certificate.wide_width
        <= CANONICAL_WIDTH
    )
    expected_inputs = set(certificate.input_ids)
    inputs_valid = (
        set(certificate.wide.initial) == expected_inputs
        and set(certificate.narrow.initial) == expected_inputs
    )
    observation_arity = len(certificate.observation_fields)
    observations_valid = all(
        len(observation) == observation_arity
        for system in (certificate.wide, certificate.narrow)
        for observation in system.observation.values()
    )
    relation_valid = certificate_valid(
        certificate.wide,
        certificate.narrow,
        certificate.relation,
    )
    return (
        widths_valid
        and inputs_valid
        and observations_valid
        and relation_valid
    )


def _initial_coverage(
    wide: FiniteSystem,
    narrow: FiniteSystem,
    relation: WidthRelation,
) -> bool:
    if set(wide.initial) != set(narrow.initial):
        return False
    return all(
        (wide_state, narrow.initial[input_id]) in relation
        for input_id, wide_state in wide.initial.items()
    )


def _state_present(system: FiniteSystem, state: str) -> bool:
    return state in system.observation and state in system.successor


def _successors_match(
    successors: tuple[str | None, str | None],
    relation: WidthRelation,
) -> bool:
    wide_next, narrow_next = successors
    if wide_next is None or narrow_next is None:
        return wide_next is None and narrow_next is None
    return (wide_next, narrow_next) in relation


def _pair_obligation(
    systems: tuple[FiniteSystem, FiniteSystem],
    relation: WidthRelation,
    pair: tuple[str, str],
) -> bool:
    wide, narrow = systems
    wide_state, narrow_state = pair
    if not (
        _state_present(wide, wide_state)
        and _state_present(narrow, narrow_state)
    ):
        return False
    observations_equal = (
        wide.observation[wide_state] == narrow.observation[narrow_state]
    )
    successors = (
        wide.successor[wide_state],
        narrow.successor[narrow_state],
    )
    return observations_equal and _successors_match(successors, relation)


def certificate_valid(
    wide: FiniteSystem,
    narrow: FiniteSystem,
    relation: WidthRelation,
) -> bool:
    """Return whether one finite lockstep width certificate is complete.

    Returns:
        True only when every declared finite obligation is satisfied.

    """
    return _initial_coverage(wide, narrow, relation) and all(
        _pair_obligation((wide, narrow), relation, pair) for pair in relation
    )


def minimum_certified_width(results: Mapping[int, bool]) -> int:
    """Return the minimum independently certified profile width.

    Returns:
        The smallest accepted width, or canonical width on missing/invalid data.

    """
    candidates = set(range(MINIMUM_WIDTH, CANONICAL_WIDTH))
    if set(results) != candidates:
        return CANONICAL_WIDTH
    if not all(type(results[width]) is bool for width in candidates):
        return CANONICAL_WIDTH
    certified = {width for width in candidates if results[width]}
    return min(certified, default=CANONICAL_WIDTH)


def _certificate_decision(
    width: int,
    decision: WidthCertificateDecision,
) -> bool | None:
    if decision is False:
        return False
    if not isinstance(decision, FiniteWidthCertificate):
        return None
    width_matches = (
        decision.narrow_width == width
        and decision.wide_width == CANONICAL_WIDTH
    )
    accepted = width_matches and finite_width_certificate_valid(decision)
    return True if accepted else None


def minimum_width_from_certificates(
    decisions: Mapping[int, WidthCertificateDecision],
) -> int:
    """Select the minimum width from certificates or explicit rejections.

    Returns:
        The minimum independently proved width, or fourteen on incomplete,
        mismatched, or authority-free acceptance data.

    """
    candidates = set(range(MINIMUM_WIDTH, CANONICAL_WIDTH))
    if set(decisions) != candidates:
        return CANONICAL_WIDTH
    results: dict[int, bool] = {}
    for width in candidates:
        result = _certificate_decision(width, decisions[width])
        if result is None:
            return CANONICAL_WIDTH
        results[width] = result
    return minimum_certified_width(results)
