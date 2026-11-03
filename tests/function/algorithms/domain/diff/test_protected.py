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
#   - Synthetic end-to-end tests for protected exact-baseline plans.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic end-to-end tests for protected exact-baseline plans."""

from __future__ import annotations

import builtins
import hashlib
import ntpath
import os
import shutil
from dataclasses import replace
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, SupportsIndex, cast, override

import pytest
from algorithms.diff import protected as protected_module
from algorithms.diff.admission import identity_tree
from algorithms.diff.exact import build_exact_plan, snapshot_tree
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.model import OracleLiteral, SourceSlice, TreeSnapshot
from algorithms.diff.payload import AuthenticatedPayload, PayloadCryptoError
from algorithms.diff.protected import (
    PayloadSlice,
    ProtectedInstruction,
    ProtectedInstructionKind,
    ProtectedMetadata,
    ProtectedPlanError,
    materialize_protected_exact_plan,
    protect_exact_plan,
    protected_plan_aad,
    recover_exact_plan,
)
from algorithms.diff.source_binding import (
    SourceBindingError,
    SourceBindingPolicy,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.model import ExactAuthoringPlan
    from algorithms.diff.protected import ProtectedExactPlan
    from algorithms.diff.source_binding import ThresholdBinding

_CONTEXT = b"synthetic-protected-exact-v1"
_BLOCK_COUNT = 48
_PASSTHROUGH_RUNTIME_DATA = b"runtime-data"
_MISSING = "missing"
_REORDERED = "reordered"
_WRONG_DIGEST = "wrong-digest"
_EXTRA = "extra"
_PATH_PARTS = "parts"
_PATH_AS_POSIX = "as_posix"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _source_bytes(label: str) -> bytes:
    return b"".join(
        hashlib.sha256(f"{label}:{index}".encode()).digest()
        for index in range(_BLOCK_COUNT)
    )


def _write(root: Path, relative: str, data: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(data)


def _fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, bytes]]:
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    source_files = {
        "keep.bin": _source_bytes("keep"),
        "patch.bin": _source_bytes("patch"),
        "move-from.bin": _source_bytes("move"),
    }
    for path, data in source_files.items():
        _write(source, path, data)
    _write(oracle, "keep.bin", source_files["keep.bin"])
    patch = source_files["patch.bin"]
    _write(oracle, "patch.bin", patch[:311] + b"TARGET-ONLY" + patch[311:])
    _write(oracle, "move-to.bin", source_files["move-from.bin"])
    _write(oracle, "new.bin", b"new-target-only\x00binary\xffpayload")
    return source, oracle, source_files


def _identity(files: dict[str, bytes]) -> IdentityTree:
    return identity_tree(files)


def _policy() -> SourceBindingPolicy:
    return SourceBindingPolicy(
        threshold_fraction=0.66,
        maximum_anchors=9,
        minimum_anchor_files=2,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )


def _protected(
    tmp_path: Path,
) -> tuple[
    Path, Path, dict[str, bytes], ExactAuthoringPlan, ProtectedExactPlan
]:
    source, oracle, source_files = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    protected = protect_exact_plan(
        exact,
        _identity(source_files),
        binding_policy=_policy(),
        context=_CONTEXT,
    )
    return source, oracle, source_files, exact, protected


def _protected_bytes(plan: ProtectedExactPlan) -> tuple[bytes, ...]:
    share_bytes = tuple(
        value
        for share in plan.binding.shares
        for value in (share.anchor_digest, share.masked_share)
    )
    return (
        plan.context,
        plan.nonce,
        plan.payload.ciphertext,
        plan.payload.tag,
        plan.binding.context,
        plan.binding.secret_commitment,
        *share_bytes,
    )


def test_protection_is_deterministic_and_contains_no_plaintext_literals(
    tmp_path: Path,
) -> None:
    """Replace local oracle literals with ciphertext and payload references."""
    source, oracle, source_files, exact, first = _protected(tmp_path)
    second = protect_exact_plan(
        exact,
        _identity(source_files),
        binding_policy=_policy(),
        context=_CONTEXT,
    )
    segment_literals = tuple(
        segment.data
        for instruction in exact.instructions
        for segment in instruction.segments
        if isinstance(segment, OracleLiteral)
    )
    whole_literals = tuple(
        instruction.literal
        for instruction in exact.instructions
        if instruction.literal is not None
    )
    protected_bytes = _protected_bytes(first)

    _expect(first == second, "protected exact plan is not deterministic")
    _expect(first.payload.ciphertext, "fixture produced no encrypted payload")
    for literal in (*segment_literals, *whole_literals):
        if literal:
            _expect(
                literal not in protected_bytes,
                "plaintext literal leaked into plan",
            )
    _expect(source.is_dir() and oracle.is_dir(), "fixture roots disappeared")


