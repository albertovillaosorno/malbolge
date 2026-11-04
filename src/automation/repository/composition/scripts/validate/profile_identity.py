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
#   - Fingerprint and verify one external Malbolge target-profile identity.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Fingerprint and verify one external Malbolge target-profile identity."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TextIO

from scripts.validate import target_profile

ARGUMENT_COUNT_MAX = 2
ARGUMENT_COUNT_MIN = 1
PYTHON_JIG = r".\.dependencies\python\3.14.7\Scripts\python-jig.cmd"
MODULE_COMMAND = f"{PYTHON_JIG} -m scripts.validate.profile_identity"


class ProfileIdentityCliError(ValueError):
    """Invalid profile-identity command-line invocation."""


def _safe_error_detail(error: Exception) -> str:
    """Describe trusted native failures without invoking foreign formatters.

    Returns:
        Native diagnostic text, or the foreign exception type name.

    """
    if type(error) in (
        ProfileIdentityCliError,
        target_profile.ProfileValidationError,
        OSError,
        PermissionError,
        FileNotFoundError,
    ):
        return str(error)
    return type(error).__name__


def _write_record(stream: TextIO, message: str) -> bool:
    """Require a complete native text write and completed flush.

    A partial record must not certify a successful identity or help response.
    Diagnostic failures remain failures even if stderr is unavailable.

    Returns:
        Whether the complete record was emitted.

    """
    try:
        written = stream.write(message)
        if type(written) is not int or written != len(message):
            return False
        return stream.flush() is None
    except (
        AttributeError,
        IndexError,
        OSError,
        OverflowError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return False


def _write_stdout(message: str) -> None:
    if not _write_record(sys.stdout, message):
        raise ProfileIdentityCliError("profile identity output write or flush failed")


def _arguments(arguments: list[str]) -> tuple[Path, str | None]:
    if type(arguments) is not list or any(
        type(argument) is not str for argument in arguments
    ):
        message = "CLI requires native CLI argument list and string tokens"
        raise ProfileIdentityCliError(message)
    if arguments in (["-h"], ["--help"]):
        usage = f"usage: {MODULE_COMMAND} PROFILE.json [EXPECTED-FINGERPRINT]\n"
        _write_stdout(usage)
        raise SystemExit(0)
    argument_count = len(arguments)
    if not ARGUMENT_COUNT_MIN <= argument_count <= ARGUMENT_COUNT_MAX:
        message = "expected profile path and optional fingerprint"
        raise ProfileIdentityCliError(message)
    expected = arguments[1] if argument_count == ARGUMENT_COUNT_MAX else None
    return Path(arguments[0]), expected


def _fingerprint(
    document: target_profile.JsonObject,
    expected: str | None,
) -> tuple[str, str]:
    canonical = target_profile.load_document(target_profile.DEFAULT_PROFILE)
    profile_id, _ = target_profile.validate_custom_profile_document(
        document,
        canonical,
    )
    if expected is None:
        fingerprint = target_profile.custom_profile_fingerprint(
            document,
            canonical,
        )
    else:
        fingerprint = target_profile.verify_custom_profile_fingerprint(
            document,
            canonical,
            expected,
        )
    return profile_id, fingerprint


def main() -> int:
    """Fingerprint or verify one external profile and return process status.

    Returns:
        Zero for a valid identity and one for deterministic validation failure.

    """
    try:
        path, expected = _arguments(sys.argv[1:])
        document = target_profile.load_document(path)
        profile_id, fingerprint = _fingerprint(document, expected)
        _write_stdout(f"profile={profile_id} fingerprint={fingerprint}\n")
    except (
        OSError,
        ProfileIdentityCliError,
        target_profile.ProfileValidationError,
    ) as error:
        _ = _write_record(sys.stderr, f"error: {_safe_error_detail(error)}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
