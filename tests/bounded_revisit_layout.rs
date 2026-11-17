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
//   - Finite, input-specific, actual VM proofs of revisited code cells.
// - Must-Not:
//   - Substitute host computation, or claim C-to-Malbolge/EOF-loop lowering.
// - Allows:
//   - Inputs: actual profile-specific guest source and independent path oracle.
//   - Outputs: exact guest control, self-encryption, output and refusal tests.
//   - Side effects: bounded normative VM execution only.
// - Split-When:
//   - A separately accepted nonlinear guest operation family needs own tests.
// - Merge-When:
//   - The final nonlinear backend proves equivalent complete VM execution.
// - Summary:
//   - Tests bounded backward-jump, real input, and repeated code execution.
// - Description:
//   - Supplies exact code and D path oracles for both canonical VMs.
// - Usage:
//   - `cargo test --test bounded_revisit_layout`.
// - Defaults:
//   - Explicitly refuses unsupported or fabricated witnesses.
//

//! Input-specific, finite VM proofs of genuine revisiting guest source code.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{LinearOpcode, LinearProfileIdentity, encode_linear_layout};
use malbolge::{
    TraceInput, current_profile, decode_profile_instruction, historical_profile,
};

// This is deliberately separate from the forward-only layout API. The first
// jump places D at 41; the following jump reads M[41]=76 to enter C=77. The
// real guest visits C=77..92 twice: the first pass reads and echoes one byte;
// the revisited input/output cells are XLAT2-encrypted into inert operations.
// The backedge at D=57 reads M[57]=76, and the second exit at D=73 reads
// M[73]=102 to reach the halt at C=103. None of these control decisions is
// supplied to the interpreter by a host callback.
fn bounded_revisit_echo_fixture(
    profile: &'static malbolge::ProfileDescriptor,
) -> Result<Vec<u8>, String> {
    let inverse = |decoded: u8, position: usize| -> Result<u8, String> {
        (33u8..=126)
            .find(|cell| {
                decode_profile_instruction(
                    u32::from(*cell),
                    u32::try_from(position).unwrap_or(u32::MAX),
                ) == Some(decoded)
            })
            .ok_or_else(|| format!("missing code byte for {position}"))
    };
    let mut source = (0..104)
        .map(|position| inverse(b'o', position))
        .collect::<Result<Vec<_>, _>>()?;
    for (position, decoded) in [
        (0, b'j'),
        (1, b'i'),
        (77, profile.input_instruction()),
        (78, profile.output_instruction()),
        (92, b'i'),
        (103, b'v'),
    ] {
        source[position] = inverse(decoded, position)?;
    }
    // All three data bytes themselves decode as loader-admitted instructions
    // at the original source positions, despite being skipped during execution.
    source[41] = 76;
    source[57] = 76;
    source[73] = 102;
    Ok(source)
}

fn bounded_revisit_code_path() -> Vec<u32> {
    let mut path = vec![0, 1];
    path.extend(77..=92);
    path.extend(77..=92);
    path.push(103);
    path
}

#[test]
fn bounded_revisiting_guest_executes_real_input_output_and_xlat2()
-> Result<(), String> {
    use layout::{BoundedRevisitExpectation, admit_bounded_revisit_layout};
    for profile in [current_profile(), historical_profile()] {
        let source = bounded_revisit_echo_fixture(profile)?;
        let path = bounded_revisit_code_path();
        let mut data_path = vec![0, 41];
        data_path.extend(42..=57);
        data_path.extend(58..=73);
        data_path.push(74);
        let cases = [
            (Vec::new(), vec![profile.eof_word().to_le_bytes()[0]], 0),
            (vec![0], vec![0], 1),
            (vec![0x80], vec![0x80], 1),
            (vec![0xff], vec![0xff], 1),
            (vec![b'A', b'B'], vec![b'A'], 1),
        ];
        for (input, expected_output, expected_consumption) in cases {
            let input_events = if input.is_empty() {
                vec![TraceInput::EndOfInput]
            } else {
                vec![TraceInput::Byte(input[0])]
            };
            let admitted = admit_bounded_revisit_layout(
                profile,
                &source,
                LinearProfileIdentity {
                    id: profile.id(),
                    fingerprint: profile.fingerprint(),
                },
                BoundedRevisitExpectation {
                    input: &input,
                    code_positions: &path,
                    output: &expected_output,
                    input_consumed: expected_consumption,
                    input_events: &input_events,
                },
            )
            .map_err(|error| {
                format!("bounded revisiting machine: {error:?}")
            })?;
            assert_eq!(admitted.source(), source);
            assert_eq!(admitted.code_positions(), path);
            assert_eq!(admitted.data_positions(), data_path);
            assert_eq!(admitted.code_positions().len(), 35);
            assert_eq!(admitted.encrypted_positions()[0], Some(0));
            assert_eq!(admitted.encrypted_positions()[1], Some(76));
            assert_eq!(admitted.encrypted_positions()[17], Some(76));
            assert_eq!(admitted.encrypted_positions()[33], Some(102));
            assert_eq!(admitted.encrypted_positions()[34], None);
            assert_eq!(admitted.output(), expected_output);
            assert_eq!(admitted.input_consumed(), expected_consumption);
            assert_eq!(admitted.input_events(), input_events);
        }
    }
    Ok(())
}

