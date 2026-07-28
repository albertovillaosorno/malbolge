# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Validate research algorithm lifecycle evidence and decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sys
import tomllib
from typing import Never
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
ALGORITHMS_ROOT = ROOT / "algorithms"
SCHEMA_VERSION = 1
PARENT_SEGMENT = ".."
EXPERIMENTAL = "experimental"
PROMOTION_CANDIDATE = "promotion-candidate"
PROMOTED = "promoted"
REJECTED = "rejected"
RETIRED = "retired"
STATES = frozenset({
    EXPERIMENTAL,
    PROMOTION_CANDIDATE,
    PROMOTED,
    REJECTED,
    RETIRED,
})
PROMOTION_STATES = frozenset({PROMOTION_CANDIDATE, PROMOTED, RETIRED})
DECISION_STATES = frozenset({PROMOTED, REJECTED, RETIRED})
PROMOTION_FIELDS = (
    "correctness",
    "reproducibility",
    "maintainability",
    "portability",
    "measured_benefit",
)


class AlgorithmLifecycleError(ValueError):
    """Research algorithm lifecycle metadata violates promotion policy."""


@dataclass(frozen=True, slots=True)
class PromotionEvidence:
    """Durable evidence required before an algorithm can be promoted."""

    correctness: str
    maintainability: str
    measured_benefit: str
    portability: str
    reproducibility: str


@dataclass(frozen=True, slots=True)
class LifecycleDecision:
    """Durable decision metadata for promoted, rejected, or retired states."""

    decided_on: date
    evidence: str
    negative_results: str | None
    reason: str
    superseded_by: str | None


@dataclass(frozen=True, slots=True)
class AlgorithmLifecycle:
    """Validated static lifecycle state for one stable research algorithm ID."""

    experiment_manifest: str
    identifier: str
    promotion: PromotionEvidence | None
    decision: LifecycleDecision | None
    research_record: str
    state: str


