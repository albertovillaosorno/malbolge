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
import tomllib
from typing import Never

from benchmarks.arena import analyze

EXTENSION_NAME = "arena_trial"
EXTENSION_FIELDS = frozenset({"schema_version", "trial", "raw_sha256"})
SCHEMA_VERSION = 1


class TrialRunError(ValueError):
    """Invalid source-reported per-trial run identity."""


@dataclass(frozen=True, slots=True)
class TrialRun:
    """Exact trial number and the raw bytes declared by a recorded run."""

    trial: int
    raw_sha256: str


def _fail(message: str) -> Never:
    raise TrialRunError(message)


def _digest(value: object) -> str:
    if not isinstance(value, str) or len(value) != analyze.SHA256_HEX_LENGTH:
        _fail("arena_trial requires lowercase SHA-256 raw_sha256")
    if not set(value) <= analyze.SHA256_ALPHABET:
        _fail("arena_trial requires lowercase SHA-256 raw_sha256")
    return value


def parse_trial_run(text: str) -> TrialRun:
    """Parse the arena extension without replacing the core run validator.

    Returns:
        A versioned trial index and lowercase raw-file fingerprint.

    Raises:
        TrialRunError: The arena extension is malformed or missing.

    """
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        message = f"invalid per-trial manifest TOML: {error}"
        raise TrialRunError(message) from error
    table = document.get(EXTENSION_NAME)
    if not isinstance(table, dict) or set(table) != EXTENSION_FIELDS:
        _fail("arena_trial requires exact schema_version/trial/raw_sha256")
    version = table["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        _fail("arena_trial requires schema_version = 1")
    trial = table["trial"]
    if type(trial) is not int or trial < 0:
        _fail("arena_trial requires nonnegative integer trial")
    return TrialRun(trial=trial, raw_sha256=_digest(table["raw_sha256"]))
