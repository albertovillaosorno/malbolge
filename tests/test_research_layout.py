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
#   - Fail-closed filesystem discovery evidence for research layout projection.
# - Must-Not:
#   - Parse experiment manifests or redefine research identities.
# - Allows:
#   - Inputs: test-local repository roots and injected filesystem failures.
#   - Outputs: deterministic discovery or propagated filesystem errors.
#   - Side effects: test-local filesystem writes only.
# - Split-When:
#   - Another discovery backend gains independent failure semantics.
# - Merge-When:
#   - Research layout discovery moves into another validator.
# - Summary:
#   - Prove research manifest discovery cannot hide inaccessible evidence.
# - Description:
#   - Distinguishes absent manifests from filesystem status failures.
# - Usage:
#   - Run through the repository Python validation suite.
# - Defaults:
#   - Inaccessible manifest status fails closed.
#

"""Fail-closed tests for research experiment layout discovery."""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Never, cast, final, override

import pytest

from scripts import research_layout


def _domain_root(root: Path) -> Path:
    return root / "src/research/algorithms/domain/algorithms"


def test_directory_without_manifest_remains_excluded(tmp_path: Path) -> None:
    """A genuinely absent experiment manifest is not a research experiment."""
    directory = _domain_root(tmp_path) / "utility"
    directory.mkdir(parents=True)
    assert research_layout.research_algorithm_directories(tmp_path) == ()


@pytest.mark.parametrize("kind", ("opaque", "foreign", "outside", "nested"))
def test_discovery_rejects_unbound_directory_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Domain enumeration must inspect only its exact native children."""
    domain = _domain_root(tmp_path)
    domain.mkdir(parents=True)
    outside = tmp_path / "outside" / "candidate"
    nested = domain / "nested" / "candidate"
    for directory in (outside, nested):
        directory.mkdir(parents=True)
        _ = (directory / "experiment.toml").write_text("schema_version = 1\n")

    class ForeignPath(type(domain)):
        @override
        def __getattribute__(self, name: str) -> object:
            if name in {"name", "parent"}:
                raise AssertionError("foreign research directory hook executed")
            return cast("object", super().__getattribute__(name))

    forged: object = {
        "opaque": object(),
        "foreign": ForeignPath(domain / "candidate"),
        "outside": outside,
        "nested": nested,
    }[kind]
    native_iterdir = Path.iterdir

    def forged_iterdir(path: Path) -> Iterator[Path]:
        if path == domain:
            yield cast("Path", forged)
        else:
            yield from native_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", forged_iterdir)
    with pytest.raises(OSError, match="native immediate directory entry"):
        _ = research_layout.research_algorithm_directories(tmp_path)


def test_inaccessible_manifest_status_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A status error cannot make one existing research manifest disappear."""
    directory = _domain_root(tmp_path) / "candidate"
    directory.mkdir(parents=True)
    manifest = directory / "experiment.toml"
    _ = manifest.write_text("schema_version = 1\n", encoding="utf-8")
    original_lstat = Path.lstat

    def fail_manifest_status(
        path: Path,
    ) -> object:
        if path == manifest:
            message = "injected research manifest status failure"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_manifest_status)
    with pytest.raises(PermissionError, match="injected research manifest"):
        _ = research_layout.research_algorithm_directories(tmp_path)