def _fail(message: str) -> Never:
    raise AlgorithmLifecycleError(message)


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(f"{context} must be a table")
    raw = cast("dict[object, object]", value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            _fail(f"{context} contains a non-string key")
        result[key] = item
    return result


def _table(document: dict[str, object], name: str) -> dict[str, object]:
    if name not in document:
        _fail(f"lifecycle.{name} table is required")
    return _mapping(document[name], f"lifecycle.{name}")


def _optional_table(
    document: dict[str, object],
    name: str,
) -> dict[str, object] | None:
    if name not in document:
        return None
    return _mapping(document[name], f"lifecycle.{name}")


def _string(table: dict[str, object], name: str, context: str) -> str:
    value = table.get(name)
    if type(value) is not str or not value:
        _fail(f"{context}.{name} must be a non-empty string")
    return value


def _optional_string(
    table: dict[str, object],
    name: str,
    context: str,
) -> str | None:
    value = table.get(name)
    if value is None:
        return None
    if type(value) is not str or not value:
        _fail(f"{context}.{name} must be a non-empty string when present")
    return value


def _relative_path(value: str, context: str) -> str:
    path = Path(value)
    if path.is_absolute() or PARENT_SEGMENT in path.parts:
        _fail(f"{context} must be repository-relative: {value}")
    return path.as_posix()


def _evidence_path(table: dict[str, object], name: str, context: str) -> str:
    return _relative_path(_string(table, name, context), f"{context}.{name}")


def _parse_date(table: dict[str, object], name: str, context: str) -> date:
    value = table.get(name)
    if isinstance(value, date):
        return value
    _fail(f"{context}.{name} must be a TOML local date")


def _parse_document(text: str) -> dict[str, object]:
    try:
        parsed = cast("object", tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        _fail(f"invalid TOML: {error}")
    document = _mapping(parsed, "lifecycle")
    version = document.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        _fail(f"unsupported algorithm lifecycle schema: {version}")
    return document


def _promotion(
    document: dict[str, object],
    state: str,
) -> PromotionEvidence | None:
    table = _optional_table(document, "promotion")
    if state not in PROMOTION_STATES:
        if table is not None:
            _fail(
                f"lifecycle state {state} must not contain promotion evidence"
            )
        return None
    if table is None:
        _fail(f"lifecycle state {state} requires promotion evidence")
    values = {
        field: _evidence_path(table, field, "lifecycle.promotion")
        for field in PROMOTION_FIELDS
    }
    return PromotionEvidence(
        correctness=values["correctness"],
        maintainability=values["maintainability"],
        measured_benefit=values["measured_benefit"],
        portability=values["portability"],
        reproducibility=values["reproducibility"],
    )


def _decision_optional_paths(
    table: dict[str, object],
) -> tuple[str | None, str | None]:
    negative_results = _optional_string(
        table,
        "negative_results",
        "lifecycle.decision",
    )
    superseded_by = _optional_string(
        table,
        "superseded_by",
        "lifecycle.decision",
    )
    if negative_results is not None:
        negative_results = _relative_path(
            negative_results,
            "lifecycle.decision.negative_results",
        )
    return (negative_results, superseded_by)


def _validate_decision_state(
    state: str,
    negative_results: str | None,
    superseded_by: str | None,
) -> None:
    if state == REJECTED and negative_results is None:
        _fail("rejected lifecycle state requires retained negative_results")
    if state == RETIRED and superseded_by is None:
        _fail("retired lifecycle state requires superseded_by")
    if state != RETIRED and superseded_by is not None:
        _fail("superseded_by is valid only for retired lifecycle state")


def _decision(
    document: dict[str, object],
    state: str,
) -> LifecycleDecision | None:
    table = _optional_table(document, "decision")
    if state not in DECISION_STATES:
        if table is not None:
            _fail(f"lifecycle state {state} must not contain a decision table")
        return None
    if table is None:
        _fail(f"lifecycle state {state} requires a decision table")
    negative_results, superseded_by = _decision_optional_paths(table)
    _validate_decision_state(state, negative_results, superseded_by)
    return LifecycleDecision(
        decided_on=_parse_date(table, "decided_on", "lifecycle.decision"),
        evidence=_evidence_path(table, "evidence", "lifecycle.decision"),
        negative_results=negative_results,
        reason=_string(table, "reason", "lifecycle.decision"),
        superseded_by=superseded_by,
    )


def parse_lifecycle(text: str) -> AlgorithmLifecycle:
    """Parse and validate one static research-algorithm lifecycle record.

    Returns:
        Immutable lifecycle state with state-specific evidence obligations.

    """
    document = _parse_document(text)
    algorithm = _table(document, "algorithm")
    state = _string(algorithm, "state", "lifecycle.algorithm")
    if state not in STATES:
        _fail(f"unsupported algorithm lifecycle state: {state}")
    return AlgorithmLifecycle(
        experiment_manifest=_relative_path(
            _string(algorithm, "experiment_manifest", "lifecycle.algorithm"),
            "lifecycle.algorithm.experiment_manifest",
        ),
        identifier=_string(algorithm, "id", "lifecycle.algorithm"),
        promotion=_promotion(document, state),
        decision=_decision(document, state),
        research_record=_relative_path(
            _string(algorithm, "research_record", "lifecycle.algorithm"),
            "lifecycle.algorithm.research_record",
        ),
        state=state,
    )


def _require_existing(relative: str, context: str) -> None:
    path = ROOT / relative
    if not path.is_file():
        _fail(f"{context} evidence path does not exist: {relative}")


def _validate_evidence_paths(record: AlgorithmLifecycle) -> None:
    _require_existing(record.experiment_manifest, "experiment manifest")
    _require_existing(record.research_record, "research record")
    if record.promotion is not None:
        promotion_paths = (
            ("correctness", record.promotion.correctness),
            ("reproducibility", record.promotion.reproducibility),
            ("maintainability", record.promotion.maintainability),
            ("portability", record.promotion.portability),
            ("measured_benefit", record.promotion.measured_benefit),
        )
        for field, evidence in promotion_paths:
            _require_existing(evidence, f"promotion {field}")
    if record.decision is not None:
        _require_existing(record.decision.evidence, "decision")
        if record.decision.negative_results is not None:
            _require_existing(
                record.decision.negative_results, "negative results"
            )


def validate_repository_lifecycle(path: Path) -> AlgorithmLifecycle:
    """Validate one checked-in lifecycle record against mirror identity.

    Returns:
        Parsed lifecycle after repository identity/evidence checks.

    """
    if not path.is_file():
        _fail(f"algorithm lifecycle manifest not found: {path}")
    record = parse_lifecycle(path.read_text(encoding="utf-8"))
    algorithm_id = path.parent.name
    if record.identifier != algorithm_id:
        message = (
            "lifecycle algorithm ID does not match directory: "
            f"{record.identifier} != {algorithm_id}"
        )
        _fail(message)
    expected_experiment = f"algorithms/{algorithm_id}/experiment.toml"
    expected_research = f"docs/research/algorithms/{algorithm_id}/research.md"
    if record.experiment_manifest != expected_experiment:
        _fail("lifecycle experiment manifest does not match mirror identity")
    if record.research_record != expected_research:
        _fail("lifecycle research record does not match mirror identity")
    _validate_evidence_paths(record)
    return record


def validate_repository() -> tuple[AlgorithmLifecycle, ...]:
    """Validate lifecycle metadata for every research mirror experiment.

    Returns:
        Lifecycle records in stable algorithm-ID order.

    """
    records: list[AlgorithmLifecycle] = []
    for directory in sorted(ALGORITHMS_ROOT.iterdir()):
        experiment = directory / "experiment.toml"
        if not experiment.is_file():
            continue
        lifecycle = directory / "lifecycle.toml"
        records.append(validate_repository_lifecycle(lifecycle))
    if not records:
        _fail("repository contains no algorithm lifecycle records")
    return tuple(records)


def main() -> int:
    """Validate repository algorithm lifecycle records and return status.

    Returns:
        Zero for valid lifecycle metadata and one for policy failure.

    """
    try:
        records = validate_repository()
    except (AlgorithmLifecycleError, OSError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    states: dict[str, int] = {}
    for record in records:
        states[record.state] = states.get(record.state, 0) + 1
    summary = ", ".join(f"{key}={states[key]}" for key in sorted(states))
    _ = sys.stdout.write(
        f"algorithm lifecycle valid: {len(records)} ({summary})\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
