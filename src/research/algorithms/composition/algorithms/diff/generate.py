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
#   - Public source-bound transformation generation API.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Public source-bound transformation generation API."""

from __future__ import annotations

import builtins
import hashlib
import math
import os
import stat
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePath
from types import MemberDescriptorType
from typing import TYPE_CHECKING, NamedTuple, cast

from algorithms.diff.admission import identity_tree
from algorithms.diff.domain import DiffDomain, DomainContractError, load_diff_domain
from algorithms.diff.emit_rust import write_rust_transform
from algorithms.diff.exact import (
    ExactTreeError,
    _snapshots_match,
    build_exact_plan,
    read_exact_regular_file,
    snapshot_tree_excluding,
)
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.model import (
    _file_fields,
    _plan_fields,
    _snapshot_files,
    reserved_windows_component,
)
from algorithms.diff.protected import protect_exact_plan
from algorithms.diff.provenance import SourcePinError, SourcePinEvidence
from algorithms.diff.source_binding import SourceBindingPolicy

# Source replay identity must not trust a mutable process-global hash hook.
_SHA256_FACTORY = hashlib.sha256
# Recipe admission must not trust a late-replaced host finite checker.
_NATIVE_ISFINITE = math.isfinite
# Policy checks must keep their pre-domain Python semantics after hook loading.
_NATIVE_ANY = builtins.any
_NATIVE_ALL = builtins.all
_NATIVE_LEN = builtins.len
_NATIVE_ISINSTANCE = builtins.isinstance
_NATIVE_BYTES_TYPE = builtins.bytes
_NATIVE_SET = builtins.set
_NATIVE_SORTED = builtins.sorted
_NATIVE_TUPLE = builtins.tuple
_NATIVE_LIST = builtins.list
_NATIVE_ENUMERATE = builtins.enumerate
_NATIVE_TYPE = builtins.type
_NATIVE_INT = builtins.int
_NATIVE_FLOAT = builtins.float
_NATIVE_STR = builtins.str
_NATIVE_BOOL = builtins.bool
_NATIVE_ATTRIBUTE_ERROR = builtins.AttributeError
_NATIVE_TYPE_ERROR = builtins.TypeError
_NATIVE_VALUE_ERROR = builtins.ValueError
_NATIVE_RUNTIME_ERROR = builtins.RuntimeError
_NATIVE_OS_ERROR = builtins.OSError
_NATIVE_UNICODE_ERROR = builtins.UnicodeError
_NATIVE_UNICODE_ENCODE_ERROR = builtins.UnicodeEncodeError
_NATIVE_PATH_TYPE = _NATIVE_TYPE(Path())
_NATIVE_OBJECT_NEW = object.__new__
_NATIVE_PATH_RAW_SLOT = cast(
    "MemberDescriptorType", PurePath.__dict__["_raw_paths"]
)
_NATIVE_PATH_STR_SLOT = cast("MemberDescriptorType", PurePath.__dict__["_str"])
_NATIVE_PATH_STRING = Path.__str__
# Native Path formatting, resolution, and equality still consult inherited
# PurePath getters and slotted descriptors. Reject changes before path use.
_PATH_PARSER_HOOK_NAMES = (
    "__getattribute__",
    "__getattr__",
    "__setattr__",
    "_str",
    "_raw_paths",
    "_drv",
    "_root",
    "drive",
    "root",
    "_str_normcase",
    "_str_normcase_cached",
    "_tail_cached",
    "_raw_path",
    "_tail",
    "_parse_path",
    "_format_parsed_parts",
    "_from_parsed_parts",
    "_from_parsed_string",
    "parser",
)
_NATIVE_PATH_CLASS_HOOKS = _NATIVE_TUPLE(
    (
        path_class,
        _NATIVE_TUPLE(
            (name, path_class.__dict__.get(name))
            for name in _PATH_PARSER_HOOK_NAMES
        ),
    )
    for path_class in _NATIVE_PATH_TYPE.__mro__
    if issubclass(path_class, PurePath)
)
_HOST_PATH_SEP = os.sep
_FILESYSTEM_ENCODING = sys.getfilesystemencoding()
_FILESYSTEM_ERRORS = sys.getfilesystemencodeerrors()
# Domain callbacks cannot redefine the host path containment verdict.
_NATIVE_PATH_EQ = Path.__eq__
_NATIVE_PATH_PARENT = cast("Callable[[Path], Path]", Path.parent.fget)
_NATIVE_PATH_RESOLVE = Path.resolve
_NATIVE_PATH_WITH_SEGMENTS = Path.with_segments
_NATIVE_PATH_FSPATH = Path.__fspath__
_NATIVE_PATH_GETATTRIBUTE = Path.__getattribute__
_NATIVE_PATH_NEW = Path.__new__
_NATIVE_PATH_INIT = Path.__init__
# The concrete PosixPath/WindowsPath class can override inherited methods.
_NATIVE_CONCRETE_FSPATH = _NATIVE_PATH_TYPE.__fspath__
_NATIVE_CONCRETE_STRING = _NATIVE_PATH_TYPE.__str__
_NATIVE_CONCRETE_WITH_SEGMENTS = _NATIVE_PATH_TYPE.with_segments
_NATIVE_CONCRETE_GETATTRIBUTE = _NATIVE_PATH_TYPE.__getattribute__
_NATIVE_CONCRETE_NEW = _NATIVE_PATH_TYPE.__new__
_NATIVE_CONCRETE_INIT = _NATIVE_PATH_TYPE.__init__
_NATIVE_OS_FSPATH = os.fspath
_NATIVE_OS_LSTAT = os.lstat
_NATIVE_OS_READLINK = os.readlink
_NATIVE_OS_GETCWD = os.getcwd
_NATIVE_STAT_ISLNK = stat.S_ISLNK
_NATIVE_REALPATH = os.path.realpath
# The original Path resolver still parses uncached raw components through
# mutable host parser names. Pin that dependency chain before resolving.
_NATIVE_HOST_PARSER = os.path
_NATIVE_HOST_SPLITROOT = os.path.splitroot
_NATIVE_HOST_SPLITDRIVE = os.path.splitdrive
_NATIVE_HOST_JOIN = os.path.join
_NATIVE_HOST_SEP = os.path.sep
_NATIVE_HOST_ALTSEP = os.path.altsep
_MAX_SHARES = 255
_NUL = "\x00"
_PARENT = ".."
_DOT = "."

