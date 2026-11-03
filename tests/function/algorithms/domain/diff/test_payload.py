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
#   - RFC and synthetic tests for authenticated literal payload primitives.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""RFC and synthetic tests for authenticated literal payload primitives."""

import builtins
import hmac
from collections.abc import Iterable, Sized
from dataclasses import replace
from typing import cast, override

import pytest
from algorithms.diff.payload import (
    AuthenticatedPayload,
    PayloadCryptoError,
    chacha20_poly1305_decrypt,
    chacha20_poly1305_encrypt,
)

_RFC_KEY = bytes.fromhex(
    "808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f"
)
_RFC_NONCE = bytes.fromhex("070000004041424344454647")
_RFC_AAD = bytes.fromhex("50515253c0c1c2c3c4c5c6c7")
_RFC_PLAINTEXT_PREFIX = (
    b"Ladies and Gentlemen of the class of '99: If I could offer you only one "
)
_RFC_PLAINTEXT = _RFC_PLAINTEXT_PREFIX + (b"tip for the future, sunscreen would be it.")
_RFC_CIPHERTEXT_HEX = (
    "d31a8d34648e60db7b86afbc53ef7ec2",
    "a4aded51296e08fea9e2b5a736ee62d6",
    "3dbea45e8ca9671282fafb69da92728b",
    "1a71de0a9e060b2905d6a5b67ecd3b36",
    "92ddbd7f2d778b8c9803aee328091b58",
    "fab324e4fad675945585808b4831d7bc",
    "3ff4def08e4b7a9de576d26586cec64b",
    "6116",
)
_RFC_CIPHERTEXT = bytes.fromhex("".join(_RFC_CIPHERTEXT_HEX))
_RFC_TAG = bytes.fromhex("1ae10b594f09e26a7e902ecbd0600691")


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_rfc8439_aead_vector() -> None:
    """Match the RFC 8439 Section 2.8.2 AEAD vector exactly."""
    payload = chacha20_poly1305_encrypt(
        _RFC_KEY,
        _RFC_NONCE,
        _RFC_PLAINTEXT,
        aad=_RFC_AAD,
    )

    _expect(payload.ciphertext == _RFC_CIPHERTEXT, "RFC ciphertext changed")
    _expect(payload.tag == _RFC_TAG, "RFC Poly1305 tag changed")
    _expect(
        chacha20_poly1305_decrypt(
            _RFC_KEY,
            _RFC_NONCE,
            payload,
            aad=_RFC_AAD,
        )
        == _RFC_PLAINTEXT,
        "RFC vector failed to decrypt",
    )


def test_empty_and_multiblock_payloads_round_trip() -> None:
    """Round-trip empty and non-block-aligned authenticated payloads."""
    key = bytes(range(32))
    nonce = bytes(range(12))
    for plaintext in (b"", b"x", bytes(range(251)) * 3):
        payload = chacha20_poly1305_encrypt(key, nonce, plaintext, aad=b"aad")
        recovered = chacha20_poly1305_decrypt(key, nonce, payload, aad=b"aad")
        _expect(recovered == plaintext, "authenticated payload round-trip changed")


def test_ciphertext_tampering_fails_before_plaintext_release() -> None:
    """Reject modified ciphertext before returning any unauthenticated bytes."""
    key = bytes(range(32))
    nonce = bytes(range(12))
    payload = chacha20_poly1305_encrypt(key, nonce, b"secret", aad=b"context")
    tampered = replace(
        payload,
        ciphertext=bytes([payload.ciphertext[0] ^ 1]) + payload.ciphertext[1:],
    )

    with pytest.raises(PayloadCryptoError, match="authentication failed"):
        _ = chacha20_poly1305_decrypt(key, nonce, tampered, aad=b"context")


