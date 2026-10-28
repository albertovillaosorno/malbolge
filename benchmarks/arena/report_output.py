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
#   - Checked one-record JSON publication through operator stdout.
# - Must-Not:
#   - Assert rollback of already-emitted output or authenticate measurements.
# - Allows:
#   - Inputs: complete report object and explicit text-record output stream.
#   - Outputs: one newline-terminated JSON record or typed output failure.
#   - Side effects: one text write followed by mandatory text flush.
# - Split-When:
#   - A persistent streaming transport needs framing and atomicity semantics.
# - Merge-When:
#   - The top-level CLI owns complete output publication contracts.
# - Summary:
#   - Rejects short or fabricated write counts and flush failures.
# - Description:
#   - Makes operator command success depend on observed output completion.
# - Usage:
#   - Called by both arena CLIs after complete preflight and analysis.
# - Defaults:
#   - No stdout completion is claimed when the stream fails.
#

"""Checked arena JSON report stdout publication, without rollback claims."""

from __future__ import annotations

import json
from typing import Any
from typing import Never
from typing import Protocol


class TextReportStream(Protocol):
    """Minimal text-stream contract accepted by the arena operator."""

    def write(self, record: str, /) -> int:
        """Write text and return the exact number of accepted characters."""
        ...

    def flush(self) -> None:
        """Flush the text record or fail."""
        ...


class ReportOutputError(ValueError):
    """Operator output did not confirm a complete flushed JSON record."""


def _fail(message: str) -> Never:
    raise ReportOutputError(message)


def publish(report: dict[str, Any], stream: TextReportStream) -> None:
    """Write one complete JSON record with strict stream admission.

    Raises:
        ReportOutputError: The writer or flush did not complete the record.

    """
    record = json.dumps(report, sort_keys=True, indent=2) + "\n"
    try:
        written = stream.write(record)
    except (
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        AttributeError,
    ) as error:
        message = f"arena report stdout write failed: {error}"
        raise ReportOutputError(message) from error
    if type(written) is not int or written != len(record):
        _fail("arena report stdout write did not accept exact text length")
    try:
        stream.flush()
    except (
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        AttributeError,
    ) as error:
        message = f"arena report stdout flush failed: {error}"
        raise ReportOutputError(message) from error
