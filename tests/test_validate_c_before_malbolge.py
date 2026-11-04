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
#   - Regression evidence for the deterministic pre-Malbolge C validator.
# - Must-Not:
#   - Treat expensive-but-supported C constructs as compatibility failures.
# - Allows:
#   - Inputs: temporary explicit C translation units and repository-pinned
#     Clang.
#   - Outputs: accepted/rejected preflight process evidence.
#   - Side effects: temporary files and pinned Clang subprocess execution.
# - Split-When:
#   - Full lowerability fixtures gain a separate end-to-end compiler suite.
# - Merge-When:
#   - The tools/tidy lowerability suite owns these exact preflight cases.
# - Summary:
#   - Locks closed includes, reproducibility checks, and non-overrejection.
# - Description:
#   - Verifies deterministic hard failures without banning ABI-supported
#     features.
# - Usage:
#   - Executed by pytest.
# - Defaults:
#   - Missing pinned Clang skips executable preflight evidence.
#

"""Deterministic pre-Malbolge C validation regressions."""

from __future__ import annotations

import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from typing import Callable, cast

import pytest

from scripts.validate import validate_c_before_malbolge as preflight

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "src/automation/repository/composition/scripts/validate"
    / "validate_c_before_malbolge.py"
)
PINNED_CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CLEAN_MESSAGE = "pre-Malbolge Clang preflight clean"
PRE_DIAGNOSTIC = "MALBOLGE-PRE-001"
DATE_DIAGNOSTIC = "date or time macro"
HOST_HEADER = "unistd.h"
NOT_FOUND = "file not found"


def _run(source: Path) -> sp.CompletedProcess[str]:
    if not PINNED_CLANG.is_file():
        pytest.skip("repository-pinned Clang is unavailable")
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(SCRIPT), "--preflight-only", str(source)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )


def test_preflight_accepts_supported_difficult_c(tmp_path: Path) -> None:
    """VLA, recursion, and function pointers are not rejected by difficulty."""
    source = tmp_path / "supported.c"
    _ = source.write_text(
        """
static int recursive(int value) {
    return value == 0 ? 0 : 1 + recursive(value - 1);
}
static int apply(int (*function)(int), int value) {
    int scratch[value > 0 ? value : 1];
    scratch[0] = function(value);
    return scratch[0];
}
int entry(int value) { return apply(recursive, value); }
""".lstrip(),
        encoding="utf-8",
    )
    completed = _run(source)
    assert completed.returncode == 0, completed.stderr
    assert CLEAN_MESSAGE in completed.stdout


def test_preflight_rejects_nondeterministic_date_macro(tmp_path: Path) -> None:
    """Compilation-time clock macros cannot enter deterministic guest source."""
    source = tmp_path / "date_macro.c"
    _ = source.write_text(
        "const char *build_date = __DATE__;\n",
        encoding="utf-8",
    )
    completed = _run(source)
    assert completed.returncode == 1
    assert PRE_DIAGNOSTIC in completed.stderr
    assert DATE_DIAGNOSTIC in completed.stderr


def test_preflight_rejects_ambient_host_header(tmp_path: Path) -> None:
    """The guest include universe cannot fall back to ambient host headers."""
    source = tmp_path / "host_header.c"
    _ = source.write_text(
        "#include <unistd.h>\nint entry(void) { return 0; }\n",
        encoding="utf-8",
    )
    completed = _run(source)
    assert completed.returncode == 1
    assert PRE_DIAGNOSTIC in completed.stderr
    assert HOST_HEADER in completed.stderr
    assert NOT_FOUND in completed.stderr


