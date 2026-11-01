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
//   - Exact finite guest-computed u8 constant emission and VM evidence.
// - Must-Not:
//   - Substitute host writes for guest rotate or imply general C arithmetic.
// - Allows:
//   - Inputs: canonical ternary MCTR literals and target profile identity.
//   - Outputs: bounded re-admitted source and independent true guest byte.
//   - Side effects: bounded normative VM execution only.
// - Split-When:
//   - General byte-constant synthesis owns a larger safe profile domain.
// - Merge-When:
//   - A full target backend admits this exact proof without specialized code.
// - Summary:
//   - Proves nonzero values come from real relocated guest data rotation.
// - Description:
//   - Verifies independently rederived per-count seeds and rejects drift.
// - Usage:
//   - cargo test --locked --test rotated_byte_constant_bridge.
// - Defaults:
//   - Out-of-domain byte constants fail closed without source emission.

//! Genuine guest nonzero literal output via a seed-dependent data rotation.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryProgram, TypedIrInput, canonical_ternary_bytes,
    canonical_ternary_program, lower_typed_ir,
};
use bridge::{
    ByteEchoBridgeError, encode_initial_zero_outputs, encode_rotated_byte_literal,
    encode_successful_latest_byte_trace,
};
use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile};
use std::collections::BTreeMap;

// Every successful short phase, including later duplicate-byte prefixes.
const SHORT_TRIPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (146, 0),
    (25, 1),
    (7, 2),
    (145, 3),
    (24, 4),
    (9, 5),
    (144, 6),
    (22, 7),
    (8, 8),
    (8, 9),
    (22, 10),
    (7, 11),
    (7, 12),
    (21, 13),
    (6, 14),
    (252, 15),
    (20, 16),
    (5, 17),
    (252, 18),
    (19, 19),
    (4, 20),
    (251, 21),
    (18, 22),
    (3, 23),
    (11, 24),
    (23, 25),
];

// All successful short four-output phases; repeated bytes remain observable.
const SHORT_QUADRUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
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
    (176, 10),
    (162, 11),
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

// All successful short five-output phases, including duplicated bytes.
const SHORT_QUINTUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (10, 0),
    (7, 1),
    (24, 2),
    (9, 3),
    (9, 4),
    (23, 5),
    (9, 6),
    (8, 7),
    (22, 8),
    (7, 9),
    (142, 10),
    (21, 11),
    (6, 12),
    (141, 13),
    (10, 14),
    (6, 15),
    (140, 16),
    (10, 17),
    (4, 18),
    (139, 19),
    (9, 20),
    (12, 21),
    (138, 22),
    (25, 23),
    (9, 24),
    (137, 25),
];

// All 26 successful short sextuple phases, including byte repeats.
const SHORT_SEXTUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (47, 0),
    (47, 1),
    (175, 2),
    (42, 3),
    (41, 4),
    (177, 5),
    (40, 6),
    (40, 7),
    (176, 8),
    (162, 9),
    (41, 10),
    (178, 11),
    (177, 12),
    (66, 13),
    (200, 14),
    (176, 15),
    (64, 16),
    (200, 17),
    (177, 18),
    (65, 19),
    (190, 20),
    (186, 21),
    (63, 22),
    (191, 23),
    (185, 24),
    (61, 25),
];

// All 26 successful short septuple phases, including byte repeats.
const SHORT_SEPTUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (21, 0),
    (9, 1),
    (8, 2),
    (23, 3),
    (8, 4),
    (8, 5),
    (22, 6),
    (7, 7),
    (7, 8),
    (21, 9),
    (6, 10),
    (6, 11),
    (20, 12),
    (253, 13),
    (5, 14),
    (19, 15),
    (251, 16),
    (4, 17),
    (18, 18),
    (9, 19),
    (9, 20),
    (17, 21),
    (12, 22),
    (8, 23),
    (16, 24),
    (10, 25),
];

// All 26 valid eight-output prefix phases, including repeated output bytes.
const SHORT_OCTUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
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
    (56, 17),
    (199, 18),
    (57, 19),
    (65, 20),
    (198, 21),
    (55, 22),
    (64, 23),
    (197, 24),
    (56, 25),
];

// All 26 loader-validated nine-output prefixes, including duplicate bytes.
const SHORT_NONUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (144, 0),
    (22, 1),
    (9, 2),
    (143, 3),
    (22, 4),
    (7, 5),
    (142, 6),
    (21, 7),
    (6, 8),
    (252, 9),
    (20, 10),
    (5, 11),
    (252, 12),
    (19, 13),
    (4, 14),
    (251, 15),
    (18, 16),
    (3, 17),
    (11, 18),
    (23, 19),
    (2, 20),
    (11, 21),
    (22, 22),
    (1, 23),
    (10, 24),
    (21, 25),
];

// All 26 ten-output source phases, including a repeated byte witness.
const SHORT_DECUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (42, 0),
    (176, 1),
    (161, 2),
    (40, 3),
    (176, 4),
    (162, 5),
    (41, 6),
    (178, 7),
    (187, 8),
    (66, 9),
    (192, 10),
    (185, 11),
    (64, 12),
    (191, 13),
    (186, 14),
    (65, 15),
    (196, 16),
    (184, 17),
    (57, 18),
    (201, 19),
    (182, 20),
    (55, 21),
    (200, 22),
    (183, 23),
    (56, 24),
    (193, 25),
];

// All 26 eleven-output phases, including overlapping byte witnesses.
const SHORT_UNDECUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (9, 0),
    (8, 1),
    (22, 2),
    (7, 3),
    (7, 4),
    (21, 5),
    (6, 6),
    (6, 7),
    (10, 8),
    (6, 9),
    (140, 10),
    (10, 11),
    (4, 12),
    (139, 13),
    (9, 14),
    (12, 15),
    (138, 16),
    (25, 17),
    (9, 18),
    (137, 19),
    (25, 20),
    (7, 21),
    (136, 22),
    (24, 23),
    (9, 24),
    (135, 25),
];

// All 26 twelve-output source phases including overlapping byte witnesses.
const SHORT_DODECUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (40, 0),
    (40, 1),
    (176, 2),
    (41, 3),
    (41, 4),
    (178, 5),
    (66, 6),
    (56, 7),
    (200, 8),
    (176, 9),
    (64, 10),
    (200, 11),
    (177, 12),
    (65, 13),
    (190, 14),
    (186, 15),
    (63, 16),
    (191, 17),
    (185, 18),
    (61, 19),
    (191, 20),
    (186, 21),
    (62, 22),
    (184, 23),
    (180, 24),
    (60, 25),
];

