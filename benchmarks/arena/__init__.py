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
#   - Package identity for the multi-objective compiler evaluation arena.
# - Must-Not:
#   - Execute experiments or promote algorithm results on import.
# - Allows:
#   - Inputs: Python package discovery.
#   - Outputs: package identity only.
#   - Side effects: none.
# - Split-When:
#   - A separately versioned analyzer requires package isolation.
# - Merge-When:
#   - The arena becomes an owning compiled-tool package.
# - Summary:
#   - Arena evidence analysis package marker.
# - Description:
#   - Enables explicit Python imports without runtime work.
# - Usage:
#   - Imported by synthetic tests and research tooling.
# - Defaults:
#   - No study is selected implicitly.
#

"""Versioned compiler algorithm evaluation arena."""
