# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Independent regressions for bounded emitted-Malbolge static admission.
# - Must-Not:
#   - Execute guest work or derive expected decode through the checker itself.
# - Allows:
#   - Inputs: fixed valid sources and deliberately invalid source mutations.
#   - Outputs: deterministic report and finding assertions.
#   - Side effects: test-local source files and subprocess output only.
# - Split-When:
#   - Dynamic reachability analysis gains independent fixtures.
# - Merge-When:
#   - Verifier conformance owns these exact initial-image cases directly.
# - Summary:
#   - Bounded static analyzer acceptance and rejection evidence.
# - Description:
#   - Covers lexical, recurrence, capacity, positional decode, and CLI output.
# - Usage:
#   - Collected by the repository Python validation suite.
# - Defaults:
#   - Dynamic analysis limits remain explicit in every report.
#

"""Bounded emitted-Malbolge static analyzer regressions."""

from __future__ import annotations

import ast
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Protocol
from typing import cast

from scripts.validate import target_profile

_ROOT = Path(__file__).resolve().parents[2]
_ANALYZER = _ROOT / "verifier" / "emitted_malbolge.py"
_FIXTURE = (
    _ROOT / "tests/compatibility/specification/spec-io-roundtrip.malbolge"
)
_HISTORICAL_INTERPRETER = (
    _ROOT / "src/interoperability/historical-malbolge/adapter-outbound/main.c"
)
_PROFILE_ID = "malbolge-1998"
_PROFILE_MEMORY_WORDS = 59_049
_FIXTURE_SOURCE_WORDS = 3
_TWO_SOURCE_WORDS = 2
_OVERSIZED_SOURCE_WORDS = 59_050
_LEXICAL_CODE = "MALBOLGE-STATIC-001"
_DECODE_CODE = "MALBOLGE-STATIC-004"
_GRAPHICAL_INVALID_BYTE = 33
_FORBIDDEN_DECODE_BYTE = 43
_SCHEMA = "malbolge-static-image/v1"
_MISSING_SOURCE_MESSAGE = "static analyzer cannot read source"
_GRAPHICAL_START = 33
_GRAPHICAL_END = 126
_DECODE_PERIOD = 94
_HISTORICAL_XLAT1_DECLARATION = "const char xlat1[] ="
_HISTORICAL_LOAD_ADMISSION_PREFIX = 'strchr( "'
_HISTORICAL_JUMP_DATA_ASSIGNMENT = "case 'j': d = mem[d]; break;"
_HISTORICAL_JUMP_CODE_ASSIGNMENT = "case 'i': c = mem[d]; break;"
_HISTORICAL_CODE_WRAP = "if ( c == 59048 ) c = 0; else c++;"
_HISTORICAL_DATA_WRAP = "if ( d == 59048 ) d = 0; else d++;"
_TEST_ALLOWED_INSTRUCTIONS = frozenset(b"ji*p</vo")
_TEST_XLAT1 = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    rb".v%{gJh4G\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)


class _Finding(Protocol):
    code: str
    byte_offset: int | None
    loaded_position: int | None
    source_byte: int | None
    decoded_byte: int | None


class _Cell(Protocol):
    position: int
    byte_offset: int
    source_byte: int
    decoded_byte: int


class _Report(Protocol):
    schema: str
    profile_id: str
    profile_version: str
    profile_memory_words: int
    profile_address_domain_closed: bool
    source_sha256: str
    required_source_words: int
    admitted_initial_image: bool
    initial_cells: tuple[_Cell, ...]
    findings: tuple[_Finding, ...]
    analysis_limits: tuple[str, ...]


class _AnalyzerModule(Protocol):
    def analyze_source(self, source: bytes) -> _Report:
        """Analyze source without running it."""
        ...

    def render_report(self, report: _Report) -> str:
        """Render canonical report JSON."""
        ...


