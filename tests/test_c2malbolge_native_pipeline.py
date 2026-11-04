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
#   - Real C source through pinned Clang, normalized JSON, guest layout, and VM.
# - Must-Not:
#   - Substitute synthetic JSON, a mock frontend, or host-side execution.
# - Allows:
#   - Inputs: exact native frontend, compiler binaries, and local C fixtures.
#   - Outputs: checked raw/capsule guest behavior and rejected C evidence.
#   - Side effects: isolated ignored .temp test fixtures only.
# - Split-When:
#   - Broad native C language acceptance gains a separate test lifecycle.
# - Merge-When:
#   - The complete turnkey compiler test covers the same real native path.
# - Summary:
#   - Proves a real native C frontend can produce VM-executable Malbolge.
# - Description:
#   - The controlled-JSON pipeline tests do not prove actual C parsing.
# - Usage:
#   - MALBOLGE_NATIVE_FRONTEND_BIN=/path/to/malbolge-c-frontend \
#     MALBOLGE_CLANG_RESOURCE_DIR=/path/to/clang/22 \
#     python3.14 -B -m unittest tests.test_c2malbolge_native_pipeline -v
# - Defaults:
#   - Use repository-pinned binaries; skip when unprovisioned unless overridden.

"""Native Clang source-C to independently executed Malbolge integration."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import final

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
FRONTEND_ROOT = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin"
FRONTEND_NAME = "malbolge-c-frontend.exe" if os.name == "nt" else "malbolge-c-frontend"
DEFAULT_FRONTEND = FRONTEND_ROOT / FRONTEND_NAME
DEFAULT_RESOURCE_DIR = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
RUST_BIN = ROOT / ".cache/rust/target/debug"

EXPLICIT_VOID = b"void noop(void) { return; }\n"
IMPLICIT_VOID = b"void noop(void) {}\n"
NESTED_VOID = b"void noop(void) {; { ; return; }}\n"
STANDALONE_ZERO = b"void noop(void) { 0; return; }\n"
CAST_ZERO = b"void noop(void) { (void)0; return; }\n"
CAST_ONE = b"void noop(void) { (void)1; return; }\n"
CAST_BINARY = b"void noop(void) { (void)(1+2); return; }\n"
ZERO_OUTPUT = b"#include <stdio.h>\nvoid emit(void) { putchar(0); return; }\n"
NONZERO_OUTPUT = b"#include <stdio.h>\nvoid emit(void) { putchar(1); return; }\n"
EXTRA_OUTPUT = (
    b"#include <stdio.h>\nvoid emit(void) { putchar(0); putchar(0); return; }\n"
)
MIXED_OUTPUT = (
    b"#include <stdio.h>\nvoid emit(void) { putchar(0); putchar(1); return; }\n"
)
EFFECTFUL_VOID = b"void noop(void) { volatile int value = 1; }\n"
INVALID_C = b"void noop(void) { return\n"


def _binary(env_var: str, default: Path) -> Path:
    return Path(os.environ.get(env_var, str(default)))


@final
class CToMalbolgeNativePipelineTests(unittest.TestCase):
    def _tools(self) -> tuple[Path, Path, Path, Path, Path]:
        frontend = _binary("MALBOLGE_NATIVE_FRONTEND_BIN", DEFAULT_FRONTEND)
        resource = _binary("MALBOLGE_CLANG_RESOURCE_DIR", DEFAULT_RESOURCE_DIR)
        adapter = _binary("MALBOLGE_JSON_ADAPTER_BIN", RUST_BIN / "c2malbolge_json")
        layout = _binary("MALBOLGE_LAYOUT_BIN", RUST_BIN / "malbolge_layout")
        vm = _binary("MALBOLGE_VM_BIN", RUST_BIN / "malbolge")
        binaries = (frontend, adapter, layout, vm)
        if (
            not all(path.is_file() and os.access(path, os.X_OK) for path in binaries)
            or not resource.is_dir()
        ):
            if "MALBOLGE_NATIVE_FRONTEND_BIN" in os.environ:
                self.fail(
                    "explicit native C test configuration has missing executables or Clang resources"
                )
            self.skipTest(
                "pinned native Clang frontend, resources, and Rust guest binaries required"
            )
        return frontend, resource, adapter, layout, vm

    def _compile(
        self,
        tools: tuple[Path, Path, Path, Path, Path],
        source: Path,
        target: Path,
        *,
        capsule: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        frontend, resource, adapter, layout, _ = tools
        args = [
            sys.executable,
            "-B",
            str(DRIVER),
            "--frontend",
            str(frontend),
            "--json-adapter",
            str(adapter),
            "--layout-backend",
            str(layout),
            "--guest-include",
            str(GUEST_INCLUDE),
            "--resource-dir",
            str(resource),
            "--source-id",
            "fixtures/noop.c",
            "--output",
            str(target),
        ]
        if capsule:
            args.append("--capsule")
        args.append(str(source))
        return subprocess.run(args, capture_output=True, check=False, timeout=120)

    def _run_guest(self, vm: Path, target: Path) -> None:
        executed = subprocess.run(
            [str(vm), str(target), "--report-steps"],
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(executed.returncode, 0, executed.stderr)
        self.assertEqual(executed.stdout, b"")
        self.assertEqual(executed.stderr, b"malbolge-steps-v1:2\n")

    def test_real_clang_explicit_and_implicit_void_compile_to_same_raw_guest(
        self,
    ) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            sources = (EXPLICIT_VOID, IMPLICIT_VOID)
            guests: list[bytes] = []
            for index, content in enumerate(sources):
                with self.subTest(source=content):
                    source = directory / f"noop-{index}.c"
                    target = directory / f"noop-{index}.malbolge"
                    _ = source.write_bytes(content)
                    compiled = self._compile(tools, source, target)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    guest = target.read_bytes()
                    self.assertEqual(len(guest), 2)
                    guests.append(guest)
                    self._run_guest(tools[4], target)
            self.assertEqual(guests[0], guests[1])

    def test_real_clang_nested_void_compiles_to_verified_capsule(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            source = Path(temporary) / "noop.c"
            target = Path(temporary) / "noop.malbolge"
            _ = source.write_bytes(NESTED_VOID)
            compiled = self._compile(tools, source, target, capsule=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertGreater(target.stat().st_size, len(NESTED_VOID))
            self._run_guest(tools[4], target)

    def test_real_clang_standalone_zero_reaches_guest_without_effects(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            source = Path(temporary) / "zero.c"
            target = Path(temporary) / "zero.malbolge"
            _ = source.write_bytes(STANDALONE_ZERO)
            compiled = self._compile(tools, source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertEqual(target.stat().st_size, 2)
            self._run_guest(tools[4], target)

    def test_real_clang_cast_zero_reaches_guest_without_effects(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            source = Path(temporary) / "cast-zero.c"
            target = Path(temporary) / "cast-zero.malbolge"
            _ = source.write_bytes(CAST_ZERO)
            compiled = self._compile(tools, source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertEqual(target.stat().st_size, 2)
            self._run_guest(tools[4], target)

    def test_real_clang_zero_output_executes_a_real_guest_nul_byte(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            source = Path(temporary) / "emit.c"
            target = Path(temporary) / "emit.malbolge"
            _ = source.write_bytes(ZERO_OUTPUT)
            compiled = self._compile(tools, source, target, capsule=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(tools[4]), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"\x00")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:2\n")

    def test_real_clang_repeated_zero_calls_emit_two_actual_nul_bytes(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            source = Path(temporary) / "emit-twice.c"
            target = Path(temporary) / "emit-twice.malbolge"
            _ = source.write_bytes(EXTRA_OUTPUT)
            compiled = self._compile(tools, source, target, capsule=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(tools[4]), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"\x00\x00")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:3\n")

    def test_real_clang_character_literals_emit_witnessed_guest_bytes(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            # This must pass through real pinned Clang, the JSON adapter, and
            # independently validated Malbolge guest code, not a source parser.
            cases = (
                (b"putchar('A'); putchar('A');", b"AA", 27),
                (b"putchar('\\x41'); putchar('\\x41');", b"AA", 27),
                (b"putchar('A'); putchar(65);", b"AA", 27),
                (b"putchar('\\0');", b"\x00", 2),
                (b"putchar(0); putchar('\\0');", b"\x00\x00", 3),
            )
            for index, (calls, expected, steps) in enumerate(cases):
                with self.subTest(calls=calls):
                    source = Path(temporary) / f"char-{index}.c"
                    target = Path(temporary) / f"char-{index}.malbolge"
                    _ = source.write_bytes(
                        b"#include <stdio.h>\nvoid emit(void) { "
                        + calls
                        + b" return; }\n"
                    )
                    compiled = self._compile(tools, source, target, capsule=True)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    executed = subprocess.run(
                        [str(tools[4]), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertEqual(
                        executed.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                    )

    def test_real_clang_implicit_void_return_after_output(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for index, (calls, expected, steps) in enumerate(
                (
                    (b"putchar(0);", b"\x00", 2),
                    (b"putchar('A'); putchar('A');", b"AA", 27),
                )
            ):
                with self.subTest(calls=calls):
                    source = Path(temporary) / f"implicit-emit-{index}.c"
                    target = Path(temporary) / f"implicit-emit-{index}.malbolge"
                    _ = source.write_bytes(
                        b"#include <stdio.h>\nvoid emit(void) { " + calls + b" }\n"
                    )
                    compiled = self._compile(tools, source, target, capsule=True)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    executed = subprocess.run(
                        [str(tools[4]), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertEqual(
                        executed.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                    )

    def test_real_clang_radix_integer_literals_emit_witnessed_guest_bytes(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            # Pinned Clang evaluates different C23 radix spellings to the same
            # byte before canonical typed IR and the independent guest VM run.
            cases = (
                (b"putchar(0x41); putchar(0101);", b"AA", 27),
                (b"putchar(0b01000001); putchar(65);", b"AA", 27),
                (b"putchar(0x0); putchar(000);", b"\x00\x00", 3),
            )
            for index, (calls, expected, steps) in enumerate(cases):
                with self.subTest(calls=calls):
                    source = Path(temporary) / f"radix-{index}.c"
                    target = Path(temporary) / f"radix-{index}.malbolge"
                    _ = source.write_bytes(
                        b"#include <stdio.h>\nvoid emit(void) { "
                        + calls
                        + b" return; }\n"
                    )
                    compiled = self._compile(tools, source, target, capsule=True)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    executed = subprocess.run(
                        [str(tools[4]), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertEqual(
                        executed.stderr, f"malbolge-steps-v1:{steps}\n".encode()
                    )

    def test_real_clang_unsupported_integer_operations_do_not_publish(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            cases = (
                b"putchar(0x41); putchar(0x42);",
                b"putchar(0x41 + 0);",
                b"putchar(0x100);",
            )
            for index, calls in enumerate(cases):
                with self.subTest(calls=calls):
                    source = Path(temporary) / f"invalid-radix-{index}.c"
                    target = Path(temporary) / f"invalid-radix-{index}.malbolge"
                    _ = source.write_bytes(
                        b"#include <stdio.h>\nvoid emit(void) { "
                        + calls
                        + b" return; }\n"
                    )
                    compiled = self._compile(tools, source, target)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())
                    self.assertIn(b"normalized frontend rejected", compiled.stderr)

    def test_real_clang_unsupported_character_operations_do_not_publish(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            cases = (
                b"putchar('A'); putchar('B');",
                b"putchar('A' + 1); putchar('A' + 1);",
                b"putchar('\\x100');",
            )
            for index, calls in enumerate(cases):
                with self.subTest(calls=calls):
                    source = Path(temporary) / f"invalid-char-{index}.c"
                    target = Path(temporary) / f"invalid-char-{index}.malbolge"
                    _ = source.write_bytes(
                        b"#include <stdio.h>\nvoid emit(void) { "
                        + calls
                        + b" return; }\n"
                    )
                    compiled = self._compile(tools, source, target)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())
                    self.assertIn(
                        b"native C frontend failed"
                        if index == 2
                        else b"normalized frontend rejected",
                        compiled.stderr,
                    )

    def test_real_clang_nonzero_or_mixed_output_rejects_guest(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for index, content in enumerate((NONZERO_OUTPUT, MIXED_OUTPUT)):
                with self.subTest(source=content):
                    source = Path(temporary) / f"invalid-emit-{index}.c"
                    target = Path(temporary) / f"invalid-emit-{index}.malbolge"
                    _ = source.write_bytes(content)
                    compiled = self._compile(tools, source, target)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())
                    self.assertIn(b"normalized frontend rejected", compiled.stderr)

    def test_real_clang_effects_and_syntax_errors_do_not_publish_guest(self) -> None:
        tools = self._tools()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            for index, source_bytes in enumerate(
                (EFFECTFUL_VOID, CAST_ONE, CAST_BINARY, INVALID_C)
            ):
                with self.subTest(source=source_bytes):
                    source = Path(temporary) / f"invalid-{index}.c"
                    target = Path(temporary) / f"invalid-{index}.malbolge"
                    _ = source.write_bytes(source_bytes)
                    compiled = self._compile(tools, source, target)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())
                    self.assertIn(
                        b"normalized frontend rejected"
                        if index != 3
                        else b"native C frontend failed",
                        compiled.stderr,
                    )


if __name__ == "__main__":
    _ = unittest.main()
