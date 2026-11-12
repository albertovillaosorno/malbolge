// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Bounded successful-byte-I/O effect traces between validated ternary IR
//     and independently admitted position-sensitive Malbolge code.
// - Must-Not:
//   - Impersonate EOF, failed byte I/O, general guest computation, or a C ABI.
// - Allows:
//   - Inputs: canonical pre-layout ternary program and selected profile.
//   - Outputs: verified linear source for echo or latest-read byte I/O traces.
//   - Side effects: none.
// - Split-When:
//   - More general guest byte flow requires runtime linkage and allocation.
// - Merge-When:
//   - A complete linker proves this exact sublanguage without special rules.
// - Summary:
//   - Connects a closed typed-IR effect trace to actual executable code.
// - Description:
//   - Proves adjacent byte echoes and latest-successful-read I/O replay traces
//     while retaining the original adjacent-echo admission unchanged.
// - Usage:
//   - First lower typed IR, then call encode_successful_byte_echo.
// - Defaults:
//   - Reject rather than approximate any unproved source semantics.
//
//! Small independently validated ternary-to-Malbolge byte-echo bridge.
//!
//! The resulting program reproduces the projected effect trace **only** when
//! every input succeeds with a byte (not EOF), every output succeeds, and the
//! function's return value and guest ABI are not observed. It is not a
//! general-purpose byte-stream runtime or a C-to-Malbolge compiler.

#[path = "../../malbolge-layout/composition/lib.rs"]
pub mod layout;
#[path = "../../ternary-lowering/composition/lib.rs"]
pub mod ternary;

#[path = "search_output_stream.rs"]
mod search_output_stream;

#[cfg(test)]
#[path = "../../../../tests/compiler/bridge/three_write_preview.rs"]
mod three_write_preview_tests;
#[cfg(test)]
#[path = "../../../../tests/compiler/bridge/four_write_preview.rs"]
mod four_write_preview_tests;

use std::collections::{BTreeMap, BTreeSet};
use std::iter::repeat_n;

use layout::{
    LinearLayout, LinearLayoutError, LinearOpcode, encode_linear_layout,
};
use malbolge::{
    ProfileDescriptor, ProfileMachine, RunOutcome, current_profile,
};
use ternary::{
    TernaryOperation, TernaryProgram, TernaryProgramValidationError,
    validate_ternary_program,
};

// Each entry is an exact, current-profile, one-output guest VM witness for
// [NoOperation; padding], RelocateDataPointer, CrazyData, OutputByte, Halt.
// These are not rotation seeds and do not extend to repeated outputs.
const SINGLE_OUTPUT_CRAZY_WITNESSES: &[(u8, usize)] = &[
    (53, 39), // '5'
    (54, 22), // '6'
    (56, 36), // '8'
    (57, 19), // '9'
    (62, 30), // '>'
    (63, 47), // '?'
    (65, 27), // 'A'
    (66, 65), // 'B'
    (80, 3),  // 'P'
    (81, 11), // 'Q'
    (83, 0),  // 'S'
    (84, 7),  // 'T'
    (90, 1),  // 'Z'
    (93, 28), // ']'
];

// Separate exact one-output guests execute *two* rotations after relocation.
// Their extra instruction changes code phases and loader-expanded source
// length.
const SINGLE_OUTPUT_DOUBLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (40, 51), // '('
    (41, 48), // ')'
    (42, 45), // '*'
];

/// Profile-specific `(byte, graphical no-op prefix)` rotation witnesses.
/// Every candidate is independently re-executed by the normative VM.
/// New witnesses beyond the first 26 prefixes use a bounded 94-phase scan.
const ROTATED_BYTE_SEEDS: &[(u8, usize)] = &[
    (4, 23),
    (5, 20),
    (6, 16),
    (9, 7),
    (10, 4),
    (11, 1),
    (12, 28),
    (13, 39),
    (14, 36),
    (15, 33),
    (16, 30),
    (17, 27),
    (18, 24),
    (19, 21),
    (20, 18),
    (21, 6),
    (22, 3),
    (23, 0),
    (25, 53),
    (29, 47),
    (36, 64),
    (37, 61),
    (38, 58),
    (39, 46),
    (43, 52),
    (44, 49),
    (157, 63),
    (158, 60),
    (159, 57),
    (160, 54),
    (161, 51),
    (162, 48),
    (251, 22),
    (253, 19),
];

/// Exact two-output witnesses differ because the additional `<` changes
/// both positional encoding and loader-expanded memory. These are not valid
/// single-output seeds, nor a proof for three or more outputs.
const ROTATED_DOUBLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (55, 20),
    (64, 19),
    (65, 22),
    (66, 16),
    (163, 7),
    (164, 1),
    (165, 4),
    (182, 3),
    (183, 0),
    (200, 21),
];

/// Three outputs need their own source-length-sensitive relocation seeds.
/// Each selected value was independently admitted and checked in the VM;
/// these are witnesses, not a claim of exhaustive byte synthesis.
const ROTATED_TRIPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (3, 23),
    (4, 20),
    (5, 17),
    (6, 14),
    (7, 2),
    (8, 8),
    (9, 5),
    (11, 24),
    (18, 22),
    (19, 19),
    (20, 16),
    (21, 13),
    (22, 7),
    (23, 25),
    (24, 4),
    (25, 1),
    (144, 6),
    (145, 3),
    (146, 0),
    (251, 21),
    (252, 15),
];

/// Four outputs change every preceding source phase and loader data word.
/// Select only one independently witnessed short-phase prefix per byte.
const ROTATED_QUADRUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (43, 0),
    (182, 1),
    (168, 2),
    (44, 3),
    (175, 4),
    (162, 5),
    (42, 6),
    (176, 7),
    (161, 8),
    (40, 9),
    (41, 12),
    (178, 13),
    (187, 14),
    (66, 15),
    (192, 16),
    (185, 17),
    (64, 18),
    (191, 19),
    (186, 20),
    (65, 21),
    (196, 22),
    (184, 23),
    (57, 24),
    (201, 25),
];

/// Five outputs have different positional decode and loader-expanded data.
/// This table keeps the first witness for each value from a 26-phase VM scan.
const ROTATED_QUINTUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (10, 0),
    (7, 1),
    (24, 2),
    (9, 3),
    (23, 5),
    (8, 7),
    (22, 8),
    (142, 10),
    (21, 11),
    (6, 12),
    (141, 13),
    (140, 16),
    (4, 18),
    (139, 19),
    (12, 21),
    (138, 22),
    (25, 23),
    (137, 25),
];

/// Six-output loader expansion has its own shortest valid VM witnesses.
const ROTATED_SEXTUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (47, 0),
    (175, 2),
    (42, 3),
    (41, 4),
    (177, 5),
    (40, 6),
    (176, 8),
    (162, 9),
    (178, 11),
    (66, 13),
    (200, 14),
    (64, 16),
    (65, 19),
    (190, 20),
    (186, 21),
    (63, 22),
    (191, 23),
    (185, 24),
    (61, 25),
];

/// Seven-output loader expansion has its own shortest valid VM witnesses.
const ROTATED_SEPTUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (21, 0),
    (9, 1),
    (8, 2),
    (23, 3),
    (22, 6),
    (7, 7),
    (6, 10),
    (20, 12),
    (253, 13),
    (5, 14),
    (19, 15),
    (251, 16),
    (4, 17),
    (18, 18),
    (17, 21),
    (12, 22),
    (16, 24),
    (10, 25),
];

/// Eight outputs have their own verified short-prefix relocation witnesses.
/// Duplicate generated values retain only their first successful phase.
const ROTATED_OCTUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (175, 0),
    (163, 1),
    (42, 2),
    (177, 3),
    (161, 4),
    (40, 5),
    (176, 6),
    (162, 7),
    (41, 8),
    (178, 9),
    (66, 10),
    (56, 11),
    (201, 12),
    (64, 13),
    (55, 14),
    (200, 15),
    (65, 16),
    (199, 18),
    (57, 19),
    (198, 21),
    (197, 24),
];

/// Nine outputs require a new positional layout and loader-resident word.
/// Each entry is the first verified phase for its byte in a 26-phase scan.
const ROTATED_NONUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (1, 23),
    (2, 20),
    (3, 17),
    (4, 14),
    (5, 11),
    (6, 8),
    (7, 5),
    (9, 2),
    (10, 24),
    (11, 18),
    (18, 16),
    (19, 13),
    (20, 10),
    (21, 7),
    (22, 1),
    (23, 19),
    (142, 6),
    (143, 3),
    (144, 0),
    (251, 15),
    (252, 9),
];

/// Ten-output positions use independently verified loader-expanded data.
const ROTATED_DECUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (40, 3),
    (41, 6),
    (42, 0),
    (55, 21),
    (56, 24),
    (57, 18),
    (64, 12),
    (65, 15),
    (66, 9),
    (161, 2),
    (162, 5),
    (176, 1),
    (178, 7),
    (182, 20),
    (183, 23),
    (184, 17),
    (185, 11),
    (186, 14),
    (187, 8),
    (191, 13),
    (192, 10),
    (193, 25),
    (196, 16),
    (200, 22),
    (201, 19),
];

/// Eleven-output positions are witnessed separately on the real guest VM.
/// Keep only the earliest safe phase for each distinct byte.
const ROTATED_UNDECUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (4, 12),
    (6, 6),
    (7, 3),
    (8, 1),
    (9, 0),
    (10, 8),
    (12, 15),
    (21, 5),
    (22, 2),
    (24, 23),
    (25, 17),
    (135, 25),
    (136, 22),
    (137, 19),
    (138, 16),
    (139, 13),
    (140, 10),
];

/// Twelve-output positions are independently replayed on the real guest VM.
/// The first safe source phase is the only admitted seed per byte.
const ROTATED_DODECUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (40, 0),
    (41, 3),
    (56, 7),
    (60, 25),
    (61, 19),
    (62, 22),
    (63, 16),
    (64, 10),
    (65, 13),
    (66, 6),
    (176, 2),
    (177, 12),
    (178, 5),
    (180, 24),
    (184, 23),
    (185, 18),
    (186, 15),
    (190, 14),
    (191, 17),
    (200, 8),
];

/// Thirteen outputs change the positional decode and loader-expanded data.
/// Only first-phased witnesses re-executed by the normative VM are admitted.
const ROTATED_TREDECUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (22, 0),
    (7, 1),
    (21, 3),
    (6, 4),
    (252, 5),
    (20, 6),
    (5, 7),
    (19, 9),
    (251, 10),
    (4, 11),
    (18, 12),
    (9, 13),
    (17, 15),
    (12, 16),
    (8, 17),
    (16, 18),
    (10, 19),
    (15, 21),
    (14, 24),
];

/// Fourteen-output loader-expanded source has independently VM-checked seeds.
const ROTATED_FOURTEEN_BYTE_SEEDS: &[(u8, usize)] = &[
    (176, 0),
    (162, 1),
    (41, 2),
    (178, 3),
    (187, 4),
    (66, 5),
    (192, 6),
    (185, 7),
    (55, 8),
    (200, 9),
    (65, 10),
    (56, 11),
    (199, 12),
    (57, 13),
    (198, 15),
    (64, 17),
    (197, 18),
    (193, 21),
    (51, 22),
    (59, 23),
    (195, 24),
    (49, 25),
];

/// Fifteen-output witnesses omit the unsupported phase 20; no phase
/// extrapolation.
const ROTATED_FIFTEEN_BYTE_SEEDS: &[(u8, usize)] = &[
    (142, 0),
    (21, 1),
    (6, 2),
    (141, 3),
    (10, 4),
    (140, 6),
    (4, 8),
    (251, 9),
    (18, 10),
    (3, 11),
    (11, 12),
    (23, 13),
    (2, 14),
    (22, 16),
    (1, 17),
    (8, 21),
    (255, 23),
];

/// Sixteen outputs have new source-length-sensitive VM and loader witnesses.
/// The shortest source phase is retained for each distinct admitted byte.
const ROTATED_SIXTEEN_BYTE_SEEDS: &[(u8, usize)] = &[
    (41, 0),
    (178, 1),
    (177, 2),
    (66, 3),
    (200, 4),
    (176, 5),
    (64, 6),
    (186, 8),
    (65, 9),
    (196, 10),
    (184, 11),
    (57, 12),
    (201, 13),
    (182, 14),
    (55, 15),
    (183, 17),
    (56, 18),
    (193, 19),
    (181, 20),
    (51, 21),
    (195, 22),
    (179, 23),
    (49, 24),
    (194, 25),
];

