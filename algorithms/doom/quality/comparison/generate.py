# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Generate the compact DOOM before/after quality comparison report."""

from __future__ import annotations

import argparse
from collections import Counter
import concurrent.futures
import dataclasses
from functools import partial
import hashlib
import json
from pathlib import Path
import re
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed repo-local executables; no shell.
import sys
from typing import Never

SCRIPT = Path(__file__).resolve()
COMPARISON_ROOT = SCRIPT.parent
QUALITY_ROOT = COMPARISON_ROOT.parent
REPO_ROOT = QUALITY_ROOT.parents[2]
LLVM_BIN = REPO_ROOT / ".dependencies" / "llvm" / "22.1.8" / "bin"
CLANG = LLVM_BIN / "clang.exe"
CLANG_TIDY = LLVM_BIN / "clang-tidy.exe"
CLANG_FORMAT = LLVM_BIN / "clang-format.exe"
ROOT_TIDY = REPO_ROOT / ".clang-tidy"
ROOT_FORMAT = REPO_ROOT / ".clang-format"
ALPINE_ROOT = REPO_ROOT / ".dependencies" / "sysroots" / "alpine" / "3.24.1"
DEFAULT_BEFORE = REPO_ROOT / "doom"
DEFAULT_AFTER = QUALITY_ROOT / "in" / "doom"
DEFAULT_TEX = COMPARISON_ROOT / "report.tex"
DEFAULT_JSON = COMPARISON_ROOT / "metrics.json"

SOURCE_EXTENSIONS = {".c", ".h", ".hh", ".hpp", ".hxx"}
C_EXTENSIONS = {".c"}
HEADER_EXTENSIONS = SOURCE_EXTENSIONS - C_EXTENSIONS
ASSET_EXTENSIONS = {".wad"}
TEXT_EXTENSIONS = SOURCE_EXTENSIONS | {".md", ".rst", ".txt"}
C_SUFFIX = ".c"
MAX_LINE_LENGTH = 80
CARRIAGE_RETURN = b"\r"
CARRIAGE_RETURN_ENDINGS = (b"\r\n", b"\r")
TAB = "\t"
WINDOWS_MARKERS = ("_WIN32", "WIN32")
MACOS_MARKERS = ("__APPLE__", "__MACH__")
BORDERLESS_MARKER = "borderless"
FORMAT_RULE = "clang-format"
COMPILER_RULE = "compiler-diagnostic"
RULE_PREFIX_FAMILIES = (
    (("text/",), "text"),
    (("readability-",), "readability"),
    (("bugprone-",), "bugprone"),
    (("clang-analyzer-",), "analyzer"),
    (("modernize-",), "modernize"),
    (("misc-",), "misc"),
    (("performance-",), "performance"),
    (("portability-",), "portability"),
    (("hicpp-",), "hicpp"),
)

TARGETS = {
    "clang-linux-x86_64": (
        "x86_64-alpine-linux-musl",
        ALPINE_ROOT / "x86_64",
    ),
    "clang-linux-arm64": (
        "aarch64-alpine-linux-musl",
        ALPINE_ROOT / "aarch64",
    ),
}

WARNING_FLAGS = [
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wshadow",
    "-Wconversion",
    "-Wsign-conversion",
    "-Wdouble-promotion",
    "-Wfloat-equal",
    "-Wformat=2",
    "-Wundef",
    "-Wcast-qual",
    "-Wcast-align",
    "-Wswitch-enum",
    "-Wswitch-default",
    "-Wvla",
    "-Wimplicit-fallthrough",
    "-Wstrict-prototypes",
    "-Wmissing-prototypes",
    "-Wmissing-variable-declarations",
    "-Wnull-dereference",
]

