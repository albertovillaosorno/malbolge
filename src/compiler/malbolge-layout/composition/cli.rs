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
//   - Bounded machine/ternary input, VM preflight and artifact publication.
// - Must-Not:
//   - Infer guest semantics from host arguments or publish unverified source.
// - Allows:
//   - Inputs: exact profile, bounded MCTI/MCTR file or stdin, or machine tokens.
//   - Outputs: one complete raw graphical `.malbolge` file.
//   - Side effects: same-directory staging and atomic no-clobber hard link.
// - Split-When:
//   - A full typed-IR machine lowering input/serialization format is admitted.
// - Merge-When:
//   - General backend owns equivalent publication with the same guarantees.
// - Summary:
//   - Publishes only complete executable machine and byte-I/O trace artifacts.
// - Description:
//   - Requires explicit profile, validates admitted source with a real VM.
// - Usage:
//   - `--profile malbolge-2026 --output hello.malbolge -- input output halt`.
// - Defaults:
//   - Never overwrites a target or exposes a partially written target path.
//

//! Closed bounded machine-subset CLI with independently checked target source.

use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::{self, OpenOptions};
use std::io::{self, Read as _, Seek as _, Write as _};
use std::path::{Path, PathBuf};
use std::process::{ExitCode, id};

use malbolge::{ProfileMachine, RunOutcome, build_capsule, parse_capsule, target_profile};

use crate::bridge::{
    encode_distinct_literal_eight, encode_distinct_literal_eighteen,
    encode_distinct_literal_eleven, encode_distinct_literal_fifteen,
    encode_distinct_literal_fourteen, encode_distinct_literal_nine,
    encode_distinct_literal_nineteen, encode_distinct_literal_pair, encode_distinct_literal_quad,
    encode_distinct_literal_quint, encode_distinct_literal_seven,
    encode_distinct_literal_seventeen, encode_distinct_literal_six,
    encode_distinct_literal_sixteen, encode_distinct_literal_ten, encode_distinct_literal_thirteen,
    encode_distinct_literal_triple, encode_distinct_literal_twelve, encode_empty_void_function,
    encode_initial_zero_outputs, encode_latest_byte_identity_trace, encode_rotated_byte_literal,
    encode_successful_byte_echo, encode_successful_latest_byte_trace,
    encode_zero_prefixed_latest_byte_trace, encode_zero_then_literal,
    ternary::{TernaryOperation, canonical_ternary_program},
};
use crate::layout::{
    LinearOpcode, LinearProfileIdentity, PaddedForwardStep, admit_linear_layout,
    encode_auto_padded_forward_layout, encode_linear_layout,
};
use crate::typed_adapter::{
    compile_canonical_typed_distinct_literal_eight,
    compile_canonical_typed_distinct_literal_eighteen,
    compile_canonical_typed_distinct_literal_eleven,
    compile_canonical_typed_distinct_literal_fifteen,
    compile_canonical_typed_distinct_literal_fourteen,
    compile_canonical_typed_distinct_literal_nine,
    compile_canonical_typed_distinct_literal_nineteen,
    compile_canonical_typed_distinct_literal_pair, compile_canonical_typed_distinct_literal_quad,
    compile_canonical_typed_distinct_literal_quint, compile_canonical_typed_distinct_literal_seven,
    compile_canonical_typed_distinct_literal_seventeen,
    compile_canonical_typed_distinct_literal_six, compile_canonical_typed_distinct_literal_sixteen,
    compile_canonical_typed_distinct_literal_ten,
    compile_canonical_typed_distinct_literal_thirteen,
    compile_canonical_typed_distinct_literal_triple,
    compile_canonical_typed_distinct_literal_twelve, compile_canonical_typed_echo,
    compile_canonical_typed_empty_void, compile_canonical_typed_identity_byte_trace,
    compile_canonical_typed_initial_zero_outputs, compile_canonical_typed_latest_byte_trace,
    compile_canonical_typed_rotated_byte_literal,
    compile_canonical_typed_zero_prefixed_latest_byte_trace,
    compile_canonical_typed_zero_then_literal,
};

const PROFILE_ARG: &str = "--profile";
const OUTPUT_ARG: &str = "--output";
const DELIMITER_ARG: &str = "--";
const CAPSULE_ARG: &str = "--capsule";
const MAX_OPERATIONS: usize = 4096;
const MAX_CANONICAL_WIRE_BYTES: u64 = 1_048_576;
const TERNARY_FILE_ARG: &str = "--ternary-file";
const LATEST_BYTE_TRACE_ARG: &str = "--latest-byte-trace";
const INITIAL_ZERO_OUTPUT_ARG: &str = "--initial-zero-output";
const ZERO_PREFIXED_BYTE_TRACE_ARG: &str = "--zero-prefixed-byte-trace";
const IDENTITY_BYTE_TRACE_ARG: &str = "--identity-byte-trace";
const SEEDED_BYTE_LITERAL_ARG: &str = "--seeded-byte-literal";
const ZERO_THEN_LITERAL_ARG: &str = "--zero-then-literal";
const DISTINCT_LITERAL_PAIR_ARG: &str = "--distinct-literal-pair";
const DISTINCT_LITERAL_TRIPLE_ARG: &str = "--distinct-literal-triple";
const DISTINCT_LITERAL_QUAD_ARG: &str = "--distinct-literal-quad";
const DISTINCT_LITERAL_QUINT_ARG: &str = "--distinct-literal-quint";
const DISTINCT_LITERAL_SIX_ARG: &str = "--distinct-literal-six";
const DISTINCT_LITERAL_SEVEN_ARG: &str = "--distinct-literal-seven";
const DISTINCT_LITERAL_EIGHT_ARG: &str = "--distinct-literal-eight";
const DISTINCT_LITERAL_NINE_ARG: &str = "--distinct-literal-nine";
const DISTINCT_LITERAL_TEN_ARG: &str = "--distinct-literal-ten";
const DISTINCT_LITERAL_ELEVEN_ARG: &str = "--distinct-literal-eleven";
const DISTINCT_LITERAL_TWELVE_ARG: &str = "--distinct-literal-twelve";
const DISTINCT_LITERAL_THIRTEEN_ARG: &str = "--distinct-literal-thirteen";
const DISTINCT_LITERAL_FOURTEEN_ARG: &str = "--distinct-literal-fourteen";
const DISTINCT_LITERAL_FIFTEEN_ARG: &str = "--distinct-literal-fifteen";
const DISTINCT_LITERAL_SIXTEEN_ARG: &str = "--distinct-literal-sixteen";
const DISTINCT_LITERAL_SEVENTEEN_ARG: &str = "--distinct-literal-seventeen";
const DISTINCT_LITERAL_EIGHTEEN_ARG: &str = "--distinct-literal-eighteen";
const DISTINCT_LITERAL_NINETEEN_ARG: &str = "--distinct-literal-nineteen";
const EMPTY_VOID_ARG: &str = "--empty-void";
const TYPED_FILE_ARG: &str = "--typed-file";
const TYPED_STDIN_ARG: &str = "--typed-stdin";
const TERNARY_STDIN_ARG: &str = "--ternary-stdin";
const AUTO_LAYOUT_ARG: &str = "--auto-layout";
const MALBOLGE_EXTENSION: &str = "malbolge";
const MAX_STAGE_NAME_ATTEMPTS: usize = 32;
// Leave enough room for an attempt suffix on ordinary filesystems and never
// derive an overlong staging component from a valid final target basename.
const MAX_STAGE_BASENAME_BYTES: usize = 128;
const STAGE_NAME_FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const STAGE_NAME_FNV_PRIME: u64 = 1_099_511_628_211;

#[derive(Debug)]
enum SourceSpec {
    AutoLayout(Vec<PaddedForwardStep>),
    CanonicalTernaryFile { path: PathBuf, mode: ByteTraceMode },
    CanonicalTernaryStdin { mode: ByteTraceMode },
    CanonicalTypedFile { path: PathBuf, mode: ByteTraceMode },
    CanonicalTypedStdin { mode: ByteTraceMode },
    MachineOperations(Vec<LinearOpcode>),
}

#[derive(Debug)]
struct CommandSpec {
    capsule: bool,
    output: PathBuf,
    profile: String,
    source: SourceSpec,
}

#[derive(Clone, Copy, Debug)]
enum ByteTraceMode {
    AdjacentEcho,
    DistinctLiteralPair,
    DistinctLiteralTriple,
    DistinctLiteralQuad,
    DistinctLiteralQuint,
    DistinctLiteralSix,
    DistinctLiteralSeven,
    DistinctLiteralEight,
    DistinctLiteralNine,
    DistinctLiteralTen,
    DistinctLiteralEleven,
    DistinctLiteralTwelve,
    DistinctLiteralThirteen,
    DistinctLiteralFourteen,
    DistinctLiteralFifteen,
    DistinctLiteralSixteen,
    DistinctLiteralSeventeen,
    DistinctLiteralEighteen,
    DistinctLiteralNineteen,
    EmptyVoid,
    IdentityByteBitcast,
    InitialZero,
    LatestRead,
    RotatedLiteral,
    ZeroPrefixedLatest,
    ZeroThenLiteral,
}

#[derive(Clone, Copy, Debug)]
enum SuccessfulByteEffect {
    Input,
    Output,
    ZeroOutput,
}