// All 26 thirteen-output phases from independent real-VM re-execution.
const SHORT_TREDECUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (22, 0),
    (7, 1),
    (7, 2),
    (21, 3),
    (6, 4),
    (252, 5),
    (20, 6),
    (5, 7),
    (5, 8),
    (19, 9),
    (251, 10),
    (4, 11),
    (18, 12),
    (9, 13),
    (9, 14),
    (17, 15),
    (12, 16),
    (8, 17),
    (16, 18),
    (10, 19),
    (7, 20),
    (15, 21),
    (9, 22),
    (9, 23),
    (14, 24),
    (9, 25),
];

// All 26 fourteen-output phases, including repeated values.
const SHORT_FOURTEEN_ROTATION_WITNESSES: &[(u8, usize)] = &[
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
    (65, 14),
    (198, 15),
    (55, 16),
    (64, 17),
    (197, 18),
    (56, 19),
    (65, 20),
    (193, 21),
    (51, 22),
    (59, 23),
    (195, 24),
    (49, 25),
];

// All 25 successful phases in the 26-phase fifteen-output VM scan.
const SHORT_FIFTEEN_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (142, 0),
    (21, 1),
    (6, 2),
    (141, 3),
    (10, 4),
    (6, 5),
    (140, 6),
    (10, 7),
    (4, 8),
    (251, 9),
    (18, 10),
    (3, 11),
    (11, 12),
    (23, 13),
    (2, 14),
    (11, 15),
    (22, 16),
    (1, 17),
    (10, 18),
    (21, 19),
    (8, 21),
    (23, 22),
    (255, 23),
    (8, 24),
    (22, 25),
];

// All 26 successful VM-checked sixteen-output phases, including byte repeats.
const SHORT_SIXTEEN_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (41, 0),
    (178, 1),
    (177, 2),
    (66, 3),
    (200, 4),
    (176, 5),
    (64, 6),
    (200, 7),
    (186, 8),
    (65, 9),
    (196, 10),
    (184, 11),
    (57, 12),
    (201, 13),
    (182, 14),
    (55, 15),
    (200, 16),
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

// All 26 independently verified seventeen-output phases; repeated bytes
// are retained here to prove shortest-first selection in the bridge table.
const SHORT_SEVENTEEN_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (6, 0),
    (6, 1),
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
    (9, 12),
    (137, 13),
    (25, 14),
    (7, 15),
    (136, 16),
    (24, 17),
    (9, 18),
    (135, 19),
    (22, 20),
    (9, 21),
    (134, 22),
    (22, 23),
    (7, 24),
    (133, 25),
];

// All 26 independent current-profile nineteen-output phases, including duplicates.
const SHORT_NINETEEN_ROTATION_WITNESSES: &[(u8, usize)] = &[
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
    (9, 16),
    (9, 17),
    (14, 18),
    (9, 19),
    (8, 20),
    (13, 21),
    (7, 22),
    (7, 23),
    (12, 24),
    (6, 25),
];

// All 26 independent current-profile twenty-output phases, including duplicates.
const SHORT_TWENTY_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (192, 0),
    (185, 1),
    (64, 2),
    (191, 3),
    (186, 4),
    (65, 5),
    (196, 6),
    (184, 7),
    (65, 8),
    (198, 9),
    (55, 10),
    (64, 11),
    (197, 12),
    (56, 13),
    (65, 14),
    (193, 15),
    (51, 16),
    (59, 17),
    (195, 18),
    (49, 19),
    (58, 20),
    (194, 21),
    (50, 22),
    (59, 23),
    (196, 24),
    (48, 25),
];

// All 26 valid twenty-three-output VM phases; duplicate byte witnesses
// retain the shortest source prefix, not an arbitrary later occurrence.
const SHORT_TWENTY_THREE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (251, 0),
    (4, 1),
    (18, 2),
    (9, 3),
    (9, 4),
    (17, 5),
    (12, 6),
    (8, 7),
    (25, 8),
    (7, 9),
    (136, 10),
    (24, 11),
    (9, 12),
    (135, 13),
    (22, 14),
    (9, 15),
    (134, 16),
    (22, 17),
    (7, 18),
    (133, 19),
    (21, 20),
    (6, 21),
    (132, 22),
    (10, 23),
    (42, 24),
    (27, 25),
];

// 25 successful 24-output VM phases (prefix seven rejects); later duplicate
// bytes remain recorded for independent shortest-prefix admission.
const SHORT_TWENTY_FOUR_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (65, 0),
    (56, 1),
    (199, 2),
    (57, 3),
    (65, 4),
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
    (185, 17),
    (180, 18),
    (59, 19),
    (187, 20),
    (168, 21),
    (48, 22),
    (21, 23),
    (21, 24),
    (155, 25),
];

// 25 successful twenty-five-output phases, excluding phase seven. Duplicates
// remain visible to assert shortest-source selection in the production table.
const SHORT_TWENTY_FIVE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (18, 0),
    (3, 1),
    (11, 2),
    (23, 3),
    (2, 4),
    (11, 5),
    (22, 6),
    (7, 8),
    (15, 9),
    (9, 10),
    (9, 11),
    (14, 12),
    (9, 13),
    (8, 14),
    (13, 15),
    (7, 16),
    (7, 17),
    (12, 18),
    (6, 19),
    (253, 20),
    (11, 21),
    (39, 22),
    (29, 23),
    (162, 24),
    (44, 25),
];

// Independent 32-output source/VM scan: 21/26 phases succeed.
// Phases three through seven fail; the later byte 139 duplicates phase 16.
const SHORT_THIRTY_TWO_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (200, 0),
    (183, 1),
    (56, 2),
    (58, 8),
    (194, 9),
    (50, 10),
    (59, 11),
    (196, 12),
    (48, 13),
    (47, 14),
    (21, 15),
    (139, 16),
    (156, 17),
    (20, 18),
    (137, 19),
    (154, 20),
    (19, 21),
    (136, 22),
    (150, 23),
    (15, 24),
    (139, 25),
];

// Independent 31-output VM scan: 22 phases, with 4..=7 rejected.
// Byte 7, 29 and 39 repeat later; only their first prefixes are admitted.
const SHORT_THIRTY_ONE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (22, 0),
    (1, 1),
    (10, 2),
    (21, 3),
    (8, 8),
    (13, 9),
    (7, 10),
    (7, 11),
    (12, 12),
    (6, 13),
    (253, 14),
    (11, 15),
    (39, 16),
    (29, 17),
    (162, 18),
    (44, 19),
    (29, 20),
    (161, 21),
    (43, 22),
    (25, 23),
    (160, 24),
    (39, 25),
];