DIAGNOSTIC_PREFIX = r"^(.+?):(\d+):(\d+): (warning|error|fatal error): "
DIAGNOSTIC_SUFFIX = r"(.*?)(?: \[([^\]]+)\])?$"
DIAGNOSTIC_RE = re.compile(f"{DIAGNOSTIC_PREFIX}{DIAGNOSTIC_SUFFIX}")
FORMAT_RE = re.compile(
    r"^(.+?):(\d+):(\d+): error: code should be clang-formatted"
)


@dataclasses.dataclass(frozen=True, slots=True)
class _Finding:
    gate: str
    path: str
    line: int
    column: int
    rule: str
    message: str

    def key(self) -> tuple[object, ...]:
        rule = self.rule
        if rule.startswith("clang-diagnostic-"):
            rule = "clang-diagnostic"
        return (
            self.path.lower(),
            self.line,
            self.column,
            rule,
            self.message,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class _CorpusMetrics:
    files: int
    c_files: int
    headers: int
    source_bytes: int
    physical_source_lines: int
    nonblank_source_lines: int
    asset_files: int
    asset_bytes: int
    asset_sha256: str
    source_sha256: str


@dataclasses.dataclass(frozen=True, slots=True)
class _ValidationMetrics:
    raw_findings: int
    unique_findings: int
    by_gate: dict[str, int]
    by_rule_family: dict[str, int]


@dataclasses.dataclass(frozen=True, slots=True)
class _Comparison:
    before_root: Path
    after_root: Path
    before_corpus: _CorpusMetrics
    after_corpus: _CorpusMetrics
    before_validation: _ValidationMetrics
    after_validation: _ValidationMetrics


@dataclasses.dataclass(frozen=True, slots=True)
class _CompilerJob:
    gate: str
    path: Path


@dataclasses.dataclass(frozen=True, slots=True)
class _TexMetrics:
    latex: str
    row_end: str
    before_density: float
    after_density: float
    unique_reduction: str
    raw_reduction: str
    density_reduction: str
    before_path: str
    after_path: str


class _Arguments(argparse.Namespace):
    before: Path
    after: Path
    tex: Path
    json: Path

    def __init__(self) -> None:
        super().__init__()
        self.before = DEFAULT_BEFORE
        self.after = DEFAULT_AFTER
        self.tex = DEFAULT_TEX
        self.json = DEFAULT_JSON


class _ComparisonError(RuntimeError):
    """Deterministic comparison configuration or stability failure."""


def _fail(message: str) -> Never:
    raise _ComparisonError(message)


def _run(
    args: list[str],
    cwd: Path = REPO_ROOT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed repository tool argv.
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        shell=False,
    )


def _source_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS
    )


def _text_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS
    )


def _encoding_result(
    data: bytes,
    relative: str,
) -> tuple[str | None, list[_Finding]]:
    try:
        return data.decode("utf-8"), []
    except UnicodeDecodeError as error:
        finding = _Finding(
            gate="editorconfig",
            path=relative,
            line=0,
            column=error.start + 1,
            rule="text/encoding",
            message="file is not valid UTF-8",
        )
        return None, [finding]


def _line_ending_findings(data: bytes, relative: str) -> list[_Finding]:
    if CARRIAGE_RETURN not in data:
        return []
    findings: list[_Finding] = []
    for row, raw_line in enumerate(data.splitlines(keepends=True), 1):
        if raw_line.endswith(CARRIAGE_RETURN_ENDINGS):
            findings.append(
                _Finding(
                    gate="editorconfig",
                    path=relative,
                    line=row,
                    column=max(1, len(raw_line)),
                    rule="text/line-ending",
                    message="line ending must be LF",
                )
            )
    return findings


