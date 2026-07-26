#!/usr/bin/env python3
"""Generate the compact DOOM before/after quality comparison report."""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

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

DIAGNOSTIC_RE = re.compile(
    r"^(.+?):(\d+):(\d+): (warning|error|fatal error): "
    r"(.*?)(?: \[([^\]]+)\])?$"
)
FORMAT_RE = re.compile(
    r"^(.+?):(\d+):(\d+): error: code should be clang-formatted"
)


@dataclasses.dataclass(frozen=True, slots=True)
class Finding:
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
class CorpusMetrics:
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
class ValidationMetrics:
    raw_findings: int
    unique_findings: int
    by_gate: dict[str, int]
    by_rule_family: dict[str, int]


def run(
    args: list[str],
    cwd: Path = REPO_ROOT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def source_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS
    )


def text_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS
    )


def text_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in text_files(root):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            findings.append(
                Finding(
                    gate="editorconfig",
                    path=relative,
                    line=0,
                    column=error.start + 1,
                    rule="text/encoding",
                    message="file is not valid UTF-8",
                )
            )
            continue

        if b"\r" in data:
            for row, raw_line in enumerate(data.splitlines(keepends=True), 1):
                if raw_line.endswith(b"\r\n") or raw_line.endswith(b"\r"):
                    findings.append(
                        Finding(
                            gate="editorconfig",
                            path=relative,
                            line=row,
                            column=max(1, len(raw_line)),
                            rule="text/line-ending",
                            message="line ending must be LF",
                        )
                    )

        lines = text.splitlines()
        for row, line in enumerate(lines, 1):
            stripped = line.rstrip(" \t")
            if stripped != line:
                findings.append(
                    Finding(
                        gate="editorconfig",
                        path=relative,
                        line=row,
                        column=len(stripped) + 1,
                        rule="text/trailing-whitespace",
                        message="trailing whitespace is not allowed",
                    )
                )
            if len(line) > 80:
                findings.append(
                    Finding(
                        gate="editorconfig",
                        path=relative,
                        line=row,
                        column=81,
                        rule="text/line-length",
                        message="line exceeds 80 columns",
                    )
                )
            leading = line[: len(line) - len(line.lstrip(" \t"))]
            if "\t" in leading and path.suffix.lower() in SOURCE_EXTENSIONS:
                findings.append(
                    Finding(
                        gate="editorconfig",
                        path=relative,
                        line=row,
                        column=leading.index("\t") + 1,
                        rule="text/indentation",
                        message="source indentation must use spaces",
                    )
                )

        if data and not data.endswith(b"\n"):
            findings.append(
                Finding(
                    gate="editorconfig",
                    path=relative,
                    line=max(1, len(lines)),
                    column=max(1, len(lines[-1]) + 1 if lines else 1),
                    rule="text/final-newline",
                    message="file must end with a newline",
                )
            )
    return findings


def tree_hash(paths: Iterable[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "little"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "little"))
        digest.update(data)
    return digest.hexdigest()


def corpus_metrics(root: Path) -> CorpusMetrics:
    sources = source_files(root)
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
    return CorpusMetrics(
        files=sum(1 for path in root.rglob("*") if path.is_file()),
        c_files=sum(1 for path in sources if path.suffix.lower() == ".c"),
        headers=sum(
            1 for path in sources if path.suffix.lower() in HEADER_EXTENSIONS
        ),
        source_bytes=sum(path.stat().st_size for path in sources),
        physical_source_lines=physical,
        nonblank_source_lines=nonblank,
        asset_files=len(assets),
        asset_bytes=sum(path.stat().st_size for path in assets),
        asset_sha256=tree_hash(assets, root),
        source_sha256=tree_hash(sources, root),
    )