if TYPE_CHECKING:
    from collections.abc import Callable

    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.model import FileRecord, TreeSnapshot


# A domain loader may execute consumer code. Pin the original hook storage
# before it can replace class getters after a validated bundle is returned.
_DOMAIN_SOURCE_HOOK_SLOT = cast(
    "MemberDescriptorType", DiffDomain.__dict__["validate_source_provenance"]
)
_DOMAIN_ORACLE_HOOK_SLOT = cast(
    "MemberDescriptorType", DiffDomain.__dict__["validate_authoring_oracle"]
)

# A domain callback can fabricate an exact native evidence instance without
# invoking its constructor, or replace its class validator before returning.
_NATIVE_SOURCE_EVIDENCE_VALIDATOR = cast(
    "Callable[[SourcePinEvidence], None]",
    SourcePinEvidence.__dict__["__post_init__"],
)


class TransformMode(StrEnum):
    """Runtime admission/materialization contract of a generated transform."""

    EXACT_BASELINE = "exact-baseline"
    COMPATIBLE = "compatible"


@dataclass(frozen=True, slots=True, init=False)
class DiffRecipe:
    """Declarative inputs and policy for one generated transform."""

    source_root: Path
    oracle_root: Path
    output_algorithm: Path
    profile: str
    mode: TransformMode
    domain_module: Path | None = None
    passthrough_roots: tuple[str, ...] = ()
    minimum_source_similarity: float = 0.50
    minimum_anchor_coverage: float = 0.66
    minimum_behavior_similarity: float = 0.80
    source_binding_threshold: float = 0.66
    source_binding_maximum_anchors: int = 127
    source_binding_minimum_files: int = 1
    ignore_comments_for_identity: bool = True
    ignore_formatting_for_identity: bool = True

    def __init__(
        self,
        source_root: Path,
        oracle_root: Path,
        output_algorithm: Path,
        profile: str,
        mode: TransformMode,
        domain_module: Path | None = None,
        passthrough_roots: tuple[str, ...] = (),
        minimum_source_similarity: float = 0.50,
        minimum_anchor_coverage: float = 0.66,
        minimum_behavior_similarity: float = 0.80,
        source_binding_threshold: float = 0.66,
        source_binding_maximum_anchors: int = 127,
        source_binding_minimum_files: int = 1,
        ignore_comments_for_identity: bool = True,
        ignore_formatting_for_identity: bool = True,
    ) -> None:
        """Store authored fields without dispatching late class setters."""
        _RECIPE_SLOTS["source_root"].__set__(self, source_root)
        _RECIPE_SLOTS["oracle_root"].__set__(self, oracle_root)
        _RECIPE_SLOTS["output_algorithm"].__set__(self, output_algorithm)
        _RECIPE_SLOTS["profile"].__set__(self, profile)
        _RECIPE_SLOTS["mode"].__set__(self, mode)
        _RECIPE_SLOTS["domain_module"].__set__(self, domain_module)
        _RECIPE_SLOTS["passthrough_roots"].__set__(self, passthrough_roots)
        _RECIPE_SLOTS["minimum_source_similarity"].__set__(
            self, minimum_source_similarity
        )
        _RECIPE_SLOTS["minimum_anchor_coverage"].__set__(
            self, minimum_anchor_coverage
        )
        _RECIPE_SLOTS["minimum_behavior_similarity"].__set__(
            self, minimum_behavior_similarity
        )
        _RECIPE_SLOTS["source_binding_threshold"].__set__(
            self, source_binding_threshold
        )
        _RECIPE_SLOTS["source_binding_maximum_anchors"].__set__(
            self, source_binding_maximum_anchors
        )
        _RECIPE_SLOTS["source_binding_minimum_files"].__set__(
            self, source_binding_minimum_files
        )
        _RECIPE_SLOTS["ignore_comments_for_identity"].__set__(
            self, ignore_comments_for_identity
        )
        _RECIPE_SLOTS["ignore_formatting_for_identity"].__set__(
            self, ignore_formatting_for_identity
        )