def test_authentication_ignores_replaced_process_global_comparator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A domain hook cannot turn a forged tag into authenticated plaintext."""
    key = bytes(range(32))
    nonce = bytes(range(12))
    payload = chacha20_poly1305_encrypt(key, nonce, b"not-for-release")
    tampered = replace(
        payload,
        tag=bytes([payload.tag[0] ^ 1]) + payload.tag[1:],
    )
    calls = 0

    def approve_any_tag(_expected: bytes, _received: bytes) -> bool:
        nonlocal calls
        calls += 1
        return True

    monkeypatch.setattr(hmac, "compare_digest", approve_any_tag)
    with pytest.raises(PayloadCryptoError, match="authentication failed"):
        _ = chacha20_poly1305_decrypt(key, nonce, tampered)
    _expect(calls == 0, "mutable process-global comparison was consulted")


def test_authentication_preserves_valid_tag_after_global_comparator_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced module function cannot reject a genuine RFC-vector tag."""
    payload = AuthenticatedPayload(_RFC_CIPHERTEXT, _RFC_TAG)
    calls = 0

    def reject_any_tag(_expected: bytes, _received: bytes) -> bool:
        nonlocal calls
        calls += 1
        return False

    monkeypatch.setattr(hmac, "compare_digest", reject_any_tag)
    recovered = chacha20_poly1305_decrypt(_RFC_KEY, _RFC_NONCE, payload, aad=_RFC_AAD)
    _expect(recovered == _RFC_PLAINTEXT, "valid RFC payload was rejected")
    _expect(calls == 0, "mutable process-global comparison was consulted")


def test_encrypt_does_not_consult_late_zip_for_stream_xor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A consumer hook cannot emit authenticated plaintext as ciphertext."""
    native_zip = zip
    calls = 0

    def forge_stream_pairs(
        left: Iterable[int], right: Iterable[int], *, strict: bool = False
    ) -> Iterable[tuple[int, int]]:
        nonlocal calls
        calls += 1
        if type(left) is bytes:
            return ((value, 0) for value in left)
        return native_zip(left, right, strict=strict)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "zip", forge_stream_pairs)
        payload = chacha20_poly1305_encrypt(
            _RFC_KEY, _RFC_NONCE, _RFC_PLAINTEXT, aad=_RFC_AAD
        )

    _expect(payload.ciphertext == _RFC_CIPHERTEXT, "stream XOR was replaced")
    _expect(payload.tag == _RFC_TAG, "forged stream altered authentication")
    _expect(calls == 0, "mutable process-global zip was consulted")


def test_encrypt_ignores_late_chacha_state_list_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced list must not silently suppress ChaCha20 rounds."""
    native_list = list
    calls = 0

    class SilentState(native_list[int]):
        @override
        def __setitem__(self, key: object, value: object) -> None:
            del key, value

    def replace_state(values: Iterable[int]) -> SilentState:
        nonlocal calls
        calls += 1
        return SilentState(values)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "list", replace_state)
        payload = chacha20_poly1305_encrypt(
            _RFC_KEY, _RFC_NONCE, _RFC_PLAINTEXT, aad=_RFC_AAD
        )

    _expect(payload.ciphertext == _RFC_CIPHERTEXT, "ChaCha state was replaced")
    _expect(calls == 0, "mutable process-global list was consulted")


def test_encrypt_ignores_late_chacha_word_tuple_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Word decoding cannot be reordered by a late tuple replacement."""
    native_tuple = tuple
    calls = 0

    def reorder_words(values: Iterable[int]) -> tuple[int, ...]:
        nonlocal calls
        calls += 1
        return native_tuple(reversed(native_tuple(values)))

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", reorder_words)
        payload = chacha20_poly1305_encrypt(
            _RFC_KEY, _RFC_NONCE, _RFC_PLAINTEXT, aad=_RFC_AAD
        )

    matches_rfc = payload.ciphertext == _RFC_CIPHERTEXT
    _expect(matches_rfc, "ChaCha words were reordered")
    _expect(calls == 0, "mutable process-global tuple was consulted")


def test_decrypt_rejects_forgery_after_late_mac_range_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced range cannot skip the authenticated Poly1305 message."""
    native_range = range
    calls = 0

    def omit_mac_blocks(*args: int) -> range:
        nonlocal calls
        calls += 1
        if len(args) == 3 and args[2] == 16:
            return native_range(0)
        return native_range(*args)

    key = bytes(range(32))
    nonce = bytes(range(12))
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "range", omit_mac_blocks)
        payload = chacha20_poly1305_encrypt(key, nonce, b"protected payload")
        forged = replace(payload, ciphertext=b"corrupted payload")
        try:
            _ = chacha20_poly1305_decrypt(key, nonce, forged)
        except PayloadCryptoError:
            rejected = True

    _expect(rejected, "range substitution admitted a forged ciphertext")
    _expect(calls == 0, "mutable process-global range was consulted")


