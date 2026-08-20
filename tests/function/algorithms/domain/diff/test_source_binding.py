# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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
#   - Synthetic tests for deterministic threshold source binding.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for deterministic threshold source binding."""

from dataclasses import replace
import hashlib
import itertools
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff.admission import identity_tree
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.source_binding import SourceBindingError
from algorithms.diff.source_binding import SourceBindingPolicy
from algorithms.diff.source_binding import SourceBindingPolicyError
from algorithms.diff.source_binding import bind_secret
from algorithms.diff.source_binding import hkdf_expand_sha256
from algorithms.diff.source_binding import hkdf_extract_sha256
from algorithms.diff.source_binding import recover_secret
import pytest

if TYPE_CHECKING:
    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.source_binding import BoundShare

_SECRET = hashlib.sha256(b"synthetic high-entropy payload key").digest()
_CONTEXT = b"synthetic-source-binding-v1"
_FILE_COUNT = 5
_BLOCKS_PER_FILE = 64
_DEFAULT_THRESHOLD = 3
_STRICT_THRESHOLD = 5


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _files(label: str) -> dict[str, bytes]:
    return {
        f"src/file-{file_index}.c": b"".join(
            hashlib.sha256(
                f"{label}:{file_index}:{block_index}".encode()
            ).digest()
            for block_index in range(_BLOCKS_PER_FILE)
        )
        for file_index in range(_FILE_COUNT)
    }


def _policy(*, threshold_fraction: float = 0.60) -> SourceBindingPolicy:
    return SourceBindingPolicy(
        threshold_fraction=threshold_fraction,
        maximum_anchors=_FILE_COUNT,
        minimum_anchor_files=3,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )


def _reference() -> IdentityTree:
    return identity_tree(_files("reference"))


def _candidate_paths(
    reference: IdentityTree, paths: tuple[str, ...]
) -> IdentityTree:
    by_path = {item.path: item.canonical for item in reference.files}
    return identity_tree({path: by_path[path] for path in paths})


def test_hkdf_sha256_matches_rfc5869_test_case_1() -> None:
    """Lock HKDF implementation to the RFC 5869 SHA-256 test vector."""
    input_key_material = bytes.fromhex("0b" * 22)
    salt = bytes.fromhex("000102030405060708090a0b0c")
    info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
    expected_prk = bytes.fromhex(
        "077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"
    )
    expected_okm_parts = (
        "3cb25f25faacd57a90434f64d0362f2a",
        "2d2d0a90cf1a5a4c5db02d56ecc4c5bf",
        "34007208d5b887185865",
    )
    expected_okm = bytes.fromhex("".join(expected_okm_parts))

    pseudorandom_key = hkdf_extract_sha256(salt, input_key_material)
    output = hkdf_expand_sha256(pseudorandom_key, info, 42)

    _expect(pseudorandom_key == expected_prk, "HKDF extract vector changed")
    _expect(output == expected_okm, "HKDF expand vector changed")


def test_full_reference_recovers_bound_secret() -> None:
    """Recover key material from the exact canonical reference source."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )

    recovered = recover_secret(binding, reference)

    _expect(recovered == _SECRET, "exact reference did not recover secret")
    _expect(
        binding.threshold == _DEFAULT_THRESHOLD, "synthetic threshold changed"
    )
    _expect(len(binding.shares) == _FILE_COUNT, "binding share count changed")


def test_every_exact_threshold_file_combination_recovers() -> None:
    """Recover from every exact-threshold combination of source files."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    paths = tuple(share.source_path for share in binding.shares)

    for selected in itertools.combinations(paths, binding.threshold):
        candidate = _candidate_paths(reference, selected)
        _expect(
            recover_secret(binding, candidate) == _SECRET,
            f"threshold combination failed: {selected!r}",
        )


