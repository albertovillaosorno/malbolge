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
#   - Functional regression coverage for the research width-certificate module.
# - Must-Not:
#   - Treat research acceptance as trusted runtime profile selection.
# - Allows:
#   - Inputs: explicit finite systems and candidate-width result maps.
#   - Outputs: fail-closed checker and selector assertions.
#   - Side effects: none.
# - Split-When:
#   - A trusted certificate verifier gains an independent product owner.
# - Merge-When:
#   - Another test owns this exact research API boundary.
# - Summary:
#   - Functional tests for experimental profile-width certificate checking.
# - Description:
#   - Exercises public research APIs independently from correspondence tests.
# - Usage:
#   - Runs with the malbolge-specific optimization research test surface.
# - Defaults:
#   - Incomplete or invalid evidence returns canonical width or false.
#

"""Functional tests for the experimental profile-width certificate module."""

from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from algorithms.profile_width.certificate import CANONICAL_WIDTH
from algorithms.profile_width.certificate import FiniteSystem
from algorithms.profile_width.certificate import MINIMUM_WIDTH
from algorithms.profile_width.certificate import certificate_valid
from algorithms.profile_width.certificate import finite_width_certificate_valid
from algorithms.profile_width.certificate import (
    initial_halt_projection_certifiable,
)
from algorithms.profile_width.certificate import minimum_certified_width
from algorithms.profile_width.certificate import minimum_width_from_certificates
from algorithms.profile_width.certificate import parse_finite_width_certificate

from verifier.emitted_malbolge_classic import decode as verifier_decode

if TYPE_CHECKING:
    from algorithms.profile_width.certificate import JsonValue


def test_certificate_fails_closed_when_state_surface_is_missing() -> None:
    """A relation cannot authorize a state missing from the declared surface."""
    wide = FiniteSystem(
        initial={"input": "w0"},
        observation={"w0": (0,)},
        successor={"w0": None},
    )
    narrow = FiniteSystem(
        initial={"input": "n0"},
        observation={},
        successor={"n0": None},
    )
    relation = frozenset({("w0", "n0")})
    assert not certificate_valid(wide, narrow, relation)


def test_selector_fails_closed_on_missing_or_invalid_result() -> None:
    """Incomplete or non-boolean certificate results retain width fourteen."""
    missing = {10: True, 11: True, 12: True}
    assert minimum_certified_width(missing) == CANONICAL_WIDTH

    invalid: dict[int, bool] = {10: True, 11: True, 12: True, 13: True}
    invalid[12] = 1  # pyright: ignore[reportArgumentType] - invalid fixture.
    assert minimum_certified_width(invalid) == CANONICAL_WIDTH


_FIXTURE = Path(__file__).with_name("fixtures") / "qp-width-certificate-v1.json"
_QP_SUBJECT_ID = "qp-halt-current14-to-historical10"
_GRAPHICAL = range(33, 127)
_LOAD_OPCODES = frozenset(b"ji*p</vo")
_DECODE_PHASES = 94


def _fixture_value() -> dict[str, JsonValue]:
    loaded = cast("JsonValue", json.loads(_FIXTURE.read_text(encoding="utf-8")))
    assert isinstance(loaded, dict)
    return loaded


def test_qp_fixture_is_accepted_by_research_certificate_checker() -> None:
    """The projection-preserving QP fixture forms a closed finite relation."""
    certificate = parse_finite_width_certificate(_fixture_value())
    assert certificate is not None
    assert certificate.subject_id == _QP_SUBJECT_ID
    assert (
        certificate.wide.initial["byte-a5"]
        != certificate.wide.initial["eof"]
    )
    assert (
        certificate.narrow.initial["byte-a5"]
        != certificate.narrow.initial["eof"]
    )
    assert finite_width_certificate_valid(certificate)


def test_certificate_parser_rejects_schema_and_surface_drift() -> None:
    """Unknown fields, duplicate inputs, or unclosed states fail closed."""
    base = _fixture_value()
    assert isinstance(base, dict)

    extra = copy.deepcopy(base)
    extra["unexpected"] = True
    assert parse_finite_width_certificate(extra) is None

    duplicate_input = copy.deepcopy(base)
    duplicate_input["input_ids"] = ["byte-a5", "byte-a5"]
    assert parse_finite_width_certificate(duplicate_input) is None

    missing_observation = copy.deepcopy(base)
    wide = cast("dict[str, JsonValue]", missing_observation["wide"])
    observation = cast("dict[str, JsonValue]", wide["observation"])
    _ = observation.pop("w-byte-1")
    certificate = parse_finite_width_certificate(missing_observation)
    assert certificate is not None
    assert not finite_width_certificate_valid(certificate)

    wrong_arity = copy.deepcopy(base)
    wide = cast("dict[str, JsonValue]", wrong_arity["wide"])
    observation = cast("dict[str, JsonValue]", wide["observation"])
    observation["w-byte-0"] = [0, 0]
    certificate = parse_finite_width_certificate(wrong_arity)
    assert certificate is not None
    assert not finite_width_certificate_valid(certificate)


