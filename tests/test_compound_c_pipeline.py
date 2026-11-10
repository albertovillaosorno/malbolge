# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Reproducible complete-C Fibonacci pipeline failure and guest oracle.
# - Must-Not:
#   - Claim unsupported C variables/branches/loops have guest semantics.
# - Allows:
#   - Inputs: a tracked stateful C program and exact pinned compiler binaries.
#   - Outputs: an identified unsupported semantic stage, with no guest artifact.
#   - Side effects: project-local temporary output only.
# - Split-When:
#   - Production C control-flow lowering has a validated end-to-end witness.
# - Merge-When:
#   - The general C semantic matrix subsumes this first full-program repro.
# - Summary:
#   - Local storage metadata is valid JSON, but local state is not yet lowered.
# - Description:
#   - The independently computed oracle remains a future positive VM target.
# - Usage:
#   - python3.14 -B -m unittest tests.test_compound_c_pipeline -v
# - Defaults:
#   - No fake output on host, no guest artifact on compiler refusal.

"""Complete Fibonacci blocker and source-bound initialized local VM parity."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/compiler/c-frontend/accepted/conditional_fibonacci.c"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
EXPECTED = bytes.fromhex("02595f08574f226d0390b323")
LOOP_OUTPUT = ROOT / "tests/compiler/c-frontend/accepted/local_loop_branch_output.c"
MASKED_FIBONACCI = (
    ROOT / "tests/compiler/c-frontend/accepted/"
    "local_masked_fibonacci_branch_stream.c"
)
WIDE_STREAM = (
    ROOT / "tests/compiler/c-frontend/accepted/local_loop_wide_branch_stream.c"
)


def root_scoped_shadowed_fibonacci_source() -> str:
    """Put the full recurrence in a scope shadowing an unrelated outer b."""
    source = MASKED_FIBONACCI.read_text()
    beginning = "    unsigned b = 1U;\n    for ("
    ending = "        b = next;\n    }\n}"
    assert source.count(beginning) == source.count(ending) == 1
    return source.replace(
        beginning,
        "    unsigned b = 77U;\n"
        "    {\n"
        "    unsigned b = 1U;\n"
        "    for (",
    ).replace(ending, "        b = next;\n    }\n    }\n}")


def unbraced_masked_fibonacci_source() -> str:
    """Use ordinary unbraced if/else output arms in the full recurrence."""
    source = MASKED_FIBONACCI.read_text()
    braced = (
        "        if ((next & 1U) == 0U) {\n"
        "            putchar((int)(next & 31U));\n"
        "        } else {\n"
        "            putchar((int)((next ^ 0x1AU) & 31U));\n"
        "        }"
    )
    unbraced = (
        "        if ((next & 1U) == 0U)\n"
        "            putchar((int)(next & 31U));\n"
        "        else\n"
        "            putchar((int)((next ^ 0x1AU) & 31U));"
    )
    assert source.count(braced) == 1
    return source.replace(braced, unbraced)


def unbraced_assigning_fibonacci_source() -> str:
    """Select an initially uninitialized byte through unbraced C writes."""
    source = MASKED_FIBONACCI.read_text()
    original = (
        "        if ((next & 1U) == 0U) {\n"
        "            putchar((int)(next & 31U));\n"
        "        } else {\n"
        "            putchar((int)((next ^ 0x1AU) & 31U));\n"
        "        }"
    )
    changed = (
        "        unsigned selected;\n"
        "        if ((next & 1U) == 0U)\n"
        "            selected = next & 31U;\n"
        "        else\n"
        "            selected = (next ^ 0x1AU) & 31U;\n"
        "        putchar((int)selected);"
    )
    assert source.count(original) == 1
    return source.replace(original, changed)


def nested_masked_fibonacci_source() -> str:
    """Keep the same recurrence while splitting its induction into 3 by 4."""
    original = MASKED_FIBONACCI.read_text()
    loop = "for (unsigned i = 0U; i < 12U; ++i) {"
    end = "        b = next;\n    }\n}"
    assert original.count(loop) == original.count(end) == 1
    return original.replace(
        loop,
        "for (unsigned row = 0U; row < 3U; ++row) {\n"
        "        for (unsigned col = 0U; col < 4U; ++col) {",
    ).replace(end, "        b = next;\n        }\n    }\n}")


def unbraced_nested_masked_fibonacci_source() -> str:
    """Nest two finite C for loops without an invented outer brace scope."""
    source = nested_masked_fibonacci_source()
    outer = (
        "for (unsigned row = 0U; row < 3U; ++row) {\n"
        "        for (unsigned col = 0U; col < 4U; ++col) {"
    )
    unbraced = (
        "for (unsigned row = 0U; row < 3U; ++row)\n"
        "        for (unsigned col = 0U; col < 4U; ++col) {"
    )
    assert source.count(outer) == source.count("        }\n    }\n}") == 1
    return source.replace(outer, unbraced).replace(
        "        }\n    }\n}", "        }\n}"
    )


def unbraced_conditional_for_fibonacci_source() -> str:
    """Select and update a full recurrence in one unbraced for-body if."""
    return (
        "#include <stdio.h>\n"
        "void emit(void) {\n"
        "    unsigned a = 1U;\n"
        "    unsigned b = 1U;\n"
        "    for (unsigned i = 0U; i < 12U; ++i)\n"
        "        if (((a + b) & 1U) == 0U) {\n"
        "            unsigned next = (a + b) & 255U;\n"
        "            putchar((int)(next & 31U));\n"
        "            a = b;\n"
        "            b = next;\n"
        "        } else {\n"
        "            unsigned next = (a + b) & 255U;\n"
        "            putchar((int)((next ^ 0x1AU) & 31U));\n"
        "            a = b;\n"
        "            b = next;\n"
        "        }\n"
        "}\n"
    )


def unbraced_conditional_while_fibonacci_source() -> str:
    """Prove state progression through one direct if inside a C while."""
    source = unbraced_conditional_for_fibonacci_source()
    header = "    for (unsigned i = 0U; i < 12U; ++i)\n"
    assignment = "            b = next;\n"
    assert source.count(header) == 1 and source.count(assignment) == 2
    return source.replace(
        header, "    unsigned i = 0U;\n    while (i < 12U)\n"
    ).replace(assignment, "            b = next;\n            ++i;\n")


def scoped_masked_fibonacci_source() -> str:
    """Carry the recurrence through a loop-local lexical transfer scope."""
    original = MASKED_FIBONACCI.read_text()
    transfer = "        a = b;\n        b = next;"
    assert original.count(transfer) == 1
    return original.replace(
        transfer,
        "        {\n"
        "            unsigned transfer = next;\n"
        "            a = b;\n"
        "            b = transfer;\n"
        "        }",
    )


def branch_local_masked_fibonacci_source() -> str:
    """Use same-name branch locals, with one nested lexical C block."""
    original = MASKED_FIBONACCI.read_text()
    even = "            putchar((int)(next & 31U));"
    odd = "            putchar((int)((next ^ 0x1AU) & 31U));"
    assert original.count(even) == original.count(odd) == 1
    return original.replace(
        even,
        "            {\n"
        "                unsigned selected = next & 31U;\n"
        "                putchar((int)selected);\n"
        "            }",
    ).replace(
        odd,
        "            unsigned selected = (next ^ 0x1AU) & 31U;\n"
        "            putchar((int)selected);",
    )


def else_if_masked_fibonacci_source() -> str:
    """Select three real C branches across a full Fibonacci recurrence.

    Returns:
        A source-backed three-way Fibonacci C program.
    """
    source = MASKED_FIBONACCI.read_text()
    previous = (
        "        } else {\n"
        "            putchar((int)((next ^ 0x1AU) & 31U));\n"
        "        }"
    )
    chain = (
        "        } else if ((next & 2U) != 0U) {\n"
        "            putchar((int)((next ^ 0x1AU) & 31U));\n"
        "        } else {\n"
        "            putchar((int)((next & 31U) ^ 0x1AU));\n"
        "        }"
    )
    assert source.count(previous) == 1
    return source.replace(previous, chain)


def wide_unsigned_masked_fibonacci_source(expression: str) -> str:
    """Use standard unsigned-C wide temporaries in the full recurrence."""
    source = MASKED_FIBONACCI.read_text()
    original = "unsigned next = (a + b) & 255U;"
    assert source.count(original) == 1
    return source.replace(original, f"unsigned next = {expression};")


def ordinary_int_masked_fibonacci_source() -> str:
    """Use C's ordinary signed-int literals in a full unsigned recurrence."""
    source = MASKED_FIBONACCI.read_text()
    for token in ("0x1AU", "255U", "31U", "12U", "1U", "0U"):
        source = source.replace(token, token[:-1])
    return source


def unary_unsigned_masked_fibonacci_source() -> str:
    """Exercise full-width unary unsigned signs in the complete C loop."""
    source = MASKED_FIBONACCI.read_text()
    original = "unsigned next = (a + b) & 255U;"
    assert source.count(original) == 1
    return source.replace(
        original,
        "unsigned wide = -(a + b);\n        unsigned next = (+(0U - wide)) & 255U;",
    )


def stored_unsigned_masked_fibonacci_source(statements: str) -> str:
    """Carry a full u32 value through a separately named automatic local."""
    source = MASKED_FIBONACCI.read_text()
    original = "unsigned next = (a + b) & 255U;"
    assert source.count(original) == 1
    return source.replace(original, statements)


def shadowed_masked_fibonacci_source() -> str:
    """Reuse the outer `b` name inside one explicit nested loop block."""
    source = MASKED_FIBONACCI.read_text()
    original = (
        "        if ((next & 1U) == 0U) {\n"
        "            putchar((int)(next & 31U));\n"
        "        } else {\n"
        "            putchar((int)((next ^ 0x1AU) & 31U));\n"
        "        }\n"
        "        a = b;"
    )
    shadowed = (
        "        {\n"
        "            unsigned b = (next ^ 0x1AU) & 31U;\n"
        "            if ((next & 1U) == 0U) {\n"
        "                putchar((int)(next & 31U));\n"
        "            } else {\n"
        "                putchar((int)b);\n"
        "            }\n"
        "        }\n"
        "        a = b;"
    )
    assert source.count(original) == 1
    return source.replace(original, shadowed)


def exiting_masked_fibonacci_source(*, keyword: str, iteration: int) -> str:
    """Exit a source-proven bounded for body after its recurrence transfer."""
    original = MASKED_FIBONACCI.read_text()
    transfer = "        b = next;"
    assert keyword in ("break", "continue")
    assert original.count(transfer) == 1
    return original.replace(
        transfer,
        f"{transfer}\n"
        f"        if (i == {iteration}U) {{\n"
        f"            {keyword};\n"
        "        }",
    )


def exiting_masked_fibonacci_while_source(*, keyword: str) -> str:
    """Exit a complete C recurrence from an updated bounded while state."""
    source = MASKED_FIBONACCI.read_text()
    induction = "for (unsigned i = 0U; i < 12U; ++i) {"
    transfer = "        b = next;"
    assert keyword in ("break", "continue")
    assert source.count(induction) == source.count(transfer) == 1
    bound = 13 if keyword == "break" else 12
    exit_at = 12 if keyword == "break" else 7
    return source.replace(
        induction, f"unsigned i = 0U;\n    while (i < {bound}U) {{"
    ).replace(
        transfer,
        f"{transfer}\n"
        "        i = i + 1U;\n"
        f"        if (i == {exit_at}U) {{\n"
        f"            {keyword};\n"
        "        }",
    )


def exiting_masked_fibonacci_do_source(*, keyword: str) -> str:
    """Replay the entire C recurrence with a body-first checked loop exit."""
    original = MASKED_FIBONACCI.read_text()
    induction = "for (unsigned i = 0U; i < 12U; ++i) {"
    transfer = "        b = next;"
    assert keyword in ("break", "continue")
    assert original.count(induction) == original.count(transfer) == 1
    assert original.count("    }\n}") == 1
    bound = 13 if keyword == "break" else 12
    exit_at = 12 if keyword == "break" else 7
    return original.replace(
        induction, "unsigned i = 0U;\n    do {"
    ).replace(
        transfer,
        f"{transfer}\n"
        "        i = i + 1U;\n"
        f"        if (i == {exit_at}U) {{\n"
        f"            {keyword};\n"
        "        }",
    ).replace("    }\n}", f"    }} while (i < {bound}U);\n}}")


def returning_masked_fibonacci_source(*, exit_at: int = 11) -> str:
    """Stop a full bounded C recurrence through a conditional void return."""
    original = MASKED_FIBONACCI.read_text()
    assert original.count("i < 12U;") == 1
    assert original.count("        b = next;") == 1
    return original.replace("i < 12U;", "i < 13U;").replace(
        "        b = next;",
        "        b = next;\n"
        f"        if (i == {exit_at}U) {{\n"
        "            return;\n"
        "        }",
    )


def returning_pair_source(*, loop_kind: str, selected: bool = True) -> str:
    """Retain the independent Q. recurrence under three C loop forms."""
    original = (
        ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
    ).read_text()
    header = "for (unsigned i = 0U; i < 2U; ++i) {"
    transfer = "        b = next;"
    assert original.count(header) == original.count(transfer) == 1
    if loop_kind == "for":
        bound = 3 if selected else 2
        original = original.replace(header, header.replace("2U", f"{bound}U"))
        increment = ""
        suffix = ""
        exit_at = 1 if selected else 7
    elif loop_kind in ("while", "do"):
        assert selected
        original = original.replace(
            header,
            "unsigned i = 0U;\n    "
            + ("while (i < 3U) {" if loop_kind == "while" else "do {"),
        )
        increment = "        i = i + 1U;\n"
        suffix = " while (i < 3U);" if loop_kind == "do" else ""
        exit_at = 2
    else:
        raise ValueError(loop_kind)
    original = original.replace(
        transfer,
        f"{transfer}\n"
        f"{increment}"
        f"        if (i == {exit_at}U) {{\n"
        "            return;\n"
        "        }",
    )
    if suffix:
        original = original.replace("    }\n}", f"    }}{suffix}\n}}")
    return original


def reference_bytes() -> bytes:
    """Reference the bounded unsigned-C arithmetic, not compiler output."""
    previous, current = 1, 1
    output = bytearray()
    for _ in range(12):
        following = (previous + current) & 0xFF
        output.append(following if following % 2 == 0 else following ^ 0x5A)
        previous, current = current, following
    return bytes(output)


