# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Regression tests for the closed Malbolge target-profile schema.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for the closed Malbolge target-profile schema."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Self, cast, override

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import BinaryIO

from scripts.validate import target_profile as validator

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "malbolge.json"
TARGET_PROFILE_CONTRACT = ROOT / "docs/technical/specification/target-profile.md"
CURRENT_PROFILE = "malbolge-2026"
CURRENT_VERSION = "2026"
TRANSITION_PROFILE = "malbolge-2026.3"
TRANSITION_VERSION = "2026.3"
TRANSITION_WORDS = 4_782_969
TRANSITION_EOF = TRANSITION_WORDS - 1
EOF_WORD_KEY = "eof_word"
CURRENT_TRITS = 15
CURRENT_WORDS = 14_348_907
CURRENT_EOF = CURRENT_WORDS - 1
WIDTH_MODEL_RADIX = 3
WIDTH_MODEL_MINIMUM = 10
WIDTH_MODEL_CHUNK_TRITS = 5
WIDTH_MODEL_ZERO_PADDING = "zero-high-trits"
WIDTH_MODEL_PROJECTION = "mod-semantic-width"
INTERPRETER_INPUT = "/"
INTERPRETER_OUTPUT = "<"
SPECIFICATION_INPUT = "<"
SPECIFICATION_OUTPUT = "/"
VERSIONED_N14_DOC = "`N = 14`, 4,782,969-word"
STALE_CURRENT_GEOMETRY_DOC = (
    "same interpreter-compatible I/O and geometry as the annual current"
)


def _canonical_text() -> str:
    return PROFILE_PATH.read_text(encoding="utf-8-sig")


def _expect_invalid(text: str) -> None:
    try:
        validator.validate_text(text)
    except validator.ProfileValidationError:
        return
    message = "profile validation unexpectedly succeeded"
    raise AssertionError(message)


def test_validate_document_rejects_foreign_top_level_type() -> None:
    """Foreign direct inputs fail through the canonical validation boundary."""
    with pytest.raises(validator.ProfileValidationError, match="must be an object"):
        validator.validate_document(cast("validator.JsonObject", object()))


def test_json_integer_beyond_host_decimal_limit_fails_typed(
    tmp_path: Path,
) -> None:
    """Large integer tokens cannot escape as raw Python parser failures."""
    digit_limit = sys.get_int_max_str_digits()
    if digit_limit == 0 or digit_limit > 20_000:
        pytest.skip("host decimal digit admission is disabled or unusually high")
    payload = '{"schema_version":' + "9" * (digit_limit + 1) + "}"
    with pytest.raises(validator.ProfileValidationError, match="invalid JSON"):
        _ = validator.loads_document(payload)

    source = tmp_path / "profile.json"
    _ = source.write_text(payload, encoding="utf-8")
    with pytest.raises(validator.ProfileValidationError, match="invalid JSON"):
        _ = validator.load_document(source)


def test_profile_text_rejects_foreign_input_type() -> None:
    """Direct parser misuse remains inside the profile validation boundary."""
    with pytest.raises(
        validator.ProfileValidationError, match="JSON text must use the exact"
    ):
        _ = validator.loads_document(cast("str", object()))


def test_profile_loader_rejects_foreign_path_type() -> None:
    """Direct loader misuse fails before invoking pathlib methods."""
    with pytest.raises(
        validator.ProfileValidationError, match="path must use pathlib Path"
    ):
        _ = validator.load_document(cast("Path", cast("object", "malbolge.json")))


def test_custom_profile_apis_reject_foreign_top_level_type() -> None:
    """Custom-profile APIs admit the document before key inspection."""
    canonical = validator.load_document(PROFILE_PATH)
    foreign = cast("validator.JsonObject", object())
    with pytest.raises(validator.ProfileValidationError, match="must be an object"):
        _ = validator.validate_custom_profile_document(foreign, canonical)
    with pytest.raises(validator.ProfileValidationError, match="must be an object"):
        _ = validator.custom_profile_fingerprint(foreign, canonical)


def test_canonical_profile_is_valid() -> None:
    """The committed canonical profile satisfies schema v2."""
    validator.validate_text(_canonical_text())


def test_semantic_width_model_is_unbounded_five_trit_chunking() -> None:
    """Canonical arithmetic chunks do not impose a semantic maximum width."""
    model = validator.semantic_width_model()
    assert model.radix == WIDTH_MODEL_RADIX
    assert model.minimum_trits == WIDTH_MODEL_MINIMUM
    assert model.chunk_trits == WIDTH_MODEL_CHUNK_TRITS
    assert model.maximum_trits is None
    assert model.partial_chunk_padding == WIDTH_MODEL_ZERO_PADDING
    assert model.result_projection == WIDTH_MODEL_PROJECTION


@pytest.mark.parametrize("mutation", ("empty", "partial", "schema-drift"))
def test_semantic_width_view_requires_closed_document(mutation: str) -> None:
    """A partial or schema-drifted profile cannot supply authoritative widths."""
    document = validator.load_document(PROFILE_PATH)
    if mutation == "empty":
        document.clear()
    elif mutation == "partial":
        model = document["semantic_width_model"]
        document.clear()
        document["semantic_width_model"] = model
    else:
        document["schema_version"] = 999
    with pytest.raises(validator.ProfileValidationError):
        _ = validator.semantic_width_model(document)


def test_semantic_width_model_handles_full_and_partial_chunks() -> None:
    """Any admitted width maps to ceil(N/5) chunks without a hard-coded cap."""
    model = validator.semantic_width_model()
    expected = {
        10: ((5, 5), 10),
        14: ((5, 5, 4), 15),
        15: ((5, 5, 5), 15),
        16: ((5, 5, 5, 1), 20),
        31: ((5, 5, 5, 5, 5, 5, 1), 35),
    }
    for word_trits, (chunks, padded) in expected.items():
        assert model.admits(word_trits)
        assert model.chunk_widths(word_trits) == chunks
        assert model.chunk_count(word_trits) == len(chunks)
        assert model.padded_trits(word_trits) == padded
    assert not model.admits(9)


