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
#   - Source-proven byte-dependent C conditional identities in full programs.
# - Must-Not:
#   - Fold guest input on the host or hide effects in the discarded arm.
# - Allows:
#   - Inputs: pinned Clang ancestry, original C and binary VM streams.
#   - Outputs: independently computed byte/step parity and refusals.
#   - Side effects: temporary guest artifacts only.
# - Split-When:
#   - Guest-dependent C branches gain general runtime control-flow lowering.
# - Merge-When:
#   - The guest byte-expression verifier has a general pure conditional proof.
# - Summary:
#   - A runtime ternary selection can preserve the same real guest byte.

"""Whole-C byte-dependent ternary identities under the normative guest VM."""

from __future__ import annotations

import copy
import hashlib
from itertools import product
import json
from pathlib import Path
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
from typing import cast
from typing import override
import unittest

from tests import test_guest_byte_identity_arithmetic_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT
OUTPUT_LINE = 6
PARENT_FIELD = "parent"
EIGHT_STEPS = b"malbolge-steps-v1:8\n"
BACKEND_ERROR = b"layout backend exited unsuccessfully"


def _source(
    *, expression: str = "current ? (current + 0) : 0", bound: int = 3
) -> str:
    """Construct the original induction/branch/continue binary stream.

    Returns:
        A complete C program with genuine guest I/O effects.

    """
    return previous.source(expression=expression, bound=bound)


