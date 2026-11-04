# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Regression tests for Jig alias stage byte integrity.
# - Must-Not:
#   - Execute native tool payloads or modify provisioning outside temporary tests.
# - Allows:
#   - Inputs: synthetic alias paths and injected stream/filesystem faults.
#   - Outputs: fail-closed physical alias publication evidence.
#   - Side effects: only temporary pytest paths.
# - Split-When:
#   - A distinct provisioning responsibility warrants separate coverage.
# - Merge-When:
#   - Another suite owns the same alias byte integrity boundary.
# - Summary:
#   - Reject forged writable streams and mutated Jig alias staging bytes.
#

"""Jig alias stage byte-integrity regressions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO, Self, cast

import pytest
from scripts.bootstrap import python_validation

ALIAS_BYTES = b"pinned-jig-alias"
PRESERVED_BYTES = b"preserved-jig-alias"


def _alias_target(tmp_path: Path) -> Path:
    target = tmp_path / "jig-bin" / "ruff.bin"
    target.parent.mkdir()
    _ = target.write_bytes(PRESERVED_BYTES)
    return target


def test_jig_alias_source_rejects_external_hardlink(
    tmp_path: Path,
) -> None:
    """Physical alias source bytes cannot be shared with outside hardlinks."""
    external = tmp_path / "outside-tool"
    _ = external.write_bytes(ALIAS_BYTES)
    source = tmp_path / "ruff-native"
    try:
        os.link(external, source)
    except OSError as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    with pytest.raises(
        python_validation.ProvisionError, match="Jig alias source.*single-link"
    ):
        _ = python_validation._read_jig_binary_source(source)
    assert external.read_bytes() == ALIAS_BYTES


@pytest.mark.parametrize("payload", [
    bytearray(ALIAS_BYTES), memoryview(ALIAS_BYTES),
])
def test_jig_alias_source_rejects_nonnative_read_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    """A substituted binary reader cannot authorize nonnative source bytes."""
    source = tmp_path / "ruff-native"
    _ = source.write_bytes(ALIAS_BYTES)

    def fake_open_read(
        _source: Path, _expected: tuple[int, int, int, int, int]
    ) -> bytes:
        return cast("bytes", payload)

    monkeypatch.setattr(
        python_validation, "_read_open_jig_binary", fake_open_read
    )
    with pytest.raises(
        python_validation.ProvisionError, match="Jig alias source.*native bytes"
    ):
        _ = python_validation._read_jig_binary_source(source)


def test_jig_alias_rejects_forged_writable_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A nonnative writer cannot swap bytes while reporting a full count."""
    target = _alias_target(tmp_path)
    original_fdopen = os.fdopen
    forged_streams: list[BinaryIO] = []

    class ForgedWriter:
        def __init__(self, stream: BinaryIO) -> None:
            self.stream = stream

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def write(self, data: bytes) -> int:
            altered = b"!" + data[1:]
            assert self.stream.write(altered) == len(altered)
            return len(data)

    def forged_fdopen(descriptor: int, mode: str) -> BinaryIO:
        if mode == "wb":
            stream = cast("BinaryIO", original_fdopen(os.dup(descriptor), mode))
            forged_streams.append(stream)
            return cast("BinaryIO", cast("object", ForgedWriter(stream)))
        return cast("BinaryIO", original_fdopen(descriptor, mode))

    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(os, "fdopen", forged_fdopen)
            with pytest.raises(
                python_validation.ProvisionError, match="native.*stream"
            ):
                python_validation._publish_jig_tool_alias(
                    target, ALIAS_BYTES, windows=True
                )
    finally:
        for stream in forged_streams:
            stream.close()
    assert target.read_bytes() == PRESERVED_BYTES
    assert list(target.parent.glob(f".{target.name}.*")) == []


def test_jig_alias_rejects_native_writer_on_substituted_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native writer on a different descriptor cannot claim stage ownership."""
    target = _alias_target(tmp_path)
    native_fdopen = os.fdopen
    originals: list[int] = []
    replacements: list[BinaryIO] = []

    def substituted_fdopen(descriptor: int, mode: str) -> BinaryIO:
        if mode == "wb":
            originals.append(descriptor)
            stream = cast("BinaryIO", native_fdopen(os.dup(descriptor), mode))
            replacements.append(stream)
            return stream
        return cast("BinaryIO", native_fdopen(descriptor, mode))

    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(os, "fdopen", substituted_fdopen)
            with pytest.raises(
                python_validation.ProvisionError, match="native.*descriptor"
            ):
                python_validation._publish_jig_tool_alias(
                    target, ALIAS_BYTES, windows=True
                )
        assert len(originals) == 1
        with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
            _ = os.fstat(originals[0])
    finally:
        for stream in replacements:
            stream.close()
    assert target.read_bytes() == PRESERVED_BYTES
    assert list(target.parent.glob(f".{target.name}.*")) == []


def test_jig_alias_rejects_mutated_stage_after_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A same-size postwrite substitution never replaces the prior alias."""
    target = _alias_target(tmp_path)
    original_admit = python_validation._check_jig_alias_path
    changed = False

    def mutate_on_prepublication_check(
        path: Path, *, directory: bool, required: bool
    ) -> os.stat_result | None:
        nonlocal changed
        status = original_admit(path, directory=directory, required=required)
        if path == target and not changed:
            stages = list(target.parent.glob(f".{target.name}.*"))
            if len(stages) == 1 and stages[0].stat().st_size == len(ALIAS_BYTES):
                with stages[0].open("r+b") as stream:
                    assert stream.write(b"!") == 1
                changed = True
        return status

    monkeypatch.setattr(
        python_validation, "_check_jig_alias_path", mutate_on_prepublication_check
    )
    with pytest.raises(
        python_validation.ProvisionError, match="Jig alias.*bytes"
    ):
        python_validation._publish_jig_tool_alias(
            target, ALIAS_BYTES, windows=True
        )
    assert changed
    assert target.read_bytes() == PRESERVED_BYTES
    assert list(target.parent.glob(f".{target.name}.*")) == []
