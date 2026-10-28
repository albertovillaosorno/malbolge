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
#   - Independent read-only replay binding of deterministic challenge bundles.
# - Must-Not:
#   - Prove compiled output, measure algorithm performance, or execute guests.
# - Allows:
#   - Inputs: admitted arena case, profile and retained generator payload bytes.
#   - Outputs: independently regenerated source digest on exact byte agreement.
#   - Side effects: no bundle publication or filesystem writes.
# - Split-When:
#   - Other challenge generators need separate explicit replay adapters.
# - Merge-When:
#   - A governed generator validator owns the same independent bundle replay.
# - Summary:
#   - Prevents unverifiable workload hashes from standing in for C challenges.
# - Description:
#   - Reuses the completed parametric source/oracle generator as authority.
# - Usage:
#   - Called by optional arena evidence challenge-root preflight.
# - Defaults:
#   - Unsupported families, profiles, or altered bundle bytes reject.
#

"""Replay completed parametric generator outputs without running guest code."""

from __future__ import annotations

from hashlib import sha256
from typing import Any
from typing import Never

from benchmarks.challenges import generate

MAX_BUNDLE_CASES = 64
MAX_BUNDLE_NODES = 4096
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_MANIFEST_BYTES = 32 * 1024
ORACLE_BYTES = 4
BUNDLE_FILES = ("program.c", "oracle.bin", "manifest.json")


class ChallengeBundleError(ValueError):
    """A retained source/oracle bundle differs from canonical generation."""


def _fail(message: str) -> Never:
    raise ChallengeBundleError(message)


def _bounded_case(case: dict[str, Any]) -> None:
    if case["difficulty"] > MAX_BUNDLE_NODES:
        _fail("challenge replay exceeds 4096-node preflight limit")


def _regenerate(
    case: dict[str, Any], profile: str
) -> generate.GeneratedChallenge:
    try:
        identity = generate.ChallengeIdentity(
            family=case["family"],
            version=case["version"],
            seed=case["seed"],
            profile=profile,
            nodes=case["difficulty"],
        )
        return generate.generate(identity)
    except generate.ChallengeError as error:
        message = f"challenge identity cannot regenerate: {error}"
        raise ChallengeBundleError(message) from error


def verify_bundle(
    case: dict[str, Any],
    profile: str,
    files: dict[str, bytes],
) -> str:
    """Reproduce exact canonical source/oracle/manifest for one challenge.

    Returns:
        Independently regenerated C source SHA-256 identity.

    """
    _bounded_case(case)
    if set(files) != set(BUNDLE_FILES):
        _fail("challenge bundle must include all three canonical files")
    if len(files["oracle.bin"]) != ORACLE_BYTES:
        _fail("challenge bundle oracle must be four bytes")
    produced = _regenerate(case, profile)
    originals = (produced.source, produced.oracle, produced.manifest)
    if any(
        files[name] != expected
        for name, expected in zip(BUNDLE_FILES, originals, strict=True)
    ):
        _fail(
            "retained challenge bundle differs from deterministic regeneration"
        )
    source_hash = sha256(produced.source).hexdigest()
    if source_hash != case["workload_sha256"]:
        _fail("arena workload SHA-256 differs from regenerated C source")
    return source_hash
