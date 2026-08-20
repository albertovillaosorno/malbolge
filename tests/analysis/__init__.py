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
#   - Package identity for analysis and research evidence tests.
# - Must-Not:
#   - Add test behavior or mutate repository evidence.
# - Allows:
#   - Inputs: Python package discovery.
#   - Outputs: package identity only.
#   - Side effects: none.
# - Split-When:
#   - Analysis evidence gains independently configured test packages.
# - Merge-When:
#   - Package identity is no longer required.
# - Summary:
#   - Analysis test package marker.
# - Description:
#   - Makes analysis tests an explicit package without adding behavior.
# - Usage:
#   - Imported only by the configured pytest collection boundary.
# - Defaults:
#   - No test is selected implicitly.
#

"""Analysis and research evidence tests."""
