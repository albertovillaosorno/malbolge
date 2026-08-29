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
LEGACY_CERTIFICATE_SCHEMA_VERSION: Final = 1
CERTIFICATE_SCHEMA_VERSION: Final = 2
INITIAL_HALT_PROOF_KIND: Final = "initial-halt-projection-v1"
INPUT_THEN_HALT_PROOF_KIND: Final = "input-then-halt-projection-v1"
INPUT_OUTPUT_HALT_PROOF_KIND: Final = "input-output-halt-projection-v1"
STRAIGHT_LINE_SAFE_PROOF_KIND: Final = "straight-line-safe-projection-v1"
NOOP_PREFIX_HALT_PROOF_KIND: Final = "noop-prefix-halt-projection-v1"
_CERTIFICATE_KEYS_V1: Final = frozenset(
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
_CERTIFICATE_KEYS_V2: Final = _CERTIFICATE_KEYS_V1 | frozenset(
    {"proof_kind", "source_bytes", "inputs"}
)
_BYTE_MAX: Final = 255
_GRAPHICAL_MIN: Final = 33
_GRAPHICAL_MAX: Final = 126
_MINIMUM_SOURCE_WORDS: Final = 2
_DECODE_PHASES: Final = 94
_SOURCE_WHITESPACE: Final = frozenset({9, 10, 11, 12, 13, 32})
_LOAD_OPCODES: Final = frozenset(b"ji*p</vo")
_CRAZY_TRIT: Final = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)
_XLAT1: Final = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    b".v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
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
class WidthCertificateSubject:
    """Exact source and input-domain identity requested by width selection."""

    source: bytes
    inputs: Mapping[str, bytes]


@dataclass(frozen=True, slots=True)
class WidthExecutionGeometry:
    """Derived execution geometry; never a canonical profile identity."""

    memory_words: int
    word_trits: int


@dataclass(frozen=True, slots=True)
class FiniteWidthCertificate:
    """One parsed research-only finite profile-width certificate."""

    schema_version: int
    input_ids: tuple[str, ...]
    observation_fields: tuple[str, ...]
    narrow_width: int
    relation: WidthRelation
    subject_id: str
    wide_width: int
    wide: FiniteSystem
    narrow: FiniteSystem
    proof_kind: str | None = None
    source_bytes: tuple[int, ...] | None = None
    inputs: Mapping[str, tuple[int, ...]] | None = None


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


def _parse_bytes(value: JsonValue) -> tuple[int, ...] | None:
    if not isinstance(value, list):
        return None
    parsed = tuple(_exact_int(item) for item in value)
    if any(item is None for item in parsed):
        return None
    integers = tuple(item for item in parsed if item is not None)
    valid = all(0 <= item <= _BYTE_MAX for item in integers)
    return integers if valid else None


def _parse_input_streams(
    value: JsonValue,
) -> dict[str, tuple[int, ...]] | None:
    if not isinstance(value, dict):
        return None
    parsed: dict[str, tuple[int, ...]] = {}
    for key, item in value.items():
        stream = _parse_bytes(item)
        if stream is None:
            return None
        parsed[key] = stream
    return parsed


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


def _parse_common_certificate_fields(
    raw: dict[str, JsonValue],
) -> tuple[
    str | None,
    int | None,
    int | None,
    tuple[str, ...] | None,
    tuple[str, ...] | None,
    FiniteSystem | None,
    FiniteSystem | None,
    WidthRelation | None,
]:
    return (
        _string(raw["subject_id"]),
        _exact_int(raw["wide_width"]),
        _exact_int(raw["narrow_width"]),
        _parse_unique_strings(raw["input_ids"]),
        _parse_unique_strings(raw["observation_fields"]),
        _parse_system(raw["wide"]),
        _parse_system(raw["narrow"]),
        _parse_relation(raw["relation"]),
    )


