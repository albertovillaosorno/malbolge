# File:
#   - generate.py
# Path:
#   - algorithms/doom/quality/languages/generate.py
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
#   - Generate module.
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

"""Generate module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent / "in" / "doom" / "linuxdoom-1.10"
SOURCE = ROOT / "d_englsh.h"

_DOUBLE_QUOTE = '"'
_BACKSLASH = "\\"
_FORMAT_MARKER = "%"
_FORMAT_REPLACEMENT = "#"
_MODE_LEET = "leet"
_MODE_MALBOLGE = "malbolge"
_PRINTABLE_MIN = 33
_PRINTABLE_MAX = 126

STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"')
_FORMAT_PATTERN_PARTS = (
    r"%(?:[-+ #0]*)(?:\d+|\*)?(?:\.(?:\d+|\*))?",
    r"(?:hh|h|ll|l|j|z|t|L)?[diuoxXfFeEgGaAcspn%]",
)
FORMAT_RE = re.compile("".join(_FORMAT_PATTERN_PARTS))

LEET = str.maketrans({
    "a": "4",
    "A": "4",
    "b": "8",
    "B": "8",
    "e": "3",
    "E": "3",
    "g": "9",
    "G": "9",
    "i": "1",
    "I": "1",
    "o": "0",
    "O": "0",
    "s": "5",
    "S": "5",
    "t": "7",
    "T": "7",
    "z": "2",
    "Z": "2",
})

# Canonical printable-character encryption table used by Malbolge. Generated
# text uses this table but replaces a generated '%' with '#' so translated
# prose cannot accidentally create a new printf conversion.
_MALBOLGE_XLAT2_PREFIX = (
    "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|"
)
_MALBOLGE_XLAT2_SUFFIX = "jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@"
MALBOLGE_XLAT2 = _MALBOLGE_XLAT2_PREFIX + _MALBOLGE_XLAT2_SUFFIX


class UnknownLanguageModeError(ValueError):
    """Raised when a generated language variant selects an unknown mode."""

    def __init__(self, mode: str) -> None:
        """Describe the unsupported generation mode."""
        message = f"Unknown language generation mode: {mode}"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class LanguageVariant:
    """One deterministic generated DOOM language-header variant."""

    description: str
    filename: str
    guard: str
    mode: str


def _preserved_fragment(inner: str, index: int) -> tuple[str, int] | None:
    result: tuple[str, int] | None = None
    if inner[index] == _BACKSLASH and index + 1 < len(inner):
        result = (inner[index : index + 2], index + 2)
    elif inner[index] == _FORMAT_MARKER:
        match = FORMAT_RE.match(inner, index)
        if match is not None:
            result = (match.group(0), match.end())
    return result


def _translated_character(character: str, mode: str) -> str:
    if mode == _MODE_LEET:
        return character.translate(LEET)
    if mode != _MODE_MALBOLGE:
        raise UnknownLanguageModeError(mode)
    codepoint = ord(character)
    if not _PRINTABLE_MIN <= codepoint <= _PRINTABLE_MAX:
        return character
    mapped = MALBOLGE_XLAT2[codepoint - _PRINTABLE_MIN]
    return _FORMAT_REPLACEMENT if mapped == _FORMAT_MARKER else mapped


def _escaped_character(character: str) -> str:
    if character == _BACKSLASH:
        return _BACKSLASH * 2
    if character == _DOUBLE_QUOTE:
        return _BACKSLASH + _DOUBLE_QUOTE
    return character


def transform_literal(raw: str, mode: str) -> str:
    """Translate one C string while preserving escapes and printf formats.

    Returns:
        A quoted C string literal with deterministic translated prose.

    """
    inner = raw[1:-1]
    output: list[str] = []
    index = 0
    while index < len(inner):
        preserved = _preserved_fragment(inner, index)
        if preserved is not None:
            fragment, index = preserved
            output.append(fragment)
            continue
        mapped = _translated_character(inner[index], mode)
        output.append(_escaped_character(mapped))
        index += 1
    return _DOUBLE_QUOTE + "".join(output) + _DOUBLE_QUOTE


def generate(variant: LanguageVariant) -> None:
    """Write one generated language header from canonical English source."""
    text = SOURCE.read_text(encoding="utf-8")
    text = text.replace(
        "English language support (default).",
        variant.description,
    )
    text = text.replace("__D_ENGLSH__", variant.guard)
    text = STRING_RE.sub(
        lambda match: transform_literal(match.group(0), variant.mode),
        text,
    )
    _ = (ROOT / variant.filename).write_text(
        text,
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    """Generate the reviewed leetspeak and Malbolge text variants."""
    variants = (
        LanguageVariant(
            description="Leetspeak language support (generated from English).",
            filename="d_1337spk.h",
            guard="__D_1337SPK__",
            mode=_MODE_LEET,
        ),
        LanguageVariant(
            description=(
                "Malbolge textual language support (generated from English)."
            ),
            filename="d_malbolge.h",
            guard="__D_MALBOLGE__",
            mode=_MODE_MALBOLGE,
        ),
    )
    for variant in variants:
        generate(variant)


if __name__ == "__main__":
    main()
