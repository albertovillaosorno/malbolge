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
from contextlib import suppress
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Never
from typing import TYPE_CHECKING
from typing import cast
from typing import override
from unittest import SkipTest

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import PrimitiveKind
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.resumable_search import resumable_evaluated_search_id
from accelerator.search_checkpoint import encode_search_checkpoint
from accelerator.search_checkpoint import search_checkpoint_codec_id
from accelerator.search_config import parse_search_configuration
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import SearchRequest
from optimizer.cli import CONFIGURATION_ERROR
from optimizer.cli import PROPOSAL_TRUST
from optimizer.cli import SearchRunOptions
from optimizer.cli import main
from optimizer.cli import run_configured_search
from optimizer.cli import search_record_json
from optimizer.crazy_target import CRAZY_TARGET_ALGORITHM_ID
from optimizer.crazy_target import CrazyTargetProblem
from optimizer.crazy_target import build_crazy_target_batch
from optimizer.enumerative import ENUMERATIVE_ALGORITHM_ID
from optimizer.enumerative import EnumerationProblem
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import build_rotate_target_batch
import pytest

from scripts import progress_sidecar as progress

if TYPE_CHECKING:
    from collections.abc import Iterator
    from accelerator.cuda import CudaExactPrimitiveAdapter as CudaAdapter
    from accelerator.search_config import SearchConfiguration

CPU_BACKEND = "cpu-reference"
CUDA_BACKEND = "cuda"
RESUME_CHECKPOINT_SHA_FIELD = "resume_checkpoint_sha256"
RESUME_EXECUTION_FIELD = "resume_execution_id"
ROTATE_ONE = 19_683
CRAZY_ALL_ONES = 29_524
CONFIG_SOURCE = "config/search.toml"
SOURCE_KIND_PROBLEM = "problem"
BYTE_LIMIT_ERROR = "byte limit"
REGULAR_SOURCE_ERROR = "regular"
SOURCE_CHANGED_ERROR = "changed before read"
SOURCE_CHANGED_DURING_ERROR = "changed during read"
SOURCE_RECHECK = 2
BASE_SOURCE = "base.toml"
UNSUPPORTED_PAIR = "unsupported search algorithm/backend"
INVALID_CHECKPOINT = "invalid search checkpoint JSON"
INVALID_INTEGER = "invalid int value"
UNSUPPORTED_RESUME = "unsupported resumable search algorithm"
TWO_PROPOSALS = 2
CRAZY_PROPOSALS = 4
ROTATE_ONE_PAYLOAD_HEX = (1).to_bytes(4, "little").hex()
REPOSITORY_REVISION = "a" * 40
PROFILE_HASH = "malbolge-profile-v1:sha256:" + ("3" * 64)
TOOLCHAIN_HASH = "sha256:" + ("2" * 64)
SEARCH_CHECKPOINT_CODEC = search_checkpoint_codec_id()


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


def _primitive_resume_checkpoint(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    kind: PrimitiveKind,
    *,
    completed: int,
) -> bytes:
    prefix_batch = CandidateEvaluationBatch(
        evaluator_id=batch.evaluator_id,
        items=tuple(batch.items[index] for index in range(completed)),
    ).validated()
    evaluator = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        kind,
    )
    result = evaluator.evaluate(prefix_batch)
    evidence = result.materialized_items_against(
        prefix_batch,
        evaluator.capability(),
    )
    return encode_search_checkpoint(request, batch, evidence)


def _rotate_resume_checkpoint(
    problem: RotateTargetProblem,
    *,
    budget: int,
    seed: int = 0,
    completed: int = 1,
) -> bytes:
    request = SearchRequest(
        algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
        evaluation_budget=budget,
        problem=problem.encode(),
        seed=seed,
    )
    batch = build_rotate_target_batch(request).validated()
    return _primitive_resume_checkpoint(
        request,
        batch,
        PrimitiveKind.ROTATE,
        completed=completed,
    )