def test_payload_key_schedule_depends_on_unserialized_source_bytes(
    tmp_path: Path,
) -> None:
    """Require source bytes, not only emitted source hashes, for keying."""
    source, _, source_files, exact, first = _protected(tmp_path)
    changed_files = dict(source_files)
    changed_files["keep.bin"] = _source_bytes("different-source-identity")
    second = protect_exact_plan(
        exact,
        _identity(changed_files),
        binding_policy=_policy(),
        context=_CONTEXT,
    )

    _expect(
        first.payload != second.payload,
        "payload encryption ignored canonical source identity bytes",
    )
    _expect(
        first.binding.secret_commitment != second.binding.secret_commitment,
        "source identity change did not change bound payload key",
    )
    _expect(source.is_dir(), "source fixture disappeared")


def test_protected_key_schedule_resists_replaced_global_sha256(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Distinct literal streams cannot reuse a key and fixed nonce via a forged hash."""
    source, oracle, source_files = _fixture(tmp_path)
    original = build_exact_plan(source, oracle)
    _write(oracle, "new.bin", b"different-oracle-literal-stream")
    changed = build_exact_plan(source, oracle)
    identity = _identity(source_files)

    calls = 0

    class _CollidingHash:
        def update(self, _data: bytes) -> None:
            _ = _data

        def digest(self) -> bytes:
            return bytes(32)

    def fake_sha256(_data: bytes = b"") -> _CollidingHash:
        nonlocal calls
        calls += 1
        return _CollidingHash()

    monkeypatch.setattr(hashlib, "sha256", fake_sha256)
    first = protect_exact_plan(
        original, identity, binding_policy=_policy(), context=_CONTEXT
    )
    second = protect_exact_plan(
        changed, identity, binding_policy=_policy(), context=_CONTEXT
    )
    _expect(first.nonce == second.nonce, "fixed nonce contract changed")
    _expect(
        first.binding.secret_commitment != second.binding.secret_commitment,
        "foreign hash caused identical encryption keys for distinct plaintexts",
    )
    _expect(calls == 0, "mutable process-global SHA-256 was consulted")


def test_source_plus_protected_plan_reconstructs_oracle_without_oracle_runtime(
    tmp_path: Path,
) -> None:
    """Materialize exactly after deleting the local authoring oracle."""
    source, oracle, source_files, _, protected = _protected(tmp_path)
    expected = snapshot_tree(oracle)
    shutil.rmtree(oracle)
    output = tmp_path / "out"

    materialize_protected_exact_plan(
        source,
        _identity(source_files),
        plan=protected,
        output_root=output,
    )

    _expect(
        snapshot_tree(output) == expected,
        "protected output changed target tree",
    )


def test_transform_without_source_evidence_cannot_recover_literals(
    tmp_path: Path,
) -> None:
    """Reject protected metadata when no candidate source is supplied."""
    _, _, _, _, protected = _protected(tmp_path)

    with pytest.raises(
        SourceBindingError,
        match="insufficient source-bound anchors",
    ):
        _ = recover_exact_plan(protected, identity_tree({}))


def test_unrelated_source_identity_cannot_recover_literals(
    tmp_path: Path,
) -> None:
    """Reject same-shaped but unrelated canonical source evidence."""
    _, _, source_files, _, protected = _protected(tmp_path)
    unrelated = {
        path: _source_bytes(f"unrelated-{index}")
        for index, path in enumerate(sorted(source_files))
    }

    with pytest.raises(
        SourceBindingError,
        match="insufficient source-bound anchors",
    ):
        _ = recover_exact_plan(protected, _identity(unrelated))


def test_protected_authoring_rejects_foreign_inputs(tmp_path: Path) -> None:
    """Validate authoring records before instructions or source evidence."""
    source, oracle, source_files = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    identity = _identity(source_files)
    policy = _policy()

    with pytest.raises(ProtectedPlanError, match="exact ExactAuthoringPlan"):
        _ = protect_exact_plan(
            cast("ExactAuthoringPlan", object()),
            identity,
            binding_policy=policy,
            context=_CONTEXT,
        )
    with pytest.raises(ProtectedPlanError, match="exact IdentityTree"):
        _ = protect_exact_plan(
            exact,
            cast("IdentityTree", object()),
            binding_policy=policy,
            context=_CONTEXT,
        )
    with pytest.raises(
        ProtectedPlanError, match=r"authoring context.*exact bytes"
    ):
        _ = protect_exact_plan(
            exact,
            identity,
            binding_policy=policy,
            context=cast("bytes", cast("object", bytearray(_CONTEXT))),
        )


@pytest.mark.parametrize(
    "invalid", ["nested/../escape.bin", "nested//unsafe.bin"]
)
def test_protected_path_admission_ignores_late_any_hook(
    monkeypatch: pytest.MonkeyPatch,
    invalid: str,
) -> None:
    """An untrusted callback cannot suppress path-component validation."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: False)
        try:
            _ = ProtectedInstruction(
                output_path=invalid,
                kind=ProtectedInstructionKind.COPY_SOURCE,
                expected_sha256="0" * 64,
                source_path="safe.bin",
            )
        except ProtectedPlanError:
            rejected = True
    assert rejected, "a late any hook admitted an unsafe output path"


def test_protected_roots_reject_overlap_under_late_enumerate_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late iterator alias cannot skip protected root overlap checks."""

    def suppress_indices(_items: object) -> tuple[()]:
        return ()

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "enumerate", suppress_indices)
        try:
            _ = ProtectedMetadata(
                source=TreeSnapshot(files=()),
                target=TreeSnapshot(files=()),
                instructions=(),
                passthrough_roots=("data", "data/archive"),
            )
        except ProtectedPlanError:
            rejected = True
    message = "late enumerate hook admitted overlapping passthrough roots"
    assert rejected, message


def test_protected_roots_ignore_late_sorted_set_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed authenticated passthrough roots remain rejected."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "sorted", lambda values: list(values))
        patched.setattr(builtins, "set", lambda values: list(values))
        try:
            _ = ProtectedMetadata(
                source=TreeSnapshot(files=()),
                target=TreeSnapshot(files=()),
                instructions=(),
                passthrough_roots=("zeta", "alpha"),
            )
        except ProtectedPlanError:
            rejected = True
    assert rejected, (
        "late sort and set hooks admitted unsorted passthrough roots"
    )


def test_protected_static_passthrough_overlap_ignores_late_any_hook(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Static target bytes cannot be published from a dynamic root."""
    _, _, _, _, plan = _protected(tmp_path)
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: False)
        try:
            _ = ProtectedMetadata(
                source=plan.source,
                target=plan.target,
                instructions=plan.instructions,
                passthrough_roots=("keep.bin",),
            )
        except ProtectedPlanError:
            rejected = True
    assert rejected, "late any hook admitted static/dynamic target overlap"


