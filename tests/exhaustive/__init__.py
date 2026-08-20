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
#   - Python package identity for exhaustive verification tests.
# - Must-Not:
#   - Select tests or add shared semantic authority.
# - Allows:
#   - Inputs: Python package discovery.
#   - Outputs: exhaustive-test package identity only.
#   - Side effects: none.
# - Split-When:
#   - Exhaustive Python evidence gains independent configuration.
# - Merge-When:
#   - Package identity is no longer required.
# - Summary:
#   - Exhaustive verifier test package marker.
# - Description:
#   - Makes Python exhaustive tests explicit beside Rust fixtures.
# - Usage:
#   - Imported only by configured pytest collection.
# - Defaults:
#   - No exhaustive test is selected implicitly.
#

"""Exhaustive verification tests."""
