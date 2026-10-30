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
//   - Exact two-way guest bytecode HALT-versus-ECHO behavior and independent checks.
// - Must-Not:
//   - Re-run the separate compact test module or claim a general bytecode VM.
// - Allows:
//   - Inputs: canonical source-bound echo-one/two programs, actual profile VM.
//   - Outputs: tests and externally executed canonical .malbolge capsules.
//   - Side effects: owned project .temp fixture creation and cleanup.
// - Split-When:
//   - A general guest bytecode program runner is added to the product compiler.
// - Merge-When:
//   - Multi-variant runtime testing becomes production compiler validation.
// - Summary:
//   - Two distinct canonical source programs share byte-identical guest code.
// - Description:
//   - Physical guest source byte 87 or 104 selects HALT or second input/output.
// - Usage:
//   - cargo test --locked --test compact_guest_conditional_dispatch
// - Defaults:
//   - Fail closed on source/profile/candidate/guest-VM discrepancies.

//! Independently verified two-way graphical guest bytecode data dispatch.

#[path = "../algorithms/compact-guest-bytecode-strategy/echo_binding.rs"]
pub mod binding;
#[path = "../algorithms/compact-guest-bytecode-strategy/conditional_dispatch.rs"]
pub mod conditional;
#[path = "../algorithms/compact-guest-bytecode-strategy/guest_payload_probe.rs"]
pub mod guest_probe;
#[path = "../algorithms/compact-guest-bytecode-strategy/isolated_dispatch.rs"]
pub mod isolated;
#[path = "../algorithms/compact-guest-bytecode-strategy/echo_macro.rs"]
pub mod strategy;

use std::fs;
use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio, id};

use conditional::{
    CEB2_START, ConditionalDispatchError, ECHO_OPCODE_WORD, ECHO_TWICE_STEPS, FIRST_OPCODE_ADDRESS,
    HALT_AFTER_ONE_STEPS, HALT_OPCODE_WORD, SECOND_OPCODE_ADDRESS, SOURCE_CELLS,
    admit_conditional_guest_dispatch, embed_conditional_guest_dispatch,
};
use malbolge::{ProfileMachine, RunOutcome, current_profile, decode_profile_instruction};
use strategy::bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryProgram, TypedIrInput, canonical_ternary_bytes,
    canonical_ternary_program, lower_typed_ir,
};

const CONFIG: &str = include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v8.toml");

struct CapsuleFixture {
    root: PathBuf,
}

impl CapsuleFixture {
    fn new() -> Result<Self, String> {
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("compact-conditional-{}", id()));
        #[expect(clippy::create_dir, reason = "unique owned test path")]
        fs::create_dir(&root).map_err(|error| format!("owned capsule fixture: {error}"))?;
        Ok(Self { root })
    }
}

#[expect(
    clippy::missing_trait_methods,
    reason = "owned short-lived test fixture cleanup"
)]
impl Drop for CapsuleFixture {
    fn drop(&mut self) {
        drop(fs::remove_dir_all(&self.root));
    }
}

const fn position(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte.saturating_add(1),
        line: 1,
    }
}

const fn span(from: u32, to: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: position(from),
        end: position(to),
    }
}

