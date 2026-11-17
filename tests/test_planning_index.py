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
#   - Canonical compact TODO priority-index evidence.
# - Must-Not:
#   - Duplicate typed metadata or accept completed work as active planning.
# - Allows:
#   - Inputs: `TODO.md` and typed TODO records.
#   - Outputs: exact phase, dependency order, summary, and links.
#   - Side effects: repository reads only.
# - Split-When:
#   - Planning surfaces acquire an independent machine-readable schema.
# - Merge-When:
#   - Jig directly validates compact priority-grouped TODO content.
# - Summary:
#   - Prevents the TODO index from duplicating or drifting from its authorities.
# - Description:
#   - Enforces P2-P10 delivery phases and compact title/summary/link blocks.
# - Usage:
#   - Runs with the repository Python test suite.
# - Defaults:
#   - Open records are indexed; completed records are excluded.
#

"""Dependency-ordered P2-P10 TODO index regressions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = ROOT / "TODO.md"
OPEN_ROOT = ROOT / "docs/todo/open"
COMPLETED_ROOT = ROOT / "docs/todo/completed"
ACTIVE_STATUS = "active"
MAX_SUMMARY_SENTENCES = 4
TODO_TARGET_PATTERN = r"docs/todo/open/.+?\.mdc"
MIGRATED_ROOT_DETAIL = "**Migrated root planning detail.**"
FORBIDDEN_SUMMARY_MARKERS = (
    "**Synthesis:**",
    "**Full TODO:**",
    "priority lane",
)
P_GROUPS = (
    ("P2", "Execute real stateful C"),
    ("P3", "Complete supported C I/O semantics"),
    ("P4", "Verify, link, and inspect generated programs"),
    ("P5", "Ship the CPU-first compiler"),
    ("P6", "Scale compilation with verified reuse"),
    ("P7", "Native execution and turnkey packaging"),
    ("P8", "Accelerators and large-program validation"),
    ("P9", "Self-hosting, machine runners and final evidence"),
    ("P10", "Final comprehensive paper"),
)
EARLIEST_BLOCKER = "parametric-guest-byte-stream-emission"
FIRST_RELEASE = "cpu-first-c-to-malbolge-release"

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
LINK_TARGET = re.compile(rf"^\[({TODO_TARGET_PATTERN})\]\(({TODO_TARGET_PATTERN})\)$")
SENTENCE = re.compile(r"[^.!?]+[.!?]")


@dataclass(frozen=True)
class PlanningRecord:
    """One open typed TODO's canonical index identity."""

    identifier: str
    lane: int
    priority: str
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
        priority=_front_matter(text, "priority"),
        status_order=0 if status == ACTIVE_STATUS else 1,
        area_order=AREA_ORDER.get(area, 99),
        title=task.removeprefix("TODO - "),
        path=path.relative_to(ROOT).as_posix(),
        dependencies=_dependencies(text),
        summary=_summary(text),
    )


def _open_records() -> tuple[PlanningRecord, ...]:
    return tuple(_record_from_typed_todo(path) for path in OPEN_ROOT.rglob("*.mdc"))


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
    expected = tuple((identifier, title) for identifier, title in P_GROUPS)
    assert actual == expected


def _expected_section_records(
    priority: str,
    open_records: tuple[PlanningRecord, ...],
) -> frozenset[PlanningRecord]:
    return frozenset(record for record in open_records if record.priority == priority)


def _assert_record_identity(
    records: list[PlanningRecord],
    open_records: tuple[PlanningRecord, ...],
) -> None:
    assert len(records) == len(open_records)
    identifiers = {record.identifier for record in records}
    assert len(identifiers) == len(open_records)
    completed_titles = _completed_titles()
    actual_titles = {f"TODO - {record.title}" for record in records}
    assert not actual_titles.intersection(completed_titles)


def test_todo_index_is_priority_grouped_compact_and_complete() -> None:
    """Every open TODO has exactly one block in the correct delivery phase."""
    sections = _parse_sections(TODO_PATH.read_text(encoding="utf-8"))
    _assert_section_headers(sections)
    open_records = _open_records()
    actual_records: list[PlanningRecord] = []
    for section, group in zip(sections, P_GROUPS, strict=True):
        expected = _expected_section_records(group[0].lower(), open_records)
        assert frozenset(section.records) == expected
        actual_records.extend(section.records)
    _assert_record_identity(actual_records, open_records)
    assert sections[0].records[0].identifier == EARLIEST_BLOCKER
    assert [item.identifier for item in sections[3].records] == [FIRST_RELEASE]