def _crazy_resume_checkpoint(
    problem: CrazyTargetProblem,
    *,
    budget: int,
    seed: int = 0,
    completed: int = 1,
) -> bytes:
    request = SearchRequest(
        algorithm_id=CRAZY_TARGET_ALGORITHM_ID,
        evaluation_budget=budget,
        problem=problem.encode(),
        seed=seed,
    )
    batch = build_crazy_target_batch(request).validated()
    return _primitive_resume_checkpoint(
        request,
        batch,
        PrimitiveKind.CRAZY,
        completed=completed,
    )


def _published_progress_sidecar(
    tmp_path: Path,
    problem: bytes,
    checkpoint: bytes,
) -> Path:
    output = tmp_path / "program.malbolge"
    source_sha256 = "sha256:" + sha256(problem).hexdigest()
    identity = progress.ResumeIdentity(
        algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
        algorithm_version="1",
        repository_revision=REPOSITORY_REVISION,
        schema=progress.SCHEMA_ID,
        seed=0,
        source_sha256=source_sha256,
        target_profile_fingerprint=PROFILE_HASH,
        target_profile_id="malbolge-2026",
        toolchain_fingerprint=TOOLCHAIN_HASH,
    )
    position = progress.PortableCheckpointPosition(
        checkpoint_sequence=1,
        stage="candidate-search",
        units_completed=1,
    )
    envelope = progress.encode_portable_checkpoint(
        identity,
        position,
        SEARCH_CHECKPOINT_CODEC,
        payload=checkpoint,
    )
    sidecar = progress.ProgressSidecar(
        active_elapsed_ns=700,
        algorithm_id=identity.algorithm_id,
        algorithm_version=identity.algorithm_version,
        backend="cpu",
        checkpoint_elapsed_ns=30,
        checkpoint_path=str(progress.checkpoint_path(output, 1)),
        checkpoint_sequence=1,
        checkpoint_sha256="sha256:" + sha256(envelope).hexdigest(),
        compatibility_fingerprint=progress.resume_compatibility_fingerprint(
            identity
        ),
        completed_at=None,
        device=None,
        diagnostic_code=None,
        diagnostic_message=None,
        operation_id="search-resume-0001",
        output_path=str(output),
        partial_bytes=None,
        partial_path=None,
        partial_sha256=None,
        paused_elapsed_ns=100,
        progress_path=str(progress.progress_path(output)),
        repository_revision=identity.repository_revision,
        schema=identity.schema,
        seed=identity.seed,
        serialization_elapsed_ns=10,
        source_path=str(tmp_path / "problem.bin"),
        source_sha256=identity.source_sha256,
        stage=position.stage,
        started_at="2026-09-26T20:00:00Z",
        status=progress.ProgressStatus.CHECKPOINTED,
        target_profile_fingerprint=identity.target_profile_fingerprint,
        target_profile_id=identity.target_profile_id,
        toolchain_fingerprint=identity.toolchain_fingerprint,
        units_completed=position.units_completed,
        units_total=5,
        updated_at="2026-09-26T20:00:01Z",
        verification_elapsed_ns=30,
        wall_elapsed_ns=870,
    )
    return progress.write_checkpoint_generation(sidecar, envelope)


def _subprocess_environment(*paths: Path) -> dict[str, str]:
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    values = [str(path) for path in paths]
    if existing:
        values.append(existing)
    environment["PYTHONPATH"] = os.pathsep.join(values)
    return environment


def _resume_cli_inputs(
    tmp_path: Path,
) -> tuple[Path, Path, Path, bytes]:
    config = tmp_path / "search.toml"
    problem_path = tmp_path / "problem.bin"
    checkpoint_path = tmp_path / "search.checkpoint"
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(0, 1, 2, 1, 4),
    )
    checkpoint = _rotate_resume_checkpoint(problem, budget=5)
    config_text = (
        "schema_version = 1\n\n[search]\n"
        f'algorithm_id = "{ROTATE_TARGET_ALGORITHM_ID}"\n'
        f'backend_id = "{CPU_BACKEND}"\n'
    )
    _ = config.write_text(config_text, encoding="utf-8")
    _ = problem_path.write_bytes(problem.encode())
    _ = checkpoint_path.write_bytes(checkpoint)
    return config, problem_path, checkpoint_path, checkpoint


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
    assert RESUME_CHECKPOINT_SHA_FIELD not in payload
    assert RESUME_EXECUTION_FIELD not in payload
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


