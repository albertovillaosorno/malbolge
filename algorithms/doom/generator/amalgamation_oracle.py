# File:
#   - amalgamation_oracle.py
# Path:
#   - algorithms/doom/generator/amalgamation_oracle.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Build the local validated DOOM single-translation-unit authoring oracle.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Build the local validated DOOM single-translation-unit authoring oracle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
QUALITY_CODE_ROOT = (
    _REPOSITORY_ROOT
    / "algorithms"
    / "doom"
    / "quality"
    / "out"
    / "doom_fixed"
    / "linuxdoom-1.10"
)
AMALGAMATION_ORACLE = (
    _REPOSITORY_ROOT
    / "algorithms"
    / "doom"
    / "amalgamate"
    / "in"
    / "oracle"
    / "doom.c"
)

_STRING_UNIT = "m_string.c"
_LANGUAGE_UNIT = "d_language.c"
_STATUS_BAR_UNIT = "st_lib.c"
_HEADER_SUFFIX = ".h"
_TERMINAL_UNITS = (_STRING_UNIT, _LANGUAGE_UNIT)
_DSTRINGS_GUARD = "__DSTRINGS__"
_INCLUDE_PATTERN = re.compile(r'^(\s*#\s*include\s*)"([^"]+)"(.*)$')
_DEFINE_PATTERN = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\b", re.MULTILINE)

# Only true main-file private collisions belong here. Header static-inline
# helpers intentionally remain shared once their guarded header is embedded.
_PRIVATE_RENAMES: dict[str, tuple[str, ...]] = {
    "am_map.c": ("plr",),
    "g_game.c": ("mousex", "mousey"),
    "hu_stuff.c": ("plr",),
    "i_music.c": ("ReadU16LE",),
    "i_sound.c": ("ReadU16LE", "channels"),
    "m_fixed.c": ("FixedMagnitude",),
    "p_enemy.c": ("RandomAngleJitter", "SignedAngleDelta"),
    "p_mobj.c": ("RandomAngleJitter",),
    "p_pspr.c": ("RandomAngleJitter", "SignedAngleDelta"),
    "p_spec.c": ("anim_t", "anims"),
    "r_main.c": ("FixedMagnitude",),
    "s_sound.c": ("channels",),
    "wi_stuff.c": ("anim_t", "anims"),
}


class DoomAmalgamationError(RuntimeError):
    """Raised when deterministic single-TU construction cannot stay safe."""


@dataclass(frozen=True, slots=True)
class AmalgamationStats:
    """Deterministic construction statistics for one local oracle."""

    translation_units: int
    private_bindings: int
    unique_headers: int
    expanded_includes: int
    deduplicated_headers: int
    cycle_elisions: int
    output_bytes: int
    output_lines: int


@dataclass(slots=True)
class _FlattenState:
    emitted_headers: set[Path]
    expanded_includes: int = 0
    deduplicated_headers: int = 0
    cycle_elisions: int = 0


def _require_regular(path: Path, description: str) -> None:
    if path.is_symlink() or not path.is_file():
        message = f"{description} must be a regular file: {path}"
        raise DoomAmalgamationError(message)


def _translation_units(code_root: Path) -> tuple[Path, ...]:
    if not code_root.is_dir():
        message = f"missing accepted DOOM code root: {code_root}"
        raise DoomAmalgamationError(message)
    units = tuple(sorted(code_root.glob("*.c"), key=lambda path: path.name))
    if not units:
        message = f"no C translation units found under: {code_root}"
        raise DoomAmalgamationError(message)
    for path in units:
        _require_regular(path, "DOOM translation unit")
    names = {path.name for path in units}
    missing_terminal = tuple(
        name for name in _TERMINAL_UNITS if name not in names
    )
    if missing_terminal:
        message = f"missing terminal translation units: {missing_terminal!r}"
        raise DoomAmalgamationError(message)
    return units