def test_phase_dependencies_do_not_point_backward_or_hide_open_work() -> None:
    """A phase never depends on later work, including within a phase."""
    sections = _parse_sections(TODO_PATH.read_text(encoding="utf-8"))
    records = _open_records()
    by_id = {record.identifier: record for record in records}
    order = {
        record.identifier: (int(section.identifier[1:]), index)
        for section in sections
        for index, record in enumerate(section.records)
    }
    for record in records:
        priority_number = int(record.priority.removeprefix("p"))
        assert 2 <= priority_number <= 10
        assert record.lane == priority_number
        for predecessor in record.dependencies:
            if predecessor not in by_id:
                # Completed predecessors retain their historical priorities.
                continue
            dependency_phase, dependency_index = order[predecessor]
            record_phase, record_index = order[record.identifier]
            assert (dependency_phase, dependency_index) < (
                record_phase,
                record_index,
            ), f"{record.identifier} scheduled before {predecessor}"


def test_phase_task_dependencies_and_contracts_are_resolvable() -> None:
    """All current typed TODOs point to real governing files and task IDs."""
    records = tuple(OPEN_ROOT.rglob("*.mdc"))
    completed = tuple(COMPLETED_ROOT.rglob("*.mdc"))
    identifiers = {
        _front_matter(path.read_text(encoding="utf-8"), "id")
        for path in (*records, *completed)
    }
    assert len(identifiers) == len(records) + len(completed)
    for path in records:
        contents = path.read_text(encoding="utf-8")
        contract = _front_matter(contents, "contract")
        assert (ROOT / contract).is_file(), path
        for dependency in _dependencies(contents):
            assert dependency in identifiers, (path, dependency)


def test_unapproved_gpu_adapter_has_no_active_reservation() -> None:
    """Removed scope must not return as a placeholder or future commitment."""
    reserved = "rocm-accelerator-adapter"
    assert not (OPEN_ROOT / "accelerator" / f"{reserved}.mdc").exists()
    assert not (
        ROOT / "docs/technical/integrations/accelerators" / f"{reserved}.md"
    ).exists()
    for document in (
        TODO_PATH,
        ROOT / "docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md",
        ROOT / "docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md",
    ):
        contents = document.read_text(encoding="utf-8")
        assert "rocm" not in contents.lower(), document
    assert all(reserved not in path.name for path in OPEN_ROOT.rglob("*.mdc"))


def test_single_todo_owns_phase_gates_and_final_paper() -> None:
    """One TODO document owns P2-P10 and ends with one comprehensive paper."""
    index = TODO_PATH.read_text(encoding="utf-8")
    assert not (ROOT / "docs/todo/ROADMAP.md").exists()
    assert "## Delivery phase gates" in index
    assert "P5 CPU-only release" in index
    assert "**Current execution queue:**" in index
    assert "CPU" in index and "CUDA" in index
    for phase, _ in P_GROUPS:
        assert index.count(f"- **{phase} — ") == 1
    sections = _parse_sections(index)
    final_section = sections[-1]
    assert final_section.identifier == "P10"
    assert len(final_section.records) == 1
    assert final_section.records[0].identifier == (
        "malbolge-machine-model-and-c-compilation-paper"
    )
    assert index.rstrip().endswith(
        "[docs/todo/open/research/malbolge-machine-model-and-c-compilation-paper.mdc]"
        "(docs/todo/open/research/malbolge-machine-model-and-c-compilation-paper.mdc)"
    )
    assert (ROOT / "docs/todo/open/compiler" / f"{FIRST_RELEASE}.mdc").is_file()


def test_removed_studies_and_completed_diff_are_not_open() -> None:
    """Scope deletions do not become an archive or a false open task."""
    removed = (
        "hexagonal-authoring-layout-experiment",
        "human-scale-malbolge-search-study",
        "effective-transcendental-separation-paper",
        "publication-grade-paper-pipeline",
    )
    assert not (ROOT / "docs/todo/withdrawn").exists()
    ids = {record.identifier for record in _open_records()}
    for identity in removed:
        assert identity not in ids
    assert "source-bound-diff-generator" not in ids
    path = COMPLETED_ROOT / "tools/source-bound-diff-generator.mdc"
    assert path.is_file()
    assert _front_matter(path.read_text(encoding="utf-8"), "status") == "completed"


def test_open_records_do_not_retain_migrated_root_detail() -> None:
    """Typed planning no longer duplicates the former expanded root index."""
    for path in OPEN_ROOT.rglob("*.mdc"):
        text = path.read_text(encoding="utf-8")
        assert MIGRATED_ROOT_DETAIL not in text


