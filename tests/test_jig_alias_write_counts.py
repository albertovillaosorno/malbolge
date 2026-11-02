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
#   - Exact-write regressions for atomic Python/Jig launcher publication.
# - Must-Not:
#   - Install Python, invoke Jig tools, or mutate real toolchain aliases.
# - Allows:
#   - Inputs: simulated short and malformed binary stream writes.
#   - Outputs: typed rejection, unchanged aliases, and private-temp cleanup.
#   - Side effects: test-local Python and Jig alias paths only.
# - Split-When:
#   - Another alias publisher gains independent file publication semantics.
# - Merge-When:
#   - Project bootstrap owns the same alias atomicity evidence.
# - Summary:
#   - Exercise fail-closed binary writes before Jig alias publication.
# - Description:
#   - Inject invalid write counts after the native writer has been admitted.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Partial or malformed writes preserve any previously committed target.
#

"""Regression evidence for Python and Jig atomic alias write counts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO, Self, cast

import pytest
from scripts.bootstrap import python_validation

_BAD_RESULTS = ("short", "overlong", "boolean", "missing")
_TOOL_ALIAS = "tool"
_PYTHON_LAUNCHER = "launcher"
_STABLE_BYTES = b"previously-verified-alias"


def _invalid_count(kind: str, expected: int) -> int:
    """Simulate a malformed byte-write acknowledgement.

    Returns:
        An incorrect, boolean, or missing write count.

    """
    results: dict[str, object] = {
        "short": expected - 1,
        "overlong": expected + 1,
        "boolean": True,
        "missing": None,
    }
    return cast("int", results[kind])


class _BrokenWriter:
    """Write incomplete bytes to a real temporary descriptor."""

    def __init__(self, stream: BinaryIO, result_kind: str) -> None:
        self._stream: BinaryIO = stream
        self._result_kind: str = result_kind

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *details: object) -> None:
        del details
        self._stream.close()

    def fileno(self) -> int:
        """Expose the real descriptor for POSIX executable-bit handling.

        Returns:
            The original open descriptor.

        """
        return self._stream.fileno()

    def write(self, payload: bytes) -> int:
        """Emit a partial payload with an invalid reported write result.

        Returns:
            An intentionally nonconforming byte count.

        """
        _ = self._stream.write(payload[:-1])
        return _invalid_count(self._result_kind, len(payload))


def _inject_defective_jig_writer(
    monkeypatch: pytest.MonkeyPatch, result_kind: str
) -> None:
    """Inject a faulty write only after native stream ownership is admitted."""
    native_open = python_validation._open_jig_alias_write_stream

    def defective_writer(descriptor: int) -> BinaryIO:
        return cast(
            "BinaryIO", cast("object", _BrokenWriter(native_open(descriptor), result_kind))
        )

    monkeypatch.setattr(
        python_validation, "_open_jig_alias_write_stream", defective_writer
    )


@pytest.mark.parametrize("result_kind", list(_BAD_RESULTS))
@pytest.mark.parametrize(
    "case",
    [
        (_TOOL_ALIAS, False),
        (_TOOL_ALIAS, True),
        (_PYTHON_LAUNCHER, False),
        (_PYTHON_LAUNCHER, True),
    ],
)
def test_alias_publication_rejects_incomplete_descriptor_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    result_kind: str,
    case: tuple[str, bool],
) -> None:
    """A failed private write must keep the old committed alias untouched."""
    kind, windows = case
    layout = python_validation.validation_layout(tmp_path, windows=windows)
    layout.scripts.mkdir(parents=True)
    if kind == _TOOL_ALIAS:
        suffix = ".exe" if windows else ""
        for tool_id in ("basedpyright", "pytest", "ruff"):
            _ = (layout.scripts / f"{tool_id}{suffix}").write_bytes(
                tool_id.encode("ascii")
            )
        parent = layout.environment / "jig-bin"
        parent.mkdir()
        target = parent / "basedpyright.bin"
    else:
        target = layout.python_launcher
        parent = target.parent
    _ = target.write_bytes(_STABLE_BYTES)
    _inject_defective_jig_writer(monkeypatch, result_kind)

    def publish() -> None:
        if kind == _TOOL_ALIAS:
            _ = python_validation.write_jig_tool_aliases(
                layout, windows=windows
            )
        else:
            python_validation.write_launchers(layout, windows=windows)

    with pytest.raises(python_validation.ProvisionError, match="write count"):
        publish()
    assert target.read_bytes() == _STABLE_BYTES
    assert not any(
        path.name.startswith(f".{target.name}.") for path in parent.iterdir()
    )


class _CloseFaultWriter:
    """Model a stage whose native writer fails on final close."""

    def __init__(self, stream: BinaryIO, fault: OSError) -> None:
        self._stream: BinaryIO = stream
        self._fault: OSError = fault

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_details: object) -> None:
        self._stream.close()
        raise self._fault

    def fileno(self) -> int:
        return self._stream.fileno()

    def write(self, payload: bytes) -> int:
        return self._stream.write(payload)


@pytest.mark.parametrize("phase", ["chmod", "close"])
def test_jig_alias_stage_host_fault_preserves_prior_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """A native stage chmod or close failure remains typed and unpublished."""
    target = tmp_path / "jig-bin" / "ruff.bin"
    target.parent.mkdir()
    _ = target.write_bytes(_STABLE_BYTES)
    fault = PermissionError(f"native {phase} failure")
    if phase == "chmod":
        def deny_chmod(_descriptor: int, _mode: int) -> None:
            raise fault

        monkeypatch.setattr(os, "fchmod", deny_chmod)
    else:
        native_open = python_validation._open_jig_alias_write_stream  # pyright: ignore[reportPrivateUsage]

        def fail_close(descriptor: int) -> BinaryIO:
            return cast(
                "BinaryIO",
                cast("object", _CloseFaultWriter(native_open(descriptor), fault)),
            )

        monkeypatch.setattr(python_validation, "_open_jig_alias_write_stream", fail_close)

    with pytest.raises(
        python_validation.ProvisionError, match="Jig alias staged write or close"
    ) as caught:
        python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
            target, b"new verified alias", windows=False
        )
    assert caught.value.__cause__ is fault
    assert target.read_bytes() == _STABLE_BYTES
    assert not list(target.parent.glob(".ruff.bin.*"))



def test_jig_alias_failed_stage_cleanup_is_typed_and_preserves_prior_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A denied private-stage unlink cannot leak an untyped host error."""
    target = tmp_path / "jig-bin" / "ruff.bin"
    target.parent.mkdir()
    _ = target.write_bytes(_STABLE_BYTES)
    fault = PermissionError("private stage unlink denied")
    native_unlink = Path.unlink
    _inject_defective_jig_writer(monkeypatch, "short")

    def deny_stage_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path.parent == target.parent and path.name.startswith(".ruff.bin."):
            raise fault
        native_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "unlink", deny_stage_unlink)
        with pytest.raises(
            python_validation.ProvisionError, match="Jig alias stage cleanup"
        ) as caught:
            python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
                target, b"replacement-alias", windows=True
            )
    assert caught.value.__cause__ is fault
    assert target.read_bytes() == _STABLE_BYTES
    leftovers = list(target.parent.glob(".ruff.bin.*"))
    assert len(leftovers) == 1
    leftovers[0].unlink()
