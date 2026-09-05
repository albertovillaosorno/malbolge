# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Canonical compact TODO priority-index evidence.
# - Must-Not:
#   - Duplicate typed metadata or accept completed work as active planning.
# - Allows:
#   - Inputs: `TODO.md` and typed TODO records.
#   - Outputs: exact group, status/title order, summary, and link assertions.
#   - Side effects: repository reads only.
# - Split-When:
#   - Planning surfaces acquire an independent machine-readable schema.
# - Merge-When:
#   - Jig directly validates compact priority-grouped TODO content.
# - Summary:
#   - Prevents the TODO index from duplicating or drifting from its authorities.
# - Description:
#   - Enforces P0-P5 grouping and compact title/summary/link blocks.
# - Usage:
#   - Runs with the repository Python test suite.
# - Defaults:
#   - Open records are indexed; completed records are excluded.
#

"""Compact priority-grouped TODO index regressions."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = ROOT / "TODO.md"
OPEN_ROOT = ROOT / "docs/todo/open"
COMPLETED_ROOT = ROOT / "docs/todo/completed"
ACTIVE_STATUS = "active"
EXPECTED_TODO_COUNT = 50
MAX_SUMMARY_SENTENCES = 4
TODO_TARGET_PATTERN = r"docs/todo/open/.+?\.mdc"
MIGRATED_ROOT_DETAIL = "**Migrated root planning detail.**"
FORBIDDEN_SUMMARY_MARKERS = (
    "**Synthesis:**",
    "**Full TODO:**",
    "priority lane",
)
P_GROUPS = (
    ("P0", "Authority and governance", range(1, 5)),
    ("P1", "Semantic and language foundations", range(5, 8)),
    ("P2", "Compiler, runtime, and accelerator core", range(8, 11)),
    ("P3", "Optimization, proof, and reusable scale", range(11, 14)),
    ("P4", "Applications, evidence, and self-hosting", range(14, 17)),
    ("P5", "Documentation and publication", range(17, 19)),
)
AREA_ORDER = {
    name: index
    for index, name in enumerate(
        (
            "foundation",
            "documentation",
            "compatibility",
            "vm",
            "verification",
            "mathematics",
            "c",
            "compiler",
            "accelerator",
            "tools",
            "applications",
            "research",
            "self_hosting",
        )
    )
}
LINK_TARGET = re.compile(
    rf"^\[({TODO_TARGET_PATTERN})\]\(({TODO_TARGET_PATTERN})\)$"
)
SENTENCE = re.compile(r"[^.!?]+[.!?]")


@dataclass(frozen=True)
class PlanningRecord:
    """One open typed TODO's canonical index identity."""

    identifier: str
    lane: int
    status_order: int
    area_order: int
    title: str
    path: str
    dependencies: tuple[str, ...]
    summary: str


@dataclass
class ParsedSection:
    """One parsed P section and its ordered TODO records."""

    identifier: str
    title: str
    records: list[PlanningRecord] = field(default_factory=list)


def _front_matter(text: str, field_name: str) -> str:
    match = re.search(
        rf'^\s*{field_name}:\s*"?([^"\n]+)',
        text,
        re.MULTILINE,
    )
    assert match is not None, f"missing {field_name}"
    return match.group(1).strip()


