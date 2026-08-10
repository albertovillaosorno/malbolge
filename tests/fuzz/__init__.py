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
#   - Python package identity for deterministic fuzz evidence tests.
# - Must-Not:
#   - Select tests, consume ambient entropy, or define semantic authority.
# - Allows:
#   - Inputs: Python package discovery.
#   - Outputs: fuzz-test package identity only.
#   - Side effects: none.
# - Split-When:
#   - Python fuzz evidence gains independent collection configuration.
# - Merge-When:
#   - Package identity is no longer required.
# - Summary:
#   - Deterministic fuzz verification package marker.
# - Description:
#   - Makes Python fuzz evidence explicit beside Rust fuzz cases.
# - Usage:
#   - Imported only by configured pytest collection.
# - Defaults:
#   - No fuzz case is selected implicitly.
#

"""Deterministic fuzz verification tests."""