@pytest.mark.parametrize(
    "invalid", ["unencodable" + chr(0xD800), "nul\x00path"]
)
def test_protected_path_metadata_rejects_unserializable_text(
    invalid: str,
) -> None:
    """Invalid path labels fail typed before UTF-8 AAD serialization."""
    digest = "0" * 64
    for data in (
        {"output_path": invalid, "source_path": "source.bin"},
        {"output_path": "target.bin", "source_path": invalid},
    ):
        with pytest.raises(ProtectedPlanError, match=r"protected.*path"):
            _ = ProtectedInstruction(
                output_path=data["output_path"],
                kind=ProtectedInstructionKind.COPY_SOURCE,
                expected_sha256=digest,
                source_path=data["source_path"],
            )
    empty = TreeSnapshot(files=())
    with pytest.raises(ProtectedPlanError, match=r"protected.*root"):
        _ = ProtectedMetadata(
            source=empty,
            target=empty,
            instructions=(),
            passthrough_roots=(invalid,),
        )


@pytest.mark.parametrize(
    "invalid",
    [
        "../escape.bin",
        "/absolute.bin",
        "nested/../escape.bin",
        "nested//data.bin",
        "./relative.bin",
        "nested\\windows.bin",
        "C:/windows.bin",
        "C:drive-relative.bin",
        "CON",
        "src/COM1/child.bin",
        "src/trailing.",
        "src/stream:fork",
    ],
)
def test_protected_paths_are_canonical_before_serialization(
    invalid: str,
) -> None:
    """Distributable protected paths must already be portable and relative."""
    digest = "0" * 64
    for output, source in ((invalid, "source.bin"), ("target.bin", invalid)):
        with pytest.raises(ProtectedPlanError, match="canonical relative"):
            _ = ProtectedInstruction(
                output_path=output,
                kind=ProtectedInstructionKind.COPY_SOURCE,
                expected_sha256=digest,
                source_path=source,
            )
    with pytest.raises(ProtectedPlanError, match="canonical relative"):
        _ = ProtectedMetadata(
            source=TreeSnapshot(files=()),
            target=TreeSnapshot(files=()),
            instructions=(),
            passthrough_roots=(invalid,),
        )


def _forge_protected_path_method(
    patched: pytest.MonkeyPatch, method: str, invalid: str
) -> None:
    def forged_parts(_path: PurePosixPath) -> tuple[str, ...]:
        del _path
        return ()

    def forged_as_posix(_path: PurePosixPath) -> str:
        del _path
        return invalid

    def forged_absolute(_path: PurePosixPath) -> bool:
        del _path
        return False

    hooks = {
        _PATH_PARTS: property(forged_parts),
        _PATH_AS_POSIX: forged_as_posix,
        "is_absolute": forged_absolute,
    }
    patched.setattr(PurePosixPath, method, hooks[method])