enum SourceEffectWitness {
    DistinctLiteralPair { first: u8, second: u8 },
    DistinctLiteralTriple { bytes: [u8; 3] },
    DistinctLiteralQuad { bytes: [u8; 4] },
    DistinctLiteralQuint { bytes: [u8; 5] },
    DistinctLiteralSix { bytes: [u8; 6] },
    DistinctLiteralSeven { bytes: [u8; 7] },
    DistinctLiteralEight { bytes: [u8; 8] },
    DistinctLiteralNine { bytes: [u8; 9] },
    DistinctLiteralTen { bytes: [u8; 10] },
    DistinctLiteralEleven { bytes: [u8; 11] },
    DistinctLiteralTwelve { bytes: [u8; 12] },
    DistinctLiteralThirteen { bytes: [u8; 13] },
    DistinctLiteralFourteen { bytes: [u8; 14] },
    DistinctLiteralFifteen { bytes: [u8; 15] },
    DistinctLiteralSixteen { bytes: [u8; 16] },
    DistinctLiteralSeventeen { bytes: [u8; 17] },
    DistinctLiteralEighteen { bytes: [u8; 18] },
    DistinctLiteralNineteen { bytes: [u8; 19] },
    EmptyVoid,
    InitialZero { outputs: usize },
    RotatedLiteral { byte: u8, outputs: usize },
    SuccessfulByteTrace(Vec<SuccessfulByteEffect>),
    ZeroThenLiteral { byte: u8 },
}

type StageFile = (PathBuf, fs::File);

struct VerifiedSource {
    effect_witness: Option<SourceEffectWitness>,
    source: Vec<u8>,
    steps: usize,
}

fn parse_operation(token: &str) -> Result<LinearOpcode, String> {
    match token {
        "crazy" => Ok(LinearOpcode::CrazyData),
        "halt" => Ok(LinearOpcode::Halt),
        "input" => Ok(LinearOpcode::InputWord),
        "nop" => Ok(LinearOpcode::NoOperation),
        "output" => Ok(LinearOpcode::OutputByte),
        "relocate" => Ok(LinearOpcode::RelocateDataPointer),
        "rotate" => Ok(LinearOpcode::RotateData),
        _ => {
            let Some(raw) = token.strip_prefix("jump:") else {
                return Err(format!("unsupported machine opcode: {token}"));
            };
            if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) {
                return Err(String::from(
                    "jump target must be an unsigned decimal address",
                ));
            }
            let target = raw
                .parse::<u32>()
                .map_err(|error| format!("jump target exceeds supported code address: {error}"))?;
            Ok(LinearOpcode::JumpForward { target })
        }
    }
}

fn parse_auto_layout_operation(token: &str) -> Result<PaddedForwardStep, String> {
    match token {
        "jump" => Ok(PaddedForwardStep::Jump),
        "auto-relocate" => Ok(PaddedForwardStep::AutoRelocate),
        _ => {
            let operation = parse_operation(token)?;
            if matches!(operation, LinearOpcode::JumpForward { .. }) {
                Err(String::from(
                    "--auto-layout accepts symbolic jump, not jump:TARGET",
                ))
            } else {
                Ok(PaddedForwardStep::Instruction(operation))
            }
        }
    }
}

fn parse_auto_layout(arguments: &mut impl Iterator<Item = OsString>) -> Result<SourceSpec, String> {
    let mut operations = Vec::new();
    for raw in arguments {
        if operations.len() >= MAX_OPERATIONS {
            return Err(String::from("too many auto-layout operation tokens"));
        }
        let token = raw
            .into_string()
            .map_err(|_error| String::from("auto-layout token must be UTF-8"))?;
        operations.push(parse_auto_layout_operation(&token)?);
    }
    if operations.is_empty() {
        return Err(String::from("missing auto-layout operation tokens"));
    }
    Ok(SourceSpec::AutoLayout(operations))
}

#[expect(
    clippy::cognitive_complexity,
    reason = "complete bounded canonical byte trace source-mode admission"
)]
fn parse_canonical_source(
    first: OsString,
    arguments: &mut impl Iterator<Item = OsString>,
) -> Result<SourceSpec, String> {
    let (kind, mode) = if first == OsStr::new(LATEST_BYTE_TRACE_ARG)
        || first == OsStr::new(INITIAL_ZERO_OUTPUT_ARG)
        || first == OsStr::new(ZERO_PREFIXED_BYTE_TRACE_ARG)
        || first == OsStr::new(IDENTITY_BYTE_TRACE_ARG)
        || first == OsStr::new(SEEDED_BYTE_LITERAL_ARG)
        || first == OsStr::new(ZERO_THEN_LITERAL_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_PAIR_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_TRIPLE_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_QUAD_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_QUINT_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_SIX_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_SEVEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_EIGHT_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_NINE_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_TEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_ELEVEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_TWELVE_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_THIRTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_FOURTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_FIFTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_SIXTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_SEVENTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_EIGHTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_NINETEEN_ARG)
        || first == OsStr::new(EMPTY_VOID_ARG)
    {
        let mode = if first == OsStr::new(EMPTY_VOID_ARG) {
            ByteTraceMode::EmptyVoid
        } else if first == OsStr::new(INITIAL_ZERO_OUTPUT_ARG) {
            ByteTraceMode::InitialZero
        } else if first == OsStr::new(ZERO_PREFIXED_BYTE_TRACE_ARG) {
            ByteTraceMode::ZeroPrefixedLatest
        } else if first == OsStr::new(IDENTITY_BYTE_TRACE_ARG) {
            ByteTraceMode::IdentityByteBitcast
        } else if first == OsStr::new(SEEDED_BYTE_LITERAL_ARG) {
            ByteTraceMode::RotatedLiteral
        } else if first == OsStr::new(ZERO_THEN_LITERAL_ARG) {
            ByteTraceMode::ZeroThenLiteral
        } else if first == OsStr::new(DISTINCT_LITERAL_PAIR_ARG) {
            ByteTraceMode::DistinctLiteralPair
        } else if first == OsStr::new(DISTINCT_LITERAL_TRIPLE_ARG) {
            ByteTraceMode::DistinctLiteralTriple
        } else if first == OsStr::new(DISTINCT_LITERAL_QUAD_ARG) {
            ByteTraceMode::DistinctLiteralQuad
        } else if first == OsStr::new(DISTINCT_LITERAL_QUINT_ARG) {
            ByteTraceMode::DistinctLiteralQuint
        } else if first == OsStr::new(DISTINCT_LITERAL_EIGHT_ARG) {
            ByteTraceMode::DistinctLiteralEight
        } else if first == OsStr::new(DISTINCT_LITERAL_NINE_ARG) {
            ByteTraceMode::DistinctLiteralNine
        } else if first == OsStr::new(DISTINCT_LITERAL_NINETEEN_ARG) {
            ByteTraceMode::DistinctLiteralNineteen
        } else if first == OsStr::new(DISTINCT_LITERAL_EIGHTEEN_ARG) {
            ByteTraceMode::DistinctLiteralEighteen
        } else if first == OsStr::new(DISTINCT_LITERAL_SEVENTEEN_ARG) {
            ByteTraceMode::DistinctLiteralSeventeen
        } else if first == OsStr::new(DISTINCT_LITERAL_SIXTEEN_ARG) {
            ByteTraceMode::DistinctLiteralSixteen
        } else if first == OsStr::new(DISTINCT_LITERAL_FIFTEEN_ARG) {
            ByteTraceMode::DistinctLiteralFifteen
        } else if first == OsStr::new(DISTINCT_LITERAL_FOURTEEN_ARG) {
            ByteTraceMode::DistinctLiteralFourteen
        } else if first == OsStr::new(DISTINCT_LITERAL_THIRTEEN_ARG) {
            ByteTraceMode::DistinctLiteralThirteen
        } else if first == OsStr::new(DISTINCT_LITERAL_TWELVE_ARG) {
            ByteTraceMode::DistinctLiteralTwelve
        } else if first == OsStr::new(DISTINCT_LITERAL_ELEVEN_ARG) {
            ByteTraceMode::DistinctLiteralEleven
        } else if first == OsStr::new(DISTINCT_LITERAL_TEN_ARG) {
            ByteTraceMode::DistinctLiteralTen
        } else if first == OsStr::new(DISTINCT_LITERAL_SEVEN_ARG) {
            ByteTraceMode::DistinctLiteralSeven
        } else if first == OsStr::new(DISTINCT_LITERAL_SIX_ARG) {
            ByteTraceMode::DistinctLiteralSix
        } else {
            ByteTraceMode::LatestRead
        };
        (
            arguments
                .next()
                .ok_or("missing canonical wire input mode")?,
            mode,
        )
    } else {
        (first, ByteTraceMode::AdjacentEcho)
    };
    let uses_file = kind == OsStr::new(TERNARY_FILE_ARG) || kind == OsStr::new(TYPED_FILE_ARG);
    let uses_stdin = kind == OsStr::new(TERNARY_STDIN_ARG) || kind == OsStr::new(TYPED_STDIN_ARG);
    if !uses_file && !uses_stdin {
        return Err(String::from(
            "effect mode requires --ternary-file, --typed-file, --ternary-stdin or --typed-stdin",
        ));
    }
    let source = if uses_stdin {
        if arguments.next().is_some() {
            return Err(String::from("canonical stdin mode accepts no input path"));
        }
        if kind == OsStr::new(TERNARY_STDIN_ARG) {
            SourceSpec::CanonicalTernaryStdin { mode }
        } else {
            SourceSpec::CanonicalTypedStdin { mode }
        }
    } else {
        let path = PathBuf::from(arguments.next().ok_or("missing canonical wire path")?);
        if arguments.next().is_some() {
            return Err(String::from(
                "canonical wire mode accepts exactly one input path",
            ));
        }
        if kind == OsStr::new(TERNARY_FILE_ARG) {
            SourceSpec::CanonicalTernaryFile { path, mode }
        } else {
            SourceSpec::CanonicalTypedFile { path, mode }
        }
    };
    Ok(source)
}

