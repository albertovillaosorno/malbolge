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
#   - Native unit conversion semantics for experiment-run resource budgets.
# - Must-Not:
#   - Claim enforcement of memory or time limits by the operating system.
# - Allows:
#   - Inputs: native bounded TOML budget tables and injected unit drift.
#   - Outputs: canonical nanoseconds/MiB byte budgets or typed failure.
#   - Side effects: isolated monkeypatches of conversion constants.
# - Split-When:
#   - Additional budget units require a separate protocol.
# - Merge-When:
#   - The arena budget-link parser owns this conversion policy.
# - Summary:
#   - Publicly replaceable unit constants cannot reinterpret source budgets.
# - Description:
#   - Red-first time and memory conversion substitutions with a valid source.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_budget_links.py`.
# - Defaults:
#   - Whole seconds and MiB convert to exact base units.
#

"""Independent source-stable arena budget-unit semantics."""

# ruff: file-ignore[assert]

from __future__ import annotations

from typing import Never

import pytest

from benchmarks.arena import budget_links

MANIFEST = "[budget]\nseconds = 3\nmemory_mib = 5\n"
EXPECTED = budget_links.RunBudgets(time_ns=3_000_000_000, memory_bytes=5_242_880)


def test_declared_seconds_and_mib_convert_without_drift() -> None:
    """A valid source budget has the exact governed physical units."""
    assert budget_links.parse_run_budgets(MANIFEST) == EXPECTED


@pytest.mark.parametrize(
    ("conversion", "forged_factor"),
    [("NANOSECONDS_PER_SECOND", 1000), ("BYTES_PER_MIB", 1000)],
)
def test_source_budget_unit_conversion_ignores_mutable_policy_drift(
    monkeypatch: pytest.MonkeyPatch, conversion: str, forged_factor: int
) -> None:
    """Changed runtime constants cannot relabel native source limits."""
    with monkeypatch.context() as patched:
        patched.setattr(budget_links, conversion, forged_factor)
        assert budget_links.parse_run_budgets(MANIFEST) == EXPECTED


def test_public_budget_size_limit_cannot_admit_oversized_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed runtime limit cannot authorize oversized source TOML."""
    oversized = MANIFEST + "#" + "x" * budget_links.MAX_RUN_MANIFEST_BYTES
    monkeypatch.setattr(budget_links, "MAX_RUN_MANIFEST_BYTES", len(oversized) + 1)
    with pytest.raises(budget_links.BudgetLinkError, match="byte limit"):
        budget_links.parse_run_budgets(oversized)


@pytest.mark.parametrize("forged_field", ["time_ns", "memory_bytes"])
def test_source_budgets_ignore_substituted_result_constructor(
    monkeypatch: pytest.MonkeyPatch, forged_field: str
) -> None:
    """A replacement result factory cannot alter checked source budgets."""
    original = budget_links.RunBudgets

    def forged_constructor(
        *, time_ns: int, memory_bytes: int
    ) -> budget_links.RunBudgets:
        result = {"time_ns": time_ns, "memory_bytes": memory_bytes}
        result[forged_field] += 1
        return original(**result)

    with monkeypatch.context() as patched:
        patched.setattr(budget_links, "RunBudgets", forged_constructor)
        assert budget_links.parse_run_budgets(MANIFEST) == EXPECTED


def test_budget_source_limit_rejects_substituted_text_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced local size preflight cannot admit oversized source TOML."""
    oversized = MANIFEST + "#" + "x" * budget_links.MAX_RUN_MANIFEST_BYTES
    monkeypatch.setattr(budget_links, "_admit_text", lambda _text: None)
    with pytest.raises(budget_links.BudgetLinkError, match="byte limit"):
        budget_links.parse_run_budgets(oversized)


def test_budget_source_limit_rejects_suppressed_error_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An overridden error hook cannot silently ignore an oversized manifest."""
    oversized = MANIFEST + "#" + "x" * budget_links.MAX_RUN_MANIFEST_BYTES
    monkeypatch.setattr(budget_links, "_fail", lambda _message: None)
    with pytest.raises(budget_links.BudgetLinkError, match="byte limit"):
        budget_links.parse_run_budgets(oversized)


@pytest.mark.parametrize("forged_seconds", [0, -3])
def test_budget_source_rejects_substituted_positive_integer_validator(
    monkeypatch: pytest.MonkeyPatch,
    forged_seconds: int,
) -> None:
    """Matching source values cannot authorize nonpositive resource budgets."""
    manifest = MANIFEST.replace("seconds = 3", f"seconds = {forged_seconds}")
    monkeypatch.setattr(
        budget_links, "_positive_integer", lambda table, key: table[key]
    )
    with pytest.raises(budget_links.BudgetLinkError, match="positive integer"):
        budget_links.parse_run_budgets(manifest)


def test_budget_limit_rejects_substituted_length_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced module length cannot shrink a source before byte admission."""
    oversized = MANIFEST + "#" + "x" * budget_links.MAX_RUN_MANIFEST_BYTES
    monkeypatch.setattr(budget_links, "len", lambda _value: 0, raising=False)
    with pytest.raises(budget_links.BudgetLinkError, match="byte limit"):
        budget_links.parse_run_budgets(oversized)


