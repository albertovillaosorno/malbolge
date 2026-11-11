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
#   - Package identity for arena regression tests.
# - Must-Not:
#   - Turn synthetic observations into performance claims.
# - Allows:
#   - Inputs: Python test discovery.
#   - Outputs: package identity only.
#   - Side effects: none.
# - Split-When:
#   - Separate algorithm evaluators need isolated suites.
# - Merge-When:
#   - The arena test boundary owns these tests directly.
# - Summary:
#   - Synthetic arena regression package marker.
# - Description:
#   - Keeps test package discovery explicit.
# - Usage:
#   - Imported by pytest when collecting arena regressions.
# - Defaults:
#   - No tests are run on import.
#

"""Synthetic analysis regressions for the compiler algorithm arena."""