def _ordered_units(units: tuple[Path, ...]) -> tuple[Path, ...]:
    terminal = set(_TERMINAL_UNITS)
    ordinary = tuple(path for path in units if path.name not in terminal)
    by_name = {path.name: path for path in units}
    return ordinary + tuple(by_name[name] for name in _TERMINAL_UNITS)


def _dstrings_aliases(code_root: Path) -> tuple[str, ...]:
    path = code_root / "dstrings.h"
    _require_regular(path, "dstrings alias header")
    names = set(_DEFINE_PATTERN.findall(path.read_text(encoding="utf-8")))
    names.discard(_DSTRINGS_GUARD)
    if not names:
        message = "dstrings.h exposes no aliases to isolate before d_language.c"
        raise DoomAmalgamationError(message)
    return tuple(sorted(names))


def _private_name(file_name: str, identifier: str) -> str:
    stem = Path(file_name).stem
    return f"__doom_tu_{stem}_{identifier}"


def _unit_wrapper_lines(
    unit: Path,
    *,
    dstrings_aliases: tuple[str, ...],
) -> tuple[str, ...]:
    lines: list[str] = [f"// Translation unit: {unit.name}"]
    if unit.name == _STATUS_BAR_UNIT:
        lines.append("#undef BG")
    if unit.name == _LANGUAGE_UNIT:
        lines.append("// Restore d_language.c's separate-TU macro environment.")
        lines.extend(f"#undef {name}" for name in dstrings_aliases)
    private = _PRIVATE_RENAMES.get(unit.name, ())
    lines.extend(
        f"#define {name} {_private_name(unit.name, name)}" for name in private
    )
    lines.append(f'#include "{unit.name}"')
    lines.extend(f"#undef {name}" for name in reversed(private))
    lines.append("")
    return tuple(lines)


def _wrapper_text(code_root: Path) -> tuple[str, int, int]:
    units = _ordered_units(_translation_units(code_root))
    aliases = _dstrings_aliases(code_root)
    lines = [
        "// Canonical DOOM single-translation-unit authoring oracle.",
        "// Generated from accepted normalized multi-file source.",
        "// Project-local headers are embedded; system headers remain",
        "// external.",
        "// Source notices remain embedded below.",
        "",
    ]
    for unit in units:
        lines.extend(_unit_wrapper_lines(unit, dstrings_aliases=aliases))
    private_bindings = sum(
        len(_PRIVATE_RENAMES.get(unit.name, ())) for unit in units
    )
    return "\n".join(lines) + "\n", len(units), private_bindings