def _build_certificate(
    schema_version: int,
    common: tuple[
        str | None,
        int | None,
        int | None,
        tuple[str, ...] | None,
        tuple[str, ...] | None,
        FiniteSystem | None,
        FiniteSystem | None,
        WidthRelation | None,
    ],
    binding: tuple[
        str,
        tuple[int, ...],
        Mapping[str, tuple[int, ...]],
    ] | None = None,
) -> FiniteWidthCertificate | None:
    if not _certificate_parts_valid(common):
        return None
    (
        subject_id,
        wide_width,
        narrow_width,
        input_ids,
        observation_fields,
        wide,
        narrow,
        relation,
    ) = common
    return FiniteWidthCertificate(
        schema_version=schema_version,
        input_ids=cast("tuple[str, ...]", input_ids),
        observation_fields=cast("tuple[str, ...]", observation_fields),
        narrow_width=cast("int", narrow_width),
        relation=cast("WidthRelation", relation),
        subject_id=cast("str", subject_id),
        wide_width=cast("int", wide_width),
        wide=cast("FiniteSystem", wide),
        narrow=cast("FiniteSystem", narrow),
        proof_kind=binding[0] if binding is not None else None,
        source_bytes=binding[1] if binding is not None else None,
        inputs=binding[2] if binding is not None else None,
    )


def _parse_v1_certificate(value: JsonValue) -> FiniteWidthCertificate | None:
    raw = _exact_object(value, _CERTIFICATE_KEYS_V1)
    if raw is None:
        return None
    return _build_certificate(
        LEGACY_CERTIFICATE_SCHEMA_VERSION,
        _parse_common_certificate_fields(raw),
    )


def _parse_v2_certificate(value: JsonValue) -> FiniteWidthCertificate | None:
    raw = _exact_object(value, _CERTIFICATE_KEYS_V2)
    if raw is None:
        return None
    proof_kind = _string(raw["proof_kind"])
    source_bytes = _parse_bytes(raw["source_bytes"])
    inputs = _parse_input_streams(raw["inputs"])
    if proof_kind is None or source_bytes is None or inputs is None:
        return None
    return _build_certificate(
        CERTIFICATE_SCHEMA_VERSION,
        _parse_common_certificate_fields(raw),
        (proof_kind, source_bytes, inputs),
    )


def parse_finite_width_certificate(
    value: JsonValue,
) -> FiniteWidthCertificate | None:
    """Parse one versioned research certificate or fail closed.

    Returns:
        The parsed certificate, or None when schema or values are invalid.

    """
    parsed = None
    if isinstance(value, dict):
        schema_version = _exact_int(value.get("schema_version"))
        if schema_version == LEGACY_CERTIFICATE_SCHEMA_VERSION:
            parsed = _parse_v1_certificate(value)
        elif schema_version == CERTIFICATE_SCHEMA_VERSION:
            parsed = _parse_v2_certificate(value)
    return parsed


def _byte_tuple_valid(values: tuple[int, ...], *, allow_empty: bool) -> bool:
    if not allow_empty and not values:
        return False
    return all(
        type(value) is int and 0 <= value <= _BYTE_MAX
        for value in values
    )


def _bound_fields_valid(
    source: tuple[int, ...],
    inputs: Mapping[str, tuple[int, ...]],
    input_ids: tuple[str, ...],
) -> bool:
    inputs_match = set(inputs) == set(input_ids)
    streams_valid = all(
        _byte_tuple_valid(stream, allow_empty=True)
        for stream in inputs.values()
    )
    return (
        _byte_tuple_valid(source, allow_empty=False)
        and inputs_match
        and streams_valid
    )


def _binding_metadata_valid(certificate: FiniteWidthCertificate) -> bool:
    valid = False
    if certificate.schema_version == LEGACY_CERTIFICATE_SCHEMA_VERSION:
        valid = (
            certificate.proof_kind is None
            and certificate.source_bytes is None
            and certificate.inputs is None
        )
    elif certificate.schema_version == CERTIFICATE_SCHEMA_VERSION:
        source = certificate.source_bytes
        inputs = certificate.inputs
        proof_kind = certificate.proof_kind
        if proof_kind is not None and source is not None and inputs is not None:
            valid = _bound_fields_valid(source, inputs, certificate.input_ids)
    return valid