# Public recipes can be passed through consumer callbacks that replace their
# class descriptors. Read each original native field slot once before any
# validation or domain execution, then carry this independent immutable view
# through all subsequent authoring and publication steps.
_RECIPE_SLOTS = {
    name: cast("MemberDescriptorType", DiffRecipe.__dict__[name])
    for name in DiffRecipe.__slots__
}


class _RecipeSnapshot(NamedTuple):
    source_root: Path
    oracle_root: Path
    output_algorithm: Path
    profile: str
    mode: TransformMode
    domain_module: Path | None
    passthrough_roots: tuple[str, ...]
    minimum_source_similarity: float
    minimum_anchor_coverage: float
    minimum_behavior_similarity: float
    source_binding_threshold: float
    source_binding_maximum_anchors: int
    source_binding_minimum_files: int
    ignore_comments_for_identity: bool
    ignore_formatting_for_identity: bool


# A validated recipe snapshot must not dispatch class allocation or
# initialization hooks installed after the public module was imported.
_RECIPE_SNAPSHOT_NEW = _RecipeSnapshot.__new__
# Consumer callbacks may replace the namedtuple's field descriptors or
# __getattribute__ after initial recipe validation. Pin their identities so
# a later field read cannot redirect source/oracle identity or publication.
_NATIVE_RECIPE_SNAPSHOT_HOOKS = _NATIVE_TUPLE(
    (name, _RecipeSnapshot.__dict__.get(name))
    for name in (
        "__getattribute__",
        "__getattr__",
        "__getitem__",
        *_RecipeSnapshot._fields,
    )
)


type _RecipeLike = DiffRecipe | _RecipeSnapshot


def _require_native_recipe_snapshot_hooks() -> None:
    """Reject mutable accessors on the validated recipe snapshot.

    Raises:
        ValueError: Original snapshot field accessors have changed.

    """
    if _NATIVE_ANY(
        _RecipeSnapshot.__dict__.get(name) is not original
        for name, original in _NATIVE_RECIPE_SNAPSHOT_HOOKS
    ):
        message = "recipe snapshot hooks changed after validation"
        raise _NATIVE_VALUE_ERROR(message)