def _dependencies(text: str) -> tuple[str, ...]:
    match = re.search(
        r"^depends_on:\s*\n(.*?)(?=^[a-z_]+:|^---$)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return ()
    return tuple(
        re.findall(
            r'^\s*-\s*"([^"]+)"',
            match.group(1),
            re.MULTILINE,
        )
    )


def _summary(text: str) -> str:
    match = re.search(
        r"^## Objective\s*$\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, "missing Objective"
    objective = " ".join(match.group(1).split())
    sentence = re.match(r"(.+?[.!?])(?:\s|$)", objective)
    summary = sentence.group(1) if sentence is not None else objective
    return summary.replace("Malbolge- specific", "Malbolge-specific")


def _record_from_typed_todo(path: Path) -> PlanningRecord:
    text = path.read_text(encoding="utf-8")
    task = _front_matter(text, "task")
    assert task.startswith("TODO - ")
    status = _front_matter(text, "status")
    assert status in {ACTIVE_STATUS, "pending"}
    area = _front_matter(text, "area")
    return PlanningRecord(
        identifier=_front_matter(text, "id"),
        lane=int(_front_matter(text, "lane")),
        status_order=0 if status == ACTIVE_STATUS else 1,
        area_order=AREA_ORDER.get(area, 99),
        title=task.removeprefix("TODO - "),
        path=path.relative_to(ROOT).as_posix(),
        dependencies=_dependencies(text),
        summary=_summary(text),
    )


def _open_records() -> tuple[PlanningRecord, ...]:
    return tuple(
        _record_from_typed_todo(path)
        for path in OPEN_ROOT.rglob("*.mdc")
    )


def _priority_key(
    record: PlanningRecord,
) -> tuple[int, str, str]:
    return (
        record.status_order,
        record.title.casefold(),
        record.identifier,
    )


def _completed_titles() -> frozenset[str]:
    return frozenset(
        _front_matter(path.read_text(encoding="utf-8"), "task")
        for path in COMPLETED_ROOT.rglob("*.mdc")
    )


def _parse_link(line: str) -> PlanningRecord:
    match = LINK_TARGET.fullmatch(line)
    assert match is not None
    visible_path = match.group(1)
    target_path = match.group(2)
    assert visible_path == target_path
    assert (ROOT / target_path).is_file()
    return _record_from_typed_todo(ROOT / target_path)


def _parse_todo_entry(
    lines: list[str],
    index: int,
) -> tuple[int, PlanningRecord]:
    title = lines[index].removeprefix("### TODO - ")
    assert not lines[index + 1]
    index += 2
    summary_lines: list[str] = []
    while index < len(lines) and lines[index]:
        summary_lines.append(lines[index])
        index += 1
    assert summary_lines
    summary = " ".join(summary_lines)
    assert index + 1 < len(lines)
    link_index = index + 1
    if lines[link_index].startswith(
        "<!-- MarkdownLint-disable-next-line MD013 MD044 -->"
    ):
        link_index += 1
    record = _parse_link(lines[link_index])
    assert title == record.title
    assert summary == record.summary
    assert not any(marker in summary for marker in FORBIDDEN_SUMMARY_MARKERS)
    assert not summary.startswith(("Active,", "Pending,"))
    sentences = tuple(SENTENCE.findall(summary))
    assert 1 <= len(sentences) <= MAX_SUMMARY_SENTENCES
    return link_index + 1, record


def _parse_sections(text: str) -> tuple[ParsedSection, ...]:
    lines = text.splitlines()
    sections: list[ParsedSection] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("## P"):
            identifier, title = line.removeprefix("## ").split(" — ", 1)
            sections.append(ParsedSection(identifier=identifier, title=title))
            index += 1
            continue
        if line.startswith("### TODO - "):
            assert sections, "TODO entry appears before its priority section"
            index, record = _parse_todo_entry(lines, index)
            sections[-1].records.append(record)
            continue
        index += 1
    return tuple(sections)


def _assert_section_headers(sections: tuple[ParsedSection, ...]) -> None:
    actual = tuple((section.identifier, section.title) for section in sections)
    expected = tuple(
        (identifier, title) for identifier, title, _lanes in P_GROUPS
    )
    assert actual == expected


def _expected_section_records(
    lanes: range,
    open_records: tuple[PlanningRecord, ...],
) -> tuple[PlanningRecord, ...]:
    return tuple(
        sorted(
            (record for record in open_records if record.lane in lanes),
            key=_priority_key,
        )
    )


def _assert_record_identity(records: list[PlanningRecord]) -> None:
    assert len(records) == EXPECTED_TODO_COUNT
    identifiers = {record.identifier for record in records}
    assert len(identifiers) == EXPECTED_TODO_COUNT
    completed_titles = _completed_titles()
    actual_titles = {f"TODO - {record.title}" for record in records}
    assert not actual_titles.intersection(completed_titles)


def test_todo_index_is_priority_grouped_compact_and_complete() -> None:
    """Every open TODO has one compact block in heuristic priority order."""
    sections = _parse_sections(TODO_PATH.read_text(encoding="utf-8"))
    _assert_section_headers(sections)
    open_records = _open_records()
    actual_records: list[PlanningRecord] = []
    for section, group in zip(sections, P_GROUPS, strict=True):
        expected = _expected_section_records(
            group[2],
            open_records,
        )
        assert tuple(section.records) == expected
        actual_records.extend(section.records)
    _assert_record_identity(actual_records)


def test_open_records_do_not_retain_migrated_root_detail() -> None:
    """Typed planning no longer duplicates the former expanded root index."""
    for path in OPEN_ROOT.rglob("*.mdc"):
        text = path.read_text(encoding="utf-8")
        assert MIGRATED_ROOT_DETAIL not in text