@pytest.mark.parametrize("redirect", ("leaf", "nested-directory", "root"))
def test_recursive_doom_rejects_redirected_sources(
    redirect: str, tmp_path: Path
) -> None:
    """Recursive doom selection must not leave its explicitly chosen tree."""
    doom = tmp_path / "doom"
    doom.mkdir()
    _ = (doom / "plain.c").write_text("int plain;\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    _ = (outside / "other.c").write_text("int outside;\n", encoding="utf-8")
    if redirect == "leaf":
        (doom / "alias.c").symlink_to(outside / "other.c")
    elif redirect == "nested-directory":
        (doom / "alias").symlink_to(outside, target_is_directory=True)
    else:
        _ = doom.rename(tmp_path / "saved")
        doom.symlink_to(outside, target_is_directory=True)
    with pytest.raises(preflight.ValidationInputError, match="redirect"):
        _ = preflight._validated_files([str(doom)])  # pyright: ignore[reportPrivateUsage]


def test_explicit_source_alias_and_physical_doom_nesting_remain_supported(
    tmp_path: Path,
) -> None:
    """Only recursive discovery prohibits links, not explicit C file paths."""
    source = tmp_path / "actual.c"
    _ = source.write_text("int actual;\n", encoding="utf-8")
    alias = tmp_path / "alias.c"
    alias.symlink_to(source)
    assert preflight._validated_files([str(alias)]) == (source,)  # pyright: ignore[reportPrivateUsage]

    nested = tmp_path / "doom" / "src"
    nested.mkdir(parents=True)
    child = nested / "child.c"
    _ = child.write_text("int child;\n", encoding="utf-8")
    assert preflight._validated_files([str(tmp_path / "doom")]) == (child,)  # pyright: ignore[reportPrivateUsage]


def test_recursive_doom_cli_reports_configuration_error(
    tmp_path: Path,
) -> None:
    """A redirected recursive input fails before invoking any Clang tool."""
    doom = tmp_path / "doom"
    doom.mkdir()
    outside = tmp_path / "outside.c"
    _ = outside.write_text("int outside;\n", encoding="utf-8")
    (doom / "alias.c").symlink_to(outside)
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true] - exact validator argv.
        [sys.executable, str(SCRIPT), "--preflight-only", str(doom)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        shell=False,
    )
    assert completed.returncode == preflight.CONFIGURATION_ERROR
    assert "recursive doom entry must not redirect" in completed.stderr
    assert not completed.stdout


