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
//   - Public CLI source-to-guest execution for witnessed multi-byte C output.
// - Must-Not:
//   - Substitute native C execution, mock the guest, or alter compiler stages.
// - Allows:
//   - Inputs: pinned C frontend and verified compiler tools in this repository.
//   - Outputs: exact profile VM stdout, steps and fail-closed publication.
//   - Side effects: project-local temporary C and capsule fixtures only.
// - Split-When:
//   - The public CLI gains independent compiler-backend configurations.
// - Merge-When:
//   - Another public CLI test covers all these source-to-VM transitions.
// - Summary:
//   - One public compile command preserves nontrivial C output guest effects.
// - Description:
//   - Checks source provenance through the real Clang, compiler, and VM chain.
// - Usage:
//   - cargo test --test cli_compile_guest_sequences
// - Defaults:
//   - Unprovisioned optional developer tools skip execution evidence.

//! Public `malbolge compile` to normative VM evidence for real C byte sequences.

use std::fs::{create_dir_all, read, remove_dir_all, write};
use std::path::{Path, PathBuf};
use std::process::{Command, Output, id};
use std::time::{SystemTime, UNIX_EPOCH};

use malbolge as _;

const ROOT: &str = env!("CARGO_MANIFEST_DIR");

struct FixtureDirectory(PathBuf);

impl FixtureDirectory {
    fn new() -> Result<Self, String> {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|error| format!("test clock unavailable: {error}"))?
            .as_nanos();
        let directory = Path::new(ROOT)
            .join(".temp")
            .join(format!("cli-sequences-{}-{suffix}", id()));
        create_dir_all(&directory)
            .map_err(|error| format!("create temporary fixture directory: {error}"))?;
        Ok(Self(directory))
    }
}

impl Drop for FixtureDirectory {
    fn drop(&mut self) {
        let _removed = remove_dir_all(&self.0);
    }
}

fn pinned_compiler_available() -> bool {
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
    binaries.iter().all(|binary| binary.is_file())
        && root.join(".dependencies/llvm/22.1.8/lib/clang/22").is_dir()
}

fn compile(source: &Path, target: &Path) -> Result<Output, String> {
    Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", ROOT)
        .arg("compile")
        .arg(source)
        .arg("-o")
        .arg(target)
        .output()
        .map_err(|error| format!("launch public compiler: {error}"))
}

fn execute_guest(target: &Path) -> Result<Output, String> {
    Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(target)
        .arg("--report-steps")
        .output()
        .map_err(|error| format!("launch normative Malbolge VM: {error}"))
}

#[test]
fn public_compile_preserves_witnessed_output_sequences() -> Result<(), String> {
    if !pinned_compiler_available() {
        return Ok(());
    }
    let fixtures = FixtureDirectory::new()?;
    let cases = [
        (
            "zero-z",
            "(void)putchar(0); putchar(90);",
            b"\x00Z".as_slice(),
            5usize,
        ),
        (
            "z-percent-h",
            "putchar('Z'); putchar('%'); putchar('H');",
            b"Z%H",
            8,
        ),
        (
            "four-distinct",
            "putchar('T'); putchar('='); putchar('4'); putchar('>');",
            b"T=4>",
            21,
        ),
        ("void-a", "(void) putchar ( 65 );", b"A", 31),
    ];
    for (name, statements, expected, steps) in cases {
        let source = fixtures.0.join(format!("C source {name}.c"));
        let target = fixtures.0.join(format!("compiled guest {name}.malbolge"));
        write(
            &source,
            format!("#include <stdio.h>\nvoid emit(void) {{ {statements} }}\n"),
        )
        .map_err(|error| format!("write {name} source: {error}"))?;

        let compiled = compile(&source, &target)?;
        if !compiled.status.success() || !compiled.stdout.is_empty() || !target.is_file() {
            return Err(format!(
                "public compiler did not publish {name}: {compiled:?}"
            ));
        }
        let guest = execute_guest(&target)?;
        if !guest.status.success()
            || guest.stdout != expected
            || guest.stderr != format!("malbolge-steps-v1:{steps}\n").as_bytes()
        {
            return Err(format!("normative guest disagreed for {name}: {guest:?}"));
        }
    }
    Ok(())
}

#[test]
fn public_compile_refuses_unlowered_expression_and_preserves_guest_output() -> Result<(), String> {
    if !pinned_compiler_available() {
        return Ok(());
    }
    let fixtures = FixtureDirectory::new()?;
    let source = fixtures.0.join("known-good.c");
    let target = fixtures.0.join("protected.malbolge");
    write(
        &source,
        "#include <stdio.h>\nvoid emit(void) { putchar('Q'); putchar('.'); }\n",
    )
    .map_err(|error| format!("write supported C source: {error}"))?;
    let first = compile(&source, &target)?;
    if !first.status.success() {
        return Err(format!("initial public compile failed: {first:?}"));
    }
    let original = read(&target).map_err(|error| format!("read original guest: {error}"))?;
    let repeated = compile(&source, &target)?;
    if repeated.status.success()
        || !String::from_utf8_lossy(&repeated.stderr).contains("no-clobber")
        || read(&target).map_err(|error| format!("reread original guest: {error}"))? != original
    {
        return Err(format!(
            "second compile did not protect output: {repeated:?}"
        ));
    }

    let unsupported = fixtures.0.join("unsupported.c");
    let refused_target = fixtures.0.join("must-not-publish.malbolge");
    write(
        &unsupported,
        "#include <stdio.h>\nvoid emit(void) { putchar('Q' + 0); putchar('.'); }\n",
    )
    .map_err(|error| format!("write unlowered expression: {error}"))?;
    let refusal = compile(&unsupported, &refused_target)?;
    if refusal.status.success() || refused_target.exists() {
        return Err(format!("unlowered C expression published: {refusal:?}"));
    }
    let guest = execute_guest(&target)?;
    if !guest.status.success() || guest.stdout != b"Q." {
        return Err(format!("protected original guest is invalid: {guest:?}"));
    }
    Ok(())
}
