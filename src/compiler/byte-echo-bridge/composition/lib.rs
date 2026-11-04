// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
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

use malbolge::{ProfileDescriptor, ProfileMachine, RunOutcome, current_profile};
use std::collections::BTreeSet;
use std::iter::repeat_n;

use layout::{LinearLayout, LinearLayoutError, LinearOpcode, encode_linear_layout};
use ternary::{
    TernaryOperation, TernaryProgram, TernaryProgramValidationError, validate_ternary_program,
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
// Their extra instruction changes code phases and loader-expanded source length.
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

/// Fifteen-output witnesses omit the unsupported phase 20; no phase extrapolation.
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
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if !matches!(
        function.operations.as_slice(),
        [TernaryOperation::ReturnVoid { .. }]
    ) {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    encode_linear_layout(profile, &[LinearOpcode::NoOperation, LinearOpcode::Halt])
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
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
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
    encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)
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
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
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
    encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)
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
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
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
    encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)
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
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
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
            let valid = last_input.map_or(value == result, |latest| *value == latest);
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
    encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)
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
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, effects)) = function.operations.split_last()
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
    encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)
}

const fn byte_bitcast_operands(operation: &TernaryOperation) -> Option<(u32, u32)> {
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
fn literal_output_witness(byte: u8, count: usize) -> Option<LiteralOutputWitness> {
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

/// Emits a nonzero `u8` one to thirty-three times using guest data operations.
///
/// Accepts one `MaterializeU8` with one to thirty-three same-SSA `ByteOutput`s and
/// `ReturnVoid` for the current profile. A bounded source-address-specific
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
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, effects)) = function.operations.split_last()
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
    let (padding, arithmetic) = literal_output_witness(scalar.bits(), outputs.len())
        .ok_or(ByteEchoBridgeError::UnsupportedEffectTrace)?;
    let mut operations = vec![LinearOpcode::NoOperation; padding];
    operations.push(LinearOpcode::RelocateDataPointer);
    operations.extend_from_slice(arithmetic);
    operations.extend(repeat_n(LinearOpcode::OutputByte, outputs.len()));
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)?;
    let mut vm = ProfileMachine::from_source(profile, layout.source(), Vec::new())
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