def _snapshot_recipe(recipe: DiffRecipe) -> _RecipeSnapshot:
    """Capture original stored fields without late recipe class dispatch."""

    def field(name: str) -> object:
        return cast("object", _RECIPE_SLOTS[name].__get__(recipe, DiffRecipe))

    return _RECIPE_SNAPSHOT_NEW(
        _RecipeSnapshot,
        source_root=cast("Path", field("source_root")),
        oracle_root=cast("Path", field("oracle_root")),
        output_algorithm=cast("Path", field("output_algorithm")),
        profile=cast("str", field("profile")),
        mode=cast("TransformMode", field("mode")),
        domain_module=cast("Path | None", field("domain_module")),
        passthrough_roots=cast("tuple[str, ...]", field("passthrough_roots")),
        minimum_source_similarity=(
            cast("float", field("minimum_source_similarity"))
        ),
        minimum_anchor_coverage=cast("float", field("minimum_anchor_coverage")),
        minimum_behavior_similarity=(
            cast("float", field("minimum_behavior_similarity"))
        ),
        source_binding_threshold=cast("float", field("source_binding_threshold")),
        source_binding_maximum_anchors=(
            cast("int", field("source_binding_maximum_anchors"))
        ),
        source_binding_minimum_files=(
            cast("int", field("source_binding_minimum_files"))
        ),
        ignore_comments_for_identity=(
            cast("bool", field("ignore_comments_for_identity"))
        ),
        ignore_formatting_for_identity=(
            cast("bool", field("ignore_formatting_for_identity"))
        ),
    )


class DiffGeneratorUnavailableError(RuntimeError):
    """Raised when a requested transform mode is not implemented yet."""


def _validate_fraction(name: str, value: object) -> None:
    if _NATIVE_TYPE(value) is _NATIVE_INT:
        # Only zero and one are integral fractions in [0, 1]. Reject other
        # integers before float conversion, which can raise OverflowError.
        if value not in {0, 1}:
            message = f"{name} must be a finite fraction in [0, 1]"
            raise _NATIVE_VALUE_ERROR(message)
        return
    if _NATIVE_TYPE(value) is not _NATIVE_FLOAT:
        message = f"{name} must be a finite numeric fraction in [0, 1]"
        raise _NATIVE_TYPE_ERROR(message)
    if not _NATIVE_ISFINITE(value) or value < 0.0 or value > 1.0:
        message = f"{name} must be a finite fraction in [0, 1], got {value}"
        raise _NATIVE_VALUE_ERROR(message)


def _validate_binding_count(
    name: str, value: object, maximum: int | None
) -> int:
    if _NATIVE_TYPE(value) is not _NATIVE_INT:
        message = f"{name} must use the exact integer type"
        raise _NATIVE_TYPE_ERROR(message)
    if value < 1 or (maximum is not None and value > maximum):
        limit = "positive" if maximum is None else f"in [1, {maximum}]"
        message = f"{name} must be {limit}"
        raise _NATIVE_VALUE_ERROR(message)
    return value


def _validate_binding_policy(recipe: _RecipeLike) -> None:
    if recipe.source_binding_threshold <= 0.0:
        message = "source_binding_threshold must be greater than zero"
        raise _NATIVE_VALUE_ERROR(message)
    maximum = _validate_binding_count(
        "source_binding_maximum_anchors",
        recipe.source_binding_maximum_anchors,
        _MAX_SHARES,
    )
    minimum = _validate_binding_count(
        "source_binding_minimum_files",
        recipe.source_binding_minimum_files,
        None,
    )
    if minimum > maximum:
        message = (
            "source_binding_minimum_files cannot exceed "
            "source_binding_maximum_anchors"
        )
        raise _NATIVE_VALUE_ERROR(message)


def _validate_path(value: object, name: str) -> None:
    # Reject Path subclasses before evaluating __fspath__ or .resolve:
    # either override can redirect authoring reads and output publication.
    if _NATIVE_TYPE(value) is not _NATIVE_PATH_TYPE:
        message = f"{name} must use exact pathlib Path"
        raise _NATIVE_TYPE_ERROR(message)
    # Python 3.14 Path may format its stored raw strings lazily through
    # os.fspath. Check the native raw components directly: a later module
    # hook cannot turn an unsafe path into benign preflight evidence.
    components = cast(
        "list[str]", _NATIVE_PATH_RAW_SLOT.__get__(value, PurePath)
    )
    if _NATIVE_TYPE(components) is not _NATIVE_LIST:
        message = f"{name} must use a native path component list"
        raise _NATIVE_TYPE_ERROR(message)
    for component in components:
        if _NATIVE_TYPE(component) is not _NATIVE_STR:
            message = f"{name} must use native string path components"
            raise _NATIVE_TYPE_ERROR(message)
        if _NUL in component:
            message = f"{name} must be a usable path without NUL"
            raise _NATIVE_VALUE_ERROR(message)
        try:
            _ = component.encode(
                _FILESYSTEM_ENCODING, errors=_FILESYSTEM_ERRORS
            )
        except _NATIVE_UNICODE_ERROR as error:
            message = f"{name} must be a usable path on this host"
            raise _NATIVE_VALUE_ERROR(message) from error


