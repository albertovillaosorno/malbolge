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
import os
import subprocess
import sys
from collections.abc import Iterable, Sized
from dataclasses import replace
from types import MemberDescriptorType
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


def test_authenticated_payload_rejects_late_type_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late type hook cannot admit mutable authenticated ciphertext."""
    foreign = bytearray(b"x")
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return bytes if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = AuthenticatedPayload(
                cast("bytes", cast("object", foreign)), bytes(16)
            )
        except PayloadCryptoError:
            rejected = True
    assert rejected, "late type hook admitted mutable ciphertext"


def test_decrypt_rejects_late_type_foreign_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lookalike payload cannot borrow the authority of a verified record."""
    key = bytes(32)
    nonce = bytes(12)
    authentic = chacha20_poly1305_encrypt(key, nonce, b"payload")

    class ForeignPayload:
        ciphertext: bytes = authentic.ciphertext
        tag: bytes = authentic.tag

    foreign = ForeignPayload()
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return AuthenticatedPayload if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = chacha20_poly1305_decrypt(
                key,
                nonce,
                cast("AuthenticatedPayload", cast("object", foreign)),
            )
        except PayloadCryptoError:
            rejected = True
    assert rejected, "late type hook admitted foreign authenticated payload"


@pytest.mark.parametrize(
    ("ciphertext", "tag", "message"),
    [
        (b"payload", b"short", "tag must be 16 bytes"),
        (bytearray(b"payload"), bytes(16), "ciphertext must use exact bytes"),
        (b"payload", bytearray(16), "tag must use exact bytes"),
    ],
)
def test_payload_constructor_ignores_replaced_validator(
    monkeypatch: pytest.MonkeyPatch,
    ciphertext: bytes,
    tag: bytes,
    message: str,
) -> None:
    """A late class validator cannot admit malformed authenticated metadata."""
    calls = 0

    def skip_validation(_payload: AuthenticatedPayload) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patch:
        patch.setattr(AuthenticatedPayload, "__post_init__", skip_validation)
        with pytest.raises(PayloadCryptoError, match=message):
            _ = AuthenticatedPayload(ciphertext, tag)
    assert calls == 0, "replaced class validator bypassed authenticated metadata"


