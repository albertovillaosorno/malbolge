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
#   - Tests for versioned deterministic search selection configuration.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Tests for versioned deterministic search selection configuration."""

from __future__ import annotations

import contextlib

import os
from pathlib import Path
from typing import BinaryIO
from typing import Never
from typing import TYPE_CHECKING
from typing import cast
from typing import override

from accelerator.search_config import SEARCH_CONFIGURATION_SCHEMA
from accelerator.search_config import SearchConfiguration
from accelerator.search_config import SearchConfigurationError
from accelerator.search_config import load_search_configuration
from accelerator.search_config import parse_search_configuration
from accelerator.search_selection import SearchSelection
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

ALGORITHM = "deterministic-corpus-enumeration-v1"
BACKEND = "cpu-reference"
GPU_BACKEND = "cuda-search"
OTHER_ALGORITHM = "other-search-v2"
SEARCH_CONFIG_SOURCE = "search.toml"
SOURCE_RECHECK = 2


def _config(*, algorithm: str = ALGORITHM, backend: str = BACKEND) -> str:
    return f"""schema_version = {SEARCH_CONFIGURATION_SCHEMA}

[search]
algorithm_id = "{algorithm}"
backend_id = "{backend}"
"""


def _expect_error(message: str, action: Callable[[], object]) -> None:
    try:
        _ = action()
    except SearchConfigurationError as error:
        if message not in str(error):
            raise AssertionError from error
        return
    raise AssertionError


def test_versioned_configuration_parses_independent_dimensions() -> None:
    """Algorithm and backend identities remain independent in durable config."""
    config = parse_search_configuration(_config(), source=SEARCH_CONFIG_SOURCE)

    assert config.selection.algorithm_id == ALGORITHM
    assert config.selection.backend_id == BACKEND
    assert config.source == SEARCH_CONFIG_SOURCE


def test_explicit_overrides_change_selection_without_mutating_base() -> None:
    """Overrides preserve the immutable loaded base configuration."""
    config = parse_search_configuration(_config(), source=SEARCH_CONFIG_SOURCE)

    effective = config.resolved(backend_override=GPU_BACKEND)

    assert effective.algorithm_id == ALGORITHM
    assert effective.backend_id == GPU_BACKEND
    assert config.selection.backend_id == BACKEND


def test_algorithm_and_backend_can_both_be_overridden() -> None:
    """Independent overrides can select another strategy/backend pair."""
    config = parse_search_configuration(_config())

    effective = config.resolved(
        algorithm_override=OTHER_ALGORITHM,
        backend_override=GPU_BACKEND,
    )

    assert effective.algorithm_id == OTHER_ALGORITHM
    assert effective.backend_id == GPU_BACKEND


def test_empty_override_fails_closed() -> None:
    """An explicit empty override never silently falls back to base config."""
    config = parse_search_configuration(_config())

    _expect_error(
        "search backend override must not be empty",
        lambda: config.resolved(backend_override=""),
    )


def test_unknown_schema_and_keys_fail_closed() -> None:
    """Configuration evolution is versioned and rejects accidental knobs."""
    _expect_error(
        "unsupported search configuration schema",
        lambda: parse_search_configuration(
            _config().replace(" = 1", " = 2", 1)
        ),
    )
    _expect_error(
        "contains unknown keys",
        lambda: parse_search_configuration(_config() + "mystery = true\n"),
    )


def test_missing_or_empty_selection_fields_fail_closed() -> None:
    """Both independent selection identities are mandatory and nonempty."""
    missing = _config().replace(f'backend_id = "{BACKEND}"\n', "")
    empty = _config(algorithm="")

    _expect_error(
        "backend_id must be a non-empty string",
        lambda: parse_search_configuration(missing),
    )
    _expect_error(
        "algorithm_id must be a non-empty string",
        lambda: parse_search_configuration(empty),
    )


def test_configuration_load_preserves_path_identity(tmp_path: Path) -> None:
    """File loading preserves exact config source identity for evidence."""
    path = tmp_path / "search.toml"
    _ = path.write_text(_config(), encoding="utf-8")

    config = load_search_configuration(path)

    assert config.source == path.as_posix()
    assert config.selection.backend_id == BACKEND


