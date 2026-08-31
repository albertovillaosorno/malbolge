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
#   - Regression evidence for the standalone final DOOM transform contract.
# - Must-Not:
#   - Require user-supplied DOOM bytes or materialize the generated Rust target.
# - Allows:
#   - Inputs: recipe metadata and test-local final-oracle fixtures.
#   - Outputs: exact source-binding and oracle-surface assertions.
#   - Side effects: test-local files only.
# - Split-When:
#   - Split when final-transform materialization gains checked-in fixtures.
# - Merge-When:
#   - Merge when another suite owns the same publication contract.
# - Summary:
#   - Keeps final DOOM publication bound directly to original upstream source.
# - Description:
#   - Prevents quality output from becoming a runtime input to amalgamate.
# - Usage:
#   - Auto-discovered by the repository Python test suite.
# - Defaults:
#   - Extra or malformed final-oracle entries fail closed.
#

"""Standalone final DOOM transform contract regressions."""

from typing import TYPE_CHECKING

from algorithms.doom.generator import amalgamate
from algorithms.doom.generator import quality
from algorithms.doom.generator.amalgamate_domain import DoomFinalOracleError
from algorithms.doom.generator.amalgamate_domain import (
    validate_authoring_oracle,
)
import pytest

if TYPE_CHECKING:
    from pathlib import Path


_FINAL_PROFILE = "doom-final-v1"
_FINAL_DOMAIN_NAME = "amalgamate_domain.py"
_QUALITY_SEGMENT = "quality"


def test_final_recipe_binds_original_source_directly() -> None:
    """The published final transform must not consume quality output."""
    expected_source = amalgamate.REPOSITORY_ROOT / "doom" / "source"
    assert amalgamate.RECIPE.source_root == expected_source
    assert amalgamate.RECIPE.profile == _FINAL_PROFILE
    assert amalgamate.RECIPE.domain_module is not None
    assert amalgamate.RECIPE.domain_module.name == _FINAL_DOMAIN_NAME
    assert _QUALITY_SEGMENT not in amalgamate.RECIPE.source_root.parts


def test_quality_and_final_recipes_share_one_upstream_location() -> None:
    """Development and publication must bind the same user source snapshot."""
    assert quality.RECIPE.source_root == amalgamate.RECIPE.source_root


def test_final_oracle_requires_exactly_one_doom_c(tmp_path: Path) -> None:
    """Final authoring evidence is one regular canonical C artifact."""
    oracle = tmp_path / "oracle"
    oracle.mkdir()
    doom_c = oracle / "doom.c"
    _ = doom_c.write_text("int main(void) { return 0; }\n", encoding="utf-8")
    validate_authoring_oracle(oracle)

    _ = (oracle / "extra.txt").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(
        DoomFinalOracleError,
        match=r"must contain only doom\.c",
    ):
        validate_authoring_oracle(oracle)