def _source_line_findings(
    path: Path,
    relative: str,
    *,
    row: int,
    line: str,
) -> list[_Finding]:
    findings: list[_Finding] = []
    stripped = line.rstrip(" \t")
    if stripped != line:
        findings.append(
            _Finding(
                gate="editorconfig",
                path=relative,
                line=row,
                column=len(stripped) + 1,
                rule="text/trailing-whitespace",
                message="trailing whitespace is not allowed",
            )
        )
    if len(line) > MAX_LINE_LENGTH:
        findings.append(
            _Finding(
                gate="editorconfig",
                path=relative,
                line=row,
                column=MAX_LINE_LENGTH + 1,
                rule="text/line-length",
                message="line exceeds 80 columns",
            )
        )
    leading = line[: len(line) - len(line.lstrip(" \t"))]
    if TAB in leading and path.suffix.lower() in SOURCE_EXTENSIONS:
        findings.append(
            _Finding(
                gate="editorconfig",
                path=relative,
                line=row,
                column=leading.index(TAB) + 1,
                rule="text/indentation",
                message="source indentation must use spaces",
            )
        )
    return findings


def _text_line_findings(
    path: Path,
    relative: str,
    text: str,
) -> list[_Finding]:
    findings: list[_Finding] = []
    for row, line in enumerate(text.splitlines(), 1):
        findings.extend(
            _source_line_findings(path, relative, row=row, line=line)
        )
    return findings


def _final_newline_finding(
    data: bytes,
    relative: str,
    text: str,
) -> list[_Finding]:
    if not data or data.endswith(b"\n"):
        return []
    lines = text.splitlines()
    line = max(1, len(lines))
    column = max(1, len(lines[-1]) + 1 if lines else 1)
    return [
        _Finding(
            gate="editorconfig",
            path=relative,
            line=line,
            column=column,
            rule="text/final-newline",
            message="file must end with a newline",
        )
    ]


def _text_file_findings(path: Path, root: Path) -> list[_Finding]:
    relative = path.relative_to(root).as_posix()
    data = path.read_bytes()
    text, findings = _encoding_result(data, relative)
    if text is None:
        return findings
    findings.extend(_line_ending_findings(data, relative))
    findings.extend(_text_line_findings(path, relative, text))
    findings.extend(_final_newline_finding(data, relative, text))
    return findings


def _text_findings(root: Path) -> list[_Finding]:
    findings: list[_Finding] = []
    for path in _text_files(root):
        findings.extend(_text_file_findings(path, root))
    return findings


def _tree_hash(paths: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "little"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "little"))
        digest.update(data)
    return digest.hexdigest()


def _corpus_metrics(root: Path) -> _CorpusMetrics:
    sources = _source_files(root)
    assets = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in ASSET_EXTENSIONS
    )
    physical = 0
    nonblank = 0
    for path in sources:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        physical += len(lines)
        nonblank += sum(1 for line in lines if line.strip())
    return _CorpusMetrics(
        files=sum(1 for path in root.rglob("*") if path.is_file()),
        c_files=sum(1 for path in sources if path.suffix.lower() == C_SUFFIX),
        headers=sum(
            1 for path in sources if path.suffix.lower() in HEADER_EXTENSIONS
        ),
        source_bytes=sum(path.stat().st_size for path in sources),
        physical_source_lines=physical,
        nonblank_source_lines=nonblank,
        asset_files=len(assets),
        asset_bytes=sum(path.stat().st_size for path in assets),
        asset_sha256=_tree_hash(assets, root),
        source_sha256=_tree_hash(sources, root),
    )


def _compile_args(
    path: Path,
    *,
    root: Path,
    triple: str,
    sysroot: Path,
) -> list[str]:
    relative = path.relative_to(root).as_posix().lower()
    args = [
        "--target=" + triple,
        "--sysroot=" + str(sysroot),
        "-x",
        "c",
        "-std=c23",
        "-fno-color-diagnostics",
        "-ferror-limit=0",
        *WARNING_FLAGS,
    ]
    if relative.startswith("linuxdoom-1.10/"):
        args.extend(["-DNORMALUNIX", "-DLINUX"])
    args.extend(["-I", str(path.parent)])
    linux_root = root / "linuxdoom-1.10"
    if linux_root.is_dir() and path.parent != linux_root:
        args.extend(["-I", str(linux_root)])
    return args