def test_runtime_configuration_strings_require_exact_type() -> None:
    """Direct parser and override APIs reject truthy foreign strings."""
    config = parse_search_configuration(_config())
    foreign_override = True

    _expect_error(
        "search backend override must use the exact string type",
        lambda: config.resolved(
            backend_override=cast("str", cast("object", foreign_override)),
        ),
    )
    _expect_error(
        "search configuration source must use the exact string type",
        lambda: parse_search_configuration(
            _config(),
            source=cast("str", cast("object", 1)),
        ),
    )


def test_direct_configuration_requires_exact_admitted_members() -> None:
    """Direct construction cannot bypass parser selection/source admission."""
    foreign_source: object = 1
    foreign_selection: object = object()
    foreign_algorithm: object = bool(1)

    _expect_error(
        "search configuration source must use the exact string type",
        lambda: SearchConfiguration(
            selection=SearchSelection(ALGORITHM, BACKEND),
            source=cast("str", cast("object", foreign_source)),
        ).resolved(),
    )
    _expect_error(
        "search configuration selection has wrong type",
        lambda: SearchConfiguration(
            selection=cast(
                "SearchSelection",
                foreign_selection,
            ),
            source=SEARCH_CONFIG_SOURCE,
        ).resolved(),
    )
    _expect_error(
        "search algorithm ID must use the exact string type",
        lambda: SearchConfiguration(
            selection=SearchSelection(
                cast("str", cast("object", foreign_algorithm)),
                BACKEND,
            ),
            source=SEARCH_CONFIG_SOURCE,
        ).validated(),
    )


def test_search_config_rejects_oversized_toml(tmp_path: Path) -> None:
    """Explicit search TOML remains bounded before decoding and parsing."""
    path = tmp_path / "huge.toml"
    with path.open("wb") as stream:
        _ = stream.truncate(1024 * 1024 + 1)
    with pytest.raises(SearchConfigurationError, match="byte limit"):
        _ = load_search_configuration(path)


def test_search_config_invalid_utf8_has_typed_error(tmp_path: Path) -> None:
    """Untrusted configuration encoding failures cannot leak raw decoding."""
    path = tmp_path / "invalid.toml"
    _ = path.write_bytes(b"\xff")
    with pytest.raises(SearchConfigurationError, match="UTF-8"):
        _ = load_search_configuration(path)


def test_search_config_rejects_directory_and_fifo(tmp_path: Path) -> None:
    """A regular source contract keeps directory/FIFO input nonblocking."""
    path = tmp_path / "search.toml"
    path.mkdir()
    with pytest.raises(SearchConfigurationError, match="regular"):
        _ = load_search_configuration(path)
    path.rmdir()
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO creation unsupported")
    mkfifo(path)
    with pytest.raises(SearchConfigurationError, match="regular"):
        _ = load_search_configuration(path)


def test_search_config_explicit_symlink_preserves_alias_identity(
    tmp_path: Path,
) -> None:
    """Caller-selected source aliases remain supported and clearly named."""
    source = tmp_path / "physical.toml"
    _ = source.write_text(_config(), encoding="utf-8")
    alias = tmp_path / "selected.toml"
    try:
        _ = alias.symlink_to(source)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unsupported: {error}")
    config = load_search_configuration(alias)
    assert config.source == alias.as_posix()
    assert config.selection.algorithm_id == ALGORITHM