def _require_native_host_realpath(name: str) -> None:
    """Fail before invoking a host resolver replaced by consumer code.

    Raises:
        ValueError: Native host resolution no longer has its original identity.

    """
    if os.path.realpath is not _NATIVE_REALPATH:
        message = f"{name} could not be resolved safely: host realpath changed"
        raise _NATIVE_VALUE_ERROR(message)
    # Path.resolve calls realpath with a Path value. The original resolver
    # still delegates to these mutable conversion hooks before containment.
    if (
        os.path is not _NATIVE_HOST_PARSER
        or os.path.splitroot is not _NATIVE_HOST_SPLITROOT
        or os.path.splitdrive is not _NATIVE_HOST_SPLITDRIVE
        or os.path.join is not _NATIVE_HOST_JOIN
        or os.path.sep is not _NATIVE_HOST_SEP
        or os.path.altsep is not _NATIVE_HOST_ALTSEP
        or builtins.isinstance is not _NATIVE_ISINSTANCE
        or builtins.bytes is not _NATIVE_BYTES_TYPE
        or builtins.str is not _NATIVE_STR
        or builtins.len is not _NATIVE_LEN
        or _NATIVE_ANY(
            path_class.__dict__.get(name) is not original
            for path_class, hooks in _NATIVE_PATH_CLASS_HOOKS
            for name, original in hooks
        )
        or os.fspath is not _NATIVE_OS_FSPATH
        or os.lstat is not _NATIVE_OS_LSTAT
        or os.readlink is not _NATIVE_OS_READLINK
        or os.getcwd is not _NATIVE_OS_GETCWD
        or stat.S_ISLNK is not _NATIVE_STAT_ISLNK
        or Path.__fspath__ is not _NATIVE_PATH_FSPATH
        or Path.__str__ is not _NATIVE_PATH_STRING
        or Path.with_segments is not _NATIVE_PATH_WITH_SEGMENTS
        or Path.__getattribute__ is not _NATIVE_PATH_GETATTRIBUTE
        or Path.__new__ is not _NATIVE_PATH_NEW
        or Path.__init__ is not _NATIVE_PATH_INIT
        or _NATIVE_PATH_TYPE.__fspath__ is not _NATIVE_CONCRETE_FSPATH
        or _NATIVE_PATH_TYPE.__str__ is not _NATIVE_CONCRETE_STRING
        or _NATIVE_PATH_TYPE.with_segments is not _NATIVE_CONCRETE_WITH_SEGMENTS
        or _NATIVE_PATH_TYPE.__getattribute__ is not _NATIVE_CONCRETE_GETATTRIBUTE
        or _NATIVE_PATH_TYPE.__new__ is not _NATIVE_CONCRETE_NEW
        or _NATIVE_PATH_TYPE.__init__ is not _NATIVE_CONCRETE_INIT
        or builtins.type is not _NATIVE_TYPE
    ):
        message = f"{name} could not be resolved safely: host path hooks changed"
        raise _NATIVE_VALUE_ERROR(message)


def _resolve_recipe_path(path: Path, name: str) -> Path:
    _require_native_host_realpath(name)
    try:
        resolved = _NATIVE_PATH_RESOLVE(path)
    except (_NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR) as error:
        message = f"{name} could not be resolved safely"
        raise _NATIVE_VALUE_ERROR(message) from error
    _require_native_host_realpath(name)
    if _NATIVE_TYPE(resolved) is not _NATIVE_TYPE(path):
        message = f"{name} could not be resolved safely"
        raise _NATIVE_VALUE_ERROR(message)
    return resolved


def _native_path_contained(path: Path, root: Path) -> bool:
    """Compare resolved native ancestry without late Path equality/parents."""
    current = path
    while True:
        if _NATIVE_PATH_EQ(current, root):
            return True
        parent = _NATIVE_PATH_PARENT(current)
        if _NATIVE_PATH_EQ(parent, current):
            return False
        current = parent