fn parse_source(arguments: &mut impl Iterator<Item = OsString>) -> Result<SourceSpec, String> {
    let first = arguments
        .next()
        .ok_or("missing machine operations or canonical wire argument")?;
    let source = if first == OsStr::new(AUTO_LAYOUT_ARG) {
        return parse_auto_layout(arguments);
    } else if first == OsStr::new(TERNARY_FILE_ARG)
        || first == OsStr::new(TYPED_FILE_ARG)
        || first == OsStr::new(TERNARY_STDIN_ARG)
        || first == OsStr::new(TYPED_STDIN_ARG)
        || first == OsStr::new(LATEST_BYTE_TRACE_ARG)
        || first == OsStr::new(INITIAL_ZERO_OUTPUT_ARG)
        || first == OsStr::new(ZERO_PREFIXED_BYTE_TRACE_ARG)
        || first == OsStr::new(IDENTITY_BYTE_TRACE_ARG)
        || first == OsStr::new(SEEDED_BYTE_LITERAL_ARG)
        || first == OsStr::new(ZERO_THEN_LITERAL_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_PAIR_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_TRIPLE_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_QUAD_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_QUINT_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_SIX_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_SEVEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_EIGHT_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_NINE_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_TEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_ELEVEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_TWELVE_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_THIRTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_FOURTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_FIFTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_SIXTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_SEVENTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_EIGHTEEN_ARG)
        || first == OsStr::new(DISTINCT_LITERAL_NINETEEN_ARG)
        || first == OsStr::new(EMPTY_VOID_ARG)
    {
        return parse_canonical_source(first, arguments);
    } else {
        let first_token = first
            .into_string()
            .map_err(|_error| String::from("opcode token must be UTF-8"))?;
        let mut operations = vec![parse_operation(&first_token)?];
        for raw_token in arguments {
            if operations.len() >= MAX_OPERATIONS {
                return Err(String::from("too many machine opcode tokens"));
            }
            let token = raw_token
                .into_string()
                .map_err(|_error| String::from("opcode token must be UTF-8"))?;
            operations.push(parse_operation(&token)?);
        }
        SourceSpec::MachineOperations(operations)
    };
    Ok(source)
}

fn parse_arguments(mut arguments: impl Iterator<Item = OsString>) -> Result<CommandSpec, String> {
    if arguments.next().as_deref() != Some(OsStr::new(PROFILE_ARG)) {
        return Err(String::from("expected --profile <canonical-id>"));
    }
    let profile = arguments
        .next()
        .ok_or("missing target profile")?
        .into_string()
        .map_err(|_error| String::from("profile must be UTF-8"))?;
    if arguments.next().as_deref() != Some(OsStr::new(OUTPUT_ARG)) {
        return Err(String::from("expected --output <path>.malbolge"));
    }
    let output = PathBuf::from(arguments.next().ok_or("missing output path")?);
    let next = arguments.next();
    let capsule = next.as_deref() == Some(OsStr::new(CAPSULE_ARG));
    if (capsule && arguments.next().as_deref() != Some(OsStr::new(DELIMITER_ARG)))
        || (!capsule && next.as_deref() != Some(OsStr::new(DELIMITER_ARG)))
    {
        return Err(String::from(
            "expected optional --capsule then -- before opcode tokens",
        ));
    }
    let source = parse_source(&mut arguments)?;
    Ok(CommandSpec {
        capsule,
        output,
        profile,
        source,
    })
}

fn fresh_stage_basename(name: &str) -> String {
    let named = format!(".{name}.stage-{}", id());
    if named.len() <= MAX_STAGE_BASENAME_BYTES {
        return named;
    }
    // This noncryptographic digest is only a deterministic *name hint*, not
    // an integrity authority. All candidates still require create_new(true), so
    // even a forced digest collision cannot overwrite a prior stage.
    let digest = name
        .as_bytes()
        .iter()
        .fold(STAGE_NAME_FNV_OFFSET, |hash, byte| {
            (hash ^ u64::from(*byte)).wrapping_mul(STAGE_NAME_FNV_PRIME)
        });
    format!(".layout-{digest:016x}.stage-{}", id())
}

fn open_fresh_stage(path: &Path, name: &str) -> Result<StageFile, String> {
    let basename = fresh_stage_basename(name);
    for attempt in 0..MAX_STAGE_NAME_ATTEMPTS {
        let staged = if attempt == 0 {
            path.with_file_name(&basename)
        } else {
            path.with_file_name(format!("{basename}-{attempt}"))
        };
        match OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .open(&staged)
        {
            Ok(file) => return Ok((staged, file)),
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {}
            Err(error) => return Err(format!("cannot open fresh stage: {error}")),
        }
    }
    Err(String::from(
        "cannot open fresh stage: all staging names occupied",
    ))
}

// The staging inode starts with one link and has exactly two links after
// atomic publication (staging + final). An extra link gives a foreign writer
// another pathname to mutate an otherwise verified executable artifact.
#[cfg(unix)]
fn has_exact_link_count(metadata: &fs::Metadata, expected: u64) -> bool {
    use std::os::unix::fs::MetadataExt as _;

    metadata.nlink() == expected
}

#[cfg(windows)]
fn has_exact_link_count(metadata: &fs::Metadata, expected: u64) -> bool {
    use std::os::windows::fs::MetadataExt as _;

    u32::try_from(expected)
        .ok()
        .is_some_and(|count| metadata.number_of_links() == Some(count))
}

#[cfg(not(any(unix, windows)))]
fn has_exact_link_count(_metadata: &fs::Metadata, _expected: u64) -> bool {
    true
}

fn verify_fsynced_stage(
    staged: &Path,
    file: &mut fs::File,
    expected: &[u8],
    admission: (&fs::Metadata, u64, &Path),
) -> Result<(), String> {
    // Pin link count and resolved pathname independently of metadata observed
    // after publication hooks, so redirected ancestors cannot reset identity.
    let (initial, expected_links, resolved_path) = admission;
    let check_identity = |opened: &fs::File| {
        let descriptor = opened
            .metadata()
            .map_err(|error| format!("cannot inspect staged descriptor: {error}"))?;
        let named = fs::symlink_metadata(staged)
            .map_err(|error| format!("cannot inspect staged pathname: {error}"))?;
        if !has_exact_link_count(&descriptor, expected_links)
            || !has_exact_link_count(&named, expected_links)
        {
            return Err(String::from("staged output has an external hard link"));
        }
        // Inode checks alone cannot detect renaming the parent directory
        // and installing a symlink back to that same regular inode.
        let observed_path = fs::canonicalize(staged)
            .map_err(|error| format!("cannot resolve staged pathname: {error}"))?;
        if observed_path != resolved_path {
            return Err(String::from("staged output resolved pathname changed"));
        }
        if !canonical_wire_metadata_matches(initial, &descriptor)
            || !canonical_wire_metadata_matches(initial, &named)
        {
            return Err(String::from(
                "staged output inode or contents changed after sync",
            ));
        }
        Ok(())
    };
    let expected_len = u64::try_from(expected.len())
        .map_err(|_error| String::from("staged output length exceeds host range"))?;
    if !initial.is_file() || initial.len() != expected_len {
        return Err(String::from(
            "staged output size disagrees with verified source",
        ));
    }
    check_identity(file)?;
    file.rewind()
        .map_err(|error| format!("cannot rewind staged descriptor: {error}"))?;
    // Never reopen an attacker-swappable stage pathname (FIFO or symlink),
    // and never allocate beyond the exact source length plus a one-byte probe.
    let mut observed = Vec::new();
    let _count = (&mut *file)
        .take(expected_len.saturating_add(1))
        .read_to_end(&mut observed)
        .map_err(|error| format!("cannot reread staged descriptor: {error}"))?;
    if observed != expected {
        return Err(String::from("staged output differs from verified source"));
    }
    check_identity(file)
}

fn publish_new(path: &Path, bytes: &[u8]) -> Result<(), String> {
    publish_new_with_stage_hook(path, bytes, |_staged| Ok(()))
}

fn publish_new_with_stage_hook(
    path: &Path,
    bytes: &[u8],
    after_sync: impl FnOnce(&Path) -> Result<(), String>,
) -> Result<(), String> {
    publish_new_with_hooks(path, bytes, after_sync, |_published| Ok(()))
}

fn publish_new_with_hooks(
    path: &Path,
    bytes: &[u8],
    after_sync: impl FnOnce(&Path) -> Result<(), String>,
    after_link: impl FnOnce(&Path) -> Result<(), String>,
) -> Result<(), String> {
    publish_new_with_directory_sync_hook(
        path,
        bytes,
        after_sync,
        after_link,
        sync_published_directory,
    )
}

// Syncing the inode alone does not make a newly linked directory entry durable.
// Windows does not support opening directories through std::fs::File; retain
// the previous best-effort boundary there rather than rejecting valid output.
fn sync_published_directory(directory: &Path) -> Result<(), String> {
    #[cfg(unix)]
    {
        // Use the nonblocking Linux descriptor opener so a pathname raced
        // from a directory to a FIFO cannot stall the durability barrier.
        let opened = open_canonical_file(directory)
            .map_err(|error| format!("cannot open publication directory: {error}"))?;
        let metadata = opened
            .metadata()
            .map_err(|error| format!("cannot inspect publication directory: {error}"))?;
        if !metadata.is_dir() {
            return Err(String::from("publication sync target is not a directory"));
        }
        opened
            .sync_all()
            .map_err(|error| format!("cannot sync publication directory: {error}"))
    }
    #[cfg(not(unix))]
    {
        let _directory = directory;
        Ok(())
    }
}

#[expect(
    clippy::too_many_arguments,
    reason = "separate stage, link and directory-sync failure injection hooks"
)]
fn publish_new_with_directory_sync_hook(
    path: &Path,
    bytes: &[u8],
    after_sync: impl FnOnce(&Path) -> Result<(), String>,
    after_link: impl FnOnce(&Path) -> Result<(), String>,
    sync_directory: impl FnMut(&Path) -> Result<(), String>,
) -> Result<(), String> {
    publish_new_with_postverify_hook(
        path,
        bytes,
        after_sync,
        after_link,
        sync_directory,
        |_stage| Ok(()),
    )
}

