# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Canonical ticket-admission profile generation from retained evidence.
# - Must-Not:
#   - Write product state implicitly or weaken retained comparison checks.
# - Allows:
#   - Inputs: one exact throughput evidence bundle.
#   - Outputs: canonical schema-v1 product profile JSON.
#   - Side effects: evidence file reads and explicit stdout only.
# - Split-When:
#   - Split when another benchmark family gains a distinct derivation protocol.
# - Merge-When:
#   - Merge when another generator owns this exact retained evidence mapping.
# - Summary:
#   - Generate product CUDA ticket-admission profiles from evidence.
# - Description:
#   - Reconstructs route promotion records and exact provenance
#     deterministically.
# - Usage:
#   - Run from repository root; tests compare output byte-for-byte with
#     product JSON.
# - Defaults:
#   - Identity, hash, route, sample, or comparison drift fails closed.
#

"""Generate canonical CUDA ticket-admission profiles from retained evidence."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
import tomllib
from typing import cast

from scripts.repository_root import repository_root

ROOT = repository_root(Path(__file__))
EVIDENCE_RELATIVE = (
    Path("benchmarks")
    / "accelerator"
    / "evidence"
    / "2026-07-29-independent-ticket-transfer-throughput-rtx4060"
)
TOOLCHAIN_RELATIVE = (
    Path("src/optimization/accelerator/adapter-outbound/accelerator/cuda")
    / "toolchain.json"
)
PROFILE_ID = "rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1"
BENCHMARK_ID = "cuda-independent-ticket-transfer-throughput-v1"
WORKLOAD_ID = "classic-crazy-full-domain-ticket-transfer-v1"
WORKLOAD_KIND = "crazy"
WORKLOAD_COUNT = 59_049
SCHEMA_VERSION = 4
EXPECTED_SAMPLE_COUNT = 15
RUNTIME_IDENTITY_ID = "cuda-runtime-toolchain-identity-v1"
MINIMUM_DRIVER_API_VERSION = 13_030
NVRTC_MAJOR = 13
NVRTC_MINOR = 3
NVRTC_PACKAGE_NAME = "cuda_nvrtc"
DISPLAY_DRIVER_VERSION = "610.88"
HOST_RUNTIME_IDENTITY_ID = "cuda-host-runtime-identity-v1"
HOST_EDITION = "Professional"
HOST_MACHINE = "x86_64"
HOST_RELEASE = "11"
HOST_SYSTEM = "Windows"
HOST_VERSION = "10.0.26200"
PYTHON_IMPLEMENTATION = "CPython"
PYTHON_VERSION = "3.14.6"
EXPECTED_HOST = "Microsoft Windows 11 Pro 10.0.26200 x86-64"
EXPECTED_RUN_TOOLCHAIN = (
    "Python 3.14.6; CUDA 13.3.1 (nvcc 13.3.73); NVIDIA driver 610.88"
)
EXPECTED_TOOLCHAIN_SHA256 = (
    "b8249cc1accf4b0532779c7c42e6505c9840d7208b4ab945e54daa456206b95e"
)
EXPECTED_SOURCE_COMMIT = "431f542ab6321eeb12b7bcb9195318f25cf376a5"
EXPECTED_WORKLOAD_SHA256 = (
    "a523502c24560424c7139b527019e3f26ded512db205dec12a073e4801d7f7dc"
)
EXPECTED_THROUGHPUT_SHA256 = (
    "edeed94f6ccca041d1db034ba7dfbc75c506e7c02069018c6f049d95e459916e"
)
EXPECTED_RAW_SHA256 = (
    "329716e4f429b7ab65096a61266af732b6630faf2bba2f66a643ea1b41d3214f"
)
SYNC_SEQUENTIAL = "synchronous-sequential"
SYNC_GROUPED = "synchronous-grouped"
STREAMED_SEQUENTIAL = "streamed-sequential"
STREAMED_GROUPED = "streamed-grouped"


class ProfileManifestError(ValueError):
    """Retained evidence cannot produce an exact product profile."""


@dataclass(frozen=True, slots=True)
class _EvidenceBundle:
    evidence_path: str
    experiment: dict[str, object]
    raw_sha256: str
    source_commit: str
    throughput: dict[str, object]
    throughput_sha256: str
    toolchain: dict[str, object]
    toolchain_sha256: str


@dataclass(frozen=True, slots=True)
class _RouteSpec:
    group_size: int
    mode: str
    paired_wins: int
    reference_id: str
    route_id: str


def main() -> int:
    """Emit canonical profile JSON after all retained evidence checks pass.

    Returns:
        Zero after one complete profile document reaches stdout.

    """
    payload = profile_manifest_text().encode("utf-8")
    _ = sys.stdout.buffer.write(payload)
    return 0


def profile_manifest_text(root: Path = ROOT) -> str:
    """Build canonical product profile JSON from one evidence bundle.

    Returns:
        Stable sorted, indented, LF-terminated JSON.

    """
    payload = profile_manifest(root)
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def profile_manifest(root: Path = ROOT) -> dict[str, object]:
    """Build one validated profile manifest object.

    Returns:
        Schema-v4 document containing one exact CUDA profile.

    """
    evidence = root / EVIDENCE_RELATIVE
    throughput_path = evidence / "throughput.json"
    raw_path = evidence / "raw.csv"
    bundle = _EvidenceBundle(
        evidence_path=(EVIDENCE_RELATIVE.as_posix() + "/"),
        experiment=_toml_object(evidence / "experiment.toml"),
        raw_sha256=_sha256(raw_path),
        source_commit=_read_text(evidence / "source-commit.txt").strip(),
        throughput=_json_object(throughput_path),
        throughput_sha256=_sha256(throughput_path),
        toolchain=_json_object(root / TOOLCHAIN_RELATIVE),
        toolchain_sha256=_sha256(root / TOOLCHAIN_RELATIVE),
    )
    _validate_evidence(bundle)
    return {
        "profiles": [_profile(bundle)],
        "schema_version": SCHEMA_VERSION,
    }


def _profile(bundle: _EvidenceBundle) -> dict[str, object]:
    throughput = bundle.throughput
    device = _object(throughput["device"], "throughput.device")
    workload = _object(throughput["workload"], "throughput.workload")
    measurement = _object(
        throughput["measurement"],
        "throughput.measurement",
    )
    run = _object(bundle.experiment["run"], "experiment.run")
    routes = _object(throughput["routes"], "throughput.routes")
    comparisons = _object(
        throughput["comparisons"],
        "throughput.comparisons",
    )
    return {
        "backend_id": _string(device["backend"], "device.backend"),
        "device_arch": _string(device["arch"], "device.arch"),
        "device_name": _string(device["name"], "device.name"),
        "evidence": {
            "benchmark_id": BENCHMARK_ID,
            "host": _string(run["host"], "run.host"),
            "path": bundle.evidence_path,
            "raw_sha256": bundle.raw_sha256,
            "source_commit": bundle.source_commit,
            "throughput_sha256": bundle.throughput_sha256,
            "toolchain": _string(run["toolchain"], "run.toolchain"),
        },
        "fallback_ticket_ns": _route_median(
            routes,
            f"{SYNC_SEQUENTIAL}-1",
            expected_mode=SYNC_SEQUENTIAL,
            expected_group=1,
        ),
        "profile_id": PROFILE_ID,
        "routes": _routes(routes, comparisons),
        "runtime": {
            "display_driver_version": DISPLAY_DRIVER_VERSION,
            "host_runtime": {
                "host_edition": HOST_EDITION,
                "host_machine": HOST_MACHINE,
                "host_release": HOST_RELEASE,
                "host_system": HOST_SYSTEM,
                "host_version": HOST_VERSION,
                "identity_id": HOST_RUNTIME_IDENTITY_ID,
                "python_implementation": PYTHON_IMPLEMENTATION,
                "python_version": PYTHON_VERSION,
            },
            "identity_id": RUNTIME_IDENTITY_ID,
            "minimum_driver_api_version": MINIMUM_DRIVER_API_VERSION,
            "nvrtc_major": NVRTC_MAJOR,
            "nvrtc_minor": NVRTC_MINOR,
            "toolchain_manifest_sha256": bundle.toolchain_sha256,
        },
        "sample_count": _int(
            measurement["sample_count"],
            "measurement.sample_count",
        ),
        "workload_count": _int(
            workload["count_per_ticket"],
            "workload.count_per_ticket",
        ),
        "workload_id": _string(workload["identity"], "workload.identity"),
        "workload_kind": _string(workload["kind"], "workload.kind"),
        "workload_sha256": _string(
            workload["sha256"],
            "workload.sha256",
        ),
    }


def _routes(
    routes: dict[str, object],
    comparisons: dict[str, object],
) -> list[dict[str, object]]:
    specs = [
        _RouteSpec(
            group_size=1,
            mode="streamed",
            paired_wins=_comparison_int(
                comparisons,
                group_size=1,
                key="streamed_sequential_wins",
            ),
            reference_id=f"{SYNC_SEQUENTIAL}-1",
            route_id=f"{STREAMED_SEQUENTIAL}-1",
        )
    ]
    for group_size in (2, 4, 8):
        specs.extend((
            _RouteSpec(
                group_size=group_size,
                mode="synchronous",
                paired_wins=_comparison_int(
                    comparisons,
                    group_size=group_size,
                    key="synchronous_grouped_wins",
                ),
                reference_id=f"{SYNC_SEQUENTIAL}-{group_size}",
                route_id=f"{SYNC_GROUPED}-{group_size}",
            ),
            _RouteSpec(
                group_size=group_size,
                mode="streamed",
                paired_wins=_comparison_int(
                    comparisons,
                    group_size=group_size,
                    key="streamed_grouped_wins_over_synchronous_grouped",
                ),
                reference_id=f"{SYNC_GROUPED}-{group_size}",
                route_id=f"{STREAMED_GROUPED}-{group_size}",
            ),
        ))
    return [_route(routes, spec) for spec in specs]


def _route(
    routes: dict[str, object],
    spec: _RouteSpec,
) -> dict[str, object]:
    candidate_median = _route_median(
        routes,
        spec.route_id,
        expected_mode=spec.route_id.rsplit("-", maxsplit=1)[0],
        expected_group=spec.group_size,
    )
    reference_median = _route_median(
        routes,
        spec.reference_id,
        expected_mode=spec.reference_id.rsplit("-", maxsplit=1)[0],
        expected_group=spec.group_size,
    )
    return {
        "candidate_median_ns": candidate_median,
        "exact_results": True,
        "group_size": spec.group_size,
        "mode": spec.mode,
        "paired_wins": spec.paired_wins,
        "reference_median_ns": reference_median,
    }


def _validate_evidence(bundle: _EvidenceBundle) -> None:
    _expect_equal(
        _string(
            bundle.throughput["benchmark_id"],
            "throughput.benchmark_id",
        ),
        BENCHMARK_ID,
        "throughput benchmark identity",
    )
    _expect_equal(
        bundle.source_commit,
        EXPECTED_SOURCE_COMMIT,
        "evidence source commit",
    )
    _expect_equal(
        bundle.throughput_sha256,
        EXPECTED_THROUGHPUT_SHA256,
        "throughput hash",
    )
    _expect_equal(
        bundle.raw_sha256,
        EXPECTED_RAW_SHA256,
        "raw sample hash",
    )
    _validate_throughput(bundle.throughput)
    _validate_experiment(bundle.experiment)
    _validate_toolchain(bundle.toolchain, bundle.toolchain_sha256)


def _validate_throughput(throughput: dict[str, object]) -> None:
    workload = _object(throughput["workload"], "throughput.workload")
    measurement = _object(
        throughput["measurement"],
        "throughput.measurement",
    )
    device = _object(throughput["device"], "throughput.device")
    routes = _object(throughput["routes"], "throughput.routes")
    comparisons = _object(
        throughput["comparisons"],
        "throughput.comparisons",
    )
    outcome = _object(
        throughput["hypothesis_outcome"],
        "throughput.hypothesis_outcome",
    )
    expectations = (
        (_string(workload["identity"], "workload.identity"), WORKLOAD_ID),
        (_string(workload["kind"], "workload.kind"), WORKLOAD_KIND),
        (
            _string(workload["sha256"], "workload.sha256"),
            EXPECTED_WORKLOAD_SHA256,
        ),
        (
            _int(workload["count_per_ticket"], "workload.count_per_ticket"),
            WORKLOAD_COUNT,
        ),
        (
            _int(measurement["sample_count"], "measurement.sample_count"),
            EXPECTED_SAMPLE_COUNT,
        ),
        (_string(device["backend"], "device.backend"), "cuda"),
        (_string(device["arch"], "device.arch"), "sm_89"),
        (_string(device["name"], "device.name"), "NVIDIA GeForce RTX 4060"),
        (len(routes), 14),
        (len(comparisons), 4),
        (_bool(outcome["passed"], "hypothesis_outcome.passed"), False),
    )
    for observed, expected in expectations:
        _expect_equal(observed, expected, "retained throughput identity")


def _validate_experiment(experiment: dict[str, object]) -> None:
    identity = _object(experiment["experiment"], "experiment.experiment")
    challenge = _object(experiment["challenge"], "experiment.challenge")
    budget = _object(experiment["budget"], "experiment.budget")
    run = _object(experiment["run"], "experiment.run")
    expectations = (
        (_string(identity["id"], "experiment.id"), BENCHMARK_ID),
        (_string(challenge["family"], "challenge.family"), WORKLOAD_ID),
        (_int(challenge["difficulty"], "challenge.difficulty"), WORKLOAD_COUNT),
        (_int(budget["samples"], "budget.samples"), EXPECTED_SAMPLE_COUNT),
        (
            _int(budget["words_per_ticket"], "budget.words_per_ticket"),
            WORKLOAD_COUNT,
        ),
        (_string(run["commit"], "run.commit"), EXPECTED_SOURCE_COMMIT),
        (_string(run["host"], "run.host"), EXPECTED_HOST),
        (_string(run["toolchain"], "run.toolchain"), EXPECTED_RUN_TOOLCHAIN),
        (
            _string(run["workload_sha256"], "run.workload_sha256"),
            EXPECTED_WORKLOAD_SHA256,
        ),
        (_string(run["outcome"], "run.outcome"), "success"),
    )
    for observed, expected in expectations:
        _expect_equal(observed, expected, "retained experiment identity")


def _validate_toolchain(
    toolchain: dict[str, object],
    toolchain_sha256: str,
) -> None:
    _expect_equal(
        toolchain_sha256,
        EXPECTED_TOOLCHAIN_SHA256,
        "CUDA toolchain manifest hash",
    )
    expectations = (
        (_int(toolchain["schema_version"], "toolchain.schema_version"), 1),
        (
            _string(toolchain["cuda_release"], "toolchain.cuda_release"),
            "13.3 Update 1",
        ),
        (
            _string(toolchain["platform"], "toolchain.platform"),
            "windows-x86_64",
        ),
        (
            _string(toolchain["toolkit_root"], "toolchain.toolkit_root"),
            ".dependencies/cuda/13.3.1/toolkit",
        ),
    )
    for observed, expected in expectations:
        _expect_equal(observed, expected, "CUDA toolchain identity")
    packages = _array(toolchain["packages"], "toolchain.packages")
    nvrtc = tuple(
        package
        for package in (
            _object(entry, f"toolchain.packages[{index}]")
            for index, entry in enumerate(packages)
        )
        if _string(package["name"], "toolchain package name")
        == NVRTC_PACKAGE_NAME
    )
    if len(nvrtc) != 1:
        message = "CUDA toolchain must contain exactly one cuda_nvrtc package"
        raise ProfileManifestError(message)
    _expect_equal(
        _string(nvrtc[0]["version"], "cuda_nvrtc.version"),
        "13.3.33",
        "NVRTC package version",
    )


def _route_median(
    routes: dict[str, object],
    route_id: str,
    *,
    expected_mode: str,
    expected_group: int,
) -> int:
    route = _object(routes[route_id], f"routes.{route_id}")
    _expect_equal(
        _string(route["route_id"], f"routes.{route_id}.route_id"),
        route_id,
        "route identity",
    )
    _expect_equal(
        _string(route["mode"], f"routes.{route_id}.mode"),
        expected_mode,
        "route mode",
    )
    _expect_equal(
        _int(route["group_size"], f"routes.{route_id}.group_size"),
        expected_group,
        "route group size",
    )
    return _positive_int(route["median_ns"], f"routes.{route_id}.median_ns")


def _comparison_int(
    comparisons: dict[str, object],
    *,
    group_size: int,
    key: str,
) -> int:
    comparison = _object(
        comparisons[str(group_size)],
        f"comparisons.{group_size}",
    )
    _expect_equal(
        _int(comparison["group_size"], f"comparisons.{group_size}.group_size"),
        group_size,
        "comparison group size",
    )
    return _nonnegative_int(
        comparison[key],
        f"comparisons.{group_size}.{key}",
    )


def _json_object(path: Path) -> dict[str, object]:
    try:
        parsed = cast(
            "object",
            json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            ),
        )
    except (json.JSONDecodeError, OSError) as error:
        message = f"cannot read retained JSON evidence {path}: {error}"
        raise ProfileManifestError(message) from error
    return _object(parsed, str(path))


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            message = f"retained JSON evidence contains duplicate key: {key}"
            raise ProfileManifestError(message)
        result[key] = value
    return result


def _toml_object(path: Path) -> dict[str, object]:
    try:
        parsed = cast(
            "object",
            tomllib.loads(path.read_text(encoding="utf-8")),
        )
    except (OSError, tomllib.TOMLDecodeError) as error:
        message = f"cannot read retained TOML evidence {path}: {error}"
        raise ProfileManifestError(message) from error
    return _object(parsed, str(path))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        message = f"cannot read retained evidence {path}: {error}"
        raise ProfileManifestError(message) from error


def _sha256(path: Path) -> str:
    try:
        payload = path.read_bytes()
    except OSError as error:
        message = f"cannot hash retained evidence {path}: {error}"
        raise ProfileManifestError(message) from error
    return sha256(payload).hexdigest()


def _object(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        message = f"{context} must be an object"
        raise ProfileManifestError(message)
    raw = cast("dict[object, object]", value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            message = f"{context} contains a non-string key"
            raise ProfileManifestError(message)
        result[key] = item
    return result


def _array(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        message = f"{context} must be an array"
        raise ProfileManifestError(message)
    return cast("list[object]", value)


def _string(value: object, context: str) -> str:
    if type(value) is not str or not value:
        message = f"{context} must be a non-empty string"
        raise ProfileManifestError(message)
    return value


def _int(value: object, context: str) -> int:
    if type(value) is not int:
        message = f"{context} must be an integer"
        raise ProfileManifestError(message)
    return value


def _positive_int(value: object, context: str) -> int:
    observed = _int(value, context)
    if observed <= 0:
        message = f"{context} must be positive"
        raise ProfileManifestError(message)
    return observed


def _nonnegative_int(value: object, context: str) -> int:
    observed = _int(value, context)
    if observed < 0:
        message = f"{context} must be non-negative"
        raise ProfileManifestError(message)
    return observed


def _bool(value: object, context: str) -> bool:
    if type(value) is not bool:
        message = f"{context} must be boolean"
        raise ProfileManifestError(message)
    return value


def _expect_equal(observed: object, expected: object, context: str) -> None:
    if observed == expected:
        return
    message = f"{context} drifted: expected {expected!r}, observed {observed!r}"
    raise ProfileManifestError(message)


if __name__ == "__main__":
    raise SystemExit(main())
