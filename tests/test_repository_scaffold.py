# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
SOURCE_CATALOG = SRC_ROOT / "README.md"
SOURCE_SIDECAR = SRC_ROOT / "README.md.yml"
CARGO_MANIFEST = ROOT / "Cargo.toml"
FUNCTION_MANIFEST = "function.yml"
MIN_COMPOSITION_PARTS = 4
SOURCE_ROOT_NAME = "src"
VM_FUNCTION = "src/runtime/virtual-machine"
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
    assert source_files == {SOURCE_CATALOG.name, SOURCE_SIDECAR.name}

    catalog = SOURCE_CATALOG.read_text(encoding="utf-8")
    for domain in EXPECTED_DOMAINS:
        assert f"[`{domain}/`]({domain}/): governed semantic domain." in catalog
        assert (SRC_ROOT / domain / "README.md").is_file()
        assert (SRC_ROOT / domain / "README.md.yml").is_file()


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
        if path.is_dir() and not any(path.iterdir())
    )
    assert not empty
