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
#   - Source-stable and atomic no-clobber publication by the C compiler driver.
# - Must-Not:
#   - Treat executable stubs as C or Malbolge semantic acceptance.
# - Allows:
#   - Inputs: controlled process stubs and temporary source/output files.
#   - Outputs: publication/rollback and concurrent-target assertions.
#   - Side effects: isolated temporary fixture files only.
# - Split-When:
#   - A real native-frontend acceptance suite subsumes these process checks.
# - Merge-When:
#   - Compiler publication has one independently tested implementation.
# - Summary:
#   - A changed source or newly occupied target must not expose guest output.
# - Description:
#   - The trusted adapter writes a private stage before the driver publishes.
# - Usage:
#   - python3.14 -B -m unittest tests/test_c2malbolge_source_publication.py -v
# - Defaults:
#   - Source and output are scoped to one isolated invocation.

"""Process-level source-stable guest publication regression checks."""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import final, override

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"

FRONTEND = textwrap.dedent("""\
    #!/usr/bin/env python3
    import hashlib
    import json
    from pathlib import Path
    import sys

    source = Path(sys.argv[-1]).read_bytes()
    print(json.dumps({
        'source': {
            'id': sys.argv[sys.argv.index('--source-id') + 1],
            'sha256': hashlib.sha256(source).hexdigest(),
        }
    }))
    """)

ADAPTER = textwrap.dedent("""\
    #!/usr/bin/env python3
    import os
    from pathlib import Path
    import sys

    _ = sys.stdin.buffer.read()
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    source = Path(os.environ['COMPILER_TEST_SOURCE'])
    target = Path(os.environ['COMPILER_TEST_TARGET'])
    mode = os.environ.get('COMPILER_TEST_MODE')
    if mode == 'mutate-source':
        source.write_bytes(b'void noop(void) { ; }\\n')
    if mode == 'occupy-target':
        target.write_bytes(b'concurrent-target')
    if mode == 'symlink-stage':
        output.symlink_to(source)
    else:
        output.write_bytes(b'verified-guest')
    if mode == 'failed-after-write':
        sys.exit(4)
    """)


@final
class SourceBoundPublicationTests(unittest.TestCase):
    @override
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.directory = Path()
        self.source = Path()
        self.target = Path()
        self.frontend = Path()
        self.adapter = Path()

    @override
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / ".temp")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source = self.directory / "input.c"
        _ = self.source.write_bytes(b"void noop(void) { return; }\n")
        self.target = self.directory / "output.malbolge"
        self.frontend = self.directory / "frontend"
        self.adapter = self.directory / "adapter"
        for path, content in ((self.frontend, FRONTEND), (self.adapter, ADAPTER)):
            _ = path.write_text(content, encoding="utf-8")
            path.chmod(0o700)

    def run_driver(
        self, mode: str = "", *, fail_sync: str = ""
    ) -> subprocess.CompletedProcess[bytes]:
        environment = os.environ.copy()
        environment.update(
            {
                "COMPILER_TEST_SOURCE": str(self.source),
                "COMPILER_TEST_TARGET": str(self.target),
                "COMPILER_TEST_MODE": mode,
            }
        )
        command = [sys.executable, "-B"]
        if fail_sync:
            # Inject failure in the real driver process, not in stub children.
            command.extend(
                [
                    "-c",
                    textwrap.dedent("""\
                        import os
                        import runpy
                        import stat
                        import sys

                        real_fsync = os.fsync
                        failed_kind = sys.argv[1]

                        def failed_sync(descriptor):
                            is_directory = stat.S_ISDIR(os.fstat(descriptor).st_mode)
                            if failed_kind == "mutate-source":
                                if not is_directory:
                                    with open(os.environ["COMPILER_TEST_SOURCE"], "wb") as source:
                                        source.write(b"source mutated during stage sync")
                            elif is_directory == (failed_kind == "directory"):
                                raise OSError("injected sync failure")
                            real_fsync(descriptor)

                        os.fsync = failed_sync
                        sys.argv = sys.argv[2:]
                        runpy.run_path(sys.argv[0], run_name="__main__")
                        """),
                    fail_sync,
                ]
            )
        command.extend(
            [
                str(DRIVER),
                "--frontend",
                str(self.frontend),
                "--json-adapter",
                str(self.adapter),
                "--layout-backend",
                str(self.directory / "layout"),
                "--guest-include",
                str(self.directory),
                "--resource-dir",
                str(self.directory),
                "--source-id",
                "fixtures/noop.c",
                "--output",
                str(self.target),
                str(self.source),
            ]
        )
        return subprocess.run(
            command,
            env=environment,
            capture_output=True,
            check=False,
            timeout=15,
        )

    def assert_no_staging_leftovers(self) -> None:
        self.assertEqual(list(self.directory.glob(".c2malbolge-*")), [])

    def test_stable_source_publishes_guest_without_staging_leftovers(self) -> None:
        completed = self.run_driver()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.target.read_bytes(), b"verified-guest")
        self.assert_no_staging_leftovers()

    def test_staged_file_sync_failure_does_not_publish_target(self) -> None:
        completed = self.run_driver(fail_sync="file")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"cannot sync staged guest artifact", completed.stderr)
        self.assertIn(b"injected sync failure", completed.stderr)
        self.assertFalse(self.target.exists())
        self.assert_no_staging_leftovers()

    def test_source_changed_during_stage_sync_rejects_before_link(self) -> None:
        completed = self.run_driver(fail_sync="mutate-source")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"source changed during guest compilation", completed.stderr)
        self.assertFalse(self.target.exists())
        self.assert_no_staging_leftovers()

    @unittest.skipUnless(os.name == "posix", "directory sync is Unix-only")
    def test_final_link_sync_failure_reports_error_without_unlinking_target(
        self,
    ) -> None:
        completed = self.run_driver(fail_sync="directory")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"cannot sync published output directory", completed.stderr)
        self.assertIn(b"injected sync failure", completed.stderr)
        # The already-created link must not be deleted after a sync failure.
        self.assertEqual(self.target.read_bytes(), b"verified-guest")
        self.assert_no_staging_leftovers()

    def test_source_changed_during_adapter_rejects_without_publication(self) -> None:
        completed = self.run_driver("mutate-source")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"source changed", completed.stderr)
        self.assertFalse(self.target.exists())
        self.assert_no_staging_leftovers()

    def test_adapter_error_after_writing_leaves_no_output(self) -> None:
        completed = self.run_driver("failed-after-write")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"adapter failed", completed.stderr)
        self.assertFalse(self.target.exists())
        self.assert_no_staging_leftovers()

    def test_output_created_during_adapter_cannot_be_overwritten(self) -> None:
        completed = self.run_driver("occupy-target")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"no-clobber", completed.stderr)
        self.assertEqual(self.target.read_bytes(), b"concurrent-target")
        self.assert_no_staging_leftovers()

    def test_adapter_symlink_does_not_publish_or_modify_source(self) -> None:
        original = self.source.read_bytes()
        completed = self.run_driver("symlink-stage")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(b"regular Malbolge target", completed.stderr)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.source.read_bytes(), original)
        self.assert_no_staging_leftovers()


if __name__ == "__main__":
    _ = unittest.main()
