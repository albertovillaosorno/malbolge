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

import hashlib
from hashlib import sha256
from typing import Any, Never

from benchmarks.challenges import generate

# Keep a source-byte reference when both public digest providers are replaced.
_NATIVE_SHA256 = sha256
# Retain original collection and pairing semantics for source admission.
_NATIVE_TYPE = type
_NATIVE_DICT = dict
_NATIVE_STR = str
_NATIVE_INT = int
_NATIVE_BYTES = bytes
_NATIVE_SET = set
_NATIVE_ZIP = zip
_NATIVE_ANY = any
_NATIVE_LEN = len
# Do not let a runtime substitution become the replay oracle itself.
_CANONICAL_GENERATE = generate.generate
_CANONICAL_IDENTITY = generate.ChallengeIdentity
_CANONICAL_RESULT = generate.GeneratedChallenge
# A substituted public error alias must not break the typed failure boundary.
_CANONICAL_ERROR = generate.ChallengeError

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
# Replay eligibility must not be widened by late mutations of public policy.
_SOURCE_MAX_BUNDLE_NODES = MAX_BUNDLE_NODES
_SOURCE_MAX_BUNDLE_VERSION_BITS = MAX_BUNDLE_VERSION_BITS
_SOURCE_SHA256_HEX_LENGTH = SHA256_HEX_LENGTH
_SOURCE_SHA256_ALPHABET = SHA256_ALPHABET
_SOURCE_MAX_SOURCE_BYTES = MAX_SOURCE_BYTES
_SOURCE_MAX_MANIFEST_BYTES = MAX_MANIFEST_BYTES
_SOURCE_ORACLE_BYTES = ORACLE_BYTES
_SOURCE_BUNDLE_FILES = BUNDLE_FILES
_SOURCE_CASE_FIELDS = CASE_FIELDS


class ChallengeBundleError(ValueError):
    """A retained source/oracle bundle differs from canonical generation."""


def _fail(message: str) -> Never:
    raise ChallengeBundleError(message)


def _bounded_case(case: dict[str, Any]) -> None:
    if (
        _NATIVE_TYPE(case) is not _NATIVE_DICT
        or _NATIVE_ANY(_NATIVE_TYPE(key) is not _NATIVE_STR for key in case)
        or _NATIVE_SET(case) != _SOURCE_CASE_FIELDS
    ):
        _fail("challenge replay requires an exact arena case")
    if (
        _NATIVE_TYPE(case["family"]) is not _NATIVE_STR
        or _NATIVE_TYPE(case["workload_sha256"]) is not _NATIVE_STR
    ):
        _fail("challenge replay requires string identity fields")
    if (
        _NATIVE_TYPE(case["version"]) is not _NATIVE_INT
        or _NATIVE_TYPE(case["seed"]) is not _NATIVE_INT
    ):
        _fail("challenge replay requires integer identity fields")
    digest = case["workload_sha256"]
    if (
        _NATIVE_LEN(digest) != _SOURCE_SHA256_HEX_LENGTH
        or not _NATIVE_SET(digest) <= _SOURCE_SHA256_ALPHABET
    ):
        _fail("challenge replay requires lowercase SHA-256 workload digest")
    if case["version"].bit_length() > _SOURCE_MAX_BUNDLE_VERSION_BITS:
        _fail("challenge replay requires a bounded version identity")
    nodes = case["difficulty"]
    if _NATIVE_TYPE(nodes) is not _NATIVE_INT or nodes < 1:
        _fail("challenge replay requires positive integer nodes")
    if nodes > _SOURCE_MAX_BUNDLE_NODES:
        _fail("challenge replay exceeds 4096-node preflight limit")


