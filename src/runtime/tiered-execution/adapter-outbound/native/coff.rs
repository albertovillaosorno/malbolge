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
//   - Fail-closed structural admission of untrusted Windows COFF objects.
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
//   - Used after untrusted object emission and before semantic admission.
// - Defaults:
//   - Only Windows x86-64/AArch64 COFF objects are admitted by this module.
//

//! Structural Windows COFF admission for untrusted native objects.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::str::from_utf8;

use super::profile_metadata::{
    PROFILE_METADATA_SECTION, canonical_profile_metadata,
};
use super::{
    CLANG_C23_BOOTSTRAP_BACKEND_ID, CLANG_C23_BOOTSTRAP_BACKEND_REVISION,
    UntrustedNativeObjectArtifact,
};
use crate::execution_cache::{HostIsa, HostOperatingSystem, NativeArtifactKey};

const COFF_ENTRYSYMBOL_MESSAGE: &str =
    "required native entry symbol is missing or duplicated";
const COFF_ENTRYTARGET_MESSAGE: &str =
    "native entry is not defined inside executable .text";
const COFF_EXTERNALDEPENDENCY_MESSAGE: &str =
    "COFF object references an undefined or invalid symbol";
const COFF_EXTRAEXTERNALFUNCTION_MESSAGE: &str =
    "COFF object exports an unexpected external function";
const COFF_FILECHARACTERISTICS_MESSAGE: &str =
    "COFF object claims executable-image file attributes";
const COFF_MACHINE_MESSAGE: &str =
    "COFF machine does not match native target identity";
const COFF_OPTIONALHEADER_MESSAGE: &str =
    "COFF bootstrap object must not contain an optional header";
const COFF_PROFILEMETADATA_MESSAGE: &str =
    "COFF profile metadata is absent, malformed, or mismatched";
const COFF_HEADER_BYTES: usize = 20;
const COFF_RELOCATION_BYTES: usize = 10;
const COFF_SECTION_BYTES: usize = 40;
const COFF_SYMBOL_BYTES: usize = 18;
const IMAGE_FILE_MACHINE_AMD64: u16 = 0x8664;
const IMAGE_FILE_MACHINE_ARM64: u16 = 0xaa64;
// These flags describe images, obsolete stripped/byte-swapped object forms,
// or reserved characteristics. Admission does not delegate their semantics.
const IMAGE_FILE_INCOMPATIBLE_FLAGS: u16 = 0x0001
    | 0x0002
    | 0x0004
    | 0x0008
    | 0x0010
    | 0x0020
    | 0x0040
    | 0x0080
    | 0x0100
    | 0x0200
    | 0x0400
    | 0x0800
    | 0x1000
    | 0x2000
    | 0x4000
    | 0x8000;
const IMAGE_SCN_ALIGN_MASK: u32 = 0x00f0_0000;
const IMAGE_SCN_CNT_CODE: u32 = 0x0000_0020;
const IMAGE_SCN_CNT_INITIALIZED_DATA: u32 = 0x0000_0040;
const IMAGE_SCN_CNT_UNINITIALIZED_DATA: u32 = 0x0000_0080;
const IMAGE_SCN_LNK_COMDAT: u32 = 0x0000_1000;
const IMAGE_SCN_LNK_INFO: u32 = 0x0000_0200;
const IMAGE_SCN_LNK_NRELOC_OVFL: u32 = 0x0100_0000;
const IMAGE_SCN_LNK_REMOVE: u32 = 0x0000_0800;
const IMAGE_SCN_MEM_DISCARDABLE: u32 = 0x0200_0000;
const IMAGE_SCN_MEM_IMAGE_POLICY_FLAGS: u32 =
    0x0400_0000 | 0x0800_0000 | 0x1000_0000;
const IMAGE_SCN_LEGACY_LOAD_FLAGS: u32 =
    0x0000_0002 | 0x0002_0000 | 0x0004_0000 | 0x0008_0000;
const IMAGE_SCN_UNSUPPORTED_SECTION_FLAGS: u32 =
    0x0000_0008 | 0x0000_0100 | 0x0000_8000;
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
    /// Object file illegally claims image-only COFF characteristics.
    FileCharacteristics,
    /// Two separately owned COFF file regions overlap on disk.
    LayoutOverlap,
    /// Deprecated COFF line-number records are not structurally supported.
    LineNumbers,
    /// COFF machine identity disagrees with the native target key.
    Machine,
    /// Object header includes an executable-image optional header.
    OptionalHeader,
    /// Required profile metadata is absent, malformed, or mismatched.
    ProfileMetadata,
    /// Extended relocation counts are unsupported by the bounded parser.
    RelocationOverflow,
    /// Span-dependent x64 relocations require linker-owned pairs.
    RelocationPair,
    /// Relocation count and table pointer disagree about table presence.
    RelocationPointer,
    /// A relocation type is undefined for the claimed COFF machine.
    RelocationType,
    /// Section characteristics use the reserved alignment encoding.
    SectionAlignment,
    /// A section claims multiple incompatible content kinds.
    SectionContent,
    /// An auxiliary section requires unsupported linker selection semantics.
    SectionLinkage,
    /// Raw section size and file-data pointer disagree about byte ownership.
    SectionPointer,
    /// The image-only section virtual-size field is nonzero.
    SectionVirtualSize,
    /// A referenced long name begins inside another string-table entry.
    StringTableOffset,
    /// A defined symbol offset exceeds its populated owning section.
    SymbolValue,
    /// This validator only admits Windows COFF target identities.
    TargetFormat,
    /// Object does not contain one usable `.text` section.
    TextSection,
    /// File has nonzero interior padding or unowned trailing bytes.
    UnownedBytes,
}

/// Rejection while extracting a relocation-free executable text image.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) enum CoffExecutableTextError {
    /// The COFF container failed ordinary structural closure checks.
    Admission(CoffAdmissionError),
    /// The object requires relocation processing not owned by this loader.
    Relocations,
}