class CompoundCPipelineTests(unittest.TestCase):
    def test_fibonacci_branch_oracle_is_independent_and_stable(self) -> None:
        self.assertEqual(reference_bytes(), EXPECTED)
        self.assertEqual(len(EXPECTED), 12)

    def test_root_lexical_shadow_replays_complete_fibonacci_guest(self) -> None:
        """A function-body block must resolve its own b through the loop."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        expected = bytearray()
        a, b = 1, 1  # The outer b is 77; the loop reads the inner b.
        for _ in range(12):
            next_value = (a + b) & 255
            expected.append(
                (next_value & 31)
                if next_value % 2 == 0
                else ((next_value ^ 0x1A) & 31)
            )
            a, b = b, next_value
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "root-shadow.c"
            source.write_text(root_scoped_shadowed_fibonacci_source())
            guest = Path(scratch) / "root-shadow.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/root-scoped-shadow-fibonacci-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=150,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def test_root_lexical_shadow_restores_outer_binding_on_guest(self) -> None:
        """After a C block, a b read must select the outer declaration."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source_text = (
            "#include <stdio.h>\n"
            "void emit(void) {\n"
            "    unsigned a = 1U;\n"
            "    unsigned b = 65U;\n"
            "    {\n"
            "        unsigned b = 90U;\n"
            "        a = a + 1U;\n"
            "    }\n"
            "    putchar((int)b);\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "scope-restoration.c"
            source.write_text(source_text)
            guest = Path(scratch) / "scope-restoration.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/root-shadow-restoration-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/root-shadow-restoration-ast-v1",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, list[dict[str, object]]], json.loads(frontend.stdout))
            nodes = parsed["nodes"]
            outer_b, inner_b = [
                n for n in nodes
                if n["kind"] == "variable-declaration"
                and n.get("name") == "b"
            ]
            # The final b read is after the inner block. Rebinding it to
            # the expired inner symbol must refuse, not output 90.
            post_scope_read = next(
                n for n in nodes
                if n["kind"] == "declaration-reference-expression"
                and n.get("reference") == outer_b["reference"]
            )
            parsed["nodes"][int(post_scope_read["id"]) - 1]["reference"] = inner_b["reference"]
            forged_guest = Path(scratch) / "forged-expired-binding.malbolge"
            refused = subprocess.run(
                [
                    str(ADAPTER),
                    "--layout-backend",
                    str(LAYOUT),
                    "--output",
                    str(forged_guest),
                    "--capsule",
                ],
                input=json.dumps(parsed).encode(),
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
            self.assertFalse(forged_guest.exists())

    def test_root_lexical_shadow_rejects_bad_source_and_forged_ast(self) -> None:
        """Reject uninitialized shadow reads and forged scope/symbol identity."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = root_scoped_shadowed_fibonacci_source()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, altered in (
                ("uninitialized-inner", source.replace("unsigned b = 1U;", "unsigned b;")),
                ("undefined-inner", source.replace("unsigned b = 1U;", "unsigned b = 1U / 0U;")),
                ("unproven-effect", source.replace("    unsigned b = 1U;", '    unsigned b = 1U; puts("extra");')),
            ):
                with self.subTest(label=label):
                    candidate = Path(scratch) / f"{label}.c"
                    candidate.write_text(altered)
                    guest = Path(scratch) / f"{label}.malbolge"
                    rejected = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/root-shadow-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)
            candidate = Path(scratch) / "root-shadow-ast.c"
            candidate.write_text(source)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/root-scoped-shadow-ast-v1",
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            root = next(node for node in nodes if node["id"] == 2)
            scope = next(
                node
                for node in nodes
                if node["kind"] == "compound-statement"
                and node["parent"] == root["id"]
            )
            outer_b, inner_b = [
                node for node in nodes
                if node["kind"] == "variable-declaration" and node.get("name") == "b"
            ]
            inner_read = next(
                node for node in nodes
                if node["kind"] == "declaration-reference-expression"
                and node.get("reference") == inner_b["reference"]
            )
            for label, node_id, field, value in (
                ("scope-parent", scope["id"], "parent", 1),
                ("scope-end", scope["id"], "span", root["span"]),
                ("scope-operation", scope["id"], "operation", "+"),
                ("shadow-alias", inner_b["id"], "reference", outer_b["reference"]),
                ("shadow-parent", inner_b["id"], "parent", outer_b["parent"]),
                ("shadow-read", inner_read["id"], "reference", outer_b["reference"]),
            ):
                with self.subTest(label=label):
                    altered = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    assert isinstance(node_id, int)
                    altered["nodes"][node_id - 1][field] = value
                    guest = Path(scratch) / f"ast-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(altered).encode(),
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                    self.assertFalse(guest.exists(), label)

    def test_masked_twelve_iteration_fibonacci_reaches_real_guest(self) -> None:
        """An entire C recurrence selects twelve actual guest byte effects."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            if following % 2 == 0:
                expected.append(following & 31)
            else:
                expected.append((following ^ 0x1A) & 31)
            previous, current = current, following
        self.assertEqual(
            bytes(expected), bytes.fromhex("02191f08170f020d03101303")
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "masked-fibonacci.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/masked-fibonacci-guest-v1",
                "--capsule",
                "--output",
                str(guest),
                str(MASKED_FIBONACCI),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=150
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(
                    executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )
            altered = Path(scratch) / "masked-fibonacci-invalid.c"
            source = MASKED_FIBONACCI.read_text()
            self.assertIn("((next ^ 0x1AU) & 31U)", source)
            altered.write_text(
                source.replace(
                    "((next ^ 0x1AU) & 31U)", "((next ^ 0x1AU) / 0U)"
                )
            )
            rejected_guest = Path(scratch) / "rejected.malbolge"
            rejected = subprocess.run(
                [*command[:-2], str(rejected_guest), str(altered)],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"Unsupported", rejected.stderr)
            self.assertFalse(rejected_guest.exists())

    def test_unbraced_if_else_full_fibonacci_reaches_guest(self) -> None:
        """Direct Clang call arms preserve twelve source-selected guest bytes."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        expected = bytearray()
        a, b = 1, 1
        for _ in range(12):
            next_value = (a + b) & 255
            expected.append(
                (next_value & 31)
                if (next_value & 1) == 0
                else ((next_value ^ 0x1A) & 31)
            )
            a, b = b, next_value
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "unbraced-fib.c"
            source.write_text(unbraced_masked_fibonacci_source())
            guest = Path(scratch) / "unbraced-fib.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/unbraced-if-else-fibonacci-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=150,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((0, 255, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def test_unbraced_conditional_assignments_full_fibonacci_guest(self) -> None:
        """Two direct C writes select a later proven guest byte at each step."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        a, b = 1, 1
        oracle = bytearray()
        for _ in range(12):
            value = (a + b) & 255
            oracle.append((value & 31) if value % 2 == 0 else ((value ^ 0x1A) & 31))
            a, b = b, value
        self.assertEqual(bytes(oracle), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "unbraced-assign.c"
            source.write_text(unbraced_assigning_fibonacci_source())
            guest = Path(scratch) / "unbraced-assign.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/unbraced-assignment-fibonacci-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=150,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, oracle)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def test_unbraced_conditional_assignments_fail_closed(self) -> None:
        """A direct branch write cannot forge a source binding or initializer."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = unbraced_assigning_fibonacci_source()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed in (
                (
                    "uninitialized-compound",
                    source.replace("selected = next & 31U;", "selected += next & 31U;"),
                ),
                (
                    "missing-selected-write",
                    source.replace(
                        "selected = (next ^ 0x1AU) & 31U;",
                        "next = (next ^ 0x1AU) & 31U;",
                    ),
                ),
            ):
                with self.subTest(source=label):
                    candidate = Path(scratch) / f"{label}.c"
                    candidate.write_text(changed)
                    guest = Path(scratch) / f"{label}.malbolge"
                    refused = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/unbraced-assignment-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)
            candidate = Path(scratch) / "assignments-ast.c"
            candidate.write_text(source)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/unbraced-assignments-ast-v1",
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(
                dict[str, list[dict[str, object]]], json.loads(frontend.stdout)
            )
            nodes = parsed["nodes"]
            branch = next(n for n in nodes if n["kind"] == "if-statement")
            assignments = [
                n
                for n in nodes
                if n["parent"] == branch["id"]
                and n["kind"] == "binary-expression"
                and n.get("operation") == "="
            ]
            self.assertEqual(len(assignments), 2)
            lhs = next(
                n
                for n in nodes
                if n["parent"] == assignments[0]["id"]
                and n["kind"] == "declaration-reference-expression"
            )
            rhs = next(
                n
                for n in nodes
                if n["parent"] == assignments[0]["id"]
                and n["kind"] == "binary-expression"
            )
            a_symbol = next(
                n["reference"]
                for n in nodes
                if n["kind"] == "variable-declaration" and n.get("name") == "a"
            )
            for label, target, changes in (
                ("then-parent", assignments[0], {"parent": 2}),
                ("else-parent", assignments[1], {"parent": 2}),
                ("then-operation", assignments[0], {"operation": "+="}),
                ("then-lhs-binding", lhs, {"reference": a_symbol}),
                ("then-rhs-type", rhs, {"type": "i32"}),
            ):
                with self.subTest(ast=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    forged["nodes"][cast(int, target["id"]) - 1].update(changes)
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    rejected = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertRegex(rejected.stderr, rb"Unsupported|Malformed")
                    self.assertFalse(guest.exists(), label)

    def test_unbraced_if_else_rejects_unproven_calls_and_ast(self) -> None:
        """Unbraced arm proof is closed against unexpected effects or links."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = unbraced_masked_fibonacci_source()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed in (
                ("undefined", source.replace("next & 31U", "next / 0U")),
                (
                    "unproven-call",
                    source.replace(
                        "putchar((int)(next & 31U));",
                        "getchar();",
                    ),
                ),
            ):
                with self.subTest(source=label):
                    candidate = Path(scratch) / f"{label}.c"
                    candidate.write_text(changed)
                    guest = Path(scratch) / f"{label}.malbolge"
                    refused = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/unbraced-if-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)
            candidate = Path(scratch) / "unbraced-ast.c"
            candidate.write_text(source)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/unbraced-if-ast-v1",
                    str(candidate),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(
                dict[str, list[dict[str, object]]], json.loads(frontend.stdout)
            )
            nodes = parsed["nodes"]
            branch = next(n for n in nodes if n["kind"] == "if-statement")
            calls = [
                n
                for n in nodes
                if n["kind"] == "call-expression" and n["parent"] == branch["id"]
            ]
            self.assertEqual(len(calls), 2)
            for label, target, changes in (
                ("then-parent", calls[0], {"parent": 2}),
                ("else-parent", calls[1], {"parent": 2}),
                ("then-reference", calls[0], {"reference": "external:getchar"}),
                ("else-operation", calls[1], {"operation": "+"}),
                ("else-span", calls[1], {"span": calls[0]["span"]}),
                ("then-extra", calls[0], {"storage_duration": "static"}),
            ):
                with self.subTest(ast=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    forged["nodes"][cast(int, target["id"]) - 1].update(changes)
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    rejected = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertRegex(rejected.stderr, rb"Unsupported|Malformed")
                    self.assertFalse(guest.exists(), label)

    def test_multi_declarator_unsigned_fibonacci_preserves_guest_oracle(self) -> None:
        """A single C declaration creates two ordered unsigned local states."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = MASKED_FIBONACCI.read_text()
        original = "unsigned a = 1U;\n    unsigned b = 1U;"
        self.assertEqual(source.count(original), 1)
        source = source.replace(original, "unsigned a = 1U, b = a;")
        previous, current = 1, 1
        independent = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            independent.append(
                (following if following % 2 == 0 else following ^ 0x1A) & 31
            )
            previous, current = current, following
        self.assertEqual(bytes(independent), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / "multi-declarator-fibonacci.c"
            candidate.write_text(source)
            guest = candidate.with_suffix(".malbolge")
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/multi-declarator-fibonacci-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=150,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((0, 255, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, independent)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def test_three_declarators_with_deferred_write_reach_guest(self) -> None:
        """Third unsigned name stays unreadable until a later C assignment."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        declaration = "unsigned a = 1U;\n    unsigned b = 1U;"
        self.assertEqual(original.count(declaration), 1)
        source = original.replace(
            declaration,
            "unsigned a = 1U, b = a, later;\n    later = b;",
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            expected.append(
                (following if following % 2 == 0 else following ^ 0x1A) & 31
            )
            previous, current = current, following
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / "three-declarators.c"
            candidate.write_text(source)
            guest = candidate.with_suffix(".malbolge")
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/three-declarators-deferred-write-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ],
                capture_output=True,
                check=False,
                timeout=150,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.exists())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def test_multi_declarator_unsigned_refuses_unproved_sources_and_ast(self) -> None:
        """No deferred reads, hidden writes or forged declarator topology."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        initial = "unsigned a = 1U;\n    unsigned b = 1U;"
        self.assertEqual(original.count(initial), 1)
        source = original.replace(initial, "unsigned a = 1U, b = a;")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / "multi-declarator-ast.c"
            candidate.write_text(source)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/multi-declarator-ast-v1",
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            statement = next(
                node for node in nodes if node["kind"] == "declaration-statement"
            )
            variables = [
                node
                for node in nodes
                if node["parent"] == statement["id"]
                and node["kind"] == "variable-declaration"
            ]
            self.assertEqual([node["name"] for node in variables], ["a", "b"])
            for label, changed in {
                "uninitialized-source": source.replace("a = 1U, b = a", "a, b = a"),
                "self-read": source.replace("a = 1U, b = a", "a = 1U, b = b"),
                "hidden-effect": source.replace("a = 1U, b = a", "a = 1U, b = a++"),
            }.items():
                invalid = Path(scratch) / f"invalid-multi-{label}.c"
                invalid.write_text(changed)
                guest = invalid.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/multi-declarator-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(invalid),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=45,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertFalse(guest.exists(), label)
            for label, node_id, field, value in (
                ("second-parent", variables[1]["id"], "parent", 0),
                ("second-type", variables[1]["id"], "type", "i32"),
                ("second-reference", variables[1]["id"], "reference", "a@0"),
                ("first-metadata", variables[0]["id"], "operation", "="),
                ("first-end", variables[0]["id"], "span", variables[1]["span"]),
                ("second-offset", variables[1]["id"], "reference", "b@0"),
                ("second-start", variables[1]["id"], "span", variables[0]["span"]),
                ("statement-end", statement["id"], "span", variables[1]["span"]),
            ):
                self.assertIsInstance(node_id, int)
                forged = cast(dict[str, object], json.loads(frontend.stdout))
                forged_nodes = cast(list[dict[str, object]], forged["nodes"])
                forged_nodes[cast(int, node_id) - 1][field] = value
                guest = Path(scratch) / f"forged-multi-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(forged).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_ordinary_int_literals_convert_to_unsigned_fibonacci_guest(self) -> None:
        """Implicit C int->unsigned constants survive the full guest pipeline."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ordinary_int_masked_fibonacci_source()
        self.assertIn("unsigned a = 1;", source)
        self.assertIn("unsigned i = 0; i < 12;", source)
        self.assertIn("(next ^ 0x1A) & 31", source)
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            expected.append(
                (following if following % 2 == 0 else following ^ 0x1A) & 31
            )
            previous, current = current, following
        self.assertEqual(expected.hex(), "02191f08170f020d03101303")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / "int-literals-fibonacci.c"
            candidate.write_text(source)
            guest = candidate.with_suffix(".malbolge")
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/int-literals-fibonacci-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ],
                capture_output=True,
                check=False,
                timeout=150,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((0, 255, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def _check_unsuffixed_for_step(self, label: str, step: str) -> None:
        """A full C recurrence uses one source-checked induction form."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ordinary_int_masked_fibonacci_source()
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            expected.append(
                (following if following % 2 == 0 else following ^ 0x1A) & 31
            )
            previous, current = current, following
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / f"int-step-{label}.c"
            candidate.write_text(source.replace("++i)", f"{step})"))
            guest = candidate.with_suffix(".malbolge")
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    f"tests/int-step-{label}-fibonacci-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=150,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

    def test_unsuffixed_compound_for_step_preserves_guest(self) -> None:
        self._check_unsuffixed_for_step("compound", "i += 1")

    def test_unsuffixed_assignment_for_step_preserves_guest(self) -> None:
        self._check_unsuffixed_for_step("assignment", "i = i + 1")

    def test_int_to_unsigned_literal_rejects_unproved_source_and_ast(self) -> None:
        """Never trust an implicit C conversion without its exact i32 leaf."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ordinary_int_masked_fibonacci_source()
        variants = {
            "signed-local": source.replace("unsigned a = 1;", "int a = 1;"),
            "negative-int": source.replace("unsigned a = 1;", "unsigned a = -1;"),
            "long-int": source.replace("unsigned a = 1;", "unsigned a = 2147483648;"),
            "explicit-cast": source.replace(
                "unsigned a = 1;", "unsigned a = (unsigned)1;"
            ),
            "effectful-mask": source.replace("(a + b) & 255", "(a + b) & (b++)"),
            "wide-loop-bound": source.replace("i < 12;", "i < 256;"),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, text in variants.items():
                with self.subTest(source=label):
                    candidate = Path(scratch) / f"unproved-{label}.c"
                    candidate.write_text(text)
                    guest = candidate.with_suffix(".malbolge")
                    refused = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/int-unsigned-unproved-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=45,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

            candidate = Path(scratch) / "int-unsigned-ast.c"
            candidate.write_text(source)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/int-unsigned-ast-v1",
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            declaration = next(
                node
                for node in nodes
                if node["kind"] == "variable-declaration" and node.get("name") == "a"
            )
            converted = next(
                node
                for node in nodes
                if node["kind"] == "cast-expression"
                and node["parent"] == declaration["id"]
            )
            leaf = next(
                node
                for node in nodes
                if node["kind"] == "integer-literal"
                and node["parent"] == converted["id"]
            )
            bound = next(
                node
                for node in nodes
                if node["kind"] == "cast-expression"
                and node.get("constant_integer") == "12"
            )
            alterations = (
                ("cast-value", converted, "constant_integer", "2"),
                ("cast-type", converted, "type", "i32"),
                ("cast-operation", converted, "operation", "lvalue-to-rvalue"),
                ("cast-reference", converted, "reference", "forged@0"),
                ("leaf-type", leaf, "type", "u32"),
                ("leaf-value", leaf, "literal", "2"),
                ("leaf-parent", leaf, "parent", declaration["id"]),
                ("bound-value", bound, "constant_integer", "11"),
            )
            for label, node, field, value in alterations:
                with self.subTest(ast=label):
                    altered = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    index = cast(int, node["id"]) - 1
                    altered["nodes"][index][field] = value
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(altered).encode(),
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_uninitialized_unsigned_local_written_before_guest_use(self) -> None:
        """A declared-then-assigned C local must reach the real guest."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        declaration = "unsigned next = (a + b) & 255U;"
        self.assertEqual(original.count(declaration), 1)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for variant in ("direct", "branch"):
                with self.subTest(variant=variant):
                    assignment = "next = (a + b) & 255U;"
                    if variant == "branch":
                        assignment = (
                            "if (a == 0U) {\n"
                            "            next = (a + b) & 255U;\n"
                            "        } else {\n"
                            "            next = (a + b) & 255U;\n"
                            "        }"
                        )
                    source = Path(scratch) / f"uninitialized-{variant}.c"
                    source.write_text(
                        original.replace(
                            declaration,
                            "unsigned next;\n        " + assignment,
                        )
                    )
                    guest = source.with_suffix(".malbolge")
                    compiled = subprocess.run(
                        [sys.executable, "-B", str(DRIVER),
                         "--repository-tools", "--source-id",
                         f"tests/uninitialized-{variant}-fibonacci-v1",
                         "--capsule", "--output", str(guest), str(source)],
                        capture_output=True, check=False, timeout=150,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    previous, current = 1, 1
                    oracle = bytearray()
                    for _ in range(12):
                        following = (previous + current) & 255
                        oracle.append(
                            following & 31 if following % 2 == 0
                            else (following ^ 0x1A) & 31
                        )
                        previous, current = current, following
                    self.assertEqual(oracle.hex(), "02191f08170f020d03101303")
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin",
                             "--report-steps"],
                            input=supplied, capture_output=True,
                            check=False, timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, oracle)
                        self.assertRegex(
                            executed.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_uninitialized_unsigned_local_rejects_reads_and_forgery(self) -> None:
        """An uninitialized local is not an implicit zero or a valid read."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        declaration = "unsigned next = (a + b) & 255U;"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, replacement in {
                "read": "unsigned next;\n        putchar((int)next);",
                "compound": "unsigned next;\n        next += (a + b) & 255U;",
                "increment": "unsigned next;\n        next++;",
                "unwritten-branch": (
                    "unsigned next;\n        if (a == 0U) {\n"
                    "            next = (a + b) & 255U;\n        }"
                ),
            }.items():
                source = Path(scratch) / f"uninitialized-invalid-{label}.c"
                source.write_text(original.replace(declaration, replacement))
                guest = source.with_suffix(".malbolge")
                result = subprocess.run(
                    [sys.executable, "-B", str(DRIVER),
                     "--repository-tools", "--source-id",
                     f"tests/uninitialized-invalid-{label}-v1",
                     "--capsule", "--output", str(guest), str(source)],
                    capture_output=True, check=False, timeout=45,
                )
                self.assertNotEqual(result.returncode, 0, label)
                self.assertFalse(guest.exists(), label)
            valid = Path(scratch) / "uninitialized-ast.c"
            valid.write_text(original.replace(
                declaration,
                "unsigned next;\n        next = (a + b) & 255U;",
            ))
            normalized = subprocess.run(
                [str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                 "--resource-dir", str(RESOURCE), "--source-id",
                 "tests/uninitialized-ast-v1", str(valid)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            parsed = json.loads(normalized.stdout)
            node = next(n for n in parsed["nodes"] if
                        n["kind"] == "variable-declaration" and
                        n.get("name") == "next")
            for label, updates in {
                "wrong-type": {"type": "i32"},
                "extra-metadata": {"operation": "="},
                "past-name-end": {"span": {
                    **node["span"], "end": {
                        **node["span"]["end"],
                        "byte": node["span"]["end"]["byte"] + 1,
                        "column": node["span"]["end"]["column"] + 1,
                    },
                }},
            }.items():
                forged = json.loads(normalized.stdout)
                forged["nodes"][node["id"] - 1].update(updates)
                guest = Path(scratch) / f"uninitialized-forged-{label}.malbolge"
                result = subprocess.run(
                    [str(ADAPTER), "--layout-backend", str(LAYOUT),
                     "--capsule", "--output", str(guest)],
                    input=json.dumps(forged).encode(),
                    capture_output=True, check=False, timeout=30,
                )
                self.assertNotEqual(result.returncode, 0, label)
                self.assertFalse(guest.exists(), label)

    def test_else_if_chain_full_fibonacci_guest_parity(self) -> None:
        """All three C arms must be proven; the real VM emits all bytes."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        expected = bytes.fromhex("02191f08170f020d03101303")
        previous, current = 1, 1
        hits = [0, 0, 0]
        outputs = bytearray()
        for _ in range(12):
            next_value = (previous + current) & 255
            if (next_value & 1) == 0:
                hits[0] += 1
                outputs.append(next_value & 31)
            elif (next_value & 2) != 0:
                hits[1] += 1
                outputs.append((next_value ^ 0x1A) & 31)
            else:
                hits[2] += 1
                outputs.append((next_value & 31) ^ 0x1A)
            previous, current = current, next_value
        self.assertTrue(all(hits), hits)
        self.assertEqual(bytes(outputs), expected)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-else-if.c"
            _written = source.write_text(else_if_masked_fibonacci_source())
            guest = Path(scratch) / "fibonacci-else-if.malbolge"
            command = [
                sys.executable, "-B", str(DRIVER), "--repository-tools",
                "--source-id", "tests/fibonacci-else-if-v1", "--capsule",
                "--output", str(guest), str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied, capture_output=True, check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(
                    executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                )

    def test_else_if_chain_refuses_unproved_source_and_forged_ast(self) -> None:
        """Even unselected C arms and nested Clang ancestry remain checked."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source_text = else_if_masked_fibonacci_source()
        odd_expression = "((next ^ 0x1AU) & 31U)"
        final_expression = "((next & 31U) ^ 0x1AU)"
        self.assertIn(odd_expression, source_text)
        self.assertIn(final_expression, source_text)
        cases = {
            "undefined-third-arm": source_text.replace(
                final_expression, "((next & 31U) / 0U)"
            ),
            "undefined-skipped-else-if": source_text.replace(
                "((next & 1U) == 0U)", "((next & 1U) <= 1U)"
            ).replace(odd_expression, "((next ^ 0x1AU) / 0U)"),
            "unbraced-else-if": source_text.replace(
                "} else if ((next & 2U) != 0U) {\n"
                + "            putchar((int)((next ^ 0x1AU) & 31U));\n"
                + "        } else {",
                "} else if ((next & 2U) != 0U)\n"
                + "            putchar((int)((next ^ 0x1AU) & 31U));\n"
                + "        else {",
            ),
            "excessive-chain-depth": source_text.replace(
                "} else {\n"
                + "            putchar((int)((next & 31U) ^ 0x1AU));",
                ("} else if ((next & 4U) != 0U) {\n"
                 + "            putchar((int)((next ^ 0x1AU) & 31U));\n") * 4
                + "        } else {\n"
                + "            putchar((int)((next & 31U) ^ 0x1AU));",
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, variant in cases.items():
                with self.subTest(label=label):
                    source = Path(scratch) / f"{label}.c"
                    _written = source.write_text(variant)
                    guest = Path(scratch) / f"{label}.malbolge"
                    rejected = subprocess.run(
                        [sys.executable, "-B", str(DRIVER),
                         "--repository-tools", "--source-id",
                         f"tests/else-if-{label}-v1", "--capsule",
                         "--output", str(guest), str(source)],
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertIn(b"normalized frontend rejected: Unsupported", rejected.stderr)
                    self.assertFalse(guest.exists(), label)
            source = Path(scratch) / "else-if-ast.c"
            _written = source.write_text(source_text)
            normalized = subprocess.run(
                [str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                 "--resource-dir", str(RESOURCE), "--source-id",
                 "tests/else-if-ast-v1", str(source)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            parsed = cast(dict[str, object], json.loads(normalized.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            chain = [node for node in nodes if node["kind"] == "if-statement"]
            self.assertEqual(len(chain), 2)
            outer, nested = chain
            self.assertEqual(nested["parent"], outer["id"])
            nested_span = cast(dict[str, dict[str, int]], nested["span"])
            altered_end = nested_span["end"]["byte"] - 1
            for label, mutation in (
                ("wrong-parent", {"parent": outer["parent"]}),
                ("unexpected-metadata", {"operation": "="}),
                ("wrong-kind", {"kind": "while-statement"}),
                ("truncated-else-if", {"span": {
                    **nested_span, "end": {
                        **nested_span["end"], "byte": altered_end,
                    },
                }}),
            ):
                with self.subTest(label=label):
                    altered = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(normalized.stdout),
                    )
                    altered["nodes"][cast(int, nested["id"]) - 1].update(mutation)
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    result = subprocess.run(
                        [str(ADAPTER), "--layout-backend", str(LAYOUT),
                         "--output", str(guest), "--capsule"],
                        input=json.dumps(altered).encode(),
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_wide_unsigned_c_literals_reach_real_fibonacci_guest(self) -> None:
        """C u32 expression leaves retain their full intermediate value."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        previous, current = 1, 1
        oracle = bytearray()
        for _ in range(12):
            following = (previous + current) % 256
            oracle.append((following if following % 2 == 0 else following ^ 26) & 31)
            previous, current = current, following
        expected = bytes(oracle)
        self.assertEqual(expected, bytes.fromhex("02191f08170f020d03101303"))
        variants = {
            "modulo-256": "(a + b) % 256U",
            "large-intermediate": "((a + b) + 65536U) % 256U",
            "wrapping-u32": "((a + b) + 4294967295U + 1U) % 256U",
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for name, expression in variants.items():
                with self.subTest(variant=name):
                    source = Path(scratch) / f"wide-{name}.c"
                    _written = source.write_text(
                        wide_unsigned_masked_fibonacci_source(expression)
                    )
                    guest = Path(scratch) / f"wide-{name}.malbolge"
                    compiled = subprocess.run(
                        [sys.executable, "-B", str(DRIVER),
                         "--repository-tools", "--source-id",
                         f"tests/fibonacci-{name}-v1", "--capsule",
                         "--output", str(guest), str(source)],
                        capture_output=True, check=False, timeout=180,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied, capture_output=True, check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertRegex(
                            executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_stored_unsigned_c_values_reach_real_fibonacci_guest(self) -> None:
        """Full C u32 locals survive reads, writes, wrap and guest byte output."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) % 256
            selected = following if following % 2 == 0 else following ^ 26
            expected.append(selected & 31)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        cases = {
            "wide-read": (
                "unsigned wide = a + b + 65536U;\n"
                "        unsigned next = wide % 256U;"
            ),
            "wide-compound-write": (
                "unsigned wide = a + b + 65536U;\n"
                "        wide -= 65536U;\n"
                "        unsigned next = wide % 256U;"
            ),
            "wide-wrapping-write": (
                "unsigned wide = a + b + 65536U;\n"
                "        wide += 4294901760U;\n"
                "        unsigned next = wide % 256U;"
            ),
            "wide-standalone-step": (
                "unsigned wide = a + b + 65535U;\n"
                "        ++wide;\n"
                "        unsigned next = wide % 256U;"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, statements in cases.items():
                with self.subTest(case=label):
                    source = Path(scratch) / f"stored-{label}.c"
                    _written = source.write_text(
                        stored_unsigned_masked_fibonacci_source(statements)
                    )
                    guest = Path(scratch) / f"stored-{label}.malbolge"
                    compiled = subprocess.run(
                        [sys.executable, "-B", str(DRIVER),
                         "--repository-tools", "--source-id",
                         f"tests/stored-{label}-v1", "--capsule",
                         "--output", str(guest), str(source)],
                        capture_output=True, check=False, timeout=180,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied, capture_output=True, check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, bytes(expected))
                        self.assertRegex(
                            executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_stored_unsigned_c_values_refuse_invalid_source_and_ast(self) -> None:
        """Unproved source types, arithmetic and output ranges remain closed."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = stored_unsigned_masked_fibonacci_source(
            "unsigned wide = a + b + 65536U;\n"
            "        unsigned next = wide % 256U;"
        )
        cases = {
            "unproved-u64-local": original.replace("65536U", "4294967296UL"),
            "undefined-wide-divisor": original.replace("wide % 256U", "wide % 0U"),
            "out-of-range-guest-output": original.replace(
                "putchar((int)(next & 31U));", "putchar((int)wide);"
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, variant in cases.items():
                with self.subTest(source=label):
                    source = Path(scratch) / f"invalid-stored-{label}.c"
                    _written = source.write_text(variant)
                    guest = Path(scratch) / f"invalid-stored-{label}.malbolge"
                    rejected = subprocess.run(
                        [sys.executable, "-B", str(DRIVER),
                         "--repository-tools", "--source-id",
                         f"tests/invalid-stored-{label}-v1", "--capsule",
                         "--output", str(guest), str(source)],
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, rejected.stderr)
                    self.assertFalse(guest.exists(), label)
            source = Path(scratch) / "stored-ast.c"
            _written = source.write_text(original)
            normalized = subprocess.run(
                [str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                 "--resource-dir", str(RESOURCE), "--source-id",
                 "tests/stored-wide-ast-v1", str(source)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            parsed = cast(dict[str, object], json.loads(normalized.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            wide = next(
                node for node in nodes
                if node["kind"] == "integer-literal"
                and node.get("literal") == "65536"
            )
            for label, change in (
                ("mismatched-literal", {"constant_integer": "65535"}),
                ("wrong-type", {"type": "u64"}),
                ("wrong-parent", {"parent": cast(int, wide["parent"]) + 1}),
                ("unexpected-reference", {"reference": "wide@0"}),
            ):
                with self.subTest(ast=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(normalized.stdout),
                    )
                    forged["nodes"][cast(int, wide["id"]) - 1].update(change)
                    guest = Path(scratch) / f"forged-stored-{label}.malbolge"
                    rejected = subprocess.run(
                        [str(ADAPTER), "--layout-backend", str(LAYOUT),
                         "--output", str(guest), "--capsule"],
                        input=json.dumps(forged).encode(),
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_wide_unsigned_c_literals_refuse_invalid_source_and_ast(self) -> None:
        """Unproved widths, malformed leaves and guest outputs fail closed."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = wide_unsigned_masked_fibonacci_source(
            "((a + b) + 65536U) % 256U"
        )
        source_cases = {
            "too-wide-type": original.replace("65536U", "4294967296U"),
            "out-of-range-output": original.replace(
                "((a + b) + 65536U) % 256U", "256U"
            ).replace("putchar((int)(next & 31U));", "putchar((int)next);"),
            "zero-divisor": original.replace("% 256U", "% 0U"),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for name, variant in source_cases.items():
                with self.subTest(source=name):
                    source = Path(scratch) / f"invalid-{name}.c"
                    _written = source.write_text(variant)
                    guest = Path(scratch) / f"invalid-{name}.malbolge"
                    rejected = subprocess.run(
                        [sys.executable, "-B", str(DRIVER),
                         "--repository-tools", "--source-id",
                         f"tests/invalid-wide-{name}-v1", "--capsule",
                         "--output", str(guest), str(source)],
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, rejected.stderr)
                    self.assertFalse(guest.exists())
            source = Path(scratch) / "wide-ast.c"
            _written = source.write_text(original)
            normalized = subprocess.run(
                [str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                 "--resource-dir", str(RESOURCE), "--source-id",
                 "tests/wide-unsigned-ast-v1", str(source)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            parsed = cast(dict[str, object], json.loads(normalized.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            wide = next(
                node for node in nodes
                if node["kind"] == "integer-literal"
                and node.get("literal") == "65536"
            )
            for label, change in (
                ("mismatched-value", {"constant_integer": "65537"}),
                ("out-of-range", {"literal": "4294967296",
                                  "constant_integer": "4294967296"}),
                ("wrong-width", {"type": "u64"}),
                ("wrong-parent", {"parent": cast(int, wide["parent"]) + 1}),
                ("unexpected-effect", {"operation": "+"}),
            ):
                with self.subTest(ast=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(normalized.stdout),
                    )
                    forged["nodes"][cast(int, wide["id"]) - 1].update(change)
                    guest = Path(scratch) / f"forged-wide-{label}.malbolge"
                    rejected = subprocess.run(
                        [str(ADAPTER), "--layout-backend", str(LAYOUT),
                         "--output", str(guest), "--capsule"],
                        input=json.dumps(forged).encode(),
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_high_bit_xor_metameric_fibonacci_guest_parity(self) -> None:
        """Different source expressions emit the same twelve actual guest bytes."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        even = "putchar((int)(next & 31U));"
        odd = "putchar((int)((next ^ 0x1AU) & 31U));"
        self.assertEqual(original.count(even), 1)
        self.assertEqual(original.count(odd), 1)
        expected = bytearray()
        previous, current = 1, 1
        for _ in range(12):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            expected.append(selected & 31)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        # The two high-bit masks are deliberately distinct. For either
        # branch, masking five low bits after XOR must remove the mutation.
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for seed in (0x20, 0x40):
                with self.subTest(seed=seed):
                    for value in (0, 1, 2, 31, 32, 63, 255):
                        self.assertEqual(
                            ((value ^ seed) & 31), value & 31
                        )
                    changed = original.replace(
                        even,
                        f"putchar((int)((next ^ 0x{seed:02X}U) & 31U));",
                    ).replace(
                        odd,
                        "putchar((int)(((next ^ 0x1AU) ^ "
                        f"0x{seed:02X}U) & 31U));",
                    )
                    source = Path(scratch) / f"fib-high-xor-{seed}.c"
                    source.write_text(changed)
                    guest = Path(scratch) / f"fib-high-xor-{seed}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/fibonacci-high-xor-{seed}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=150,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [
                                str(VM),
                                str(guest),
                                "--input-stdin",
                                "--report-steps",
                            ],
                            input=supplied,
                            check=False,
                            capture_output=True,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertRegex(
                            executed.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_postfix_for_induction_preserves_complete_c_guest_stream(self) -> None:
        """A discarded i++ controls twelve actual source-proven byte effects."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        self.assertEqual(original.count("++i"), 1)
        changed = original.replace("++i", "i++")
        previous, current = 1, 1
        oracle = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            oracle.append(selected & 31)
            previous, current = current, following
        self.assertEqual(bytes(oracle), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-postfix.c"
            source.write_text(changed)
            guest = Path(scratch) / "fibonacci-postfix.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/fibonacci-postfix-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, oracle)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            for label, variant in (("decrement", changed.replace("i++", "i--")),):
                rejected = Path(scratch) / f"rejected-{label}.c"
                rejected.write_text(variant)
                rejected_guest = Path(scratch) / f"rejected-{label}.malbolge"
                attempt = subprocess.run(
                    [*command[:-2], str(rejected_guest), str(rejected)],
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertNotEqual(attempt.returncode, 0, label)
                self.assertIn(b"Unsupported", attempt.stderr, label)
                self.assertFalse(rejected_guest.exists(), label)

    def test_compound_for_induction_emits_complete_masked_fibonacci(self) -> None:
        """A proven i += 1U controls twelve real guest output effects."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        self.assertEqual(original.count("++i"), 1)
        changed = original.replace("++i", "i += 1U")
        previous, current = 1, 1
        oracle = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            oracle.append(selected & 31)
            previous, current = current, following
        self.assertEqual(bytes(oracle), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-compound.c"
            source.write_text(changed)
            guest = Path(scratch) / "fibonacci-compound.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/fibonacci-compound-induction-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, oracle)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            for label, variant in (
                ("two-step", changed.replace("i += 1U", "i += 2U")),
                ("subtraction", changed.replace("i += 1U", "i -= 1U")),
                ("wrong-symbol", changed.replace("i += 1U", "b += 1U")),
            ):
                rejected_source = Path(scratch) / f"invalid-{label}.c"
                rejected_source.write_text(variant)
                refused = Path(scratch) / f"invalid-{label}.malbolge"
                attempt = subprocess.run(
                    [*command[:-2], str(refused), str(rejected_source)],
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertNotEqual(attempt.returncode, 0, label)
                self.assertFalse(refused.exists(), label)

    def test_strided_for_induction_emits_complete_masked_fibonacci(self) -> None:
        """A two-step induction controls a twelve-effect C recurrence."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        self.assertEqual(original.count("i = 0U"), 1)
        self.assertEqual(original.count("++i"), 1)
        changed = original.replace("i = 0U", "i = 1U").replace(
            "++i", "i += 2U"
        ).replace("i < 12U", "i < 25U")
        previous, current = 1, 1
        oracle = bytearray()
        for _ in range(1, 25, 2):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            oracle.append(selected & 31)
            previous, current = current, following
        self.assertEqual(bytes(oracle), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-stride-two.c"
            source.write_text(changed)
            guest = Path(scratch) / "fibonacci-stride-two.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/fibonacci-stride-two-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, oracle)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            for label, variant in (
                ("zero-step", changed.replace("i += 2U", "i += 0U")),
                ("decrement", changed.replace("i += 2U", "i -= 2U")),
                ("foreign-counter", changed.replace("i += 2U", "b += 2U")),
                ("unbounded-step", changed.replace("i += 2U", "i += 13U")),
                ("too-many-trips", changed.replace("i < 25U", "i < 27U")),
            ):
                rejected_source = Path(scratch) / f"invalid-{label}.c"
                rejected_source.write_text(variant)
                refused = Path(scratch) / f"invalid-{label}.malbolge"
                attempt = subprocess.run(
                    [*command[:-2], str(refused), str(rejected_source)],
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertNotEqual(attempt.returncode, 0, label)
                self.assertFalse(refused.exists(), label)

    def test_assignment_form_for_induction_full_fibonacci_guest_parity(self) -> None:
        """Ordinary C assignment can advance a bounded, source-checked for."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        assert original.count("++i") == 1
        previous, current = 1, 1
        oracle = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            oracle.append((following if following % 2 == 0 else following ^ 26) & 31)
            previous, current = current, following
        self.assertEqual(bytes(oracle), bytes.fromhex("02191f08170f020d03101303"))
        ascending = original.replace("++i", "i = i + 1U")
        descending = (
            original.replace("i = 0U", "i = 24U")
            .replace("i < 12U", "i > 0U")
            .replace("++i", "i = i - 2U")
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source_text in (
                ("ascending", ascending),
                ("descending-stride", descending),
            ):
                with self.subTest(case=label):
                    source = Path(scratch) / f"for-assign-{label}.c"
                    source.write_text(source_text)
                    guest = Path(scratch) / f"for-assign-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/for-assign-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=180,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, oracle)
                        self.assertRegex(
                            executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                        )

    def test_assignment_form_for_induction_refuses_unproved_source(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        source_text = original.replace("++i", "i = i + 1U")
        invalid = (
            ("zero-stride", source_text.replace("i = i + 1U", "i = i + 0U")),
            ("large-stride", source_text.replace("i = i + 1U", "i = i + 13U")),
            ("backward", source_text.replace("i = i + 1U", "i = i - 1U")),
            ("foreign-read", source_text.replace("i = i + 1U", "i = b + 1U")),
            ("different-operator", source_text.replace("i = i + 1U", "i = i * 1U")),
            ("nested-expression", source_text.replace("i = i + 1U", "i = i + (1U)")),
            ("unproved-spacing", source_text.replace("i = i + 1U", "i=i+1U")),
            ("extra-effect", source_text.replace("i = i + 1U", "i = i + 1U, b = 0U")),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, text in invalid:
                with self.subTest(case=label):
                    source = Path(scratch) / f"invalid-for-assign-{label}.c"
                    source.write_text(text)
                    guest = Path(scratch) / f"invalid-for-assign-{label}.malbolge"
                    rejected = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/invalid-for-assign-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=45,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_assignment_form_for_induction_refuses_forged_ast(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "for-assignment.c"
            source.write_text(MASKED_FIBONACCI.read_text().replace("++i", "i = i + 1U"))
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/for-assignment-forgery-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            loop = next(n for n in nodes if n["kind"] == "for-statement")
            assignment = next(
                n
                for n in nodes
                if n["parent"] == loop["id"] and n.get("operation") == "="
            )
            left = next(
                n
                for n in nodes
                if n["parent"] == assignment["id"]
                and n["kind"] == "declaration-reference-expression"
            )
            add = next(
                n
                for n in nodes
                if n["parent"] == assignment["id"] and n.get("operation") == "+"
            )
            cast_node = next(
                n
                for n in nodes
                if n["parent"] == add["id"] and n["kind"] == "cast-expression"
            )
            right = next(n for n in nodes if n["parent"] == cast_node["id"])
            literal = next(
                n
                for n in nodes
                if n["parent"] == add["id"] and n["kind"] == "integer-literal"
            )
            for label, node_id, field, replacement in (
                ("assignment-operator", assignment["id"], "operation", "+="),
                ("rhs-operator", add["id"], "operation", "-"),
                ("lhs-symbol", left["id"], "reference", "other@0"),
                ("rhs-symbol", right["id"], "reference", "other@0"),
                ("rhs-parent", add["id"], "parent", loop["id"]),
                ("load-parent", cast_node["id"], "parent", assignment["id"]),
                ("literal-value", literal["id"], "literal", "2"),
                ("extra-metadata", add["id"], "reference", "i@0"),
            ):
                with self.subTest(case=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]], json.loads(frontend.stdout)
                    )
                    forged["nodes"][cast(int, node_id) - 1][field] = replacement
                    guest = Path(scratch) / f"forged-for-assign-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                    self.assertFalse(guest.exists(), label)

    def test_standalone_local_steps_complete_while_fibonacci(self) -> None:
        """Source-local ++/-- actually advance twelve checked while trips."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        induction = "for (unsigned i = 0U; i < 12U; ++i) {"
        assert original.count(induction) == 1
        assert original.count("        b = next;") == 1
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            expected.append(selected & 31)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, start, guard, step in (
                ("prefix-up", 0, "<", "++i"),
                ("postfix-up", 0, "<", "i++"),
                ("prefix-down", 12, ">", "--i"),
                ("postfix-down", 12, ">", "i--"),
            ):
                with self.subTest(case=label):
                    text = original.replace(
                        induction,
                        f"unsigned i = {start}U;\n    while (i {guard} "
                        f"{12 if guard == '<' else 0}U) {{",
                    ).replace(
                        "        b = next;", f"        b = next;\n        {step};"
                    )
                    source = Path(scratch) / f"while-step-{label}.c"
                    source.write_text(text)
                    guest = Path(scratch) / f"while-step-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/while-step-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=180,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((0, 255, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertRegex(
                            executed.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_standalone_local_steps_refuse_source_and_ast_forgery(self) -> None:
        """Unbounded, hidden or forged unary writes cannot publish a guest."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        source_text = original.replace(
            "for (unsigned i = 0U; i < 12U; ++i) {",
            "unsigned i = 0U;\n    while (i < 12U) {",
        ).replace("        b = next;", "        b = next;\n        ++i;")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "while-step-ast.c"
            source.write_text(source_text)
            normalized = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/while-step-forgery-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            parsed = json.loads(normalized.stdout)
            step = next(
                node
                for node in parsed["nodes"]
                if node["kind"] == "unary-expression" and node.get("operation") == "++"
            )
            read = next(
                node for node in parsed["nodes"] if node["parent"] == step["id"]
            )
            foreign = next(
                node
                for node in parsed["nodes"]
                if node["kind"] == "variable-declaration" and node.get("name") == "next"
            )
            for label, target, mutation in (
                ("wrong-parent", step, {"parent": 2}),
                ("wrong-operator", step, {"operation": "~"}),
                ("extra-metadata", step, {"name": "not-a-write"}),
                ("wrong-destination", read, {"reference": foreign["reference"]}),
                ("forged-prefix", read, {"span": step["span"]}),
            ):
                with self.subTest(case=label):
                    changed = json.loads(normalized.stdout)
                    changed["nodes"][target["id"] - 1].update(mutation)
                    guest = Path(scratch) / f"while-step-forged-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(changed).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertIn(b"Unsupported", refused.stderr, label)
                    self.assertFalse(guest.exists(), label)
            for label, invalid in (
                ("underflow", source_text.replace("++i;", "--i;")),
                ("noncontiguous", source_text.replace("++i;", "++ i;")),
            ):
                with self.subTest(case=label):
                    invalid_source = Path(scratch) / f"while-step-{label}.c"
                    invalid_source.write_text(invalid)
                    guest = Path(scratch) / f"while-step-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/while-step-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(invalid_source),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertIn(b"Unsupported", refused.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_unsigned_boolean_local_drives_full_fibonacci_guest(self) -> None:
        """A stored unsigned comparison must select real C branch effects."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        condition = "if ((next & 1U) == 0U) {"
        self.assertEqual(original.count(condition), 1)
        previous, current = 1, 1
        oracle = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            selected = following if following & 1 == 0 else following ^ 0x1A
            oracle.append(selected & 31)
            previous, current = current, following
        self.assertEqual(oracle.hex(), "02191f08170f020d03101303")
        expressions = {
            "comparison": "((next & 1U) == 0U)",
            "negated": "!((next & 1U) != 0U)",
            "ordered": "((next & 1U) < 1U)",
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, expression in expressions.items():
                with self.subTest(case=label):
                    source = Path(scratch) / f"boolean-{label}.c"
                    source.write_text(original.replace(
                        condition,
                        f"unsigned even = {expression};\n        if (even) {{",
                    ))
                    guest = source.with_suffix(".malbolge")
                    compiled = subprocess.run(
                        [sys.executable, "-B", str(DRIVER),
                         "--repository-tools", "--source-id",
                         f"tests/boolean-{label}-fibonacci-v1", "--capsule",
                         "--output", str(guest), str(source)],
                        capture_output=True, check=False, timeout=120,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied, capture_output=True, check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, oracle)
                        self.assertRegex(
                            executed.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )
            for label, expression in {
                "side-effect": "((next++ & 1U) == 0U)",
                "undefined-division": "((next / 0U) == 0U)",
                "signed-cast": "(((int)next & 1) == 0)",
                "impure-call": "((putchar(70) & 1) == 0)",
            }.items():
                source = Path(scratch) / f"invalid-boolean-{label}.c"
                source.write_text(original.replace(
                    condition,
                    f"unsigned even = {expression};\n        if (even) {{",
                ))
                guest = source.with_suffix(".malbolge")
                refused = subprocess.run(
                    [sys.executable, "-B", str(DRIVER),
                     "--repository-tools", "--source-id",
                     f"tests/invalid-boolean-{label}-v1", "--capsule",
                     "--output", str(guest), str(source)],
                    capture_output=True, check=False, timeout=45,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr, label)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_boolean_local_forged_ast_refuses(self) -> None:
        """Do not mistake a forged signed result for a proven C Boolean."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        source_text = original.replace(
            "if ((next & 1U) == 0U) {",
            "unsigned even = ((next & 1U) == 0U);\n        if (even) {",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "boolean-ast.c"
            source.write_text(source_text)
            normalized = subprocess.run(
                [str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                 "--resource-dir", str(RESOURCE), "--source-id",
                 "tests/boolean-forged-ast-v1", str(source)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            parsed = json.loads(normalized.stdout)
            nodes = parsed["nodes"]
            boolean = next(
                node for node in nodes
                if node["kind"] == "variable-declaration"
                and node.get("name") == "even"
            )
            cast = next(
                node for node in nodes
                if node["parent"] == boolean["id"]
                and node["kind"] == "cast-expression"
            )
            group = next(
                node for node in nodes
                if node["parent"] == cast["id"]
                and node["kind"] == "parenthesized-expression"
            )
            comparison = next(
                node for node in nodes
                if node["parent"] == group["id"]
                and node["kind"] == "binary-expression"
            )
            cases = (
                ("explicit-operation", cast, {"operation": "lvalue-to-rvalue"}),
                ("wrong-type", cast, {"type": "i32"}),
                ("nonboolean-operand", group, {"type": "u32"}),
                ("unsupported-predicate", comparison, {"operation": "&"}),
                ("wrong-parent", comparison, {"parent": boolean["id"]}),
                ("extra-metadata", cast, {"name": "forged"}),
                ("cast-span", cast, {"span": {
                    **cast["span"],
                    "end": {
                        **cast["span"]["end"],
                        "byte": cast["span"]["end"]["byte"] + 1,
                        "column": cast["span"]["end"]["column"] + 1,
                    },
                }}),
            )
            for label, target, update in cases:
                with self.subTest(case=label):
                    changed = json.loads(normalized.stdout)
                    changed["nodes"][target["id"] - 1].update(update)
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    rejected = subprocess.run(
                        [str(ADAPTER), "--layout-backend", str(LAYOUT),
                         "--output", str(guest), "--capsule"],
                        input=json.dumps(changed).encode(),
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertIn(b"Unsupported", rejected.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_compound_assignment_fibonacci_guest_parity(self) -> None:
        """Compound C transfers retain the full twelve-byte guest oracle."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        self.assertEqual(original.count("b = next;"), 1)
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            expected.append(selected & 31)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, transfer in (
                ("xor", "b ^= b ^ next;"),
                ("add", "b += next - b;"),
                ("sub", "b -= b - next;"),
            ):
                with self.subTest(transfer=label):
                    source = Path(scratch) / f"compound-{label}.c"
                    source.write_text(original.replace("b = next;", transfer))
                    guest = Path(scratch) / f"compound-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/compound-{label}-fibonacci-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=180,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertRegex(
                            executed.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_bitwise_compound_fibonacci_guest_and_rejections(self) -> None:
        """Real C bitwise updates preserve a complete conditional recurrence."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        self.assertEqual(original.count("b = next;"), 1)
        source_text = original.replace(
            "b = next;", "b |= next;\n        b &= next;"
        )
        # For each iteration, (old_b | next) & next == next for unsigned C.
        previous, current = 1, 1
        oracle = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            oracle.append((following if following % 2 == 0 else
                           following ^ 0x1A) & 31)
            previous, current = current, (current | following) & following
        self.assertEqual(bytes(oracle), bytes.fromhex("02191f08170f020d03101303"))

        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-bitwise-compound.c"
            source.write_text(source_text)
            guest = Path(scratch) / "fibonacci-bitwise-compound.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable, "-B", str(DRIVER), "--repository-tools",
                    "--source-id", "tests/bitwise-compound-fibonacci-v1",
                    "--capsule", "--output", str(guest), str(source),
                ],
                capture_output=True, check=False, timeout=180,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied, capture_output=True, check=False, timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, oracle)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

            for label, altered in (
                ("split-token", source_text.replace("b |= next;", "b | = next;")),
                ("zero-divisor", source_text.replace(
                    "b &= next;", "b &= (next / 0U);"
                )),
                ("signed-cast", source_text.replace(
                    "b &= next;", "b &= (int)next;"
                )),
            ):
                invalid = Path(scratch) / f"{label}.c"
                invalid.write_text(altered)
                rejected = Path(scratch) / f"{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable, "-B", str(DRIVER), "--repository-tools",
                        "--source-id", f"tests/bitwise-{label}-invalid-v1",
                        "--capsule", "--output", str(rejected), str(invalid),
                    ],
                    capture_output=True, check=False, timeout=45,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertFalse(rejected.exists(), label)

            normalized = subprocess.run(
                [
                    str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                    "--resource-dir", str(RESOURCE), "--source-id",
                    "tests/bitwise-ast-v1", str(source),
                ],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            parsed = json.loads(normalized.stdout)
            target = next(
                node for node in parsed["nodes"]
                if node["kind"] == "compound-assignment-expression"
                and node.get("operation") == "&="
            )
            for label, update in (
                ("forged-operator", {"operation": "<<="}),
                ("forged-parent", {"parent": 2}),
                ("forged-metadata", {"name": "wrong"}),
            ):
                changed = json.loads(normalized.stdout)
                changed["nodes"][target["id"] - 1].update(update)
                rejected = Path(scratch) / f"{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER), "--layout-backend", str(LAYOUT),
                        "--output", str(rejected), "--capsule",
                    ],
                    input=json.dumps(changed).encode(),
                    capture_output=True, check=False, timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr, label)
                self.assertFalse(rejected.exists(), label)

    def test_wide_compound_fibonacci_guest_and_rejections(self) -> None:
        """Unsigned compound arithmetic preserves full u32 state and source."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        self.assertEqual(original.count("b = next;"), 1)
        transfer = (
            "unsigned wide = next + 65536U;\n"
            "        wide %= 256U;\n"
            "        wide <<= 1U;\n"
            "        wide >>= 1U;\n"
            "        b *= 0U;\n"
            "        b += wide;\n"
            "        b /= 1U;"
        )
        source_text = original.replace("b = next;", transfer)
        previous, current = 1, 1
        oracle = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            oracle.append((following if following % 2 == 0 else
                           following ^ 0x1A) & 31)
            wide = (following + 65536) % 256
            wide = (wide << 1) & 0xFFFFFFFF
            wide >>= 1
            previous, current = current, ((current * 0) + wide) // 1
        self.assertEqual(bytes(oracle), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-wide-compound.c"
            source.write_text(source_text)
            guest = Path(scratch) / "fibonacci-wide-compound.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable, "-B", str(DRIVER), "--repository-tools",
                    "--source-id", "tests/wide-compound-fibonacci-v1",
                    "--capsule", "--output", str(guest), str(source),
                ],
                capture_output=True, check=False, timeout=180,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied, capture_output=True, check=False, timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, oracle)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

            for label, altered in (
                ("shift32", source_text.replace("wide <<= 1U;", "wide <<= 32U;")),
                ("divzero", source_text.replace("b /= 1U;", "b /= 0U;")),
                ("modzero", source_text.replace("wide %= 256U;", "wide %= 0U;")),
                ("split-shift", source_text.replace("wide <<= 1U;", "wide << = 1U;")),
            ):
                invalid = Path(scratch) / f"{label}.c"
                invalid.write_text(altered)
                rejected = Path(scratch) / f"{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable, "-B", str(DRIVER), "--repository-tools",
                        "--source-id", f"tests/wide-{label}-invalid-v1",
                        "--capsule", "--output", str(rejected), str(invalid),
                    ],
                    capture_output=True, check=False, timeout=45,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertFalse(rejected.exists(), label)

            normalized = subprocess.run(
                [
                    str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                    "--resource-dir", str(RESOURCE), "--source-id",
                    "tests/wide-compound-ast-v1", str(source),
                ],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            parsed = json.loads(normalized.stdout)
            shift = next(
                node for node in parsed["nodes"]
                if node["kind"] == "compound-assignment-expression"
                and node.get("operation") == "<<="
            )
            for label, update in (
                ("wrong-token-width", {"operation": "&="}),
                ("wrong-parent", {"parent": 2}),
                ("unexpected-metadata", {"name": "forged"}),
            ):
                changed = json.loads(normalized.stdout)
                changed["nodes"][shift["id"] - 1].update(update)
                rejected = Path(scratch) / f"{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER), "--layout-backend", str(LAYOUT),
                        "--output", str(rejected), "--capsule",
                    ],
                    input=json.dumps(changed).encode(),
                    capture_output=True, check=False, timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr, label)
                self.assertFalse(rejected.exists(), label)

    def test_compound_assignment_refuses_unproved_source_and_ast(self) -> None:
        """Wrong operators, destination symbols and AST geometry fail closed."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        source_text = original.replace("b = next;", "b ^= b ^ next;")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "compound-source.c"
            source.write_text(source_text)
            normalized = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/compound-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            parsed = json.loads(normalized.stdout)
            assignment = next(
                node
                for node in parsed["nodes"]
                if node["kind"] == "compound-assignment-expression"
                and node.get("operation") == "^="
            )
            left = next(
                node
                for node in parsed["nodes"]
                if node["parent"] == assignment["id"]
                and node["kind"] == "declaration-reference-expression"
            )
            transfer = next(
                node
                for node in parsed["nodes"]
                if node["kind"] == "variable-declaration" and node.get("name") == "next"
            )
            for label, target, update in (
                ("wrong-operator", assignment, {"operation": "/="}),
                ("wrong-parent", assignment, {"parent": 2}),
                ("wrong-destination", left, {"reference": transfer["reference"]}),
                ("extra-metadata", assignment, {"name": "forged"}),
                (
                    "broken-operator-width",
                    left,
                    {
                        "span": {
                            "begin": left["span"]["begin"],
                            "end": {
                                **left["span"]["end"],
                                "byte": left["span"]["end"]["byte"] + 1,
                                "column": left["span"]["end"]["column"] + 1,
                            },
                        }
                    },
                ),
            ):
                with self.subTest(case=label):
                    changed = json.loads(normalized.stdout)
                    changed["nodes"][target["id"] - 1].update(update)
                    guest = Path(scratch) / f"{label}.malbolge"
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(changed).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertIn(b"Unsupported", refused.stderr, label)
                    self.assertFalse(guest.exists(), label)
            invalid = Path(scratch) / "invalid-compound.c"
            invalid.write_text(original.replace("b = next;", "b /= (next - next);"))
            guest = Path(scratch) / "invalid-compound.malbolge"
            refused = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/invalid-compound-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(invalid),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(guest.exists())

    def test_shadowed_loop_local_preserves_outer_fibonacci_state(self) -> None:
        """A nested `b` is distinct from the recurrence's enclosing `b`."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            shadow = (following ^ 0x1A) & 31
            expected.append((following & 31) if following % 2 == 0 else shadow)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        source_text = shadowed_masked_fibonacci_source()
        updated = source_text.replace(
            "            unsigned b = (next ^ 0x1AU) & 31U;",
            "            unsigned b = next & 31U;\n"
            "            b = b ^ 0x1AU;",
        )
        self.assertNotEqual(updated, source_text)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, variant in (("declaration", source_text), ("write", updated)):
                with self.subTest(label=label):
                    source = Path(scratch) / f"shadowed-{label}.c"
                    source.write_text(variant)
                    guest = Path(scratch) / f"shadowed-{label}.malbolge"
                    command = [
                        sys.executable, "-B", str(DRIVER), "--repository-tools",
                        "--source-id", f"tests/shadowed-{label}-v1", "--capsule",
                        "--output", str(guest), str(source),
                    ]
                    compiled = subprocess.run(
                        command, capture_output=True, check=False, timeout=180,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied, capture_output=True, check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertRegex(
                            executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                        )

    def test_shadowed_local_rejects_forged_binding_and_bad_source(self) -> None:
        """Retargeting an inner `b` read to the outer `b` cannot pass."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        text = shadowed_masked_fibonacci_source()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "shadowed-fibonacci.c"
            source.write_text(text)
            normalized = subprocess.run(
                [str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                 "--resource-dir", str(RESOURCE), "--source-id",
                 "tests/shadowed-fibonacci-ast-v1", str(source)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            parsed = json.loads(normalized.stdout)
            declarations = [
                node for node in parsed["nodes"]
                if node["kind"] == "variable-declaration" and node.get("name") == "b"
            ]
            self.assertEqual(len(declarations), 2)
            outer, inner = declarations
            self.assertNotEqual(outer["reference"], inner["reference"])
            reads = [
                node for node in parsed["nodes"]
                if node["kind"] == "declaration-reference-expression"
                and node.get("reference") == inner["reference"]
            ]
            self.assertEqual(len(reads), 1)
            for label, original, update in (
                ("retarget-inner-read", reads[0], {"reference": outer["reference"]}),
                ("retarget-inner-declaration", inner, {"reference": outer["reference"]}),
                ("forged-parent", inner, {"parent": outer["parent"]}),
                ("forged-metadata", inner, {"operation": "="}),
            ):
                with self.subTest(label=label):
                    altered = json.loads(normalized.stdout)
                    altered["nodes"][original["id"] - 1].update(update)
                    guest = Path(scratch) / f"{label}.malbolge"
                    result = subprocess.run(
                        [str(ADAPTER), "--layout-backend", str(LAYOUT),
                         "--output", str(guest), "--capsule"],
                        input=json.dumps(altered).encode(),
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, label)
                    self.assertIn(b"Unsupported", result.stderr, label)
                    self.assertFalse(guest.exists(), label)
            updated_text = text.replace(
                "            unsigned b = (next ^ 0x1AU) & 31U;",
                "            unsigned b = next & 31U;\n"
                "            b = b ^ 0x1AU;",
            )
            rewritten = Path(scratch) / "shadowed-write.c"
            rewritten.write_text(updated_text)
            write_frontend = subprocess.run(
                [str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                 "--resource-dir", str(RESOURCE), "--source-id",
                 "tests/shadowed-write-ast-v1", str(rewritten)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(write_frontend.returncode, 0, write_frontend.stderr)
            write_nodes = json.loads(write_frontend.stdout)["nodes"]
            assignments = [
                node for node in write_nodes
                if node["kind"] == "binary-expression"
                and node.get("operation") == "="
                and node["span"]["begin"]["line"]
                == updated_text[:updated_text.index("b = b ^ 0x1AU;")].count("\n") + 1
            ]
            self.assertEqual(len(assignments), 1)
            written = next(
                node for node in write_nodes
                if node["parent"] == assignments[0]["id"]
                and node["kind"] == "declaration-reference-expression"
            )
            self.assertNotEqual(written["reference"], outer["reference"])
            forged = json.loads(write_frontend.stdout)
            forged["nodes"][written["id"] - 1]["reference"] = outer["reference"]
            refused = Path(scratch) / "retarget-shadow-write.malbolge"
            attempt = subprocess.run(
                [str(ADAPTER), "--layout-backend", str(LAYOUT),
                 "--output", str(refused), "--capsule"],
                input=json.dumps(forged).encode(),
                capture_output=True, check=False, timeout=30,
            )
            self.assertNotEqual(attempt.returncode, 0)
            self.assertIn(b"Unsupported", attempt.stderr)
            self.assertFalse(refused.exists())
            invalid = Path(scratch) / "shadow-undefined.c"
            invalid.write_text(text.replace("(next ^ 0x1AU) & 31U", "next / 0U"))
            guest = Path(scratch) / "undefined.malbolge"
            failed = subprocess.run(
                [sys.executable, "-B", str(DRIVER), "--repository-tools",
                 "--source-id", "tests/shadow-undefined-v1", "--capsule",
                 "--output", str(guest), str(invalid)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(guest.exists())

    def test_branch_local_fibonacci_emits_real_guest_bytes(self) -> None:
        """Scoped conditional temporaries preserve enclosing Fibonacci state."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            chosen = following if following % 2 == 0 else following ^ 0x1A
            expected.append(chosen & 31)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-branch-local.c"
            source.write_text(branch_local_masked_fibonacci_source())
            guest = Path(scratch) / "fibonacci-branch-local.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/fibonacci-branch-local-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=180,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_branch_local_shadow_and_ast_refusal(self) -> None:
        """Skipped branches remain checked; forged scopes never publish."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = branch_local_masked_fibonacci_source()
        self.assertEqual(original.count("i = 0U"), 1)
        self.assertEqual(original.count("    }\n}\n"), 1)
        zero_trip = original.replace("i = 0U", "i = 12U").replace(
            "    }\n}\n", "    }\n    putchar((int)(a + 64U));\n}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-branch-zero.c"
            source.write_text(zero_trip)
            guest = Path(scratch) / "fibonacci-branch-zero.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/fibonacci-branch-zero-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command,
                capture_output=True,
                check=False,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"A")
            for label, mutant in (
                (
                    "unselected-undefined",
                    zero_trip.replace("(next ^ 0x1AU) & 31U", "(next ^ 0x1AU) / 0U"),
                ),
                (
                    "scope-over-depth",
                    zero_trip.replace(
                        "                unsigned selected = next & 31U;\n"
                        "                putchar((int)selected);",
                        "{\n" * 5
                        + "unsigned selected = next & 31U;\n"
                        + "putchar((int)selected);\n"
                        + "}\n" * 5,
                    ),
                ),
            ):
                with self.subTest(label=label):
                    invalid = Path(scratch) / f"invalid-{label}.c"
                    invalid.write_text(mutant)
                    refused = Path(scratch) / f"invalid-{label}.malbolge"
                    attempt = subprocess.run(
                        [*command[:-2], str(refused), str(invalid)],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(attempt.returncode, 0, label)
                    self.assertIn(b"Unsupported", attempt.stderr, label)
                    self.assertFalse(refused.exists(), label)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/fibonacci-branch-forged-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            lexical = next(
                node
                for node in nodes
                if node["kind"] == "compound-statement"
                and any(
                    child["parent"] == node["id"]
                    and child["kind"] == "declaration-statement"
                    and any(
                        decl["parent"] == child["id"] and decl.get("name") == "selected"
                        for decl in nodes
                    )
                    for child in nodes
                )
            )
            for label, key, value in (
                ("parent", "parent", 1),
                ("metadata", "definition", "definition"),
            ):
                with self.subTest(label=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    forged["nodes"][cast(int, lexical["id"]) - 1][key] = value
                    refused = Path(scratch) / f"forged-{label}.malbolge"
                    attempt = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(refused),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(attempt.returncode, 0, label)
                    self.assertIn(b"Unsupported", attempt.stderr, label)
                    self.assertFalse(refused.exists(), label)

    def test_loop_scoped_transfer_emits_complete_masked_fibonacci(self) -> None:
        """A block-local transfer dies each trip, not its enclosing writes."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source_text = scoped_masked_fibonacci_source()
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            expected.append(selected & 31)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-scope.c"
            source.write_text(source_text)
            guest = Path(scratch) / "fibonacci-scope.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/fibonacci-scope-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_loop_scoped_shadow_and_negative_admission(self) -> None:
        """Skipped blocks prove source, and forged lexical identity refuses."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = scoped_masked_fibonacci_source()
        self.assertEqual(original.count("i = 0U"), 1)
        self.assertEqual(original.count("    }\n}\n"), 1)
        zero_trip = original.replace("i = 0U", "i = 12U").replace(
            "    }\n}\n", "    }\n    putchar((int)(a + 64U));\n}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-scope-zero-trip.c"
            source.write_text(zero_trip)
            guest = Path(scratch) / "fibonacci-scope-zero-trip.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/fibonacci-scope-zero-trip-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=90
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(VM), str(guest), "--input-stdin", "--report-steps"],
                input=bytes((255, 0, 128)),
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"A")

            bad = Path(scratch) / "fibonacci-scope-invalid.c"
            bad.write_text(
                zero_trip.replace(
                    "unsigned transfer = next;", "unsigned transfer = next / 0U;"
                )
            )
            rejected_guest = Path(scratch) / "fibonacci-scope-invalid.malbolge"
            rejected = subprocess.run(
                [*command[:-2], str(rejected_guest), str(bad)],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"Unsupported", rejected.stderr)
            self.assertFalse(rejected_guest.exists())

            shallow = (
                "        {\n"
                "            unsigned transfer = next;\n"
                "            a = b;\n"
                "            b = transfer;\n"
                "        }"
            )
            self.assertEqual(zero_trip.count(shallow), 1)
            nested = "unsigned transfer = next;\na = b;\nb = transfer;"
            for _ in range(5):
                nested = "{\n" + nested + "\n}"
            deep_source = Path(scratch) / "fibonacci-scope-too-deep.c"
            deep_source.write_text(zero_trip.replace(shallow, nested))
            deep_guest = Path(scratch) / "fibonacci-scope-too-deep.malbolge"
            too_deep = subprocess.run(
                [*command[:-2], str(deep_guest), str(deep_source)],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(too_deep.returncode, 0)
            self.assertIn(b"Unsupported", too_deep.stderr)
            self.assertFalse(deep_guest.exists())

            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/fibonacci-scope-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            nodes = cast(list[dict[str, object]], json.loads(frontend.stdout)["nodes"])
            scoped = next(
                node
                for node in nodes
                if node["kind"] == "compound-statement"
                and any(
                    child["parent"] == node["id"]
                    and child.get("kind") == "declaration-statement"
                    and any(
                        member["parent"] == child["id"]
                        and member.get("name") == "transfer"
                        for member in nodes
                    )
                    for child in nodes
                )
            )
            for label, key, value in (
                ("parent", "parent", 1),
                ("metadata", "definition", "definition"),
            ):
                with self.subTest(label=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    forged["nodes"][cast(int, scoped["id"]) - 1][key] = value
                    output = Path(scratch) / f"fibonacci-scope-{label}.malbolge"
                    attempt = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(output),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(attempt.returncode, 0, label)
                    self.assertIn(b"Unsupported", attempt.stderr, label)
                    self.assertFalse(output.exists(), label)

    def test_conditional_void_return_ends_complete_c_guest_recurrence(self) -> None:
        """An actual function return stops C before a thirteenth output."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        previous, current = 1, 1
        expected = bytearray()
        for index in range(13):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            expected.append(selected & 31)
            previous, current = current, following
            if index == 11:
                break
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-return.c"
            source.write_text(returning_masked_fibonacci_source())
            guest = Path(scratch) / "fibonacci-return.malbolge"
            command = [
                sys.executable, "-B", str(DRIVER), "--repository-tools",
                "--source-id", "tests/fibonacci-conditional-return-v1",
                "--capsule", "--output", str(guest), str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied, capture_output=True, check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(
                    executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )

    def test_conditional_return_preserves_early_pair_across_loop_forms(self) -> None:
        """Early C function return differs from an exhausted loop bound."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        a, b = 1, 1
        expected = bytearray()
        for index in range(3):
            following = (a + b) & 255
            expected.append(following ^ (83 if following % 2 == 0 else 45))
            a, b = b, following
            if index == 1:
                break
        self.assertEqual(expected, b"Q.")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for loop_kind, selected in (
                ("for", True), ("for", False),
                ("while", True), ("do", True),
            ):
                with self.subTest(loop=loop_kind, selected=selected):
                    label = f"{loop_kind}-{selected}"
                    source = Path(scratch) / f"return-pair-{label}.c"
                    source.write_text(returning_pair_source(
                        loop_kind=loop_kind, selected=selected,
                    ))
                    guest = Path(scratch) / f"return-pair-{label}.malbolge"
                    compiled = subprocess.run(
                        [sys.executable, "-B", str(DRIVER), "--repository-tools",
                         "--source-id", f"tests/return-pair-{label}-v1",
                         "--capsule", "--output", str(guest), str(source)],
                        capture_output=True, check=False, timeout=120,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied, capture_output=True,
                            check=False, timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertRegex(
                            executed.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_conditional_void_return_rejects_unproved_suffix_and_ast(self) -> None:
        """Returned control cannot silently drop later C effects."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        text = returning_masked_fibonacci_source()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "conditional-return.c"
            source.write_text(text)
            normalized = subprocess.run(
                [str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                 "--resource-dir", str(RESOURCE), "--source-id",
                 "tests/conditional-return-ast-v1", str(source)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            original = json.loads(normalized.stdout)
            returns = [
                node for node in original["nodes"]
                if node["kind"] == "return-statement"
            ]
            self.assertEqual(len(returns), 1)
            for label, update in (
                ("parent", {"parent": 1}),
                ("kind", {"kind": "break-statement"}),
                ("metadata", {"operation": "="}),
                ("span", {"span": {
                    **returns[0]["span"],
                    "end": {**returns[0]["span"]["end"],
                            "byte": returns[0]["span"]["end"]["byte"] + 1},
                }}),
            ):
                with self.subTest(label=label):
                    forged = json.loads(normalized.stdout)
                    forged["nodes"][returns[0]["id"] - 1].update(update)
                    guest = Path(scratch) / f"return-{label}.malbolge"
                    rejected = subprocess.run(
                        [str(ADAPTER), "--layout-backend", str(LAYOUT),
                         "--output", str(guest), "--capsule"],
                        input=json.dumps(forged).encode(),
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertIn(b"Unsupported", rejected.stderr, label)
                    self.assertFalse(guest.exists(), label)
            for label, invalid in (
                ("return-tail", text.replace(
                    "            return;",
                    "            return;\n"
                    "            putchar((int)(next & 31U));",
                )),
                ("after-loop", text.replace(
                    "    }\n}", "    }\n    putchar((int)(a & 31U));\n}",
                )),
            ):
                with self.subTest(label=label):
                    invalid_source = Path(scratch) / f"return-{label}.c"
                    invalid_source.write_text(invalid)
                    guest = Path(scratch) / f"return-{label}.malbolge"
                    rejected = subprocess.run(
                        [sys.executable, "-B", str(DRIVER),
                         "--repository-tools", "--source-id",
                         f"tests/return-{label}-v1", "--capsule",
                         "--output", str(guest), str(invalid_source)],
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertIn(b"Unsupported", rejected.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_bounded_for_selected_break_and_continue_guest_parity(self) -> None:
        """An early exit is selected by C state, not guessed by the guest."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for keyword, exit_at in (("break", 6), ("continue", 6)):
                with self.subTest(keyword=keyword):
                    source_text = exiting_masked_fibonacci_source(
                        keyword=keyword, iteration=exit_at
                    )
                    previous, current = 1, 1
                    expected = bytearray()
                    for index in range(12):
                        following = (previous + current) & 255
                        chosen = following if following % 2 == 0 else following ^ 0x1A
                        expected.append(chosen & 31)
                        previous, current = current, following
                        if index == exit_at and keyword == "break":
                            break
                    self.assertEqual(len(expected), 7 if keyword == "break" else 12)
                    source = Path(scratch) / f"fibonacci-{keyword}.c"
                    source.write_text(source_text)
                    guest = Path(scratch) / f"fibonacci-{keyword}.malbolge"
                    command = [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/fibonacci-{keyword}-exit-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(source),
                    ]
                    compiled = subprocess.run(
                        command, capture_output=True, check=False, timeout=180
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertRegex(
                            executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                        )

                    # An effect after the selected exit is not silently dropped.
                    trailing = source_text.replace(
                        f"            {keyword};",
                        f"            {keyword};\n"
                        "            putchar((int)(next & 31U));",
                    )
                    invalid_source = Path(scratch) / f"fibonacci-{keyword}-trailing.c"
                    invalid_source.write_text(trailing)
                    rejected_guest = (
                        Path(scratch) / f"fibonacci-{keyword}-trailing.malbolge"
                    )
                    rejected = subprocess.run(
                        [*command[:-2], str(rejected_guest), str(invalid_source)],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn(b"Unsupported", rejected.stderr)
                    self.assertFalse(rejected_guest.exists())

    def _check_bounded_while_selected_exit(self, keyword: str) -> None:
        """Replay one complete twelve-byte C while exit through the guest."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        with (
            tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch,
            self.subTest(keyword=keyword),
        ):
            source_text = exiting_masked_fibonacci_while_source(
                keyword=keyword
            )
            previous, current = 1, 1
            expected = bytearray()
            for iteration in range(12):
                following = (previous + current) & 255
                selected = (
                    following if following % 2 == 0 else following ^ 0x1A
                )
                expected.append(selected & 31)
                previous, current = current, following
                if keyword == "break" and iteration + 1 == 12:
                    break
            self.assertEqual(len(expected), 12)
            source = Path(scratch) / f"while-{keyword}.c"
            source.write_text(source_text)
            guest = Path(scratch) / f"while-{keyword}.malbolge"
            command = [
                sys.executable, "-B", str(DRIVER), "--repository-tools",
                "--source-id", f"tests/while-{keyword}-exit-v1",
                "--capsule", "--output", str(guest), str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied, capture_output=True, check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(
                    executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )

            invalid = Path(scratch) / f"while-{keyword}-trailing.c"
            invalid.write_text(source_text.replace(
                f"            {keyword};",
                f"            {keyword};\n"
                "            putchar((int)(next & 31U));",
            ))
            rejected_guest = Path(scratch) / f"while-{keyword}-trailing.malbolge"
            rejected = subprocess.run(
                [*command[:-2], str(rejected_guest), str(invalid)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"Unsupported", rejected.stderr)
            self.assertFalse(rejected_guest.exists())

    def test_bounded_while_break_preserves_twelve_guest_bytes(self) -> None:
        self._check_bounded_while_selected_exit("break")

    def test_bounded_while_continue_preserves_twelve_guest_bytes(self) -> None:
        self._check_bounded_while_selected_exit("continue")

    def _check_bounded_do_selected_exit(self, keyword: str) -> None:
        """A complete C do-loop must follow C's body-first exit semantics."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        previous, current = 1, 1
        oracle = bytearray()
        for iteration in range(12):
            following = (previous + current) & 255
            oracle.append(
                (following if following % 2 == 0 else following ^ 0x1A) & 31
            )
            previous, current = current, following
            if keyword == "break" and iteration + 1 == 12:
                break
        self.assertEqual(
            bytes(oracle), bytes.fromhex("02191f08170f020d03101303")
        )
        text = exiting_masked_fibonacci_do_source(keyword=keyword)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / f"do-{keyword}-fib.c"
            source.write_text(text)
            guest = Path(scratch) / f"do-{keyword}-fib.malbolge"
            command = [
                sys.executable, "-B", str(DRIVER), "--repository-tools",
                "--source-id", f"tests/do-{keyword}-fib-v1",
                "--capsule", "--output", str(guest), str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied, capture_output=True, check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, oracle)
                self.assertRegex(
                    executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )
            invalid = Path(scratch) / f"do-{keyword}-trailing.c"
            invalid.write_text(text.replace(
                f"            {keyword};",
                f"            {keyword};\n"
                "            putchar((int)(next & 31U));",
            ))
            rejected_guest = Path(scratch) / f"do-{keyword}-trailing.malbolge"
            rejected = subprocess.run(
                [*command[:-2], str(rejected_guest), str(invalid)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"Unsupported", rejected.stderr)
            self.assertFalse(rejected_guest.exists())

    def test_bounded_do_selected_break_reaches_full_guest(self) -> None:
        self._check_bounded_do_selected_exit("break")

    def test_bounded_do_selected_continue_reaches_full_guest(self) -> None:
        self._check_bounded_do_selected_exit("continue")

    def test_bounded_do_early_break_keeps_pair_guest_output(self) -> None:
        """A do body exits after two effects, before its third true guard."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        induction = "for (unsigned i = 0U; i < 2U; ++i) {"
        transfer = "        b = next;"
        self.assertEqual(original.count(induction), 1)
        self.assertEqual(original.count(transfer), 1)
        source_text = original.replace(
            induction, "unsigned i = 0U;\n    do {"
        ).replace(
            transfer,
            f"{transfer}\n"
            "        i = i + 1U;\n"
            "        if (i == 2U) {\n"
            "            break;\n"
            "        }",
        ).replace("    }\n}", "    } while (i < 3U);\n}")
        a, b = 1, 1
        oracle = bytearray()
        for iteration in range(3):
            following = (a + b) & 255
            oracle.append(following ^ (83 if following % 2 == 0 else 45))
            a, b = b, following
            if iteration + 1 == 2:
                break
        self.assertEqual(bytes(oracle), b"Q.")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "do-early-pair.c"
            source.write_text(source_text)
            guest = Path(scratch) / "do-early-pair.malbolge"
            compiled = subprocess.run(
                [sys.executable, "-B", str(DRIVER), "--repository-tools",
                 "--source-id", "tests/do-early-pair-v1", "--capsule",
                 "--output", str(guest), str(source)],
                capture_output=True, check=False, timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied, capture_output=True, check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, oracle)
                self.assertRegex(
                    executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )

    def test_bounded_do_exit_forged_ast_refuses_publication(self) -> None:
        """A false Clang exit keyword, parent or metadata cannot publish."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "do-break-ast.c"
            source.write_text(
                exiting_masked_fibonacci_do_source(keyword="break")
            )
            normalized = subprocess.run(
                [str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                 "--resource-dir", str(RESOURCE), "--source-id",
                 "tests/do-exit-forged-v1", str(source)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            original = json.loads(normalized.stdout)
            exits = [
                node for node in original["nodes"]
                if node["kind"] == "break-statement"
            ]
            self.assertEqual(len(exits), 1)
            for label, change in (
                ("parent", {"parent": 1}),
                ("keyword", {"kind": "continue-statement"}),
                ("metadata", {"operation": "="}),
            ):
                with self.subTest(label=label):
                    forged = json.loads(normalized.stdout)
                    forged["nodes"][exits[0]["id"] - 1].update(change)
                    guest = Path(scratch) / f"do-exit-forged-{label}.malbolge"
                    refused = subprocess.run(
                        [str(ADAPTER), "--layout-backend", str(LAYOUT),
                         "--output", str(guest), "--capsule"],
                        input=json.dumps(forged).encode(),
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertIn(b"Unsupported", refused.stderr)
                    self.assertFalse(guest.exists())

    def test_bounded_while_early_break_keeps_pair_guest_output(self) -> None:
        """A two-trip C break shortens a loop bounded for three iterations."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        induction = "for (unsigned i = 0U; i < 2U; ++i) {"
        transfer = "        b = next;"
        self.assertEqual(original.count(induction), 1)
        self.assertEqual(original.count(transfer), 1)
        source_text = original.replace(
            induction, "unsigned i = 0U;\n    while (i < 3U) {"
        ).replace(
            transfer,
            f"{transfer}\n"
            "        i = i + 1U;\n"
            "        if (i == 2U) {\n"
            "            break;\n"
            "        }",
        )
        a, b = 1, 1
        oracle = bytearray()
        for iteration in range(3):
            following = (a + b) & 255
            oracle.append(following ^ (83 if following % 2 == 0 else 45))
            a, b = b, following
            if iteration + 1 == 2:
                break
        self.assertEqual(bytes(oracle), b"Q.")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "while-early-pair.c"
            source.write_text(source_text)
            guest = Path(scratch) / "while-early-pair.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable, "-B", str(DRIVER), "--repository-tools",
                    "--source-id", "tests/while-early-pair-v1",
                    "--capsule", "--output", str(guest), str(source),
                ],
                capture_output=True, check=False, timeout=100,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied, capture_output=True, check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, oracle)
                self.assertRegex(
                    executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )

    def test_bounded_while_zero_trip_exit_shadow_discards_effects(self) -> None:
        """A skipped loop must prove its break, but publish no shadow effects."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = exiting_masked_fibonacci_while_source(keyword="break")
        self.assertEqual(original.count("while (i < 13U)"), 1)
        self.assertEqual(original.count("if (i == 12U)"), 1)
        self.assertEqual(original.count("    }\n}"), 1)
        skipped = (
            original.replace("while (i < 13U)", "while (i < 0U)")
            .replace("if (i == 12U)", "if (i == 1U)")
            .replace("    }\n}", "    }\n    putchar((int)(a ^ 64U));\n}")
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "while-skipped-break.c"
            source.write_text(skipped)
            guest = Path(scratch) / "while-skipped-break.malbolge"
            command = [
                sys.executable, "-B", str(DRIVER), "--repository-tools",
                "--source-id", "tests/while-skipped-break-v1",
                "--capsule", "--output", str(guest), str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=85
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--input-stdin", "--report-steps"],
                input=bytes((255, 0, 128)), capture_output=True,
                check=False, timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"A")
            self.assertRegex(
                executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
            )
            invalid = Path(scratch) / "while-skipped-invalid.c"
            invalid.write_text(skipped.replace("b = next;", "b = next / 0U;"))
            rejected_guest = Path(scratch) / "while-skipped-invalid.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(rejected_guest), str(invalid)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(rejected_guest.exists())

    def test_bounded_while_exit_forged_ast_refuses(self) -> None:
        """Clang while exit keyword, provenance and parent must all agree."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "while-break-forged.c"
            source.write_text(exiting_masked_fibonacci_while_source(keyword="break"))
            normalized = subprocess.run(
                [str(FRONTEND), "--guest-include", str(GUEST_INCLUDE),
                 "--resource-dir", str(RESOURCE), "--source-id",
                 "tests/while-exit-forged-v1", str(source)],
                capture_output=True, check=False, timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            original = json.loads(normalized.stdout)
            exits = [
                node for node in original["nodes"] if node["kind"] == "break-statement"
            ]
            self.assertEqual(len(exits), 1)
            for label, change in (
                ("parent", {"parent": 1}),
                ("keyword", {"kind": "continue-statement"}),
                ("operation", {"operation": "="}),
            ):
                with self.subTest(label=label):
                    forged = json.loads(normalized.stdout)
                    forged["nodes"][exits[0]["id"] - 1].update(change)
                    guest = Path(scratch) / f"while-forged-{label}.malbolge"
                    rejected = subprocess.run(
                        [str(ADAPTER), "--layout-backend", str(LAYOUT),
                         "--output", str(guest), "--capsule"],
                        input=json.dumps(forged).encode(),
                        capture_output=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn(b"Unsupported", rejected.stderr)
                    self.assertFalse(guest.exists())

    def test_bounded_for_exit_forged_ast_refuses(self) -> None:
        """Only exact Clang exit ancestry and keyword spans are admissible."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-break-ast.c"
            source.write_text(
                exiting_masked_fibonacci_source(keyword="break", iteration=6)
            )
            normalized = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/fibonacci-break-ast-v1",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            original = json.loads(normalized.stdout)
            exits = [
                node for node in original["nodes"] if node["kind"] == "break-statement"
            ]
            self.assertEqual(len(exits), 1)
            target = exits[0]
            for label, mutation in (
                ("wrong-parent", {"parent": 1}),
                ("wrong-keyword", {"kind": "continue-statement"}),
                ("unexpected-op", {"operation": "="}),
            ):
                with self.subTest(label=label):
                    forged = json.loads(normalized.stdout)
                    forged["nodes"][target["id"] - 1].update(mutation)
                    output = Path(scratch) / f"forged-{label}.malbolge"
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(output),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, label)
                    self.assertIn(b"Unsupported", result.stderr, label)
                    self.assertFalse(output.exists(), label)

    def test_unbraced_for_conditional_emits_complete_fibonacci_guest(self) -> None:
        """An unbraced for may directly parent one source-checked if/else."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source_text = unbraced_conditional_for_fibonacci_source()
        a, b = 1, 1
        expected = bytearray()
        for _ in range(12):
            next_value = (a + b) & 255
            expected.append(
                (next_value & 31) if next_value % 2 == 0 else ((next_value ^ 0x1A) & 31)
            )
            a, b = b, next_value
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "unbraced-for-if.c"
            source.write_text(source_text)
            guest = Path(scratch) / "unbraced-for-if.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/unbraced-for-if-fibonacci-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", b"\xff\x00\x80"):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")
            for label, altered_source in (
                (
                    "conditional-side-effect",
                    source_text.replace("((a + b) & 1U)", "((a++ + b) & 1U)"),
                ),
                (
                    "counter-write",
                    source_text.replace(
                        "            a = b;", "            i = 0U;\n            a = b;"
                    ),
                ),
                (
                    "unsupported-switch-effect",
                    source_text.replace(
                        "            b = next;\n        }\n}",
                        "            switch (next) { default: b = next; }\n"
                        "        }\n}",
                    ),
                ),
            ):
                with self.subTest(label=label):
                    bad = Path(scratch) / f"unbraced-for-if-{label}.c"
                    bad.write_text(altered_source)
                    rejected_guest = Path(scratch) / f"{label}.malbolge"
                    rejected = subprocess.run(
                        [*command[:-2], str(rejected_guest), str(bad)],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertIn(b"Unsupported", rejected.stderr, label)
                    self.assertFalse(rejected_guest.exists(), label)

    def test_unbraced_for_conditional_forged_ast_refuses_guest(self) -> None:
        """No fabricated braces, control parent, or ending may be supplied."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "unbraced-for-if-ast.c"
            source.write_text(unbraced_conditional_for_fibonacci_source())
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/unbraced-for-if-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            original = cast(
                dict[str, list[dict[str, object]]], json.loads(frontend.stdout)
            )
            outer = next(n for n in original["nodes"] if n["kind"] == "for-statement")
            conditional = next(
                n for n in original["nodes"] if n["kind"] == "if-statement"
            )
            self.assertEqual(conditional["parent"], outer["id"])
            for label in (
                "wrong-parent",
                "outer-tail",
                "if-tail",
                "unexpected-operation",
                "wrong-arm-parent",
            ):
                with self.subTest(label=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    nodes = forged["nodes"]
                    candidate = nodes[cast(int, conditional["id"]) - 1]
                    if label == "wrong-parent":
                        candidate["parent"] = 2
                    elif label in ("outer-tail", "if-tail"):
                        targeted = (
                            nodes[cast(int, outer["id"]) - 1]
                            if label == "outer-tail"
                            else candidate
                        )
                        span = cast(dict[str, dict[str, int]], targeted["span"])
                        span["end"]["byte"] -= 1
                        span["end"]["column"] -= 1
                    elif label == "unexpected-operation":
                        candidate["operation"] = "="
                    else:
                        arm = next(
                            n
                            for n in nodes
                            if n["kind"] == "compound-statement"
                            and n["parent"] == conditional["id"]
                        )
                        nodes[cast(int, arm["id"]) - 1]["parent"] = outer["id"]
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    rejected = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertIn(b"Unsupported", rejected.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_unbraced_while_conditional_emits_full_fibonacci_guest(self) -> None:
        """A bounded while's sole direct if keeps real C state and output."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source_text = unbraced_conditional_while_fibonacci_source()
        expected = bytearray()
        a, b, i = 1, 1, 0
        while i < 12:
            following = (a + b) & 255
            expected.append(
                (following & 31) if following % 2 == 0 else (following ^ 0x1A) & 31
            )
            a, b, i = b, following, i + 1
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "unbraced-while-if.c"
            source.write_text(source_text)
            guest = Path(scratch) / "unbraced-while-if.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/unbraced-while-if-fibonacci-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", b"\xff\x00\x80"):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")
            for label, bad_source in (
                (
                    "condition-side-effect",
                    source_text.replace("while (i < 12U)", "while (i++ < 12U)"),
                ),
                (
                    "unproved-switch-effect",
                    source_text.replace(
                        "            ++i;\n        }\n}",
                        "            switch (next) { default: ++i; }\n        }\n}",
                    ),
                ),
            ):
                with self.subTest(label=label):
                    rejected_guest = Path(scratch) / f"{label}.malbolge"
                    bad = Path(scratch) / f"{label}.c"
                    bad.write_text(bad_source)
                    rejected = subprocess.run(
                        [*command[:-2], str(rejected_guest), str(bad)],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertIn(b"Unsupported", rejected.stderr, label)
                    self.assertFalse(rejected_guest.exists(), label)

    def test_unbraced_while_conditional_forged_ast_refuses_guest(self) -> None:
        """The while's direct if must preserve its genuine Clang ancestry."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "unbraced-while-if-ast.c"
            source.write_text(unbraced_conditional_while_fibonacci_source())
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/unbraced-while-if-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            normalized = cast(
                dict[str, list[dict[str, object]]], json.loads(frontend.stdout)
            )
            enclosing = next(
                node
                for node in normalized["nodes"]
                if node["kind"] == "while-statement"
            )
            conditional = next(
                node for node in normalized["nodes"] if node["kind"] == "if-statement"
            )
            self.assertEqual(conditional["parent"], enclosing["id"])
            for label in ("wrong-parent", "while-tail", "if-tail", "if-operator"):
                with self.subTest(label=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    nodes = forged["nodes"]
                    chosen = nodes[cast(int, conditional["id"]) - 1]
                    if label == "wrong-parent":
                        chosen["parent"] = 2
                    elif label == "if-operator":
                        chosen["operation"] = "="
                    else:
                        target = (
                            nodes[cast(int, enclosing["id"]) - 1]
                            if label == "while-tail"
                            else chosen
                        )
                        span = cast(dict[str, dict[str, int]], target["span"])
                        span["end"]["byte"] -= 1
                        span["end"]["column"] -= 1
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    rejected = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertIn(b"Unsupported", rejected.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_unbraced_nested_for_emits_complete_fibonacci_on_guest(self) -> None:
        """An outer for may contain exactly one unbraced inner for body."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source_text = unbraced_nested_masked_fibonacci_source()
        a, b = 1, 1
        expected = bytearray()
        for _row in range(3):
            for _col in range(4):
                following = (a + b) & 255
                selected = (
                    following & 31 if following % 2 == 0 else (following ^ 0x1A) & 31
                )
                expected.append(selected)
                a, b = b, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "unbraced-nested.c"
            source.write_text(source_text)
            guest = Path(scratch) / "unbraced-nested.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/unbraced-nested-for-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")
            bad = Path(scratch) / "unbraced-nested-counter-write.c"
            bad.write_text(
                source_text.replace(
                    "        a = b;", "        row = 0U;\n        a = b;"
                )
            )
            refused_guest = Path(scratch) / "unbraced-nested-counter-write.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(refused_guest), str(bad)],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(refused_guest.exists())

    def test_unbraced_nested_for_forged_ast_refuses_guest(self) -> None:
        """A direct child for must have true parentage and an exact tail span."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "unbraced-nested-ast.c"
            source.write_text(unbraced_nested_masked_fibonacci_source())
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/unbraced-nested-for-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(
                dict[str, list[dict[str, object]]], json.loads(frontend.stdout)
            )
            outer, inner = [
                node for node in parsed["nodes"] if node["kind"] == "for-statement"
            ]
            self.assertEqual(inner["parent"], outer["id"])
            for label in ("wrong-parent", "outer-tail", "inner-tail"):
                with self.subTest(label=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    nodes = forged["nodes"]
                    if label == "wrong-parent":
                        nodes[cast(int, inner["id"]) - 1]["parent"] = 2
                    else:
                        targeted = outer if label == "outer-tail" else inner
                        span = cast(
                            dict[str, dict[str, int]],
                            nodes[cast(int, targeted["id"]) - 1]["span"],
                        )
                        span["end"]["byte"] -= 1
                        span["end"]["column"] -= 1
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    rejected = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(rejected.returncode, 0, label)
                    self.assertIn(b"Unsupported", rejected.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_nested_for_induction_emits_complete_masked_fibonacci(self) -> None:
        """A 3-by-4 loop nest carries real C state across all twelve outputs."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source_text = nested_masked_fibonacci_source()
        previous, current = 1, 1
        expected = bytearray()
        for _row in range(3):
            for _col in range(4):
                following = (previous + current) & 255
                selected = following if following % 2 == 0 else following ^ 0x1A
                expected.append(selected & 31)
                previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-nested.c"
            source.write_text(source_text)
            guest = Path(scratch) / "fibonacci-nested.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/fibonacci-nested-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command,
                capture_output=True,
                check=False,
                timeout=180,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            for label, mutation in (
                ("outer-write", "row = 0U;"),
                ("inner-write", "col = 0U;"),
            ):
                bad_source = Path(scratch) / f"nested-{label}.c"
                bad_source.write_text(
                    source_text.replace(
                        "        a = b;",
                        f"        {mutation}\n        a = b;",
                    )
                )
                bad_guest = Path(scratch) / f"nested-{label}.malbolge"
                rejected = subprocess.run(
                    [*command[:-2], str(bad_guest), str(bad_source)],
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertNotEqual(rejected.returncode, 0, label)
                self.assertIn(b"Unsupported", rejected.stderr, label)
                self.assertFalse(bad_guest.exists(), label)

    def test_nested_zero_trip_discards_output_and_proves_shadow(self) -> None:
        """Every skipped inner body remains checked without emitting effects."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = nested_masked_fibonacci_source()
        self.assertEqual(original.count("col = 0U"), 1)
        self.assertEqual(original.count("    }\n}\n"), 1)
        zero_trip = original.replace("col = 0U", "col = 4U").replace(
            "    }\n}\n",
            "    }\n    putchar((int)(a + 64U));\n}\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "nested-zero-trip.c"
            source.write_text(zero_trip)
            guest = Path(scratch) / "nested-zero-trip.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/nested-zero-trip-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command,
                capture_output=True,
                check=False,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertRegex(
                    executed.stderr,
                    rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                )
            bad = Path(scratch) / "nested-shadow-invalid.c"
            bad.write_text(zero_trip.replace("next ^ 0x1AU", "next / 0U"))
            rejected_guest = Path(scratch) / "nested-shadow-invalid.malbolge"
            rejected = subprocess.run(
                [*command[:-2], str(rejected_guest), str(bad)],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"Unsupported", rejected.stderr)
            self.assertFalse(rejected_guest.exists())

    def test_three_level_for_nesting_refuses_without_guest(self) -> None:
        """Nested induction is explicitly bounded to two lexical levels."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = nested_masked_fibonacci_source()
        third_level = original.replace(
            "for (unsigned col = 0U; col < 4U; ++col) {",
            "for (unsigned col = 0U; col < 4U; ++col) {\n"
            "            for (unsigned deep = 0U; deep < 1U; ++deep) {",
        ).replace(
            "        b = next;\n        }\n    }",
            "        b = next;\n            }\n        }\n    }",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "nested-three-level.c"
            source.write_text(third_level)
            guest = Path(scratch) / "nested-three-level.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/nested-three-level-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"Unsupported", compiled.stderr)
            self.assertFalse(guest.exists())

    def test_nested_for_induction_rejects_forged_ast(self) -> None:
        """A forged nested parent or induction symbol never publishes guest code."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "nested-ast.c"
            source.write_text(nested_masked_fibonacci_source())
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/nested-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            outer, inner = [n for n in nodes if n["kind"] == "for-statement"]
            outer_symbol = next(
                n["reference"]
                for n in nodes
                if n["kind"] == "variable-declaration" and n["name"] == "row"
            )
            inner_increment = next(
                n
                for n in nodes
                if n["parent"] == inner["id"] and n.get("operation") == "++"
            )
            inner_read = next(n for n in nodes if n["parent"] == inner_increment["id"])
            for label in ("parent", "outer-counter", "step"):
                with self.subTest(label=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    changed_nodes = forged["nodes"]
                    if label == "parent":
                        changed_nodes[cast(int, inner["id"]) - 1]["parent"] = outer[
                            "id"
                        ]
                    elif label == "outer-counter":
                        changed_nodes[cast(int, inner_read["id"]) - 1]["reference"] = (
                            outer_symbol
                        )
                    else:
                        changed_nodes[cast(int, inner_increment["id"]) - 1][
                            "operation"
                        ] = "--"
                    guest = Path(scratch) / f"nested-forged-{label}.malbolge"
                    attempt = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(attempt.returncode, 0, label)
                    self.assertIn(b"Unsupported", attempt.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_not_equal_for_induction_emits_complete_masked_fibonacci(self) -> None:
        """A bounded != loop must reach its endpoint in real guest output."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            expected.append(selected & 31)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, start, condition, step in (
                ("ascending", "0U", "i != 12U", "++i"),
                ("descending", "12U", "i != 0U", "--i"),
                ("strided", "1U", "i != 25U", "i += 2U"),
            ):
                with self.subTest(label=label):
                    changed = (
                        original.replace("i = 0U", f"i = {start}")
                        .replace("i < 12U", condition)
                        .replace("++i", step)
                    )
                    source = Path(scratch) / f"not-equal-{label}.c"
                    source.write_text(changed)
                    guest = Path(scratch) / f"not-equal-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/not-equal-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=180,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, expected)
                        self.assertRegex(
                            executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                        )

    def test_not_equal_for_zero_trip_preserves_following_guest_effect(self) -> None:
        """Equality at entry skips checked C effects, not later output."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        ).read_text()
        self.assertEqual(original.count("while (i < 3U)"), 1)
        changed = original.replace(
            "while (i < 3U)", "for (unsigned j = 0U; j != 0U; ++j)"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "zero-trip-not-equal.c"
            source.write_text(changed)
            guest = Path(scratch) / "zero-trip-not-equal.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/not-equal-zero-trip-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=100,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", b"\xff\x00\x80"):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                # The skipped putchar is not emitted. The three-iteration
                # following do-while computes ASCII A independently.
                self.assertEqual(executed.stdout, b"A")
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_not_equal_for_induction_rejects_unreachable_bounds(self) -> None:
        """Do not publish guest effects for invalid or nonterminating != loops."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        unequal = original.replace("i < 12U", "i != 12U")
        cases = (
            ("thirteen-trips", unequal.replace("i != 12U", "i != 13U")),
            ("wrong-direction", unequal.replace("++i", "--i")),
            ("wrong-counter", unequal.replace("++i", "++b")),
            (
                "overshoot",
                unequal.replace("i != 12U", "i != 11U").replace("++i", "i += 2U"),
            ),
            ("zero-stride", unequal.replace("++i", "i += 0U")),
            ("wrong-test", unequal.replace("i != 12U", "i == 12U")),
            (
                "descending-overshoot",
                unequal.replace("i = 0U", "i = 12U")
                .replace("i != 12U", "i != 1U")
                .replace("++i", "i -= 2U"),
            ),
            (
                "zero-trip-invalid-body",
                unequal.replace("i = 0U", "i = 12U").replace(
                    "next ^ 0x1AU", "next * 0x1AU"
                ),
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed in cases:
                with self.subTest(label=label):
                    source = Path(scratch) / f"invalid-neq-{label}.c"
                    source.write_text(changed)
                    guest = Path(scratch) / f"invalid-neq-{label}.malbolge"
                    attempted = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/invalid-neq-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(attempted.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_not_equal_for_induction_rejects_forged_ast(self) -> None:
        """Source spans and typed Clang evidence constrain != admission."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        unequal = MASKED_FIBONACCI.read_text().replace("i < 12U", "i != 12U")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "not-equal-ast.c"
            source.write_text(unequal)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/not-equal-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            loop = next(n for n in nodes if n["kind"] == "for-statement")
            comparison = next(
                n
                for n in nodes
                if n["parent"] == loop["id"] and n.get("operation") == "!="
            )
            increment = next(
                n
                for n in nodes
                if n["parent"] == loop["id"] and n.get("operation") == "++"
            )
            for label in ("shortened", "inclusive", "span", "counter"):
                with self.subTest(label=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    changed_nodes = forged["nodes"]
                    comp = changed_nodes[cast(int, comparison["id"]) - 1]
                    if label == "shortened":
                        comp["operation"] = "<"
                    elif label == "inclusive":
                        comp["operation"] = "<="
                    elif label == "span":
                        span = cast(dict[str, dict[str, int]], comp["span"])
                        span["end"]["byte"] -= 1
                    else:
                        increment_copy = changed_nodes[cast(int, increment["id"]) - 1]
                        read = next(
                            n
                            for n in changed_nodes
                            if n["parent"] == increment_copy["id"]
                            and n["kind"] == "declaration-reference-expression"
                        )
                        read["reference"] = "other@0"
                    guest = Path(scratch) / f"forged-neq-{label}.malbolge"
                    attempt = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(attempt.returncode, 0, label)
                    self.assertIn(b"Unsupported", attempt.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_inclusive_for_induction_emits_complete_masked_fibonacci(self) -> None:
        """Inclusive ascending/descending bounds preserve a full C recurrence."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            expected.append(selected & 31)
            previous, current = current, following
        oracle = bytes(expected)
        self.assertEqual(oracle, bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, start, comparison, step in (
                ("ascending", "0U", "i <= 11U", "++i"),
                ("descending", "12U", "i >= 1U", "--i"),
                ("strided", "1U", "i <= 23U", "i += 2U"),
            ):
                with self.subTest(label=label):
                    changed = (
                        original.replace("i = 0U", f"i = {start}")
                        .replace("i < 12U", comparison)
                        .replace("++i", step)
                    )
                    source = Path(scratch) / f"inclusive-{label}.c"
                    source.write_text(changed)
                    guest = Path(scratch) / f"inclusive-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/inclusive-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=180,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, oracle)
                        self.assertRegex(
                            executed.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_inclusive_for_induction_rejects_bad_sources(self) -> None:
        """Reject unsafe inclusive loops before an output artifact is written."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        inclusive = original.replace("i < 12U", "i <= 11U")
        variants = (
            ("thirteen-trips", inclusive.replace("i <= 11U", "i <= 12U")),
            ("wrong-direction", inclusive.replace("++i", "--i")),
            ("wrong-counter", inclusive.replace("++i", "++b")),
            ("unsupported-test", inclusive.replace("i <= 11U", "i != 11U")),
            (
                "zero-trip-invalid-shadow",
                inclusive.replace("i = 0U", "i = 12U").replace(
                    "next ^ 0x1AU", "next * 0x1AU"
                ),
            ),
            (
                "descending-underflow",
                inclusive.replace("i = 0U", "i = 12U")
                .replace("i <= 11U", "i >= 0U")
                .replace("++i", "--i"),
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, variant in variants:
                with self.subTest(label=label):
                    source = Path(scratch) / f"inclusive-invalid-{label}.c"
                    source.write_text(variant)
                    guest = Path(scratch) / f"inclusive-invalid-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/inclusive-invalid-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(compiled.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_inclusive_for_induction_rejects_forged_ast(self) -> None:
        """A shortened comparison token cannot change source loop semantics."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        inclusive = original.replace("i < 12U", "i <= 11U")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "inclusive-source.c"
            source.write_text(inclusive)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/inclusive-source-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            loop = next(node for node in nodes if node["kind"] == "for-statement")
            comparison = next(
                node
                for node in nodes
                if node["parent"] == loop["id"]
                and node.get("operation") == "<="
            )
            bound = next(
                node
                for node in nodes
                if node["parent"] == comparison["id"]
                and node["kind"] == "integer-literal"
            )
            for label in ("shortened", "reversed", "forged-bound", "span"):
                with self.subTest(label=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    changed_nodes = forged["nodes"]
                    comparison_copy = changed_nodes[cast(int, comparison["id"]) - 1]
                    bound_copy = changed_nodes[cast(int, bound["id"]) - 1]
                    if label == "shortened":
                        comparison_copy["operation"] = "<"
                    elif label == "reversed":
                        comparison_copy["operation"] = ">="
                    elif label == "forged-bound":
                        bound_copy["constant_integer"] = "12"
                        bound_copy["literal"] = "12U"
                    else:
                        span = cast(
                            dict[str, dict[str, int]], comparison_copy["span"]
                        )
                        span["end"]["byte"] -= 1
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    attempt = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(attempt.returncode, 0, label)
                    self.assertIn(b"Unsupported", attempt.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_descending_for_induction_emits_complete_masked_fibonacci(self) -> None:
        """Real guest parity for a source-proven bounded C countdown."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        self.assertEqual(original.count("i = 0U"), 1)
        self.assertEqual(original.count("i < 12U"), 1)
        self.assertEqual(original.count("++i"), 1)
        previous, current = 1, 1
        oracle = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            selected = following if following % 2 == 0 else following ^ 0x1A
            oracle.append(selected & 31)
            previous, current = current, following
        self.assertEqual(bytes(oracle), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, start, step in (
                ("prefix", "12U", "--i"),
                ("postfix", "12U", "i--"),
                ("stride-two", "24U", "i -= 2U"),
            ):
                with self.subTest(label=label):
                    changed = (
                        original.replace("i = 0U", f"i = {start}")
                        .replace("i < 12U", "i > 0U")
                        .replace("++i", step)
                    )
                    source = Path(scratch) / f"countdown-{label}.c"
                    source.write_text(changed)
                    guest = Path(scratch) / f"countdown-{label}.malbolge"
                    command = [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/countdown-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(source),
                    ]
                    compiled = subprocess.run(
                        command, capture_output=True, check=False, timeout=180
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for supplied in (b"", bytes((255, 0, 128))):
                        executed = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=supplied,
                            capture_output=True,
                            check=False,
                            timeout=30,
                        )
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(executed.stdout, oracle)
                        self.assertRegex(
                            executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                        )

    def test_descending_for_induction_invalid_sources_fail_closed(self) -> None:
        """A changed countdown cannot smuggle effects into the guest."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = MASKED_FIBONACCI.read_text()
        changed = (
            original.replace("i = 0U", "i = 24U")
            .replace("i < 12U", "i > 0U")
            .replace("++i", "i -= 2U")
        )
        variants = (
            ("zero-step", changed.replace("i -= 2U", "i -= 0U")),
            ("wide-step", changed.replace("i -= 2U", "i -= 13U")),
            ("wrong-direction", changed.replace("i -= 2U", "i += 2U")),
            ("wrong-counter", changed.replace("i -= 2U", "b -= 2U")),
            ("thirteen-trips", changed.replace("i = 24U", "i = 26U")),
            ("underflow", changed.replace("i = 24U", "i = 23U")),
            ("non-strict", changed.replace("i > 0U", "i >= 0U")),
            (
                "invalid-zero-trip-shadow",
                changed.replace("i = 24U", "i = 0U").replace(
                    "next ^ 0x1AU", "next * 0x1AU"
                ),
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, variant in variants:
                with self.subTest(label=label):
                    source = Path(scratch) / f"invalid-{label}.c"
                    source.write_text(variant)
                    guest = Path(scratch) / f"invalid-{label}.malbolge"
                    attempt = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/countdown-invalid-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(source),
                        ],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(attempt.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_descending_for_induction_rejects_forged_ast(self) -> None:
        """A matching operator cannot compensate for forged C loop evidence."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        changed = (
            MASKED_FIBONACCI.read_text()
            .replace("i = 0U", "i = 24U")
            .replace("i < 12U", "i > 0U")
            .replace("++i", "i -= 2U")
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "countdown-ast.c"
            source.write_text(changed)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/countdown-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            loop = next(node for node in nodes if node["kind"] == "for-statement")
            comparison = next(
                node
                for node in nodes
                if node["parent"] == loop["id"] and node.get("operation") == ">"
            )
            increment = next(
                node
                for node in nodes
                if node["parent"] == loop["id"]
                and node["kind"] == "compound-assignment-expression"
            )
            children = [node for node in nodes if node["parent"] == increment["id"]]
            self.assertEqual(
                [node["kind"] for node in children],
                ["declaration-reference-expression", "integer-literal"],
            )
            read, literal = children
            for label in (
                "comparison",
                "increment",
                "zero-stride",
                "operand",
                "symbol",
                "increment-span",
                "literal-span",
            ):
                with self.subTest(label=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    changed_nodes = forged["nodes"]
                    comparison_copy = changed_nodes[cast(int, comparison["id"]) - 1]
                    increment_copy = changed_nodes[cast(int, increment["id"]) - 1]
                    literal_copy = changed_nodes[cast(int, literal["id"]) - 1]
                    if label == "comparison":
                        comparison_copy["operation"] = ">="
                    elif label == "increment":
                        increment_copy["operation"] = "+="
                    elif label == "zero-stride":
                        literal_copy["constant_integer"] = "0"
                        literal_copy["literal"] = "0"
                    elif label == "operand":
                        literal_copy["literal"] = "1"
                    elif label == "symbol":
                        changed_nodes[cast(int, read["id"]) - 1]["reference"] = (
                            "other@0"
                        )
                    elif label == "increment-span":
                        span = cast(dict[str, dict[str, int]], increment_copy["span"])
                        span["begin"]["byte"] += 1
                    else:
                        span = cast(dict[str, dict[str, int]], literal_copy["span"])
                        span["end"]["byte"] -= 1
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    attempt = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(attempt.returncode, 0, label)
                    self.assertIn(b"Unsupported", attempt.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_compound_for_induction_rejects_forged_ast(self) -> None:
        """A typed += operator alone cannot prove the correct loop step."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        changed = MASKED_FIBONACCI.read_text().replace("++i", "i += 1U")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-compound.c"
            source.write_text(changed)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/fibonacci-compound-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            loop = next(node for node in nodes if node["kind"] == "for-statement")
            increment = next(
                node
                for node in nodes
                if node["parent"] == loop["id"]
                and node["kind"] == "compound-assignment-expression"
            )
            self.assertEqual(increment["operation"], "+=")
            children = [node for node in nodes if node["parent"] == increment["id"]]
            self.assertEqual(
                [node["kind"] for node in children],
                ["declaration-reference-expression", "integer-literal"],
            )
            read, step = children
            self.assertEqual(step["constant_integer"], "1")
            for label in (
                "operator",
                "step",
                "literal",
                "symbol",
                "increment-span",
                "step-span",
            ):
                with self.subTest(label=label):
                    forged = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    modified = forged["nodes"]
                    increment_copy = modified[cast(int, increment["id"]) - 1]
                    step_copy = modified[cast(int, step["id"]) - 1]
                    if label == "operator":
                        increment_copy["operation"] = "-="
                    elif label == "step":
                        # A different supported stride is a valid typed
                        # input, but a stride beyond the bounded proof is not.
                        step_copy["constant_integer"] = "13"
                        step_copy["literal"] = "13"
                    elif label == "literal":
                        step_copy["literal"] = "2"
                    elif label == "symbol":
                        modified[cast(int, read["id"]) - 1]["reference"] = "other@0"
                    elif label == "increment-span":
                        span = cast(dict[str, dict[str, int]], increment_copy["span"])
                        span["begin"]["byte"] += 1
                    else:
                        span = cast(dict[str, dict[str, int]], step_copy["span"])
                        span["end"]["byte"] -= 1
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    attempt = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(forged).encode(),
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertNotEqual(attempt.returncode, 0, label)
                    self.assertIn(b"Unsupported", attempt.stderr, label)
                    self.assertFalse(guest.exists(), label)

    def test_postfix_induction_ast_shape_must_be_source_proven(self) -> None:
        """A forged increment span or symbol cannot publish guest output."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        changed = MASKED_FIBONACCI.read_text().replace("++i", "i++")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-postfix.c"
            source.write_text(changed)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/fibonacci-postfix-ast-v1",
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            loop = next(node for node in nodes if node["kind"] == "for-statement")
            increment = next(
                node
                for node in nodes
                if node["parent"] == loop["id"]
                and node["kind"] == "unary-expression"
                and node.get("operation") == "++"
            )
            read = next(node for node in nodes if node["parent"] == increment["id"])
            self.assertEqual(read["kind"], "declaration-reference-expression")
            for label in ("decrement", "extra-suffix", "foreign-symbol"):
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                node = tampered["nodes"][cast(int, increment["id"]) - 1]
                if label == "decrement":
                    node["operation"] = "--"
                elif label == "extra-suffix":
                    span = cast(dict[str, dict[str, int]], node["span"])
                    span["end"]["byte"] += 1
                    span["end"]["column"] += 1
                else:
                    tampered["nodes"][cast(int, read["id"]) - 1]["reference"] = (
                        "unknown@0"
                    )
                guest = Path(scratch) / f"forged-{label}.malbolge"
                attempt = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertNotEqual(attempt.returncode, 0, label)
                self.assertIn(b"Unsupported", attempt.stderr, label)
                self.assertFalse(guest.exists(), label)

    def test_six_bit_masked_fibonacci_full_c_guest_parity(self) -> None:
        """Twelve source-proven conditional bytes retain all six low bits."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(12):
            following = (previous + current) & 255
            if following % 2 == 0:
                expected.append(following & 63)
            else:
                expected.append((following ^ 0x1A) & 63)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("02191f08170f222d03103323"))
        original = MASKED_FIBONACCI.read_text()
        self.assertIn("next & 31U", original)
        self.assertIn("(next ^ 0x1AU) & 31U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "six-bit-fibonacci.c"
            source.write_text(original.replace("31U", "63U"))
            guest = Path(scratch) / "six-bit-fibonacci.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/six-bit-fibonacci-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=150
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((0, 255, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            altered = Path(scratch) / "six-bit-unsupported.c"
            altered.write_text(
                source.read_text().replace(
                    "((next ^ 0x1AU) & 63U)", "((next ^ 0x1AU) / 0U)"
                )
            )
            rejected_guest = Path(scratch) / "rejected.malbolge"
            rejected = subprocess.run(
                [*command[:-2], str(rejected_guest), str(altered)],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"Unsupported", rejected.stderr)
            self.assertFalse(rejected_guest.exists())

    def test_three_live_relocations_reach_real_guest_from_c(self) -> None:
        """Closed C arithmetic/branch, three actual relocated guest writes."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_three_relocation_branch_stream.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(3):
            next_value = (previous + current) & 255
            if next_value % 2 == 0:
                expected.append((next_value * 40 + 1) & 255)
            else:
                expected.append((next_value * 46 + 24) & 255)
            previous, current = current, next_value
        self.assertEqual(bytes(expected), bytes.fromhex("51a2fe"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "three-relocations.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/three-relocation-c-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                replay = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(replay.returncode, 0, replay.stderr)
                self.assertEqual(replay.stdout, expected)
                self.assertRegex(replay.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            invalid = Path(scratch) / "three-relocations-invalid.c"
            invalid.write_text(source.read_text().replace("next * 46U", "next / 0U"))
            rejected_guest = Path(scratch) / "rejected.malbolge"
            rejected = subprocess.run(
                [*command[:-2], str(rejected_guest), str(invalid)],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"Unsupported", rejected.stderr)
            self.assertFalse(rejected_guest.exists())

    def test_five_effect_recurrence_reaches_guest_after_layout_fix(self) -> None:
        """Project a complete stateful loop, branch and five guest bytes."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_four_relocation_five_output_branch_stream.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(5):
            next_value = (previous + current) & 255
            if next_value % 2 == 0:
                expected.append(((next_value // 2) * 241 + 68) & 255)
            else:
                expected.append(
                    ((next_value // 2) * 212 + (next_value // 8) * 119 + 52)
                    & 255
                )
            previous, current = current, next_value
        self.assertEqual(bytes(expected), bytes.fromhex("3508dc08a3"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "five-effects.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/five-effect-c-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                replay = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(replay.returncode, 0, replay.stderr)
                self.assertEqual(replay.stdout, expected)
                self.assertRegex(replay.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            invalid = Path(scratch) / "five-effects-invalid.c"
            invalid.write_text(source.read_text().replace("next / 2U", "next / 0U"))
            rejected_guest = Path(scratch) / "rejected.malbolge"
            rejected = subprocess.run(
                [*command[:-2], str(rejected_guest), str(invalid)],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b"Unsupported", rejected.stderr)
            self.assertFalse(rejected_guest.exists())

    def test_original_fibonacci_two_iterations_use_guest_source_scratch(self) -> None:
        """The actual C recurrence emits two guest bytes after a forward jump."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler binaries are not built")
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        expected = reference_bytes()[:2]
        self.assertEqual(expected, bytes.fromhex("0259"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-two.c"
            source.write_text(original.replace("i < 12U", "i < 2U"))
            guest = Path(scratch) / "fibonacci-two.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/conditional-fibonacci-two-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                replay = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied,
                    capture_output=True,
                    check=False,
                    timeout=45,
                )
                self.assertEqual(replay.returncode, 0, replay.stderr)
                self.assertEqual(replay.stdout, expected)
                self.assertRegex(replay.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_whole_program_rejection_or_guest_parity(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        if not RESOURCE.is_dir() or not GUEST_INCLUDE.is_dir():
            self.skipTest("pinned Clang resources or includes are absent")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "fibonacci.malbolge"
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--frontend",
                    str(FRONTEND),
                    "--json-adapter",
                    str(ADAPTER),
                    "--layout-backend",
                    str(LAYOUT),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/conditional-fibonacci-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(SOURCE),
                ],
                check=False,
                capture_output=True,
                timeout=20,
            )
            if process.returncode == 0:
                # Future implementation must pass an actual normative VM
                # replay. The host oracle never substitutes for guest output.
                self.assertTrue(guest.is_file())
                execution = subprocess.run(
                    [str(VM), str(guest), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(execution.returncode, 0, execution.stderr)
                self.assertEqual(execution.stdout, reference_bytes())
                self.assertRegex(
                    execution.stderr,
                    rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                )
                return
            # Typed constant/SSA admission succeeds for the full C loop;
            # only the positional guest byte-stream layout lacks a witness.
            self.assertIn(
                b"canonical typed byte bridge rejected: Layout(UnsupportedEffectTrace)",
                process.stderr,
            )
            self.assertNotIn(b"normalized frontend rejected", process.stderr)
            self.assertFalse(guest.exists(), "unwitnessed C published a guest")

    def test_three_iteration_branch_uses_guest_source_scratch(self) -> None:
        """Closed C state selects three bytes, guest computes their output."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler binaries are not built")
        original = SOURCE.read_text()
        expression = "next ^ (0x5AU ^ ((next & 4U) * 17U))"
        expected = bytes((2, 3 ^ 0x5A, 5 ^ (0x5A ^ (4 * 17))))
        self.assertEqual(expected, bytes.fromhex("02591b"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-three-scratch.c"
            source.write_text(
                original.replace("i < 12U", "i < 3U")
                .replace("next ^ 0x5AU", expression)
            )
            guest = Path(scratch) / "fibonacci-three-scratch.malbolge"
            command = [
                sys.executable, "-B", str(DRIVER), "--repository-tools",
                "--source-id", "tests/conditional-fibonacci-three-scratch-v1",
                "--capsule", "--output", str(guest), str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for supplied in (b"", bytes((255, 0, 128))):
                replay = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=supplied, check=False, capture_output=True,
                    timeout=30,
                )
                self.assertEqual(replay.returncode, 0, replay.stderr)
                self.assertEqual(replay.stdout, expected)
                self.assertRegex(replay.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_original_fibonacci_three_output_prefix_on_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        # The even arm emits 2; the odd arm uses source-derived XOR 0x3d.
        expected = bytes((2, 3 ^ 0x3D, 5 ^ 0x3D))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-three.c"
            _written = source.write_text(
                original.replace("i < 12U", "i < 3U").replace(
                    "next ^ 0x5AU", "next ^ 0x3DU"
                )
            )
            guest = Path(scratch) / "fibonacci-three.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/conditional-fibonacci-three-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((0xFF, 0x00, 0x80))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            # An unsupported source operation must not inherit the witness.
            altered = Path(scratch) / "fibonacci-three-unsupported.c"
            altered.write_text(source.read_text().replace("next ^ 0x3DU", "next / 0U"))
            refused_guest = Path(scratch) / "fibonacci-three-unsupported.malbolge"
            refused = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/conditional-fibonacci-three-unsupported-v1",
                    "--capsule",
                    "--output",
                    str(refused_guest),
                    str(altered),
                ],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(refused_guest.exists())

    def test_four_iteration_masked_fibonacci_emits_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        self.assertIn("putchar((int)next);", original)
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(4):
            following = (previous + current) & 255
            expected.append(following ^ (26 if following % 2 == 0 else 61))
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes((24, 62, 56, 18)))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "fibonacci-four-masked.c"
            source.write_text(
                original.replace("i < 12U", "i < 4U")
                .replace("putchar((int)next);", "putchar((int)(next ^ 26U));")
                .replace("next ^ 0x5AU", "next ^ 61U")
            )
            guest = Path(scratch) / "fibonacci-four-masked.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/conditional-fibonacci-four-masked-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, bytes(expected))
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            # An unsupported C effect may not inherit the source witness.
            altered = Path(scratch) / "fibonacci-four-unsupported.c"
            altered.write_text(source.read_text().replace("next ^ 61U", "next / 0U"))
            refused_guest = Path(scratch) / "fibonacci-four-unsupported.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(refused_guest), str(altered)],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(refused_guest.exists())

    def test_unmodified_fibonacci_four_byte_prefix_still_refuses(self) -> None:
        """The P0 original output prefix still lacks a verified guest."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "original-fibonacci-prefix.c"
            source.write_text(original.replace("i < 12U", "i < 4U"))
            guest = Path(scratch) / "original-fibonacci-prefix.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/original-fibonacci-prefix-four-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"Layout(UnsupportedEffectTrace)", compiled.stderr)
            self.assertFalse(guest.exists(), "unwitnessed program published a guest")

    def test_zero_prefix_conditional_loop_reaches_guest(self) -> None:
        """Real guest output may precede data relocation without host I/O."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_zero_prefix_conditional_stream.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(4):
            following = (previous + current) & 255
            if following % 2 == 0:
                expected.append(0 if following == 2 else 63)
            else:
                expected.append(84 if following == 3 else 178)
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("0054b23f"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "zero-prefix.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/zero-prefix-conditional-stream-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            altered = Path(scratch) / "zero-prefix-unsupported.c"
            original = source.read_text()
            self.assertIn("next == 3U", original)
            altered.write_text(original.replace("next == 3U", "next++ == 3U"))
            refused_guest = Path(scratch) / "zero-prefix-unsupported.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(refused_guest), str(altered)],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(refused_guest.exists())

    def test_wrapping_unsigned_recurrence_four_outputs_reach_guest(self) -> None:
        """Source C's unsigned +, - and * wrap at 32 bits before masking."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_wrapping_recurrence_stream.c"
        )
        original = source.read_text()
        self.assertIn("(0U - (a + b)) * 255U", original)
        self.assertIn("(~next + 1U) + (next * 2U)", original)
        a, b = 1, 1
        expected = bytearray()
        for _ in range(4):
            following = a + b
            negated = (0 - following) & 0xFFFF_FFFF
            multiplied = negated * 255
            next_value = (multiplied & 0xFFFF_FFFF) & 255
            complement = ((~next_value) + 1) & 0xFFFF_FFFF
            sum_value = complement + (next_value * 2)
            restored = (sum_value & 0xFFFF_FFFF) & 255
            self.assertGreater(negated, 255)
            self.assertGreater(multiplied, 0xFFFF_FFFF)
            self.assertGreater(sum_value, 0xFFFF_FFFF)
            self.assertEqual((next_value, restored), (following, following))
            expected.append(
                ((restored * 29 + 251) & 255)
                if restored % 2 == 0
                else (((restored // 2) * 73 + 119) & 255)
            )
            a, b = b, restored
        self.assertEqual(bytes(expected), bytes.fromhex("35c009e3"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "wrapping-recurrence.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/unsigned-wrapping-four-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for data in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=data,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            for label, changed in {
                "unmasked-wide-local": original.replace(
                    "unsigned next = ((0U - (a + b)) * 255U) & 255U;",
                    "unsigned next = ((0U - (a + b)) * 255U);",
                ),
                "undefined-divisor": original.replace(
                    "restored / 2U", "restored / 0U"
                ),
                "side-effect": original.replace(
                    "(restored & 1U)", "(restored++ & 1U)"
                ),
                "unproven-signed-cast": original.replace(
                    "~next + 1U", "~(int)next + 1U"
                ),
            }.items():
                altered = Path(scratch) / f"wrapping-invalid-{label}.c"
                _ = altered.write_text(changed)
                refused_guest = altered.with_suffix(".malbolge")
                refused = subprocess.run(
                    [*command[:-2], str(refused_guest), str(altered)],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(refused_guest.exists(), label)

    def test_wide_conditional_loop_four_outputs_reach_guest(self) -> None:
        """Divide/multiply/mask in C, then prove four real guest bytes."""
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(4):
            following = (previous + current) & 255
            expected.append(
                ((following * 29 + 251) & 255)
                if following % 2 == 0
                else (((following // 2) * 73 + 119) & 255)
            )
            previous, current = current, following
        self.assertEqual(bytes(expected), bytes.fromhex("35c009e3"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "wide-loop.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/wide-fibonacci-guest-four-v1",
                "--capsule",
                "--output",
                str(guest),
                str(WIDE_STREAM),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, expected)
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            unsupported = Path(scratch) / "wide-loop-divide-zero.c"
            unsupported.write_text(
                WIDE_STREAM.read_text().replace("next / 2U", "next / 0U")
            )
            refused_guest = Path(scratch) / "wide-loop-divide-zero.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(refused_guest), str(unsupported)],
                check=False,
                capture_output=True,
                timeout=180,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(refused_guest.exists())

    def test_branch_selected_output_inside_bounded_loop_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = LOOP_OUTPUT.read_text()
        self.assertIn("i < 12U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for bound in (12, 7):
                # Independent unsigned C state, predicate and call sequence.
                previous, current = 1, 1
                expected = bytearray()
                for _ in range(bound):
                    following = (previous + current) & 255
                    expected.append(
                        (following ^ following)
                        if following & 1 == 0
                        else (following - following)
                    )
                    previous, current = current, following
                source = Path(scratch) / f"loop-{bound}.c"
                _written = source.write_text(
                    original.replace("i < 12U", f"i < {bound}U")
                )
                guest = Path(scratch) / f"loop-{bound}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/loop-branch-{bound}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(source),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                executed = subprocess.run(
                    [str(VM), str(guest), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, bytes(expected))
                self.assertEqual(
                    executed.stderr,
                    f"malbolge-steps-v1:{bound + 1}\n".encode(),
                )

    def test_repeated_conditional_loop_output_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_repeated_output.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(3):
            following = (previous + current) & 255
            expected.append(following ^ (58 if following % 2 == 0 else 59))
            previous, current = current, following
        self.assertEqual(bytes(expected), b"88>")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "repeated-loop.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/loop-repeated-output-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            execution = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(execution.returncode, 0, execution.stderr)
            self.assertEqual(execution.stdout, bytes(expected))
            self.assertRegex(execution.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            # Shifts lie outside the source-proven arithmetic slice;
            # a modified program must not inherit the valid guest witness.
            mutated = Path(scratch) / "repeated-mutation.c"
            mutated.write_text(source.read_text().replace("next ^ 58U", "next >> 1U"))
            rejected = Path(scratch) / "repeated-mutation.malbolge"
            refused = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/loop-repeated-mutation-v1",
                    "--capsule",
                    "--output",
                    str(rejected),
                    str(mutated),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(rejected.exists())

    def test_nonadjacent_equal_loop_bytes_reach_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_nonadjacent_output.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for index in range(3):
            following = (previous + current) & 255
            expected.append((following - following) + (90 if index % 2 == 0 else 37))
            previous, current = current, following
        self.assertEqual(bytes(expected), b"Z%Z")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "nonadjacent-loop.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/loop-nonadjacent-output-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            execution = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(execution.returncode, 0, execution.stderr)
            self.assertEqual(execution.stdout, bytes(expected))
            self.assertRegex(
                execution.stderr,
                rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
            )
            # An unsupported effect must not inherit the verified guest.
            mutated = Path(scratch) / "nonadjacent-mutation.c"
            mutated.write_text(
                source.read_text().replace("next - next", "next >> next")
            )
            rejected = Path(scratch) / "nonadjacent-mutation.malbolge"
            refused = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/loop-nonadjacent-mutation-v1",
                    "--capsule",
                    "--output",
                    str(rejected),
                    str(mutated),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(rejected.exists())

    def test_three_source_effects_with_identical_bytes_reach_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_nonadjacent_output.c"
        ).read_text()
        self.assertIn("+ 90U", original)
        self.assertIn("+ 37U", original)
        # Three source-evaluated loop outputs, from both branches, converge.
        a, b = 1, 1
        expected = bytearray()
        for _ in range(3):
            next_value = (a + b) & 255
            expected.append((next_value - next_value) + 56)
            a, b = b, next_value
        self.assertEqual(bytes(expected), b"888")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "three-equal-loop.c"
            source.write_text(
                original.replace("+ 90U", "+ 56U").replace("+ 37U", "+ 56U")
            )
            guest = Path(scratch) / "three-equal-loop.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/three-equal-loop-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=180
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for input_bytes in (b"", bytes((255, 0, 128))):
                execution = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=input_bytes,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(execution.returncode, 0, execution.stderr)
                self.assertEqual(execution.stdout, expected)
                self.assertRegex(
                    execution.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                )
            mutated = Path(scratch) / "three-equal-mutation.c"
            mutated.write_text(
                source.read_text().replace("next - next", "next >> next")
            )
            rejected = Path(scratch) / "three-equal-mutation.malbolge"
            refused = subprocess.run(
                [*command[:-2], str(rejected), str(mutated)],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(rejected.exists())

    def test_separate_branch_effects_with_equal_bytes_reach_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        self.assertIn("next ^ 83U", original)
        self.assertIn("next ^ 45U", original)
        # Two different C branches and source SSA values converge on 0x38.
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(2):
            following = (previous + current) & 255
            expected.append(following ^ (58 if following % 2 == 0 else 59))
            previous, current = current, following
        self.assertEqual(bytes(expected), b"88")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "equal-branch-loop.c"
            source.write_text(
                original.replace("next ^ 83U", "next ^ 58U").replace(
                    "next ^ 45U", "next ^ 59U"
                )
            )
            guest = Path(scratch) / "equal-branch-loop.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/equal-branch-loop-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            execution = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(execution.returncode, 0, execution.stderr)
            self.assertEqual(execution.stdout, bytes(expected))
            self.assertRegex(execution.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            mutation = Path(scratch) / "unsupported-equal-branch.c"
            mutation.write_text(source.read_text().replace("next ^ 59U", "next >> 1U"))
            rejected = Path(scratch) / "unsupported-equal-branch.malbolge"
            refused = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/equal-branch-mutation-v1",
                    "--capsule",
                    "--output",
                    str(rejected),
                    str(mutation),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"Unsupported", refused.stderr)
            self.assertFalse(rejected.exists())

    def test_distinct_conditional_loop_outputs_reach_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        )
        previous, current = 1, 1
        expected = bytearray()
        for _ in range(2):
            following = (previous + current) & 255
            expected.append(following ^ (83 if following % 2 == 0 else 45))
            previous, current = current, following
        self.assertEqual(bytes(expected), b"Q.")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "branch-stream.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/loop-distinct-output-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, bytes(expected))
            self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_other_source_proven_loop_pair_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        self.assertIn("next ^ 83U", original)
        self.assertIn("next ^ 45U", original)
        # Independent Fibonacci C arithmetic: 2 ^ 0 = 2, 3 ^ 204 = 207.
        expected = bytes((2, 207))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            changed = Path(scratch) / "other-loop-pair.c"
            _written = changed.write_text(
                original.replace("next ^ 83U", "next ^ 0U").replace(
                    "next ^ 45U", "next ^ 204U"
                )
            )
            guest = Path(scratch) / "other-loop-pair.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/other-loop-pair-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(changed),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, expected)
            self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_original_fibonacci_prefix_with_composed_guest_arithmetic(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        self.assertIn("next ^ 0x5AU", original)
        # The first original value is 2; the odd branch selects 3 ^ 54 = 53.
        expected = bytes((2, 53))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            changed = Path(scratch) / "fib-composed-pair.c"
            _written = changed.write_text(
                original.replace("i < 12U", "i < 2U").replace(
                    "next ^ 0x5AU", "next ^ 54U"
                )
            )
            guest = Path(scratch) / "fib-composed-pair.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/fib-composed-pair-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(changed),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, expected)
            self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_unwitnessed_distinct_loop_stream_does_not_publish_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        self.assertIn("next ^ 83U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            changed = Path(scratch) / "unwitnessed-loop.c"
            _written = changed.write_text(original.replace("next ^ 83U", "next ^ 82U"))
            guest = Path(scratch) / "unwitnessed-loop.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/unwitnessed-loop-distinct-output-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(changed),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(
                b"canonical typed byte bridge rejected: Layout(UnsupportedEffectTrace)",
                compiled.stderr,
            )
            self.assertNotIn(b"normalized frontend rejected", compiled.stderr)
            self.assertFalse(guest.exists())

    def test_nonzero_conditional_loop_stream_does_not_publish_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = LOOP_OUTPUT.read_text()
        self.assertIn("next - next", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            source = Path(scratch) / "nonzero-loop.c"
            _written = source.write_text(original.replace("next - next", "next ^ 1U"))
            guest = Path(scratch) / "nonzero.malbolge"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/unsupported-loop-stream-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"Unsupported", result.stderr)
            self.assertFalse(guest.exists())

    def test_unsupported_shift_rejects_guest_artifact(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_initialized_output.c"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            altered = Path(scratch) / "changed.c"
            text = source.read_text()
            self.assertIn("    putchar(value);", text)
            _written = altered.write_text(
                text.replace(
                    "    putchar(value);",
                    "    value = value >> 2U;\n    putchar(value);",
                )
            )
            guest = Path(scratch) / "invalid.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/mutated-local-output-v1",
                    "--output",
                    str(guest),
                    str(altered),
                ],
                check=False,
                capture_output=True,
                timeout=20,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"Unsupported", compiled.stderr)
            self.assertFalse(guest.exists())

    def _assert_constant_branch_guest(self, stem: str, second: int) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / f"tests/compiler/c-frontend/accepted/{stem}.c"
        value = 60 + second
        expected = value ^ (3 if (value & 1) == 0 else 2)
        self.assertEqual(expected, 65)
        source_id = "tests/" + stem.replace("_", "-") + "-v1"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "conditional.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    source_id,
                    "--output",
                    str(guest),
                    "--capsule",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, bytes([expected]))
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")

    def test_source_proven_if_then_reaches_real_guest_output(self) -> None:
        self._assert_constant_branch_guest("local_conditional_output", 6)

    def test_source_proven_if_else_reaches_real_guest_output(self) -> None:
        self._assert_constant_branch_guest("local_conditional_else_output", 7)

    def test_masked_wide_sum_branch_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_masked_sum_output.c"
        original = source.read_text()
        self.assertIn("unsigned a = 233U;", original)
        self.assertIn("next = next ^ 3U;", original)
        # 377 and 376 exceed a byte before C's unsigned AND mask.
        cases = (
            (original, ((233 + 144) & 255) ^ 56, 31),
            (
                original.replace("unsigned a = 233U;", "unsigned a = 232U;").replace(
                    "next = next ^ 3U;", "next = next ^ 58U;"
                ),
                ((232 + 144) & 255) ^ 58,
                69,
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for index, (text, expected, steps) in enumerate(cases):
                altered = Path(scratch) / f"masked-{index}.c"
                _written = altered.write_text(text)
                guest = Path(scratch) / f"masked-{index}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/masked-sum-{index}-v1",
                        "--output",
                        str(guest),
                        "--capsule",
                        str(altered),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest.is_file())
                executed = subprocess.run(
                    [str(VM), str(guest), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, bytes([expected]))
                self.assertEqual(
                    executed.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                )

    def test_source_proven_static_loop_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_static_loop_output.c"
        original = source.read_text()
        self.assertIn("for (unsigned i = 0U; i < 8U; ++i)", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for iterations, mask in ((8, 107), (7, 91)):
                altered = Path(scratch) / f"loop-{iterations}.c"
                text = original.replace("i < 8U", f"i < {iterations}U").replace(
                    "b ^ 107U", f"b ^ {mask}U"
                )
                _written = altered.write_text(text)
                # Independent, finite unsigned-C oracle, not a compiler trace.
                a, b = 1, 1
                for _ in range(iterations):
                    next_value = (a + b) & 255
                    next_value ^= 0 if next_value % 2 == 0 else 1
                    a, b = b, next_value
                expected = b ^ mask
                self.assertEqual(expected, 65)
                guest = Path(scratch) / f"loop-{iterations}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/static-loop-{iterations}-v1",
                        "--output",
                        str(guest),
                        "--capsule",
                        str(altered),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest.is_file())
                execution = subprocess.run(
                    [str(VM), str(guest), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(execution.returncode, 0, execution.stderr)
                self.assertEqual(execution.stdout, bytes([expected]))
                self.assertEqual(execution.stderr, b"malbolge-steps-v1:31\n")

            for index, changed in enumerate(
                (
                    original.replace("i < 8U", "i < 13U"),
                    original.replace("++i", "--i"),
                    original.replace(
                        "        a = b;", "        i = i + 1U;\n        a = b;"
                    ),
                    original.replace(
                        "        a = b;", "        putchar(65);\n        a = b;"
                    ),
                )
            ):
                altered = Path(scratch) / f"unsupported-loop-{index}.c"
                _written = altered.write_text(changed)
                guest = Path(scratch) / f"unsupported-loop-{index}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/unsupported-static-loop-{index}-v1",
                        "--output",
                        str(guest),
                        str(altered),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=60,
                )
                self.assertNotEqual(compiled.returncode, 0)
                self.assertIn(b"Unsupported", compiled.stderr)
                self.assertFalse(guest.exists())

    def test_unmasked_wide_sum_and_shift_refuse_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_masked_sum_output.c"
        original = source.read_text()
        pattern = "unsigned next = (a + b) & 255U;"
        self.assertIn(pattern, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for index, changed in enumerate(
                ("unsigned next = (a + b);", "unsigned next = (a >> b) & 255U;")
            ):
                altered = Path(scratch) / f"unsupported-{index}.c"
                _written = altered.write_text(original.replace(pattern, changed))
                guest = Path(scratch) / f"unsupported-{index}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/unsupported-masked-{index}-v1",
                        "--output",
                        str(guest),
                        "--capsule",
                        str(altered),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(compiled.returncode, 0)
                self.assertIn(b"Unsupported", compiled.stderr)
                self.assertFalse(guest.exists())

    def test_expression_argument_branches_reach_real_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_expression_output.c"
        original = source.read_text()
        self.assertIn("unsigned b = 6U;", original)
        self.assertIn("result = result ^ 1U;", original)
        # Independent arithmetic: true (66 ^ 0) ^ 3 => 65;
        # false (67 ^ 0) ^ 1 => 66. Both paths must perform C arithmetic.
        cases = (
            (original, (60 + 6) ^ 0 ^ 3),
            (
                original.replace("unsigned b = 6U;", "unsigned b = 7U;")
                .replace("result = result ^ 1U;", "result = result ^ 0U;")
                .replace(
                    "putchar((int)(result ^ 3U));", "putchar((int)(result ^ 1U));"
                ),
                (60 + 7) ^ 0 ^ 1,
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for index, (text, expected) in enumerate(cases):
                altered = Path(scratch) / f"expression-{index}.c"
                _written = altered.write_text(text)
                guest = Path(scratch) / f"expression-{index}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/checked-expression-{index}-v1",
                        "--output",
                        str(guest),
                        "--capsule",
                        str(altered),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                executed = subprocess.run(
                    [str(VM), str(guest), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, bytes([expected]))
                self.assertEqual(
                    executed.stderr,
                    f"malbolge-steps-v1:{31 if index == 0 else 69}\n".encode(),
                )

            unsupported = original.replace(
                "putchar((int)(result ^ 3U));",
                "putchar((int)(result >> 1U));",
            )
            altered = Path(scratch) / "unsupported-expression.c"
            _written = altered.write_text(unsupported)
            guest = Path(scratch) / "unsupported-expression.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/unsupported-expression-v1",
                    "--output",
                    str(guest),
                    str(altered),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"Unsupported", compiled.stderr)
            self.assertFalse(guest.exists())

    def test_multi_local_constant_flow_reaches_real_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_multi_output.c"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "multi-local.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/local-multi-output-v1",
                    "--output",
                    str(guest),
                    "--capsule",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            # (60 + 8) ^ 3 - 6 comes from distinct source-bound locals.
            self.assertEqual(executed.stdout, b"A")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")

    def test_ordered_arithmetic_reaches_real_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_arithmetic_output.c"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "local-arithmetic.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/local-arithmetic-output-v1",
                    "--output",
                    str(guest),
                    "--capsule",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            # (60 + 8) ^ 3 - 6 = 65, not a copied source literal.
            self.assertEqual(executed.stdout, b"A")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")

    def test_ordered_literal_reassignment_reaches_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_reassigned_output.c"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "local-reassignment.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/local-reassigned-output-v1",
                    "--output",
                    str(guest),
                    "--capsule",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            # Neither 0 from the initializer nor 66 from the first write.
            self.assertEqual(executed.stdout, b"A")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")

    def test_checked_remainder_recurrence_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_remainder_recurrence_output.c"
        )
        a, b = 3, 5
        observed = []
        for _ in range(3):
            next_value = (a * b) & 255
            observed.append(next_value)
            a = (next_value % 17) ^ 1 if next_value % 2 == 0 else next_value - 1
            b = next_value
        self.assertEqual(observed, [15, 210, 190])
        self.assertEqual(a, 2)
        self.assertEqual(a ^ 67, 65)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "remainder-recurrence.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/local-remainder-recurrence-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=90
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for data in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=data,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            original = source.read_text()
            invalid = {
                "zero-divisor": original.replace("next % 17U", "next % 0U"),
                "shift": original.replace("next % 17U", "next >> 1U"),
            }
            for label, changed in invalid.items():
                altered = Path(scratch) / f"{label}-remainder.c"
                altered.write_text(changed)
                rejected = Path(scratch) / f"{label}-remainder.malbolge"
                refused = subprocess.run(
                    [*command[:-2], str(rejected), str(altered)],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertFalse(rejected.exists())

    def test_unsigned_or_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_or_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("((a * b) | 16U) & 255U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for mask, xor_key, visited, final in (
                (16, 66, [31, 248, 16], 3),
                (8, 83, [15, 120, 152], 18),
            ):
                a, b = 3, 5
                actual = []
                for _ in range(3):
                    next_value = ((a * b) | mask) & 255
                    actual.append(next_value)
                    a = (
                        ((next_value >> 3) ^ 1)
                        if (next_value & 1) == 0
                        else next_value ^ 7
                    )
                    b = next_value
                self.assertEqual(actual, visited)
                self.assertEqual(a, final)
                self.assertEqual(a ^ xor_key, 65)
                changed = original.replace("| 16U", f"| {mask}U").replace(
                    "a ^ 66U", f"a ^ {xor_key}U"
                )
                candidate = Path(scratch) / f"or-mask-{mask}.c"
                candidate.write_text(changed)
                guest = Path(scratch) / f"or-mask-{mask}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/local-or-recurrence-{mask}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, (mask, compiled.stderr))
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [
                            str(VM),
                            str(guest),
                            "--input-stdin",
                            "--report-steps",
                        ],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A")
                    self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            for label, changed in {
                "logical-or": original.replace("| 16U", "|| 16U"),
                "unmasked-wide-state": original.replace(" & 255U", ""),
                "side-effect-read": original.replace("a * b", "a * b++"),
            }.items():
                invalid = Path(scratch) / f"{label}.c"
                invalid.write_text(changed)
                guest = Path(scratch) / f"{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/local-or-{label}-invalid-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(invalid),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_relational_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_relational_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("(next & 8U) < 8U", original)
        relations = {
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
            "!=": lambda a, b: a != b,
            "==": lambda a, b: a == b,
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for operator, threshold, expected_branches in (
                ("<", 8, [False, True, True]),
                ("<=", 7, [False, True, True]),
                (">", 7, [True, False, False]),
                (">=", 8, [True, False, False]),
                ("!=", 8, [False, True, True]),
                ("==", 0, [False, True, True]),
            ):
                a, b = 3, 5
                branches = []
                for _ in range(3):
                    next_value = ((a * b) << 2) & 255
                    selected = relations[operator](next_value & 8, threshold)
                    branches.append(selected)
                    a = ((next_value >> 3) ^ 1) if selected else next_value - 1
                    b = next_value
                self.assertEqual(branches, expected_branches)
                self.assertLessEqual(a, 255)
                xor_key = a ^ 65
                changed = original.replace(
                    "(next & 8U) < 8U",
                    f"(next & 8U) {operator} {threshold}U",
                ).replace("a ^ 88U", f"a ^ {xor_key}U")
                relation_name = {
                    "<": "lt",
                    "<=": "le",
                    ">": "gt",
                    ">=": "ge",
                    "!=": "ne",
                    "==": "eq",
                }[operator]
                candidate = Path(scratch) / f"relational-{relation_name}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                command = [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    f"tests/local-relational-{relation_name}-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ]
                compiled = subprocess.run(
                    command, check=False, capture_output=True, timeout=90
                )
                self.assertEqual(compiled.returncode, 0, (operator, compiled.stderr))
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A")
                    self.assertRegex(
                        executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                    )
            for label, changed in {
                "logical-and": original.replace("< 8U", "&& 8U"),
                "increment-side-effect": original.replace(
                    "(next & 8U)", "(next++ & 8U)"
                ),
                "signed-conversion": original.replace(
                    "(next & 8U) < 8U", "((int)(next & 8U)) < 8"
                ),
            }.items():
                candidate = Path(scratch) / f"invalid-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/local-relational-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_pure_logical_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_logical_recurrence_output.c"
        )
        original = source.read_text()
        condition = "((next & 8U) < 8U) && ((b & 4U) != 0U)"
        self.assertIn(condition, original)
        variants = (
            ("and", condition, [False, True, False]),
            (
                "or",
                "((next & 8U) < 8U) || ((b & 4U) == 0U)",
                [False, True, True],
            ),
            (
                "mixed",
                "(" + condition + ") || ((next & 16U) == 16U)",
                [True, True, False],
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, replacement, expected_branches in variants:
                a, b = 3, 5
                branches = []
                for _ in range(3):
                    next_value = ((a * b) << 2) & 255
                    left = (next_value & 8) < 8
                    right = (b & 4) != 0
                    if label == "and":
                        selected = left and right
                    elif label == "or":
                        selected = left or not right
                    else:
                        selected = (left and right) or (next_value & 16) == 16
                    branches.append(selected)
                    a = ((next_value >> 3) ^ 1) if selected else next_value - 1
                    b = next_value
                self.assertEqual(branches, expected_branches, label)
                self.assertLessEqual(a, 255)
                changed = original.replace(condition, replacement).replace(
                    "a ^ 254U", f"a ^ {a ^ 65}U"
                )
                candidate = Path(scratch) / f"logical-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/logical-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(
                    compiled.returncode, 0, (label, compiled.stderr)
                )
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [
                            str(VM),
                            str(guest),
                            "--input-stdin",
                            "--report-steps",
                        ],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A", label)
                    self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            for label, changed in {
                "side-effect-in-right-operand": original.replace("b & 4U", "b++ & 4U"),
                "unsupported-bitwise-combine": original.replace(" && ", " & "),
                "unsupported-call-in-right-operand": original.replace(
                    "(b & 4U) != 0U", "(putchar(70) & 4U) != 0U"
                ),
            }.items():
                candidate = Path(scratch) / f"invalid-logical-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/logical-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_truthy_conditions_reach_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_truthy_condition_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("if ((next & 8U))", original)
        variants = (
            ("masked", "(next & 8U)", [True, False, False]),
            ("bare", "next", [True, True, True]),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, condition, expected_branches in variants:
                a, b = 3, 5
                branches = []
                for _ in range(3):
                    next_value = ((a * b) << 2) & 255
                    selected = (
                        (next_value & 8) != 0
                        if label == "masked"
                        else next_value != 0
                    )
                    branches.append(selected)
                    a = ((next_value >> 3) ^ 1) if selected else next_value - 1
                    b = next_value
                self.assertEqual(branches, expected_branches, label)
                self.assertLessEqual(a, 255)
                changed = original.replace("(next & 8U)", condition, 1).replace(
                    "a ^ 62U", f"a ^ {a ^ 65}U"
                )
                candidate = Path(scratch) / f"truthy-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/truthy-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, (label, compiled.stderr))
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A", label)
                    self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            for label, changed in {
                "increment": original.replace("next & 8U", "next++ & 8U", 1),
                "impure-call": original.replace(
                    "next & 8U", "putchar(70) & 8U", 1
                ),
                "undefined-divisor": original.replace(
                    "next & 8U", "(next & 8U) / 0U", 1
                ),
                "signed-cast": original.replace(
                    "if ((next & 8U))", "if ((int)(next & 8U))", 1
                ),
            }.items():
                candidate = Path(scratch) / f"invalid-truthy-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/truthy-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_truthy_ast_mutations_refuse_publication(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_truthy_condition_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/truthy-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        branch = next(node for node in nodes if node["kind"] == "if-statement")
        grouped = next(
            node
            for node in nodes
            if node["parent"] == branch["id"]
            and node["kind"] == "parenthesized-expression"
        )
        condition = next(
            node
            for node in nodes
            if node["parent"] == grouped["id"]
            and node["kind"] == "binary-expression"
            and node.get("operation") == "&"
        )
        condition_id = cast(int, condition["id"])
        self.assertIsInstance(condition_id, int)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, field, value in (
                ("operator", "operation", "||"),
                ("type", "type", "i32"),
                ("parent", "parent", 0),
                ("literal", "literal", "1"),
            ):
                tampered = cast(dict[str, object], json.loads(frontend.stdout))
                changed_nodes = cast(list[dict[str, object]], tampered["nodes"])
                changed_nodes[condition_id - 1][field] = value
                guest = Path(scratch) / f"invalid-truthy-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_negated_logical_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_negated_logical_recurrence_output.c"
        )
        original = source.read_text()
        condition = "!(((next & 8U) >= 8U) && ((b & 4U) != 0U))"
        self.assertIn(condition, original)
        variants = (
            ("negated-and", condition, [False, True, True]),
            (
                "double-negation",
                "!!(((next & 8U) < 8U) && ((b & 4U) != 0U))",
                [False, True, False],
            ),
            (
                "nested-not",
                "!(((next & 8U) >= 8U) || !((b & 4U) != 0U))",
                [False, True, False],
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, replacement, expected_branches in variants:
                a, b = 3, 5
                branches = []
                for _ in range(3):
                    next_value = ((a * b) << 2) & 255
                    left = (next_value & 8) >= 8
                    right = (b & 4) != 0
                    if label == "negated-and":
                        selected = not (left and right)
                    elif label == "double-negation":
                        selected = (not left) and right
                    else:
                        selected = not (left or (not right))
                    branches.append(selected)
                    a = ((next_value >> 3) ^ 1) if selected else next_value - 1
                    b = next_value
                self.assertEqual(branches, expected_branches, label)
                self.assertLessEqual(a, 255)
                changed = original.replace(condition, replacement).replace(
                    "a ^ 88U", f"a ^ {a ^ 65}U"
                )
                candidate = Path(scratch) / f"negated-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/negated-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, (label, compiled.stderr))
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A", label)
                    self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            for label, changed in {
                "increment": original.replace("b & 4U", "b++ & 4U"),
                "impure-call": original.replace(
                    "(b & 4U) != 0U", "(putchar(70) & 4U) != 0U"
                ),
                "bitwise-complement": original.replace("if (!(", "if (~(", 1),
            }.items():
                candidate = Path(scratch) / f"rejected-negated-{label}.c"
                candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/negated-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_unary_signs_preserve_complete_c_guest_oracle(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = unary_unsigned_masked_fibonacci_source()
        # An independent unsigned-C oracle: both signs wrap modulo 2**32.
        a, b = 1, 1
        reference = bytearray()
        saw_wrapping_negative = False
        for _ in range(12):
            wide = (-(a + b)) & 0xFFFF_FFFF
            saw_wrapping_negative = saw_wrapping_negative or wide > 255
            following = (-wide) & 0xFFFF_FFFF
            following &= 255
            reference.append(
                (following & 31) if (following & 1) == 0 else ((following ^ 0x1A) & 31)
            )
            a, b = b, following
        self.assertTrue(saw_wrapping_negative)
        self.assertEqual(bytes(reference), bytes.fromhex("02191f08170f020d03101303"))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / "unsigned-unary-complete.c"
            candidate.write_text(original)
            guest = candidate.with_suffix(".malbolge")
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/unsigned-unary-complete-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=100,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, bytes(reference))
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:47\n")

            for label, changed in {
                "unparenthesized": original.replace("-(a + b)", "-a"),
                "spaced-sign": original.replace("-(a + b)", "- (a + b)"),
                "postincrement": original.replace("-(a + b)", "-(a + b++)"),
                "undefined": original.replace("0U - wide", "0U - (wide / 0U)"),
                "signed-cast": original.replace("0U - wide", "0U - (int)wide"),
            }.items():
                refused_source = Path(scratch) / f"invalid-unary-{label}.c"
                refused_source.write_text(changed)
                refused_guest = refused_source.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/invalid-unary-{label}-v1",
                        "--capsule",
                        "--output",
                        str(refused_guest),
                        str(refused_source),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(refused_guest.exists(), label)

    def test_unsigned_unary_signs_reject_forged_ast(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / "unsigned-unary-ast.c"
            candidate.write_text(unary_unsigned_masked_fibonacci_source())
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/unsigned-unary-ast-v1",
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            unary = [
                node
                for node in nodes
                if node["kind"] == "unary-expression"
                and node.get("operation") in ("+", "-")
            ]
            self.assertEqual(len(unary), 2)
            outer = next(node for node in unary if node["operation"] == "+")
            first = next(node for node in unary if node["operation"] == "-")
            first_id = cast(int, first["id"])
            first_operand = next(node for node in nodes if node["parent"] == first_id)
            self.assertEqual(first_operand["kind"], "parenthesized-expression")
            changes = (
                ("operator", first_id, "operation", "*"),
                ("type", first_id, "type", "i32"),
                ("parent", first_id, "parent", 0),
                ("metadata", first_id, "literal", "0"),
                (
                    "operand-kind",
                    cast(int, first_operand["id"]),
                    "kind",
                    "cast-expression",
                ),
                ("plus-type", cast(int, outer["id"]), "type", "i32"),
            )
            for label, node_id, field, value in changes:
                forged = cast(dict[str, object], json.loads(frontend.stdout))
                forged_nodes = cast(list[dict[str, object]], forged["nodes"])
                forged_nodes[node_id - 1][field] = value
                guest = Path(scratch) / f"forged-unsigned-unary-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(forged).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_unsigned_complement_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_complement_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("(~next) & 255U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, variant, xor_key, trace in (
                (
                    "single",
                    original,
                    88,
                    [(60, True, 195), (208, False, 27), (192, False, 25)],
                ),
                (
                    "double",
                    original.replace("~next", "~~next").replace("^ 88U", "^ 64U"),
                    64,
                    [(60, True, 60), (64, False, 9), (0, False, 1)],
                ),
            ):
                a, b = 3, 5
                observed: list[tuple[int, bool, int]] = []
                for _ in range(3):
                    following = ((a * b) << 2) & 255
                    take_then = (following & 8) != 0
                    if take_then:
                        complement = (~following) & 0xFFFF_FFFF
                        if label == "double":
                            complement = (~complement) & 0xFFFF_FFFF
                        a = complement & 255
                    else:
                        a = (following >> 3) ^ 1
                    b = following
                    observed.append((following, take_then, a))
                self.assertEqual(observed, trace)
                self.assertEqual(a ^ xor_key, 65)
                candidate = Path(scratch) / f"complement-{label}.c"
                _ = candidate.write_text(variant)
                guest = candidate.with_suffix(".malbolge")
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/complement-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest.is_file())
                for guest_input in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A")
                    self.assertRegex(
                        executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                    )

            for label, changed in {
                "increment": original.replace("~next", "~next++"),
                "assignment": original.replace("~next", "~(next += 1U)"),
                "undefined": original.replace("~next", "~(next / (b - b))"),
                "signed": original.replace("~next", "~(int)next"),
                "unsupported-minus": original.replace("~next", "-next"),
            }.items():
                candidate = Path(scratch) / f"invalid-complement-{label}.c"
                _ = candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/complement-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_unsigned_complement_ast_mutations_fail_closed(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_complement_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/complement-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        unary = [
            node
            for node in nodes
            if node["kind"] == "unary-expression" and node.get("operation") == "~"
        ]
        self.assertEqual(len(unary), 1)
        expression = unary[0]
        expression_id = expression["id"]
        self.assertIsInstance(expression_id, int)
        operands = [node for node in nodes if node["parent"] == expression_id]
        self.assertEqual(len(operands), 1)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("operation", expression_id, "operation", "-"),
                ("result-type", expression_id, "type", "i32"),
                ("foreign-parent", expression_id, "parent", 0),
                ("extra-metadata", expression_id, "literal", "0"),
                ("operand-kind", operands[0]["id"], "kind", "call-expression"),
                ("operand-type", operands[0]["id"], "type", "i32"),
            ):
                assert isinstance(node_id, int)
                tampered = cast(dict[str, object], json.loads(frontend.stdout))
                changed_nodes = cast(list[dict[str, object]], tampered["nodes"])
                changed_nodes[node_id - 1][field] = value
                guest = Path(scratch) / f"invalid-complement-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_conditional_expression_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_conditional_expression_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("(next & 8U) != 0U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            a, b = 3, 5
            branches: list[bool] = []
            for _ in range(3):
                following = ((a * b) << 2) & 255
                take_then = (following & 8) != 0
                branches.append(take_then)
                a = ((following >> 3) ^ 1) if take_then else following - 1
                b = following
            self.assertEqual(branches, [True, False, False])
            self.assertEqual(a, 127)
            self.assertEqual(a ^ 62, 65)
            guest = Path(scratch) / "conditional.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/conditional-expression-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")
            for label, changed in {
                "impure-condition": original.replace("next & 8U", "next++ & 8U"),
                "impure-unselected-arm": original.replace("next - 1U", "next++ - 1U"),
                "undefined-unselected-arm": original.replace(
                    "next - 1U", "next / (b - b)"
                ),
                "unsupported-unsigned-arm": original.replace(
                    "next - 1U", "(unsigned)(next > 1U)"
                ),
            }.items():
                candidate = Path(scratch) / f"invalid-conditional-{label}.c"
                _ = candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/conditional-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_conditional_expression_ast_mutations_fail_closed(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_conditional_expression_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/conditional-ast-mutation-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        nodes = cast(list[dict[str, object]], json.loads(frontend.stdout)["nodes"])
        conditional = [
            node for node in nodes if node["kind"] == "conditional-expression"
        ]
        self.assertEqual(len(conditional), 1)
        expression = conditional[0]
        expression_id = expression["id"]
        self.assertIsInstance(expression_id, int)
        arms = [node for node in nodes if node["parent"] == expression_id]
        self.assertEqual(len(arms), 3)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("conditional-type", expression_id, "type", "i32"),
                ("conditional-operation", expression_id, "operation", "!"),
                ("condition-parent", arms[0]["id"], "parent", 0),
                ("true-arm-kind", arms[1]["id"], "kind", "call-expression"),
                ("false-arm-type", arms[2]["id"], "type", "i32"),
            ):
                assert isinstance(node_id, int)
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                tampered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"conditional-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_computed_unsigned_comparison_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_computed_condition_recurrence_output.c"
        )
        original = source.read_text()
        comparison = "((next & 31U) + (a & 7U)) >= ((b ^ 2U) + 3U)"
        self.assertIn(comparison, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, operator, expected_branches in (
                ("greater-equal", ">=", [True, False, False]),
                ("less-than", "<", [False, True, True]),
            ):
                a, b = 3, 5
                branches = []
                for _ in range(3):
                    following = ((a * b) << 2) & 255
                    lhs = (following & 31) + (a & 7)
                    rhs = (b ^ 2) + 3
                    take_then = lhs >= rhs if operator == ">=" else lhs < rhs
                    branches.append(take_then)
                    a = ((following >> 3) ^ 1) if take_then else following - 1
                    b = following
                self.assertEqual(branches, expected_branches, label)
                self.assertLessEqual(a, 255)
                variant = original.replace(
                    comparison,
                    comparison.replace(">=", operator),
                ).replace("a ^ 62U", f"a ^ {a ^ 65}U")
                candidate = Path(scratch) / f"computed-{label}.c"
                _written = candidate.write_text(variant)
                guest = candidate.with_suffix(".malbolge")
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/computed-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertEqual(compiled.returncode, 0, (label, compiled.stderr))
                self.assertTrue(guest.is_file())
                for guest_input in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"A", label)
                    self.assertRegex(
                        executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                    )
            for label, changed in {
                "impure-left": original.replace("a & 7U", "a++ & 7U"),
                "undefined-right": original.replace(
                    "(b ^ 2U) + 3U", "(b ^ 2U) / (b - b)"
                ),
                "logical-condition": original.replace(">= ((b", "|| ((b"),
            }.items():
                candidate = Path(scratch) / f"rejected-computed-{label}.c"
                _written = candidate.write_text(changed)
                guest = candidate.with_suffix(".malbolge")
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/computed-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(guest.exists(), label)

    def test_computed_unsigned_comparison_ast_mutations_fail_closed(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_computed_condition_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/computed-ast-mutation-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        canonical = json.loads(frontend.stdout)
        comparisons = [
            node
            for node in canonical["nodes"]
            if node["kind"] == "binary-expression" and node.get("operation") == ">="
        ]
        self.assertEqual(len(comparisons), 1)
        comparison = comparisons[0]
        right = next(
            node
            for node in canonical["nodes"]
            if node["parent"] == comparison["id"]
            and node["kind"] == "parenthesized-expression"
            and node["span"]["begin"]["byte"] > comparison["span"]["begin"]["byte"]
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, field, value in (
                ("bad-rhs-type", "type", "i32"),
                ("bad-rhs-parent", "parent", 0),
                ("bad-rhs-kind", "kind", "call-expression"),
            ):
                tampered = json.loads(frontend.stdout)
                tampered["nodes"][right["id"] - 1][field] = value
                guest = Path(scratch) / f"computed-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_negated_logical_ast_mutations_refuse_publication(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_negated_logical_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/negated-ast-mutations-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        normalized = json.loads(frontend.stdout)
        unary_positions = [
            index
            for index, node in enumerate(normalized["nodes"])
            if node["kind"] == "unary-expression" and node.get("operation") == "!"
        ]
        self.assertEqual(len(unary_positions), 1)
        index = unary_positions[0]
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, field, value in (
                ("wrong-operation", "operation", "~"),
                ("wrong-type", "type", "u32"),
                ("wrong-parent", "parent", 0),
                ("wrong-kind", "kind", "binary-expression"),
            ):
                altered = json.loads(frontend.stdout)
                altered["nodes"][index][field] = value
                guest = Path(scratch) / f"rejected-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(altered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_unsigned_shift_recurrence_reaches_real_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_shift_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("((a * b) << 2U) & 255U", original)
        self.assertIn("(next >> 3U) ^ 1U", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for left_shift, right_shift, xor_key, visited, final in (
                (2, 3, 88, [60, 80, 192], 25),
                (0, 0, 86, [15, 210, 22], 23),
                (31, 3, 64, [0, 0, 0], 1),
            ):
                a, b = 3, 5
                actual_visited = []
                for _ in range(3):
                    # C unsigned left shift reduces modulo 2**32, then masks.
                    next_value = ((a * b) << left_shift) & 0xFFFFFFFF & 255
                    actual_visited.append(next_value)
                    a = (
                        ((next_value >> right_shift) ^ 1)
                        if (next_value & 8) == 0
                        else next_value - 1
                    )
                    b = next_value
                self.assertEqual(actual_visited, visited)
                self.assertEqual(a, final)
                self.assertEqual(a ^ xor_key, 65)
                changed = (
                    original.replace("<< 2U", f"<< {left_shift}U")
                    .replace(">> 3U", f">> {right_shift}U")
                    .replace("a ^ 88U", f"a ^ {xor_key}U")
                    # Both conditional arms must produce byte-sized local
                    # stores, including the unselected unsigned underflow.
                    .replace(
                        "next - 1U",
                        "next + 1U" if left_shift == 31 else "next - 1U",
                    )
                )
                candidate = Path(scratch) / f"shift-{left_shift}-{right_shift}.c"
                candidate.write_text(changed)
                guest = Path(scratch) / f"shift-{left_shift}-{right_shift}.malbolge"
                command = [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    f"tests/local-shift-recurrence-{left_shift}-{right_shift}-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ]
                compiled = subprocess.run(
                    command, check=False, capture_output=True, timeout=90
                )
                self.assertEqual(
                    compiled.returncode,
                    0,
                    (left_shift, right_shift, compiled.stderr),
                )
                self.assertTrue(guest.is_file())
                for data in (b"", bytes((255, 0, 128))):
                    execution = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=data,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(execution.returncode, 0, execution.stderr)
                    self.assertEqual(execution.stdout, b"A")
                    self.assertEqual(execution.stderr, b"malbolge-steps-v1:31\n")
            for label, changed in {
                "left-count-32": original.replace("<< 2U", "<< 32U"),
                "right-count-32": original.replace(">> 3U", ">> 32U"),
                "unsupported-logical-and": original.replace("next - 1U", "next && 1U"),
            }.items():
                invalid = Path(scratch) / f"{label}.c"
                invalid.write_text(changed)
                guest = Path(scratch) / f"{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/local-shift-{label}-invalid-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(invalid),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertFalse(guest.exists(), label)

    def test_checked_division_recurrence_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_division_recurrence_output.c"
        )
        a, b = 3, 5
        visited = []
        for _ in range(3):
            next_value = (a * b) & 255
            visited.append(next_value)
            a = (next_value // 17) ^ 1 if next_value % 2 == 0 else next_value - 1
            b = next_value
        self.assertEqual(visited, [15, 210, 170])
        self.assertEqual(a, 11)
        self.assertEqual(a ^ 74, 65)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "division-recurrence.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/local-division-recurrence-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=90
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for data in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=data,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            original = source.read_text()
            self.assertIn("next / 17U", original)
            invalid = {
                "zero-divisor": original.replace("next / 17U", "next / 0U"),
                "shift": original.replace("next / 17U", "next >> 1U"),
            }
            for label, changed in invalid.items():
                altered = Path(scratch) / f"{label}-division.c"
                altered.write_text(changed)
                rejected = Path(scratch) / f"{label}-division.malbolge"
                refused = subprocess.run(
                    [*command[:-2], str(rejected), str(altered)],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(rejected.exists())

    def test_checked_multiplicative_recurrence_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/"
            "local_multiplicative_recurrence_output.c"
        )
        a, b = 3, 5
        visited = []
        for _ in range(3):
            next_value = (a * b) & 255
            visited.append(next_value)
            a = (next_value ^ 1) if next_value % 2 == 0 else next_value - 1
            b = next_value
        self.assertEqual(visited, [15, 210, 22])
        self.assertEqual(a ^ 86, 65)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "multiply-recurrence.malbolge"
            command = [
                sys.executable,
                "-B",
                str(DRIVER),
                "--repository-tools",
                "--source-id",
                "tests/local-multiplicative-recurrence-v1",
                "--capsule",
                "--output",
                str(guest),
                str(source),
            ]
            compiled = subprocess.run(
                command, check=False, capture_output=True, timeout=90
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for data in (b"", bytes((255, 0, 128))):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=data,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertEqual(executed.stderr, b"malbolge-steps-v1:31\n")
            original = source.read_text()
            # Unsigned arithmetic wraps, but undefined division or an
            # unproven signed cast must still refuse without a guest.
            invalid = {
                "zero-divisor": original.replace(
                    "(a * b) & 255U", "((a * b) / 0U) & 255U"
                ),
                "signed-cast": original.replace("a * b", "a * (int)b"),
            }
            for label, changed in invalid.items():
                altered = Path(scratch) / f"{label}-recurrence.c"
                altered.write_text(changed)
                rejected = Path(scratch) / f"{label}-recurrence.malbolge"
                refused = subprocess.run(
                    [*command[:-2], str(rejected), str(altered)],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(b"Unsupported", refused.stderr)
                self.assertFalse(rejected.exists())

    def test_automatic_unsigned_local_reaches_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = ROOT / "tests/compiler/c-frontend/accepted/local_initialized_output.c"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            guest = Path(scratch) / "local-output.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/local-initialized-output-v1",
                    "--output",
                    str(guest),
                    "--capsule",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            executed = subprocess.run(
                [str(VM), str(guest), "--report-steps"],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"A")
            self.assertRegex(executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$")

    def test_bounded_while_state_and_branch_stream_reach_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_while_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("while (i < 3U)", original)
        a, b = 3, 5
        taken = []
        for _ in range(3):
            following = ((a * b) << 2) & 255
            selected = (following & 8) != 0
            taken.append(selected)
            a = ((following >> 3) ^ 1) if selected else following - 1
            b = following
        self.assertEqual(taken, [True, False, False])
        self.assertEqual(a, 127)
        self.assertEqual(a ^ 62, 65)

        # The same while replay must preserve distinct selected output
        # effects, not merely a single final byte of compile-time state.
        pair_source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        self.assertIn("for (unsigned i = 0U; i < 2U; ++i)", pair_source)
        pair_source = pair_source.replace(
            "for (unsigned i = 0U; i < 2U; ++i) {",
            "unsigned i = 0U;\n    while (i < 2U) {",
        ).replace("        b = next;\n", "        b = next;\n        i = i + 1U;\n")
        previous, current = 1, 1
        expected_pair = bytearray()
        for _ in range(2):
            following = (previous + current) & 255
            expected_pair.append(following ^ (83 if following % 2 == 0 else 45))
            previous, current = current, following
        self.assertEqual(bytes(expected_pair), b"Q.")

        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            pair = Path(scratch) / "while-pair.c"
            pair.write_text(pair_source)
            for label, candidate, expected in (
                ("state", source, b"A"),
                ("stream", pair, bytes(expected_pair)),
            ):
                guest = Path(scratch) / f"while-{label}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/while-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=100,
                )
                self.assertEqual(compiled.returncode, 0, (label, compiled.stderr))
                self.assertTrue(guest.is_file(), label)
                for guest_input in (b"", bytes((255, 0, 128))):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected, label)
                    self.assertRegex(
                        executed.stderr,
                        rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                    )

            for label, changed in {
                "nonterminating": original.replace("i = i + 1U", "i = i + 0U"),
                "beyond-bound": original.replace("i < 3U", "i < 13U"),
                "side-effecting-test": original.replace("i < 3U", "i++ < 3U"),
                "undefined-test": original.replace("i < 3U", "(i / 0U) < 3U"),
                "nested-loop": original.replace(
                    "i = i + 1U;", "while (i < 3U) { i = i + 1U; }"
                ),
            }.items():
                candidate = Path(scratch) / f"rejected-while-{label}.c"
                candidate.write_text(changed)
                guest = Path(scratch) / f"rejected-while-{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/while-invalid-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=90,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)

    def test_bounded_while_forged_ast_refuses_publication(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_while_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/while-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        loop = next(node for node in nodes if node["kind"] == "while-statement")
        children = [node for node in nodes if node["parent"] == loop["id"]]
        condition = next(
            node for node in children if node["kind"] == "binary-expression"
        )
        body = next(node for node in children if node["kind"] == "compound-statement")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("wrong-loop-kind", loop["id"], "kind", "for-statement"),
                ("foreign-loop-parent", loop["id"], "parent", 0),
                ("loop-extra-operation", loop["id"], "operation", "++"),
                ("condition-operation", condition["id"], "operation", ">="),
                ("condition-type", condition["id"], "type", "u32"),
                ("body-parent", body["id"], "parent", 0),
            ):
                assert isinstance(node_id, int)
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                tampered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"while-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)


    def _check_bounded_do_while_guest(self, selected_label: str) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_do_while_recurrence_output.c"
        )
        original = source.read_text()
        self.assertIn("} while (i < 3U);", original)
        # Independently replay C's body-before-test semantics.
        a, b, i = 3, 5, 0
        taken = []
        while True:
            next_value = ((a * b) << 2) & 255
            branch = (next_value & 8) != 0
            taken.append(branch)
            a = ((next_value >> 3) ^ 1) if branch else next_value - 1
            b = next_value
            i += 1
            if not i < 3:
                break
        self.assertEqual(taken, [True, False, False])
        self.assertEqual(a ^ 62, 65)
        one_next = ((3 * 5) << 2) & 255
        one_a = (one_next >> 3) ^ 1
        self.assertEqual(one_a ^ 71, 65)
        pair_source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_loop_distinct_output.c"
        ).read_text()
        self.assertIn("for (unsigned i = 0U; i < 2U; ++i)", pair_source)
        pair_source = (
            pair_source.replace(
                "for (unsigned i = 0U; i < 2U; ++i) {",
                "unsigned i = 0U;\n    do {",
            )
            .replace("        b = next;\n", "        b = next;\n        i = i + 1U;\n")
            .replace("    }\n}\n", "    } while (i < 2U);\n}\n")
        )
        previous, current = 1, 1
        expected_pair = bytearray()
        for _ in range(2):
            following = (previous + current) & 255
            expected_pair.append(following ^ (83 if following % 2 == 0 else 45))
            previous, current = current, following
        self.assertEqual(bytes(expected_pair), b"Q.")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed, expected in (
                ("three-trips", original, b"A"),
                ("branch-stream", pair_source, bytes(expected_pair)),
                # This test starts false, yet a do-loop executes once.
                (
                    "mandatory-first-trip",
                    original.replace("unsigned i = 0U;", "unsigned i = 3U;").replace(
                        "a ^ 62U", "a ^ 71U"
                    ),
                    b"A",
                ),
            ):
                if label != selected_label:
                    continue
                candidate = Path(scratch) / f"do-{label}.c"
                candidate.write_text(changed)
                guest = Path(scratch) / f"do-{label}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/do-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=180,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest.is_file())
                for guest_input in (b"", bytes((0, 255, 128))):
                    execution = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(execution.returncode, 0, execution.stderr)
                    self.assertEqual(execution.stdout, expected)
                    self.assertRegex(
                        execution.stderr,
                        rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                    )

    def test_bounded_do_while_three_trips_reaches_guest(self) -> None:
        self._check_bounded_do_while_guest("three-trips")

    def test_bounded_do_while_branch_stream_reaches_guest(self) -> None:
        self._check_bounded_do_while_guest("branch-stream")

    def test_bounded_do_while_mandatory_first_trip_reaches_guest(self) -> None:
        self._check_bounded_do_while_guest("mandatory-first-trip")

    def test_bounded_do_while_source_refusals(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_do_while_recurrence_output.c"
        )
        original = source.read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed in {
                "nonterminating": original.replace("i = i + 1U", "i = i + 0U"),
                "beyond-bound": original.replace("i < 3U", "i < 13U"),
                "side-effecting-test": original.replace("i < 3U", "i++ < 3U"),
                "undefined-test": original.replace("i < 3U", "(i / 0U) < 3U"),
                "nested-loop": original.replace(
                    "i = i + 1U;", "while (i < 3U) { i = i + 1U; }"
                ),
            }.items():
                candidate = Path(scratch) / f"reject-do-{label}.c"
                candidate.write_text(changed)
                guest = Path(scratch) / f"reject-do-{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/do-reject-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=45,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)

    def test_bounded_do_while_forged_ast_refuses_publication(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted/local_do_while_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/do-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        loop = next(node for node in nodes if node["kind"] == "do-statement")
        children = [node for node in nodes if node["parent"] == loop["id"]]
        body = next(node for node in children if node["kind"] == "compound-statement")
        condition = next(
            node for node in children if node["kind"] == "binary-expression"
        )
        self.assertLess(cast(int, body["id"]), cast(int, condition["id"]))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("wrong-kind", loop["id"], "kind", "while-statement"),
                ("wrong-parent", loop["id"], "parent", 0),
                ("extra-operation", loop["id"], "operation", "++"),
                ("unsupported-condition", condition["id"], "operation", "%"),
                ("condition-type", condition["id"], "type", "u32"),
                ("body-parent", body["id"], "parent", 0),
            ):
                assert isinstance(node_id, int)
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                tampered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"do-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)


    def test_bounded_if_without_else_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_if_without_else_recurrence_output.c"
        ).read_text()
        self.assertIn("if (next & 8U) {", source)

        def oracle(mask: int, xor: int) -> tuple[bytes, list[bool]]:
            a, b, i = 3, 5, 0
            branches: list[bool] = []
            while True:
                following = ((a * b) << 2) & 255
                taken = bool(following & mask)
                branches.append(taken)
                if taken:
                    a = (following >> 3) ^ 1
                b = following
                i += 1
                if i == 3:
                    break
            return bytes((a ^ xor,)), branches

        self.assertEqual(oracle(8, 71), (b"A", [True, False, False]))
        self.assertEqual(oracle(2, 66), (b"A", [False, False, False]))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed, expected in (
                ("taken-and-skipped", source, oracle(8, 71)[0]),
                (
                    "always-skipped",
                    source.replace("next & 8U", "next & 2U").replace(
                        "a ^ 71U", "a ^ 66U"
                    ),
                    oracle(2, 66)[0],
                ),
            ):
                candidate = Path(scratch) / f"no-else-{label}.c"
                _ = candidate.write_text(changed)
                guest = Path(scratch) / f"no-else-{label}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/no-else-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=100,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest.is_file())
                for guest_input in (b"", b"\xff\x00\x80"):
                    executed = subprocess.run(
                        [
                            str(VM),
                            str(guest),
                            "--input-stdin",
                            "--report-steps",
                        ],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertRegex(
                        executed.stderr,
                        rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                    )

    def test_bounded_if_without_else_source_refusals(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_if_without_else_recurrence_output.c"
        ).read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed in {
                "extra-assignment": source.replace(
                    "a = (next >> 3U) ^ 1U;",
                    "a = (next >> 3U) ^ 1U;\n            b = 0U;",
                ),
                "hidden-effect": source.replace(
                    "a = (next >> 3U) ^ 1U;",
                    "a = (next >> 3U) ^ 1U;\n            putchar((int)next);",
                ),
                "missing-braces": source.replace(
                    "if (next & 8U) {\n"
                    + "            a = (next >> 3U) ^ 1U;\n        }",
                    "if (next & 8U) a = (next >> 3U) ^ 1U;",
                ),
                "undefined-arithmetic": source.replace(
                    "a = (next >> 3U) ^ 1U;", "a = next / 0U;"
                ),
                "unbounded": source.replace("i < 3U", "i < 13U"),
            }.items():
                candidate = Path(scratch) / f"reject-no-else-{label}.c"
                _ = candidate.write_text(changed)
                guest = Path(scratch) / f"reject-no-else-{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/no-else-reject-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=40,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)

    def test_bounded_if_without_else_forged_ast_refuses(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_if_without_else_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/no-else-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        branch = next(node for node in nodes if node["kind"] == "if-statement")
        children = [node for node in nodes if node["parent"] == branch["id"]]
        body = next(
            node for node in children if node["kind"] == "compound-statement"
        )
        body_span = cast(dict[str, object], body["span"])
        branch_span = cast(dict[str, object], branch["span"])
        self.assertEqual(body_span["end"], branch_span["end"])
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("wrong-kind", branch["id"], "kind", "while-statement"),
                ("wrong-parent", branch["id"], "parent", 0),
                ("extra-operation", branch["id"], "operation", "!"),
                ("body-parent", body["id"], "parent", 0),
                ("body-kind", body["id"], "kind", "declaration-statement"),
            ):
                assert isinstance(node_id, int)
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                tampered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"no-else-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)


    def test_zero_trip_while_skips_checked_body_and_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        ).read_text()
        self.assertIn("while (i < 3U)", original)
        self.assertIn("putchar((int)(next ^ 1U));", original)

        # Independently evaluate the C order: the first loop skips its
        # output and mutations; the second executes three complete trips.
        def oracle() -> tuple[bytes, list[int], int]:
            a, b, i = 3, 5, 3
            skipped = 0
            while i < 3:
                skipped += 1
                next_value = ((a * b) << 2) & 255
                a = ((next_value >> 3) ^ 1) if next_value & 8 else next_value - 1
                b = next_value
                i += 1
            visited: list[int] = []
            while True:
                next_value = ((a * b) << 2) & 255
                visited.append(next_value)
                a = ((next_value >> 3) ^ 1) if next_value & 8 else next_value - 1
                b = next_value
                i += 1
                if i >= 6:
                    break
            return bytes((a ^ 62,)), visited, skipped

        expected, visited, skipped = oracle()
        self.assertEqual((expected, visited, skipped), (b"A", [60, 160, 128], 0))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source in (
                ("true-shadow", original),
                ("false-shadow", original.replace("next & 8U", "next & 2U", 1)),
            ):
                candidate = Path(scratch) / f"zero-trip-{label}.c"
                candidate.write_text(source)
                guest = Path(scratch) / f"zero-trip-{label}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/zero-trip-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=100,
                )
                self.assertEqual(compiled.returncode, 0, (label, compiled.stderr))
                self.assertTrue(guest.is_file(), label)
                for guest_input in (b"", b"\xff\x00\x80"):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected, label)
                    self.assertRegex(
                        executed.stderr,
                        rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                    )

    def test_zero_trip_while_unproved_source_refuses_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        ).read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, changed in {
                "impure-guard": original.replace("while (i < 3U)", "while (i++ < 3U)"),
                "undefined-skipped-expression": original.replace(
                    "putchar((int)(next ^ 1U));", "putchar((int)(next / 0U));"
                ),
                "unproved-skipped-effect": original.replace(
                    "putchar((int)(next ^ 1U));", "next++;"
                ),
                "nested-skipped-loop": original.replace(
                    "putchar((int)(next ^ 1U));",
                    "while (next & 8U) { next = next - 1U; }",
                ),
            }.items():
                source = Path(scratch) / f"invalid-zero-trip-{label}.c"
                source.write_text(changed)
                guest = Path(scratch) / f"invalid-zero-trip-{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/invalid-zero-trip-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(source),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=40,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)

    def test_zero_trip_while_forged_skipped_ast_refuses_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        )
        frontend = subprocess.run(
            [
                str(FRONTEND),
                "--guest-include",
                str(GUEST_INCLUDE),
                "--resource-dir",
                str(RESOURCE),
                "--source-id",
                "tests/zero-trip-ast-v1",
                str(source),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        parsed = cast(dict[str, object], json.loads(frontend.stdout))
        nodes = cast(list[dict[str, object]], parsed["nodes"])
        zero_loop = next(node for node in nodes if node["kind"] == "while-statement")
        children = [node for node in nodes if node["parent"] == zero_loop["id"]]
        condition = next(
            node for node in children if node["kind"] == "binary-expression"
        )
        body = next(node for node in children if node["kind"] == "compound-statement")
        skipped_call = next(
            node
            for node in nodes
            if node["kind"] == "call-expression"
            and cast(dict[str, dict[str, int]], node["span"])["begin"]["byte"]
            < cast(dict[str, dict[str, int]], body["span"])["end"]["byte"]
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, node_id, field, value in (
                ("loop-parent", zero_loop["id"], "parent", 0),
                ("guard-type", condition["id"], "type", "u32"),
                ("skipped-body-parent", body["id"], "parent", 0),
                ("skipped-body-operation", body["id"], "operation", "++"),
                (
                    "skipped-output-callee",
                    skipped_call["id"],
                    "reference",
                    "external:puts",
                ),
            ):
                assert isinstance(node_id, int)
                tampered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                tampered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"zero-trip-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(tampered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)


    def test_zero_trip_for_skips_body_and_reaches_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        ).read_text()
        self.assertEqual(original.count("while (i < 3U)"), 1)
        candidate_source = original.replace(
            "while (i < 3U)", "for (unsigned j = 0U; j < 0U; ++j)"
        )
        # C executes the do-while three times after skipping the entire
        # for body, including its output. The oracle is independent of IR.
        a, b, i = 3, 5, 3
        visited: list[int] = []
        for _ in range(3):
            next_value = ((a * b) << 2) & 255
            visited.append(next_value)
            a = ((next_value >> 3) ^ 1) if next_value & 8 else next_value - 1
            b = next_value
            i += 1
        self.assertEqual((visited, i, a ^ 62), ([60, 160, 128], 6, 65))
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / "zero-trip-for.c"
            candidate.write_text(candidate_source)
            guest = Path(scratch) / "zero-trip-for.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/zero-trip-for-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=100,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest.is_file())
            for guest_input in (b"", b"\xff\x00\x80"):
                executed = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=guest_input,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, b"A")
                self.assertRegex(
                    executed.stderr,
                    rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                )

    def test_zero_trip_for_unproved_source_and_ast_refuse(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_zero_trip_while_recurrence_output.c"
        ).read_text()
        source = original.replace(
            "while (i < 3U)", "for (unsigned j = 0U; j < 0U; ++j)"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            candidate = Path(scratch) / "zero-trip-for.c"
            candidate.write_text(source)
            for label, changed in {
                "skipped-increment": source.replace(
                    "putchar((int)(next ^ 1U));", "next++;"
                ),
                "skipped-zero-divisor": source.replace(
                    "putchar((int)(next ^ 1U));", "putchar((int)(next / 0U));"
                ),
                "nested-skipped-loop": source.replace(
                    "putchar((int)(next ^ 1U));",
                    "while (next & 8U) { next = next - 1U; }",
                ),
                "wrong-counter": source.replace("++j)", "++i)", 1),
            }.items():
                bad = Path(scratch) / f"invalid-zero-for-{label}.c"
                bad.write_text(changed)
                guest = Path(scratch) / f"invalid-zero-for-{label}.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/invalid-zero-for-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(bad),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=40,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/zero-for-ast-v1",
                    str(candidate),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            loop = next(node for node in nodes if node["kind"] == "for-statement")
            body = next(
                node
                for node in nodes
                if node["parent"] == loop["id"] and node["kind"] == "compound-statement"
            )
            for label, node_id, field, value in (
                ("for-parent", loop["id"], "parent", 0),
                ("for-operation", loop["id"], "operation", "+="),
                ("skipped-body-parent", body["id"], "parent", 0),
            ):
                assert isinstance(node_id, int)
                altered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                altered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"invalid-zero-for-ast-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(altered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)


    def test_multi_assignment_conditional_recurrence_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_multi_assignment_branch_recurrence.c"
        ).read_text()
        else_arm = (
            "        } else {\n"
            "            a = next - 1U;\n"
            "            b = next;\n"
            "        }"
        )
        self.assertEqual(original.count(else_arm), 1)
        no_else = original.replace(else_arm, "        }")

        def oracle(a: int, b: int, with_else: bool) -> tuple[list[int], int]:
            visited: list[int] = []
            for _ in range(3):
                following = ((a * b) << 2) & 255
                visited.append(following)
                if following & 8:
                    a = (following >> 3) ^ 1
                    b = following ^ 2
                elif with_else:
                    a = following - 1
                    b = following
            return visited, a

        cases = (
            ("both-arms", original, 3, 5, True, 254, b"A", [60, 208, 192]),
            (
                "false-first",
                original.replace("unsigned a = 3U;", "unsigned a = 1U;")
                .replace("unsigned b = 5U;", "unsigned b = 1U;")
                .replace("a ^ 254U", "a ^ 125U"),
                1,
                1,
                True,
                125,
                b"B",
                [4, 48, 64],
            ),
            (
                "no-else-taken",
                no_else.replace("a ^ 254U", "a ^ 71U"),
                3,
                5,
                False,
                71,
                b"A",
                [60, 208, 208],
            ),
            (
                "no-else-skipped",
                no_else.replace("unsigned a = 3U;", "unsigned a = 1U;")
                .replace("unsigned b = 5U;", "unsigned b = 1U;")
                .replace("a ^ 254U", "a ^ 64U"),
                1,
                1,
                False,
                64,
                b"A",
                [4, 4, 4],
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source, a, b, with_else, mask, expected, trace in cases:
                visited, result = oracle(a, b, with_else)
                self.assertEqual(visited, trace, label)
                self.assertEqual(bytes([(result ^ mask) & 255]), expected)
                candidate = Path(scratch) / f"multi-arm-{label}.c"
                _ = candidate.write_text(source)
                guest = Path(scratch) / f"multi-arm-{label}.malbolge"
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/multi-arm-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=120,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                self.assertTrue(guest.is_file(), label)
                for guest_input in (b"", b"\xff\x00\x80"):
                    executed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--report-steps"],
                        input=guest_input,
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected, label)
                    self.assertRegex(
                        executed.stderr,
                        rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                    )

    def test_multi_assignment_conditional_rejects_unproved_effects(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_multi_assignment_branch_recurrence.c"
        ).read_text()
        for label, changed in {
            "unselected-increment": original.replace("b = next ^ 2U;", "b = next++;"),
            "unselected-undefined": original.replace(
                "b = next ^ 2U;", "b = next / 0U;"
            ),
            "branch-extra-unsupported-call": original.replace(
                "b = next ^ 2U;", 'b = next ^ 2U; puts("extra");'
            ),
            "else-compound-assignment": original.replace("b = next;", "b += next;"),
            "unbraced-nested-branch": original.replace(
                "b = next;", "if (next & 1U) b = next;"
            ),
            "too-many-writes": original.replace("b = next;", "b = next;" * 17),
        }.items():
            with (
                self.subTest(label=label),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch,
            ):
                candidate = Path(scratch) / f"invalid-multi-arm-{label}.c"
                _ = candidate.write_text(changed)
                guest = Path(scratch) / "rejected.malbolge"
                refused = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--source-id",
                        f"tests/invalid-multi-arm-{label}-v1",
                        "--capsule",
                        "--output",
                        str(guest),
                        str(candidate),
                    ],
                    check=False,
                    capture_output=True,
                    timeout=40,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|FRONTEND-")
                self.assertFalse(guest.exists(), label)

    def test_multi_assignment_conditional_forged_ast_refuses(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        original = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_multi_assignment_branch_recurrence.c"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/multi-arm-ast-v1",
                    str(original),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            conditional = next(n for n in nodes if n["kind"] == "if-statement")
            arms = [
                n
                for n in nodes
                if n["kind"] == "compound-statement"
                and n["parent"] == conditional["id"]
            ]
            self.assertEqual(len(arms), 2)
            assignments = [
                [
                    n
                    for n in nodes
                    if n["kind"] == "binary-expression"
                    and n.get("operation") == "="
                    and n["parent"] == arm["id"]
                ]
                for arm in arms
            ]
            self.assertEqual(list(map(len, assignments)), [2, 2])
            then_second, else_second = assignments[0][1], assignments[1][1]
            then_left = next(
                n
                for n in nodes
                if n["parent"] == then_second["id"]
                and n["kind"] == "declaration-reference-expression"
            )
            for label, node_id, field, value in (
                ("then-second-parent", then_second["id"], "parent", conditional["id"]),
                ("else-second-parent", else_second["id"], "parent", conditional["id"]),
                ("then-second-operator", then_second["id"], "operation", "+="),
                ("then-second-reference", then_left["id"], "reference", "foreign@0"),
            ):
                assert isinstance(node_id, int)
                altered = cast(
                    dict[str, list[dict[str, object]]],
                    json.loads(frontend.stdout),
                )
                altered["nodes"][node_id - 1][field] = value
                guest = Path(scratch) / f"invalid-multi-arm-{label}.malbolge"
                refused = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        str(LAYOUT),
                        "--output",
                        str(guest),
                        "--capsule",
                    ],
                    input=json.dumps(altered).encode(),
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertNotEqual(refused.returncode, 0, label)
                self.assertRegex(refused.stderr, rb"Unsupported|Malformed")
                self.assertFalse(guest.exists(), label)

    def test_mixed_conditional_writes_and_output_reach_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_mixed_conditional_output.c"
        ).read_text()

        else_arm = (
            "        } else {\n"
            "            b = (next + 1U) & 255U;\n"
            "            putchar((int)(next ^ 45U));\n"
            "        }"
        )
        self.assertEqual(source.count(else_arm), 1)
        no_else = source.replace(else_arm, "        }")

        def oracle(iterations: int, *, with_else: bool) -> bytes:
            a, b, index = 1, 1, 0
            result = bytearray()
            while index < iterations:
                following = (a + b) & 255
                if (index & 1) == 0:
                    a = following
                    result.append(following ^ 83)
                elif with_else:
                    b = (following + 1) & 255
                    result.append(following ^ 45)
                index += 1
            return bytes(result)

        self.assertEqual(oracle(2, with_else=True), b"Q.")
        self.assertEqual(oracle(1, with_else=True), b"Q")
        self.assertEqual(oracle(2, with_else=False), b"Q")
        cases = (
            ("both-arms", source, 2, True),
            ("one-trip", source.replace("i < 2U", "i < 1U"), 1, True),
            ("no-else", no_else, 2, False),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, text, bound, with_else in cases:
                with self.subTest(label=label):
                    candidate = Path(scratch) / f"mixed-{label}.c"
                    _ = candidate.write_text(text)
                    guest = Path(scratch) / f"mixed-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/mixed-conditional-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=120,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for guest_input in (b"", bytes((255, 0, 128))):
                        execution = subprocess.run(
                            [str(VM), str(guest), "--input-stdin", "--report-steps"],
                            input=guest_input,
                            check=False,
                            capture_output=True,
                            timeout=30,
                        )
                        self.assertEqual(execution.returncode, 0, execution.stderr)
                        self.assertEqual(
                            execution.stdout, oracle(bound, with_else=with_else)
                        )
                        self.assertRegex(
                            execution.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_mixed_conditional_rejects_unproved_effects(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_mixed_conditional_output.c"
        ).read_text()
        variants = {
            "selected-postincrement": source.replace("a = next;", "a = next++;"),
            "unselected-postincrement": source.replace(
                "b = (next + 1U) & 255U;", "b = next++;"
            ),
            "unselected-undefined": source.replace("next ^ 45U", "next / 0U"),
            "unselected-hidden-call": source.replace(
                "putchar((int)(next ^ 45U));",
                'putchar((int)(next ^ 45U)); puts("extra");',
            ),
            "unselected-unbraced-branch": source.replace(
                "b = (next + 1U) & 255U;",
                "if (next) b = next;",
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, altered in variants.items():
                with self.subTest(label=label):
                    candidate = Path(scratch) / f"invalid-{label}.c"
                    _ = candidate.write_text(altered)
                    guest = Path(scratch) / f"invalid-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/mixed-conditional-invalid-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=45,
                    )
                    self.assertNotEqual(compiled.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_mixed_conditional_forged_ast_refuses(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT / "tests/compiler/c-frontend/accepted/local_mixed_conditional_output.c"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/mixed-conditional-ast-v1",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            branch = next(n for n in nodes if n["kind"] == "if-statement")
            arms = [
                n
                for n in nodes
                if n["kind"] == "compound-statement" and n["parent"] == branch["id"]
            ]
            self.assertEqual(len(arms), 2)
            calls = [
                next(
                    n
                    for n in nodes
                    if n["kind"] == "call-expression" and n["parent"] == arm["id"]
                )
                for arm in arms
            ]
            assignments = [
                next(
                    n
                    for n in nodes
                    if n["kind"] == "binary-expression"
                    and n.get("operation") == "="
                    and n["parent"] == arm["id"]
                )
                for arm in arms
            ]
            for label, node, field, value in (
                ("then-call-parent", calls[0], "parent", branch["id"]),
                ("else-call-parent", calls[1], "parent", branch["id"]),
                ("else-write-parent", assignments[1], "parent", branch["id"]),
                ("else-call-kind", calls[1], "kind", "binary-expression"),
            ):
                with self.subTest(label=label):
                    altered = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    node_id = cast(int, node["id"])
                    altered["nodes"][node_id - 1][field] = value
                    guest = Path(scratch) / f"forged-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(altered).encode(),
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_nested_conditional_state_and_guest_output(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_nested_conditional_output.c"
        ).read_text()
        outer_else = (
            "        } else {\n"
            "            if ((next & 1U) != 0U) {\n"
            "                b = (next + 1U) & 255U;\n"
            "                putchar((int)(next ^ 45U));\n"
            "            } else {\n"
            "                b = next;\n"
            "                putchar((int)(next ^ 44U));\n"
            "            }\n"
            "        }"
        )
        nested_else = (
            "            } else {\n"
            "                b = next;\n"
            "                putchar((int)(next ^ 44U));\n"
            "            }"
        )
        self.assertEqual(source.count(outer_else), 1)
        self.assertEqual(source.count(nested_else), 1)

        def oracle(
            *, outer_else_enabled: bool, inner_else_enabled: bool
        ) -> bytes:
            a, b, i = 1, 1, 0
            result = bytearray()
            while i < 2:
                next_value = (a + b) & 255
                if (i & 1) == 0:
                    if (next_value & 1) == 0:
                        a = next_value
                        result.append(next_value ^ 83)
                    else:
                        a = (next_value + 1) & 255
                        result.append(next_value ^ 84)
                elif outer_else_enabled:
                    if (next_value & 1) != 0:
                        b = (next_value + 1) & 255
                        result.append(next_value ^ 45)
                    elif inner_else_enabled:
                        b = next_value
                        result.append(next_value ^ 44)
                i += 1
            return bytes(result)

        self.assertEqual(
            oracle(outer_else_enabled=True, inner_else_enabled=True), b"Q."
        )
        self.assertEqual(
            oracle(outer_else_enabled=False, inner_else_enabled=True), b"Q"
        )
        self.assertEqual(
            oracle(outer_else_enabled=True, inner_else_enabled=False), b"Q."
        )
        cases = (
            ("both-nested-arms", source, True, True),
            (
                "skipped-outer-else",
                source.replace(outer_else, "        }"),
                False,
                True,
            ),
            (
                "nested-if-without-else",
                source.replace(nested_else, "            }"),
                True,
                False,
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source_text, use_outer_else, use_inner_else in cases:
                with self.subTest(label=label):
                    candidate = Path(scratch) / f"nested-{label}.c"
                    _ = candidate.write_text(source_text)
                    guest = Path(scratch) / f"nested-{label}.malbolge"
                    compiled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/nested-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=150,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(guest.is_file())
                    for guest_input in (b"", b"\xff\x00\x80"):
                        executed = subprocess.run(
                            [
                                str(VM),
                                str(guest),
                                "--input-stdin",
                                "--report-steps",
                            ],
                            input=guest_input,
                            check=False,
                            capture_output=True,
                            timeout=30,
                        )
                        self.assertEqual(
                            executed.returncode, 0, executed.stderr
                        )
                        self.assertEqual(
                            executed.stdout,
                            oracle(
                                outer_else_enabled=use_outer_else,
                                inner_else_enabled=use_inner_else,
                            ),
                        )
                        self.assertRegex(
                            executed.stderr,
                            rb"^malbolge-steps-v1:[1-9][0-9]*\n$",
                        )

    def test_nested_conditional_unproved_source_refuses_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_nested_conditional_output.c"
        ).read_text()
        variants = {
            "selected-increment": source.replace("a = next;", "a = next++;"),
            "unselected-undefined": source.replace("next ^ 44U", "next / 0U"),
            "unselected-hidden-increment": source.replace(
                "b = next;", "b = next; next++;"
            ),
            "unselected-unsupported-call": source.replace(
                "b = next;", 'b = next; puts("hidden");'
            ),
            "unbraced-inner": source.replace(
                "if ((next & 1U) != 0U) {",
                "if ((next & 1U) != 0U)",
            ),
            "too-deep": source.replace(
                "a = next;",
                "if (next) { if (next) { if (next) { a = next; } } }",
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            for label, source_text in variants.items():
                with self.subTest(label=label):
                    candidate = Path(scratch) / f"nested-invalid-{label}.c"
                    _ = candidate.write_text(source_text)
                    guest = Path(scratch) / f"nested-invalid-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--repository-tools",
                            "--source-id",
                            f"tests/nested-invalid-{label}-v1",
                            "--capsule",
                            "--output",
                            str(guest),
                            str(candidate),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=50,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)

    def test_nested_conditional_forged_ast_refuses_guest(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT)):
            self.skipTest("pinned C compiler binaries are not built")
        source = (
            ROOT
            / "tests/compiler/c-frontend/accepted"
            / "local_nested_conditional_output.c"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            frontend = subprocess.run(
                [
                    str(FRONTEND),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "tests/nested-conditional-ast-v1",
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(frontend.returncode, 0, frontend.stderr)
            parsed = cast(dict[str, object], json.loads(frontend.stdout))
            nodes = cast(list[dict[str, object]], parsed["nodes"])
            nested = [n for n in nodes if n["kind"] == "if-statement"]
            self.assertEqual(len(nested), 3)
            outer = nested[0]
            first = nested[1]
            self.assertTrue(
                any(
                    n["id"] == first["parent"] and n["parent"] == outer["id"]
                    for n in nodes
                )
            )
            arm = next(
                n
                for n in nodes
                if (
                    n["kind"] == "compound-statement"
                    and n["parent"] == first["id"]
                )
            )
            write = next(
                n
                for n in nodes
                if n["kind"] == "binary-expression"
                and n.get("operation") == "="
                and n["parent"] == arm["id"]
            )
            call = next(
                n
                for n in nodes
                if n["kind"] == "call-expression" and n["parent"] == arm["id"]
            )
            for label, node, field, value in (
                ("inner-if-parent", first, "parent", outer["id"]),
                ("inner-arm-parent", arm, "parent", outer["id"]),
                ("inner-write-parent", write, "parent", first["id"]),
                ("inner-output-parent", call, "parent", first["id"]),
                ("inner-if-metadata", first, "operation", "&&"),
            ):
                with self.subTest(label=label):
                    altered = cast(
                        dict[str, list[dict[str, object]]],
                        json.loads(frontend.stdout),
                    )
                    node_id = cast(int, node["id"])
                    altered["nodes"][node_id - 1][field] = value
                    guest = Path(scratch) / f"nested-forged-{label}.malbolge"
                    refused = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--output",
                            str(guest),
                            "--capsule",
                        ],
                        input=json.dumps(altered).encode(),
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertNotEqual(refused.returncode, 0, label)
                    self.assertFalse(guest.exists(), label)


if __name__ == "__main__":
    _ = unittest.main()
