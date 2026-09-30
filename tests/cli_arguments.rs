// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE-APACHE-2.0
//
// Boundary-Contract:
// - Owns:
//   - End-to-end argument-policy evidence for the top-level CLI.
// - Must-Not:
//   - Compile or execute guest programs.
// - Allows:
//   - Inputs: command arguments and repository-local progress fixtures.
//   - Outputs: exact status, diagnostics, and checkpoint bytes.
//   - Side effects: child processes plus cleaned repository temp fixtures.
// - Split-When:
//   - Split when another argument family gains independent policy.
// - Merge-When:
//   - Merge when the CLI composition owns direct parser unit tests.
// - Summary:
//   - Fail-closed help and missing-source argument evidence.
// - Description:
//   - Proves help cannot mask malformed input and missing source is diagnostic.
// - Usage:
//   - Collected by the repository Cargo test suite.
// - Defaults:
//   - Standalone help succeeds; missing or combined arguments fail.
//

//! End-to-end top-level CLI argument-policy evidence.

use std::fs::{create_dir_all, remove_dir_all};
use std::path::{Path, PathBuf};
use std::process::{Command, id};

use malbolge as _;

const PORTABLE_CODEC: &str = "search.evaluated-prefix-v1";
const PORTABLE_FIXTURE_SCRIPT: &str = r#"
from hashlib import sha256
from pathlib import Path
import sys

sys.path.insert(0, sys.argv[1])
from scripts import progress_sidecar as progress

directory = Path(sys.argv[2])
terminal = sys.argv[3] == "completed"
output = directory / "program.malbolge"
source_hash = "sha256:" + ("1" * 64)
toolchain_hash = "sha256:" + ("2" * 64)
profile_hash = "malbolge-profile-v1:sha256:" + ("3" * 64)
revision = "a" * 40
identity = progress.ResumeIdentity(
    algorithm_id="search.enumerative",
    algorithm_version="1",
    repository_revision=revision,
    schema=progress.SCHEMA_ID,
    seed=7,
    source_sha256=source_hash,
    target_profile_fingerprint=profile_hash,
    target_profile_id="malbolge-2026",
    toolchain_fingerprint=toolchain_hash,
)
position = progress.PortableCheckpointPosition(
    checkpoint_sequence=1,
    stage="candidate-search",
    units_completed=14,
)
payload = bytes.fromhex(
    "70726f647563742d636c692d737461746500ff"
)
codec = "search.evaluated-prefix-v1"
checkpoint = progress.encode_portable_checkpoint(
    identity,
    position,
    codec,
    payload=payload,
)
sidecar = progress.ProgressSidecar(
    active_elapsed_ns=700,
    algorithm_id="search.enumerative",
    algorithm_version="1",
    backend="cpu",
    checkpoint_elapsed_ns=30,
    checkpoint_path=str(progress.checkpoint_path(output, 1)),
    checkpoint_sequence=1,
    checkpoint_sha256="sha256:" + sha256(checkpoint).hexdigest(),
    compatibility_fingerprint=(
        progress.resume_compatibility_fingerprint(identity)
    ),
    completed_at="2026-08-06T14:00:03Z" if terminal else None,
    device=None,
    diagnostic_code=None,
    diagnostic_message=None,
    operation_id="compile-cli-extract",
    output_path=str(output),
    partial_bytes=None,
    partial_path=None,
    partial_sha256=None,
    paused_elapsed_ns=100,
    progress_path=str(progress.progress_path(output)),
    repository_revision=revision,
    schema=progress.SCHEMA_ID,
    seed=7,
    serialization_elapsed_ns=10,
    source_path="input.c",
    source_sha256=source_hash,
    stage="candidate-search",
    started_at="2026-08-06T14:00:00Z",
    status=(
        progress.ProgressStatus.COMPLETED
        if terminal
        else progress.ProgressStatus.CHECKPOINTED
    ),
    target_profile_fingerprint=profile_hash,
    target_profile_id="malbolge-2026",
    toolchain_fingerprint=toolchain_hash,
    units_completed=14,
    units_total=None,
    updated_at=(
        "2026-08-06T14:00:03Z"
        if terminal
        else "2026-08-06T14:00:02Z"
    ),
    verification_elapsed_ns=30,
    wall_elapsed_ns=870,
)
progress.write_checkpoint_generation(sidecar, checkpoint)
"#;

