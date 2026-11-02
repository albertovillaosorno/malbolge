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
#   - Regression tests for the research algorithm mirror contract.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for the research algorithm mirror contract."""

from __future__ import annotations

import os
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import] - Git-only fixture.
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Never, cast, override

import pytest

from scripts.validate import research_mirror as validator

ALGORITHMS_DIRECTORY = "algorithms"
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


def _always_ignored(entry: validator.MirrorEntry) -> bool:
    return bool(entry.research_id)


def _expect_id_failure(
    document_ids: frozenset[str],
    executable_ids: frozenset[str],
) -> None:
    try:
        _ = validator.validate_id_sets(document_ids, executable_ids)
    except validator.ResearchMirrorError:
        return
    message = "research mirror ID mismatch unexpectedly succeeded"
    raise AssertionError(message)


def test_repository_research_mirror_is_complete() -> None:
    """Every current research ID satisfies both halves and ignored output."""
    assert validator.validate_repository(_always_ignored) == EXPECTED_IDS


@pytest.mark.parametrize("verdict", (None, 0, 1, "ignored", object()))
def test_research_output_policy_requires_native_boolean(verdict: object) -> None:
    """A truthy or falsy foreign receipt cannot certify output isolation."""

    class ForeignVerdict:
        def __bool__(self) -> Never:
            raise AssertionError("foreign output policy truthiness executed")

    receipt = ForeignVerdict() if type(verdict) is object else verdict
    observed: list[str] = []

    def policy(entry: validator.MirrorEntry) -> bool:
        observed.append(entry.research_id)
        return cast("bool", receipt)

    with pytest.raises(validator.ResearchMirrorError, match="native boolean"):
        _ = validator.validate_repository(policy)
    assert observed == [EXPECTED_IDS[0]]


def test_document_only_research_id_fails_closed() -> None:
    """Reject a documentation-only algorithm without executable research."""
    _expect_id_failure(
        frozenset({"alpha", "beta"}),
        frozenset({"alpha"}),
    )


def test_executable_only_research_id_fails_closed() -> None:
    """Executable research without its academic record is rejected."""
    _expect_id_failure(
        frozenset({"alpha"}),
        frozenset({"alpha", "beta"}),
    )


@pytest.mark.parametrize(
    "aliases",
    [
        frozenset({"alpha", "ALPHA"}),
        frozenset({"analysis-v2", "ANALYSIS-v2"}),
        frozenset({"caf\u00e9", "cafe\u0301"}),
    ],
)
def test_casefold_colliding_research_ids_fail_closed(
    aliases: frozenset[str],
) -> None:
    """Distinct POSIX names cannot alias one research ID on Windows/macOS."""
    with pytest.raises(validator.ResearchMirrorError, match="case-insensitive"):
        _ = validator.validate_id_sets(aliases, aliases)


@pytest.mark.parametrize(
    "identifier",
    (
        "NUL",
        "scratch:stream",
        "a:b",
        "C:temp",
        "trailing.",
        "trailing ",
        r"foo\bar",
        ".",
        "..",
    ),
)
def test_unportable_research_ids_fail_closed(identifier: str) -> None:
    """A mirrored research ID must name one portable physical directory."""
    with pytest.raises(validator.ResearchMirrorError, match="not portable"):
        _ = validator.validate_id_sets(frozenset({identifier}), frozenset({identifier}))


def test_empty_research_mirror_fails_closed() -> None:
    """Deleting both halves cannot turn the mirror contract into a no-op."""
    _expect_id_failure(frozenset(), frozenset())


def test_non_research_algorithm_suites_are_explicitly_excluded() -> None:
    """Keep reusable/product suites in algorithms without academic mirroring."""
    executable_ids = frozenset((*EXPECTED_IDS, "diff", "doom"))
    assert validator.executable_research_ids(executable_ids) == frozenset(EXPECTED_IDS)
    assert frozenset({"diff", "doom"}) == validator.NON_RESEARCH_ALGORITHM_IDS


def test_unknown_executable_algorithm_still_fails_closed() -> None:
    """Do not silently classify unknown algorithm directories as product."""
    executable_ids = validator.executable_research_ids(
        frozenset((*EXPECTED_IDS, "diff", "doom", "mystery"))
    )
    _expect_id_failure(frozenset(EXPECTED_IDS), executable_ids)


