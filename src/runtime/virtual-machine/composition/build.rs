// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Deterministic generation of arithmetic lookup-table source artifacts.
// - Must-Not:
//   - Read host-dependent semantic inputs or change target behavior.
// - Allows:
//   - Inputs: fixed normative ternary and rotation constants in this file.
//   - Outputs: Rust lookup-table source under Cargo OUT_DIR.
//   - Side effects: writes only Cargo-owned generated build output.
// - Split-When:
//   - Split when another generated VM artifact has an independent authority.
// - Merge-When:
//   - Merge when another VM build generator owns identical table generation.
// - Summary:
//   - Generates finite classic-Malbolge arithmetic lookup tables.
// - Description:
//   - Streams exact rotate and crazy tables into Rust source.
// - Usage:
//   - Invoked automatically by Cargo before compiling the VM library.
// - Defaults:
//   - Generation uses only fixed 1998-profile constants and deterministic
//   - loops.
//

//! Cargo generator for finite classic Malbolge arithmetic lookup tables.

use std::env;
use std::fs::File;
use std::io::{Error, ErrorKind, Result as IoResult, Write as _};
use std::path::PathBuf;

const CHUNK_TRITS: u8 = 5;
const CHUNK_VALUES: u16 = 243;
const MEMORY_WORDS: usize = 59_049;
const ROTATE_HIGH_TRIT_WEIGHT: u16 = 19_683;

const fn crazy_chunk_scalar(data: u16, accumulator: u16) -> u16 {
    let mut remaining_data = data;
    let mut remaining_accumulator = accumulator;
    let mut result = 0u16;
    let mut place = 1u16;
    let mut trit = 0u8;
    while trit < CHUNK_TRITS {
        let output = crazy_trit(
            remaining_data.rem_euclid(3),
            remaining_accumulator.rem_euclid(3),
        );
        result = result.saturating_add(output.saturating_mul(place));
        place = place.saturating_mul(3);
        remaining_data = remaining_data.div_euclid(3);
        remaining_accumulator = remaining_accumulator.div_euclid(3);
        trit = trit.saturating_add(1);
    }
    result
}

const fn crazy_trit(data: u16, accumulator: u16) -> u16 {
    if ((data == 0 || data == 1) && accumulator == 0)
        || (data == 2 && accumulator == 2)
    {
        1
    } else if (data == 1 && accumulator == 2)
        || (data == 2 && (accumulator == 0 || accumulator == 1))
    {
        2
    } else {
        0
    }
}
fn main() -> Result<(), Error> {
    let out_dir =
        env::var_os("OUT_DIR").map(PathBuf::from).ok_or_else(|| {
            Error::new(ErrorKind::NotFound, "Cargo OUT_DIR is missing")
        })?;
    let ternary_output = out_dir.join("ternary_tables.rs");
    let mut ternary_file = File::create(ternary_output)?;
    write_crazy_table(&mut ternary_file)?;

    let word_output = out_dir.join("classic_word_tables.rs");
    let mut word_file = File::create(word_output)?;
    write_rotate_table(&mut word_file)?;
    Ok(())
}

const fn rotate_scalar(value: u16) -> u16 {
    let quotient = value.div_euclid(3);
    let low_trit = value.rem_euclid(3);
    let high_trit = low_trit.saturating_mul(ROTATE_HIGH_TRIT_WEIGHT);
    quotient.saturating_add(high_trit)
}

fn write_crazy_table(file: &mut File) -> IoResult<()> {
    writeln!(file, "static CRAZY_CHUNK_TABLE: [u16; {MEMORY_WORDS}] = [")?;
    let mut data = 0u16;
    while data < CHUNK_VALUES {
        let mut accumulator = 0u16;
        while accumulator < CHUNK_VALUES {
            let value = crazy_chunk_scalar(data, accumulator);
            write!(file, "{value},")?;
            accumulator = accumulator.saturating_add(1);
        }
        writeln!(file)?;
        data = data.saturating_add(1);
    }
    writeln!(file, "];")?;
    Ok(())
}

fn write_rotate_table(file: &mut File) -> IoResult<()> {
    writeln!(file, "static ROTATE_TABLE: [u16; {MEMORY_WORDS}] = [")?;
    let mut index = 0usize;
    let mut value = 0u16;
    while index < MEMORY_WORDS {
        let rotated = rotate_scalar(value);
        write!(file, "{rotated},")?;
        index = index.saturating_add(1);
        value = value.saturating_add(1);
    }
    writeln!(file, "];")?;
    Ok(())
}