def _load_analyzer() -> _AnalyzerModule:
    spec = importlib.util.spec_from_file_location("emitted_malbolge", _ANALYZER)
    if spec is None or spec.loader is None:
        message = "static analyzer module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_AnalyzerModule", cast("object", module))


_ANALYZER_MODULE = _load_analyzer()


def _historical_xlat1_literals(tail: str) -> list[str]:
    literals: list[str] = []
    for line in tail.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith(";"):
            literals.append(stripped.removesuffix(";"))
            return literals
        literals.append(stripped)
    message = "historical interpreter xlat1 terminator is missing"
    raise AssertionError(message)


def _historical_xlat1() -> bytes:
    source = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    _, declaration, tail = source.partition(_HISTORICAL_XLAT1_DECLARATION)
    if not declaration:
        message = "historical interpreter xlat1 declaration is missing"
        raise AssertionError(message)
    literals = _historical_xlat1_literals(tail)
    try:
        decoded = "".join(ast.literal_eval(literal) for literal in literals)
    except (SyntaxError, ValueError) as error:
        message = "historical interpreter xlat1 literal is malformed"
        raise AssertionError(message) from error
    return decoded.encode("ascii")


def _historical_load_instructions() -> frozenset[int]:
    source = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    _, marker, tail = source.partition(_HISTORICAL_LOAD_ADMISSION_PREFIX)
    if not marker:
        message = "historical interpreter load-admission set is missing"
        raise AssertionError(message)
    literal, terminator, _ = tail.partition('"')
    if not terminator:
        message = "historical interpreter load-admission literal is malformed"
        raise AssertionError(message)
    return frozenset(literal.encode("ascii"))


def test_report_hash_binds_exact_source_bytes() -> None:
    """Report identity includes the exact raw source byte hash."""
    source = _FIXTURE.read_bytes()
    report = _ANALYZER_MODULE.analyze_source(source)
    expected = "sha256:" + sha256(source).hexdigest()
    assert report.source_sha256 == expected

    mutated = source + b" "
    mutated_report = _ANALYZER_MODULE.analyze_source(mutated)
    assert mutated_report.required_source_words == report.required_source_words
    assert mutated_report.source_sha256 != report.source_sha256


def test_report_profile_identity_matches_canonical_authority() -> None:
    """Historical report identity is a projection of canonical malbolge.json."""
    canonical = cast(
        "dict[str, object]",
        json.loads((_ROOT / "malbolge.json").read_text(encoding="utf-8")),
    )
    profiles = cast("dict[str, object]", canonical["profiles"])
    historical = cast("dict[str, object]", profiles[_PROFILE_ID])
    memory = cast("dict[str, object]", historical["memory"])
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    assert report.profile_version == historical["version"]
    assert report.profile_memory_words == memory["words"]


def test_independent_decode_table_matches_preserved_interpreter() -> None:
    """Independent decode expectations are anchored to primary evidence."""
    assert _historical_xlat1() == _TEST_XLAT1


def test_load_admission_set_matches_preserved_interpreter() -> None:
    """Anchor independent load-admission expectations to primary evidence."""
    assert _historical_load_instructions() == _TEST_ALLOWED_INSTRUCTIONS


def test_known_valid_fixture_has_exact_initial_decode() -> None:
    """Historical roundtrip source is admitted with fixed independent decode."""
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    assert report.admitted_initial_image
    assert report.profile_id == _PROFILE_ID
    assert report.profile_memory_words == _PROFILE_MEMORY_WORDS
    assert report.profile_address_domain_closed
    assert report.required_source_words == _FIXTURE_SOURCE_WORDS
    assert [cell.source_byte for cell in report.initial_cells] == [99, 116, 79]
    assert [cell.decoded_byte for cell in report.initial_cells] == [60, 47, 118]
    assert report.findings == ()