def test_cpu_rotate_resume_matches_fresh_search() -> None:
    """Programmatic checkpoint resume preserves ordinary CPU proposals."""
    configuration = _configuration(ROTATE_TARGET_ALGORITHM_ID, CPU_BACKEND)
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(0, 1, 2, 1, 4),
    )
    checkpoint = _rotate_resume_checkpoint(problem, budget=5)

    resumed = run_configured_search(
        configuration,
        problem.encode(),
        SearchRunOptions(
            evaluation_budget=5,
            resume_checkpoint=checkpoint,
        ),
    )
    fresh = run_configured_search(
        configuration,
        problem.encode(),
        SearchRunOptions(evaluation_budget=5),
    )

    assert resumed == fresh


def test_cpu_crazy_resume_matches_fresh_search() -> None:
    """Crazy checkpoint resume preserves ordinary CPU proposals."""
    configuration = _configuration(CRAZY_TARGET_ALGORITHM_ID, CPU_BACKEND)
    problem = CrazyTargetProblem(
        accumulator=0,
        target=CRAZY_ALL_ONES,
        candidates=(0, 1, 2, 3, 4, 1),
    )
    checkpoint = _crazy_resume_checkpoint(problem, budget=6)

    resumed = run_configured_search(
        configuration,
        problem.encode(),
        SearchRunOptions(
            evaluation_budget=6,
            resume_checkpoint=checkpoint,
        ),
    )
    fresh = run_configured_search(
        configuration,
        problem.encode(),
        SearchRunOptions(evaluation_budget=6),
    )

    assert resumed == fresh


def test_unavailable_cuda_resume_falls_back_to_cpu() -> None:
    """Unavailable CUDA keeps configured identity and resumes on CPU."""
    configuration = _configuration(ROTATE_TARGET_ALGORITHM_ID, CUDA_BACKEND)
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(0, 1, 2, 1, 4),
    )
    checkpoint = _rotate_resume_checkpoint(problem, budget=5)

    record = run_configured_search(
        configuration,
        problem.encode(),
        SearchRunOptions(
            evaluation_budget=5,
            resume_checkpoint=checkpoint,
        ),
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


def test_enumerative_checkpoint_resume_is_rejected_explicitly() -> None:
    """The CLI does not claim resumability for algorithms without a codec."""
    configuration = _configuration(ENUMERATIVE_ALGORITHM_ID, CPU_BACKEND)
    problem = EnumerationProblem(candidates=(b"one",)).encode()

    _expect_value_error(
        UNSUPPORTED_RESUME,
        lambda: run_configured_search(
            configuration,
            problem,
            SearchRunOptions(
                evaluation_budget=1,
                resume_checkpoint=b"checkpoint",
            ),
        ),
    )


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


def test_live_cuda_cli_resumes_rotate_checkpoint() -> None:
    """Live CUDA resume records CUDA and preserves fresh proposals."""
    configuration = _configuration(ROTATE_TARGET_ALGORITHM_ID, CUDA_BACKEND)
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(0, 1, 2, 1, 4),
    )
    checkpoint = _rotate_resume_checkpoint(problem, budget=5)
    with _live_cuda() as cuda:
        record = run_configured_search(
            configuration,
            problem.encode(),
            SearchRunOptions(
                evaluation_budget=5,
                resume_checkpoint=checkpoint,
            ),
            cuda_factory=lambda: cuda,
        )

    assert record.identity.configured_backend_id == CUDA_BACKEND
    assert record.identity.actual_backend_id == CUDA_BACKEND
    assert tuple(item.logical_id for item in record.result.proposals) == (
        "corpus-1",
    )


def test_live_cuda_cli_resumes_crazy_checkpoint() -> None:
    """Live CUDA resumes crazy-target state with exact proposal identity."""
    configuration = _configuration(CRAZY_TARGET_ALGORITHM_ID, CUDA_BACKEND)
    problem = CrazyTargetProblem(
        accumulator=0,
        target=CRAZY_ALL_ONES,
        candidates=(0, 1, 2, 3, 4, 1),
    )
    checkpoint = _crazy_resume_checkpoint(problem, budget=6)
    with _live_cuda() as cuda:
        record = run_configured_search(
            configuration,
            problem.encode(),
            SearchRunOptions(
                evaluation_budget=6,
                resume_checkpoint=checkpoint,
            ),
            cuda_factory=lambda: cuda,
        )

    assert record.identity.actual_backend_id == CUDA_BACKEND
    assert len(record.result.proposals) == CRAZY_PROPOSALS


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