/// Owned executable `.text` plus its validated entry offset.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(super) struct CoffExecutableText {
    pub(super) code: Box<[u8]>,
    pub(super) entry_offset: usize,
}

impl Display for CoffAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Bounds => "COFF structure exceeds object bounds",
            Self::EntrySymbol => COFF_ENTRYSYMBOL_MESSAGE,
            Self::EntryTarget => COFF_ENTRYTARGET_MESSAGE,
            Self::ExternalDependency => COFF_EXTERNALDEPENDENCY_MESSAGE,
            Self::ExtraExternalFunction => COFF_EXTRAEXTERNALFUNCTION_MESSAGE,
            Self::FileCharacteristics => COFF_FILECHARACTERISTICS_MESSAGE,
            Self::LayoutOverlap => "COFF file regions overlap",
            Self::LineNumbers => "COFF line-number records are unsupported",
            Self::Machine => COFF_MACHINE_MESSAGE,
            Self::OptionalHeader => COFF_OPTIONALHEADER_MESSAGE,
            Self::ProfileMetadata => COFF_PROFILEMETADATA_MESSAGE,
            Self::RelocationOverflow => {
                "COFF extended relocation counts are unsupported"
            },
            Self::RelocationPair => {
                "COFF span-dependent relocation pairs are unsupported"
            },
            Self::RelocationPointer => {
                "COFF relocation count and table pointer disagree"
            },
            Self::RelocationType => {
                "COFF relocation type is invalid for the native machine"
            },
            Self::SectionAlignment => "COFF uses reserved section alignment",
            Self::SectionContent => {
                "COFF section has conflicting content kinds"
            },
            Self::SectionLinkage => "COFF section requires linker selection",
            Self::SectionPointer => "COFF section raw-size/pointer mismatch",
            Self::SectionVirtualSize => {
                "COFF object section declares image-only virtual size"
            },
            Self::StringTableOffset => {
                "COFF long-name offset is not a string start"
            },
            Self::SymbolValue => {
                "COFF defined symbol exceeds its raw section extent"
            },
            Self::TargetFormat => {
                "COFF admission requires a Windows native target"
            },
            Self::TextSection => {
                "COFF object lacks one non-writable executable .text section"
            },
            Self::UnownedBytes => "COFF object has unowned non-padding bytes",
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
    virtual_address: u32,
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

/// Extracts one closed relocation-free executable `.text` image.
///
/// # Errors
///
/// Returns [`CoffExecutableTextError`] for malformed structure, target drift,
/// unresolved closure, or any relocation owned by no current loader.
pub(super) fn extract_relocation_free_executable_text(
    object: &[u8],
    isa: HostIsa,
) -> Result<CoffExecutableText, CoffExecutableTextError> {
    if read_u16(object, 0).map_err(CoffExecutableTextError::Admission)?
        != expected_machine(isa)
    {
        return Err(CoffExecutableTextError::Admission(
            CoffAdmissionError::Machine,
        ));
    }
    if read_u16(object, 16).map_err(CoffExecutableTextError::Admission)? != 0 {
        return Err(CoffExecutableTextError::Admission(
            CoffAdmissionError::OptionalHeader,
        ));
    }
    validate_file_characteristics(object)
        .map_err(CoffExecutableTextError::Admission)?;
    let parsed =
        parse_coff(object).map_err(CoffExecutableTextError::Admission)?;
    validate_sections(object, &parsed.sections)
        .map_err(CoffExecutableTextError::Admission)?;
    validate_coff_layout(object, &parsed)
        .map_err(CoffExecutableTextError::Admission)?;
    validate_symbols_and_relocations(object, &parsed)
        .map_err(CoffExecutableTextError::Admission)?;
    if parsed
        .sections
        .iter()
        .any(|section| section.relocation_count != 0)
    {
        return Err(CoffExecutableTextError::Relocations);
    }
    let text = parsed
        .sections
        .iter()
        .find(|section| section.name == ".text")
        .ok_or(CoffExecutableTextError::Admission(
            CoffAdmissionError::TextSection,
        ))?;
    let entry_offset = required_entry_offset(&parsed)
        .map_err(CoffExecutableTextError::Admission)?;
    let code = slice(object, text.raw_start, text.raw_size)
        .map_err(CoffExecutableTextError::Admission)?
        .into();
    Ok(CoffExecutableText { code, entry_offset })
}

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
    validate_file_characteristics(object)?;
    let parsed = parse_coff(object)?;
    validate_sections(object, &parsed.sections)?;
    validate_coff_layout(object, &parsed)?;
    validate_profile_metadata(object, &parsed.sections, artifact.key())?;
    validate_symbols_and_relocations(object, &parsed)?;
    Ok(StructurallyAdmittedNativeObjectArtifact {
        artifact: artifact.clone(),
    })
}