def test_payload_metadata_rejects_foreign_bytes_after_namespace_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late builtins.bytes alias cannot admit mutable ciphertext or tags."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytes", bytearray)
        try:
            _ = AuthenticatedPayload(
                ciphertext=cast("bytes", cast("object", bytearray(b"x"))),
                tag=cast("bytes", cast("object", bytearray(16))),
            )
        except PayloadCryptoError:
            rejected = True

    _expect(rejected, "mutable bytes aliases admitted a foreign payload")


def test_decrypt_preserves_rfc_vector_after_bytes_namespace_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authenticated native bytes remain valid after a global type alias."""
    payload = AuthenticatedPayload(_RFC_CIPHERTEXT, _RFC_TAG)
    result: bytes | None = None
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytes", bytearray)
        try:
            result = chacha20_poly1305_decrypt(
                _RFC_KEY, _RFC_NONCE, payload, aad=_RFC_AAD
            )
        except PayloadCryptoError:
            result = None

    _expect(result == _RFC_PLAINTEXT, "native bytes were rejected by alias")


def test_payload_rejects_short_tag_after_late_len_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged length must not admit invalid authentication tags."""
    native_len = len
    calls = 0

    def approve_short_tag(value: Sized) -> int:
        nonlocal calls
        calls += 1
        if type(value) is bytes and value == b"short":
            return 16
        return native_len(value)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "len", approve_short_tag)
        try:
            _ = AuthenticatedPayload(ciphertext=b"data", tag=b"short")
        except PayloadCryptoError:
            rejected = True

    _expect(rejected, "forged length admitted short authentication tag")
    _expect(calls == 0, "mutable process-global len was consulted")


def test_encrypt_ignores_late_mutable_output_buffer_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced bytearray must not corrupt authenticated ciphertext."""
    native_bytearray = bytearray
    calls = 0

    class SilentBuffer(native_bytearray):
        @override
        def __setitem__(self, key: object, value: object) -> None:
            del key, value

    def replace_output_buffer(size: int) -> SilentBuffer:
        nonlocal calls
        calls += 1
        return SilentBuffer(size)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytearray", replace_output_buffer)
        payload = chacha20_poly1305_encrypt(
            _RFC_KEY, _RFC_NONCE, _RFC_PLAINTEXT, aad=_RFC_AAD
        )

    matches_rfc = payload.ciphertext == _RFC_CIPHERTEXT
    _expect(matches_rfc, "ciphertext buffer corrupted")
    _expect(payload.tag == _RFC_TAG, "ciphertext tag was changed")
    _expect(calls == 0, "mutable process-global bytearray was consulted")


class _ForgedInt:
    """Simulate a domain callback replacing the ambient integer namespace."""

    @staticmethod
    # jig-ignore-next-line: native int.from_bytes signature is Ruff-indivisible
    def from_bytes(data: bytes, byteorder: str = "big", *, signed: bool = False) -> int:
        """Return a zero even for nonzero inputs.

        Returns:
            A forged zero integer.

        """
        del data, byteorder, signed
        return 0


def test_decrypt_never_accepts_zero_tag_after_integer_namespace_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late builtins replacement cannot authenticate untrusted bytes."""
    key = bytes(range(32))
    nonce = bytes(range(12))
    unauthenticated = AuthenticatedPayload(b"forged ciphertext", bytes(16))
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", _ForgedInt)
        try:
            _ = chacha20_poly1305_decrypt(key, nonce, unauthenticated)
        except PayloadCryptoError:
            rejected = True

    _expect(rejected, "forged integer decoder admitted a forged payload tag")