def test_certificate_parser_rejects_ambiguous_scalar_types_and_widths() -> None:
    """Ambiguous scalar types and invalid width ordering fail closed."""
    base = _fixture_value()
    assert isinstance(base, dict)

    boolean_width = copy.deepcopy(base)
    boolean_width["narrow_width"] = True
    assert parse_finite_width_certificate(boolean_width) is None

    reversed_width = copy.deepcopy(base)
    reversed_width["wide_width"] = 10
    reversed_width["narrow_width"] = 14
    certificate = parse_finite_width_certificate(reversed_width)
    assert certificate is not None
    assert not finite_width_certificate_valid(certificate)


def test_selector_requires_certificates_for_positive_width_decisions() -> None:
    """A bare true result cannot replace a checked certificate."""
    certificate = parse_finite_width_certificate(_fixture_value())
    assert certificate is not None
    decisions = {10: certificate, 11: False, 12: False, 13: False}
    assert minimum_width_from_certificates(decisions) == MINIMUM_WIDTH

    authority_free = {10: True, 11: False, 12: False, 13: False}
    assert minimum_width_from_certificates(authority_free) == CANONICAL_WIDTH

    missing = {10: certificate, 11: False, 12: False}
    assert minimum_width_from_certificates(missing) == CANONICAL_WIDTH


def test_selector_rejects_certificate_width_mismatch() -> None:
    """A valid relation cannot authorize a different candidate-width key."""
    certificate = parse_finite_width_certificate(_fixture_value())
    assert certificate is not None
    decisions = {10: False, 11: certificate, 12: False, 13: False}
    assert minimum_width_from_certificates(decisions) == CANONICAL_WIDTH


def test_initial_halt_checker_certifies_qp_from_semantic_premises() -> None:
    """QP satisfies the initial-halt theorem at endpoint checked widths."""
    assert initial_halt_projection_certifiable(
        b"QP",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
    )
    assert initial_halt_projection_certifiable(
        b"Q P\n",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
    )


def test_initial_halt_checker_rejects_invalid_or_nonhalting_sources() -> None:
    """Invalid widths, source, or first opcode fail closed."""
    assert not initial_halt_projection_certifiable(
        b"QP",
        CANONICAL_WIDTH,
        MINIMUM_WIDTH,
    )
    assert not initial_halt_projection_certifiable(
        b"Q",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
    )
    assert not initial_halt_projection_certifiable(
        b"Q\x80",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
    )
    assert not initial_halt_projection_certifiable(
        b"PP",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
    )


def _verifier_admitted_cell(position: int) -> int:
    for cell in _GRAPHICAL:
        decoded = verifier_decode(cell, position)
        if decoded in _LOAD_OPCODES:
            return cell
    raise AssertionError


def test_initial_halt_checker_matches_verifier_admission_surface() -> None:
    """Research source decisions match the independent verifier decode model."""
    second = _verifier_admitted_cell(1)
    for first in _GRAPHICAL:
        expected = verifier_decode(first, 0) == ord("v")
        observed = initial_halt_projection_certifiable(
            bytes((first, second)),
            MINIMUM_WIDTH,
            CANONICAL_WIDTH,
        )
        assert observed == expected

    prefix = [ord("Q")]
    for position in range(1, _DECODE_PHASES):
        for cell in _GRAPHICAL:
            decoded = verifier_decode(cell, position)
            expected = decoded in _LOAD_OPCODES
            observed = initial_halt_projection_certifiable(
                bytes((*prefix, cell)),
                MINIMUM_WIDTH,
                CANONICAL_WIDTH,
            )
            assert observed == expected
        prefix.append(_verifier_admitted_cell(position))


def test_direct_certificate_cannot_bypass_metadata_checks() -> None:
    """Dataclass callers cannot bypass parser-owned metadata invariants."""
    certificate = parse_finite_width_certificate(_fixture_value())
    assert certificate is not None
    assert not finite_width_certificate_valid(
        replace(certificate, schema_version=certificate.schema_version + 1)
    )
    empty_subject = replace(certificate, subject_id="")
    assert not finite_width_certificate_valid(empty_subject)
    assert not finite_width_certificate_valid(
        replace(certificate, input_ids=("eof", "eof"))
    )
    assert not finite_width_certificate_valid(
        replace(certificate, observation_fields=("output_len", "output_len"))
    )
