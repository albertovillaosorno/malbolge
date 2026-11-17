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
#   - Complete signed-getchar C23 conditional-output EOF publication check.
# - Must-Not:
#   - Accept successful-byte guest parity as EOF parity or fake VM output.
# - Allows:
#   - Inputs: frozen source C, pinned Clang, and actual guest compiler/VM.
#   - Outputs: native-C parity with guest execution or typed no-artifact refusal.
#   - Side effects: isolated temporary test artifacts.
# - Split-When:
#   - General guest signed EOF-to-byte lowering is fully verified.
# - Merge-When:
#   - Shared C23 EOF tests cover every conditional source shape.
# - Summary:
#   - Refuse guest publication when signed conditional output misrepresents EOF.

"""Check source-C conditional signed EOF semantics before guest publication."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import final

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "tests/compiler/c-frontend/accepted"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
ADAPTER = ROOT / ".cache/rust/target/debug/c2malbolge_json"
LAYOUT = ROOT / ".cache/rust/target/debug/malbolge_layout"
VM = ROOT / ".cache/rust/target/debug/malbolge"
STEMS = (
    "unsigned_guarded_modular_output_live_input",
    "unsigned_nested_guarded_live_input",
    "unsigned_multiple_guarded_live_input",
    "unsigned_switch_guarded_live_input",
    "unsigned_scalar_truth_live_input",
    "unsigned_alias_induction_live_input",
    "unsigned_nested_alias_live_input",
)
INPUTS = (b"", b"\x00", b"\x80", b"\xff", b"\x00\x80\xff\x03")
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"

NESTED_STEMS = (
    "triple_control_live_input",
    "triple_induction_live_input",
    "nested_mixed_induction_live_input",
    "nested_outer_induction_live_input",
    "unsigned_nested_fresh_live_input",
    "unsigned_alias_induction_live_input",
    "unsigned_nested_alias_live_input",
)


@final
class GuardedC23EofPublicationTests(unittest.TestCase):
    def test_signed_local_scope_cannot_publish_byte_only_guest(self) -> None:
        """Nested induction and outer locals cannot establish input success."""
        if not ADAPTER.is_file():
            self.skipTest("pinned JSON adapter missing")
        golden = ROOT / "tests/compiler/c-frontend/golden"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for stem in NESTED_STEMS:
                output = Path(temporary) / f"{stem}.malbolge"
                result = subprocess.run(
                    [
                        str(ADAPTER),
                        "--layout-backend",
                        "/bin/false",
                        "--output",
                        str(output),
                        "--source",
                        str(SOURCES / f"{stem}.c"),
                    ],
                    input=(golden / f"{stem}.json").read_bytes(),
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                with self.subTest(stem=stem):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b"Unsupported", result.stderr)
                    self.assertFalse(output.exists())

    def test_transitive_alias_only_eof_outputs_refuse_before_layout(self) -> None:
        """A copied signed getchar is EOF-sensitive even without direct output."""
        dependencies = (FRONTEND, CLANG, ADAPTER)
        if not all(path.is_file() for path in dependencies):
            self.skipTest("pinned C frontend, Clang, or JSON adapter missing")
        cases = (
            (
                "unsigned_alias_induction_live_input",
                b"putchar(first);",
                b"putchar(alias);",
                3,
            ),
            (
                "unsigned_nested_alias_live_input",
                b"putchar(first);",
                b"putchar(localcopy);",
                4,
            ),
        )
        env = os.environ.copy()
        llvm_lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (llvm_lib, env.get("LD_LIBRARY_PATH", "")) if part
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            folder = Path(temporary)
            for stem, old, new, writes in cases:
                with self.subTest(shape=stem):
                    original = (SOURCES / f"{stem}.c").read_bytes()
                    self.assertEqual(original.count(old), 1)
                    source = folder / "alias-only.c"
                    _ = source.write_bytes(original.replace(old, new))
                    frontend = subprocess.run(
                        [
                            str(FRONTEND),
                            "--guest-include",
                            str(GUEST_INCLUDE),
                            "--resource-dir",
                            str(RESOURCE),
                            "--source-id",
                            "tests/alias-only-c23-eof-v1",
                            str(source),
                        ],
                        env=env,
                        capture_output=True,
                        check=False,
                        timeout=20,
                    )
                    self.assertEqual(frontend.returncode, 0, frontend.stderr)
                    guest = folder / "alias-only.malbolge"
                    adapter = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            "/bin/false",
                            "--output",
                            str(guest),
                            "--source",
                            str(source),
                        ],
                        input=frontend.stdout,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertNotEqual(adapter.returncode, 0)
                    self.assertIn(b"Unsupported", adapter.stderr)
                    self.assertNotIn(b"layout backend", adapter.stderr)
                    self.assertFalse(guest.exists())
                    wrapper = folder / "main.c"
                    _ = wrapper.write_text(
                        '#include "alias-only.c"\n'
                        "int main(void) { emit(); return 0; }\n",
                        encoding="ascii",
                    )
                    for optimization in ("-O0", "-O2"):
                        native = folder / f"native-{optimization[2:]}"
                        built = subprocess.run(
                            [
                                str(CLANG),
                                "-std=c23",
                                optimization,
                                "-Wall",
                                "-Wextra",
                                "-Werror",
                                "-fsanitize=undefined",
                                "-fno-sanitize-recover=all",
                                str(wrapper),
                                "-o",
                                str(native),
                            ],
                            env=env,
                            capture_output=True,
                            check=False,
                            timeout=20,
                        )
                        self.assertEqual(built.returncode, 0, built.stderr)
                        for data in INPUTS:
                            with self.subTest(mode=optimization, data=data.hex()):
                                run = subprocess.run(
                                    [str(native)],
                                    input=data,
                                    capture_output=True,
                                    check=False,
                                    timeout=10,
                                )
                                self.assertEqual(run.returncode, 0, run.stderr)
                                expected = bytes((data[0] if data else 255,)) * writes
                                self.assertEqual(run.stdout, expected)

    def test_complete_conditional_c23_outputs_match_or_refuse(self) -> None:
        dependencies = (FRONTEND, CLANG, ADAPTER, LAYOUT, VM)
        if not all(path.is_file() for path in dependencies):
            self.skipTest("pinned frontend, native C, compiler or VM missing")
        env = dict(os.environ)
        lib = str(ROOT / ".dependencies/llvm/22.1.8/lib")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            item for item in (lib, env.get("LD_LIBRARY_PATH", "")) if item
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            folder = Path(temporary)
            for stem in STEMS:
                source = SOURCES / f"{stem}.c"
                guest = folder / f"{stem}.malbolge"
                wrapper = folder / "main.c"
                _ = wrapper.write_text(
                    f'#include "{source}"\nint main(void) {{ emit(); return 0; }}\n',
                    encoding="utf-8",
                )
                native_outputs: list[tuple[bytes, ...]] = []
                for optimization in ("-O0", "-O2"):
                    executable = folder / f"native-{optimization[2:]}"
                    built = subprocess.run(
                        [
                            str(CLANG),
                            "-std=c23",
                            optimization,
                            "-fsanitize=undefined",
                            "-fno-sanitize-recover=all",
                            str(wrapper),
                            "-o",
                            str(executable),
                        ],
                        env=env,
                        capture_output=True,
                        check=False,
                        timeout=45,
                    )
                    self.assertEqual(built.returncode, 0, built.stderr)
                    outputs = []
                    for data in INPUTS:
                        result = subprocess.run(
                            [str(executable)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=15,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        outputs.append(result.stdout)
                    native_outputs.append(tuple(outputs))
                with self.subTest(source=stem):
                    self.assertEqual(native_outputs[0], native_outputs[1])
                    self.assertTrue(native_outputs[0][0])
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(DRIVER),
                        "--repository-tools",
                        "--capsule",
                        str(source),
                        "--output",
                        str(guest),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=120,
                )
                if compiled.returncode != 0:
                    with self.subTest(source=stem, result="refusal"):
                        self.assertIn(b"Unsupported", compiled.stderr)
                        self.assertFalse(guest.exists())
                    continue
                self.assertTrue(guest.is_file())
                for data, expected in zip(INPUTS, native_outputs[0], strict=True):
                    observed = subprocess.run(
                        [str(VM), str(guest), "--input-stdin", "--max-steps", "128"],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    with self.subTest(source=stem, stdin=data.hex()):
                        self.assertEqual(observed.returncode, 0, observed.stderr)
                        self.assertEqual(observed.stdout, expected)


if __name__ == "__main__":
    unittest.main()