fn verified_output_basename(path: &Path) -> Result<&str, String> {
    if path.extension() != Some(OsStr::new(MALBOLGE_EXTENSION)) {
        return Err(String::from("output must have a .malbolge extension"));
    }
    path.file_name()
        .and_then(OsStr::to_str)
        .ok_or_else(|| String::from("output needs a UTF-8 filename"))
}

fn verify_cleaned_publication(
    paths: (&Path, Option<&Path>),
    bytes: &[u8],
    file: &mut fs::File,
    sync_directory: &mut impl FnMut(&Path) -> Result<(), String>,
) -> Result<(), String> {
    let (path, resolved_target) = paths;
    let target = resolved_target.ok_or("missing original resolved output path")?;
    let parent = target.parent().ok_or("cannot identify cleanup directory")?;
    // A synced final link does not persist the subsequent stage unlink.
    // Sync the same resolved directory again before reporting success.
    sync_directory(parent)?;
    let final_metadata = file
        .metadata()
        .map_err(|error| format!("cannot inspect cleaned output: {error}"))?;
    verify_fsynced_stage(path, file, bytes, (&final_metadata, 1, target))
}

fn cleanup_original_stage(staged: &Path, opened: io::Result<fs::Metadata>) -> Result<(), String> {
    match (opened, fs::symlink_metadata(staged)) {
        (Ok(original), Ok(named)) if canonical_wire_metadata_matches(&original, &named) => {
            fs::remove_file(staged)
                .map_err(|error| format!("stage cleanup failed after publication: {error}"))
        }
        // A pre-unlinked stage is safe only if its inode now has the final link.
        (Ok(original), Err(error))
            if error.kind() == io::ErrorKind::NotFound
                && cfg!(any(unix, windows))
                && has_exact_link_count(&original, 1) =>
        {
            Ok(())
        }
        (Ok(_), Ok(_)) => Err(String::from("stage cleanup rejected substituted pathname")),
        (Ok(_), Err(error)) => Err(format!("stage cleanup cannot inspect path: {error}")),
        (Err(error), _) => Err(format!("stage cleanup cannot inspect inode: {error}")),
    }
}

#[expect(
    clippy::too_many_arguments,
    reason = "inject independently scheduled stage cleanup race after final admission"
)]
fn publish_new_with_postverify_hook(
    path: &Path,
    bytes: &[u8],
    after_sync: impl FnOnce(&Path) -> Result<(), String>,
    after_link: impl FnOnce(&Path) -> Result<(), String>,
    mut sync_directory: impl FnMut(&Path) -> Result<(), String>,
    after_final_verify: impl FnOnce(&Path) -> Result<(), String>,
) -> Result<(), String> {
    let name = verified_output_basename(path)?;
    // A crashed publisher may leave its stage behind, and PIDs get recycled.
    // Create only a fresh path; never remove or reuse any collided stage.
    let (staged, mut file) = open_fresh_stage(path, name)?;
    let mut resolved_final_path = None;
    let outcome = (|| {
        // Capture the originally opened stage location before any externally
        // observable write or verification hooks. Stable symlinked parents are
        // allowed; a later symlink rebound to a moved directory is not.
        let resolved_stage = fs::canonicalize(&staged)
            .map_err(|error| format!("cannot resolve original stage: {error}"))?;
        let resolved_target = resolved_stage.with_file_name(name);
        resolved_final_path = Some(resolved_target.clone());
        file.write_all(bytes)
            .map_err(|error| format!("stage write failed: {error}"))?;
        file.sync_all()
            .map_err(|error| format!("stage sync failed: {error}"))?;
        let initial = file
            .metadata()
            .map_err(|error| format!("cannot inspect synced stage: {error}"))?;
        after_sync(&staged)?;
        verify_fsynced_stage(&staged, &mut file, bytes, (&initial, 1, &resolved_stage))?;
        fs::hard_link(&staged, path)
            .map_err(|error| format!("cannot publish new target: {error}"))?;
        after_link(path)?;
        let opened = file
            .metadata()
            .map_err(|error| format!("cannot inspect published stage: {error}"))?;
        let published = fs::symlink_metadata(path)
            .map_err(|error| format!("cannot inspect published target: {error}"))?;
        if !canonical_wire_metadata_matches(&opened, &published) {
            return Err(String::from(
                "published target inode changed after stage admission",
            ));
        }
        // The hard link exposes a writable inode. Recheck the final path and
        // exact bytes before claiming success; late mutation leaves an already
        // published target but cannot be falsely called a verified artifact.
        verify_fsynced_stage(path, &mut file, bytes, (&opened, 2, &resolved_target))?;
        // The final no-clobber hard link must survive a host crash before
        // reporting success. Sync the originally resolved parent, never a
        // newly redirected symlinked parent of the requested output path.
        let parent = resolved_target
            .parent()
            .ok_or("cannot identify publication directory")?;
        sync_directory(parent)?;
        // The durability barrier is not the end of the trust boundary: a
        // competing writer may replace the final name or rewrite its inode
        // while that directory is being synced. Check the same original
        // descriptor, pathname, link count and exact bytes once more before
        // declaring the published artifact verified.
        verify_fsynced_stage(path, &mut file, bytes, (&opened, 2, &resolved_target))?;
        after_final_verify(&staged)?;
        Ok(())
    })();
    // Retire only our own original staging inode. A stage pathname swapped
    // after the exclusive create belongs to the other writer and is preserved.
    let cleanup = cleanup_original_stage(&staged, file.metadata());
    // Unlinking the stage changes inode ctime and its link count. Re-admit the
    // original descriptor and final pathname *after* cleanup, requiring the
    // final output to be its only surviving hard link. A foreign alias created
    // after the last pre-cleanup verification must not authorize success.
    let post_cleanup = if outcome.is_ok() && cleanup.is_ok() {
        verify_cleaned_publication(
            (path, resolved_final_path.as_deref()),
            bytes,
            &mut file,
            &mut sync_directory,
        )
    } else {
        Ok(())
    };
    drop(file);
    // A committed final file survives a failed cleanup, but a surviving stage
    // or external alias remains a writable hard link. Never claim success
    // without final identity, byte and link-count admission after cleanup.
    // Never remove a foreign staging path; retain any primary publication error.
    outcome.and(cleanup).and(post_cleanup)
}

// On Linux/Android use nonblocking open first, *then* inspect the actual
// opened descriptor. A writerless FIFO (or one substituted for a regular
// symlink) cannot block acquisition; subsequent fstat refuses that handle.
// Ordinary regular-file symlinks remain valid.
#[cfg(any(target_os = "linux", target_os = "android"))]
fn open_canonical_file(path: &Path) -> io::Result<fs::File> {
    use std::os::unix::fs::OpenOptionsExt as _;

    // Linux asm-generic fcntl.h: O_NONBLOCK = 1 << 11. Regular files ignore
    // this status bit for reads; FIFO opens cannot wait for a writer.
    const LINUX_O_NONBLOCK: i32 = 1 << 11;
    OpenOptions::new()
        .read(true)
        .custom_flags(LINUX_O_NONBLOCK)
        .open(path)
}

#[cfg(not(any(target_os = "linux", target_os = "android")))]
fn open_canonical_file(path: &Path) -> io::Result<fs::File> {
    fs::File::open(path)
}

// A bounded read is not a stable snapshot unless the opened file and its
// source pathname still identify the same unchanged inode afterwards.
#[cfg(unix)]
fn canonical_wire_metadata_matches(before: &fs::Metadata, after: &fs::Metadata) -> bool {
    use std::os::unix::fs::MetadataExt as _;

    before.is_file()
        && after.is_file()
        && before.dev() == after.dev()
        && before.ino() == after.ino()
        && before.len() == after.len()
        && before.mtime() == after.mtime()
        && before.mtime_nsec() == after.mtime_nsec()
        && before.ctime() == after.ctime()
        && before.ctime_nsec() == after.ctime_nsec()
}

#[cfg(windows)]
fn canonical_wire_metadata_matches(before: &fs::Metadata, after: &fs::Metadata) -> bool {
    use std::os::windows::fs::MetadataExt as _;

    before.is_file()
        && after.is_file()
        && before.len() == after.len()
        && before.volume_serial_number().is_some()
        && before.volume_serial_number() == after.volume_serial_number()
        && before.file_index().is_some()
        && before.file_index() == after.file_index()
        && before.last_write_time() == after.last_write_time()
        && before.change_time() == after.change_time()
}

#[cfg(not(any(unix, windows)))]
fn canonical_wire_metadata_matches(before: &fs::Metadata, after: &fs::Metadata) -> bool {
    before.is_file()
        && after.is_file()
        && before.len() == after.len()
        && before.modified().ok().is_some()
        && before.modified().ok() == after.modified().ok()
}

fn read_canonical_wire(path: &Path, kind: &str) -> Result<Vec<u8>, String> {
    read_canonical_wire_with_reader(path, kind, |file, bytes| {
        file.take(MAX_CANONICAL_WIRE_BYTES.saturating_add(1))
            .read_to_end(bytes)
    })
}

fn admit_wire_read_receipt(kind: &str, reported: usize, collected: usize) -> Result<(), String> {
    if reported != collected {
        return Err(format!(
            "canonical {kind} wire read count disagrees with collected bytes",
        ));
    }
    Ok(())
}

