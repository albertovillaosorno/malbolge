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
//   - Explicit normalized Clang JSON-to-verified-Malbolge process handoff.
// - Must-Not:
//   - Claim direct C parsing or skip canonical typed/backend verification.
// - Allows:
//   - Inputs: bounded normalized JSON stdin and an explicit trusted backend.
//   - Outputs: verified graphical `.malbolge` through that backend only.
//   - Side effects: one child process and backend-owned artifact publication.
// - Split-When:
//   - Native C frontend process orchestration gains its own admitted boundary.
// - Merge-When:
//   - The complete C compiler composes the same typed/backend verification.
// - Summary:
//   - Connects Clang JSON through MCTI to the existing real VM publisher.
// - Description:
//   - The backend controls atomic no-clobber publication and final VM replay.
// - Usage:
//   - `c2malbolge_json --layout-backend BIN --output FILE [--capsule]`.
// - Defaults:
//   - No artifact is created when JSON admission or backend execution fails.
//

//! Explicit stdin-normalized C JSON to verified guest artifact composition.

use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::File;
use std::io::{self, Read as _, Write as _};
use std::path::Path;
use std::process::{Command, ExitCode, Stdio};

#[cfg(test)]
use malbolge as _;
use malbolge_c_frontend_json_adapter::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir_with_source,
    first_unlowered_c_node,
};
use serde as _;
use serde_json as _;

const USAGE: &str = concat!(
    "expected --layout-backend BIN --output FILE ",
    "[--source C] [--capsule]",
);
const MAX_JSON_BYTES: u64 = 1_048_576;
const MAX_SOURCE_BYTES: u64 = 64 * 1024 * 1024;

struct Arguments {
    backend: OsString,
    capsule: bool,
    output: OsString,
    source: Option<OsString>,
}

fn parse_args() -> Result<Arguments, &'static str> {
    let args = env::args_os().skip(1).collect::<Vec<_>>();
    let [backend_arg, backend, output_arg, output, rest @ ..] = args.as_slice()
    else {
        return Err(USAGE);
    };
    if backend_arg != OsStr::new("--layout-backend")
        || output_arg != OsStr::new("--output")
    {
        return Err(USAGE);
    }
    let (source, capsule) = match rest {
        [] => (None, false),
        [flag] if flag == OsStr::new("--capsule") => (None, true),
        [flag, name] if flag == OsStr::new("--source") => {
            (Some(name.clone()), false)
        },
        [flag, name, capsule]
            if flag == OsStr::new("--source")
                && capsule == OsStr::new("--capsule") =>
        {
            (Some(name.clone()), true)
        },
        _ => {
            return Err(USAGE);
        },
    };
    Ok(Arguments {
        backend: backend.clone(),
        capsule,
        output: output.clone(),
        source,
    })
}

fn read_source_witness(
    name: Option<&OsString>,
) -> Result<Option<Vec<u8>>, String> {
    let Some(name) = name else {
        return Ok(None);
    };
    let path = Path::new(name);
    let file = File::open(path)
        .map_err(|error| format!("cannot open C source witness: {error}"))?;
    let metadata = file
        .metadata()
        .map_err(|error| format!("cannot inspect C source witness: {error}"))?;
    if !metadata.is_file() || metadata.len() > MAX_SOURCE_BYTES {
        return Err(
            "C source witness must be a regular file of at most 64 MiB"
                .to_owned(),
        );
    }
    let mut bytes = Vec::new();
    let _read = file
        .take(MAX_SOURCE_BYTES + 1)
        .read_to_end(&mut bytes)
        .map_err(|error| format!("cannot read C source witness: {error}"))?;
    if u64::try_from(bytes.len()).unwrap_or(u64::MAX) > MAX_SOURCE_BYTES {
        return Err("C source witness exceeds the 64 MiB bound".to_owned());
    }
    Ok(Some(bytes))
}