def test_current_profile_identity_is_distinct() -> None:
    """Current-language identity never aliases historical conformance."""
    document = validator.load_document(PROFILE_PATH)
    assert document["current_profile"] == validator.CURRENT_PROFILE_ID
    assert document["current_profile"] != validator.HISTORICAL_PROFILE


def test_geometry_views_reject_foreign_direct_inputs() -> None:
    """Validate geometry documents and IDs before lookup operations."""
    with pytest.raises(validator.ProfileValidationError, match="must be an object"):
        _ = validator.current_profile_geometry(cast("validator.JsonObject", object()))

    document = validator.load_document(PROFILE_PATH)
    foreign_id = cast("str", cast("object", []))
    with pytest.raises(validator.ProfileValidationError, match="profile identity"):
        _ = validator.profile_geometry(document, foreign_id)
    with pytest.raises(validator.ProfileValidationError, match="profile identity"):
        _ = validator.profile_fingerprint(document, foreign_id)


def test_current_profile_geometry_view_matches_canonical_document() -> None:
    """Implemented consumers receive exact selected geometry from one API."""
    geometry = validator.current_profile_geometry()
    assert geometry.profile_id == CURRENT_PROFILE
    assert geometry.word_trits == CURRENT_TRITS
    assert geometry.word_modulus == CURRENT_WORDS
    assert geometry.memory_words == CURRENT_WORDS
    assert geometry.eof_word == CURRENT_EOF
    assert geometry.input_instruction == INTERPRETER_INPUT
    assert geometry.output_instruction == INTERPRETER_OUTPUT


def test_target_profile_contract_tracks_selected_geometry() -> None:
    """The owning human contract cannot lag the selected profile geometry."""
    text = TARGET_PROFILE_CONTRACT.read_text(encoding="utf-8")
    implementation = text.split("### Implementation Status", maxsplit=1)[1].split(
        "## Invariants", maxsplit=1
    )[0]
    assert f"N = {CURRENT_TRITS}" in implementation
    assert f"{CURRENT_WORDS:,}" in implementation
    assert f"{CURRENT_EOF:,}" in implementation
    assert VERSIONED_N14_DOC in implementation
    assert STALE_CURRENT_GEOMETRY_DOC not in implementation


def test_profile_file_rejects_invalid_utf8(tmp_path: Path) -> None:
    """Profile file encoding failure remains a typed validation error."""
    path = tmp_path / "profile.json"
    _ = path.write_bytes(bytes((0x7B, 0xFF, 0x7D)))
    with pytest.raises(
        validator.ProfileValidationError,
        match="invalid target-profile UTF-8",
    ):
        _ = validator.load_document(path)


def test_profile_file_utf8_error_preserves_native_cause(tmp_path: Path) -> None:
    """Malformed UTF-8 reports a useful native error and preserves its cause."""
    path = tmp_path / "profile.json"
    _ = path.write_bytes(b"{\xff}")
    with pytest.raises(
        validator.ProfileValidationError, match="invalid target-profile UTF-8"
    ) as caught:
        _ = validator.load_document(path)
    assert type(caught.value.__cause__) is UnicodeDecodeError
    assert "position 1" in str(caught.value)


def test_profile_file_utf8_error_never_formats_foreign_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An injected decoder failure cannot execute foreign formatter hooks."""

    class ForeignUnicodeFault(UnicodeDecodeError):
        def __str__(self) -> str:
            raise AssertionError("foreign Unicode formatter executed")

    fault = ForeignUnicodeFault("utf-8", b"\xff", 0, 1, "host failure")

    class FailingBytes(bytes):
        def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
            del encoding, errors
            raise fault

    monkeypatch.setattr(validator, "_read_profile_bytes", lambda _path: FailingBytes())
    with pytest.raises(
        validator.ProfileValidationError, match="invalid target-profile UTF-8"
    ) as caught:
        _ = validator.load_document(tmp_path / "profile.json")
    assert caught.value.__cause__ is fault


def test_profile_file_rejects_linked_leaf_and_directory(tmp_path: Path) -> None:
    """Profile authority cannot be supplied through path redirects."""
    original = tmp_path / "profile.json"
    _ = original.write_text(_canonical_text(), encoding="utf-8")
    leaf = tmp_path / "linked-profile.json"
    parent = tmp_path / "linked-directory"
    try:
        leaf.symlink_to(original)
        parent.symlink_to(tmp_path, target_is_directory=True)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"symlinks unsupported on this platform: {error}")
    for redirected in (leaf, parent / original.name):
        with pytest.raises(validator.ProfileValidationError, match=r"redirect|regular"):
            _ = validator.load_document(redirected)


def test_target_profile_cli_refuses_linked_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Canonical validator CLI must not resolve aliases before admission."""
    source = tmp_path / "profile.json"
    _ = source.write_text(_canonical_text(), encoding="utf-8")
    linked = tmp_path / "profile-link.json"
    try:
        linked.symlink_to(source)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"symlinks unsupported on this platform: {error}")
    monkeypatch.setattr(sys, "argv", ["target_profile", str(linked)])
    assert validator.main() == 1
    result = capsys.readouterr()
    assert result.err.startswith(
        "error: target-profile document must be a regular file"
    )
    assert not result.out


def test_profile_file_rejects_nonregular_and_oversized_sources(
    tmp_path: Path,
) -> None:
    """Untrusted profile documents have a finite regular-file boundary."""
    with pytest.raises(validator.ProfileValidationError, match="regular"):
        _ = validator.load_document(tmp_path)
    large = tmp_path / "huge.json"
    with large.open("wb") as stream:
        _ = stream.truncate(validator.MAX_DOCUMENT_BYTES + 1)
    with pytest.raises(validator.ProfileValidationError, match="byte limit"):
        _ = validator.load_document(large)
    missing = tmp_path / "missing.json"
    with pytest.raises(validator.ProfileValidationError, match="failed to read"):
        _ = validator.load_document(missing)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