@pytest.mark.parametrize(
    "redirect",
    ("research-file", "executable-readme", "document-directory", "test-directory"),
)
def test_mirror_rejects_redirected_evidence(
    redirect: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Outside aliases must not fulfill the physical research mirror contract."""
    documents = tmp_path / "docs/research/algorithms"
    document = documents / "fixture"
    executable = tmp_path / "src/research/algorithms/domain/algorithms/fixture"
    test_directory = tmp_path / "tests/function/algorithms/domain/fixture"
    for directory in (document, executable, test_directory):
        directory.mkdir(parents=True)
    for filename in ("README.md", "research.md"):
        _ = (document / filename).write_text("fixture", encoding="utf-8")
    for filename in ("README.md", "experiment.toml", "lifecycle.toml"):
        _ = (executable / filename).write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "DOCUMENT_ROOT", documents)
    assert validator.validate_repository(_always_ignored) == ("fixture",)

    if redirect == "document-directory":
        victim = document
    elif redirect == "test-directory":
        victim = test_directory
    elif redirect == "research-file":
        victim = document / "research.md"
    else:
        victim = executable / "README.md"
    outside = tmp_path / "outside" / victim.name
    outside.parent.mkdir(exist_ok=True)
    _ = victim.rename(outside)
    victim.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(validator.ResearchMirrorError, match="redirect"):
        _ = validator.validate_repository(_always_ignored)


def test_mirror_rejects_directory_id_symlink(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A redirected research ID cannot enumerate as a direct physical ID."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    documents = tmp_path / "documents"
    documents.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (documents / "alias").symlink_to(outside, target_is_directory=True)
    with pytest.raises(validator.ResearchMirrorError, match="redirect"):
        _ = validator._directory_ids(documents)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
@pytest.mark.parametrize(
    "operation", ("leaf_lstat", "leaf_junction", "parent_lstat", "parent_junction")
)
def test_mirror_physical_path_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """Malformed path-inspection errors cannot escape the physical contract."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    directory = tmp_path / "documents"
    directory.mkdir()
    evidence = directory / "research.md"
    _ = evidence.write_text("fixture", encoding="utf-8")
    target = directory if operation.startswith("parent_") else evidence
    if operation.endswith("lstat"):
        real_lstat = Path.lstat

        def fail_lstat(path: Path) -> os.stat_result:
            if path == target:
                raise fault_type("injected mirror lstat fault")
            return real_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    else:
        real_junction = Path.is_junction

        def fail_junction(path: Path) -> bool:
            if path == target:
                raise fault_type("injected mirror junction fault")
            return real_junction(path)

        monkeypatch.setattr(Path, "is_junction", fail_junction)
    with pytest.raises(validator.ResearchMirrorError, match="status failed"):
        _ = validator._physical_status(  # pyright: ignore[reportPrivateUsage]
            evidence, "research evidence"
        )


@pytest.mark.parametrize(
    "kind", ("nonpath", "foreign-path", "outside-root", "nested-child")
)
def test_mirror_directory_scan_requires_native_immediate_children(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """A forged directory iterator cannot certify a different directory ID."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    documents = tmp_path / "documents"
    documents.mkdir()
    outside = tmp_path / "outside" / "fixture"
    nested = documents / "nested" / "fixture"
    outside.mkdir(parents=True)
    nested.mkdir(parents=True)

    class ForeignPath(type(documents)):
        @override
        def __getattribute__(self, name: str) -> object:
            if name in {"name", "parent"}:
                raise AssertionError("foreign directory entry hook executed")
            return cast("object", super().__getattribute__(name))

    children: dict[str, object] = {
        "nonpath": object(),
        "foreign-path": ForeignPath(documents / "fixture"),
        "outside-root": outside,
        "nested-child": nested,
    }
    bad_child = children[kind]
    native_iterdir = Path.iterdir

    def forged_iterdir(path: Path) -> Iterator[Path]:
        if path == documents:
            yield cast("Path", bad_child)
        else:
            yield from native_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", forged_iterdir)
    with pytest.raises(validator.ResearchMirrorError, match="directory entry"):
        _ = validator._directory_ids(documents)  # pyright: ignore[reportPrivateUsage]


def test_mirror_scan_rejects_repeated_directory_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated native mirror entries cannot be collapsed into one ID."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    documents = tmp_path / "documents"
    child = documents / "candidate"
    child.mkdir(parents=True)
    native_iterdir = Path.iterdir

    def duplicate_iterdir(path: Path) -> Iterator[Path]:
        if path == documents:
            yield child
            yield child
        else:
            yield from native_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", duplicate_iterdir)
    with pytest.raises(
        validator.ResearchMirrorError, match="duplicate directory entry"
    ):
        _ = validator._directory_ids(documents)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
@pytest.mark.parametrize("operation", ("id_lstat", "id_junction", "iterdir"))
def test_mirror_directory_discovery_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """A failed ID scan cannot pretend to enumerate the research mirror."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    documents = tmp_path / "documents"
    documents.mkdir()
    child = documents / "fixture"
    child.mkdir()
    if operation == "id_lstat":
        real_lstat = Path.lstat

        def fail_lstat(path: Path) -> os.stat_result:
            if path == child:
                raise fault_type("injected mirror ID status fault")
            return real_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    elif operation == "id_junction":
        real_junction = Path.is_junction

        def fail_junction(path: Path) -> bool:
            if path == child:
                raise fault_type("injected mirror ID junction fault")
            return real_junction(path)

        monkeypatch.setattr(Path, "is_junction", fail_junction)
    else:
        real_iterdir = Path.iterdir

        def fail_iterdir(path: Path) -> Iterator[Path]:
            if path == documents:
                raise fault_type("injected mirror directory scan fault")
            return real_iterdir(path)

        monkeypatch.setattr(Path, "iterdir", fail_iterdir)
    expected = "scan failed" if operation == "iterdir" else "ID status failed"
    with pytest.raises(validator.ResearchMirrorError, match=expected):
        _ = validator._directory_ids(documents)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "kind",
    (
        "noncanonical",
        "duplicate",
        "foreign-collection",
        "foreign-pair",
        "foreign-id",
        "foreign-directory",
    ),
)
def test_mirror_shared_discovery_requires_canonical_unique_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """A shared layout response cannot silently rewrite a research identity."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    documents = tmp_path / "docs/research/algorithms"
    monkeypatch.setattr(validator, "DOCUMENT_ROOT", documents)
    document = documents / "candidate"
    correct = tmp_path / "src/research/algorithms/domain/algorithms/candidate"
    alternate = tmp_path / "src/research/algorithms/domain/unrelated/candidate"
    tests = tmp_path / "tests/function/algorithms/domain/candidate"
    for directory in (document, correct, alternate, tests):
        directory.mkdir(parents=True)
    for filename in ("README.md", "research.md"):
        _ = (document / filename).write_text("fixture", encoding="utf-8")
    for executable in (correct, alternate):
        for filename in ("README.md", "experiment.toml", "lifecycle.toml"):
            _ = (executable / filename).write_text("fixture", encoding="utf-8")

    class ForeignId(str):  # ruff: ignore[subclass-builtin]
        @override
        def __hash__(self) -> Never:
            raise AssertionError("foreign research identifier hashing executed")

    class ForeignDirectory(type(correct)):
        @override
        def __eq__(self, other: object) -> Never:
            del other
            raise AssertionError("foreign research directory equality executed")

    records: object = {
        "noncanonical": (("candidate", alternate),),
        "duplicate": (("candidate", correct), ("candidate", correct)),
        "foreign-collection": [("candidate", correct)],
        "foreign-pair": (["candidate", correct],),
        "foreign-id": ((ForeignId("candidate"), correct),),
        "foreign-directory": (("candidate", ForeignDirectory(correct)),),
    }[kind]

    def forged_discovery(_root: Path) -> tuple[tuple[str, Path], ...]:
        return cast("tuple[tuple[str, Path], ...]", records)

    monkeypatch.setattr(validator, "research_algorithm_directories", forged_discovery)
    with pytest.raises(validator.ResearchMirrorError, match="discovery"):
        _ = validator.validate_repository(_always_ignored)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_mirror_shared_layout_failure_is_typed(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Shared layout enumeration errors stay within the mirror error model."""

    def fail_layout(_root: Path) -> tuple[tuple[str, Path], ...]:
        raise fault_type("injected shared layout failure")

    monkeypatch.setattr(validator, "research_algorithm_directories", fail_layout)
    with pytest.raises(validator.ResearchMirrorError, match="discovery failed"):
        _ = validator.validate_repository(_always_ignored)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_mirror_git_output_probe_failure_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A failed Git ignore probe is a typed research policy rejection."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    entry = validator.MirrorEntry(
        document=tmp_path / "docs" / "fixture",
        executable=tmp_path / "algorithms" / "fixture",
        research_id="fixture",
    )

    def fail_git(*_args: object, **_kwargs: object) -> sp.CompletedProcess[str]:
        raise fault_type("injected Git ignore failure")

    monkeypatch.setattr(sp, "run", fail_git)
    with pytest.raises(validator.ResearchMirrorError, match="Git ignore probe failed"):
        _ = validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("receipt", [None, False, 0, 0.0, {}, object()])