def test_budget_rejects_substituted_integer_with_forged_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign numeric receipt cannot fake source equality then change units."""

    class ForgedSeconds:
        def __le__(self, _other: int) -> bool:
            return False

        def __eq__(self, other: object) -> bool:
            return other == 3

        def __ne__(self, other: object) -> bool:
            return other != 3

        def __mul__(self, _unit: int) -> int:
            return 7

    real_type = type
    forged = ForgedSeconds()

    def forged_type(value: object) -> type[object]:
        return int if value is forged else real_type(value)

    monkeypatch.setattr(budget_links, "type", forged_type, raising=False)
    monkeypatch.setattr(
        budget_links.tomllib,
        "loads",
        lambda _text: {"budget": {"seconds": forged, "memory_mib": 5}},
    )
    with pytest.raises(budget_links.BudgetLinkError, match="positive integer"):
        budget_links.parse_run_budgets(MANIFEST)


def test_budget_rejects_nonstring_decoder_keys_despite_substituted_any(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The source parser does not legalize foreign keys in another decoder."""
    invalid_key = object()
    monkeypatch.setattr(budget_links, "any", lambda _values: False, raising=False)
    monkeypatch.setattr(
        budget_links.tomllib,
        "loads",
        lambda _text: {
            invalid_key: "foreign",
            "budget": {"seconds": 3, "memory_mib": 5},
        },
    )
    with pytest.raises(budget_links.BudgetLinkError, match="native string keys"):
        budget_links.parse_run_budgets(MANIFEST)


@pytest.mark.parametrize("provider", ["type", "any", "dict", "str", "int"])
def test_budget_native_shape_providers_are_source_bound(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    """Module-level aliases cannot change the original TOML shape policy."""

    def forged_operation(*_args: object, **_kwargs: object) -> Never:
        pytest.fail(f"public {provider} was called instead of native provider")

    monkeypatch.setattr(budget_links, provider, forged_operation, raising=False)
    assert budget_links.parse_run_budgets(MANIFEST) == EXPECTED


@pytest.mark.parametrize(
    ("source", "failure"),
    [
        ("not source TOML", "invalid experiment run budget TOML"),
        ("[budget]\nseconds = 0\nmemory_mib = 5\n", "positive integer"),
        ("[budget]\nseconds = 1\n#\ud800\nmemory_mib = 5\n", "strict UTF-8"),
    ],
)
@pytest.mark.parametrize("replacement", [RuntimeError, object()])
def test_budget_rejection_preserves_native_error_after_public_alias_rebinding(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    failure: str,
    replacement: object,
) -> None:
    """Malformed source remains a typed admission failure after alias drift."""
    original = budget_links.BudgetLinkError
    with monkeypatch.context() as patched:
        patched.setattr(budget_links, "BudgetLinkError", replacement)
        with pytest.raises(original, match=failure):
            budget_links.parse_run_budgets(source)


@pytest.mark.parametrize("replacement", [RuntimeError, object()])
def test_budget_valid_source_ignores_replaced_public_error_alias(
    monkeypatch: pytest.MonkeyPatch, replacement: object
) -> None:
    """A renamed error class does not influence valid budget results."""
    with monkeypatch.context() as patched:
        patched.setattr(budget_links, "BudgetLinkError", replacement)
        assert budget_links.parse_run_budgets(MANIFEST) == EXPECTED


@pytest.mark.parametrize("replacement", [object(), RuntimeError])
@pytest.mark.parametrize(
    ("stage", "diagnostic"),
    [
        ("decoder", "invalid experiment run budget TOML"),
        ("source", "source TOML could not be parsed"),
        ("utf8", "requires strict UTF-8 text"),
    ],
)
def test_budget_native_catch_aliases_preserve_typed_rejection(
    monkeypatch: pytest.MonkeyPatch,
    replacement: object,
    stage: str,
    diagnostic: str,
) -> None:
    """Late exception aliases cannot leak raw parser or encoding failures."""
    with monkeypatch.context() as patched:
        if stage == "utf8":
            patched.setattr(budget_links, "UnicodeEncodeError", replacement, raising=False)
            source = "\ud800"
        else:
            patched.setattr(budget_links, "Exception", replacement, raising=False)
            source = MANIFEST
            if stage == "source":
                def unavailable(_text: str) -> None:
                    raise OSError("source parser failed")
                patched.setattr(budget_links, "_SOURCE_TOML_LOADS", unavailable)
            else:
                source = "[budget\nseconds = 3\n"
        with pytest.raises(budget_links.BudgetLinkError, match=diagnostic):
            budget_links.parse_run_budgets(source)


@pytest.mark.parametrize("replacement", [object(), RuntimeError])
def test_budget_valid_native_manifest_ignores_error_aliases(
    monkeypatch: pytest.MonkeyPatch, replacement: object
) -> None:
    """Normal budget conversion is independent of exception catch aliases."""
    with monkeypatch.context() as patched:
        patched.setattr(budget_links, "Exception", replacement, raising=False)
        patched.setattr(budget_links, "UnicodeEncodeError", replacement, raising=False)
        assert budget_links.parse_run_budgets(MANIFEST) == EXPECTED
