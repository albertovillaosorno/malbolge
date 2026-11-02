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
#   - Regression tests for reproducible experiment manifest schema v1.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for reproducible experiment manifest schema v1."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Never, Self, TextIO, cast, final, override

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import BinaryIO

from scripts.validate import experiment_manifest as validator

EXPECTED_IDS = (
    "adaptive-accelerator-resource-budgeting",
    "compact-guest-bytecode-strategy",
    "malbolge-specific-optimization-mathematics",
    "pytorch-search-orchestration",
    "search-pruning-and-state-canonicalization",
    "self-modification-state-graph-optimizer",
    "stochastic-and-guided-search",
    "superoptimization-research-program",
    "template",
)
RESOURCE_EXHAUSTED = "resource-exhausted"
RUN_COMMIT = "a" * 40
RUN_HASH = "b" * 64
CURRENT_PROFILE_FINGERPRINT = (
    "malbolge-profile-v1:sha256:"
    "e33e1488162dffdc8bad9102df8eed3f8aac294d057b4f7ad7a389906963fc50"
)
MISMATCH_FINGERPRINT = "malbolge-profile-v1:sha256:" + ("0" * 64)
PROFILE_INDEPENDENT = "profile-independent"


def _run_manifest(**overrides: str) -> str:
    values = {
        "accelerator": "none",
        "commit": RUN_COMMIT,
        "host": "windows-x86_64-test",
        "outcome": "success",
        "raw_output": "algorithms/example/out/raw.json",
        "toolchain": "python-3.14.6",
        "workload_sha256": RUN_HASH,
    }
    values.update(overrides)
    return f"""schema_version = 1

[experiment]
id = "example"
record_kind = "run"
method_class = "benchmarking"
seed = 7

[challenge]
family = "fixture"
difficulty = 1
target_profile = "malbolge-2026.2"
target_profile_fingerprint = "{CURRENT_PROFILE_FINGERPRINT}"

[budget]
seconds = 1

[verification]
required = true
oracle = "trusted-fixture"

[provenance]
implementation = "algorithms/example/"
configuration = "algorithms/example/experiment.toml"
output = "algorithms/example/out/"

[run]
commit = "{values["commit"]}"
workload_sha256 = "{values["workload_sha256"]}"
host = "{values["host"]}"
accelerator = "{values["accelerator"]}"
toolchain = "{values["toolchain"]}"
outcome = "{values["outcome"]}"
raw_output = "{values["raw_output"]}"
"""


def _expect_failure(text: str, message: str) -> None:
    try:
        _ = validator.parse_manifest(text)
    except validator.ExperimentManifestError as error:
        if message not in str(error):
            mismatch = f"unexpected manifest error: {error}"
            raise AssertionError(mismatch) from error
        return
    failure = "invalid experiment manifest unexpectedly succeeded"
    raise AssertionError(failure)


def test_manifest_file_rejects_invalid_utf8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manifest file encoding failure remains a typed validation error."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    path = tmp_path / "experiment.toml"
    _ = path.write_bytes(bytes((0x5B, 0xFF, 0x5D)))
    with pytest.raises(
        validator.ExperimentManifestError,
        match="invalid experiment manifest UTF-8",
    ):
        _ = validator.validate_repository_manifest(path)


def test_repository_experiment_manifests_are_schema_valid() -> None:
    """Every mirrored algorithm carries one valid version-one plan manifest."""
    manifests = validator.validate_repository()
    assert tuple(item.identifier for item in manifests) == EXPECTED_IDS


def test_repo_relative_manifest_path_admits_canonical_identity() -> None:
    """Relative and absolute spellings share one in-repository identity."""
    absolute = (
        validator.ROOT
        / "src/research/algorithms/domain/algorithms/template/experiment.toml"
    )
    relative = absolute.relative_to(validator.ROOT)
    assert validator.validate_repository_manifest(relative) == (
        validator.validate_repository_manifest(absolute)
    )


def _repository_manifest_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Clone one canonical template under a detached repository-shaped root.

    Returns:
        A physical and schema-valid experiment manifest path.

    """
    relative = Path(
        "src/research/algorithms/domain/algorithms/template/experiment.toml"
    )
    original = validator.ROOT / relative
    fixture = tmp_path / relative
    fixture.parent.mkdir(parents=True)
    _ = fixture.write_bytes(original.read_bytes())
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    return fixture


def test_repository_manifest_rejects_unregistered_directory_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A matching basename and rewritten provenance cannot mint research ID."""
    canonical = _repository_manifest_fixture(tmp_path, monkeypatch)
    foreign = tmp_path / "scratch/template/experiment.toml"
    foreign.parent.mkdir(parents=True)
    body = canonical.read_text().replace(
        "src/research/algorithms/domain/algorithms/template/experiment.toml",
        "scratch/template/experiment.toml",
    )
    _ = foreign.write_text(body)
    with pytest.raises(
        validator.ExperimentManifestError, match="registered research algorithm"
    ):
        _ = validator.validate_repository_manifest(foreign)