fn repository_python(root: &Path) -> PathBuf {
    if cfg!(windows) {
        root.join(".dependencies/python/3.14.6/python.exe")
    } else {
        root.join(".dependencies/python/3.14.6/bin/python")
    }
}

fn publish_portable_fixture(
    root: &Path,
    directory: &Path,
    terminal: bool,
) -> Result<PathBuf, String> {
    if directory.exists() {
        remove_dir_all(directory).map_err(|error| {
            format!("remove stale progress fixture: {error}")
        })?;
    }
    create_dir_all(directory)
        .map_err(|error| format!("create progress fixture: {error}"))?;
    let module_root = root.join("src/automation/repository/composition");
    let output = Command::new(repository_python(root))
        .arg("-B")
        .arg("-c")
        .arg(PORTABLE_FIXTURE_SCRIPT)
        .arg(module_root)
        .arg(directory)
        .arg(if terminal {
            "completed"
        } else {
            "checkpointed"
        })
        .output()
        .map_err(|error| format!("publish progress fixture: {error}"))?;
    if !output.status.success() {
        let _cleanup = remove_dir_all(directory);
        return Err(format!(
            "progress fixture publication failed: {}",
            String::from_utf8_lossy(&output.stderr),
        ));
    }
    Ok(directory.join("program.malbolge.progress.json"))
}

#[test]
fn help_is_accepted_only_as_the_sole_argument() -> Result<(), String> {
    for help in ["--help", "-h"] {
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .arg(help)
            .output()
            .map_err(|error| format!("run standalone help: {error}"))?;
        if !output.status.success()
            || !String::from_utf8_lossy(&output.stdout)
                .contains("Usage: malbolge <program.malbolge>")
            || !String::from_utf8_lossy(&output.stdout)
                .contains("malbolge <program.c> [program args...]")
            || !String::from_utf8_lossy(&output.stdout)
                .contains("malbolge --checkpoint-info")
            || !String::from_utf8_lossy(&output.stdout)
                .contains("malbolge --extract-checkpoint")
            || !String::from_utf8_lossy(&output.stdout)
                .contains("malbolge --follow-progress")
            || !output.stderr.is_empty()
        {
            return Err(format!(
                concat!(
                    "standalone help failed: {}: status={} ",
                    "stdout={} stderr={}",
                ),
                help,
                output.status,
                String::from_utf8_lossy(&output.stdout),
                String::from_utf8_lossy(&output.stderr),
            ));
        }
    }
    for arguments in [["--help", "unexpected"], ["-h", "source.c"]] {
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .args(arguments)
            .output()
            .map_err(|error| format!("run combined help: {error}"))?;
        let stderr = String::from_utf8_lossy(&output.stderr);
        if output.status.success()
            || !output.stdout.is_empty()
            || !stderr.contains("--help cannot be combined")
        {
            return Err(format!(
                concat!(
                    "combined help did not fail closed: {:?}: ",
                    "status={} stdout={} stderr={}",
                ),
                arguments,
                output.status,
                String::from_utf8_lossy(&output.stdout),
                stderr,
            ));
        }
    }
    Ok(())
}

#[test]
fn missing_source_is_a_diagnostic_not_help() -> Result<(), String> {
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .output()
        .map_err(|error| format!("run CLI without arguments: {error}"))?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if !output.status.success()
        && output.stdout.is_empty()
        && stderr.contains("expected source path; use --help for usage")
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "missing-source policy mismatch: status={} ",
                "stdout={} stderr={}",
            ),
            output.status,
            String::from_utf8_lossy(&output.stdout),
            stderr,
        ))
    }
}

