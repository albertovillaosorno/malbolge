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
#   - Optional version-one per-trial arena run-manifest extension admission.
# - Must-Not:
#   - Certify independent verification or trusted raw-file provenance.
# - Allows:
#   - Inputs: bounded experiment-run manifest bytes with arena_trial table.
#   - Outputs: exact repetition index and recorded raw-file fingerprint.
#   - Side effects: none.
# - Split-When:
#   - Another trial-run format requires a separately versioned boundary.
# - Merge-When:
#   - The experiment manifest authority includes arena trial bindings.
# - Summary:
#   - Binds each individual reported trial to a declared run-file digest.
# - Description:
#   - Rejects unversioned, malformed, or incomplete per-trial evidence links.
# - Usage:
#   - Called from benchmarks.arena.evidence --require-trial-run-identity.
# - Defaults:
#   - Missing or extra fields and noncanonical digests fail closed.
#

"""Versioned per-trial arena extension of governed experiment run manifests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Never

import tomllib

from benchmarks.arena import analyze

# Preserve an independent source parse when a decoder provider is replaced.
_SOURCE_TOML_LOADS = tomllib.loads
_SOURCE_LEN = len
_SOURCE_SET = set
# Preserve native field and key shapes even when public builtins are replaced.
_SOURCE_TYPE = type
_SOURCE_ANY = any
_SOURCE_DICT = dict
_SOURCE_STR = str
_SOURCE_INT = int
# The source digest grammar must not follow late analyzer module substitutions.
_SOURCE_SHA256_HEX_LENGTH = analyze.SHA256_HEX_LENGTH
_SOURCE_SHA256_ALPHABET = analyze.SHA256_ALPHABET

EXTENSION_NAME = "arena_trial"
EXTENSION_FIELDS = frozenset({"schema_version", "trial", "raw_sha256"})
SCHEMA_VERSION = 1
MAX_RUN_MANIFEST_BYTES = 1_048_576
# The version-one extension identity and resource cap are fixed at import.
_SOURCE_EXTENSION_NAME = EXTENSION_NAME
_SOURCE_EXTENSION_FIELDS = EXTENSION_FIELDS
_SOURCE_SCHEMA_VERSION = SCHEMA_VERSION
_SOURCE_MAX_RUN_MANIFEST_BYTES = MAX_RUN_MANIFEST_BYTES


class TrialRunError(ValueError):
    """Invalid source-reported per-trial run identity."""


# Rejection identity must survive consumer rebinding of the public error.
_SOURCE_TRIAL_RUN_ERROR = TrialRunError


@dataclass(frozen=True, slots=True)
class TrialRun:
    """Exact trial number and the raw bytes declared by a recorded run."""

    trial: int
    raw_sha256: str


# Preserve the checked run identity against a substituted result factory.
_SOURCE_TRIAL_RUN = TrialRun


def _fail(message: str) -> Never:
    raise _SOURCE_TRIAL_RUN_ERROR(message)


_SOURCE_FAIL = _fail


def _digest(value: object) -> str:
    if (
        _SOURCE_TYPE(value) is not _SOURCE_STR
        or _SOURCE_LEN(value) != _SOURCE_SHA256_HEX_LENGTH
    ):
        _SOURCE_FAIL("arena_trial requires lowercase SHA-256 raw_sha256")
    if not _SOURCE_SET(value) <= _SOURCE_SHA256_ALPHABET:
        _SOURCE_FAIL("arena_trial requires lowercase SHA-256 raw_sha256")
    return value


def _admit_text(text: str) -> None:
    if _SOURCE_TYPE(text) is not _SOURCE_STR:
        _SOURCE_FAIL("per-trial run manifest requires exact str text")
    if _SOURCE_LEN(text) > _SOURCE_MAX_RUN_MANIFEST_BYTES:
        _SOURCE_FAIL("per-trial run manifest exceeds byte limit")
    try:
        encoded_size = _SOURCE_LEN(text.encode("utf-8"))
    except UnicodeEncodeError as error:
        message = "per-trial run manifest requires strict UTF-8 text"
        raise _SOURCE_TRIAL_RUN_ERROR(message) from error
    if encoded_size > _SOURCE_MAX_RUN_MANIFEST_BYTES:
        _SOURCE_FAIL("per-trial run manifest exceeds byte limit")


_SOURCE_ADMIT_TEXT = _admit_text


_SOURCE_DIGEST = _digest


def parse_trial_run(text: str) -> TrialRun:
    """Parse the arena extension without replacing the core run validator.

    Returns:
        A versioned trial index and lowercase raw-file fingerprint.

    Raises:
        TrialRunError: The arena extension is malformed or missing.

    """
    _SOURCE_ADMIT_TEXT(text)
    try:
        document = tomllib.loads(text)
    except Exception as error:
        # The parser is a dependency: all ordinary faults must stay typed.
        # Preserve the cause without invoking foreign exception formatters.
        message = "invalid per-trial manifest TOML"
        raise _SOURCE_TRIAL_RUN_ERROR(message) from error
    if _SOURCE_TYPE(document) is not _SOURCE_DICT:
        _SOURCE_FAIL("invalid per-trial manifest TOML root")
    if _SOURCE_ANY(_SOURCE_TYPE(key) is not _SOURCE_STR for key in document):
        _SOURCE_FAIL("per-trial manifest TOML requires native string keys")
    table = document.get(_SOURCE_EXTENSION_NAME)
    if (
        _SOURCE_TYPE(table) is not _SOURCE_DICT
        or _SOURCE_ANY(_SOURCE_TYPE(key) is not _SOURCE_STR for key in table)
        or _SOURCE_SET(table) != _SOURCE_EXTENSION_FIELDS
    ):
        _SOURCE_FAIL(
            "arena_trial requires exact schema_version/trial/raw_sha256 and native string keys"
        )
    version = table["schema_version"]
    if _SOURCE_TYPE(version) is not _SOURCE_INT or version != _SOURCE_SCHEMA_VERSION:
        _SOURCE_FAIL("arena_trial requires schema_version = 1")
    trial = table["trial"]
    if _SOURCE_TYPE(trial) is not _SOURCE_INT or trial < 0:
        _SOURCE_FAIL("arena_trial requires nonnegative integer trial")
    digest = _SOURCE_DIGEST(table["raw_sha256"])
    # The native shape of a returned mapping does not prove that its values
    # were parsed from this manifest. Compare against the retained source
    # parser before binding a trial number or raw-file hash.
    try:
        source = _SOURCE_TOML_LOADS(text)
    except Exception as error:
        message = "per-trial manifest source TOML could not be parsed"
        raise _SOURCE_TRIAL_RUN_ERROR(message) from error
    source_table = source.get(_SOURCE_EXTENSION_NAME)
    if (
        _SOURCE_TYPE(source_table) is not _SOURCE_DICT
        or _SOURCE_SET(source_table) != _SOURCE_EXTENSION_FIELDS
        or _SOURCE_TYPE(source_table.get("schema_version")) is not _SOURCE_INT
        or source_table["schema_version"] != version
        or _SOURCE_TYPE(source_table.get("trial")) is not _SOURCE_INT
        or source_table["trial"] != trial
        or _SOURCE_TYPE(source_table.get("raw_sha256")) is not _SOURCE_STR
        or source_table["raw_sha256"] != digest
    ):
        _SOURCE_FAIL("per-trial manifest identity differs from source TOML")
    return _SOURCE_TRIAL_RUN(trial=trial, raw_sha256=digest)