def _relative_project_path(code_root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(code_root)
    except ValueError as exc:
        message = f"project include escapes accepted code root: {path}"
        raise DoomAmalgamationError(message) from exc
    return relative.as_posix()


def _project_include(base: Path, name: str, code_root: Path) -> Path:
    target = (base / name).resolve()
    _ = _relative_project_path(code_root, target)
    _require_regular(target, "project include")
    return target


@dataclass(frozen=True, slots=True)
class _ExpansionFrame:
    parent_name: str
    base: Path
    active: tuple[Path, ...]


@dataclass(slots=True)
class _Flattener:
    code_root: Path
    state: _FlattenState

    def expand(self, text: str, frame: _ExpansionFrame) -> list[str]:
        output: list[str] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            output.extend(self._expand_line(line_number, line, frame))
        return output

    def _expand_line(
        self,
        line_number: int,
        line: str,
        frame: _ExpansionFrame,
    ) -> list[str]:
        match = _INCLUDE_PATTERN.match(line)
        if match is None:
            return [line]
        return self._expand_project_include(
            line_number,
            match.group(2),
            frame,
        )

    def _expand_project_include(
        self,
        line_number: int,
        include_name: str,
        frame: _ExpansionFrame,
    ) -> list[str]:
        target = _project_include(frame.base, include_name, self.code_root)
        relative = _relative_project_path(self.code_root, target)
        if target in frame.active:
            self.state.cycle_elisions += 1
            return [f"/* guarded recursive include elided: {relative} */"]
        is_header = target.suffix.lower() == _HEADER_SUFFIX
        if is_header and target in self.state.emitted_headers:
            self.state.deduplicated_headers += 1
            return [f"/* duplicate project header elided: {relative} */"]
        if is_header:
            self.state.emitted_headers.add(target)
        self.state.expanded_includes += 1
        nested = _ExpansionFrame(
            parent_name=relative,
            base=target.parent,
            active=(*frame.active, target),
        )
        output = [f'#line 1 "{relative}"']
        output.extend(self.expand(target.read_text(encoding="utf-8"), nested))
        output.append(f'#line {line_number + 1} "{frame.parent_name}"')
        return output


def _remaining_project_includes(text: str) -> tuple[str, ...]:
    return tuple(
        line
        for line in text.splitlines()
        if _INCLUDE_PATTERN.match(line) is not None
    )


def _flatten_wrapper(
    code_root: Path, wrapper: str
) -> tuple[str, _FlattenState]:
    state = _FlattenState(emitted_headers=set())
    body = _Flattener(code_root=code_root, state=state).expand(
        wrapper,
        _ExpansionFrame(parent_name="doom.c", base=code_root, active=()),
    )
    header = (
        "// Canonical DOOM single-translation-unit authoring oracle.",
        "// Project headers are embedded once; system headers remain external.",
        "// This file remains local authoring evidence; source provenance",
        "// is embedded.",
        "",
        '#line 1 "doom.c"',
    )
    output = "\n".join((*header, *body)) + "\n"
    remaining = _remaining_project_includes(output)
    if remaining:
        message = f"unflattened project includes remain: {remaining[:3]!r}"
        raise DoomAmalgamationError(message)
    return output, state


def _amalgamation_stats(
    output: str,
    state: _FlattenState,
    *,
    unit_count: int,
    private_bindings: int,
) -> AmalgamationStats:
    return AmalgamationStats(
        translation_units=unit_count,
        private_bindings=private_bindings,
        unique_headers=len(state.emitted_headers),
        expanded_includes=state.expanded_includes,
        deduplicated_headers=state.deduplicated_headers,
        cycle_elisions=state.cycle_elisions,
        output_bytes=len(output.encode("utf-8")),
        output_lines=output.count("\n"),
    )


def build_amalgamation(code_root: Path) -> tuple[bytes, AmalgamationStats]:
    """Build the deterministic local single-TU oracle from accepted DOOM source.

    Returns:
        UTF-8 oracle bytes and deterministic construction statistics.

    """
    resolved_root = code_root.resolve()
    wrapper, unit_count, private_bindings = _wrapper_text(resolved_root)
    output, state = _flatten_wrapper(resolved_root, wrapper)
    stats = _amalgamation_stats(
        output,
        state,
        unit_count=unit_count,
        private_bindings=private_bindings,
    )
    return output.encode("utf-8"), stats


def write_amalgamation_oracle(
    code_root: Path = QUALITY_CODE_ROOT,
    output_path: Path = AMALGAMATION_ORACLE,
) -> AmalgamationStats:
    """Write the ignored local oracle atomically and return construction stats.

    Returns:
        Deterministic statistics for the written oracle.

    """
    data, stats = build_amalgamation(code_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    _ = temporary.write_bytes(data)
    _ = temporary.replace(output_path)
    return stats


def _format_stats(stats: AmalgamationStats) -> Iterable[str]:
    yield f"translation_units={stats.translation_units}"
    yield f"private_bindings={stats.private_bindings}"
    yield f"unique_headers={stats.unique_headers}"
    yield f"expanded_includes={stats.expanded_includes}"
    yield f"deduplicated_headers={stats.deduplicated_headers}"
    yield f"cycle_elisions={stats.cycle_elisions}"
    yield f"output_bytes={stats.output_bytes}"
    yield f"output_lines={stats.output_lines}"


def main() -> int:
    """Write the local oracle and report construction statistics.

    Returns:
        Process status code.

    """
    stats = write_amalgamation_oracle()
    _ = sys.stdout.write("\n".join(_format_stats(stats)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
