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
#   - Independent read-only admission of retained host-C arena studies.
# - Must-Not:
#   - Measure host performance, execute candidate binaries or certify Malbolge.
# - Allows:
#   - Inputs: bounded ignored local host-C study and optional source replay.
#   - Outputs: checked report over source, raw, run, and binary identities.
#   - Side effects: none by default; optional temporary host-C oracle replay.
# - Split-When:
#   - Target compiler results need an independently attested trust boundary.
# - Merge-When:
#   - All arena studies acquire a governed generic offline audit contract.
# - Summary:
#   - Reopen retained studies without trusting their producer's own checks.
# - Description:
#   - Revalidates trial links, canonical source and binary hashes/byte lengths.
# - Usage:
#   - `python -B -m benchmarks.arena.reference_audit .temp/RUN/study.json`.
# - Defaults:
#   - No native child process or claimed performance verification by default.
#

"""Read-only offline audit of retained real host-C reference studies."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import stat
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from dataclasses import dataclass
from hashlib import sha256
from itertools import starmap
from pathlib import Path
from typing import Any, Never, cast

from benchmarks.arena import (
    analyze,
    evidence,
    host_c_oracle,
    reference_study,
    report_output,
)
from benchmarks.challenges import generate
from scripts.validate import experiment_manifest

_ROOT = Path(__file__).resolve().parents[2]
_NATIVE_SHA256 = sha256
_NATIVE_COPYSIGN = math.copysign
_NATIVE_TYPE = type
_NATIVE_DICT = dict
_NATIVE_LIST = list
_NATIVE_FLOAT = float
_NATIVE_NONE_TYPE = type(None)
_NATIVE_ZIP = zip
_NATIVE_BYTES = bytes
_NATIVE_BOOL = bool
_NATIVE_ANY = any
_NATIVE_ALL = all
_NATIVE_LEN = len
_NATIVE_STR = str
_NATIVE_INT = int
_NATIVE_JSON_LOADS = json.loads
_JSON_OBJECT_PARSER_NAME = "JSONObject"
_JSON_ARRAY_PARSER_NAME = "JSONArray"
_JSON_STRING_PARSER_NAME = "scanstring"
_JSON_SCANNER_MODULE_NAME = "scanner"
_JSON_SCANNER_FACTORY_NAME = "make_scanner"
_NATIVE_JSON_DECODER = json.JSONDecoder
_NATIVE_JSON_DECODER_INIT = json.JSONDecoder.__init__
_NATIVE_JSON_DECODER_DECODE = json.JSONDecoder.decode
_NATIVE_JSON_DECODER_RAW = json.JSONDecoder.raw_decode
_NATIVE_JSON_OBJECT_PARSER = getattr(json.decoder, _JSON_OBJECT_PARSER_NAME)
_NATIVE_JSON_ARRAY_PARSER = getattr(json.decoder, _JSON_ARRAY_PARSER_NAME)
_NATIVE_JSON_STRING_PARSER = getattr(json.decoder, _JSON_STRING_PARSER_NAME)
_NATIVE_JSON_SCANNER_MODULE = getattr(json.decoder, _JSON_SCANNER_MODULE_NAME)
_NATIVE_JSON_SCANNER_FACTORY = getattr(
    getattr(json, _JSON_SCANNER_MODULE_NAME), _JSON_SCANNER_FACTORY_NAME
)
MAX_ARTIFACT_INDEX_BYTES = 1024 * 1024
PART_COUNT = 3
ROOT_PART = ".temp"
GIT_COMMIT_TYPE = b"commit"
UNDERSCORE = "_"
STUDY_LEAF = "study.json"
ARTIFACT_LEAF = "artifacts.json"
FAILURES_LEAF = "failures.json"
RESOURCE_CONTROLS_LEAF = "resource-controls.json"
MAX_RESOURCE_CONTROLS_BYTES = 4096
MAX_FAILURES_BYTES = 64 * 1024
# Retained sidecar limits are version-one audit policy, not mutable reader hints.
_SOURCE_MAX_ARTIFACT_INDEX_BYTES = MAX_ARTIFACT_INDEX_BYTES
_SOURCE_MAX_RESOURCE_CONTROLS_BYTES = MAX_RESOURCE_CONTROLS_BYTES
_SOURCE_MAX_FAILURES_BYTES = MAX_FAILURES_BYTES
RUN_PREFIX = "arena-host-c-study-"
# These labels define the ignored source-tree admission boundary.
_SOURCE_PART_COUNT = PART_COUNT
_SOURCE_ROOT_PART = ROOT_PART
_SOURCE_STUDY_LEAF = STUDY_LEAF
_SOURCE_RUN_PREFIX = RUN_PREFIX
_SOURCE_UNDERSCORE = UNDERSCORE
STAGE = "host-c-reference-not-malbolge"
TOOLCHAIN = "repo-pinned-clang-22.1.8"
PRODUCER_IMPLEMENTATION = "benchmarks/arena/reference_study.py"
PRODUCER_CONFIGURATION = "benchmarks/arena/README.md"
PRODUCER_METHOD_CLASS = "benchmarking"
PRODUCER_ACCELERATOR = "none"
PRODUCER_RESEARCH_CLAIMS = {
    "question": "Does Clang O2 reduce time or code size vs O0?",
    "hypothesis": "O2 improves verified time/size frontier on C.",
    "rejection_observation": "O2 is dominated by O0 at all difficulties.",
}
# Audit provenance cannot follow substituted producer labels or hypothesis text.
_SOURCE_STAGE = STAGE
_SOURCE_TOOLCHAIN = TOOLCHAIN
_SOURCE_PRODUCER_RESEARCH_CLAIMS = tuple(PRODUCER_RESEARCH_CLAIMS.items())
# A retained child-limit receipt must match the original producer policy,
# not a replacement helper or mutable producer configuration seen at audit time.
_SOURCE_RESOURCE_CONTROL_POLICY = tuple(
    host_c_oracle.resource_controls_record().items()
)
REQUIRED_OBJECTIVES = ["elapsed_ns", "artifact_bytes"]
CURRENT_OBJECTIVES = [*REQUIRED_OBJECTIVES, "peak_rss_bytes"]
RSS_RESOURCE_POLICY_VERSION = 2
REQUIRED_ALGORITHMS = frozenset(
    {
        reference_study.BASELINE,
        reference_study.CANDIDATE,
    }
)


@dataclass(frozen=True, slots=True)
class AuditOptions:
    """Optional admission and replay gates for retained host-C evidence."""

    replay_oracles: bool = False
    rebuild_binaries: bool = False
    require_source_commit_object: bool = False
    require_resource_controls_record: bool = False


@dataclass(frozen=True, slots=True)
class _AuditData:
    document: dict[str, Any]
    checked: dict[str, Any]
    artifacts: dict[str, dict[str, str]]
    verified_binaries: int
    failed_diagnostics: int
    commit: str
    resource_record_version: int
    manifest_fingerprints: dict[str, bytes]
    sidecar_fingerprints: dict[str, bytes | None]
    evidence_snapshot: evidence.EvidenceSnapshot
    study_fingerprint: bytes


_SOURCE_AUDIT_OPTIONS_TYPE = AuditOptions
DEFAULT_AUDIT_OPTIONS = AuditOptions()


class ReferenceAuditError(ValueError):
    """Retained host-C research evidence is not independently consistent."""


# Trust only the error types present at import, not replaced public aliases.
_SOURCE_DIAGNOSTIC_ERRORS = (
    ReferenceAuditError,
    report_output.ReportOutputError,
    analyze.ArenaError,
    evidence.EvidenceError,
    reference_study.ReferenceStudyError,
    host_c_oracle.HostOracleError,
    experiment_manifest.ExperimentManifestError,
    OSError,
    PermissionError,
    FileNotFoundError,
    ValueError,
    TypeError,
    UnicodeError,
    UnicodeDecodeError,
)
_SOURCE_OS_DIAGNOSTIC_ERRORS = (OSError, PermissionError, FileNotFoundError)


def _fail(message: str) -> Never:
    raise ReferenceAuditError(message)


def _safe_error_detail(error: Exception) -> str:
    """Keep exact source-native errors readable without foreign formatter hooks.

    Returns:
        Trusted diagnostic text, otherwise the foreign exception type name.

    """
    error_type = _NATIVE_TYPE(error)
    if error_type in _SOURCE_DIAGNOSTIC_ERRORS:
        # Exact native exception types can still carry caller-owned arguments.
        # Never let their default __str__ format a foreign object.
        arguments = error.args
        if _NATIVE_LEN(arguments) == 1 and _NATIVE_TYPE(arguments[0]) is _NATIVE_STR:
            return arguments[0]
        if (
            error_type in _SOURCE_OS_DIAGNOSTIC_ERRORS
            and _NATIVE_LEN(arguments) == 2
            and _NATIVE_TYPE(arguments[0]) is _NATIVE_INT
            and _NATIVE_TYPE(arguments[1]) is _NATIVE_STR
        ):
            return f"{error_type.__name__}: [Errno {arguments[0]}] {arguments[1]}"
    return error_type.__name__


def _admit_options(options: AuditOptions) -> None:
    """Require precise opt-ins before any input reads or native child work."""
    if _NATIVE_TYPE(options) is not _SOURCE_AUDIT_OPTIONS_TYPE or _NATIVE_ANY(
        _NATIVE_TYPE(value) is not _NATIVE_BOOL
        for value in (
            options.replay_oracles,
            options.rebuild_binaries,
            options.require_source_commit_object,
            options.require_resource_controls_record,
        )
    ):
        _fail("host-C audit options require exact booleans")


def _prefix(relative: str) -> str:
    if _NATIVE_TYPE(relative) is not _NATIVE_STR:
        _fail("host-C audit requires a canonical ignored study path")
    parts = relative.split("/")
    if (
        _NATIVE_LEN(parts) != _SOURCE_PART_COUNT
        or parts[0] != _SOURCE_ROOT_PART
        or parts[2] != _SOURCE_STUDY_LEAF
    ):
        _fail("host-C audit requires .temp/arena-host-c-study-*/study.json")
    directory = parts[1]
    suffix = directory.removeprefix(_SOURCE_RUN_PREFIX)
    if not directory.startswith(_SOURCE_RUN_PREFIX) or not suffix:
        _fail("host-C audit requires a generated host-C study directory")
    if not suffix.isascii() or not _NATIVE_ALL(
        char.isalnum() or char == _SOURCE_UNDERSCORE for char in suffix
    ):
        _fail("host-C audit requires a canonical local study directory")
    return "/".join(parts[:2])


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            _fail(f"host-C retained JSON has duplicate field: {name}")
        result[name] = value
    return result


def _reject_nonfinite(value: str) -> Never:
    _fail(f"host-C retained JSON has nonfinite number: {value}")


def _read_bounded_evidence(relative: str, *, limit: int) -> bytes:
    """Admit exact bounded native reader bytes before hashing or interpretation."""
    raw = evidence.read_bounded_regular(_ROOT, relative, limit=limit)
    if _NATIVE_TYPE(raw) is not _NATIVE_BYTES or _NATIVE_LEN(raw) > limit:
        _fail(f"host-C retained evidence requires exact bounded bytes: {relative}")
    return raw


SHA256_DIGEST_BYTES = 32
_SOURCE_SHA256_DIGEST_BYTES = SHA256_DIGEST_BYTES


def _source_fingerprint(raw: bytes) -> bytes:
    """Require agreement with the import-bound SHA-256 source constructor.

    Return exactly one native SHA-256 digest. Joint substitutions of the two
    mutable runtime constructors cannot relabel retained evidence bytes;
    ordinary dependency faults remain typed and preserve their cause.
    """
    if _NATIVE_TYPE(raw) is not _NATIVE_BYTES:
        _fail("host-C audit SHA-256 requires exact native source bytes")
    try:
        result = sha256(raw).digest()
        # Check through an independent constructor, not the mutable module
        # attribute which can be replaced alongside the bound sha256 alias.
        reference = hashlib.new("sha256", raw).digest()
        source_bound = _NATIVE_SHA256(raw).digest()
    except Exception as error:
        message = "host-C audit SHA-256 fingerprint dependency failed"
        raise ReferenceAuditError(message) from error
    if (
        _NATIVE_TYPE(result) is not _NATIVE_BYTES
        or _NATIVE_TYPE(reference) is not _NATIVE_BYTES
        or _NATIVE_TYPE(source_bound) is not _NATIVE_BYTES
        or _NATIVE_LEN(result) != _SOURCE_SHA256_DIGEST_BYTES
        or _NATIVE_LEN(reference) != _SOURCE_SHA256_DIGEST_BYTES
        or _NATIVE_LEN(source_bound) != _SOURCE_SHA256_DIGEST_BYTES
        or result != reference
        or result != source_bound
    ):
        _fail("host-C audit SHA-256 fingerprint receipt differs from source")
    return result


def _matches_native_json_tree(received: object, original: object) -> bool:
    """Corroborate JSON decoded values with original native traversal helpers.

    Returns:
        Whether the substituted parser returned the exact original JSON tree.

    """
    kind = _NATIVE_TYPE(original)
    if _NATIVE_TYPE(received) is not kind:
        return False
    if kind is _NATIVE_DICT:
        received_map = cast("dict[object, object]", received)
        original_map = cast("dict[object, object]", original)
        if _NATIVE_ANY(_NATIVE_TYPE(key) is not _NATIVE_STR for key in received_map):
            _fail("host-C retained JSON decoder returned non-native key")
        return _NATIVE_LEN(received_map) == _NATIVE_LEN(original_map) and _NATIVE_ALL(
            key in received_map and _matches_native_json_tree(received_map[key], value)
            for key, value in original_map.items()
        )
    if kind is _NATIVE_LIST:
        received_items = cast("list[object]", received)
        original_items = cast("list[object]", original)
        return _NATIVE_LEN(received_items) == _NATIVE_LEN(original_items) and _NATIVE_ALL(
            _matches_native_json_tree(left, right)
            for left, right in _NATIVE_ZIP(received_items, original_items, strict=True)
        )
    if kind is _NATIVE_FLOAT:
        left = cast("float", received)
        right = cast("float", original)
        return left == right and (
            right != 0.0
            or _NATIVE_COPYSIGN(1.0, left) == _NATIVE_COPYSIGN(1.0, right)
        )
    return kind in (_NATIVE_STR, _NATIVE_INT, _NATIVE_BOOL, _NATIVE_NONE_TYPE) and (
        received == original
    )


def _require_source_json_decoder() -> None:
    """Reject mutable decoder internals shared by both JSON parse paths."""
    if (
        _NATIVE_JSON_DECODER.__init__ is not _NATIVE_JSON_DECODER_INIT
        or _NATIVE_JSON_DECODER.decode is not _NATIVE_JSON_DECODER_DECODE
        or _NATIVE_JSON_DECODER.raw_decode is not _NATIVE_JSON_DECODER_RAW
        or getattr(json.decoder, _JSON_OBJECT_PARSER_NAME)
        is not _NATIVE_JSON_OBJECT_PARSER
        or getattr(json.decoder, _JSON_ARRAY_PARSER_NAME)
        is not _NATIVE_JSON_ARRAY_PARSER
        or getattr(json.decoder, _JSON_STRING_PARSER_NAME)
        is not _NATIVE_JSON_STRING_PARSER
        or getattr(json.decoder, _JSON_SCANNER_MODULE_NAME)
        is not _NATIVE_JSON_SCANNER_MODULE
        or getattr(getattr(json, _JSON_SCANNER_MODULE_NAME), _JSON_SCANNER_FACTORY_NAME)
        is not _NATIVE_JSON_SCANNER_FACTORY
    ):
        _fail("host-C retained JSON decoder provider differs from source")


def _read_json(
    relative: str, *, limit: int, fingerprints: dict[str, bytes | None]
) -> object:
    raw = _read_bounded_evidence(relative, limit=limit)
    try:
        source_text = raw.decode("utf-8")
        _require_source_json_decoder()
        decoder = json.loads
        parsed = decoder(
            source_text,
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_nonfinite,
        )
        _require_source_json_decoder()
        # Even the saved json.loads function resolves the current mutable
        # json.JSONDecoder class. Independently decode with the class bound at
        # import so a forged class cannot certify its own output.
        original = _NATIVE_JSON_DECODER(
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_nonfinite,
        ).decode(source_text)
        _require_source_json_decoder()
        if not _matches_native_json_tree(parsed, original):
            _fail(f"host-C retained JSON decoder differs from source: {relative}")
        # Never return a mutable object still owned by a substituted decoder.
        parsed = original
    except ReferenceAuditError:
        raise
    except Exception as error:
        # Any ordinary JSON dependency fault remains a typed admission failure.
        message = f"host-C retained JSON is not valid: {relative}"
        raise ReferenceAuditError(message) from error
    fingerprints[relative] = _source_fingerprint(raw)
    return parsed


def _load_study(relative: str) -> tuple[dict[str, Any], bytes]:
    raw = _read_bounded_evidence(
        relative,
        limit=analyze.MAX_INPUT_BYTES,
    )
    return analyze.parse_document(raw.decode("utf-8")), _source_fingerprint(raw)


def _check_trials(
    document: dict[str, Any],
    prefix: str,
) -> None:
    observations = document["observations"]
    if {row["algorithm"] for row in observations} != REQUIRED_ALGORITHMS:
        _fail("host-C reference audit requires both recorded Clang arms")
    for row in observations:
        if row["verifier"] != reference_study.VERIFIER:
            _fail("host-C reference audit requires native C entry oracle")
        case = row["case"]
        name = f"{row['algorithm']}-nodes-{case['difficulty']}-trial-{row['trial']}"
        if (
            row["experiment_manifest"] != f"{prefix}/runs/{name}.toml"
            or row["raw_sample"] != f"{prefix}/raw/{name}.csv"
        ):
            _fail("host-C reference audit trial paths differ from native producer")


def _check_plan_trials(rows: list[dict[str, Any]]) -> None:
    trials = {row["trial"] for row in rows}
    if not 1 <= len(trials) <= reference_study.MAX_TRIALS:
        _fail("host-C audit contains too many trial repetitions")
    if trials != set(range(len(trials))):
        _fail("host-C audit requires consecutive trial repetition indices")
    # The native producer applies one repetition count to every difficulty.
    # Per-difficulty paired cohorts alone do not establish that invariant.
    by_difficulty: dict[int, set[int]] = {}
    for row in rows:
        difficulty = row["case"]["difficulty"]
        by_difficulty.setdefault(difficulty, set()).add(row["trial"])
    if any(level_trials != trials for level_trials in by_difficulty.values()):
        _fail("host-C audit requires the same trials at every difficulty")


def _check_case_plan(document: dict[str, Any]) -> None:
    rows = document["observations"]
    families = {row["case"]["family"] for row in rows}
    seeds = {row["case"]["seed"] for row in rows}
    difficulties = {row["case"]["difficulty"] for row in rows}
    if len(families) != 1 or len(seeds) != 1:
        _fail("host-C audit requires one generated family and seed")
    if not 1 <= len(difficulties) <= reference_study.MAX_DIFFICULTIES:
        _fail("host-C audit contains too many challenge difficulty levels")
    if max(difficulties) > reference_study.host_c_oracle.MAX_REPLAY_NODES:
        _fail("host-C audit exceeds the source runner challenge limit")
    family = next(iter(families))
    seed = next(iter(seeds))
    if document["study"]["id"] != f"host-C-reference-{family}-seed-{seed}":
        _fail("host-C reference audit study identity differs from source")
    _check_plan_trials(rows)


def _check_stage(document: dict[str, Any], prefix: str) -> None:
    study = document["study"]
    if (
        study["stage"] != _SOURCE_STAGE
        or study["target_profile"] != reference_study.PROFILE
    ):
        _fail("host-C reference audit stage or target profile differs")
    if any(
        study[field] != expected for field, expected in _SOURCE_PRODUCER_RESEARCH_CLAIMS
    ):
        _fail("host-C reference producer research claims differ")
    if study["toolchain"] != _SOURCE_TOOLCHAIN:
        _fail("host-C reference audit toolchain differs from source")
    if study["baseline"] != reference_study.BASELINE or study["objectives"] not in (
        REQUIRED_OBJECTIVES,
        CURRENT_OBJECTIVES,
    ):
        _fail("host-C reference audit configured arms or objectives differ")
    expected_budget = {
        "time_ns": reference_study.BUDGET_SECONDS * 1_000_000_000,
        "memory_bytes": reference_study.BUDGET_MEMORY_MIB * 1_048_576,
    }
    if study["budget"] != expected_budget:
        _fail("host-C reference audit budgets differ from source runner")
    _check_trials(document, prefix)
    _check_case_plan(document)


def _index_entry(name: object, item: object) -> tuple[str, dict[str, str]]:
    if (
        type(name) is not str
        or type(item) is not dict
        or any(type(key) is not str for key in item)
    ):
        _fail("host-C artifact index has invalid trial entries")
    if set(item) != {"path", "sha256"}:
        _fail("host-C artifact index requires exact identity fields")
    path, digest = item["path"], item["sha256"]
    if type(path) is not str or type(digest) is not str:
        _fail("host-C artifact index requires string identity fields")
    return name, {"path": path, "sha256": digest}


def _check_artifact_index(
    source: object,
    document: dict[str, Any],
) -> dict[str, dict[str, str]]:
    if type(source) is not dict or any(type(key) is not str for key in source):
        _fail("host-C artifact index must be a native JSON map")
    if len(source) > len(document["observations"]):
        _fail("host-C artifact index contains extra entries")
    return dict(starmap(_index_entry, source.items()))


def _check_trial_file_inventory(
    document: dict[str, Any],
    artifacts: dict[str, dict[str, str]],
    prefix: str,
) -> None:
    """Reject undeclared trial files rather than ignoring foreign local data."""
    expected: dict[str, set[str]] = {
        "runs": {
            row["experiment_manifest"].rsplit("/", maxsplit=1)[1]
            for row in document["observations"]
        },
        "raw": {
            row["raw_sample"].rsplit("/", maxsplit=1)[1]
            for row in document["observations"]
        },
        "candidates": {
            value["path"].rsplit("/", maxsplit=1)[1] for value in artifacts.values()
        },
    }
    for folder, names in expected.items():
        directory = _ROOT / prefix / folder
        if directory.is_symlink() or not directory.is_dir():
            _fail(f"host-C trial file inventory directory invalid: {folder}")
        observed: set[str] = set()
        for entry in directory.iterdir():
            if entry.name not in names:
                _fail(f"unregistered host-C trial file in {folder}: {entry.name}")
            observed.add(entry.name)
        if observed != names:
            _fail(f"host-C trial file inventory missing entries in {folder}")


def _recorded_source_commit(
    document: dict[str, Any],
    *,
    require_git_object: bool,
) -> tuple[str, dict[str, bytes]]:
    commits: set[str] = set()
    fingerprints: dict[str, bytes] = {}
    paths = {row["experiment_manifest"] for row in document["observations"]}
    for relative in sorted(paths):
        data = _read_bounded_evidence(
            relative,
            limit=evidence.MAX_MANIFEST_BYTES,
        )
        fingerprints[relative] = _source_fingerprint(data)
        manifest = experiment_manifest.parse_manifest(data.decode("utf-8"))
        if manifest.run is None:
            _fail("host-C audit source commit requires a recorded run")
        if (
            manifest.implementation != PRODUCER_IMPLEMENTATION
            or manifest.configuration != PRODUCER_CONFIGURATION
            or manifest.method_class != PRODUCER_METHOD_CLASS
            or manifest.output != relative.rsplit("/runs/", maxsplit=1)[0]
            or manifest.run.accelerator != PRODUCER_ACCELERATOR
        ):
            _fail("host-C run manifest producer provenance differs")
        commits.add(manifest.run.commit)
    if len(commits) != 1:
        _fail("host-C study run manifests disagree on source commit")
    commit = next(iter(commits))
    if require_git_object:
        _require_git_commit(commit)
    return commit, fingerprints


def _require_unchanged_manifests(fingerprints: dict[str, bytes]) -> None:
    """Reject retained run-manifest drift across a host-C audit pass."""
    for relative, fingerprint in sorted(fingerprints.items()):
        data = _read_bounded_evidence(relative, limit=evidence.MAX_MANIFEST_BYTES)
        if _source_fingerprint(data) != fingerprint:
            _fail("host-C run manifest changed during audit")


def _require_unchanged_sidecars(
    prefix: str, fingerprints: dict[str, bytes | None]
) -> None:
    """Bind optional and required receipts to their originally parsed bytes."""
    for leaf, limit in (
        (ARTIFACT_LEAF, _SOURCE_MAX_ARTIFACT_INDEX_BYTES),
        (FAILURES_LEAF, _SOURCE_MAX_FAILURES_BYTES),
        (RESOURCE_CONTROLS_LEAF, _SOURCE_MAX_RESOURCE_CONTROLS_BYTES),
    ):
        relative = f"{prefix}/{leaf}"
        if relative not in fingerprints:
            _fail("host-C audit missing admitted sidecar identity")
        original = fingerprints[relative]
        if original is None:
            try:
                (_ROOT / relative).lstat()
            except Exception as error:
                # Only an exact native absence proves an optional sidecar
                # remained absent; foreign subclasses may forge missing files.
                if type(error) is FileNotFoundError:
                    continue
                message = f"host-C retained sidecar changed during audit: {relative}"
                raise ReferenceAuditError(message) from error
            _fail(f"host-C retained sidecar changed during audit: {relative}")
        try:
            current = _read_bounded_evidence(relative, limit=limit)
        except Exception as error:
            # An unanticipated bounded-reader fault must not leak as a raw
            # exception or invoke foreign exception diagnostic hooks.
            message = f"host-C retained sidecar changed during audit: {relative}"
            raise ReferenceAuditError(message) from error
        if _source_fingerprint(current) != original:
            _fail(f"host-C retained sidecar changed during audit: {relative}")


def _require_git_commit(commit: str) -> None:
    try:
        executable = shutil.which("git", path=os.defpath)
    except Exception as error:
        # Unexpected ordinary resolver faults remain typed provenance errors.
        message = "host-C source commit Git lookup failed"
        raise ReferenceAuditError(message) from error
    if executable is None:
        _fail("host-C source commit admission requires local Git")
    if (
        type(executable) is not str
        or not executable
        or "\0" in executable
        or not Path(executable).is_absolute()
    ):
        _fail("host-C source commit admission requires absolute Git executable")
    try:
        _ = os.fsencode(executable)
    except UnicodeError as error:
        message = "host-C source commit admission requires encodable Git executable"
        raise ReferenceAuditError(message) from error
    try:
        metadata = Path(executable).lstat()
        is_executable = os.access(executable, os.X_OK)
    except Exception as error:
        # Do not allow a substituted host inspector to escape this boundary.
        message = "host-C source commit Git path inspection failed"
        raise ReferenceAuditError(message) from error
    if type(metadata) is not os.stat_result:
        _fail("host-C source commit has invalid Git metadata")
    if not stat.S_ISREG(metadata.st_mode) or is_executable is not True:
        _fail("host-C source commit requires physical executable Git")
    # Foreign GIT_DIR and object alternates cannot satisfy local admission.
    try:
        clean_env: dict[str, str] = {}
        for name, value in os.environ.items():
            if type(name) is not str or type(value) is not str:
                _fail("host-C source commit requires native Git environment strings")
            if not name.startswith("GIT_"):
                clean_env[name] = value
    except ReferenceAuditError:
        raise
    except Exception as error:
        message = "host-C source commit Git environment unavailable"
        raise ReferenceAuditError(message) from error
    command = [executable, "cat-file", "-t", commit]
    # Retain the original prepared argv object: an equal copied completion
    # cannot establish that it came from this particular subprocess request.
    prepared = command.copy()
    try:
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            prepared,
            cwd=_ROOT,
            stdin=sp.DEVNULL,
            env=clean_env,
            check=False,
            shell=False,
            capture_output=True,
            timeout=5,
        )
    except Exception as error:
        # Contain child launch and observation faults without foreign formatting.
        message = "host-C source commit object lookup failed"
        raise ReferenceAuditError(message) from error
    if type(completed) is not sp.CompletedProcess:
        _fail("host-C recorded source commit is not a local Git commit object")
    returncode = completed.returncode
    stdout = completed.stdout
    if (
        type(completed.args) is not list
        or completed.args is not prepared
        or any(type(argument) is not str for argument in completed.args)
        or completed.args != command
        or type(returncode) is not int
        or returncode != 0
        or type(stdout) is not bytes
        or stdout != GIT_COMMIT_TYPE + b"\n"
        or type(completed.stderr) is not bytes
        or completed.stderr != b""
    ):
        _fail("host-C recorded source commit is not a local Git commit object")


def _valid_failure_version(version: object) -> bool:
    return type(version) is int and version == 1


def _check_retained_failures(
    document: dict[str, Any],
    prefix: str,
    fingerprints: dict[str, bytes | None],
) -> int:
    relative = f"{prefix}/{FAILURES_LEAF}"
    path = _ROOT / relative
    has_failure = any(
        row["outcome"] == reference_study.FAILED_OUTCOME
        for row in document["observations"]
    )
    if not path.exists() and not path.is_symlink():
        if has_failure:
            _fail("host-C reference failure details file is missing")
        fingerprints[relative] = None
        return 0  # Pre-extension all-success pilot is still admissible.
    source = _read_json(
        relative, limit=_SOURCE_MAX_FAILURES_BYTES, fingerprints=fingerprints
    )
    if (
        not isinstance(source, dict)
        or set(source) != {"schema_version", "failures"}
        or not _valid_failure_version(source["schema_version"])
    ):
        _fail("host-C reference failure file has invalid schema")
    failures = source["failures"]
    if not isinstance(failures, dict) or any(
        type(key) is not str or type(value) is not str
        for key, value in failures.items()
    ):
        _fail("host-C reference failure index has invalid data")
    return reference_study.check_retained_failures(document, failures)


def _expected_resource_policy(version: int) -> dict[str, str | int]:
    expected = dict(_SOURCE_RESOURCE_CONTROL_POLICY)
    if version == 1:
        expected = {
            key: value
            for key, value in expected.items()
            if key not in {"rss_measurement", "rss_tool"}
        }
        expected["schema_version"] = 1
    return expected


def _validate_resource_policy_fields(
    recorded: dict[str, Any],
    version: int,
) -> None:
    expected = _expected_resource_policy(version)
    if set(recorded) != set(expected):
        _fail("host-C reference child resource-control policy differs")
    if any(
        type(recorded[name]) is not type(value) or recorded[name] != value
        for name, value in expected.items()
    ):
        _fail("host-C reference child resource-control policy differs")


def _check_resource_controls(
    prefix: str,
    *,
    required: bool,
    fingerprints: dict[str, bytes | None],
) -> int:
    relative = f"{prefix}/{RESOURCE_CONTROLS_LEAF}"
    path = _ROOT / relative
    if not path.exists() and not path.is_symlink():
        if required:
            _fail("host-C reference resource-control record is missing")
        fingerprints[relative] = None
        return 0  # Legacy measurements predate controlled child launches.
    recorded = _read_json(
        relative, limit=_SOURCE_MAX_RESOURCE_CONTROLS_BYTES, fingerprints=fingerprints
    )
    if not isinstance(recorded, dict):
        _fail("host-C reference child resource-control policy differs")
    version = recorded.get("schema_version")
    if type(version) is not int or version not in {1, 2}:
        _fail("host-C reference child resource-control version invalid")
    _validate_resource_policy_fields(recorded, version)
    return version


def _admit_data(
    relative_study: str,
    prefix: str,
    options: AuditOptions,
) -> _AuditData:
    document, study_fingerprint = _load_study(relative_study)
    _check_stage(document, prefix)
    # Bind the reported source revision to the same retained manifest bytes
    # admitted by the subsequent independent link preflight.
    commit, manifest_fingerprints = _recorded_source_commit(
        document,
        require_git_object=options.require_source_commit_object,
    )
    snapshots: list[evidence.EvidenceSnapshot] = []
    checked = evidence.validate_links(
        document,
        _ROOT,
        policy=evidence.EvidencePolicy(
            require_trial_run_identity=True,
            require_budget_agreement=True,
            challenge_root=f"{prefix}/bundles",
            require_host_c_challenge_oracle=options.replay_oracles,
        ),
        _snapshot_out=snapshots,
    )
    if len(snapshots) != 1:
        _fail("host-C audit did not retain its linked evidence snapshot")
    sidecar_fingerprints: dict[str, bytes | None] = {}
    artifacts = _check_artifact_index(
        _read_json(
            f"{prefix}/{ARTIFACT_LEAF}",
            limit=_SOURCE_MAX_ARTIFACT_INDEX_BYTES,
            fingerprints=sidecar_fingerprints,
        ),
        document,
    )
    verified_binaries = reference_study.check_retained_artifacts(
        document,
        artifacts,
    )
    _check_trial_file_inventory(document, artifacts, prefix)
    failed_diagnostics = _check_retained_failures(
        document, prefix, sidecar_fingerprints
    )
    resource_record = _check_resource_controls(
        prefix,
        required=options.require_resource_controls_record,
        fingerprints=sidecar_fingerprints,
    )
    if (
        document["study"]["objectives"] == CURRENT_OBJECTIVES
        and resource_record != RSS_RESOURCE_POLICY_VERSION
    ):
        _fail("host-C peak-RSS study requires v2 resource-control record")
    return _AuditData(
        document,
        checked,
        artifacts,
        verified_binaries,
        failed_diagnostics,
        commit,
        resource_record,
        manifest_fingerprints,
        sidecar_fingerprints,
        snapshots[0],
        study_fingerprint,
    )


def _rebuild_reference_binaries(
    document: dict[str, Any],
    artifacts: dict[str, dict[str, str]],
) -> int:
    built: dict[tuple[str, int, int, int, str], bytes] = {}
    for row in document["observations"]:
        if row["outcome"] != analyze.VERIFIED:
            continue
        case = row["case"]
        mode = "-O0" if row["algorithm"] == reference_study.BASELINE else "-O2"
        key = (
            case["family"],
            case["version"],
            case["seed"],
            case["difficulty"],
            mode,
        )
        if key not in built:
            identity = generate.ChallengeIdentity(
                family=case["family"],
                version=case["version"],
                seed=case["seed"],
                nodes=case["difficulty"],
                profile=reference_study.PROFILE,
            )
            rebuilt = host_c_oracle.rebuild_reference(identity, mode)
            if (
                type(rebuilt) is not bytes
                or not 0 < len(rebuilt) <= reference_study.MAX_ARTIFACT_BYTES
            ):
                _fail("host-C rebuilt executable requires exact bounded bytes")
            built[key] = rebuilt
        retained = _read_bounded_evidence(
            artifacts[row["experiment_manifest"]]["path"],
            limit=reference_study.MAX_ARTIFACT_BYTES,
        )
        if built[key] != retained:
            _fail("host-C retained binary differs from canonical rebuilt C")
    return len(built)


def audit(
    relative_study: str,
    *,
    options: AuditOptions = DEFAULT_AUDIT_OPTIONS,
) -> dict[str, Any]:
    """Reopen and validate all retained host-C reference evidence.

    The optional independent source oracle check only compiles regenerated
    canonical C; rebuild mode compiles a new reference without executing the
    retained trial binary or pretending to reproduce its recorded elapsed time.

    Returns:
        Audited source counts, checked artifact count, and offline arena report.

    Raises:
        ReferenceAuditError: Evidence is absent, malformed, or inconsistent.

    """
    _admit_options(options)
    prefix = _prefix(relative_study)
    try:
        data = _admit_data(relative_study, prefix, options)
        rebuilt = (
            _rebuild_reference_binaries(data.document, data.artifacts)
            if options.rebuild_binaries
            else 0
        )
        report = analyze.analyze(data.document)
        # Unlike a fresh preflight, this compares the originally admitted
        # raw and bundle bytes without repeating optional native replay.
        evidence.recheck_evidence_snapshot(data.evidence_snapshot)
        _require_unchanged_manifests(data.manifest_fingerprints)
        _require_unchanged_sidecars(prefix, data.sidecar_fingerprints)
        current = _read_bounded_evidence(relative_study, limit=analyze.MAX_INPUT_BYTES)
        if _source_fingerprint(current) != data.study_fingerprint:
            _fail("host-C retained study JSON changed during audit")
        # Recheck original native binary claims after any optional rebuild or
        # oracle replay. The preflight may have admitted bytes that are no
        # longer present when this report is returned.
        if (
            reference_study.check_retained_artifacts(data.document, data.artifacts)
            != data.verified_binaries
        ):
            _fail("host-C retained artifact count changed during audit")
        _check_trial_file_inventory(data.document, data.artifacts, prefix)
    except ReferenceAuditError:
        # Local typed evidence rejections already contain the right diagnostic.
        raise
    except Exception as error:
        # Dependency faults must remain typed and safe to render at the CLI.
        message = f"host-C reference evidence audit failed: {_safe_error_detail(error)}"
        raise ReferenceAuditError(message) from error
    return {
        "schema_version": 1,
        "scope": (
            "Retained source-reported host-C reference evidence consistent; "
            "no Malbolge candidate execution, measurement replay, "
            "or physical budget attestation."
        ),
        "study": relative_study,
        "host_c_binaries_checked": data.verified_binaries,
        "host_c_failure_diagnostics_checked": data.failed_diagnostics,
        "recorded_source_commit": data.commit,
        "source_commit_object_verified": options.require_source_commit_object,
        "resource_controls_record_checked": data.resource_record_version > 0,
        "resource_controls_record_version": data.resource_record_version,
        "host_c_oracle_replayed": options.replay_oracles,
        "host_c_reference_builds_reproduced": rebuilt,
        "evidence_preflight": data.checked,
        "capacity_curve": report["capacity_curve"],
        "pareto_frontiers": report["pareto_frontiers"],
    }


def main() -> int:
    """Audit a retained local host-C study without modifying its files.

    Returns:
        Zero with a checked JSON audit report or two on admission failure.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", help=".temp/arena-host-c-study-*/study.json")
    parser.add_argument("--replay-oracles", action="store_true")
    parser.add_argument("--rebuild-binaries", action="store_true")
    parser.add_argument("--require-source-commit-object", action="store_true")
    parser.add_argument("--require-resource-controls-record", action="store_true")
    args = parser.parse_args()
    try:
        report = audit(
            args.study,
            options=AuditOptions(
                replay_oracles=args.replay_oracles,
                rebuild_binaries=args.rebuild_binaries,
                require_source_commit_object=args.require_source_commit_object,
                require_resource_controls_record=args.require_resource_controls_record,
            ),
        )
        report_output.publish(report, sys.stdout)
    except Exception as error:
        # Unexpected ordinary audit or publication dependency failures are
        # rejected too, without invoking untrusted exception format hooks.
        parser.exit(2, f"host-C reference audit: {_safe_error_detail(error)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