def test_main_reads_resume_checkpoint_and_records_provenance(
    tmp_path: Path,
) -> None:
    """CLI resume path records checkpoint digest and executor identity."""
    config, problem_path, checkpoint_path, checkpoint = _resume_cli_inputs(
        tmp_path
    )
    stdout = StringIO()
    stderr = StringIO()

    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = main((
            "--config",
            str(config),
            "--problem",
            str(problem_path),
            "--budget",
            "5",
            "--resume-checkpoint",
            str(checkpoint_path),
        ))

    assert status == 0
    payload = _json_object(stdout.getvalue())
    assert payload[RESUME_CHECKPOINT_SHA_FIELD] == sha256(
        checkpoint
    ).hexdigest()
    assert payload[RESUME_EXECUTION_FIELD] == resumable_evaluated_search_id()
    assert payload["actual_backend_id"] == CPU_BACKEND
    assert not stderr.getvalue()


def _extract_progress_checkpoint(root: Path, sidecar_path: Path) -> bytes:
    progress_module = progress.__file__
    assert progress_module is not None
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            progress_module,
            "--extract-checkpoint",
            SEARCH_CHECKPOINT_CODEC,
            str(sidecar_path),
        ],
        check=False,
        capture_output=True,
        env=_subprocess_environment(
            root / "src/automation/repository/composition"
        ),
        shell=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    return completed.stdout


def _run_optimizer_resume_subprocess(
    root: Path,
    tmp_path: Path,
    problem: bytes,
    *,
    checkpoint: bytes,
) -> dict[str, object]:
    config, problem_path, checkpoint_path, _ = _resume_cli_inputs(tmp_path)
    _ = problem_path.write_bytes(problem)
    _ = checkpoint_path.write_bytes(checkpoint)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            "-m",
            "optimizer.cli",
            "--config",
            str(config),
            "--problem",
            str(problem_path),
            "--budget",
            "5",
            "--resume-checkpoint",
            str(checkpoint_path),
        ],
        check=False,
        capture_output=True,
        env=_subprocess_environment(
            root / "src/optimization/accelerator/application",
            root / "src/optimization/accelerator/adapter-outbound",
            root / "src/optimization/optimizer/application",
        ),
        shell=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    return _json_object(completed.stdout.decode())


def test_progress_extraction_bridges_to_optimizer_resume_cli(
    tmp_path: Path,
) -> None:
    """Verified sidecar extraction feeds the product-facing resume flag."""
    root = Path(__file__).resolve().parents[2]
    problem = RotateTargetProblem(
        target=ROTATE_ONE,
        candidates=(0, 1, 2, 1, 4),
    )
    problem_bytes = problem.encode()
    checkpoint = _rotate_resume_checkpoint(problem, budget=5)
    sidecar_path = _published_progress_sidecar(
        tmp_path,
        problem_bytes,
        checkpoint,
    )

    extracted = _extract_progress_checkpoint(root, sidecar_path)
    payload = _run_optimizer_resume_subprocess(
        root,
        tmp_path,
        problem_bytes,
        checkpoint=extracted,
    )

    assert extracted == checkpoint
    assert payload[RESUME_CHECKPOINT_SHA_FIELD] == sha256(
        checkpoint
    ).hexdigest()
    assert payload["actual_backend_id"] == CPU_BACKEND
    assert payload["proposals"] == [
        {"logical_id": "corpus-1", "payload_hex": ROTATE_ONE_PAYLOAD_HEX}
    ]


