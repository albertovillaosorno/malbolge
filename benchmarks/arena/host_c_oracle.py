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

from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import time
from typing import Any
from typing import Never

from benchmarks.challenges import generate

MAX_REPLAY_CASES = 16
MAX_REPLAY_NODES = 512
ORACLE_BYTES = 4
SUBPROCESS_TIMEOUT_SECONDS = 15
CHILD_VIRTUAL_MEMORY_MIB = 1024
CHILD_CPU_SECONDS = 16
CHILD_FILE_BYTES = 8 * 1024 * 1024
MIB_BYTES = 1024 * 1024
GROUP_TERMINATION_SIGNAL = 9
LINUX_PLATFORM = "linux"
RESOURCE_LIMIT_TOOL = "prlimit"
OPTIMIZATION_MODES = ("-O0", "-O2")
_ROOT = Path(__file__).resolve().parents[2]
_PINNED_CLANG = _ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
_TEMP = _ROOT / ".temp"


@dataclass(frozen=True, slots=True)
class ReferenceMeasurement:
    """One measured canonical host-C compile/link/oracle execution."""

    elapsed_ns: int
    executable: bytes


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


def resource_controls_record() -> dict[str, str | int]:
    """Describe configured Linux child limits, not observed resource use.

    Returns:
        Stable version-one producer policy record for post-run audit.

    """
    return {
        "schema_version": 1,
        "platform": LINUX_PLATFORM,
        "limiter": RESOURCE_LIMIT_TOOL,
        "scope": "per-child-inherited-not-aggregate",
        "virtual_address_space_bytes": CHILD_VIRTUAL_MEMORY_MIB * MIB_BYTES,
        "cpu_seconds": CHILD_CPU_SECONDS,
        "output_file_bytes": CHILD_FILE_BYTES,
        "wall_timeout_seconds": SUBPROCESS_TIMEOUT_SECONDS,
        "cleanup": "new-session-best-effort-original-process-group",
    }


def _limited_command(command: list[str]) -> list[str]:
    if sys.platform != LINUX_PLATFORM:
        _fail("host-C child resource controls require Linux")
    utility = shutil.which(RESOURCE_LIMIT_TOOL)
    if utility is None:
        _fail("host-C child resource controls require util-linux prlimit")
    memory = CHILD_VIRTUAL_MEMORY_MIB * MIB_BYTES
    return [
        utility,
        f"--as={memory}:{memory}",
        f"--cpu={CHILD_CPU_SECONDS}:{CHILD_CPU_SECONDS}",
        f"--fsize={CHILD_FILE_BYTES}:{CHILD_FILE_BYTES}",
        "--",
        *command,
    ]


def require_child_resource_controls() -> None:
    """Refuse reference-study creation if the Linux limiter is absent."""
    _ = _limited_command([])


def _kill_child_group(child: sp.Popen[bytes]) -> None:

    # Linux negative PID targets the child's separate session/process group.
    with suppress(ProcessLookupError):
        os.kill(-child.pid, GROUP_TERMINATION_SIGNAL)


def _bounded_child(command: list[str], cwd: Path, label: str) -> None:
    limited = _limited_command(command)
    try:
        child = sp.Popen(  # ruff: ignore[subprocess-without-shell-equals-true]
            limited,
            cwd=cwd,
            shell=False,
            stdin=sp.DEVNULL,
            stdout=sp.DEVNULL,
            stderr=sp.DEVNULL,
            start_new_session=True,
        )
    except (OSError, sp.SubprocessError) as error:
        message = f"host-C challenge oracle {label} could not start"
        raise HostOracleError(message) from error
    try:
        try:
            _ = child.communicate(timeout=SUBPROCESS_TIMEOUT_SECONDS)
        except sp.TimeoutExpired as error:
            message = f"host-C challenge oracle {label} timed out"
            raise HostOracleError(message) from error
    finally:
        # A compiler wrapper may fork grandchildren that outlive the leader.
        # Best-effort group termination does not imply a cgroup-wide sandbox.
        _kill_child_group(child)
        _ = child.wait()
    if child.returncode != 0:
        _fail(f"host-C challenge oracle {label} failed")


def _run(command: list[str], cwd: Path, label: str) -> None:
    """Execute one bounded host-C stage with descendant cleanup."""
    _bounded_child(command, cwd, label)


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


def _reference_source(
    identity: generate.ChallengeIdentity,
    mode: str,
) -> generate.GeneratedChallenge:
    if mode not in OPTIMIZATION_MODES:
        _fail("unsupported host-C reference optimization mode")
    if identity.nodes > MAX_REPLAY_NODES:
        _fail("host-C reference exceeds 512-node limit")
    if not _PINNED_CLANG.is_file() or not _TEMP.is_dir():
        _fail("pinned host-C compiler or local temporary directory unavailable")
    try:
        return generate.generate(identity)
    except generate.ChallengeError as error:
        message = f"host-C reference identity cannot regenerate: {error}"
        raise HostOracleError(message) from error


def _write_canonical_source(
    directory: Path,
    generated: generate.GeneratedChallenge,
) -> None:
    _ = (directory / "program.c").write_bytes(generated.source)
    _ = (directory / "oracle-harness.c").write_bytes(_harness(generated.oracle))


def rebuild_reference(
    identity: generate.ChallengeIdentity,
    mode: str,
) -> bytes:
    """Independently build and execute the canonical host-C entry harness.

    No retained trial binary is executed, no old output path is read, and the
    original wall-clock cost cannot be reconstructed from a fresh compilation.

    Returns:
        The newly compiled native executable bytes for exact same-host review.

    """
    generated = _reference_source(identity, mode)
    with tempfile.TemporaryDirectory(
        prefix="arena-host-c-rebuild-",
        dir=_TEMP,
    ) as temporary:
        directory = Path(temporary)
        _write_canonical_source(directory, generated)
        _replay_mode(directory, mode)
        return (directory / "oracle-check").read_bytes()


def measure_reference(
    identity: generate.ChallengeIdentity,
    mode: str,
) -> ReferenceMeasurement:
    """Measure canonical host-C reference compilation through oracle replay.

    This is a measured HOST-C reference stage, not a Malbolge artifact or
    a certified external optimizer result. Wall time includes native compile,
    link, process startup and the independent return-value harness execution.

    Returns:
        Exact observed elapsed nanoseconds and successful executable bytes.

    """
    generated = _reference_source(identity, mode)
    with tempfile.TemporaryDirectory(
        prefix="arena-host-c-measure-",
        dir=_TEMP,
    ) as temporary:
        directory = Path(temporary)
        _write_canonical_source(directory, generated)
        started = time.perf_counter_ns()
        _replay_mode(directory, mode)
        elapsed = time.perf_counter_ns() - started
        artifact = (directory / "oracle-check").read_bytes()
    return ReferenceMeasurement(elapsed_ns=elapsed, executable=artifact)
