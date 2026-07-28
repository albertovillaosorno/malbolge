# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Optional NVIDIA CUDA accelerator adapter."""

from accelerator.cuda.exact_primitives import CudaExactPrimitiveAdapter
from accelerator.cuda.exact_primitives import CudaPreparedPrimitiveStats

__all__ = ["CudaExactPrimitiveAdapter", "CudaPreparedPrimitiveStats"]
