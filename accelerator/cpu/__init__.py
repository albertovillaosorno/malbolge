# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Mandatory deterministic CPU accelerator reference adapters."""

from accelerator.cpu.exact_primitives import CpuExactPrimitiveAdapter
from accelerator.cpu.exact_primitives import CpuPreparedPrimitiveStats
from accelerator.cpu.work_ports import CpuCandidateEvaluationAdapter
from accelerator.cpu.work_ports import CpuSearchExecutionAdapter

__all__ = [
    "CpuCandidateEvaluationAdapter",
    "CpuExactPrimitiveAdapter",
    "CpuPreparedPrimitiveStats",
    "CpuSearchExecutionAdapter",
]
