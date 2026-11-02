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
#   - Native C validation dispatcher host-failure normalization regressions.
# - Must-Not:
#   - Execute native tools or depend on installed compiler availability.
# - Allows:
#   - Inputs: synthetic subprocess host failures.
#   - Outputs: typed failures with original host causes.
#   - Side effects: pytest monkeypatch state only.
# - Split-When:
#   - Dispatcher behavior gains independent process lifecycle ownership.
# - Merge-When:
#   - Existing native validation tests own the same failure contract.
# - Summary:
#   - Reject foreign host exception formatting in three C validation probes.

"""Fail-closed native C validator subprocess error normalization."""

from __future__ import annotations

# Directly exercises the validator's private subprocess admission functions.
# ruff: file-ignore[private-member-access]
# pyright: reportPrivateUsage=false
import subprocess  # ruff: ignore[suspicious-subprocess-import] - patched only; no processes run.
from pathlib import Path
from typing import Never, cast, override

import pytest

from scripts.validate import main as validator

PROBE_VERSION = "version"
PROBE_REGISTRATION = "registration"
NATIVE_DETAIL = "synthetic native process error"
FOREIGN_DETAIL = "ForeignProcessError"


class ForeignProcessError(OSError):
    """Injected OSError subtype with untrusted textual formatter."""

    @override
    def __str__(self) -> str:
        """Reject invocation of a foreign exception text formatter.

        Raises:
            AssertionError: The validator invoked an untrusted host hook.

        """
        message = "foreign native C process error formatter executed"
        raise AssertionError(message)


def _execute_probe(probe: str, executable: Path) -> None:
    """Invoke one native C dispatcher subprocess probe without a real tool."""
    if probe == PROBE_VERSION:
        _ = validator._tool_version_output(executable, "Clang")
    elif probe == PROBE_REGISTRATION:
        validator._require_plugin_registration(executable, Path("/synthetic/plugin"))
    else:
        _ = validator._run([str(executable), "--version"])