@pytest.mark.parametrize("bad_status", [False, True, 0.0, 1.0, "0", None])
def test_preflight_rejects_noninteger_process_status_receipts(
    bad_status: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bool or floating exit status cannot impersonate Clang success."""
    completed = sp.CompletedProcess(
        args=["clang", "--version"],
        returncode=0,
        stdout="clang version 22.1.8",
        stderr="",
    )
    completed.returncode = cast("int", bad_status)
    monkeypatch.setattr(preflight.sp, "run", lambda *_args, **_kwargs: completed)
    with pytest.raises(preflight.ValidationInputError, match="process receipt"):
        _ = preflight._tool_output(["clang", "--version"])


@pytest.mark.parametrize("field", ["stdout", "stderr"])
def test_preflight_rejects_foreign_process_output_text(
    field: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Output hooks are never invoked before process receipt admission."""

    class HostileText(str):
        def __bool__(self) -> bool:
            raise AssertionError("foreign Clang output truthiness hook executed")

        def __add__(self, other: object) -> str:
            del other
            raise AssertionError("foreign Clang output concatenation executed")

    completed = sp.CompletedProcess(
        args=["clang", "--version"],
        returncode=0,
        stdout="clang version 22.1.8",
        stderr="",
    )
    setattr(completed, field, HostileText("some text"))
    monkeypatch.setattr(preflight.sp, "run", lambda *_args, **_kwargs: completed)
    with pytest.raises(preflight.ValidationInputError, match="process receipt"):
        _ = preflight._tool_output(["clang", "--version"])


def test_preflight_rejects_foreign_completed_process_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown process result objects cannot dispatch attribute hooks."""

    class HostileResult:
        def __getattribute__(self, _name: str) -> object:
            raise AssertionError("foreign process property hook executed")

    monkeypatch.setattr(preflight.sp, "run", lambda *_args, **_kwargs: HostileResult())
    with pytest.raises(preflight.ValidationInputError, match="process receipt"):
        _ = preflight._tool_output(["clang", "--version"])


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_preflight_tool_execution_faults_preserve_cause_without_formatting(
    fault_type: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Host execution errors never run untrusted exception formatters."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign Clang host formatter executed")

    foreign = type("HostileClangFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe external error")

    def fail_run(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(preflight.sp, "run", fail_run)
    with pytest.raises(
        preflight.ValidationInputError, match="failed to execute"
    ) as caught:
        _ = preflight._tool_output(["clang", "--version"])
    assert caught.value.__cause__ is fault


def test_preflight_canonical_contract_never_formats_foreign_valueerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign canonical ABI failures retain their cause without hook dispatch."""

    class ForeignAbiFault(ValueError):
        def __str__(self) -> str:
            raise AssertionError("foreign canonical guest ABI formatter executed")

    fault = ForeignAbiFault("untrusted ABI detail")

    def fail_abi() -> None:
        raise fault

    monkeypatch.setattr(preflight.c_abi, "canonical_projection", fail_abi)
    with pytest.raises(
        preflight.ValidationInputError, match="invalid canonical guest-C contract"
    ) as caught:
        _ = preflight._canonical_abi()
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("foreign", [False, True])
def test_preflight_cli_policy_errors_have_safe_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    foreign: bool,
) -> None:
    """Native validation diagnostics remain useful without foreign formatters."""

    class ForeignPolicyFault(preflight.ValidationInputError):
        def __str__(self) -> str:
            raise AssertionError("foreign preflight CLI formatter executed")

    fault = (
        ForeignPolicyFault("untrusted detail")
        if foreign
        else preflight.ValidationInputError("native policy detail")
    )

    def fail_validation(_arguments: object) -> int:
        raise fault

    monkeypatch.setattr(preflight, "_parse_arguments", lambda: object())
    monkeypatch.setattr(preflight, "_run_validation", fail_validation)
    assert preflight.main() == preflight.CONFIGURATION_ERROR
    report = capsys.readouterr()
    assert ("ForeignPolicyFault" if foreign else "native policy detail") in report.err
    assert not report.out


@pytest.mark.parametrize(
    "receipt_kind",
    ["wrong_args", "tuple_args", "foreign_args", "foreign_token"],
)
def test_preflight_rejects_unverified_process_command_receipts(
    monkeypatch: pytest.MonkeyPatch,
    receipt_kind: str,
) -> None:
    """Clang cannot report successful evidence for an unrelated invocation."""

    class ForeignArgs(list[str]):
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign command-equality hook executed")

    class ForeignToken(str):
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign token-equality hook executed")

    def forged_run(args: list[str], **_options: object) -> object:
        forged: object = {
            "wrong_args": [*args, "--extra"],
            "tuple_args": tuple(args),
            "foreign_args": ForeignArgs(args),
            "foreign_token": [ForeignToken(args[0]), *args[1:]],
        }[receipt_kind]
        return sp.CompletedProcess(
            forged,
            0,
            stdout="clang version 22.1.8",
            stderr="",
        )

    monkeypatch.setattr(preflight.sp, "run", forged_run)
    with pytest.raises(preflight.ValidationInputError, match="process receipt"):
        _ = preflight._tool_output(["clang", "--version"])


@pytest.mark.parametrize("where", ["root", "leaf"])
@pytest.mark.parametrize("method", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("status", [0, None, 0.0])
def test_preflight_rejects_unverified_redirect_status_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    where: str,
    method: str,
    status: object,
) -> None:
    """Recursive doom admission requires native redirect-status booleans."""
    doom = tmp_path / "doom"
    doom.mkdir()
    source = doom / "unit.c"
    _ = source.write_bytes(b"int unit;\n")
    target = doom if where == "root" else source
    native = getattr(Path, method)

    def fake_status(path: Path) -> object:
        return status if path == target else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, method, fake_status)
        with pytest.raises(preflight.ValidationInputError, match="redirect"):
            _ = preflight._validated_files([str(doom)])