/// Seventeen outputs have a separately derived 26-phase VM witness table.
/// The first physical prefix per nonzero byte is the only admitted seed.
const ROTATED_SEVENTEEN_BYTE_SEEDS: &[(u8, usize)] = &[
    (6, 0),
    (20, 2),
    (253, 3),
    (5, 4),
    (19, 5),
    (251, 6),
    (4, 7),
    (9, 8),
    (12, 9),
    (138, 10),
    (25, 11),
    (137, 13),
    (7, 15),
    (136, 16),
    (24, 17),
    (135, 19),
    (22, 20),
    (134, 22),
    (133, 25),
];

/// Eighteen outputs use independently re-executed loader-expanded geometry.
/// Each nonzero byte admits only its first (shortest) successful phase.
const ROTATED_EIGHTEEN_BYTE_SEEDS: &[(u8, usize)] = &[
    (66, 0),
    (56, 1),
    (201, 2),
    (64, 3),
    (55, 4),
    (200, 5),
    (65, 6),
    (190, 8),
    (186, 9),
    (63, 10),
    (191, 11),
    (185, 12),
    (61, 13),
    (62, 16),
    (184, 17),
    (180, 18),
    (60, 19),
    (179, 21),
    (58, 22),
    (59, 25),
];

/// Nineteen repeated outputs require a separate VM-verified data/phase table.
/// Duplicated phases retain only the shortest graphical no-op prefix.
const ROTATED_NINETEEN_BYTE_SEEDS: &[(u8, usize)] = &[
    (20, 0),
    (5, 1),
    (252, 2),
    (19, 3),
    (4, 4),
    (251, 5),
    (18, 6),
    (3, 7),
    (9, 8),
    (17, 9),
    (12, 10),
    (8, 11),
    (16, 12),
    (10, 13),
    (7, 14),
    (15, 15),
    (14, 18),
    (13, 21),
    (6, 25),
];

/// Twenty outputs use an independently verified source/loader phase table.
/// Duplicate bytes retain only their shortest safe graphical prefix.
const ROTATED_TWENTY_BYTE_SEEDS: &[(u8, usize)] = &[
    (192, 0),
    (185, 1),
    (64, 2),
    (191, 3),
    (186, 4),
    (65, 5),
    (196, 6),
    (184, 7),
    (198, 9),
    (55, 10),
    (197, 12),
    (56, 13),
    (193, 15),
    (51, 16),
    (59, 17),
    (195, 18),
    (49, 19),
    (58, 20),
    (194, 21),
    (50, 22),
    (48, 25),
];

/// Twenty-one outputs require their own exact loader-phase witnesses.
/// Phase fourteen is not admitted; duplicated values keep shortest prefixes.
const ROTATED_TWENTY_ONE_BYTE_SEEDS: &[(u8, usize)] = &[
    (140, 0),
    (10, 1),
    (4, 2),
    (139, 3),
    (9, 4),
    (12, 5),
    (138, 6),
    (25, 7),
    (2, 8),
    (11, 9),
    (22, 10),
    (1, 11),
    (21, 13),
    (8, 15),
    (23, 16),
    (255, 17),
    (254, 20),
    (7, 21),
    (253, 23),
    (252, 24),
];

/// Twenty-two outputs have a separate 26-phase loader-bound rotation oracle.
/// Phase ten duplicates the shorter phase one witness for byte 200.
const ROTATED_TWENTY_TWO_BYTE_SEEDS: &[(u8, usize)] = &[
    (64, 0),
    (200, 1),
    (177, 2),
    (65, 3),
    (190, 4),
    (186, 5),
    (63, 6),
    (191, 7),
    (182, 8),
    (55, 9),
    (183, 11),
    (56, 12),
    (193, 13),
    (181, 14),
    (51, 15),
    (195, 16),
    (179, 17),
    (49, 18),
    (194, 19),
    (180, 20),
    (50, 21),
    (196, 22),
    (169, 23),
    (48, 24),
    (18, 25),
];

/// Twenty-three outputs use their own bounded real-VM-verified source phases.
/// Duplicate byte values retain only the shortest source no-op prefix.
const ROTATED_TWENTY_THREE_BYTE_SEEDS: &[(u8, usize)] = &[
    (251, 0),
    (4, 1),
    (18, 2),
    (9, 3),
    (17, 5),
    (12, 6),
    (8, 7),
    (25, 8),
    (7, 9),
    (136, 10),
    (24, 11),
    (135, 13),
    (22, 14),
    (134, 16),
    (133, 19),
    (21, 20),
    (6, 21),
    (132, 22),
    (10, 23),
    (42, 24),
    (27, 25),
];

/// Twenty-four outputs use a separate bounded real-VM-verified phase scan.
/// Phase seven fails admission; duplicate values keep their shortest prefix.
const ROTATED_TWENTY_FOUR_BYTE_SEEDS: &[(u8, usize)] = &[
    (65, 0),
    (56, 1),
    (199, 2),
    (57, 3),
    (198, 5),
    (55, 6),
    (191, 8),
    (186, 9),
    (62, 10),
    (184, 11),
    (180, 12),
    (60, 13),
    (185, 14),
    (179, 15),
    (58, 16),
    (59, 19),
    (187, 20),
    (168, 21),
    (48, 22),
    (21, 23),
    (155, 25),
];

/// Twenty-five outputs use only independently VM-verified source phases.
/// Phase seven fails; duplicated bytes retain the shortest safe prefix.
const ROTATED_TWENTY_FIVE_BYTE_SEEDS: &[(u8, usize)] = &[
    (2, 4),
    (3, 1),
    (6, 19),
    (7, 8),
    (8, 14),
    (9, 10),
    (11, 2),
    (12, 18),
    (13, 15),
    (14, 12),
    (15, 9),
    (18, 0),
    (22, 6),
    (23, 3),
    (29, 23),
    (39, 22),
    (44, 25),
    (162, 24),
    (253, 20),
];

/// Twenty-six outputs admit 24 independent real-VM source phases.
/// Phases six and seven fail; duplicate byte values keep the shortest prefix.
const ROTATED_TWENTY_SIX_BYTE_SEEDS: &[(u8, usize)] = &[
    (20, 24),
    (21, 21),
    (47, 20),
    (48, 19),
    (49, 13),
    (50, 16),
    (51, 10),
    (55, 5),
    (57, 2),
    (58, 14),
    (59, 11),
    (65, 8),
    (137, 25),
    (139, 22),
    (156, 23),
    (182, 4),
    (184, 1),
    (193, 9),
    (194, 15),
    (195, 12),
    (196, 0),
    (201, 3),
];

/// Twenty-seven outputs admit 23 real-VM phases, excluding six through eight.
/// Each distinct byte retains only its first admissible no-op prefix.
const ROTATED_TWENTY_SEVEN_BYTE_SEEDS: &[(u8, usize)] = &[
    (7, 5),
    (8, 9),
    (9, 2),
    (11, 19),
    (21, 16),
    (22, 13),
    (23, 10),
    (25, 1),
    (41, 23),
    (42, 20),
    (137, 3),
    (138, 0),
    (164, 22),
    (165, 21),
    (252, 18),
    (253, 17),
    (254, 14),
    (255, 11),
];

/// Twenty-eight outputs admit 23 independently replayed short source phases.
/// Phases five through seven fail; byte 191 uses its shortest prefix (one).
const ROTATED_TWENTY_EIGHT_BYTE_SEEDS: &[(u8, usize)] = &[
    (18, 19),
    (19, 25),
    (21, 22),
    (48, 18),
    (49, 12),
    (50, 15),
    (51, 9),
    (61, 3),
    (63, 0),
    (140, 23),
    (141, 20),
    (151, 24),
    (153, 21),
    (169, 17),
    (179, 11),
    (180, 14),
    (181, 8),
    (185, 2),
    (191, 1),
    (194, 13),
    (195, 10),
    (196, 16),
];

/// Twenty-nine outputs admit 23 guest VM phases; five through seven fail.
/// Later duplicate literals keep their earliest safe prefix.
const ROTATED_TWENTY_NINE_BYTE_SEEDS: &[(u8, usize)] = &[
    (6, 15),
    (7, 4),
    (8, 1),
    (9, 9),
    (10, 3),
    (12, 0),
    (16, 2),
    (21, 14),
    (22, 8),
    (25, 25),
    (26, 22),
    (27, 19),
    (42, 18),
    (43, 21),
    (132, 16),
    (133, 13),
    (134, 10),
    (164, 23),
    (165, 20),
];

/// Thirty-three outputs have 21 verified VM phases (not three to seven).
/// Bytes 164 and 160 use the shortest successful guest rotation prefix.
const ROTATED_THIRTY_THREE_BYTE_SEEDS: &[(u8, usize)] = &[
    (7, 9),
    (9, 2),
    (11, 13),
    (21, 10),
    (24, 1),
    (39, 23),
    (40, 20),
    (41, 17),
    (42, 14),
    (136, 0),
    (158, 25),
    (159, 24),
    (160, 21),
    (164, 16),
    (165, 15),
    (252, 12),
    (253, 11),
    (254, 8),
];

/// Thirty-two outputs have 21 successful VM phases; three through seven fail.
/// Only the earliest guest-computed witness for byte 139 is retained.
const ROTATED_THIRTY_TWO_BYTE_SEEDS: &[(u8, usize)] = &[
    (15, 24),
    (19, 21),
    (20, 18),
    (21, 15),
    (47, 14),
    (48, 13),
    (50, 10),
    (56, 2),
    (58, 8),
    (59, 11),
    (136, 22),
    (137, 19),
    (139, 16),
    (150, 23),
    (154, 20),
    (156, 17),
    (183, 1),
    (194, 9),
    (196, 12),
    (200, 0),
];

/// Thirty-one-output source layout admits 22/26 independent VM phases.
/// Only shortest nonzero byte witnesses are included (7, 29, 39 repeat).
const ROTATED_THIRTY_ONE_BYTE_SEEDS: &[(u8, usize)] = &[
    (1, 1),
    (6, 13),
    (7, 10),
    (8, 8),
    (10, 2),
    (11, 15),
    (12, 12),
    (13, 9),
    (21, 3),
    (22, 0),
    (25, 23),
    (29, 17),
    (39, 16),
    (43, 22),
    (44, 19),
    (160, 24),
    (161, 21),
    (162, 18),
    (253, 14),
];

/// Thirty-output source and loader geometry admit 22 of 26 phases.
/// Four through seven fail; repeated byte 185/21 keeps the shorter prefix.
const ROTATED_THIRTY_BYTE_SEEDS: &[(u8, usize)] = &[
    (15, 24),
    (16, 23),
    (18, 20),
    (19, 21),
    (21, 17),
    (48, 16),
    (55, 0),
    (56, 3),
    (58, 10),
    (59, 13),
    (64, 1),
    (150, 25),
    (154, 22),
    (155, 19),
    (168, 15),
    (179, 9),
    (180, 12),
    (185, 8),
    (187, 14),
    (197, 2),
];

// The distinct-pair composer searches the canonical graphical decoder phases
// and two genuine data-operation choices per output. A cheap proposal model
// never authorizes publication; only the independent normative VM does.
const DISTINCT_PAIR_PREFIX_PHASES: usize = 94;
const HIGH_TRIT_WEIGHT: u32 = 4_782_969; // 3^14 for 15-trit words.

// Each pair is an exact one-zero-output-then-one-nonzero-output guest
// witness: `<`, padding `o`, `j`, `p`, `<`, `v` under malbolge-2026.
// Three source-proven different bytes, each produced by its own relocated
// `p` on independently checked out-of-source data addresses.
const DISTINCT_LITERAL_TRIPLE_CRAZY_WITNESSES: &[([u8; 3], usize)] = &[
    (*b"Z%H", 0),
    (*b"Q.O", 1),
    (*b"Y-P", 2),
    (*b"T\"O", 4),
    (*b"T\"Q", 6),
];

const ZERO_THEN_LITERAL_CRAZY_WITNESSES: &[(u8, usize)] =
    &[(b'Z', 0), (b'P', 2), (b'T', 6), (b'S', 17)];

/// A failed pre-layout admission, semantic bridge, or final target admission.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ByteEchoBridgeError {
    /// Canonical pre-layout program semantics or provenance are invalid.
    InvalidProgram(TernaryProgramValidationError),
    /// The independently checked target encoder rejected the selected trace.
    Layout(LinearLayoutError),
    /// The selected VM profile differs from the validated program identity.
    ProfileMismatch,
    /// The function is not a nonempty sequence of adjacent echo pairs with
    /// one final value-free return, or multiple functions are supplied.
    UnsupportedEffectTrace,
}

