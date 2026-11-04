# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
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
from typing import Never

import tomllib

# Preserve a source parser independent of the mutable public module entrypoint.
_SOURCE_TOML_LOADS = tomllib.loads
_SOURCE_LEN = len
# Native value and mapping shapes must not follow replacement module aliases.
_SOURCE_TYPE = type
_SOURCE_ANY = any
_SOURCE_DICT = dict
_SOURCE_STR = str
_SOURCE_INT = int

NANOSECONDS_PER_SECOND = 1_000_000_000
BYTES_PER_MIB = 1_048_576
# Canonical unit semantics must survive substitutions of public module values.
_SOURCE_NANOSECONDS_PER_SECOND = NANOSECONDS_PER_SECOND
_SOURCE_BYTES_PER_MIB = BYTES_PER_MIB
MAX_RUN_MANIFEST_BYTES = 1_048_576
_SOURCE_MAX_RUN_MANIFEST_BYTES = MAX_RUN_MANIFEST_BYTES


class BudgetLinkError(ValueError):
    """Incompatible or missing run resource limit declaration."""


# Rejection identity must survive consumer rebinding of the public error.
_SOURCE_BUDGET_LINK_ERROR = BudgetLinkError


@dataclass(frozen=True, slots=True)
class RunBudgets:
    """Reported resource limits in the arena's exact base units."""

    time_ns: int
    memory_bytes: int


# Keep admitted budget values independent of a substituted public factory.
_SOURCE_RUN_BUDGETS = RunBudgets


def _fail(message: str) -> Never:
    raise _SOURCE_BUDGET_LINK_ERROR(message)


_SOURCE_FAIL = _fail


def _positive_integer(table: dict[str, object], key: str) -> int:
    value = table.get(key)
    if _SOURCE_TYPE(value) is not _SOURCE_INT or value <= 0:
        _SOURCE_FAIL(f"experiment run budget.{key} must be a positive integer")
    return value


def _admit_text(text: str) -> None:
    if _SOURCE_TYPE(text) is not _SOURCE_STR:
        _SOURCE_FAIL("budget run manifest requires exact str text")
    if _SOURCE_LEN(text) > _SOURCE_MAX_RUN_MANIFEST_BYTES:
        _SOURCE_FAIL("budget run manifest exceeds byte limit")
    try:
        encoded_size = _SOURCE_LEN(text.encode("utf-8"))
    except UnicodeEncodeError as error:
        message = "budget run manifest requires strict UTF-8 text"
        raise _SOURCE_BUDGET_LINK_ERROR(message) from error
    if encoded_size > _SOURCE_MAX_RUN_MANIFEST_BYTES:
        _SOURCE_FAIL("budget run manifest exceeds byte limit")


_SOURCE_ADMIT_TEXT = _admit_text


_SOURCE_POSITIVE_INTEGER = _positive_integer


def parse_run_budgets(text: str) -> RunBudgets:
    """Read optional strict arena budget links from experiment-run TOML.

    Returns:
        Exact declared limit values after deterministic unit conversion.

    Raises:
        BudgetLinkError: The run lacks the required declared resource limits.

    """
    _SOURCE_ADMIT_TEXT(text)
    try:
        document = tomllib.loads(text)
    except Exception as error:
        # The parser is a dependency: all ordinary faults must stay typed.
        # Preserve the cause without invoking foreign exception formatters.
        message = "invalid experiment run budget TOML"
        raise _SOURCE_BUDGET_LINK_ERROR(message) from error
    if _SOURCE_TYPE(document) is not _SOURCE_DICT:
        _SOURCE_FAIL("invalid experiment run budget TOML root")
    if _SOURCE_ANY(_SOURCE_TYPE(key) is not _SOURCE_STR for key in document):
        _SOURCE_FAIL("experiment run budget TOML requires native string keys")
    budget = document.get("budget")
    if _SOURCE_TYPE(budget) is not _SOURCE_DICT:
        _SOURCE_FAIL("experiment run budget table is missing")
    if _SOURCE_ANY(_SOURCE_TYPE(key) is not _SOURCE_STR for key in budget):
        _SOURCE_FAIL("experiment run budget table requires native string keys")
    seconds = _SOURCE_POSITIVE_INTEGER(budget, "seconds")
    memory_mib = _SOURCE_POSITIVE_INTEGER(budget, "memory_mib")
    # A substituted decoder can return a perfectly native but fabricated
    # budget. Compare the admitted fields with an import-time bound parser of
    # the actual source, not another invocation through the mutable module.
    try:
        source = _SOURCE_TOML_LOADS(text)
    except Exception as error:
        message = "experiment run budget source TOML could not be parsed"
        raise _SOURCE_BUDGET_LINK_ERROR(message) from error
    source_budget = source.get("budget")
    if (
        _SOURCE_TYPE(source_budget) is not _SOURCE_DICT
        or _SOURCE_TYPE(source_budget.get("seconds")) is not _SOURCE_INT
        or source_budget["seconds"] != seconds
        or _SOURCE_TYPE(source_budget.get("memory_mib")) is not _SOURCE_INT
        or source_budget["memory_mib"] != memory_mib
    ):
        _SOURCE_FAIL("experiment run budget differs from source TOML")
    return _SOURCE_RUN_BUDGETS(
        time_ns=seconds * _SOURCE_NANOSECONDS_PER_SECOND,
        memory_bytes=memory_mib * _SOURCE_BYTES_PER_MIB,
    )
