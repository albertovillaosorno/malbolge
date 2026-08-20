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
#   - Python package identity for repository verifier tooling.
# - Must-Not:
#   - Execute verification or import guest semantics implicitly.
# - Allows:
#   - Inputs: Python package discovery.
#   - Outputs: verifier package identity only.
#   - Side effects: none.
# - Split-When:
#   - Verifier tools require independently configured packages.
# - Merge-When:
#   - Package identity is no longer required.
# - Summary:
#   - Verifier Python package marker.
# - Description:
#   - Keeps bounded verifier tools importable without package-level behavior.
# - Usage:
#   - Used only by repository verifier tooling and tests.
# - Defaults:
#   - No verifier is selected implicitly.
#

"""Repository verifier tooling."""