#[test]
fn checkpoint_info_requires_exactly_one_progress_path() -> Result<(), String> {
    for arguments in [vec!["--checkpoint-info"], vec![
        "--checkpoint-info",
        "first.progress.json",
        "second.progress.json",
    ]] {
        let output =
            Command::new(env!("CARGO_BIN_EXE_malbolge"))
                .args(&arguments)
                .output()
                .map_err(|error| {
                    format!(
                        "run checkpoint-info arity case {arguments:?}: {error}",
                    )
                })?;
        let stderr = String::from_utf8_lossy(&output.stderr);
        if output.status.success()
            || !output.stdout.is_empty()
            || !stderr.contains(
                "--checkpoint-info requires exactly one progress sidecar path",
            )
        {
            return Err(format!(
                concat!(
                    "checkpoint-info arity did not fail closed: {:?}: ",
                    "status={} stdout={} stderr={}",
                ),
                arguments,
                output.status,
                String::from_utf8_lossy(&output.stdout),
                stderr,
            ));
        }
    }
    Ok(())
}

#[test]
fn checkpoint_info_delegates_validation_to_trusted_inspector()
-> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let missing = root.join(".temp").join(format!(
        "missing-cli-progress-{}.malbolge.progress.json",
        id(),
    ));
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", root)
        .arg("--checkpoint-info")
        .arg(&missing)
        .output()
        .map_err(|error| {
            format!("run checkpoint-info inspector case: {error}")
        })?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if !output.status.success()
        && output.stdout.is_empty()
        && stderr.contains("portable checkpoint inspection failed:")
        && stderr.contains("progress sidecar is unavailable")
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "checkpoint-info did not delegate to inspector: status={} ",
                "stdout={} stderr={}",
            ),
            output.status,
            String::from_utf8_lossy(&output.stdout),
            stderr,
        ))
    }
}

#[test]
fn follow_progress_requires_exactly_one_progress_path() -> Result<(), String> {
    for arguments in [vec!["--follow-progress"], vec![
        "--follow-progress",
        "first.progress.json",
        "second.progress.json",
    ]] {
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .args(&arguments)
            .output()
            .map_err(|error| {
                format!("run follow-progress arity case {arguments:?}: {error}")
            })?;
        let stderr = String::from_utf8_lossy(&output.stderr);
        if output.status.success()
            || !output.stdout.is_empty()
            || !stderr.contains(
                "--follow-progress requires exactly one progress sidecar path",
            )
        {
            return Err(format!(
                concat!(
                    "follow-progress arity did not fail closed: {:?}: ",
                    "status={} stdout={} stderr={}",
                ),
                arguments,
                output.status,
                String::from_utf8_lossy(&output.stdout),
                stderr,
            ));
        }
    }
    Ok(())
}

#[test]
fn follow_progress_delegates_validation_to_trusted_inspector()
-> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let missing = root.join(".temp").join(format!(
        "missing-cli-follow-{}.malbolge.progress.json",
        id(),
    ));
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", root)
        .arg("--follow-progress")
        .arg(&missing)
        .output()
        .map_err(|error| {
            format!("run follow-progress inspector case: {error}")
        })?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if !output.status.success()
        && output.stdout.is_empty()
        && stderr.contains("progress sidecar follow failed:")
        && stderr.contains("progress sidecar is unavailable")
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "follow-progress did not delegate to inspector: status={} ",
                "stdout={} stderr={}",
            ),
            output.status,
            String::from_utf8_lossy(&output.stdout),
            stderr,
        ))
    }
}

