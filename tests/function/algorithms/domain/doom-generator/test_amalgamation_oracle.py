# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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
#   - Synthetic tests for the DOOM single-TU oracle builder.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for the DOOM single-TU oracle builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from algorithms.doom.generator import amalgamation_oracle as oracle
import pytest

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED_UNITS = 4
MISSING_TERMINAL = "missing terminal translation units"
SYSTEM_INCLUDE = "#include <stdint.h>"
QUOTED_INCLUDE = '#include "'
P_SPEC_ANIM = "__doom_tu_p_spec_anim_t"
WI_STUFF_ANIM = "__doom_tu_wi_stuff_anim_t"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _source(*lines: str) -> str:
    return "\n".join((*lines, ""))


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _required_headers(root: Path) -> None:
    _ = _write(
        root,
        "dstrings.h",
        _source(
            "#ifndef __DSTRINGS__",
            "#define __DSTRINGS__",
            "#define TXT value",
            "#endif",
        ),
    )
    _ = _write(
        root,
        "shared.h",
        _source(
            "#ifndef SHARED_H",
            "#define SHARED_H",
            '#include "cycle.h"',
            "#include <stdint.h>",
            "int shared;",
            "#endif",
        ),
    )
    _ = _write(
        root,
        "cycle.h",
        _source(
            "#ifndef CYCLE_H",
            "#define CYCLE_H",
            '#include "shared.h"',
            "int cycle;",
            "#endif",
        ),
    )


def _accepted_tree(root: Path) -> None:
    _required_headers(root)
    _ = _write(root, "p_spec.c", '#include "shared.h"\ntypedef int anim_t;\n')
    _ = _write(root, "wi_stuff.c", '#include "shared.h"\ntypedef int anim_t;\n')
    _ = _write(root, "m_string.c", '#include "shared.h"\nint string_unit;\n')
    _ = _write(
        root,
        "d_language.c",
        '#include "dstrings.h"\nint language_unit;\n',
    )


def test_build_amalgamation_is_deterministic_and_isolates_units(
    tmp_path: Path,
) -> None:
    """Produce stable bytes while preserving separate-TU private identities."""
    _accepted_tree(tmp_path)

    first, first_stats = oracle.build_amalgamation(tmp_path)
    second, second_stats = oracle.build_amalgamation(tmp_path)
    output = first.decode("utf-8")

    _expect(first == second, "amalgamation bytes changed between runs")
    _expect(
        first_stats == second_stats,
        "amalgamation statistics changed between runs",
    )
    _expect(
        first_stats.translation_units == EXPECTED_UNITS,
        "unexpected translation-unit count",
    )
    _expect(P_SPEC_ANIM in output, "p_spec private type was not isolated")
    _expect(WI_STUFF_ANIM in output, "wi_stuff private type was not isolated")
    _expect(
        output.index("Translation unit: p_spec.c")
        < output.index("Translation unit: m_string.c"),
        "terminal translation unit was not ordered last",
    )
    _expect(
        output.index("Translation unit: m_string.c")
        < output.index("Translation unit: d_language.c"),
        "language translation unit was not final",
    )


def test_build_amalgamation_flattens_project_headers_once(
    tmp_path: Path,
) -> None:
    """Embed guarded project headers once while retaining system includes."""
    _accepted_tree(tmp_path)

    encoded, stats = oracle.build_amalgamation(tmp_path)
    output = encoded.decode("utf-8")

    _expect(output.count("int shared;") == 1, "shared header was duplicated")
    _expect(output.count("int cycle;") == 1, "cycle header was duplicated")
    _expect(SYSTEM_INCLUDE in output, "system include was flattened")
    _expect(QUOTED_INCLUDE not in output, "project include survived")
    _expect(stats.cycle_elisions == 1, "guarded include cycle was not elided")
    _expect(stats.deduplicated_headers > 0, "duplicate headers were not elided")


def test_build_amalgamation_rejects_missing_terminal_unit(
    tmp_path: Path,
) -> None:
    """Reject an incomplete macro-destructive terminal ordering."""
    _ = _write(tmp_path, "dstrings.h", "#define TXT value\n")
    _ = _write(tmp_path, "alpha.c", "int alpha;\n")

    with pytest.raises(oracle.DoomAmalgamationError, match=MISSING_TERMINAL):
        _ = oracle.build_amalgamation(tmp_path)