def test_repository_manifest_rejects_noncanonical_filename_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An alternate TOML file cannot impersonate the canonical experiment."""
    canonical = _repository_manifest_fixture(tmp_path, monkeypatch)
    foreign = canonical.with_name("other.toml")
    body = canonical.read_text().replace(
        "src/research/algorithms/domain/algorithms/template/experiment.toml",
        "src/research/algorithms/domain/algorithms/template/other.toml",
    )
    _ = foreign.write_text(body)
    with pytest.raises(
        validator.ExperimentManifestError, match="canonical experiment.toml"
    ):
        _ = validator.validate_repository_manifest(foreign)


def test_repository_manifest_rejects_symlink_leaf_and_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid schema and provenance cannot authorize a linked manifest path."""
    source = _repository_manifest_fixture(tmp_path, monkeypatch)
    alias = source.with_name("linked.toml")
    linked_dir = tmp_path / "linked-directory"
    try:
        alias.symlink_to(source)
        linked_dir.symlink_to(source.parent, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unsupported: {error}")
    for redirected in (alias, linked_dir / source.name):
        with pytest.raises(
            validator.ExperimentManifestError, match=r"redirect|regular"
        ):
            _ = validator.validate_repository_manifest(redirected)


def test_repository_manifest_rejects_external_alias_to_valid_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An outside symlink cannot be canonicalized into repository authority."""
    source = _repository_manifest_fixture(tmp_path, monkeypatch)
    external = tmp_path.parent / f"{tmp_path.name}-external-link.toml"
    try:
        external.symlink_to(source)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unsupported: {error}")
    try:
        with pytest.raises(
            validator.ExperimentManifestError, match="escapes repository"
        ):
            _ = validator.validate_repository_manifest(external)
    finally:
        external.unlink(missing_ok=True)


def test_repository_manifest_rejects_parent_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parent segments are not accepted as evidence path canonicalization."""
    source = _repository_manifest_fixture(tmp_path, monkeypatch)
    alternate = source.parent / ".." / source.parent.name / source.name
    with pytest.raises(
        validator.ExperimentManifestError, match="must not traverse parents"
    ):
        _ = validator.validate_repository_manifest(alternate)


def test_manifest_reader_rejects_nonregular_missing_and_oversized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bounded regular admission rejects a directory, missing source or size."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    with pytest.raises(validator.ExperimentManifestError, match="not found"):
        _ = validator.validate_repository_manifest(tmp_path)
    with pytest.raises(validator.ExperimentManifestError, match="not found"):
        _ = validator.validate_repository_manifest(tmp_path / "missing.toml")
    oversized = tmp_path / "oversized.toml"
    with oversized.open("wb") as stream:
        _ = stream.truncate(validator.MAX_MANIFEST_BYTES + 1)
    with pytest.raises(validator.ExperimentManifestError, match="byte limit"):
        _ = validator.validate_repository_manifest(oversized)


def test_repository_manifest_refuses_fifo_without_blocking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repository admission excludes a writerless FIFO before opening it."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    mkfifo = cast("Callable[[Path], None] | None", getattr(os, "mkfifo", None))
    if mkfifo is None:
        pytest.skip("FIFO not supported on this platform")
    fifo = tmp_path / "source.fifo"
    mkfifo(fifo)
    with pytest.raises(validator.ExperimentManifestError, match="not found"):
        _ = validator.validate_repository_manifest(fifo)


def test_manifest_reader_rejects_same_byte_swap_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing a regular file before descriptor opening invalidates it."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    replacement = tmp_path / "replacement.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    _ = replacement.write_bytes(source.read_bytes())
    real_open = os.open
    swapped = False

    def swap_on_open(path: Path, flags: int) -> int:
        nonlocal swapped
        if path == source:
            _ = replacement.replace(source)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_on_open)
    with pytest.raises(validator.ExperimentManifestError, match="changed before read"):
        _ = validator.validate_repository_manifest(source)
    assert swapped


def test_manifest_reader_rejects_same_byte_swap_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An identically formatted replacement does not validate stale bytes."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    replacement = tmp_path / "replacement.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    _ = replacement.write_bytes(source.read_bytes())
    real_open = os.open
    real_lstat = Path.lstat
    opened = swapped = False

    def track_open(path: Path, flags: int) -> int:
        nonlocal opened
        descriptor = real_open(path, flags)
        if path == source:
            opened = True
        return descriptor

    def swap_at_recheck(path: Path) -> os.stat_result:
        nonlocal swapped
        if path == source and opened and not swapped:
            _ = replacement.replace(source)
            swapped = True
        return real_lstat(path)

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(Path, "lstat", swap_at_recheck)
    with pytest.raises(validator.ExperimentManifestError, match="changed during read"):
        _ = validator.validate_repository_manifest(source)
    assert swapped


def test_manifest_reader_rejects_in_place_change_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same-inode rewrite after byte collection invalidates source evidence."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    real_open = os.open
    real_lstat = Path.lstat
    opened = modified = False

    def track_open(path: Path, flags: int) -> int:
        nonlocal opened
        descriptor = real_open(path, flags)
        if path == source:
            opened = True
        return descriptor

    def modify_at_recheck(path: Path) -> os.stat_result:
        nonlocal modified
        if path == source and opened and not modified:
            with source.open("r+b") as stream:
                _ = stream.write(b"x")
            os.utime(source, ns=(0, 0))
            modified = True
        return real_lstat(path)

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(Path, "lstat", modify_at_recheck)
    with pytest.raises(validator.ExperimentManifestError, match="changed during read"):
        _ = validator.validate_repository_manifest(source)
    assert modified


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_repository_manifest_inspection_failures_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Malformed host filesystem failures cannot escape public admission."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    real_is_file = Path.is_file

    def fault_is_file(path: Path) -> bool:
        if path == source:
            raise fault_type("injected is_file fault")
        return real_is_file(path)

    monkeypatch.setattr(Path, "is_file", fault_is_file)
    with pytest.raises(
        validator.ExperimentManifestError,
        match="experiment manifest cannot be inspected",
    ):
        _ = validator.validate_repository_manifest(source)