fn read_canonical_wire_with_reader(
    path: &Path,
    kind: &str,
    read: impl FnOnce(&mut fs::File, &mut Vec<u8>) -> io::Result<usize>,
) -> Result<Vec<u8>, String> {
    // Linux/Android open the descriptor nonblocking and inspect that very
    // handle. Other platforms retain the bounded pre-open pathname guard.
    #[cfg(not(any(target_os = "linux", target_os = "android")))]
    {
        let path_metadata = fs::metadata(path)
            .map_err(|error| format!("cannot inspect canonical {kind} path: {error}"))?;
        if !path_metadata.is_file()
            || path_metadata.len() == 0
            || path_metadata.len() > MAX_CANONICAL_WIRE_BYTES
        {
            return Err(String::from(
                "canonical wire must be a nonempty bounded regular file",
            ));
        }
    }
    // A changed parent may lead through a symlink to another hard link of
    // the exact same inode. Metadata equality alone cannot bind that path.
    // Linux exposes the actual opened dentry through /proc/self/fd; check
    // it both before and after the caller-supplied bounded reader.
    #[cfg(target_os = "linux")]
    let expected_opened_path = fs::canonicalize(path)
        .map_err(|error| format!("cannot resolve canonical {kind} path: {error}"))?;
    let mut file = open_canonical_file(path)
        .map_err(|error| format!("cannot open canonical {kind} wire: {error}"))?;
    #[cfg(target_os = "linux")]
    verify_opened_canonical_path(&file, &expected_opened_path, kind)?;
    let metadata = file
        .metadata()
        .map_err(|error| format!("cannot inspect canonical {kind} wire: {error}"))?;
    if !metadata.is_file() || metadata.len() == 0 || metadata.len() > MAX_CANONICAL_WIRE_BYTES {
        return Err(String::from(
            "canonical wire must be a nonempty bounded regular file",
        ));
    }
    let before = fs::metadata(path)
        .map_err(|error| format!("cannot inspect canonical {kind} path: {error}"))?;
    if !canonical_wire_metadata_matches(&metadata, &before) {
        return Err(String::from("canonical wire changed during read"));
    }
    let mut bytes = Vec::new();
    let bytes_read = read(&mut file, &mut bytes)
        .map_err(|error| format!("cannot read canonical {kind} wire: {error}"))?;
    admit_wire_read_receipt(kind, bytes_read, bytes.len())?;
    let length = u64::try_from(bytes.len())
        .map_err(|_error| String::from("ternary wire length overflow"))?;
    if length > MAX_CANONICAL_WIRE_BYTES || length != metadata.len() {
        return Err(String::from(
            "ternary wire read length disagrees with bounded file",
        ));
    }
    // Reject observed source or pathname mutation before attributing any
    // mismatch to the reader's returned bytes.
    let after = file
        .metadata()
        .map_err(|error| format!("cannot recheck canonical {kind} wire: {error}"))?;
    let current = fs::metadata(path)
        .map_err(|error| format!("cannot recheck canonical {kind} path: {error}"))?;
    if !canonical_wire_metadata_matches(&metadata, &after)
        || !canonical_wire_metadata_matches(&metadata, &current)
    {
        return Err(String::from("canonical wire changed during read"));
    }
    #[cfg(target_os = "linux")]
    {
        verify_opened_canonical_path(&file, &expected_opened_path, kind)?;
        verify_requested_canonical_path(path, &expected_opened_path, kind)?;
    }
    // A correct byte count alone does not bind a replaceable reader's
    // returned buffer to the opened descriptor. Independently reread the
    // same bounded file before accepting compiler input bytes.
    file.rewind()
        .map_err(|error| format!("cannot rewind canonical {kind} wire: {error}"))?;
    let mut source_bytes = Vec::new();
    let _count = (&mut file)
        .take(MAX_CANONICAL_WIRE_BYTES.saturating_add(1))
        .read_to_end(&mut source_bytes)
        .map_err(|error| format!("cannot corroborate canonical {kind} wire: {error}"))?;
    if source_bytes != bytes {
        return Err(format!(
            "canonical {kind} wire reader bytes disagree with opened source",
        ));
    }
    let after = file
        .metadata()
        .map_err(|error| format!("cannot recheck canonical {kind} wire: {error}"))?;
    let current = fs::metadata(path)
        .map_err(|error| format!("cannot recheck canonical {kind} path: {error}"))?;
    if !canonical_wire_metadata_matches(&metadata, &after)
        || !canonical_wire_metadata_matches(&metadata, &current)
    {
        return Err(String::from("canonical wire changed during read"));
    }
    #[cfg(target_os = "linux")]
    {
        verify_opened_canonical_path(&file, &expected_opened_path, kind)?;
        verify_requested_canonical_path(path, &expected_opened_path, kind)?;
    }
    Ok(bytes)
}

// The opened descriptor can still name its original physical path after an
// initially stable parent symlink is rebound to a different hard link of the
// same inode. The caller's requested path must still resolve to that source.
#[cfg(target_os = "linux")]
fn verify_requested_canonical_path(path: &Path, expected: &Path, kind: &str) -> Result<(), String> {
    let current = fs::canonicalize(path)
        .map_err(|error| format!("cannot resolve canonical {kind} path after read: {error}"))?;
    if current != expected {
        return Err(String::from(
            "canonical wire requested path changed during read",
        ));
    }
    Ok(())
}

#[cfg(target_os = "linux")]
fn verify_opened_canonical_path(
    file: &fs::File,
    expected: &Path,
    kind: &str,
) -> Result<(), String> {
    use std::os::fd::AsRawFd as _;
    let descriptor_path = format!("/proc/self/fd/{}", file.as_raw_fd());
    let opened_path = fs::read_link(descriptor_path)
        .map_err(|error| format!("cannot inspect canonical {kind} opened path: {error}"))?;
    if opened_path != expected {
        return Err(String::from(
            "canonical wire opened path changed during read",
        ));
    }
    Ok(())
}

fn read_canonical_stdin(kind: &str) -> Result<Vec<u8>, String> {
    // Input must finish (EOF), but memory is bounded even if the writer
    // supplies an unlimited stream. Never publish until canonical admission.
    let mut bytes = Vec::new();
    let _read = io::stdin()
        .lock()
        .take(MAX_CANONICAL_WIRE_BYTES.saturating_add(1))
        .read_to_end(&mut bytes)
        .map_err(|error| format!("cannot read canonical {kind} stdin: {error}"))?;
    if bytes.is_empty()
        || u64::try_from(bytes.len()).map_err(|_error| "canonical stdin length overflow")?
            > MAX_CANONICAL_WIRE_BYTES
    {
        return Err(String::from(
            "canonical stdin must be nonempty and at most 1 MiB",
        ));
    }
    Ok(bytes)
}

