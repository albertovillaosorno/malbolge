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
//   - Public single-command C-to-Malbolge compilation and argument admission.
// - Must-Not:
//   - Replace the pinned frontend or accept compiler output as VM evidence.
// - Allows:
//   - Inputs: one bounded C fixture and provisioned repository compiler tools.
//   - Outputs: independently executed guest bytes and failed-path diagnostics.
//   - Side effects: one cleaned repository-local test directory.
// - Split-When:
//   - Compiler mode gains a separate user-facing toolchain lifecycle.
// - Merge-When:
//   - Another CLI test verifies identical compile and no-clobber behavior.
// - Summary:
//   - The top-level CLI delegates to the verified compiler without substitutions.
// - Description:
//   - Checks strict arguments, one real guest byte, and second-run no-clobber.
// - Usage:
//   - cargo test --test cli_compile
// - Defaults:
//   - Real guest proof is unavailable until pinned tools are provisioned.

//! Public single-command compiler end-to-end and fail-closed argument evidence.

use std::fs::{copy, create_dir_all, read, remove_dir_all, write};
use std::path::{Path, PathBuf};
use std::process::{Command, id};
use std::time::{SystemTime, UNIX_EPOCH};

use malbolge as _;

const ROOT: &str = env!("CARGO_MANIFEST_DIR");
const C_SOURCE: &str = "src/interface/command-line/composition/examples/emit-plus.c";

struct FixtureDirectory {
    path: PathBuf,
}

impl FixtureDirectory {
    fn create() -> Result<Self, String> {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|error| format!("clock unavailable for fixture: {error}"))?
            .as_nanos();
        let path = Path::new(ROOT)
            .join(".temp")
            .join(format!("cli-compile-{}-{suffix}", id()));
        create_dir_all(&path).map_err(|error| format!("create fixture directory: {error}"))?;
        Ok(Self { path })
    }
}

impl Drop for FixtureDirectory {
    fn drop(&mut self) {
        let _removed = remove_dir_all(&self.path);
    }
}

fn run_cli(arguments: &[&str]) -> Result<std::process::Output, String> {
    Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", ROOT)
        .args(arguments)
        .output()
        .map_err(|error| format!("start public CLI: {error}"))
}

fn run_public_compile(source: &Path, target: &Path) -> Result<std::process::Output, String> {
    Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", ROOT)
        .arg("compile")
        .arg(source)
        .arg("-o")
        .arg(target)
        .output()
        .map_err(|error| format!("invoke public C compiler: {error}"))
}

#[cfg(unix)]
#[test]
fn installed_unix_shim_forwards_public_compile_argument_contract() -> Result<(), String> {
    let shim = Path::new(ROOT).join("src/interface/command-line/composition/scripts/malbolge");
    let rejected = Command::new(shim)
        .arg("--repository-tools")
        .arg("compile")
        .output()
        .map_err(|error| format!("start installed repository-tools shim: {error}"))?;
    if rejected.status.success()
        || !rejected.stdout.is_empty()
        || !String::from_utf8_lossy(&rejected.stderr)
            .contains("compile requires input.c -o output.malbolge")
    {
        return Err(format!(
            "installed shim did not delegate compile: {rejected:?}"
        ));
    }
    Ok(())
}

#[test]
fn compiler_arguments_reject_ambiguous_or_unsupported_public_forms() -> Result<(), String> {
    let help = run_cli(&["--help"])?;
    if !help.status.success()
        || !help.stderr.is_empty()
        || !String::from_utf8_lossy(&help.stdout)
            .contains("malbolge compile <input.c> -o <output.malbolge>")
    {
        return Err(format!("public help omitted compiler mode: {help:?}"));
    }
    for (arguments, diagnostic) in [
        (
            vec!["compile"],
            "compile requires input.c -o output.malbolge",
        ),
        (
            vec!["compile", "input.c"],
            "compile requires input.c -o output.malbolge",
        ),
        (
            vec!["compile", "input.c", "-o"],
            "compile requires input.c -o output.malbolge",
        ),
        (
            vec!["compile", "input.c", "--output", "output.malbolge"],
            "compile requires exactly",
        ),
        (
            vec!["compile", "input.c", "-o", "output.malbolge", "extra"],
            "compile requires exactly",
        ),
        (
            vec!["compile", "input.txt", "-o", "output.malbolge"],
            "compile source must have a .c extension",
        ),
        (
            vec!["compile", "input.c", "-o", "output.txt"],
            "compile output must have a .malbolge extension",
        ),
    ] {
        let output = run_cli(&arguments)?;
        if output.status.success()
            || !output.stdout.is_empty()
            || !String::from_utf8_lossy(&output.stderr).contains(diagnostic)
        {
            return Err(format!(
                "compile arguments {:?} did not reject: {output:?}",
                arguments
            ));
        }
    }
    Ok(())
}