def finite_width_certificate_valid(certificate: FiniteWidthCertificate) -> bool:
    """Check one parsed certificate without granting product authority.

    Returns:
        True only for checked widths, exact input coverage, and a closed
        relation.

    """
    metadata_valid = (
        bool(certificate.subject_id)
        and bool(certificate.input_ids)
        and len(set(certificate.input_ids)) == len(certificate.input_ids)
        and bool(certificate.observation_fields)
        and len(set(certificate.observation_fields))
        == len(certificate.observation_fields)
        and _binding_metadata_valid(certificate)
    )
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
        metadata_valid
        and widths_valid
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


def _ternary_modulus(width: int) -> int:
    modulus = 1
    for _ in range(width):
        modulus *= 3
    return modulus


def _crazy_word(data: int, accumulator: int, width: int) -> int:
    result = 0
    place = 1
    for _ in range(width):
        result += _CRAZY_TRIT[data % 3][accumulator % 3] * place
        data //= 3
        accumulator //= 3
        place *= 3
    return result


def _initial_memory_word_from_cells(
    cells: tuple[int, ...],
    width: int,
    address: int,
) -> int:
    if address < len(cells):
        return cells[address]
    memory = list(cells)
    while len(memory) <= address:
        memory.append(_crazy_word(memory[-2], memory[-1], width))
    return memory[address]


def initial_memory_word(
    source: bytes,
    width: int,
    address: int,
) -> int | None:
    """Return one research initial-memory word at a checked derived width.

    Returns:
        The exact initialized word, or None for invalid source/width/address.

    """
    width_valid = MINIMUM_WIDTH <= width <= CANONICAL_WIDTH
    address_valid = (
        0 <= address < _ternary_modulus(width) if width_valid else False
    )
    cells = _source_cells(source)
    source_valid = cells is not None and len(cells) >= _MINIMUM_SOURCE_WORDS
    if not address_valid or not source_valid or cells is None:
        return None
    if _admitted_source_decodes(source, width) is None:
        return None
    return _initial_memory_word_from_cells(cells, width, address)


def _source_cells(source: bytes) -> tuple[int, ...] | None:
    cells: list[int] = []
    for byte in source:
        if byte in _SOURCE_WHITESPACE:
            continue
        if not _GRAPHICAL_MIN <= byte <= _GRAPHICAL_MAX:
            return None
        cells.append(byte)
    return tuple(cells)


def _decode_source_cell(cell: int, position: int) -> int:
    phase = (cell - _GRAPHICAL_MIN + position) % _DECODE_PHASES
    return _XLAT1[phase]


def _admitted_source_decodes(
    source: bytes,
    width: int,
) -> tuple[int, ...] | None:
    cells = _source_cells(source)
    if cells is None:
        return None
    capacity = _ternary_modulus(width)
    size_valid = _MINIMUM_SOURCE_WORDS <= len(cells) <= capacity
    decoded = tuple(
        _decode_source_cell(cell, position)
        for position, cell in enumerate(cells)
    ) if size_valid else ()
    admitted = size_valid and all(opcode in _LOAD_OPCODES for opcode in decoded)
    return decoded if admitted else None


def initial_halt_projection_certifiable(
    source: bytes,
    narrow_width: int,
    wide_width: int,
) -> bool:
    """Check the sufficient initial-halt projection theorem premises.

    Returns:
        True only when the source is admitted at the narrow width and its first
        instruction halts before any width-sensitive transition effect.

    """
    widths_valid = (
        MINIMUM_WIDTH <= narrow_width < wide_width <= CANONICAL_WIDTH
    )
    if not widths_valid:
        return False
    decoded = _admitted_source_decodes(source, narrow_width)
    return decoded is not None and decoded[0] == ord("v")


@dataclass(frozen=True, slots=True)
class _StraightLineSourceState:
    data_address: int | None
    events: tuple[int, ...]
    projection_writes: frozenset[int]


@dataclass(frozen=True, slots=True)
class _StraightLineSourceContext:
    cells: tuple[int, ...]
    narrow_width: int
    wide_width: int

    @property
    def modulus(self) -> int:
        return _ternary_modulus(self.narrow_width)


