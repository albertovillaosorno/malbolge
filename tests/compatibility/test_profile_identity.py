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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Canonical and custom Malbolge target-profile identity tests.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Canonical and custom Malbolge target-profile identity tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast, final, override

import pytest

from scripts.validate import profile_identity
from scripts.validate import target_profile as validator

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = (
    ROOT
    / "src/interoperability/profile-compatibility/contract"
    / "custom-profile.example.json"
)
PROFILE_PATH = ROOT / "malbolge.json"
CURRENT_PROFILE = "malbolge-2026"
NATIVE_CLI_MESSAGE = "native CLI"
CUSTOM_PROFILE = "custom-14-example"
EXAMPLE_FINGERPRINT = (
    "malbolge-profile-v1:sha256:"
    "221015e0ac4cbde88444ad6d55c703a2e2cc96904bd65b81cb44e256aa1f3177"
)
MISMATCH_FINGERPRINT = "malbolge-profile-v1:sha256:" + ("0" * 64)
FOURTEEN_TRIT_WORDS = 4_782_969


def _clone(document: validator.JsonObject) -> validator.JsonObject:
    text = json.dumps(document, sort_keys=False)
    return validator.loads_document(text)


def _object(value: validator.JsonValue) -> validator.JsonObject:
    assert isinstance(value, dict)
    return value


def _string(value: validator.JsonValue) -> str:
    assert isinstance(value, str)
    return value


def _canonical() -> validator.JsonObject:
    return validator.load_document(PROFILE_PATH)


def _example() -> validator.JsonObject:
    return validator.load_document(EXAMPLE_PATH)


def _external_for_canonical(profile_id: str) -> validator.JsonObject:
    canonical = _canonical()
    profiles = _object(canonical["profiles"])
    profile = _object(profiles[profile_id])
    definition: validator.JsonObject = {
        "memory": _object(profile["memory"]),
        "semantics": _object(profile["semantics"]),
        "version": _string(profile["version"]),
        "word": _object(profile["word"]),
    }
    return {
        "profile": definition,
        "profile_id": profile_id,
        "schema_version": validator.CUSTOM_PROFILE_SCHEMA_VERSION,
        "target_schema_version": validator.SCHEMA_VERSION,
    }


def _expect_profile_invalid(document: validator.JsonObject) -> None:
    try:
        _ = validator.custom_profile_fingerprint(document, _canonical())
    except validator.ProfileValidationError:
        return
    message = "custom profile validation unexpectedly succeeded"
    raise AssertionError(message)


def _mismatch_message(document: validator.JsonObject) -> str | None:
    try:
        _ = validator.verify_custom_profile_fingerprint(
            document,
            _canonical(),
            MISMATCH_FINGERPRINT,
        )
    except validator.ProfileFingerprintMismatchError as error:
        return str(error)
    return None


def test_example_custom_profile_has_stable_fingerprint() -> None:
    """The versioned custom example locks canonicalization output."""
    observed = validator.custom_profile_fingerprint(_example(), _canonical())
    assert observed == EXAMPLE_FINGERPRINT


def test_canonical_profile_external_form_has_same_fingerprint() -> None:
    """External and registry forms bind to one immutable profile identity."""
    canonical = _canonical()
    external = _external_for_canonical(CURRENT_PROFILE)
    external_fingerprint = validator.custom_profile_fingerprint(
        external,
        canonical,
    )
    registry_fingerprint = validator.profile_fingerprint(
        canonical,
        CURRENT_PROFILE,
    )
    assert external_fingerprint == registry_fingerprint


def test_json_key_order_does_not_change_fingerprint() -> None:
    """Canonicalization ignores object insertion order and source whitespace."""
    document = _example()
    profile = _object(document["profile"])
    reordered_profile: validator.JsonObject = {
        key: profile[key] for key in reversed(tuple(profile))
    }
    reordered: validator.JsonObject = {
        key: document[key] for key in reversed(tuple(document))
    }
    reordered["profile"] = reordered_profile
    assert validator.custom_profile_fingerprint(
        reordered,
        _canonical(),
    ) == validator.custom_profile_fingerprint(document, _canonical())


def test_custom_profile_id_participates_in_identity() -> None:
    """Identical geometry under another published ID receives another hash."""
    original = _example()
    renamed = _clone(original)
    renamed["profile_id"] = "custom-14-renamed"
    assert validator.custom_profile_fingerprint(
        original,
        _canonical(),
    ) != validator.custom_profile_fingerprint(renamed, _canonical())