@pytest.mark.parametrize("probe", ["version", "registration", "validation"])
@pytest.mark.parametrize("fault_type", [ForeignProcessError, OSError])
def test_native_validator_admits_only_trusted_host_error_text(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    fault_type: type[OSError],
) -> None:
    """Typed process faults retain native details but avoid foreign hooks."""
    fault = fault_type(NATIVE_DETAIL)

    def reject_run(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise fault

    monkeypatch.setattr(subprocess, "run", reject_run)
    executable = Path("/synthetic/clang")

    with pytest.raises(validator.InputError, match="failed") as caught:
        _execute_probe(probe, executable)
    assert caught.value.__cause__ is fault
    expected = NATIVE_DETAIL if fault_type is OSError else FOREIGN_DETAIL
    assert expected in str(caught.value)


@pytest.mark.parametrize("probe", ("version", "registration"))
def test_manual_c_probe_requires_finite_timeout(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
) -> None:
    """Read-only Clang identity and plugin queries have a finite latency bound."""

    def inspect_run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert kwargs.get("timeout") == 15
        output = (
            "clang version 22.1.8\n"
            if probe == "version"
            else "\n".join(sorted(validator.PLUGIN_CHECKS))
        )
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    monkeypatch.setattr(subprocess, "run", inspect_run)
    _execute_probe(probe, Path("/synthetic/clang"))


@pytest.mark.parametrize("probe", ("version", "registration"))
@pytest.mark.parametrize("hostile", (False, True))
def test_manual_c_probe_timeout_stays_typed(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    hostile: bool,
) -> None:
    """A hung compiler discovery probe never escapes as a raw timeout."""

    def unsafe_str(self: Exception) -> Never:
        del self
        raise AssertionError("foreign timeout formatter executed")

    timeout_type = (
        type("ForeignTimeout", (subprocess.TimeoutExpired,), {"__str__": unsafe_str})
        if hostile
        else subprocess.TimeoutExpired
    )
    fault = timeout_type(["/synthetic/clang"], timeout=15)

    def fail_run(*_args: object, **_kwargs: object) -> Never:
        raise fault

    monkeypatch.setattr(subprocess, "run", fail_run)
    with pytest.raises(validator.InputError, match="failed") as caught:
        _execute_probe(probe, Path("/synthetic/clang"))
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("probe", ["version", "registration", "validation"])
@pytest.mark.parametrize(
    "receipt_kind",
    [
        "foreign_process",
        "subclass_process",
        "boolean_status",
        "float_status",
        "text_status",
        "foreign_args",
        "foreign_argument",
        "wrong_args",
    ],
)
def test_manual_c_validator_rejects_forged_process_receipts(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    receipt_kind: str,
) -> None:
    """Only an exact native matching subprocess may grant guest-C validation."""

    class ForeignProcess:
        @property
        def returncode(self) -> object:
            raise AssertionError("foreign process status hook executed")

    class SubclassProcess(subprocess.CompletedProcess[str]):
        pass

    class ForeignArgs(list[str]):
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign argument equality hook executed")

    class ForeignArgument(str):
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign token equality hook executed")

    def forged_run(args: list[str], **options: object) -> object:
        if receipt_kind == "foreign_process":
            return ForeignProcess()
        args_receipt: object = args
        if receipt_kind == "foreign_args":
            args_receipt = ForeignArgs(args)
        elif receipt_kind == "foreign_argument":
            args_receipt = [ForeignArgument(args[0]), *args[1:]]
        elif receipt_kind == "wrong_args":
            args_receipt = [*args, "--forged"]
        status = cast(
            "int",
            {
                "boolean_status": False,
                "float_status": 0.0,
                "text_status": "0",
            }.get(receipt_kind, 0),
        )
        constructor = (
            SubclassProcess
            if receipt_kind == "subclass_process"
            else subprocess.CompletedProcess
        )
        capturing = options.get("capture_output") is True
        return constructor(
            cast("list[str]", cast("object", args_receipt)),
            status,
            stdout="" if capturing else None,
            stderr="" if capturing else None,
        )

    monkeypatch.setattr(subprocess, "run", forged_run)
    with pytest.raises(validator.InputError, match="invalid.*process receipt"):
        _execute_probe(probe, Path("/synthetic/clang"))


@pytest.mark.parametrize("probe", ["version", "registration"])
@pytest.mark.parametrize(
    "receipt_kind",
    ["foreign_stdout", "foreign_stderr", "bytes_stdout", "missing_stderr"],
)
def test_manual_c_validator_rejects_forged_captured_output(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    receipt_kind: str,
) -> None:
    """Captured Clang output is exact native text before any inspection."""

    class ForeignText(str):
        def __add__(self, _other: object) -> str:
            raise AssertionError("foreign captured text evaluated")

        def splitlines(self, *_args: object, **_kwargs: object) -> list[str]:
            raise AssertionError("foreign captured line hooks executed")

    def forged_run(args: list[str], **_options: object) -> object:
        stdout: object = ""
        stderr: object = ""
        if receipt_kind == "foreign_stdout":
            stdout = ForeignText("")
        elif receipt_kind == "foreign_stderr":
            stderr = ForeignText("")
        elif receipt_kind == "bytes_stdout":
            stdout = b""
        elif receipt_kind == "missing_stderr":
            stderr = None
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(subprocess, "run", forged_run)
    with pytest.raises(validator.InputError, match="invalid.*process receipt"):
        _execute_probe(probe, Path("/synthetic/clang"))


@pytest.mark.parametrize("field", ["stdout", "stderr"])
def test_manual_c_validator_rejects_inherited_output_receipts(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """The inherited-I/O source validation may not claim captured output."""

    def forged_run(args: list[str], **_options: object) -> object:
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="" if field == "stdout" else None,
            stderr="" if field == "stderr" else None,
        )

    monkeypatch.setattr(subprocess, "run", forged_run)
    with pytest.raises(validator.InputError, match="invalid.*process receipt"):
        _execute_probe("validation", Path("/synthetic/clang"))


@pytest.mark.parametrize("probe", ["version", "registration", "validation"])
@pytest.mark.parametrize("fault_type", [ValueError, TypeError, RuntimeError])
def test_manual_c_validator_catches_non_os_host_faults_without_hooks(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    fault_type: type[Exception],
) -> None:
    """A foreign host exception retains its cause but never formats itself."""

    def unsafe_str(self: Exception) -> str:
        raise AssertionError("foreign host failure formatter executed")

    foreign = type("ForeignHostFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("private error evidence")

    def fail_run(*_args: object, **_kwargs: object) -> Never:
        raise fault

    monkeypatch.setattr(subprocess, "run", fail_run)
    with pytest.raises(validator.InputError, match="failed") as caught:
        _execute_probe(probe, Path("/synthetic/clang"))
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "fault_type",
    [
        validator.InputError,
        validator.c_abi_source.SourceAnalysisError,
        validator.c_libc_source.LibcSourceError,
    ],
)
def test_manual_c_validator_error_reporting_never_formats_foreign_errors(
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """Foreign validation errors cannot trigger arbitrary diagnostic hooks."""

    def unsafe_str(self: Exception) -> str:
        raise AssertionError("foreign diagnostic hook executed")

    foreign = type("ForeignDiagnostic", (fault_type,), {"__str__": unsafe_str})
    validator._write_error(foreign("private host error"))
    output = capsys.readouterr()
    assert "ForeignDiagnostic" in output.err
    assert "private host error" not in output.err
    assert not output.out


def test_manual_c_validator_preserves_native_diagnostic_text(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Native InputError retains the operator-visible failure detail."""
    validator._write_error(validator.InputError("native compiler failure"))
    assert "native compiler failure" in capsys.readouterr().err


@pytest.mark.parametrize("probe", ["version", "registration", "validation"])
def test_manual_c_validator_native_process_receipts_keep_legacy_behavior(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
) -> None:
    """Exact native process evidence retains version, plugin and exit policy."""

    def native_run(
        args: list[str], **options: object
    ) -> subprocess.CompletedProcess[str]:
        capture = options.get("capture_output") is True
        output = (
            "clang version 22.1.8\n"
            if probe == "version"
            else "\n".join(sorted(validator.PLUGIN_CHECKS))
        )
        return subprocess.CompletedProcess(
            args,
            7 if probe == "validation" else 0,
            stdout=output if capture else None,
            stderr="" if capture else None,
        )

    monkeypatch.setattr(subprocess, "run", native_run)
    executable = Path("/synthetic/clang")
    if probe == "version":
        assert "version 22.1.8" in validator._tool_version_output(executable, "Clang")
    elif probe == "registration":
        validator._require_plugin_registration(executable, Path("/synthetic/plugin"))
    else:
        assert validator._run([str(executable), "--version"]) == 7


def test_manual_c_validator_foreign_contract_failure_preserves_safe_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign ValueError from canonical ABI cannot format itself."""

    class ForeignContractFailure(ValueError):
        def __str__(self) -> str:
            raise AssertionError("foreign canonical contract formatter executed")

    fault = ForeignContractFailure("private manifest detail")

    def reject_abi() -> Never:
        raise fault

    monkeypatch.setattr(validator, "_require_file", lambda *_args: None)
    monkeypatch.setattr(validator, "_require_llvm_version", lambda *_args: None)
    monkeypatch.setattr(validator, "_default_plugin", lambda *_args: None)
    monkeypatch.setattr(validator.c_abi, "canonical_projection", reject_abi)
    with pytest.raises(validator.InputError, match="ForeignContractFailure") as caught:
        _ = validator._configuration(validator._Arguments())
    assert "private manifest detail" not in str(caught.value)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "boundary", ("required-tool", "default-host", "default-library", "default-plugin")
)
@pytest.mark.parametrize(
    "receipt_kind", ("missing", "falsey", "truthy", "text", "hostile")
)
def test_manual_c_tool_admission_requires_native_file_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    receipt_kind: str,
) -> None:
    """A forged file verdict cannot select or admit compiler plugin evidence."""
    host = tmp_path / "clang-tidy"
    library = tmp_path / "plugin.so"
    _ = host.write_text("host", encoding="utf-8")
    _ = library.write_text("plugin", encoding="utf-8")
    monkeypatch.setattr(validator, "PLUGIN_HOST", host)
    monkeypatch.setattr(validator, "PLUGIN_LIBRARY", library)
    target = library if boundary in ("default-library", "default-plugin") else host
    native = Path.is_file

    class ForeignVerdict:
        def __bool__(self) -> Never:
            raise AssertionError("foreign compiler file truthiness executed")

    forged: object = {
        "missing": None,
        "falsey": 0,
        "truthy": 1,
        "text": "yes",
        "hostile": ForeignVerdict(),
    }[receipt_kind]

    def forged_file(path: Path) -> bool:
        return cast("bool", forged) if path == target else native(path)

    monkeypatch.setattr(Path, "is_file", forged_file)
    with pytest.raises(validator.InputError, match="status receipt"):
        if boundary == "required-tool":
            validator._require_file(host, "clang-tidy")
        elif boundary in ("default-host", "default-library"):
            _ = validator._default_clang_tidy()
        else:
            _ = validator._default_plugin(host)


def test_manual_c_tool_admission_preserves_native_default_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native file verdicts retain the reviewed host/plugin fallback rules."""
    host = tmp_path / "malbolge-clang-tidy"
    library = tmp_path / "malbolge-plugin.so"
    _ = host.write_bytes(b"host")
    _ = library.write_bytes(b"plugin")
    monkeypatch.setattr(validator, "PLUGIN_HOST", host)
    monkeypatch.setattr(validator, "PLUGIN_LIBRARY", library)
    assert validator._default_clang_tidy() == host
    assert validator._default_plugin(host) == library
    validator._require_file(host, "clang-tidy")

    library.unlink()
    assert validator._default_clang_tidy() == validator.PINNED_CLANG_TIDY
    assert validator._default_plugin(host) is None
    with pytest.raises(validator.InputError, match="not found"):
        validator._require_file(library, "clang-tidy plugin")


@pytest.mark.parametrize(
    "boundary",
    ("clang-tidy", "clang", "profile", "plugin", "default-host", "default-plugin"),
)
@pytest.mark.parametrize("receipt_kind", ("opaque", "text", "hostile"))
def test_manual_c_tool_resolution_requires_native_path_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    receipt_kind: str,
) -> None:
    """Compiler and implicit plugin resolution cannot admit foreign path hooks."""
    host = tmp_path / "clang-tidy"
    clang = tmp_path / "clang"
    profile = tmp_path / "profile.yaml"
    plugin = tmp_path / "plugin.so"
    for path in (host, clang, profile, plugin):
        _ = path.write_bytes(b"fixture")
    arguments = validator._Arguments()
    arguments.clang_tidy = host
    arguments.clang = clang
    arguments.profile = profile
    arguments.plugin = plugin
    monkeypatch.setattr(validator, "PLUGIN_HOST", host)
    monkeypatch.setattr(validator, "PLUGIN_LIBRARY", plugin)
    target = {
        "clang-tidy": host,
        "clang": clang,
        "profile": profile,
        "plugin": plugin,
        "default-host": host,
        "default-plugin": plugin,
    }[boundary]

    class ForeignPath:
        @override
        def __eq__(self, other: object) -> Never:
            del self, other
            raise AssertionError("foreign resolved-path equality hook executed")

    receipt: object = {
        "opaque": object(),
        "text": "/foreign/tool",
        "hostile": ForeignPath(),
    }[receipt_kind]
    native_resolve = Path.resolve

    def forged_resolve(path: Path, strict: bool = False) -> Path:
        return (
            cast("Path", receipt)
            if path == target
            else native_resolve(path, strict=strict)
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "resolve", forged_resolve)
        with pytest.raises(validator.InputError, match="resolved-path receipt"):
            if boundary in ("default-host", "default-plugin"):
                _ = validator._default_plugin(host)
            else:
                _ = validator._configuration(arguments)


@pytest.mark.parametrize(
    ("method", "receipt"),
    [
        ("exists", 0),
        ("exists", None),
        ("is_dir", 0),
        ("is_dir", None),
        ("is_file", 0),
        ("is_file", 1),
    ],
)
def test_manual_c_selection_rejects_non_native_source_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    receipt: object,
) -> None:
    """Explicit C selection cannot trust foreign truthy or falsey status."""
    source = tmp_path / "unit.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    native = getattr(Path, method)

    def forged_status(path: Path) -> object:
        return receipt if path == source else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, method, forged_status)
        with pytest.raises(validator.InputError, match="status receipt"):
            _ = validator._validated_files([str(source)])


@pytest.mark.parametrize("location", ["root", "leaf"])
@pytest.mark.parametrize("method", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("receipt", [0, None, 0.0])
def test_manual_c_selection_rejects_non_native_redirect_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
    method: str,
    receipt: object,
) -> None:
    """Recursive Doom admission only trusts exact native redirect booleans."""
    doom = tmp_path / "doom"
    doom.mkdir()
    source = doom / "unit.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    target = doom if location == "root" else source
    native = getattr(Path, method)

    def forged_status(path: Path) -> object:
        return receipt if path == target else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, method, forged_status)
        with pytest.raises(validator.InputError, match="redirect"):
            _ = validator._validated_files([str(doom)])


@pytest.mark.parametrize("receipt", [0, None, 1.0])
def test_manual_c_selection_rejects_non_native_recursive_file_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Discovered Doom source files require native regular-file results."""
    doom = tmp_path / "doom"
    doom.mkdir()
    source = doom / "unit.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    native = Path.is_file

    def forged_status(path: Path) -> object:
        return receipt if path == source else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_file", forged_status)
        with pytest.raises(validator.InputError, match="status receipt"):
            _ = validator._validated_files([str(doom)])


@pytest.mark.parametrize("receipt", [object(), "/foreign/unit.c"])
def test_manual_c_selection_rejects_non_native_resolved_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """A path-resolution result may not smuggle a foreign path wrapper."""
    source = tmp_path / "unit.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    native = Path.resolve

    def forged_resolve(path: Path, strict: bool = False) -> object:
        return receipt if path == source else native(path, strict=strict)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "resolve", forged_resolve)
        with pytest.raises(validator.InputError, match="resolved-path receipt"):
            _ = validator._validated_files([str(source)])