def _exact_pointer_successor(value: int, modulus: int) -> int | None:
    return value + 1 if 0 <= value < modulus - 1 else None


def _exact_initial_read(
    state: _StraightLineSourceState,
    position: int,
    context: _StraightLineSourceContext,
) -> int | None:
    address = state.data_address
    if address is None or address in state.projection_writes:
        return None
    if address < len(context.cells):
        return context.cells[address] if address >= position else None
    narrow = _initial_memory_word_from_cells(
        context.cells,
        context.narrow_width,
        address,
    )
    wide = _initial_memory_word_from_cells(
        context.cells,
        context.wide_width,
        address,
    )
    return narrow if narrow == wide else None


def _advance_data_address(
    state: _StraightLineSourceState,
    context: _StraightLineSourceContext,
) -> int | None:
    address = state.data_address
    return (
        _exact_pointer_successor(address, context.modulus)
        if address is not None
        else None
    )


def _jump_source_state(
    state: _StraightLineSourceState,
    position: int,
    context: _StraightLineSourceContext,
) -> _StraightLineSourceState | None:
    if state.data_address is None:
        return None
    exact_value = _exact_initial_read(state, position, context)
    next_address = (
        _exact_pointer_successor(exact_value, context.modulus)
        if exact_value is not None
        else None
    )
    return _StraightLineSourceState(
        data_address=next_address,
        events=state.events,
        projection_writes=state.projection_writes,
    )


def _crazy_source_state(
    state: _StraightLineSourceState,
    position: int,
    context: _StraightLineSourceContext,
) -> _StraightLineSourceState | None:
    address = state.data_address
    if address is None or address == position:
        return None
    rewrites_future_code = position < address < len(context.cells)
    if rewrites_future_code:
        return None
    return _StraightLineSourceState(
        data_address=_exact_pointer_successor(address, context.modulus),
        events=(*state.events, ord("p")),
        projection_writes=state.projection_writes | frozenset((address,)),
    )


def _ordinary_source_state(
    state: _StraightLineSourceState,
    opcode: int,
    context: _StraightLineSourceContext,
) -> _StraightLineSourceState:
    events = (
        (*state.events, opcode)
        if opcode in {ord("/"), ord("<")}
        else state.events
    )
    return _StraightLineSourceState(
        data_address=_advance_data_address(state, context),
        events=events,
        projection_writes=state.projection_writes,
    )


def _advance_straight_line_source(
    state: _StraightLineSourceState,
    step: tuple[int, int],
    context: _StraightLineSourceContext,
) -> _StraightLineSourceState | None:
    position, opcode = step
    advanced: _StraightLineSourceState | None = None
    if opcode == ord("j"):
        advanced = _jump_source_state(state, position, context)
    elif opcode == ord("p"):
        advanced = _crazy_source_state(state, position, context)
    elif opcode in {ord("o"), ord("/"), ord("<")}:
        advanced = _ordinary_source_state(state, opcode, context)
    return advanced


def _straight_line_events(
    decoded: tuple[int, ...],
    cells: tuple[int, ...],
    narrow_width: int,
    *,
    wide_width: int,
) -> tuple[int, ...] | None:
    state = _StraightLineSourceState(0, (), frozenset())
    context = _StraightLineSourceContext(cells, narrow_width, wide_width)
    for step in enumerate(decoded):
        _, opcode = step
        if opcode == ord("v"):
            return state.events
        advanced = _advance_straight_line_source(state, step, context)
        if advanced is None:
            return None
        state = advanced
    return None


def _stream_events_safe(
    events: tuple[int, ...],
    stream: tuple[int, ...],
) -> bool:
    input_cursor = 0
    accumulator_exact = True
    safe = True
    for opcode in events:
        if opcode == ord("/"):
            accumulator_exact = input_cursor < len(stream)
            input_cursor += int(accumulator_exact)
        elif opcode == ord("p"):
            accumulator_exact = False
        elif not accumulator_exact:
            safe = False
            break
    return safe


