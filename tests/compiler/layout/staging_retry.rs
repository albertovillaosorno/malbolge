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
//   - Crash-stale stage collision and no-clobber publisher regressions.
// - Must-Not:
//   - Delete or modify another invocation's pre-existing stage or final output.
// - Allows:
//   - Inputs: owned stale staging files and literal publication bytes.
//   - Outputs: exact isolated new-file publication or explicit error.
//   - Side effects: isolated ignored fixture directories under `.temp`.
// - Split-When:
//   - Platform-specific atomic publication needs a separate adapter.
// - Merge-When:
//   - Generic artifact output publication subsumes the layout publisher.
// - Summary:
//   - Proves stale process-ID stages do not prevent fresh complete output.
// - Description:
//   - Injects one or two occupied staging names and an occupied destination.
// - Usage:
//   - `cargo test --bin malbolge_layout staging_retry_tests`.
// - Defaults:
//   - Never mutate an occupied artifact or abandoned stage.
//

//! Crash-stale temporary-name collision regression coverage.

use super::{
    MAX_STAGE_NAME_ATTEMPTS, publish_new, publish_new_with_hooks,
    publish_new_with_stage_hook,
};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::process::id;
use std::sync::atomic::{AtomicUsize, Ordering};

static SEQUENCE: AtomicUsize = AtomicUsize::new(0);

struct Fixture(PathBuf);

impl Fixture {
    fn new() -> io::Result<Self> {
        let sequence = SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("layout-stale-stage-{}-{sequence}", id()));
        #[expect(clippy::create_dir, reason = "never reuse a fixture directory")]
        fs::create_dir(&root)?;
        Ok(Self(root))
    }

    fn output(&self) -> PathBuf {
        self.0.join("artifact.malbolge")
    }
}

#[expect(
    clippy::missing_trait_methods,
    reason = "fixture Drop cleans owned files"
)]
impl Drop for Fixture {
    fn drop(&mut self) {
        drop(fs::remove_dir_all(&self.0));
    }
}

fn stage(output: &Path, sequence: Option<usize>) -> PathBuf {
    let basename = format!(".artifact.malbolge.stage-{}", id());
    match sequence {
        None => output.with_file_name(basename),
        Some(number) => output.with_file_name(format!("{basename}-{number}")),
    }
}