def test_report_profile_capacity_matches_canonical_authority() -> None:
    """Historical capacity agrees with validated `malbolge.json`."""
    canonical = target_profile.load_document(target_profile.DEFAULT_PROFILE)
    geometry = target_profile.profile_geometry(canonical, _PROFILE_ID)
    profiles = cast("dict[str, object]", canonical["profiles"])
    historical = cast("dict[str, object]", profiles[_PROFILE_ID])
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    assert report.profile_id == geometry.profile_id
    assert report.profile_version == historical["version"]
    assert report.profile_memory_words == geometry.memory_words


def test_exact_c_locale_whitespace_does_not_consume_source_words() -> None:
    """All six specified whitespace bytes preserve loaded positions."""
    source = bytes((39, 9, 10, 11, 12, 13, 32, 38))
    report = _ANALYZER_MODULE.analyze_source(source)
    assert report.admitted_initial_image
    assert report.required_source_words == _TWO_SOURCE_WORDS
    assert [cell.position for cell in report.initial_cells] == [0, 1]
    assert [cell.byte_offset for cell in report.initial_cells] == [0, 7]
    assert [cell.decoded_byte for cell in report.initial_cells] == [42, 42]


def test_non_graphical_source_byte_is_reported_with_offset() -> None:
    """A non-whitespace non-graphical byte fails lexical image admission."""
    report = _ANALYZER_MODULE.analyze_source(bytes((39, 0, 38)))
    assert not report.admitted_initial_image
    assert report.required_source_words == _FIXTURE_SOURCE_WORDS
    assert report.initial_cells == ()
    finding = report.findings[0]
    assert finding.code == _LEXICAL_CODE
    assert finding.byte_offset == 1
    assert finding.source_byte == 0


def test_recurrence_underflow_is_reported_without_guest_execution() -> None:
    """One loaded word cannot supply the recurrence base."""
    report = _ANALYZER_MODULE.analyze_source(bytes((39,)))
    assert not report.admitted_initial_image
    codes = [finding.code for finding in report.findings]
    assert codes == ["MALBOLGE-STATIC-002"]


def test_exact_historical_capacity_can_be_fully_admitted() -> None:
    """The 59,049-word historical ceiling is inclusive for valid source."""
    target_decode = ord("o")
    target_index = _TEST_XLAT1.index(target_decode)
    source = bytes(
        ((target_index - position) % _DECODE_PERIOD) + _GRAPHICAL_START
        for position in range(_PROFILE_MEMORY_WORDS)
    )
    report = _ANALYZER_MODULE.analyze_source(source)
    assert report.admitted_initial_image
    assert report.required_source_words == _PROFILE_MEMORY_WORDS
    assert len(report.initial_cells) == _PROFILE_MEMORY_WORDS
    assert report.findings == ()
    assert all(
        cell.decoded_byte == target_decode for cell in report.initial_cells
    )


def test_profile_capacity_prevents_initial_decode_of_oversized_source() -> None:
    """An oversized graphical source reports historical capacity explicitly."""
    report = _ANALYZER_MODULE.analyze_source(b"!" * _OVERSIZED_SOURCE_WORDS)
    assert not report.admitted_initial_image
    assert report.required_source_words == _OVERSIZED_SOURCE_WORDS
    assert report.initial_cells == ()
    codes = [finding.code for finding in report.findings]
    assert codes == ["MALBOLGE-STATIC-003"]


def test_every_graphical_byte_and_phase_matches_independent_decode() -> None:
    """All 8,836 initial decode pairs match the independent historical table."""
    assert len(_TEST_XLAT1) == _DECODE_PERIOD
    filler = bytes((_GRAPHICAL_START,))
    for position in range(_DECODE_PERIOD):
        prefix = filler * position
        for source_byte in range(_GRAPHICAL_START, _GRAPHICAL_END + 1):
            source = prefix + bytes((source_byte,))
            if len(source) < _TWO_SOURCE_WORDS:
                source += filler
            report = _ANALYZER_MODULE.analyze_source(source)
            cell = report.initial_cells[position]
            expected_index = (
                source_byte - _GRAPHICAL_START + position
            ) % _DECODE_PERIOD
            expected_decode = _TEST_XLAT1[expected_index]
            assert cell.source_byte == source_byte
            assert cell.decoded_byte == expected_decode
            rejected_positions = {
                finding.loaded_position
                for finding in report.findings
                if finding.code == _DECODE_CODE
            }
            assert (position in rejected_positions) == (
                expected_decode not in _TEST_ALLOWED_INSTRUCTIONS
            )