def _relative_path(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _parse_diagnostics(output: str, gate: str, root: Path) -> list[_Finding]:
    findings: list[_Finding] = []
    for line in output.splitlines():
        match = DIAGNOSTIC_RE.match(line)
        if not match:
            continue
        path_text, row, column, _, message, rule = match.groups()
        path = Path(path_text)
        if not path.is_absolute():
            path = REPO_ROOT / path
        relative = _relative_path(path, root)
        if relative is None:
            continue
        findings.append(
            _Finding(
                gate=gate,
                path=relative,
                line=int(row),
                column=int(column),
                rule=rule or "compiler-diagnostic",
                message=message,
            )
        )
    return findings


def _format_findings(path: Path, root: Path) -> list[_Finding]:
    proc = _run([
        str(CLANG_FORMAT),
        f"--style=file:{ROOT_FORMAT}",
        "--dry-run",
        "--Werror",
        str(path),
    ])
    findings: list[_Finding] = []
    for line in proc.stdout.splitlines():
        match = FORMAT_RE.match(line)
        if not match:
            continue
        path_text, row, column = match.groups()
        candidate = Path(path_text)
        if not candidate.is_absolute():
            candidate = REPO_ROOT / candidate
        relative = _relative_path(candidate, root)
        if relative is None:
            continue
        findings.append(
            _Finding(
                gate="clang-format",
                path=relative,
                line=int(row),
                column=int(column),
                rule="clang-format",
                message="code should be clang-formatted",
            )
        )
    return findings


def _compiler_findings(path: Path, root: Path, gate: str) -> list[_Finding]:
    triple, sysroot = TARGETS[gate]
    proc = _run([
        str(CLANG),
        "-fsyntax-only",
        *_compile_args(path, root=root, triple=triple, sysroot=sysroot),
        str(path),
    ])
    return _parse_diagnostics(proc.stdout, gate, root)


def _tidy_findings(path: Path, root: Path) -> list[_Finding]:
    triple, sysroot = TARGETS["clang-linux-x86_64"]
    proc = _run([
        str(CLANG_TIDY),
        "-quiet",
        f"--config-file={ROOT_TIDY}",
        str(path),
        "--",
        *_compile_args(path, root=root, triple=triple, sysroot=sysroot),
    ])
    return _parse_diagnostics(proc.stdout, "clang-tidy", root)


def _platform_patterns() -> tuple[tuple[re.Pattern[str], str], ...]:
    return (
        (re.compile(r"#\s*include\s*<dos\.h>", re.IGNORECASE), "legacy-dos"),
        (
            re.compile(
                r"#\s*include\s*<linux/soundcard\.h>",
                re.IGNORECASE,
            ),
            "legacy-oss-audio",
        ),
        (re.compile(r"#\s*include\s*<X11/", re.IGNORECASE), "direct-x11"),
        (re.compile(r"\bsndserver\b", re.IGNORECASE), "external-sndserver"),
    )


def _platform_file_findings(
    path: Path,
    root: Path,
) -> tuple[list[_Finding], str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    relative = path.relative_to(root).as_posix()
    findings: list[_Finding] = []
    patterns = _platform_patterns()
    for row, line in enumerate(text.splitlines(), start=1):
        for pattern, rule in patterns:
            match = pattern.search(line)
            if match is not None:
                findings.append(
                    _Finding(
                        gate="interop",
                        path=relative,
                        line=row,
                        column=match.start() + 1,
                        rule=rule,
                        message=rule.replace("-", " "),
                    )
                )
    return findings, text


def _missing_platform_findings(corpus: str) -> list[_Finding]:
    lower_corpus = corpus.lower()
    required = (
        (
            "windows-backend",
            any(marker in corpus for marker in WINDOWS_MARKERS),
        ),
        (
            "macos-backend",
            any(marker in corpus for marker in MACOS_MARKERS),
        ),
        ("borderless-mode", BORDERLESS_MARKER in lower_corpus),
    )
    return [
        _Finding(
            gate="interop",
            path="<corpus>",
            line=0,
            column=0,
            rule=f"{rule}-missing",
            message=f"{rule.replace("-", " ")} missing",
        )
        for rule, present in required
        if not present
    ]


def _platform_findings(root: Path) -> list[_Finding]:
    findings: list[_Finding] = []
    corpus: list[str] = []
    for path in _source_files(root):
        file_findings, text = _platform_file_findings(path, root)
        findings.extend(file_findings)
        corpus.append(text)
    findings.extend(_missing_platform_findings("\n".join(corpus)))
    return findings


def _dedupe(findings: list[_Finding]) -> list[_Finding]:
    unique: dict[tuple[object, ...], _Finding] = {}
    for finding in findings:
        _ = unique.setdefault(finding.key(), finding)
    return list(unique.values())


def _rule_family(rule: str) -> str:
    family = "interop/other"
    if rule == FORMAT_RULE:
        family = "format"
    elif rule == COMPILER_RULE or rule.startswith(("clang-diagnostic-", "-W")):
        family = "compiler"
    else:
        for prefixes, candidate in RULE_PREFIX_FAMILIES:
            if rule.startswith(prefixes):
                family = candidate
                break
    return family


def _ensure_corpus_stable(
    root: Path,
    expected: _CorpusMetrics,
    label: str,
) -> None:
    observed = _corpus_metrics(root)
    if observed != expected:
        _fail(
            f"{label} corpus changed during comparison; refusing mixed evidence"
        )


def _compiler_job_findings(
    job: _CompilerJob,
    root: Path,
) -> list[_Finding]:
    return _compiler_findings(job.path, root, job.gate)


def _validate(root: Path) -> _ValidationMetrics:
    findings: list[_Finding] = []
    sources = _source_files(root)
    units = [path for path in sources if path.suffix.lower() == C_SUFFIX]
    findings.extend(_text_findings(root))

    format_runner = partial(_format_findings, root=root)
    tidy_runner = partial(_tidy_findings, root=root)
    compiler_runner = partial(_compiler_job_findings, root=root)
    compiler_jobs = [
        _CompilerJob(gate=gate, path=path) for path in units for gate in TARGETS
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for result in executor.map(format_runner, sources):
            findings.extend(result)
        for result in executor.map(compiler_runner, compiler_jobs):
            findings.extend(result)
        for result in executor.map(tidy_runner, units):
            findings.extend(result)

    findings.extend(_platform_findings(root))
    unique = _dedupe(findings)
    return _ValidationMetrics(
        raw_findings=len(findings),
        unique_findings=len(unique),
        by_gate=dict(sorted(Counter(item.gate for item in unique).items())),
        by_rule_family=dict(
            sorted(Counter(_rule_family(item.rule) for item in unique).items())
        ),
    )


def _reduction(before: int, after: int) -> str:
    if before == 0:
        return "0.0" if after == 0 else "n/a"
    value = 100.0 * (before - after) / before
    return f"{value:.2f}"


def _findings_per_kloc(findings: int, lines: int) -> float:
    if lines == 0:
        return 0.0
    return findings * 1000.0 / lines


def _tex_escape(text: str) -> str:
    latex = "\\"
    replacements = {
        "\\": latex + "textbackslash{}",
        "&": latex + "&",
        "%": latex + "%",
        "$": latex + "$",
        "#": latex + "#",
        "_": latex + "_",
        "{": latex + "{",
        "}": latex + "}",
        "~": latex + "textasciitilde{}",
        "^": latex + "textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _emit_json(path: Path, comparison: _Comparison) -> None:
    before_root = comparison.before_root
    after_root = comparison.after_root
    before_corpus = comparison.before_corpus
    after_corpus = comparison.after_corpus
    before_validation = comparison.before_validation
    after_validation = comparison.after_validation
    payload = {
        "generator": str(SCRIPT.relative_to(REPO_ROOT).as_posix()),
        "llvm_version": "22.1.8",
        "before": {
            "path": str(before_root.relative_to(REPO_ROOT).as_posix()),
            "corpus": dataclasses.asdict(before_corpus),
            "validation": dataclasses.asdict(before_validation),
        },
        "after": {
            "path": str(after_root.relative_to(REPO_ROOT).as_posix()),
            "corpus": dataclasses.asdict(after_corpus),
            "validation": dataclasses.asdict(after_validation),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _tex_metrics(comparison: _Comparison) -> _TexMetrics:
    latex = "\\"
    before_density = _findings_per_kloc(
        comparison.before_validation.unique_findings,
        comparison.before_corpus.physical_source_lines,
    )
    after_density = _findings_per_kloc(
        comparison.after_validation.unique_findings,
        comparison.after_corpus.physical_source_lines,
    )
    return _TexMetrics(
        latex=latex,
        row_end=latex * 2,
        before_density=before_density,
        after_density=after_density,
        unique_reduction=_reduction(
            comparison.before_validation.unique_findings,
            comparison.after_validation.unique_findings,
        ),
        raw_reduction=_reduction(
            comparison.before_validation.raw_findings,
            comparison.after_validation.raw_findings,
        ),
        density_reduction=_reduction(
            round(before_density * 100),
            round(after_density * 100),
        ),
        before_path=_tex_escape(
            comparison.before_root.relative_to(REPO_ROOT).as_posix()
        ),
        after_path=_tex_escape(
            comparison.after_root.relative_to(REPO_ROOT).as_posix()
        ),
    )


def _tex_count_row(
    label: str,
    before: int,
    after: int,
    *,
    row_end: str,
) -> str:
    return f"{_tex_escape(label)} & {before} & {after} {row_end}"


def _tex_path_line(label: str, path: str, metrics: _TexMetrics) -> str:
    return f"{label}: {metrics.latex}texttt{{{path}}}.{metrics.row_end}"


def _emit_tex(path: Path, comparison: _Comparison) -> None:
    metrics = _tex_metrics(comparison)
    before_corpus = comparison.before_corpus
    after_corpus = comparison.after_corpus
    before_validation = comparison.before_validation
    after_validation = comparison.after_validation
    gates = sorted(
        set(before_validation.by_gate) | set(after_validation.by_gate)
    )
    families = sorted(
        set(before_validation.by_rule_family)
        | set(after_validation.by_rule_family)
    )

    lines = [
        metrics.latex + "documentclass[10pt]{article}",
        metrics.latex + "usepackage[margin=0.8in]{geometry}",
        metrics.latex + "usepackage{booktabs}",
        metrics.latex + "usepackage{microtype}",
        metrics.latex + "usepackage{pgfplots}",
        metrics.latex + "pgfplotsset{compat=1.18}",
        metrics.latex + "begin{document}",
        metrics.latex
        + "section*{DOOM Quality Modernization: Before vs. After}",
        (
            "This report contains aggregate measurements only. Individual "
            "diagnostic paths and messages are intentionally excluded so "
            "report size does not scale with finding count."
        ),
        "",
        _tex_path_line("Before corpus", metrics.before_path, metrics),
        _tex_path_line("After corpus", metrics.after_path, metrics),
        "Pinned validator toolchain: LLVM/Clang 22.1.8.",
        metrics.latex + "subsection*{Corpus metrics}",
        metrics.latex + "begin{tabular}{lrr}",
        f"{metrics.latex}toprule Metric & Before & After {metrics.row_end}",
        metrics.latex + "midrule",
        _tex_count_row(
            "C translation units",
            before_corpus.c_files,
            after_corpus.c_files,
            row_end=metrics.row_end,
        ),
        (
            f"Headers & {before_corpus.headers} & "
            f"{after_corpus.headers} {metrics.row_end}"
        ),
        (
            "Physical source lines & "
            f"{before_corpus.physical_source_lines} & "
            f"{after_corpus.physical_source_lines} {metrics.row_end}"
        ),
        (
            "Nonblank source lines & "
            f"{before_corpus.nonblank_source_lines} & "
            f"{after_corpus.nonblank_source_lines} {metrics.row_end}"
        ),
        (
            "Source bytes & "
            f"{before_corpus.source_bytes} & "
            f"{after_corpus.source_bytes} {metrics.row_end}"
        ),
        (
            "Local WAD files & "
            f"{before_corpus.asset_files} & "
            f"{after_corpus.asset_files} {metrics.row_end}"
        ),
        (
            "Local WAD bytes & "
            f"{before_corpus.asset_bytes} & "
            f"{after_corpus.asset_bytes} {metrics.row_end}"
        ),
        metrics.latex + "bottomrule",
        metrics.latex + "end{tabular}",
        "",
        (
            "WAD files are reported separately and are excluded from source "
            "LOC and source-byte measurements."
        ),
        metrics.latex + "subsection*{Quality outcome}",
        metrics.latex + "begin{tabular}{lrrr}",
        (
            f"{metrics.latex}toprule Metric & Before & After & "
            f"Reduction ({metrics.latex}%) {metrics.row_end}"
        ),
        metrics.latex + "midrule",
        (
            "Unique findings & "
            f"{before_validation.unique_findings} & "
            f"{after_validation.unique_findings} & "
            f"{metrics.unique_reduction} {metrics.row_end}"
        ),
        (
            "Raw reports & "
            f"{before_validation.raw_findings} & "
            f"{after_validation.raw_findings} & "
            f"{metrics.raw_reduction} {metrics.row_end}"
        ),
        (
            "Findings / KLOC & "
            f"{metrics.before_density:.2f} & {metrics.after_density:.2f} & "
            f"{metrics.density_reduction} {metrics.row_end}"
        ),
        metrics.latex + "bottomrule",
        metrics.latex + "end{tabular}",
        metrics.latex + "subsection*{Findings by gate}",
        metrics.latex + "begin{tabular}{lrr}",
        f"{metrics.latex}toprule Gate & Before & After {metrics.row_end}",
        metrics.latex + "midrule",
    ]
    lines.extend(
        _tex_count_row(
            gate,
            before_validation.by_gate.get(gate, 0),
            after_validation.by_gate.get(gate, 0),
            row_end=metrics.row_end,
        )
        for gate in gates
    )
    lines.extend([
        metrics.latex + "bottomrule",
        metrics.latex + "end{tabular}",
        metrics.latex + "subsection*{Findings by rule family}",
        metrics.latex + "begin{tabular}{lrr}",
        f"{metrics.latex}toprule Family & Before & After {metrics.row_end}",
        metrics.latex + "midrule",
    ])
    lines.extend(
        _tex_count_row(
            family,
            before_validation.by_rule_family.get(family, 0),
            after_validation.by_rule_family.get(family, 0),
            row_end=metrics.row_end,
        )
        for family in families
    )
    lines.extend([
        metrics.latex + "bottomrule",
        metrics.latex + "end{tabular}",
        metrics.latex + "subsection*{Visual comparison}",
        metrics.latex + "begin{center}",
        metrics.latex + "begin{tikzpicture}",
        metrics.latex + "begin{axis}[",
        "ybar,",
        "bar width=18pt,",
        f"width=0.88{metrics.latex}linewidth,",
        "height=6cm,",
        "ylabel={Unique findings},",
        "symbolic x coords={Before,After},",
        "xtick=data,",
        "nodes near coords,",
        "ymin=0,",
        "]",
        (
            f"{metrics.latex}addplot coordinates "
            f"{{(Before,{before_validation.unique_findings}) "
            f"(After,{after_validation.unique_findings})}};"
        ),
        metrics.latex + "end{axis}",
        metrics.latex + "end{tikzpicture}",
        metrics.latex + "end{center}",
        metrics.latex + "subsection*{Reproducibility}",
        (
            f"Before source SHA-256: {metrics.latex}texttt{{"
            + before_corpus.source_sha256
            + f"}}.{metrics.row_end}"
        ),
        (
            f"After source SHA-256: {metrics.latex}texttt{{"
            + after_corpus.source_sha256
            + f"}}.{metrics.row_end}"
        ),
        (
            f"Before asset SHA-256: {metrics.latex}texttt{{"
            + before_corpus.asset_sha256
            + f"}}.{metrics.row_end}"
        ),
        (
            f"After asset SHA-256: {metrics.latex}texttt{{"
            + after_corpus.asset_sha256
            + f"}}.{metrics.row_end}"
        ),
        (
            "Machine-readable aggregate metrics: "
            + metrics.latex
            + "texttt{algorithms/doom/quality/comparison/metrics.json}."
        ),
        "The generator intentionally stores no per-finding ledger.",
        metrics.latex + "end{document}",
    ])
    _ = path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _ensure_inputs(before: Path, after: Path) -> None:
    required = [CLANG, CLANG_TIDY, CLANG_FORMAT, ROOT_TIDY, ROOT_FORMAT]
    required.extend([before, after])
    missing = [path for path in required if not path.exists()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        _fail(f"missing required input/tool: {joined}")

    format_probe = _run([
        str(CLANG_FORMAT),
        f"--style=file:{ROOT_FORMAT}",
        "--assume-filename=probe.c",
    ])
    if format_probe.returncode != 0:
        message = "clang-format policy is unusable with LLVM 22.1.8:\n"
        _fail(message + format_probe.stdout)

    tidy_probe = _run([str(CLANG_TIDY), "--verify-config"])
    if tidy_probe.returncode != 0:
        message = "clang-tidy policy is unusable with LLVM 22.1.8:\n"
        _fail(message + tidy_probe.stdout)


def _parse_arguments() -> _Arguments:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--before", type=Path, default=DEFAULT_BEFORE)
    _ = parser.add_argument("--after", type=Path, default=DEFAULT_AFTER)
    _ = parser.add_argument("--tex", type=Path, default=DEFAULT_TEX)
    _ = parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    arguments = _Arguments()
    _ = parser.parse_args(namespace=arguments)
    return arguments


def _progress(message: str) -> None:
    _ = sys.stdout.write(message + "\n")
    _ = sys.stdout.flush()


def _measure(arguments: _Arguments) -> _Comparison:
    before = arguments.before.resolve()
    after = arguments.after.resolve()
    _ensure_inputs(before, after)
    _progress("measuring before corpus")
    before_corpus = _corpus_metrics(before)
    _progress("validating before corpus")
    before_validation = _validate(before)
    _ensure_corpus_stable(before, before_corpus, "before")
    _progress("measuring after corpus")
    after_corpus = _corpus_metrics(after)
    _progress("validating after corpus")
    after_validation = _validate(after)
    _ensure_corpus_stable(after, after_corpus, "after")
    _ensure_corpus_stable(before, before_corpus, "before")
    return _Comparison(
        before_root=before,
        after_root=after,
        before_corpus=before_corpus,
        after_corpus=after_corpus,
        before_validation=before_validation,
        after_validation=after_validation,
    )


def _emit_outputs(arguments: _Arguments, comparison: _Comparison) -> None:
    tex_path = arguments.tex.resolve()
    json_path = arguments.json.resolve()
    _emit_json(json_path, comparison)
    _emit_tex(tex_path, comparison)
    summary = " ".join((
        f"before_unique={comparison.before_validation.unique_findings}",
        f"after_unique={comparison.after_validation.unique_findings}",
    ))
    _progress(summary)
    _progress(f"tex={tex_path}")
    _progress(f"json={json_path}")


def main() -> int:
    """Measure both corpora and emit compact aggregate evidence.

    Returns:
        Zero after a coherent report is emitted, otherwise one.

    """
    try:
        arguments = _parse_arguments()
        comparison = _measure(arguments)
        _emit_outputs(arguments, comparison)
    except (OSError, _ComparisonError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
