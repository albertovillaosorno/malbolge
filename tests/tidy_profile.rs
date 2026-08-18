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
//   - Rust integration evidence for the optional native clang-tidy profile.
// - Must-Not:
//   - Build LLVM, choose guest-C inputs, or replace the user-facing validator.
// - Allows:
//   - Inputs: canonical local plugin outputs and tracked C fixture corpora.
//   - Outputs: exact registration and accept/reject assertions.
//   - Side effects: child clang-tidy processes only when outputs are present.
// - Split-When:
//   - Split when another native-analysis platform needs independent fixtures.
// - Merge-When:
//   - Merge when another Rust test owns the exact plugin profile regression.
// - Summary:
//   - Regress the real clang-tidy plugin from Rust when locally available.
// - Description:
//   - Locks reviewed checks and fixture behavior without making native LLVM
//     provisioning mandatory for ordinary Rust test environments.
// - Usage:
//   - Collected by Cargo; returns early when optional plugin outputs are
//     absent.
// - Defaults:
//   - Missing optional native outputs do not substitute an ambient clang-tidy.
//

//! Optional live regression coverage for the pinned Malbolge clang-tidy plugin.

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use malbolge as _;

const LLVM_VERSION: &str = "22.1.8";
const CHECKS: [&str; 5] = [
    "malbolge-abi-bit-field",
    "malbolge-abi-over-alignment",
    "malbolge-abi-packed-layout",
    "malbolge-abi-pragma-pack",
    "malbolge-abi-type-surface",
];

struct NativeOutputs {
    host: PathBuf,
    plugin: PathBuf,
    resource: PathBuf,
}

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn native_outputs(root: &Path) -> Option<NativeOutputs> {
    let llvm = root.join(".dependencies").join("llvm").join(LLVM_VERSION);
    let output = root
        .join(".dependencies")
        .join("tools-tidy")
        .join(LLVM_VERSION);
    let (host, plugin) = if cfg!(windows) {
        (
            output.join("bin").join("malbolge-clang-tidy.exe"),
            output.join("bin").join("malbolge-tidy.dll"),
        )
    } else if cfg!(target_os = "linux") {
        (
            llvm.join("jig-bin").join("clang-tidy.bin"),
            output.join("bin").join("malbolge-tidy.so"),
        )
    } else {
        return None;
    };
    let resource = llvm.join("lib").join("clang").join("22");
    if host.is_file() && plugin.is_file() && resource.is_dir() {
        Some(NativeOutputs { host, plugin, resource })
    } else {
        None
    }
}

fn run_plugin(
    root: &Path,
    native: &NativeOutputs,
    source: &Path,
) -> Option<Output> {
    Command::new(&native.host)
        .current_dir(root)
        .arg(format!("--load={}", native.plugin.display()))
        .arg("--checks=-*,malbolge-*")
        .arg("--warnings-as-errors=malbolge-*")
        .arg(source)
        .arg("--")
        .arg(format!("-resource-dir={}", native.resource.display()))
        .args([
            "-x",
            "c",
            "--target=wasm32-unknown-unknown",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            "-pedantic-errors",
        ])
        .output()
        .ok()
}

fn diagnostic_text(output: &Output) -> String {
    let mut text = String::from_utf8_lossy(&output.stdout).into_owned();
    text.push_str(&String::from_utf8_lossy(&output.stderr));
    text
}

#[test]
fn native_plugin_registers_exact_reviewed_checks() {
    let root = repository_root();
    let Some(native) = native_outputs(&root) else {
        return;
    };
    let launch = Command::new(&native.host)
        .current_dir(&root)
        .arg(format!("--load={}", native.plugin.display()))
        .arg("--checks=-*,malbolge-*")
        .arg("--list-checks")
        .output()
        .ok();
    assert!(
        launch.is_some(),
        "canonical clang-tidy plugin host must launch"
    );
    let Some(execution) = launch else {
        return;
    };
    assert!(
        execution.status.success(),
        "{}",
        diagnostic_text(&execution)
    );

    let observed = String::from_utf8_lossy(&execution.stdout)
        .lines()
        .map(str::trim)
        .filter(|line| line.starts_with("malbolge-"))
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    let expected = CHECKS
        .into_iter()
        .map(str::to_owned)
        .collect::<BTreeSet<_>>();
    assert_eq!(observed, expected);
}

#[test]
fn native_plugin_accepts_reviewed_positive_fixtures() {
    let root = repository_root();
    let Some(native) = native_outputs(&root) else {
        return;
    };
    for fixture in ["abi_layout.c", "abi_language_surface.c"] {
        let source = root
            .join("tests")
            .join("tidy")
            .join("accepted")
            .join(fixture);
        let launch = run_plugin(&root, &native, &source);
        assert!(
            launch.is_some(),
            "canonical clang-tidy plugin host must launch"
        );
        let Some(execution) = launch else {
            return;
        };
        assert!(
            execution.status.success(),
            "{}",
            diagnostic_text(&execution)
        );
    }
}

#[test]
fn native_plugin_rejects_reviewed_abi_exclusions() {
    let root = repository_root();
    let Some(native) = native_outputs(&root) else {
        return;
    };
    let rejected = [
        ("rejected/abi_bit_field.c", "MALBOLGE-ABI-001"),
        ("rejected/abi_packed_attribute.c", "MALBOLGE-ABI-002"),
        ("rejected/abi_packed_field.c", "MALBOLGE-ABI-002"),
        ("rejected/abi_pragma_pack.c", "MALBOLGE-ABI-003"),
        ("rejected/abi_extended_alignment.c", "MALBOLGE-ABI-004"),
        ("rejected/abi_bit_int.c", "MALBOLGE-ABI-005"),
        ("rejected/abi_int128_extension.c", "MALBOLGE-ABI-006"),
        ("rejected/abi_vector_extension.c", "MALBOLGE-ABI-007"),
        ("rejected/abi_address_space.c", "MALBOLGE-ABI-008"),
        (
            "plugin-rejected/abi_imported_forbidden_alias.c",
            "MALBOLGE-ABI-006",
        ),
    ];
    for (fixture, expected_code) in rejected {
        let source = root.join("tests").join("tidy").join(fixture);
        let launch = run_plugin(&root, &native, &source);
        assert!(
            launch.is_some(),
            "canonical clang-tidy plugin host must launch"
        );
        let Some(execution) = launch else {
            return;
        };
        let diagnostics = diagnostic_text(&execution);
        assert!(!execution.status.success(), "{fixture} unexpectedly passed");
        assert!(
            diagnostics.contains(expected_code),
            "{fixture} did not emit {expected_code}: {diagnostics}"
        );
    }
}