def test_search_config_rejects_replaced_inode_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-byte replacement after stat invalidates configuration source."""
    source = tmp_path / "search.toml"
    _ = source.write_text(_config(), encoding="utf-8")
    replacement = tmp_path / "replacement.toml"
    _ = replacement.write_bytes(source.read_bytes())
    real_open = os.open
    swapped = False

    def swap_at_open(path: Path, flags: int) -> int:
        nonlocal swapped
        if path == source:
            _ = replacement.replace(source)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_at_open)
    with pytest.raises(SearchConfigurationError, match="changed before read"):
        _ = load_search_configuration(source)
    assert swapped


def test_search_config_rejects_same_byte_inode_swap_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """File replacement after source reading never authorizes TOML identity."""
    source = tmp_path / "search.toml"
    _ = source.write_text(_config(), encoding="utf-8")
    replacement = tmp_path / "replacement.toml"
    _ = replacement.write_bytes(source.read_bytes())
    real_stat = Path.stat
    seen = 0

    def swap_on_recheck(
        path: Path,
        *,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal seen
        if path == source:
            seen += 1
            if seen == SOURCE_RECHECK:
                _ = replacement.replace(source)
        return real_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", swap_on_recheck)
    with pytest.raises(SearchConfigurationError, match="changed during read"):
        _ = load_search_configuration(source)
    assert seen == SOURCE_RECHECK


def test_search_config_rejects_in_place_change_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equal-size edits to an opened TOML source cannot pass unchanged."""
    source = tmp_path / "search.toml"
    _ = source.write_text(_config(), encoding="utf-8")
    real_stat = Path.stat
    seen = 0

    def edit_on_recheck(
        path: Path,
        *,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal seen
        if path == source:
            seen += 1
            if seen == SOURCE_RECHECK:
                with source.open("r+b") as stream:
                    _ = stream.write(b"x")
        return real_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", edit_on_recheck)
    with pytest.raises(SearchConfigurationError, match="changed during read"):
        _ = load_search_configuration(source)
    assert seen == SOURCE_RECHECK


def test_search_config_missing_file_is_typed_error(tmp_path: Path) -> None:
    """Absent caller-configured TOML produces a stable typed failure."""
    with pytest.raises(SearchConfigurationError, match="cannot read"):
        _ = load_search_configuration(tmp_path / "missing.toml")


@pytest.mark.parametrize(
    "opened",
    [False, True, -1, "5", 2**80, type("ForeignFd", (int,), {})(7)],
    ids=["false", "true", "negative", "text", "overlarge", "subclass"],
)
def test_search_config_rejects_non_native_open_receipt_before_fdopen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    opened: object,
) -> None:
    """A forged config descriptor never aliases an unrelated process stream."""
    path = tmp_path / SEARCH_CONFIG_SOURCE
    _ = path.write_text(_config(), encoding="utf-8")
    reached = False

    def fake_open(selected: Path, flags: int) -> int:
        del flags
        nonlocal reached
        assert selected == path
        reached = True
        return cast("int", opened)

    def forbidden_fdopen(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise AssertionError("foreign configuration descriptor reached fdopen")

    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "fdopen", forbidden_fdopen)
    with pytest.raises(SearchConfigurationError, match="descriptor"):
        _ = load_search_configuration(path)
    assert reached