#[expect(
    clippy::too_many_lines,
    reason = "source-bound mode-dependent VM witnesses"
)]
fn verified_ternary_bytes(
    bytes: &[u8],
    mode: ByteTraceMode,
    profile: &'static malbolge::ProfileDescriptor,
) -> Result<VerifiedSource, String> {
    let program = canonical_ternary_program(bytes)
        .map_err(|error| format!("canonical ternary wire rejected: {error:?}"))?;
    let layout = match mode {
        ByteTraceMode::AdjacentEcho => encode_successful_byte_echo(&program, profile),
        ByteTraceMode::EmptyVoid => encode_empty_void_function(&program, profile),
        ByteTraceMode::InitialZero => encode_initial_zero_outputs(&program, profile),
        ByteTraceMode::LatestRead => encode_successful_latest_byte_trace(&program, profile),
        ByteTraceMode::ZeroPrefixedLatest => {
            encode_zero_prefixed_latest_byte_trace(&program, profile)
        }
        ByteTraceMode::IdentityByteBitcast => encode_latest_byte_identity_trace(&program, profile),
        ByteTraceMode::RotatedLiteral => encode_rotated_byte_literal(&program, profile),
        ByteTraceMode::ZeroThenLiteral => encode_zero_then_literal(&program, profile),
        ByteTraceMode::DistinctLiteralPair => encode_distinct_literal_pair(&program, profile),
        ByteTraceMode::DistinctLiteralTriple => encode_distinct_literal_triple(&program, profile),
        ByteTraceMode::DistinctLiteralQuad => encode_distinct_literal_quad(&program, profile),
        ByteTraceMode::DistinctLiteralQuint => encode_distinct_literal_quint(&program, profile),
        ByteTraceMode::DistinctLiteralSix => encode_distinct_literal_six(&program, profile),
        ByteTraceMode::DistinctLiteralSeven => encode_distinct_literal_seven(&program, profile),
        ByteTraceMode::DistinctLiteralEight => encode_distinct_literal_eight(&program, profile),
        ByteTraceMode::DistinctLiteralNine => encode_distinct_literal_nine(&program, profile),
        ByteTraceMode::DistinctLiteralTen => encode_distinct_literal_ten(&program, profile),
        ByteTraceMode::DistinctLiteralEleven => encode_distinct_literal_eleven(&program, profile),
        ByteTraceMode::DistinctLiteralTwelve => encode_distinct_literal_twelve(&program, profile),
        ByteTraceMode::DistinctLiteralThirteen => {
            encode_distinct_literal_thirteen(&program, profile)
        }
        ByteTraceMode::DistinctLiteralFourteen => {
            encode_distinct_literal_fourteen(&program, profile)
        }
        ByteTraceMode::DistinctLiteralFifteen => encode_distinct_literal_fifteen(&program, profile),
        ByteTraceMode::DistinctLiteralSixteen => encode_distinct_literal_sixteen(&program, profile),
        ByteTraceMode::DistinctLiteralSeventeen => {
            encode_distinct_literal_seventeen(&program, profile)
        }
        ByteTraceMode::DistinctLiteralEighteen => {
            encode_distinct_literal_eighteen(&program, profile)
        }
        ByteTraceMode::DistinctLiteralNineteen => {
            encode_distinct_literal_nineteen(&program, profile)
        }
    }
    .map_err(|error| format!("ternary byte-trace bridge rejected: {error:?}"))?;
    if layout.profile_id() != profile.id() || layout.profile_fingerprint() != profile.fingerprint()
    {
        return Err(String::from(
            "ternary source profile mismatch after admission",
        ));
    }
    let operations = &program
        .functions
        .first()
        .ok_or("bridge accepted no ternary function")?
        .operations;
    let effect_witness = if matches!(mode, ByteTraceMode::EmptyVoid) {
        Some(SourceEffectWitness::EmptyVoid)
    } else if matches!(mode, ByteTraceMode::RotatedLiteral) {
        let [TernaryOperation::MaterializeU8 { scalar, .. }, ..] = operations.as_slice() else {
            return Err(String::from("missing seeded byte scalar"));
        };
        Some(SourceEffectWitness::RotatedLiteral {
            byte: scalar.bits(),
            outputs: operations
                .iter()
                .filter(|operation| matches!(operation, TernaryOperation::ByteOutput { .. }))
                .count(),
        })
    } else if matches!(mode, ByteTraceMode::ZeroThenLiteral) {
        let [
            TernaryOperation::MaterializeU8 { .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::MaterializeU8 { scalar, .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::ReturnVoid { .. },
        ] = operations.as_slice()
        else {
            return Err(String::from("missing zero-then-literal effects"));
        };
        Some(SourceEffectWitness::ZeroThenLiteral {
            byte: scalar.bits(),
        })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralPair) {
        let [
            TernaryOperation::MaterializeU8 { scalar: first, .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::MaterializeU8 { scalar: second, .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::ReturnVoid { .. },
        ] = operations.as_slice()
        else {
            return Err(String::from("missing distinct-literal-pair effects"));
        };
        Some(SourceEffectWitness::DistinctLiteralPair {
            first: first.bits(),
            second: second.bits(),
        })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralTriple) {
        let [
            TernaryOperation::MaterializeU8 { scalar: first, .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::MaterializeU8 { scalar: second, .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::MaterializeU8 { scalar: third, .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::ReturnVoid { .. },
        ] = operations.as_slice()
        else {
            return Err(String::from("missing distinct-literal-triple effects"));
        };
        Some(SourceEffectWitness::DistinctLiteralTriple {
            bytes: [first.bits(), second.bits(), third.bits()],
        })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralQuad) {
        let [
            TernaryOperation::MaterializeU8 { scalar: first, .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::MaterializeU8 { scalar: second, .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::MaterializeU8 { scalar: third, .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::MaterializeU8 { scalar: fourth, .. },
            TernaryOperation::ByteOutput { .. },
            TernaryOperation::ReturnVoid { .. },
        ] = operations.as_slice()
        else {
            return Err(String::from("missing distinct-literal-quad effects"));
        };
        Some(SourceEffectWitness::DistinctLiteralQuad {
            bytes: [first.bits(), second.bits(), third.bits(), fourth.bits()],
        })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralQuint) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-quint return"));
        };
        if pairs.len() != 5 {
            return Err(String::from("missing distinct-literal-quint effects"));
        }
        let mut bytes = [0; 5];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-quint effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-quint SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralQuint { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralSix) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-six return"));
        };
        if pairs.len() != 6 {
            return Err(String::from("missing distinct-literal-six effects"));
        }
        let mut bytes = [0; 6];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-six effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-six SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralSix { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralSeven) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-seven return"));
        };
        if pairs.len() != 7 {
            return Err(String::from("missing distinct-literal-seven effects"));
        }
        let mut bytes = [0; 7];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-seven effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-seven SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralSeven { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralEight) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-eight return"));
        };
        if pairs.len() != 8 {
            return Err(String::from("missing distinct-literal-eight effects"));
        }
        let mut bytes = [0; 8];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-eight effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-eight SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralEight { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralNine) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-nine return"));
        };
        if pairs.len() != 9 {
            return Err(String::from("missing distinct-literal-nine effects"));
        }
        let mut bytes = [0; 9];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-nine effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-nine SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralNine { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralTen) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-ten return"));
        };
        if pairs.len() != 10 {
            return Err(String::from("missing distinct-literal-ten effects"));
        }
        let mut bytes = [0; 10];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-ten effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-ten SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralTen { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralEleven) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-eleven return"));
        };
        if pairs.len() != 11 {
            return Err(String::from("missing distinct-literal-eleven effects"));
        }
        let mut bytes = [0; 11];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-eleven effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-eleven SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralEleven { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralTwelve) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-twelve return"));
        };
        if pairs.len() != 12 {
            return Err(String::from("missing distinct-literal-twelve effects"));
        }
        let mut bytes = [0; 12];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-twelve effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-twelve SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralTwelve { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralThirteen) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-thirteen return"));
        };
        if pairs.len() != 13 {
            return Err(String::from("missing distinct-literal-thirteen effects"));
        }
        let mut bytes = [0; 13];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-thirteen effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-thirteen SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralThirteen { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralFourteen) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-fourteen return"));
        };
        if pairs.len() != 14 {
            return Err(String::from("missing distinct-literal-fourteen effects"));
        }
        let mut bytes = [0; 14];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-fourteen effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-fourteen SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralFourteen { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralFifteen) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-fifteen return"));
        };
        if pairs.len() != 15 {
            return Err(String::from("missing distinct-literal-fifteen effects"));
        }
        let mut bytes = [0; 15];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-fifteen effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-fifteen SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralFifteen { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralSixteen) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-sixteen return"));
        };
        if pairs.len() != 16 {
            return Err(String::from("missing distinct-literal-sixteen effects"));
        }
        let mut bytes = [0; 16];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-sixteen effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-sixteen SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralSixteen { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralSeventeen) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-seventeen return"));
        };
        if pairs.len() != 17 {
            return Err(String::from("missing distinct-literal-seventeen effects"));
        }
        let mut bytes = [0; 17];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-seventeen effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-seventeen SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralSeventeen { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralEighteen) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-eighteen return"));
        };
        if pairs.len() != 18 {
            return Err(String::from("missing distinct-literal-eighteen effects"));
        }
        let mut bytes = [0; 18];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-eighteen effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-eighteen SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralEighteen { bytes })
    } else if matches!(mode, ByteTraceMode::DistinctLiteralNineteen) {
        let (pairs, remainder) = operations.as_chunks::<2>();
        let [TernaryOperation::ReturnVoid { .. }] = remainder else {
            return Err(String::from("missing distinct-literal-nineteen return"));
        };
        if pairs.len() != 19 {
            return Err(String::from("missing distinct-literal-nineteen effects"));
        }
        let mut bytes = [0; 19];
        for (index, [constant, output]) in pairs.iter().enumerate() {
            let (
                TernaryOperation::MaterializeU8 { result, scalar, .. },
                TernaryOperation::ByteOutput { value, .. },
            ) = (constant, output)
            else {
                return Err(String::from("missing distinct-literal-nineteen effects"));
            };
            if result != value {
                return Err(String::from("distinct-literal-nineteen SSA mismatch"));
            }
            bytes[index] = scalar.bits();
        }
        Some(SourceEffectWitness::DistinctLiteralNineteen { bytes })
    } else if matches!(mode, ByteTraceMode::InitialZero) {
        Some(SourceEffectWitness::InitialZero {
            outputs: operations
                .iter()
                .filter(|operation| matches!(operation, TernaryOperation::ByteOutput { .. }))
                .count(),
        })
    } else {
        let effects = operations
            .iter()
            .filter(|operation| {
                matches!(
                    operation,
                    TernaryOperation::ByteInput { .. } | TernaryOperation::ByteOutput { .. }
                )
            })
            .scan(false, |seen_input, operation| {
                if matches!(operation, TernaryOperation::ByteInput { .. }) {
                    *seen_input = true;
                    Some(SuccessfulByteEffect::Input)
                } else if matches!(mode, ByteTraceMode::ZeroPrefixedLatest) && !*seen_input {
                    Some(SuccessfulByteEffect::ZeroOutput)
                } else {
                    Some(SuccessfulByteEffect::Output)
                }
            })
            .collect();
        Some(SourceEffectWitness::SuccessfulByteTrace(effects))
    };
    Ok(VerifiedSource {
        effect_witness,
        source: layout.source().to_vec(),
        steps: layout.executed_code_positions().len(),
    })
}