def straight_line_projection_certifiable(
    source: bytes,
    narrow_width: int,
    wide_width: int,
    *,
    inputs: Mapping[str, tuple[int, ...]],
) -> bool:
    """Check straight-line projection through no-op and byte-I/O effects.

    Returns:
        True only when every bound stream reaches halt through admitted no-op,
        byte-I/O, exact-address jump, and guarded crazy transitions while
        preserving the width projection.

    """
    widths_valid = (
        MINIMUM_WIDTH <= narrow_width < wide_width <= CANONICAL_WIDTH
    )
    decoded = (
        _admitted_source_decodes(source, narrow_width)
        if widths_valid
        else None
    )
    cells = _source_cells(source)
    events = (
        _straight_line_events(
            decoded,
            cells,
            narrow_width,
            wide_width=wide_width,
        )
        if decoded is not None and cells is not None
        else None
    )
    return (
        events is not None
        and bool(inputs)
        and all(
            _stream_events_safe(events, stream)
            for stream in inputs.values()
        )
    )


def input_output_halt_projection_certifiable(
    source: bytes,
    narrow_width: int,
    wide_width: int,
    *,
    inputs: Mapping[str, tuple[int, ...]],
) -> bool:
    """Check the sufficient input-output-halt projection premises.

    Returns:
        True only for `/`, `<`, `v` with no EOF-capable declared input stream.

    """
    widths_valid = (
        MINIMUM_WIDTH <= narrow_width < wide_width <= CANONICAL_WIDTH
    )
    decoded = (
        _admitted_source_decodes(source, narrow_width)
        if widths_valid
        else None
    )
    streams_safe = bool(inputs) and all(
        bool(stream) for stream in inputs.values()
    )
    sequence_safe = (
        decoded is not None
        and decoded[:3] == (ord("/"), ord("<"), ord("v"))
    )
    return sequence_safe and streams_safe


def input_then_halt_projection_certifiable(
    source: bytes,
    narrow_width: int,
    wide_width: int,
) -> bool:
    """Check the sufficient input-then-halt projection theorem premises.

    Returns:
        True only when one admitted source executes `/` then `v` initially.

    """
    widths_valid = (
        MINIMUM_WIDTH <= narrow_width < wide_width <= CANONICAL_WIDTH
    )
    if not widths_valid:
        return False
    decoded = _admitted_source_decodes(source, narrow_width)
    return decoded is not None and decoded[:2] == (ord("/"), ord("v"))


def noop_prefix_halt_projection_certifiable(
    source: bytes,
    narrow_width: int,
    wide_width: int,
) -> bool:
    """Check the sufficient no-op-prefix-then-halt projection premises.

    Returns:
        True only for one or more initial `o` instructions followed by `v`.

    """
    widths_valid = (
        MINIMUM_WIDTH <= narrow_width < wide_width <= CANONICAL_WIDTH
    )
    if not widths_valid:
        return False
    decoded = _admitted_source_decodes(source, narrow_width)
    if decoded is None:
        return False
    prefix_length = 0
    for opcode in decoded:
        if opcode != ord("o"):
            break
        prefix_length += 1
    following = (
        decoded[prefix_length] if prefix_length < len(decoded) else None
    )
    return bool(prefix_length) and following == ord("v")


