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
use std::io::{self, Read as _, Write as _};
use std::process::{Command, ExitCode, Stdio};

use malbolge_c_frontend_json_adapter::{FrontendGuestMode, canonical_guest_typed_ir};
use serde as _;
use serde_json as _;

const MAX_JSON_BYTES: u64 = 1_048_576;

struct Arguments {
    backend: OsString,
    capsule: bool,
    output: OsString,
}

fn parse_args() -> Result<Arguments, &'static str> {
    let args = env::args_os().skip(1).collect::<Vec<_>>();
    match args.as_slice() {
        [backend_arg, backend, output_arg, output]
            if backend_arg == OsStr::new("--layout-backend")
                && output_arg == OsStr::new("--output") =>
        {
            Ok(Arguments {
                backend: backend.clone(),
                capsule: false,
                output: output.clone(),
            })
        }
        [backend_arg, backend, output_arg, output, capsule]
            if backend_arg == OsStr::new("--layout-backend")
                && output_arg == OsStr::new("--output")
                && capsule == OsStr::new("--capsule") =>
        {
            Ok(Arguments {
                backend: backend.clone(),
                capsule: true,
                output: output.clone(),
            })
        }
        _ => Err("expected --layout-backend BIN --output FILE [--capsule]"),
    }
}

fn execute() -> Result<(), String> {
    let Arguments {
        backend,
        capsule,
        output,
    } = parse_args().map_err(str::to_owned)?;
    let mut input = Vec::new();
    let _read = io::stdin()
        .lock()
        .take(MAX_JSON_BYTES + 1)
        .read_to_end(&mut input)
        .map_err(|error| format!("cannot read normalized JSON stdin: {error}"))?;
    let (typed, mode) = canonical_guest_typed_ir(&input)
        .map_err(|error| format!("normalized frontend rejected: {error:?}"))?;
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
        FrontendGuestMode::DistinctLiteralThirteen => "--distinct-literal-thirteen",
        FrontendGuestMode::DistinctLiteralFourteen => "--distinct-literal-fourteen",
        FrontendGuestMode::DistinctLiteralFifteen => "--distinct-literal-fifteen",
        FrontendGuestMode::DistinctLiteralSixteen => "--distinct-literal-sixteen",
        FrontendGuestMode::DistinctLiteralSeventeen => "--distinct-literal-seventeen",
        FrontendGuestMode::DistinctLiteralEighteen => "--distinct-literal-eighteen",
        FrontendGuestMode::DistinctLiteralNineteen => "--distinct-literal-nineteen",
        FrontendGuestMode::DistinctLiteralTwenty => "--distinct-literal-twenty",
        FrontendGuestMode::DistinctLiteralTwentyOne => "--distinct-literal-twenty-one",
        FrontendGuestMode::DistinctLiteralTwentyTwo => "--distinct-literal-twenty-two",
        FrontendGuestMode::DistinctLiteralTwentyThree => "--distinct-literal-twenty-three",
    };
    let mut child = command
        .args(["--", mode_arg, "--typed-stdin"])
        .stdin(Stdio::piped())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|error| format!("cannot launch selected layout backend: {error}"))?;
    let write_result = child
        .stdin
        .take()
        .ok_or("cannot open layout backend stdin")
        .and_then(|mut pipe| {
            pipe.write_all(&typed)
                .map_err(|_error| "layout backend rejected canonical typed input")
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
            let _reported = writeln!(io::stderr().lock(), "c2malbolge_json: {error}");
            ExitCode::FAILURE
        }
    }
}