def test_redirected_manifest_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Research manifest discovery never follows redirected evidence."""
    directory = _domain_root(tmp_path) / "candidate"
    directory.mkdir(parents=True)
    manifest = directory / "experiment.toml"
    _ = manifest.write_text("schema_version = 1\n", encoding="utf-8")
    original_is_junction = Path.is_junction

    def report_junction(path: Path) -> bool:
        if path == manifest:
            return True
        return original_is_junction(path)

    monkeypatch.setattr(Path, "is_junction", report_junction)
    with pytest.raises(OSError, match="must not redirect"):
        _ = research_layout.research_algorithm_directories(tmp_path)


def test_linked_algorithm_directory_is_not_discovered(tmp_path: Path) -> None:
    """An external experiment cannot enter discovery through an ID link."""
    domain = _domain_root(tmp_path)
    domain.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    _ = (outside / "experiment.toml").write_text("schema_version = 1\n")
    (domain / "candidate").symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError, match="redirect"):
        _ = research_layout.research_algorithm_directories(tmp_path)


def test_linked_ancestor_directory_is_not_discovered(tmp_path: Path) -> None:
    """A link above the algorithm ID cannot import external experiments."""
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    candidate = outside / "research/algorithms/domain/algorithms/candidate"
    candidate.mkdir(parents=True)
    _ = (candidate / "experiment.toml").write_text("schema_version = 1\n")
    (root / "src").symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError, match="redirect"):
        _ = research_layout.research_algorithm_directories(root)


def test_linked_state_graph_directory_is_not_discovered(tmp_path: Path) -> None:
    """The composition research projection cannot follow an alias either."""
    _domain_root(tmp_path).mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    _ = (outside / "experiment.toml").write_text("schema_version = 1\n")
    state_graph = tmp_path / "src/research/algorithms/composition/state-graph"
    state_graph.parent.mkdir(parents=True)
    state_graph.symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError, match="redirect"):
        _ = research_layout.research_algorithm_directories(tmp_path)


@pytest.mark.parametrize(
    ("domain_ids", "include_composition"),
    [
        (("candidate", "CANDIDATE"), False),
        ((research_layout.STATE_GRAPH_ID.swapcase(),), True),
        (("caf\u00e9", "cafe\u0301"), False),
    ],
)
def test_discovery_rejects_casefold_colliding_experiments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    domain_ids: tuple[str, ...],
    include_composition: bool,
) -> None:
    """All manifest consumers reject aliases on case-insensitive hosts."""
    domain = _domain_root(tmp_path)
    domain.mkdir(parents=True)
    composition = tmp_path / "src/research/algorithms/composition/state-graph"
    original_iterdir = Path.iterdir

    def fake_iterdir(path: Path) -> Iterator[Path]:
        if path == domain:
            return iter(domain / identifier for identifier in domain_ids)
        return original_iterdir(path)

    def fake_manifest(path: Path, _root: Path) -> bool:
        return path.name == "experiment.toml" and (
            path.parent.parent == domain
            or (include_composition and path.parent == composition)
        )

    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    monkeypatch.setattr(research_layout, "_manifest_is_file", fake_manifest)
    with pytest.raises(OSError, match="case-insensitive"):
        _ = research_layout.research_algorithm_directories(tmp_path)


@pytest.mark.parametrize(
    "identifier", ("NUL", "scratch:stream", "a:b", "C:temp", "trailing.")
)
def test_discovery_rejects_unportable_research_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    identifier: str,
) -> None:
    """Domain discovery cannot publish a Windows-reserved stable identity."""
    domain = _domain_root(tmp_path)
    domain.mkdir(parents=True)
    original_iterdir = Path.iterdir

    def fake_iterdir(path: Path) -> Iterator[Path]:
        if path == domain:
            return iter((domain / identifier,))
        return original_iterdir(path)

    def fake_manifest(path: Path, _root: Path) -> bool:
        return path == domain / identifier / "experiment.toml"

    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    monkeypatch.setattr(research_layout, "_manifest_is_file", fake_manifest)
    with pytest.raises(OSError, match="not portable"):
        _ = research_layout.research_algorithm_directories(tmp_path)


def test_domain_and_composition_research_id_collision_fails_closed(
    tmp_path: Path,
) -> None:
    """Two physical experiments cannot silently share one stable research ID."""
    domain = _domain_root(tmp_path) / research_layout.STATE_GRAPH_ID
    domain.mkdir(parents=True)
    _ = (domain / "experiment.toml").write_text("schema_version = 1\n")
    composition = tmp_path / "src/research/algorithms/composition/state-graph"
    composition.mkdir(parents=True)
    _ = (composition / "experiment.toml").write_text("schema_version = 1\n")
    with pytest.raises(OSError, match="duplicate research algorithm ID"):
        _ = research_layout.research_algorithm_directories(tmp_path)


@pytest.mark.parametrize("position", ("domain", "candidate", "manifest"))
@pytest.mark.parametrize("receipt_kind", ("opaque", "hostile"))
def test_discovery_requires_native_status_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    position: str,
    receipt_kind: str,
) -> None:
    """Untrusted OS status objects cannot claim physical research evidence."""
    domain = _domain_root(tmp_path)
    candidate = domain / "candidate"
    candidate.mkdir(parents=True)
    manifest = candidate / "experiment.toml"
    _ = manifest.write_bytes(b"schema_version = 1\n")
    target = {"domain": domain, "candidate": candidate, "manifest": manifest}[position]
    original_lstat = Path.lstat

    @final
    class HostileStatus:
        @override
        def __getattribute__(self, _name: str) -> Never:
            raise AssertionError("foreign research stat field executed")

    receipt: object = HostileStatus() if receipt_kind == "hostile" else object()

    def forged_status(path: Path) -> os.stat_result:
        if path == target:
            return cast("os.stat_result", receipt)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", forged_status)
    with pytest.raises(OSError, match="native stat receipt"):
        _ = research_layout.research_algorithm_directories(tmp_path)


@pytest.mark.parametrize("position", ("domain", "candidate", "manifest"))
@pytest.mark.parametrize(
    "mode_kind", ("missing", "boolean", "float", "text", "foreign")
)
def test_discovery_requires_native_mode_in_stat_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    position: str,
    mode_kind: str,
) -> None:
    """Neither physical parent nor manifest leaf trusts forged stat mode fields."""
    domain = _domain_root(tmp_path)
    candidate = domain / "candidate"
    candidate.mkdir(parents=True)
    manifest = candidate / "experiment.toml"
    _ = manifest.write_bytes(b"schema_version = 1\n")
    target = {"domain": domain, "candidate": candidate, "manifest": manifest}[position]

    @final
    class ForeignMode(int):
        @override
        def __and__(self, other: object) -> Never:
            del self, other
            raise AssertionError("foreign research stat mode hook executed")

    bad_mode: object = {
        "missing": None,
        "boolean": True,
        "float": 1.5,
        "text": "directory",
        "foreign": ForeignMode(target.lstat().st_mode),
    }[mode_kind]
    original_lstat = Path.lstat
    native = target.lstat()
    fields: list[object] = [*native]
    fields[0] = bad_mode
    forged = os.stat_result(cast("tuple[int, ...]", tuple(fields)))

    def forged_lstat(path: Path) -> os.stat_result:
        return forged if path == target else original_lstat(path)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    with pytest.raises(OSError, match="native stat mode"):
        _ = research_layout.research_algorithm_directories(tmp_path)


@pytest.mark.parametrize("position", ("candidate", "manifest"))
@pytest.mark.parametrize("receipt_kind", ("truthy", "falsey", "hostile"))
def test_discovery_requires_native_junction_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    position: str,
    receipt_kind: str,
) -> None:
    """Forged junction predicates cannot suppress or invent research aliases."""
    domain = _domain_root(tmp_path)
    candidate = domain / "candidate"
    candidate.mkdir(parents=True)
    manifest = candidate / "experiment.toml"
    _ = manifest.write_bytes(b"schema_version = 1\n")
    target = candidate if position == "candidate" else manifest
    original_junction = Path.is_junction

    @final
    class HostilePredicate:
        def __bool__(self) -> Never:
            raise AssertionError("foreign research junction truthiness executed")

    receipt: object = {
        "truthy": "redirect",
        "falsey": list[object](),
        "hostile": HostilePredicate(),
    }[receipt_kind]

    def forged_junction(path: Path) -> bool:
        if path == target:
            return cast("bool", cast("object", receipt))
        return original_junction(path)

    monkeypatch.setattr(Path, "is_junction", forged_junction)
    with pytest.raises(OSError, match="native junction receipt"):
        _ = research_layout.research_algorithm_directories(tmp_path)