@pytest.mark.parametrize("receipt", (None, 0, 1, "yes", object()))
def test_repository_manifest_requires_native_file_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """A foreign file-inspection result must not authorize source admission."""
    source = _repository_manifest_fixture(tmp_path, monkeypatch)
    original = Path.is_file

    class ForeignVerdict:
        def __bool__(self) -> Never:
            raise AssertionError("foreign file-inspection truthiness executed")

    verdict = ForeignVerdict() if type(receipt) is object else receipt

    def forged_is_file(path: Path) -> bool:
        return cast("bool", verdict) if path == source else original(path)

    monkeypatch.setattr(Path, "is_file", forged_is_file)
    with pytest.raises(validator.ExperimentManifestError, match="native file receipt"):
        _ = validator.validate_repository_manifest(source)


@final
class _ForeignDescriptor(int):
    """An int subtype cannot claim native ownership of a file descriptor."""

    @override
    def __str__(self) -> str:
        raise AssertionError("foreign manifest descriptor formatted")


@pytest.fixture
def borrowed_manifest_streams() -> Iterator[list[BinaryIO]]:
    """Close duplicated file handles owned by adversarial test wrappers."""
    handles: list[BinaryIO] = []
    yield handles
    for handle in reversed(handles):
        handle.close()


def test_manifest_rejects_same_length_forged_toml_from_stream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_manifest_streams: list[BinaryIO],
) -> None:
    """File metadata cannot authorize bytes fabricated by an fdopen wrapper."""
    source = tmp_path / "experiment.toml"
    expected = b"schema_version = 1\n"
    _ = source.write_bytes(b"!" * len(expected))
    native_fdopen = os.fdopen

    @final
    class ForgedStream:
        def __init__(self, descriptor: int, mode: str) -> None:
            self.descriptor = descriptor
            self.wrapped = cast("BinaryIO", native_fdopen(os.dup(descriptor), mode))
            borrowed_manifest_streams.append(self.wrapped)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def fileno(self) -> int:
            return self.descriptor

        def read(self, _size: int) -> bytes:
            return expected

    monkeypatch.setattr(os, "fdopen", ForgedStream)
    with pytest.raises(validator.ExperimentManifestError, match="native stream"):
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]


def test_manifest_rejects_native_reader_of_other_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_manifest_streams: list[BinaryIO],
) -> None:
    """A native reader on a duplicate fd cannot replace the opened handle."""
    source = tmp_path / "experiment.toml"
    _ = source.write_bytes(b"schema_version = 1\n")
    native_fdopen = os.fdopen
    native_fstat = os.fstat
    opened: list[int] = []

    def substituted_fdopen(descriptor: int, mode: str) -> BinaryIO:
        opened.append(descriptor)
        stream = cast("BinaryIO", native_fdopen(os.dup(descriptor), mode))
        borrowed_manifest_streams.append(stream)
        return stream

    monkeypatch.setattr(os, "fdopen", substituted_fdopen)
    with pytest.raises(validator.ExperimentManifestError, match="native stream"):
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = native_fstat(opened[0])