fn verified_typed_bytes(
    typed_bytes: &[u8],
    mode: ByteTraceMode,
    profile: &'static malbolge::ProfileDescriptor,
) -> Result<VerifiedSource, String> {
    let compiled = match mode {
        ByteTraceMode::AdjacentEcho => compile_canonical_typed_echo(typed_bytes, profile),
        ByteTraceMode::EmptyVoid => compile_canonical_typed_empty_void(typed_bytes, profile),
        ByteTraceMode::InitialZero => {
            compile_canonical_typed_initial_zero_outputs(typed_bytes, profile)
        }
        ByteTraceMode::LatestRead => {
            compile_canonical_typed_latest_byte_trace(typed_bytes, profile)
        }
        ByteTraceMode::ZeroPrefixedLatest => {
            compile_canonical_typed_zero_prefixed_latest_byte_trace(typed_bytes, profile)
        }
        ByteTraceMode::IdentityByteBitcast => {
            compile_canonical_typed_identity_byte_trace(typed_bytes, profile)
        }
        ByteTraceMode::RotatedLiteral => {
            compile_canonical_typed_rotated_byte_literal(typed_bytes, profile)
        }
        ByteTraceMode::ZeroThenLiteral => {
            compile_canonical_typed_zero_then_literal(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralPair => {
            compile_canonical_typed_distinct_literal_pair(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralTriple => {
            compile_canonical_typed_distinct_literal_triple(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralQuad => {
            compile_canonical_typed_distinct_literal_quad(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralQuint => {
            compile_canonical_typed_distinct_literal_quint(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralSix => {
            compile_canonical_typed_distinct_literal_six(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralSeven => {
            compile_canonical_typed_distinct_literal_seven(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralEight => {
            compile_canonical_typed_distinct_literal_eight(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralNine => {
            compile_canonical_typed_distinct_literal_nine(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralTen => {
            compile_canonical_typed_distinct_literal_ten(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralEleven => {
            compile_canonical_typed_distinct_literal_eleven(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralTwelve => {
            compile_canonical_typed_distinct_literal_twelve(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralThirteen => {
            compile_canonical_typed_distinct_literal_thirteen(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralFourteen => {
            compile_canonical_typed_distinct_literal_fourteen(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralFifteen => {
            compile_canonical_typed_distinct_literal_fifteen(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralSixteen => {
            compile_canonical_typed_distinct_literal_sixteen(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralSeventeen => {
            compile_canonical_typed_distinct_literal_seventeen(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralEighteen => {
            compile_canonical_typed_distinct_literal_eighteen(typed_bytes, profile)
        }
        ByteTraceMode::DistinctLiteralNineteen => {
            compile_canonical_typed_distinct_literal_nineteen(typed_bytes, profile)
        }
    }
    .map_err(|error| format!("canonical typed byte bridge rejected: {error:?}"))?;
    // The typed adapter proposes an MCTR wire and encoded layout. Re-decode
    // its actual MCTR bytes and re-encode target code through the independent
    // ternary bridge before any guest execution or file publication.
    let admitted = verified_ternary_bytes(compiled.ternary_bytes(), mode, profile)?;
    if admitted.source != compiled.layout().source()
        || admitted.steps != compiled.layout().executed_code_positions().len()
        || compiled.layout().profile_id() != profile.id()
        || compiled.layout().profile_fingerprint() != profile.fingerprint()
    {
        return Err(String::from(
            "independently admitted typed and ternary target source disagree",
        ));
    }
    Ok(admitted)
}

fn verified_source(
    spec: &SourceSpec,
    profile: &'static malbolge::ProfileDescriptor,
) -> Result<VerifiedSource, String> {
    match spec {
        SourceSpec::AutoLayout(logical) => {
            let proposed = encode_auto_padded_forward_layout(profile, logical)
                .map_err(|error| format!("auto-layout rejected: {error:?}"))?;
            let artifact = admit_linear_layout(
                profile,
                proposed.operations(),
                proposed.layout().source(),
                LinearProfileIdentity {
                    fingerprint: proposed.layout().profile_fingerprint(),
                    id: proposed.layout().profile_id(),
                },
            )
            .map_err(|error| format!("auto-layout independent admission failed: {error:?}"))?;
            Ok(VerifiedSource {
                effect_witness: None,
                source: artifact.source().to_vec(),
                steps: artifact.executed_code_positions().len(),
            })
        }
        SourceSpec::MachineOperations(operations) => {
            let artifact = encode_linear_layout(profile, operations)
                .map_err(|error| format!("layout rejected: {error:?}"))?;
            let admitted = admit_linear_layout(
                profile,
                operations,
                artifact.source(),
                LinearProfileIdentity {
                    fingerprint: artifact.profile_fingerprint(),
                    id: artifact.profile_id(),
                },
            )
            .map_err(|error| format!("source admission failed: {error:?}"))?;
            Ok(VerifiedSource {
                effect_witness: None,
                source: admitted.source().to_vec(),
                steps: admitted.executed_code_positions().len(),
            })
        }
        SourceSpec::CanonicalTernaryFile { path, mode } => {
            verified_ternary_bytes(&read_canonical_wire(path, "ternary")?, *mode, profile)
        }
        SourceSpec::CanonicalTypedFile { path, mode } => {
            verified_typed_bytes(&read_canonical_wire(path, "typed")?, *mode, profile)
        }
        SourceSpec::CanonicalTernaryStdin { mode } => {
            verified_ternary_bytes(&read_canonical_stdin("ternary")?, *mode, profile)
        }
        SourceSpec::CanonicalTypedStdin { mode } => {
            verified_typed_bytes(&read_canonical_stdin("typed")?, *mode, profile)
        }
    }
}

fn verify_successful_byte_trace(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    effects: &[SuccessfulByteEffect],
) -> Result<(), String> {
    let patterns: [[u8; 8]; 2] = [
        [0, 255, 173, 128, 1, 254, 10, 65],
        [255, 0, 82, 127, 254, 1, 42, 13],
    ];
    let reads = effects
        .iter()
        .filter(|effect| matches!(effect, SuccessfulByteEffect::Input))
        .count();
    if reads == 0 || effects.len().checked_add(1) != Some(artifact.steps) {
        return Err(String::from(
            "ternary bridge emitted an unexpected effect geometry",
        ));
    }
    for pattern in patterns {
        let input: Vec<u8> = pattern.into_iter().cycle().take(reads).collect();
        let mut consumed = 0;
        let mut latest = None;
        let mut expected_output = Vec::new();
        for effect in effects {
            match effect {
                SuccessfulByteEffect::Input => {
                    latest = input.get(consumed).copied();
                    consumed = consumed.checked_add(1).ok_or("byte input count overflow")?;
                }
                SuccessfulByteEffect::Output => {
                    expected_output.push(latest.ok_or("output before successful input")?);
                }
                SuccessfulByteEffect::ZeroOutput if latest.is_none() => {
                    expected_output.push(0);
                }
                SuccessfulByteEffect::ZeroOutput => {
                    return Err(String::from("zero output after accumulator overwrite"));
                }
            }
        }
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("successful-byte VM load failed: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps: count, .. }) if count == artifact.steps)
        {
            return Err(String::from("successful-byte VM trace did not terminate"));
        }
        if vm.output() != expected_output || vm.input_consumed() != reads {
            return Err(String::from("successful-byte VM trace mismatch"));
        }
    }
    Ok(())
}

// An effect-free function still reaches its actual guest halt. The second
// admission independently proves no output or input effects for two inputs.
fn verify_empty_void(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
) -> Result<(), String> {
    if artifact.steps != 2 {
        return Err(String::from("empty-void guest halt geometry disagrees"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("empty-void guest VM load failed: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || !vm.output().is_empty()
        {
            return Err(String::from("empty-void guest trace mismatch"));
        }
    }
    Ok(())
}

// Constant-zero emission has no successful input effects: the selected VM
// must emit each zero from initial A=0 while ignoring any supplied guest stdin.
fn verify_initial_zero_outputs(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    outputs: usize,
) -> Result<(), String> {
    if outputs == 0 || outputs.checked_add(1) != Some(artifact.steps) {
        return Err(String::from("initial-zero guest output geometry disagrees"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("initial-zero guest VM load failed: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output().len() != outputs
            || vm.output().iter().any(|byte| *byte != 0)
        {
            return Err(String::from("initial-zero guest VM output mismatch"));
        }
    }
    Ok(())
}

// The bridge proposes a seed; publication repeats the complete VM witness.
fn verify_rotated_literal(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    byte: u8,
    outputs: usize,
) -> Result<(), String> {
    if outputs == 0 || artifact.steps < outputs.saturating_add(3) {
        return Err(String::from(
            "seeded literal guest output geometry disagrees",
        ));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("seeded literal guest load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output().len() != outputs
            || vm.output().iter().any(|actual| *actual != byte)
        {
            return Err(String::from("rotated literal guest output disagrees"));
        }
    }
    Ok(())
}

// Publication independently re-runs the full effect order in the actual VM.
fn verify_zero_then_literal(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    byte: u8,
) -> Result<(), String> {
    if artifact.steps < 5 || !matches!(byte, b'Z' | b'P' | b'T' | b'S') {
        return Err(String::from("zero-then-literal guest geometry disagrees"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("zero-then-literal guest load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != [0, byte]
        {
            return Err(String::from("zero-then-literal guest output disagrees"));
        }
    }
    Ok(())
}

// Independent publisher proof: both source bytes require fresh guest writes.
fn verify_distinct_literal_pair(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    first: u8,
    second: u8,
) -> Result<(), String> {
    let expected_steps = match (first, second) {
        (b'Y', b'/') => 6,
        (b'Y', b'$') => 7,
        (b'Q', b'.') => 8,
        _ => return Err(String::from("distinct-literal pair has no guest witness")),
    };
    if artifact.steps != expected_steps {
        return Err(String::from("distinct-literal guest geometry disagrees"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal guest load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != [first, second]
        {
            return Err(String::from("distinct-literal guest output disagrees"));
        }
    }
    Ok(())
}

// Independent file-publisher proof that every byte was guest-computed.
fn verify_distinct_literal_triple(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 3],
) -> Result<(), String> {
    let expected_steps = match &bytes {
        b"Z%H" => 8,
        b"Q.O" => 9,
        b"Y-P" => 10,
        b"T\"O" => 12,
        b"T\"Q" => 14,
        _ => return Err(String::from("distinct-literal triple has no guest witness")),
    };
    if artifact.steps != expected_steps {
        return Err(String::from("distinct-literal triple geometry disagrees"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal triple load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal triple output disagrees"));
        }
    }
    Ok(())
}

// Reopen the five-source-byte claim under the normative profile VM.
fn verify_distinct_literal_quint(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 5],
) -> Result<(), String> {
    if bytes != *b"Q\"\x1b79" || artifact.steps != 23 {
        return Err(String::from("distinct-literal quint has no guest witness"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal quint load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal quint output disagrees"));
        }
    }
    Ok(())
}

// Reopen the six-source-byte claim under the normative profile VM.
fn verify_distinct_literal_six(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 6],
) -> Result<(), String> {
    if bytes != *b"Q\x1cO\x1dP\x1b" || artifact.steps != 15 {
        return Err(String::from("distinct-literal six has no guest witness"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal six load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal six output disagrees"));
        }
    }
    Ok(())
}

// Reopen the seven-source-byte claim under the normative profile VM.
fn verify_distinct_literal_seven(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 7],
) -> Result<(), String> {
    if bytes != *b"6>5\x02T\x1f\x18" || artifact.steps != 21 {
        return Err(String::from("distinct-literal seven has no guest witness"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal seven load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal seven output disagrees"));
        }
    }
    Ok(())
}

// Reopen the eight-source-byte claim under the normative profile VM.
fn verify_distinct_literal_eight(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 8],
) -> Result<(), String> {
    if bytes != *b"S \x17<6\x01R\x06" || artifact.steps != 21 {
        return Err(String::from("distinct-literal eight has no guest witness"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal eight load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal eight output disagrees"));
        }
    }
    Ok(())
}

// Reopen the nine-source-byte claim under the normative profile VM.
fn verify_distinct_literal_nine(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 9],
) -> Result<(), String> {
    if bytes != *b"T=\x8d\xd1\xc0\xb4\xbf\xd2\xa2" || artifact.steps != 21 {
        return Err(String::from("distinct-literal nine has no guest witness"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal nine load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal nine output disagrees"));
        }
    }
    Ok(())
}

// Reopen the ten-source-byte claim under the normative profile VM.
fn verify_distinct_literal_ten(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 10],
) -> Result<(), String> {
    if bytes != *b"Q\"\xfd\xce\xa5\x98\xba\xb6\x87\xcb" || artifact.steps != 23 {
        return Err(String::from("distinct-literal ten has no guest witness"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal ten load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal ten output disagrees"));
        }
    }
    Ok(())
}

// Reopen the eleven-source-byte claim under the normative profile VM.
fn verify_distinct_literal_eleven(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 11],
) -> Result<(), String> {
    if bytes != *b"P\x1d\x1a6\x05\xb4\xba\xb3\x84\xcf\x9e" || artifact.steps != 24 {
        return Err(String::from("distinct-literal eleven has no guest witness"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal eleven load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal eleven output disagrees"));
        }
    }
    Ok(())
}

// Reopen the twelve-source-byte claim under the normative profile VM.
fn verify_distinct_literal_twelve(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 12],
) -> Result<(), String> {
    if bytes != *b"Q748\xfb\xce\x9f\x98\xb8\xb4\x83\xcd" || artifact.steps != 27 {
        return Err(String::from("distinct-literal twelve has no guest witness"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal twelve load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal twelve output disagrees"));
        }
    }
    Ok(())
}

fn verify_distinct_literal_thirteen(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 13],
) -> Result<(), String> {
    if bytes != *b"BC0\x16T\x09\xbf\xc6\xc8\x87\xe3\xab\xa4" || artifact.steps != 29 {
        return Err(String::from(
            "distinct-literal thirteen has no guest witness",
        ));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal thirteen load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal thirteen output disagrees"));
        }
    }
    Ok(())
}

fn verify_distinct_literal_fourteen(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 14],
) -> Result<(), String> {
    if bytes != *b"YE,HS\x17LO=@[1\x194" || artifact.steps != 31 {
        return Err(String::from(
            "distinct-literal fourteen has no guest witness",
        ));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal fourteen load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal fourteen output disagrees"));
        }
    }
    Ok(())
}

fn verify_distinct_literal_fifteen(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 15],
) -> Result<(), String> {
    if bytes != *b"Q.\x198>\x89\xd2\xad\xa3\xb7\xc8\x88\x08\xd5\xc6" || artifact.steps != 33 {
        return Err(String::from(
            "distinct-literal fifteen has no guest witness",
        ));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal fifteen load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal fifteen output disagrees"));
        }
    }
    Ok(())
}

fn verify_distinct_literal_sixteen(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 16],
) -> Result<(), String> {
    if bytes != *b"?I6\x13Z\x0a\xba\xb3\xc3\x86\xcc\xaa\x01\x07\xd5\xc5" || artifact.steps != 35 {
        return Err(String::from(
            "distinct-literal sixteen has no guest witness",
        ));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal sixteen load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal sixteen output disagrees"));
        }
    }
    Ok(())
}

fn verify_distinct_literal_seventeen(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 17],
) -> Result<(), String> {
    if bytes != *b"Y?,HP\x1b\x182\x15MK;B\x0fD0\x17" || artifact.steps != 37 {
        return Err(String::from(
            "distinct-literal seventeen has no guest witness",
        ));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal seventeen load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal seventeen output disagrees"));
        }
    }
    Ok(())
}

fn verify_distinct_literal_eighteen(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 18],
) -> Result<(), String> {
    if bytes != *b"\x54\x22\x19\x3e\x38\x03\x09\xdd\x87\xd1\xa5\x99\xbf\x08\xc7\xc6\xc2\x91"
        || artifact.steps != 39
    {
        return Err(String::from(
            "distinct-literal eighteen has no guest witness",
        ));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal eighteen load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal eighteen output disagrees"));
        }
    }
    Ok(())
}

fn verify_distinct_literal_nineteen(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 19],
) -> Result<(), String> {
    if bytes != *b"S!\x1a<8\x03\x17U\x0eI+\x10F\x16@L:\x19X" || artifact.steps != 40 {
        return Err(String::from(
            "distinct-literal nineteen has no guest witness",
        ));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal nineteen load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal nineteen output disagrees"));
        }
    }
    Ok(())
}

// Independently re-execute the four-source-byte candidate before publication.
fn verify_distinct_literal_quad(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    bytes: [u8; 4],
) -> Result<(), String> {
    if bytes != *b"T=4>" || artifact.steps != 21 {
        return Err(String::from("distinct-literal quad has no guest witness"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("distinct-literal quad load: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output() != bytes
        {
            return Err(String::from("distinct-literal quad output disagrees"));
        }
    }
    Ok(())
}

fn execute(spec: &CommandSpec) -> Result<(), String> {
    let profile = target_profile(&spec.profile).ok_or("unknown canonical target profile")?;
    let artifact = verified_source(&spec.source, profile)?;
    let mut vm = ProfileMachine::from_source(profile, &artifact.source, Vec::new())
        .map_err(|error| format!("normative VM rejected source: {error:?}"))?;
    if !matches!(vm.run(artifact.steps), Ok(RunOutcome::Terminated { steps: count, .. }) if count == artifact.steps)
    {
        return Err(String::from(
            "normative VM did not halt at the proven code step",
        ));
    }
    match &artifact.effect_witness {
        Some(SourceEffectWitness::SuccessfulByteTrace(effects)) => {
            verify_successful_byte_trace(profile, &artifact, effects)?;
        }
        Some(SourceEffectWitness::EmptyVoid) => {
            verify_empty_void(profile, &artifact)?;
        }
        Some(SourceEffectWitness::InitialZero { outputs }) => {
            verify_initial_zero_outputs(profile, &artifact, *outputs)?;
        }
        Some(SourceEffectWitness::RotatedLiteral { byte, outputs }) => {
            verify_rotated_literal(profile, &artifact, *byte, *outputs)?;
        }
        Some(SourceEffectWitness::ZeroThenLiteral { byte }) => {
            verify_zero_then_literal(profile, &artifact, *byte)?;
        }
        Some(SourceEffectWitness::DistinctLiteralPair { first, second }) => {
            verify_distinct_literal_pair(profile, &artifact, *first, *second)?;
        }
        Some(SourceEffectWitness::DistinctLiteralTriple { bytes }) => {
            verify_distinct_literal_triple(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralQuad { bytes }) => {
            verify_distinct_literal_quad(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralQuint { bytes }) => {
            verify_distinct_literal_quint(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralSix { bytes }) => {
            verify_distinct_literal_six(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralSeven { bytes }) => {
            verify_distinct_literal_seven(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralEight { bytes }) => {
            verify_distinct_literal_eight(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralNine { bytes }) => {
            verify_distinct_literal_nine(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralTen { bytes }) => {
            verify_distinct_literal_ten(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralEleven { bytes }) => {
            verify_distinct_literal_eleven(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralTwelve { bytes }) => {
            verify_distinct_literal_twelve(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralThirteen { bytes }) => {
            verify_distinct_literal_thirteen(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralFourteen { bytes }) => {
            verify_distinct_literal_fourteen(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralFifteen { bytes }) => {
            verify_distinct_literal_fifteen(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralSixteen { bytes }) => {
            verify_distinct_literal_sixteen(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralSeventeen { bytes }) => {
            verify_distinct_literal_seventeen(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralEighteen { bytes }) => {
            verify_distinct_literal_eighteen(profile, &artifact, *bytes)?;
        }
        Some(SourceEffectWitness::DistinctLiteralNineteen { bytes }) => {
            verify_distinct_literal_nineteen(profile, &artifact, *bytes)?;
        }
        None => {}
    }
    let publication = if spec.capsule {
        let bytes = build_capsule(profile, &artifact.source)
            .map_err(|error| format!("capsule build rejected: {error}"))?;
        let parsed = parse_capsule(&bytes)
            .map_err(|error| format!("capsule independent parse rejected: {error}"))?
            .ok_or("capsule marker missing after framing")?;
        if parsed.profile() != profile || parsed.payload() != artifact.source {
            return Err(String::from("capsule profile or source payload disagrees"));
        }
        bytes
    } else {
        artifact.source
    };
    publish_new(&spec.output, &publication)?;
    let notice = format!(
        "emitted {} bytes for {} ({} VM steps)\n",
        publication.len(),
        profile.id(),
        artifact.steps,
    );
    drop(io::stderr().lock().write_all(notice.as_bytes()));
    Ok(())
}

/// Executes the closed validated layout CLI and returns a failure exit code
/// without publishing partial target artifacts.
#[must_use]
pub fn run() -> ExitCode {
    match parse_arguments(env::args_os().skip(1)).and_then(|spec| execute(&spec)) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            let notice = format!("malbolge_layout: {error}\n");
            drop(io::stderr().lock().write_all(notice.as_bytes()));
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
#[path = "../../../../tests/compiler/layout/canonical_wire_read.rs"]
mod canonical_wire_read_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/layout/staging_retry.rs"]
mod staging_retry_tests;