// Two original input instructions execute before the first output. Their
// encrypted second-pass forms are inert, so EOF can be observed after a
// successful first byte without a host-controlled exit or synthetic input.
#[test]
fn revisiting_guest_proves_successful_reads_followed_by_real_eof()
-> Result<(), String> {
    use layout::{BoundedRevisitExpectation, admit_bounded_revisit_layout};
    for profile in [current_profile(), historical_profile()] {
        let mut source = bounded_revisit_echo_fixture(profile)?;
        for (position, opcode) in [
            (78, profile.input_instruction()),
            (79, profile.output_instruction()),
        ] {
            source[position] = (33u8..=126)
                .find(|byte| {
                    decode_profile_instruction(
                        u32::from(*byte),
                        u32::try_from(position).unwrap_or(u32::MAX),
                    ) == Some(opcode)
                })
                .ok_or_else(|| {
                    format!("cannot encode input/output at {position}")
                })?;
        }
        let path = bounded_revisit_code_path();
        let eof_byte = profile.eof_word().to_le_bytes()[0];
        let cases = [
            (
                vec![],
                vec![TraceInput::EndOfInput, TraceInput::EndOfInput],
                vec![eof_byte],
                0,
            ),
            (
                vec![0],
                vec![TraceInput::Byte(0), TraceInput::EndOfInput],
                vec![eof_byte],
                1,
            ),
            (
                vec![0x80, 0xff],
                vec![TraceInput::Byte(0x80), TraceInput::Byte(0xff)],
                vec![0xff],
                2,
            ),
            (
                vec![b'A', b'B', b'C'],
                vec![TraceInput::Byte(b'A'), TraceInput::Byte(b'B')],
                vec![b'B'],
                2,
            ),
        ];
        for (input, events, output, consumed) in cases {
            let admitted = admit_bounded_revisit_layout(
                profile,
                &source,
                LinearProfileIdentity {
                    id: profile.id(),
                    fingerprint: profile.fingerprint(),
                },
                BoundedRevisitExpectation {
                    input: &input,
                    code_positions: &path,
                    output: &output,
                    input_consumed: consumed,
                    input_events: &events,
                },
            )
            .map_err(|error| format!("revisiting EOF guest: {error:?}"))?;
            assert_eq!(admitted.code_positions(), path);
            assert_eq!(admitted.input_events(), events);
            assert_eq!(admitted.input_consumed(), consumed);
            assert_eq!(admitted.output(), output);
        }
        // Deleting the second EOF read preserves this exact input's path,
        // output and successful byte count. The extra EOF event is the only
        // independent witness that must refuse the altered guest source.
        let mut missing_eof = source.clone();
        *missing_eof
            .get_mut(78)
            .ok_or_else(|| String::from("missing source instruction"))? = (33u8
            ..=126)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), 78) == Some(b'o')
            })
            .ok_or_else(|| String::from("missing inert instruction"))?;
        let events = [TraceInput::EndOfInput, TraceInput::EndOfInput];
        let output = [eof_byte];
        assert_eq!(
            admit_bounded_revisit_layout(
                profile,
                &missing_eof,
                LinearProfileIdentity {
                    id: profile.id(),
                    fingerprint: profile.fingerprint(),
                },
                BoundedRevisitExpectation {
                    input: &[],
                    code_positions: &path,
                    output: &output,
                    input_consumed: 0,
                    input_events: &events,
                },
            ),
            Err(layout::BoundedRevisitError::InputEventsMismatch),
        );
    }
    Ok(())
}