def test_mirror_git_probe_rejects_nonprocess_receipts(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Only real process receipts may certify that Git ignored output."""
    entry = validator.MirrorEntry(
        document=validator.ROOT / "docs/fixture",
        executable=validator.ROOT / "algorithms/fixture",
        research_id="fixture",
    )

    def forged_run(*args: object, **kwargs: object) -> object:
        del args, kwargs
        return receipt

    monkeypatch.setattr(sp, "run", forged_run)
    with pytest.raises(validator.ResearchMirrorError, match="malformed Git"):
        # ruff: ignore[private-member-access]
        _ = validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("returncode", [False, True, 0.0, 1.0, None, "0"])
def test_mirror_git_probe_rejects_noninteger_exit_receipts(
    monkeypatch: pytest.MonkeyPatch,
    returncode: object,
) -> None:
    """Boolean, float and missing exits must not impersonate Git status."""
    entry = validator.MirrorEntry(
        document=validator.ROOT / "docs/fixture",
        executable=validator.ROOT / "algorithms/fixture",
        research_id="fixture",
    )
    completed = sp.CompletedProcess[str](args=[], returncode=cast("int", returncode))

    def forged_run(*args: object, **kwargs: object) -> sp.CompletedProcess[str]:
        del args, kwargs
        return completed

    monkeypatch.setattr(sp, "run", forged_run)
    with pytest.raises(validator.ResearchMirrorError, match="malformed Git"):
        # ruff: ignore[private-member-access]
        _ = validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "kind",
    (
        "missing",
        "tuple",
        "wrong-command",
        "wrong-target",
        "foreign-list",
        "foreign-string",
        "opaque",
    ),
)
def test_mirror_git_probe_requires_exact_command_receipt(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Only the requested directory's Git verdict can certify its ignore rule."""
    entry = validator.MirrorEntry(
        document=validator.ROOT / "docs/fixture",
        executable=validator.ROOT / "algorithms/fixture",
        research_id="fixture",
    )
    expected = [
        "git",
        "check-ignore",
        "--quiet",
        "--no-index",
        "--",
        "algorithms/fixture/out/",
    ]

    class ForeignList(list[str]):
        @override
        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign Git command list compared")

    class ForeignString(str):  # ruff: ignore[subclass-builtin]
        @override
        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign Git command member compared")

    altered: object = {
        "missing": None,
        "tuple": tuple(expected),
        "wrong-command": ["git", "version"],
        "wrong-target": [*expected[:-1], "algorithms/other/out/"],
        "foreign-list": ForeignList(expected),
        "foreign-string": [ForeignString("git"), *expected[1:]],
        "opaque": object(),
    }[kind]
    completed = sp.CompletedProcess[str](args=cast("list[str]", altered), returncode=0)

    def forged_run(*_args: object, **_kwargs: object) -> sp.CompletedProcess[str]:
        return completed

    monkeypatch.setattr(sp, "run", forged_run)
    with pytest.raises(validator.ResearchMirrorError, match="malformed Git"):
        _ = validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]