fn canonical_echo_program(pairs: u32) -> Result<TernaryProgram, String> {
    let mut instructions = Vec::new();
    for index in 0..pairs {
        let from = index.saturating_mul(2);
        instructions.push(InputInstruction::ByteInput {
            result: index,
            span: span(from, from.saturating_add(1)),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: span(from.saturating_add(1), from.saturating_add(2)),
            value: index,
        });
    }
    let end = pairs.saturating_mul(2).saturating_add(1);
    let source = TypedIrInput {
        abi_id: String::from("malbolge-c32-v1"),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: 0,
                instructions,
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: span(end.saturating_sub(1), end),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("research_echo"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("research/compact-echo.c"),
        source_sha256: [0x51; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered = lower_typed_ir(&source).map_err(|error| format!("lower original: {error:?}"))?;
    let bytes = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("canonical source: {error:?}"))?;
    let roundtrip = canonical_ternary_program(&bytes)
        .map_err(|error| format!("canonical decode: {error:?}"))?;
    if roundtrip != lowered {
        return Err(String::from("canonical round-trip source mismatch"));
    }
    Ok(roundtrip)
}

#[expect(
    clippy::type_complexity,
    reason = "paired canonical program and resident source"
)]
#[expect(
    clippy::panic_in_result_fn,
    reason = "host descriptor fixture validates itself"
)]
fn candidate(pairs: u32) -> Result<(TernaryProgram, Vec<u8>), String> {
    let program = canonical_echo_program(pairs)?;
    let envelope = binding::encode_bound_echo_macro(&program, current_profile())
        .map_err(|error| format!("CEB2 source digest: {error:?}"))?;
    let source = embed_conditional_guest_dispatch(&program, current_profile(), &envelope)
        .map_err(|error| format!("conditional source: {error:?}"))?;
    assert_eq!(
        admit_conditional_guest_dispatch(&program, current_profile(), &source),
        Ok(envelope),
        "host must recover and re-admit full CEB2"
    );
    Ok((program, source))
}

