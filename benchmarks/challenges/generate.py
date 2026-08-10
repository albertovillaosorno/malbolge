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
#   - Deterministic versioned compiler-challenge generation.
# - Must-Not:
#   - Depend on host randomness, host integer overflow, or compiler internals.
# - Allows:
#   - Inputs: explicit family/version/seed/profile/difficulty and output root.
#   - Outputs: one C source, binary oracle, and canonical JSON manifest.
#   - Side effects: atomic publication below the requested output root.
# - Split-When:
#   - Another family requires an independent semantic oracle or input model.
# - Merge-When:
#   - Another generator has identical identity and oracle semantics.
# - Summary:
#   - Deterministic parametric compiler challenge generator.
# - Description:
#   - Generates replayable arithmetic DAG workloads with exact C32 oracles.
# - Usage:
#   - `python benchmarks/challenges/generate.py arithmetic-dag ...`.
# - Defaults:
#   - Invalid identities, collisions, and difficulty parameters fail closed.
#

"""Deterministic parametric compiler challenge generation."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Never, Protocol, cast

_WINDOWS_OS_NAME: Final = "nt"
_LINUX_PLATFORM: Final = "linux"
_AT_FDCWD: Final = -100
_RENAME_NOREPLACE: Final = 1

_FAMILY: Final = "arithmetic-dag"
_VERSION: Final = 1
_MASK32: Final = (1 << 32) - 1
_MASK64: Final = (1 << 64) - 1
_MAX_NODES: Final = 1_000_000
_OP_ADD: Final = 0
_OP_XOR: Final = 1
_OP_MULTIPLY: Final = 2
_ORACLE_BYTES: Final = 4
_ENTRY_SYMBOL: Final = "malbolge_challenge"
_PROFILE_CANONICALIZATION: Final = "malbolge-profile-v1"
_PROFILE_PREFIX: Final = f"{_PROFILE_CANONICALIZATION}:sha256:"
_ROOT: Final = Path(__file__).resolve().parents[2]
_COMPOSITION_ROOT: Final = _ROOT / "src" / "automation" / "repository" / "composition"
if str(_COMPOSITION_ROOT) not in sys.path:
    sys.path.insert(0, str(_COMPOSITION_ROOT))

from scripts.validate import (  # ruff: ignore[module-import-not-at-top-of-file]
    target_profile,
)

_PROFILE_MANIFEST: Final = target_profile.FINGERPRINT_MANIFEST
_EXPECTED_ARTIFACTS: Final = frozenset(
    {
        "manifest.json",
        "oracle.bin",
        "program.c",
    }
)


class _RenameAt2(Protocol):
    """Typed view of the Linux libc renameat2 entry point."""

    argtypes: tuple[object, ...]
    restype: object

    def __call__(self, *arguments: int | bytes) -> int:
        """Rename one path with the fixed Linux renameat2 ABI arguments."""
        ...


class ChallengeError(ValueError):
    """Raised when challenge identity or publication cannot fail safely."""


def _fail(message: str, cause: BaseException | None = None) -> Never:
    if cause is None:
        raise ChallengeError(message)
    raise ChallengeError(message) from cause


def _canonical_profile_document() -> target_profile.JsonObject:
    try:
        return target_profile.load_document(target_profile.DEFAULT_PROFILE)
    except (OSError, target_profile.ProfileValidationError) as error:
        message = "canonical target profile authority is unavailable or invalid"
        _fail(message, error)


def _verify_profile_projection(canonical: target_profile.JsonObject) -> None:
    try:
        observed_projection = _PROFILE_MANIFEST.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        message = "canonical profile fingerprint manifest is unavailable"
        _fail(message, error)
    expected_projection = target_profile.render_profile_fingerprint_manifest(canonical)
    if observed_projection != expected_projection:
        message = "canonical profile fingerprint manifest disagrees with registry"
        _fail(message)


def _canonical_profile_fingerprint(profile_id: str) -> str:
    canonical = _canonical_profile_document()
    _verify_profile_projection(canonical)
    try:
        return target_profile.profile_fingerprint(canonical, profile_id)
    except target_profile.ProfileValidationError as error:
        message = f"unsupported canonical target profile: {profile_id}"
        _fail(message, error)


@dataclass(frozen=True, slots=True)
class ChallengeIdentity:
    """Stable identity of one generated challenge."""

    family: str
    version: int
    seed: int
    profile: str
    nodes: int

    def validate(self) -> None:
        """Validate exact family/version/profile/difficulty identity."""
        _validate_family_version(self.family, self.version)
        _validate_seed(self.seed)
        _validate_profile(self.profile)
        _validate_nodes(self.nodes)


def _validate_family_version(family: str, version: int) -> None:
    if family != _FAMILY:
        message = f"unsupported challenge family: {family}"
        _fail(message)
    if type(version) is not int or version != _VERSION:
        message = f"unsupported {_FAMILY} version: {version}"
        _fail(message)


def _validate_seed(seed: int) -> None:
    if type(seed) is not int or not 0 <= seed <= _MASK64:
        message = "seed must be an unsigned 64-bit integer"
        _fail(message)


def _validate_profile(profile: str) -> None:
    if type(profile) is not str or not profile or profile != profile.strip():
        message = "profile must be a non-empty unpadded identity"
        _fail(message)
    _ = _canonical_profile_fingerprint(profile)


def _validate_nodes(nodes: int) -> None:
    if type(nodes) is not int or not 1 <= nodes <= _MAX_NODES:
        message = f"nodes must be in [1, {_MAX_NODES}]"
        _fail(message)


@dataclass(frozen=True, slots=True)
class GeneratedChallenge:
    """One generated source/oracle/manifest payload."""

    source: bytes
    oracle: bytes
    manifest: bytes


class _SplitMix64:
    """Version-stable SplitMix64 stream used only for challenge construction."""

    def __init__(self, seed: int) -> None:
        self._state: int = seed & _MASK64

    def next_u64(self) -> int:
        """Return the next SplitMix64 word.

        Returns:
            The next deterministic unsigned 64-bit stream value.

        """
        self._state = (self._state + 0x9E3779B97F4A7C15) & _MASK64
        value = self._state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
        return (value ^ (value >> 31)) & _MASK64

    def next_u32(self) -> int:
        """Return the low 32 bits of the next word.

        Returns:
            The next deterministic unsigned 32-bit stream value.

        """
        return self.next_u64() & _MASK32


def _rotate_left(value: int, shift: int) -> int:
    shift &= 31
    if shift == 0:
        return value & _MASK32
    return ((value << shift) | (value >> (32 - shift))) & _MASK32


def _node_expression(
    rng: _SplitMix64, index: int, values: list[int]
) -> tuple[str, int]:
    left_index = len(values) - 1
    right_index = rng.next_u64() % len(values)
    left = values[left_index]
    right = values[right_index]
    operation = rng.next_u64() % 4
    if operation == _OP_ADD:
        expression = f"v{left_index} + v{right_index}"
        value = (left + right) & _MASK32
    elif operation == _OP_XOR:
        expression = f"v{left_index} ^ v{right_index}"
        value = left ^ right
    elif operation == _OP_MULTIPLY:
        multiplier = rng.next_u32() | 1
        expression = f"v{left_index} * UINT32_C({multiplier})"
        value = (left * multiplier) & _MASK32
    else:
        shift = int((rng.next_u64() % 31) + 1)
        expression = f"(v{left_index} << {shift}) | (v{left_index} >> {32 - shift})"
        value = _rotate_left(left, shift)
    return f"    uint32_t v{index} = {expression};", value


def _program_payload(identity: ChallengeIdentity) -> tuple[bytes, bytes]:
    rng = _SplitMix64(identity.seed)
    initial = rng.next_u32()
    lines = [
        "#include <stdint.h>",
        "",
        f"uint32_t {_ENTRY_SYMBOL}(void) {{",
        f"    uint32_t v0 = UINT32_C({initial});",
    ]
    values = [initial]
    for index in range(1, identity.nodes + 1):
        line, value = _node_expression(rng, index, values)
        lines.append(line)
        values.append(value)
    final = values[-1]
    lines.extend(
        (
            f"    return v{identity.nodes};",
            "}",
            "",
            "int main(void) {",
            f"    uint32_t result = {_ENTRY_SYMBOL}();",
            "    return (int)(result & UINT32_C(2147483647));",
            "}",
            "",
        )
    )
    source = "\n".join(lines).encode()
    oracle = final.to_bytes(_ORACLE_BYTES, byteorder="little")
    return source, oracle


def _manifest_bytes(
    identity: ChallengeIdentity,
    source: bytes,
    oracle: bytes,
    *,
    profile_fingerprint: str,
) -> bytes:
    manifest_object = {
        "schema": "malbolge-parametric-challenge/v1",
        "identity": {
            "family": identity.family,
            "version": identity.version,
            "seed": identity.seed,
            "target_profile": identity.profile,
            "target_profile_fingerprint": profile_fingerprint,
            "difficulty": {"nodes": identity.nodes},
        },
        "artifacts": {
            "source": "program.c",
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "oracle": "oracle.bin",
            "oracle_sha256": hashlib.sha256(oracle).hexdigest(),
            "oracle_bytes": len(oracle),
        },
        "oracle_semantics": "entry-return-u32-little-endian",
        "entry_symbol": _ENTRY_SYMBOL,
        "standalone_main": "low-31-bits-only-not-oracle",
        "generator": {
            "family_algorithm": "splitmix64-arithmetic-dag-v1",
            "unsigned_arithmetic": "modulo-2-to-32",
        },
    }
    text = json.dumps(manifest_object, sort_keys=True, separators=(",", ":"))
    return f"{text}\n".encode()


def generate(identity: ChallengeIdentity) -> GeneratedChallenge:
    """Generate one deterministic `arithmetic-dag/v1` challenge.

    Returns:
        Exact source, oracle, and canonical manifest bytes.

    """
    identity.validate()
    profile_fingerprint = _canonical_profile_fingerprint(identity.profile)
    source, oracle = _program_payload(identity)
    manifest = _manifest_bytes(
        identity, source, oracle, profile_fingerprint=profile_fingerprint
    )
    return GeneratedChallenge(source=source, oracle=oracle, manifest=manifest)


def _path_redirects(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _published_artifact_paths(
    root: Path,
) -> tuple[Path, Path, Path] | None:
    if _path_redirects(root) or not root.is_dir():
        return None
    entries = frozenset(path.name for path in root.iterdir())
    if entries != _EXPECTED_ARTIFACTS:
        return None
    artifacts = (
        root / "program.c",
        root / "oracle.bin",
        root / "manifest.json",
    )
    redirected = any(_path_redirects(path) or not path.is_file() for path in artifacts)
    return None if redirected else artifacts


def _published_payload(root: Path) -> GeneratedChallenge | None:
    try:
        artifacts = _published_artifact_paths(root)
        if artifacts is None:
            return None
        source, oracle, manifest = artifacts
        return GeneratedChallenge(
            source=source.read_bytes(),
            oracle=oracle.read_bytes(),
            manifest=manifest.read_bytes(),
        )
    except OSError:
        return None


def _existing_output_is_replay(
    output_root: Path,
    generated: GeneratedChallenge,
) -> bool:
    if not output_root.exists() and not _path_redirects(output_root):
        return False
    if _published_payload(output_root) == generated:
        return True
    message = f"output path already exists: {output_root}"
    _fail(message)


def _reject_linked_output_ancestor(parent: Path) -> None:
    candidate = parent
    while True:
        if _path_redirects(candidate):
            message = f"output path has linked ancestor: {candidate}"
            _fail(message)
        ancestor = candidate.parent
        if ancestor == candidate:
            return
        candidate = ancestor


def _staging_path(output_root: Path) -> Path:
    if output_root.name in {"", ".", ".."}:
        message = "output path must name a distinct directory"
        _fail(message)
    parent = output_root.parent
    _reject_linked_output_ancestor(parent)
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        message = f"output parent cannot be prepared: {parent}"
        _fail(message, error)
    staging = parent / f".{output_root.name}.staging"
    if staging.exists() or _path_redirects(staging):
        message = f"staging path already exists: {staging}"
        _fail(message)
    return staging


def _claim_staging(staging: Path) -> None:
    try:
        staging.mkdir()
    except FileExistsError as error:
        message = f"staging path already exists: {staging}"
        _fail(message, error)
    except OSError as error:
        message = f"staging path cannot be created: {staging}"
        _fail(message, error)


def _write_staging(staging: Path, generated: GeneratedChallenge) -> None:
    _ = (staging / "program.c").write_bytes(generated.source)
    _ = (staging / "oracle.bin").write_bytes(generated.oracle)
    _ = (staging / "manifest.json").write_bytes(generated.manifest)


def _linux_rename_noreplace(source: Path, destination: Path) -> None:
    try:
        library = ctypes.CDLL(None, use_errno=True)
        renameat2 = cast("_RenameAt2", cast("object", library.renameat2))
        renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameat2.restype = ctypes.c_int
    except (AttributeError, OSError) as error:
        raise OSError(
            errno.ENOTSUP,
            "Linux renameat2(RENAME_NOREPLACE) is unavailable",
            destination,
        ) from error
    result = renameat2(
        _AT_FDCWD,
        os.fsencode(source),
        _AT_FDCWD,
        os.fsencode(destination),
        _RENAME_NOREPLACE,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(
            error_number,
            os.strerror(error_number),
            destination,
        )


def _publish_staging_no_replace(
    staging: Path,
    output_root: Path,
    *,
    os_name: str = os.name,
    platform: str = sys.platform,
) -> None:
    if os_name == _WINDOWS_OS_NAME:
        _ = staging.rename(output_root)
        return
    if platform == _LINUX_PLATFORM:
        _linux_rename_noreplace(staging, output_root)
        return
    raise OSError(
        errno.ENOTSUP,
        "atomic no-replace directory publication is unsupported",
        output_root,
    )


def write_challenge(identity: ChallengeIdentity, output_root: Path) -> None:
    """Publish without deleting pre-existing unrelated state."""
    generated = generate(identity)
    _reject_linked_output_ancestor(output_root.parent)
    if _existing_output_is_replay(output_root, generated):
        return
    staging = _staging_path(output_root)
    _claim_staging(staging)
    try:
        _write_staging(staging, generated)
        _publish_staging_no_replace(staging, output_root)
    except OSError as error:
        shutil.rmtree(staging, ignore_errors=True)
        message = f"challenge publication failed: {error}"
        _fail(message, error)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("family", choices=[_FAMILY])
    _ = parser.add_argument("--version", type=int, required=True)
    _ = parser.add_argument("--seed", type=int, required=True)
    _ = parser.add_argument("--profile", required=True)
    _ = parser.add_argument("--nodes", type=int, required=True)
    _ = parser.add_argument("--output", type=Path, required=True)
    return parser


def _parsed_identity(
    arguments: dict[str, object],
) -> tuple[ChallengeIdentity, Path]:
    family = arguments.get("family")
    version = arguments.get("version")
    seed = arguments.get("seed")
    profile = arguments.get("profile")
    nodes = arguments.get("nodes")
    output = arguments.get("output")
    if not isinstance(output, Path):
        message = "challenge generation failed: output must be a path"
        raise SystemExit(message)
    if not (
        type(family) is str
        and type(profile) is str
        and type(version) is int
        and type(seed) is int
        and type(nodes) is int
    ):
        message = "challenge generation failed: invalid CLI argument types"
        raise SystemExit(message)
    return ChallengeIdentity(family, version, seed, profile, nodes), output


def main() -> int:
    """Run the deterministic challenge CLI.

    Returns:
        Zero after an exact challenge is published or replayed.

    Raises:
        SystemExit: If CLI arguments or challenge publication are invalid.

    """
    arguments = cast("dict[str, object]", vars(_parser().parse_args()))
    identity, output = _parsed_identity(arguments)
    try:
        write_challenge(identity, output)
    except ChallengeError as error:
        message = f"challenge generation failed: {error}"
        raise SystemExit(message) from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
