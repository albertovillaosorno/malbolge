# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Differential evidence for replaceable exact primitive adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import SkipTest

if TYPE_CHECKING:
    from collections.abc import Callable

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import InvalidPrimitiveBatchError
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind

CUDA_BACKEND = "cuda"
EDGE_WORDS = (0, 1, 2, 3, 59_048, 19_683, 39_366, 243, 59_047)


def _cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _deterministic_words(count: int) -> tuple[int, ...]:
    value = 0x1234_5678
    words: list[int] = []
    for _ in range(count):
        value = (value * 1_664_525 + 1_013_904_223) & 0xFFFF_FFFF
        words.append(value % (MAX_WORD + 1))
    return tuple(words)


def _expect_error(
    exception: type[Exception],
    message: str,
    action: Callable[[], object],
) -> None:
    try:
        _ = action()
    except exception as error:
        observed = str(error)
        if message not in observed:
            raise AssertionError from error
        return
    raise AssertionError


def test_closed_cuda_adapter_fails_explicitly() -> None:
    """A closed optional adapter never silently changes execution semantics."""
    adapter = _cuda()
    adapter.close()
    batch = PrimitiveBatch(
        accumulators=(), data=(1,), kind=PrimitiveKind.ROTATE
    )
    _expect_error(
        AcceleratorExecutionError,
        "CUDA adapter is closed",
        lambda: adapter.evaluate(batch),
    )


def test_cpu_reference_known_edges() -> None:
    """CPU reference preserves established classic rotate/crazy edge vectors."""
    cpu = CpuExactPrimitiveAdapter()
    rotate = cpu.evaluate(
        PrimitiveBatch(
            accumulators=(), data=(1, 3, MAX_WORD), kind=PrimitiveKind.ROTATE
        )
    )
    assert rotate.values == (19_683, 1, MAX_WORD)
    crazy = cpu.evaluate(
        PrimitiveBatch(
            accumulators=(0, MAX_WORD),
            data=(MAX_WORD, 0),
            kind=PrimitiveKind.CRAZY,
        )
    )
    assert crazy.values == (MAX_WORD, 0)


def test_cuda_crazy_matches_cpu_reference() -> None:
    """CUDA crazy equals CPU scalar reference on a fixed paired corpus."""
    data = EDGE_WORDS + _deterministic_words(4_096)
    accumulator = tuple(reversed(data))
    batch = PrimitiveBatch(
        accumulators=accumulator,
        data=data,
        kind=PrimitiveKind.CRAZY,
    )
    cpu = CpuExactPrimitiveAdapter().evaluate(batch)
    with _cuda() as adapter:
        cuda = adapter.evaluate(batch)
    assert cuda.values == cpu.values


def test_cuda_rotate_matches_cpu_reference() -> None:
    """CUDA rotation equals CPU scalar reference over edges and fixed corpus."""
    data = EDGE_WORDS + _deterministic_words(4_096)
    batch = PrimitiveBatch(
        accumulators=(), data=data, kind=PrimitiveKind.ROTATE
    )
    cpu = CpuExactPrimitiveAdapter().evaluate(batch)
    with _cuda() as adapter:
        cuda = adapter.evaluate(batch)
    assert cuda.values == cpu.values
    assert cuda.capability.backend_id == CUDA_BACKEND
    assert cuda.capability.device_arch.startswith("sm_")
    assert cuda.capability.device_name


def test_invalid_batch_fails_before_backend_execution() -> None:
    """Reject malformed requests before backend execution."""
    batch = PrimitiveBatch(
        accumulators=(1,),
        data=(2,),
        kind=PrimitiveKind.ROTATE,
    )
    _expect_error(
        InvalidPrimitiveBatchError,
        "rotate batch must not carry accumulators",
        lambda: CpuExactPrimitiveAdapter().evaluate(batch),
    )
