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
//   - Real compiler-emitter-to-runner evidence for input-dependent guest
//     ternary crazy arithmetic and actual rotate data mutation.
// - Must-Not:
//   - Represent this bounded machine plan as arbitrary C or ternary lowering.
// - Allows:
//   - Inputs: profile-bound symbolic target instructions, exact binary input.
//   - Outputs: actual raw/capsule artifact and runner output vs scalar oracle.
//   - Side effects: isolated ignored .temp fixture files only.
// - Split-When:
//   - General guest arithmetic IR lowering has its own proof contract.
// - Merge-When:
//   - An independently verified general target runner covers these effects.
// - Summary:
//   - Tests non-echo guest computation through actual emitted `.malbolge`.
// - Description:
//   - The target VM, not a host callback, performs p and * operations.
// - Usage:
//   - cargo test --test malbolge_layout_guest_arithmetic
// - Defaults:
//   - Fail closed on output/provenance mismatch.

//! End-to-end source publishing and real guest computation, not host emulation.

use std::fs;
use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio, id};
use std::sync::atomic::{AtomicUsize, Ordering};

use malbolge::{
    ProfileDescriptor, ProfileMachine, RunOutcome, current_profile, decode_profile_instruction,
    historical_profile, parse_capsule, target_profile,
};

const LAYOUT_CLI: &str = env!("CARGO_BIN_EXE_malbolge_layout");
const RUNNER_CLI: &str = env!("CARGO_BIN_EXE_malbolge");
const GUEST_PLAN: [&str; 7] = [
    "input",
    "auto-relocate",
    "crazy",
    "output",
    "rotate",
    "output",
    "halt",
];
static SEQUENCE: AtomicUsize = AtomicUsize::new(0);

struct Fixture {
    root: PathBuf,
}

impl Fixture {
    fn new() -> Result<Self, String> {
        let number = SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("layout-guest-arithmetic-{}-{number}", id()));
        #[expect(clippy::create_dir, reason = "never reuse another test's files")]
        fs::create_dir(&root).map_err(|error| format!("fixture: {error}"))?;
        Ok(Self { root })
    }

    fn path(&self, name: &str) -> PathBuf {
        self.root.join(name)
    }
}

#[expect(
    clippy::missing_trait_methods,
    reason = "Drop::pin_drop is unstable and its default no-op is correct here"
)]
impl Drop for Fixture {
    fn drop(&mut self) {
        drop(fs::remove_dir_all(&self.root));
    }
}

struct GuestOracle {
    crazy_data_word: u32,
    rotate_low_byte: u8,
    word_trits: u8,
}

impl GuestOracle {
    #[expect(
        clippy::integer_division,
        clippy::integer_division_remainder_used,
        reason = "independent ternary rotate requires exact base-three division"
    )]
    fn from_source(profile: &'static ProfileDescriptor, source: &[u8]) -> Result<Self, String> {
        let initial = ProfileMachine::from_source(profile, source, Vec::new())
            .map_err(|error| format!("normative initial source load: {error:?}"))?;
        let crazy_data_word = initial
            .memory_word(40)
            .map_err(|error| format!("initial crazy operand: {error:?}"))?;
        let rotate_word = initial
            .memory_word(42)
            .map_err(|error| format!("initial rotate operand: {error:?}"))?;
        let rotated = (rotate_word / 3)
            .saturating_add((rotate_word % 3).saturating_mul(profile.word_modulus() / 3));
        let rotate_low_byte = u8::try_from(rotated % 256).map_err(|error| error.to_string())?;
        Ok(Self {
            crazy_data_word,
            rotate_low_byte,
            word_trits: profile.word_trits(),
        })
    }

    #[expect(
        clippy::integer_division_remainder_used,
        reason = "the guest output low-byte contract uses remainder 256"
    )]
    fn output(&self, input: u8) -> Result<[u8; 2], String> {
        let crazy = scalar_crazy(self.crazy_data_word, u32::from(input), self.word_trits);
        let crazy_low_byte = u8::try_from(crazy % 256).map_err(|error| error.to_string())?;
        Ok([crazy_low_byte, self.rotate_low_byte])
    }
}

fn publish(profile: &str, destination: &Path, capsule: bool) -> Result<Vec<u8>, String> {
    let mut command = Command::new(LAYOUT_CLI);
    let _args = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(destination);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    let output = command
        .arg("--")
        .arg("--auto-layout")
        .args(GUEST_PLAN)
        .output()
        .map_err(|error| format!("spawn graphical encoder: {error}"))?;
    if !output.status.success() || !output.stdout.is_empty() {
        return Err(format!("graphical publisher failed: {output:?}"));
    }
    fs::read(destination).map_err(|error| format!("read graphical artifact: {error}"))
}

