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
#   - Executable evidence for repository responsibility topology.
# - Must-Not:
#   - Treat implementation language or Cargo package mechanics as ownership.
# - Allows:
#   - Inputs: source-domain docs, function manifests, and Cargo composition.
#   - Outputs: exact topology and ownership diagnostics.
#   - Side effects: repository reads only.
# - Split-When:
#   - Function-manifest schema validation gains a separate repository owner.
# - Merge-When:
#   - Jig directly validates the complete responsibility scaffold contract.
# - Summary:
#   - Proves that source roots and functions remain responsibility-oriented.
# - Description:
#   - Rejects language buckets, unowned functions, and root Cargo source files.
# - Usage:
#   - Runs with the repository Python test suite.
# - Defaults:
#   - The checked-in source-domain catalog is the exact accepted topology.
#

"""Repository responsibility-scaffold regressions."""

from __future__ import annotations

from pathlib import Path
import re

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed Git argv, never a shell command.
import tomllib
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
GRAPH_MIRROR_ROOT = ROOT / ".jig" / "graph" / "mirror"
SOURCE_CATALOG = SRC_ROOT / "README.md"
SOURCE_SIDECAR = GRAPH_MIRROR_ROOT / "src" / "README.md.yml"
CARGO_MANIFEST = ROOT / "Cargo.toml"
GIT = "git"
FUNCTION_MANIFEST = "function.yml"
MIN_COMPOSITION_PARTS = 4
SOURCE_ROOT_NAME = "src"
VM_FUNCTION = "src/runtime/virtual-machine"
CARGO_EXCLUDED_ROOTS = frozenset({
    ".cache",
    ".dependencies",
    ".git",
    ".temp",
    "target",
})
DEPENDENCY_TABLE_NAMES = frozenset({
    "build-dependencies",
    "dependencies",
    "dev-dependencies",
})
WORKSPACE_PACKAGE_KEYS = frozenset({
    "description",
    "edition",
    "license",
    "publish",
    "repository",
    "rust-version",
    "version",
})
EXPECTED_DOMAINS = (
    "automation",
    "compiler",
    "examples",
    "interface",
    "interoperability",
    "optimization",
    "performance",
    "research",
    "runtime",
    "specification",
    "tooling",
)
FORBIDDEN_LANGUAGE_ROOTS = frozenset({
    "c",
    "cpp",
    "cuda",
    "cxx",
    "python",
    "rust",
})
FUNCTION_ROUTE = "route: src/<domain>/<function>/<kind>/<part>"
FUNCTION_SCHEMA = "schema: jig-function/v3"
FUNCTION_ROLE = "role: governed-function"
COMPOSITION_PATH = re.compile(
    r'^(?:build|path) = "(src/[^"]+)"$',
    re.MULTILINE,
)
LANGUAGE = re.compile(r"^\s+language: ([a-z0-9_+-]+)$", re.MULTILINE)


