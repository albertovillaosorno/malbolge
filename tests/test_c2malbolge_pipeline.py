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
#   - Process-level failure ordering and source binding for the C driver.
# - Must-Not:
#   - Mistake stub executables for a pinned Clang or real Malbolge guest.
# - Allows:
#   - Inputs: temporary C sources and controlled executable stubs.
#   - Outputs: exact invocation, no-clobber and fail-closed assertions.
#   - Side effects: isolated ignored .temp fixtures only.
# - Split-When:
#   - Actual native Clang build gains independent end-to-end acceptance.
# - Merge-When:
#   - One verified compiler command replaces process composition.
# - Summary:
#   - A failing or forged frontend never launches the publishing adapter.
# - Description:
#   - Real compiler/VM acceptance remains with their own executable tests.
# - Usage:
#   - python3.14 -B -m unittest tests/test_c2malbolge_pipeline.py -v
# - Defaults:
#   - No mock case claims C-to-Malbolge semantic completeness.

"""Subprocess composition tests; child stubs are not compiler implementations."""

import hashlib
import os
import runpy
import subprocess
import sys
import tempfile
import textwrap
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import cast, final, override

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"

STUB = textwrap.dedent("""\
    #!/usr/bin/env python3
    import hashlib
    import json
    import os
    from pathlib import Path
    import sys

    role = Path(sys.argv[0]).name
    mode = os.environ.get('COMPILER_STUB_MODE', '')
    with open(os.environ['COMPILER_STUB_TRACE'], 'ab') as trace:
        trace.write(b'F' if role == 'frontend' else b'A')
    if role == 'frontend':
        if mode == 'FRONTEND_FAILURE':
            sys.exit(3)
        if mode == 'OVERSIZE':
            sys.stdout.buffer.write(b'x' * 1_048_577)
            sys.exit(0)
        source = Path(sys.argv[-1])
        payload = {
            'source': {
                'id': sys.argv[sys.argv.index('--source-id') + 1],
                'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            },
        }
        if mode == 'WRONG_DIGEST':
            payload['source']['sha256'] = 'f' * 64
        if mode == 'WRONG_ID':
            payload['source']['id'] = 'not-this-source.c'
        if mode == 'SOURCE_CHANGED':
            source.write_bytes(b'void noop(void) { }\\n')
        if mode == 'DUPLICATE':
            print('{' + '\"source\": {},' + '\"source\": {}' + '}')
        else:
            print(json.dumps(payload))
    else:
        assert sys.argv[1:3] == ['--layout-backend', os.environ['COMPILER_STUB_LAYOUT']]
        assert sys.argv[3] == '--output'
        assert ('--capsule' in sys.argv) == (os.environ['COMPILER_STUB_CAPSULE'] == '1')
        payload = json.loads(sys.stdin.buffer.read())
        assert payload['source']['id'] == 'fixtures/noop.c'
        if mode == 'ADAPTER_FAILURE':
            sys.exit(4)
        if mode == 'ADAPTER_FALSE_SUCCESS':
            sys.exit(0)
        Path(sys.argv[4]).write_bytes(b'stub-artifact')
    """)