@pytest.mark.parametrize(
    "operation",
    (
        "parent_symlink",
        "parent_junction",
        "leaf_lstat",
        "leaf_symlink",
        "leaf_junction",
        "open",
        "fdopen",
        "fstat",
    ),
)
def test_target_profile_host_file_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """Untrusted filesystem inspection failures stay within profile errors."""
    source = tmp_path / "profile.json"
    _ = source.write_text(_canonical_text(), encoding="utf-8")
    if operation == "leaf_lstat":
        original_lstat = Path.lstat

        def fail_lstat(path: Path) -> os.stat_result:
            if path == source:
                raise fault_type("injected profile lstat fault")
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    elif operation in {
        "parent_symlink",
        "parent_junction",
        "leaf_symlink",
        "leaf_junction",
    }:
        target = source.parent if operation.startswith("parent_") else source
        method = Path.is_symlink if operation.endswith("symlink") else Path.is_junction

        def fail_redirect(path: Path) -> bool:
            if path == target:
                raise fault_type("injected profile redirect status fault")
            return method(path)

        monkeypatch.setattr(
            Path,
            "is_symlink" if operation.endswith("symlink") else "is_junction",
            fail_redirect,
        )
    elif operation == "open":
        original_open = os.open

        def fail_open(path: Path, flags: int) -> int:
            if path == source:
                raise fault_type("injected profile open fault")
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", fail_open)
    elif operation == "fdopen":

        def fail_fdopen(_descriptor: int, _mode: str) -> object:
            raise fault_type("injected profile fdopen fault")

        monkeypatch.setattr(os, "fdopen", fail_fdopen)
    else:

        def fail_fstat(_descriptor: int) -> os.stat_result:
            raise fault_type("injected profile fstat fault")

        monkeypatch.setattr(os, "fstat", fail_fstat)
    with pytest.raises(validator.ProfileValidationError, match="failed to read"):
        _ = validator.load_document(source)


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
def test_target_profile_fdopen_failure_releases_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """An incomplete profile stream releases its owned file descriptor."""
    source = tmp_path / "profile.json"
    _ = source.write_text(_canonical_text(), encoding="utf-8")
    original_open = os.open
    opened: list[int] = []

    def track_open(path: Path, flags: int) -> int:
        descriptor = original_open(path, flags)
        if path == source:
            opened.append(descriptor)
        return descriptor

    def fail_fdopen(_descriptor: int, _mode: str) -> object:
        raise fault_type("injected profile fdopen fault")

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    with pytest.raises(validator.ProfileValidationError, match="failed to read"):
        _ = validator.load_document(source)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


def test_profile_file_refuses_fifo_without_blocking(tmp_path: Path) -> None:
    """A writerless FIFO cannot hang canonical profile validation."""
    mkfifo = cast("Callable[[Path], None] | None", getattr(os, "mkfifo", None))
    if mkfifo is None:
        pytest.skip("FIFOs are unavailable on this host")
    fifo = tmp_path / "source.fifo"
    mkfifo(fifo)
    with pytest.raises(validator.ProfileValidationError, match="regular"):
        _ = validator.load_document(fifo)


def test_profile_file_rejects_same_byte_swap_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inode replacement after lstat must not pass the snapshot check."""
    source = tmp_path / "profile.json"
    replacement = tmp_path / "replacement.json"
    content = _canonical_text()
    _ = source.write_text(content, encoding="utf-8")
    _ = replacement.write_text(content, encoding="utf-8")
    real_open = os.open

    def swap_on_open(path: Path, flags: int) -> int:
        _ = replacement.replace(source)
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_on_open)
    with pytest.raises(validator.ProfileValidationError, match="changed before read"):
        _ = validator.load_document(source)


def test_profile_file_rejects_same_byte_swap_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replacement after consuming source bytes also invalidates JSON."""
    source = tmp_path / "profile.json"
    replacement = tmp_path / "replacement.json"
    content = _canonical_text()
    _ = source.write_text(content, encoding="utf-8")
    _ = replacement.write_text(content, encoding="utf-8")
    real_lstat = Path.lstat
    recheck_index = 2
    checks = 0

    def swap_at_recheck(path: Path) -> os.stat_result:
        nonlocal checks
        if path == source:
            checks += 1
            if checks == recheck_index:
                _ = replacement.replace(source)
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", swap_at_recheck)
    with pytest.raises(validator.ProfileValidationError, match="changed during read"):
        _ = validator.load_document(source)
    assert checks == recheck_index