@pytest.mark.parametrize(
    ("method", "invalid"),
    [
        ("is_absolute", "/outside.bin"),
        ("parts", "nested/../outside.bin"),
        ("as_posix", "nested//outside.bin"),
    ],
)
def test_protected_paths_ignore_replaced_pathlib_class_methods(
    monkeypatch: pytest.MonkeyPatch, method: str, invalid: str
) -> None:
    """Mutable native path methods cannot authorize unsafe metadata labels."""
    with monkeypatch.context() as patched:
        _forge_protected_path_method(patched, method, invalid)
        with pytest.raises(ProtectedPlanError, match="canonical relative"):
            _ = ProtectedInstruction(
                output_path=invalid,
                kind=ProtectedInstructionKind.COPY_SOURCE,
                expected_sha256="0" * 64,
                source_path="safe.bin",
            )
        with pytest.raises(ProtectedPlanError, match="canonical relative"):
            _ = ProtectedMetadata(
                source=TreeSnapshot(files=()),
                target=TreeSnapshot(files=()),
                instructions=(),
                passthrough_roots=(invalid,),
            )


@pytest.mark.parametrize(
    "reserved_path", ["CON", "src/COM1/child.bin", "src/trailing."]
)
def test_protected_path_policy_ignores_mutable_host_reserved_hook(
    monkeypatch: pytest.MonkeyPatch,
    reserved_path: str,
) -> None:
    """Runtime domain changes cannot reclassify authenticated path labels."""

    def forged_isreserved(path: str) -> bool:
        del path
        return False

    monkeypatch.setattr(ntpath, "isreserved", forged_isreserved)
    with pytest.raises(ProtectedPlanError, match="canonical relative"):
        _ = ProtectedInstruction(
            output_path=reserved_path,
            kind=ProtectedInstructionKind.COPY_SOURCE,
            expected_sha256="0" * 64,
            source_path="src.bin",
        )
    with pytest.raises(ProtectedPlanError, match="canonical relative"):
        _ = ProtectedMetadata(
            source=TreeSnapshot(files=()),
            target=TreeSnapshot(files=()),
            instructions=(),
            passthrough_roots=(reserved_path,),
        )


@pytest.mark.parametrize(
    "roots",
    [
        ("data", "data"),
        ("zeta", "alpha"),
        ("data", "data/archive"),
    ],
)
def test_protected_passthrough_roots_reject_duplicates_or_overlaps(
    roots: tuple[str, ...],
) -> None:
    """Ambiguous passthrough root sets must fail before AAD generation."""
    with pytest.raises(ProtectedPlanError, match="passthrough roots"):
        _ = ProtectedMetadata(
            source=TreeSnapshot(files=()),
            target=TreeSnapshot(files=()),
            instructions=(),
            passthrough_roots=roots,
        )


def test_protected_metadata_rejects_static_target_in_passthrough(
    tmp_path: Path,
) -> None:
    """Authenticated static output must not also be a dynamic source copy."""
    _, _, _, _, protected = _protected(tmp_path)
    passthrough = ("keep.bin",)
    with pytest.raises(ProtectedPlanError, match=r"static target.*passthrough"):
        _ = ProtectedMetadata(
            source=protected.source,
            target=protected.target,
            instructions=protected.instructions,
            passthrough_roots=passthrough,
        )
    with pytest.raises(ProtectedPlanError, match=r"static target.*passthrough"):
        _ = replace(protected, passthrough_roots=passthrough)


def test_protected_metadata_rejects_duplicate_output_instructions(
    tmp_path: Path,
) -> None:
    """Invalid output topology must fail before encryption or recovery."""
    _, _, _, _, protected = _protected(tmp_path)
    duplicate = (protected.instructions[0], protected.instructions[0])

    with pytest.raises(ProtectedPlanError, match="unique output paths"):
        _ = ProtectedMetadata(
            source=protected.source,
            target=protected.target,
            instructions=duplicate,
            passthrough_roots=protected.passthrough_roots,
        )
    with pytest.raises(ProtectedPlanError, match="unique output paths"):
        _ = replace(protected, instructions=duplicate)


@pytest.mark.parametrize(
    "mutation", [_MISSING, _REORDERED, _WRONG_DIGEST, _EXTRA]
)
def test_protected_metadata_rejects_target_instruction_mismatch(
    tmp_path: Path, mutation: str
) -> None:
    """A protected plan must keep a one-to-one ordered target file mapping."""
    _, _, _, _, protected = _protected(tmp_path)
    instructions = list(protected.instructions)
    if mutation == _MISSING:
        _ = instructions.pop()
    elif mutation == _REORDERED:
        instructions[0], instructions[1] = instructions[1], instructions[0]
    elif mutation == _WRONG_DIGEST:
        instructions[0] = replace(instructions[0], expected_sha256="0" * 64)
    else:
        instructions.append(
            replace(instructions[0], output_path="extra-target.bin")
        )
    mismatched = tuple(instructions)

    with pytest.raises(ProtectedPlanError, match="match the target snapshot"):
        _ = ProtectedMetadata(
            source=protected.source,
            target=protected.target,
            instructions=mismatched,
        )
    with pytest.raises(ProtectedPlanError, match="match the target snapshot"):
        _ = replace(protected, instructions=mismatched)


