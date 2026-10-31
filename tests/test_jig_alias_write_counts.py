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
#   - Inject invalid write counts at the private descriptor boundary.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Partial or malformed writes preserve any previously committed target.
#

"""Regression evidence for Python and Jig atomic alias write counts."""

from __future__ import annotations

import os
from typing import BinaryIO
from typing import Self
from typing import TYPE_CHECKING
from typing import cast

import pytest
from scripts.bootstrap import python_validation

if TYPE_CHECKING:
    from pathlib import Path


_BAD_RESULTS = ("short", "overlong", "boolean", "missing")
_TOOL_ALIAS = "tool"
_PYTHON_LAUNCHER = "launcher"
_STABLE_BYTES = b"previously-verified-alias"
_BINARY_WRITE_MODE = "wb"


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


def _inject_defective_fdopen(
    monkeypatch: pytest.MonkeyPatch, result_kind: str
) -> None:
    real_fdopen = os.fdopen

    def fdopen(fd: int, mode: str) -> BinaryIO | _BrokenWriter:
        stream = cast("BinaryIO", real_fdopen(fd, mode))
        if mode == _BINARY_WRITE_MODE:
            return _BrokenWriter(stream, result_kind)
        return stream

    monkeypatch.setattr(os, "fdopen", fdopen)


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
    _inject_defective_fdopen(monkeypatch, result_kind)

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