fn validate_file_characteristics(
    object: &[u8],
) -> Result<(), CoffAdmissionError> {
    let flags = read_u16(object, 18)?;
    if flags & IMAGE_FILE_INCOMPATIBLE_FLAGS != 0 {
        return Err(CoffAdmissionError::FileCharacteristics);
    }
    Ok(())
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
    // The table contains NUL-terminated names, including unreferenced
    // entries. A declared trailing fragment cannot remain unterminated.
    if string_bytes > 4
        && object
            .get(checked_add(string_table, string_bytes.saturating_sub(1))?)
            != Some(&0u8)
    {
        return Err(CoffAdmissionError::Bounds);
    }
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
        // VirtualSize describes a loaded PE image, not a COFF object.
        // Object sections must use raw-size geometry instead.
        if read_u32(object, checked_add(offset, 8)?)? != 0 {
            return Err(CoffAdmissionError::SectionVirtualSize);
        }
        let virtual_address = read_u32(object, checked_add(offset, 12)?)?;
        let raw_size =
            usize_from_u32(read_u32(object, checked_add(offset, 16)?)?)?;
        let raw_start =
            usize_from_u32(read_u32(object, checked_add(offset, 20)?)?)?;
        let relocation_start =
            usize_from_u32(read_u32(object, checked_add(offset, 24)?)?)?;
        let relocation_count =
            usize::from(read_u16(object, checked_add(offset, 32)?)?);
        // COFF line-number debug records have no validator or ownership in
        // this execution format. Ignore neither an advertised count nor an
        // orphaned file pointer: each would leave untrusted bytes unchecked.
        if read_u32(object, checked_add(offset, 28)?)? != 0
            || read_u16(object, checked_add(offset, 34)?)? != 0
        {
            return Err(CoffAdmissionError::LineNumbers);
        }
        let characteristics = read_u32(object, checked_add(offset, 36)?)?;
        sections.push(CoffSection {
            characteristics,
            name,
            raw_size,
            raw_start,
            relocation_count,
            relocation_start,
            virtual_address,
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
        validate_section_storage(object, section)?;
        validate_metadata_section_flags(section)?;
        if section.name == ".text" {
            text_count = text_count.saturating_add(1);
            validate_required_text_section_flags(section)?;
        }
        validate_section_content_flags(section)?;
        if section.characteristics & IMAGE_SCN_UNSUPPORTED_SECTION_FLAGS != 0 {
            return Err(CoffAdmissionError::SectionLinkage);
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

fn validate_section_storage(
    object: &[u8],
    section: &CoffSection,
) -> Result<(), CoffAdmissionError> {
    // Alignment codes 1..=14 are defined in PE/COFF. The all-ones
    // code 15 is reserved, not a valid requested section alignment.
    if section.characteristics & IMAGE_SCN_ALIGN_MASK == IMAGE_SCN_ALIGN_MASK {
        return Err(CoffAdmissionError::SectionAlignment);
    }
    // The overflow flag makes the first relocation a count record,
    // rather than the symbol relocation parsed by this bounded reader.
    if section.characteristics & IMAGE_SCN_LNK_NRELOC_OVFL != 0 {
        return Err(CoffAdmissionError::RelocationOverflow);
    }
    // A zero relocation count must not advertise an orphan pointer;
    // likewise, real relocation records require a nonzero table pointer.
    if (section.relocation_count == 0) != (section.relocation_start == 0) {
        return Err(CoffAdmissionError::RelocationPointer);
    }
    // Some COFF compilers preserve an in-file raw pointer even for a
    // zero-size section. Such a pointer owns no bytes but cannot extend
    // outside this object. Populated sections cannot begin at byte zero.
    if section.raw_size == 0 {
        if section.raw_start > object.len() {
            return Err(CoffAdmissionError::Bounds);
        }
    } else {
        if section.raw_start == 0 {
            return Err(CoffAdmissionError::SectionPointer);
        }
        require_range(object, section.raw_start, section.raw_size)?;
    }
    if section.relocation_count != 0 {
        let bytes =
            checked_mul(section.relocation_count, COFF_RELOCATION_BYTES)?;
        require_range(object, section.relocation_start, bytes)?;
    }
    Ok(())
}

const fn validate_required_text_section_flags(
    section: &CoffSection,
) -> Result<(), CoffAdmissionError> {
    let required =
        IMAGE_SCN_CNT_CODE | IMAGE_SCN_MEM_EXECUTE | IMAGE_SCN_MEM_READ;
    let forbidden = IMAGE_SCN_CNT_INITIALIZED_DATA
        | IMAGE_SCN_CNT_UNINITIALIZED_DATA
        | IMAGE_SCN_MEM_WRITE
        | IMAGE_SCN_MEM_DISCARDABLE
        | IMAGE_SCN_MEM_IMAGE_POLICY_FLAGS
        | IMAGE_SCN_LEGACY_LOAD_FLAGS
        | IMAGE_SCN_UNSUPPORTED_SECTION_FLAGS
        | IMAGE_SCN_LNK_COMDAT
        | IMAGE_SCN_LNK_INFO
        | IMAGE_SCN_LNK_REMOVE;
    if section.raw_size == 0
        || section.characteristics & required != required
        || section.characteristics & forbidden != 0
    {
        Err(CoffAdmissionError::TextSection)
    } else {
        Ok(())
    }
}

const fn validate_section_content_flags(
    section: &CoffSection,
) -> Result<(), CoffAdmissionError> {
    // PE/COFF content kinds are mutually exclusive. Linker/bookkeeping
    // sections may omit content kinds entirely.
    let kinds = section.characteristics
        & (IMAGE_SCN_CNT_CODE
            | IMAGE_SCN_CNT_INITIALIZED_DATA
            | IMAGE_SCN_CNT_UNINITIALIZED_DATA);
    let data_kinds =
        IMAGE_SCN_CNT_INITIALIZED_DATA | IMAGE_SCN_CNT_UNINITIALIZED_DATA;
    if (kinds & IMAGE_SCN_CNT_UNINITIALIZED_DATA != 0 && section.raw_size != 0)
        || kinds.count_ones() > 1
        || (kinds & data_kinds != 0
            && section.characteristics & IMAGE_SCN_MEM_EXECUTE != 0)
        || (kinds & IMAGE_SCN_CNT_INITIALIZED_DATA != 0
            && section.raw_size != 0
            && section.characteristics & IMAGE_SCN_MEM_READ == 0)
        || (kinds & IMAGE_SCN_CNT_INITIALIZED_DATA != 0
            && section.raw_size != 0
            && section.characteristics
                & (IMAGE_SCN_LEGACY_LOAD_FLAGS
                    | IMAGE_SCN_MEM_IMAGE_POLICY_FLAGS)
                != 0)
    {
        Err(CoffAdmissionError::SectionContent)
    } else {
        Ok(())
    }
}

fn validate_metadata_section_flags(
    section: &CoffSection,
) -> Result<(), CoffAdmissionError> {
    // Profile identity must remain initialized, readable, and non-writable
    // in both structural admission and relocation-free text extraction.
    if section.name == PROFILE_METADATA_SECTION {
        let required = IMAGE_SCN_CNT_INITIALIZED_DATA | IMAGE_SCN_MEM_READ;
        let forbidden = IMAGE_SCN_CNT_CODE
            | IMAGE_SCN_CNT_UNINITIALIZED_DATA
            | IMAGE_SCN_LNK_COMDAT
            | IMAGE_SCN_LNK_INFO
            | IMAGE_SCN_LNK_REMOVE
            | IMAGE_SCN_MEM_DISCARDABLE
            | IMAGE_SCN_MEM_IMAGE_POLICY_FLAGS
            | IMAGE_SCN_LEGACY_LOAD_FLAGS
            | IMAGE_SCN_UNSUPPORTED_SECTION_FLAGS
            | IMAGE_SCN_MEM_EXECUTE
            | IMAGE_SCN_MEM_WRITE;
        if section.raw_size == 0
            || section.relocation_count != 0
            || section.characteristics & required != required
            || section.characteristics & forbidden != 0
        {
            return Err(CoffAdmissionError::ProfileMetadata);
        }
    }
    Ok(())
}

fn requires_profile_metadata(key: &NativeArtifactKey) -> bool {
    let target = key.target();
    target.backend_id().starts_with("direct-")
        || (target.backend_id() == CLANG_C23_BOOTSTRAP_BACKEND_ID
            && target.backend_revision()
                >= CLANG_C23_BOOTSTRAP_BACKEND_REVISION)
}

fn validate_profile_metadata(
    object: &[u8],
    sections: &[CoffSection],
    key: &NativeArtifactKey,
) -> Result<(), CoffAdmissionError> {
    let mut matches = sections
        .iter()
        .filter(|section| section.name == PROFILE_METADATA_SECTION);
    let metadata_section = matches.next();
    if matches.next().is_some() {
        return Err(CoffAdmissionError::ProfileMetadata);
    }
    let Some(metadata) = metadata_section else {
        if requires_profile_metadata(key) {
            return Err(CoffAdmissionError::ProfileMetadata);
        }
        return Ok(());
    };
    let required = IMAGE_SCN_CNT_INITIALIZED_DATA | IMAGE_SCN_MEM_READ;
    if metadata.raw_size == 0
        || metadata.relocation_count != 0
        || metadata.characteristics & required != required
        || metadata.characteristics
            & (IMAGE_SCN_CNT_CODE
                | IMAGE_SCN_CNT_UNINITIALIZED_DATA
                | IMAGE_SCN_MEM_EXECUTE
                | IMAGE_SCN_MEM_WRITE)
            != 0
    {
        return Err(CoffAdmissionError::ProfileMetadata);
    }
    let observed = slice(object, metadata.raw_start, metadata.raw_size)?;
    let expected = canonical_profile_metadata(key)
        .ok_or(CoffAdmissionError::ProfileMetadata)?;
    if observed == expected {
        Ok(())
    } else {
        Err(CoffAdmissionError::ProfileMetadata)
    }
}

fn required_entry_offset(
    parsed: &ParsedCoff,
) -> Result<usize, CoffAdmissionError> {
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
    let mut entry_offset = None;
    for symbol in parsed.symbols.iter().flatten() {
        if symbol.storage_class != IMAGE_SYM_CLASS_EXTERNAL {
            continue;
        }
        if symbol.section_number == 0 {
            return Err(CoffAdmissionError::ExternalDependency);
        }
        // The callable entry must be the exact COFF function type, not a
        // different base/derived type which happens to set the function bit.
        if symbol.name == REQUIRED_ENTRY
            && symbol.symbol_type != IMAGE_SYM_DTYPE_FUNCTION
        {
            return Err(CoffAdmissionError::EntryTarget);
        }
        if symbol.symbol_type & IMAGE_SYM_DTYPE_FUNCTION == 0 {
            continue;
        }
        if symbol.name != REQUIRED_ENTRY {
            return Err(CoffAdmissionError::ExtraExternalFunction);
        }
        if entry_offset.is_some() {
            return Err(CoffAdmissionError::EntrySymbol);
        }
        let value = usize_from_u32(symbol.value)?;
        if symbol.section_number != text_section_number
            || value >= text.raw_size
        {
            return Err(CoffAdmissionError::EntryTarget);
        }
        entry_offset = Some(value);
    }
    entry_offset.ok_or(CoffAdmissionError::EntrySymbol)
}

fn validate_symbol_sections(
    object: &[u8],
    parsed: &ParsedCoff,
) -> Result<(), CoffAdmissionError> {
    let table = usize_from_u32(read_u32(object, 8)?)?;
    for (symbol_index, candidate) in parsed.symbols.iter().enumerate() {
        let Some(symbol) = candidate else {
            continue;
        };
        // Every symbol, including unreferenced static symbols, must carry
        // either a real one-based section or one of COFF's three sentinels:
        // UNDEFINED (0), ABSOLUTE (-1), or DEBUG (-2).
        let invalid = symbol.section_number < -2
            || (symbol.section_number > 0
                && usize::try_from(symbol.section_number)
                    .is_ok_and(|number| number > parsed.sections.len()));
        if invalid {
            return Err(CoffAdmissionError::ExternalDependency);
        }
        if symbol.section_number <= 0
            && symbol.storage_class == 3
            && symbol.value == 0
            && symbol.symbol_type == 0
            && parsed
                .sections
                .iter()
                .any(|section| section.name == symbol.name)
        {
            let offset = checked_add(
                table,
                checked_mul(symbol_index, COFF_SYMBOL_BYTES)?,
            )?;
            if read_u8(object, checked_add(offset, 17)?)? != 0 {
                return Err(CoffAdmissionError::SectionLinkage);
            }
        }
        if symbol.section_number > 0 {
            let index = usize::try_from(symbol.section_number)
                .map_err(|_error| CoffAdmissionError::Bounds)?;
            let section = parsed
                .sections
                .get(index.saturating_sub(1))
                .ok_or(CoffAdmissionError::ExternalDependency)?;
            // BSS and other zero-raw-size sections may contain logical
            // symbols beyond the empty file extent. Populated sections do
            // have a concrete bound, including one-past-end labels.
            if section.raw_size != 0
                && usize_from_u32(symbol.value)? > section.raw_size
            {
                return Err(CoffAdmissionError::SymbolValue);
            }
        }
    }
    Ok(())
}

fn validate_non_comdat_section_auxiliaries(
    object: &[u8],
    parsed: &ParsedCoff,
) -> Result<(), CoffAdmissionError> {
    let table = usize_from_u32(read_u32(object, 8)?)?;
    for (section_index, section) in parsed.sections.iter().enumerate() {
        if section.characteristics & IMAGE_SCN_LNK_COMDAT != 0 {
            continue;
        }
        let number = i16::try_from(section_index.saturating_add(1))
            .map_err(|_error| CoffAdmissionError::Bounds)?;
        let mut has_definition = false;
        for (index, candidate) in parsed.symbols.iter().enumerate() {
            let Some(symbol) = candidate else {
                continue;
            };
            if symbol.section_number != number {
                continue;
            }
            let offset =
                checked_add(table, checked_mul(index, COFF_SYMBOL_BYTES)?)?;
            let aux_count = read_u8(object, checked_add(offset, 17)?)?;
            if aux_count == 0 {
                continue;
            }
            let first_in_section = !parsed
                .symbols
                .iter()
                .take(index)
                .flatten()
                .any(|prior| prior.section_number == number);
            if symbol.symbol_type == 0
                && (symbol.value == 0 || first_in_section)
                && (symbol.name != section.name || symbol.storage_class != 3)
            {
                return Err(CoffAdmissionError::SectionLinkage);
            }
            if symbol.name != section.name {
                continue;
            }
            if has_definition
                || aux_count != 1
                || symbol.storage_class != 3
                || symbol.value != 0
                || symbol.symbol_type != 0
            {
                return Err(CoffAdmissionError::SectionLinkage);
            }
            has_definition = true;
            // Ordinary section definitions duplicate header geometry and
            // must not hide unsupported big-object or reserved aux bytes.
            validate_comdat_aux_geometry(object, offset, section)?;
            validate_comdat_reserved_aux_bytes(object, offset)?;
            if read_u8(object, checked_add(offset, COFF_SYMBOL_BYTES + 14)?)?
                != 0
            {
                return Err(CoffAdmissionError::SectionLinkage);
            }
        }
    }
    Ok(())
}

fn validate_comdat_selections(
    object: &[u8],
    parsed: &ParsedCoff,
) -> Result<(), CoffAdmissionError> {
    let table = usize_from_u32(read_u32(object, 8)?)?;
    let mut associations = vec![None; parsed.sections.len()];
    for (section_index, section) in parsed.sections.iter().enumerate() {
        if section.characteristics & IMAGE_SCN_LNK_COMDAT == 0 {
            continue;
        }
        let number = i16::try_from(section_index.saturating_add(1))
            .map_err(|_error| CoffAdmissionError::Bounds)?;
        if skip_unselected_empty_comdat(
            object,
            parsed,
            table,
            (section, number),
        )? {
            continue;
        }
        validate_comdat_first_symbol(parsed, section, number)?;
        validate_selected_comdat_definition(
            object,
            parsed,
            (section_index, section),
            &mut associations,
        )?;
    }
    validate_comdat_empty_parents(object, parsed, table, &mut associations)?;
    validate_comdat_association_cycles(&associations)
}

fn validate_selected_comdat_definition(
    object: &[u8],
    parsed: &ParsedCoff,
    section_identity: (usize, &CoffSection),
    associations: &mut [Option<usize>],
) -> Result<(), CoffAdmissionError> {
    let (section_index, section) = section_identity;
    let table = usize_from_u32(read_u32(object, 8)?)?;
    let number = i16::try_from(section_index.saturating_add(1))
        .map_err(|_error| CoffAdmissionError::Bounds)?;
    let mut validated = false;
    for (index, candidate) in parsed.symbols.iter().enumerate() {
        let Some(symbol) = candidate else {
            continue;
        };
        if symbol.section_number != number
            || symbol.storage_class != 3
            || symbol.name != section.name
        {
            continue;
        }
        if validated || symbol.value != 0 || symbol.symbol_type != 0 {
            return Err(CoffAdmissionError::SectionLinkage);
        }
        let offset =
            checked_add(table, checked_mul(index, COFF_SYMBOL_BYTES)?)?;
        if read_u8(object, checked_add(offset, 17)?)? != 1 {
            return Err(CoffAdmissionError::SectionLinkage);
        }
        validate_comdat_aux_geometry(object, offset, section)?;
        validate_comdat_reserved_aux_bytes(object, offset)?;
        let selection_offset = checked_add(offset, COFF_SYMBOL_BYTES + 14)?;
        let selection = read_u8(object, selection_offset)?;
        if !(1..=7).contains(&selection) {
            return Err(CoffAdmissionError::SectionLinkage);
        }
        validate_comdat_association(
            object,
            offset,
            (section_index, parsed.sections.as_slice()),
            selection,
        )?;
        if selection == 5 {
            record_comdat_association(
                object,
                offset,
                section_index,
                associations,
            )?;
        }
        validated = true;
    }
    if !validated {
        return Err(CoffAdmissionError::SectionLinkage);
    }
    Ok(())
}

fn skip_unselected_empty_comdat(
    object: &[u8],
    parsed: &ParsedCoff,
    symbol_table: usize,
    section_identity: (&CoffSection, i16),
) -> Result<bool, CoffAdmissionError> {
    let (section, _) = section_identity;
    if section.raw_size != 0 || section.relocation_count != 0 {
        return Ok(false);
    }
    Ok(!has_empty_comdat_selection(
        object,
        parsed,
        symbol_table,
        section_identity,
    )?)
}

fn has_empty_comdat_selection(
    object: &[u8],
    parsed: &ParsedCoff,
    symbol_table: usize,
    section_identity: (&CoffSection, i16),
) -> Result<bool, CoffAdmissionError> {
    let (section, number) = section_identity;
    let mut unselected_definitions = 0usize;
    // Clang emits empty bookkeeping COMDATs without active selection.
    // A nonzero selector must not bypass ordinary COMDAT validation.
    for (index, candidate) in parsed.symbols.iter().enumerate() {
        let Some(symbol) = candidate else {
            continue;
        };
        if symbol.section_number != number {
            continue;
        }
        let offset =
            checked_add(symbol_table, checked_mul(index, COFF_SYMBOL_BYTES)?)?;
        let aux_count = read_u8(object, checked_add(offset, 17)?)?;
        if aux_count == 0 {
            continue;
        }
        let selection =
            read_u8(object, checked_add(offset, COFF_SYMBOL_BYTES + 14)?)?;
        if selection != 0 {
            // A selected empty definition cannot escape admission by
            // disguising its name or storage class.
            return Ok(true);
        }
        if symbol.name != section.name || symbol.storage_class != 3 {
            // Even without a selector, a null-valued, null-typed section
            // definition cannot hide malformed ownership in an aux record.
            let first_in_section = !parsed
                .symbols
                .iter()
                .take(index)
                .flatten()
                .any(|prior| prior.section_number == number);
            if first_in_section
                || (symbol.value == 0 && symbol.symbol_type == 0)
            {
                return Err(CoffAdmissionError::SectionLinkage);
            }
            continue;
        }
        // Selection zero permits compiler bookkeeping, not malformed
        // auxiliary records with hidden geometry or reserved fields.
        if aux_count != 1 {
            return Err(CoffAdmissionError::SectionLinkage);
        }
        unselected_definitions = unselected_definitions.saturating_add(1);
        if unselected_definitions != 1 {
            return Err(CoffAdmissionError::SectionLinkage);
        }
        validate_comdat_first_symbol(parsed, section, number)?;
        validate_comdat_aux_geometry(object, offset, section)?;
        validate_comdat_reserved_aux_bytes(object, offset)?;
    }
    Ok(false)
}

fn record_comdat_association(
    object: &[u8],
    symbol_offset: usize,
    section_index: usize,
    associations: &mut [Option<usize>],
) -> Result<(), CoffAdmissionError> {
    // The immediate parent is valid, but a chain of parents must also
    // terminate rather than form an associative loop.
    let parent = usize::from(read_u16(
        object,
        checked_add(symbol_offset, COFF_SYMBOL_BYTES + 12)?,
    )?);
    *associations
        .get_mut(section_index)
        .ok_or(CoffAdmissionError::SectionLinkage)? = parent.checked_sub(1);
    Ok(())
}

fn validate_comdat_first_symbol(
    parsed: &ParsedCoff,
    section: &CoffSection,
    number: i16,
) -> Result<(), CoffAdmissionError> {
    // A correct section-definition symbol appearing later in the table
    // cannot legitimize any preceding symbol in the same COMDAT section.
    let first = parsed
        .symbols
        .iter()
        .flatten()
        .find(|symbol| symbol.section_number == number)
        .ok_or(CoffAdmissionError::SectionLinkage)?;
    if first.storage_class != 3
        || first.name != section.name
        || first.value != 0
        || first.symbol_type != 0
    {
        Err(CoffAdmissionError::SectionLinkage)
    } else {
        Ok(())
    }
}

fn validate_comdat_empty_parents(
    object: &[u8],
    parsed: &ParsedCoff,
    symbol_table: usize,
    associations: &mut [Option<usize>],
) -> Result<(), CoffAdmissionError> {
    // Follow parents transitively, including empty associative sections.
    // The pending/visited worklist ensures each referenced parent is checked
    // at most once; cycles are rejected by the final three-state walk.
    let mut pending: Vec<usize> =
        associations.iter().flatten().copied().collect();
    let mut visited = vec![false; associations.len()];
    while let Some(parent_index) = pending.pop() {
        let already_seen = visited
            .get_mut(parent_index)
            .ok_or(CoffAdmissionError::SectionLinkage)?;
        if *already_seen {
            continue;
        }
        *already_seen = true;
        if let Some(next) = validate_referenced_empty_comdat_parent(
            object,
            parsed,
            symbol_table,
            parent_index,
        )? {
            *associations
                .get_mut(parent_index)
                .ok_or(CoffAdmissionError::SectionLinkage)? = Some(next);
            pending.push(next);
        }
    }
    Ok(())
}

fn validate_referenced_empty_comdat_parent(
    object: &[u8],
    parsed: &ParsedCoff,
    symbol_table: usize,
    parent_index: usize,
) -> Result<Option<usize>, CoffAdmissionError> {
    let section = parsed
        .sections
        .get(parent_index)
        .ok_or(CoffAdmissionError::SectionLinkage)?;
    if section.raw_size != 0 || section.relocation_count != 0 {
        return Ok(None);
    }
    // Unreferenced empty COMDATs may remain unselected bookkeeping,
    // but any referenced one must have real selection metadata.
    let number = i16::try_from(parent_index.saturating_add(1))
        .map_err(|_error| CoffAdmissionError::SectionLinkage)?;
    validate_comdat_first_symbol(parsed, section, number)?;
    // Populated COMDATs reject duplicate section definitions. Referenced
    // empty COMDATs must enforce that same single-owner requirement.
    let definitions = parsed
        .symbols
        .iter()
        .flatten()
        .filter(|symbol| {
            symbol.section_number == number
                && symbol.storage_class == 3
                && symbol.name == section.name
        })
        .count();
    if definitions != 1 {
        return Err(CoffAdmissionError::SectionLinkage);
    }
    let symbol_index = parsed
        .symbols
        .iter()
        .position(|slot| {
            slot.as_ref()
                .is_some_and(|symbol| symbol.section_number == number)
        })
        .ok_or(CoffAdmissionError::SectionLinkage)?;
    let symbol_offset = checked_add(
        symbol_table,
        checked_mul(symbol_index, COFF_SYMBOL_BYTES)?,
    )?;
    if read_u8(object, checked_add(symbol_offset, 17)?)? != 1 {
        return Err(CoffAdmissionError::SectionLinkage);
    }
    validate_comdat_aux_geometry(object, symbol_offset, section)?;
    validate_comdat_reserved_aux_bytes(object, symbol_offset)?;
    let selection =
        read_u8(object, checked_add(symbol_offset, COFF_SYMBOL_BYTES + 14)?)?;
    if !(1..=7).contains(&selection) {
        return Err(CoffAdmissionError::SectionLinkage);
    }
    validate_comdat_association(
        object,
        symbol_offset,
        (parent_index, parsed.sections.as_slice()),
        selection,
    )?;
    if selection == 5 {
        let parent = usize::from(read_u16(
            object,
            checked_add(symbol_offset, COFF_SYMBOL_BYTES + 12)?,
        )?);
        Ok(parent.checked_sub(1))
    } else {
        Ok(None)
    }
}

fn validate_comdat_association_cycles(
    associations: &[Option<usize>],
) -> Result<(), CoffAdmissionError> {
    // A three-state walk visits each node at most twice, even for large
    // acyclic association chains with many incoming edges.
    let mut states = vec![0u8; associations.len()];
    for start in 0..associations.len() {
        let mut current = Some(start);
        while let Some(index) = current {
            match *states
                .get(index)
                .ok_or(CoffAdmissionError::SectionLinkage)?
            {
                1 => return Err(CoffAdmissionError::SectionLinkage),
                2 => break,
                _ => {
                    *states
                        .get_mut(index)
                        .ok_or(CoffAdmissionError::SectionLinkage)? = 1;
                },
            }
            current = associations.get(index).copied().flatten();
        }
        let mut cursor = Some(start);
        while let Some(index) = cursor {
            if *states
                .get(index)
                .ok_or(CoffAdmissionError::SectionLinkage)?
                != 1
            {
                break;
            }
            *states
                .get_mut(index)
                .ok_or(CoffAdmissionError::SectionLinkage)? = 2;
            cursor = associations.get(index).copied().flatten();
        }
    }
    Ok(())
}

fn validate_comdat_aux_geometry(
    object: &[u8],
    symbol_offset: usize,
    section: &CoffSection,
) -> Result<(), CoffAdmissionError> {
    let aux = checked_add(symbol_offset, COFF_SYMBOL_BYTES)?;
    let length = usize_from_u32(read_u32(object, aux)?)?;
    let relocations = usize::from(read_u16(object, checked_add(aux, 4)?)?);
    let line_numbers = read_u16(object, checked_add(aux, 6)?)?;
    if length != section.raw_size
        || relocations != section.relocation_count
        || line_numbers != 0
    {
        return Err(CoffAdmissionError::SectionLinkage);
    }
    Ok(())
}

fn validate_comdat_reserved_aux_bytes(
    object: &[u8],
    symbol_offset: usize,
) -> Result<(), CoffAdmissionError> {
    let aux = checked_add(symbol_offset, COFF_SYMBOL_BYTES)?;
    let unused = read_u8(object, checked_add(aux, 15)?)?;
    let high_section = read_u16(object, checked_add(aux, 16)?)?;
    if unused != 0 || high_section != 0 {
        return Err(CoffAdmissionError::SectionLinkage);
    }
    Ok(())
}

fn validate_comdat_association(
    object: &[u8],
    symbol_offset: usize,
    section_bounds: (usize, &[CoffSection]),
    selection: u8,
) -> Result<(), CoffAdmissionError> {
    let (section_index, sections) = section_bounds;
    if selection != 5 {
        return Ok(());
    }
    let associated = usize::from(read_u16(
        object,
        checked_add(symbol_offset, COFF_SYMBOL_BYTES + 12)?,
    )?);
    if associated == 0
        || section_index.checked_add(1) == Some(associated)
        || sections
            .get(associated.saturating_sub(1))
            .is_none_or(|section| {
                section.characteristics & IMAGE_SCN_LNK_COMDAT == 0
            })
    {
        return Err(CoffAdmissionError::SectionLinkage);
    }
    Ok(())
}

fn validate_symbols_and_relocations(
    object: &[u8],
    parsed: &ParsedCoff,
) -> Result<(), CoffAdmissionError> {
    validate_symbol_sections(object, parsed)?;
    validate_non_comdat_section_auxiliaries(object, parsed)?;
    validate_comdat_selections(object, parsed)?;
    let _entry_offset = required_entry_offset(parsed)?;
    let machine = read_u16(object, 0)?;
    for section in &parsed.sections {
        for relocation_index in 0..section.relocation_count {
            let offset = checked_add(
                section.relocation_start,
                checked_mul(relocation_index, COFF_RELOCATION_BYTES)?,
            )?;
            let virtual_address = read_u32(object, offset)?;
            // COFF relocation addresses are section-relative positions plus
            // the section header's virtual-address origin. Reject positions
            // that do not designate a byte in the owning section.
            let relative = virtual_address
                .checked_sub(section.virtual_address)
                .and_then(|position| usize::try_from(position).ok())
                .ok_or(CoffAdmissionError::Bounds)?;
            let kind = read_u16(object, checked_add(offset, 8)?)?;
            // x64 span-dependent types require the following PAIR record.
            // The pair is not an independent relocation and cannot be
            // structurally admitted without owning its linker semantics.
            if machine == IMAGE_FILE_MACHINE_AMD64
                && matches!(kind, 0x000e..=0x0010)
            {
                return Err(CoffAdmissionError::RelocationPair);
            }
            let width = relocation_patch_width(machine, kind)
                .ok_or(CoffAdmissionError::RelocationType)?;
            if relative >= section.raw_size
                || relative
                    .checked_add(width)
                    .is_none_or(|end| end > section.raw_size)
            {
                return Err(CoffAdmissionError::Bounds);
            }
            let symbol_index =
                usize_from_u32(read_u32(object, checked_add(offset, 4)?)?)?;
            let symbol = parsed
                .symbols
                .get(symbol_index)
                .and_then(Option::as_ref)
                .ok_or(CoffAdmissionError::ExternalDependency)?;
            // A relocation must resolve to an actual one-based COFF section
            // or to the defined absolute-symbol sentinel. Undefined/common,
            // debug, and out-of-range section numbers have no loadable target.
            let defined = symbol.section_number == -1
                || (symbol.section_number > 0
                    && usize::try_from(symbol.section_number)
                        .is_ok_and(|number| number <= parsed.sections.len()));
            if !defined {
                return Err(CoffAdmissionError::ExternalDependency);
            }
        }
    }
    Ok(())
}

// Width in bytes of the location patched by each defined PE/COFF relocation
// type. ABSOLUTE is metadata-only and patches no section bytes. Unsupported
// x64 span-dependent PAIR forms are rejected before this lookup.
const fn relocation_patch_width(machine: u16, kind: u16) -> Option<usize> {
    match (machine, kind) {
        (IMAGE_FILE_MACHINE_AMD64 | IMAGE_FILE_MACHINE_ARM64, 0x0000) => {
            Some(0)
        },
        (IMAGE_FILE_MACHINE_AMD64, 0x0001)
        | (IMAGE_FILE_MACHINE_ARM64, 0x000e) => Some(8),
        (IMAGE_FILE_MACHINE_AMD64, 0x000a)
        | (IMAGE_FILE_MACHINE_ARM64, 0x000d) => Some(2),
        (IMAGE_FILE_MACHINE_AMD64, 0x000c) => Some(1),
        (IMAGE_FILE_MACHINE_AMD64, 0x0002..=0x0009 | 0x000b | 0x000d)
        | (IMAGE_FILE_MACHINE_ARM64, 0x0001..=0x000c | 0x000f..=0x0011) => {
            Some(4)
        },
        _ => None,
    }
}

fn add_coff_layout_range(
    object: &[u8],
    ranges: &mut Vec<(usize, usize)>,
    start: usize,
    size: usize,
) -> Result<(), CoffAdmissionError> {
    if size == 0 {
        return Ok(());
    }
    require_range(object, start, size)?;
    ranges.push((start, checked_add(start, size)?));
    Ok(())
}

fn validate_coff_layout(
    object: &[u8],
    parsed: &ParsedCoff,
) -> Result<(), CoffAdmissionError> {
    let header_bytes = checked_add(
        COFF_HEADER_BYTES,
        checked_mul(parsed.sections.len(), COFF_SECTION_BYTES)?,
    )?;
    let symbol_start = usize_from_u32(read_u32(object, 8)?)?;
    let symbol_count = usize_from_u32(read_u32(object, 12)?)?;
    let symbol_bytes = checked_mul(symbol_count, COFF_SYMBOL_BYTES)?;
    let string_start = checked_add(symbol_start, symbol_bytes)?;
    let string_bytes = parse_string_table_length(object, string_start)?;
    let capacity = parsed.sections.len().saturating_mul(2).saturating_add(3);
    let mut ranges = Vec::with_capacity(capacity);
    add_coff_layout_range(object, &mut ranges, 0, header_bytes)?;
    add_coff_layout_range(object, &mut ranges, symbol_start, symbol_bytes)?;
    add_coff_layout_range(object, &mut ranges, string_start, string_bytes)?;
    for section in &parsed.sections {
        add_coff_layout_range(
            object,
            &mut ranges,
            section.raw_start,
            section.raw_size,
        )?;
        let relocation_bytes =
            checked_mul(section.relocation_count, COFF_RELOCATION_BYTES)?;
        add_coff_layout_range(
            object,
            &mut ranges,
            section.relocation_start,
            relocation_bytes,
        )?;
    }
    ranges.sort_unstable_by_key(|(start, _end)| *start);
    let mut previous_end = 0;
    for &(start, end) in &ranges {
        if start < previous_end {
            return Err(CoffAdmissionError::LayoutOverlap);
        }
        previous_end = end;
    }
    // Overlap has priority over padding diagnostics: malformed range claims
    // are rejected before checking any unowned interior alignment bytes.
    let mut padding_start = 0;
    for (start, end) in ranges {
        // Allow ordinary compiler alignment but never allow opaque payloads
        // between declared regions to bypass COFF structural admission.
        if object
            .get(padding_start..start)
            .ok_or(CoffAdmissionError::Bounds)?
            .iter()
            .any(|byte| *byte != 0)
        {
            return Err(CoffAdmissionError::UnownedBytes);
        }
        padding_start = end;
    }
    // Every byte after the last owned range is an opaque, unvalidated
    // overlay. Relocation tables after the string table are already owned
    // above and remain valid when their declared ranges reach file end.
    if previous_end != object.len() {
        return Err(CoffAdmissionError::UnownedBytes);
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
        let digits = trim_nul(raw.get(1..).ok_or(CoffAdmissionError::Bounds)?)?;
        if digits.is_empty() || !digits.iter().all(u8::is_ascii_digit) {
            return Err(CoffAdmissionError::Bounds);
        }
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
    let bytes = trim_nul(raw)?;
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
    if relative > 4 && object.get(start.saturating_sub(1)) != Some(&0u8) {
        return Err(CoffAdmissionError::StringTableOffset);
    }
    let table_end = checked_add(strings.start, strings.bytes)?;
    let remainder = object
        .get(start..table_end)
        .ok_or(CoffAdmissionError::Bounds)?;
    let length = remainder
        .iter()
        .position(|byte| *byte == 0)
        .ok_or(CoffAdmissionError::Bounds)?;
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

fn trim_nul(bytes: &[u8]) -> Result<&[u8], CoffAdmissionError> {
    let length = bytes
        .iter()
        .position(|byte| *byte == 0)
        .unwrap_or(bytes.len());
    // COFF short names are NUL-padded, not arbitrary data following the
    // first terminator. Reject hidden bytes on any parsed inline name.
    if bytes
        .get(length..)
        .is_none_or(|padding| padding.iter().any(|byte| *byte != 0))
    {
        return Err(CoffAdmissionError::Bounds);
    }
    bytes.get(..length).ok_or(CoffAdmissionError::Bounds)
}

fn usize_from_u32(value: u32) -> Result<usize, CoffAdmissionError> {
    usize::try_from(value).map_err(|_error| CoffAdmissionError::Bounds)
}
