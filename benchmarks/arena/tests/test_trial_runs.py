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
#   - Independent per-trial SHA-256 policy-substitution regressions.
# - Must-Not:
#   - Authenticate manifest producers or real file-content provenance.
# - Allows:
#   - Inputs: direct bounded TOML manifests and injected analyzer policy drift.
#   - Outputs: native trial records or typed malformed-digest rejection.
#   - Side effects: test-local monkeypatches only.
# - Split-When:
#   - Different parser policy needs separately governed fixtures.
# - Merge-When:
#   - The arena per-trial manifest parser owns these negative tests.
# - Summary:
#   - Mutable analyzer constants cannot redefine canonical run digests.
# - Description:
#   - Red-first short and uppercase digest policy substitutions.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_trial_runs.py`.
# - Defaults:
#   - Noncanonical SHA-256 digests fail closed.
#

"""Source-stable per-trial run digest policy regressions."""

# ruff: file-ignore[assert]

from __future__ import annotations

from typing import Never

import pytest

from benchmarks.arena import analyze, trial_runs


def _manifest(digest: str) -> str:
    return f'[arena_trial]\nschema_version = 1\ntrial = 7\nraw_sha256 = "{digest}"\n'


def test_native_manifest_digest_is_accepted_without_policy_changes() -> None:
    """A canonical digest retains its exact parsed source identity."""
    digest = "a" * 64
    assert trial_runs.parse_trial_run(_manifest(digest)) == trial_runs.TrialRun(
        trial=7, raw_sha256=digest
    )


@pytest.mark.parametrize(
    ("policy", "digest"),
    [("length", "abc"), ("alphabet", "G" * 64)],
)
def test_mutable_analyzer_policy_cannot_admit_noncanonical_run_digest(
    monkeypatch: pytest.MonkeyPatch, policy: str, digest: str
) -> None:
    """A late-bound digest policy must not weaken canonical source admission."""
    with pytest.raises(trial_runs.TrialRunError, match="lowercase SHA-256"):
        _ = trial_runs.parse_trial_run(_manifest(digest))

    with monkeypatch.context() as patch:
        if policy == "length":
            patch.setattr(analyze, "SHA256_HEX_LENGTH", len(digest))
        else:
            patch.setattr(analyze, "SHA256_ALPHABET", frozenset("0123456789abcdefG"))
        with pytest.raises(trial_runs.TrialRunError, match="lowercase SHA-256"):
            _ = trial_runs.parse_trial_run(_manifest(digest))


@pytest.mark.parametrize("policy", ["name", "fields", "version"])
def test_public_trial_schema_policy_cannot_admit_foreign_source(
    monkeypatch: pytest.MonkeyPatch,
    policy: str,
) -> None:
    """A replaced schema policy cannot redefine canonical trial identity."""
    source = _manifest("a" * 64)
    if policy == "name":
        source = source.replace("arena_trial", "alternate_trial", 1)
        monkeypatch.setattr(trial_runs, "EXTENSION_NAME", "alternate_trial")
    elif policy == "fields":
        source += "extra = 1\n"
        monkeypatch.setattr(
            trial_runs, "EXTENSION_FIELDS", trial_runs.EXTENSION_FIELDS | {"extra"}
        )
    else:
        source = source.replace("schema_version = 1", "schema_version = 2", 1)
        monkeypatch.setattr(trial_runs, "SCHEMA_VERSION", 2)
    with pytest.raises(trial_runs.TrialRunError, match="arena_trial"):
        trial_runs.parse_trial_run(source)


def test_public_trial_size_limit_cannot_admit_oversized_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An oversized manifest must fail regardless of runtime limit changes."""
    oversized = _manifest("a" * 64) + "#" + "x" * trial_runs.MAX_RUN_MANIFEST_BYTES
    monkeypatch.setattr(trial_runs, "MAX_RUN_MANIFEST_BYTES", len(oversized) + 1)
    with pytest.raises(trial_runs.TrialRunError, match="byte limit"):
        trial_runs.parse_trial_run(oversized)


@pytest.mark.parametrize("forged_field", ["trial", "raw_sha256"])
def test_source_run_identity_ignores_substituted_result_constructor(
    monkeypatch: pytest.MonkeyPatch, forged_field: str
) -> None:
    """A replacement result factory cannot forge checked trial identity."""
    original = trial_runs.TrialRun
    expected = original(trial=7, raw_sha256="a" * 64)

    def forged_constructor(*, trial: int, raw_sha256: str) -> trial_runs.TrialRun:
        return original(
            trial=trial + int(forged_field == "trial"),
            raw_sha256="b" * 64 if forged_field == "raw_sha256" else raw_sha256,
        )

    with monkeypatch.context() as patched:
        patched.setattr(trial_runs, "TrialRun", forged_constructor)
        assert trial_runs.parse_trial_run(_manifest("a" * 64)) == expected


def test_trial_source_limit_rejects_substituted_text_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced local size preflight cannot admit oversized source TOML."""
    oversized = _manifest("a" * 64) + "#" + "x" * trial_runs.MAX_RUN_MANIFEST_BYTES
    monkeypatch.setattr(trial_runs, "_admit_text", lambda _text: None)
    with pytest.raises(trial_runs.TrialRunError, match="byte limit"):
        trial_runs.parse_trial_run(oversized)


