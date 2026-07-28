// File:
//   - coff.rs
// Path:
//   - execution/native/coff.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Fail-closed structural admission of bootstrap Windows COFF objects.
// - Must-Not:
//   - Claim semantic equivalence, execute machine code, or invoke LLVM tools.
// - Allows:
//   - Inputs: untrusted native object bytes bound to an exact native target
//   - key.
//   - Outputs: structurally admitted object wrappers or typed rejection.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when ELF or Mach-O object admission gains its own format owner.
// - Merge-When:
//   - Merge when one reviewed object-format validator owns all native formats.
// - Summary:
//   - Parses COFF directly and rejects host dependencies or malformed
//   - structure.
// - Description:
//   - Confirms ISA, sections, entry symbol, relocations, and symbol closure.
// - Usage:
//   - Used after untrusted Clang bootstrap compilation and before semantics.
// - Defaults:
//   - Only Windows x86-64/AArch64 COFF objects are admitted by this module.
//
// Related documents:
// - docs/technical/adr/verification-trust-boundary.md
// - docs/technical/runtime/execution/tiered-native-execution-engine.md
//
// Large file:
//   - false
//

//! Structural Windows COFF admission for untrusted native bootstrap objects.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::str::from_utf8;

use super::UntrustedNativeObjectArtifact;
use crate::execution_cache::{HostIsa, HostOperatingSystem, NativeArtifactKey};

const COFF_HEADER_BYTES: usize = 20;
const COFF_RELOCATION_BYTES: usize = 10;
const COFF_SECTION_BYTES: usize = 40;
const COFF_SYMBOL_BYTES: usize = 18;
const IMAGE_FILE_MACHINE_AMD64: u16 = 0x8664;
const IMAGE_FILE_MACHINE_ARM64: u16 = 0xaa64;
const IMAGE_SCN_CNT_CODE: u32 = 0x0000_0020;
const IMAGE_SCN_MEM_EXECUTE: u32 = 0x2000_0000;
const IMAGE_SCN_MEM_READ: u32 = 0x4000_0000;
const IMAGE_SCN_MEM_WRITE: u32 = 0x8000_0000;
const IMAGE_SYM_CLASS_EXTERNAL: u8 = 2;
const IMAGE_SYM_DTYPE_FUNCTION: u16 = 0x0020;
const REQUIRED_ENTRY: &str = "malbolge_native_region_apply";

/// Structural rejection while inspecting one untrusted Windows COFF object.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CoffAdmissionError {
    /// Object bytes end before a declared structure or table is complete.
    Bounds,
    /// The required native region entry symbol is absent or duplicated.
    EntrySymbol,
    /// The required entry is not defined inside executable `.text`.
    EntryTarget,
    /// A relocation or symbol refers to a malformed/undefined symbol.
    ExternalDependency,
    /// Object contains an external function other than the required entry.
    ExtraExternalFunction,
    /// COFF machine identity disagrees with the native target key.
    Machine,
    /// Object header includes an executable-image optional header.
    OptionalHeader,
    /// This validator only admits Windows COFF target identities.
    TargetFormat,
    /// Object does not contain one usable `.text` section.
    TextSection,
}

impl Display for CoffAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Bounds => "COFF structure exceeds object bounds",
            Self::EntrySymbol => {
                "required native entry symbol is missing or duplicated"
            },
            Self::EntryTarget => {
                "native entry is not defined inside executable .text"
            },
            Self::ExternalDependency => {
                "COFF object depends on an undefined external symbol"
            },
            Self::ExtraExternalFunction => {
                "COFF object exports an unexpected external function"
            },
            Self::Machine => {
                "COFF machine does not match native target identity"
            },
            Self::OptionalHeader => {
                "COFF bootstrap object must not contain an optional header"
            },
            Self::TargetFormat => {
                "COFF admission requires a Windows native target"
            },
            Self::TextSection => {
                "COFF object lacks one non-writable executable .text section"
            },
        })
    }
}

/// Object whose COFF container is closed/self-contained but not semantically
/// verified.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StructurallyAdmittedNativeObjectArtifact {
    artifact: UntrustedNativeObjectArtifact,
}