def test_main_rejects_malformed_resume_checkpoint(tmp_path: Path) -> None:
    """Malformed durable state returns the stable CLI configuration status."""
    config, problem_path, checkpoint_path, _ = _resume_cli_inputs(tmp_path)
    _ = checkpoint_path.write_bytes(b"not-json")
    stdout = StringIO()
    stderr = StringIO()

    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = main((
            "--config",
            str(config),
            "--problem",
            str(problem_path),
            "--budget",
            "5",
            "--resume-checkpoint",
            str(checkpoint_path),
        ))

    assert status == CONFIGURATION_ERROR
    assert not stdout.getvalue()
    assert INVALID_CHECKPOINT in stderr.getvalue()


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


def _file_input_cli(
    config: Path,
    problem: Path,
    checkpoint: Path,
) -> tuple[int, str, str]:
    """Run a deterministic resume CLI request without process exit.

    Returns:
        Exit code, standard output, and error diagnostic.

    """
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        status = main((
            "--config", str(config), "--problem", str(problem),
            "--budget", "5", "--resume-checkpoint", str(checkpoint),
        ))
    return status, stdout.getvalue(), stderr.getvalue()


@pytest.mark.parametrize("source_kind", ["problem", "checkpoint"])
def test_cli_rejects_oversized_binary_source(
    tmp_path: Path,
    source_kind: str,
) -> None:
    """Canonical problem and resume payloads are independently bounded."""
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    selected = problem if source_kind == SOURCE_KIND_PROBLEM else checkpoint
    with selected.open("wb") as stream:
        _ = stream.truncate(64 * 1024 * 1024 + 1)
    status, output, error = _file_input_cli(config, problem, checkpoint)
    assert status == CONFIGURATION_ERROR
    assert not output
    assert BYTE_LIMIT_ERROR in error


@pytest.mark.parametrize("source_kind", ["problem", "checkpoint"])
def test_cli_rejects_directory_binary_source(
    tmp_path: Path,
    source_kind: str,
) -> None:
    """Directory inputs produce explicit errors before backend work."""
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    selected = problem if source_kind == SOURCE_KIND_PROBLEM else checkpoint
    selected.unlink()
    selected.mkdir()
    status, output, error = _file_input_cli(config, problem, checkpoint)
    assert status == CONFIGURATION_ERROR
    assert not output
    assert REGULAR_SOURCE_ERROR in error


@pytest.mark.parametrize("source_kind", ["problem", "checkpoint"])
def test_cli_rejects_replaced_binary_source_before_read(  # ruff: ignore[too-many-locals]
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    """Equal-byte replacement after stat cannot supply search evidence."""
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    selected = problem if source_kind == SOURCE_KIND_PROBLEM else checkpoint
    replacement = tmp_path / "replacement.bin"
    _ = replacement.write_bytes(selected.read_bytes())
    real_open = os.open
    swapped = False

    def swap_at_open(path: Path, flags: int) -> int:
        nonlocal swapped
        if path == selected:
            _ = replacement.replace(selected)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_at_open)
    status, output, error = _file_input_cli(config, problem, checkpoint)
    assert status == CONFIGURATION_ERROR
    assert not output
    assert SOURCE_CHANGED_ERROR in error
    assert swapped


@pytest.mark.parametrize("source_kind", ["problem", "checkpoint"])
def test_cli_rejects_fifo_binary_source(
    tmp_path: Path,
    source_kind: str,
) -> None:
    """Writerless FIFO inputs never block CLI execution."""
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO unavailable on host")
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    selected = problem if source_kind == SOURCE_KIND_PROBLEM else checkpoint
    selected.unlink()
    mkfifo(selected)
    status, output, error = _file_input_cli(config, problem, checkpoint)
    assert status == CONFIGURATION_ERROR
    assert not output
    assert REGULAR_SOURCE_ERROR in error