def test_protected_metadata_requires_exact_runtime_records(
    tmp_path: Path,
) -> None:
    """Reject mutable aliases and foreign records before AAD serialization."""
    _, _, _, _, protected = _protected(tmp_path)
    digest = protected.instructions[0].expected_sha256

    boolean_alias: object = True
    with pytest.raises(ProtectedPlanError, match="exact integers"):
        _ = PayloadSlice(cast("int", boolean_alias), 0)
    with pytest.raises(ProtectedPlanError, match="output path"):
        _ = ProtectedInstruction(
            output_path=cast("str", object()),
            kind=ProtectedInstructionKind.COPY_SOURCE,
            expected_sha256=digest,
            source_path="source.bin",
        )
    with pytest.raises(ProtectedPlanError, match="64 lowercase hex"):
        _ = ProtectedInstruction(
            output_path="target.bin",
            kind=ProtectedInstructionKind.COPY_SOURCE,
            expected_sha256=cast("str", object()),
            source_path="source.bin",
        )
    with pytest.raises(ProtectedPlanError, match="exact immutable records"):
        _ = ProtectedMetadata(
            source=protected.source,
            target=protected.target,
            instructions=cast(
                "tuple[ProtectedInstruction, ...]",
                cast("object", [*protected.instructions]),
            ),
        )
    with pytest.raises(ProtectedPlanError, match="exact ProtectedMetadata"):
        _ = protected_plan_aad(
            cast("ProtectedMetadata", object()),
            context=_CONTEXT,
        )
    metadata = ProtectedMetadata(
        source=protected.source,
        target=protected.target,
        instructions=protected.instructions,
        passthrough_roots=protected.passthrough_roots,
    )
    with pytest.raises(ProtectedPlanError, match="exact bytes"):
        _ = protected_plan_aad(
            metadata,
            context=cast("bytes", cast("object", bytearray(_CONTEXT))),
        )


def test_protected_plan_envelope_requires_exact_runtime_types(
    tmp_path: Path,
) -> None:
    """Reject forged plan envelope fields before recovery reads evidence."""
    source, _, source_files, _, protected = _protected(tmp_path)
    identity = _identity(source_files)

    with pytest.raises(ProtectedPlanError, match=r"context.*exact bytes"):
        _ = replace(
            protected,
            context=cast("bytes", cast("object", bytearray(_CONTEXT))),
        )
    with pytest.raises(ProtectedPlanError, match=r"nonce.*exact 12-byte"):
        _ = replace(
            protected,
            nonce=cast("bytes", cast("object", bytearray(protected.nonce))),
        )
    with pytest.raises(
        ProtectedPlanError, match=r"payload.*exact authenticated"
    ):
        _ = replace(
            protected,
            payload=cast("AuthenticatedPayload", object()),
        )
    with pytest.raises(
        ProtectedPlanError, match=r"binding.*exact ThresholdBinding"
    ):
        _ = replace(
            protected,
            binding=cast("ThresholdBinding", object()),
        )
    foreign = cast("ProtectedExactPlan", object())
    with pytest.raises(ProtectedPlanError, match="exact ProtectedExactPlan"):
        _ = recover_exact_plan(foreign, identity)
    output = tmp_path / "foreign-plan-out"
    with pytest.raises(ProtectedPlanError, match="exact ProtectedExactPlan"):
        materialize_protected_exact_plan(
            source,
            identity,
            plan=foreign,
            output_root=output,
        )
    _expect(not output.exists(), "foreign protected plan published output")


class _HostileBindingError(SourceBindingError):
    """An injected binding error must not execute diagnostic hooks."""

    @override
    def __str__(self) -> str:
        message = "foreign error formatter was called"
        raise AssertionError(message)