def test_manual_c_selection_rejects_foreign_recursive_entry_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign recursive entry cannot supply path-status hooks."""
    doom = tmp_path / "doom"
    doom.mkdir()
    source = doom / "unit.c"
    _ = source.write_text("int value;\n", encoding="utf-8")
    native = Path.rglob

    class ForeignEntry:
        def __getattribute__(self, _name: str) -> object:
            raise AssertionError("foreign recursive-entry hook evaluated")

    def forged_rglob(path: Path, pattern: str) -> object:
        return iter([ForeignEntry()]) if path == doom else native(path, pattern)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "rglob", forged_rglob)
        with pytest.raises(validator.InputError, match="entry.*receipt"):
            _ = validator._validated_files([str(doom)])


def test_manual_c_selection_keeps_explicit_alias_and_physical_doom_nesting(
    tmp_path: Path,
) -> None:
    """Native source selection preserves reviewed aliases and nested trees."""
    source = tmp_path / "physical.c"
    _ = source.write_text("int physical;\n", encoding="utf-8")
    alias = tmp_path / "alias.c"
    try:
        alias.symlink_to(source)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlink unavailable: {error}")
    assert validator._validated_files([str(alias)]) == (source,)
    nested = tmp_path / "doom" / "src"
    nested.mkdir(parents=True)
    child = nested / "unit.c"
    _ = child.write_text("int unit;\n", encoding="utf-8")
    assert validator._validated_files([str(tmp_path / "doom")]) == (child,)


def test_manual_c_selection_keeps_redirect_rejection_for_recursive_doom(
    tmp_path: Path,
) -> None:
    """A genuinely linked recursive leaf is still refused deterministically."""
    doom = tmp_path / "doom"
    doom.mkdir()
    outside = tmp_path / "outside.c"
    _ = outside.write_text("int outside;\n", encoding="utf-8")
    link = doom / "alias.c"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlink unavailable: {error}")
    with pytest.raises(
        validator.InputError, match="recursive doom entry must not redirect"
    ):
        _ = validator._validated_files([str(doom)])


MUTATE_EXECUTABLE = "executable"
MUTATE_APPEND = "append"
MUTATE_REMOVE = "remove"


@pytest.mark.parametrize(
    "probe", [PROBE_VERSION, PROBE_REGISTRATION, "validation"]
)
@pytest.mark.parametrize(
    "mutation", [MUTATE_EXECUTABLE, MUTATE_APPEND, MUTATE_REMOVE]
)
def test_manual_validator_rejects_mutated_subprocess_invocation(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    mutation: str,
) -> None:
    """A borrowed argument list cannot certify its own altered invocation."""

    def mutate_run(
        command: list[str], **options: object
    ) -> subprocess.CompletedProcess[str]:
        if mutation == MUTATE_EXECUTABLE:
            command[0] = "/foreign/clang"
        elif mutation == MUTATE_APPEND:
            command.append("--foreign-option")
        else:
            _ = command.pop()
        capturing = options.get("capture_output") is True
        output = (
            "clang version 22.1.8\n"
            if probe == PROBE_VERSION
            else "\n".join(sorted(validator.PLUGIN_CHECKS))
        )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=output if capturing else None,
            stderr="" if capturing else None,
        )

    monkeypatch.setattr(subprocess, "run", mutate_run)
    with pytest.raises(
        validator.InputError, match=r"invalid .* process receipt"
    ):
        _execute_probe(probe, Path("/synthetic/clang"))