@pytest.mark.parametrize("source_kind", ["problem", "checkpoint"])
def test_cli_rejects_binary_inode_swap_after_read(  # ruff: ignore[too-many-locals]
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    """Input source must still match the opened descriptor after reading."""
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    selected = problem if source_kind == SOURCE_KIND_PROBLEM else checkpoint
    replacement = tmp_path / "replacement.bin"
    _ = replacement.write_bytes(selected.read_bytes())
    real_stat = Path.stat
    seen = 0

    def swap_on_recheck(
        path: Path,
        *,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal seen
        if path == selected:
            seen += 1
            if seen == SOURCE_RECHECK:
                _ = replacement.replace(selected)
        return real_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", swap_on_recheck)
    status, output, error = _file_input_cli(config, problem, checkpoint)
    assert status == CONFIGURATION_ERROR
    assert not output
    assert SOURCE_CHANGED_DURING_ERROR in error
    assert seen == SOURCE_RECHECK


@pytest.mark.parametrize("source_kind", ["problem", "checkpoint"])
def test_cli_rejects_in_place_binary_edit_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    """Equal-length edits under one inode cannot supply CLI evidence."""
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    selected = problem if source_kind == SOURCE_KIND_PROBLEM else checkpoint
    real_stat = Path.stat
    seen = 0

    def edit_on_recheck(
        path: Path,
        *,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal seen
        if path == selected:
            seen += 1
            if seen == SOURCE_RECHECK:
                with selected.open("r+b") as stream:
                    _ = stream.write(b"x")
        return real_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", edit_on_recheck)
    status, output, error = _file_input_cli(config, problem, checkpoint)
    assert status == CONFIGURATION_ERROR
    assert not output
    assert SOURCE_CHANGED_DURING_ERROR in error
    assert seen == SOURCE_RECHECK


def test_cli_allows_explicit_binary_aliases(tmp_path: Path) -> None:
    """User-selected symlink paths preserve supported CLI input semantics."""
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    problem_alias = tmp_path / "linked-problem.bin"
    checkpoint_alias = tmp_path / "linked-checkpoint.bin"
    try:
        _ = problem_alias.symlink_to(problem)
        _ = checkpoint_alias.symlink_to(checkpoint)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    status, output, error = _file_input_cli(
        config, problem_alias, checkpoint_alias
    )
    assert status == 0
    assert not error
    assert _json_object(output)["actual_backend_id"] == CPU_BACKEND


@pytest.mark.parametrize("source_kind", ["problem", "checkpoint"])
@pytest.mark.parametrize(
    "opened",
    [False, True, -1, "5", 2**80, type("ForeignFd", (int,), {})(7)],
    ids=["false", "true", "negative", "text", "overlarge", "subclass"],
)
def test_cli_rejects_foreign_binary_descriptor_before_fdopen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
    opened: object,
) -> None:
    """An untrusted descriptor must never alias or close a host standard FD."""
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    selected = problem if source_kind == SOURCE_KIND_PROBLEM else checkpoint
    real_open = os.open
    reached = False

    def fake_open(path: Path, flags: int) -> int:
        nonlocal reached
        if path == selected:
            reached = True
            monkeypatch.setattr(os, "fdopen", forbidden_fdopen)
            return cast("int", opened)
        return real_open(path, flags)

    def forbidden_fdopen(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise AssertionError("foreign descriptor reached fdopen")

    monkeypatch.setattr(os, "open", fake_open)
    status, output, error = _file_input_cli(config, problem, checkpoint)
    assert reached
    assert status == CONFIGURATION_ERROR
    assert not output
    assert "descriptor" in error


@pytest.mark.parametrize("source_kind", ["problem", "checkpoint"])
def test_cli_fdopen_failure_releases_binary_source_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    """An opened native source FD cannot leak when stream transfer fails."""
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    selected = problem if source_kind == SOURCE_KIND_PROBLEM else checkpoint
    real_open = os.open
    opened_descriptor: int | None = None

    def fake_open(path: Path, flags: int) -> int:
        nonlocal opened_descriptor
        descriptor = real_open(path, flags)
        if path == selected:
            opened_descriptor = descriptor
            monkeypatch.setattr(os, "fdopen", failing_fdopen)
        return descriptor

    def failing_fdopen(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise ValueError("synthetic stream transfer failure")

    monkeypatch.setattr(os, "open", fake_open)
    try:
        status, output, error = _file_input_cli(config, problem, checkpoint)
        assert opened_descriptor is not None
        assert status == CONFIGURATION_ERROR
        assert not output
        assert "synthetic stream transfer failure" in error
        with pytest.raises(OSError):
            _ = os.fstat(opened_descriptor)
    finally:
        if opened_descriptor is not None:
            with suppress(OSError):
                os.close(opened_descriptor)


def _write_failure_cli_args(tmp_path: Path) -> tuple[str, ...]:
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    return (
        "--config", str(config), "--problem", str(problem),
        "--budget", "5", "--resume-checkpoint", str(checkpoint),
    )


@pytest.mark.parametrize("claimed", [None, True, False, -1, 0, 1_000_000])
def test_cli_rejects_incomplete_search_json_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    claimed: object,
) -> None:
    """Operator success requires the full text write, not a forged count."""
    class BrokenOutput(StringIO):
        flush_calls: int = 0

        @override
        def write(self, content: str) -> int:
            del content
            return cast("int", claimed)

        @override
        def flush(self) -> None:
            self.flush_calls += 1
            super().flush()

    output = BrokenOutput()
    diagnostic = StringIO()
    with monkeypatch.context() as context:
        context.setattr(sys, "stdout", output)
        context.setattr(sys, "stderr", diagnostic)
        status = main(_write_failure_cli_args(tmp_path))
    assert status == CONFIGURATION_ERROR
    assert not output.getvalue()
    assert output.flush_calls == 0
    assert "stdout" in diagnostic.getvalue()


@pytest.mark.parametrize("claimed", [False, True, -1, 0, "done"])
def test_cli_rejects_noncanonical_search_json_flush(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    claimed: object,
) -> None:
    """A nonnative flush receipt cannot certify output completion."""
    class BrokenOutput(StringIO):
        flush_calls: int = 0

        @override
        def flush(self) -> None:
            self.flush_calls += 1
            return cast("None", claimed)

    output = BrokenOutput()
    diagnostic = StringIO()
    with monkeypatch.context() as context:
        context.setattr(sys, "stdout", output)
        context.setattr(sys, "stderr", diagnostic)
        status = main(_write_failure_cli_args(tmp_path))
    assert status == CONFIGURATION_ERROR
    assert output.getvalue().endswith("\n")
    assert output.flush_calls == 1
    assert "stdout" in diagnostic.getvalue()


@pytest.mark.parametrize("phase", ["write", "flush"])
@pytest.mark.parametrize("failure", [OSError, ValueError, RuntimeError, IndexError])
def test_cli_contains_search_json_output_dependency_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    failure: type[Exception],
) -> None:
    """Ordinary output faults cannot exit with success or an uncaught error."""
    class BrokenOutput(StringIO):
        flush_calls: int = 0

        @override
        def write(self, content: str) -> int:
            if phase == "write":
                raise failure("untrusted output write fault")
            return super().write(content)

        @override
        def flush(self) -> None:
            self.flush_calls += 1
            if phase == "flush":
                raise failure("untrusted output flush fault")
            super().flush()

    output = BrokenOutput()
    diagnostic = StringIO()
    with monkeypatch.context() as context:
        context.setattr(sys, "stdout", output)
        context.setattr(sys, "stderr", diagnostic)
        status = main(_write_failure_cli_args(tmp_path))
    assert status == CONFIGURATION_ERROR
    assert output.flush_calls == (0 if phase == "write" else 1)
    assert "stdout" in diagnostic.getvalue()


@pytest.mark.parametrize("phase", ["write", "flush"])
def test_cli_preserves_configuration_failure_when_stderr_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    """An unavailable diagnostic sink cannot erase a rejected CLI request."""
    class BrokenDiagnostic(StringIO):
        @override
        def write(self, content: str) -> int:
            if phase == "write":
                raise OSError("stderr write unavailable")
            return super().write(content)

        @override
        def flush(self) -> None:
            if phase == "flush":
                raise ValueError("stderr flush unavailable")
            super().flush()

    with monkeypatch.context() as context:
        context.setattr(sys, "stderr", BrokenDiagnostic())
        assert main(("--budget", "invalid")) == CONFIGURATION_ERROR


@pytest.mark.parametrize("source_kind", ["problem", "checkpoint"])
@pytest.mark.parametrize("probe", ["preflight", "opened"])
def test_cli_rejects_foreign_binary_file_metadata_before_field_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
    probe: str,
) -> None:
    """Foreign stat receipts must not impersonate a stable regular input."""
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    selected = problem if source_kind == SOURCE_KIND_PROBLEM else checkpoint
    real_path_stat = Path.stat
    real_open = os.open
    real_fstat = os.fstat
    selected_descriptor: int | None = None
    rejected_receipt = False

    class ForeignStat:
        @override
        def __getattribute__(self, name: str) -> object:
            del name
            raise AssertionError("foreign stat fields were accessed")

    def fake_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        nonlocal rejected_receipt
        if path == selected and probe == "preflight":
            rejected_receipt = True
            return cast("os.stat_result", cast("object", ForeignStat()))
        return real_path_stat(path, follow_symlinks=follow_symlinks)

    def fake_open(path: Path, flags: int) -> int:
        nonlocal selected_descriptor
        descriptor = real_open(path, flags)
        if path == selected:
            selected_descriptor = descriptor
        return descriptor

    def fake_fstat(descriptor: int) -> os.stat_result:
        nonlocal rejected_receipt
        if descriptor == selected_descriptor and probe == "opened":
            rejected_receipt = True
            return cast("os.stat_result", cast("object", ForeignStat()))
        return real_fstat(descriptor)

    monkeypatch.setattr(Path, "stat", fake_stat)
    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "fstat", fake_fstat)
    status, output, error = _file_input_cli(config, problem, checkpoint)
    assert rejected_receipt
    assert status == CONFIGURATION_ERROR
    assert not output
    assert "metadata" in error