// A finite source layout carries one or more guest arithmetic operations.
type LiteralOutputWitness = (usize, &'static [LinearOpcode]);
type RotatedByteSeedTable = &'static [(u8, usize)];

// Each output count has a distinct positional decode and loader-expanded
// memory witness. The closed selector prevents a seed from leaking across
// source lengths before independent guest execution verifies the candidate.
const fn rotated_byte_seeds(outputs: usize) -> Option<RotatedByteSeedTable> {
    match outputs {
        1 => Some(ROTATED_BYTE_SEEDS),
        2 => Some(ROTATED_DOUBLE_BYTE_SEEDS),
        3 => Some(ROTATED_TRIPLE_BYTE_SEEDS),
        4 => Some(ROTATED_QUADRUPLE_BYTE_SEEDS),
        5 => Some(ROTATED_QUINTUPLE_BYTE_SEEDS),
        6 => Some(ROTATED_SEXTUPLE_BYTE_SEEDS),
        7 => Some(ROTATED_SEPTUPLE_BYTE_SEEDS),
        8 => Some(ROTATED_OCTUPLE_BYTE_SEEDS),
        9 => Some(ROTATED_NONUPLE_BYTE_SEEDS),
        10 => Some(ROTATED_DECUPLE_BYTE_SEEDS),
        11 => Some(ROTATED_UNDECUPLE_BYTE_SEEDS),
        12 => Some(ROTATED_DODECUPLE_BYTE_SEEDS),
        13 => Some(ROTATED_TREDECUPLE_BYTE_SEEDS),
        14 => Some(ROTATED_FOURTEEN_BYTE_SEEDS),
        15 => Some(ROTATED_FIFTEEN_BYTE_SEEDS),
        16 => Some(ROTATED_SIXTEEN_BYTE_SEEDS),
        17 => Some(ROTATED_SEVENTEEN_BYTE_SEEDS),
        18 => Some(ROTATED_EIGHTEEN_BYTE_SEEDS),
        19 => Some(ROTATED_NINETEEN_BYTE_SEEDS),
        20 => Some(ROTATED_TWENTY_BYTE_SEEDS),
        21 => Some(ROTATED_TWENTY_ONE_BYTE_SEEDS),
        22 => Some(ROTATED_TWENTY_TWO_BYTE_SEEDS),
        23 => Some(ROTATED_TWENTY_THREE_BYTE_SEEDS),
        24 => Some(ROTATED_TWENTY_FOUR_BYTE_SEEDS),
        25 => Some(ROTATED_TWENTY_FIVE_BYTE_SEEDS),
        26 => Some(ROTATED_TWENTY_SIX_BYTE_SEEDS),
        27 => Some(ROTATED_TWENTY_SEVEN_BYTE_SEEDS),
        28 => Some(ROTATED_TWENTY_EIGHT_BYTE_SEEDS),
        29 => Some(ROTATED_TWENTY_NINE_BYTE_SEEDS),
        30 => Some(ROTATED_THIRTY_BYTE_SEEDS),
        31 => Some(ROTATED_THIRTY_ONE_BYTE_SEEDS),
        32 => Some(ROTATED_THIRTY_TWO_BYTE_SEEDS),
        33 => Some(ROTATED_THIRTY_THREE_BYTE_SEEDS),
        _ => None,
    }
}

/// Emits a genuine two-step guest program for a side-effect-free void function.
///
/// The complete admitted ternary function must contain only `ReturnVoid`.
/// The first cell is an inert no-op required by the canonical two-cell
/// source loader; the second is a reached guest halt. No C computation,
/// source effects, process exit status or arbitrary return ABI are inferred.
///
/// # Errors
///
/// Rejects malformed/foreign canonical state, non-void returns, any source
/// effect, or a layout that fails independent profile admission.
pub fn encode_empty_void_function(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if !matches!(function.operations.as_slice(), [
        TernaryOperation::ReturnVoid { .. }
    ]) {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    encode_linear_layout(profile, &[
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ])
    .map_err(ByteEchoBridgeError::Layout)
}

/// Emits one bounded, source-validated successful-byte-echo trace.
///
/// Each adjacent `ByteInput`/`ByteOutput` pair must use the exact same SSA
/// value, and the final operation must be `ReturnVoid`. The VM itself has no
/// host byte callbacks: source is returned from the separately verified linear
/// layout. The caller must enforce that all projected inputs/outputs succeed;
/// the VM's raw EOF word is **not** the typed successful-byte result.
///
/// # Errors
///
/// Rejects malformed canonical state, profile drift, any unsupported source
/// effect or return, and any address-sensitive layout failure.
pub fn encode_successful_byte_echo(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, instructions)) =
        function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = instructions.as_chunks::<2>();
    if pairs.is_empty() || !remainder.is_empty() {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut operations = Vec::with_capacity(function.operations.len());
    for pair in pairs {
        let [
            TernaryOperation::ByteInput { result, .. },
            TernaryOperation::ByteOutput { value, .. },
        ] = pair
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
        operations.push(LinearOpcode::InputWord);
        operations.push(LinearOpcode::OutputByte);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)
}

/// Emits a bounded successful-byte I/O trace using the VM accumulator itself.
///
/// Every source operation is one successful `ByteInput` or `ByteOutput`, with
/// one final `ReturnVoid`. An output must name **exactly the most recent**
/// successful input's SSA result; the input may be output repeatedly or not
/// at all. Reading a later byte overwrites the accumulator, so an earlier
/// byte's SSA identity cannot be replayed after that read. No guest work is
/// delegated to a host callback; the linear code contains only raw VM input,
/// output and halt instructions.
///
/// This is deliberately distinct from [`encode_successful_byte_echo`]: the
/// old API retains its strict adjacent-pair contract. The caller must enforce
/// successful byte reads (never EOF) and successful writes. Return/ABI state
/// is unobserved. This function does not realize arbitrary byte dataflow,
/// constants, arithmetic, guest heap or control-flow operations.
///
/// # Errors
///
/// Rejects malformed or profile-mismatched ternary state, absent successful
/// input, any non-I/O effect, stale/undefined SSA output and unsafe layout.
pub fn encode_successful_latest_byte_trace(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, instructions)) =
        function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let mut last_input = None;
    let mut operations = Vec::with_capacity(function.operations.len());
    for instruction in instructions {
        if let TernaryOperation::ByteInput { result, .. } = instruction {
            last_input = Some(*result);
            operations.push(LinearOpcode::InputWord);
        } else if let TernaryOperation::ByteOutput { value, .. } = instruction {
            if last_input != Some(*value) {
                return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
            }
            operations.push(LinearOpcode::OutputByte);
        } else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    if last_input.is_none() {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)
}

/// Emits an exact nonempty zero-byte output trace using the VM's initial A=0.
///
/// The source is one verified `MaterializeU8(0)` SSA definition, followed by
/// one or more outputs of **that same** SSA byte and a final `ReturnVoid`.
/// `MaterializeU8(0)` needs no guest instruction because the normative VM
/// initializes its accumulator to zero. Each output is still a real guest
/// `<` instruction, followed by one guest halt. Neither a host print nor a
/// fabricated guest byte register is involved. No byte input is consumed.
///
/// This opt-in bridge does **not** alter strict echo or latest-read semantics.
/// Only the original initial zero constant is admitted: a nonzero scalar,
/// rewritten value, older SSA identity, additional constant or other target
/// operation needs separate executable dataflow proof. Source provenance
/// remains in the canonical ternary input; code slots only cover guest work.
///
/// # Errors
///
/// Rejects invalid/profile-mismatched ternary source, unsupported or absent
/// zero output, and target code longer than the linear layout capacity.
pub fn encode_initial_zero_outputs(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, instructions)) =
        function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::MaterializeU8 { result, scalar, .. }, writes)) =
        instructions.split_first()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if scalar.bits() != 0 || writes.is_empty() {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut operations = Vec::with_capacity(writes.len().saturating_add(1));
    for write in writes {
        let TernaryOperation::ByteOutput { value, .. } = write else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if value != result {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
        operations.push(LinearOpcode::OutputByte);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)
}

/// Emits verified guest code for zero outputs followed by latest-byte I/O.
///
/// The sole source function must begin with one `MaterializeU8(0)` and at
/// least one output of that SSA byte before the first successful input.
/// Once any input executes, the accumulator changes and every subsequent
/// output must name exactly the *latest* input SSA result. At least one input
/// and an output of an input are required; the last operation is `ReturnVoid`.
/// The zero materialization is proven by initial A=0, not host computation;
/// each output and input is a real guest instruction. EOF, failures, memory,
/// arithmetic, and guest ABI state remain outside this bounded contract.
///
/// # Errors
///
/// Rejects malformed source, wrong profile, stale SSA, unsupported effects,
/// and unsafe or excessively long address-sensitive source.
pub fn encode_zero_prefixed_latest_byte_trace(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, instructions)) =
        function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::MaterializeU8 { result, scalar, .. }, effects)) =
        instructions.split_first()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if scalar.bits() != 0 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut last_input = None;
    let mut initial_outputs = false;
    let mut subsequent_outputs = false;
    let mut operations = Vec::with_capacity(effects.len().saturating_add(1));
    for effect in effects {
        if let TernaryOperation::ByteInput { result: latest, .. } = effect {
            last_input = Some(*latest);
            operations.push(LinearOpcode::InputWord);
        } else if let TernaryOperation::ByteOutput { value, .. } = effect {
            let valid =
                last_input.map_or(value == result, |latest| *value == latest);
            if !valid {
                return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
            }
            if last_input.is_some() {
                subsequent_outputs = true;
            } else {
                initial_outputs = true;
            }
            operations.push(LinearOpcode::OutputByte);
        } else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    if !initial_outputs || last_input.is_none() || !subsequent_outputs {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)
}

/// Emits guest I/O while proving exact byte-bitcast SSA aliases remain live.
///
/// Only eight-bit signed/unsigned representation-preserving casts are allowed.
/// Every new input invalidates previous aliases; casts emit no guest code.
/// The trace needs at least one input, cast and output, and final void return.
///
/// # Errors
/// Rejects noncanonical operations, stale aliases, other effects or bad layout.
pub fn encode_latest_byte_identity_trace(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, effects)) =
        function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if effects.len() > 4096 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut aliases = BTreeSet::new();
    let mut seen_cast = false;
    let mut seen_output = false;
    let mut operations = Vec::with_capacity(effects.len().saturating_add(1));
    for effect in effects {
        if let TernaryOperation::ByteInput { result, .. } = effect {
            aliases.clear();
            _ = aliases.insert(*result);
            operations.push(LinearOpcode::InputWord);
        } else if let TernaryOperation::ByteOutput { value, .. } = effect {
            if !aliases.contains(value) {
                return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
            }
            seen_output = true;
            operations.push(LinearOpcode::OutputByte);
        } else if let Some((result, value)) = byte_bitcast_operands(effect) {
            if !aliases.contains(&value) {
                return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
            }
            _ = aliases.insert(result);
            seen_cast = true;
        } else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    if aliases.is_empty() || !seen_cast || !seen_output {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)
}

const fn byte_bitcast_operands(
    operation: &TernaryOperation,
) -> Option<(u32, u32)> {
    let (TernaryOperation::BitcastI8ToI8 { result, value, .. }
    | TernaryOperation::BitcastI8ToU8 { result, value, .. }
    | TernaryOperation::BitcastU8ToI8 { result, value, .. }
    | TernaryOperation::BitcastU8ToU8 { result, value, .. }) = operation
    else {
        return None;
    };
    Some((*result, *value))
}

// A witness must be tied to the exact output count: changing the count
// changes both positional encoding and the guest's loader-expanded data.
fn literal_output_witness(
    byte: u8,
    count: usize,
) -> Option<LiteralOutputWitness> {
    let seeds = rotated_byte_seeds(count)?;
    if let Some((_, padding)) = seeds.iter().find(|(value, _)| *value == byte) {
        return Some((*padding, &[LinearOpcode::RotateData]));
    }
    if count != 1 {
        return None;
    }
    if let Some((_, padding)) = SINGLE_OUTPUT_CRAZY_WITNESSES
        .iter()
        .find(|(value, _)| *value == byte)
    {
        return Some((*padding, &[LinearOpcode::CrazyData]));
    }
    SINGLE_OUTPUT_DOUBLE_ROTATION_WITNESSES
        .iter()
        .find(|(value, _)| *value == byte)
        .map(|(_, padding)| {
            (
                *padding,
                &[LinearOpcode::RotateData, LinearOpcode::RotateData][..],
            )
        })
}

