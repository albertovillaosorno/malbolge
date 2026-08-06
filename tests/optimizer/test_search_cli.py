# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Tests for the reproducible search command-line runner.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Tests for the reproducible search command-line runner."""

from __future__ import annotations

from contextlib import redirect_stderr
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from typing import TYPE_CHECKING
from typing import cast
from unittest import SkipTest

from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.search_config import parse_search_configuration
from optimizer.cli import CONFIGURATION_ERROR
from optimizer.cli import PROPOSAL_TRUST
from optimizer.cli import SearchRunOptions
from optimizer.cli import main
from optimizer.cli import run_configured_search
from optimizer.cli import search_record_json
from optimizer.crazy_target import CRAZY_TARGET_ALGORITHM_ID
from optimizer.crazy_target import CrazyTargetProblem
from optimizer.enumerative import ENUMERATIVE_ALGORITHM_ID
from optimizer.enumerative import EnumerationProblem
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem

if TYPE_CHECKING:
    from pathlib import Path

    from accelerator.cuda import CudaExactPrimitiveAdapter as CudaAdapter
    from accelerator.search_config import SearchConfiguration

CPU_BACKEND = "cpu-reference"
CUDA_BACKEND = "cuda"
ROTATE_ONE = 19_683
CRAZY_ALL_ONES = 29_524
CONFIG_SOURCE = "config/search.toml"
BASE_SOURCE = "base.toml"
UNSUPPORTED_PAIR = "unsupported search algorithm/backend"
INVALID_INTEGER = "invalid int value"
TWO_PROPOSALS = 2
CRAZY_PROPOSALS = 4


def _configuration(
    algorithm: str,
    backend: str,
    *,
    source: str = "search.toml",
) -> SearchConfiguration:
    return parse_search_configuration(
        f"""schema_version = 1

[search]
algorithm_id = "{algorithm}"
backend_id = "{backend}"
""",
        source=source,
    )


def _unavailable_cuda() -> CudaAdapter:
    message = "synthetic CUDA unavailable"
    raise AcceleratorUnavailableError(message)


def _live_cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _json_object(text: str) -> dict[str, object]:
    parsed = cast("object", json.loads(text))
    if not isinstance(parsed, dict):
        raise TypeError
    return cast("dict[str, object]", parsed)


def _json_list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError
    return cast("list[object]", value)


def _expect_value_error(message: str, action: object) -> None:
    if not callable(action):
        raise TypeError
    try:
        _ = action()
    except ValueError as error:
        if message not in str(error):
            raise TypeError from error
        return
    raise TypeError


def test_cpu_enumeration_output_records_reproducible_identity() -> None:
    """CPU evidence records config source, problem hash, and trust boundary."""
    configuration = _configuration(
        ENUMERATIVE_ALGORITHM_ID,
        CPU_BACKEND,
        source=CONFIG_SOURCE,
    )
    problem = EnumerationProblem(candidates=(b"alpha", b"beta")).encode()

    record = run_configured_search(
        configuration,
        problem,
        SearchRunOptions(evaluation_budget=1, seed=1),
    )
    payload = _json_object(search_record_json(configuration, problem, record))

    assert payload["schema_version"] == 1
    assert payload["configuration_source"] == CONFIG_SOURCE
    assert payload["algorithm_id"] == ENUMERATIVE_ALGORITHM_ID
    assert payload["configured_backend_id"] == CPU_BACKEND
    assert payload["actual_backend_id"] == CPU_BACKEND
    assert payload["problem_sha256"] == sha256(problem).hexdigest()
    assert payload["proposal_trust"] == PROPOSAL_TRUST
    assert payload["proposals"] == [
        {"logical_id": "corpus-1", "payload_hex": b"beta".hex()}
    ]


def test_explicit_overrides_select_another_registered_cpu_algorithm() -> None:
    """Overrides replace selection without changing configuration provenance."""
    configuration = _configuration(
        ENUMERATIVE_ALGORITHM_ID,
        CUDA_BACKEND,
        source=BASE_SOURCE,
    )
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(0, 1, 2),
    ).encode()

    record = run_configured_search(
        configuration,
        problem,
        SearchRunOptions(
            algorithm_override=ROTATE_TARGET_ALGORITHM_ID,
            backend_override=CPU_BACKEND,
            evaluation_budget=3,
        ),
    )
    payload = _json_object(search_record_json(configuration, problem, record))

    assert payload["configuration_source"] == BASE_SOURCE
    assert payload["algorithm_id"] == ROTATE_TARGET_ALGORITHM_ID
    assert payload["configured_backend_id"] == CPU_BACKEND
    assert payload["actual_backend_id"] == CPU_BACKEND


def test_cpu_crazy_target_route_is_registered() -> None:
    """CLI registry exposes exact multiposition crazy search on CPU."""
    configuration = _configuration(CRAZY_TARGET_ALGORITHM_ID, CPU_BACKEND)
    problem = CrazyTargetProblem(
        accumulator=0,
        target=CRAZY_ALL_ONES,
        candidates=(0, 1, 2, 3, 4),
    ).encode()

    record = run_configured_search(
        configuration,
        problem,
        SearchRunOptions(evaluation_budget=5),
    )

    assert record.identity.actual_backend_id == CPU_BACKEND
    assert tuple(item.logical_id for item in record.result.proposals) == (
        "corpus-0",
        "corpus-1",
        "corpus-3",
        "corpus-4",
    )