def test_search_cli_rejects_foreign_argument_vectors_before_argparse() -> None:
    """Direct CLI callers cannot execute foreign comparison/iteration hooks."""
    class HostileArguments(list[str]):
        @override
        def __iter__(self) -> Iterator[str]:
            raise AssertionError("foreign CLI argument iteration executed")

    class HostileText(str):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign CLI string conversion executed")

    malformed: tuple[object, ...] = (
        [42], [None], [b"--budget"], ["--config", 42],
        (42,), "--budget", b"--budget", HostileArguments(["--help"]),
        [HostileText("--help")],
    )
    for supplied in malformed:
        output = StringIO()
        diagnostic = StringIO()
        with redirect_stdout(output), redirect_stderr(diagnostic):
            status = main(cast("list[str] | tuple[str, ...]", supplied))
        assert status == CONFIGURATION_ERROR
        assert not output.getvalue()
        assert "arguments" in diagnostic.getvalue()


def test_search_cli_rejects_foreign_process_argv_before_argparse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The implicit process argv source has the same native-string boundary."""
    output = StringIO()
    diagnostic = StringIO()
    with monkeypatch.context() as context:
        context.setattr(sys, "argv", cast("list[str]", ["optimizer", 42]))
        with redirect_stdout(output), redirect_stderr(diagnostic):
            status = main(None)
    assert status == CONFIGURATION_ERROR
    assert not output.getvalue()
    assert "arguments" in diagnostic.getvalue()


@pytest.mark.parametrize("source_kind", ["problem", "checkpoint"])
@pytest.mark.parametrize("phase", ["stat", "open"])
def test_cli_wraps_hostile_binary_source_os_errors_without_string_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
    phase: str,
) -> None:
    """Untrusted OSError __str__ cannot escape as an untyped CLI traceback."""
    config, problem, checkpoint, _ = _resume_cli_inputs(tmp_path)
    selected = problem if source_kind == SOURCE_KIND_PROBLEM else checkpoint
    real_stat = Path.stat
    real_open = os.open
    raised = False

    class HostileOsError(OSError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign OSError __str__ called")

    def failing_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        nonlocal raised
        if path == selected and phase == "stat":
            raised = True
            raise HostileOsError("synthetic hostile binary source")
        return real_stat(path, follow_symlinks=follow_symlinks)

    def failing_open(path: Path, flags: int) -> int:
        nonlocal raised
        if path == selected and phase == "open":
            raised = True
            raise HostileOsError("synthetic hostile binary source")
        return real_open(path, flags)

    monkeypatch.setattr(Path, "stat", failing_stat)
    monkeypatch.setattr(os, "open", failing_open)
    status, output, error = _file_input_cli(config, problem, checkpoint)
    assert raised
    assert status == CONFIGURATION_ERROR
    assert not output
    assert "HostileOsError" in error