def test_mirror_git_probe_uses_finite_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The local Git verdict must not hang the research validation runner."""
    entry = validator.MirrorEntry(
        document=validator.ROOT / "docs/fixture",
        executable=validator.ROOT / "algorithms/fixture",
        research_id="fixture",
    )

    def inspect_run(command: list[str], **kwargs: object) -> sp.CompletedProcess[str]:
        assert kwargs.get("timeout") == 15
        return sp.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(sp, "run", inspect_run)
    assert validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]


def test_mirror_git_probe_timeout_is_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A delayed Git ignore verdict remains a typed research policy failure."""
    entry = validator.MirrorEntry(
        document=validator.ROOT / "docs/fixture",
        executable=validator.ROOT / "algorithms/fixture",
        research_id="fixture",
    )

    def timed_out(*_args: object, **_kwargs: object) -> sp.CompletedProcess[str]:
        raise sp.TimeoutExpired(cmd=["git", "check-ignore"], timeout=15)

    monkeypatch.setattr(sp, "run", timed_out)
    with pytest.raises(validator.ResearchMirrorError, match="Git ignore probe failed"):
        _ = validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "kind",
    ("missing", "false", "short", "long", "foreign", "write", "flush", "flush-receipt"),
)
def test_mirror_cli_rejects_incomplete_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """A failed or forged stdout record cannot certify a valid mirror."""
    monkeypatch.setattr(validator, "validate_repository", lambda: ("candidate",))
    calls: list[str] = []

    class ForeignCount(int):
        @override
        def __eq__(self, other: object) -> Never:
            del other
            raise AssertionError("foreign output count comparison executed")

    class Output:
        def write(self, message: str) -> int:
            calls.append("write")
            if kind == "write":
                raise OSError("injected mirror stdout write failure")
            receipts: dict[str, object] = {
                "missing": None,
                "false": False,
                "short": len(message) - 1,
                "long": len(message) + 1,
                "foreign": ForeignCount(len(message)),
            }
            return cast("int", receipts.get(kind, len(message)))

        def flush(self) -> None:
            calls.append("flush")
            if kind == "flush":
                raise RuntimeError("injected mirror stdout flush failure")
            if kind == "flush-receipt":
                return cast("None", cast("object", 1))

    monkeypatch.setattr(sys, "stdout", Output())
    assert validator.main() == 1
    assert calls == (["write", "flush"] if kind.startswith("flush") else ["write"])
    assert "CLI output write or flush failed" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ("write", "flush", "receipt"))