#[test]
fn one_command_compiles_a_real_c_byte_and_preserves_existing_output() -> Result<(), String> {
    let root = Path::new(ROOT);
    let suffix = if cfg!(windows) { ".exe" } else { "" };
    let binaries = [
        root.join(".dependencies/compiler-c-frontend/22.1.8/bin")
            .join(format!("malbolge-c-frontend{suffix}")),
        root.join(".cache/rust/target/debug")
            .join(format!("c2malbolge_json{suffix}")),
        root.join(".cache/rust/target/debug")
            .join(format!("malbolge_layout{suffix}")),
    ];
    if !binaries.iter().all(|binary| binary.is_file())
        || !root.join(".dependencies/llvm/22.1.8/lib/clang/22").is_dir()
    {
        return Ok(());
    }
    let fixture = FixtureDirectory::create()?;
    let target = fixture.path.join("output with spaces.malbolge");
    let source = fixture.path.join("source with spaces.c");
    let _copied = copy(root.join(C_SOURCE), &source)
        .map_err(|error| format!("copy real C source fixture: {error}"))?;
    let compiled = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", ROOT)
        .arg("compile")
        .arg(&source)
        .arg("-o")
        .arg(&target)
        .output()
        .map_err(|error| format!("invoke public C compiler: {error}"))?;
    if !compiled.status.success() || !compiled.stdout.is_empty() {
        return Err(format!("public C compiler failed: {compiled:?}"));
    }
    let artifact = read(&target).map_err(|error| format!("read guest artifact: {error}"))?;
    if artifact.len() < 7 {
        return Err(String::from("public compiler did not emit a capsule"));
    }
    let executed = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&target)
        .arg("--report-steps")
        .output()
        .map_err(|error| format!("run resulting Malbolge capsule: {error}"))?;
    if !executed.status.success()
        || executed.stdout != b"+"
        || !executed.stderr.starts_with(b"malbolge-steps-v1:")
    {
        return Err(format!(
            "normative VM disagrees with C byte output: {executed:?}"
        ));
    }
    let repeated = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", ROOT)
        .arg("compile")
        .arg(source)
        .arg("-o")
        .arg(&target)
        .output()
        .map_err(|error| format!("repeat public C compiler: {error}"))?;
    if repeated.status.success()
        || !String::from_utf8_lossy(&repeated.stderr).contains("no-clobber")
        || read(&target).map_err(|error| format!("reread guest artifact: {error}"))? != artifact
    {
        return Err(format!(
            "repeated compile did not preserve artifact: {repeated:?}"
        ));
    }
    let malformed = fixture.path.join("malformed.c");
    let rejected_target = fixture.path.join("must-not-exist.malbolge");
    write(&malformed, b"void broken( {\n")
        .map_err(|error| format!("write invalid C fixture: {error}"))?;
    let rejected = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", ROOT)
        .arg("compile")
        .arg(&malformed)
        .arg("-o")
        .arg(&rejected_target)
        .output()
        .map_err(|error| format!("compile invalid C: {error}"))?;
    if rejected.status.success() || rejected_target.exists() {
        return Err(format!("invalid C published output: {rejected:?}"));
    }
    Ok(())
}

#[test]
fn public_compile_executes_guest_crazy_literals_and_refuses_repeats() -> Result<(), String> {
    let root = Path::new(ROOT);
    let suffix = if cfg!(windows) { ".exe" } else { "" };
    if ![
        root.join(".dependencies/compiler-c-frontend/22.1.8/bin")
            .join(format!("malbolge-c-frontend{suffix}")),
        root.join(".cache/rust/target/debug")
            .join(format!("c2malbolge_json{suffix}")),
        root.join(".cache/rust/target/debug")
            .join(format!("malbolge_layout{suffix}")),
    ]
    .iter()
    .all(|binary| binary.is_file())
        || !root.join(".dependencies/llvm/22.1.8/lib/clang/22").is_dir()
    {
        return Ok(());
    }

    let fixture = FixtureDirectory::create()?;
    for (label, byte, steps) in [("S", b'S', 4usize), ("question", b'?', 51)] {
        let source = fixture.path.join(format!("single-{label}.c"));
        let target = fixture.path.join(format!("single-{label}.malbolge"));
        let call = format!(
            "#include <stdio.h>\nvoid emit(void) {{ putchar('{}'); }}\n",
            char::from(byte)
        );
        write(&source, call).map_err(|error| format!("write verified {label} C: {error}"))?;
        let compiled = run_public_compile(&source, &target)?;
        if !compiled.status.success() || !compiled.stdout.is_empty() || !target.is_file() {
            return Err(format!("public {label} compiler failed: {compiled:?}"));
        }
        let executed = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .arg(&target)
            .arg("--report-steps")
            .output()
            .map_err(|error| format!("execute {label} Malbolge guest: {error}"))?;
        if !executed.status.success()
            || executed.stdout != [byte]
            || executed.stderr != format!("malbolge-steps-v1:{steps}\n").as_bytes()
        {
            return Err(format!("{label} guest output/steps diverged: {executed:?}"));
        }

        let unsupported = fixture.path.join(format!("unsupported-double-{label}.c"));
        let rejected_target = fixture
            .path
            .join(format!("must-not-publish-{label}.malbolge"));
        let repeated = format!(
            "#include <stdio.h>\nvoid emit(void) {{ putchar('{0}'); putchar('{0}'); }}\n",
            char::from(byte)
        );
        write(&unsupported, repeated)
            .map_err(|error| format!("write unwitnessed two-{label}: {error}"))?;
        let rejected = run_public_compile(&unsupported, &rejected_target)?;
        if rejected.status.success() || rejected_target.exists() {
            return Err(format!(
                "unwitnessed two-{label} guest published: {rejected:?}"
            ));
        }
    }
    Ok(())
}