def test_payload_constructor_preserves_valid_metadata_after_validator_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late class validator cannot reject otherwise valid detached payloads."""
    calls = 0

    def reject_every_payload(_payload: AuthenticatedPayload) -> None:
        nonlocal calls
        calls += 1
        raise PayloadCryptoError("forged rejection")

    with monkeypatch.context() as patch:
        patch.setattr(AuthenticatedPayload, "__post_init__", reject_every_payload)
        payload = AuthenticatedPayload(_RFC_CIPHERTEXT, _RFC_TAG)
    assert payload.ciphertext == _RFC_CIPHERTEXT
    assert payload.tag == _RFC_TAG
    assert calls == 0, "replaced class validator rejected genuine metadata"


def test_payload_constructor_ignores_late_field_getattribute_forgery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late class hook cannot hide a malformed detached tag at creation."""
    original_getattribute = AuthenticatedPayload.__getattribute__
    calls = 0

    def forged_tag(value: AuthenticatedPayload, name: str) -> object:
        nonlocal calls
        if name == "tag":
            calls += 1
            return bytes(16)
        return cast("object", original_getattribute(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(AuthenticatedPayload, "__getattribute__", forged_tag)
        with pytest.raises(PayloadCryptoError, match="tag must be 16 bytes"):
            _ = AuthenticatedPayload(b"payload", b"short")
    assert calls == 0, "late class hook concealed a malformed raw tag"


def test_decrypt_ignores_late_ciphertext_read_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authentication and plaintext release must use the same raw bytes."""
    key = bytes(range(32))
    nonce = bytes(range(12))
    plaintext = b"authenticated secret"
    payload = chacha20_poly1305_encrypt(key, nonce, plaintext)
    original_getattribute = AuthenticatedPayload.__getattribute__
    calls = 0

    def switch_ciphertext(value: AuthenticatedPayload, name: str) -> object:
        nonlocal calls
        if name == "ciphertext":
            calls += 1
            if calls >= 3:
                raw = cast("bytes", original_getattribute(value, name))
                return b"x" * len(raw)
        return cast("object", original_getattribute(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(
            AuthenticatedPayload, "__getattribute__", switch_ciphertext
        )
        recovered = chacha20_poly1305_decrypt(key, nonce, payload)
    assert recovered == plaintext, "decrypted bytes differed from authenticated"
    assert calls == 0, "late class hook changed authenticated bytes"


@pytest.mark.parametrize("field", ["ciphertext", "tag"])
def test_decrypt_ignores_late_payload_descriptor_forgery(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Only raw detached payload fields can carry crypto authority."""
    key = bytes(range(32))
    nonce = bytes(range(12))
    plaintext = b"safe payload"
    authentic = chacha20_poly1305_encrypt(key, nonce, plaintext)
    invalid = AuthenticatedPayload(authentic.ciphertext, bytes(16))
    forged_value = (
        b"x" * len(authentic.ciphertext)
        if field == "ciphertext"
        else authentic.tag
    )
    calls = 0

    def forged_field(_value: AuthenticatedPayload) -> bytes:
        nonlocal calls
        calls += 1
        return forged_value

    with monkeypatch.context() as patched:
        patched.setattr(AuthenticatedPayload, field, property(forged_field))
        if field == "tag":
            with pytest.raises(
                PayloadCryptoError, match="authentication failed"
            ):
                _ = chacha20_poly1305_decrypt(key, nonce, invalid)
        else:
            recovered = chacha20_poly1305_decrypt(key, nonce, authentic)
            assert recovered == plaintext
    assert calls == 0, "late descriptor changed authenticated payload metadata"


@pytest.mark.parametrize("field", ["ciphertext", "tag"])
def test_payload_constructor_rejects_forged_field_setter(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A late setter must not repair invalid ciphertext or tag metadata."""
    slot = AuthenticatedPayload.__dict__[field]
    calls = 0

    def sanitize(self: AuthenticatedPayload, _value: object) -> None:
        nonlocal calls
        calls += 1
        slot.__set__(self, b"safe" if field == "ciphertext" else bytes(16))

    with monkeypatch.context() as patched:
        patched.setattr(AuthenticatedPayload, field, property(fset=sanitize))
        with pytest.raises(PayloadCryptoError):
            _ = AuthenticatedPayload(
                cast("bytes", cast("object", bytearray(b"unsafe")))
                if field == "ciphertext"
                else b"payload",
                b"short" if field == "tag" else bytes(16),
            )
    assert calls == 0, "invalid payload was laundered by late field setter"


@pytest.mark.parametrize("field", ["ciphertext", "tag"])
def test_payload_constructor_writes_original_fields(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Valid authenticated metadata bypasses substituted class setters."""
    calls = 0

    def forbidden_setter(_self: AuthenticatedPayload, _value: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("constructor invoked foreign payload setter")

    with monkeypatch.context() as patched:
        patched.setattr(
            AuthenticatedPayload, field, property(fset=forbidden_setter)
        )
        payload = AuthenticatedPayload(b"payload", bytes(16))
    assert type(payload) is AuthenticatedPayload
    assert calls == 0, "valid payload dispatched late field setter"


@pytest.mark.parametrize("field", ["ciphertext", "tag"])
def test_encrypt_ignores_late_payload_initializer(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Late class initializers cannot replace computed AEAD output bytes."""
    expected = chacha20_poly1305_encrypt(_RFC_KEY, _RFC_NONCE, b"source-bound")
    native_init = AuthenticatedPayload.__init__
    slot = cast("MemberDescriptorType", AuthenticatedPayload.__dict__[field])
    calls = 0

    def forged_init(
        self: AuthenticatedPayload, ciphertext: bytes, tag: bytes
    ) -> None:
        nonlocal calls
        calls += 1
        native_init(self, ciphertext, tag)
        slot.__set__(
            self,
            bytes(len(ciphertext)) if field == "ciphertext" else bytes(16),
        )

    with monkeypatch.context() as patched:
        patched.setattr(AuthenticatedPayload, "__init__", forged_init)
        observed = chacha20_poly1305_encrypt(
            _RFC_KEY, _RFC_NONCE, b"source-bound"
        )
    assert observed == expected, "late constructor replaced authenticated output"
    assert calls == 0, "late payload initializer was consulted"


def test_encrypt_ignores_late_payload_allocator_in_isolated_process() -> None:
    """A class __new__ hook must not replace authenticated encryption output."""
    script = """
from algorithms.diff.payload import AuthenticatedPayload, chacha20_poly1305_encrypt
key = bytes(range(32))
nonce = bytes(range(12))
expected = chacha20_poly1305_encrypt(key, nonce, b"verified literal")
def forbidden_new(cls, *args, **kwargs):
    raise AssertionError("late payload __new__ was consulted")
AuthenticatedPayload.__new__ = staticmethod(forbidden_new)
observed = chacha20_poly1305_encrypt(key, nonce, b"verified literal")
assert observed == expected
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