def test_profile_file_rejects_in_place_update_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changes to bytes of the same inode cannot validate a stale snapshot."""
    source = tmp_path / "profile.json"
    content = _canonical_text().encode("utf-8")
    _ = source.write_bytes(content)
    real_lstat = Path.lstat
    recheck_index = 2
    checks = 0

    def change_at_recheck(path: Path) -> os.stat_result:
        nonlocal checks
        if path == source:
            checks += 1
            if checks == recheck_index:
                with source.open("r+b") as stream:
                    _ = stream.write(b"x")
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", change_at_recheck)
    with pytest.raises(validator.ProfileValidationError, match="changed during read"):
        _ = validator.load_document(source)
    assert checks == recheck_index


def test_inconsistent_giant_trit_count_rejects_before_power() -> None:
    """Impossible billion-trit geometry cannot trigger huge exponentiation."""
    changed = _canonical_text().replace('"trits": 15', '"trits": 1000000000', 1)
    assert changed != _canonical_text()
    with pytest.raises(
        validator.ProfileValidationError,
        match="modulus must equal radix",
    ):
        validator.validate_text(changed)


def test_large_valid_word_geometry_has_no_artificial_trit_cap() -> None:
    """The rejection bound still admits a matching large ternary modulus."""
    trits = 256
    modulus = 3**trits
    text = _canonical_text()
    for before, after in (
        ('"trits": 15', f'"trits": {trits}'),
        (f'"modulus": {CURRENT_WORDS}', f'"modulus": {modulus}'),
        (f'"words": {CURRENT_WORDS}', f'"words": {modulus}'),
        (f'"eof_word": {CURRENT_EOF}', f'"eof_word": {modulus - 1}'),
    ):
        assert before in text
        text = text.replace(before, after, 1)
    validator.validate_text(text)


def test_duplicate_json_keys_fail_closed() -> None:
    """Duplicate object keys are rejected before semantic validation."""
    _expect_invalid('{"schema_version":2,"schema_version":2}')


def test_historical_word_model_cannot_drift() -> None:
    """The frozen 1998 ten-trit word domain cannot be enlarged in place."""
    changed = _canonical_text().replace('"trits": 10', '"trits": 11', 1)
    _expect_invalid(changed)


def test_current_semantic_core_cannot_drift_in_schema_v2() -> None:
    """Schema v2 does not admit a parallel current guest profile."""
    marker = '"guest_order": "sequential"'
    before, separator, current = _canonical_text().rpartition(marker)
    assert separator == marker
    changed = before + '"guest_order": "parallel"' + current
    _expect_invalid(changed)


def test_single_word_memory_matches_word_modulus() -> None:
    """Single-word modular memory cannot escape its address word domain."""
    marker = '"words": 4782969'
    before, separator, current = _canonical_text().rpartition(marker)
    assert separator == marker
    _expect_invalid(before + '"words": 4782968' + current)


def test_unknown_schema_key_fails_closed() -> None:
    """Unknown top-level policy is rejected instead of ignored."""
    changed = _canonical_text().replace(
        '"schema_version": 2,',
        '"schema_version": 2, "implicit_fallback": true,',
        1,
    )
    _expect_invalid(changed)


def test_current_profile_is_fourteen_trit_scalable_geometry() -> None:
    """The current profile is the first selected scalable ternary geometry."""
    document = validator.load_document(PROFILE_PATH)
    profiles = document["profiles"]
    assert isinstance(profiles, dict)
    current_id = document["current_profile"]
    assert isinstance(current_id, str)
    assert current_id == CURRENT_PROFILE
    current = profiles[current_id]
    assert isinstance(current, dict)
    assert current["version"] == CURRENT_VERSION
    word = current["word"]
    memory = current["memory"]
    semantics = current["semantics"]
    assert isinstance(word, dict)
    assert isinstance(memory, dict)
    assert isinstance(semantics, dict)
    assert word["trits"] == CURRENT_TRITS
    assert word["modulus"] == CURRENT_WORDS
    assert memory["words"] == CURRENT_WORDS
    assert semantics["eof_word"] == CURRENT_EOF
    assert semantics["input_instruction"] == INTERPRETER_INPUT
    assert semantics["output_instruction"] == INTERPRETER_OUTPUT


def test_published_pre_compatibility_profiles_retain_io_assignment() -> None:
    """The 2026.1/.2 identities keep their published specification-first I/O."""
    document = validator.load_document(PROFILE_PATH)
    profiles = document["profiles"]
    assert isinstance(profiles, dict)
    for profile_id in ("malbolge-2026.1", "malbolge-2026.2"):
        profile = profiles[profile_id]
        assert isinstance(profile, dict)
        semantics = profile["semantics"]
        assert isinstance(semantics, dict)
        assert semantics["input_instruction"] == SPECIFICATION_INPUT
        assert semantics["output_instruction"] == SPECIFICATION_OUTPUT


def test_interpreter_compatible_transition_remains_versioned() -> None:
    """The published 2026.3 identity remains immutable evidence."""
    document = validator.load_document(PROFILE_PATH)
    profiles = document["profiles"]
    assert isinstance(profiles, dict)
    current = profiles[CURRENT_PROFILE]
    transition = profiles[TRANSITION_PROFILE]
    assert isinstance(current, dict)
    assert isinstance(transition, dict)
    assert transition["kind"] == validator.VERSIONED_KIND
    assert transition["version"] == TRANSITION_VERSION
    assert transition["word"] == {
        "radix": WIDTH_MODEL_RADIX,
        "trits": 14,
        "modulus": TRANSITION_WORDS,
    }
    assert transition["memory"] == {
        "model": validator.MEMORY_MODEL,
        "words": TRANSITION_WORDS,
    }
    transition_semantics = cast("dict[str, object]", transition["semantics"])
    current_semantics = cast("dict[str, object]", current["semantics"])
    assert {
        key: value for key, value in transition_semantics.items() if key != EOF_WORD_KEY
    } == {key: value for key, value in current_semantics.items() if key != EOF_WORD_KEY}
    assert transition_semantics[EOF_WORD_KEY] == TRANSITION_EOF
    assert current_semantics[EOF_WORD_KEY] == CURRENT_EOF
    assert validator.profile_fingerprint(
        document, TRANSITION_PROFILE
    ) != validator.profile_fingerprint(document, CURRENT_PROFILE)


@pytest.mark.parametrize(
    "profile_id",
    ("malbolge-2026.1", "malbolge-2026.2", "malbolge-2026.3"),
)
def test_published_versioned_profile_cannot_be_omitted(profile_id: str) -> None:
    """Each published profile must survive canonical registry validation."""
    document = validator.loads_document(_canonical_text())
    profiles = cast("dict[str, object]", document["profiles"])
    del profiles[profile_id]
    with pytest.raises(validator.ProfileValidationError, match="published profile"):
        validator.validate_document(document)


@pytest.mark.parametrize(
    "profile_id",
    ("malbolge-2026.1", "malbolge-2026.2", "malbolge-2026.3"),
)
@pytest.mark.parametrize("mutation", ("kind", "version", "geometry", "io"))
def test_published_versioned_profile_cannot_be_redefined(
    profile_id: str,
    mutation: str,
) -> None:
    """A published identity cannot be rebound to different registry behavior."""
    document = validator.loads_document(_canonical_text())
    profiles = cast("dict[str, object]", document["profiles"])
    profile = cast("dict[str, object]", profiles[profile_id])
    if mutation == "kind":
        profile["kind"] = validator.HISTORICAL_KIND
    elif mutation == "version":
        profile["version"] = "2099"
    elif mutation == "geometry":
        word = cast("dict[str, object]", profile["word"])
        memory = cast("dict[str, object]", profile["memory"])
        semantics = cast("dict[str, object]", profile["semantics"])
        word["trits"] = 16
        word["modulus"] = 3**16
        memory["words"] = 3**16
        semantics["eof_word"] = 3**16 - 1
    else:
        semantics = cast("dict[str, object]", profile["semantics"])
        semantics["input_instruction"], semantics["output_instruction"] = (
            semantics["output_instruction"],
            semantics["input_instruction"],
        )
    with pytest.raises(validator.ProfileValidationError, match="published profile"):
        validator.validate_document(document)


def test_annual_current_identity_cannot_drift() -> None:
    """Schema v2 fixes the official selected identity to the release year."""
    changed = _canonical_text().replace(
        '"current_profile": "malbolge-2026"',
        '"current_profile": "malbolge-2026.3"',
        1,
    )
    _expect_invalid(changed)


def test_annual_current_version_cannot_drift() -> None:
    """The official annual profile version matches its year-only ID."""
    changed = _canonical_text().replace(
        '"version": "2026"',
        '"version": "2026.3"',
        1,
    )
    _expect_invalid(changed)


def test_io_instructions_must_be_assigned_exactly_once() -> None:
    """Profiles cannot alias or replace the two versioned I/O opcodes."""
    changed = _canonical_text().replace(
        '"input_instruction": "/",',
        '"input_instruction": "<",',
        1,
    )
    _expect_invalid(changed)


def test_scaled_eof_must_track_word_maximum() -> None:
    """EOF remains the all-two-trit maximum word for every geometry."""
    changed = _canonical_text().replace(
        '"eof_word": 4782968',
        '"eof_word": 59048',
        1,
    )
    _expect_invalid(changed)


def test_only_selected_profile_has_current_kind() -> None:
    """Old profile identities cannot also claim to be the current default."""
    changed = _canonical_text().replace(
        '"kind": "versioned"',
        '"kind": "current"',
        1,
    )
    _expect_invalid(changed)


def test_rust_semantic_width_projection_matches_canonical_model() -> None:
    """Checked-in Rust width constants are a byte-exact JSON projection."""
    document = validator.load_document(PROFILE_PATH)
    expected = validator.render_rust_semantic_width_projection(document)
    observed = validator.RUST_SEMANTIC_WIDTH_PROJECTION.read_text(encoding="utf-8")
    assert observed == expected


def test_rust_projection_matches_canonical_profile() -> None:
    """Checked-in Rust profile data is a byte-exact JSON projection."""
    document = validator.load_document(PROFILE_PATH)
    expected = validator.render_rust_projection(document)
    observed = validator.RUST_PROJECTION.read_text(encoding="utf-8")
    assert observed == expected


def test_fingerprint_manifest_matches_canonical_profile() -> None:
    """Checked-in fingerprints are a byte-exact canonical projection."""
    document = validator.load_document(PROFILE_PATH)
    expected = validator.render_profile_fingerprint_manifest(document)
    observed = validator.FINGERPRINT_MANIFEST.read_text(encoding="utf-8")
    assert observed == expected


def test_transition_and_historical_fingerprints_are_distinct() -> None:
    """Equal geometry does not collapse distinct published identities."""
    document = validator.load_document(PROFILE_PATH)
    historical = validator.profile_fingerprint(document, "malbolge-1998")
    transition = validator.profile_fingerprint(document, "malbolge-2026.1")
    assert historical != transition


@pytest.mark.parametrize(
    "fault_type",
    [validator.json.JSONDecodeError, ValueError, TypeError, RuntimeError],
)
def test_profile_json_parser_never_formats_foreign_errors(
    monkeypatch: pytest.MonkeyPatch, fault_type: type[Exception]
) -> None:
    """A hostile JSON decoder error remains typed without formatter hooks."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign profile JSON exception formatter executed")

    foreign = type("ForeignProfileJsonFault", (fault_type,), {"__str__": unsafe_str})
    fault = (
        foreign("decoder fault", '{"invalid', 1)
        if fault_type is validator.json.JSONDecodeError
        else foreign("decoder fault")
    )

    def fail_json(_text: str, *, object_pairs_hook: object) -> None:
        del object_pairs_hook
        raise fault

    monkeypatch.setattr(validator.json, "loads", fail_json)
    with pytest.raises(
        validator.ProfileValidationError, match="invalid JSON"
    ) as caught:
        validator.loads_document(_canonical_text())
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("entrypoint", ["text", "file", "parser"])
def test_profile_json_parser_binds_native_receipts_to_original_text(
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: str,
) -> None:
    """A substituted JSON decoder cannot alter an accepted width contract."""
    source = _canonical_text()
    native_loads = json.loads
    forged = cast("validator.JsonObject", native_loads(source))
    width = cast("dict[str, object]", forged["semantic_width_model"])
    width["maximum_trits"] = 100
    # The forged document is still a valid profile, so schema validation
    # alone cannot establish the bytes that the validator actually parsed.
    validator.validate_document(forged)

    def forged_loads(_text: str, *, object_pairs_hook: object) -> object:
        del object_pairs_hook
        return forged

    monkeypatch.setattr(json, "loads", forged_loads)

    with pytest.raises(
        validator.ProfileValidationError,
        match="JSON decoder provider differs from source",
    ):
        if entrypoint == "text":
            validator.validate_text(source)
        elif entrypoint == "file":
            _ = validator.load_document(PROFILE_PATH)
        else:
            _ = validator.loads_document(source)