class GuestByteConditionalIdentityCPipelineTests(unittest.TestCase):
    """Prove guest parity and conservative refusal for zero-guard identities."""

    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest(
                "pinned frontend, adapter, layout and VM are required"
            )

    def test_complete_branch_continue_loop_preserves_binary_guest_input(
        self,
    ) -> None:
        """A demanded C program must execute its byte effects in Malbolge."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "conditional.c"
            guest = root / "conditional.malbolge"
            program.write_text(_source(), encoding="utf-8")
            compiled = COMPILE(program, guest)
            if compiled.returncode != 0:
                self.fail(f"original C refused: {compiled.stderr!r}")
            streams = (
                hashlib.shake_256(bytes((127, i))).digest(2) for i in range(16)
            )
            for data in (bytes((0, 255)), bytes((255, 0)), *streams):
                result = RUN(guest, data)
                assert result.returncode == 0, result.stderr
                assert result.stdout == bytes((data[0],) * 4 + (data[1],))
                assert result.stderr == EIGHT_STEPS

    def test_zero_trip_and_alternate_identity_shapes(self) -> None:
        """All zero-guard directions preserve runtime data and guest steps."""
        # The complete fixture above proves the primary runtime trace. Two
        # distinct traces here witness reversed guards and skipped loops;
        # remaining equivalent forms need only run the source-authentication
        # gate, not repeat expensive synthesis of the same effect trace.
        variants = (
            ("current == 0 ? 0 : (current + 0)", 3, 8, 4),
            ("current ? ((current * 1) % 256) : 0", 0, 5, 1),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (expression, bound, steps, first_count) in enumerate(
                variants
            ):
                program = root / f"variant-{index}.c"
                guest = root / f"variant-{index}.malbolge"
                program.write_text(
                    _source(expression=expression, bound=bound),
                    encoding="utf-8",
                )
                compiled = COMPILE(program, guest)
                if compiled.returncode != 0:
                    self.fail(f"{expression!r} refused: {compiled.stderr!r}")
                for data in (bytes((0, 255)), bytes((255, 0))):
                    result = RUN(guest, data)
                    assert result.returncode == 0, result.stderr
                    assert result.stdout == bytes(
                        (data[0],) * first_count + (data[1],)
                    )
                    assert (
                        result.stderr == f"malbolge-steps-v1:{steps}\n".encode()
                    )

    def test_other_identity_guards_pass_source_frontend(self) -> None:
        """Additional pure guards authenticate without repeated guest search."""
        identities = (
            "current ? current : 0",
            "(current ^ 0) ? (current & 255) : 0",
            "current != 0 ? (current & 255) : 0",
            "!current ? 0 : (current ^ 0)",
            "(current == 0 ? 0 : current) ^ 0",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(identities):
                program = root / f"guard-{index}.c"
                guest = root / f"guard-{index}.malbolge"
                program.write_text(
                    _source(expression=expression), encoding="utf-8"
                )
                result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        sys.executable,
                        "--output",
                        str(guest),
                        "--source",
                        str(program),
                        "--capsule",
                    ],
                    input=json.dumps(NORMALIZED(program)).encode(),
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                if result.returncode != 1:
                    self.fail(f"unexpected adapter status for {expression}")
                assert BACKEND_ERROR in result.stderr
                assert not guest.exists(), expression

    def test_unsound_conditional_expressions_refuse(self) -> None:
        """Incorrect identities, extra reads and hidden outputs fail closed."""
        invalid = (
            "current ? (current + 1) : 0",
            "current ? current : 1",
            "current ? current : getchar()",
            "getchar() ? current : 0",
            "current ? putchar(current) : 0",
            "current ? (current + 0) : putchar(0)",
            "current ? 0 : current",
            "current ? current : -1",
            "current ? (current ^ 1) : 0",
            "current ? current : (0 / current)",
            "current ? (current & 255) : (0 + 0)",
            "current == 1 ? 0 : current",
            "current != 0 ? current : 1",
            "current == 0 ? 1 : current",
            "!current ? 1 : current",
            "current == 0 ? 0 : (current - 1)",
            "current == getchar() ? 0 : current",
            "!putchar(current) ? 0 : current",
            "(current ^ 1) == 0 ? 0 : current",
            "current == 0 ? 0 : putchar(current)",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(invalid):
                program = root / f"bad-{index}.c"
                guest = root / f"bad-{index}.malbolge"
                program.write_text(
                    _source(expression=expression), encoding="utf-8"
                )
                rejected = COMPILE(program, guest)
                if rejected.returncode == 0:
                    self.fail(f"unsound C accepted: {expression}")
                assert not guest.exists(), expression

    def test_conditional_ast_forgery_refuses(self) -> None:
        """Every changed Clang parent or coordinate must reject publication."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "original.c"
            program.write_text(_source(), encoding="utf-8")
            original = NORMALIZED(program)
            nodes = cast("list[dict[str, object]]", original["nodes"])
            affected = [
                i
                for i, node in enumerate(nodes)
                if cast("dict[str, dict[str, int]]", node["span"])["begin"][
                    "line"
                ]
                == OUTPUT_LINE
            ]
            for index, field in product(affected, (PARENT_FIELD, "span")):
                forged = copy.deepcopy(original)
                changed = cast("list[dict[str, object]]", forged["nodes"])
                if field == PARENT_FIELD:
                    changed[index]["parent"] = 1
                else:
                    span = cast(
                        "dict[str, dict[str, int]]", changed[index]["span"]
                    )
                    span["begin"]["column"] += 1
                guest = root / f"ast-{index}-{field}.malbolge"
                rejected = PROJECT(forged, guest, program)
                if rejected.returncode == 0:
                    self.fail(f"forged {field} admitted on node {index}")
                assert not guest.exists(), (index, field)

    def test_conditional_source_and_missing_witness_refuse(self) -> None:
        """Rehashed C changes cannot counterfeit normalized Clang evidence."""
        changes = (
            ("? (current + 0) : 0", "? (current + 0) : 1"),
            ("current ?", "currenx ?"),
            ("current + 0", "current + 1"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "original.c"
            program.write_text(_source(), encoding="utf-8")
            original = NORMALIZED(program)
            for index, (old, new) in enumerate(changes):
                tampered = root / f"tampered-{index}.c"
                tampered.write_text(
                    _source().replace(old, new), encoding="utf-8"
                )
                forged = copy.deepcopy(original)
                metadata = cast("dict[str, object]", forged["source"])
                metadata["sha256"] = hashlib.sha256(
                    tampered.read_bytes()
                ).hexdigest()
                guest = root / f"tampered-{index}.malbolge"
                rejected = PROJECT(forged, guest, tampered)
                if rejected.returncode == 0:
                    self.fail(f"changed C source admitted: {index}")
                assert not guest.exists(), index
            guest = root / "no-source.malbolge"
            rejected = PROJECT(original, guest, None)
            assert rejected.returncode != 0
            assert not guest.exists()


if __name__ == "__main__":
    unittest.main()