fn run_real_guest(path: &Path, input: u8) -> Result<Output, String> {
    let mut child = Command::new(RUNNER_CLI)
        .arg(path)
        .arg("--input-stdin")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("spawn true guest runner: {error}"))?;
    let mut stdin = child.stdin.take().ok_or("runner lacks input pipe")?;
    stdin
        .write_all(&[input])
        .map_err(|error| format!("send binary guest byte: {error}"))?;
    drop(stdin);
    child
        .wait_with_output()
        .map_err(|error| format!("collect guest output: {error}"))
}

fn verify_guest_process(path: &Path, input: u8, expected: [u8; 2]) -> Result<(), String> {
    let output = run_real_guest(path, input)?;
    if !output.status.success() || !output.stderr.is_empty() {
        return Err(format!("real guest runner failed: {output:?}"));
    }
    if output.stdout != expected {
        return Err(format!(
            "guest arithmetic mismatch for input {input}: expected {expected:?}, got {:?}",
            output.stdout,
        ));
    }
    if output.stdout == [input] {
        return Err(String::from("guest arithmetic unexpectedly echoed input"));
    }
    Ok(())
}

/// Independent scalar table rather than VM chunked-ternary crazy arithmetic.
#[expect(
    clippy::integer_division_remainder_used,
    reason = "trit-table oracle must independently extract base-3 digits"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0u32;
    let mut place = 1u32;
    for _digit in 0..trits {
        let row = usize::try_from(data % 3).unwrap_or_default();
        let col = usize::try_from(accumulator % 3).unwrap_or_default();
        let digit = TABLE
            .get(row)
            .and_then(|values| values.get(col))
            .copied()
            .unwrap_or_default();
        result = result.saturating_add(place.saturating_mul(digit));
        place = place.saturating_mul(3);
        data /= 3;
        accumulator /= 3;
    }
    result
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "the compiler and actual Malbolge runner outputs must be checked"
)]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "all immutable profile identities and real guest effects are compared"
)]
fn real_emitted_malbolge_computes_non_echo_crazy_and_rotate_bytes() -> Result<(), String> {
    let fixture = Fixture::new()?;
    let profiles = [
        historical_profile(),
        current_profile(),
        target_profile("malbolge-2026.1").ok_or("missing versioned 2026.1")?,
        target_profile("malbolge-2026.2").ok_or("missing versioned 2026.2")?,
        target_profile("malbolge-2026.3").ok_or("missing versioned 2026.3")?,
    ];
    for profile in profiles {
        let raw_path = fixture.path(&format!("{}-raw.malbolge", profile.id()));
        let capsule_path = fixture.path(&format!("{}-capsule.malbolge", profile.id()));
        let raw = publish(profile.id(), &raw_path, false)?;
        assert_eq!(raw.len(), 7);
        for (index, opcode) in [
            profile.input_instruction(),
            b'j',
            b'p',
            profile.output_instruction(),
            b'*',
            profile.output_instruction(),
            b'v',
        ]
        .iter()
        .enumerate()
        {
            let code = u32::try_from(index).map_err(|error| error.to_string())?;
            assert_eq!(
                decode_profile_instruction(
                    u32::from(*raw.get(index).ok_or("missing exact code cell")?),
                    code,
                ),
                Some(*opcode)
            );
        }
        let frame = publish(profile.id(), &capsule_path, true)?;
        let capsule = parse_capsule(&frame)
            .map_err(|error| format!("independent frame parser: {error:?}"))?
            .ok_or("capsule not recognized")?;
        assert_eq!(capsule.profile().id(), profile.id());
        assert_eq!(capsule.profile().fingerprint(), profile.fingerprint());
        assert_eq!(capsule.payload(), raw);
        let oracle = GuestOracle::from_source(profile, &raw)?;
        // The 14/15-trit versioned capsules are expensive to load. Exercise
        // one binary high-byte on each immutable version and two boundary
        // bytes on the canonical historical/current pair.
        let inputs = if profile.id() == current_profile().id()
            || profile.id() == historical_profile().id()
        {
            &[0u8, 255][..]
        } else {
            &[255u8][..]
        };
        for &input in inputs {
            let expected = oracle.output(input)?;
            // Historical raw and both profile capsules have direct CLI
            // dispatch. Modern raw is intentionally profile-unframed.
            if profile.id() == historical_profile().id() {
                verify_guest_process(&raw_path, input, expected)?;
            }
            verify_guest_process(&capsule_path, input, expected)?;
        }
        let mut vm = ProfileMachine::from_source(profile, &raw, vec![255])
            .map_err(|error| format!("normative guest source load: {error:?}"))?;
        assert!(matches!(
            vm.run(7),
            Ok(RunOutcome::Terminated { steps: 7, .. })
        ));
        assert_eq!(vm.output(), &oracle.output(255)?);
    }
    Ok(())
}