#[test]
fn conditional_v8_pins_both_guest_opcodes_and_non_interpreter_limits() {
    for line in [
        "schema = \"compact-guest-bytecode-pilot-v8\"",
        "accepted_original_echo_pairs = [1, 2]",
        "identical_guest_code_for_both_counts = true",
        "physical_source_cells = 227",
        "halt_opcode_graphical_word = 87",
        "echo_opcode_graphical_word = 104",
        "halt_after_one_handler = \"halt@88\"",
        "echo_second_handler = \"input@105-output@106-halt@107\"",
        "one_pair_guest_steps = 86",
        "two_pair_guest_steps = 88",
        "source_bound_descriptor_start = 125",
        "source_bound_descriptor_cells = 102",
        "runtime_selects_halt_or_echo_from_guest_source = true",
        "guest_decodes_ternary_ordinal = false",
        "guest_sha256_authentication = false",
        "general_guest_interpreter = false",
        "count_driven_loop = false",
    ] {
        assert!(
            CONFIG.lines().any(|actual| actual == line),
            "missing pinned negative or positive v8 invariant {line}"
        );
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "two canonical guest programs share one code"
)]
#[expect(
    clippy::too_many_lines,
    reason = "cross-source source, VM and descriptor comparison"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "independent guest-source branch witnesses"
)]
#[expect(
    clippy::excessive_nesting,
    reason = "VM jump trace on two code paths and input cases"
)]
fn two_canonical_programs_use_identical_guest_code_but_data_selects_halt_or_echo()
-> Result<(), String> {
    let (one, one_source) = candidate(1)?;
    let (two, two_source) = candidate(2)?;
    assert_eq!(one_source.len(), SOURCE_CELLS);
    assert_eq!(two_source.len(), SOURCE_CELLS);
    assert_eq!(FIRST_OPCODE_ADDRESS, 121);
    assert_eq!(SECOND_OPCODE_ADDRESS, 124);
    assert_eq!(CEB2_START, 125);
    assert_eq!(one_source.get(124), Some(&HALT_OPCODE_WORD));
    assert_eq!(two_source.get(124), Some(&ECHO_OPCODE_WORD));
    assert_eq!(
        one_source.get(..SECOND_OPCODE_ADDRESS),
        two_source.get(..SECOND_OPCODE_ADDRESS),
        "all initial machine code + both handlers must be the SAME bytes"
    );
    for position in SECOND_OPCODE_ADDRESS..CEB2_START {
        assert_eq!(
            position, SECOND_OPCODE_ADDRESS,
            "only last source cell before CEB2 differs between variants"
        );
    }
    for source in [&one_source, &two_source] {
        for (position, &glyph) in source.iter().enumerate() {
            assert!(
                matches!(
                    decode_profile_instruction(
                        u32::from(glyph),
                        u32::try_from(position).map_err(|error| error.to_string())?
                    ),
                    Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                ),
                "all code and CEB2 positions must be loader valid {position}"
            );
        }
    }
    for (pairs, program, source, second_word, steps) in [
        (
            1usize,
            &one,
            &one_source,
            u32::from(HALT_OPCODE_WORD),
            HALT_AFTER_ONE_STEPS,
        ),
        (
            2,
            &two,
            &two_source,
            u32::from(ECHO_OPCODE_WORD),
            ECHO_TWICE_STEPS,
        ),
    ] {
        let direct = strategy::bridge::encode_successful_byte_echo(program, current_profile())
            .map_err(|error| format!("independent direct one/two echo: {error:?}"))?;
        assert_eq!(
            direct.source().len(),
            pairs.saturating_mul(2).saturating_add(1)
        );
        for input in [vec![0u8, 255], vec![128, 129]] {
            let mut guest = ProfileMachine::from_source(current_profile(), source, input.clone())
                .map_err(|error| format!("guest loader: {error:?}"))?;
            let mut jumps = Vec::new();
            let outcome = guest
                .run_traced(steps, &mut |trace| {
                    if matches!(trace.before.registers.code_pointer, 81 | 93) {
                        jumps.push(*trace);
                    }
                })
                .map_err(|error| format!("native guest VM: {error:?}"))?;
            assert!(
                matches!(outcome, RunOutcome::Terminated { steps: committed, .. }
                if committed == steps),
                "guest halts exactly after both reached jumps"
            );
            assert_eq!(jumps.len(), 2, "both branches are guest executed");
            for (index, (code, data, operand)) in [(81u32, 121u32, 90u32), (93, 124, second_word)]
                .into_iter()
                .enumerate()
            {
                let trace = jumps.get(index).ok_or("two separate branch traces")?;
                assert_eq!(trace.decoded, Some(b'i'));
                assert_eq!(trace.before.registers.code_pointer, code);
                assert_eq!(trace.before.registers.data_pointer, data);
                assert_eq!(
                    trace
                        .memory_reads
                        .data
                        .map(|read| (read.address, read.value)),
                    Some((data, operand)),
                    "opcode read from physical guest data"
                );
                assert_eq!(
                    trace.memory_delta.encryption.map(|write| write.address),
                    Some(operand),
                    "XLAT2 only modifies code cells"
                );
                assert_eq!(
                    trace.after.registers.code_pointer,
                    operand.saturating_add(1)
                );
            }
            let mut baseline =
                ProfileMachine::from_source(current_profile(), direct.source(), input.clone())
                    .map_err(|error| format!("direct source loader: {error:?}"))?;
            let direct_steps = pairs.saturating_mul(2).saturating_add(1);
            assert!(matches!(baseline.run(direct_steps),
                Ok(RunOutcome::Terminated { steps: count, .. }) if count == direct_steps));
            assert_eq!(
                guest.output(),
                baseline.output(),
                "single shared code chooses correct original semantic count"
            );
            assert_eq!(guest.input_consumed(), baseline.input_consumed());
            assert_eq!(guest.input_consumed(), pairs);
            for index in CEB2_START..SOURCE_CELLS {
                let address = u32::try_from(index).map_err(|error| error.to_string())?;
                assert_eq!(
                    guest
                        .memory_word(address)
                        .map_err(|error| format!("bound guest CEB2[{index}]: {error:?}"))?,
                    u32::from(*source.get(index).ok_or("resident descriptor cell")?),
                    "both physical code paths preserve all 102 bound data words"
                );
            }
        }
    }
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "host-rejected opcode switch")]
#[expect(
    clippy::cognitive_complexity,
    reason = "host/guest trust boundary mutation witness"
)]
fn flipping_only_second_opcode_changes_guest_behavior_but_invalidates_binding() -> Result<(), String>
{
    let (one, one_source) = candidate(1)?;
    let envelope = binding::encode_bound_echo_macro(&one, current_profile())
        .map_err(|error| format!("original CEB2: {error:?}"))?;
    let mut forged = one_source.clone();
    *forged
        .get_mut(SECOND_OPCODE_ADDRESS)
        .ok_or("second opcode")? = ECHO_OPCODE_WORD;
    assert_eq!(
        admit_conditional_guest_dispatch(&one, current_profile(), &forged),
        Err(ConditionalDispatchError::InvalidSource),
        "host must compare source-bound canonical count and graphical opcode"
    );
    assert_eq!(
        admit_conditional_guest_dispatch(&one, current_profile(), &one_source),
        Ok(envelope),
        "original source still passes independently"
    );
    for (source, expected_steps, expected) in [
        (&one_source, HALT_AFTER_ONE_STEPS, vec![0u8]),
        (&forged, ECHO_TWICE_STEPS, vec![0u8, 255]),
    ] {
        let mut machine = ProfileMachine::from_source(current_profile(), source, vec![0u8, 255])
            .map_err(|error| format!("real guest loaded: {error:?}"))?;
        let outcome = machine
            .run(expected_steps)
            .map_err(|error| format!("real data-selected guest flow: {error:?}"))?;
        assert!(
            matches!(outcome, RunOutcome::Terminated { steps, .. }
            if steps == expected_steps),
            "real guest follows changed opcode data"
        );
        assert_eq!(machine.output(), expected);
        assert_eq!(machine.input_consumed(), expected.len());
        for position in CEB2_START..SOURCE_CELLS {
            assert_eq!(
                machine
                    .memory_word(u32::try_from(position).map_err(|error| error.to_string())?)
                    .map_err(|error| format!("guest CEB2 memory: {error:?}"))?,
                u32::from(*source.get(position).ok_or("bound source cell")?)
            );
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "two source-bound CLI program variants"
)]
#[expect(
    clippy::too_many_lines,
    reason = "external direct/guest capsule byte and step receipts"
)]
fn conditional_guest_and_direct_capsules_match_in_general_malbolge_cli() -> Result<(), String> {
    let fixture = CapsuleFixture::new()?;
    for pairs in [1usize, 2] {
        let program =
            canonical_echo_program(u32::try_from(pairs).map_err(|error| error.to_string())?)?;
        let bound = binding::encode_bound_echo_macro(&program, current_profile())
            .map_err(|error| format!("canonical source-bound CEB2: {error:?}"))?;
        let guest = embed_conditional_guest_dispatch(&program, current_profile(), &bound)
            .map_err(|error| format!("guest publisher: {error:?}"))?;
        assert_eq!(
            admit_conditional_guest_dispatch(&program, current_profile(), &guest),
            Ok(bound),
            "only verified guest sources enter general CLI"
        );
        let direct = strategy::bridge::encode_successful_byte_echo(&program, current_profile())
            .map_err(|error| format!("real direct publisher: {error:?}"))?;
        for (kind, bytes) in [("guest", guest.as_slice()), ("direct", direct.source())] {
            let path = fixture.root.join(format!("{kind}-{pairs}.malbolge"));
            let capsule = malbolge::build_capsule(current_profile(), bytes)
                .map_err(|error| format!("build canonical capsule: {error:?}"))?;
            fs::write(path, capsule).map_err(|error| format!("publish: {error}"))?;
        }
        for (kind, expected_steps) in [
            ("direct", pairs.saturating_mul(2).saturating_add(1)),
            (
                "guest",
                if pairs == 1 {
                    HALT_AFTER_ONE_STEPS
                } else {
                    ECHO_TWICE_STEPS
                },
            ),
        ] {
            let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
                .arg(fixture.root.join(format!("{kind}-{pairs}.malbolge")))
                .arg("--input-stdin")
                .arg("--report-steps")
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .map_err(|error| format!("general Malbolge CLI: {error}"))?;
            let mut stdin = child.stdin.take().ok_or("CLI stdin missing")?;
            stdin
                .write_all(&[0u8, 255])
                .map_err(|error| format!("CLI stdin write: {error}"))?;
            drop(stdin);
            let output = child
                .wait_with_output()
                .map_err(|error| format!("CLI process wait: {error}"))?;
            assert!(output.status.success(), "general CLI failed: {output:?}");
            assert_eq!(
                output.stdout,
                [0u8, 255]
                    .get(..pairs)
                    .ok_or("expected one/two CLI bytes")?,
                "two alternative bytecode operands select exact output length"
            );
            assert_eq!(
                output.stderr,
                format!("malbolge-steps-v1:{expected_steps}\n").as_bytes(),
                "real general CLI provides independent committed step receipt"
            );
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "host-only descriptor forgery matrix"
)]
#[expect(
    clippy::too_many_lines,
    reason = "unsupported count and all code/data boundary cases"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "two canonical programs and mutation cases"
)]
fn conditional_dispatch_rejects_wrong_counts_unknown_opcodes_and_foreign_sources()
-> Result<(), String> {
    for unsupported_pairs in [3u32, 7, 10, 64] {
        let original = canonical_echo_program(unsupported_pairs)?;
        let envelope = binding::encode_bound_echo_macro(&original, current_profile())
            .map_err(|error| format!("bound unsupported count: {error:?}"))?;
        assert_eq!(
            embed_conditional_guest_dispatch(&original, current_profile(), &envelope),
            Err(ConditionalDispatchError::UnsupportedEchoCount),
            "only one and two original echo pairs have native guest semantics"
        );
    }
    for pairs in [1u32, 2] {
        let (original, source) = candidate(pairs)?;
        let envelope = binding::encode_bound_echo_macro(&original, current_profile())
            .map_err(|error| format!("bound candidate: {error:?}"))?;
        let original_word = *source.get(SECOND_OPCODE_ADDRESS).ok_or("second opcode")?;
        let allowed = (33u8..=126u8).filter(|&glyph| {
            matches!(
                decode_profile_instruction(
                    u32::from(glyph),
                    u32::try_from(SECOND_OPCODE_ADDRESS).unwrap_or(u32::MAX)
                ),
                Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            )
        });
        let mut alternatives = 0usize;
        for word in allowed.filter(|&word| word != original_word) {
            let mut altered = source.clone();
            *altered
                .get_mut(SECOND_OPCODE_ADDRESS)
                .ok_or("alter opcode")? = word;
            assert!(
                admit_conditional_guest_dispatch(&original, current_profile(), &altered).is_err(),
                "all seven alternative loader glyphs must fail admission"
            );
            alternatives = alternatives.saturating_add(1);
        }
        assert_eq!(alternatives, 7, "every other phase-valid choice is tested");
        for address in [0usize, 81, 88, 91, 92, 93, 105, 106, 107, 121] {
            let mut altered = source.clone();
            *altered.get_mut(address).ok_or("native code cell")? = b'!';
            assert_eq!(
                admit_conditional_guest_dispatch(&original, current_profile(), &altered),
                Err(ConditionalDispatchError::InvalidSource),
                "changed code or the first opcode must fail exact admission"
            );
        }
        for address in [CEB2_START, CEB2_START + 1, SOURCE_CELLS - 1] {
            let mut altered = source.clone();
            let current = *altered.get(address).ok_or("CEB2 glyph")?;
            let alternative = (33u8..=126u8)
                .find(|&glyph| {
                    glyph != current
                        && matches!(
                            decode_profile_instruction(
                                u32::from(glyph),
                                u32::try_from(address).unwrap_or(u32::MAX)
                            ),
                            Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                        )
                })
                .ok_or("second valid packed descriptor glyph")?;
            *altered.get_mut(address).ok_or("mutated CEB2 glyph")? = alternative;
            assert!(
                admit_conditional_guest_dispatch(&original, current_profile(), &altered).is_err(),
                "source-bound descriptor rejects loader-valid tampering"
            );
        }
        for shortened in [0usize, 1, 81, 124, CEB2_START, SOURCE_CELLS - 1] {
            assert_eq!(
                admit_conditional_guest_dispatch(
                    &original,
                    current_profile(),
                    source.get(..shortened).ok_or("source prefix")?
                ),
                Err(ConditionalDispatchError::InvalidSource),
                "short source cannot admit complete source-bound program"
            );
        }
        let mut extended = source.clone();
        extended.push(b'!');
        assert_eq!(
            admit_conditional_guest_dispatch(&original, current_profile(), &extended),
            Err(ConditionalDispatchError::InvalidSource),
            "overlong source cannot be admitted"
        );
        let mut other = original;
        other.source_id = format!("research/foreign-{pairs}-echo.c");
        assert!(
            admit_conditional_guest_dispatch(&other, current_profile(), &source).is_err(),
            "same count with foreign canonical identity must fail digest binding"
        );
        let unmodified = candidate(pairs)?.1;
        let verifier_input = canonical_echo_program(pairs)?;
        assert_eq!(
            admit_conditional_guest_dispatch(&verifier_input, current_profile(), &unmodified),
            Ok(envelope),
            "independent host verification still accepts original"
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent two-way EOF/input parity"
)]
#[expect(
    clippy::too_many_lines,
    reason = "full-state VM replay with both instruction choices"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "EOF, one/two and surplus stream oracles"
)]
fn same_native_guest_code_matches_direct_for_eof_short_and_trailing_input() -> Result<(), String> {
    for pairs in [1u32, 2] {
        let (program, source) = candidate(pairs)?;
        let direct = strategy::bridge::encode_successful_byte_echo(&program, current_profile())
            .map_err(|error| format!("direct one/two echo lowering: {error:?}"))?;
        let guest_initial = ProfileMachine::from_source(current_profile(), &source, Vec::new())
            .map_err(|error| format!("source-bound guest preload: {error:?}"))?
            .snapshot_state();
        let direct_initial =
            ProfileMachine::from_source(current_profile(), direct.source(), Vec::new())
                .map_err(|error| format!("independent direct preload: {error:?}"))?
                .snapshot_state();
        let pair_count = usize::try_from(pairs).map_err(|error| error.to_string())?;
        let steps = if pairs == 1 {
            HALT_AFTER_ONE_STEPS
        } else {
            ECHO_TWICE_STEPS
        };
        let direct_steps = pair_count.saturating_mul(2).saturating_add(1);
        for input in [
            Vec::new(),
            vec![0u8],
            vec![255],
            vec![0, 255],
            vec![7, 129, 255],
            vec![0, 1, 2, 3],
        ] {
            // Each execution starts from its own exact immutable loader
            // checkpoint; never reuse a previous run's self-encrypted code.
            let mut guest = ProfileMachine::from_state(
                current_profile(),
                guest_initial.memory().to_vec(),
                input.clone(),
                malbolge::ProfileRegisters::default(),
            )
            .map_err(|error| format!("restored guest VM: {error:?}"))?;
            let mut baseline = ProfileMachine::from_state(
                current_profile(),
                direct_initial.memory().to_vec(),
                input.clone(),
                malbolge::ProfileRegisters::default(),
            )
            .map_err(|error| format!("restored direct VM: {error:?}"))?;
            assert!(
                matches!(guest.run(steps), Ok(RunOutcome::Terminated {
                steps: committed, ..
            }) if committed == steps),
                "guest variant halts under EOF and surplus input"
            );
            assert!(
                matches!(baseline.run(direct_steps), Ok(RunOutcome::Terminated {
                steps: committed, ..
            }) if committed == direct_steps),
                "direct variant halts under same input"
            );
            assert_eq!(
                guest.output(),
                baseline.output(),
                "both independent native programs produce identical bytes"
            );
            assert_eq!(
                guest.output().len(),
                pair_count,
                "ECHO/HALT chosen by guest opcode preserves correct output count"
            );
            assert_eq!(
                guest.input_consumed(),
                baseline.input_consumed(),
                "real guest consumes exactly what direct program consumed"
            );
            assert_eq!(
                guest.input_consumed(),
                input.len().min(pair_count),
                "available input is consumed at most once per ECHO opcode"
            );
            for address in CEB2_START..SOURCE_CELLS {
                let addr = u32::try_from(address).map_err(|error| error.to_string())?;
                assert_eq!(
                    guest
                        .memory_word(addr)
                        .map_err(|error| format!("guest protected memory: {error:?}"))?,
                    u32::from(*source.get(address).ok_or("source-bound CEB2 cell")?),
                    "both opcode branches must preserve all CEB2 physical words"
                );
            }
        }
    }
    Ok(())
}