def _validate_output_location(recipe: _RecipeLike) -> None:
    output = _resolve_recipe_path(recipe.output_algorithm, "output_algorithm")
    for name, root in (
        ("source_root", recipe.source_root),
        ("oracle_root", recipe.oracle_root),
    ):
        if _native_path_contained(output, _resolve_recipe_path(root, name)):
            message = f"output_algorithm must be outside {name}"
            raise _NATIVE_VALUE_ERROR(message)
    if recipe.domain_module is not None and _NATIVE_PATH_EQ(
        output, _resolve_recipe_path(recipe.domain_module, "domain_module")
    ):
        message = "output_algorithm must not overwrite domain_module"
        raise _NATIVE_VALUE_ERROR(message)


def _validate_recipe_paths(recipe: _RecipeLike) -> None:
    for value, name in (
        (recipe.source_root, "source_root"),
        (recipe.oracle_root, "oracle_root"),
        (recipe.output_algorithm, "output_algorithm"),
    ):
        _validate_path(value, name)
    if recipe.domain_module is not None:
        _validate_path(recipe.domain_module, "domain_module")
    _validate_output_location(recipe)


def _validate_profile_text(value: object) -> None:
    if _NATIVE_TYPE(value) is not _NATIVE_STR:
        message = "profile must use the exact string type"
        raise _NATIVE_TYPE_ERROR(message)
    if not value:
        message = "profile must be non-empty"
        raise _NATIVE_VALUE_ERROR(message)
    try:
        _ = value.encode("utf-8")
    except _NATIVE_UNICODE_ENCODE_ERROR as error:
        message = "profile must be portable UTF-8 text"
        raise _NATIVE_VALUE_ERROR(message) from error
    if _NUL in value:
        message = "profile must be portable UTF-8 text without NUL"
        raise _NATIVE_VALUE_ERROR(message)


def _validate_recipe_identity(recipe: _RecipeLike) -> None:
    _validate_profile_text(recipe.profile)
    if _NATIVE_TYPE(recipe.mode) is not TransformMode:
        message = "mode must use the exact TransformMode type"
        raise _NATIVE_TYPE_ERROR(message)


def _canonical_passthrough_component(component: str) -> bool:
    return (
        component not in {"", _DOT, _PARENT}
        and not reserved_windows_component(component)
    )


def _canonical_passthrough_root(root: str) -> bool:
    # ntpath's helpers and pathlib's methods consult late mutable host hooks.
    # Admit path labels lexically without executing those dependencies.
    try:
        _ = root.encode("utf-8")
    except _NATIVE_UNICODE_ENCODE_ERROR:
        return False
    return _NATIVE_ALL(
        _canonical_passthrough_component(part) for part in root.split("/")
    )


def _validate_passthrough_topology(roots: tuple[str, ...]) -> None:
    if roots != _NATIVE_TUPLE(_NATIVE_SORTED(_NATIVE_SET(roots))):
        message = "passthrough_roots must be canonical, sorted and disjoint"
        raise _NATIVE_VALUE_ERROR(message)
    for index, root in _NATIVE_ENUMERATE(roots):
        if _NATIVE_ANY(
            other.startswith(root + "/") for other in roots[index + 1 :]
        ):
            message = "passthrough_roots must be canonical, sorted and disjoint"
            raise _NATIVE_VALUE_ERROR(message)


def _validate_passthrough_roots(value: object) -> None:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = "passthrough_roots must use the exact immutable tuple type"
        raise _NATIVE_TYPE_ERROR(message)
    items = cast("tuple[object, ...]", value)
    if _NATIVE_ANY(_NATIVE_TYPE(root) is not _NATIVE_STR for root in items):
        message = "passthrough_roots entries must use the exact string type"
        raise _NATIVE_TYPE_ERROR(message)
    roots = cast("tuple[str, ...]", value)
    if _NATIVE_ANY(not root for root in roots):
        message = "passthrough_roots entries must be non-empty"
        raise _NATIVE_VALUE_ERROR(message)
    if _NATIVE_ANY(not _canonical_passthrough_root(root) for root in roots):
        message = "passthrough_roots must be canonical, sorted and disjoint"
        raise _NATIVE_VALUE_ERROR(message)
    _validate_passthrough_topology(roots)


