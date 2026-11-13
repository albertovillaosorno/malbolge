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
#   - Source-proven, guest-byte-dependent C if with equivalent output effects.
# - Must-Not:
#   - Guess guest data or erase conditional input, storage, or exit effects.
# - Allows:
#   - Inputs: pinned C/Clang evidence and successful guest input bytes.
#   - Outputs: normative VM parity or explicit rejection without publication.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - Guest branching supports general runtime-dependent C control flow.
# - Merge-When:
#   - Typed effect-equivalence proofs replace bounded source-C selection.
# - Summary:
#   - Equivalent pure byte output traces may eliminate a live-byte C branch.
# - Description:
#   - Verify full C streams and reject source/AST/side-effect forgeries.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Dependent branches with differing effects refuse publication.

"""Real C-to-Malbolge parity for dynamic guards with identical effects."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_guest_byte_total_if_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def source(guard: str = "current & 1", *, bound: int = 3) -> str:
    """Retain counted induction, continue, two branches and real byte I/O."""
    original = previous.source(guard, bound=bound)
    old = "                putchar(getchar());\n"
    assert old in original
    # jig-ignore-next-line: pinned Ruff formats at 88 columns
    return original.replace(old, "                putchar((current + 0) & 255);\n", 1)


class GuestByteEquivalentIfCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C frontend, adapter, layout and VM required")

    # jig-ignore-next-line: pinned Ruff formats at 88 columns
    def test_real_byte_dependent_branch_has_identical_guest_effects(self) -> None:
        """Both C arms write the same live byte without a host guess."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "dynamic-equivalent.c"
            guest = root / "dynamic-equivalent.malbolge"
            _ = program.write_text(source(), encoding="utf-8")
            result = COMPILE(program, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            boundaries = (
                bytes((0, 255)),
                bytes((1, 254)),
                bytes((127, 128)),
                bytes((128, 127)),
                bytes((255, 0)),
            )
            seeded = (
                # jig-ignore-next-line: pinned Ruff formats at 88 columns
                hashlib.shake_256(bytes((253, index))).digest(2)
                for index in range(16)
            )
            # jig-ignore-next-line: pinned Ruff formats at 88 columns
            strata = (bytes((index, index ^ 255)) for index in range(0, 256, 16))
            for data in (*boundaries, *seeded, *strata):
                with self.subTest(data=data):
                    result = RUN(guest, data)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    # jig-ignore-next-line: pinned Ruff formats at 88 columns
                    self.assertEqual(result.stdout, bytes((data[0],) * 4 + (data[1],)))
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:8\n")

    def test_another_dependent_guard_and_zero_trip_match_guest(self) -> None:
        """A pure comparison also preserves identity with no loop iterations."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "zero-trip.c"
            guest = root / "zero-trip.malbolge"
            # jig-ignore-next-line: pinned Ruff formats at 88 columns
            _ = program.write_text(source("current >= 128", bound=0), encoding="utf-8")
            compiled = COMPILE(program, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((255, 0))):
                result = RUN(guest, data)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, bytes((data[0], data[1])))
                self.assertEqual(result.stderr, b"malbolge-steps-v1:5\n")

    def test_two_output_effects_in_both_arms_match_guest(self) -> None:
        """Each dynamic C arm writes the same source-proven byte twice."""
        original = source("current >= 128", bound=1)
        old = (
            "                putchar(current);\n"
            "            } else {\n"
            "                putchar((current + 0) & 255);"
        )
        new = (
            "                putchar(current);\n"
            "                putchar((current | 0));\n"
            "            } else {\n"
            "                putchar((current ^ 0));\n"
            "                putchar((current + 0) & 255);"
        )
        self.assertIn(old, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "two-effects.c"
            guest = root / "two-effects.malbolge"
            _ = program.write_text(original.replace(old, new), encoding="utf-8")
            compiled = COMPILE(program, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255)),
                bytes((127, 128)),
                bytes((128, 127)),
                bytes((255, 0)),
            ):
                with self.subTest(data=data):
                    vm = RUN(guest, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    # jig-ignore-next-line: pinned Ruff formats at 88 columns
                    self.assertEqual(vm.stdout, bytes((data[0],) * 3 + (data[1],)))
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:7\n")

    def test_non_equivalent_or_effectful_guards_refuse(self) -> None:
        """Equal output count is not a substitute for effect equivalence."""
        invalid = (
            previous.source("current & 1"),
            source("getchar() & 1"),
            source("current & 1 || getchar() >= 0"),
            source().replace("(current + 0) & 255", "current + 1"),
            # jig-ignore-next-line: pinned Ruff formats at 88 columns
            source().replace("putchar((current + 0) & 255)", "putchar(getchar())"),
            source().replace(
                "putchar((current + 0) & 255)", "putchar(putchar(current))"
            ),
            source().replace(
                "putchar((current + 0) & 255)",
                "putchar(current);\n                putchar(current)",
            ),
            source().replace(
                # jig-ignore-next-line: pinned Ruff formats at 88 columns
                " else {\n                putchar((current + 0) & 255);\n            }",
                "",
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, text in enumerate(invalid):
                with self.subTest(index=index):
                    program = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    _ = program.write_text(text, encoding="utf-8")
                    result = COMPILE(program, guest)
                    self.assertNotEqual(result.returncode, 0, text)
                    self.assertFalse(guest.exists())

    def test_forged_ast_and_original_source_refuse(self) -> None:
        """The dynamic guard and both arms require authentic C evidence."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "original.c"
            original = source("current & 1")
            _ = program.write_text(original, encoding="utf-8")
            normalized = NORMALIZED(program)
            for field in ("operation", "parent", "literal", "span"):
                with self.subTest(field=field):
                    forged = copy.deepcopy(normalized)
                    nodes = cast("list[dict[str, object]]", forged["nodes"])
                    guard = next(
                        n
                        for n in nodes
                        if n.get("operation") == "&"
                        # jig-ignore-next-line: pinned Ruff formats at 88 columns
                        and cast("dict[str, dict[str, int]]", n["span"])["begin"][
                            "line"
                        ]
                        == 6
                    )
                    if field == "operation":
                        guard[field] = "|"
                    else:
                        node = next(
                            n
                            for n in nodes
                            if n.get("literal") == "1"
                            and n.get("parent") == guard["id"]
                        )
                        if field == "parent":
                            node[field] = 0
                        elif field == "literal":
                            node[field] = "2"
                        else:
                            # jig-ignore-next-line: pinned Ruff formats at 88 columns
                            span = cast("dict[str, dict[str, int]]", node[field])
                            span["begin"]["column"] += 1
                    guest = root / f"forged-{field}.malbolge"
                    result = PROJECT(forged, guest, program)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())
            changed = root / "changed.c"
            _ = changed.write_text(
                original.replace("current & 1", "current & 2"), encoding="utf-8"
            )
            forged = copy.deepcopy(normalized)
            record = cast("dict[str, object]", forged["source"])
            record["sha256"] = hashlib.sha256(changed.read_bytes()).hexdigest()
            guest = root / "changed.malbolge"
            self.assertNotEqual(PROJECT(forged, guest, changed).returncode, 0)
            self.assertFalse(guest.exists())
            guest = root / "missing.malbolge"
            self.assertNotEqual(PROJECT(normalized, guest, None).returncode, 0)
            self.assertFalse(guest.exists())