def test_protected_plan_does_not_format_foreign_binding_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hostile binding validator cannot run arbitrary code via error text."""
    _, _, _, _, protected = _protected(tmp_path)

    def reject_binding(_binding: ThresholdBinding) -> ThresholdBinding:
        message = "foreign binding validator"
        raise _HostileBindingError(message)

    monkeypatch.setattr(
        protected_module, "validate_threshold_binding", reject_binding
    )
    with pytest.raises(
        ProtectedPlanError, match="binding is invalid: _HostileBindingError"
    ) as caught:
        _ = replace(protected, binding=protected.binding)
    _expect(
        type(caught.value.__cause__) is _HostileBindingError,
        "foreign binding error cause was lost",
    )


def test_protected_plan_rejects_malformed_binding_metadata(
    tmp_path: Path,
) -> None:
    """Validate the complete source binding before a plan becomes emit-ready."""
    _, _, _, _, protected = _protected(tmp_path)
    malformed_count = replace(protected.binding, threshold=True)
    with pytest.raises(
        ProtectedPlanError, match=r"binding is invalid.*threshold"
    ):
        _ = replace(protected, binding=malformed_count)

    first = protected.binding.shares[0]
    malformed_share = replace(first, x=True)
    malformed_binding = replace(
        protected.binding,
        shares=(malformed_share, *protected.binding.shares[1:]),
    )
    with pytest.raises(
        ProtectedPlanError,
        match=r"binding is invalid.*coordinate",
    ):
        _ = replace(protected, binding=malformed_binding)


def test_ciphertext_or_tag_tampering_fails_before_output(
    tmp_path: Path,
) -> None:
    """Authenticate the literal stream before creating the output directory."""
    source, _, source_files, _, protected = _protected(tmp_path)
    tampered_payload = AuthenticatedPayload(
        ciphertext=(
            bytes([protected.payload.ciphertext[0] ^ 1])
            + protected.payload.ciphertext[1:]
        ),
        tag=protected.payload.tag,
    )
    tampered = replace(protected, payload=tampered_payload)
    output = tmp_path / "tampered-out"

    with pytest.raises(PayloadCryptoError, match="authentication failed"):
        materialize_protected_exact_plan(
            source,
            _identity(source_files),
            plan=tampered,
            output_root=output,
        )
    _expect(
        not output.exists(),
        "unauthenticated output directory was published",
    )


def test_metadata_tampering_is_bound_as_aead_aad(tmp_path: Path) -> None:
    """Reject changed protected instruction metadata before materialization."""
    source, _, source_files, _, protected = _protected(tmp_path)
    first = protected.instructions[0]
    changed = replace(first, source_path="move-from.bin")
    tampered = replace(
        protected,
        instructions=(changed, *protected.instructions[1:]),
    )
    output = tmp_path / "metadata-out"

    with pytest.raises(PayloadCryptoError, match="authentication failed"):
        materialize_protected_exact_plan(
            source,
            _identity(source_files),
            plan=tampered,
            output_root=output,
        )
    _expect(not output.exists(), "AAD-tampered output directory was published")


def test_exact_source_snapshot_is_checked_before_output(tmp_path: Path) -> None:
    """Keep the protected module explicitly exact-baseline rather than fuzzy."""
    source, _, source_files, _, protected = _protected(tmp_path)
    _write(source, "extra.bin", b"changed source tree")
    output = tmp_path / "wrong-exact-out"

    with pytest.raises(ProtectedPlanError, match="source snapshot"):
        materialize_protected_exact_plan(
            source,
            _identity(source_files),
            plan=protected,
            output_root=output,
        )
    _expect(not output.exists(), "wrong exact source published output")


def test_protected_passthrough_can_change_after_authoring(
    tmp_path: Path,
) -> None:
    """Authenticate passthrough policy without pinning external bytes."""
    source, oracle, source_files = _fixture(tmp_path)
    _write(source, "external/game.bin", b"authoring-data")
    _write(oracle, "external/game.bin", b"authoring-data")
    exact = build_exact_plan(
        source,
        oracle,
        passthrough_roots=("external",),
    )
    protected = protect_exact_plan(
        exact,
        _identity(source_files),
        binding_policy=_policy(),
        context=_CONTEXT,
    )
    _write(source, "external/game.bin", _PASSTHROUGH_RUNTIME_DATA)
    output = tmp_path / "passthrough-protected-out"

    materialize_protected_exact_plan(
        source,
        _identity(source_files),
        plan=protected,
        output_root=output,
    )

    _expect(
        (output / "external/game.bin").read_bytes()
        == _PASSTHROUGH_RUNTIME_DATA,
        "protected passthrough pinned external bytes",
    )


def test_payload_slice_rejects_late_type_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign fractional payload offset cannot pass native int admission."""
    foreign = 1.5
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return int if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = PayloadSlice(cast("int", cast("object", foreign)), 1)
        except ProtectedPlanError:
            rejected = True
    assert rejected, "late type hook admitted a fractional payload offset"


