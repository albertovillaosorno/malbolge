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

import os
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import time
from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Never

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
RSS_MEASUREMENT_TOOL = "time"
RSS_REPORT_MAX_BYTES = 32
SYSTEM_TOOL_SEARCH_PATH = os.defpath
KIB_BYTES = 1024
OPTIMIZATION_MODES = ("-O0", "-O2")
REQUIRED_CASE_FIELDS = frozenset({"family", "version", "seed", "difficulty"})
_ROOT = Path(__file__).resolve().parents[2]
_PINNED_CLANG = _ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
_TEMP = _ROOT / ".temp"


@dataclass(frozen=True, slots=True)
class ReferenceMeasurement:
    """One measured canonical host-C compile/link/oracle execution."""

    elapsed_ns: int
    executable: bytes
    peak_rss_bytes: int


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
        "schema_version": 2,
        "platform": LINUX_PLATFORM,
        "limiter": RESOURCE_LIMIT_TOOL,
        "scope": "per-child-inherited-not-aggregate",
        "virtual_address_space_bytes": CHILD_VIRTUAL_MEMORY_MIB * MIB_BYTES,
        "cpu_seconds": CHILD_CPU_SECONDS,
        "output_file_bytes": CHILD_FILE_BYTES,
        "wall_timeout_seconds": SUBPROCESS_TIMEOUT_SECONDS,
        "cleanup": "new-session-best-effort-original-process-group",
        "rss_measurement": "gnu-time-per-stage-max-ru_maxrss-kib",
        "rss_tool": RSS_MEASUREMENT_TOOL,
    }


def _system_tool(name: str) -> str | None:
    """Resolve OS-provided child tools without a caller-controlled PATH."""
    return shutil.which(name, path=SYSTEM_TOOL_SEARCH_PATH)


def _limited_command(command: list[str]) -> list[str]:
    if sys.platform != LINUX_PLATFORM:
        _fail("host-C child resource controls require Linux")
    utility = _system_tool(RESOURCE_LIMIT_TOOL)
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
    """Refuse new studies unless the limiter and RSS measurer are present."""
    _ = _limited_command([])
    if _system_tool(RSS_MEASUREMENT_TOOL) is None:
        _fail("host-C child RSS measurement requires GNU time")


def _kill_child_group(child: sp.Popen[bytes]) -> None:

    # Linux negative PID targets the child's separate session/process group.
    with suppress(ProcessLookupError):
        os.kill(-child.pid, GROUP_TERMINATION_SIGNAL)


def _ascii_digits(value: bytes) -> bool:
    return value.isascii() and value.isdigit()


def _read_stage_rss(path: Path) -> int:
    from benchmarks.arena import evidence  # ruff: ignore[import-outside-top-level]

    try:
        raw = evidence.read_bounded_regular(
            path.parent, path.name, limit=RSS_REPORT_MAX_BYTES
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        evidence.EvidenceError,
    ) as error:
        message = "host-C child RSS observation missing or unsafe"
        raise HostOracleError(message) from error
    if not raw.endswith(b"\n") or not _ascii_digits(raw[:-1]):
        _fail("host-C child RSS observation missing or malformed")
    peak_kib = int(raw[:-1])
    if not 0 < peak_kib <= CHILD_VIRTUAL_MEMORY_MIB * MIB_BYTES // KIB_BYTES:
        _fail("host-C child RSS observation outside child limits")
    return peak_kib * KIB_BYTES


def _finish_child(child: sp.Popen[bytes]) -> None:
    failures: list[Exception] = []
    try:
        _kill_child_group(child)
    except OSError as error:
        failures.append(error)
        # A group-signal failure must not skip the direct-child fallback.
        try:
            if child.poll() is None:
                child.kill()
        except OSError as direct_error:
            failures.append(direct_error)
    try:
        _ = child.wait(timeout=1)
    except sp.TimeoutExpired:
        # The original group may have become unavailable while its direct
        # child is still alive; retry one bounded direct kill and reap.
        try:
            child.kill()
            _ = child.wait(timeout=1)
        except (OSError, sp.SubprocessError) as error:
            failures.append(error)
    except (OSError, ValueError) as error:
        failures.append(error)
    if failures:
        message = "host-C challenge oracle child cleanup failed"
        failure = HostOracleError(message)
        for error in failures[1:]:
            failure.add_note(f"additional host-C cleanup failure: {error}")
        raise failure from failures[0]