def test_search_config_releases_fd_on_stream_transfer_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed TOML stream ownership transfer must not leave an open FD."""
    path = tmp_path / SEARCH_CONFIG_SOURCE
    _ = path.write_text(_config(), encoding="utf-8")
    real_open = os.open
    descriptor: int | None = None

    def fake_open(selected: Path, flags: int) -> int:
        nonlocal descriptor
        result = real_open(selected, flags)
        assert selected == path
        descriptor = result
        return result

    def failing_fdopen(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise ValueError("synthetic config stream failure")

    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "fdopen", failing_fdopen)
    try:
        with pytest.raises(SearchConfigurationError, match="stream"):
            _ = load_search_configuration(path)
        assert descriptor is not None
        with pytest.raises(OSError):
            _ = os.fstat(descriptor)
    finally:
        if descriptor is not None:
            with contextlib.suppress(OSError):
                os.close(descriptor)


@pytest.mark.parametrize("probe", ["preflight", "opened"])
def test_search_config_rejects_foreign_metadata_before_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
) -> None:
    """Non-native stat receipts cannot supply TOML configuration identity."""
    path = tmp_path / SEARCH_CONFIG_SOURCE
    _ = path.write_text(_config(), encoding="utf-8")
    real_stat = Path.stat
    real_open = os.open
    real_fstat = os.fstat
    opened_fd: int | None = None
    reached = False

    class ForeignStat:
        @override
        def __getattribute__(self, name: str) -> object:
            del name
            raise AssertionError("foreign stat fields accessed")

    def fake_stat(selected: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        nonlocal reached
        if selected == path and probe == "preflight":
            reached = True
            return cast("os.stat_result", cast("object", ForeignStat()))
        return real_stat(selected, follow_symlinks=follow_symlinks)

    def fake_open(selected: Path, flags: int) -> int:
        nonlocal opened_fd
        result = real_open(selected, flags)
        if selected == path:
            opened_fd = result
        return result

    def fake_fstat(descriptor: int) -> os.stat_result:
        nonlocal reached
        if descriptor == opened_fd and probe == "opened":
            reached = True
            return cast("os.stat_result", cast("object", ForeignStat()))
        return real_fstat(descriptor)

    monkeypatch.setattr(Path, "stat", fake_stat)
    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "fstat", fake_fstat)
    with pytest.raises(SearchConfigurationError, match="metadata"):
        _ = load_search_configuration(path)
    assert reached


@pytest.mark.parametrize("cleanup_type", [OSError, ValueError, IndexError, OverflowError])
def test_search_config_stream_failure_preserves_primary_over_close_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_type: type[Exception],
) -> None:
    """A secondary failed close never becomes the primary config rejection."""
    path = tmp_path / SEARCH_CONFIG_SOURCE
    _ = path.write_text(_config(), encoding="utf-8")
    real_open = os.open
    real_close = os.close
    descriptor: int | None = None

    def fake_open(selected: Path, flags: int) -> int:
        nonlocal descriptor
        descriptor = real_open(selected, flags)
        return descriptor

    def failed_fdopen(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise ValueError("primary stream constructor fault")

    def failed_close(target: int) -> None:
        if target == descriptor:
            raise cleanup_type("secondary close fault")
        real_close(target)

    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "fdopen", failed_fdopen)
    monkeypatch.setattr(os, "close", failed_close)
    try:
        with pytest.raises(SearchConfigurationError, match="stream transfer") as caught:
            _ = load_search_configuration(path)
        source = caught.value.__cause__
        assert type(source) is ValueError
        assert "primary stream constructor fault" in str(source)
        assert any(
            cleanup_type.__name__ in note for note in getattr(source, "__notes__", ())
        )
    finally:
        if descriptor is not None:
            with contextlib.suppress(OSError):
                real_close(descriptor)


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt, SystemExit])
def test_search_config_stream_interruption_closes_descriptor_before_reraising(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupt: type[BaseException],
) -> None:
    """Process-control signals retain their identity while closing raw FDs."""
    path = tmp_path / SEARCH_CONFIG_SOURCE
    _ = path.write_text(_config(), encoding="utf-8")
    real_open = os.open
    descriptor: int | None = None

    def fake_open(selected: Path, flags: int) -> int:
        nonlocal descriptor
        descriptor = real_open(selected, flags)
        return descriptor

    def interrupted_fdopen(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise interrupt("synthetic interrupted stream transfer")

    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "fdopen", interrupted_fdopen)
    try:
        with pytest.raises(interrupt):
            _ = load_search_configuration(path)
        assert descriptor is not None
        with pytest.raises(OSError):
            _ = os.fstat(descriptor)
    finally:
        if descriptor is not None:
            with contextlib.suppress(OSError):
                os.close(descriptor)


@pytest.mark.parametrize(
    "foreign_text",
    [b"schema_version = 1", True, 7, type("ForeignText", (str,), {})("schema_version = 1")],
    ids=["bytes", "boolean", "integer", "string-subclass"],
)
def test_search_configuration_rejects_foreign_toml_text_before_parser(
    foreign_text: object,
) -> None:
    """Direct TOML entry must not invoke foreign values or subclass hooks."""
    with pytest.raises(SearchConfigurationError, match="text.*exact string"):
        _ = parse_search_configuration(cast("str", foreign_text))


@pytest.mark.parametrize("source_kind", ["direct", "file"])
def test_search_configuration_rejects_deep_toml_parser_stack_exhaustion(
    tmp_path: Path,
    source_kind: str,
) -> None:
    """Deeply nested untrusted TOML must fail with a typed configuration error."""
    deep = _config() + "nested = " + "[" * 512 + "0" + "]" * 512 + "\n"
    if source_kind == "direct":
        with pytest.raises(SearchConfigurationError, match="recursion"):
            _ = parse_search_configuration(deep)
    else:
        path = tmp_path / SEARCH_CONFIG_SOURCE
        _ = path.write_text(deep, encoding="utf-8")
        with pytest.raises(SearchConfigurationError, match="recursion"):
            _ = load_search_configuration(path)


@pytest.mark.parametrize("foreign_path", [None, "search.toml", b"search.toml", True])
def test_search_configuration_load_rejects_foreign_path_before_file_calls(
    foreign_path: object,
) -> None:
    """Direct library loads require an exact native filesystem path object."""
    with pytest.raises(SearchConfigurationError, match="native path"):
        _ = load_search_configuration(cast("Path", foreign_path))


@pytest.mark.parametrize("bad_name", ["bad\0name.toml", "bad\ud800name.toml"])
def test_search_configuration_load_rejects_unencodable_pathnames(
    tmp_path: Path,
    bad_name: str,
) -> None:
    """Malformed path spellings fail typed before performing filesystem reads."""
    with pytest.raises(SearchConfigurationError, match="path"):
        _ = load_search_configuration(tmp_path / bad_name)


def test_search_configuration_load_preserves_surrogateescape_byte_path(
    tmp_path: Path,
) -> None:
    """Valid POSIX byte-path aliases remain accepted during path admission."""
    if os.name != "posix":
        pytest.skip("POSIX byte pathname semantics required")
    raw_name = os.fsdecode(b"search-\xff.toml")
    path = tmp_path / raw_name
    _ = path.write_text(_config(), encoding="utf-8")
    parsed = load_search_configuration(path)
    assert parsed.source == path.as_posix()
    assert parsed.selection.backend_id == BACKEND


@pytest.mark.parametrize("phase", ["stat", "open"])
def test_search_config_wraps_hostile_os_errors_without_string_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    """Foreign OSError subclasses cannot escape through diagnostic formatting."""
    source = tmp_path / SEARCH_CONFIG_SOURCE
    _ = source.write_text(_config(), encoding="utf-8")
    real_stat = Path.stat
    real_open = os.open
    raised = False

    class HostileOsError(OSError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign OSError __str__ called")

    def failing_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        nonlocal raised
        if path == source and phase == "stat":
            raised = True
            raise HostileOsError("synthetic hostile source")
        return real_stat(path, follow_symlinks=follow_symlinks)

    def failing_open(path: Path, flags: int) -> int:
        nonlocal raised
        if path == source and phase == "open":
            raised = True
            raise HostileOsError("synthetic hostile source")
        return real_open(path, flags)

    monkeypatch.setattr(Path, "stat", failing_stat)
    monkeypatch.setattr(os, "open", failing_open)
    with pytest.raises(SearchConfigurationError, match="HostileOsError") as caught:
        _ = load_search_configuration(source)
    assert raised
    assert type(caught.value.__cause__) is HostileOsError


@pytest.mark.parametrize("reported", [None, True, 7, bytearray(b"data")])
def test_search_config_rejects_non_native_binary_read_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reported: object,
) -> None:
    """A foreign stream must not supply a successful TOML read receipt."""
    source = tmp_path / SEARCH_CONFIG_SOURCE
    _ = source.write_text(_config(), encoding="utf-8")
    real_fdopen = os.fdopen
    intercepted = False

    class ForgedStream:
        def __init__(self, inner: object) -> None:
            self.inner: object = inner

        def __enter__(self) -> ForgedStream:
            return self

        def __exit__(self, exc_type: object, exc_value: object, trace: object) -> None:
            del exc_type, exc_value, trace
            cast("BinaryIO", self.inner).close()

        def fileno(self) -> int:
            return cast("BinaryIO", self.inner).fileno()

        def read(self, count: int) -> bytes:
            nonlocal intercepted
            del count
            intercepted = True
            return cast("bytes", reported)

    def fake_fdopen(descriptor: int, mode: str) -> ForgedStream:
        return ForgedStream(real_fdopen(descriptor, mode))

    monkeypatch.setattr(os, "fdopen", fake_fdopen)
    with pytest.raises(SearchConfigurationError, match="non-native bytes"):
        _ = load_search_configuration(source)
    assert intercepted