@pytest.mark.parametrize(
    ("method", "value"),
    [
        ("exists", 1),
        ("exists", object()),
        ("is_dir", 0),
        ("is_dir", object()),
        ("is_file", 1),
        ("is_file", object()),
    ],
)
def test_preflight_rejects_unverified_explicit_file_status_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    value: object,
) -> None:
    """A foreign path-status return never admits an explicit C source."""
    source = tmp_path / "unit.c"
    _ = source.write_bytes(b"int unit;\n")
    native = getattr(Path, method)

    def fake_status(path: Path) -> object:
        return value if path == source else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, method, fake_status)
        with pytest.raises(preflight.ValidationInputError, match="status receipt"):
            _ = preflight._validated_files([str(source)])


@pytest.mark.parametrize("value", ["/foreign/source.c", object()])
def test_preflight_rejects_unverified_resolved_file_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    value: object,
) -> None:
    """A foreign resolved-path wrapper cannot act as a selected source."""
    source = tmp_path / "unit.c"
    _ = source.write_bytes(b"int unit;\n")
    native = Path.resolve

    def fake_resolve(path: Path, strict: bool = False) -> object:
        return value if path == source else native(path, strict=strict)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "resolve", fake_resolve)
        with pytest.raises(preflight.ValidationInputError, match="resolved.*receipt"):
            _ = preflight._validated_files([str(source)])


@pytest.mark.parametrize("method", ["is_file", "is_dir"])
@pytest.mark.parametrize("status", [1, object()])
def test_preflight_rejects_unverified_pinned_tool_path_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    status: object,
) -> None:
    """A forged pinned-tool/directory status cannot authorize execution."""
    target = preflight.PINNED_CLANG if method == "is_file" else tmp_path
    native = getattr(Path, method)

    def fake_status(path: Path) -> object:
        return status if path == target else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, method, fake_status)
        if method == "is_file":
            with pytest.raises(preflight.ValidationInputError, match="status receipt"):
                preflight._require_pinned_clang()
        else:
            with pytest.raises(preflight.ValidationInputError, match="status receipt"):
                preflight._require_directory(tmp_path, "test guest headers")