def test_unavailable_cuda_preserves_configured_identity_and_falls_back() -> (
    None
):
    """CUDA setup failure changes actual capacity, not configured intent."""
    configuration = _configuration(ROTATE_TARGET_ALGORITHM_ID, CUDA_BACKEND)
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(0, 1, 2),
    ).encode()

    record = run_configured_search(
        configuration,
        problem,
        SearchRunOptions(evaluation_budget=3),
        cuda_factory=_unavailable_cuda,
    )

    assert record.identity.configured_backend_id == CUDA_BACKEND
    assert record.identity.actual_backend_id == CPU_BACKEND
    assert tuple(item.logical_id for item in record.result.proposals) == (
        "corpus-1",
    )


def test_unavailable_cuda_crazy_target_falls_back_to_cpu() -> None:
    """Crazy-target CUDA setup failure preserves exact CPU proposals."""
    configuration = _configuration(CRAZY_TARGET_ALGORITHM_ID, CUDA_BACKEND)
    problem = CrazyTargetProblem(
        accumulator=0,
        target=CRAZY_ALL_ONES,
        candidates=(0, 1, 2, 3, 4),
    ).encode()

    record = run_configured_search(
        configuration,
        problem,
        SearchRunOptions(evaluation_budget=5),
        cuda_factory=_unavailable_cuda,
    )

    assert record.identity.configured_backend_id == CUDA_BACKEND
    assert record.identity.actual_backend_id == CPU_BACKEND
    assert len(record.result.proposals) == CRAZY_PROPOSALS


def test_unsupported_algorithm_backend_pair_fails_explicitly() -> None:
    """No GPU binding is invented for an unsupported algorithm/backend pair."""
    configuration = _configuration(ENUMERATIVE_ALGORITHM_ID, CUDA_BACKEND)
    problem = EnumerationProblem(candidates=(b"one",)).encode()

    _expect_value_error(
        UNSUPPORTED_PAIR,
        lambda: run_configured_search(
            configuration,
            problem,
            SearchRunOptions(evaluation_budget=1),
            cuda_factory=_unavailable_cuda,
        ),
    )


def test_live_cuda_cli_route_records_actual_cuda_execution() -> None:
    """Live CLI route records CUDA for the rotate-target search strategy."""
    configuration = _configuration(ROTATE_TARGET_ALGORITHM_ID, CUDA_BACKEND)
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=tuple(range(257)),
    ).encode()
    with _live_cuda() as cuda:
        record = run_configured_search(
            configuration,
            problem,
            SearchRunOptions(evaluation_budget=257, seed=17),
            cuda_factory=lambda: cuda,
        )

    assert record.identity.configured_backend_id == CUDA_BACKEND
    assert record.identity.actual_backend_id == CUDA_BACKEND
    assert tuple(item.logical_id for item in record.result.proposals) == (
        "corpus-1",
    )


def test_live_cuda_cli_runs_crazy_target_strategy() -> None:
    """Live CLI registry records CUDA for exact crazy-target search."""
    configuration = _configuration(CRAZY_TARGET_ALGORITHM_ID, CUDA_BACKEND)
    problem = CrazyTargetProblem(
        accumulator=0,
        target=CRAZY_ALL_ONES,
        candidates=(0, 1, 2, 3, 4),
    ).encode()
    with _live_cuda() as cuda:
        record = run_configured_search(
            configuration,
            problem,
            SearchRunOptions(evaluation_budget=5),
            cuda_factory=lambda: cuda,
        )

    assert record.identity.configured_backend_id == CUDA_BACKEND
    assert record.identity.actual_backend_id == CUDA_BACKEND
    assert len(record.result.proposals) == CRAZY_PROPOSALS


def test_main_reads_files_and_emits_json(tmp_path: Path) -> None:
    """Module CLI reads durable config/problem files and emits JSON evidence."""
    config = tmp_path / "search.toml"
    problem = tmp_path / "problem.bin"
    _ = config.write_text(
        f"""schema_version = 1

[search]
algorithm_id = "{ENUMERATIVE_ALGORITHM_ID}"
backend_id = "{CPU_BACKEND}"
""",
        encoding="utf-8",
    )
    _ = problem.write_bytes(
        EnumerationProblem(candidates=(b"alpha", b"beta")).encode()
    )
    stdout = StringIO()
    stderr = StringIO()

    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = main((
            "--config",
            str(config),
            "--problem",
            str(problem),
            "--budget",
            "2",
            "--seed",
            "0",
        ))

    assert status == 0
    payload = _json_object(stdout.getvalue())
    assert payload["actual_backend_id"] == CPU_BACKEND
    assert len(_json_list(payload["proposals"])) == TWO_PROPOSALS
    assert not stderr.getvalue()


def test_main_reports_argument_errors_without_process_exit() -> None:
    """Malformed typed arguments return the documented configuration status."""
    stdout = StringIO()
    stderr = StringIO()

    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = main((
            "--config",
            "search.toml",
            "--problem",
            "problem.bin",
            "--budget",
            "not-an-integer",
        ))

    assert status == CONFIGURATION_ERROR
    assert INVALID_INTEGER in stderr.getvalue()
    assert not stdout.getvalue()


def test_main_reports_configuration_errors(tmp_path: Path) -> None:
    """Invalid algorithm/backend selection returns a stable nonzero status."""
    config = tmp_path / "search.toml"
    problem = tmp_path / "problem.bin"
    _ = config.write_text(
        f"""schema_version = 1

[search]
algorithm_id = "{ENUMERATIVE_ALGORITHM_ID}"
backend_id = "{CUDA_BACKEND}"
""",
        encoding="utf-8",
    )
    _ = problem.write_bytes(EnumerationProblem(candidates=(b"one",)).encode())
    stdout = StringIO()
    stderr = StringIO()

    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = main((
            "--config",
            str(config),
            "--problem",
            str(problem),
            "--budget",
            "1",
        ))

    assert status == CONFIGURATION_ERROR
    assert UNSUPPORTED_PAIR in stderr.getvalue()
    assert not stdout.getvalue()