def test_protected_context_rejects_late_type_spoof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Mutable context cannot bypass AAD exact-bytes admission."""
    _, _, _, _, plan = _protected(tmp_path)
    metadata = ProtectedMetadata(
        source=plan.source,
        target=plan.target,
        instructions=plan.instructions,
        passthrough_roots=plan.passthrough_roots,
    )
    foreign = bytearray(_CONTEXT)
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return bytes if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = protected_plan_aad(
                metadata, context=cast("bytes", cast("object", foreign))
            )
        except ProtectedPlanError:
            rejected = True
    assert rejected, "late type hook admitted mutable AAD context"


def test_protected_aad_ignores_late_len_framing_spoof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """External length hooks cannot rewrite authenticated frame lengths."""
    _, _, _, _, plan = _protected(tmp_path)
    metadata = ProtectedMetadata(
        source=plan.source,
        target=plan.target,
        instructions=plan.instructions,
        passthrough_roots=plan.passthrough_roots,
    )
    baseline = protected_plan_aad(metadata, context=_CONTEXT)
    native_len = len

    def forged_len(value: object) -> int:
        if value is _CONTEXT:
            return native_len(_CONTEXT) + 1
        return native_len(cast("bytes", value))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", forged_len)
        observed = protected_plan_aad(metadata, context=_CONTEXT)
    assert observed == baseline, "late len hook rewrote authenticated AAD"


def test_payload_slice_ignores_late_len_extent_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An out-of-range authenticated payload slice must fail closed."""
    plaintext = b"ABC"
    reference = PayloadSlice(2, 2)
    native_len = len
    rejected = False

    def forged_len(value: object) -> int:
        if value is plaintext:
            return 100
        return native_len(cast("bytes", value))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", forged_len)
        try:
            # This internal extent guard is unreachable via tampered AAD.
            internal_name = "_payload_slice"
            read_slice = cast(
                "Callable[[bytes, PayloadSlice], bytes]",
                getattr(protected_module, internal_name),
            )
            _ = read_slice(plaintext, reference)
        except ProtectedPlanError:
            rejected = True
    assert rejected, "late len hook allowed truncated payload slice"


def test_protected_authoring_ignores_late_payload_buffer_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced bytearray collector cannot erase authenticated literals."""
    _, _, source_files, exact, baseline = _protected(tmp_path)
    identity = _identity(source_files)

    class _DiscardingBytearray(bytearray):
        """A hostile accumulator that silently drops appended literals."""

        @override
        def extend(self, content: Iterable[SupportsIndex]) -> None:
            del content

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytearray", _DiscardingBytearray)
        observed = protect_exact_plan(
            exact,
            identity,
            binding_policy=_policy(),
            context=_CONTEXT,
        )
    assert observed.payload == baseline.payload
    assert observed.binding == baseline.binding


def test_protected_aad_ignores_late_isinstance_segment_spoof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A late builtin hook cannot relabel payload segments as source spans."""
    _, _, _, _, plan = _protected(tmp_path)
    metadata = ProtectedMetadata(
        source=plan.source,
        target=plan.target,
        instructions=plan.instructions,
        passthrough_roots=plan.passthrough_roots,
    )
    assert any(
        type(segment) is PayloadSlice
        for instruction in plan.instructions
        for segment in instruction.segments
    )
    baseline = protected_plan_aad(metadata, context=_CONTEXT)
    native_isinstance = isinstance

    def forged_isinstance(value: object, classinfo: type[object]) -> bool:
        if native_isinstance(value, PayloadSlice) and classinfo is SourceSlice:
            return True
        return native_isinstance(value, classinfo)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "isinstance", forged_isinstance)
        observed = protected_plan_aad(metadata, context=_CONTEXT)
    assert observed == baseline, (
        "late isinstance hook altered authenticated tags"
    )


@pytest.mark.parametrize("role", ["output", "source", "passthrough"])
@pytest.mark.parametrize(
    "unsafe", ["C:relative", "CON", "src/COM2", "src/trailing."]
)
def test_protected_path_rejects_late_ntpath_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    unsafe: str,
) -> None:
    """Protected path admission ignores late dependency hooks in ntpath."""

    def hide_windows_path(value: object) -> tuple[str, str, str]:
        del value
        return "", "", "safe"

    def checked_record() -> object:
        if role == "passthrough":
            empty = TreeSnapshot(files=())
            return ProtectedMetadata(empty, empty, (), (unsafe,))
        return ProtectedInstruction(
            output_path=unsafe if role == "output" else "target.bin",
            kind=ProtectedInstructionKind.COPY_SOURCE,
            expected_sha256="0" * 64,
            source_path=unsafe if role == "source" else "source.bin",
        )

    with monkeypatch.context() as patch:
        patch.setattr(ntpath, "splitroot", hide_windows_path)
        with pytest.raises(ProtectedPlanError, match="canonical relative"):
            _ = checked_record()


@pytest.mark.parametrize("hook", ["fspath", "any"])
def test_protected_reserved_device_ignores_late_host_hook(
    monkeypatch: pytest.MonkeyPatch,
    hook: str,
) -> None:
    """A late filesystem or builtin hook cannot make CON a portable path."""
    with monkeypatch.context() as patch:
        if hook == "fspath":
            patch.setattr(os, "fspath", lambda value: "safe")
        else:
            patch.setattr(builtins, "any", lambda values: False)
        with pytest.raises(ProtectedPlanError, match="canonical relative"):
            _ = ProtectedInstruction(
                output_path="CON",
                kind=ProtectedInstructionKind.COPY_SOURCE,
                expected_sha256="0" * 64,
                source_path="source.bin",
            )