def test_profile_json_parser_allows_equivalent_delegating_decoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An equivalent adapter does not alter source-bound profile evidence."""
    native_loads = json.loads

    def delegated(text: str, *, object_pairs_hook: object) -> object:
        return native_loads(
            text,
            object_pairs_hook=cast(
                "Callable[[list[tuple[str, object]]], object]", object_pairs_hook
            ),
        )

    monkeypatch.setattr(json, "loads", delegated)
    validator.validate_text(_canonical_text())


@pytest.mark.parametrize("source", ("{}", "[]", "{invalid"))
def test_profile_parser_rejects_forged_decoder_that_restores_itself(
    monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """Changing the public parser back during decoding cannot skip source check."""
    native = json.loads

    def forged(_text: str, *, object_pairs_hook: object) -> object:
        del object_pairs_hook
        monkeypatch.setattr(json, "loads", native)
        return {"fabricated": "admitted"}

    monkeypatch.setattr(json, "loads", forged)
    with pytest.raises(
        validator.ProfileValidationError,
        match="JSON decoder provider differs from source|invalid JSON",
    ):
        _ = validator.loads_document(source)


def test_profile_parser_returns_source_owned_tree_from_equivalent_decoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutating a substituted decoder's result cannot rewrite admitted profile data."""
    source = _canonical_text()
    aliased = cast("validator.JsonObject", json.loads(source))
    original = aliased["schema_version"]

    def equivalent(_text: str, **_kwargs: object) -> object:
        return aliased

    monkeypatch.setattr(json, "loads", equivalent)
    document = validator.loads_document(source)
    aliased["schema_version"] = "forged"
    assert document is not aliased
    assert document["schema_version"] == original