def test_mirror_cli_diagnostic_failure_preserves_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """A broken diagnostic stream cannot conceal a failed mirror policy."""

    def fail_validation() -> tuple[str, ...]:
        raise validator.ResearchMirrorError("injected mirror policy failure")

    class BrokenStderr:
        def write(self, _message: str) -> int:
            if kind == "write":
                raise OSError("injected mirror stderr write failure")
            return 0 if kind == "receipt" else len(_message)

        def flush(self) -> None:
            if kind == "flush":
                raise RuntimeError("injected mirror stderr flush failure")

    monkeypatch.setattr(validator, "validate_repository", fail_validation)
    monkeypatch.setattr(sys, "stderr", BrokenStderr())
    assert validator.main() == 1


def test_mirror_cli_does_not_format_foreign_os_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Host subclasses cannot run custom formatters in the CLI boundary."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError

    foreign = type("ForeignGitError", (OSError,), {"__str__": unsafe_str})
    fault = foreign("untrusted Git error")

    def failed_validation() -> tuple[str, ...]:
        raise fault

    monkeypatch.setattr(validator, "validate_repository", failed_validation)
    assert validator.main() == 1
    assert foreign.__name__ in capsys.readouterr().err


def test_output_policy_checks_directory_not_just_one_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ignoring a single probe must not admit trackable research outputs."""
    _ = sp.run(
        ["git", "init", "--quiet", str(tmp_path)],
        check=True,
        capture_output=True,
        shell=False,
    )
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    executable = tmp_path / "algorithms" / "fixture"
    executable.mkdir(parents=True)
    entry = validator.MirrorEntry(
        document=tmp_path / "docs" / "fixture",
        executable=executable,
        research_id="fixture",
    )
    ignore_file = tmp_path / ".gitignore"

    _ = ignore_file.write_text("**/out/.mirror-probe\n", encoding="utf-8")
    assert not validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]

    _ = ignore_file.write_text("**/out/\n", encoding="utf-8")
    assert validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]

    _ = ignore_file.write_text("**/out/*.bin\n", encoding="utf-8")
    assert not validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]

    _ = ignore_file.write_text("**/out/*\n", encoding="utf-8")
    assert validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("boundary", ["physical", "scan", "id", "discovery", "git"])
@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_mirror_foreign_host_error_formatters_cannot_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    boundary: str,
    fault_type: type[Exception],
) -> None:
    """Host exceptions retain typed causes without caller-owned formatting."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("research mirror foreign exception formatting executed")

    foreign = type("ForeignResearchMirrorFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("dangerous exception text")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    if boundary in {"physical", "scan", "id"}:
        directory = tmp_path / "documents"
        directory.mkdir()
        child = directory / "fixture"
        _ = child.write_text("fixture", encoding="utf-8")
        original_lstat = Path.lstat
        original_iterdir = Path.iterdir
        if boundary in {"physical", "id"}:

            def fail_lstat(path: Path) -> os.stat_result:
                if path == child:
                    raise fault
                return original_lstat(path)

            monkeypatch.setattr(Path, "lstat", fail_lstat)
        else:

            def fail_iterdir(path: Path) -> Iterator[Path]:
                if path == directory:
                    raise fault
                return original_iterdir(path)

            monkeypatch.setattr(Path, "iterdir", fail_iterdir)
        with pytest.raises(
            validator.ResearchMirrorError,
            match=(
                "status failed"
                if boundary == "physical"
                else "scan failed"
                if boundary == "scan"
                else "ID status failed"
            ),
        ) as caught:
            if boundary == "physical":
                _ = validator._physical_status(  # pyright: ignore[reportPrivateUsage]
                    child, "research document"
                )
            else:
                _ = validator._directory_ids(  # pyright: ignore[reportPrivateUsage]
                    directory
                )
    elif boundary == "discovery":

        def fail_discovery(_root: Path) -> None:
            raise fault

        monkeypatch.setattr(validator, "research_algorithm_directories", fail_discovery)
        with pytest.raises(
            validator.ResearchMirrorError, match="discovery failed"
        ) as caught:
            _ = validator.validate_repository(_always_ignored)
    else:
        entry = validator.MirrorEntry(
            document=tmp_path / "docs/fixture",
            executable=tmp_path / "algorithms/fixture",
            research_id="fixture",
        )

        def fail_git(*_args: object, **_kwargs: object) -> None:
            raise fault

        monkeypatch.setattr(sp, "run", fail_git)
        with pytest.raises(
            validator.ResearchMirrorError, match="Git ignore probe failed"
        ) as caught:
            _ = validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is fault


def test_mirror_native_host_error_diagnostic_remains_actionable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Exact built-in OSError text remains in typed failure diagnostics."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    entry = validator.MirrorEntry(
        document=tmp_path / "docs/fixture",
        executable=tmp_path / "algorithms/fixture",
        research_id="fixture",
    )
    fault = OSError("native git executable unavailable")

    def fail_git(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(sp, "run", fail_git)
    with pytest.raises(
        validator.ResearchMirrorError,
        match="native git executable unavailable",
    ) as caught:
        _ = validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("operation", ("parent_status", "leaf_status", "id_status"))
@pytest.mark.parametrize("receipt_kind", ("opaque", "hostile"))
def test_mirror_direct_stat_receipt_must_be_native(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    receipt_kind: str,
) -> None:
    """Neither direct evidence nor discovered ID status may execute host hooks."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    documents = tmp_path / "documents"
    documents.mkdir()
    evidence = documents / "research.md"
    _ = evidence.write_text("fixture", encoding="utf-8")
    child = documents / "fixture"
    child.mkdir()
    target = {
        "parent_status": documents,
        "leaf_status": evidence,
        "id_status": child,
    }[operation]

    class ForeignStatus:
        @override
        def __getattribute__(self, name: str) -> object:
            del self, name
            raise AssertionError("foreign mirror status hook executed")

    receipt: object = ForeignStatus() if receipt_kind == "hostile" else object()
    native_lstat = Path.lstat

    def forged_lstat(path: Path) -> os.stat_result:
        if path == target:
            return cast("os.stat_result", receipt)
        return native_lstat(path)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    with pytest.raises(validator.ResearchMirrorError, match="native stat receipt"):
        if operation == "id_status":
            _ = validator._directory_ids(documents)  # pyright: ignore[reportPrivateUsage]
        else:
            _ = validator._physical_status(  # pyright: ignore[reportPrivateUsage]
                evidence, "research evidence"
            )


@pytest.mark.parametrize("operation", ("parent", "leaf", "id"))
@pytest.mark.parametrize(
    "mode_kind", ("missing", "boolean", "float", "text", "foreign")
)
def test_mirror_direct_stat_mode_requires_native_integer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    mode_kind: str,
) -> None:
    """A native stat container cannot launder a foreign path-mode verdict."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    directory = tmp_path / "documents"
    directory.mkdir()
    evidence = directory / "research.md"
    _ = evidence.write_text("fixture", encoding="utf-8")
    child = directory / "fixture"
    child.mkdir()
    target = {"parent": directory, "leaf": evidence, "id": child}[operation]

    class ForeignMode(int):
        @override
        def __and__(self, other: object) -> Never:
            del self, other
            raise AssertionError("foreign mirror mode bitwise hook executed")

    bad_mode: object = {
        "missing": None,
        "boolean": True,
        "float": 1.5,
        "text": "directory",
        "foreign": ForeignMode(target.lstat().st_mode),
    }[mode_kind]
    original_lstat = Path.lstat
    native = target.lstat()
    forged_fields: list[object] = [*native]
    forged_fields[0] = bad_mode
    forged = os.stat_result(cast("tuple[int, ...]", tuple(forged_fields)))

    def forged_lstat(path: Path) -> os.stat_result:
        return forged if path == target else original_lstat(path)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    with pytest.raises(validator.ResearchMirrorError, match="native stat mode"):
        if operation == "id":
            _ = validator._directory_ids(directory)  # pyright: ignore[reportPrivateUsage]
        else:
            _ = validator._physical_status(  # pyright: ignore[reportPrivateUsage]
                evidence, "research evidence"
            )


@pytest.mark.parametrize(
    "operation", ("parent_junction", "leaf_junction", "id_junction")
)
@pytest.mark.parametrize("receipt", (0, 1, object()))
def test_mirror_direct_junction_receipt_must_be_native_bool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    receipt: object,
) -> None:
    """Direct research mirrors never infer redirection through truthiness."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    documents = tmp_path / "documents"
    documents.mkdir()
    evidence = documents / "research.md"
    _ = evidence.write_text("fixture", encoding="utf-8")
    child = documents / "fixture"
    child.mkdir()
    target = {
        "parent_junction": documents,
        "leaf_junction": evidence,
        "id_junction": child,
    }[operation]

    class ForeignVerdict:
        def __bool__(self) -> bool:
            raise AssertionError("foreign mirror junction truthiness hook executed")

    verdict = ForeignVerdict() if type(receipt) is object else receipt
    native_junction = Path.is_junction

    def forged_junction(path: Path) -> bool:
        if path == target:
            return cast("bool", verdict)
        return native_junction(path)

    monkeypatch.setattr(Path, "is_junction", forged_junction)
    with pytest.raises(validator.ResearchMirrorError, match="native junction receipt"):
        if operation == "id_junction":
            _ = validator._directory_ids(documents)  # pyright: ignore[reportPrivateUsage]
        else:
            _ = validator._physical_status(  # pyright: ignore[reportPrivateUsage]
                evidence, "research evidence"
            )


@pytest.mark.parametrize(
    ("index", "replacement"),
    [
        (0, "foreign-git"),
        (1, "status"),
        (-1, "algorithms/foreign/out/"),
    ],
)
def test_mirror_git_probe_cannot_mutate_borrowed_command_receipt(
    monkeypatch: pytest.MonkeyPatch,
    index: int,
    replacement: str,
) -> None:
    """Mutating the launched argv cannot rewrite the expected Git invocation."""
    entry = validator.MirrorEntry(
        document=validator.ROOT / "docs/fixture",
        executable=validator.ROOT / "algorithms/fixture",
        research_id="fixture",
    )

    def mutated_run(argv: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        argv[index] = replacement
        return sp.CompletedProcess(argv, 0)

    monkeypatch.setattr(sp, "run", mutated_run)
    with pytest.raises(validator.ResearchMirrorError, match="malformed Git"):
        _ = validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]
