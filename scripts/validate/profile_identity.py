# File:
#   - profile_identity.py
# Path:
#   - scripts/validate/profile_identity.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Fingerprint and verify one external Malbolge target-profile identity."""

from __future__ import annotations

from pathlib import Path
import sys

from scripts.validate import target_profile

ARGUMENT_COUNT_MAX = 2
ARGUMENT_COUNT_MIN = 1
PYTHON_JIG = r".\.dependencies\python\3.14.6\Scripts\python-jig.cmd"
MODULE_COMMAND = f"{PYTHON_JIG} -m scripts.validate.profile_identity"


class ProfileIdentityCliError(ValueError):
    """Invalid profile-identity command-line invocation."""


def _arguments(arguments: list[str]) -> tuple[Path, str | None]:
    if arguments in (["-h"], ["--help"]):
        usage = f"usage: {MODULE_COMMAND} PROFILE.json [EXPECTED-FINGERPRINT]\n"
        _ = sys.stdout.write(usage)
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
        document = target_profile.load_document(path.resolve())
        profile_id, fingerprint = _fingerprint(document, expected)
    except (
        OSError,
        ProfileIdentityCliError,
        target_profile.ProfileValidationError,
    ) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(f"profile={profile_id} fingerprint={fingerprint}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