impl StructurallyAdmittedNativeObjectArtifact {
    /// Returns the complete cache/native identity claimed by this object.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the structurally admitted but semantically untrusted COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the Clang target triple associated with this object claim.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

#[derive(Clone, Debug)]
struct CoffSection {
    characteristics: u32,
    name: String,
    raw_size: usize,
    raw_start: usize,
    relocation_count: usize,
    relocation_start: usize,
}

#[derive(Clone, Debug)]
struct CoffSymbol {
    name: String,
    section_number: i16,
    storage_class: u8,
    symbol_type: u16,
    value: u32,
}

#[derive(Debug)]
struct ParsedCoff {
    sections: Vec<CoffSection>,
    symbols: SymbolSlots,
}

#[derive(Clone, Copy, Debug)]
struct StringTable {
    bytes: usize,
    start: usize,
}

type SymbolSlots = Vec<Option<CoffSymbol>>;

/// Parses and structurally admits one self-contained Windows COFF candidate.
///
/// Structural admission verifies object-format closure only. It does not prove
/// that compiler-produced machine code implements the claimed region effects.
///
/// # Errors
///
/// Returns [`CoffAdmissionError`] for malformed objects, target mismatches,
/// undefined host dependencies, or a missing/unexpected callable surface.
pub fn structurally_admit_coff(
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<StructurallyAdmittedNativeObjectArtifact, CoffAdmissionError> {
    let target = artifact.key().target();
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(CoffAdmissionError::TargetFormat);
    }
    let object = artifact.object();
    let machine = read_u16(object, 0)?;
    if machine != expected_machine(target.host_isa()) {
        return Err(CoffAdmissionError::Machine);
    }
    if read_u16(object, 16)? != 0 {
        return Err(CoffAdmissionError::OptionalHeader);
    }
    let parsed = parse_coff(object)?;
    validate_sections(object, &parsed.sections)?;
    validate_symbols_and_relocations(object, &parsed)?;
    Ok(StructurallyAdmittedNativeObjectArtifact {
        artifact: artifact.clone(),
    })
}

const fn expected_machine(isa: HostIsa) -> u16 {
    match isa {
        HostIsa::AArch64 => IMAGE_FILE_MACHINE_ARM64,
        HostIsa::X86_64 => IMAGE_FILE_MACHINE_AMD64,
    }
}

fn parse_coff(object: &[u8]) -> Result<ParsedCoff, CoffAdmissionError> {
    require_range(object, 0, COFF_HEADER_BYTES)?;
    let section_count = usize::from(read_u16(object, 2)?);
    let symbol_table = usize_from_u32(read_u32(object, 8)?)?;
    let symbol_count = usize_from_u32(read_u32(object, 12)?)?;
    let optional_header = usize::from(read_u16(object, 16)?);
    let section_start = checked_add(COFF_HEADER_BYTES, optional_header)?;
    let section_bytes = checked_mul(section_count, COFF_SECTION_BYTES)?;
    require_range(object, section_start, section_bytes)?;

    let symbol_bytes = checked_mul(symbol_count, COFF_SYMBOL_BYTES)?;
    require_range(object, symbol_table, symbol_bytes)?;
    let string_table = checked_add(symbol_table, symbol_bytes)?;
    let string_bytes = parse_string_table_length(object, string_table)?;
    require_range(object, string_table, string_bytes)?;
    let strings = StringTable {
        bytes: string_bytes,
        start: string_table,
    };

    let sections =
        parse_sections(object, section_start, section_count, strings)?;
    let symbols = parse_symbols(object, symbol_table, symbol_count, strings)?;
    Ok(ParsedCoff { sections, symbols })
}

fn parse_sections(
    object: &[u8],
    start: usize,
    count: usize,
    strings: StringTable,
) -> Result<Vec<CoffSection>, CoffAdmissionError> {
    let mut sections = Vec::with_capacity(count);
    for index in 0..count {
        let offset =
            checked_add(start, checked_mul(index, COFF_SECTION_BYTES)?)?;
        let name = parse_section_name(object, offset, strings)?;
        let raw_size =
            usize_from_u32(read_u32(object, checked_add(offset, 16)?)?)?;
        let raw_start =
            usize_from_u32(read_u32(object, checked_add(offset, 20)?)?)?;
        let relocation_start =
            usize_from_u32(read_u32(object, checked_add(offset, 24)?)?)?;
        let relocation_count =
            usize::from(read_u16(object, checked_add(offset, 32)?)?);
        let characteristics = read_u32(object, checked_add(offset, 36)?)?;
        sections.push(CoffSection {
            characteristics,
            name,
            raw_size,
            raw_start,
            relocation_count,
            relocation_start,
        });
    }
    Ok(sections)
}

fn parse_symbols(
    object: &[u8],
    start: usize,
    count: usize,
    strings: StringTable,
) -> Result<SymbolSlots, CoffAdmissionError> {
    let mut symbols = vec![None; count];
    let mut raw_index = 0usize;
    while raw_index < count {
        let offset =
            checked_add(start, checked_mul(raw_index, COFF_SYMBOL_BYTES)?)?;
        let name = parse_symbol_name(object, offset, strings)?;
        let value = read_u32(object, checked_add(offset, 8)?)?;
        let section_number = read_i16(object, checked_add(offset, 12)?)?;
        let symbol_type = read_u16(object, checked_add(offset, 14)?)?;
        let storage_class = read_u8(object, checked_add(offset, 16)?)?;
        let aux_count = usize::from(read_u8(object, checked_add(offset, 17)?)?);
        let slot = symbols
            .get_mut(raw_index)
            .ok_or(CoffAdmissionError::Bounds)?;
        *slot = Some(CoffSymbol {
            name,
            section_number,
            storage_class,
            symbol_type,
            value,
        });
        raw_index = checked_add(raw_index, checked_add(aux_count, 1)?)?;
        if raw_index > count {
            return Err(CoffAdmissionError::Bounds);
        }
    }
    Ok(symbols)
}

fn validate_sections(
    object: &[u8],
    sections: &[CoffSection],
) -> Result<(), CoffAdmissionError> {
    let mut text_count = 0usize;
    for section in sections {
        if section.raw_size != 0 {
            require_range(object, section.raw_start, section.raw_size)?;
        }
        if section.relocation_count != 0 {
            let bytes =
                checked_mul(section.relocation_count, COFF_RELOCATION_BYTES)?;
            require_range(object, section.relocation_start, bytes)?;
        }
        if section.name == ".text" {
            text_count = text_count.saturating_add(1);
            let required =
                IMAGE_SCN_CNT_CODE | IMAGE_SCN_MEM_EXECUTE | IMAGE_SCN_MEM_READ;
            if section.raw_size == 0
                || section.characteristics & required != required
                || section.characteristics & IMAGE_SCN_MEM_WRITE != 0
            {
                return Err(CoffAdmissionError::TextSection);
            }
        }
        if section.characteristics & IMAGE_SCN_MEM_EXECUTE != 0
            && section.characteristics & IMAGE_SCN_MEM_WRITE != 0
        {
            return Err(CoffAdmissionError::TextSection);
        }
    }
    if text_count == 1 {
        Ok(())
    } else {
        Err(CoffAdmissionError::TextSection)
    }
}

fn validate_symbols_and_relocations(
    object: &[u8],
    parsed: &ParsedCoff,
) -> Result<(), CoffAdmissionError> {
    let text_index = parsed
        .sections
        .iter()
        .position(|section| section.name == ".text")
        .ok_or(CoffAdmissionError::TextSection)?;
    let text_section_number = i16::try_from(text_index.saturating_add(1))
        .map_err(|_error| CoffAdmissionError::Bounds)?;
    let text = parsed
        .sections
        .get(text_index)
        .ok_or(CoffAdmissionError::TextSection)?;
    let mut entry_count = 0usize;

    for symbol in parsed.symbols.iter().flatten() {
        if symbol.storage_class != IMAGE_SYM_CLASS_EXTERNAL {
            continue;
        }
        if symbol.section_number == 0 {
            return Err(CoffAdmissionError::ExternalDependency);
        }
        if symbol.symbol_type & IMAGE_SYM_DTYPE_FUNCTION != 0 {
            if symbol.name != REQUIRED_ENTRY {
                return Err(CoffAdmissionError::ExtraExternalFunction);
            }
            entry_count = entry_count.saturating_add(1);
            let value = usize_from_u32(symbol.value)?;
            if symbol.section_number != text_section_number
                || value >= text.raw_size
            {
                return Err(CoffAdmissionError::EntryTarget);
            }
        }
    }
    if entry_count != 1 {
        return Err(CoffAdmissionError::EntrySymbol);
    }

    for section in &parsed.sections {
        for relocation_index in 0..section.relocation_count {
            let offset = checked_add(
                section.relocation_start,
                checked_mul(relocation_index, COFF_RELOCATION_BYTES)?,
            )?;
            let symbol_index =
                usize_from_u32(read_u32(object, checked_add(offset, 4)?)?)?;
            let symbol = parsed
                .symbols
                .get(symbol_index)
                .and_then(Option::as_ref)
                .ok_or(CoffAdmissionError::ExternalDependency)?;
            if symbol.section_number == 0 {
                return Err(CoffAdmissionError::ExternalDependency);
            }
        }
    }
    Ok(())
}

fn parse_section_name(
    object: &[u8],
    offset: usize,
    strings: StringTable,
) -> Result<String, CoffAdmissionError> {
    let raw = slice(object, offset, 8)?;
    if raw.first() == Some(&b'/') {
        let digits = trim_nul(raw.get(1..).ok_or(CoffAdmissionError::Bounds)?);
        let text =
            from_utf8(digits).map_err(|_error| CoffAdmissionError::Bounds)?;
        let relative = text
            .parse::<usize>()
            .map_err(|_error| CoffAdmissionError::Bounds)?;
        return parse_string(object, strings, relative);
    }
    parse_inline_name(raw)
}

fn parse_symbol_name(
    object: &[u8],
    offset: usize,
    strings: StringTable,
) -> Result<String, CoffAdmissionError> {
    let raw = slice(object, offset, 8)?;
    let first = read_u32(raw, 0)?;
    if first == 0 {
        let relative = usize_from_u32(read_u32(raw, 4)?)?;
        parse_string(object, strings, relative)
    } else {
        parse_inline_name(raw)
    }
}

fn parse_inline_name(raw: &[u8]) -> Result<String, CoffAdmissionError> {
    let bytes = trim_nul(raw);
    let text = from_utf8(bytes).map_err(|_error| CoffAdmissionError::Bounds)?;
    Ok(String::from(text))
}

fn parse_string(
    object: &[u8],
    strings: StringTable,
    relative: usize,
) -> Result<String, CoffAdmissionError> {
    if relative < 4 || relative >= strings.bytes {
        return Err(CoffAdmissionError::Bounds);
    }
    let start = checked_add(strings.start, relative)?;
    let table_end = checked_add(strings.start, strings.bytes)?;
    let remainder = object
        .get(start..table_end)
        .ok_or(CoffAdmissionError::Bounds)?;
    let length = remainder
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(remainder.len());
    let bytes = remainder.get(..length).ok_or(CoffAdmissionError::Bounds)?;
    let text = from_utf8(bytes).map_err(|_error| CoffAdmissionError::Bounds)?;
    Ok(String::from(text))
}

fn parse_string_table_length(
    object: &[u8],
    start: usize,
) -> Result<usize, CoffAdmissionError> {
    let length = usize_from_u32(read_u32(object, start)?)?;
    if length < 4 {
        return Err(CoffAdmissionError::Bounds);
    }
    Ok(length)
}

const fn checked_add(
    left: usize,
    right: usize,
) -> Result<usize, CoffAdmissionError> {
    match left.checked_add(right) {
        Some(value) => Ok(value),
        None => Err(CoffAdmissionError::Bounds),
    }
}

const fn checked_mul(
    left: usize,
    right: usize,
) -> Result<usize, CoffAdmissionError> {
    match left.checked_mul(right) {
        Some(value) => Ok(value),
        None => Err(CoffAdmissionError::Bounds),
    }
}

fn read_i16(object: &[u8], offset: usize) -> Result<i16, CoffAdmissionError> {
    let bytes = slice(object, offset, 2)?;
    let array = <[u8; 2]>::try_from(bytes)
        .map_err(|_error| CoffAdmissionError::Bounds)?;
    Ok(i16::from_le_bytes(array))
}

fn read_u16(object: &[u8], offset: usize) -> Result<u16, CoffAdmissionError> {
    let bytes = slice(object, offset, 2)?;
    let array = <[u8; 2]>::try_from(bytes)
        .map_err(|_error| CoffAdmissionError::Bounds)?;
    Ok(u16::from_le_bytes(array))
}

fn read_u32(object: &[u8], offset: usize) -> Result<u32, CoffAdmissionError> {
    let bytes = slice(object, offset, 4)?;
    let array = <[u8; 4]>::try_from(bytes)
        .map_err(|_error| CoffAdmissionError::Bounds)?;
    Ok(u32::from_le_bytes(array))
}

fn read_u8(object: &[u8], offset: usize) -> Result<u8, CoffAdmissionError> {
    object
        .get(offset)
        .copied()
        .ok_or(CoffAdmissionError::Bounds)
}

fn require_range(
    object: &[u8],
    start: usize,
    length: usize,
) -> Result<(), CoffAdmissionError> {
    let end = checked_add(start, length)?;
    if end <= object.len() {
        Ok(())
    } else {
        Err(CoffAdmissionError::Bounds)
    }
}

fn slice(
    object: &[u8],
    start: usize,
    length: usize,
) -> Result<&[u8], CoffAdmissionError> {
    let end = checked_add(start, length)?;
    object.get(start..end).ok_or(CoffAdmissionError::Bounds)
}

fn trim_nul(bytes: &[u8]) -> &[u8] {
    let length = bytes
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(bytes.len());
    bytes.get(..length).unwrap_or(bytes)
}

fn usize_from_u32(value: u32) -> Result<usize, CoffAdmissionError> {
    usize::try_from(value).map_err(|_error| CoffAdmissionError::Bounds)
}
