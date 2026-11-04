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
#   - Real typed adapter, layout publisher, and VM handoff from compiler CLI.
# - Must-Not:
#   - Present a controlled JSON producer as real native Clang C parsing.
# - Allows:
#   - Inputs: source-bound JSON from a controlled frontend producer.
#   - Outputs: actual Malbolge capsule with normative VM step evidence.
#   - Side effects: isolated ignored .temp test fixtures only.
# - Split-When:
#   - Pinned native Clang and full source-C acceptance tests become available.
# - Merge-When:
#   - The turnkey compiler tests cover this exact downstream handoff.
# - Summary:
#   - Full downstream producer/publisher/runner composition executes real code.
# - Description:
#   - Pinned Clang is not available in this test; Rust binaries are real.
# - Usage:
#   - python3.14 -B -m unittest discover -s tests
#     -p test_c2malbolge_real_pipeline.py -v
# - Defaults:
#   - Skip when built binaries are absent; do not replace them with stubs.

"""Real JSON adapter, layout, and VM validation with controlled frontend JSON."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import final

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
SOURCE = b"void noop(void) { return; }\n"
EMPTY_SOURCE = b"void noop(void) {}\n"
NULL_SOURCE = b"void noop(void) {; ; return;}\n"

# This source-bound JSON producer is not a Clang substitute. It creates only
# the exact, independently admitted normalized no-effect void wire.
FRONTEND = """#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import sys

source = Path(sys.argv[-1]).read_bytes()
implicit = source == b"void noop(void) {}\\n"
nulls = source == b"void noop(void) {; ; return;}\\n"
assert implicit or nulls or source == b"void noop(void) { return; }\\n"
source_id = sys.argv[sys.argv.index("--source-id") + 1]
def span(begin, end):
    return {"begin": {"byte": begin, "line": 1, "column": begin + 1},
            "end": {"byte": end, "line": 1, "column": end + 1}}
end = 29 if nulls else 18 if implicit else 27
nodes = [
    {"id":1, "parent":0, "kind":"function-declaration", "span":span(0,end),
     "name":"noop", "type":"fn()->void", "definition":"definition",
     "inline_specified":False, "linkage":"external", "storage_class":"none"},
    {"id":2, "parent":1, "kind":"compound-statement", "span":span(16,end)},
]
if nulls:
    nodes.extend([
        {"id":3, "parent":2, "kind":"null-statement", "span":span(17,18)},
        {"id":4, "parent":2, "kind":"null-statement", "span":span(19,20)},
        {"id":5, "parent":2, "kind":"return-statement", "span":span(21,28)},
    ])
elif not implicit:
    nodes.append({"id":3, "parent":2, "kind":"return-statement",
                  "span":span(18,25)})
if os.environ.get("MALBOLGE_TEST_FORGED_EFFECT") == "1":
    nodes.append({"id":4, "parent":2, "kind":"call-expression",
                  "span":span(18,25)})