// All 22 successful thirty-output source phases from an independent VM scan.
// Phases four through seven fail; repeated bytes preserve the first prefix.
const SHORT_THIRTY_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (55, 0),
    (64, 1),
    (197, 2),
    (56, 3),
    (185, 8),
    (179, 9),
    (58, 10),
    (185, 11),
    (180, 12),
    (59, 13),
    (187, 14),
    (168, 15),
    (48, 16),
    (21, 17),
    (21, 18),
    (155, 19),
    (18, 20),
    (19, 21),
    (154, 22),
    (16, 23),
    (15, 24),
    (150, 25),
];

// Twenty-nine outputs admit 23 VM phases; five through seven fail.
// Duplicates keep their original prefix for shortest safe admission.
const SHORT_TWENTY_NINE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (12, 0),
    (8, 1),
    (16, 2),
    (10, 3),
    (7, 4),
    (22, 8),
    (9, 9),
    (134, 10),
    (22, 11),
    (7, 12),
    (133, 13),
    (21, 14),
    (6, 15),
    (132, 16),
    (10, 17),
    (42, 18),
    (27, 19),
    (165, 20),
    (43, 21),
    (26, 22),
    (164, 23),
    (43, 24),
    (25, 25),
];

// Every successful 28-output prefix from an independent real-VM scan.
// Prefixes five through seven fail; the second 191 keeps the first seed.
const SHORT_TWENTY_EIGHT_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (63, 0),
    (191, 1),
    (185, 2),
    (61, 3),
    (191, 4),
    (181, 8),
    (51, 9),
    (195, 10),
    (179, 11),
    (49, 12),
    (194, 13),
    (180, 14),
    (50, 15),
    (196, 16),
    (169, 17),
    (48, 18),
    (18, 19),
    (141, 20),
    (153, 21),
    (21, 22),
    (140, 23),
    (151, 24),
    (19, 25),
];

// 23 independent twenty-seven-output VM phases; six, seven, and eight fail.
// Duplicates remain as evidence for choosing the first safe seed.
const SHORT_TWENTY_SEVEN_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (138, 0),
    (25, 1),
    (9, 2),
    (137, 3),
    (25, 4),
    (7, 5),
    (8, 9),
    (23, 10),
    (255, 11),
    (8, 12),
    (22, 13),
    (254, 14),
    (7, 15),
    (21, 16),
    (253, 17),
    (252, 18),
    (11, 19),
    (42, 20),
    (165, 21),
    (164, 22),
    (41, 23),
    (164, 24),
    (164, 25),
];

// 24 independent 26-output guest phases; phase six and seven fail.
// Preserve duplicates to check the earliest valid no-op prefix per byte.
const SHORT_TWENTY_SIX_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (196, 0),
    (184, 1),
    (57, 2),
    (201, 3),
    (182, 4),
    (55, 5),
    (65, 8),
    (193, 9),
    (51, 10),
    (59, 11),
    (195, 12),
    (49, 13),
    (58, 14),
    (194, 15),
    (50, 16),
    (59, 17),
    (196, 18),
    (48, 19),
    (47, 20),
    (21, 21),
    (139, 22),
    (156, 23),
    (20, 24),
    (137, 25),
];

// All 26 valid twenty-two-output VM phases; one value repeats at phase ten.
const SHORT_TWENTY_TWO_ROTATION_WITNESSES: &[(u8, usize)] = &[
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
    (200, 10),
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

// All 25 valid twenty-one-output VM phases; phase fourteen is rejected.
const SHORT_TWENTY_ONE_ROTATION_WITNESSES: &[(u8, usize)] = &[
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
    (10, 12),
    (21, 13),
    (8, 15),
    (23, 16),
    (255, 17),
    (8, 18),
    (22, 19),
    (254, 20),
    (7, 21),
    (21, 22),
    (253, 23),
    (252, 24),
    (11, 25),
];

// All 26 independently VM-verified eighteen-output phases. Duplicates prove
// that only shortest source prefixes may enter the production seed table.
const SHORT_EIGHTEEN_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (66, 0),
    (56, 1),
    (201, 2),
    (64, 3),
    (55, 4),
    (200, 5),
    (65, 6),
    (56, 7),
    (190, 8),
    (186, 9),
    (63, 10),
    (191, 11),
    (185, 12),
    (61, 13),
    (191, 14),
    (186, 15),
    (62, 16),
    (184, 17),
    (180, 18),
    (60, 19),
    (185, 20),
    (179, 21),
    (58, 22),
    (185, 23),
    (180, 24),
    (59, 25),
];

const fn pos(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte.saturating_add(1),
        line: 1,
    }
}

const fn span(begin: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: pos(begin),
        end: pos(end),
    }
}