def test_decrypt_preserves_rfc_vector_after_integer_namespace_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid authenticated ciphertext survives a late integer swap."""
    payload = AuthenticatedPayload(_RFC_CIPHERTEXT, _RFC_TAG)
    recovered: bytes | None = None
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", _ForgedInt)
        try:
            recovered = chacha20_poly1305_decrypt(
                _RFC_KEY, _RFC_NONCE, payload, aad=_RFC_AAD
            )
        except PayloadCryptoError:
            recovered = None

    _expect(recovered == _RFC_PLAINTEXT, "genuine RFC payload was rejected")


def test_tag_and_aad_tampering_fail_closed() -> None:
    """Bind both the detached tag and associated metadata to the plaintext."""
    key = bytes(reversed(range(32)))
    nonce = bytes(reversed(range(12)))
    payload = chacha20_poly1305_encrypt(key, nonce, b"payload", aad=b"metadata")
    wrong_tag = AuthenticatedPayload(
        ciphertext=payload.ciphertext,
        tag=bytes([payload.tag[0] ^ 1]) + payload.tag[1:],
    )

    with pytest.raises(PayloadCryptoError, match="authentication failed"):
        _ = chacha20_poly1305_decrypt(key, nonce, wrong_tag, aad=b"metadata")
    with pytest.raises(PayloadCryptoError, match="authentication failed"):
        _ = chacha20_poly1305_decrypt(key, nonce, payload, aad=b"different")


def test_key_nonce_and_tag_widths_fail_closed() -> None:
    """Reject malformed RFC 8439 key, nonce, and tag widths."""
    with pytest.raises(PayloadCryptoError, match="key must be 32 bytes"):
        _ = chacha20_poly1305_encrypt(b"short", bytes(12), b"")
    with pytest.raises(PayloadCryptoError, match="nonce must be 12 bytes"):
        _ = chacha20_poly1305_encrypt(bytes(32), b"short", b"")
    with pytest.raises(PayloadCryptoError, match="tag must be 16 bytes"):
        _ = AuthenticatedPayload(ciphertext=b"", tag=b"short")


def test_payload_api_rejects_non_bytes_without_crypto_work() -> None:
    """AEAD public inputs require exact bytes, not bytes-like coercions."""
    key = bytes(32)
    nonce = bytes(12)
    foreign = cast("bytes", cast("object", bytearray(b"x")))
    with pytest.raises(PayloadCryptoError, match="key must use exact bytes"):
        _ = chacha20_poly1305_encrypt(
            cast("bytes", cast("object", bytearray(key))), nonce, b"payload"
        )
    with pytest.raises(PayloadCryptoError, match="nonce must use exact bytes"):
        _ = chacha20_poly1305_encrypt(
            key, cast("bytes", cast("object", bytearray(nonce))), b"payload"
        )
    with pytest.raises(PayloadCryptoError, match="plaintext must use exact bytes"):
        _ = chacha20_poly1305_encrypt(key, nonce, cast("bytes", cast("object", "")))
    with pytest.raises(PayloadCryptoError, match="plaintext must use exact bytes"):
        _ = chacha20_poly1305_encrypt(key, nonce, foreign)
    with pytest.raises(
        PayloadCryptoError, match="associated data must use exact bytes"
    ):
        _ = chacha20_poly1305_encrypt(key, nonce, b"payload", aad=foreign)


def test_authenticated_payload_rejects_foreign_ciphertext_and_tag() -> None:
    """Detached payload metadata cannot carry mutable or foreign byte values."""
    with pytest.raises(PayloadCryptoError, match="ciphertext must use exact bytes"):
        _ = AuthenticatedPayload(
            ciphertext=cast("bytes", cast("object", bytearray(b"x"))),
            tag=bytes(16),
        )
    with pytest.raises(PayloadCryptoError, match="tag must use exact bytes"):
        _ = AuthenticatedPayload(
            ciphertext=b"x",
            tag=cast("bytes", cast("object", bytearray(16))),
        )


def test_decrypt_rejects_foreign_payload_before_field_access() -> None:
    """Decrypt validates payload and AAD types before authentication."""
    key = bytes(32)
    nonce = bytes(12)
    payload = chacha20_poly1305_encrypt(key, nonce, b"payload")
    with pytest.raises(PayloadCryptoError, match="exact authenticated type"):
        _ = chacha20_poly1305_decrypt(
            key, nonce, cast("AuthenticatedPayload", object())
        )
    with pytest.raises(
        PayloadCryptoError, match="associated data must use exact bytes"
    ):
        _ = chacha20_poly1305_decrypt(
            key,
            nonce,
            payload,
            aad=cast("bytes", cast("object", bytearray())),
        )
