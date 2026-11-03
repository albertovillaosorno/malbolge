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
#   - Regressions for emitted Rust output path authenticity.
# - Must-Not:
#   - Modify project source trees or bypass output admission policy.
# - Allows:
#   - Inputs: synthetic local output paths and mutable late host hooks.
#   - Outputs: deterministic failure and path-integrity assertions.
#   - Side effects: temporary test filesystem state only.
# - Split-When:
#   - Split when another independent output path ABI needs coverage.
# - Merge-When:
#   - Merge when the emitter test suite owns this exact boundary.
# - Summary:
#   - Native output path identity regressions for Rust source emission.
# - Description:
#   - Ensures late pathlib and host encoders cannot redirect output.
# - Usage:
#   - Used by the source-bound diff test suite.
# - Defaults:
#   - Late path hook substitution fails closed.
#

"""Native output path identity regressions for Rust source emission."""

from __future__ import annotations

import builtins
import os
from pathlib import Path

import pytest
from algorithms.diff import emit_rust


def test_emitter_rejects_late_path_getattribute_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An original Path type with replaced getters is not an output authority."""
    destination = tmp_path / "destination.rs"
    redirected = tmp_path / "redirected.rs"
    _ = redirected.write_bytes(b"foreign")
    redirected_text = str(redirected)
    original = Path.__getattribute__
    calls = 0

    def forged_getattribute(path: Path, name: str) -> object:
        nonlocal calls
        if path is destination and name == "_str":
            calls += 1
            return redirected_text
        return original(path, name)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "__getattribute__", forged_getattribute)
        with pytest.raises(emit_rust.RustEmissionError, match="path hooks changed"):
            emit_rust._validate_output_path(destination)
    assert calls == 0
    assert not destination.exists()
    assert redirected.read_bytes() == b"foreign"


def test_emitter_rejects_late_path_getter_status_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An absent output cannot masquerade as a different existing leaf."""
    destination = tmp_path / "destination.rs"
    redirected = tmp_path / "redirected.rs"
    _ = redirected.write_bytes(b"foreign")
    redirected_text = str(redirected)
    original = Path.__getattribute__

    def forged_getattribute(path: Path, name: str) -> object:
        if path is destination and name == "_str":
            return redirected_text
        return original(path, name)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "__getattribute__", forged_getattribute)
        with pytest.raises(emit_rust.RustEmissionError, match="path hooks changed"):
            emit_rust._native_path_lstat(destination)
    assert not destination.exists()
    assert redirected.read_bytes() == b"foreign"


@pytest.mark.skipif(os.name == "nt", reason="POSIX raw-path encoding regression")
def test_emitter_rejects_late_fspath_redirect_of_fresh_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fresh multi-part output must not run a replacement os.fspath."""
    destination = Path(str(tmp_path), "destination.rs")
    native_fspath = os.fspath
    calls = 0

    def forged_fspath(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    ) -> str | bytes:
        nonlocal calls
        if path == "destination.rs":
            calls += 1
            return "redirected.rs"
        return native_fspath(path)

    with monkeypatch.context() as patched:
        patched.setattr(os, "fspath", forged_fspath)
        with pytest.raises(emit_rust.RustEmissionError, match="path hooks changed"):
            emit_rust._validate_output_path(destination)
    assert calls == 0
    assert not destination.exists()
    assert not (tmp_path / "redirected.rs").exists()


@pytest.mark.parametrize("entrypoint", ["preflight", "template"])
def test_emitter_rejects_late_host_str_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entrypoint: str
) -> None:
    """Late str aliases must not reach pathname parsing or resolver dispatch."""
    destination = tmp_path / "destination.rs"
    observed: Exception | None = None
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "str", bytes)
        try:
            if entrypoint == "preflight":
                emit_rust._validate_output_path(destination)
            else:
                emit_rust._require_output_not_runtime_template(destination)
        except emit_rust.RustEmissionError as error:
            observed = error
    assert type(observed) is emit_rust.RustEmissionError, observed
    assert "path hooks changed" in str(observed)
    assert not destination.exists()
