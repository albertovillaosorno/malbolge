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
#   - Seeded binary first/second-read independence for real guest EOF control.
# - Must-Not:
#   - Select guest branches on the host or accept host output as guest output.
# - Allows:
#   - Inputs: pinned C23 source, native oracle and finite binary streams.
#   - Outputs: exact native/guest stdout and normative guest step counts.
#   - Side effects: bounded temporary compiler and VM children only.
# - Split-When:
#   - General EOF loops and stateful C guest parity subsume this finite proof.
# - Merge-When:
#   - The source-backed branch publication gate grows a shared matrix runner.
# - Summary:
#   - Cross-check both input positions and ignored suffixes in real VM runs.

"""Independent seeded guest/native evidence for the published two-read C23 branch."""

from __future__ import annotations

import hashlib
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final, final

from tests.test_two_read_eof_branch_publication import (
    CLANG,
    DRIVER,
    SOURCE,
    SOURCE_SHA,
    VM,
    environment,
)

ROOT: Final = Path(__file__).resolve().parents[1]
BOUNDARIES: Final = (0x00, 0x01, 0x02, 0x7F, 0x80, 0xFE, 0xFF)
SEED: Final = 0x5EEDC23
GUEST_MAX_STEPS: Final = 500


def input_matrix() -> tuple[bytes, ...]:
    """Freeze each semantic boundary before launching compiler or VM children."""
    vectors = [b""]
    vectors.extend(bytes((first,)) for first in BOUNDARIES)
    # The same second word must not depend on the first byte's numeric value.
    vectors.extend(bytes((first, 0)) for first in BOUNDARIES)
    # Vary the second word while its first-word register history is held fixed.
    vectors.extend(bytes((0x55, second)) for second in BOUNDARIES)
    randomizer = random.Random(SEED)
    seen = set(vectors)
    while len(vectors) < 46:
        first = randomizer.randrange(256)
        second = randomizer.randrange(256)
        suffix = (randomizer.randrange(256),) if len(vectors) % 2 else ()
        candidate = bytes((first, second, *suffix))
        if candidate not in seen:
            seen.add(candidate)
            vectors.append(candidate)
    return tuple(vectors)


def independent_c23_oracle(data: bytes) -> tuple[bytes, int]:
    """Derive C23 behavior without executing or trusting compiler output."""
    first = data[0] if data else 106
    if len(data) < 2:
        return bytes((first, 30)), 119
    return bytes((first, 154)), 175


@final
class TwoReadEofBranchMatrixTests(unittest.TestCase):
    def test_seeded_native_c23_and_normative_guest_matrix(self) -> None:
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SOURCE_SHA)
        vectors = input_matrix()
        self.assertEqual(len(vectors), 46)
        self.assertEqual(len(set(vectors)), len(vectors))
        self.assertEqual(independent_c23_oracle(b""), (b"\x6a\x1e", 119))
        self.assertEqual(independent_c23_oracle(b"\xff\x00\x80"), (b"\xff\x9a", 175))

        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            temp = Path(directory)
            wrapper = temp / "main.c"
            wrapper.write_text(
                f'#include "{SOURCE}"\nint main(void) {{ emit(); return 0; }}\n',
                encoding="utf-8",
            )
            for optimization in ("-O0", "-O2"):
                native = temp / f"native-{optimization[2:]}"
                compiled = subprocess.run(
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
                    capture_output=True,
                    env=environment(),
                    check=False,
                    timeout=20,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                for index, data in enumerate(vectors):
                    with self.subTest(
                        native=optimization, case=index, stdin=data.hex()
                    ):
                        ran = subprocess.run(
                            [str(native)],
                            input=data,
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(ran.returncode, 0, ran.stderr)
                        self.assertEqual(ran.stdout, independent_c23_oracle(data)[0])

            guest_path = temp / "two-read-branch.malbolge"
            compiled = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--capsule",
                    "--max-wall-seconds",
                    "80",
                    "--output",
                    str(guest_path),
                    str(SOURCE),
                ],
                capture_output=True,
                env=environment(),
                check=False,
                timeout=90,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(guest_path.is_file())
            # Each guest process initializes the full N15 memory. Keep a
            # bounded subset with both EOF arms, edge bytes, cross-position
            # independence and seeded unread suffixes; native C covers all 46.
            guest_cases = (0, 1, 7, 8, 14, 15, 18, 21, 23, 28, 37, 45)
            self.assertEqual(len(guest_cases), 12)
            for index in guest_cases:
                data = vectors[index]
                with self.subTest(guest=index, stdin=data.hex()):
                    expected, steps = independent_c23_oracle(data)
                    ran = subprocess.run(
                        [
                            str(VM),
                            str(guest_path),
                            "--input-stdin",
                            "--max-steps",
                            str(GUEST_MAX_STEPS),
                            "--report-steps",
                        ],
                        input=data,
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(ran.returncode, 0, ran.stderr)
                    self.assertEqual(ran.stdout, expected)
                    self.assertIn(f"malbolge-steps-v1:{steps}".encode(), ran.stderr)


if __name__ == "__main__":
    unittest.main()
