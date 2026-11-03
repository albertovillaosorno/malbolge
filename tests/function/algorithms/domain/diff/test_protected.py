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

import hashlib
import ntpath
import shutil
from dataclasses import replace
from typing import TYPE_CHECKING, cast, override

import pytest
from algorithms.diff import protected as protected_module
from algorithms.diff.admission import identity_tree
from algorithms.diff.exact import build_exact_plan, snapshot_tree
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.model import OracleLiteral, TreeSnapshot
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
from algorithms.diff.source_binding import SourceBindingError, SourceBindingPolicy

if TYPE_CHECKING:
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
) -> tuple[Path, Path, dict[str, bytes], ExactAuthoringPlan, ProtectedExactPlan]:
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
    with pytest.raises(ProtectedPlanError, match=r"authoring context.*exact bytes"):
        _ = protect_exact_plan(
            exact,
            identity,
            binding_policy=policy,
            context=cast("bytes", cast("object", bytearray(_CONTEXT))),
        )


@pytest.mark.parametrize("invalid", ["unencodable" + chr(0xD800), "nul\x00path"])
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


@pytest.mark.parametrize("mutation", [_MISSING, _REORDERED, _WRONG_DIGEST, _EXTRA])
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
        instructions.append(replace(instructions[0], output_path="extra-target.bin"))
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
    with pytest.raises(ProtectedPlanError, match=r"payload.*exact authenticated"):
        _ = replace(
            protected,
            payload=cast("AuthenticatedPayload", object()),
        )
    with pytest.raises(ProtectedPlanError, match=r"binding.*exact ThresholdBinding"):
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

    monkeypatch.setattr(protected_module, "validate_threshold_binding", reject_binding)
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
    with pytest.raises(ProtectedPlanError, match=r"binding is invalid.*threshold"):
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
        (output / "external/game.bin").read_bytes() == _PASSTHROUGH_RUNTIME_DATA,
        "protected passthrough pinned external bytes",
    )