def _wait_child(child: sp.Popen[bytes], label: str) -> None:
    try:
        try:
            _ = child.communicate(timeout=SUBPROCESS_TIMEOUT_SECONDS)
        except sp.TimeoutExpired as error:
            message = f"host-C challenge oracle {label} timed out"
            raise HostOracleError(message) from error
        except (OSError, ValueError, RuntimeError, sp.SubprocessError) as error:
            message = f"host-C challenge oracle {label} transport failed"
            raise HostOracleError(message) from error
    finally:
        original = sys.exception()
        try:
            _finish_child(child)
        except HostOracleError as error:
            if original is None:
                raise
            original.add_note(f"host-C cleanup also failed: {error}")
    if child.returncode != 0:
        _fail(f"host-C challenge oracle {label} failed")


def _bounded_child(command: list[str], cwd: Path, label: str) -> int:
    limited = _limited_command(command)
    time_tool = _system_tool(RSS_MEASUREMENT_TOOL)
    if time_tool is None:
        _fail("host-C child RSS measurement requires GNU time")
    try:
        fd, output_path = tempfile.mkstemp(
            dir=cwd,
            prefix="host-c-stage-rss-",
            suffix=".txt",
        )
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        message = "host-C challenge oracle RSS temporary receipt unavailable"
        raise HostOracleError(message) from error
    try:
        try:
            os.close(fd)
        except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
            message = "host-C challenge oracle RSS descriptor close failed"
            raise HostOracleError(message) from error
        try:
            child = sp.Popen(  # ruff: ignore[subprocess-without-shell-equals-true]
                [
                    time_tool,
                    "--format=%M",
                    "--output",
                    output_path,
                    "--",
                    *limited,
                ],
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
        _wait_child(child, label)
        return _read_stage_rss(Path(output_path))
    finally:
        primary = sys.exception()
        try:
            Path(output_path).unlink(missing_ok=True)
        except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
            if primary is not None:
                primary.add_note(f"host-C RSS receipt cleanup also failed: {error}")
            else:
                message = "host-C challenge oracle RSS receipt cleanup failed"
                raise HostOracleError(message) from error


def _run(command: list[str], cwd: Path, label: str) -> int:
    """Execute one limited host stage and return its kernel peak RSS bytes.

    Returns:
        GNU time ru_maxrss converted from Linux KiB to bytes.

    """
    return _bounded_child(command, cwd, label)


def _replay_mode(directory: Path, mode: str) -> int:
    source = directory / "program.c"
    harness = directory / "oracle-harness.c"
    obj = directory / "challenge.o"
    binary = directory / "oracle-check"
    compile_rss = _run(
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
    link_rss = _run(
        [str(_PINNED_CLANG), str(obj), str(harness), "-o", str(binary)],
        directory,
        f"{mode} link",
    )
    execute_rss = _run([str(binary)], directory, f"{mode} execute")
    return max(compile_rss, link_rss, execute_rss)


def _bounded_nodes(nodes: object, *, limit: int, scope: str) -> None:
    if type(nodes) is not int or nodes < 1:
        _fail(f"host-C {scope} identity requires positive integer nodes")
    if nodes > limit:
        _fail(f"host-C {scope} exceeds {limit}-node limit")


def _canonical_payload(
    case: dict[str, Any],
    profile: str,
    source_sha256: str,
) -> generate.GeneratedChallenge:
    if type(case) is not dict or not REQUIRED_CASE_FIELDS.issubset(case):
        _fail("host-C challenge oracle identity requires complete case fields")
    if type(case["family"]) is not str:
        _fail("host-C challenge oracle identity requires a string family")
    _bounded_nodes(
        case["difficulty"], limit=MAX_REPLAY_NODES, scope="challenge oracle"
    )
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
    if type(identity) is not generate.ChallengeIdentity:
        _fail("host-C reference identity requires canonical challenge fields")
    _bounded_nodes(identity.nodes, limit=MAX_REPLAY_NODES, scope="reference")
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


def _read_reference_executable(directory: Path) -> bytes:
    """Admit a bounded, stable physical executable from a completed host stage.

    Returns:
        Exact bytes of the independently checked compiler output.

    """
    from benchmarks.arena import evidence  # ruff: ignore[import-outside-top-level]

    try:
        return evidence.read_bounded_regular(
            directory, "oracle-check", limit=CHILD_FILE_BYTES
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        evidence.EvidenceError,
    ) as error:
        message = "host-C reference executable missing or unsafe"
        raise HostOracleError(message) from error


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
        return _read_reference_executable(directory)


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
        peak_rss = _replay_mode(directory, mode)
        elapsed = time.perf_counter_ns() - started
        artifact = _read_reference_executable(directory)
    return ReferenceMeasurement(
        elapsed_ns=elapsed,
        executable=artifact,
        peak_rss_bytes=peak_rss,
    )