/// Emit exactly one initial zero byte followed by one witnessed nonzero byte.
///
/// Two different canonical source SSA constants are required. The guest
/// outputs initial A=0, then its relocated `p` operation computes the second
/// byte; neither effect is simulated by the host. Every recipe is executed in
/// the normative VM before its source can be published.
///
/// # Errors
///
/// Refuses malformed source effects, profile drift, unsupported byte pairs,
/// invalid layout, or a guest trace that differs from the requested bytes.
pub fn encode_zero_then_literal(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let [
        TernaryOperation::MaterializeU8 {
            result: zero_id,
            scalar: zero,
            ..
        },
        TernaryOperation::ByteOutput { value: first_id, .. },
        TernaryOperation::MaterializeU8 {
            result: second_id,
            scalar: second,
            ..
        },
        TernaryOperation::ByteOutput { value: last_id, .. },
        TernaryOperation::ReturnVoid { .. },
    ] = function.operations.as_slice()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if zero.bits() != 0
        || zero_id != first_id
        || second_id != last_id
        || zero_id == second_id
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let padding = ZERO_THEN_LITERAL_CRAZY_WITNESSES
        .iter()
        .find(|(byte, _)| *byte == second.bits())
        .map(|(_, padding)| *padding)
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
    let mut operations = vec![LinearOpcode::OutputByte];
    operations.extend(repeat_n(LinearOpcode::NoOperation, padding));
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != [0, second.bits()]
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Cache graphical source encodings for bounded pair and triple proposals.
///
/// This is a proposal accelerator only: final source admission independently
/// decodes every byte and checks actual guest execution.
fn pair_source_cells(profile: &ProfileDescriptor) -> Option<Vec<[u8; 6]>> {
    let opcodes = [b'o', b'j', b'p', b'*', profile.output_instruction(), b'v'];
    (0..DISTINCT_PAIR_PREFIX_PHASES + 48)
        .map(|position| {
            let mut encoded = [0u8; 6];
            let position = u32::try_from(position).ok()?;
            for (slot, &opcode) in encoded.iter_mut().zip(opcodes.iter()) {
                *slot = (33u8..=126).find(|&byte| {
                    malbolge::decode_profile_instruction(
                        u32::from(byte),
                        position,
                    ) == Some(opcode)
                })?;
            }
            Some(encoded)
        })
        .collect()
}

const fn pair_opcode_slot(operation: LinearOpcode) -> Option<usize> {
    match operation {
        LinearOpcode::NoOperation => Some(0),
        LinearOpcode::RelocateDataPointer => Some(1),
        LinearOpcode::CrazyData => Some(2),
        LinearOpcode::RotateData => Some(3),
        LinearOpcode::OutputByte => Some(4),
        LinearOpcode::Halt => Some(5),
        _ => None,
    }
}

/// Predict a bounded guest byte stream without full independent layout.
///
/// A disposable model filters candidates; it cannot authorize publication.
/// Both arithmetic operations and no-op data strides advance the guest data
/// pointer, while only guest arithmetic changes the accumulator.
fn proposed_output_stream<const N: usize>(
    operations: &[LinearOpcode],
    source_cells: &[[u8; 6]],
) -> Option<[u8; N]> {
    let source = operations
        .iter()
        .enumerate()
        .map(|(position, &operation)| {
            let slot = pair_opcode_slot(operation)?;
            source_cells.get(position).map(|cells| cells[slot])
        })
        .collect::<Option<Vec<_>>>()?;
    let memory_words =
        usize::try_from(current_profile().memory_words()).ok()?;
    let mut accumulator = 0u32;
    let mut data_pointer = 0usize;
    let mut relocated = false;
    let mut written = BTreeSet::new();
    let mut output = Vec::with_capacity(N);
    // Preview only untouched loader operands. The independent checker still
    // owns code encryption, relocation safety, and guest output admission.
    for (position, operation) in operations.iter().enumerate() {
        match operation {
            LinearOpcode::RelocateDataPointer => {
                // A final relocation cannot affect the output or the halt.
                if position == operations.len().saturating_sub(2) && relocated {
                    continue;
                }
                let operand = if !relocated && data_pointer < source.len() {
                    u32::from(*source.get(data_pointer)?)
                } else {
                    if written.contains(&data_pointer) {
                        return None;
                    }
                    layout::unwritten_loader_word(
                        &source,
                        data_pointer,
                        current_profile(),
                    )
                    .ok()?
                };
                let next = usize::try_from(operand).ok()?.saturating_add(1)
                    % memory_words;
                if next < source.len() {
                    return None;
                }
                data_pointer = next;
                relocated = true;
                continue;
            },
            LinearOpcode::CrazyData | LinearOpcode::RotateData => {
                if !relocated || !written.insert(data_pointer) {
                    return None;
                }
                let word = layout::unwritten_loader_word(
                    &source,
                    data_pointer,
                    current_profile(),
                )
                .ok()?;
                accumulator = if *operation == LinearOpcode::CrazyData {
                    malbolge::profile_crazy(word, accumulator, 15)
                } else {
                    word / 3 + (word % 3) * HIGH_TRIT_WEIGHT
                };
            },
            LinearOpcode::OutputByte => output.push(accumulator as u8),
            LinearOpcode::NoOperation | LinearOpcode::Halt => {},
            _ => return None,
        }
        data_pointer = data_pointer.saturating_add(1) % memory_words;
    }
    output.try_into().ok()
}

/// Independently admit and VM-replay one proposed guest output stream.
fn verified_output_stream_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    operations: &[LinearOpcode],
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    if proposed_output_stream(operations, source_cells) != Some(expected) {
        return None;
    }
    let layout = encode_linear_layout(profile, operations).ok()?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    let expected_writes = operations
        .iter()
        .filter(|operation| {
            matches!(
                operation,
                LinearOpcode::CrazyData | LinearOpcode::RotateData
            )
        })
        .count();
    if writes.len() != expected_writes
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != writes.len()
        || writes
            .iter()
            .any(|&position| position < layout.source().len() as u32)
    {
        return None;
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .ok()?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != expected
        {
            return None;
        }
    }
    Some(layout)
}

/// Reuse an unchanged guest accumulator for distinct source output effects.
///
/// The repeated value does not permit SSA aliasing: it eliminates a second
/// guest arithmetic *effect*, not either of the two guest output effects.
/// A second arithmetic write may be needed to compute the initial value.
fn verified_repeated_output_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    let arithmetic = [LinearOpcode::CrazyData, LinearOpcode::RotateData];
    for padding in 0..DISTINCT_PAIR_PREFIX_PHASES {
        for &operation in &arithmetic {
            let mut operations = vec![LinearOpcode::NoOperation; padding];
            operations.extend([LinearOpcode::RelocateDataPointer, operation]);
            operations.extend(repeat_n(LinearOpcode::OutputByte, N));
            operations.push(LinearOpcode::Halt);
            if let Some(layout) = verified_output_stream_layout(
                profile,
                &operations,
                expected,
                source_cells,
            ) {
                return Some(layout);
            }
        }
    }
    // A second write before the first output reaches values that a single
    // positional p/* operation cannot compute within the first 94 phases.
    for padding in 0..12 {
        for before in 0..=8 {
            for between in 0..=20 {
                for &first in &arithmetic {
                    for &second in &arithmetic {
                        let mut operations =
                            vec![LinearOpcode::NoOperation; padding];
                        operations.push(LinearOpcode::RelocateDataPointer);
                        operations.extend(repeat_n(
                            LinearOpcode::NoOperation,
                            before,
                        ));
                        operations.push(first);
                        operations.extend(repeat_n(
                            LinearOpcode::NoOperation,
                            between,
                        ));
                        operations.push(second);
                        operations
                            .extend(repeat_n(LinearOpcode::OutputByte, N));
                        operations.push(LinearOpcode::Halt);
                        if let Some(layout) = verified_output_stream_layout(
                            profile,
                            &operations,
                            expected,
                            source_cells,
                        ) {
                            return Some(layout);
                        }
                    }
                }
            }
        }
    }
    // The new, more expensive grammar is admitted only for one output.
    // Existing two/three-output grammars retain their original search cost.
    if N != 1 {
        return None;
    }
    verified_three_write_single_output_layout(
        profile,
        expected.first().copied()?,
        source_cells,
    )
}

/// Preview a three-write suffix from its immutable expanded memory tail.
///
/// All candidates with the same length end in the same encoded `OutputByte`
/// and `Halt`. The Malbolge memory recurrence depends only on those two cells,
/// and every arithmetic write advances to a fresh out-of-source address.
/// The independent layout and VM check still owns candidate acceptance.
fn preview_three_write_suffix(
    source_cells: &[[u8; 6]],
    memory_by_length: &mut BTreeMap<usize, Vec<u32>>,
    padding_and_strides: [usize; 4],
    operations: [LinearOpcode; 3],
) -> Option<u8> {
    let [padding, before, between_first, between_second] = padding_and_strides;
    let strides = [before, between_first, between_second];
    let source_length = strides.iter().copied().fold(
        padding.saturating_add(6),
        usize::saturating_add,
    );
    let output_cell = *source_cells
        .get(source_length.checked_sub(2)?)?
        .get(4)?;
    let halt_cell = *source_cells
        .get(source_length.checked_sub(1)?)?
        .get(5)?;
    let relocated = usize::from(*source_cells.get(padding)?.get(1)?);
    if relocated.saturating_add(1) < source_length
        || relocated.saturating_add(source_length) >= 4096
    {
        return None;
    }
    let last_write = strides.iter().copied().fold(
        relocated.saturating_add(3),
        usize::saturating_add,
    );
    let memory = memory_by_length.entry(source_length).or_insert_with(|| {
        let mut expanded = vec![0u32; source_length.saturating_sub(2)];
        expanded.extend([u32::from(output_cell), u32::from(halt_cell)]);
        expanded
    });
    while memory.len() <= last_write {
        let mut tail = memory.iter().rev();
        let latest = *tail.next()?;
        let previous = *tail.next()?;
        memory.push(malbolge::profile_crazy(previous, latest, 15));
    }
    let mut accumulator = 0u32;
    let mut address = relocated.saturating_add(1);
    for (operation, stride) in operations.into_iter().zip(strides) {
        address = address.saturating_add(stride);
        let word = *memory.get(address)?;
        accumulator = if operation == LinearOpcode::CrazyData {
            malbolge::profile_crazy(word, accumulator, 15)
        } else {
            word.div_euclid(3).saturating_add(
                word.rem_euclid(3).saturating_mul(HIGH_TRIT_WEIGHT),
            )
        };
        address = address.saturating_add(1);
    }
    u8::try_from(accumulator & 255).ok()
}

/// Enumerate a finite three-write guest grammar in stable lexicographic order.
/// Each proposal still requires independent layout and normative VM proof.
fn verified_three_write_single_output_layout(
    profile: &'static ProfileDescriptor,
    expected: u8,
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    const PATTERNS: usize = 12 * 9 * 21 * 21 * 8;
    // Every candidate ends in OutputByte/Halt. Guest memory expansion
    // past the source uses only those two encoded source cells, so it is
    // identical for candidate programs with the same source length.
    // This is only a disposable proposal filter: the selected candidate
    // still passes full independent layout and normative VM admission.
    let mut memory_by_source_length = BTreeMap::<usize, Vec<u32>>::new();
    for candidate in 0..PATTERNS {
        let mut index = candidate;
        let third = if index % 2 == 0 {
            LinearOpcode::CrazyData
        } else {
            LinearOpcode::RotateData
        };
        index /= 2;
        let second = if index % 2 == 0 {
            LinearOpcode::CrazyData
        } else {
            LinearOpcode::RotateData
        };
        index /= 2;
        let first = if index % 2 == 0 {
            LinearOpcode::CrazyData
        } else {
            LinearOpcode::RotateData
        };
        index /= 2;
        let between_second = index % 21;
        index /= 21;
        let between_first = index % 21;
        index /= 21;
        let before = index % 9;
        let padding = index / 9;
        if preview_three_write_suffix(
            source_cells,
            &mut memory_by_source_length,
            [padding, before, between_first, between_second],
            [first, second, third],
        ) != Some(expected)
        {
            continue;
        }
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.push(LinearOpcode::RelocateDataPointer);
        operations.extend(repeat_n(LinearOpcode::NoOperation, before));
        operations.push(first);
        operations.extend(repeat_n(LinearOpcode::NoOperation, between_first));
        operations.push(second);
        operations.extend(repeat_n(LinearOpcode::NoOperation, between_second));
        operations.push(third);
        operations.push(LinearOpcode::OutputByte);
        operations.push(LinearOpcode::Halt);
        if let Some(layout) = verified_output_stream_layout(
            profile,
            &operations,
            [expected],
            source_cells,
        ) {
            return Some(layout);
        }
    }
    None
}

/// Cache only the immutable loader-expanded data suffix of each source length.
///
/// Every admitted candidate ends with the same position-encoded output/halt
/// cells at a given length. The Malbolge crazy expansion depends only on the
/// two previous cells; the earlier code is never read through relocated data
/// addresses and is not part of this disposable proposal cache.
fn cached_output_tail<'a>(
    source_cells: &[[u8; 6]],
    memory_by_length: &'a mut BTreeMap<usize, Vec<u32>>,
    source_length: usize,
    last_address: usize,
) -> Option<&'a [u32]> {
    let output_cell = *source_cells
        .get(source_length.checked_sub(2)?)?
        .get(4)?;
    let halt_cell = *source_cells
        .get(source_length.checked_sub(1)?)?
        .get(5)?;
    let memory = memory_by_length.entry(source_length).or_insert_with(|| {
        let mut expanded = vec![0u32; source_length.saturating_sub(2)];
        expanded.extend([u32::from(output_cell), u32::from(halt_cell)]);
        expanded
    });
    while memory.len() <= last_address {
        let mut tail = memory.iter().rev();
        let latest = *tail.next()?;
        let previous = *tail.next()?;
        memory.push(malbolge::profile_crazy(previous, latest, 15));
    }
    Some(memory)
}

