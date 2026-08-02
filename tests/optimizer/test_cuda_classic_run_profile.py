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
#   - CUDA diagnostic profiling preserves classic resident execution semantics.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""CUDA diagnostic profiling preserves classic resident execution semantics."""

from __future__ import annotations

from unittest import SkipTest

from accelerator.classic_run import ClassicRunRequest
from accelerator.classic_run import MEMORY_WORDS
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_run import CudaClassicRunAdapter
from accelerator.exact_primitives import AcceleratorUnavailableError

ZERO_MEMORY: tuple[int, ...] = (0,) * MEMORY_WORDS


def _cuda() -> CudaClassicRunAdapter:
    try:
        return CudaClassicRunAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def test_profiled_classic_run_matches_normal_cuda_execution() -> None:
    """Profiling records timing without changing the resident VM result."""
    request = ClassicRunRequest(
        accumulator=7,
        code_pointer=0,
        data_pointer=0,
        input_bytes=(),
        input_consumed=0,
        memory=ZERO_MEMORY,
        output_bytes=(),
        step_budget=4,
        termination=StepTermination.NONE,
    ).validated()
    with _cuda() as adapter:
        expected = adapter.evaluate((request,))
        observed, profile = adapter.profile_evaluate((request,))
    assert observed == expected
    assert profile.chunks == 1
    phases = (
        profile.validation_plan_ns,
        profile.host_build_ns,
        profile.allocate_ns,
        profile.upload_ns,
        profile.kernel_ns,
        profile.download_ns,
        profile.decode_ns,
        profile.release_ns,
    )
    assert all(value >= 0 for value in phases)
    assert sum(phases) <= profile.total_ns