def _validate_identity_flags(recipe: _RecipeLike) -> None:
    for name, value in (
        ("ignore_comments_for_identity", recipe.ignore_comments_for_identity),
        (
            "ignore_formatting_for_identity",
            recipe.ignore_formatting_for_identity,
        ),
    ):
        if _NATIVE_TYPE(value) is not _NATIVE_BOOL:
            message = f"{name} must be an exact boolean"
            raise _NATIVE_TYPE_ERROR(message)


def _validate_recipe(recipe: DiffRecipe) -> _RecipeSnapshot:
    _require_native_recipe_snapshot_hooks()
    if _NATIVE_TYPE(recipe) is not DiffRecipe:
        message = "diff recipe must use the exact DiffRecipe type"
        raise _NATIVE_TYPE_ERROR(message)
    snapshot = _snapshot_recipe(recipe)
    _validate_recipe_paths(snapshot)
    _validate_recipe_identity(snapshot)
    _validate_passthrough_roots(snapshot.passthrough_roots)
    _validate_identity_flags(snapshot)
    for name, value in (
        ("minimum_source_similarity", snapshot.minimum_source_similarity),
        ("minimum_anchor_coverage", snapshot.minimum_anchor_coverage),
        ("minimum_behavior_similarity", snapshot.minimum_behavior_similarity),
        ("source_binding_threshold", snapshot.source_binding_threshold),
    ):
        _validate_fraction(name, value)
    _validate_binding_policy(snapshot)
    return snapshot


def _native_source_identity_path(root: Path, relative: str) -> Path:
    """Append a canonical source label without mutable host path factories."""
    path = cast("Path", _NATIVE_OBJECT_NEW(_NATIVE_PATH_TYPE))
    components = cast(
        "list[str]", _NATIVE_PATH_RAW_SLOT.__get__(root, PurePath)
    )
    _NATIVE_PATH_RAW_SLOT.__set__(path, [*components, relative])
    # pathlib's lazy string formatting invokes process-global os.fspath.
    # Cache the admitted lexical child spelling without late host hooks.
    root_spelling = _NATIVE_PATH_STRING(root)
    host_relative = relative.replace("/", _HOST_PATH_SEP)
    if root_spelling == ".":
        spelling = host_relative
    elif root_spelling.endswith(_HOST_PATH_SEP) or (
        _HOST_PATH_SEP == "\\" and root_spelling.endswith(":")
    ):
        spelling = root_spelling + host_relative
    else:
        spelling = root_spelling + _HOST_PATH_SEP + host_relative
    _NATIVE_PATH_STR_SLOT.__set__(path, spelling)
    return path


def _read_exact_identity_file(path: Path, record: FileRecord) -> bytes:
    replay = read_exact_regular_file(path, "exact source identity")
    relative_path, expected_digest, expected_size = _file_fields(record)
    if (
        _NATIVE_LEN(replay) != expected_size
        or _SHA256_FACTORY(replay).hexdigest() != expected_digest
    ):
        message = f"exact source identity changed after planning: {relative_path}"
        raise ExactTreeError(message)
    return replay


def _raw_exact_identity(
    recipe: _RecipeLike,
    source: TreeSnapshot,
) -> IdentityTree:
    files: dict[str, bytes] = {}
    for record in _snapshot_files(source):
        relative = _file_fields(record)[0]
        files[relative] = _read_exact_identity_file(
            _native_source_identity_path(recipe.source_root, relative),
            record,
        )
    return identity_tree(files)