fn source(value: u8, outputs: usize) -> Result<TernaryProgram, String> {
    let mut instructions = vec![InputInstruction::ConstantInteger {
        bit_width: 8,
        little_endian: vec![value],
        result: 0,
        span: span(0, 1),
        type_kind: InputScalarType::U8,
    }];
    for index in 0..outputs {
        let start = u32::try_from(index.saturating_add(1))
            .map_err(|error| format!("literal output span: {error}"))?;
        instructions.push(InputInstruction::ByteOutput {
            span: span(start, start.saturating_add(1)),
            value: 0,
        });
    }
    let end = u32::try_from(outputs.saturating_add(2))
        .map_err(|error| format!("literal return span: {error}"))?;
    let typed = TypedIrInput {
        abi_id: String::from("malbolge-c32-v1"),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: 0,
                instructions,
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: span(end.saturating_sub(1), end),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("one_literal_output"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/rotated-constant.c"),
        source_sha256: [0x73; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered =
        lower_typed_ir(&typed).map_err(|error| format!("literal ternary lowering: {error:?}"))?;
    let canonical = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("literal canonical MCTR encode: {error:?}"))?;
    let admitted = canonical_ternary_program(&canonical)
        .map_err(|error| format!("literal canonical MCTR decode: {error:?}"))?;
    if admitted != lowered {
        return Err(String::from(
            "literal ternary byte-for-byte roundtrip drift",
        ));
    }
    Ok(admitted)
}

#[test]
fn all_seeded_nonzero_literals_execute_real_guest_rotate_output() -> Result<(), String> {
    for (byte, noops) in [
        (4, 23),
        (5, 20),
        (6, 16),
        (9, 7),
        (10, 4),
        (11, 1),
        (18, 24),
        (19, 21),
        (20, 18),
        (21, 6),
        (22, 3),
        (23, 0),
        (251, 22),
        (253, 19),
    ] {
        let program = source(byte, 1)?;
        let layout = encode_rotated_byte_literal(&program, current_profile())
            .map_err(|error| format!("seeded {byte} target rejected: {error:?}"))?;
        if layout.source().len() != noops + 4
            || layout.executed_code_positions().len() != noops + 4
            || layout
                .data_write_positions()
                .iter()
                .filter(|x| x.is_some())
                .count()
                != 1
        {
            return Err(format!("seeded literal {byte} geometry drift"));
        }
        // Each bridge admission already checks one actual VM output.
        // Repeat under nonempty stdin for representative short/high seeds.
        if [4, 23, 253].contains(&byte) {
            let mut vm =
                ProfileMachine::from_source(current_profile(), layout.source(), vec![255, 0, 128])
                    .map_err(|error| format!("guest seeded {byte} load: {error:?}"))?;
            if !matches!(vm.run(noops + 4),
                Ok(RunOutcome::Terminated { steps, .. }) if steps == noops + 4)
                || vm.output() != [byte]
                || vm.input_consumed() != 0
            {
                return Err(format!("guest seeded {byte} output diverged"));
            }
        }
        if encode_initial_zero_outputs(&program, current_profile()).is_ok()
            || encode_successful_latest_byte_trace(&program, current_profile()).is_ok()
        {
            return Err(format!("old byte trace mode admitted nonzero {byte}"));
        }
    }
    Ok(())
}

#[test]
fn seeded_literals_refuse_unsupported_values_and_profiles() -> Result<(), String> {
    const WITNESSED: &[u8] = &[4, 5, 6, 9, 10, 11, 18, 19, 20, 21, 22, 23, 251, 253];
    for byte in u8::MIN..=u8::MAX {
        if WITNESSED.contains(&byte) {
            continue;
        }
        let program = source(byte, 1)?;
        if encode_rotated_byte_literal(&program, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unverified u8 literal {byte} admitted"));
        }
    }
    let valid = source(23, 1)?;
    if encode_rotated_byte_literal(&valid, historical_profile())
        != Err(ByteEchoBridgeError::ProfileMismatch)
    {
        return Err(String::from("foreign profile admitted"));
    }
    Ok(())
}

#[test]
fn seeded_literals_repeat_guest_output_without_new_rotation() -> Result<(), String> {
    for (byte, padding) in [(64, 19), (183, 0), (200, 21)] {
        let program = source(byte, 2)?;
        let layout = encode_rotated_byte_literal(&program, current_profile())
            .map_err(|error| format!("repeat {byte} x2: {error:?}"))?;
        if layout.source().len() != padding + 5
            || layout
                .data_write_positions()
                .iter()
                .filter(|x| x.is_some())
                .count()
                != 1
        {
            return Err(format!("repeat {byte} geometry changed"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![255, 0, 128])
                .map_err(|error| format!("repeat {byte} guest load: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != [byte, byte]
        {
            return Err(format!("repeat {byte} guest VM mismatch"));
        }
        if encode_rotated_byte_literal(&source(byte, 1)?, current_profile()).is_ok() {
            return Err(format!("repeated {byte} leaked into single-output seeds"));
        }
    }
    for (byte, outputs) in [(23, 0), (23, 2), (183, 3), (183, 100)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unproved seeded shape {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_triple_literals_reuse_the_real_rotated_accumulator() -> Result<(), String> {
    // Distinct phases, including a new small byte and high-bit bytes.
    for (byte, padding) in [(146, 0), (7, 2), (252, 15), (3, 23), (23, 25)] {
        let admitted = source(byte, 3)?;
        let layout = encode_rotated_byte_literal(&admitted, current_profile())
            .map_err(|error| format!("triple {byte} target rejected: {error:?}"))?;
        if layout.source().len() != padding + 6
            || layout.executed_code_positions().len() != padding + 6
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("triple {byte} source or memory geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![255, 0, 128])
                .map_err(|error| format!("triple {byte} guest load: {error:?}"))?;
        if !matches!(vm.run(padding + 6),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == padding + 6)
            || vm.output() != [byte, byte, byte]
            || vm.input_consumed() != 0
        {
            return Err(format!("triple {byte} guest output or halt diverged"));
        }
    }
    for (byte, outputs) in [(3, 1), (3, 2), (146, 2), (252, 4), (183, 3)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unproven triple shape {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_four_output_literals_reuse_guest_rotation() -> Result<(), String> {
    for (byte, padding) in [(43, 0), (182, 1), (192, 16), (201, 25)] {
        let admitted = source(byte, 4)?;
        let layout = encode_rotated_byte_literal(&admitted, current_profile())
            .map_err(|error| format!("four-output {byte} rejected: {error:?}"))?;
        if layout.source().len() != padding + 7
            || layout.executed_code_positions().len() != padding + 7
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("four-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("four-output {byte} guest load: {error:?}"))?;
        if !matches!(vm.run(padding + 7),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == padding + 7)
            || vm.output() != [byte; 4]
            || vm.input_consumed() != 0
        {
            return Err(format!("four-output {byte} guest execution diverged"));
        }
    }
    for (byte, outputs) in [(43, 1), (43, 2), (43, 3), (43, 5), (3, 4)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unproved four-output seed {byte} x{outputs}"));
        }
    }
    Ok(())
}

#[test]
fn four_output_seed_table_admits_exactly_the_witnessed_byte_domain() -> Result<(), String> {
    let mut expected = BTreeMap::new();
    for (byte, padding) in SHORT_QUADRUPLE_ROTATION_WITNESSES {
        _ = expected.entry(*byte).or_insert(*padding);
    }
    let mut witnessed = BTreeMap::new();
    for byte in u8::MIN..=u8::MAX {
        let admitted = source(byte, 4)?;
        match encode_rotated_byte_literal(&admitted, current_profile()) {
            Ok(layout) => {
                let Some(padding) = expected.get(&byte) else {
                    return Err(format!("unwitnessed four-output byte {byte} admitted"));
                };
                if layout.source().len() != padding + 7
                    || layout.executed_code_positions().len() != padding + 7
                    || layout
                        .data_write_positions()
                        .iter()
                        .filter(|position| position.is_some())
                        .count()
                        != 1
                {
                    return Err(format!("four-output {byte} seed geometry drift"));
                }
                _ = witnessed.insert(byte, layout.source().len() - 7);
            }
            Err(ByteEchoBridgeError::UnsupportedEffectTrace) => {
                if expected.contains_key(&byte) {
                    return Err(format!("four-output witnessed byte {byte} rejected"));
                }
            }
            Err(error) => return Err(format!("unexpected four-output error {byte}: {error:?}")),
        }
    }
    if witnessed != expected {
        return Err(format!("four-output byte-domain mismatch: {witnessed:?}"));
    }
    Ok(())
}

#[test]
fn witnessed_five_output_literals_use_guest_rotation() -> Result<(), String> {
    for (byte, padding) in [(10, 0), (142, 10), (140, 16), (137, 25)] {
        let admitted = source(byte, 5)?;
        let layout = encode_rotated_byte_literal(&admitted, current_profile())
            .map_err(|error| format!("five-output {byte} rejected: {error:?}"))?;
        if layout.source().len() != padding + 8
            || layout.executed_code_positions().len() != padding + 8
            || layout
                .data_write_positions()
                .iter()
                .filter(|item| item.is_some())
                .count()
                != 1
        {
            return Err(format!("five-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![255, 0, 128])
                .map_err(|error| format!("five-output {byte} guest load: {error:?}"))?;
        if !matches!(vm.run(padding + 8),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == padding + 8)
            || vm.output() != [byte; 5]
            || vm.input_consumed() != 0
        {
            return Err(format!("five-output {byte} guest VM mismatch"));
        }
    }
    for (byte, outputs) in [(10, 4), (43, 5), (137, 4), (10, 6)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unproved five-output shape {byte} x{outputs}"));
        }
    }
    Ok(())
}

#[test]
fn five_output_seed_table_admits_only_shortest_witnessed_byte_domain() -> Result<(), String> {
    let mut expected = BTreeMap::new();
    for (byte, padding) in SHORT_QUINTUPLE_ROTATION_WITNESSES {
        _ = expected.entry(*byte).or_insert(*padding);
    }
    let mut actual = BTreeMap::new();
    for byte in u8::MIN..=u8::MAX {
        match encode_rotated_byte_literal(&source(byte, 5)?, current_profile()) {
            Ok(layout) => {
                let Some(padding) = expected.get(&byte) else {
                    return Err(format!("unwitnessed five-output {byte} admitted"));
                };
                if layout.source().len() != padding + 8
                    || layout.executed_code_positions().len() != padding + 8
                    || layout
                        .data_write_positions()
                        .iter()
                        .filter(|item| item.is_some())
                        .count()
                        != 1
                {
                    return Err(format!("five-output {byte} geometry drift"));
                }
                _ = actual.insert(byte, layout.source().len() - 8);
            }
            Err(ByteEchoBridgeError::UnsupportedEffectTrace) => {
                if expected.contains_key(&byte) {
                    return Err(format!("witnessed five-output {byte} rejected"));
                }
            }
            Err(error) => return Err(format!("five-output {byte} unexpected: {error:?}")),
        }
    }
    if actual != expected {
        return Err(format!("five-output admitted domain drift: {actual:?}"));
    }
    Ok(())
}

fn check_repeated_output_seed_domain(
    outputs: usize,
    witnesses: &[(u8, usize)],
) -> Result<(), String> {
    let mut expected = BTreeMap::new();
    for (byte, padding) in witnesses {
        _ = expected.entry(*byte).or_insert(*padding);
    }
    let mut admitted = BTreeMap::new();
    for byte in u8::MIN..=u8::MAX {
        match encode_rotated_byte_literal(&source(byte, outputs)?, current_profile()) {
            Ok(layout) => {
                let Some(padding) = expected.get(&byte) else {
                    return Err(format!("unwitnessed {byte} x{outputs} admitted"));
                };
                let expected_len = padding.saturating_add(outputs).saturating_add(3);
                if layout.source().len() != expected_len
                    || layout.executed_code_positions().len() != expected_len
                    || layout
                        .data_write_positions()
                        .iter()
                        .filter(|position| position.is_some())
                        .count()
                        != 1
                {
                    return Err(format!("seeded {byte} x{outputs} geometry drift"));
                }
                _ = admitted.insert(
                    byte,
                    layout
                        .source()
                        .len()
                        .saturating_sub(outputs.saturating_add(3)),
                );
            }
            Err(ByteEchoBridgeError::UnsupportedEffectTrace) => {
                if expected.contains_key(&byte) {
                    return Err(format!("witnessed {byte} x{outputs} rejected"));
                }
            }
            Err(error) => return Err(format!("seeded {byte} x{outputs}: {error:?}")),
        }
    }
    if admitted != expected {
        return Err(format!("{outputs}-output domain drift: {admitted:?}"));
    }
    Ok(())
}

#[test]
fn six_and_seven_output_seed_tables_admit_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(6, SHORT_SEXTUPLE_ROTATION_WITNESSES)?;
    check_repeated_output_seed_domain(7, SHORT_SEPTUPLE_ROTATION_WITNESSES)
}

#[test]
fn eight_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(8, SHORT_OCTUPLE_ROTATION_WITNESSES)
}

#[test]
fn witnessed_six_and_seven_output_literals_execute_guest_rotation() -> Result<(), String> {
    for (byte, padding, outputs) in [
        (47, 0, 6),
        (200, 14, 6),
        (61, 25, 6),
        (21, 0, 7),
        (253, 13, 7),
        (10, 25, 7),
    ] {
        let layout = encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            .map_err(|error| format!("seeded {byte} x{outputs}: {error:?}"))?;
        if layout.source().len() != padding + outputs + 3
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("guest seeded {byte} x{outputs} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x{outputs}: {error:?}"))?;
        if !matches!(vm.run(padding + outputs + 3),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == padding + outputs + 3)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; outputs]
        {
            return Err(format!("guest repeated output {byte} x{outputs} diverged"));
        }
    }
    for (byte, outputs) in [(21, 6), (47, 7), (47, 5), (10, 8)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unsupported seeded {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn nine_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(9, SHORT_NONUPLE_ROTATION_WITNESSES)
}

#[test]
fn ten_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(10, SHORT_DECUPLE_ROTATION_WITNESSES)
}

#[test]
fn eleven_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(11, SHORT_UNDECUPLE_ROTATION_WITNESSES)
}

#[test]
fn twelve_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(12, SHORT_DODECUPLE_ROTATION_WITNESSES)
}

#[test]
fn thirteen_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(13, SHORT_TREDECUPLE_ROTATION_WITNESSES)
}

#[test]
fn fourteen_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(14, SHORT_FOURTEEN_ROTATION_WITNESSES)
}

#[test]
fn fifteen_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(15, SHORT_FIFTEEN_ROTATION_WITNESSES)
}

#[test]
fn sixteen_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(16, SHORT_SIXTEEN_ROTATION_WITNESSES)
}

#[test]
fn seventeen_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(17, SHORT_SEVENTEEN_ROTATION_WITNESSES)
}

#[test]
fn eighteen_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(18, SHORT_EIGHTEEN_ROTATION_WITNESSES)
}

#[test]
fn nineteen_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(19, SHORT_NINETEEN_ROTATION_WITNESSES)
}

#[test]
fn thirty_two_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(32, SHORT_THIRTY_TWO_ROTATION_WITNESSES)
}

#[test]
fn witnessed_thirty_two_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(200, 0), (139, 16), (15, 24)] {
        let layout = encode_rotated_byte_literal(&source(byte, 32)?, current_profile())
            .map_err(|error| format!("seeded {byte} x32: {error:?}"))?;
        let steps = padding + 35;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("thirty-two-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x32: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 32]
        {
            return Err(format!("thirty-two-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(22, 32), (160, 32), (200, 33), (200, 31)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn thirty_one_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(31, SHORT_THIRTY_ONE_ROTATION_WITNESSES)
}

#[test]
fn witnessed_thirty_one_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(22, 0), (29, 17), (160, 24)] {
        let layout = encode_rotated_byte_literal(&source(byte, 31)?, current_profile())
            .map_err(|error| format!("seeded {byte} x30: {error:?}"))?;
        let steps = padding + 34;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("thirty-one-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x30: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 31]
        {
            return Err(format!("thirty-one-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(55, 31), (63, 31), (22, 32), (22, 30)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn thirty_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(30, SHORT_THIRTY_ROTATION_WITNESSES)
}

#[test]
fn witnessed_thirty_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(55, 0), (21, 17), (150, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 30)?, current_profile())
            .map_err(|error| format!("seeded {byte} x30: {error:?}"))?;
        let steps = padding + 33;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("thirty-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x30: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 30]
        {
            return Err(format!("thirty-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(12, 30), (63, 30), (55, 31), (55, 29)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn twenty_nine_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(29, SHORT_TWENTY_NINE_ROTATION_WITNESSES)
}

#[test]
fn witnessed_twenty_nine_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(12, 0), (132, 16), (25, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 29)?, current_profile())
            .map_err(|error| format!("seeded {byte} x29: {error:?}"))?;
        let steps = padding + 32;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|x| x.is_some())
                .count()
                != 1
        {
            return Err(format!("twenty-nine-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x29: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 29]
        {
            return Err(format!("twenty-nine-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(138, 29), (63, 29), (12, 30), (12, 28)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn twenty_eight_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(28, SHORT_TWENTY_EIGHT_ROTATION_WITNESSES)
}

#[test]
fn witnessed_twenty_eight_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(63, 0), (196, 16), (19, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 28)?, current_profile())
            .map_err(|error| format!("seeded {byte} x28: {error:?}"))?;
        let steps = padding + 31;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("twenty-eight-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x28: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 28]
        {
            return Err(format!("twenty-eight-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(138, 28), (66, 28), (63, 29), (63, 27)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn twenty_seven_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(27, SHORT_TWENTY_SEVEN_ROTATION_WITNESSES)
}

#[test]
fn witnessed_twenty_seven_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(138, 0), (253, 17), (41, 23)] {
        let layout = encode_rotated_byte_literal(&source(byte, 27)?, current_profile())
            .map_err(|error| format!("seeded {byte} x27: {error:?}"))?;
        let steps = padding + 30;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("twenty-seven-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x27: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 27]
        {
            return Err(format!("twenty-seven-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(66, 27), (196, 27), (138, 28), (138, 26)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn twenty_six_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(26, SHORT_TWENTY_SIX_ROTATION_WITNESSES)
}

#[test]
fn witnessed_twenty_six_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(196, 0), (47, 20), (137, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 26)?, current_profile())
            .map_err(|error| format!("seeded {byte} x26: {error:?}"))?;
        let steps = padding + 29;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("twenty-six-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x26: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 26]
        {
            return Err(format!("twenty-six-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(66, 26), (196, 25), (196, 27)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn twenty_five_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(25, SHORT_TWENTY_FIVE_ROTATION_WITNESSES)
}

#[test]
fn witnessed_twenty_five_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(18, 0), (253, 20), (44, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 25)?, current_profile())
            .map_err(|error| format!("seeded {byte} x25: {error:?}"))?;
        let steps = padding + 28;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("twenty-five-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x25: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 25]
        {
            return Err(format!("twenty-five-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(65, 25), (18, 24), (18, 26)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn twenty_four_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(24, SHORT_TWENTY_FOUR_ROTATION_WITNESSES)
}

#[test]
fn witnessed_twenty_four_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(65, 0), (185, 14), (155, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 24)?, current_profile())
            .map_err(|error| format!("seeded {byte} x24: {error:?}"))?;
        let steps = padding + 27;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("twenty-four-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x24: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 24]
        {
            return Err(format!("twenty-four-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(66, 24), (65, 23), (65, 25)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn twenty_three_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(23, SHORT_TWENTY_THREE_ROTATION_WITNESSES)
}

#[test]
fn witnessed_twenty_three_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(251, 0), (136, 10), (27, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 23)?, current_profile())
            .map_err(|error| format!("seeded {byte} x23: {error:?}"))?;
        let steps = padding + 26;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("twenty-three-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x23: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 23]
        {
            return Err(format!("twenty-three-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(66, 23), (251, 22), (251, 24)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn twenty_two_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(22, SHORT_TWENTY_TWO_ROTATION_WITNESSES)
}

#[test]
fn witnessed_twenty_two_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(64, 0), (55, 9), (18, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 22)?, current_profile())
            .map_err(|error| format!("seeded {byte} x22: {error:?}"))?;
        let steps = padding + 25;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("twenty-two-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x22: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 22]
        {
            return Err(format!("twenty-two-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(66, 22), (64, 21), (64, 23)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn twenty_one_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(21, SHORT_TWENTY_ONE_ROTATION_WITNESSES)
}

#[test]
fn witnessed_twenty_one_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(140, 0), (22, 10), (252, 24)] {
        let layout = encode_rotated_byte_literal(&source(byte, 21)?, current_profile())
            .map_err(|error| format!("seeded {byte} x21: {error:?}"))?;
        let steps = padding + 24;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("twenty-one-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x21: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 21]
        {
            return Err(format!("twenty-one-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(66, 21), (140, 20), (140, 22)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn twenty_output_seed_table_admits_only_shortest_witnessed_bytes() -> Result<(), String> {
    check_repeated_output_seed_domain(20, SHORT_TWENTY_ROTATION_WITNESSES)
}

#[test]
fn witnessed_twenty_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(192, 0), (55, 10), (48, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 20)?, current_profile())
            .map_err(|error| format!("seeded {byte} x20: {error:?}"))?;
        let steps = padding + 23;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("twenty-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x20: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 20]
        {
            return Err(format!("twenty-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(66, 20), (192, 19), (192, 21)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_nineteen_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(20, 0), (12, 10), (6, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 19)?, current_profile())
            .map_err(|error| format!("seeded {byte} x19: {error:?}"))?;
        let steps = padding + 22;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("nineteen-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x19: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 19]
        {
            return Err(format!("nineteen-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(66, 19), (20, 18), (20, 20)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_eighteen_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(66, 0), (63, 10), (59, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 18)?, current_profile())
            .map_err(|error| format!("seeded {byte} x18: {error:?}"))?;
        let steps = padding + 21;
        if layout.source().len() != steps
            || layout.executed_code_positions().len() != steps
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("eighteen-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x18: {error:?}"))?;
        if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: completed, .. }) if completed == steps)
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 18]
        {
            return Err(format!("eighteen-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(6, 18), (66, 17), (66, 20)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_seventeen_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(6, 0), (25, 11), (133, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 17)?, current_profile())
            .map_err(|error| format!("seeded {byte} x17: {error:?}"))?;
        if layout.source().len() != padding + 20
            || layout.executed_code_positions().len() != padding + 20
            || layout
                .data_write_positions()
                .iter()
                .filter(|slot| slot.is_some())
                .count()
                != 1
        {
            return Err(format!("seventeen-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x17: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 17]
        {
            return Err(format!("seventeen-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(41, 17), (6, 16), (6, 20)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_sixteen_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(41, 0), (181, 20), (194, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 16)?, current_profile())
            .map_err(|error| format!("seeded {byte} x16: {error:?}"))?;
        if layout.source().len() != padding + 19
            || layout
                .data_write_positions()
                .iter()
                .filter(|slot| slot.is_some())
                .count()
                != 1
        {
            return Err(format!("sixteen-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x16: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 16]
        {
            return Err(format!("sixteen-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(142, 16), (41, 15), (41, 17)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_fifteen_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(142, 0), (251, 9), (255, 23)] {
        let layout = encode_rotated_byte_literal(&source(byte, 15)?, current_profile())
            .map_err(|error| format!("seeded {byte} x15: {error:?}"))?;
        if layout.source().len() != padding + 18
            || layout
                .data_write_positions()
                .iter()
                .filter(|slot| slot.is_some())
                .count()
                != 1
        {
            return Err(format!("fifteen-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x15: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 15]
        {
            return Err(format!("fifteen-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(40, 15), (142, 14), (142, 16)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_fourteen_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(176, 0), (199, 12), (49, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 14)?, current_profile())
            .map_err(|error| format!("seeded {byte} x14: {error:?}"))?;
        if layout.source().len() != padding + 17
            || layout
                .data_write_positions()
                .iter()
                .filter(|slot| slot.is_some())
                .count()
                != 1
        {
            return Err(format!("fourteen-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x14: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 14]
        {
            return Err(format!("fourteen-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(22, 14), (176, 13), (176, 15)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_thirteen_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(22, 0), (252, 5), (14, 24)] {
        let layout = encode_rotated_byte_literal(&source(byte, 13)?, current_profile())
            .map_err(|error| format!("seeded {byte} x13: {error:?}"))?;
        if layout.source().len() != padding + 16
            || layout
                .data_write_positions()
                .iter()
                .filter(|slot| slot.is_some())
                .count()
                != 1
        {
            return Err(format!("thirteen-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x13: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 13]
        {
            return Err(format!("thirteen-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(40, 13), (22, 12), (22, 14)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_twelve_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(40, 0), (176, 2), (60, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 12)?, current_profile())
            .map_err(|error| format!("seeded {byte} x12: {error:?}"))?;
        if layout.source().len() != padding + 15
            || layout
                .data_write_positions()
                .iter()
                .filter(|slot| slot.is_some())
                .count()
                != 1
        {
            return Err(format!("twelve-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x12: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 12]
        {
            return Err(format!("twelve-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(9, 12), (40, 11), (40, 13)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_eleven_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(9, 0), (8, 1), (135, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 11)?, current_profile())
            .map_err(|error| format!("seeded {byte} x11: {error:?}"))?;
        if layout.source().len() != padding + 14
            || layout
                .data_write_positions()
                .iter()
                .filter(|slot| slot.is_some())
                .count()
                != 1
        {
            return Err(format!("eleven-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x11: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 11]
        {
            return Err(format!("eleven-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(42, 11), (9, 10), (9, 12)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_ten_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(42, 0), (176, 1), (193, 25)] {
        let layout = encode_rotated_byte_literal(&source(byte, 10)?, current_profile())
            .map_err(|error| format!("seeded {byte} x10: {error:?}"))?;
        if layout.source().len() != padding + 13
            || layout
                .data_write_positions()
                .iter()
                .filter(|slot| slot.is_some())
                .count()
                != 1
        {
            return Err(format!("ten-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x10: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 10]
        {
            return Err(format!("ten-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(144, 10), (42, 9), (42, 11)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_nine_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(144, 0), (22, 1), (1, 23)] {
        let layout = encode_rotated_byte_literal(&source(byte, 9)?, current_profile())
            .map_err(|error| format!("seeded {byte} x9: {error:?}"))?;
        if layout.source().len() != padding + 12
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("nine-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x9: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; 9]
        {
            return Err(format!("nine-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(175, 9), (144, 8), (144, 10)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_eight_output_literals_preserve_guest_computation() -> Result<(), String> {
    for (byte, padding) in [(175, 0), (56, 11), (197, 24)] {
        let outputs = 8;
        let layout = encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            .map_err(|error| format!("seeded {byte} x{outputs}: {error:?}"))?;
        if layout.source().len() != padding + outputs + 3
            || layout
                .data_write_positions()
                .iter()
                .filter(|slot| slot.is_some())
                .count()
                != 1
        {
            return Err(format!("eight-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("guest {byte} x{outputs}: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != vec![byte; outputs]
        {
            return Err(format!("eight-output guest literal {byte} diverged"));
        }
    }
    for (byte, outputs) in [(10, 8), (175, 9), (197, 7)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unwitnessed literal {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
#[ignore = "full short-phase source/VM search: run optimized with --ignored"]
fn independently_rederive_three_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};

    // Finite 0..26 no-op prefixes only. This is not a claim that all 94
    // decoder phases or all 256 literal values have been synthesized.
    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::RotateData,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ]);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let [first, second, third] = vm.output() else {
            continue;
        };
        if *first != 0 && first == second && first == third {
            witnessed.push((*first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TRIPLE_ROTATION_WITNESSES {
        return Err(format!("triple source/VM witness drift: {witnessed:?}"));
    }
    Ok(())
}

#[test]
#[ignore = "bounded four-output witness scan: run optimized with --ignored"]
fn independently_rederive_four_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::RotateData,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ]);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let [first, second, third, fourth] = vm.output() else {
            continue;
        };
        if *first != 0 && first == second && first == third && first == fourth {
            witnessed.push((*first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_QUADRUPLE_ROTATION_WITNESSES {
        return Err(format!(
            "four-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded five-output witness scan: run optimized with --ignored"]
fn independently_rederive_five_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::RotateData,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ]);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let [first, second, third, fourth, fifth] = vm.output() else {
            continue;
        };
        if *first != 0 && first == second && first == third && first == fourth && first == fifth {
            witnessed.push((*first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_QUINTUPLE_ROTATION_WITNESSES {
        return Err(format!(
            "five-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded six-output rotation scan: run optimized with --ignored"]
fn independently_rederive_six_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 6));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let &[first, second, third, fourth, fifth, sixth] = vm.output() else {
            continue;
        };
        if first != 0
            && first == second
            && first == third
            && first == fourth
            && first == fifth
            && first == sixth
        {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_SEXTUPLE_ROTATION_WITNESSES {
        return Err(format!("six-output source/VM witness drift: {witnessed:?}"));
    }
    Ok(())
}

#[test]
#[ignore = "bounded seven-output rotation scan: run optimized with --ignored"]
fn independently_rederive_seven_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 7));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let &[first, second, third, fourth, fifth, sixth, seventh] = vm.output() else {
            continue;
        };
        if first != 0
            && [second, third, fourth, fifth, sixth, seventh]
                .iter()
                .all(|byte| *byte == first)
        {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_SEPTUPLE_ROTATION_WITNESSES {
        return Err(format!(
            "seven-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded eight-output rotation scan: run optimized with --ignored"]
fn independently_rederive_eight_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 8));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 7 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_OCTUPLE_ROTATION_WITNESSES {
        return Err(format!(
            "eight-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded nine-output rotation scan: run optimized with --ignored"]
fn independently_rederive_nine_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 9));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 8 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_NONUPLE_ROTATION_WITNESSES {
        return Err(format!(
            "nine-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded ten-output rotation scan: run optimized with --ignored"]
fn independently_rederive_ten_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 10));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 9 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_DECUPLE_ROTATION_WITNESSES {
        return Err(format!("ten-output source/VM witness drift: {witnessed:?}"));
    }
    Ok(())
}

#[test]
#[ignore = "bounded eleven-output rotation scan: run optimized with --ignored"]
fn independently_rederive_eleven_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 11));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 10 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_UNDECUPLE_ROTATION_WITNESSES {
        return Err(format!(
            "eleven-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twelve-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twelve_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 12));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 11 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_DODECUPLE_ROTATION_WITNESSES {
        return Err(format!(
            "twelve-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded thirteen-output rotation scan: run optimized with --ignored"]
fn independently_rederive_thirteen_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 13));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 12 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TREDECUPLE_ROTATION_WITNESSES {
        return Err(format!(
            "thirteen-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded fourteen-output rotation scan: run optimized with --ignored"]
fn independently_rederive_fourteen_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 14));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 13 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_FOURTEEN_ROTATION_WITNESSES {
        return Err(format!(
            "fourteen-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded sixteen-output rotation scan: run optimized with --ignored"]
fn independently_rederive_sixteen_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 16));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 15 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_SIXTEEN_ROTATION_WITNESSES {
        return Err(format!(
            "sixteen-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded seventeen-output rotation scan: run optimized with --ignored"]
fn independently_rederive_seventeen_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 17));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 16 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_SEVENTEEN_ROTATION_WITNESSES {
        return Err(format!(
            "seventeen-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded eighteen-output rotation scan: run optimized with --ignored"]
fn independently_rederive_eighteen_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 18));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 17 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_EIGHTEEN_ROTATION_WITNESSES {
        return Err(format!(
            "eighteen-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded nineteen-output rotation scan: run optimized with --ignored"]
fn independently_rederive_nineteen_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 19));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 18 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_NINETEEN_ROTATION_WITNESSES {
        return Err(format!(
            "nineteen-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twenty-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twenty_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 20));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 19 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TWENTY_ROTATION_WITNESSES {
        return Err(format!(
            "twenty-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twenty-one-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twenty_one_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 21));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 20 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TWENTY_ONE_ROTATION_WITNESSES {
        return Err(format!(
            "twenty-one-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twenty-two-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twenty_two_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 22));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 21 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TWENTY_TWO_ROTATION_WITNESSES {
        return Err(format!(
            "twenty-two-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twenty-three-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twenty_three_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 23));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 22 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TWENTY_THREE_ROTATION_WITNESSES {
        return Err(format!(
            "twenty-three-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded thirty-two-output rotation scan: run optimized with --ignored"]
fn independently_rederive_thirty_two_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 32));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 31 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_THIRTY_TWO_ROTATION_WITNESSES {
        return Err(format!(
            "thirty-two-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded thirty-one-output rotation scan: run optimized with --ignored"]
fn independently_rederive_thirty_one_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 31));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 30 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_THIRTY_ONE_ROTATION_WITNESSES {
        return Err(format!(
            "thirty-one-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded thirty-output rotation scan: run optimized with --ignored"]
fn independently_rederive_thirty_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 30));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 29 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_THIRTY_ROTATION_WITNESSES {
        return Err(format!(
            "thirty-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twenty-nine-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twenty_nine_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 29));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 28 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TWENTY_NINE_ROTATION_WITNESSES {
        return Err(format!(
            "twenty-nine-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twenty-eight-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twenty_eight_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 28));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 27 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TWENTY_EIGHT_ROTATION_WITNESSES {
        return Err(format!(
            "twenty-eight-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twenty-seven-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twenty_seven_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 27));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 26 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TWENTY_SEVEN_ROTATION_WITNESSES {
        return Err(format!(
            "twenty-seven-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twenty-six-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twenty_six_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 26));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 25 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TWENTY_SIX_ROTATION_WITNESSES {
        return Err(format!(
            "twenty-six-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twenty-five-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twenty_five_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 25));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 24 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TWENTY_FIVE_ROTATION_WITNESSES {
        return Err(format!(
            "twenty-five-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded twenty-four-output rotation scan: run optimized with --ignored"]
fn independently_rederive_twenty_four_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 24));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 23 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TWENTY_FOUR_ROTATION_WITNESSES {
        return Err(format!(
            "twenty-four-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}

#[test]
#[ignore = "bounded fifteen-output rotation scan: run optimized with --ignored"]
fn independently_rederive_fifteen_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};
    use std::iter::repeat_n;

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
        operations.extend(repeat_n(LinearOpcode::OutputByte, 15));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let Some((&first, rest)) = vm.output().split_first() else {
            continue;
        };
        if first != 0 && rest.len() == 14 && rest.iter().all(|byte| *byte == first) {
            witnessed.push((first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_FIFTEEN_ROTATION_WITNESSES {
        return Err(format!(
            "fifteen-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}