def test_graphical_but_forbidden_initial_decode_reports_position() -> None:
    """Graphical source can still fail positional decode."""
    report = _ANALYZER_MODULE.analyze_source(bytes((33, 38)))
    assert not report.admitted_initial_image
    assert len(report.initial_cells) == _TWO_SOURCE_WORDS
    finding = report.findings[0]
    assert finding.code == _DECODE_CODE
    assert finding.byte_offset == 0
    assert finding.loaded_position == 0
    assert finding.source_byte == _GRAPHICAL_INVALID_BYTE
    assert finding.decoded_byte == _FORBIDDEN_DECODE_BYTE


def test_historical_address_domain_is_structurally_closed() -> None:
    """Classic pointers stay inside the fixed 59,049-word memory domain."""
    interpreter = _HISTORICAL_INTERPRETER.read_text(encoding="utf-8")
    assert _HISTORICAL_JUMP_DATA_ASSIGNMENT in interpreter
    assert _HISTORICAL_JUMP_CODE_ASSIGNMENT in interpreter
    assert _HISTORICAL_CODE_WRAP in interpreter
    assert _HISTORICAL_DATA_WRAP in interpreter
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    assert report.profile_memory_words == _PROFILE_MEMORY_WORDS
    assert report.profile_address_domain_closed


def test_dynamic_analysis_limits_are_explicit_and_stable() -> None:
    """Initial-image admission never implies dynamic reachability proof."""
    report = _ANALYZER_MODULE.analyze_source(bytes((39, 38)))
    assert report.analysis_limits == (
        "code-data-aliasing:not-analyzed",
        "control-flow-reachability:not-analyzed",
        "dataflow:not-analyzed",
        "input-dependent-cycles:not-analyzed",
        "self-modification:profile-required-not-analyzed",
        "source-map-context:not-analyzed",
        "wraparound-reachability:not-analyzed",
    )


def test_report_rendering_is_canonical_and_replayable() -> None:
    """Canonical JSON output is byte-stable for one report."""
    report = _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    first = _ANALYZER_MODULE.render_report(report)
    second = _ANALYZER_MODULE.render_report(report)
    assert first == second
    assert first.endswith("\n")
    parsed = cast("dict[str, object]", json.loads(first))
    assert parsed["schema"] == _SCHEMA
    assert parsed["admitted_initial_image"] is True


def test_cli_prints_same_report_as_library() -> None:
    """The command-line surface emits the exact canonical report bytes."""
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(_FIXTURE)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    expected = _ANALYZER_MODULE.render_report(
        _ANALYZER_MODULE.analyze_source(_FIXTURE.read_bytes())
    ).encode("utf-8")
    assert completed.stdout == expected
    assert not completed.stderr


def test_cli_rejected_image_returns_failure_with_report(
    tmp_path: Path,
) -> None:
    """Semantic rejection is visible in JSON and process status."""
    source = tmp_path / "invalid.malbolge"
    _ = source.write_bytes(bytes((_GRAPHICAL_INVALID_BYTE, 38)))
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(source)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    document = cast("dict[str, object]", json.loads(completed.stdout))
    assert document["admitted_initial_image"] is False


def test_cli_rejects_missing_source(tmp_path: Path) -> None:
    """Filesystem failures remain outside the semantic report."""
    missing = tmp_path / "missing.malbolge"
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(_ANALYZER), str(missing)],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode != 0
    assert _MISSING_SOURCE_MESSAGE in completed.stderr