@pytest.mark.parametrize(
    "receipt",
    [
        pytest.param(True, id="boolean"),
        pytest.param(-1, id="negative"),
        pytest.param(1 << 40, id="oversized"),
        pytest.param(3.0, id="float"),
        pytest.param("3", id="text"),
        pytest.param(_ForeignDescriptor(3), id="foreign-integer"),
    ],
)
def test_manifest_open_requires_native_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Invalid open receipts must not reach fdopen or descriptor cleanup."""
    source = tmp_path / "experiment.toml"
    _ = source.write_bytes(b"schema_version = 1\n")
    real_open = os.open

    def forged_open(path: Path, flags: int) -> int:
        if path == source:
            return cast("int", receipt)
        return real_open(path, flags)

    def forbidden_fdopen(_descriptor: int, _mode: str) -> Never:
        raise AssertionError("forged manifest descriptor passed to fdopen")

    def forbidden_close(_descriptor: int) -> Never:
        raise AssertionError("forged manifest descriptor passed to close")

    monkeypatch.setattr(os, "open", forged_open)
    monkeypatch.setattr(os, "fdopen", forbidden_fdopen)
    monkeypatch.setattr(os, "close", forbidden_close)
    with pytest.raises(validator.ExperimentManifestError, match="native descriptor"):
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "receipt",
    [
        pytest.param(True, id="boolean"),
        pytest.param(-1, id="negative"),
        pytest.param(1 << 40, id="oversized"),
        pytest.param(1, id="unrelated-native"),
        pytest.param("3", id="text"),
        pytest.param(_ForeignDescriptor(3), id="foreign-integer"),
    ],
)
def test_manifest_stream_requires_bound_native_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_manifest_streams: list[BinaryIO],
    receipt: object,
) -> None:
    """A forged stream fileno cannot authorize fstat or manifest reads."""
    source = tmp_path / "experiment.toml"
    _ = source.write_bytes(b"schema_version = 1\n")
    real_fdopen = os.fdopen
    real_fstat = os.fstat
    opened: list[int] = []

    @final
    class ForgedStream:
        def __init__(self, descriptor: int, mode: str) -> None:
            self.stream: BinaryIO = cast(
                "BinaryIO", real_fdopen(os.dup(descriptor), mode)
            )
            borrowed_manifest_streams.append(self.stream)
            opened.append(descriptor)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> object:
            return receipt

        def read(self, length: int) -> bytes:
            return self.stream.read(length)

    def guarded_fstat(descriptor: int) -> os.stat_result:
        if not opened or type(descriptor) is not int or descriptor != opened[0]:
            raise AssertionError("forged manifest stream descriptor reached fstat")
        return real_fstat(descriptor)

    monkeypatch.setattr(os, "fdopen", ForgedStream)
    monkeypatch.setattr(os, "fstat", guarded_fstat)
    with pytest.raises(validator.ExperimentManifestError, match="native stream"):
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = real_fstat(opened[0])


def test_manifest_rejects_switching_stream_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_manifest_streams: list[BinaryIO],
) -> None:
    """A switchable foreign wrapper cannot reach its descriptor hooks."""
    source = tmp_path / "experiment.toml"
    _ = source.write_bytes(b"schema_version = 1\n")
    real_fdopen = os.fdopen
    real_fstat = os.fstat
    calls: list[int] = []
    opened: list[int] = []

    @final
    class SwitchingStream:
        def __init__(self, descriptor: int, mode: str) -> None:
            self.stream: BinaryIO = cast(
                "BinaryIO", real_fdopen(os.dup(descriptor), mode)
            )
            borrowed_manifest_streams.append(self.stream)
            opened.append(descriptor)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            calls.append(1)
            return opened[0] if len(calls) == 1 else -1

        def read(self, length: int) -> bytes:
            return self.stream.read(length)

    def guarded_fstat(descriptor: int) -> os.stat_result:
        if type(descriptor) is not int or descriptor != opened[0]:
            raise AssertionError("swapped manifest descriptor reached fstat")
        return real_fstat(descriptor)

    monkeypatch.setattr(os, "fdopen", SwitchingStream)
    monkeypatch.setattr(os, "fstat", guarded_fstat)
    with pytest.raises(validator.ExperimentManifestError, match="native stream"):
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]
    assert not calls


@pytest.mark.parametrize("receipt_kind", ("subclass", "text", "bytearray", "none"))
def test_manifest_rejects_foreign_read_implementation_before_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_manifest_streams: list[BinaryIO],
    receipt_kind: str,
) -> None:
    """A foreign read implementation cannot execute its byte receipt hooks."""
    source = tmp_path / "experiment.toml"
    _ = source.write_bytes(b"schema_version = 1\n")
    real_fdopen = os.fdopen

    @final
    class ForeignBytes(bytes):
        @override
        def __len__(self) -> int:
            raise AssertionError("foreign manifest length executed")

    @final
    class ForgedStream:
        def __init__(self, descriptor: int, mode: str) -> None:
            self.stream: BinaryIO = cast(
                "BinaryIO", real_fdopen(os.dup(descriptor), mode)
            )
            borrowed_manifest_streams.append(self.stream)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, length: int) -> bytes:
            raw = self.stream.read(length)
            receipts: dict[str, object] = {
                "subclass": ForeignBytes(raw),
                "text": raw.decode("utf-8"),
                "bytearray": bytearray(raw),
                "none": None,
            }
            return cast("bytes", receipts[receipt_kind])

    monkeypatch.setattr(os, "fdopen", ForgedStream)
    with pytest.raises(validator.ExperimentManifestError, match="native stream"):
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]


def test_manifest_invalid_utf8_preserves_native_decoder_cause(tmp_path: Path) -> None:
    """A malformed source retains the exact native decoder cause."""
    source = tmp_path / "experiment.toml"
    _ = source.write_bytes(b"{\xff}")
    with pytest.raises(
        validator.ExperimentManifestError, match="invalid experiment manifest UTF-8"
    ) as caught:
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]
    assert type(caught.value.__cause__) is UnicodeDecodeError
    assert "position 1" in str(caught.value)


@pytest.mark.parametrize("phase", ("initial", "opened", "after", "recheck"))
@pytest.mark.parametrize("receipt_kind", ("opaque", "hostile"))
def test_manifest_rejects_foreign_stat_receipts_before_field_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    receipt_kind: str,
) -> None:
    """Non-native stat receipts cannot forge stable manifest file identity."""
    source = tmp_path / "experiment.toml"
    _ = source.write_bytes(b"schema_version = 1\n")
    real_lstat = Path.lstat
    real_open = os.open
    real_fstat = os.fstat
    opened = False
    fstat_calls = 0

    @final
    class HostileStatus:
        def __getattribute__(self, _name: str) -> Never:
            raise AssertionError("foreign manifest stat field executed")

    receipt: object = HostileStatus() if receipt_kind == "hostile" else object()

    def tracked_open(path: Path, flags: int) -> int:
        nonlocal opened
        descriptor = real_open(path, flags)
        if path == source:
            opened = True
        return descriptor

    def forged_lstat(path: Path) -> os.stat_result:
        if path == source and (
            (phase == "initial" and not opened) or (phase == "recheck" and opened)
        ):
            return cast("os.stat_result", receipt)
        return real_lstat(path)

    def forged_fstat(descriptor: int) -> os.stat_result:
        nonlocal fstat_calls
        fstat_calls += 1
        if (phase == "opened" and fstat_calls == 1) or (
            phase == "after" and fstat_calls == 2
        ):
            return cast("os.stat_result", receipt)
        return real_fstat(descriptor)

    monkeypatch.setattr(os, "open", tracked_open)
    monkeypatch.setattr(Path, "lstat", forged_lstat)
    monkeypatch.setattr(os, "fstat", forged_fstat)
    with pytest.raises(validator.ExperimentManifestError, match="native stat receipt"):
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("phase", ("initial", "opened", "after", "recheck"))
@pytest.mark.parametrize(
    "field", ("mode", "inode", "device", "size", "mtime_ns", "ctime_ns")
)
def test_manifest_requires_native_stat_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    field: str,
) -> None:
    """Even native stat containers cannot authorize foreign identity fields."""
    source = tmp_path / "experiment.toml"
    _ = source.write_bytes(b"schema_version = 1\n")
    native = source.lstat()
    fields: list[object] = [
        *native,
        native.st_atime,
        native.st_mtime,
        native[9],
        native.st_atime_ns,
        native.st_mtime_ns,
        native.st_ctime_ns,
    ]
    target_index = {
        "mode": 0,
        "inode": 1,
        "device": 2,
        "size": 6,
        "mtime_ns": 14,
        "ctime_ns": 15,
    }[field]
    fields[target_index] = "foreign"
    forged = os.stat_result(cast("tuple[int, ...]", tuple(fields)))
    real_lstat = Path.lstat
    real_open = os.open
    real_fstat = os.fstat
    opened = False
    fstat_calls = 0

    def tracked_open(path: Path, flags: int) -> int:
        nonlocal opened
        descriptor = real_open(path, flags)
        if path == source:
            opened = True
        return descriptor

    def forged_lstat(path: Path) -> os.stat_result:
        if path == source and (
            (phase == "initial" and not opened) or (phase == "recheck" and opened)
        ):
            return forged
        return real_lstat(path)

    def forged_fstat(descriptor: int) -> os.stat_result:
        nonlocal fstat_calls
        fstat_calls += 1
        if (phase == "opened" and fstat_calls == 1) or (
            phase == "after" and fstat_calls == 2
        ):
            return forged
        return real_fstat(descriptor)

    monkeypatch.setattr(os, "open", tracked_open)
    monkeypatch.setattr(Path, "lstat", forged_lstat)
    monkeypatch.setattr(os, "fstat", forged_fstat)
    with pytest.raises(validator.ExperimentManifestError, match="native stat fields"):
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]


def test_manifest_rejects_negative_native_stat_size(tmp_path: Path) -> None:
    """A forged negative size cannot be treated as bounded regular evidence."""
    source = tmp_path / "experiment.toml"
    _ = source.write_bytes(b"schema_version = 1\n")
    native = source.lstat()
    fields = [
        *native,
        native.st_atime,
        native.st_mtime,
        native[9],
        native.st_atime_ns,
        native.st_mtime_ns,
        native.st_ctime_ns,
    ]
    fields[6] = -1
    forged = os.stat_result(tuple(fields))
    with pytest.raises(validator.ExperimentManifestError, match="native stat fields"):
        _ = validator._manifest_identity(forged)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
@pytest.mark.parametrize(
    "operation", ("lstat", "is_symlink", "is_junction", "open", "fstat", "fdopen")
)
def test_manifest_reader_host_failures_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """An untrusted host failure cannot bypass the manifest error boundary."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    if operation in {"lstat", "is_symlink", "is_junction"}:
        original = {
            "lstat": Path.lstat,
            "is_symlink": Path.is_symlink,
            "is_junction": Path.is_junction,
        }[operation]

        def fault_path(path: Path) -> os.stat_result | bool:
            if path == source:
                raise fault_type(f"injected {operation} fault")
            return original(path)

        monkeypatch.setattr(Path, operation, fault_path)
    elif operation == "open":
        original_open = os.open

        def fault_open(path: Path, flags: int) -> int:
            if path == source:
                raise fault_type("injected open fault")
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", fault_open)
    elif operation == "fstat":

        def fault_fstat(_descriptor: int) -> os.stat_result:
            raise fault_type("injected fstat fault")

        monkeypatch.setattr(os, "fstat", fault_fstat)
    else:

        def fault_fdopen(_descriptor: int, _mode: str) -> object:
            raise fault_type("injected fdopen fault")

        monkeypatch.setattr(os, "fdopen", fault_fdopen)
    with pytest.raises(
        validator.ExperimentManifestError,
        match="experiment manifest cannot be read",
    ):
        _ = validator.validate_repository_manifest(source)


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
def test_manifest_fdopen_failure_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A failed stream wrapper must not leak the private opened descriptor."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    source = tmp_path / "source.toml"
    _ = source.write_bytes(b"manifest = 1\n")
    real_open = os.open
    opened: list[int] = []

    def track_open(path: Path, flags: int) -> int:
        descriptor = real_open(path, flags)
        if path == source:
            opened.append(descriptor)
        return descriptor

    def fault_fdopen(_descriptor: int, _mode: str) -> object:
        raise fault_type("injected fdopen fault")

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(os, "fdopen", fault_fdopen)
    with pytest.raises(validator.ExperimentManifestError):
        _ = validator.validate_repository_manifest(source)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