def execution_geometry(width: int) -> WidthExecutionGeometry | None:
    """Return exact mathematical ternary geometry for one semantic width.

    Returns:
        Width and `3^N` words for every integer N at or above the repository
        minimum. Backend integer/address limits are deliberately not language
        limits and must be checked by the consuming runtime or accelerator.

    """
    if type(width) is not int or width < MINIMUM_WIDTH:
        return None
    return WidthExecutionGeometry(
        memory_words=_ternary_modulus(width),
        word_trits=width,
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


def _input_bound_proof_valid(
    certificate: FiniteWidthCertificate,
    source: bytes,
    inputs: Mapping[str, tuple[int, ...]],
) -> bool | None:
    if certificate.proof_kind == INPUT_OUTPUT_HALT_PROOF_KIND:
        return input_output_halt_projection_certifiable(
            source,
            certificate.narrow_width,
            certificate.wide_width,
            inputs=inputs,
        )
    if certificate.proof_kind == STRAIGHT_LINE_SAFE_PROOF_KIND:
        return straight_line_projection_certifiable(
            source,
            certificate.narrow_width,
            certificate.wide_width,
            inputs=inputs,
        )
    return None


def _recognized_proof_valid(
    certificate: FiniteWidthCertificate,
    source: bytes,
) -> bool:
    simple_checkers = {
        INITIAL_HALT_PROOF_KIND: initial_halt_projection_certifiable,
        INPUT_THEN_HALT_PROOF_KIND: input_then_halt_projection_certifiable,
        NOOP_PREFIX_HALT_PROOF_KIND: noop_prefix_halt_projection_certifiable,
    }
    proof_kind = certificate.proof_kind
    checker = (
        simple_checkers.get(proof_kind) if proof_kind is not None else None
    )
    accepted: bool | None = None
    if checker is not None:
        accepted = checker(
            source,
            certificate.narrow_width,
            certificate.wide_width,
        )
    elif certificate.inputs is not None:
        accepted = _input_bound_proof_valid(
            certificate,
            source,
            certificate.inputs,
        )
    return accepted is True


def bound_width_certificate_valid(
    certificate: FiniteWidthCertificate,
) -> bool:
    """Check one source-bound certificate through a recognized proof kind.

    Returns:
        True only when structural evidence and theorem-specific premises pass.

    """
    if (
        not finite_width_certificate_valid(certificate)
        or certificate.schema_version != CERTIFICATE_SCHEMA_VERSION
    ):
        return False
    source = certificate.source_bytes
    if source is None:
        return False
    return _recognized_proof_valid(certificate, bytes(source))


def _certificate_matches_subject(
    certificate: FiniteWidthCertificate,
    subject: WidthCertificateSubject,
) -> bool:
    source = certificate.source_bytes
    inputs = certificate.inputs
    if source is None or inputs is None:
        return False
    if set(inputs) != set(subject.inputs):
        return False
    source_matches = source == tuple(subject.source)
    inputs_match = all(
        inputs[input_id] == tuple(stream)
        for input_id, stream in subject.inputs.items()
    )
    return source_matches and inputs_match


def _certificate_decision(
    width: int,
    decision: WidthCertificateDecision,
    subject: WidthCertificateSubject,
) -> bool | None:
    if decision is False:
        return False
    if not isinstance(decision, FiniteWidthCertificate):
        return None
    width_matches = (
        decision.narrow_width == width
        and decision.wide_width == CANONICAL_WIDTH
    )
    accepted = (
        width_matches
        and bound_width_certificate_valid(decision)
        and _certificate_matches_subject(decision, subject)
    )
    return True if accepted else None


def minimum_width_from_certificates(
    subject: WidthCertificateSubject,
    decisions: Mapping[int, WidthCertificateDecision],
) -> int:
    """Select the minimum width for one exact source/input subject.

    Returns:
        The minimum independently proved width, or fourteen on incomplete,
        mismatched, authority-free, or wrong-subject acceptance data.

    """
    candidates = set(range(MINIMUM_WIDTH, CANONICAL_WIDTH))
    if set(decisions) != candidates:
        return CANONICAL_WIDTH
    results: dict[int, bool] = {}
    for width in candidates:
        result = _certificate_decision(width, decisions[width], subject)
        if result is None:
            return CANONICAL_WIDTH
        results[width] = result
    return minimum_certified_width(results)


def minimum_geometry_from_certificates(
    subject: WidthCertificateSubject,
    decisions: Mapping[int, WidthCertificateDecision],
) -> WidthExecutionGeometry:
    """Return exact derived geometry for one fail-closed width decision.

    Returns:
        The selected geometry; invalid evidence maps to canonical fourteen.

    """
    selected = minimum_width_from_certificates(subject, decisions)
    geometry = execution_geometry(selected)
    if geometry is not None:
        return geometry
    return WidthExecutionGeometry(
        memory_words=_ternary_modulus(CANONICAL_WIDTH),
        word_trits=CANONICAL_WIDTH,
    )