def _source_domains() -> tuple[Path, ...]:
    return tuple(
        sorted(
            (path for path in SRC_ROOT.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        )
    )


def _function_directories() -> tuple[Path, ...]:
    return tuple(
        sorted(
            (
                function
                for domain in _source_domains()
                for function in domain.iterdir()
                if function.is_dir()
            ),
            key=lambda path: path.as_posix(),
        )
    )


def _composition_paths(text: str) -> tuple[str, ...]:
    return tuple(
        match.group(1) for match in COMPOSITION_PATH.finditer(text)
    )


def _toml_table(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast("dict[str, object]", value)


def _load_cargo_manifest(path: Path) -> dict[str, object]:
    return cast(
        "dict[str, object]",
        tomllib.loads(path.read_text(encoding="utf-8")),
    )


def _cargo_manifests() -> tuple[Path, ...]:
    return tuple(
        sorted(
            (
                path
                for path in ROOT.rglob("Cargo.toml")
                if not CARGO_EXCLUDED_ROOTS.intersection(
                    path.relative_to(ROOT).parts
                )
            ),
            key=lambda path: path.as_posix(),
        )
    )


def _dependency_tables(
    document: dict[str, object],
) -> tuple[tuple[tuple[str, ...], dict[str, object]], ...]:
    tables: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def visit(value: dict[str, object], path: tuple[str, ...]) -> None:
        for key, child in value.items():
            if not isinstance(child, dict):
                continue
            table = cast("dict[str, object]", child)
            current = (*path, key)
            if key in DEPENDENCY_TABLE_NAMES:
                tables.append((current, table))
            visit(table, current)

    visit(document, ())
    return tuple(tables)


def _is_workspace_dependency(declaration: object) -> bool:
    if not isinstance(declaration, dict):
        return False
    table = cast("dict[str, object]", declaration)
    allowed_keys = frozenset({"features", "optional", "workspace"})
    return (
        table.get("workspace") is True
        and frozenset(table) <= allowed_keys
    )


def _manifest_dependency_violations(manifest: Path) -> tuple[str, ...]:
    document = _load_cargo_manifest(manifest)
    relative = manifest.relative_to(ROOT).as_posix()
    violations: list[str] = []
    for path, dependencies in _dependency_tables(document):
        if path == ("workspace", "dependencies"):
            continue
        table = ".".join(path)
        violations.extend(
            f"{relative}:{table}:{name}"
            for name, declaration in dependencies.items()
            if not _is_workspace_dependency(declaration)
        )
    return tuple(violations)


def _is_git_ignored(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    # jig-ignore-next-line: indivisible reviewed identifier
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed Git argv, no shell.
        [GIT, "check-ignore", "--quiet", "--no-index", relative],
        cwd=ROOT,
        check=False,
        shell=False,
    )
    assert completed.returncode in {0, 1}, relative
    return completed.returncode == 0


def test_source_root_matches_declared_responsibility_domains() -> None:
    """The thin source root contains only its catalog and governed domains."""
    assert SOURCE_CATALOG.is_file()
    assert SOURCE_SIDECAR.is_file()
    actual_domains = tuple(path.name for path in _source_domains())
    assert actual_domains == EXPECTED_DOMAINS
    assert not FORBIDDEN_LANGUAGE_ROOTS.intersection(actual_domains)

    source_files = {
        path.name for path in SRC_ROOT.iterdir() if path.is_file()
    }
    assert source_files == {SOURCE_CATALOG.name}

    catalog = SOURCE_CATALOG.read_text(encoding="utf-8")
    for domain in EXPECTED_DOMAINS:
        assert f"[`{domain}/`]({domain}/): governed semantic domain." in catalog
        assert (SRC_ROOT / domain / "README.md").is_file()
        assert (
            GRAPH_MIRROR_ROOT / "src" / domain / "README.md.yml"
        ).is_file()


def test_every_function_has_one_governed_manifest() -> None:
    """Every second-level source directory is an owned governed function."""
    functions = _function_directories()
    assert functions
    mixed_language_functions: list[str] = []
    for function in functions:
        manifest = function / FUNCTION_MANIFEST
        assert manifest.is_file(), function.relative_to(ROOT).as_posix()
        text = manifest.read_text(encoding="utf-8")
        relative = function.relative_to(ROOT).as_posix()
        assert FUNCTION_SCHEMA in text
        assert f"path: {relative}" in text
        assert FUNCTION_ROLE in text
        assert FUNCTION_ROUTE in text
        languages = frozenset(LANGUAGE.findall(text))
        if len(languages) > 1:
            mixed_language_functions.append(relative)

    assert VM_FUNCTION in mixed_language_functions


def test_cargo_package_metadata_inherits_workspace_authority() -> None:
    """Every inheritable root-package field comes from workspace authority."""
    document = _load_cargo_manifest(CARGO_MANIFEST)
    package = _toml_table(document["package"])
    workspace = _toml_table(document["workspace"])
    workspace_package = _toml_table(workspace["package"])
    assert workspace_package.keys() >= WORKSPACE_PACKAGE_KEYS
    for key in WORKSPACE_PACKAGE_KEYS:
        assert package[key] == {"workspace": True}


def test_workspace_dependency_rule_rejects_local_sources() -> None:
    """Workspace members may add features, never local source ownership."""
    accepted = (
        {"workspace": True},
        {"features": ["serde"], "workspace": True},
        {"optional": True, "workspace": True},
    )
    rejected = (
        "1.2.3",
        {"git": "https://example.invalid/repository.git"},
        {"path": "../dependency"},
        {"version": "1.2.3"},
        {"version": "1.2.3", "workspace": True},
    )
    assert all(_is_workspace_dependency(value) for value in accepted)
    assert not any(_is_workspace_dependency(value) for value in rejected)


def test_cargo_dependencies_are_declared_only_by_workspace() -> None:
    """Cargo members cannot own dependency versions or source locations."""
    violations = tuple(
        violation
        for manifest in _cargo_manifests()
        for violation in _manifest_dependency_violations(manifest)
    )
    assert not violations, "non-workspace Cargo dependencies:\n" + "\n".join(
        violations
    )


def test_cargo_composition_stays_inside_owned_functions() -> None:
    """Cargo entrypoints remain build wiring inside responsibility functions."""
    manifest = CARGO_MANIFEST.read_text(encoding="utf-8")
    paths = _composition_paths(manifest)
    assert paths
    for value in paths:
        parts = Path(value).parts
        assert len(parts) >= MIN_COMPOSITION_PARTS
        assert parts[0] == SOURCE_ROOT_NAME
        assert parts[1] in EXPECTED_DOMAINS
        function_manifest = ROOT.joinpath(
            parts[0],
            parts[1],
            parts[2],
            FUNCTION_MANIFEST,
        )
        assert function_manifest.is_file()

    assert not (SRC_ROOT / "lib.rs").exists()
    assert not (SRC_ROOT / "main.rs").exists()


def test_source_tree_has_no_speculative_empty_directories() -> None:
    """No speculative empty directory survives inside governed source."""
    empty = tuple(
        path.relative_to(ROOT).as_posix()
        for path in SRC_ROOT.rglob("*")
        if (
            path.is_dir()
            and not any(path.iterdir())
            and not _is_git_ignored(path)
        )
    )
    assert not empty