def test_trial_source_limit_rejects_suppressed_error_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An overridden error hook cannot silently ignore an oversized manifest."""
    oversized = _manifest("a" * 64) + "#" + "x" * trial_runs.MAX_RUN_MANIFEST_BYTES
    monkeypatch.setattr(trial_runs, "_fail", lambda _message: None)
    with pytest.raises(trial_runs.TrialRunError, match="byte limit"):
        trial_runs.parse_trial_run(oversized)


@pytest.mark.parametrize("noncanonical", ["abc", "G" * 64])
def test_trial_source_rejects_substituted_digest_validator(
    monkeypatch: pytest.MonkeyPatch,
    noncanonical: str,
) -> None:
    """Matching source values cannot authorize a noncanonical digest."""
    monkeypatch.setattr(trial_runs, "_digest", lambda value: value)
    with pytest.raises(trial_runs.TrialRunError, match="lowercase SHA-256"):
        trial_runs.parse_trial_run(_manifest(noncanonical))


def test_trial_limit_rejects_substituted_length_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced module length cannot shrink a source before byte admission."""
    original_len = len
    ceiling = trial_runs.MAX_RUN_MANIFEST_BYTES
    oversized = _manifest("a" * 64) + "#" + "x" * ceiling
    monkeypatch.setattr(
        trial_runs,
        "len",
        lambda value: 0 if original_len(value) > ceiling else original_len(value),
        raising=False,
    )
    with pytest.raises(trial_runs.TrialRunError, match="byte limit"):
        trial_runs.parse_trial_run(oversized)


def test_trial_digest_rejects_substituted_character_set_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced set factory cannot erase forbidden digest glyphs."""
    native_set = set
    monkeypatch.setattr(
        trial_runs,
        "set",
        lambda value: native_set() if type(value) is str else native_set(value),
        raising=False,
    )
    with pytest.raises(trial_runs.TrialRunError, match="lowercase SHA-256"):
        trial_runs.parse_trial_run(_manifest("G" * 64))


def test_trial_rejects_foreign_integer_with_forged_source_equality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A substituted decoder cannot return a foreign trial counter as native."""

    class ForgedTrial:
        def __lt__(self, _other: int) -> bool:
            return False

        def __eq__(self, other: object) -> bool:
            return other == 7

        def __ne__(self, other: object) -> bool:
            return other != 7

    forged = ForgedTrial()
    native_type = type

    def forged_type(value: object) -> type[object]:
        return int if value is forged else native_type(value)

    monkeypatch.setattr(trial_runs, "type", forged_type, raising=False)
    monkeypatch.setattr(
        trial_runs.tomllib,
        "loads",
        lambda _text: {
            "arena_trial": {
                "schema_version": 1,
                "trial": forged,
                "raw_sha256": "a" * 64,
            }
        },
    )
    with pytest.raises(trial_runs.TrialRunError, match="nonnegative integer"):
        trial_runs.parse_trial_run(_manifest("a" * 64))


def test_trial_rejects_foreign_decoder_keys_despite_substituted_any(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native source equality cannot override the decoder's key type policy."""
    invalid_key = object()
    monkeypatch.setattr(trial_runs, "any", lambda _keys: False, raising=False)
    monkeypatch.setattr(
        trial_runs.tomllib,
        "loads",
        lambda _text: {
            invalid_key: "foreign",
            "arena_trial": {
                "schema_version": 1,
                "trial": 7,
                "raw_sha256": "a" * 64,
            },
        },
    )
    with pytest.raises(trial_runs.TrialRunError, match="native string keys"):
        trial_runs.parse_trial_run(_manifest("a" * 64))


@pytest.mark.parametrize("provider", ["type", "any", "dict", "str", "int"])
def test_trial_source_bound_native_shape_providers(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    """Public aliases cannot redefine native run identity or its input text."""

    def forged_operation(*_args: object, **_kwargs: object) -> Never:
        pytest.fail(f"public {provider} called instead of source native")

    monkeypatch.setattr(trial_runs, provider, forged_operation, raising=False)
    assert trial_runs.parse_trial_run(_manifest("a" * 64)) == trial_runs.TrialRun(
        trial=7, raw_sha256="a" * 64
    )


@pytest.mark.parametrize(
    ("source", "failure"),
    [
        ("not source TOML", "invalid per-trial manifest TOML"),
        (_manifest("G" * 64), "lowercase SHA-256"),
        ("[arena_trial]\n#\ud800\ntrial = 0\n", "strict UTF-8"),
    ],
)
@pytest.mark.parametrize("replacement", [RuntimeError, object()])
def test_trial_rejection_preserves_native_error_after_public_alias_rebinding(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    failure: str,
    replacement: object,
) -> None:
    """Bad run identity remains a typed failure after error alias drift."""
    original = trial_runs.TrialRunError
    with monkeypatch.context() as patched:
        patched.setattr(trial_runs, "TrialRunError", replacement)
        with pytest.raises(original, match=failure):
            trial_runs.parse_trial_run(source)


@pytest.mark.parametrize("replacement", [RuntimeError, object()])
def test_trial_valid_source_ignores_replaced_public_error_alias(
    monkeypatch: pytest.MonkeyPatch, replacement: object
) -> None:
    """Error alias changes cannot affect successful source admission."""
    with monkeypatch.context() as patched:
        patched.setattr(trial_runs, "TrialRunError", replacement)
        assert trial_runs.parse_trial_run(_manifest("a" * 64)).trial == 7
