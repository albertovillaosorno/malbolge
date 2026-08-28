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
from itertools import product
import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from algorithms.profile_width.certificate import CANONICAL_WIDTH
from algorithms.profile_width.certificate import CERTIFICATE_SCHEMA_VERSION
from algorithms.profile_width.certificate import FiniteSystem
from algorithms.profile_width.certificate import INPUT_OUTPUT_HALT_PROOF_KIND
from algorithms.profile_width.certificate import INPUT_THEN_HALT_PROOF_KIND
from algorithms.profile_width.certificate import MINIMUM_WIDTH
from algorithms.profile_width.certificate import NOOP_PREFIX_HALT_PROOF_KIND
from algorithms.profile_width.certificate import STRAIGHT_LINE_SAFE_PROOF_KIND
from algorithms.profile_width.certificate import WidthCertificateSubject
from algorithms.profile_width.certificate import bound_width_certificate_valid
from algorithms.profile_width.certificate import certificate_valid
from algorithms.profile_width.certificate import finite_width_certificate_valid
from algorithms.profile_width.certificate import (
    initial_halt_projection_certifiable,
)
from algorithms.profile_width.certificate import (
    input_output_halt_projection_certifiable,
)
from algorithms.profile_width.certificate import (
    input_then_halt_projection_certifiable,
)
from algorithms.profile_width.certificate import minimum_certified_width
from algorithms.profile_width.certificate import minimum_width_from_certificates
from algorithms.profile_width.certificate import (
    noop_prefix_halt_projection_certifiable,
)
from algorithms.profile_width.certificate import parse_finite_width_certificate
from algorithms.profile_width.certificate import (
    straight_line_projection_certifiable,
)

from verifier.emitted_malbolge_classic import decode as verifier_decode

if TYPE_CHECKING:
    from collections.abc import Mapping

    from algorithms.profile_width.certificate import JsonValue
    from algorithms.profile_width.certificate import WidthCertificateDecision


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


_FIXTURES = Path(__file__).with_name("fixtures")
_FIXTURE_V1 = _FIXTURES / "qp-width-certificate-v1.json"
_FIXTURE_V2 = _FIXTURES / "qp-width-certificate-v2.json"
_COMPOSED_FIXTURE = _FIXTURES / "ucar-safe-width-certificate-v2.json"
_DP_FIXTURE_V2 = _FIXTURES / "dp-noop-halt-width-certificate-v2.json"
_UP_FIXTURE_V2 = _FIXTURES / "up-input-halt-width-certificate-v2.json"
_UBO_FIXTURE_V2 = _FIXTURES / "ubo-input-output-halt-width-certificate-v2.json"
_QP_SUBJECT_ID = "qp-halt-current14-to-historical10"
_GRAPHICAL = range(33, 127)
_LOAD_OPCODES = frozenset(b"ji*p</vo")
_DECODE_PHASES = 94


def _qp_subject() -> WidthCertificateSubject:
    return WidthCertificateSubject(
        source=b"QP",
        inputs={"byte-a5": bytes((165,)), "eof": b""},
    )


def _selected_width(
    decisions: Mapping[int, WidthCertificateDecision],
) -> int:
    return minimum_width_from_certificates(_qp_subject(), decisions)