def _write_exact_algorithm(recipe: _RecipeLike) -> None:
    _require_native_recipe_snapshot_hooks()
    exact = build_exact_plan(
        recipe.source_root,
        recipe.oracle_root,
        passthrough_roots=recipe.passthrough_roots,
    )
    _require_native_recipe_snapshot_hooks()
    # Domain callbacks can replace ExactAuthoringPlan class getters after
    # creation; only the original plan slots can authorize post-protection
    # input drift checks and source-bound key material.
    planned_source, planned_target, _, _ = _plan_fields(exact)
    identity = _raw_exact_identity(recipe, planned_source)
    _require_native_recipe_snapshot_hooks()
    replayed_source = snapshot_tree_excluding(
        recipe.source_root, recipe.passthrough_roots
    )
    if not _snapshots_match(replayed_source, planned_source):
        message = "exact source tree changed after identity replay"
        raise ExactTreeError(message)
    policy = SourceBindingPolicy(
        threshold_fraction=recipe.source_binding_threshold,
        maximum_anchors=recipe.source_binding_maximum_anchors,
        minimum_anchor_files=recipe.source_binding_minimum_files,
        anchor_policy=AnchorPolicy(),
    )
    context = f"{recipe.profile}:exact-baseline-v1".encode()
    protected = protect_exact_plan(
        exact,
        identity,
        binding_policy=policy,
        context=context,
    )
    _require_native_recipe_snapshot_hooks()
    # Protection can take time; reject persistent input drift before emitting
    # a distributable transform bound to a stale source or oracle snapshot.
    for name, root, expected in (
        ("source", recipe.source_root, planned_source),
        ("oracle", recipe.oracle_root, planned_target),
    ):
        if not _snapshots_match(
            snapshot_tree_excluding(root, recipe.passthrough_roots), expected
        ):
            message = f"exact {name} tree changed during payload protection"
            raise ExactTreeError(message)
    _require_native_recipe_snapshot_hooks()
    write_rust_transform(
        protected,
        f"{recipe.profile}-exact-baseline-v1",
        recipe.output_algorithm,
    )


def _require_source_provenance_evidence(value: object) -> None:
    """Revalidate the original native receipt after consumer callbacks.

    Raises:
        DomainContractError: Evidence is foreign, incomplete, or inconsistent.

    """
    if _NATIVE_TYPE(value) is not SourcePinEvidence:
        message = "domain source provenance hook must return SourcePinEvidence"
        raise DomainContractError(message)
    try:
        _NATIVE_SOURCE_EVIDENCE_VALIDATOR(value)
    except (
        SourcePinError,
        _NATIVE_ATTRIBUTE_ERROR,
        _NATIVE_TYPE_ERROR,
    ) as error:
        message = "domain source provenance evidence is invalid"
        raise DomainContractError(message) from error


def _preflight_domain(recipe: _RecipeLike) -> None:
    if recipe.domain_module is None:
        message = "domain preflight requires a domain module"
        raise DiffGeneratorUnavailableError(message)
    domain = load_diff_domain(recipe.domain_module)
    _require_native_recipe_snapshot_hooks()
    if _NATIVE_TYPE(domain) is not DiffDomain:
        message = "domain loader must return exact DiffDomain"
        raise DomainContractError(message)
    source_hook = cast(
        "Callable[[Path], SourcePinEvidence]",
        _DOMAIN_SOURCE_HOOK_SLOT.__get__(domain, DiffDomain),
    )
    oracle_hook = cast(
        "Callable[[Path], None]",
        _DOMAIN_ORACLE_HOOK_SLOT.__get__(domain, DiffDomain),
    )
    _require_source_provenance_evidence(source_hook(recipe.source_root))
    _require_native_recipe_snapshot_hooks()
    oracle_result = oracle_hook(recipe.oracle_root)
    _require_native_recipe_snapshot_hooks()
    if oracle_result is not None:
        message = "domain oracle preflight hook must return None"
        raise DomainContractError(message)


def write_algorithm(recipe: DiffRecipe) -> None:
    """Generate one requested transform mode or fail closed.

    Exact-baseline mode is implemented and may exclude explicit passthrough
    roots from its static source snapshot. Domain-aware recipes execute source
    provenance and oracle preflights before either mode continues.
    Compatible mode executes those preflights and then remains unavailable.
    It then remains unavailable until compatible protected serialization and
    runtime emission are complete.

    Raises:
        DiffGeneratorUnavailableError: Compatible emission is not implemented.

    """
    recipe_view = _validate_recipe(recipe)
    if recipe_view.domain_module is not None:
        _preflight_domain(recipe_view)
        _require_native_recipe_snapshot_hooks()
    elif recipe_view.mode is TransformMode.COMPATIBLE:
        message = "compatible generation requires a domain module"
        raise DiffGeneratorUnavailableError(message)
    if recipe_view.mode is TransformMode.EXACT_BASELINE:
        # Domain code runs after recipe preflight and may replace host hooks.
        _require_native_host_realpath("output_algorithm")
        _write_exact_algorithm(recipe_view)
        return
    message = (
        "compatible source-bound Rust emission is not implemented; "
        "preflight passed but no output was materialized"
    )
    raise DiffGeneratorUnavailableError(message)