def test_accelerator_reuses_cpu_contract_and_requires_real_speedup() -> None:
    """GPU-compatible CPU design must precede optional large-scale CUDA work."""
    cpu = (OPEN_ROOT / "accelerator/deterministic-cpu-optimizer.mdc").read_text(
        encoding="utf-8"
    )
    cuda = (OPEN_ROOT / "accelerator/cuda-superoptimizer.mdc").read_text(
        encoding="utf-8"
    )
    port = (
        ROOT / "docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md"
    ).read_text(encoding="utf-8")
    cuda_contract = (
        ROOT / "docs/technical/integrations/accelerators/cuda-superoptimizer.md"
    ).read_text(encoding="utf-8")
    roadmap = TODO_PATH.read_text(encoding="utf-8")
    assert "versioned hardware-neutral" in cpu
    assert "bounded" in cpu and "CUDA" in cpu
    assert "GPU-projectable" in port
    assert ">= 1.25x" in cuda
    assert "1.25x" in cuda_contract
    assert "paired" in cuda and "end-to-end" in cuda
    assert "CUDA acceleration is" in roadmap
    assert "stochastic-and-guided-search" not in _dependencies(cuda)


def test_optional_infrastructure_cannot_block_baseline_milestones() -> None:
    """Optional research, residency and DOOM do not gate CPU deliverables."""
    dependency_edges = (
        (
            "accelerator/compilation-latency-performance-budget.mdc",
            ("resident-incremental-compiler-and-wal",),
        ),
        (
            "applications/real-program-benchmark-suite.mdc",
            ("doom-playable-generated-code-performance",),
        ),
        (
            "compiler/turnkey-c-to-malbolge-toolchain.mdc",
            (
                "cross-platform-native-capability-runners",
                "cuda-linux-runtime-and-hermetic-toolchain",
            ),
        ),
    )
    for name, prohibited in dependency_edges:
        text = (OPEN_ROOT / name).read_text(encoding="utf-8")
        assert not set(_dependencies(text)).intersection(prohibited), name
    latency = (
        OPEN_ROOT / "accelerator/compilation-latency-performance-budget.mdc"
    ).read_text(encoding="utf-8")
    assert "CPU cold-build budget first" in latency
    assert "N/A" in latency


def test_backend_identity_and_proof_scopes_are_not_universalized() -> None:
    """Only fixed replay promises byte identity; proofs have stated bounds."""
    artifacts = (
        OPEN_ROOT / "applications/deterministic-cross-backend-artifact-hashing.mdc"
    ).read_text(encoding="utf-8")
    resume = (
        OPEN_ROOT / "compiler/resumable-compilation-progress-sidecars.mdc"
    ).read_text(encoding="utf-8")
    verifier = (OPEN_ROOT / "verification/translation-validation.mdc").read_text(
        encoding="utf-8"
    )
    artifact_contract = (
        ROOT / "docs/technical/contracts/deterministic-artifact-hashing.md"
    ).read_text(encoding="utf-8")
    assert "Different valid optimizers" in artifacts
    assert "Different valid CPU/CUDA" in artifact_contract
    assert "backend-specific opaque search state" in resume
    assert "uninterrupted run" in resume
    assert "unsupported, resource-unbounded or unproved" in verifier
    assert "fail" in verifier


def test_large_applications_and_single_paper_have_bounded_acceptance() -> None:
    """DOOM/ISA demos and the publication retain a finite evidence boundary."""
    doom = (
        OPEN_ROOT / "applications/doom-playable-generated-code-performance.mdc"
    ).read_text(encoding="utf-8")
    apollo = (
        OPEN_ROOT / "applications/apollo-11-luminary-agc-malbolge-demonstration.mdc"
    ).read_text(encoding="utf-8")
    rv32i = (OPEN_ROOT / "applications/rv32i-malbolge-runner.mdc").read_text(
        encoding="utf-8"
    )
    paper = (
        OPEN_ROOT / "research/malbolge-machine-model-and-c-compilation-paper.mdc"
    ).read_text(encoding="utf-8")
    assert "60-second" in doom and "p95" in doom
    assert "`doom.c`" in doom and "generated guest" in doom
    assert "one existing AGC interpreter C file" in apollo
    assert "Only `rv32i_runner.c`" in rv32i
    assert "Privileged ISA" in rv32i
    assert "sole P10 manuscript" in paper
    assert "negative DOOM latency measurements" in paper