/// Preview three real outputs from four disjoint arithmetic writes.
///
/// One write precedes an output without emitting a byte. The deferred output
/// can follow the first, second or third write. Identical source lengths have
/// identical loader-expanded tails: the final two source cells encode `<` and
/// `v`, and all arithmetic writes are beyond the complete source. This is a
/// proposal filter, never a publishing authority.
fn preview_four_write_triple(
    source_cells: &[[u8; 6]],
    memory_by_length: &mut BTreeMap<usize, Vec<u32>>,
    geometry: [usize; 5],
    writes: [LinearOpcode; 4],
    deferred_output: usize,
    expected: [u8; 3],
) -> Option<[u8; 3]> {
    let [padding, before, between_first, between_second, between_third] =
        geometry;
    let strides = [before, between_first, between_second, between_third];
    let source_length = strides.iter().copied().fold(
        padding.saturating_add(9),
        usize::saturating_add,
    );
    let relocated = usize::from(*source_cells.get(padding)?.get(1)?);
    if relocated.saturating_add(1) < source_length
        || relocated.saturating_add(source_length) >= 4096
        || deferred_output >= 3
    {
        return None;
    }
    let memory = cached_output_tail(
        source_cells,
        memory_by_length,
        source_length,
        relocated.saturating_add(source_length),
    )?;
    let mut accumulator = 0u32;
    let mut address = relocated.saturating_add(1);
    let mut observed = [0; 3];
    let mut output_index = 0;
    for (index, (operation, stride)) in
        writes.into_iter().zip(strides).enumerate()
    {
        address = address.saturating_add(stride);
        let word = *memory.get(address)?;
        accumulator = match operation {
            LinearOpcode::CrazyData => {
                malbolge::profile_crazy(word, accumulator, 15)
            },
            LinearOpcode::RotateData => {
                word / 3 + (word % 3) * HIGH_TRIT_WEIGHT
            },
            _ => return None,
        };
        address = address.saturating_add(1);
        if index != deferred_output {
            observed[output_index] = accumulator as u8;
            if observed[output_index] != expected[output_index] {
                return None;
            }
            output_index += 1;
            address = address.saturating_add(1);
        }
    }
    Some(observed)
}

fn four_write_triple_operations(
    geometry: [usize; 5],
    writes: [LinearOpcode; 4],
    deferred_output: usize,
) -> Vec<LinearOpcode> {
    let [padding, before, between_first, between_second, between_third] =
        geometry;
    let mut operations = vec![LinearOpcode::NoOperation; padding];
    operations.push(LinearOpcode::RelocateDataPointer);
    for (index, (write, stride)) in writes
        .into_iter()
        .zip([before, between_first, between_second, between_third])
        .enumerate()
    {
        operations.extend(repeat_n(LinearOpcode::NoOperation, stride));
        operations.push(write);
        if index != deferred_output {
            operations.push(LinearOpcode::OutputByte);
        }
    }
    operations.push(LinearOpcode::Halt);
    operations
}