def _regenerate(
    case: dict[str, Any], profile: str
) -> generate.GeneratedChallenge:
    try:
        identity = _CANONICAL_IDENTITY(
            family=case["family"],
            version=case["version"],
            seed=case["seed"],
            profile=profile,
            nodes=case["difficulty"],
        )
        produced = generate.generate(identity)
    except _CANONICAL_ERROR as error:
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
    if _NATIVE_TYPE(produced) is not _CANONICAL_RESULT:
        _fail("canonical challenge regeneration produced invalid payload")
    try:
        payloads = (produced.source, produced.oracle, produced.manifest)
    except Exception as error:
        # A malformed native result may have unset slots. Do not expose the
        # dependency's raw attribute fault through the replay boundary.
        message = "canonical challenge regeneration produced invalid payload"
        raise ChallengeBundleError(message) from error
    if _NATIVE_ANY(
        _NATIVE_TYPE(payload) is not _NATIVE_BYTES for payload in payloads
    ):
        _fail("canonical challenge regeneration produced invalid payload")
    # Validate malformed/failing dependency receipts above so they keep their
    # typed diagnostic and original cause. A successful replaced generator,
    # however, is not independent evidence of its own reported challenge.
    if generate.generate is not _CANONICAL_GENERATE:
        _fail("canonical challenge regeneration provider changed")
    return produced


def _admit_files(files: dict[str, bytes]) -> None:
    if (
        _NATIVE_TYPE(files) is not _NATIVE_DICT
        or _NATIVE_ANY(_NATIVE_TYPE(key) is not _NATIVE_STR for key in files)
        or _NATIVE_SET(files) != _NATIVE_SET(_SOURCE_BUNDLE_FILES)
    ):
        _fail("challenge bundle must include all three canonical files")
    if _NATIVE_ANY(
        _NATIVE_TYPE(files[name]) is not _NATIVE_BYTES
        for name in _SOURCE_BUNDLE_FILES
    ):
        _fail("challenge bundle payloads must be byte strings")
    if _NATIVE_LEN(files["oracle.bin"]) != _SOURCE_ORACLE_BYTES:
        _fail("challenge bundle oracle must be four bytes")
    if _NATIVE_LEN(files["program.c"]) > _SOURCE_MAX_SOURCE_BYTES or (
        _NATIVE_LEN(files["manifest.json"]) > _SOURCE_MAX_MANIFEST_BYTES
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
    # Both maps are exact native dicts, but their callers retain references.
    # Snapshot their admitted identities before replaceable dependencies run.
    original_case = case.copy()
    original_files = files.copy()
    produced = _regenerate(case, profile)
    originals = (produced.source, produced.oracle, produced.manifest)
    if _NATIVE_ANY(
        files[name] != expected
        for name, expected in _NATIVE_ZIP(_SOURCE_BUNDLE_FILES, originals, strict=True)
    ):
        _fail(
            "retained challenge bundle differs from deterministic regeneration"
        )
    try:
        source_hash = sha256(produced.source).hexdigest()
        # The public hashlib.sha256 attribute can share the replaced callable
        # above. Hash through the separate algorithm-name constructor instead.
        independent_hash = hashlib.new("sha256", produced.source).hexdigest()
        source_bound_hash = _NATIVE_SHA256(produced.source).hexdigest()
    except Exception as error:
        # The hashing dependency must not publish a foreign failure or rely
        # on caller-owned exception formatters for source authentication.
        message = "challenge source SHA-256 computation failed"
        raise ChallengeBundleError(message) from error
    # A substituted first hash provider must not certify a false workload
    # claim by returning the same native-looking digest as the forged claim.
    if (
        _NATIVE_TYPE(source_hash) is not _NATIVE_STR
        or _NATIVE_TYPE(independent_hash) is not _NATIVE_STR
        or _NATIVE_TYPE(source_bound_hash) is not _NATIVE_STR
        or _NATIVE_LEN(source_hash) != _SOURCE_SHA256_HEX_LENGTH
        or _NATIVE_LEN(independent_hash) != _SOURCE_SHA256_HEX_LENGTH
        or _NATIVE_LEN(source_bound_hash) != _SOURCE_SHA256_HEX_LENGTH
        or source_hash != source_bound_hash
        or independent_hash != source_bound_hash
    ):
        _fail("challenge source SHA-256 receipt differs from regenerated bytes")
    # A digest provider can change caller-owned native maps while returning
    # the true source hash. Re-admit native types before equality, so changed
    # values cannot supply custom comparison hooks or a newly widened policy.
    _bounded_case(case)
    _admit_files(files)
    if case != original_case or files != original_files:
        _fail("challenge replay input identity changed during verification")
    if source_hash != original_case["workload_sha256"]:
        _fail("arena workload SHA-256 differs from regenerated C source")
    return source_hash
