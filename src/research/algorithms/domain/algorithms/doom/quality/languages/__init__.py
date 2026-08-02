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
#   - Python package identity for deterministic DOOM language generation.
# - Must-Not:
#   - Execute generators during package import.
# - Allows:
#   - Inputs: ordinary Python package imports.
#   - Outputs: package identity only.
#   - Side effects: none.
# - Split-When:
#   - The package gains independently imported public helpers.
# - Merge-When:
#   - Language generation no longer requires a Python package boundary.
# - Summary:
#   - DOOM language-generation package.
# - Description:
#   - Marks deterministic language generation as an explicit Python package.
# - Usage:
#   - Imported through the owning DOOM quality tooling boundary.
# - Defaults:
#   - Package import performs no generation.
#

"""DOOM language-generation package."""
