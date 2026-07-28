# File:
#   - exact_primitives.py
# Path:
#   - accelerator/cpu/exact_primitives.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Deterministic CPU reference for exact classic ternary primitives.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Deterministic CPU reference for exact classic ternary primitives."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from itertools import starmap
from operator import itemgetter
from typing import TYPE_CHECKING
from typing import cast
from typing import final
from typing import override

from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import ExactPrimitiveAdapter
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import PrimitiveResult
from accelerator.exact_primitives import ROTATE_HIGH_TRIT_WEIGHT
from accelerator.exact_primitives import TRIT_COUNT

if TYPE_CHECKING:
    from accelerator.exact_primitives import PreparedPrimitiveBatch
    from accelerator.exact_primitives import PrimitiveBatch

CPU_CAPABILITY = AcceleratorCapability(
    backend_id="cpu-reference",
    device_arch="scalar",
    device_name="portable-cpu",
)
CRAZY_TRIT_TABLE = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


@dataclass(frozen=True, slots=True)
class CpuPreparedPrimitiveStats:
    """Observable prepared CPU decode-session and rotate-table usage."""

    builds: int
    evaluations: int
    resident_count: int
    resident_kind: PrimitiveKind | None
    reuses: int
    rotate_table_entries: int


@dataclass(frozen=True, slots=True)
class _CpuPreparedPrimitiveSession:
    prepared: PreparedPrimitiveBatch
    batch: PrimitiveBatch


@final
class CpuExactPrimitiveAdapter(ExactPrimitiveAdapter):
    """Mandatory exact scalar reference implementation."""

    _prepared_builds: int
    _prepared_evaluations: int
    _prepared_reuses: int
    _prepared_rotate_table_entries: int
    _prepared_session: _CpuPreparedPrimitiveSession | None

    def __init__(self) -> None:
        """Create one CPU adapter with empty prepared-use diagnostics."""
        self._prepared_builds = 0
        self._prepared_evaluations = 0
        self._prepared_reuses = 0
        self._prepared_rotate_table_entries = 0
        self._prepared_session = None

    @override
    def capability(self) -> AcceleratorCapability:
        """Return the portable CPU reference identity.

        Returns:
            Stable scalar CPU capability identity.

        """
        return CPU_CAPABILITY

    @override
    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveResult:
        """Evaluate exact primitives with independent scalar ternary formulas.

        Returns:
            Exact classic-word results in input order.

        """
        return _evaluate_validated(batch.validated())

    @override
    def evaluate_prepared(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> PrimitiveResult:
        """Evaluate previously validated immutable primitive input.

        Returns:
            Exact classic-word results in input order.

        """
        session = self._prepared_session_for(prepared)
        result = _evaluate_prepared_validated(session.batch)
        self._prepared_evaluations += 1
        if session.batch.kind is PrimitiveKind.ROTATE and session.batch.data:
            self._prepared_rotate_table_entries = len(_rotate_table())
        return result

    def prepared_stats(self) -> CpuPreparedPrimitiveStats:
        """Return prepared rotate-table evaluation diagnostics.

        Returns:
            Immutable evaluation count and observed table cardinality.

        """
        session = self._prepared_session
        return CpuPreparedPrimitiveStats(
            builds=self._prepared_builds,
            evaluations=self._prepared_evaluations,
            resident_count=(0 if session is None else len(session.batch.data)),
            resident_kind=(None if session is None else session.batch.kind),
            reuses=self._prepared_reuses,
            rotate_table_entries=self._prepared_rotate_table_entries,
        )

    def _prepared_session_for(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> _CpuPreparedPrimitiveSession:
        current = self._prepared_session
        if current is not None and current.prepared is prepared:
            self._prepared_reuses += 1
            return current
        session = _CpuPreparedPrimitiveSession(
            prepared=prepared,
            batch=prepared.validated_batch(),
        )
        self._prepared_session = session
        self._prepared_builds += 1
        return session


def _evaluate_prepared_validated(batch: PrimitiveBatch) -> PrimitiveResult:
    if batch.kind is PrimitiveKind.ROTATE:
        values = _prepared_rotate(batch.data)
        return PrimitiveResult(capability=CPU_CAPABILITY, values=values)
    return _evaluate_validated(batch)


def _evaluate_validated(batch: PrimitiveBatch) -> PrimitiveResult:
    if batch.kind is PrimitiveKind.ROTATE:
        values = tuple(_rotate(value) for value in batch.data)
    else:
        pairs = zip(
            batch.data,
            batch.accumulators,
            strict=True,
        )
        values = tuple(starmap(_crazy, pairs))
    return PrimitiveResult(capability=CPU_CAPABILITY, values=values)


def _crazy(data: int, accumulator: int) -> int:
    result = 0
    place = 1
    for _ in range(TRIT_COUNT):
        output = _crazy_trit(data % 3, accumulator % 3)
        result += output * place
        place *= 3
        data //= 3
        accumulator //= 3
    return result


def _crazy_trit(data: int, accumulator: int) -> int:
    return CRAZY_TRIT_TABLE[data][accumulator]


def _prepared_rotate(data: tuple[int, ...]) -> tuple[int, ...]:
    if not data:
        return ()
    table = _rotate_table()
    if len(data) == 1:
        return (table[data[0]],)
    return cast("tuple[int, ...]", itemgetter(*data)(table))


@cache
def _rotate_table() -> tuple[int, ...]:
    return tuple(_rotate(value) for value in range(MAX_WORD + 1))


def _rotate(value: int) -> int:
    return (value // 3) + ((value % 3) * ROTATE_HIGH_TRIT_WEIGHT)