@final
class CToMalbolgeDriverTests(unittest.TestCase):
    @override
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.temporary: tempfile.TemporaryDirectory[str] | None = None
        self.path = Path()
        self.source = Path()
        self.target = Path()
        self.trace = Path()
        self.frontend = Path()
        self.adapter = Path()
        self.layout = Path()

    @override
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".temp")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)
        self.source = self.path / "program.c"
        _ = self.source.write_bytes(b"void noop(void) { return; }\n")
        self.target = self.path / "output.malbolge"
        self.trace = self.path / "trace"
        self.frontend = self.path / "frontend"
        self.adapter = self.path / "adapter"
        self.layout = self.path / "layout"
        for executable in (self.frontend, self.adapter):
            _ = executable.write_text(STUB, encoding="utf-8")
            _ = executable.chmod(0o700)

    def run_pipeline(
        self,
        mode: str = "",
        *,
        capsule: bool = True,
        source_id: str = "fixtures/noop.c",
    ) -> subprocess.CompletedProcess[bytes]:
        environment = os.environ.copy()
        environment.update(
            {
                "COMPILER_STUB_MODE": mode,
                "COMPILER_STUB_TRACE": str(self.trace),
                "COMPILER_STUB_LAYOUT": str(self.layout),
                "COMPILER_STUB_CAPSULE": "1" if capsule else "0",
            }
        )
        argv = [
            sys.executable,
            "-B",
            str(DRIVER),
            "--frontend",
            str(self.frontend),
            "--json-adapter",
            str(self.adapter),
            "--layout-backend",
            str(self.layout),
            "--guest-include",
            str(self.path),
            "--resource-dir",
            str(self.path),
            "--source-id",
            source_id,
            "--output",
            str(self.target),
        ]
        if capsule:
            argv.append("--capsule")
        argv.append(str(self.source))
        return subprocess.run(argv, env=environment, capture_output=True, check=False)

    def assert_stages(self, expected: bytes) -> None:
        self.assertEqual(
            self.trace.read_bytes() if self.trace.exists() else b"", expected
        )

    def test_success_calls_frontend_then_adapter_with_source_bound_json(self):
        for capsule in (False, True):
            with self.subTest(capsule=capsule):
                self.target.unlink(missing_ok=True)
                self.trace.unlink(missing_ok=True)
                completed = self.run_pipeline(capsule=capsule)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assert_stages(b"FA")
                self.assertEqual(self.target.read_bytes(), b"stub-artifact")

    def test_frontend_failure_never_invokes_adapter(self):
        completed = self.run_pipeline("FRONTEND_FAILURE")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"native C frontend failed", completed.stderr)
        self.assert_stages(b"F")
        self.assertFalse(self.target.exists())

    def test_mismatch_or_corrupted_json_never_invokes_adapter(self):
        for mode in ("WRONG_DIGEST", "WRONG_ID", "DUPLICATE", "OVERSIZE"):
            with self.subTest(mode=mode):
                self.trace.unlink(missing_ok=True)
                completed = self.run_pipeline(mode)
                self.assertNotEqual(completed.returncode, 0)
                self.assert_stages(b"F")
                self.assertFalse(self.target.exists())

    def test_source_mutation_during_frontend_rejects_before_publication(self):
        completed = self.run_pipeline("SOURCE_CHANGED")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"source changed", completed.stderr)
        self.assert_stages(b"F")
        self.assertFalse(self.target.exists())

    def test_adapter_failure_does_not_claim_publication(self):
        completed = self.run_pipeline("ADAPTER_FAILURE")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"JSON-to-target adapter failed", completed.stderr)
        self.assert_stages(b"FA")
        self.assertFalse(self.target.exists())

    def test_adapter_success_without_artifact_is_not_a_success(self):
        completed = self.run_pipeline("ADAPTER_FALSE_SUCCESS")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"did not publish", completed.stderr)
        self.assert_stages(b"FA")
        self.assertFalse(self.target.exists())

    def test_existing_output_is_not_overwritten_or_compiled(self):
        _ = self.target.write_bytes(b"existing")
        completed = self.run_pipeline()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"already exists", completed.stderr)
        self.assert_stages(b"")
        self.assertEqual(self.target.read_bytes(), b"existing")

    def test_repository_default_source_id_accepts_portable_basenames_and_encodes_others(
        self,
    ) -> None:
        # A physical filename is not the logical Clang source identity. The
        # default must stay portable without changing the selected source bytes.
        module = runpy.run_path(str(DRIVER), run_name="malbolge_driver_test")
        default_source_id = cast(Callable[[str], str], module["default_source_id"])
        self.assertEqual(default_source_id("folder/ordinary-name.c"), "ordinary-name.c")
        self.assertEqual(default_source_id("other/ordinary-name.c"), "ordinary-name.c")
        for basename in ("source with spaces.c", "caf\u00e9.c", "a:b.c"):
            with self.subTest(basename=basename):
                expected = (
                    f"source-{hashlib.sha256(os.fsencode(basename)).hexdigest()}.c"
                )
                self.assertEqual(default_source_id(f"folder/{basename}"), expected)
                self.assertTrue(
                    all(
                        byte in "abcdefghijklmnopqrstuvwxyz0123456789-."
                        for byte in expected
                    )
                )
                self.assertEqual(default_source_id(f"other/{basename}"), expected)

    def test_invalid_portable_source_id_prevents_all_stages(self):
        for source_id in ("/absolute.c", "../bad.c", "a//b.c", "a\\b.c"):
            with self.subTest(source_id=source_id):
                completed = self.run_pipeline(source_id=source_id)
                self.assertNotEqual(completed.returncode, 0)
                self.assert_stages(b"")
                self.assertFalse(self.target.exists())

    @unittest.skipUnless(
        hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"), "POSIX only"
    )
    def test_named_pipe_source_is_rejected_without_blocking(self):
        self.source.unlink()
        os.mkfifo(self.source)
        completed = self.run_pipeline()
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"regular file", completed.stderr)
        self.assert_stages(b"")


if __name__ == "__main__":
    _ = unittest.main()
