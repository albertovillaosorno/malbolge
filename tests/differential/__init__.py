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
#   - Python package identity for differential verification tests.
# - Must-Not:
#   - Select tests or define shared semantic authority.
# - Allows:
#   - Inputs: Python package discovery.
#   - Outputs: differential-test package identity only.
#   - Side effects: none.
# - Split-When:
#   - Differential Python evidence gains independent configuration.
# - Merge-When:
#   - Package identity is no longer required.
# - Summary:
#   - Differential verifier test package marker.
# - Description:
#   - Makes Python differential tests explicit beside Rust evidence.
# - Usage:
#   - Imported only by configured pytest collection.
# - Defaults:
#   - No differential test is selected implicitly.
#

"""Differential verification tests."""