def test_custom_profile_cannot_change_semantic_core() -> None:
    """Custom geometry cannot turn sequential Malbolge into another language."""
    changed = _clone(_example())
    profile = _object(changed["profile"])
    semantics = _object(profile["semantics"])
    semantics["guest_order"] = "parallel"
    _expect_profile_invalid(changed)


def test_canonical_id_cannot_be_redefined_externally() -> None:
    """A canonical profile ID cannot be rebound to different geometry."""
    changed = _external_for_canonical(CURRENT_PROFILE)
    profile = _object(changed["profile"])
    word = _object(profile["word"])
    memory = _object(profile["memory"])
    semantics = _object(profile["semantics"])
    word["trits"] = 14
    word["modulus"] = FOURTEEN_TRIT_WORDS
    memory["words"] = FOURTEEN_TRIT_WORDS
    semantics["eof_word"] = FOURTEEN_TRIT_WORDS - 1
    _expect_profile_invalid(changed)


def test_artifact_fingerprint_mismatch_has_stable_diagnostic() -> None:
    """An external config mismatch is detected instead of reinterpreted."""
    expected = " ".join(
        (
            "MALBOLGE-PROFILE-ID-001",
            f"profile={CUSTOM_PROFILE}",
            f"expected={MISMATCH_FINGERPRINT}",
            f"observed={EXAMPLE_FINGERPRINT}",
        )
    )
    assert _mismatch_message(_example()) == expected


def test_profile_identity_cli_refuses_linked_external_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI must not erase a redirected pathname before loader admission."""
    source = tmp_path / "profile.json"
    _ = source.write_bytes(EXAMPLE_PATH.read_bytes())
    linked = tmp_path / "profile-link.json"
    try:
        linked.symlink_to(source)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unsupported on this platform: {error}")
    monkeypatch.setattr(sys, "argv", ["profile_identity", str(linked)])
    assert profile_identity.main() == 1
    result = capsys.readouterr()
    assert result.err.startswith(
        "error: target-profile document must be a regular file"
    )
    assert not result.out


@pytest.mark.parametrize(
    "fault_type",
    [
        OSError,
        profile_identity.ProfileIdentityCliError,
        validator.ProfileValidationError,
    ],
)
def test_profile_identity_cli_never_formats_foreign_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """Host/profile error hooks cannot conceal deterministic CLI rejection."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign profile identity error formatter executed")

    foreign = type("ForeignIdentityFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe profile identity diagnostic")

    def fail_load(_path: Path) -> None:
        raise fault

    monkeypatch.setattr(validator, "load_document", fail_load)
    monkeypatch.setattr(sys, "argv", ["profile_identity", str(EXAMPLE_PATH)])
    assert profile_identity.main() == 1
    output = capsys.readouterr()
    assert not output.out
    assert "ForeignIdentityFault" in output.err


def test_profile_identity_cli_native_failure_retains_diagnostic(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exact built-in profile errors retain useful operator details."""
    fault = validator.ProfileValidationError("external profile fingerprint mismatch")

    def fail_load(_path: Path) -> None:
        raise fault

    monkeypatch.setattr(validator, "load_document", fail_load)
    monkeypatch.setattr(sys, "argv", ["profile_identity", str(EXAMPLE_PATH)])
    assert profile_identity.main() == 1
    assert "external profile fingerprint mismatch" in capsys.readouterr().err


def test_profile_identity_cli_rejects_short_success_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A partial fingerprint record must never receive a success status."""

    @final
    class ShortWriter:
        def write(self, text: str) -> int:
            return len(text) - 1

        def flush(self) -> None:
            raise AssertionError("flush after short write")

    monkeypatch.setattr(sys, "argv", ["profile_identity", str(EXAMPLE_PATH)])
    monkeypatch.setattr(sys, "stdout", ShortWriter())
    assert profile_identity.main() == 1
    assert "output" in capsys.readouterr().err


@final
class _ForeignWriteCount(int):
    """An untrusted write-count subclass with unsafe comparison behavior."""

    @override
    def __eq__(self, other: object) -> bool:
        del other
        raise AssertionError("foreign write-count equality executed")


@pytest.mark.parametrize("invocation", ("fingerprint", "help"))
@pytest.mark.parametrize(
    "receipt",
    ("short", "excess", "bool", "subclass", "none", "write-error", "flush-error", "flush-receipt"),
)
def test_profile_identity_cli_requires_exact_output_receipts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    invocation: str,
    receipt: str,
) -> None:
    """Incomplete help/fingerprint output cannot be reported as success."""
    flushes: list[bool] = []

    @final
    class HostileWriter:
        def write(self, text: str) -> int:
            if receipt == "write-error":
                raise OSError("injected output write failure")
            values: dict[str, object] = {
                "short": len(text) - 1,
                "excess": len(text) + 1,
                "bool": True,
                "subclass": _ForeignWriteCount(len(text)),
                "none": None,
            }
            return cast("int", values.get(receipt, len(text)))

        def flush(self) -> None:
            flushes.append(True)
            if receipt == "flush-error":
                raise ValueError("injected output flush failure")
            if receipt == "flush-receipt":
                return cast("None", cast("object", True))
            return None

    argv = ["profile_identity", "--help" if invocation == "help" else str(EXAMPLE_PATH)]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(sys, "stdout", HostileWriter())
    assert profile_identity.main() == 1
    assert "output" in capsys.readouterr().err
    assert bool(flushes) == (receipt in ("flush-error", "flush-receipt"))