def test_protected_plan_constructor_ignores_late_context_getter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An envelope with an empty stored context must never be admitted."""
    _, _, _, _, protected = _protected(tmp_path)
    plan_type = protected_module.ProtectedExactPlan
    original_getattribute = plan_type.__getattribute__
    calls = 0

    def forged_context(value: ProtectedExactPlan, name: str) -> object:
        nonlocal calls
        if name == "context":
            calls += 1
            return _CONTEXT
        return cast("object", original_getattribute(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(plan_type, "__getattribute__", forged_context)
        with pytest.raises(ProtectedPlanError, match="non-empty exact bytes"):
            _ = plan_type(
                source=protected.source,
                target=protected.target,
                instructions=protected.instructions,
                passthrough_roots=protected.passthrough_roots,
                context=b"",
                nonce=protected.nonce,
                payload=protected.payload,
                binding=protected.binding,
            )
    assert calls == 0, "late getter concealed an invalid plan context"


def test_recover_exact_plan_ignores_late_context_getter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged plan getter cannot change authenticated metadata at recovery."""
    _, _, source_files, expected, protected = _protected(tmp_path)
    plan_type = protected_module.ProtectedExactPlan
    original_getattribute = plan_type.__getattribute__
    calls = 0

    def forged_context(value: ProtectedExactPlan, name: str) -> object:
        nonlocal calls
        if name == "context":
            calls += 1
            return b"untrusted-context"
        return cast("object", original_getattribute(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(plan_type, "__getattribute__", forged_context)
        recovered = recover_exact_plan(protected, _identity(source_files))
    assert recovered == expected
    assert calls == 0, "late getter changed the authenticated plan context"


@pytest.mark.parametrize(
    "field",
    [
        "source",
        "target",
        "instructions",
        "passthrough_roots",
        "context",
        "nonce",
        "payload",
        "binding",
    ],
)
def test_recovery_ignores_late_envelope_field_forgery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Recover the originally signed envelope, not a later class getter."""
    _, _, source_files, expected, protected = _protected(tmp_path)
    plan_type = protected_module.ProtectedExactPlan
    original_getattribute = plan_type.__getattribute__
    forged: object = object()
    calls = 0

    def forged_attribute(value: ProtectedExactPlan, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", original_getattribute(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(plan_type, "__getattribute__", forged_attribute)
        recovered = recover_exact_plan(protected, _identity(source_files))
    assert recovered == expected
    assert calls == 0, "late envelope getter influenced recovery"


def test_materialization_ignores_late_envelope_source_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pre-publication snapshot check must use stored source identity."""
    source, oracle, source_files, _, protected = _protected(tmp_path)
    expected = snapshot_tree(oracle)
    output = tmp_path / "late-source-descriptor-out"
    plan_type = protected_module.ProtectedExactPlan
    calls = 0

    def forged_source(_value: ProtectedExactPlan) -> object:
        nonlocal calls
        calls += 1
        return object()

    with monkeypatch.context() as patched:
        patched.setattr(plan_type, "source", property(forged_source))
        materialize_protected_exact_plan(
            source, _identity(source_files), plan=protected, output_root=output
        )
    assert snapshot_tree(output) == expected
    assert calls == 0, "late source descriptor influenced output admission"


def test_payload_slice_constructor_ignores_late_coordinate_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late class getter cannot conceal negative stored slice bounds."""
    original_getattribute = PayloadSlice.__getattribute__
    calls = 0

    def forged_offset(value: PayloadSlice, name: str) -> object:
        nonlocal calls
        if name == "offset":
            calls += 1
            return 0
        return cast("object", original_getattribute(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(PayloadSlice, "__getattribute__", forged_offset)
        with pytest.raises(ProtectedPlanError, match="non-negative"):
            _ = PayloadSlice(offset=-1, length=2)
    assert calls == 0, "late slice getter concealed negative storage"


def test_payload_slice_reads_original_coordinates_after_late_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decoded literal ranges must match authenticated stored coordinates."""
    reference = PayloadSlice(offset=2, length=3)
    original_getattribute = PayloadSlice.__getattribute__
    calls = 0

    def forged_offset(value: PayloadSlice, name: str) -> object:
        nonlocal calls
        if name == "offset":
            calls += 1
            return 0
        return cast("object", original_getattribute(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(PayloadSlice, "__getattribute__", forged_offset)
        recovered = protected_module._payload_slice(b"abcdef", reference)
    assert recovered == b"cde"
    assert calls == 0, "late slice getter redirected literal range"


def test_protected_recovery_ignores_late_payload_slice_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Serialized AAD and recovered literals use identical slice coordinates."""
    _, _, source_files, expected, protected = _protected(tmp_path)
    calls = 0

    def forged_offset(_value: PayloadSlice) -> int:
        nonlocal calls
        calls += 1
        return 0

    with monkeypatch.context() as patched:
        patched.setattr(PayloadSlice, "offset", property(forged_offset))
        recovered = recover_exact_plan(protected, _identity(source_files))
    assert recovered == expected
    assert calls == 0, "late slice descriptor changed authenticated AAD"