def compile_args(
    path: Path,
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


def parse_diagnostics(output: str, gate: str, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for line in output.splitlines():
        match = DIAGNOSTIC_RE.match(line)
        if not match:
            continue
        path_text, row, column, _severity, message, rule = match.groups()
        path = Path(path_text)
        if not path.is_absolute():
            path = REPO_ROOT / path
        try:
            relative = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        findings.append(
            Finding(
                gate=gate,
                path=relative,
                line=int(row),
                column=int(column),
                rule=rule or "compiler-diagnostic",
                message=message,
            )
        )
    return findings


def format_findings(path: Path, root: Path) -> list[Finding]:
    proc = run(
        [
            str(CLANG_FORMAT),
            f"--style=file:{ROOT_FORMAT}",
            "--dry-run",
            "--Werror",
            str(path),
        ]
    )
    findings: list[Finding] = []
    for line in proc.stdout.splitlines():
        match = FORMAT_RE.match(line)
        if not match:
            continue
        path_text, row, column = match.groups()
        candidate = Path(path_text)
        if not candidate.is_absolute():
            candidate = REPO_ROOT / candidate
        try:
            relative = (
                candidate.resolve()
                .relative_to(root.resolve())
                .as_posix()
            )
        except ValueError:
            continue
        findings.append(
            Finding(
                gate="clang-format",
                path=relative,
                line=int(row),
                column=int(column),
                rule="clang-format",
                message="code should be clang-formatted",
            )
        )
    return findings


def compiler_findings(path: Path, root: Path, gate: str) -> list[Finding]:
    triple, sysroot = TARGETS[gate]
    proc = run(
        [
            str(CLANG),
            "-fsyntax-only",
            *compile_args(path, root, triple, sysroot),
            str(path),
        ]
    )
    return parse_diagnostics(proc.stdout, gate, root)


def tidy_findings(path: Path, root: Path) -> list[Finding]:
    triple, sysroot = TARGETS["clang-linux-x86_64"]
    proc = run(
        [
            str(CLANG_TIDY),
            "-quiet",
            f"--config-file={ROOT_TIDY}",
            str(path),
            "--",
            *compile_args(path, root, triple, sysroot),
        ]
    )
    return parse_diagnostics(proc.stdout, "clang-tidy", root)


def platform_findings(root: Path) -> list[Finding]:
    patterns = [
        (r"#\s*include\s*<dos\.h>", "legacy-dos"),
        (r"#\s*include\s*<linux/soundcard\.h>", "legacy-oss-audio"),
        (r"#\s*include\s*<X11/", "direct-x11"),
        (r"\bsndserver\b", "external-sndserver"),
    ]
    findings: list[Finding] = []
    sources = source_files(root)
    corpus = []
    for path in sources:
        text = path.read_text(encoding="utf-8", errors="replace")
        corpus.append(text)
        relative = path.relative_to(root).as_posix()
        for row, line in enumerate(text.splitlines(), start=1):
            for pattern, rule in patterns:
                match = re.search(pattern, line, flags=re.IGNORECASE)
                if match:
                    findings.append(
                        Finding(
                            gate="interop",
                            path=relative,
                            line=row,
                            column=match.start() + 1,
                            rule=rule,
                            message=rule.replace("-", " "),
                        )
                    )
    joined = "\n".join(corpus)
    synthetic = [
        ("windows-backend", "_WIN32" in joined or "WIN32" in joined),
        ("macos-backend", "__APPLE__" in joined or "__MACH__" in joined),
        ("borderless-mode", "borderless" in joined.lower()),
    ]
    for rule, present in synthetic:
        if not present:
            findings.append(
                Finding(
                    gate="interop",
                    path="<corpus>",
                    line=0,
                    column=0,
                    rule=rule + "-missing",
                    message=rule.replace("-", " ") + " missing",
                )
            )
    return findings


def dedupe(findings: Iterable[Finding]) -> list[Finding]:
    unique: dict[tuple[object, ...], Finding] = {}
    for finding in findings:
        unique.setdefault(finding.key(), finding)
    return list(unique.values())


def rule_family(rule: str) -> str:
    if rule == "clang-format":
        return "format"
    if rule.startswith("text/"):
        return "text"
    if (
        rule.startswith("clang-diagnostic-")
        or rule.startswith("-W")
        or rule == "compiler-diagnostic"
    ):
        return "compiler"
    if rule.startswith("readability-"):
        return "readability"
    if rule.startswith("bugprone-"):
        return "bugprone"
    if rule.startswith("clang-analyzer-"):
        return "analyzer"
    if rule.startswith("modernize-"):
        return "modernize"
    if rule.startswith("misc-"):
        return "misc"
    if rule.startswith("performance-"):
        return "performance"
    if rule.startswith("portability-"):
        return "portability"
    if rule.startswith("hicpp-"):
        return "hicpp"
    return "interop/other"


def ensure_corpus_stable(
    root: Path,
    expected: CorpusMetrics,
    label: str,
) -> None:
    observed = corpus_metrics(root)
    if observed != expected:
        raise SystemExit(
            f"{label} corpus changed during comparison; "
            "refusing to emit mixed evidence"
        )


def validate(root: Path) -> ValidationMetrics:
    findings: list[Finding] = []
    sources = source_files(root)
    units = [path for path in sources if path.suffix.lower() == ".c"]
    findings.extend(text_findings(root))

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for result in executor.map(
            lambda path: format_findings(path, root),
            sources,
        ):
            findings.extend(result)

        compiler_jobs = [
            (path, gate)
            for path in units
            for gate in TARGETS
        ]
        for result in executor.map(
            lambda item: compiler_findings(item[0], root, item[1]),
            compiler_jobs,
        ):
            findings.extend(result)

        for result in executor.map(
            lambda path: tidy_findings(path, root),
            units,
        ):
            findings.extend(result)

    findings.extend(platform_findings(root))
    unique = dedupe(findings)
    return ValidationMetrics(
        raw_findings=len(findings),
        unique_findings=len(unique),
        by_gate=dict(sorted(Counter(item.gate for item in unique).items())),
        by_rule_family=dict(
            sorted(Counter(rule_family(item.rule) for item in unique).items())
        ),
    )


def reduction(before: int, after: int) -> str:
    if before == 0:
        return "0.0" if after == 0 else "n/a"
    value = 100.0 * (before - after) / before
    return f"{value:.2f}"


def findings_per_kloc(findings: int, lines: int) -> float:
    if lines == 0:
        return 0.0
    return findings * 1000.0 / lines


def tex_escape(text: str) -> str:
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


def emit_json(
    path: Path,
    before_root: Path,
    after_root: Path,
    before_corpus: CorpusMetrics,
    after_corpus: CorpusMetrics,
    before_validation: ValidationMetrics,
    after_validation: ValidationMetrics,
) -> None:
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
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def emit_tex(
    path: Path,
    before_root: Path,
    after_root: Path,
    before_corpus: CorpusMetrics,
    after_corpus: CorpusMetrics,
    before_validation: ValidationMetrics,
    after_validation: ValidationMetrics,
) -> None:
    latex = "\\"
    row_end = latex * 2
    gates = sorted(
        set(before_validation.by_gate) | set(after_validation.by_gate)
    )
    families = sorted(
        set(before_validation.by_rule_family)
        | set(after_validation.by_rule_family)
    )
    before_density = findings_per_kloc(
        before_validation.unique_findings,
        before_corpus.physical_source_lines,
    )
    after_density = findings_per_kloc(
        after_validation.unique_findings,
        after_corpus.physical_source_lines,
    )
    unique_reduction = reduction(
        before_validation.unique_findings,
        after_validation.unique_findings,
    )
    raw_reduction = reduction(
        before_validation.raw_findings,
        after_validation.raw_findings,
    )
    density_reduction = reduction(
        round(before_density * 100),
        round(after_density * 100),
    )
    before_path = tex_escape(
        before_root.relative_to(REPO_ROOT).as_posix()
    )
    after_path = tex_escape(
        after_root.relative_to(REPO_ROOT).as_posix()
    )

    lines = [
        latex + "documentclass[10pt]{article}",
        latex + "usepackage[margin=0.8in]{geometry}",
        latex + "usepackage{booktabs}",
        latex + "usepackage{microtype}",
        latex + "usepackage{pgfplots}",
        latex + "pgfplotsset{compat=1.18}",
        latex + "begin{document}",
        latex + "section*{DOOM Quality Modernization: Before vs. After}",
        (
            "This report contains aggregate measurements only. Individual "
            "diagnostic paths and messages are intentionally excluded so "
            "report size does not scale with finding count."
        ),
        "",
        f"Before corpus: {latex}texttt{{{before_path}}}.{row_end}",
        f"After corpus: {latex}texttt{{{after_path}}}.{row_end}",
        "Pinned validator toolchain: LLVM/Clang 22.1.8.",
        latex + "subsection*{Corpus metrics}",
        latex + "begin{tabular}{lrr}",
        f"{latex}toprule Metric & Before & After {row_end}",
        latex + "midrule",
        (
            "C translation units & "
            f"{before_corpus.c_files} & {after_corpus.c_files} {row_end}"
        ),
        (
            f"Headers & {before_corpus.headers} & "
            f"{after_corpus.headers} {row_end}"
        ),
        (
            "Physical source lines & "
            f"{before_corpus.physical_source_lines} & "
            f"{after_corpus.physical_source_lines} {row_end}"
        ),
        (
            "Nonblank source lines & "
            f"{before_corpus.nonblank_source_lines} & "
            f"{after_corpus.nonblank_source_lines} {row_end}"
        ),
        (
            "Source bytes & "
            f"{before_corpus.source_bytes} & "
            f"{after_corpus.source_bytes} {row_end}"
        ),
        (
            "Local WAD files & "
            f"{before_corpus.asset_files} & "
            f"{after_corpus.asset_files} {row_end}"
        ),
        (
            "Local WAD bytes & "
            f"{before_corpus.asset_bytes} & "
            f"{after_corpus.asset_bytes} {row_end}"
        ),
        latex + "bottomrule",
        latex + "end{tabular}",
        "",
        (
            "WAD files are reported separately and are excluded from source "
            "LOC and source-byte measurements."
        ),
        latex + "subsection*{Quality outcome}",
        latex + "begin{tabular}{lrrr}",
        (
            f"{latex}toprule Metric & Before & After & "
            f"Reduction ({latex}%) {row_end}"
        ),
        latex + "midrule",
        (
            "Unique findings & "
            f"{before_validation.unique_findings} & "
            f"{after_validation.unique_findings} & "
            f"{unique_reduction} {row_end}"
        ),
        (
            "Raw reports & "
            f"{before_validation.raw_findings} & "
            f"{after_validation.raw_findings} & "
            f"{raw_reduction} {row_end}"
        ),
        (
            "Findings / KLOC & "
            f"{before_density:.2f} & {after_density:.2f} & "
            f"{density_reduction} {row_end}"
        ),
        latex + "bottomrule",
        latex + "end{tabular}",
        latex + "subsection*{Findings by gate}",
        latex + "begin{tabular}{lrr}",
        f"{latex}toprule Gate & Before & After {row_end}",
        latex + "midrule",
    ]
    for gate in gates:
        lines.append(
            f"{tex_escape(gate)} & "
            f"{before_validation.by_gate.get(gate, 0)} & "
            f"{after_validation.by_gate.get(gate, 0)} {row_end}"
        )
    lines.extend(
        [
            latex + "bottomrule",
            latex + "end{tabular}",
            latex + "subsection*{Findings by rule family}",
            latex + "begin{tabular}{lrr}",
            f"{latex}toprule Family & Before & After {row_end}",
            latex + "midrule",
        ]
    )
    for family in families:
        lines.append(
            f"{tex_escape(family)} & "
            f"{before_validation.by_rule_family.get(family, 0)} & "
            f"{after_validation.by_rule_family.get(family, 0)} {row_end}"
        )
    lines.extend(
        [
            latex + "bottomrule",
            latex + "end{tabular}",
            latex + "subsection*{Visual comparison}",
            latex + "begin{center}",
            latex + "begin{tikzpicture}",
            latex + "begin{axis}[",
            "ybar,",
            "bar width=18pt,",
            f"width=0.88{latex}linewidth,",
            "height=6cm,",
            "ylabel={Unique findings},",
            "symbolic x coords={Before,After},",
            "xtick=data,",
            "nodes near coords,",
            "ymin=0,",
            "]",
            (
                f"{latex}addplot coordinates "
                f"{{(Before,{before_validation.unique_findings}) "
                f"(After,{after_validation.unique_findings})}};"
            ),
            latex + "end{axis}",
            latex + "end{tikzpicture}",
            latex + "end{center}",
            latex + "subsection*{Reproducibility}",
            (
                f"Before source SHA-256: {latex}texttt{{"
                + before_corpus.source_sha256
                + f"}}.{row_end}"
            ),
            (
                f"After source SHA-256: {latex}texttt{{"
                + after_corpus.source_sha256
                + f"}}.{row_end}"
            ),
            (
                f"Before asset SHA-256: {latex}texttt{{"
                + before_corpus.asset_sha256
                + f"}}.{row_end}"
            ),
            (
                f"After asset SHA-256: {latex}texttt{{"
                + after_corpus.asset_sha256
                + f"}}.{row_end}"
            ),
            (
                "Machine-readable aggregate metrics: "
                + latex
                + "texttt{interop/algorithms/quality/comparison/metrics.json}."
            ),
            "The generator intentionally stores no per-finding ledger.",
            latex + "end{document}",
        ]
    )
    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def ensure_inputs(before: Path, after: Path) -> None:
    required = [CLANG, CLANG_TIDY, CLANG_FORMAT, ROOT_TIDY, ROOT_FORMAT]
    required.extend([before, after])
    missing = [path for path in required if not path.exists()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise SystemExit("missing required input/tool: " + joined)

    format_probe = run(
        [
            str(CLANG_FORMAT),
            f"--style=file:{ROOT_FORMAT}",
            "--assume-filename=probe.c",
        ]
    )
    if format_probe.returncode != 0:
        raise SystemExit(
            "clang-format policy is unusable with LLVM 22.1.8:\n"
            + format_probe.stdout
        )

    tidy_probe = run([str(CLANG_TIDY), "--verify-config"])
    if tidy_probe.returncode != 0:
        raise SystemExit(
            "clang-tidy policy is unusable with LLVM 22.1.8:\n"
            + tidy_probe.stdout
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, default=DEFAULT_BEFORE)
    parser.add_argument("--after", type=Path, default=DEFAULT_AFTER)
    parser.add_argument("--tex", type=Path, default=DEFAULT_TEX)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    args = parser.parse_args()
    before = args.before.resolve()
    after = args.after.resolve()
    ensure_inputs(before, after)

    print("measuring before corpus", flush=True)
    before_corpus = corpus_metrics(before)
    print("validating before corpus", flush=True)
    before_validation = validate(before)
    ensure_corpus_stable(before, before_corpus, "before")
    print("measuring after corpus", flush=True)
    after_corpus = corpus_metrics(after)
    print("validating after corpus", flush=True)
    after_validation = validate(after)
    ensure_corpus_stable(after, after_corpus, "after")
    ensure_corpus_stable(before, before_corpus, "before")

    emit_json(
        args.json.resolve(),
        before,
        after,
        before_corpus,
        after_corpus,
        before_validation,
        after_validation,
    )
    emit_tex(
        args.tex.resolve(),
        before,
        after,
        before_corpus,
        after_corpus,
        before_validation,
        after_validation,
    )
    print(
        f"before_unique={before_validation.unique_findings} "
        f"after_unique={after_validation.unique_findings}"
    )
    print(f"tex={args.tex.resolve()}")
    print(f"json={args.json.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