#[cfg(unix)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "valid long output filenames must publish"
)]
fn long_valid_output_names_have_bounded_unique_stage_names() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let common = "x".repeat(235);
    let first = fixture.0.join(format!("{common}a.malbolge"));
    let second = fixture.0.join(format!("{common}b.malbolge"));
    // The target filename itself must be valid on this filesystem; only the
    // staging suffix would cross the per-component filename limit.
    fs::write(&first, b"probe").map_err(|error| error.to_string())?;
    fs::remove_file(&first).map_err(|error| error.to_string())?;
    publish_new(&first, b"ctO")?;
    publish_new(&second, b"qPh")?;
    assert_eq!(fs::read(&first).map_err(|error| error.to_string())?, b"ctO");
    assert_eq!(
        fs::read(&second).map_err(|error| error.to_string())?,
        b"qPh"
    );
    assert_eq!(
        fs::read_dir(&fixture.0)
            .map_err(|error| error.to_string())?
            .count(),
        2,
        "only final targets, not temporary stages, may survive"
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "preserve occupied compact staging name"
)]
fn long_output_retries_occupied_compact_stage_without_overwriting() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let name = format!("{}.malbolge", "m".repeat(236));
    let output = fixture.0.join(&name);
    let basename = super::fresh_stage_basename(&name);
    assert!(basename.starts_with(".layout-"));
    assert!(basename.len() <= super::MAX_STAGE_BASENAME_BYTES);
    let stale = output.with_file_name(&basename);
    fs::write(&stale, b"existing-stale-bytes").map_err(|error| error.to_string())?;
    publish_new(&output, b"ctO")?;
    assert_eq!(
        fs::read(&output).map_err(|error| error.to_string())?,
        b"ctO"
    );
    assert_eq!(
        fs::read(&stale).map_err(|error| error.to_string())?,
        b"existing-stale-bytes"
    );
    assert!(!output.with_file_name(format!("{basename}-1")).exists());
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert exact publication bytes")]
fn stale_process_id_stage_is_preserved_during_successful_retry() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    let stale = stage(&output, None);
    fs::write(&stale, b"abandoned").map_err(|error| error.to_string())?;
    publish_new(&output, b"ctO")?;
    assert_eq!(
        fs::read(&output).map_err(|error| error.to_string())?,
        b"ctO"
    );
    assert_eq!(
        fs::read(&stale).map_err(|error| error.to_string())?,
        b"abandoned"
    );
    assert!(!stage(&output, Some(1)).exists());
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert exact publication bytes")]
fn multiple_stale_stages_preserve_every_occupied_path() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    let first = stage(&output, None);
    let second = stage(&output, Some(1));
    fs::write(&first, b"first").map_err(|error| error.to_string())?;
    fs::write(&second, b"second").map_err(|error| error.to_string())?;
    publish_new(&output, b"ctO")?;
    assert_eq!(
        fs::read(&output).map_err(|error| error.to_string())?,
        b"ctO"
    );
    assert_eq!(
        fs::read(&first).map_err(|error| error.to_string())?,
        b"first"
    );
    assert_eq!(
        fs::read(&second).map_err(|error| error.to_string())?,
        b"second"
    );
    assert!(!stage(&output, Some(2)).exists());
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "existing output must never be replaced"
)]
fn stale_stage_fallback_cannot_clobber_existing_final_output() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    let stale = stage(&output, None);
    fs::write(&stale, b"abandoned").map_err(|error| error.to_string())?;
    fs::write(&output, b"original").map_err(|error| error.to_string())?;
    assert!(publish_new(&output, b"ctO").is_err());
    assert_eq!(
        fs::read(&output).map_err(|error| error.to_string())?,
        b"original"
    );
    assert_eq!(
        fs::read(&stale).map_err(|error| error.to_string())?,
        b"abandoned"
    );
    assert!(!stage(&output, Some(1)).exists());
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assert bounded fail-closed retry"
)]
fn bounded_retry_exhaustion_preserves_all_occupied_stages() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    for attempt in 0..MAX_STAGE_NAME_ATTEMPTS {
        let marker = u8::try_from(attempt).map_err(|error| error.to_string())?;
        let occupied = stage(&output, (attempt != 0).then_some(attempt));
        fs::write(&occupied, [marker]).map_err(|error| error.to_string())?;
    }
    let result = publish_new(&output, b"ctO");
    assert!(
        result
            .as_ref()
            .is_err_and(|error| error.contains("staging names occupied")),
        "exhausted staging paths were admitted: {result:?}"
    );
    assert!(!output.exists());
    for attempt in 0..MAX_STAGE_NAME_ATTEMPTS {
        let marker = u8::try_from(attempt).map_err(|error| error.to_string())?;
        let occupied = stage(&output, (attempt != 0).then_some(attempt));
        assert_eq!(
            fs::read(&occupied).map_err(|error| error.to_string())?,
            [marker]
        );
    }
    assert!(!stage(&output, Some(MAX_STAGE_NAME_ATTEMPTS)).exists());
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "stale symlink must be preserved")]
fn stale_symlink_stage_is_not_followed() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    let sensitive = output.with_file_name("sensitive.txt");
    let stale = stage(&output, None);
    fs::write(&sensitive, b"unchanged").map_err(|error| error.to_string())?;
    std::os::unix::fs::symlink(&sensitive, &stale).map_err(|error| error.to_string())?;
    publish_new(&output, b"ctO")?;
    assert_eq!(
        fs::read(&output).map_err(|error| error.to_string())?,
        b"ctO"
    );
    assert_eq!(
        fs::read(&sensitive).map_err(|error| error.to_string())?,
        b"unchanged"
    );
    assert!(
        fs::symlink_metadata(&stale)
            .map_err(|error| error.to_string())?
            .file_type()
            .is_symlink()
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert stage identity gate")]
fn replaced_equal_byte_stage_is_rejected_and_preserved() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    let foreign = output.with_file_name("replacement-stage");
    fs::write(&foreign, b"ctO").map_err(|error| error.to_string())?;
    let result = publish_new_with_stage_hook(&output, b"ctO", |staged| {
        fs::remove_file(staged).map_err(|error| error.to_string())?;
        fs::rename(&foreign, staged).map_err(|error| error.to_string())
    });
    assert!(result.is_err(), "foreign inode was published: {result:?}");
    assert!(!output.exists());
    assert_eq!(
        fs::read(stage(&output, None)).map_err(|error| error.to_string())?,
        b"ctO"
    );
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert stage identity gate")]
fn substituted_stage_symlink_is_rejected_and_preserved() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    let foreign = output.with_file_name("foreign-input");
    fs::write(&foreign, b"ctO").map_err(|error| error.to_string())?;
    let result = publish_new_with_stage_hook(&output, b"ctO", |staged| {
        fs::remove_file(staged).map_err(|error| error.to_string())?;
        std::os::unix::fs::symlink(&foreign, staged).map_err(|error| error.to_string())
    });
    assert!(result.is_err(), "foreign symlink was published: {result:?}");
    assert!(!output.exists());
    assert_eq!(
        fs::read(&foreign).map_err(|error| error.to_string())?,
        b"ctO"
    );
    assert!(stage(&output, None).is_symlink());
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "reject foreign stage aliases")]
fn linked_stage_is_rejected_before_publication() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    let alias = fixture.0.join("foreign-stage-link");
    let result = publish_new_with_stage_hook(&output, b"ctO", |staged| {
        fs::hard_link(staged, &alias).map_err(|error| error.to_string())
    });
    assert!(
        result
            .as_ref()
            .is_err_and(|error| error.contains("external hard link")),
        "linked staging inode reached publication: {result:?}"
    );
    assert!(!output.exists());
    assert_eq!(
        fs::read(&alias).map_err(|error| error.to_string())?,
        b"ctO"
    );
    assert!(!stage(&output, None).exists());
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "reject late foreign aliases")]
fn linked_published_stage_cannot_report_success() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    let alias = fixture.0.join("foreign-published-link");
    let result = publish_new_with_hooks(
        &output,
        b"ctO",
        |_staged| Ok(()),
        |path| fs::hard_link(path, &alias).map_err(|error| error.to_string()),
    );
    assert!(
        result
            .as_ref()
            .is_err_and(|error| error.contains("external hard link")),
        "aliased published inode falsely succeeded: {result:?}"
    );
    assert_eq!(
        fs::read(&output).map_err(|error| error.to_string())?,
        b"ctO"
    );
    assert_eq!(
        fs::read(&alias).map_err(|error| error.to_string())?,
        b"ctO"
    );
    assert!(!stage(&output, None).exists());
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "admit unchanged parent alias")]
fn stable_symlinked_parent_remains_publishable() -> Result<(), String> {
    use std::os::unix::fs::symlink;

    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let physical_parent = fixture.0.join("physical-parent");
    let alias = fixture.0.join("stable-parent-link");
    fs::create_dir(&physical_parent).map_err(|error| error.to_string())?;
    symlink(&physical_parent, &alias).map_err(|error| error.to_string())?;
    let output = alias.join("artifact.malbolge");
    publish_new(&output, b"ctO")?;
    assert_eq!(
        fs::read(&output).map_err(|error| error.to_string())?,
        b"ctO"
    );
    assert_eq!(
        fs::read_dir(&physical_parent)
            .map_err(|error| error.to_string())?
            .count(),
        1
    );
    assert!(!stage(&output, None).exists());
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "reject redirected stage parent")]
fn parent_rebound_to_same_inode_after_sync_cannot_publish() -> Result<(), String> {
    use std::os::unix::fs::symlink;

    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let parent = fixture.0.join("publication-parent");
    let moved = fixture.0.join("moved-publication-parent");
    fs::create_dir(&parent).map_err(|error| error.to_string())?;
    let output = parent.join("artifact.malbolge");
    let result = publish_new_with_stage_hook(&output, b"ctO", |_staged| {
        fs::rename(&parent, &moved).map_err(|error| error.to_string())?;
        symlink(&moved, &parent).map_err(|error| error.to_string())
    });
    fs::remove_file(&parent).map_err(|error| error.to_string())?;
    fs::rename(&moved, &parent).map_err(|error| error.to_string())?;
    assert!(
        result
            .as_ref()
            .is_err_and(|error| error.contains("resolved pathname changed")),
        "parent symlink redirected stage publication: {result:?}"
    );
    assert!(!output.exists(), "target appeared after parent redirect");
    assert!(!stage(&output, None).exists());
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "reject redirected published parent"
)]
fn parent_rebound_to_same_inode_after_link_cannot_report_success() -> Result<(), String> {
    use std::os::unix::fs::symlink;

    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let parent = fixture.0.join("publication-parent");
    let moved = fixture.0.join("moved-publication-parent");
    fs::create_dir(&parent).map_err(|error| error.to_string())?;
    let output = parent.join("artifact.malbolge");
    let result = publish_new_with_hooks(
        &output,
        b"ctO",
        |_staged| Ok(()),
        |_path| {
            fs::rename(&parent, &moved).map_err(|error| error.to_string())?;
            symlink(&moved, &parent).map_err(|error| error.to_string())
        },
    );
    fs::remove_file(&parent).map_err(|error| error.to_string())?;
    fs::rename(&moved, &parent).map_err(|error| error.to_string())?;
    assert!(
        result
            .as_ref()
            .is_err_and(|error| error.contains("resolved pathname changed")),
        "parent symlink redirected final admission: {result:?}"
    );
    assert_eq!(
        fs::read(&output).map_err(|error| error.to_string())?,
        b"ctO"
    );
    assert!(!stage(&output, None).exists());
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(clippy::panic_in_result_fn, reason = "assert bounded stage reread")]
fn grown_stage_rejects_before_an_unbounded_reread() -> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    let result = publish_new_with_stage_hook(&output, b"ctO", |staged| {
        fs::OpenOptions::new()
            .write(true)
            .open(staged)
            .map_err(|error| error.to_string())?
            .set_len(8 * 1024 * 1024 * 1024)
            .map_err(|error| error.to_string())
    });
    assert!(
        result
            .as_ref()
            .is_err_and(|error| error.contains("staged output")),
        "oversized stage reached publication: {result:?}"
    );
    assert!(!output.exists());
    assert!(!stage(&output, None).exists());
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "late published-byte mutation must be detected after link"
)]
fn published_same_inode_content_rewrite_cannot_report_success()
-> Result<(), String> {
    let fixture = Fixture::new().map_err(|error| error.to_string())?;
    let output = fixture.output();
    let result = publish_new_with_hooks(
        &output,
        b"ctO",
        |_staged| Ok(()),
        |published| {
            fs::write(published, b"ctX").map_err(|error| error.to_string())
        },
    );
    assert!(
        result.is_err(),
        "late content substitution admitted: {result:?}"
    );
    assert_eq!(
        fs::read(&output).map_err(|error| error.to_string())?,
        b"ctX",
    );
    assert!(!stage(&output, None).exists());
    Ok(())
}
