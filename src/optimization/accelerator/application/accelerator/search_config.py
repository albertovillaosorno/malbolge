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
import os
from stat import S_ISREG
import tomllib
from typing import TYPE_CHECKING
from typing import cast

from accelerator.search_selection import SearchSelection
from accelerator.search_selection import SearchSelectionError

if TYPE_CHECKING:
    from pathlib import Path

SEARCH_CONFIGURATION_SCHEMA = 1
MAX_SEARCH_CONFIGURATION_BYTES = 1024 * 1024


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


def _config_source_identity(status: os.stat_result) -> tuple[int, ...]:
    """Admit regular config input and record mutation-sensitive identity.

    Returns:
        Device, inode, size, and modification/change timestamps.

    Raises:
        SearchConfigurationError: Config source is not regular.

    """
    if not S_ISREG(status.st_mode):
        message = "search configuration must be a regular file"
        raise SearchConfigurationError(message)
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _read_config_descriptor(
    path: Path,
    descriptor: int,
    expected: tuple[int, ...],
) -> bytes:
    """Verify that the opened user-selected file remains unchanged.

    Returns:
        Exact bounded bytes from the stable opened source.

    Raises:
        SearchConfigurationError: Config source changes during reading.

    """
    with os.fdopen(descriptor, "rb") as stream:
        if _config_source_identity(os.fstat(stream.fileno())) != expected:
            message = "search configuration changed before read"
            raise SearchConfigurationError(message)
        payload = stream.read(MAX_SEARCH_CONFIGURATION_BYTES + 1)
        if len(payload) != expected[2]:
            message = (
                "search configuration changed during read or "
                "exceeds byte limit"
            )
            raise SearchConfigurationError(message)
        if (
            _config_source_identity(os.fstat(stream.fileno())) != expected
            or _config_source_identity(path.stat()) != expected
        ):
            message = "search configuration changed during read"
            raise SearchConfigurationError(message)
        return payload


def _read_config_file(path: Path) -> bytes:
    """Open one stable regular user-selected configuration file.

    Returns:
        The complete bounded source bytes.

    Raises:
        SearchConfigurationError: Source file is invalid or oversized.

    """
    admitted = path.stat()
    expected = _config_source_identity(admitted)
    if admitted.st_size > MAX_SEARCH_CONFIGURATION_BYTES:
        message = "search configuration exceeds byte limit"
        raise SearchConfigurationError(message)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags)
    return _read_config_descriptor(path, descriptor, expected)


def _read_config_bytes(path: Path) -> bytes:
    """Admit one bounded user-selected TOML file, including explicit aliases.

    Returns:
        Source bytes without partial reads or a changing physical file.

    Raises:
        SearchConfigurationError: File is invalid, oversized or unavailable.

    """
    try:
        return _read_config_file(path)
    except OSError as error:
        message = f"cannot read search configuration: {error}"
        raise SearchConfigurationError(message) from error


def load_search_configuration(path: Path) -> SearchConfiguration:
    """Load one versioned TOML search configuration from disk.

    Returns:
        Validated configuration with repository/caller-visible source identity.

    Raises:
        SearchConfigurationError: Source, encoding, or TOML is invalid.

    """
    try:
        text = _read_config_bytes(path).decode("utf-8")
    except UnicodeDecodeError as error:
        message = f"invalid search configuration UTF-8: {error}"
        raise SearchConfigurationError(message) from error
    return parse_search_configuration(text, source=path.as_posix())


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
