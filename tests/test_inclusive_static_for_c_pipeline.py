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
#   - Bounded one-based and inclusive C induction with guest byte I/O.
# - Must-Not:
#   - Treat guest input as a compile-time value or admit unproved steps.
# - Allows:
#   - Inputs: pinned Clang, binary guest stdin and forged normalized JSON.
#   - Outputs: whole-program VM parity and fail-closed diagnostics.
#   - Side effects: isolated temporary compiler artifacts.
# - Split-When:
#   - Guest-side loops replace finite source-time replay.
# - Merge-When:
#   - Source-authenticated counted-loop bounds share their proof.
# - Summary:
#   - The C induction includes its true initial and final trip values.

"""C inclusive and one-based bounds select real guest byte effects."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

from tests.test_induction_static_for_c_pipeline import (
    ADAPTER,
    DRIVER,
    FRONTEND,
    INCLUDE,
    LAYOUT,
    RESOURCE,
    ROOT,
    VM,
)

if TYPE_CHECKING:
    from subprocess import CompletedProcess

INCLUSIVE_OPERATOR = "<="
DOUBLE_OUTPUT_TRIPS = frozenset({2, 3})
BREAK_TRIP = 4
FOR_KIND = "for-statement"
BINARY_KIND = "binary-expression"
DECLARATION_KIND = "declaration-statement"
LITERAL_KIND = "integer-literal"
FIRST_TRIP = "1"


def program(start: int = 1, operator: str = "<=", bound: int = 4) -> str:
    """Construct one whole C source with selected and skipped loop I/O.

    Returns:
        Source text with source-time induction and runtime guest reads.

    """
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    for (int i = {start}; i {operator} {bound}; i++) {{\n"
        "        int current = getchar();\n"
        "        if (i == 2 || i == 3) {\n"
        "            putchar(putchar(current));\n"
        "            continue;\n"
        "        }\n"
        "        if (i == 4) {\n"
        "            break;\n"
        "        }\n"
        "        putchar(current);\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


def oracle(start: int, operator: str, bound: int, *, data: bytes) -> tuple[bytes, int]:
    """Compute C control flow independently of the normalized Clang tree.

    Returns:
        Expected guest stdout and the count of consumed input bytes.

    """
    outputs = bytearray()
    reads = 0
    for counter in range(start, bound + int(operator == INCLUSIVE_OPERATOR)):
        current = data[reads]
        reads += 1
        if counter in DOUBLE_OUTPUT_TRIPS:
            outputs.extend((current, current))
            continue
        if counter == BREAK_TRIP:
            break
        outputs.append(current)
        outputs.append(data[reads])
        reads += 1
    outputs.append(data[reads])
    return bytes(outputs), reads + 1


def forged_mutations(
    artifact: dict[str, object],
) -> tuple[tuple[int, str, object], ...]:
    """Select independently authenticated Clang nodes for tampering.

    Returns:
        Deliberately inconsistent node IDs, field paths and new values.

    """
    nodes = artifact["nodes"]
    loop = next(node for node in nodes if node["kind"] == FOR_KIND)
    condition = next(
        node
        for node in nodes
        if node["parent"] == loop["id"] and node["kind"] == BINARY_KIND
    )
    declaration = next(
        node
        for node in nodes
        if node["parent"] == loop["id"] and node["kind"] == DECLARATION_KIND
    )
    initial = next(node for node in nodes if node.get("literal") == FIRST_TRIP)
    bound = next(
        node
        for node in nodes
        if node["parent"] == condition["id"] and node["kind"] == LITERAL_KIND
    )
    return (
        (condition["id"], "operation", "<"),
        (condition["id"], "operation", ">="),
        (condition["id"], "operation", "!="),
        (condition["id"], "span.end.column", 1),
        (condition["id"], "parent", declaration["id"]),
        (initial["id"], "literal", "0"),
        (initial["id"], "constant_integer", "0"),
        (initial["id"], "parent", loop["id"]),
        (bound["id"], "span.begin.byte", 0),
        (bound["id"], "constant_integer", "9"),
    )


def mutate_artifact(
    artifact: dict[str, object], mutation: tuple[int, str, object]
) -> dict[str, object]:
    """Change one normalized node field without altering source identity.

    Returns:
        Forged normalized artifact for the compiler's refusal check.

    """
    node_id, field, value = mutation
    forged = copy.deepcopy(artifact)
    node = next(node for node in forged["nodes"] if node["id"] == node_id)
    dest = node
    parts = field.split(".")
    for part in parts[:-1]:
        dest = dest[part]
    dest[parts[-1]] = value
    return forged


class InclusiveStaticForCPipelineTests(unittest.TestCase):
    """Exercise real C compilation and Malbolge VM binary input parity."""

    def setUp(self) -> None:
        """Skip on hosts without the pinned compiler chain and guest VM."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned source-C compiler and normative guest VM needed")

    @staticmethod
    def compile(path: Path, target: Path) -> CompletedProcess[bytes]:
        """Compile through trusted repository-selected executables.

        Returns:
            Completed process, including any compiler rejection diagnostic.

        """
        return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--capsule",
                "--output",
                str(target),
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=90,
        )

    @staticmethod
    def normalized(path: Path) -> dict[str, object]:
        """Request the pinned Clang proof for negative mutation tests.

        Returns:
            Parsed normalized compiler artifact.

        """
        result = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [
                str(FRONTEND),
                "--guest-include",
                str(INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "inclusive-for",
                str(path),
            ],
            capture_output=True,
            check=False,
            timeout=20,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def assert_guest_parity(self, cases: tuple[tuple[int, str, int], ...]) -> None:
        """Compare compiled guest traces to a separate bounded C oracle."""
        streams = (
            bytes((0, 255, 128, 1, 42, 9, 27, 45, 200, 7)),
            hashlib.shake_256(b"inclusive-for-seed-0x1ac1").digest(10),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for start, operator, bound in cases:
                path = root / f"start-{start}-{operator.replace('=', 'e')}-{bound}.c"
                target = path.with_suffix(".malbolge")
                path.write_text(program(start, operator, bound), encoding="utf-8")
                result = self.compile(path, target)
                assert result.returncode == 0, result.stderr
                for stream in streams:
                    expected, reads = oracle(start, operator, bound, data=stream)
                    vm = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
                        [
                            str(VM),
                            str(target),
                            "--input-stdin",
                            "--report-steps",
                        ],
                        input=stream,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    assert vm.returncode == 0, vm.stderr
                    assert vm.stdout == expected
                    expected_steps = reads + len(expected) + 1
                    assert vm.stderr == f"malbolge-steps-v1:{expected_steps}\n".encode()

    def test_one_based_c_bounds_match_guest_vm(self) -> None:
        """Prove one-based inclusive and strict comparisons."""
        self.assert_guest_parity(((1, "<=", 4), (1, "<", 5)))

    def test_zero_based_inclusive_bound_matches_guest_vm(self) -> None:
        """Include the zero bound as exactly one source-proven trip."""
        self.assert_guest_parity(((0, "<=", 3), (0, "<=", 0)))

    def test_one_based_inclusive_boundary_matches_guest_vm(self) -> None:
        """Cover minimum and maximum admitted inclusive trip counts."""
        self.assert_guest_parity(((1, "<=", 1), (1, "<=", 16)))

    def test_unproved_loop_bounds_refuse_publication(self) -> None:
        """Refuse unknown, nonterminating, and over-budget C loops."""
        sources = (
            program(start=100),
            program(start=1, operator=">=", bound=4),
            program(start=1, operator="<=", bound=17),
            program(start=0, operator="<=", bound=16),
            program(start=5, operator="!=", bound=1),
            program(start=1, operator="!=", bound=0),
            program().replace("i++)", "i += 2)"),
            program().replace("i <= 4", "getchar() <= 4"),
            program().replace("int i = 1", "int i = getchar()"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, source in enumerate(sources):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    target = path.with_suffix(".malbolge")
                    path.write_text(source, encoding="utf-8")
                    assert self.compile(path, target).returncode != 0
                    assert not target.exists()

    def test_forged_normalized_loop_metadata_refuses(self) -> None:
        """Reject modified Clang loop ancestry and operator metadata."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "source.c"
            source.write_text(program(), encoding="utf-8")
            normalized = self.normalized(source)
            for index, mutation in enumerate(forged_mutations(normalized)):
                forged = mutate_artifact(normalized, mutation)
                target = root / f"forged-{index}.malbolge"
                result = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(target),
                        "--capsule",
                    ],
                    input=json.dumps(forged).encode(),
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                assert result.returncode != 0, result.stderr
                assert not target.exists()


if __name__ == "__main__":
    unittest.main()