def test_direct_experiment_toml_admits_only_bounded_exact_utf8() -> None:
    """Direct TOML entry points use the same bounded wire-text boundary."""

    class _ForgedText(str):  # ruff: ignore[subclass-builtin]
        """An in-memory string with caller-controlled inherited behavior."""

        __slots__ = ()

    source = _run_manifest()
    if not source.endswith("\n"):
        source += "\n"
    limit = validator.MAX_MANIFEST_BYTES
    exact = source + "#" + "x" * (limit - len(source) - 1)
    assert validator.parse_manifest(exact)
    with pytest.raises(validator.ExperimentManifestError, match="byte limit"):
        validator.parse_manifest(exact + "x")
    with pytest.raises(validator.ExperimentManifestError, match="byte limit"):
        validator.parse_manifest(source + "#" + "é" * (limit // 2))
    with pytest.raises(validator.ExperimentManifestError, match="UTF-8"):
        validator.parse_manifest(source + "#\ud800")
    with pytest.raises(validator.ExperimentManifestError, match="exact str"):
        validator.parse_manifest(_ForgedText(source))


def test_manifest_nested_array_parser_capacity_is_typed() -> None:
    """Deep but bounded TOML must not leak raw host RecursionError."""
    nested = "[" * 1000 + "1" + "]" * 1000
    text = _run_manifest() + "\nparser_probe = " + nested + "\n"
    _expect_failure(text, "invalid TOML exceeds host parser capacity")


def test_manifest_oversized_decimal_token_fails_typed() -> None:
    """Host parser digit limits cannot leak untyped ValueErrors."""
    limit = sys.get_int_max_str_digits()
    if limit == 0 or limit > 20_000:
        pytest.skip("host decimal digit limit unavailable")
    text = _run_manifest().replace("seconds = 1", "seconds = " + "9" * (limit + 1))
    _expect_failure(text, "invalid TOML exceeds host parser capacity")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("implementation", "algorithms/example/"),
        ("configuration", "algorithms/example/experiment.toml"),
        ("output", "algorithms/example/out/"),
        ("raw_output", "algorithms/example/out/raw.json"),
    ),
)
def test_manifest_paths_reject_toml_escaped_nul(field: str, value: str) -> None:
    """Escaped NUL path segments fail typed admission before consumers use them."""
    text = _run_manifest().replace(
        f'{field} = "{value}"', f'{field} = "algorithms/\\u0000invalid"'
    )
    _expect_failure(text, "must not contain NUL")