def _fixture_value(path: Path = _FIXTURE_V2) -> dict[str, JsonValue]:
    loaded = cast("JsonValue", json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(loaded, dict)
    return loaded


def test_qp_fixture_is_accepted_by_research_certificate_checker() -> None:
    """The source-bound QP fixture forms a proved closed finite relation."""
    certificate = parse_finite_width_certificate(_fixture_value())
    assert certificate is not None
    assert certificate.schema_version == CERTIFICATE_SCHEMA_VERSION
    assert certificate.subject_id == _QP_SUBJECT_ID
    assert certificate.source_bytes == (81, 80)
    assert certificate.inputs == {"byte-a5": (165,), "eof": ()}
    assert (
        certificate.wide.initial["byte-a5"]
        != certificate.wide.initial["eof"]
    )
    assert (
        certificate.narrow.initial["byte-a5"]
        != certificate.narrow.initial["eof"]
    )
    assert finite_width_certificate_valid(certificate)
    assert bound_width_certificate_valid(certificate)


def test_legacy_v1_is_structural_evidence_but_cannot_select_width() -> None:
    """Legacy relation evidence cannot grant positive width authority."""
    certificate = parse_finite_width_certificate(_fixture_value(_FIXTURE_V1))
    assert certificate is not None
    assert finite_width_certificate_valid(certificate)
    assert not bound_width_certificate_valid(certificate)
    decisions = {10: certificate, 11: False, 12: False, 13: False}
    assert _selected_width(decisions) == CANONICAL_WIDTH


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


def test_bound_certificate_rejects_source_subject_drift() -> None:
    """A different source cannot authorize the requested QP subject."""
    wrong_source = copy.deepcopy(_fixture_value())
    wrong_source["source_bytes"] = [80, 80]
    certificate = parse_finite_width_certificate(wrong_source)
    assert certificate is not None
    assert not bound_width_certificate_valid(certificate)
    decisions = {10: certificate, 11: False, 12: False, 13: False}
    assert _selected_width(decisions) == CANONICAL_WIDTH


def test_selector_rejects_exact_input_subject_drift() -> None:
    """A valid certificate for another input stream cannot select QP."""
    wrong_inputs = copy.deepcopy(_fixture_value())
    wrong_inputs["inputs"] = {"byte-a5": [164], "eof": []}
    certificate = parse_finite_width_certificate(wrong_inputs)
    assert certificate is not None
    assert bound_width_certificate_valid(certificate)
    assert certificate.inputs != {"byte-a5": (165,), "eof": ()}
    decisions = {10: certificate, 11: False, 12: False, 13: False}
    assert _selected_width(decisions) == CANONICAL_WIDTH


def test_bound_certificate_rejects_unknown_proof_and_input_surface() -> None:
    """Unknown proof kinds or incomplete input bindings fail closed."""
    base = _fixture_value()
    unknown_proof = copy.deepcopy(base)
    unknown_proof["proof_kind"] = "unknown-proof-v1"
    certificate = parse_finite_width_certificate(unknown_proof)
    assert certificate is not None
    assert finite_width_certificate_valid(certificate)
    assert not bound_width_certificate_valid(certificate)

    missing_input = copy.deepcopy(base)
    missing_input["inputs"] = {"eof": []}
    certificate = parse_finite_width_certificate(missing_input)
    assert certificate is not None
    assert not finite_width_certificate_valid(certificate)


def test_selector_requires_certificates_for_positive_width_decisions() -> None:
    """A bare true result cannot replace a checked certificate."""
    certificate = parse_finite_width_certificate(_fixture_value())
    assert certificate is not None
    decisions = {10: certificate, 11: False, 12: False, 13: False}
    assert _selected_width(decisions) == MINIMUM_WIDTH

    authority_free = {10: True, 11: False, 12: False, 13: False}
    assert _selected_width(authority_free) == CANONICAL_WIDTH

    missing = {10: certificate, 11: False, 12: False}
    assert _selected_width(missing) == CANONICAL_WIDTH


def test_selector_rejects_certificate_width_mismatch() -> None:
    """A valid relation cannot authorize a different candidate-width key."""
    certificate = parse_finite_width_certificate(_fixture_value())
    assert certificate is not None
    decisions = {10: False, 11: certificate, 12: False, 13: False}
    assert _selected_width(decisions) == CANONICAL_WIDTH


def test_ubo_fixture_certifies_only_nonempty_input_domain() -> None:
    """UbO certifies byte input but refuses a subject that also includes EOF."""
    certificate = parse_finite_width_certificate(
        _fixture_value(_UBO_FIXTURE_V2)
    )
    assert certificate is not None
    assert certificate.proof_kind == INPUT_OUTPUT_HALT_PROOF_KIND
    assert bound_width_certificate_valid(certificate)
    byte_subject = WidthCertificateSubject(
        source=b"ubO",
        inputs={"byte-a5": bytes((165,))},
    )
    decisions = {10: certificate, 11: False, 12: False, 13: False}
    assert (
        minimum_width_from_certificates(byte_subject, decisions)
        == MINIMUM_WIDTH
    )
    eof_subject = WidthCertificateSubject(
        source=b"ubO",
        inputs={"byte-a5": bytes((165,)), "eof": b""},
    )
    assert (
        minimum_width_from_certificates(eof_subject, decisions)
        == CANONICAL_WIDTH
    )


def test_input_output_halt_checker_rejects_eof_capable_domain() -> None:
    """The proof checker accepts bytes and rejects any empty declared stream."""
    assert input_output_halt_projection_certifiable(
        b"ubO",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
        inputs={"a": (0,), "b": (255, 1)},
    )
    assert not input_output_halt_projection_certifiable(
        b"ubO",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
        inputs={"byte": (165,), "eof": ()},
    )


def test_up_fixture_certifies_input_then_halt_projection() -> None:
    """UP binds byte and EOF input effects while preserving width projection."""
    certificate = parse_finite_width_certificate(
        _fixture_value(_UP_FIXTURE_V2)
    )
    assert certificate is not None
    assert certificate.proof_kind == INPUT_THEN_HALT_PROOF_KIND
    assert finite_width_certificate_valid(certificate)
    assert bound_width_certificate_valid(certificate)
    subject = WidthCertificateSubject(
        source=b"uP",
        inputs={"byte-a5": bytes((165,)), "eof": b""},
    )
    decisions = {10: certificate, 11: False, 12: False, 13: False}
    assert minimum_width_from_certificates(subject, decisions) == MINIMUM_WIDTH


def test_input_then_halt_checker_matches_verifier_decode_pairs() -> None:
    """Input-then-halt proof matches independent decode for every cell pair."""
    for first in _GRAPHICAL:
        first_opcode = verifier_decode(first, 0)
        for second in _GRAPHICAL:
            second_opcode = verifier_decode(second, 1)
            expected = first_opcode == ord("/") and second_opcode == ord("v")
            observed = input_then_halt_projection_certifiable(
                bytes((first, second)),
                MINIMUM_WIDTH,
                CANONICAL_WIDTH,
            )
            assert observed == expected


def test_dp_fixture_certifies_two_step_noop_then_halt_projection() -> None:
    """DP carries a bound two-step proof through no-op, encryption, and halt."""
    certificate = parse_finite_width_certificate(
        _fixture_value(_DP_FIXTURE_V2)
    )
    assert certificate is not None
    assert certificate.proof_kind == NOOP_PREFIX_HALT_PROOF_KIND
    assert certificate.source_bytes == (68, 80)
    assert finite_width_certificate_valid(certificate)
    assert bound_width_certificate_valid(certificate)
    subject = WidthCertificateSubject(
        source=b"DP",
        inputs={"byte-a5": bytes((165,)), "eof": b""},
    )
    decisions = {10: certificate, 11: False, 12: False, 13: False}
    assert minimum_width_from_certificates(subject, decisions) == MINIMUM_WIDTH
    assert noop_prefix_halt_projection_certifiable(
        b"DCBA@?>=I",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
    )


def test_noop_prefix_halt_checker_matches_verifier_decode_pairs() -> None:
    """Minimum no-op-prefix proof matches independent decode for cell pairs."""
    for first in _GRAPHICAL:
        first_opcode = verifier_decode(first, 0)
        for second in _GRAPHICAL:
            second_opcode = verifier_decode(second, 1)
            expected = first_opcode == ord("o") and second_opcode == ord("v")
            observed = noop_prefix_halt_projection_certifiable(
                bytes((first, second)),
                MINIMUM_WIDTH,
                CANONICAL_WIDTH,
            )
            assert observed == expected


def _encoded_source(decoded: tuple[int, ...]) -> bytes:
    cells: list[int] = []
    for position, opcode in enumerate(decoded):
        matches = tuple(
            cell
            for cell in _GRAPHICAL
            if verifier_decode(cell, position) == opcode
        )
        assert len(matches) == 1
        cells.append(matches[0])
    return bytes(cells)


def _straight_line_oracle(decoded: tuple[int, ...], stream_len: int) -> bool:
    prefix = decoded[:-1]
    jump_data_safe = prefix.count(ord("j")) <= 1
    outputs_safe = all(
        prefix[:position].count(ord("/")) <= stream_len
        for position, opcode in enumerate(prefix)
        if opcode == ord("<")
    )
    return decoded[-1] == ord("v") and jump_data_safe and outputs_safe


def test_straight_line_checker_matches_exhaustive_bounded_composition() -> None:
    """Bounded safe-op programs match a decode/input/data-read oracle."""
    prefix_opcodes = (ord("o"), ord("/"), ord("<"), ord("j"))
    for prefix_len in range(1, 5):
        for prefix in product(prefix_opcodes, repeat=prefix_len):
            decoded = (*prefix, ord("v"))
            source = _encoded_source(decoded)
            for stream_len in range(3):
                stream = tuple(range(stream_len))
                expected = _straight_line_oracle(decoded, stream_len)
                observed = straight_line_projection_certifiable(
                    source,
                    MINIMUM_WIDTH,
                    CANONICAL_WIDTH,
                    inputs={"bounded": stream},
                )
                assert observed == expected


def test_straight_line_checker_composes_safe_noop_and_io_steps() -> None:
    """One checker composes no-op, input, output, and halt obligations."""
    two_bytes = {"two-bytes": (165, 66)}
    assert straight_line_projection_certifiable(
        b"uCar_L",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
        inputs=two_bytes,
    )
    assert straight_line_projection_certifiable(
        b"cP",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
        inputs={"eof": ()},
    )
    assert straight_line_projection_certifiable(
        b"(P",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
        inputs={"eof": ()},
    )


def test_straight_line_checker_rejects_unsafe_or_unsupported_paths() -> None:
    """EOF output, unsupported opcodes, and fall-through fail closed."""
    assert not straight_line_projection_certifiable(
        b"uCar_L",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
        inputs={"one-byte": (165,)},
    )
    assert not straight_line_projection_certifiable(
        b"DC",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
        inputs={"eof": ()},
    )
    assert not straight_line_projection_certifiable(
        b"('O",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
        inputs={"eof": ()},
    )
    assert not straight_line_projection_certifiable(
        b"(=%r_L",
        MINIMUM_WIDTH,
        CANONICAL_WIDTH,
        inputs={"byte-a5": (165,)},
    )


def test_bound_certificate_accepts_compositional_proof_kind() -> None:
    """Schema-v2 binding can delegate safety to the compositional checker."""
    certificate = parse_finite_width_certificate(_fixture_value())
    assert certificate is not None
    compositional = replace(
        certificate,
        proof_kind=STRAIGHT_LINE_SAFE_PROOF_KIND,
    )
    assert bound_width_certificate_valid(compositional)
    decisions = {10: compositional, 11: False, 12: False, 13: False}
    assert _selected_width(decisions) == MINIMUM_WIDTH


def test_composed_fixture_selects_width_for_exact_two_byte_subject() -> None:
    """A six-transition bound certificate can authorize the narrow width."""
    certificate = parse_finite_width_certificate(
        _fixture_value(_COMPOSED_FIXTURE)
    )
    assert certificate is not None
    assert finite_width_certificate_valid(certificate)
    assert bound_width_certificate_valid(certificate)
    subject = WidthCertificateSubject(
        source=b"uCar_L",
        inputs={"two-bytes": bytes((165, 66))},
    )
    decisions = {10: certificate, 11: False, 12: False, 13: False}
    assert minimum_width_from_certificates(subject, decisions) == MINIMUM_WIDTH


def test_composed_certificate_supports_each_candidate_width() -> None:
    """Widths ten through thirteen remain independent positive decisions."""
    certificate = parse_finite_width_certificate(
        _fixture_value(_COMPOSED_FIXTURE)
    )
    assert certificate is not None
    subject = WidthCertificateSubject(
        source=b"uCar_L",
        inputs={"two-bytes": bytes((165, 66))},
    )
    candidates = range(MINIMUM_WIDTH, CANONICAL_WIDTH)
    certificates = {
        width: replace(certificate, narrow_width=width)
        for width in candidates
    }
    all_valid = all(
        bound_width_certificate_valid(item)
        for item in certificates.values()
    )
    assert all_valid
    for selected_width in candidates:
        decisions = {
            width: certificates[width] if width == selected_width else False
            for width in candidates
        }
        selected = minimum_width_from_certificates(subject, decisions)
        assert selected == selected_width
    assert minimum_width_from_certificates(
        subject,
        dict.fromkeys(candidates, False),
    ) == CANONICAL_WIDTH


def test_composed_fixture_cannot_authorize_shorter_input_subject() -> None:
    """Changing only the bound input stream fails closed to canonical width."""
    certificate = parse_finite_width_certificate(
        _fixture_value(_COMPOSED_FIXTURE)
    )
    assert certificate is not None
    subject = WidthCertificateSubject(
        source=b"uCar_L",
        inputs={"two-bytes": bytes((165,))},
    )
    decisions = {10: certificate, 11: False, 12: False, 13: False}
    selected = minimum_width_from_certificates(subject, decisions)
    assert selected == CANONICAL_WIDTH


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