@pytest.mark.parametrize("receipt", ["short", "boolean", "overlong", "bad-flush"])
def test_preflight_success_requires_complete_stdout_delivery(
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """Incomplete or foreign stdout receipts must not certify clean C."""

    class Output:
        def __init__(self) -> None:
            self.flushed: bool = False

        def write(self, message: str) -> object:
            if receipt == "short":
                return len(message) - 1
            if receipt == "boolean":
                return True
            if receipt == "overlong":
                return len(message) + 1
            return len(message)

        def flush(self) -> object:
            self.flushed = True
            return 1 if receipt == "bad-flush" else None

    output = Output()
    monkeypatch.setattr(sys, "stdout", output)
    with pytest.raises(preflight.ValidationInputError, match="output"):
        preflight._success_message(  # pyright: ignore[reportPrivateUsage]
            "pre-Malbolge Clang preflight clean", 1
        )
    assert output.flushed is (receipt == "bad-flush")


@pytest.mark.parametrize("field", ["stdout", "stderr"])
def test_preflight_tool_output_rejects_short_writes(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """Delegated tool output must not be silently lost on success."""

    class ShortWriter:
        def write(self, message: str) -> int:
            return len(message) - 1

        def flush(self) -> None:
            raise AssertionError("partial write must not be flushed")

    monkeypatch.setattr(sys, field, ShortWriter())
    output = sp.CompletedProcess(
        ["clang"], 0,
        stdout="tool output" if field == "stdout" else "",
        stderr="tool diagnostics" if field == "stderr" else "",
    )
    with pytest.raises(preflight.ValidationInputError, match="output"):
        preflight._write_tool_output(output)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("failure", ["write", "flush"])
def test_preflight_main_remains_nonzero_when_stderr_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """A failed diagnostic sink cannot turn rejected C into an exit-zero result."""

    class FailingStream:
        def write(self, message: str) -> int:
            if failure == "write":
                raise OSError("stderr unavailable")
            return len(message)

        def flush(self) -> None:
            raise OSError("stderr flush unavailable")

    def invalid_arguments() -> None:
        raise preflight.ValidationInputError("rejected input")

    monkeypatch.setattr(preflight, "_parse_arguments", invalid_arguments)
    monkeypatch.setattr(sys, "stderr", FailingStream())
    assert preflight.main() == preflight.CONFIGURATION_ERROR


def test_preflight_main_rejects_incomplete_clean_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful validation result needs its complete stdout record."""

    class ShortStream:
        def write(self, message: str) -> int:
            return len(message) - 1

        def flush(self) -> None:
            raise AssertionError("a short write must not be flushed")

    monkeypatch.setattr(sys, "stdout", ShortStream())
    monkeypatch.setattr(preflight, "_parse_arguments", lambda: object())

    def pretend_clean(_arguments: object) -> int:
        preflight._success_message(  # pyright: ignore[reportPrivateUsage]
            "pre-Malbolge guest-C validation clean", 1
        )
        return 0

    monkeypatch.setattr(preflight, "_run_validation", pretend_clean)
    assert preflight.main() == preflight.CONFIGURATION_ERROR


def test_preflight_valid_tool_output_flushes_complete_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native complete streams still permit ordinary Clang result forwarding."""
    received: list[tuple[str, str]] = []

    class CompleteStream:
        def __init__(self, name: str) -> None:
            self.name: str = name

        def write(self, message: str) -> int:
            received.append((self.name, message))
            return len(message)

        def flush(self) -> None:
            received.append((self.name, "flush"))

    monkeypatch.setattr(sys, "stdout", CompleteStream("stdout"))
    monkeypatch.setattr(sys, "stderr", CompleteStream("stderr"))
    completed = sp.CompletedProcess(
        ["clang"], 0, stdout="accepted output", stderr="warning output"
    )
    preflight._write_tool_output(completed)  # pyright: ignore[reportPrivateUsage]
    assert received == [
        ("stdout", "accepted output"),
        ("stdout", "flush"),
        ("stderr", "warning output"),
        ("stderr", "flush"),
    ]


@pytest.mark.parametrize("receipt", ["short", "boolean", "bad-flush"])
def test_preflight_help_must_not_succeed_without_delivery(
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """Argparse help is an operator record, not an unverified success exit."""

    class HelpStream:
        def write(self, message: str) -> object:
            if receipt == "short":
                return len(message) - 1
            if receipt == "boolean":
                return True
            return len(message)

        def flush(self) -> object:
            return False if receipt == "bad-flush" else None

    monkeypatch.setattr(sys, "argv", ["pre-malbolge", "--help"])
    monkeypatch.setattr(sys, "stdout", HelpStream())
    assert preflight.main() == preflight.CONFIGURATION_ERROR


def test_preflight_help_delivers_complete_native_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid help retains argparse's normal zero exit after flushing stdout."""
    outputs: list[str] = []

    class HelpStream:
        def write(self, message: str) -> int:
            outputs.append(message)
            return len(message)

        def flush(self) -> None:
            outputs.append("flush")

    monkeypatch.setattr(sys, "argv", ["pre-malbolge", "--help"])
    monkeypatch.setattr(sys, "stdout", HelpStream())
    with pytest.raises(SystemExit) as caught:
        _ = preflight.main()
    assert caught.value.code == 0
    assert outputs and "usage:" in outputs[0]
    assert outputs[-1] == "flush"


@pytest.mark.parametrize(
    "forged_entry", ["outside", "parent-escape", "linked-intermediate"]
)
def test_recursive_doom_refuses_unbound_discovery_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forged_entry: str,
) -> None:
    """A directory iterator cannot approve sources outside its admitted root."""
    doom = tmp_path / "doom"
    doom.mkdir()
    native_source = doom / "unit.c"
    _ = native_source.write_bytes(b"int unit;\n")
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_source = outside_dir / "foreign.c"
    _ = outside_source.write_bytes(b"int foreign;\n")
    if forged_entry == "outside":
        forged = outside_source
    elif forged_entry == "parent-escape":
        forged = doom / ".." / "outside" / "foreign.c"
    else:
        (doom / "shortcut").symlink_to(outside_dir, target_is_directory=True)
        forged = doom / "shortcut" / "foreign.c"

    native_rglob = Path.rglob

    def injected_rglob(path: Path, pattern: str) -> object:
        if path == doom:
            assert pattern == "*"
            return iter((native_source, forged))
        return native_rglob(path, pattern)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "rglob", injected_rglob)
        with pytest.raises(preflight.ValidationInputError, match="recursive doom"):
            _ = preflight._validated_files([str(doom)])  # pyright: ignore[reportPrivateUsage]


def test_recursive_doom_rejects_duplicate_iterator_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An untrusted repeated walker receipt is not a second physical source."""
    doom = tmp_path / "doom"
    doom.mkdir()
    source = doom / "unit.c"
    _ = source.write_bytes(b"int unit;\n")
    native_rglob = Path.rglob

    def repeated(path: Path, pattern: str) -> object:
        if path == doom:
            assert pattern == "*"
            return iter((source, source))
        return native_rglob(path, pattern)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "rglob", repeated)
        with pytest.raises(preflight.ValidationInputError, match="duplicate"):
            _ = preflight._validated_files([str(doom)])  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("receipt", ["foreign", "host-error", "false-membership"])
def test_recursive_doom_relative_path_requires_native_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """A forged relative-path result cannot bypass root provenance checks."""
    doom = tmp_path / "doom"
    doom.mkdir()
    source = doom / "unit.c"
    _ = source.write_bytes(b"int unit;\n")
    native_relative = Path.relative_to
    native_membership = Path.is_relative_to

    def forged_relative(path: Path, other: Path, *args: object, **kwargs: object) -> object:
        if path == source and other == doom:
            if receipt == "host-error":
                raise RuntimeError("unexpected relative path host failure")
            return object()
        return native_relative(path, other, *args, **kwargs)

    def forged_membership(path: Path, other: Path) -> object:
        if path == source and other == doom:
            return "true"
        return native_membership(path, other)

    with monkeypatch.context() as isolated:
        if receipt == "false-membership":
            isolated.setattr(Path, "is_relative_to", forged_membership)
        else:
            isolated.setattr(Path, "relative_to", forged_relative)
        with pytest.raises(preflight.ValidationInputError, match="recursive doom"):
            _ = preflight._validated_files([str(doom)])  # pyright: ignore[reportPrivateUsage]


MUTATE_PRE_EXECUTABLE = "executable"
MUTATE_PRE_APPEND = "append"
MUTATE_PRE_REMOVE = "remove"
PRE_TOOL_OUTPUT_NAME = "_tool_output"


@pytest.mark.parametrize(
    "mutation", [MUTATE_PRE_EXECUTABLE, MUTATE_PRE_APPEND, MUTATE_PRE_REMOVE]
)
def test_preflight_rejects_mutated_subprocess_argv(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """A launcher's mutation cannot rewrite expected Clang receipt identity."""

    def mutate_run(
        command: list[str], **_options: object
    ) -> sp.CompletedProcess[str]:
        del _options
        if mutation == MUTATE_PRE_EXECUTABLE:
            command[0] = "/foreign/clang"
        elif mutation == MUTATE_PRE_APPEND:
            command.append("--forged")
        else:
            _ = command.pop()
        return sp.CompletedProcess(
            command,
            0,
            stdout="clang version 22.1.8",
            stderr="",
        )

    monkeypatch.setattr(sp, "run", mutate_run)
    probe = cast(
        "Callable[[list[str]], sp.CompletedProcess[str]]",
        getattr(preflight, PRE_TOOL_OUTPUT_NAME),
    )
    with pytest.raises(preflight.ValidationInputError, match="process receipt"):
        _ = probe(["clang", "--version"])