#[test]
fn follow_progress_streams_terminal_summary_once() -> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let directory = root
        .join(".temp")
        .join(format!("cli-follow-fixture-{}", id()));
    let progress_path = publish_portable_fixture(root, &directory, true)?;
    let output_result = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", root)
        .arg("--follow-progress")
        .arg(&progress_path)
        .output()
        .map_err(|error| format!("run terminal progress follow: {error}"));
    let cleanup = remove_dir_all(&directory)
        .map_err(|error| format!("remove progress fixture: {error}"));
    let output = output_result?;
    cleanup?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    if output.status.success()
        && output.stderr.is_empty()
        && stdout.lines().count() == 1
        && stdout.contains("status=completed")
        && !stdout.contains("checkpoint_sequence")
    {
        Ok(())
    } else {
        Err(format!(
            concat!("terminal follow mismatch: status={} stdout={} stderr={}",),
            output.status,
            stdout,
            String::from_utf8_lossy(&output.stderr),
        ))
    }
}

#[test]
fn extract_checkpoint_requires_codec_and_progress_path() -> Result<(), String> {
    let cases = [
        vec!["--extract-checkpoint"],
        vec!["--extract-checkpoint", "search.state-v1"],
        vec![
            "--extract-checkpoint",
            "search.state-v1",
            "state.progress.json",
            "unexpected",
        ],
    ];
    for arguments in cases {
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .args(&arguments)
            .output()
            .map_err(|error| {
                format!(
                    "run extract-checkpoint arity case {arguments:?}: {error}",
                )
            })?;
        let stderr = String::from_utf8_lossy(&output.stderr);
        if output.status.success()
            || !output.stdout.is_empty()
            || !stderr.contains(
                "--extract-checkpoint requires a state codec and progress path",
            )
        {
            return Err(format!(
                concat!(
                    "extract-checkpoint arity did not fail closed: {:?}: ",
                    "status={} stdout={} stderr={}",
                ),
                arguments,
                output.status,
                String::from_utf8_lossy(&output.stdout),
                stderr,
            ));
        }
    }
    Ok(())
}

#[test]
fn extract_checkpoint_delegates_validation_to_trusted_inspector()
-> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let missing = root.join(".temp").join(format!(
        "missing-cli-extract-{}.malbolge.progress.json",
        id(),
    ));
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", root)
        .arg("--extract-checkpoint")
        .arg("search.evaluated-prefix-v1")
        .arg(&missing)
        .output()
        .map_err(|error| {
            format!("run extract-checkpoint inspector case: {error}")
        })?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if !output.status.success()
        && output.stdout.is_empty()
        && stderr.contains("portable checkpoint extraction failed:")
        && stderr.contains("progress sidecar is unavailable")
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "extract-checkpoint did not delegate to inspector: status={} ",
                "stdout={} stderr={}",
            ),
            output.status,
            String::from_utf8_lossy(&output.stdout),
            stderr,
        ))
    }
}

#[test]
fn extract_checkpoint_preserves_verified_binary_state() -> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let directory = root
        .join(".temp")
        .join(format!("cli-extract-fixture-{}", id()));
    let progress_path = publish_portable_fixture(root, &directory, false)?;
    let output_result = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env("MALBOLGE_ROOT", root)
        .arg("--extract-checkpoint")
        .arg(PORTABLE_CODEC)
        .arg(&progress_path)
        .output()
        .map_err(|error| format!("run binary checkpoint extraction: {error}"));
    let cleanup = remove_dir_all(&directory)
        .map_err(|error| format!("remove progress fixture: {error}"));
    let output = output_result?;
    cleanup?;
    let mut expected = b"product-cli-state".to_vec();
    expected.extend_from_slice(&[0, 255]);
    if output.status.success()
        && output.stdout == expected
        && output.stderr.is_empty()
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "binary extraction mismatch: status={} stdout={:?} ",
                "stderr={}",
            ),
            output.status,
            output.stdout,
            String::from_utf8_lossy(&output.stderr),
        ))
    }
}