def test_profile_json_parser_rejects_foreign_nested_key_before_equality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A colliding foreign key cannot run hooks during source comparison."""

    class ForeignKey(str):
        @override
        def __hash__(self) -> int:
            return str.__hash__(self)

        @override
        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign profile key equality executed")

    source = _canonical_text()
    native = cast("dict[str, object]", json.loads(source))
    profiles = cast("dict[str, object]", native["profiles"]).copy()
    current = profiles.pop("malbolge-2026")
    profiles[ForeignKey("malbolge-2026")] = current
    native["profiles"] = profiles
    monkeypatch.setattr(json, "loads", lambda _text, **_kwargs: native)

    with pytest.raises(validator.ProfileValidationError, match="non-native string key"):
        _ = validator.loads_document(source)


def test_native_profile_json_syntax_diagnostic_keeps_position_and_cause() -> None:
    """Native JSON syntax errors preserve actionable source coordinates."""
    with pytest.raises(
        validator.ProfileValidationError, match="invalid JSON"
    ) as caught:
        validator.loads_document('{"broken":')
    assert type(caught.value.__cause__) is validator.json.JSONDecodeError
    assert "line" in str(caught.value)


@pytest.mark.parametrize("position", ["root", "nested", "key"])
def test_profile_json_parser_refuses_foreign_mapping_receipts(
    monkeypatch: pytest.MonkeyPatch, position: str
) -> None:
    """JSON map and key subclasses are rejected before inherited hooks run."""

    class ForeignMap(dict[str, object]):
        def items(self):  # type: ignore[override]
            raise AssertionError("foreign profile map iteration executed")

    class ForeignKey(str):
        __hash__ = str.__hash__

        def __str__(self) -> str:
            raise AssertionError("foreign profile key formatter executed")

    native = validator.json.loads(_canonical_text())
    if position == "root":
        forged: object = ForeignMap(native)
    elif position == "nested":
        forged = {**native, "profiles": ForeignMap(native["profiles"])}
    else:
        forged = {**native, ForeignKey("untrusted"): "value"}
    monkeypatch.setattr(validator.json, "loads", lambda _text, **_kwargs: forged)
    expected = "non-native string key" if position == "key" else "must be an object"
    with pytest.raises(validator.ProfileValidationError, match=expected):
        validator.validate_text(_canonical_text())


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_profile_file_host_faults_never_format_foreign_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Host status error subclasses cannot escape trusted failure handling."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign target-profile host formatter executed")

    foreign = type("ForeignProfileHostFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe filesystem detail")
    path = tmp_path / "profile.json"
    _ = path.write_text(_canonical_text(), encoding="utf-8")
    original_lstat = Path.lstat

    def fail_lstat(candidate: Path) -> os.stat_result:
        if candidate == path:
            raise fault
        return original_lstat(candidate)

    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(
        validator.ProfileValidationError, match="failed to read"
    ) as caught:
        validator.load_document(path)
    assert caught.value.__cause__ is fault


def test_profile_native_host_errors_keep_original_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact built-in host errors remain diagnosable after wrapping."""
    path = tmp_path / "profile.json"
    _ = path.write_text(_canonical_text(), encoding="utf-8")
    fault = OSError("native profile read blocked")
    original_open = os.open

    def fail_open(candidate: Path, flags: int) -> int:
        if candidate == path:
            raise fault
        return original_open(candidate, flags)

    monkeypatch.setattr(os, "open", fail_open)
    with pytest.raises(
        validator.ProfileValidationError, match="native profile read blocked"
    ) as caught:
        validator.load_document(path)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("position", ["pairs", "pair", "key"])
def test_profile_duplicate_key_hook_refuses_foreign_containers(
    position: str,
) -> None:
    """The JSON object-pairs callback never executes foreign list/key hooks."""

    class ForeignPairs(list[tuple[str, object]]):
        def __iter__(self):  # type: ignore[override]
            raise AssertionError("foreign JSON pairs iteration executed")

    class ForeignPair(tuple[str, object]):
        def __iter__(self):  # type: ignore[override]
            raise AssertionError("foreign JSON pair iteration executed")

    class ForeignKey(str):
        def __hash__(self) -> int:
            raise AssertionError("foreign JSON key hashing executed")

    if position == "pairs":
        pairs = ForeignPairs([("trusted", 1)])
    elif position == "pair":
        pairs = [ForeignPair(("trusted", 1))]
    else:
        pairs = [(ForeignKey("trusted"), 1)]
    with pytest.raises(validator.ProfileValidationError, match="JSON"):
        validator._reject_duplicate_pairs(  # pyright: ignore[reportPrivateUsage]
            cast("list[tuple[str, object]]", pairs)
        )


