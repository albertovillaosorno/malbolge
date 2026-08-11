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
#   - White-box exact-state identity evidence for bounded classic cycle proofs.
# - Must-Not:
#   - Claim public-source reachability or certify unknown accumulator values.
# - Allows:
#   - Inputs: test-local concrete machine states and immutable source words.
#   - Outputs: canonical memory and repeated-state certificate assertions.
#   - Side effects: module loading only.
# - Split-When:
#   - Public report-level cycle fixtures gain independent differential evidence.
# - Merge-When:
#   - Prefix transfer tests own the same exact state-identity invariant.
# - Summary:
#   - Proves sparse effective memory is sufficient for exact cycle identity.
# - Description:
#   - Covers write restoration, unknown-state refusal, and period evidence.
# - Usage:
#   - Collected by the exhaustive Python verifier test surface.
# - Defaults:
#   - No guest loop or external source is executed.
#

"""White-box exact-state identity tests for bounded Malbolge cycle proofs."""

# ruff: file-ignore[private-member-access]
# pyright: reportPrivateUsage=false

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import cast

_ROOT = Path(__file__).resolve().parents[2]
_PREFIX = _ROOT / "verifier" / "emitted_malbolge_prefix.py"
_INITIAL = (99, 116)
_CHANGED = 42
_OTHER_CHANGED = 43
_CODE_POINTER = 3
_OTHER_CODE_POINTER = 4
_DATA_POINTER = 5
_ACCUMULATOR = 6
_FIRST = 2
_REPEAT = 7


class _MemoryState(Protocol):
    overrides: tuple[tuple[int, int], ...]


class _MachineState(Protocol):
    code_pointer: int
    data_pointer: int
    accumulator: int | None


class _Certificate(Protocol):
    first_seen_before_transition: int
    repeated_before_transition: int
    period_transitions: int
    code_pointer: int
    data_pointer: int
    accumulator: int
    memory_overrides: tuple[tuple[int, int], ...]


class _MemoryFactory(Protocol):
    def __call__(
        self,
        words: tuple[int, ...],
        overrides: tuple[tuple[int, int], ...] = (),
    ) -> _MemoryState: ...


class _MachineFactory(Protocol):
    def __call__(
        self,
        code_pointer: int,
        data_pointer: int,
        accumulator: int | None,
    ) -> _MachineState: ...


class _PrefixModule(Protocol):
    _MemoryState: _MemoryFactory
    _MachineState: _MachineFactory

    def _commit_write(
        self,
        memory: _MemoryState,
        address: int | None,
        value: int | None,
    ) -> _MemoryState: ...

    def _exact_state_key(
        self,
        memory: _MemoryState,
        state: _MachineState | None,
    ) -> tuple[int, int, int, tuple[tuple[int, int], ...]] | None: ...

    def _remember_exact_state(
        self,
        seen: dict[tuple[int, int, int, tuple[tuple[int, int], ...]], int],
        memory: _MemoryState,
        state: _MachineState | None,
        *,
        before_transition: int,
    ) -> _Certificate | None: ...


def _load_prefix() -> _PrefixModule:
    spec = importlib.util.spec_from_file_location(
        "cycle_identity_prefix",
        _PREFIX,
    )
    if spec is None or spec.loader is None:
        message = "prefix transfer module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(_PREFIX.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        _ = sys.path.pop(0)
    return cast("_PrefixModule", cast("object", module))


_PREFIX_MODULE = _load_prefix()


def _memory() -> _MemoryState:
    return _PREFIX_MODULE._MemoryState(_INITIAL)


def _state(
    *,
    code_pointer: int = _CODE_POINTER,
    accumulator: int | None = _ACCUMULATOR,
) -> _MachineState:
    return _PREFIX_MODULE._MachineState(
        code_pointer,
        _DATA_POINTER,
        accumulator,
    )


def test_effective_memory_removes_restored_initial_value() -> None:
    """Writing the immutable initial value removes the sparse override."""
    changed = _PREFIX_MODULE._commit_write(_memory(), 0, _CHANGED)
    assert changed.overrides == ((0, _CHANGED),)
    restored = _PREFIX_MODULE._commit_write(changed, 0, _INITIAL[0])
    assert restored.overrides == ()


def test_effective_memory_identity_is_order_independent() -> None:
    """Equivalent writes canonicalize to one sorted memory identity."""
    first = _PREFIX_MODULE._commit_write(_memory(), 1, _OTHER_CHANGED)
    first = _PREFIX_MODULE._commit_write(first, 0, _CHANGED)
    second = _PREFIX_MODULE._commit_write(_memory(), 0, _CHANGED)
    second = _PREFIX_MODULE._commit_write(second, 1, _OTHER_CHANGED)
    expected = ((0, _CHANGED), (1, _OTHER_CHANGED))
    assert first.overrides == expected
    assert second.overrides == expected


def test_unknown_accumulator_has_no_exact_state_key() -> None:
    """Unknown input state never masquerades as a concrete repeated state."""
    unknown = _state(accumulator=None)
    assert _PREFIX_MODULE._exact_state_key(_memory(), unknown) is None
    assert _PREFIX_MODULE._exact_state_key(_memory(), None) is None


def test_cycle_identity_distinguishes_registers_and_effective_memory() -> None:
    """Only full register and effective-memory equality produces a repeat."""
    original_memory = _PREFIX_MODULE._commit_write(_memory(), 0, _CHANGED)
    original_state = _state()
    seen: dict[tuple[int, int, int, tuple[tuple[int, int], ...]], int] = {}
    assert (
        _PREFIX_MODULE._remember_exact_state(
            seen,
            original_memory,
            original_state,
            before_transition=_FIRST,
        )
        is None
    )
    changed_memory = _PREFIX_MODULE._commit_write(
        original_memory,
        1,
        _OTHER_CHANGED,
    )
    assert (
        _PREFIX_MODULE._remember_exact_state(
            seen,
            changed_memory,
            original_state,
            before_transition=_FIRST + 1,
        )
        is None
    )
    assert (
        _PREFIX_MODULE._remember_exact_state(
            seen,
            original_memory,
            _state(code_pointer=_OTHER_CODE_POINTER),
            before_transition=_FIRST + 2,
        )
        is None
    )
    repeated = _PREFIX_MODULE._remember_exact_state(
        seen,
        original_memory,
        original_state,
        before_transition=_REPEAT,
    )
    assert repeated is not None
    assert repeated.first_seen_before_transition == _FIRST
    assert repeated.repeated_before_transition == _REPEAT
    assert repeated.period_transitions == _REPEAT - _FIRST
    assert repeated.code_pointer == _CODE_POINTER
    assert repeated.data_pointer == _DATA_POINTER
    assert repeated.accumulator == _ACCUMULATOR
    assert repeated.memory_overrides == ((0, _CHANGED),)
