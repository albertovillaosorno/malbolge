// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Included forbidden-type alias used by a rejected guest-C fixture.
// - Must-Not:
//   - Act as an independently selected translation unit or host ABI authority.
// - Allows:
//   - Inputs: pinned Clang parsing as part of the including source fixture.
//   - Outputs: one imported alias for source-use rejection evidence.
//   - Side effects: none.
// - Split-When:
//   - Split when imported-type fixtures need independent header contracts.
// - Merge-When:
//   - Merge when imported forbidden aliases are no longer regression evidence.
// - Summary:
//   - Provide an imported __int128 alias for guest-C rejection testing.
// - Description:
//   - Keeps the forbidden declaration outside the explicitly selected source.
// - Usage:
//   - Included only by abi_imported_forbidden_alias.c.
// - Defaults:
//   - Inclusion does not make this header a user-selected translation unit.
//

//! Declares one forbidden integer alias outside the selected source.

#ifndef MALBOLGE_TESTS_TIDY_REJECTED_ABI_FORBIDDEN_ALIAS_H
#define MALBOLGE_TESTS_TIDY_REJECTED_ABI_FORBIDDEN_ALIAS_H

typedef __int128 ImportedWideInteger;

#endif
