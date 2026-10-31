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
#   - Exact unit-preserving admission of declared experiment-run budgets.
# - Must-Not:
#   - Assert actual resource enforcement, sampling, or verifier execution.
# - Allows:
#   - Inputs: bounded version-one experiment run manifest TOML text.
#   - Outputs: declared time and memory budgets normalized to arena units.
#   - Side effects: none.
# - Split-When:
#   - Other budget units require separately versioned interpretation.
# - Merge-When:
#   - A governed experiment-run parser exposes the same resource semantics.
# - Summary:
#   - Prevents incompatible resource budgets from entering an arena study.
# - Description:
#   - Requires exact whole-second and MiB source declarations.
# - Usage:
#   - Called only by optional arena evidence budget-agreement preflight.
# - Defaults:
#   - Missing, nonpositive, or noninteger budgets fail closed.
#

"""Read declared experiment-run resource limits without measuring resources."""

from __future__ import annotations

from dataclasses import dataclass
import tomllib
from typing import Never

NANOSECONDS_PER_SECOND = 1_000_000_000
BYTES_PER_MIB = 1_048_576
MAX_RUN_MANIFEST_BYTES = 1_048_576


class BudgetLinkError(ValueError):
    """Incompatible or missing run resource limit declaration."""


@dataclass(frozen=True, slots=True)
class RunBudgets:
    """Reported resource limits in the arena's exact base units."""

    time_ns: int
    memory_bytes: int


def _fail(message: str) -> Never:
    raise BudgetLinkError(message)


def _positive_integer(table: dict[str, object], key: str) -> int:
    value = table.get(key)
    if type(value) is not int or value <= 0:
        _fail(f"experiment run budget.{key} must be a positive integer")
    return value


def _admit_text(text: str) -> None:
    if type(text) is not str:
        _fail("budget run manifest requires exact str text")
    if len(text) > MAX_RUN_MANIFEST_BYTES:
        _fail("budget run manifest exceeds byte limit")
    try:
        encoded_size = len(text.encode("utf-8"))
    except UnicodeEncodeError as error:
        message = "budget run manifest requires strict UTF-8 text"
        raise BudgetLinkError(message) from error
    if encoded_size > MAX_RUN_MANIFEST_BYTES:
        _fail("budget run manifest exceeds byte limit")


def parse_run_budgets(text: str) -> RunBudgets:
    """Read optional strict arena budget links from experiment-run TOML.

    Returns:
        Exact declared limit values after deterministic unit conversion.

    Raises:
        BudgetLinkError: The run lacks the required declared resource limits.

    """
    _admit_text(text)
    try:
        document = tomllib.loads(text)
    except Exception as error:
        # The parser is a dependency: all ordinary faults must stay typed.
        # Preserve the cause without invoking foreign exception formatters.
        message = "invalid experiment run budget TOML"
        raise BudgetLinkError(message) from error
    if type(document) is not dict:
        _fail("invalid experiment run budget TOML root")
    if any(type(key) is not str for key in document):
        _fail("experiment run budget TOML requires native string keys")
    budget = document.get("budget")
    if type(budget) is not dict:
        _fail("experiment run budget table is missing")
    if any(type(key) is not str for key in budget):
        _fail("experiment run budget table requires native string keys")
    return RunBudgets(
        time_ns=_positive_integer(budget, "seconds") * NANOSECONDS_PER_SECOND,
        memory_bytes=_positive_integer(budget, "memory_mib") * BYTES_PER_MIB,
    )