print(json.dumps({
    "schema_version":1, "artifact_id":"malbolge-c-frontend-v1",
    "clang":{"version":"22.1.8", "target":"wasm32-unknown-unknown",
             "language":"c23"},
    "profile":{"abi_id":"malbolge-c32-v1",
               "target_profile":"malbolge-2026"},
    "source":{"id":source_id,"sha256":hashlib.sha256(source).hexdigest()},
    "nodes":nodes,
}))
"""


def real_binaries() -> tuple[Path, Path, Path] | None:
    """Select real compiled binaries; never synthesize a missing executable."""
    default = ROOT / ".cache/rust/target/debug"
    binaries = (
        Path(
            os.environ.get(
                "MALBOLGE_JSON_ADAPTER_BIN", str(default / "c2malbolge_json")
            )
        ),
        Path(os.environ.get("MALBOLGE_LAYOUT_BIN", str(default / "malbolge_layout"))),
        Path(os.environ.get("MALBOLGE_VM_BIN", str(default / "malbolge"))),
    )
    if all(binary.is_file() and os.access(binary, os.X_OK) for binary in binaries):
        return binaries
    return None


def fixture_files(
    directory: Path, *, empty_body: bool = False, null_statements: bool = False
) -> tuple[Path, Path, Path]:
    """Create a bounded C source and a deliberately controlled JSON producer."""
    frontend = directory / "frontend-stub"
    source = directory / "noop.c"
    target = directory / "noop.malbolge"
    _ = frontend.write_text(FRONTEND, encoding="utf-8")
    _ = frontend.chmod(0o700)
    _ = source.write_bytes(
        NULL_SOURCE if null_statements else EMPTY_SOURCE if empty_body else SOURCE
    )
    return frontend, source, target


def run_compiler(
    frontend: Path,
    source: Path,
    target: Path,
    adapter: Path,
    layout: Path,
    *,
    invalid_effect: bool = False,
    capsule: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["MALBOLGE_TEST_FORGED_EFFECT"] = "1" if invalid_effect else "0"
    argv = [
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
        str(source.parent),
        "--resource-dir",
        str(source.parent),
        "--source-id",
        "fixtures/noop.c",
        "--output",
        str(target),
    ]
    if capsule:
        argv.append("--capsule")
    argv.append(str(source))
    return subprocess.run(
        argv,
        env=environment,
        capture_output=True,
        check=False,
        timeout=120,
    )


@final
class CToMalbolgeRealPipelineTests(unittest.TestCase):
    def test_bounded_normalized_void_compiles_and_runs_on_real_vm(self) -> None:
        binaries = real_binaries()
        if binaries is None or os.name != "posix":
            self.skipTest("real Rust compiler/layout/VM binaries on POSIX required")
        adapter, layout, vm = binaries
        for empty_body in (False, True):
            for capsule in (False, True):
                with (
                    self.subTest(empty_body=empty_body, capsule=capsule),
                    tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary,
                ):
                    frontend, source, target = fixture_files(
                        Path(temporary), empty_body=empty_body
                    )
                    compiled = run_compiler(
                        frontend, source, target, adapter, layout, capsule=capsule
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    self.assertTrue(target.is_file())
                    if capsule:
                        self.assertGreater(
                            target.stat().st_size, len(source.read_bytes())
                        )
                    else:
                        self.assertEqual(target.stat().st_size, 2)
                    executed = subprocess.run(
                        [str(vm), str(target), "--report-steps"],
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(executed.returncode, 0, executed.stderr)
                    self.assertEqual(executed.stdout, b"")
                    self.assertEqual(executed.stderr, b"malbolge-steps-v1:2\n")

    def test_null_statements_produce_verified_capsule_on_real_vm(self) -> None:
        binaries = real_binaries()
        if binaries is None or os.name != "posix":
            self.skipTest("real Rust compiler/layout/VM binaries on POSIX required")
        adapter, layout, vm = binaries
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary:
            frontend, source, target = fixture_files(
                Path(temporary), null_statements=True
            )
            compiled = run_compiler(frontend, source, target, adapter, layout)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertGreater(target.stat().st_size, len(NULL_SOURCE))
            executed = subprocess.run(
                [str(vm), str(target), "--report-steps"],
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, b"")
            self.assertEqual(executed.stderr, b"malbolge-steps-v1:2\n")

    def test_extra_normalized_call_is_rejected_before_guest_publication(self) -> None:
        binaries = real_binaries()
        if binaries is None or os.name != "posix":
            self.skipTest("real Rust compiler/layout/VM binaries on POSIX required")
        adapter, layout, _ = binaries
        for empty_body in (False, True):
            with (
                self.subTest(empty_body=empty_body),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temporary,
            ):
                frontend, source, target = fixture_files(
                    Path(temporary), empty_body=empty_body
                )
                compiled = run_compiler(
                    frontend,
                    source,
                    target,
                    adapter,
                    layout,
                    invalid_effect=True,
                )
                self.assertNotEqual(compiled.returncode, 0)
                self.assertIn(b"normalized frontend rejected", compiled.stderr)
                self.assertFalse(target.exists())


if __name__ == "__main__":
    _ = unittest.main()