/// Search one additional real write at any of the first three output sites.
///
/// Candidates must still pass independent layout, out-of-source write
/// admission and normative guest VM replay on two different input streams.
fn verified_four_write_triple_layout(
    profile: &'static ProfileDescriptor,
    expected: [u8; 3],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    let mut memory_by_length = BTreeMap::<usize, Vec<u32>>::new();
    for padding in 0..2 {
        for before in 0..=1 {
            for between_first in 0..=2 {
                for between_second in 0..=8 {
                    for between_third in 0..=12 {
                        let geometry = [
                            padding, before, between_first, between_second,
                            between_third,
                        ];
                        for bits in 0usize..16 {
                            let mut writes = [LinearOpcode::CrazyData; 4];
                            for (bit, operation) in writes.iter_mut().enumerate() {
                                if bits & (1 << bit) != 0 {
                                    *operation = LinearOpcode::RotateData;
                                }
                            }
                            for deferred_output in 0..3 {
                                if preview_four_write_triple(
                                    source_cells,
                                    &mut memory_by_length,
                                    geometry,
                                    writes,
                                    deferred_output,
                                    expected,
                                ) != Some(expected) {
                                    continue;
                                }
                                let operations = four_write_triple_operations(
                                    geometry,
                                    writes,
                                    deferred_output,
                                );
                                if let Some(layout) = verified_output_stream_layout(
                                    profile, &operations, expected, source_cells,
                                ) {
                                    return Some(layout);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    None
}

/// The disposable four-write proposal has no authority to publish source.
#[derive(Clone, Copy)]
struct FourWriteQuadProposal {
    geometry: [usize; 5],
    writes: [LinearOpcode; 4],
    expected: [u8; 4],
}

/// Preview four real byte effects using four disjoint guest arithmetic writes.
///
/// The last source cells encode output and halt. Loader memory beyond the
/// source therefore depends only on total length; every candidate is still
/// independently re-admitted and executed before it can be published.
fn preview_four_write_quad(
    source_cells: &[[u8; 6]],
    memory_by_length: &mut BTreeMap<usize, Vec<u32>>,
    proposal: FourWriteQuadProposal,
) -> Option<[u8; 4]> {
    let FourWriteQuadProposal {
        geometry,
        writes,
        expected,
    } = proposal;
    let [
        padding,
        before,
        between_first,
        between_second,
        between_third,
    ] = geometry;
    let strides = [before, between_first, between_second, between_third];
    let source_length = strides
        .iter()
        .copied()
        .fold(padding.saturating_add(10), usize::saturating_add);
    let relocated = usize::from(*source_cells.get(padding)?.get(1)?);
    if relocated.saturating_add(1) < source_length
        || relocated.saturating_add(source_length) >= 4096
    {
        return None;
    }
    let memory = cached_output_tail(
        source_cells,
        memory_by_length,
        source_length,
        relocated.saturating_add(source_length),
    )?;
    let mut accumulator = 0u32;
    let mut address = relocated.saturating_add(1);
    let mut observed = [0; 4];
    for (((operation, stride), slot), expected_byte) in writes
        .into_iter()
        .zip(strides)
        .zip(&mut observed)
        .zip(expected)
    {
        address = address.saturating_add(stride);
        let word = *memory.get(address)?;
        accumulator = match operation {
            LinearOpcode::CrazyData => {
                malbolge::profile_crazy(word, accumulator, 15)
            },
            LinearOpcode::RotateData => word.div_euclid(3).saturating_add(
                word.rem_euclid(3).saturating_mul(HIGH_TRIT_WEIGHT),
            ),
            LinearOpcode::Halt
            | LinearOpcode::InputWord
            | LinearOpcode::JumpForward { .. }
            | LinearOpcode::NoOperation
            | LinearOpcode::SkippedDataByte { .. }
            | LinearOpcode::OutputByte
            | LinearOpcode::RelocateDataPointer => return None,
        };
        *slot = u8::try_from(accumulator & 255).ok()?;
        if *slot != expected_byte {
            return None;
        }
        // Every real output is an instruction, advancing the data pointer.
        address = address.saturating_add(2);
    }
    Some(observed)
}

fn four_write_quad_operations(
    geometry: [usize; 5],
    writes: [LinearOpcode; 4],
) -> Vec<LinearOpcode> {
    let [
        padding,
        before,
        between_first,
        between_second,
        between_third,
    ] = geometry;
    let mut operations = vec![LinearOpcode::NoOperation; padding];
    operations.push(LinearOpcode::RelocateDataPointer);
    for (write, stride) in writes.into_iter().zip([
        before,
        between_first,
        between_second,
        between_third,
    ]) {
        operations.extend(repeat_n(LinearOpcode::NoOperation, stride));
        operations.extend([write, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    operations
}

/// Search a bounded four-output grammar, not a hard-coded teaching stream.
///
/// A preview is only a filter. The chosen source must independently pass
/// layout admission, distinct out-of-source writes and normative VM replay.
fn verified_four_write_quad_layout(
    profile: &'static ProfileDescriptor,
    expected: [u8; 4],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    const PATTERNS: usize = 12 * 9 * 9 * 9 * 9 * 16;
    let mut memory_by_length = BTreeMap::<usize, Vec<u32>>::new();
    for candidate in 0..PATTERNS {
        let mut index = candidate;
        let bits = index.rem_euclid(16);
        index = index.div_euclid(16);
        let between_third = index.rem_euclid(9);
        index = index.div_euclid(9);
        let between_second = index.rem_euclid(9);
        index = index.div_euclid(9);
        let between_first = index.rem_euclid(9);
        index = index.div_euclid(9);
        let before = index.rem_euclid(9);
        let padding = index.div_euclid(9);
        let geometry = [
            padding,
            before,
            between_first,
            between_second,
            between_third,
        ];
        let mut writes = [LinearOpcode::CrazyData; 4];
        for (bit, operation) in writes.iter_mut().enumerate() {
            if bits & (1 << bit) != 0 {
                *operation = LinearOpcode::RotateData;
            }
        }
        if preview_four_write_quad(
            source_cells,
            &mut memory_by_length,
            FourWriteQuadProposal {
                geometry,
                writes,
                expected,
            },
        ) != Some(expected)
        {
            continue;
        }
        let operations = four_write_quad_operations(geometry, writes);
        if let Some(layout) = verified_output_stream_layout(
            profile,
            &operations,
            expected,
            source_cells,
        ) {
            return Some(layout);
        }
    }
    None
}

/// Compose two distinct source-proven bytes using real guest arithmetic.
///
/// A bounded search tries all 94 graphical prefix phases, two arithmetic
/// choices per output, and an additional bounded compound-write grammar.
/// Position-encoded source cells are cached only to accelerate proposals;
/// empty and nonempty input are independently replayed in the normative VM.
/// Search failure does not mean the requested byte pair is impossible in
/// Malbolge, only that this bounded linear grammar did not realize it.
///
/// # Errors
///
/// Refuses invalid source/SSA, mismatched profile, unsafe guest memory,
/// unachievable pairs in this grammar or any VM disagreement.
pub fn encode_distinct_literal_pair(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let [
        TernaryOperation::MaterializeU8 {
            result: first_id,
            scalar: first,
            ..
        },
        TernaryOperation::ByteOutput { value: emitted_first, .. },
        TernaryOperation::MaterializeU8 {
            result: second_id,
            scalar: second,
            ..
        },
        TernaryOperation::ByteOutput {
            value: emitted_second, ..
        },
        TernaryOperation::ReturnVoid { .. },
    ] = function.operations.as_slice()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if first_id != emitted_first
        || second_id != emitted_second
        || first_id == second_id
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let expected = [first.bits(), second.bits()];
    let source_cells = pair_source_cells(profile)
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
    if expected[0] == expected[1] {
        return verified_repeated_output_layout(profile, expected, &source_cells)
            .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    // Preserve already-published positional witnesses before broadening the
    // grammar. Every candidate still needs independent layout and VM proof.
    for padding in 0..DISTINCT_PAIR_PREFIX_PHASES {
        for initial in [LinearOpcode::CrazyData, LinearOpcode::RotateData] {
            for subsequent in
                [LinearOpcode::CrazyData, LinearOpcode::RotateData]
            {
                let mut operations = vec![LinearOpcode::NoOperation; padding];
                operations.extend([
                    LinearOpcode::RelocateDataPointer,
                    initial,
                    LinearOpcode::OutputByte,
                    subsequent,
                    LinearOpcode::OutputByte,
                    LinearOpcode::Halt,
                ]);
                if let Some(layout) = verified_output_stream_layout(
                    profile,
                    &operations,
                    expected,
                    &source_cells,
                ) {
                    return Ok(layout);
                }
            }
        }
    }
    // A bounded compound grammar admits one *additional* arithmetic write
    // before either output, with explicit data-pointer strides. The first
    // twelve phases and finite strides bound negative-case search cost.
    for padding in 0..12 {
        for before in 0..=8 {
            for between in 0..=20 {
                for initial in
                    [LinearOpcode::CrazyData, LinearOpcode::RotateData]
                {
                    for middle in
                        [LinearOpcode::CrazyData, LinearOpcode::RotateData]
                    {
                        for last in
                            [LinearOpcode::CrazyData, LinearOpcode::RotateData]
                        {
                            for double_first in [true, false] {
                                let mut operations =
                                    vec![LinearOpcode::NoOperation; padding];
                                operations
                                    .push(LinearOpcode::RelocateDataPointer);
                                operations.extend(repeat_n(
                                    LinearOpcode::NoOperation,
                                    before,
                                ));
                                operations.push(initial);
                                if double_first {
                                    operations.push(middle);
                                }
                                operations.push(LinearOpcode::OutputByte);
                                operations.extend(repeat_n(
                                    LinearOpcode::NoOperation,
                                    between,
                                ));
                                if !double_first {
                                    operations.push(middle);
                                }
                                operations.extend([
                                    last,
                                    LinearOpcode::OutputByte,
                                    LinearOpcode::Halt,
                                ]);
                                if let Some(layout) =
                                    verified_output_stream_layout(
                                        profile,
                                        &operations,
                                        expected,
                                        &source_cells,
                                    )
                                {
                                    return Ok(layout);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    search_output_stream::verified_source_scratch_output_layout(
        profile,
        expected,
        &source_cells,
    )
    .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)
}

/// Emits a nonzero `u8` one to thirty-three times using guest data operations.
///
/// Accepts one `MaterializeU8` with one to thirty-three same-SSA `ByteOutput`s
/// and `ReturnVoid` for the current profile. A bounded source-address-specific
/// sequence of no-ops, `j`, `*`, `<`, and `v` selects a loader-expanded
/// word and rotates it in the guest, never on the host. Separate exact
/// one-output witnesses use either `p` or two consecutive `*` operations;
/// they do not authorize other bytes or output counts. Every chosen
/// witness is re-executed in the independent VM before publication.
///
/// # Errors
///
/// Refuses invalid shape/provenance, foreign profiles, unsupported literals,
/// overlapping data/code, wrong output, guest input, or nontermination.
pub fn encode_rotated_byte_literal(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, effects)) =
        function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::MaterializeU8 { result, scalar, .. }, outputs)) =
        effects.split_first()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if outputs.is_empty()
        || outputs.iter().any(|effect| {
            !matches!(effect, TernaryOperation::ByteOutput { value, .. } if value == result)
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let selected = literal_output_witness(scalar.bits(), outputs.len());
    if selected.is_none() && outputs.len() == 1 {
        // The finite historical table is not an exhaustive byte language.
        // Search actual guest arithmetic before rejecting a source constant.
        let source_cells = pair_source_cells(profile)
            .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
        return verified_repeated_output_layout(
            profile,
            [scalar.bits()],
            &source_cells,
        )
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let (padding, arithmetic) =
        selected.ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
    let mut operations = vec![LinearOpcode::NoOperation; padding];
    operations.push(LinearOpcode::RelocateDataPointer);
    operations.extend_from_slice(arithmetic);
    operations.extend(repeat_n(LinearOpcode::OutputByte, outputs.len()));
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let mut vm =
        ProfileMachine::from_source(profile, layout.source(), Vec::new())
            .map_err(|_error| ByteEchoBridgeError::UnsupportedEffectTrace)?;
    if !matches!(vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
        || vm.input_consumed() != 0
        || vm.output().len() != outputs.len()
        || vm.output().iter().any(|actual| *actual != scalar.bits())
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    Ok(layout)
}

/// Emit four source-distinct bytes from four real guest arithmetic writes.
///
/// The historical `T=4>` witness is retained. Other streams use a bounded
/// positional `p`/`*` grammar, independently validated and guest-VM replayed.
/// The finite search does not establish arbitrary byte-stream support.
///
/// # Errors
///
/// Rejects unproved constants, stale SSA, profile drift, unsafe layout or
/// byte streams that lack a verified real-VM guest within the search bounds.
pub fn encode_distinct_literal_quad(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 4 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    let mut expected = [0u8; 4];
    for (slot, [constant, output]) in expected.iter_mut().zip(pairs) {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value || !ids.insert(*result) {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
        *slot = scalar.bits();
    }
    if expected == *b"T=4>" {
        let mut operations = vec![LinearOpcode::NoOperation; 11];
        operations.push(LinearOpcode::RelocateDataPointer);
        for _ in 0..4_usize {
            operations
                .extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
        }
        operations.push(LinearOpcode::Halt);
        return verified_output_stream_layout(
            profile,
            &operations,
            expected,
            &pair_source_cells(profile)
                .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?,
        )
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let source_cells = pair_source_cells(profile)
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
    search_output_stream::verified_state_space_output_layout(
        profile, expected, &source_cells,
    )
    .or_else(|| {
        verified_four_write_quad_layout(profile, expected, &source_cells)
    })
    .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)
}

/// Emit five source-distinct bytes through independently verified guest code.
///
/// The historical five-write `Q"\x1b79` source remains pinned. A separate
/// bounded search can realize an initial zero before guest data relocation,
/// followed by four arithmetic-derived output bytes; every proposed source
/// is independently re-admitted and executed by the normative VM.
///
/// # Errors
///
/// Rejects arbitrary five-byte traces, stale SSA, foreign profiles and
/// normative VM disagreement before the source can be published.
pub fn encode_distinct_literal_quint(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 5 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    let mut expected = [0u8; 5];
    for (slot, [constant, output]) in expected.iter_mut().zip(pairs) {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value || !ids.insert(*result) {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
        *slot = scalar.bits();
    }
    if expected != *b"Q\"\x1b79" {
        let cells = pair_source_cells(profile)
            .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
        // Keep the established leading-zero search order. Other streams
        // may need additional live relocations even when the first guest
        // accumulator is nonzero. The verifier, not this byte gate,
        // decides whether a proposed source can be published.
        let verified = if expected[0] == 0 {
            search_output_stream::verified_state_space_output_layout(
                profile, expected, &cells,
            )
        } else {
            search_output_stream::verified_four_relocation_write_layout(
                profile, expected, &cells,
            )
            .or_else(|| {
                search_output_stream::verified_state_space_output_layout(
                    profile, expected, &cells,
                )
            })
        };
        return verified.ok_or(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut operations = vec![LinearOpcode::NoOperation; 11];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..5 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 5
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 5
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"Q\"\x1b79"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit one independently VM-witnessed six-distinct-byte C trace.
///
/// The exact observed guest program performs six separate relocated `p`
/// writes, followed by six independent output instructions. One byte is ESC;
/// this is a binary output contract, not a text literal convention.
///
/// # Errors
///
/// Rejects arbitrary six-byte traces, stale SSA, foreign profiles and
/// normative VM disagreement before the source can be published.
pub fn encode_distinct_literal_six(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 6 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    let mut expected = [0u8; 6];
    for (slot, [constant, output]) in expected.iter_mut().zip(pairs) {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value || !ids.insert(*result) {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
        *slot = scalar.bits();
    }
    if expected != *b"Q\x1cO\x1dP\x1b" {
        // The initial accumulator is zero, but relocated guest arithmetic
        // can produce a nonzero first byte and later emit an interior zero.
        // Only source-independent bounded proposals independently decoded
        // and replayed by the normative VM can pass this path.
        let cells = pair_source_cells(profile)
            .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
        return search_output_stream::verified_state_space_output_layout(
            profile, expected, &cells,
        )
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut operations = vec![LinearOpcode::NoOperation; 1];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0usize..6 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 6
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 6
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"Q\x1cO\x1dP\x1b"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit one independently VM-witnessed seven-distinct-byte C trace.
///
/// The exact observed guest program performs seven separate relocated `p`
/// writes and seven output instructions. Three emitted bytes are control
/// codes; this is a binary output contract, not a text literal convention.
///
/// # Errors
///
/// Rejects arbitrary seven-byte traces, stale SSA, foreign profiles and
/// normative VM disagreement before the source can be published.
pub fn encode_distinct_literal_seven(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 7 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || scalar.bits() != b"6>5\x02T\x1f\x18"[index]
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 5];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0usize..7 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 7
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 7
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"6>5\x02T\x1f\x18"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit one independently VM-witnessed eight-distinct-byte C trace.
///
/// The guest executes seven relocated `p` writes, one relocated `*` write,
/// and eight output instructions. Three output bytes are control codes;
/// this is a binary output contract, not a text literal convention.
///
/// # Errors
///
/// Rejects arbitrary eight-byte traces, stale SSA, foreign profiles and
/// normative VM disagreement before the source can be published.
pub fn encode_distinct_literal_eight(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 8 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || scalar.bits() != b"S \x17<6\x01R\x06"[index]
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 3];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0usize..7 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.extend([LinearOpcode::RotateData, LinearOpcode::OutputByte]);
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 8
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 8
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"S \x17<6\x01R\x06"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit one independently VM-witnessed nine-distinct-byte C trace.
///
/// The guest executes eight relocated `p` writes, one relocated `*` write,
/// and nine output instructions. Several output bytes are outside ASCII;
/// this is a binary output contract, not a text literal convention.
///
/// # Errors
///
/// Rejects arbitrary nine-byte traces, stale SSA, foreign profiles and
/// normative VM disagreement before the source can be published.
pub fn encode_distinct_literal_nine(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 9 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || scalar.bits() != b"T=\x8d\xd1\xc0\xb4\xbf\xd2\xa2"[index]
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 1];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..9 {
        operations.extend([
            if index == 2 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 9
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 9
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"T=\x8d\xd1\xc0\xb4\xbf\xd2\xa2"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit one independently VM-witnessed ten-distinct-byte C trace.
///
/// The guest executes nine relocated `p` writes, one relocated `*` write,
/// and ten output instructions. Several output bytes are outside ASCII;
/// this is a binary output contract, not a text literal convention.
///
/// # Errors
///
/// Rejects arbitrary ten-byte traces, stale SSA, foreign profiles and
/// normative VM disagreement before the source can be published.
pub fn encode_distinct_literal_ten(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 10 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || scalar.bits() != b"Q\"\xfd\xce\xa5\x98\xba\xb6\x87\xcb"[index]
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 1];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..10 {
        operations.extend([
            if index == 2 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 10
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 10
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"Q\"\xfd\xce\xa5\x98\xba\xb6\x87\xcb"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit one independently VM-witnessed eleven-distinct-byte C trace.
///
/// The guest executes ten relocated `p` writes, one relocated `*` write,
/// and eleven output instructions. Several output bytes are outside ASCII;
/// this is a binary output contract, not a text literal convention.
///
/// # Errors
///
/// Rejects arbitrary eleven-byte traces, stale SSA, foreign profiles and
/// normative VM disagreement before the source can be published.
pub fn encode_distinct_literal_eleven(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 11 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || scalar.bits() != b"P\x1d\x1a6\x05\xb4\xba\xb3\x84\xcf\x9e"[index]
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = Vec::new();
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..11 {
        operations.extend([
            if index == 4 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 11
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 11
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"P\x1d\x1a6\x05\xb4\xba\xb3\x84\xcf\x9e"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit twelve source-distinct bytes using independently verified guest code.
///
/// The historical positional witness is retained. Other twelve-byte traces
/// use a bounded crazy/rotate search with early byte-prefix pruning; every
/// proposal must still pass disjoint-write admission and normative VM replay.
/// This finite straight-line grammar cannot emit arbitrary byte streams.
///
/// # Errors
///
/// Rejects unproved SSA, foreign profiles, unwitnessed guest bytes, unsafe
/// layouts or normative VM disagreement before publication.
pub fn encode_distinct_literal_twelve(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 12 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    let mut expected = [0u8; 12];
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value || !ids.insert(*result) {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
        expected[index] = scalar.bits();
    }
    if expected != *b"Q748\xfb\xce\x9f\x98\xb8\xb4\x83\xcd" {
        let cells = pair_source_cells(profile)
            .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
        // The source-scratch grammar can prove compound C byte streams
        // without exploring the much larger relocated-tail state space.
        // Every proposal still receives independent positional/VM proof.
        return search_output_stream::verified_variable_source_scratch_layout(
            profile, expected,
        )
        .or_else(|| {
            search_output_stream::verified_straight_write_output_layout(
                profile, expected, &cells,
            )
        })
        .or_else(|| {
            search_output_stream::verified_short_output_layout(
                profile, expected, &cells,
            )
        })
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut operations = vec![LinearOpcode::NoOperation];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..12 {
        operations.extend([
            if index == 4 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 12
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 12
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"Q748\xfb\xce\x9f\x98\xb8\xb4\x83\xcd"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven thirteen-distinct-byte guest trace.
///
/// Twelve relocated crazy writes and one rotate compute real binary output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_thirteen(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 13 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"BC0\x16T\x09\xbf\xc6\xc8\x87\xe3\xab\xa4"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..13 {
        operations.extend([
            if index == 5 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 13
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 13
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"BC0\x16T\x09\xbf\xc6\xc8\x87\xe3\xab\xa4"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven fourteen-distinct-byte guest trace.
///
/// Twelve relocated crazy writes and two rotates compute real binary output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_fourteen(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 14 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"YE,HS\x17LO=@[1\x194".get(index).copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..14 {
        operations.extend([
            if index == 5 || index == 12 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 14
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 14
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"YE,HS\x17LO=@[1\x194"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven fifteen-distinct-byte guest trace.
///
/// Thirteen relocated crazy writes and two rotates compute real binary output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_fifteen(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 15 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"Q.\x198>\x89\xd2\xad\xa3\xb7\xc8\x88\x08\xd5\xc6"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..15 {
        operations.extend([
            if index == 5 || index == 12 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 15
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 15
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output()
                != b"Q.\x198>\x89\xd2\xad\xa3\xb7\xc8\x88\x08\xd5\xc6"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven sixteen-distinct-byte guest trace.
///
/// Thirteen relocated crazy writes and three rotates compute real binary
/// output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_sixteen(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 16 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"?I6\x13Z\x0a\xba\xb3\xc3\x86\xcc\xaa\x01\x07\xd5\xc5"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..16 {
        operations.extend([
            if index == 5 || index == 12 || index == 13 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 16
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 16
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output()
                != b"?I6\x13Z\x0a\xba\xb3\xc3\x86\xcc\xaa\x01\x07\xd5\xc5"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven seventeen-distinct-byte guest trace.
///
/// Fourteen relocated crazy writes and three rotates compute real binary
/// output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_seventeen(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 17 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"Y?,HP\x1b\x182\x15MK;B\x0fD0\x17".get(index).copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..17 {
        operations.extend([
            if index == 6 || index == 8 || index == 13 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 17
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 17
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"Y?,HP\x1b\x182\x15MK;B\x0fD0\x17"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven eighteen-distinct-byte guest trace.
///
/// Fifteen relocated crazy writes and three rotates compute real binary output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_eighteen(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 18 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x54\x22\x19\x3e\x38\x03\x09\xdd\x87\xd1\xa5\x99\xbf\x08\xc7\xc6\xc2\x91"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..18 {
        operations.extend([
            if index == 6 || index == 8 || index == 13 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 18
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 18
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output()
                != b"\x54\x22\x19\x3e\x38\x03\x09\xdd\x87\xd1\xa5\x99\xbf\x08\xc7\xc6\xc2\x91"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven nineteen-distinct-byte guest trace.
///
/// Sixteen relocated crazy writes and three rotates compute real binary output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_nineteen(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 19 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"S!\x1a<8\x03\x17U\x0eI+\x10F\x16@L:\x19X"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::RelocateDataPointer];
    for index in 0usize..19 {
        operations.extend([
            if index == 6 || index == 8 || index == 13 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 19
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 19
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"S!\x1a<8\x03\x17U\x0eI+\x10F\x16@L:\x19X"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven twenty-distinct-byte guest trace.
///
/// Seventeen relocated crazy writes and three rotates compute real binary
/// output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_twenty(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 20 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x3e\x14\x35\x12\x3f\x0a\xa4\x9c\xad\xa3\x1a\xa8\xa2\x95\xab\x9f\x98\x1d\xac\xae"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 12];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..20 {
        operations.extend([
            if index == 6 || index == 10 || index == 17 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 20
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 20
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x3e\x14\x35\x12\x3f\x0a\xa4\x9c\xad\xa3\x1a\xa8\xa2\x95\xab\x9f\x98\x1d\xac\xae"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven twenty-one-distinct-byte guest trace.
///
/// Eighteen relocated crazy writes and three rotates compute real binary
/// output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_twenty_one(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 21 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x41\x0e\x3b\x0f\x3f\x0a\x40\x8e\x26\x92\x27\x96\x22\x97\x8d\x15\x31\x18\x35\x1a\x2f"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 15];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..21 {
        operations.extend([
            if index == 7 || index == 14 || index == 15 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::NoOperation);
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 21
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 21
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x41\x0e\x3b\x0f\x3f\x0a\x40\x8e\x26\x92\x27\x96\x22\x97\x8d\x15\x31\x18\x35\x1a\x2f"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven twenty-two-distinct-byte guest trace.
///
/// Twenty relocated crazy writes and two rotates compute real binary output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_twenty_two(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 22 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x39\x16\x37\x05\x41\x0c\x30\x8e\x24\x9f\x1b\xa0\x23\x97\x15\x28\x27\x29\x14\x32\x1e\x1f"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 10];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..22 {
        operations.extend([
            if index == 7 || index == 14 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::NoOperation);
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 22
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 22
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x39\x16\x37\x05\x41\x0c\x30\x8e\x24\x9f\x1b\xa0\x23\x97\x15\x28\x27\x29\x14\x32\x1e\x1f"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven twenty-three-distinct-byte guest trace.
///
/// Twenty relocated crazy writes and three rotates compute real binary output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_twenty_three(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 23 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x42\x0e\x2f\x17\x39\x04\x8e\x24\x9f\x1b\xa0\x23\x97\x15\x28\x27\x29\x14\x32\x1e\x8b\x26\x92"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..23 {
        operations.extend([
            if index == 6 || index == 13 || index == 20 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::NoOperation);
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 23
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 23
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x42\x0e\x2f\x17\x39\x04\x8e\x24\x9f\x1b\xa0\x23\x97\x15\x28\x27\x29\x14\x32\x1e\x8b\x26\x92"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven twenty-four-distinct-byte guest trace.
///
/// Twenty-one relocated crazy writes and three rotates compute real binary
/// output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_twenty_four(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 24 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x3e\x0b\x2c\x12\x36\x01\x3d\x95\x0f\x9d\x17\x8b\x21\x93\x92\x20\x94\x0e\x9b\x18\x8a\x1c\x2f\x23"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 21];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..24 {
        operations.extend([
            if index == 7 || index == 14 || index == 21 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::NoOperation);
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 24
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 24
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x3e\x0b\x2c\x12\x36\x01\x3d\x95\x0f\x9d\x17\x8b\x21\x93\x92\x20\x94\x0e\x9b\x18\x8a\x1c\x2f\x23"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven twenty-five-distinct-byte guest trace.
///
/// Twenty-two relocated crazy writes and three rotates compute real binary
/// output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_twenty_five(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 25 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 26];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..25 {
        operations.extend([
            if index == 7 || index == 14 || index == 21 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend(repeat_n(LinearOpcode::NoOperation, 27));
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 25
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 25
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven twenty-six-distinct-byte guest trace.
///
/// Twenty-three relocated crazy writes and three rotates compute real binary
/// output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_twenty_six(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 26 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 26];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..26 {
        operations.extend([
            if index == 7 || index == 14 || index == 21 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend(repeat_n(LinearOpcode::NoOperation, 25));
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 26
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 26
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven twenty-seven-distinct-byte guest trace.
///
/// Twenty-four relocated crazy writes and three rotates compute real binary
/// output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_twenty_seven(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 27 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 26];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..27 {
        operations.extend([
            if index == 7 || index == 14 || index == 21 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend(repeat_n(LinearOpcode::NoOperation, 23));
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 27
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 27
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit the exact source-proven twenty-eight-distinct-byte guest trace.
///
/// Twenty-five relocated crazy writes and three rotates compute real binary
/// output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_twenty_eight(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 28 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d\xab"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 26];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..28 {
        operations.extend([
            if index == 7 || index == 14 || index == 21 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend(repeat_n(LinearOpcode::NoOperation, 21));
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 28
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 28
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d\xab"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Admit the exact twenty-nine-byte ternary literal trace to a verified guest.
///
/// Twenty-five relocated crazy writes and four rotates compute distinct VM
/// output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_twenty_nine(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 29 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x87\xb7\xbc\xb1\x8a\xce\x9f\x9c\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d\xab\x33\x3d\x39\x05\x53\x23\x1b"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 9];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..29 {
        if index == 1 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index == 0 || index == 8 || index == 15 || index == 22 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend(repeat_n(LinearOpcode::NoOperation, 35));
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 29
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 29
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x87\xb7\xbc\xb1\x8a\xce\x9f\x9c\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d\xab\x33\x3d\x39\x05\x53\x23\x1b"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Admit the exact thirty-byte ternary literal trace to a verified guest.
///
/// Twenty-six relocated crazy writes and four rotates compute distinct
/// guest output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_thirty(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 30 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x39\xa8\x07\xda\x99\xdd\xa3\xcf\xa7\xd9\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 34];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..30 {
        if index == 3 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index == 1 || index == 10 || index == 17 || index == 24 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 30
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 30
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x39\xa8\x07\xda\x99\xdd\xa3\xcf\xa7\xd9\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Admit the exact thirty-one-byte ternary literal trace to a verified guest.
///
/// Twenty-six relocated crazy writes and five rotates compute distinct
/// guest output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_thirty_one(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 31 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x3f\x0b\x92\x21\x94\x0e\x9d\x1c\x34\x27\x2b\x25\x35\x1d\x33\x11\xa8\xa2\x95\xab\x9f\x98\x14\xac\xae\xa4\x9b\xa5\xad\xa3\x9c"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..31 {
        if index == 8 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 2 | 7 | 15 | 22 | 26) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 31
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 31
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x3f\x0b\x92\x21\x94\x0e\x9d\x1c\x34\x27\x2b\x25\x35\x1d\x33\x11\xa8\xa2\x95\xab\x9f\x98\x14\xac\xae\xa4\x9b\xa5\xad\xa3\x9c"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Admit the exact thirty-two-byte ternary literal trace to a verified guest.
///
/// Twenty-nine relocated crazy writes and three rotates compute distinct
/// guest output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_thirty_two(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 32 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x41\x17\x32\x18\x50\x23\x5c\x27\x4b\x34\x4f\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 30];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..32 {
        if index == 4 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 11 | 18 | 25) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 32
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 32
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x41\x17\x32\x18\x50\x23\x5c\x27\x4b\x34\x4f\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Admit the exact thirty-three-byte ternary literal trace to a verified guest.
///
/// Thirty relocated crazy writes and three rotates compute distinct
/// guest output.
///
/// # Errors
///
/// Rejects unproved effects, wrong profiles, altered SSA or VM disagreement.
pub fn encode_distinct_literal_thirty_three(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 33 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x39\x19\x34\x08\x41\x0c\x5c\x32\x4d\x33\x5a\x25\x5b\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 28];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..33 {
        if index == 6 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 13 | 20 | 27) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 33
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 33
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x39\x19\x34\x08\x41\x0c\x5c\x32\x4d\x33\x5a\x25\x5b\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Bind the exact thirty-four source-proven binary bytes to guest arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_thirty_four(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 34 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x3f\x11\x2c\x14\x39\x04\xa8\x50\x36\x3d\x42\x44\x2f\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 26];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..34 {
        if index == 7 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 6 | 13 | 20 | 27) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 34
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 34
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x3f\x11\x2c\x14\x39\x04\xa8\x50\x36\x3d\x42\x44\x2f\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Bind the exact thirty-five source-proven binary bytes to guest arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_thirty_five(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 35 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 24];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..35 {
        if index == 8 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 0 | 7 | 14 | 21 | 28) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 35
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 35
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Bind the exact thirty-six source-proven binary bytes to guest arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_thirty_six(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 36 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x39\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x4b\x34\x4f\x23\x5c\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 22];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..36 {
        if index == 10 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 1 | 8 | 15 | 22 | 29) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 36
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 36
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x39\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x4b\x34\x4f\x23\x5c\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Bind the exact thirty-seven source-proven binary bytes to guest arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_thirty_seven(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 37 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x3f\x11\x2c\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x4b\x34\x4f\x23\x5c\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 20];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..37 {
        if index == 12 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 3 | 10 | 17 | 24 | 31) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 37
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 37
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x3f\x11\x2c\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x4b\x34\x4f\x23\x5c\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Bind the exact thirty-eight source-proven binary bytes to guest arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_thirty_eight(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 38 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x41\x17\x32\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 18];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..38 {
        if index == 11 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 3 | 10 | 17 | 24 | 31) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 38
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 38
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x41\x17\x32\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Bind the exact thirty-nine source-proven binary bytes to guest arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_thirty_nine(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 39 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x5c\x32\x26\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 15];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..39 {
        if index == 2 || index == 18 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 3 | 10 | 17 | 24 | 31 | 38) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 39
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 39
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x5c\x32\x26\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Bind the exact forty source-independent binary bytes to guest arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_forty(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 40 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 14];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..40 {
        if index == 15 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 0 | 7 | 14 | 21 | 28 | 35) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 40
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 40
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Bind the exact forty-one source-independent binary bytes to guest
/// arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_forty_one(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 41 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\x5a\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 11];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..41 {
        if index == 1 || index == 16 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 1 | 8 | 15 | 22 | 29 | 36) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 41
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 41
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\x5a\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Bind the exact forty-two source-independent binary bytes to guest
/// arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_forty_two(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 42 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != b"\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
                    .get(index)
                    .copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 9];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..42 {
        if index == 0 || index == 15 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 0 | 7 | 14 | 21 | 28 | 35) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 42
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 42
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != b"\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

const FORTY_THREE_LITERAL_OUTPUT: [u8; 43] = [
    81, 46, 79, 29, 26, 47, 27, 28, 36, 38, 17, 167, 5, 184, 252, 182, 64, 45,
    73, 52, 56, 62, 146, 228, 164, 226, 174, 218, 172, 8, 213, 171, 221, 162,
    222, 170, 11, 217, 156, 227, 163, 210, 173,
];

/// Bind the exact forty-three source-independent binary bytes to guest
/// arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_forty_three(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 43 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != FORTY_THREE_LITERAL_OUTPUT.get(index).copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 10];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..43 {
        if index == 4 || index == 16 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 11 | 22 | 29 | 36) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 43
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 43
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != FORTY_THREE_LITERAL_OUTPUT
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

const FORTY_FOUR_LITERAL_OUTPUT: [u8; 44] = [
    90, 38, 71, 11, 62, 9, 45, 19, 52, 165, 6, 175, 243, 168, 47, 17, 65, 15,
    48, 25, 55, 8, 77, 50, 78, 31, 87, 41, 68, 10, 212, 153, 221, 160, 204,
    170, 211, 7, 213, 145, 222, 161, 220, 171,
];

/// Bind the exact forty-four source-independent binary bytes to guest
/// arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_forty_four(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 44 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != FORTY_FOUR_LITERAL_OUTPUT.get(index).copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 11];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..44 {
        if index == 3 || index == 22 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 9 | 13 | 14 | 29 | 37 | 39) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 44
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 44
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != FORTY_FOUR_LITERAL_OUTPUT
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

const FORTY_FIVE_LITERAL_OUTPUT: [u8; 45] = [
    81, 62, 53, 56, 84, 31, 78, 135, 209, 165, 153, 9, 8, 199, 198, 194, 145,
    225, 167, 172, 152, 219, 155, 160, 183, 191, 124, 181, 44, 203, 18, 180,
    248, 202, 14, 149, 45, 171, 51, 61, 57, 5, 83, 35, 27,
];

/// Bind the exact forty-five source-independent binary bytes to guest
/// arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_forty_five(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 45 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != FORTY_FIVE_LITERAL_OUTPUT.get(index).copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 11];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..45 {
        if index == 20 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 7 | 11 | 12 | 27 | 31 | 38) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::NoOperation);
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 45
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 45
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
            || vm.output() != FORTY_FIVE_LITERAL_OUTPUT
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

const FORTY_SIX_LITERAL_OUTPUT: [u8; 46] = [
    84, 34, 79, 35, 83, 30, 9, 8, 226, 171, 221, 126, 192, 125, 186, 129, 188,
    123, 42, 16, 48, 14, 47, 17, 45, 163, 255, 167, 0, 162, 1, 166, 252, 207,
    165, 206, 159, 210, 161, 204, 144, 227, 174, 225, 173, 228,
];

/// Bind the exact forty-six source-independent binary bytes to guest
/// arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_forty_six(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 46 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != FORTY_SIX_LITERAL_OUTPUT.get(index).copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 10];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..46 {
        if index == 11 || index == 33 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 6 | 7 | 18 | 25 | 29 | 40) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 46
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 46
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let expected_steps = operations.len();
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(expected_steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == expected_steps)
            || vm.input_consumed() != 0
            || vm.output() != FORTY_SIX_LITERAL_OUTPUT
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

/// Emit three source-proven bytes with guest arithmetic and output effects.
///
/// Three separate `MaterializeU8`/`ByteOutput` SSA pairs and a void return
/// select a bounded positional `p`/`*` layout with independently replayed
/// guest output. Search failure does not prove the bytes unrealizable.
///
/// # Errors
///
/// Rejects foreign profiles, unproved triples, stale/duplicate SSA or guest
/// output that fails real-VM verification.
pub fn encode_distinct_literal_triple(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let [
        first,
        first_output,
        second,
        second_output,
        third,
        third_output,
        TernaryOperation::ReturnVoid { .. },
    ] = function.operations.as_slice()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let triples = [
        (first, first_output),
        (second, second_output),
        (third, third_output),
    ];
    let mut bytes = Vec::with_capacity(3);
    let mut ids = BTreeSet::new();
    for (constant, output) in triples {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value || !ids.insert(*result) {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
        bytes.push(scalar.bits());
    }
    let expected: [u8; 3] = bytes
        .try_into()
        .map_err(|_error| ByteEchoBridgeError::UnsupportedEffectTrace)?;
    // Three source-distinct effects with the same value can observe one
    // unchanged guest accumulator. Only the source SSA identities are
    // independent; repeating the output instruction is not a second write.
    if expected[0] == expected[1] && expected[1] == expected[2] {
        let source_cells = pair_source_cells(profile)
            .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
        return verified_repeated_output_layout(
            profile,
            expected,
            &source_cells,
        )
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    // An unchanged accumulator can be output twice without a second data
    // write, while source SSA definitions stay distinct. This is a genuine
    // guest output effect, not a host-side stream duplication.
    if expected[0] == expected[1] || expected[1] == expected[2] {
        let repeat_first = expected[0] == expected[1];
        if expected[0] == expected[2] {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
        let source_cells = pair_source_cells(profile)
            .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
        for padding in 0..12 {
            for before in 0..=12 {
                for between in 0..=12 {
                    for first in
                        [LinearOpcode::CrazyData, LinearOpcode::RotateData]
                    {
                        for second in
                            [LinearOpcode::CrazyData, LinearOpcode::RotateData]
                        {
                            let mut operations =
                                vec![LinearOpcode::NoOperation; padding];
                            operations.push(LinearOpcode::RelocateDataPointer);
                            operations.extend(repeat_n(
                                LinearOpcode::NoOperation,
                                before,
                            ));
                            operations
                                .extend([first, LinearOpcode::OutputByte]);
                            if repeat_first {
                                operations.push(LinearOpcode::OutputByte);
                            }
                            operations.extend(repeat_n(
                                LinearOpcode::NoOperation,
                                between,
                            ));
                            operations
                                .extend([second, LinearOpcode::OutputByte]);
                            if !repeat_first {
                                operations.push(LinearOpcode::OutputByte);
                            }
                            operations.push(LinearOpcode::Halt);
                            if let Some(layout) = verified_output_stream_layout(
                                profile,
                                &operations,
                                expected,
                                &source_cells,
                            ) {
                                return Ok(layout);
                            }
                        }
                    }
                }
            }
        }
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    // Retain the exact, published legacy source phases before broadening
    // the independently verified layout grammar.
    if let Some((_, padding)) = DISTINCT_LITERAL_TRIPLE_CRAZY_WITNESSES
        .iter()
        .find(|(candidate, _)| *candidate == expected)
    {
        let mut operations = vec![LinearOpcode::NoOperation; *padding];
        operations.extend([
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::OutputByte,
            LinearOpcode::CrazyData,
            LinearOpcode::OutputByte,
            LinearOpcode::CrazyData,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ]);
        return encode_linear_layout(profile, &operations)
            .map_err(ByteEchoBridgeError::Layout);
    }
    let source_cells = pair_source_cells(profile)
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
    let arithmetic = [LinearOpcode::CrazyData, LinearOpcode::RotateData];
    // First search all 94 graphical phases with three independent writes.
    // The fast accumulator model is only a proposal filter; a matched
    // source is re-admitted and replayed on two normative VM inputs.
    for padding in 0..DISTINCT_PAIR_PREFIX_PHASES {
        for &first in &arithmetic {
            for &second in &arithmetic {
                for &third in &arithmetic {
                    let mut operations =
                        vec![LinearOpcode::NoOperation; padding];
                    operations.extend([
                        LinearOpcode::RelocateDataPointer,
                        first,
                        LinearOpcode::OutputByte,
                        second,
                        LinearOpcode::OutputByte,
                        third,
                        LinearOpcode::OutputByte,
                        LinearOpcode::Halt,
                    ]);
                    if let Some(layout) = verified_output_stream_layout(
                        profile,
                        &operations,
                        expected,
                        &source_cells,
                    ) {
                        return Ok(layout);
                    }
                }
            }
        }
    }
    // A finite stride grammar changes the three genuine loader-resident
    // operands without inserting new host-computed output effects. The
    // explicit bounds make unsuccessful searches deterministic and finite.
    for padding in 0..12 {
        for before in 0..=8 {
            for between_first in 0..=8 {
                for between_second in 0..=8 {
                    for &first in &arithmetic {
                        for &second in &arithmetic {
                            for &third in &arithmetic {
                                let mut operations =
                                    vec![LinearOpcode::NoOperation; padding];
                                operations
                                    .push(LinearOpcode::RelocateDataPointer);
                                operations.extend(repeat_n(
                                    LinearOpcode::NoOperation,
                                    before,
                                ));
                                operations
                                    .extend([first, LinearOpcode::OutputByte]);
                                operations.extend(repeat_n(
                                    LinearOpcode::NoOperation,
                                    between_first,
                                ));
                                operations
                                    .extend([second, LinearOpcode::OutputByte]);
                                operations.extend(repeat_n(
                                    LinearOpcode::NoOperation,
                                    between_second,
                                ));
                                operations.extend([
                                    third,
                                    LinearOpcode::OutputByte,
                                    LinearOpcode::Halt,
                                ]);
                                if let Some(layout) =
                                    verified_output_stream_layout(
                                        profile,
                                        &operations,
                                        expected,
                                        &source_cells,
                                    )
                                {
                                    return Ok(layout);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    verified_four_write_triple_layout(profile, expected, &source_cells)
        .or_else(|| {
            search_output_stream::verified_three_relocation_write_layout(
                profile, expected, &source_cells,
            )
        })
        .or_else(|| {
            search_output_stream::verified_source_scratch_output_layout(
                profile, expected, &source_cells,
            )
        })
        .or_else(|| {
            search_output_stream::verified_revisited_source_scratch_triple(
                profile, expected,
            )
        })
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)
}

const FORTY_SEVEN_LITERAL_OUTPUT: [u8; 47] = [
    5, 252, 205, 167, 216, 194, 187, 195, 215, 64, 65, 89, 36, 90, 28, 27, 46,
    79, 47, 26, 72, 185, 253, 211, 23, 157, 51, 183, 176, 59, 175, 55, 81, 29,
    80, 56, 54, 74, 53, 20, 44, 63, 45, 10, 70, 38, 17,
];

/// Bind the exact forty-seven source-independent binary bytes to guest
/// arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_forty_seven(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 47 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != FORTY_SEVEN_LITERAL_OUTPUT.get(index).copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 16];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..47 {
        if matches!(index, 3 | 14 | 16 | 31 | 37 | 40) {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 0 | 1 | 9 | 21 | 28) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 47
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 47
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let expected_steps = operations.len();
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(expected_steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == expected_steps)
            || vm.input_consumed() != 0
            || vm.output() != FORTY_SEVEN_LITERAL_OUTPUT
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}

const FORTY_EIGHT_LITERAL_OUTPUT: [u8; 48] = [
    81, 55, 52, 56, 251, 206, 159, 152, 184, 180, 131, 205, 4, 202, 28, 27, 46,
    79, 139, 207, 167, 162, 149, 214, 150, 161, 175, 197, 186, 224, 157, 225,
    185, 65, 71, 92, 42, 68, 41, 14, 50, 78, 49, 24, 31, 76, 32, 23,
];

/// Bind the exact forty-eight source-independent binary bytes to guest
/// arithmetic.
///
/// # Errors
///
/// Rejects other effects, profile drift, SSA aliases and VM disagreements.
pub fn encode_distinct_literal_forty_eight(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program)
        .map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = function.operations.as_chunks::<2>();
    let [TernaryOperation::ReturnVoid { .. }] = remainder else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if pairs.len() != 48 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            TernaryOperation::MaterializeU8 { result, scalar, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (constant, output)
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value
            || !ids.insert(*result)
            || Some(scalar.bits())
                != FORTY_EIGHT_LITERAL_OUTPUT.get(index).copied()
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    let mut operations = vec![LinearOpcode::NoOperation; 13];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0usize..48 {
        if matches!(index, 13 | 14 | 16 | 18 | 20 | 22 | 27 | 37 | 40 | 44) {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 4 | 12 | 18 | 33) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations)
        .map_err(ByteEchoBridgeError::Layout)?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    if writes.len() != 48
        || writes.iter().copied().collect::<BTreeSet<_>>().len() != 48
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < layout.source().len())
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let expected_steps = operations.len();
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|_error| {
                    ByteEchoBridgeError::UnsupportedEffectTrace
                })?;
        if !matches!(vm.run(expected_steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == expected_steps)
            || vm.input_consumed() != 0
            || vm.output() != FORTY_EIGHT_LITERAL_OUTPUT
        {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    Ok(layout)
}
