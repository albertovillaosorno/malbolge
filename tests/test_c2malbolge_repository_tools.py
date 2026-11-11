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
#   - Explicit repository-pinned compiler tool selection and executable guest proof.
# - Must-Not:
#   - Replace pinned Clang with stub JSON or pretend to bootstrap absent tools.
# - Allows:
#   - Inputs: bounded native C file and repository-pinned built toolchain.
#   - Outputs: actual current-profile capsule and guest VM stdout/step evidence.
#   - Side effects: ignored .temp fixtures only.
# - Split-When:
#   - A supported installer takes over the local compiler build lifecycle.
# - Merge-When:
#   - The native source compiler CLI owns a full turnkey integration suite.
# - Summary:
#   - A single opt-in flag can compile C with the already built pinned toolchain.
# - Description:
#   - Invalid option combinations refuse before any frontend process launch.
# - Usage:
#   - python3.14 -B -m unittest tests.test_c2malbolge_repository_tools -v
# - Defaults:
#   - Skip real guest execution if actual pinned executables are unprovisioned.

"""Repository-pinned tools are an opt-in to real C-to-guest compilation."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import final

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
NATIVE = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin"
NATIVE_NAME = "malbolge-c-frontend.exe" if os.name == "nt" else "malbolge-c-frontend"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
RUST = ROOT / ".cache/rust/target/debug"
RUST_SUFFIX = ".exe" if os.name == "nt" else ""
SOURCE = b"void noop(void) { return; }\n"


@final
class RepositoryToolCompilerTests(unittest.TestCase):
    def _command(self, source: Path, target: Path, *extra: str) -> list[str]:
        return [
            sys.executable,
            "-B",
            str(DRIVER),
            "--repository-tools",
            "--output",
            str(target),
            *extra,
            str(source),
        ]

    def _real_binaries(self) -> Path:
        guest = RUST / f"malbolge{RUST_SUFFIX}"
        binaries = (
            NATIVE / NATIVE_NAME,
            RUST / f"c2malbolge_json{RUST_SUFFIX}",
            RUST / f"malbolge_layout{RUST_SUFFIX}",
            guest,
        )
        if not RESOURCE.is_dir() or not all(
            path.is_file() and os.access(path, os.X_OK) for path in binaries
        ):
            self.skipTest("actual repository-pinned compiler/VM tools not provisioned")
        return guest

    def test_missing_explicit_tools_cannot_fall_through_to_repository_mode(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "noop.c", root / "noop.malbolge"
            _ = source.write_bytes(SOURCE)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--output",
                    str(target),
                    str(source),
                ],
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(b"explicit compiler tools required", completed.stderr)
            self.assertFalse(target.exists())

    def test_repository_mode_rejects_mixed_explicit_capabilities(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "noop.c", root / "noop.malbolge"
            _ = source.write_bytes(SOURCE)
            for option in (
                "--frontend",
                "--json-adapter",
                "--layout-backend",
                "--guest-include",
                "--resource-dir",
            ):
                with self.subTest(option=option):
                    completed = subprocess.run(
                        self._command(source, target, option, str(root)),
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn(b"cannot be mixed", completed.stderr)
                    self.assertFalse(target.exists())

    def test_native_source_basename_compiles_and_runs_real_capsule(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "not-in-the-repo.c", root / "result.malbolge"
            _ = source.write_bytes(SOURCE)
            command = self._command(source, target, "--capsule")
            compiled = subprocess.run(
                command, capture_output=True, check=False, timeout=120
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertGreater(target.stat().st_size, len(SOURCE))
            executed = subprocess.run(
                [str(vm), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:2\n")

            original_artifact = target.read_bytes()
            repeat = subprocess.run(
                command, capture_output=True, check=False, timeout=10
            )
            self.assertNotEqual(repeat.returncode, 0)
            self.assertIn(b"no-clobber", repeat.stderr)
            self.assertEqual(target.read_bytes(), original_artifact)

    def test_pinned_two_zero_calls_emit_ordered_guest_nul_bytes(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            source = Path(temporary) / "two-zeros.c"
            target = Path(temporary) / "two-zeros.malbolge"
            _ = source.write_bytes(
                b"#include <stdio.h>\nvoid emit(void) { putchar(0); putchar(0); return; }\n"
            )
            compiled = subprocess.run(
                self._command(source, target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(vm), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"\x00\x00")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:3\n")

    def test_witnessed_nonzero_c_literals_emit_actual_guest_bytes(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            # The independently witnessed seeded-layout table is count-specific.
            for byte, outputs in ((23, 1), (65, 2), (146, 3), (65, 10)):
                with self.subTest(byte=byte, outputs=outputs):
                    source = root / f"literal-{byte}-{outputs}.c"
                    target = root / f"literal-{byte}-{outputs}.malbolge"
                    statements = " ".join(f"putchar({byte});" for _ in range(outputs))
                    _ = source.write_text(
                        f"#include <stdio.h>\nvoid emit(void) {{ {statements} return; }}\n",
                        encoding="ascii",
                    )
                    compiled = subprocess.run(
                        self._command(source, target, "--capsule"),
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    executed = subprocess.run(
                        [str(vm), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, bytes([byte]) * outputs)
                    self.assertRegex(
                        executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                    )

    def test_repository_mode_wrapped_unsigned_c_literals_reach_guest(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source = root / "wrapped-unsigned.c"
            target = root / "wrapped-unsigned.malbolge"
            # Clang generates five AST nodes for each wrapped argument.
            # An omitted return is an implicit void return, not a lost effect.
            _ = source.write_bytes(
                b"#include <stdio.h>\n"
                + b"void emit(void) { putchar((65)); putchar(65u); }\n"
            )
            compiled = subprocess.run(
                self._command(source, target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(vm), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"AA")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:27\n")

            nested = root / "nested.c"
            rejected = root / "nested.malbolge"
            _ = nested.write_bytes(
                b"#include <stdio.h>\nvoid emit(void) { putchar(((65))); }\n"
            )
            refused = subprocess.run(
                self._command(nested, rejected, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b"normalized frontend rejected", refused.stderr)
            self.assertFalse(rejected.exists())

    def test_repository_mode_inert_statements_between_output_calls(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "inert.c", root / "inert.malbolge"
            # Both statements are source-proven inert; their AST nodes must
            # not be misread as independent guest output or discarded calls.
            _ = source.write_bytes(
                b"#include <stdio.h>\n"
                + b"void emit(void) { putchar(65); ; putchar(65); 0; return; }\n"
            )
            compiled = subprocess.run(
                self._command(source, target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(vm), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"AA")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:27\n")

    def test_repository_mode_sibling_scopes_preserve_guest_output(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "sibling-blocks.c", root / "sibling-blocks.malbolge"
            # Clang nests the calls under distinct CompoundStmt parents;
            # adjacent }{ and }return; tokens must preserve source order.
            _ = source.write_bytes(
                b"#include <stdio.h>\n"
                + b"void emit(void) { { putchar(65); }{ ; putchar(65); }return; }\n"
            )
            compiled = subprocess.run(
                self._command(source, target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(vm), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"AA")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:27\n")

    def test_repository_mode_nested_early_return_refuses_publication(self) -> None:
        _ = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "early-return.c", root / "early-return.malbolge"
            # Flattening this block would incorrectly emit an unreachable A.
            _ = source.write_bytes(
                b"#include <stdio.h>\n"
                + b"void emit(void) { putchar(65); { return; } putchar(65); }\n"
            )
            compiled = subprocess.run(
                self._command(source, target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"normalized frontend rejected", compiled.stderr)
            self.assertFalse(target.exists())

    def test_repository_mode_interleaved_nonzero_expression_refuses_publication(
        self,
    ) -> None:
        _ = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "effect.c", root / "effect.malbolge"
            _ = source.write_bytes(
                b"#include <stdio.h>\n"
                + b"void emit(void) { putchar(65); 1; putchar(65); return; }\n"
            )
            compiled = subprocess.run(
                self._command(source, target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"normalized frontend rejected", compiled.stderr)
            self.assertFalse(target.exists())

    def test_repository_mode_excess_inert_statements_refuse_publication(self) -> None:
        _ = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            source, target = root / "excess.c", root / "excess.malbolge"
            # Source-admitted no-op statements still have a hard AST bound.
            _ = source.write_bytes(
                b"#include <stdio.h>\nvoid emit(void) { putchar(65); "
                + (b"; " * 129)
                + b"putchar(65); return; }\n"
            )
            compiled = subprocess.run(
                self._command(source, target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn(b"normalized frontend rejected", compiled.stderr)
            self.assertFalse(target.exists())

    def test_pinned_extended_single_literals_use_guest_rotation(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            # Output values come from actual guest rotation, not host printing.
            for byte, expected, steps in ((39, b"'", 50), (157, b"\x9d", 67)):
                with self.subTest(byte=byte):
                    source = root / f"literal-{byte}.c"
                    target = root / f"literal-{byte}.malbolge"
                    _ = source.write_text(
                        "#include <stdio.h>\n"
                        + f"void emit(void) {{ putchar({byte}); return; }}\n",
                        encoding="ascii",
                    )
                    compiled = subprocess.run(
                        self._command(source, target, "--capsule"),
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    executed = subprocess.run(
                        [str(vm), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=35,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertEqual(
                        executed.stderr,
                        f"malbolge-steps-v1:{steps}\n".encode("ascii"),
                    )

    def test_pinned_radix_c_literals_emit_witnessed_guest_byte(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            # Source spelling is Clang-owned; the guest result is byte 23.
            for index, literal in enumerate(("0x17", "027")):
                with self.subTest(literal=literal):
                    source = root / f"radix-{index}.c"
                    target = root / f"radix-{index}.malbolge"
                    _ = source.write_text(
                        "#include <stdio.h>\n"
                        + f"void emit(void) {{ putchar({literal}); return; }}\n",
                        encoding="ascii",
                    )
                    compiled = subprocess.run(
                        self._command(source, target, "--capsule"),
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    executed = subprocess.run(
                        [str(vm), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"\x17")
                    self.assertRegex(
                        executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                    )

    def test_pinned_c_escape_literals_emit_guest_control_bytes(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            # The guest VM must emit bytes, not human-readable escape text.
            for index, (literal, expected) in enumerate(
                ((r"'\n'", b"\n"), (r"'\t'", b"\t"))
            ):
                with self.subTest(literal=literal):
                    source = root / f"escape-{index}.c"
                    target = root / f"escape-{index}.malbolge"
                    _ = source.write_text(
                        "#include <stdio.h>\n"
                        + f"void emit(void) {{ putchar({literal}); return; }}\n",
                        encoding="ascii",
                    )
                    compiled = subprocess.run(
                        self._command(source, target, "--capsule"),
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    executed = subprocess.run(
                        [str(vm), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertRegex(
                        executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                    )

    def test_pinned_putchar_i32_arguments_emit_low_byte_in_guest(self) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            # C putchar converts int to unsigned char: the full argument is
            # source-checked, but the guest observes only its low eight bits.
            for index, (argument, outputs, expected) in enumerate(
                ((256, 1, b"\x00"), (321, 2, b"AA"), (65559, 1, b"\x17"))
            ):
                with self.subTest(argument=argument, outputs=outputs):
                    source = root / f"wide-{index}.c"
                    target = root / f"wide-{index}.malbolge"
                    statements = " ".join(
                        f"putchar({argument});" for _ in range(outputs)
                    )
                    _ = source.write_text(
                        f"#include <stdio.h>\nvoid emit(void) {{ {statements} return; }}\n",
                        encoding="ascii",
                    )
                    compiled = subprocess.run(
                        self._command(source, target, "--capsule"),
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    executed = subprocess.run(
                        [str(vm), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, expected)
                    self.assertRegex(
                        executed.stderr, rb"^malbolge-steps-v1:[1-9][0-9]*\n$"
                    )

    def test_unwitnessed_or_mixed_c_literals_do_not_publish(self) -> None:
        _ = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            root = Path(temporary)
            for index, statements in enumerate(
                (
                    "putchar(1);",
                    "putchar(23); putchar(23);",
                    "putchar(23); putchar(65);",
                    "putchar(-1);",
                )
            ):
                with self.subTest(source=statements):
                    source = root / f"rejected-{index}.c"
                    target = root / f"rejected-{index}.malbolge"
                    _ = source.write_text(
                        f"#include <stdio.h>\nvoid emit(void) {{ {statements} return; }}\n",
                        encoding="ascii",
                    )
                    compiled = subprocess.run(
                        self._command(source, target, "--capsule"),
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())
                    self.assertTrue(compiled.stderr)

    def test_native_zero_output_emits_real_nul_and_unwitnessed_nonzero_refuses(
        self,
    ) -> None:
        vm = self._real_binaries()
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            directory = Path(temporary)
            good = directory / "emit.c"
            target = directory / "emit.malbolge"
            _ = good.write_bytes(
                b"#include <stdio.h>\nvoid emit(void) { putchar(0); return; }\n"
            )
            compiled = subprocess.run(
                self._command(good, target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [str(vm), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"\x00")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:2\n")

            bad = directory / "not-supported.c"
            rejected_target = directory / "not-supported.malbolge"
            _ = bad.write_bytes(
                b"#include <stdio.h>\nvoid emit(void) { putchar(1); return; }\n"
            )
            rejected = subprocess.run(
                self._command(bad, rejected_target, "--capsule"),
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertNotEqual(rejected.returncode, 0)
            # A canonical nonzero byte passes C/IR admission, but this
            # byte/count pair has no independently verified guest layout.
            self.assertIn(b"layout backend exited unsuccessfully", rejected.stderr)
            self.assertFalse(rejected_target.exists())


if __name__ == "__main__":
    _ = unittest.main()
