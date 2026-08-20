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
#   - Versioned deterministic search algorithm and backend configuration.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Versioned deterministic search algorithm and backend configuration."""

from __future__ import annotations

from dataclasses import dataclass
import tomllib
from typing import TYPE_CHECKING
from typing import cast

from accelerator.search_selection import SearchSelection
from accelerator.search_selection import SearchSelectionError

if TYPE_CHECKING:
    from pathlib import Path

SEARCH_CONFIGURATION_SCHEMA = 1


class SearchConfigurationError(ValueError):
    """Versioned search configuration is malformed or unsupported."""


@dataclass(frozen=True, slots=True)
class SearchConfiguration:
    """Versioned base algorithm/backend selection loaded from durable config."""

    selection: SearchSelection
    source: str

    def validated(self) -> SearchConfiguration:
        """Return one exact direct or parsed configuration record.

        Returns:
            Configuration with validated selection and source identities.

        Raises:
            SearchConfigurationError: If direct construction bypassed admission.

        """
        if type(self.selection) is not SearchSelection:
            message = "search configuration selection has wrong type"
            raise SearchConfigurationError(message)
        try:
            selection = self.selection.validated()
        except SearchSelectionError as error:
            raise SearchConfigurationError(str(error)) from error
        return SearchConfiguration(
            selection=selection,
            source=_validated_source(self.source),
        )

    def resolved(
        self,
        *,
        algorithm_override: str | None = None,
        backend_override: str | None = None,
    ) -> SearchSelection:
        """Return the effective selection after explicit caller overrides.

        Returns:
            Validated algorithm/backend identities after applying overrides.

        Raises:
            SearchConfigurationError: If an override is explicitly empty.

        """
        configuration = self.validated()
        algorithm_id = _override(
            configuration.selection.algorithm_id,
            algorithm_override,
            "search algorithm override",
        )
        backend_id = _override(
            configuration.selection.backend_id,
            backend_override,
            "search backend override",
        )
        try:
            return SearchSelection(
                algorithm_id=algorithm_id,
                backend_id=backend_id,
            ).validated()
        except SearchSelectionError as error:
            raise SearchConfigurationError(str(error)) from error


def load_search_configuration(path: Path) -> SearchConfiguration:
    """Load one versioned TOML search configuration from disk.

    Returns:
        Validated configuration with repository/caller-visible source identity.

    """
    return parse_search_configuration(
        path.read_text(encoding="utf-8"),
        source=path.as_posix(),
    )


def parse_search_configuration(
    text: str,
    *,
    source: str = "<memory>",
) -> SearchConfiguration:
    """Parse one versioned TOML search configuration.

    Returns:
        Validated base algorithm/backend selection.

    Raises:
        SearchConfigurationError: If TOML or required fields are invalid.

    """
    try:
        document = cast("object", tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        message = f"invalid search configuration TOML: {error}"
        raise SearchConfigurationError(message) from error
    table = _mapping(document, "search configuration")
    _reject_unknown(table, {"schema_version", "search"}, "search configuration")
    version = table.get("schema_version")
    if type(version) is not int or version != SEARCH_CONFIGURATION_SCHEMA:
        message = f"unsupported search configuration schema: {version}"
        raise SearchConfigurationError(message)
    search = _mapping(table.get("search"), "search configuration.search")
    _reject_unknown(
        search,
        {"algorithm_id", "backend_id"},
        "search configuration.search",
    )
    algorithm_id = _string(search, "algorithm_id")
    backend_id = _string(search, "backend_id")
    try:
        selection = SearchSelection(
            algorithm_id=algorithm_id,
            backend_id=backend_id,
        ).validated()
    except SearchSelectionError as error:
        raise SearchConfigurationError(str(error)) from error
    return SearchConfiguration(
        selection=selection,
        source=source,
    ).validated()


def _validated_source(value: str) -> str:
    if type(value) is not str:
        message = "search configuration source must use the exact string type"
        raise SearchConfigurationError(message)
    if not value:
        message = "search configuration source must not be empty"
        raise SearchConfigurationError(message)
    return value


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        message = f"{context} must be a TOML table"
        raise SearchConfigurationError(message)
    raw = cast("dict[object, object]", value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            message = f"{context} contains a non-string key"
            raise SearchConfigurationError(message)
        result[key] = item
    return result


def _override(base: str, value: str | None, label: str) -> str:
    if value is None:
        return base
    if type(value) is not str:
        message = f"{label} must use the exact string type"
        raise SearchConfigurationError(message)
    if not value:
        message = f"{label} must not be empty"
        raise SearchConfigurationError(message)
    return value


def _reject_unknown(
    table: dict[str, object],
    allowed: set[str],
    context: str,
) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        message = f"{context} contains unknown keys: {unknown}"
        raise SearchConfigurationError(message)


def _string(table: dict[str, object], name: str) -> str:
    value = table.get(name)
    if type(value) is not str or not value:
        message = (
            f"search configuration.search.{name} must be a non-empty string"
        )
        raise SearchConfigurationError(message)
    return value