def test_below_threshold_fails_before_secret_recovery() -> None:
    """Reject a candidate with one fewer bound source file than required."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    selected = tuple(
        share.source_path for share in binding.shares[: binding.threshold - 1]
    )
    candidate = _candidate_paths(reference, selected)

    with pytest.raises(
        SourceBindingError, match="insufficient source-bound anchors"
    ):
        _ = recover_secret(binding, candidate)


def test_empty_source_cannot_materialize_bound_secret() -> None:
    """Prove the distributable binding metadata is insufficient by itself."""
    binding = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )

    with pytest.raises(
        SourceBindingError, match="insufficient source-bound anchors"
    ):
        _ = recover_secret(binding, identity_tree({}))


def test_enough_shares_from_too_few_files_still_fails_closed() -> None:
    """Reject numerically sufficient shares concentrated in one source file."""
    reference = _reference()
    policy = SourceBindingPolicy(
        threshold_fraction=0.20,
        maximum_anchors=15,
        minimum_anchor_files=3,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )
    binding = bind_secret(
        reference,
        _SECRET,
        policy=policy,
        context=_CONTEXT,
    )
    concentrated_path = binding.shares[0].source_path
    candidate = _candidate_paths(reference, (concentrated_path,))

    with pytest.raises(
        SourceBindingError,
        match="insufficient distributed source-bound files",
    ):
        _ = recover_secret(binding, candidate)


def test_insertions_shift_offsets_without_breaking_bound_anchors() -> None:
    """Recover when unchanged source windows move to different byte offsets."""
    reference_files = _files("reference")
    reference = identity_tree(reference_files)
    binding = bind_secret(
        reference,
        _SECRET,
        policy=_policy(),
        context=_CONTEXT,
    )
    candidate = identity_tree({
        path: b"inserted-prefix:" + data
        for path, data in reference_files.items()
    })

    _expect(
        recover_secret(binding, candidate) == _SECRET,
        "offset-shifted stable anchors did not recover the secret",
    )


def test_unrelated_same_shape_source_cannot_recover_secret() -> None:
    """Reject unrelated canonical bytes with similar paths and sizes."""
    binding = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    unrelated = identity_tree(_files("unrelated"))

    with pytest.raises(
        SourceBindingError, match="insufficient source-bound anchors"
    ):
        _ = recover_secret(binding, unrelated)


def test_binding_is_deterministic_and_distributed() -> None:
    """Generate deterministic masked shares distributed across source files."""
    reference = _reference()
    first = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    second = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)

    _expect(first == second, "repeated source binding changed")
    selected_files = {share.source_path for share in first.shares}
    _expect(
        len(selected_files) == _FILE_COUNT,
        "binding concentrated in fewer files",
    )
    _expect(
        all(share.masked_share != _SECRET for share in first.shares),
        "binding stored plaintext secret as a share",
    )


def test_tampered_masked_share_fails_secret_commitment() -> None:
    """Reject malformed transform metadata rather than returning a wrong key."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    first = binding.shares[0]
    tampered_bytes = bytes([first.masked_share[0] ^ 1]) + first.masked_share[1:]
    tampered_share = replace(first, masked_share=tampered_bytes)
    tampered = replace(binding, shares=(tampered_share, *binding.shares[1:]))

    with pytest.raises(SourceBindingError, match="failed commitment"):
        _ = recover_secret(tampered, reference)


def test_stricter_fraction_changes_threshold_fail_closed() -> None:
    """Round the configured threshold fraction up deterministically."""
    reference = _reference()
    binding = bind_secret(
        reference,
        _SECRET,
        policy=_policy(threshold_fraction=0.81),
        context=_CONTEXT,
    )

    _expect(
        binding.threshold == _STRICT_THRESHOLD,
        "threshold fraction did not round up",
    )


def test_source_binding_policy_rejects_boolean_numeric_fields() -> None:
    """Boolean aliases cannot become thresholds, counts, or HKDF lengths."""
    with pytest.raises(SourceBindingPolicyError, match="finite value"):
        _ = SourceBindingPolicy(threshold_fraction=True)
    with pytest.raises(SourceBindingPolicyError, match="positive integer"):
        _ = SourceBindingPolicy(threshold_fraction=0.66, maximum_anchors=True)
    with pytest.raises(SourceBindingPolicyError, match="positive integer"):
        _ = SourceBindingPolicy(
            threshold_fraction=0.66,
            minimum_anchor_files=True,
        )
    with pytest.raises(SourceBindingPolicyError, match="integer within"):
        _ = hkdf_expand_sha256(b"key", b"info", length=True)