@pytest.mark.parametrize("phase", ["admitted", "opened", "after", "visible"])
def test_profile_foreign_stat_receipts_rejected_before_field_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Manifest identity cannot trust forged path or descriptor stat results."""
    source = tmp_path / "profile.json"
    _ = source.write_bytes(b"{}")

    class ForeignStat:
        @override
        def __getattribute__(self, name: str) -> object:
            del self, name
            raise AssertionError("foreign profile stat hook executed")

    original_lstat = Path.lstat
    original_fstat = os.fstat
    lstat_calls = 0
    fstat_calls = 0

    def forged_lstat(path: Path) -> os.stat_result:
        nonlocal lstat_calls
        if path == source:
            lstat_calls += 1
            if (phase == "admitted" and lstat_calls == 1) or (
                phase == "visible" and lstat_calls == 2
            ):
                return cast("os.stat_result", cast("object", ForeignStat()))
        return original_lstat(path)

    def forged_fstat(descriptor: int) -> os.stat_result:
        nonlocal fstat_calls
        fstat_calls += 1
        if (phase == "opened" and fstat_calls == 1) or (
            phase == "after" and fstat_calls == 2
        ):
            return cast("os.stat_result", cast("object", ForeignStat()))
        return original_fstat(descriptor)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    monkeypatch.setattr(os, "fstat", forged_fstat)
    with pytest.raises(validator.ProfileValidationError, match="native stat"):
        _ = validator.load_document(source)


@pytest.mark.parametrize(
    "phase", ["parent_symlink", "parent_junction", "leaf_symlink", "leaf_junction"]
)
@pytest.mark.parametrize("receipt", [0, 1, object()])
def test_profile_foreign_redirect_receipts_rejected_without_truthiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, receipt: object
) -> None:
    """Every source path redirect verdict must be an exact boolean."""
    source = tmp_path / "profile.json"
    _ = source.write_bytes(b"{}")
    leaf = phase.startswith("leaf")
    target = source if leaf else source.parent
    is_symlink = phase.endswith("symlink")
    original = Path.is_symlink if is_symlink else Path.is_junction

    class ForeignVerdict:
        def __bool__(self) -> bool:
            raise AssertionError("foreign redirect truthiness hook executed")

    verdict = ForeignVerdict() if type(receipt) is object else receipt

    def forged_method(path: Path) -> bool:
        if path == target:
            return cast("bool", verdict)
        return original(path)

    monkeypatch.setattr(
        Path, "is_symlink" if is_symlink else "is_junction", forged_method
    )
    with pytest.raises(validator.ProfileValidationError, match="native redirect"):
        _ = validator.load_document(source)


@pytest.mark.parametrize("receipt", [True, False, -1, 3.0])
def test_profile_foreign_open_descriptor_rejected_before_fd_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Invalid open values cannot become stream owners or close host fds."""
    source = tmp_path / "profile.json"
    _ = source.write_bytes(b"{}")
    original_open = os.open

    def forged_open(path: Path, flags: int) -> int:
        if path == source:
            return cast("int", receipt)
        return original_open(path, flags)

    monkeypatch.setattr(os, "open", forged_open)
    with pytest.raises(validator.ProfileValidationError, match="native descriptor"):
        _ = validator.load_document(source)


@pytest.fixture
def borrowed_profile_streams() -> Iterator[list[BinaryIO]]:
    """Close handles intentionally borrowed by forged stream fixtures."""
    opened: list[BinaryIO] = []
    yield opened
    for stream in reversed(opened):
        stream.close()


def test_profile_rejects_forged_valid_json_from_foreign_stream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_profile_streams: list[BinaryIO],
) -> None:
    """A forged stream cannot supply JSON unrelated to the on-disk file."""
    source = tmp_path / "profile.json"
    expected = b"{}"
    _ = source.write_bytes(b"!!")
    original_fdopen = os.fdopen

    def substituted_fdopen(descriptor: int, mode: str) -> BinaryIO:
        stream = cast("BinaryIO", original_fdopen(os.dup(descriptor), mode))
        borrowed_profile_streams.append(stream)
        return cast("BinaryIO", cast("object", _ProfileForgedStream(stream, expected)))

    monkeypatch.setattr(os, "fdopen", substituted_fdopen)
    with pytest.raises(validator.ProfileValidationError, match="native stream"):
        _ = validator.load_document(source)


def test_profile_rejects_native_reader_of_other_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_profile_streams: list[BinaryIO],
) -> None:
    """A real reader of a duplicated fd cannot replace the owned open handle."""
    source = tmp_path / "profile.json"
    _ = source.write_bytes(b"{}")
    original_fdopen = os.fdopen
    opened: list[int] = []

    def substituted_fdopen(descriptor: int, mode: str) -> BinaryIO:
        opened.append(descriptor)
        stream = cast("BinaryIO", original_fdopen(os.dup(descriptor), mode))
        borrowed_profile_streams.append(stream)
        return stream

    monkeypatch.setattr(os, "fdopen", substituted_fdopen)
    with pytest.raises(validator.ProfileValidationError, match="native stream"):
        _ = validator.load_document(source)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


class _ProfileForgedStream:
    """Own a native stream but expose a selected forged return value."""

    def __init__(
        self, stream: BinaryIO, payload: object, descriptor: object = None
    ) -> None:
        self.stream: BinaryIO = stream
        self.payload: object = payload
        self.descriptor: object = descriptor

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        del args
        self.stream.close()

    def fileno(self) -> int:
        return cast(
            "int",
            self.descriptor if self.descriptor is not None else self.stream.fileno(),
        )

    def read(self, size: int) -> bytes:
        del size
        return cast("bytes", self.payload)


@pytest.mark.parametrize("kind", ["str", "list", "subclass"])
def test_profile_foreign_stream_byte_receipt_rejected_before_length(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_profile_streams: list[BinaryIO],
    kind: str,
) -> None:
    """Forged stream bytes cannot execute caller-owned byte hooks."""
    source = tmp_path / "profile.json"
    _ = source.write_bytes(b"{}")
    original_fdopen = os.fdopen

    class ForeignBytes(bytes):
        @override
        def __len__(self) -> int:
            raise AssertionError("foreign byte length hook executed")

    receipts: dict[str, object] = {
        "str": "{}",
        "list": list(b"{}"),
        "subclass": ForeignBytes(b"{}"),
    }

    def forged_fdopen(fd: int, mode: str) -> BinaryIO:
        stream = cast("BinaryIO", original_fdopen(os.dup(fd), mode))
        borrowed_profile_streams.append(stream)
        return cast(
            "BinaryIO", cast("object", _ProfileForgedStream(stream, receipts[kind]))
        )

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    with pytest.raises(validator.ProfileValidationError, match="native stream"):
        _ = validator.load_document(source)