fn execute() -> Result<(), String> {
    let Arguments {
        backend,
        capsule,
        output,
        source,
    } = parse_args().map_err(str::to_owned)?;
    let mut input = Vec::new();
    let _read = io::stdin()
        .lock()
        .take(MAX_JSON_BYTES + 1)
        .read_to_end(&mut input)
        .map_err(|error| {
            format!("cannot read normalized JSON stdin: {error}")
        })?;
    let source_witness = read_source_witness(source.as_ref())?;
    let (typed, mode) =
        canonical_guest_typed_ir_with_source(&input, source_witness.as_deref())
            .map_err(|error| {
                if error == FrontendJsonError::Unsupported
                    && let Some(node) = first_unlowered_c_node(&input)
                {
                    return format!(
                        concat!(
                            "normalized frontend rejected: {:?}; ",
                            "unlowered C {} at {}:{} (node {})"
                        ),
                        error, node.kind, node.line, node.column, node.id
                    );
                }
                format!("normalized frontend rejected: {error:?}")
            })?;
    let mut command = Command::new(backend);
    let _arguments = command.args([
        OsStr::new("--profile"),
        OsStr::new("malbolge-2026"),
        OsStr::new("--output"),
        output.as_os_str(),
    ]);
    if capsule {
        let _capsule_argument = command.arg("--capsule");
    }
    let mode_arg = match mode {
        FrontendGuestMode::AdjacentEcho => "",
        FrontendGuestMode::LatestRead => "--latest-byte-trace",
        FrontendGuestMode::EmptyVoid => "--empty-void",
        FrontendGuestMode::InitialZeroOutput => "--initial-zero-output",
        FrontendGuestMode::SeededByteLiteral => "--seeded-byte-literal",
        FrontendGuestMode::ZeroThenLiteral => "--zero-then-literal",
        FrontendGuestMode::DistinctLiteralPair => "--distinct-literal-pair",
        FrontendGuestMode::DistinctLiteralTriple => "--distinct-literal-triple",
        FrontendGuestMode::DistinctLiteralQuad => "--distinct-literal-quad",
        FrontendGuestMode::DistinctLiteralQuint => "--distinct-literal-quint",
        FrontendGuestMode::DistinctLiteralSix => "--distinct-literal-six",
        FrontendGuestMode::DistinctLiteralSeven => "--distinct-literal-seven",
        FrontendGuestMode::DistinctLiteralEight => "--distinct-literal-eight",
        FrontendGuestMode::DistinctLiteralNine => "--distinct-literal-nine",
        FrontendGuestMode::DistinctLiteralTen => "--distinct-literal-ten",
        FrontendGuestMode::DistinctLiteralEleven => "--distinct-literal-eleven",
        FrontendGuestMode::DistinctLiteralTwelve => "--distinct-literal-twelve",
        FrontendGuestMode::DistinctLiteralThirteen => {
            "--distinct-literal-thirteen"
        },
        FrontendGuestMode::DistinctLiteralFourteen => {
            "--distinct-literal-fourteen"
        },
        FrontendGuestMode::DistinctLiteralFifteen => {
            "--distinct-literal-fifteen"
        },
        FrontendGuestMode::DistinctLiteralSixteen => {
            "--distinct-literal-sixteen"
        },
        FrontendGuestMode::DistinctLiteralSeventeen => {
            "--distinct-literal-seventeen"
        },
        FrontendGuestMode::DistinctLiteralEighteen => {
            "--distinct-literal-eighteen"
        },
        FrontendGuestMode::DistinctLiteralNineteen => {
            "--distinct-literal-nineteen"
        },
        FrontendGuestMode::DistinctLiteralTwenty => "--distinct-literal-twenty",
        FrontendGuestMode::DistinctLiteralTwentyOne => {
            "--distinct-literal-twenty-one"
        },
        FrontendGuestMode::DistinctLiteralTwentyTwo => {
            "--distinct-literal-twenty-two"
        },
        FrontendGuestMode::DistinctLiteralTwentyThree => {
            "--distinct-literal-twenty-three"
        },
        FrontendGuestMode::DistinctLiteralTwentyFour => {
            "--distinct-literal-twenty-four"
        },
        FrontendGuestMode::DistinctLiteralTwentyFive => {
            "--distinct-literal-twenty-five"
        },
        FrontendGuestMode::DistinctLiteralTwentySix => {
            "--distinct-literal-twenty-six"
        },
        FrontendGuestMode::DistinctLiteralTwentySeven => {
            "--distinct-literal-twenty-seven"
        },
        FrontendGuestMode::DistinctLiteralTwentyEight => {
            "--distinct-literal-twenty-eight"
        },
        FrontendGuestMode::DistinctLiteralTwentyNine => {
            "--distinct-literal-twenty-nine"
        },
        FrontendGuestMode::DistinctLiteralThirty => "--distinct-literal-thirty",
        FrontendGuestMode::DistinctLiteralThirtyOne => {
            "--distinct-literal-thirty-one"
        },
        FrontendGuestMode::DistinctLiteralThirtyTwo => {
            "--distinct-literal-thirty-two"
        },
        FrontendGuestMode::DistinctLiteralThirtyThree => {
            "--distinct-literal-thirty-three"
        },
        FrontendGuestMode::DistinctLiteralThirtyFour => {
            "--distinct-literal-thirty-four"
        },
        FrontendGuestMode::DistinctLiteralThirtyFive => {
            "--distinct-literal-thirty-five"
        },
        FrontendGuestMode::DistinctLiteralThirtySix => {
            "--distinct-literal-thirty-six"
        },
        FrontendGuestMode::DistinctLiteralThirtySeven => {
            "--distinct-literal-thirty-seven"
        },
        FrontendGuestMode::DistinctLiteralThirtyEight => {
            "--distinct-literal-thirty-eight"
        },
        FrontendGuestMode::DistinctLiteralThirtyNine => {
            "--distinct-literal-thirty-nine"
        },
        FrontendGuestMode::DistinctLiteralForty => "--distinct-literal-forty",
        FrontendGuestMode::DistinctLiteralFortyOne => {
            "--distinct-literal-forty-one"
        },
        FrontendGuestMode::DistinctLiteralFortyTwo => {
            "--distinct-literal-forty-two"
        },
        FrontendGuestMode::DistinctLiteralFortyThree => {
            "--distinct-literal-forty-three"
        },
        FrontendGuestMode::DistinctLiteralFortyFour => {
            "--distinct-literal-forty-four"
        },
        FrontendGuestMode::DistinctLiteralFortyFive => {
            "--distinct-literal-forty-five"
        },
        FrontendGuestMode::DistinctLiteralFortySix => {
            "--distinct-literal-forty-six"
        },
        FrontendGuestMode::DistinctLiteralFortySeven => {
            "--distinct-literal-forty-seven"
        },
        FrontendGuestMode::DistinctLiteralFortyEight => {
            "--distinct-literal-forty-eight"
        },
    };
    let _arguments = command.arg("--");
    if !mode_arg.is_empty() {
        let _mode = command.arg(mode_arg);
    }
    let mut child = command
        .arg("--typed-stdin")
        .stdin(Stdio::piped())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|error| {
            format!("cannot launch selected layout backend: {error}")
        })?;
    let write_result = child
        .stdin
        .take()
        .ok_or("cannot open layout backend stdin")
        .and_then(|mut pipe| {
            pipe.write_all(&typed).map_err(
                |_error| "layout backend rejected canonical typed input",
            )
        });
    let status = child
        .wait()
        .map_err(|error| format!("cannot reap layout backend: {error}"))?;
    write_result.map_err(str::to_owned)?;
    if !status.success() {
        return Err(format!("layout backend exited unsuccessfully: {status}"));
    }
    Ok(())
}

fn main() -> ExitCode {
    match execute() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            let _reported =
                writeln!(io::stderr().lock(), "c2malbolge_json: {error}");
            ExitCode::FAILURE
        },
    }
}