def test_public_source_binding_inputs_fail_closed() -> None:
    """Public binding and HKDF APIs reject foreign runtime input types."""
    reference = _reference()
    policy = _policy()
    with pytest.raises(SourceBindingPolicyError, match="exact IdentityTree"):
        _ = bind_secret(
            cast("IdentityTree", object()),
            _SECRET,
            policy=policy,
            context=_CONTEXT,
        )
    with pytest.raises(SourceBindingPolicyError, match="non-empty exact bytes"):
        _ = bind_secret(
            reference,
            cast("bytes", cast("object", bytearray(_SECRET))),
            policy=policy,
            context=_CONTEXT,
        )
    with pytest.raises(
        SourceBindingPolicyError, match="exact SourceBindingPolicy"
    ):
        _ = bind_secret(
            reference,
            _SECRET,
            policy=cast("SourceBindingPolicy", object()),
            context=_CONTEXT,
        )
    with pytest.raises(SourceBindingPolicyError, match="non-empty exact bytes"):
        _ = bind_secret(
            reference,
            _SECRET,
            policy=policy,
            context=cast("bytes", cast("object", bytearray(_CONTEXT))),
        )
    with pytest.raises(SourceBindingPolicyError, match="extract inputs"):
        _ = hkdf_extract_sha256(
            cast("bytes", cast("object", bytearray())), _SECRET
        )
    with pytest.raises(SourceBindingPolicyError, match="expand inputs"):
        _ = hkdf_expand_sha256(
            _SECRET, cast("bytes", cast("object", bytearray(b"info"))), 1
        )


def test_recovery_rejects_malformed_binding_before_candidate_use() -> None:
    """Distributable binding metadata is admitted before source inspection."""
    reference = _reference()
    binding = bind_secret(
        reference,
        _SECRET,
        policy=_policy(),
        context=_CONTEXT,
    )
    malformed = (
        replace(
            binding,
            context=cast("bytes", cast("object", bytearray(binding.context))),
        ),
        replace(binding, threshold=True),
        replace(binding, threshold=-1),
        replace(binding, minimum_anchor_files=True),
        replace(binding, minimum_anchor_files=-1),
        replace(binding, secret_length=True),
        replace(binding, secret_length=0),
        replace(binding, secret_commitment=b"short"),
        replace(binding, anchor_policy=cast("AnchorPolicy", object())),
        replace(
            binding,
            shares=cast(
                "tuple[BoundShare, ...]", cast("object", list(binding.shares))
            ),
        ),
        replace(binding, threshold=len(binding.shares) + 1),
        replace(binding, minimum_anchor_files=len(binding.shares) + 1),
    )
    for candidate in malformed:
        with pytest.raises(SourceBindingError, match="source"):
            _ = recover_secret(candidate, cast("IdentityTree", object()))


def test_recovery_rejects_malformed_share_metadata() -> None:
    """Every serialized share is canonical even when enough peers remain."""
    reference = _reference()
    binding = bind_secret(
        reference,
        _SECRET,
        policy=_policy(),
        context=_CONTEXT,
    )
    first = binding.shares[0]
    second = binding.shares[1]
    malformed_shares = (
        replace(first, source_path="../escape.c"),
        replace(first, anchor_digest=b"short"),
        replace(first, x=True),
        replace(first, x=0),
        replace(first, x=256),
        replace(first, masked_share=b"short"),
    )
    for share in malformed_shares:
        malformed = replace(binding, shares=(share, *binding.shares[1:]))
        with pytest.raises(SourceBindingError, match="source"):
            _ = recover_secret(malformed, reference)

    duplicate_x = replace(second, x=first.x)
    with pytest.raises(SourceBindingError, match="coordinates must be unique"):
        _ = recover_secret(
            replace(binding, shares=(first, duplicate_x, *binding.shares[2:])),
            reference,
        )
    duplicate_anchor = replace(
        second,
        source_path=first.source_path,
        anchor_digest=first.anchor_digest,
    )
    with pytest.raises(SourceBindingError, match="anchors must be unique"):
        _ = recover_secret(
            replace(
                binding, shares=(first, duplicate_anchor, *binding.shares[2:])
            ),
            reference,
        )