@pytest.mark.parametrize("receipt", ("short", "write-error", "flush-error", "bad-flush"))
def test_profile_identity_cli_diagnostic_delivery_cannot_flip_failed_status(
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """A failed command stays failed when stderr delivery is unreliable."""

    @final
    class BrokenStderr:
        def write(self, text: str) -> int:
            if receipt == "write-error":
                raise OSError("unavailable stderr")
            return len(text) - 1 if receipt == "short" else len(text)

        def flush(self) -> None:
            if receipt == "flush-error":
                raise RuntimeError("unavailable stderr flush")
            if receipt == "bad-flush":
                return cast("None", cast("object", True))
            return None

    monkeypatch.setattr(sys, "argv", ["profile_identity"])
    monkeypatch.setattr(sys, "stderr", BrokenStderr())
    assert profile_identity.main() == 1


def test_profile_identity_cli_native_output_has_exact_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Normal output reports the admitted external identity exactly."""
    monkeypatch.setattr(sys, "argv", ["profile_identity", str(EXAMPLE_PATH)])
    assert profile_identity.main() == 0
    result = capsys.readouterr()
    assert not result.err
    assert result.out == f"profile={CUSTOM_PROFILE} fingerprint={EXAMPLE_FINGERPRINT}\n"


@final
class _ForeignCliArgument:
    """Adversarial caller value with executable comparison behavior."""

    __hash__ = object.__hash__

    @override
    def __eq__(self, other: object) -> bool:
        """Detect an unsafe argument comparison.

        Raises:
            AssertionError: If equality executes before argument admission.

        """
        del other
        message = "foreign profile CLI equality executed"
        raise AssertionError(message)


@final
class _ForeignCliString(str):  # ruff: ignore[subclass-builtin]
    """String subclass cannot masquerade as a trusted CLI token."""

    __slots__: tuple[str, ...] = ()

    @override
    def __eq__(self, other: object) -> bool:
        """Detect an unsafe string comparison.

        Raises:
            AssertionError: If equality executes before argument admission.

        """
        del other
        message = "foreign profile CLI string equality executed"
        raise AssertionError(message)

    __hash__ = str.__hash__


@final
class _ForeignCliList(list[str]):  # ruff: ignore[subclass-builtin]
    """List subclass cannot own CLI argument-sequence equality."""

    __hash__ = None

    @override
    def __eq__(self, other: object) -> bool:
        """Detect an unsafe sequence comparison.

        Raises:
            AssertionError: If equality executes before argument admission.

        """
        del other
        message = "foreign profile CLI list equality executed"
        raise AssertionError(message)


@pytest.mark.parametrize(
    "supplied",
    [
        [_ForeignCliArgument()],
        [_ForeignCliString("--help")],
        _ForeignCliList(["--help"]),
        ["profile.json", _ForeignCliArgument()],
        ["profile.json", _ForeignCliString("fingerprint")],
    ],
)
def test_profile_identity_rejects_foreign_cli_arguments_before_comparison(
    supplied: object,
) -> None:
    """Neither caller-owned containers nor tokens may execute equality hooks."""
    arguments = cast(
        "Callable[[list[str]], tuple[Path, str | None]]",
        vars(profile_identity)["_arguments"],
    )
    with pytest.raises(
        profile_identity.ProfileIdentityCliError, match="native CLI"
    ):
        _ = arguments(cast("list[str]", supplied))


def test_profile_identity_cli_main_rejects_foreign_argument_without_hook(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI errors remain typed, deterministic and safely rendered."""
    monkeypatch.setattr(
        sys, "argv", ["profile_identity", _ForeignCliArgument()]
    )
    assert profile_identity.main() == 1
    output = capsys.readouterr()
    assert not output.out
    assert NATIVE_CLI_MESSAGE in output.err