@pytest.mark.parametrize("receipt", [True, -1, 3.0])
def test_profile_foreign_stream_descriptor_rejected_before_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_profile_streams: list[BinaryIO],
    receipt: object,
) -> None:
    """A forged stream fileno must never reach os.fstat."""
    source = tmp_path / "profile.json"
    _ = source.write_bytes(b"{}")
    original_fdopen = os.fdopen

    def forged_fdopen(fd: int, mode: str) -> BinaryIO:
        stream = cast("BinaryIO", original_fdopen(os.dup(fd), mode))
        borrowed_profile_streams.append(stream)
        return cast(
            "BinaryIO", cast("object", _ProfileForgedStream(stream, b"{}", receipt))
        )

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    with pytest.raises(validator.ProfileValidationError, match="native stream"):
        _ = validator.load_document(source)


@pytest.mark.parametrize("supplied", ("list", "token"))
def test_target_profile_cli_rejects_foreign_arguments_before_hooks(
    supplied: str,
) -> None:
    """Malformed CLI containers and tokens cannot decide profile admission."""

    class ForeignList(list[str]):  # ruff: ignore[subclass-builtin]
        def __bool__(self) -> bool:
            raise AssertionError("foreign CLI argument truthiness executed")

    class ForeignToken(str):  # ruff: ignore[subclass-builtin]
        @override
        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign CLI token equality executed")

    arguments = ForeignList(["--help"]) if supplied == "list" else [ForeignToken("--help")]
    parser = cast("Callable[[list[str]], Path]", vars(validator)["_profile_argument"])
    with pytest.raises(validator.ProfileValidationError, match="native CLI"):
        _ = parser(cast("list[str]", arguments))


@pytest.mark.parametrize("command", ("success", "help"))
def test_target_profile_cli_rejects_short_success_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
) -> None:
    """Partial success/help responses never certify canonical target profiles."""

    class ShortOutput:
        def write(self, message: str) -> int:
            return len(message) - 1

        def flush(self) -> None:
            raise AssertionError("output flushed after short write")

    argument = "--help" if command == "help" else str(PROFILE_PATH)
    monkeypatch.setattr(sys, "argv", ["target_profile", argument])
    monkeypatch.setattr(sys, "stdout", ShortOutput())
    assert validator.main() == 1
    assert "output" in capsys.readouterr().err


class _UntrustedTargetWriteCount(int):
    """A hostile write-count subclass whose equality cannot be invoked."""

    @override
    def __eq__(self, other: object) -> bool:
        del other
        raise AssertionError("foreign target write-count equality invoked")


@pytest.mark.parametrize("command", ("success", "help"))
@pytest.mark.parametrize(
    "receipt",
    ("overlong", "bool", "foreign", "none", "write-error", "flush-error", "flush-receipt"),
)
def test_target_profile_cli_requires_complete_native_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    receipt: str,
) -> None:
    """Hostile output cannot certify a canonical profile or successful help."""
    flushes: list[bool] = []

    class BrokenOutput:
        def write(self, message: str) -> int:
            if receipt == "write-error":
                raise OSError("injected target output failure")
            values: dict[str, object] = {
                "overlong": len(message) + 1,
                "bool": True,
                "foreign": _UntrustedTargetWriteCount(len(message)),
                "none": None,
            }
            return cast("int", values.get(receipt, len(message)))

        def flush(self) -> None:
            flushes.append(True)
            if receipt == "flush-error":
                raise RuntimeError("injected target flush failure")
            if receipt == "flush-receipt":
                return cast("None", cast("object", True))
            return None

    argument = "--help" if command == "help" else str(PROFILE_PATH)
    monkeypatch.setattr(sys, "argv", ["target_profile", argument])
    monkeypatch.setattr(sys, "stdout", BrokenOutput())
    assert validator.main() == 1
    assert "output" in capsys.readouterr().err
    assert bool(flushes) == (receipt in ("flush-error", "flush-receipt"))


@pytest.mark.parametrize("receipt", ("short", "write-error", "flush-error", "bad-flush"))
def test_target_profile_cli_diagnostic_fault_preserves_rejection(
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """A failed profile still fails with broken diagnostic stream delivery."""

    class BrokenErrorOutput:
        def write(self, message: str) -> int:
            if receipt == "write-error":
                raise OSError("injected target error output failure")
            return len(message) - 1 if receipt == "short" else len(message)

        def flush(self) -> None:
            if receipt == "flush-error":
                raise ValueError("injected target error flush failure")
            if receipt == "bad-flush":
                return cast("None", cast("object", True))
            return None

    monkeypatch.setattr(sys, "argv", ["target_profile", "invalid", "extra"])
    monkeypatch.setattr(sys, "stderr", BrokenErrorOutput())
    assert validator.main() == 1


def test_target_profile_cli_preserves_normal_success_and_help_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Native output preserves the original stable CLI success/help contract."""
    monkeypatch.setattr(sys, "argv", ["target_profile"])
    assert validator.main() == 0
    result = capsys.readouterr()
    assert result.out == f"target profile valid: {PROFILE_PATH}\n"
    assert not result.err
    monkeypatch.setattr(sys, "argv", ["target_profile", "--help"])
    with pytest.raises(SystemExit) as exit_status:
        _ = validator.main()
    assert exit_status.value.code == 0
    assert capsys.readouterr().out == "usage: target_profile.py [PROFILE.json]\n"


@pytest.mark.parametrize("fault_type", [OSError, validator.ProfileValidationError])
def test_profile_foreign_cli_exception_formatter_not_invoked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """The CLI cannot call foreign error subclass string formatters."""

    class ForeignError(fault_type):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign profile CLI error formatter executed")

    fault = ForeignError("unsafe diagnostic")

    def fail_validate(_document: object) -> None:
        raise fault

    monkeypatch.setattr(validator, "validate_document", fail_validate)
    monkeypatch.setattr(sys, "argv", ["target_profile", str(tmp_path / "profile.json")])
    _ = (tmp_path / "profile.json").write_bytes(b"{}")
    assert validator.main() == 1
    assert "ForeignError" in capsys.readouterr().err