#[test]
fn bounded_revisiting_admission_rejects_forged_or_incomplete_evidence()
-> Result<(), String> {
    use layout::{
        BoundedRevisitError as Error, BoundedRevisitExpectation,
        MAX_REVISIT_STEPS, admit_bounded_revisit_layout,
    };
    let profile = current_profile();
    let source = bounded_revisit_echo_fixture(profile)?;
    let path = bounded_revisit_code_path();
    let input = [0xe7];
    let output = [0xe7];
    let input_events = [TraceInput::Byte(0xe7)];
    let id = LinearProfileIdentity {
        id: profile.id(),
        fingerprint: profile.fingerprint(),
    };
    let witness = BoundedRevisitExpectation {
        input: &input,
        code_positions: &path,
        output: &output,
        input_consumed: 1,
        input_events: &input_events,
    };
    let admit = |candidate: &[u8], identity, expected| {
        admit_bounded_revisit_layout(profile, candidate, identity, expected)
    };
    assert_eq!(
        admit(
            &source,
            LinearProfileIdentity {
                id: "malbolge-forged",
                ..id
            },
            witness
        ),
        Err(Error::ProfileMismatch),
    );
    let mut corrupted = source.clone();
    corrupted[2] = b' ';
    assert_eq!(admit(&corrupted, id, witness), Err(Error::InvalidSource));
    let mut changed = source.clone();
    // A different *loader-valid* instruction at the backedge operand breaks
    // the witnessed successor while preserving source admissibility.
    changed[57] = 77;
    assert_eq!(admit(&changed, id, witness), Err(Error::PathMismatch));
    let mut wrong_path = path.clone();
    wrong_path[18] = 78;
    assert_eq!(
        admit(&source, id, BoundedRevisitExpectation {
            code_positions: &wrong_path,
            ..witness
        }),
        Err(Error::PathMismatch),
    );
    assert_eq!(
        admit(&source, id, BoundedRevisitExpectation {
            code_positions: &path[..34],
            ..witness
        }),
        Err(Error::TerminationMismatch),
    );
    assert_eq!(
        admit(&source, id, BoundedRevisitExpectation {
            output: b"Q",
            ..witness
        }),
        Err(Error::OutputMismatch),
    );
    assert_eq!(
        admit(&source, id, BoundedRevisitExpectation {
            input_consumed: 0,
            ..witness
        }),
        Err(Error::InputConsumptionMismatch),
    );
    let forged_events = [TraceInput::EndOfInput];
    assert_eq!(
        admit(&source, id, BoundedRevisitExpectation {
            input_events: &forged_events,
            ..witness
        }),
        Err(Error::InputEventsMismatch),
    );
    assert_eq!(
        admit(&source, id, BoundedRevisitExpectation {
            input_events: &[],
            ..witness
        }),
        Err(Error::InputEventsMismatch),
    );
    let forward = encode_linear_layout(profile, &[
        LinearOpcode::NoOperation,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ])
    .map_err(|error| format!("forward witness: {error:?}"))?;
    assert_eq!(
        admit(forward.source(), id, BoundedRevisitExpectation {
            input: &[],
            code_positions: &[0, 1, 2],
            output: &[0],
            input_consumed: 0,
            input_events: &[],
        },),
        Err(Error::NotRevisiting),
    );
    let too_many = vec![0; MAX_REVISIT_STEPS + 1];
    assert_eq!(
        admit(&source, id, BoundedRevisitExpectation {
            code_positions: &too_many,
            ..witness
        }),
        Err(Error::InvalidExpectation),
    );
    let oversized_events = vec![TraceInput::EndOfInput; MAX_REVISIT_STEPS + 1];
    assert_eq!(
        admit(&source, id, BoundedRevisitExpectation {
            input_events: &oversized_events,
            ..witness
        }),
        Err(Error::InvalidExpectation),
    );
    let oversized_input = vec![0; MAX_REVISIT_STEPS + 1];
    assert_eq!(
        admit(&source, id, BoundedRevisitExpectation {
            input: &oversized_input,
            ..witness
        }),
        Err(Error::InvalidExpectation),
    );
    assert_eq!(
        admit(&source, id, BoundedRevisitExpectation {
            code_positions: &[],
            ..witness
        }),
        Err(Error::InvalidExpectation),
    );
    Ok(())
}