def test_manifest_rejects_windows_drive_relative_path() -> None:
    """Drive-relative Windows syntax cannot redirect retained run output."""
    _expect_failure(
        _run_manifest(raw_output="D:escape"),
        "must be repository-relative",
    )


@pytest.mark.parametrize(
    "reserved",
    (
        "algorithms/example/out/raw.json:metadata",
        "algorithms/example/out/NUL.txt",
        "algorithms/NUL/out/raw.json",
        "algorithms/example/out/results.",
        "algorithms/example/out/results ",
    ),
)
def test_manifest_rejects_windows_reserved_run_artifact_name(reserved: str) -> None:
    """NTFS streams and Windows-reserved components are not portable evidence."""
    _expect_failure(_run_manifest(raw_output=reserved), "Windows-reserved")


@pytest.mark.parametrize(
    ("field", "original", "portable_alias"),
    (
        (
            "implementation",
            "algorithms/example/",
            r"algorithms\example",
        ),
        (
            "configuration",
            "algorithms/example/experiment.toml",
            r"algorithms\example\experiment.toml",
        ),
        (
            "output",
            "algorithms/example/out/",
            r"algorithms\example\out",
        ),
        (
            "raw_output",
            "algorithms/example/out/raw.json",
            r"algorithms\example\out\raw.json",
        ),
    ),
)
def test_manifest_rejects_host_dependent_backslash_paths(
    field: str,
    original: str,
    portable_alias: str,
) -> None:
    """A Windows path alias cannot name a different Linux evidence file."""
    text = _run_manifest().replace(
        f'{field} = "{original}"',
        f"{field} = '{portable_alias}'",
    )
    _expect_failure(text, "must use forward slashes")


def test_recorded_run_requires_exact_commit_and_workload_hash() -> None:
    """Recorded evidence cannot omit exact source and workload identity."""
    _expect_failure(
        _run_manifest(commit="short"),
        "lowercase 40-hex Git commit",
    )
    _expect_failure(
        _run_manifest(workload_sha256="short"),
        "lowercase SHA-256 hex",
    )


def test_recorded_run_retains_negative_outcome_identity() -> None:
    """A non-success run remains a valid recorded experiment outcome."""
    manifest = validator.parse_manifest(_run_manifest(outcome=RESOURCE_EXHAUSTED))
    assert manifest.run is not None
    assert manifest.run.outcome == RESOURCE_EXHAUSTED


def test_recorded_run_rejects_unknown_outcome() -> None:
    """Unknown run outcomes fail closed."""
    _expect_failure(_run_manifest(outcome="lucky"), "unsupported run outcome")


def test_plan_requires_positive_stopping_bound() -> None:
    """A research plan without a positive budget is not reconstructible."""
    text = _run_manifest().replace("seconds = 1", "seconds = 0")
    _expect_failure(text, "positive integer stopping bound")


def test_verification_cannot_be_disabled_by_manifest() -> None:
    """Research configuration cannot make semantic verification optional."""
    text = _run_manifest().replace("required = true", "required = false")
    _expect_failure(text, "verification.required must be true")


def test_plan_cannot_smuggle_recorded_run_metadata() -> None:
    """A plan does not masquerade as already observed run evidence."""
    text = _run_manifest().replace('record_kind = "run"', 'record_kind = "plan"')
    _expect_failure(text, "plan experiment manifest must not contain a run table")


def test_canonical_target_profile_requires_fingerprint() -> None:
    """Canonical IDs cannot appear in manifests without immutable identity."""
    text = _run_manifest().replace(
        f'target_profile_fingerprint = "{CURRENT_PROFILE_FINGERPRINT}"\n',
        "",
    )
    _expect_failure(text, "target_profile_fingerprint is required")


def test_canonical_target_profile_mismatch_is_deterministic() -> None:
    """A stale artifact binding uses the shared profile mismatch diagnostic."""
    text = _run_manifest().replace(
        CURRENT_PROFILE_FINGERPRINT,
        MISMATCH_FINGERPRINT,
    )
    expected = " ".join(
        (
            "MALBOLGE-PROFILE-ID-001",
            "profile=malbolge-2026.2",
            f"expected={MISMATCH_FINGERPRINT}",
            f"observed={CURRENT_PROFILE_FINGERPRINT}",
        )
    )
    _expect_failure(text, expected)


def test_unknown_target_profile_never_falls_back() -> None:
    """Unknown artifact target identity cannot select a nearby profile."""
    text = _run_manifest().replace(
        'target_profile = "malbolge-2026.2"',
        'target_profile = "malbolge-current-ish"',
    )
    _expect_failure(text, "unsupported manifest challenge target profile")


def test_noncanonical_target_scope_forbids_profile_fingerprint() -> None:
    """Meta scopes cannot masquerade as canonical profile identities."""
    text = _run_manifest().replace(
        'target_profile = "malbolge-2026.2"',
        'target_profile = "profile-independent"',
    )
    _expect_failure(text, "must be absent for noncanonical target scope")


