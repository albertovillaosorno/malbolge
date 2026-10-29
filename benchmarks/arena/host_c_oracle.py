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
#   - Bounded host-C execution replay of canonical challenge oracles.
# - Must-Not:
#   - Certify a compiler candidate or claim host C equals Malbolge semantics.
# - Allows:
#   - Inputs: previously validated challenge identity and canonical digest.
#   - Outputs: source SHA-256 after native replay checks both compiler modes.
#   - Side effects: bounded native compiler/runner subprocesses and temp files.
# - Split-When:
#   - Candidate artifact execution receives a separate verifier contract.
# - Merge-When:
#   - The governed challenge oracle verifier owns host replay directly.
# - Summary:
#   - Cross-checks generator oracle against independent compiled C execution.
# - Description:
#   - Pinned Clang O0/O2 checks C entry against canonical four-byte oracle.
# - Usage:
#   - Opt-in arena evidence --require-host-c-challenge-oracle.
# - Defaults:
#   - Unavailable toolchain, timeout, mismatch, or over-limit case rejects.
#

"""Host-C check of the canonical challenge generator result."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import tempfile
from typing import Any
from typing import Never

from benchmarks.challenges import generate

MAX_REPLAY_CASES = 16
MAX_REPLAY_NODES = 512
ORACLE_BYTES = 4
SUBPROCESS_TIMEOUT_SECONDS = 15
OPTIMIZATION_MODES = ("-O0", "-O2")
_ROOT = Path(__file__).resolve().parents[2]
_PINNED_CLANG = _ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
_TEMP = _ROOT / ".temp"


class HostOracleError(ValueError):
    """Host-C execution failed to reproduce a canonical challenge oracle."""


def _fail(message: str) -> Never:
    raise HostOracleError(message)


def _harness(oracle: bytes) -> bytes:
    expected = int.from_bytes(oracle, "little")
    return (
        "#include <stdint.h>\n"
        "uint32_t malbolge_challenge(void);\n"
        "int main(void) {\n"
        "    return malbolge_challenge() == "
        f"UINT32_C({expected}) ? 0 : 1;\n"
        "}\n"
    ).encode("ascii")


def _run(command: list[str], cwd: Path, label: str) -> None:
    try:
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            command,
            cwd=cwd,
            check=False,
            shell=False,
            stdin=sp.DEVNULL,
            stdout=sp.DEVNULL,
            stderr=sp.PIPE,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
    except (OSError, sp.TimeoutExpired) as error:
        message = f"host-C challenge oracle {label} did not complete"
        raise HostOracleError(message) from error
    if completed.returncode != 0:
        _fail(f"host-C challenge oracle {label} failed")


def _replay_mode(directory: Path, mode: str) -> None:
    source = directory / "program.c"
    harness = directory / "oracle-harness.c"
    obj = directory / "challenge.o"
    binary = directory / "oracle-check"
    _run(
        [
            str(_PINNED_CLANG),
            "-std=c23",
            "-Wall",
            "-Wextra",
            "-Werror",
            mode,
            "-Dmain=malbolge_generated_main",
            "-c",
            str(source),
            "-o",
            str(obj),
        ],
        directory,
        f"{mode} compile",
    )
    _run(
        [str(_PINNED_CLANG), str(obj), str(harness), "-o", str(binary)],
        directory,
        f"{mode} link",
    )
    _run([str(binary)], directory, f"{mode} execute")


def _canonical_payload(
    case: dict[str, Any],
    profile: str,
    source_sha256: str,
) -> generate.GeneratedChallenge:
    if case["difficulty"] > MAX_REPLAY_NODES:
        _fail("host-C challenge oracle exceeds 512-node limit")
    try:
        generated = generate.generate(
            generate.ChallengeIdentity(
                family=case["family"],
                version=case["version"],
                seed=case["seed"],
                profile=profile,
                nodes=case["difficulty"],
            )
        )
    except generate.ChallengeError as error:
        message = f"host-C challenge identity cannot regenerate: {error}"
        raise HostOracleError(message) from error
    digest = sha256(generated.source).hexdigest()
    if digest != source_sha256 or len(generated.oracle) != ORACLE_BYTES:
        _fail("host-C challenge oracle source or output identity differs")
    return generated


def replay_one(
    case: dict[str, Any],
    profile: str,
    source_sha256: str,
) -> str:
    """Replay generated C entry result against the generator oracle.

    The caller must first admit retained bundle bytes through the canonical
    challenge generator and ensure the supplied source digest was checked.
    Re-generating here prevents an unreviewed candidate source from executing.

    Returns:
        Canonical source hash checked by both native optimization modes.

    """
    if not _PINNED_CLANG.is_file() or not _TEMP.is_dir():
        _fail("pinned host-C compiler or local temporary directory unavailable")
    generated = _canonical_payload(case, profile, source_sha256)
    with tempfile.TemporaryDirectory(
        prefix="arena-host-c-oracle-",
        dir=_TEMP,
    ) as temporary:
        directory = Path(temporary)
        _ = (directory / "program.c").write_bytes(generated.source)
        _ = (directory / "oracle-harness.c").write_bytes(
            _harness(generated.oracle)
        )
        for mode in OPTIMIZATION_MODES:
            _replay_mode(directory, mode)
    return source_sha256
