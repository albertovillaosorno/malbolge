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
MAX_BUNDLE_VERSION_BITS = 64
SHA256_HEX_LENGTH = 64
SHA256_ALPHABET = frozenset("0123456789abcdef")
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_MANIFEST_BYTES = 32 * 1024
ORACLE_BYTES = 4
BUNDLE_FILES = ("program.c", "oracle.bin", "manifest.json")
CASE_FIELDS = frozenset({
    "family",
    "version",
    "seed",
    "difficulty",
    "workload_sha256",
})


class ChallengeBundleError(ValueError):
    """A retained source/oracle bundle differs from canonical generation."""


def _fail(message: str) -> Never:
    raise ChallengeBundleError(message)


def _bounded_case(case: dict[str, Any]) -> None:
    if (
        type(case) is not dict
        or any(type(key) is not str for key in case)
        or set(case) != CASE_FIELDS
    ):
        _fail("challenge replay requires an exact arena case")
    if (
        type(case["family"]) is not str
        or type(case["workload_sha256"]) is not str
    ):
        _fail("challenge replay requires string identity fields")
    if type(case["version"]) is not int or type(case["seed"]) is not int:
        _fail("challenge replay requires integer identity fields")
    digest = case["workload_sha256"]
    if len(digest) != SHA256_HEX_LENGTH or not set(digest) <= SHA256_ALPHABET:
        _fail("challenge replay requires lowercase SHA-256 workload digest")
    if case["version"].bit_length() > MAX_BUNDLE_VERSION_BITS:
        _fail("challenge replay requires a bounded version identity")
    nodes = case["difficulty"]
    if type(nodes) is not int or nodes < 1:
        _fail("challenge replay requires positive integer nodes")
    if nodes > MAX_BUNDLE_NODES:
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
        produced = generate.generate(identity)
    except generate.ChallengeError as error:
        message = "challenge identity cannot regenerate"
        raise ChallengeBundleError(message) from error
    except Exception as error:
        # The canonical generator is a dependency, not an exception authority.
        # Unexpected ordinary faults must also fail through the typed replay
        # boundary, without formatting caller-defined exception hooks.
        message = "challenge canonical regeneration dependency failed"
        raise ChallengeBundleError(message) from error
    # Only exact native generator output can serve as comparison evidence.
    # A foreign bytes subclass could override equality to admit forged data.
    if type(produced) is not generate.GeneratedChallenge:
        _fail("canonical challenge regeneration produced invalid payload")
    try:
        payloads = (produced.source, produced.oracle, produced.manifest)
    except Exception as error:
        # A malformed native result may have unset slots. Do not expose the
        # dependency's raw attribute fault through the replay boundary.
        message = "canonical challenge regeneration produced invalid payload"
        raise ChallengeBundleError(message) from error
    if any(type(payload) is not bytes for payload in payloads):
        _fail("canonical challenge regeneration produced invalid payload")
    return produced


def _admit_files(files: dict[str, bytes]) -> None:
    if (
        type(files) is not dict
        or any(type(key) is not str for key in files)
        or set(files) != set(BUNDLE_FILES)
    ):
        _fail("challenge bundle must include all three canonical files")
    if any(type(files[name]) is not bytes for name in BUNDLE_FILES):
        _fail("challenge bundle payloads must be byte strings")
    if len(files["oracle.bin"]) != ORACLE_BYTES:
        _fail("challenge bundle oracle must be four bytes")
    if len(files["program.c"]) > MAX_SOURCE_BYTES or (
        len(files["manifest.json"]) > MAX_MANIFEST_BYTES
    ):
        _fail("challenge bundle payload exceeds replay byte limit")


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
    _admit_files(files)
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