def test_profile_independent_scope_is_valid_without_fingerprint() -> None:
    """A declared profile-independent experiment remains explicitly unbound."""
    text = (
        _run_manifest()
        .replace(
            'target_profile = "malbolge-2026.2"',
            'target_profile = "profile-independent"',
        )
        .replace(
            f'target_profile_fingerprint = "{CURRENT_PROFILE_FINGERPRINT}"\n',
            "",
        )
    )

    manifest = validator.parse_manifest(text)

    assert manifest.target_profile == PROFILE_INDEPENDENT
    assert manifest.target_profile_fingerprint is None


@pytest.mark.parametrize(
    "tamper",
    ["syntax", "schema", "run-commit"],
)
def test_core_manifest_refuses_substituted_toml_provider_receipts(
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    """Native-shaped parser output cannot invent core source/run identity."""
    source = _run_manifest()
    native = validator.tomllib.loads(source)
    if tamper == "syntax":
        source = "this is not a TOML manifest"
    elif tamper == "schema":
        source = source.replace("schema_version = 1", "schema_version = 2")
    else:
        native["run"]["commit"] = "c" * 40
    with monkeypatch.context() as context:
        context.setattr(validator.tomllib, "loads", lambda _text: native)
        with pytest.raises(
            validator.ExperimentManifestError, match="TOML.*provider"
        ):
            validator.parse_manifest(source)
    assert validator.parse_manifest(_run_manifest()).run is not None


@pytest.mark.parametrize("tamper", ("syntax", "schema", "run-commit"))
def test_core_manifest_refuses_decoder_restoring_itself_mid_call(
    monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    """Manifest trust cannot depend on the decoder attribute after invocation."""
    source = _run_manifest()
    native_loads = validator.tomllib.loads
    fabricated = native_loads(source)
    if tamper == "syntax":
        source = "! invalid manifest TOML"
    elif tamper == "schema":
        source = source.replace("schema_version = 1", "schema_version = 2")
    else:
        fabricated["run"]["commit"] = "c" * 40

    def self_restoring(_text: str) -> object:
        monkeypatch.setattr(validator.tomllib, "loads", native_loads)
        return fabricated

    monkeypatch.setattr(validator.tomllib, "loads", self_restoring)
    with pytest.raises(validator.ExperimentManifestError, match="TOML decoder provider"):
        _ = validator._parse_document(source)


@pytest.mark.parametrize(
    "fault_type",
    [validator.tomllib.TOMLDecodeError, ValueError, TypeError, RuntimeError],
)
def test_direct_manifest_parser_never_formats_foreign_errors(
    monkeypatch: pytest.MonkeyPatch, fault_type: type[Exception]
) -> None:
    """TOML host faults remain typed without running exception __str__ hooks."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("untrusted parser exception formatter invoked")

    hostile = type("ForeignTOMLFault", (fault_type,), {"__str__": unsafe_str})
    fault = (
        hostile("malformed decoder state", "[invalid", 1)
        if fault_type is validator.tomllib.TOMLDecodeError
        else hostile("malformed decoder state")
    )

    def broken_loader(_text: str) -> None:
        raise fault

    monkeypatch.setattr(validator.tomllib, "loads", broken_loader)
    with pytest.raises(
        validator.ExperimentManifestError, match="invalid TOML"
    ) as caught:
        validator.parse_manifest(_run_manifest())
    assert caught.value.__cause__ is fault


def test_native_toml_syntax_error_retains_original_decoder_detail() -> None:
    """Ordinary malformed TOML remains useful for diagnosing file positions."""
    with pytest.raises(
        validator.ExperimentManifestError, match="invalid TOML"
    ) as caught:
        validator.parse_manifest("[bad\n")
    assert type(caught.value.__cause__) is validator.tomllib.TOMLDecodeError
    assert "line" in str(caught.value)


@pytest.mark.parametrize("nesting", ["root", "nested", "key"])
def test_toml_parser_cannot_return_foreign_mapping_or_key(
    monkeypatch: pytest.MonkeyPatch, nesting: str
) -> None:
    """Forged parser result containers never run mapping or key hooks."""

    class ForeignMap(dict[str, object]):
        def items(self):  # type: ignore[override]
            raise AssertionError("foreign TOML map iteration invoked")

    class ForeignKey(str):
        __hash__ = str.__hash__

        def __str__(self) -> str:
            raise AssertionError("foreign TOML key formatting invoked")

    native = validator.tomllib.loads(_run_manifest())
    if nesting == "root":
        forged: object = ForeignMap(native)
    elif nesting == "nested":
        forged = {**native, "experiment": ForeignMap(native["experiment"])}
    else:
        forged = {**native, ForeignKey("foreign"): 1}
    monkeypatch.setattr(validator.tomllib, "loads", lambda _text: forged)
    with pytest.raises(validator.ExperimentManifestError, match="manifest"):
        validator.parse_manifest(_run_manifest())


@pytest.mark.parametrize("operation", ["inspect", "read"])
@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_manifest_host_failures_do_not_format_foreign_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    fault_type: type[Exception],
) -> None:
    """Native typed manifest errors survive untrusted host fault formatters."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("untrusted filesystem exception formatter invoked")

    foreign_type = type("ForeignHostFault", (fault_type,), {"__str__": unsafe_str})
    source = _repository_manifest_fixture(tmp_path, monkeypatch)
    fault = foreign_type("unsafe host detail")
    if operation == "inspect":
        original_is_file = Path.is_file

        def fail_is_file(path: Path) -> bool:
            if path == source:
                raise fault
            return original_is_file(path)

        monkeypatch.setattr(Path, "is_file", fail_is_file)
    else:
        original_open = os.open

        def fail_open(path: Path, flags: int) -> int:
            if path == source:
                raise fault
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", fail_open)
    with pytest.raises(
        validator.ExperimentManifestError,
        match=f"experiment manifest cannot be {'inspected' if operation == 'inspect' else 'read'}",
    ) as caught:
        validator.validate_repository_manifest(source)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("fault_type", [validator.ExperimentManifestError, OSError])
def test_manifest_cli_never_formats_foreign_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """Validation errors cannot execute a caller-controlled __str__ hook."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign experiment CLI formatter executed")

    foreign = type("ForeignManifestCliFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe CLI detail")

    def fail_validate() -> None:
        raise fault

    monkeypatch.setattr(validator, "validate_repository", fail_validate)
    assert validator.main() == 1
    output = capsys.readouterr()
    assert not output.out
    assert "ForeignManifestCliFault" in output.err


def test_manifest_cli_native_error_retains_detail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exact system failures preserve a diagnostic in the operator report."""
    fault = PermissionError("manifest inspection permission denied")

    def fail_validate() -> None:
        raise fault

    monkeypatch.setattr(validator, "validate_repository", fail_validate)
    assert validator.main() == 1
    assert "manifest inspection permission denied" in capsys.readouterr().err


@pytest.mark.parametrize(
    "case", ("partial", "foreign-count", "write-fault", "flush-fault", "foreign-flush")
)
def test_manifest_cli_requires_delivered_success(
    monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """Validated manifests cannot certify success with an output failure."""

    class FakeOutput:
        def write(self, message: str) -> object:
            if case == "partial":
                return len(message) - 1
            if case == "foreign-count":
                return True
            if case == "write-fault":
                raise OSError("output unavailable")
            return len(message)

        def flush(self) -> object:
            if case == "flush-fault":
                raise OSError("flush unavailable")
            if case == "foreign-flush":
                return False
            return None

    monkeypatch.setattr(validator, "validate_repository", lambda: ("one",))
    monkeypatch.setattr(sys, "stdout", cast("TextIO", cast("object", FakeOutput())))
    assert validator.main() == 1


def test_manifest_cli_flushes_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """A normal summary succeeds after a complete native write and flush."""

    class CapturingOutput:
        messages: list[str]
        flushes: int

        def __init__(self) -> None:
            self.messages = []
            self.flushes = 0

        def write(self, message: str) -> int:
            self.messages.append(message)
            return len(message)

        def flush(self) -> None:
            self.flushes += 1

    output = CapturingOutput()
    monkeypatch.setattr(validator, "validate_repository", lambda: ("one",))
    monkeypatch.setattr(sys, "stdout", cast("TextIO", cast("object", output)))
    assert validator.main() == 0
    assert output.messages == ["experiment manifests valid: 1\n"]
    assert output.flushes == 1


def test_manifest_cli_failed_stderr_does_not_mask_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An invalid manifest remains a failure after diagnostic sink loss."""

    class FailingStderr:
        def write(self, _message: str) -> None:
            raise OSError("diagnostics unavailable")

    def reject_manifest() -> None:
        raise validator.ExperimentManifestError("invalid manifest")

    monkeypatch.setattr(validator, "validate_repository", reject_manifest)
    monkeypatch.setattr(sys, "stderr", cast("TextIO", cast("object", FailingStderr())))
    assert validator.main() == 1


def test_manifest_foreign_bytes_rejected_before_decode_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A supplied byte subclass cannot run custom text decoder callbacks."""

    class ForeignBytes(bytes):
        def decode(self, *_args: object, **_kwargs: object) -> str:
            raise AssertionError("foreign experiment byte decoder hook executed")

    monkeypatch.setattr(
        validator, "_read_manifest_bytes", lambda _path: ForeignBytes(b"data")
    )
    with pytest.raises(validator.ExperimentManifestError, match="native byte receipt"):
        _ = validator._read_utf8(Path("manifest.toml"))


def test_manifest_invalid_utf8_keeps_decoder_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native invalid UTF-8 retains the underlying Unicode decoder evidence."""
    monkeypatch.setattr(validator, "_read_manifest_bytes", lambda _path: b"\xff")
    with pytest.raises(
        validator.ExperimentManifestError, match="invalid experiment manifest UTF-8"
    ) as caught:
        _ = validator._read_utf8(Path("manifest.toml"))
    assert type(caught.value.__cause__) is UnicodeDecodeError


@pytest.mark.parametrize(
    "stage",
    (
        "parent_symlink",
        "parent_junction",
        "leaf_symlink",
        "leaf_junction",
        "post_parent_symlink",
        "post_parent_junction",
    ),
)
@pytest.mark.parametrize("receipt", (0, 1, object()))
def test_manifest_redirect_receipts_require_native_boolean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    receipt: object,
) -> None:
    """Path redirection cannot invoke forged host-return truthiness hooks."""
    source = tmp_path / "experiment.toml"
    _ = source.write_bytes(b"manifest\n")
    is_leaf = stage.startswith("leaf_")
    is_after = stage.startswith("post_")
    target = source if is_leaf else source.parent
    symlink = stage.endswith("symlink")
    native = Path.is_symlink if symlink else Path.is_junction
    inspections = 0

    class ForeignVerdict:
        def __bool__(self) -> bool:
            raise AssertionError("foreign manifest redirect hook executed")

    verdict = ForeignVerdict() if type(receipt) is object else receipt

    def forged_redirect(candidate: Path) -> bool:
        nonlocal inspections
        if candidate == target:
            inspections += 1
            if (not is_after and inspections == 1) or (is_after and inspections == 2):
                return cast("bool", verdict)
        return native(candidate)

    monkeypatch.setattr(
        Path, "is_symlink" if symlink else "is_junction", forged_redirect
    )
    with pytest.raises(validator.ExperimentManifestError, match="native redirect"):
        _ = validator._read_utf8(source)  # pyright: ignore[reportPrivateUsage]
