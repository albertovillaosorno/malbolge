# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Package identity for deterministic compiler challenge generators.
# - Must-Not:
#   - Add runtime behavior or implicit challenge selection.
# - Allows:
#   - Inputs: Python package discovery.
#   - Outputs: package identity only.
#   - Side effects: none.
# - Split-When:
#   - Challenge families require independently versioned Python packages.
# - Merge-When:
#   - Package identity is no longer required.
# - Summary:
#   - Compiler challenge generator package marker.
# - Description:
#   - Keeps challenge modules explicit without adding package-level behavior.
# - Usage:
#   - Imported only by repository tooling and tests.
# - Defaults:
#   - No challenge is selected implicitly.
#

"""Deterministic compiler challenge generators."""
