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
//   - Real typed-IR wire to executable Malbolge byte-echo integration evidence.
// - Must-Not:
//   - Claim arbitrary C lowering, EOF equivalence, or guest ABI realization.
// - Allows:
//   - Inputs: complete typed IR wire and adversarial admitted typed fixtures.
//   - Outputs: exact ternary and target stage witnesses and real VM execution.
//   - Side effects: bounded in-memory VM and owned ignored process fixtures.
// - Split-When:
//   - A complete canonical typed-IR assembler replaces the narrow fixture.
// - Merge-When:
//   - End-to-end verified source-C compilation owns this same target subset.
// - Summary:
//   - Proves compiler-owned projections, not caller-made semantic copies.
// - Description:
//   - Tests typed source/SSA invariants plus canonical MCTR and VM output.
// - Usage:
//   - Run cargo test --locked --test typed_echo_adapter.
// - Defaults:
//   - No target publication on any input or stage failure.
//
//! Verifies the admitted typed-IR trace reaches real executable Malbolge.

#[path = "../src/compiler/typed-echo-adapter/composition/lib.rs"]
pub mod adapter;

use adapter::bridge::ternary::{TernaryOperation, TernarySourceSpan, canonical_ternary_program};
use adapter::typed::{
    BasicBlock, BasicBlockSpec, BlockId, Function, FunctionId, FunctionSpec, Instruction,
    LocatedInstruction, Module, ModuleSpec, SourcePosition, SourceSpan, Terminator, TypeDef,
    TypeEntry, TypeId, ValueId, canonical_bytes, canonical_module, validate_module,
};
use adapter::{TypedEchoAdapterError, compile_canonical_typed_echo};
use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile, target_profile};
use std::fs;
use std::io::Write as _;
use std::iter::repeat_n;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio, id};
#[cfg(target_os = "linux")]
use std::sync::atomic::AtomicBool;
use std::sync::atomic::{AtomicUsize, Ordering};

static TEST_SEQUENCE: AtomicUsize = AtomicUsize::new(0);

#[derive(Clone, Copy)]
enum ZeroPrefixedEffect {
    Input(u32),
    Output(u32),
    Scalar(u32),
}

#[derive(Clone, Copy)]
enum IdentityEffect {
    Cast {
        result: u32,
        value: u32,
        type_id: u32,
    },
    Input(u32),
    Literal {
        result: u32,
        byte: u8,
    },
    Output(u32),
    Zero(u32),
}

type SeededPublisherCase = (u8, usize, bool, bool, bool);

struct OwnedFixture {
    root: PathBuf,
}

impl OwnedFixture {
    fn new() -> Result<Self, String> {
        let index = TEST_SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("typed-echo-adapter-{}-{index}", id()));
        #[expect(clippy::create_dir, reason = "require fresh private test directory")]
        fs::create_dir(&root).map_err(|error| format!("fixture create: {error}"))?;
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
impl Drop for OwnedFixture {
    fn drop(&mut self) {
        drop(fs::remove_dir_all(&self.root));
    }
}

const fn pos(byte: u32) -> SourcePosition {
    SourcePosition::new(byte, 1, byte.saturating_add(1))
}

const fn span(start: u32, end: u32) -> SourceSpan {
    SourceSpan::new(pos(start), pos(end))
}

fn effects(pairs: usize) -> Result<Vec<LocatedInstruction>, String> {
    let mut result = Vec::with_capacity(pairs.saturating_mul(2));
    for i in 0..pairs {
        let index = u32::try_from(i).map_err(|error| format!("SSA identity: {error}"))?;
        let start = index.saturating_mul(2);
        result.push(LocatedInstruction::new(
            Instruction::ByteInput {
                result: ValueId::new(index),
                type_id: TypeId::new(0),
            },
            span(start, start.saturating_add(1)),
        ));
        result.push(LocatedInstruction::new(
            Instruction::ByteOutput {
                value: ValueId::new(index),
            },
            span(start.saturating_add(1), start.saturating_add(2)),
        ));
    }
    Ok(result)
}

fn fixture_with_instructions(
    instructions: Vec<LocatedInstruction>,
    source_id: &str,
) -> Result<Module, String> {
    fixture_with_profile(instructions, source_id, current_profile().id())
}

fn fixture_with_profile(
    instructions: Vec<LocatedInstruction>,
    source_id: &str,
    profile_id: &str,
) -> Result<Module, String> {
    let count = u32::try_from(instructions.len())
        .map_err(|error| format!("fixture operation count: {error}"))?;
    Ok(Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: adapter::typed::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: span(0, count.saturating_add(1)),
                terminator: Terminator::Return { value: None },
                terminator_span: span(count, count.saturating_add(1)),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("typed_echo"),
            parameters: Vec::new(),
            signature: TypeId::new(1),
            span: span(0, count.saturating_add(1)),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: source_id.to_owned(),
        source_sha256: [0xb4; 32],
        target_profile: profile_id.to_owned(),
        types: vec![
            TypeEntry::new(TypeId::new(0), TypeDef::U8),
            TypeEntry::new(TypeId::new(1), TypeDef::function(Vec::new(), None, false)),
        ],
    }))
}

fn fixture(pairs: usize) -> Result<Module, String> {
    fixture_with_instructions(effects(pairs)?, "fixtures/typed-echo.c")
}

fn wire(module: &Module) -> Result<Vec<u8>, String> {
    validate_module(module).map_err(|error| format!("typed IR admission: {error:?}"))?;
    canonical_bytes(module).map_err(|error| format!("typed IR encode: {error:?}"))
}

fn zero_prefixed_typed_fixture(
    initial: u8,
    effects: &[ZeroPrefixedEffect],
) -> Result<Module, String> {
    let mut instructions = Vec::with_capacity(effects.len().saturating_add(1));
    instructions.push(LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: adapter::typed::IntegerConstant::new(8, vec![initial]),
            result: ValueId::new(0),
            type_id: TypeId::new(0),
        },
        span(0, 1),
    ));
    for (index, effect) in effects.iter().enumerate() {
        let start = u32::try_from(index.saturating_add(1))
            .map_err(|error| format!("mixed canonical typed span: {error}"))?;
        let instruction = match effect {
            ZeroPrefixedEffect::Input(result) => Instruction::ByteInput {
                result: ValueId::new(*result),
                type_id: TypeId::new(0),
            },
            ZeroPrefixedEffect::Output(value) => Instruction::ByteOutput {
                value: ValueId::new(*value),
            },
            ZeroPrefixedEffect::Scalar(result) => Instruction::ConstantInteger {
                constant: adapter::typed::IntegerConstant::new(8, vec![0]),
                result: ValueId::new(*result),
                type_id: TypeId::new(0),
            },
        };
        instructions.push(LocatedInstruction::new(
            instruction,
            span(start, start.saturating_add(1)),
        ));
    }
    fixture_with_instructions(instructions, "fixtures/typed-zero-prefixed.c")
}

fn admitted_zero_prefix_fixture() -> Result<Module, String> {
    zero_prefixed_typed_fixture(
        0,
        &[
            ZeroPrefixedEffect::Output(0),
            ZeroPrefixedEffect::Output(0),
            ZeroPrefixedEffect::Input(1),
            ZeroPrefixedEffect::Output(1),
            ZeroPrefixedEffect::Output(1),
            ZeroPrefixedEffect::Input(2),
            ZeroPrefixedEffect::Output(2),
        ],
    )
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "stage and real VM output assertions"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "independent decoder, layout and VM assertions"
)]
fn canonical_typed_ir_executes_without_caller_supplied_projection() -> Result<(), String> {
    for pairs in [1, 2, 7, 64, 256] {
        let typed = fixture(pairs)?;
        let encoded = wire(&typed)?;
        let restored =
            canonical_module(&encoded).map_err(|error| format!("typed restoration: {error:?}"))?;
        assert_eq!(restored, typed);
        let compiled = compile_canonical_typed_echo(&encoded, current_profile())
            .map_err(|error| format!("typed executable subset: {error:?}"))?;
        let ternary = canonical_ternary_program(compiled.ternary_bytes())
            .map_err(|error| format!("canonical MCTR: {error:?}"))?;
        assert_eq!(ternary.source_id, typed.source_id());
        assert_eq!(ternary.source_sha256, *typed.source_sha256());
        assert_eq!(ternary.functions.len(), 1);
        assert_eq!(
            ternary
                .functions
                .first()
                .map(|function| function.name.as_str()),
            Some("typed_echo")
        );
        assert_eq!(
            compiled.layout().source().len(),
            pairs.saturating_mul(2).saturating_add(1)
        );
        let bytes = [0, 255, 128, 13, 10, 42, 65]
            .into_iter()
            .cycle()
            .take(pairs)
            .collect::<Vec<_>>();
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            compiled.layout().source(),
            bytes.clone(),
        )
        .map_err(|error| format!("VM loader: {error:?}"))?;
        assert!(matches!(
            vm.run(pairs.saturating_mul(2).saturating_add(1)),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), bytes);
        assert_eq!(vm.input_consumed(), pairs);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "fail-closed malformed wire assertions"
)]
fn canonical_typed_echo_rejects_forged_wire_and_profile() -> Result<(), String> {
    let canonical = wire(&fixture(2)?)?;
    let compiled = compile_canonical_typed_echo(&canonical, current_profile())
        .map_err(|error| format!("admitted source: {error:?}"))?;
    assert!(!compiled.ternary_bytes().is_empty());
    for length in [0, 1, 4, canonical.len().saturating_sub(1)] {
        let cut = canonical.get(..length).ok_or("missing canonical prefix")?;
        assert!(matches!(
            compile_canonical_typed_echo(cut, current_profile()),
            Err(TypedEchoAdapterError::InvalidTypedIr(_))
        ));
    }
    let mut appended = canonical.clone();
    appended.push(0);
    assert!(matches!(
        compile_canonical_typed_echo(&appended, current_profile()),
        Err(TypedEchoAdapterError::InvalidTypedIr(_))
    ));
    assert!(matches!(
        compile_canonical_typed_echo(&canonical, historical_profile()),
        Err(TypedEchoAdapterError::Layout(_))
    ));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independently admitted variant rejection"
)]
fn typed_ir_rejects_nonadjacent_byte_dataflow_without_fabricated_projection() -> Result<(), String>
{
    let mut instructions = effects(2)?;
    // Both byte values remain defined; the second output now reuses the first
    // successful byte. This typed program is valid but the exact echo subset
    // cannot silently substitute a different byte for the second read.
    let last = instructions.pop().ok_or("missing second byte output")?;
    instructions.push(LocatedInstruction::new(
        Instruction::ByteOutput {
            value: ValueId::new(0),
        },
        last.span(),
    ));
    let module = fixture_with_instructions(instructions, "fixtures/typed-echo.c")?;
    let encoded = wire(&module)?;
    assert_eq!(
        compile_canonical_typed_echo(&encoded, current_profile()),
        Err(TypedEchoAdapterError::UnsupportedTypedIr),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "unsupported typed computation admission"
)]
fn typed_ir_rejects_valid_non_echo_operation_and_missing_effects() -> Result<(), String> {
    assert_eq!(
        compile_canonical_typed_echo(&wire(&fixture(0)?)?, current_profile()),
        Err(TypedEchoAdapterError::UnsupportedTypedIr),
    );
    let mut instructions = effects(1)?;
    let first = instructions.pop().ok_or("missing output")?;
    instructions.push(LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: adapter::typed::IntegerConstant::new(8, vec![9]),
            result: ValueId::new(1),
            type_id: TypeId::new(0),
        },
        first.span(),
    ));
    instructions.push(first);
    let extra = fixture_with_instructions(instructions, "fixtures/typed-echo.c")?;
    let encoded = wire(&extra)?;
    assert_eq!(
        compile_canonical_typed_echo(&encoded, current_profile()),
        Err(TypedEchoAdapterError::UnsupportedTypedIr),
    );
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "source provenance and SSA tests")]
fn typed_source_provenance_is_not_authenticated_by_reused_source_digest() -> Result<(), String> {
    let original = fixture(1)?;
    let changed = fixture_with_instructions(effects(1)?, "fixtures/other-typed-echo.c")?;
    assert_eq!(original.source_sha256(), changed.source_sha256());
    let compiled_original = compile_canonical_typed_echo(&wire(&original)?, current_profile())
        .map_err(|error| format!("original: {error:?}"))?;
    let compiled_changed = compile_canonical_typed_echo(&wire(&changed)?, current_profile())
        .map_err(|error| format!("changed source: {error:?}"))?;
    assert_ne!(
        compiled_original.ternary_bytes(),
        compiled_changed.ternary_bytes()
    );
    assert_eq!(
        compiled_original.layout().source(),
        compiled_changed.layout().source()
    );
    Ok(())
}

#[expect(
    clippy::too_many_lines,
    reason = "file publication and VM behavior in one proof"
)]
fn real_publisher_matches_direct_typed_ir(pairs: usize, capsule: bool) -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let compiled = compile_canonical_typed_echo(&wire(&self::fixture(pairs)?)?, current_profile())
        .map_err(|error| format!("typed source compile: {error:?}"))?;
    let path = fixture.path("echo.mctr");
    fs::write(&path, compiled.ternary_bytes())
        .map_err(|error| format!("write canonical MCTR: {error}"))?;
    let emitted = fixture.path("echo.malbolge");
    let mut command = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"));
    let _command = command
        .arg("--profile")
        .arg(current_profile().id())
        .arg("--output")
        .arg(&emitted);
    if capsule {
        let _optional_capsule = command.arg("--capsule");
    }
    let result = command
        .arg("--")
        .arg("--ternary-file")
        .arg(&path)
        .output()
        .map_err(|error| format!("launch artifact publisher: {error}"))?;
    if !result.status.success() {
        return Err(format!(
            "publisher failed: {}",
            String::from_utf8_lossy(&result.stderr)
        ));
    }
    let published =
        fs::read(&emitted).map_err(|error| format!("published source read: {error}"))?;
    let content = if capsule {
        let parsed = malbolge::parse_capsule(&published)
            .map_err(|error| format!("parse capsule: {error}"))?
            .ok_or("missing capsule marker")?;
        if parsed.profile() != current_profile() {
            return Err(String::from("capsule profile drift"));
        }
        parsed.payload().to_vec()
    } else {
        published
    };
    if content != compiled.layout().source() {
        return Err(String::from(
            "typed IR adapter differs from published source",
        ));
    }
    let input = [0, 255, 27, 128, 9, 65, 42]
        .into_iter()
        .cycle()
        .take(pairs)
        .collect::<Vec<_>>();
    let mut vm = ProfileMachine::from_source(current_profile(), &content, input.clone())
        .map_err(|error| format!("published VM: {error:?}"))?;
    if !matches!(
        vm.run(pairs.saturating_mul(2).saturating_add(1)),
        Ok(RunOutcome::Terminated { .. })
    ) || vm.input_consumed() != pairs
        || vm.output() != input
    {
        return Err(String::from("published successful-byte VM trace mismatch"));
    }
    Ok(())
}

#[test]
fn canonical_typed_ir_reaches_real_raw_and_capsule_file_publisher() -> Result<(), String> {
    for (pairs, capsule) in [(1, false), (3, true)] {
        real_publisher_matches_direct_typed_ir(pairs, capsule)?;
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "all-byte success and maximum layout proof"
)]
fn canonical_typed_ir_supports_full_byte_domain_and_maximum_trace() -> Result<(), String> {
    for pairs in [256, 2047] {
        let compiled = compile_canonical_typed_echo(&wire(&fixture(pairs)?)?, current_profile())
            .map_err(|error| format!("typed maximum: {error:?}"))?;
        let bytes = (0..=u8::MAX).cycle().take(pairs).collect::<Vec<_>>();
        let steps = pairs.saturating_mul(2).saturating_add(1);
        assert_eq!(compiled.layout().source().len(), steps);
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            compiled.layout().source(),
            bytes.clone(),
        )
        .map_err(|error| format!("VM: {error:?}"))?;
        assert!(matches!(vm.run(steps), Ok(RunOutcome::Terminated { .. })));
        assert_eq!(vm.output(), bytes);
        assert_eq!(vm.input_consumed(), pairs);
    }
    assert_eq!(
        compile_canonical_typed_echo(&wire(&fixture(2048)?)?, current_profile()),
        Err(TypedEchoAdapterError::UnsupportedTypedIr),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "unsupported but admitted reordering"
)]
fn canonical_typed_ir_rejects_valid_interleaved_two_input_trace() -> Result<(), String> {
    let mut instructions = effects(2)?;
    instructions.swap(1, 2);
    let altered = fixture_with_instructions(instructions, "fixtures/typed-echo.c")?;
    let encoded = wire(&altered)?;
    assert_eq!(
        compile_canonical_typed_echo(&encoded, current_profile()),
        Err(TypedEchoAdapterError::UnsupportedTypedIr),
    );
    Ok(())
}

const fn exact_source_span(original: SourceSpan, lowered: TernarySourceSpan) -> bool {
    original.begin().byte() == lowered.begin.byte
        && original.begin().column() == lowered.begin.column
        && original.begin().line() == lowered.begin.line
        && original.end().byte() == lowered.end.byte
        && original.end().column() == lowered.end.column
        && original.end().line() == lowered.end.line
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "checks entire typed-to-ternary provenance"
)]
#[expect(
    clippy::too_many_lines,
    reason = "every source operation and terminator is checked"
)]
fn typed_ir_projection_binds_every_operation_ssa_and_source_span() -> Result<(), String> {
    let module = fixture(7)?;
    let compiled = compile_canonical_typed_echo(&wire(&module)?, current_profile())
        .map_err(|error| format!("compile: {error:?}"))?;
    let lowered = canonical_ternary_program(compiled.ternary_bytes())
        .map_err(|error| format!("decode MCTR: {error:?}"))?;
    let [typed_function] = module.functions() else {
        return Err(String::from("missing source function"));
    };
    let [typed_block] = typed_function.blocks() else {
        return Err(String::from("missing source block"));
    };
    let [ternary_function] = lowered.functions.as_slice() else {
        return Err(String::from("missing ternary function"));
    };
    let Some((TernaryOperation::ReturnVoid { span: return_span }, target_ops)) =
        ternary_function.operations.split_last()
    else {
        return Err(String::from("missing void terminator"));
    };
    assert_eq!(typed_function.id().value(), ternary_function.id);
    assert_eq!(typed_function.name(), ternary_function.name);
    assert!(exact_source_span(
        typed_function.span(),
        ternary_function.span
    ));
    assert!(exact_source_span(
        typed_block.terminator_span(),
        *return_span
    ));
    let (source_pairs, source_tail) = typed_block.instructions().as_chunks::<2>();
    let (target_pairs, target_tail) = target_ops.as_chunks::<2>();
    assert!(source_tail.is_empty() && target_tail.is_empty());
    assert_eq!(source_pairs.len(), target_pairs.len());
    for (source, target) in source_pairs.iter().zip(target_pairs) {
        let [typed_read, typed_write] = source;
        let [
            TernaryOperation::ByteInput {
                result,
                span: read_span,
            },
            TernaryOperation::ByteOutput {
                value,
                span: write_span,
            },
        ] = target
        else {
            return Err(String::from("wrong lowered effect family"));
        };
        let Instruction::ByteInput {
            result: typed_result,
            ..
        } = typed_read.instruction()
        else {
            return Err(String::from("wrong source read family"));
        };
        let Instruction::ByteOutput { value: typed_value } = typed_write.instruction() else {
            return Err(String::from("wrong source write family"));
        };
        assert_eq!(*result, typed_result.value());
        assert_eq!(*value, typed_value.value());
        assert!(exact_source_span(typed_read.span(), *read_span));
        assert!(exact_source_span(typed_write.span(), *write_span));
    }
    Ok(())
}

fn latest_typed_fixture(steps: &[(bool, u32)]) -> Result<Module, String> {
    latest_typed_fixture_for_profile(steps, current_profile().id())
}

fn latest_typed_fixture_for_profile(
    steps: &[(bool, u32)],
    profile_id: &str,
) -> Result<Module, String> {
    let mut instructions = Vec::with_capacity(steps.len());
    for (index, (read, value)) in steps.iter().enumerate() {
        let begin = u32::try_from(index).map_err(|error| format!("source offset: {error}"))?;
        let instruction = if *read {
            Instruction::ByteInput {
                result: ValueId::new(*value),
                type_id: TypeId::new(0),
            }
        } else {
            Instruction::ByteOutput {
                value: ValueId::new(*value),
            }
        };
        instructions.push(LocatedInstruction::new(
            instruction,
            span(begin, begin.saturating_add(1)),
        ));
    }
    fixture_with_profile(instructions, "fixtures/typed-echo.c", profile_id)
}

fn verify_latest_typed_execution(
    steps: &[(bool, u32)],
    input: &[u8],
    expected: &[u8],
) -> Result<(), String> {
    let original = latest_typed_fixture(steps)?;
    let compiled =
        adapter::compile_canonical_typed_latest_byte_trace(&wire(&original)?, current_profile())
            .map_err(|error| format!("typed latest-read compile: {error:?}"))?;
    let decoded = canonical_ternary_program(compiled.ternary_bytes())
        .map_err(|error| format!("ternary restoration: {error:?}"))?;
    if decoded.source_id != original.source_id()
        || decoded.source_sha256 != *original.source_sha256()
        || compiled.layout().source().len() != steps.len().saturating_add(1)
        || decoded
            .functions
            .first()
            .is_none_or(|function| function.operations.len() != steps.len().saturating_add(1))
    {
        return Err(String::from("typed latest-read stage provenance mismatch"));
    }
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        compiled.layout().source(),
        input.to_vec(),
    )
    .map_err(|error| format!("latest-read real VM load: {error:?}"))?;
    let execution_steps = steps.len().saturating_add(1);
    if !matches!(vm.run(execution_steps),
        Ok(RunOutcome::Terminated { steps: executed, .. }) if executed == execution_steps)
        || vm.input_consumed() != input.len()
        || vm.output() != expected
    {
        return Err(String::from(
            "typed latest-read VM output or consumption mismatch",
        ));
    }
    Ok(())
}

#[test]
fn canonical_typed_latest_byte_trace_executes_mixed_uses() -> Result<(), String> {
    verify_latest_typed_execution(&[(true, 0)], &[0], &[])?;
    verify_latest_typed_execution(
        &[
            (true, 0),
            (false, 0),
            (false, 0),
            (true, 1),
            (false, 1),
            (false, 1),
        ],
        &[0, 255],
        &[0, 0, 255, 255],
    )?;
    verify_latest_typed_execution(
        &[(true, 0), (true, 1), (false, 1), (true, 2), (false, 2)],
        &[13, 128, 42],
        &[128, 42],
    )?;
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "legacy echo and new semantic boundary"
)]
fn canonical_typed_latest_byte_trace_keeps_strict_echo_distinct() -> Result<(), String> {
    let steps = [(true, 0), (false, 0), (false, 0)];
    let canonical = wire(&latest_typed_fixture(&steps)?)?;
    let compiled =
        adapter::compile_canonical_typed_latest_byte_trace(&canonical, current_profile())
            .map_err(|error| format!("repeat-byte compile: {error:?}"))?;
    assert_eq!(compiled.layout().source().len(), 4);
    assert_eq!(
        compile_canonical_typed_echo(&canonical, current_profile()),
        Err(TypedEchoAdapterError::UnsupportedTypedIr),
    );
    let traditional = wire(&fixture(7)?)?;
    let older = compile_canonical_typed_echo(&traditional, current_profile())
        .map_err(|error| format!("strict old echo: {error:?}"))?;
    let newer = adapter::compile_canonical_typed_latest_byte_trace(&traditional, current_profile())
        .map_err(|error| format!("latest-read ordinary echo: {error:?}"))?;
    assert_eq!(older, newer);
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "stale SSA and profile forgeries")]
fn canonical_typed_latest_byte_trace_rejects_stale_ssa_and_wrong_profile() -> Result<(), String> {
    let valid_typed = latest_typed_fixture(&[(true, 0), (true, 1), (false, 0)])?;
    let encoded = wire(&valid_typed)?;
    assert_eq!(
        adapter::compile_canonical_typed_latest_byte_trace(&encoded, current_profile()),
        Err(TypedEchoAdapterError::UnsupportedTypedIr),
    );
    let source = wire(&latest_typed_fixture(&[(true, 0), (false, 0)])?)?;
    assert!(matches!(
        adapter::compile_canonical_typed_latest_byte_trace(&source, historical_profile()),
        Err(TypedEchoAdapterError::Layout(_)),
    ));
    assert!(matches!(
        adapter::compile_canonical_typed_latest_byte_trace(
            source.get(..1).ok_or("missing prefix")?,
            current_profile()
        ),
        Err(TypedEchoAdapterError::InvalidTypedIr(_)),
    ));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "maximum real guest trace boundary"
)]
fn canonical_typed_latest_byte_trace_reaches_4096_cells_and_rejects_4097() -> Result<(), String> {
    let mut steps = Vec::with_capacity(4096);
    steps.push((true, 0));
    steps.extend(repeat_n((false, 0), 4094));
    let original = latest_typed_fixture(&steps)?;
    let compiled =
        adapter::compile_canonical_typed_latest_byte_trace(&wire(&original)?, current_profile())
            .map_err(|error| format!("maximum typed trace: {error:?}"))?;
    assert_eq!(compiled.layout().source().len(), 4096);
    let mut vm =
        ProfileMachine::from_source(current_profile(), compiled.layout().source(), vec![255])
            .map_err(|error| format!("maximum real VM load: {error:?}"))?;
    assert!(matches!(
        vm.run(4096),
        Ok(RunOutcome::Terminated { steps: 4096, .. })
    ));
    assert_eq!(vm.input_consumed(), 1);
    assert_eq!(vm.output(), vec![255; 4094]);
    steps.push((false, 0));
    assert_eq!(
        adapter::compile_canonical_typed_latest_byte_trace(
            &wire(&latest_typed_fixture(&steps)?)?,
            current_profile(),
        ),
        Err(TypedEchoAdapterError::UnsupportedTypedIr),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "canonical typed-to-MCTR-to-file-to-VM evidence shares one fixture"
)]
fn canonical_typed_latest_byte_trace_publishes_independent_capsule() -> Result<(), String> {
    let steps = [
        (true, 0),
        (false, 0),
        (false, 0),
        (true, 1), // successful byte consumed but not output
        (true, 2),
        (false, 2),
    ];
    let canonical = wire(&latest_typed_fixture(&steps)?)?;
    let compiled =
        adapter::compile_canonical_typed_latest_byte_trace(&canonical, current_profile())
            .map_err(|error| format!("canonical typed trace: {error:?}"))?;
    let fixture = OwnedFixture::new()?;
    let mctr = fixture.path("typed-latest.mctr");
    fs::write(&mctr, compiled.ternary_bytes())
        .map_err(|error| format!("write admitted MCTR: {error}"))?;
    let refused_path = fixture.path("strict-reject.malbolge");
    let refused = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
        .arg("--profile")
        .arg(current_profile().id())
        .arg("--output")
        .arg(&refused_path)
        .arg("--")
        .arg("--ternary-file")
        .arg(&mctr)
        .output()
        .map_err(|error| format!("strict publisher launch: {error}"))?;
    if refused.status.success() || refused_path.exists() {
        return Err(String::from(
            "strict adjacent publisher accepted nonadjacent typed trace",
        ));
    }

    let target = fixture.path("typed-latest.malbolge");
    let result = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
        .arg("--profile")
        .arg(current_profile().id())
        .arg("--output")
        .arg(&target)
        .arg("--capsule")
        .arg("--")
        .arg("--latest-byte-trace")
        .arg("--ternary-file")
        .arg(&mctr)
        .output()
        .map_err(|error| format!("opt-in publisher launch: {error}"))?;
    if !result.status.success() {
        return Err(format!(
            "latest typed trace publication failed: {}",
            String::from_utf8_lossy(&result.stderr)
        ));
    }
    let bytes = fs::read(&target).map_err(|error| format!("published capsule: {error}"))?;
    let capsule = malbolge::parse_capsule(&bytes)
        .map_err(|error| format!("independent capsule parser: {error}"))?
        .ok_or("typed trace capsule framing absent")?;
    if capsule.profile() != current_profile() || capsule.payload() != compiled.layout().source() {
        return Err(String::from("published typed source or profile drift"));
    }
    let mut vm =
        ProfileMachine::from_source(capsule.profile(), capsule.payload(), vec![0, 255, 128])
            .map_err(|error| format!("published typed VM load: {error:?}"))?;
    if !matches!(
        vm.run(steps.len().saturating_add(1)),
        Ok(RunOutcome::Terminated { steps: 7, .. })
    ) || vm.input_consumed() != 3
        || vm.output() != [0, 0, 128]
    {
        return Err(String::from(
            "published typed latest-byte effect trace mismatch",
        ));
    }
    Ok(())
}

#[expect(
    clippy::too_many_arguments,
    reason = "independent publisher invocation preserves the mode matrix"
)]
fn publish_typed_wire(
    profile: &str,
    source: &Path,
    target: &Path,
    latest: bool,
    capsule: bool,
) -> Result<Output, String> {
    let mut command = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"));
    let _profile_arguments = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    let _delimiter = command.arg("--");
    if latest {
        let _latest = command.arg("--latest-byte-trace");
    }
    command
        .arg("--typed-file")
        .arg(source)
        .output()
        .map_err(|error| format!("typed CLI spawn: {error}"))
}

#[expect(
    clippy::too_many_arguments,
    reason = "independent publisher invocation preserves the mode matrix"
)]
fn publish_ternary_wire(
    profile: &str,
    source: &Path,
    target: &Path,
    latest: bool,
    capsule: bool,
) -> Result<Output, String> {
    let mut command = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"));
    let _profile_arguments = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    let _delimiter = command.arg("--");
    if latest {
        let _latest = command.arg("--latest-byte-trace");
    }
    command
        .arg("--ternary-file")
        .arg(source)
        .output()
        .map_err(|error| format!("ternary CLI spawn: {error}"))
}

#[expect(
    clippy::cognitive_complexity,
    reason = "two format variants and independent baseline are checked together"
)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "external canonical typed producer is checked against the independent MCTR route"
)]
fn canonical_typed_file_publisher_matches_independent_ternary_file() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let canonical = wire(&fixture(3)?)?;
    let compiled = compile_canonical_typed_echo(&canonical, current_profile())
        .map_err(|error| format!("strict typed compiler: {error:?}"))?;
    let typed = workspace.path("source.mcti");
    let ternary = workspace.path("source.mctr");
    fs::write(&typed, canonical).map_err(|error| error.to_string())?;
    fs::write(&ternary, compiled.ternary_bytes()).map_err(|error| error.to_string())?;
    for capsule in [false, true] {
        let typed_output = workspace.path(if capsule {
            "typed-cap.malbolge"
        } else {
            "typed-raw.malbolge"
        });
        let ternary_output = workspace.path(if capsule {
            "ternary-cap.malbolge"
        } else {
            "ternary-raw.malbolge"
        });
        let produced = publish_typed_wire(
            current_profile().id(),
            &typed,
            &typed_output,
            false,
            capsule,
        )?;
        let baseline = publish_ternary_wire(
            current_profile().id(),
            &ternary,
            &ternary_output,
            false,
            capsule,
        )?;
        assert!(
            produced.status.success(),
            "{}",
            String::from_utf8_lossy(&produced.stderr)
        );
        assert!(
            baseline.status.success(),
            "{}",
            String::from_utf8_lossy(&baseline.stderr)
        );
        let actual = fs::read(&typed_output).map_err(|error| error.to_string())?;
        assert_eq!(
            actual,
            fs::read(ternary_output).map_err(|error| error.to_string())?
        );
        if capsule {
            let frame = malbolge::parse_capsule(&actual)
                .map_err(|error| format!("typed capsule parse: {error}"))?
                .ok_or("typed publisher capsule missing")?;
            assert_eq!(frame.profile(), current_profile());
            assert_eq!(frame.payload(), compiled.layout().source());
        } else {
            assert_eq!(actual, compiled.layout().source());
        }
    }
    Ok(())
}

#[expect(
    clippy::cognitive_complexity,
    reason = "strict reject plus two file forms plus normative VM"
)]
#[expect(
    clippy::too_many_lines,
    reason = "full canonical MCTI to MCTR to real VM file verification"
)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "latest typed output is checked against an independently decoded MCTR and real VM"
)]
fn canonical_typed_latest_file_publishes_exact_executable_capsule() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let steps = [
        (true, 0),
        (false, 0),
        (false, 0),
        (true, 1),
        (true, 2),
        (false, 2),
        (false, 2),
    ];
    let typed_bytes = wire(&latest_typed_fixture(&steps)?)?;
    let compiled =
        adapter::compile_canonical_typed_latest_byte_trace(&typed_bytes, current_profile())
            .map_err(|error| format!("latest typed compiler: {error:?}"))?;
    let typed = workspace.path("latest.mcti");
    let ternary = workspace.path("latest.mctr");
    fs::write(&typed, typed_bytes).map_err(|error| error.to_string())?;
    fs::write(&ternary, compiled.ternary_bytes()).map_err(|error| error.to_string())?;
    let strict_target = workspace.path("strict-reject.malbolge");
    let refused = publish_typed_wire(current_profile().id(), &typed, &strict_target, false, true)?;
    assert!(!refused.status.success());
    assert!(!strict_target.exists());
    for capsule in [false, true] {
        let target = workspace.path(if capsule {
            "latest-cap.malbolge"
        } else {
            "latest-raw.malbolge"
        });
        let baseline_target = workspace.path(if capsule {
            "latest-mctr-cap.malbolge"
        } else {
            "latest-mctr-raw.malbolge"
        });
        let typed_result =
            publish_typed_wire(current_profile().id(), &typed, &target, true, capsule)?;
        let ternary_result = publish_ternary_wire(
            current_profile().id(),
            &ternary,
            &baseline_target,
            true,
            capsule,
        )?;
        assert!(
            typed_result.status.success(),
            "{}",
            String::from_utf8_lossy(&typed_result.stderr)
        );
        assert!(
            ternary_result.status.success(),
            "{}",
            String::from_utf8_lossy(&ternary_result.stderr)
        );
        let output = fs::read(target).map_err(|error| error.to_string())?;
        assert_eq!(
            output,
            fs::read(baseline_target).map_err(|error| error.to_string())?
        );
        let raw = if capsule {
            let frame = malbolge::parse_capsule(&output)
                .map_err(|error| format!("latest capsule parse: {error}"))?
                .ok_or("missing latest typed capsule")?;
            assert_eq!(frame.profile(), current_profile());
            frame.payload().to_vec()
        } else {
            output
        };
        assert_eq!(raw, compiled.layout().source());
        let mut vm = ProfileMachine::from_source(current_profile(), &raw, vec![0, 255, 128])
            .map_err(|error| format!("published latest VM load: {error:?}"))?;
        assert!(matches!(
            vm.run(8),
            Ok(RunOutcome::Terminated { steps: 8, .. })
        ));
        assert_eq!(vm.input_consumed(), 3);
        assert_eq!(vm.output(), &[0, 0, 128, 128]);
    }
    Ok(())
}

#[expect(
    clippy::cognitive_complexity,
    reason = "all malformed paths must avoid final output"
)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "all typed file failures must retain original output and refuse unauthorized input"
)]
fn canonical_typed_file_cli_rejects_stale_ssa_corrupt_wire_profile_and_oversize()
-> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let valid = wire(&fixture(1)?)?;
    let typed = workspace.path("hostile.mcti");
    let target = workspace.path("refused.malbolge");
    fs::write(&typed, &valid).map_err(|error| error.to_string())?;
    let wrong_profile =
        publish_typed_wire(historical_profile().id(), &typed, &target, false, false)?;
    assert!(!wrong_profile.status.success());
    assert!(!target.exists());
    fs::write(&typed, valid.get(..1).ok_or("missing malformed prefix")?)
        .map_err(|error| error.to_string())?;
    let malformed = publish_typed_wire(current_profile().id(), &typed, &target, false, false)?;
    assert!(!malformed.status.success());
    assert!(!target.exists());
    let stale = wire(&latest_typed_fixture(&[(true, 0), (true, 1), (false, 0)])?)?;
    fs::write(&typed, stale).map_err(|error| error.to_string())?;
    let unsupported = publish_typed_wire(current_profile().id(), &typed, &target, true, false)?;
    assert!(!unsupported.status.success());
    assert!(!target.exists());
    fs::write(&typed, vec![0x42; 1_048_577]).map_err(|error| error.to_string())?;
    let oversized = publish_typed_wire(current_profile().id(), &typed, &target, false, true)?;
    assert!(!oversized.status.success());
    assert!(!target.exists());
    fs::write(&typed, valid).map_err(|error| error.to_string())?;
    let sentinel = b"existing raw output must not change";
    fs::write(&target, sentinel).map_err(|error| error.to_string())?;
    let collision = publish_typed_wire(current_profile().id(), &typed, &target, false, true)?;
    assert!(!collision.status.success());
    assert_eq!(
        fs::read(target).map_err(|error| error.to_string())?,
        sentinel
    );
    Ok(())
}

#[test]
fn canonical_typed_latest_file_runs_real_general_cli_with_successful_binary_stdin()
-> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let steps = [
        (true, 0),
        (false, 0),
        (false, 0),
        (true, 1),
        (true, 2),
        (false, 2),
        (false, 2),
    ];
    let canonical = wire(&latest_typed_fixture(&steps)?)?;
    let source = workspace.path("process-input.mcti");
    let artifact = workspace.path("process-output.malbolge");
    fs::write(&source, canonical).map_err(|error| error.to_string())?;
    let published = publish_typed_wire(current_profile().id(), &source, &artifact, true, true)?;
    if !published.status.success() {
        return Err(format!(
            "canonical typed-to-capsule publisher failed: {}",
            String::from_utf8_lossy(&published.stderr)
        ));
    }
    let bytes = fs::read(&artifact).map_err(|error| error.to_string())?;
    let restored = malbolge::parse_capsule(&bytes)
        .map_err(|error| format!("independent capsule read: {error}"))?
        .ok_or("missing directly published typed capsule")?;
    if restored.profile() != current_profile() || restored.payload().len() != 8 {
        return Err(String::from(
            "direct typed process target identity or size drift",
        ));
    }
    let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&artifact)
        .arg("--input-stdin")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("real guest CLI launch: {error}"))?;
    let mut stdin = child.stdin.take().ok_or("guest CLI has no input pipe")?;
    stdin
        .write_all(&[0, 255, 128])
        .map_err(|error| format!("binary guest input: {error}"))?;
    drop(stdin);
    let observed = child
        .wait_with_output()
        .map_err(|error| format!("read guest process result: {error}"))?;
    if !observed.status.success()
        || observed.stdout != [0, 0, 128, 128]
        || !observed.stderr.is_empty()
    {
        return Err(format!("real guest typed execution mismatch: {observed:?}"));
    }
    Ok(())
}

#[test]
fn canonical_typed_file_mode_requires_exact_explicit_grammar() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let source = workspace.path("valid.mcti");
    let target = workspace.path("grammar-refused.malbolge");
    fs::write(&source, wire(&fixture(1)?)?).map_err(|error| error.to_string())?;
    for tokens in [
        vec!["--typed-file"],
        vec!["--latest-byte-trace", "--typed-file"],
        vec!["--latest-byte-trace", "--auto-layout", "input", "halt"],
        vec!["--latest-byte-trace", "--typed-file", "missing.mcti", "nop"],
        vec!["--typed-file", "missing.mcti", "--latest-byte-trace"],
    ] {
        let result = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
            .arg("--profile")
            .arg(current_profile().id())
            .arg("--output")
            .arg(&target)
            .arg("--")
            .args(tokens)
            .output()
            .map_err(|error| format!("typed grammar invocation: {error}"))?;
        if result.status.success() || target.exists() {
            return Err(String::from("invalid typed mode grammar published source"));
        }
    }
    let rejected_extra = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
        .arg("--profile")
        .arg(current_profile().id())
        .arg("--output")
        .arg(&target)
        .arg("--")
        .arg("--typed-file")
        .arg(&source)
        .arg("nop")
        .output()
        .map_err(|error| format!("typed trailing token: {error}"))?;
    if rejected_extra.status.success() || target.exists() {
        return Err(String::from("typed file accepted a trailing machine token"));
    }
    Ok(())
}

#[expect(
    clippy::too_many_lines,
    reason = "each profile requires an independently serialized target, VM and external runner"
)]
fn verify_profile_bound_typed_capsule(
    workspace: &OwnedFixture,
    profile_id: &str,
    latest: bool,
) -> Result<(), String> {
    let profile = target_profile(profile_id)
        .ok_or_else(|| format!("missing registered profile {profile_id}"))?;
    let (module, input, expected, consumed, steps) = if latest {
        (
            latest_typed_fixture_for_profile(
                &[
                    (true, 0),
                    (false, 0),
                    (false, 0),
                    (true, 1),
                    (true, 2),
                    (false, 2),
                ],
                profile_id,
            )?,
            vec![0, 255, 128],
            vec![0, 0, 128],
            3,
            7,
        )
    } else {
        (
            fixture_with_profile(effects(2)?, "fixtures/typed-echo.c", profile_id)?,
            vec![0, 255],
            vec![0, 255],
            2,
            5,
        )
    };
    let canonical = wire(&module)?;
    let compiled = if latest {
        adapter::compile_canonical_typed_latest_byte_trace(&canonical, profile)
    } else {
        compile_canonical_typed_echo(&canonical, profile)
    }
    .map_err(|error| format!("{profile_id} typed lowering: {error:?}"))?;
    let restored = canonical_ternary_program(compiled.ternary_bytes())
        .map_err(|error| format!("{profile_id} canonical MCTR restoration: {error:?}"))?;
    if restored.target_profile != profile_id
        || restored.source_id != module.source_id()
        || restored.source_sha256 != *module.source_sha256()
        || compiled.layout().profile_id() != profile_id
        || compiled.layout().profile_fingerprint() != profile.fingerprint()
    {
        return Err(format!("{profile_id} stage provenance drift"));
    }
    let typed_path = workspace.path(&format!("{profile_id}-{latest}.mcti"));
    let capsule_path = workspace.path(&format!("{profile_id}-{latest}.malbolge"));
    fs::write(&typed_path, canonical).map_err(|error| error.to_string())?;
    let published = publish_typed_wire(profile_id, &typed_path, &capsule_path, latest, true)?;
    if !published.status.success() {
        return Err(format!(
            "{profile_id} typed publication: {}",
            String::from_utf8_lossy(&published.stderr)
        ));
    }
    let output = fs::read(&capsule_path).map_err(|error| error.to_string())?;
    let capsule = malbolge::parse_capsule(&output)
        .map_err(|error| format!("{profile_id} independent capsule parse: {error}"))?
        .ok_or("missing profile capsule from typed publisher")?;
    if capsule.profile().id() != profile_id
        || capsule.profile().fingerprint() != profile.fingerprint()
        || capsule.payload() != compiled.layout().source()
    {
        return Err(format!("{profile_id} capsule identity or source mismatch"));
    }
    let mut vm = ProfileMachine::from_source(profile, capsule.payload(), input.clone())
        .map_err(|error| format!("{profile_id} normative VM load: {error:?}"))?;
    if !matches!(vm.run(steps),
        Ok(RunOutcome::Terminated { steps: executed, .. }) if executed == steps)
        || vm.input_consumed() != consumed
        || vm.output() != expected
    {
        return Err(format!("{profile_id} normative typed VM result mismatch"));
    }
    let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&capsule_path)
        .arg("--input-stdin")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("{profile_id} actual guest runner: {error}"))?;
    let mut stdin = child.stdin.take().ok_or("missing guest stdin")?;
    stdin
        .write_all(&input)
        .map_err(|error| format!("{profile_id} guest binary input: {error}"))?;
    drop(stdin);
    let observed = child
        .wait_with_output()
        .map_err(|error| format!("{profile_id} general runner result: {error}"))?;
    if !observed.status.success() || observed.stdout != expected || !observed.stderr.is_empty() {
        return Err(format!(
            "{profile_id} actual guest output differs: {observed:?}"
        ));
    }
    Ok(())
}

#[test]
fn canonical_typed_file_profile_admission_is_fixed_to_v1_current_contract() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let current = current_profile().id();
    verify_profile_bound_typed_capsule(&workspace, current, false)?;
    verify_profile_bound_typed_capsule(&workspace, current, true)?;
    let valid_current = wire(&fixture(1)?)?;
    let wire_path = workspace.path("only-current.mcti");
    fs::write(&wire_path, valid_current).map_err(|error| error.to_string())?;
    for profile_id in [
        "malbolge-1998",
        "malbolge-2026.1",
        "malbolge-2026.2",
        "malbolge-2026.3",
    ] {
        let invalid_source =
            fixture_with_profile(effects(1)?, "fixtures/typed-echo.c", profile_id)?;
        if validate_module(&invalid_source) != Err(adapter::typed::ValidationError::ProfileIdentity)
        {
            return Err(format!("typed v1 source unexpectedly admits {profile_id}"));
        }
        let profile = target_profile(profile_id)
            .ok_or_else(|| format!("missing registered profile {profile_id}"))?;
        if compile_canonical_typed_echo(
            &fs::read(&wire_path).map_err(|error| error.to_string())?,
            profile,
        ) != Err(TypedEchoAdapterError::Layout(
            adapter::bridge::ByteEchoBridgeError::ProfileMismatch,
        )) {
            return Err(format!(
                "typed v1 source incorrectly lowered for {profile_id}"
            ));
        }
        let target = workspace.path(&format!("{profile_id}-forbidden.malbolge"));
        let rejected = publish_typed_wire(profile_id, &wire_path, &target, false, true)?;
        if rejected.status.success() || target.exists() {
            return Err(format!(
                "typed v1 file published wrong profile {profile_id}"
            ));
        }
    }
    Ok(())
}

#[test]
fn canonical_typed_profile_mismatch_precedes_unsupported_effect_projection() -> Result<(), String> {
    let canonical = wire(&latest_typed_fixture(&[(true, 0), (true, 1), (false, 0)])?)?;
    if adapter::compile_canonical_typed_latest_byte_trace(&canonical, current_profile())
        != Err(TypedEchoAdapterError::UnsupportedTypedIr)
    {
        return Err(String::from(
            "unsupported stale SSA accepted on matching profile",
        ));
    }
    if adapter::compile_canonical_typed_latest_byte_trace(
        &canonical,
        target_profile("malbolge-2026.1").ok_or("unregistered .1")?,
    ) != Err(TypedEchoAdapterError::Layout(
        adapter::bridge::ByteEchoBridgeError::ProfileMismatch,
    )) {
        return Err(String::from(
            "profile drift did not reject before SSA lowering",
        ));
    }
    Ok(())
}

#[test]
fn canonical_typed_file_latest_read_publishes_exact_4096_cell_limit() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let mut steps = Vec::with_capacity(4096);
    steps.push((true, 0));
    steps.extend(repeat_n((false, 0), 4094));
    let canonical = wire(&latest_typed_fixture(&steps)?)?;
    if canonical.len() > 1_048_576 {
        return Err(String::from(
            "maximum typed trace exceeds file admission limit",
        ));
    }
    let wire_path = workspace.path("maximum-admitted.mcti");
    fs::write(&wire_path, canonical).map_err(|error| error.to_string())?;
    let target = workspace.path("exact-4096.malbolge");
    let published = publish_typed_wire(current_profile().id(), &wire_path, &target, true, false)?;
    if !published.status.success() {
        return Err(format!(
            "maximum canonical typed source refused: {}",
            String::from_utf8_lossy(&published.stderr)
        ));
    }
    let source = fs::read(&target).map_err(|error| error.to_string())?;
    if source.len() != 4096 {
        return Err(format!(
            "expected 4096 guest cells, received {}",
            source.len()
        ));
    }
    let mut vm = ProfileMachine::from_source(current_profile(), &source, vec![255])
        .map_err(|error| format!("maximum published VM load: {error:?}"))?;
    if !matches!(vm.run(4096), Ok(RunOutcome::Terminated { steps: 4096, .. }))
        || vm.input_consumed() != 1
        || vm.output().len() != 4094
        || vm.output().iter().any(|byte| *byte != 255)
    {
        return Err(String::from(
            "maximum published guest trace did not execute",
        ));
    }
    steps.push((false, 0));
    let excessive = workspace.path("overflow.mcti");
    fs::write(&excessive, wire(&latest_typed_fixture(&steps)?)?)
        .map_err(|error| error.to_string())?;
    let forbidden = workspace.path("overflow.malbolge");
    let rejected = publish_typed_wire(current_profile().id(), &excessive, &forbidden, true, false)?;
    if rejected.status.success() || forbidden.exists() {
        return Err(String::from(
            "4097-cell trace bypassed bounded source admission",
        ));
    }
    Ok(())
}

#[cfg(unix)]
#[test]
fn canonical_wire_file_modes_reject_fifos_without_waiting_for_a_writer() -> Result<(), String> {
    use std::os::unix::fs::symlink;
    use std::thread;
    use std::time::{Duration, Instant};

    let workspace = OwnedFixture::new()?;
    let pipe = workspace.path("unreadable.fifo");
    let link = workspace.path("fifo-link.mcti");
    let created = Command::new("mkfifo")
        .arg(&pipe)
        .status()
        .map_err(|error| format!("create FIFO fixture: {error}"))?;
    if !created.success() {
        return Err(String::from("mkfifo fixture refused"));
    }
    symlink(&pipe, &link).map_err(|error| format!("FIFO symlink: {error}"))?;
    for (index, (mode, path)) in [
        ("--typed-file", &pipe),
        ("--ternary-file", &pipe),
        ("--typed-file", &link),
        ("--ternary-file", &link),
    ]
    .into_iter()
    .enumerate()
    {
        let target = workspace.path(&format!("refused-{index}.malbolge"));
        let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
            .arg("--profile")
            .arg(current_profile().id())
            .arg("--output")
            .arg(&target)
            .arg("--")
            .arg(mode)
            .arg(path)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|error| format!("FIFO publisher spawn: {error}"))?;
        let started = Instant::now();
        let result = loop {
            if let Some(outcome) = child
                .try_wait()
                .map_err(|error| format!("FIFO publisher poll: {error}"))?
            {
                break outcome;
            }
            if started.elapsed() > Duration::from_secs(3) {
                drop(child.kill());
                drop(child.wait());
                return Err(format!("{mode} blocked trying to open a FIFO input"));
            }
            thread::sleep(Duration::from_millis(10));
        };
        if result.success() || target.exists() {
            return Err(format!("{mode} accepted non-regular FIFO source"));
        }
    }
    Ok(())
}

#[cfg(unix)]
#[test]
fn canonical_typed_file_retains_regular_symlink_input_compatibility() -> Result<(), String> {
    use std::os::unix::fs::symlink;

    let workspace = OwnedFixture::new()?;
    let source = workspace.path("original.mcti");
    let link = workspace.path("source-link.mcti");
    let artifact = workspace.path("linked-source.malbolge");
    fs::write(&source, wire(&fixture(1)?)?).map_err(|error| error.to_string())?;
    symlink(&source, &link).map_err(|error| format!("regular input link: {error}"))?;
    let result = publish_typed_wire(current_profile().id(), &link, &artifact, false, false)?;
    if !result.status.success() {
        return Err(format!(
            "regular linked MCTI was rejected: {}",
            String::from_utf8_lossy(&result.stderr)
        ));
    }
    let source_bytes = fs::read(&artifact).map_err(|error| error.to_string())?;
    let mut vm = ProfileMachine::from_source(current_profile(), &source_bytes, vec![255])
        .map_err(|error| format!("linked canonical input VM: {error:?}"))?;
    if !matches!(vm.run(3), Ok(RunOutcome::Terminated { steps: 3, .. }))
        || vm.output() != [255]
        || vm.input_consumed() != 1
    {
        return Err(String::from("linked typed input changed guest semantics"));
    }
    Ok(())
}

#[expect(
    clippy::too_many_arguments,
    reason = "canonical stdin runner independently selects wire, mode and output framing"
)]
fn publish_canonical_stdin(
    profile: &str,
    canonical: &[u8],
    target: &Path,
    typed: bool,
    latest: bool,
    capsule: bool,
) -> Result<Output, String> {
    let mut command = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"));
    let _profile = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    let _separator = command.arg("--");
    if latest {
        let _latest = command.arg("--latest-byte-trace");
    }
    let _mode = command.arg(if typed {
        "--typed-stdin"
    } else {
        "--ternary-stdin"
    });
    let mut child = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("canonical stdin publication spawn: {error}"))?;
    child
        .stdin
        .take()
        .ok_or("canonical stdin pipe unavailable")?
        .write_all(canonical)
        .map_err(|error| format!("canonical stdin feed: {error}"))?;
    child
        .wait_with_output()
        .map_err(|error| format!("canonical stdin publication completion: {error}"))
}

fn restored_canonical_stdin_source(published: Vec<u8>, capsule: bool) -> Result<Vec<u8>, String> {
    if !capsule {
        return Ok(published);
    }
    let parsed = malbolge::parse_capsule(&published)
        .map_err(|error| format!("canonical stdin capsule: {error}"))?
        .ok_or("canonical stdin capsule marker absent")?;
    if parsed.profile() != current_profile() {
        return Err(String::from("canonical stdin capsule profile drift"));
    }
    Ok(parsed.payload().to_vec())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "the real file and stdin publishers must agree in both byte-flow sublanguages"
)]
#[expect(
    clippy::too_many_lines,
    reason = "integration matrix exercises both IR formats and publication framings"
)]
fn canonical_stdin_pub_matches_file_artefacts_in_both_byte_trace_modes() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for (latest, typed_module) in [
        (false, fixture(2)?),
        (
            true,
            latest_typed_fixture(&[
                (true, 0),
                (false, 0),
                (false, 0),
                (true, 1),
                (true, 2),
                (false, 2),
            ])?,
        ),
    ] {
        let typed_wire = wire(&typed_module)?;
        let compiled = if latest {
            adapter::compile_canonical_typed_latest_byte_trace(&typed_wire, current_profile())
        } else {
            compile_canonical_typed_echo(&typed_wire, current_profile())
        }
        .map_err(|error| format!("canonical byte-trace lowering: {error:?}"))?;
        let typed_path = workspace.path(&format!("typed-{latest}.mcti"));
        let ternary_path = workspace.path(&format!("ternary-{latest}.mctr"));
        fs::write(&typed_path, &typed_wire).map_err(|error| error.to_string())?;
        fs::write(&ternary_path, compiled.ternary_bytes()).map_err(|error| error.to_string())?;
        for typed in [true, false] {
            let capsule = latest;
            let kind = if typed { "typed" } else { "ternary" };
            let published_path = workspace.path(&format!("stdin-{kind}-{latest}.malbolge"));
            let baseline_path = workspace.path(&format!("file-{kind}-{latest}.malbolge"));
            let bytes = if typed {
                &typed_wire
            } else {
                compiled.ternary_bytes()
            };
            let from_stdin = publish_canonical_stdin(
                current_profile().id(),
                bytes,
                &published_path,
                typed,
                latest,
                capsule,
            )?;
            let from_file = if typed {
                publish_typed_wire(
                    current_profile().id(),
                    &typed_path,
                    &baseline_path,
                    latest,
                    capsule,
                )?
            } else {
                publish_ternary_wire(
                    current_profile().id(),
                    &ternary_path,
                    &baseline_path,
                    latest,
                    capsule,
                )?
            };
            if !from_stdin.status.success() || !from_file.status.success() {
                return Err(format!(
                    "{kind} {latest} stdin/file failure: stdin={from_stdin:?}, file={from_file:?}"
                ));
            }
            let published = fs::read(published_path).map_err(|error| error.to_string())?;
            let baseline = fs::read(baseline_path).map_err(|error| error.to_string())?;
            if published != baseline {
                return Err(format!("{kind} {latest} stdin/file code bytes differ"));
            }
            let executable = restored_canonical_stdin_source(published, capsule)?;
            if executable != compiled.layout().source() {
                return Err(format!("{kind} {latest} target source drift"));
            }
            let mut vm =
                ProfileMachine::from_source(current_profile(), &executable, vec![0, 255, 128])
                    .map_err(|error| format!("{kind} real VM load: {error:?}"))?;
            let expected = if latest {
                vec![0, 0, 128]
            } else {
                vec![0, 255]
            };
            let steps = if latest { 7 } else { 5 };
            if !matches!(vm.run(steps),
                Ok(RunOutcome::Terminated { steps: executed, .. }) if executed == steps)
                || vm.output() != expected
                || vm.input_consumed() != (if latest { 3 } else { 2 })
            {
                return Err(format!("{kind} {latest} canonical stdin guest mismatch"));
            }
        }
    }
    Ok(())
}

#[test]
fn canonical_stdin_modes_reject_missing_bounded_or_corrupt_wire_without_publication()
-> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let valid = wire(&fixture(1)?)?;
    let output = workspace.path("rejected.malbolge");
    for (typed, bytes) in [
        (true, Vec::new()),
        (false, Vec::new()),
        (true, vec![0xff; 1_048_577]),
        (false, vec![0xff; 1_048_577]),
        (true, vec![0x4d, 0x43, 0x54, 0x49, 0]),
        (false, valid.clone()),
    ] {
        let result =
            publish_canonical_stdin(current_profile().id(), &bytes, &output, typed, false, true)?;
        if result.status.success() || output.exists() {
            return Err(String::from(
                "invalid canonical stdin unexpectedly published",
            ));
        }
    }
    let compiled = compile_canonical_typed_echo(&valid, current_profile())
        .map_err(|error| format!("negative-test MCTR fixture: {error:?}"))?;
    for (typed, wire) in [
        (true, valid.clone()),
        (false, compiled.ternary_bytes().to_vec()),
    ] {
        let rejected = publish_canonical_stdin(
            historical_profile().id(),
            &wire,
            &output,
            typed,
            false,
            true,
        )?;
        if rejected.status.success() || output.exists() {
            return Err(String::from(
                "canonical stdin accepted source-profile drift",
            ));
        }
    }
    let stale = wire(&latest_typed_fixture(&[(true, 0), (true, 1), (false, 0)])?)?;
    let unsupported =
        publish_canonical_stdin(current_profile().id(), &stale, &output, true, true, false)?;
    if unsupported.status.success() || output.exists() {
        return Err(String::from("latest stdin accepted stale typed SSA output"));
    }
    let sentinel = b"existing output cannot be replaced by stdin";
    fs::write(&output, sentinel).map_err(|error| error.to_string())?;
    let refused =
        publish_canonical_stdin(current_profile().id(), &valid, &output, true, false, false)?;
    if refused.status.success() || fs::read(output).map_err(|error| error.to_string())? != sentinel
    {
        return Err(String::from("canonical stdin overwrote existing output"));
    }
    Ok(())
}

#[test]
fn canonical_stdin_modes_require_exact_zero_argument_grammar() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let target = workspace.path("bad-grammar.malbolge");
    for modes in [
        vec!["--typed-stdin", "unexpected.mcti"],
        vec!["--ternary-stdin", "unexpected.mctr"],
        vec!["--latest-byte-trace", "--typed-stdin", "nop"],
        vec!["--latest-byte-trace", "--ternary-stdin", "--capsule"],
        vec!["--typed-stdin", "--ternary-stdin"],
    ] {
        let result = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
            .arg("--profile")
            .arg(current_profile().id())
            .arg("--output")
            .arg(&target)
            .arg("--")
            .args(modes)
            .stdin(Stdio::null())
            .output()
            .map_err(|error| format!("invalid canonical stdin options: {error}"))?;
        if result.status.success() || target.exists() {
            return Err(String::from("malformed stdin grammar admitted output"));
        }
    }
    Ok(())
}

#[test]
fn canonical_typed_stdin_capsule_executes_in_real_general_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let target = workspace.path("from-typed-pipe.malbolge");
    let typed = wire(&latest_typed_fixture(&[
        (true, 0),
        (false, 0),
        (false, 0),
        (true, 1),
        (true, 2),
        (false, 2),
    ])?)?;
    let publication =
        publish_canonical_stdin(current_profile().id(), &typed, &target, true, true, true)?;
    if !publication.status.success() {
        return Err(format!(
            "typed stdin capsule rejected: {}",
            String::from_utf8_lossy(&publication.stderr)
        ));
    }
    let binary = fs::read(&target).map_err(|error| error.to_string())?;
    let capsule = malbolge::parse_capsule(&binary)
        .map_err(|error| format!("streamed capsule parser: {error}"))?
        .ok_or("streamed MCTI capsule missing")?;
    if capsule.profile() != current_profile() || capsule.payload().len() != 7 {
        return Err(String::from("streamed capsule profile/length changed"));
    }
    let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&target)
        .arg("--input-stdin")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("real general Malbolge runner: {error}"))?;
    child
        .stdin
        .take()
        .ok_or("guest runner missing stdin")?
        .write_all(&[0, 255, 128])
        .map_err(|error| format!("real guest binary feed: {error}"))?;
    let executed = child
        .wait_with_output()
        .map_err(|error| format!("real guest output: {error}"))?;
    if !executed.status.success() || executed.stdout != [0, 0, 128] || !executed.stderr.is_empty() {
        return Err(format!(
            "streamed typed capsule runner changed semantics: {executed:?}"
        ));
    }
    Ok(())
}

#[test]
fn canonical_typed_stdin_keeps_target_absent_until_valid_eof() -> Result<(), String> {
    use std::thread;
    use std::time::Duration;

    let workspace = OwnedFixture::new()?;
    let canonical = wire(&fixture(1)?)?;
    let target = workspace.path("complete-stream.malbolge");
    let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
        .arg("--profile")
        .arg(current_profile().id())
        .arg("--output")
        .arg(&target)
        .arg("--")
        .arg("--typed-stdin")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("split MCTI child launch: {error}"))?;
    let mut input = child.stdin.take().ok_or("missing MCTI stdin writer")?;
    let prefix = canonical.get(..16).ok_or("canonical MCTI prefix missing")?;
    let suffix = canonical.get(16..).ok_or("canonical MCTI suffix missing")?;
    input
        .write_all(prefix)
        .map_err(|error| format!("write partial MCTI prefix: {error}"))?;
    thread::sleep(Duration::from_millis(75));
    if target.exists()
        || child
            .try_wait()
            .map_err(|error| format!("check incomplete publication: {error}"))?
            .is_some()
    {
        drop(child.kill());
        drop(child.wait());
        return Err(String::from(
            "publisher completed before canonical input EOF",
        ));
    }
    for byte in suffix {
        input
            .write_all(&[*byte])
            .map_err(|error| format!("write fragmented MCTI: {error}"))?;
    }
    drop(input);
    let result = child
        .wait_with_output()
        .map_err(|error| format!("complete fragmented MCTI: {error}"))?;
    if !result.status.success() {
        return Err(format!(
            "complete split MCTI rejected: {}",
            String::from_utf8_lossy(&result.stderr)
        ));
    }
    let compiled = compile_canonical_typed_echo(&canonical, current_profile())
        .map_err(|error| format!("MCTI semantic baseline: {error:?}"))?;
    if fs::read(&target).map_err(|error| error.to_string())? != compiled.layout().source() {
        return Err(String::from("fragmented stdin changed encoded guest bytes"));
    }
    Ok(())
}

#[cfg(target_os = "linux")]
fn cycle_canonical_file_alias(
    still_running: &AtomicBool,
    alias: &Path,
    regular: &Path,
    pipe: &Path,
) -> Result<usize, String> {
    use std::os::unix::fs::symlink;
    use std::thread;
    use std::time::Duration;

    let staged = alias.with_extension("replacement");
    let mut cycles = 0usize;
    while still_running.load(Ordering::Relaxed) {
        for target in [pipe, regular] {
            symlink(target, &staged)
                .map_err(|error| format!("stage canonical alias switch: {error}"))?;
            fs::rename(&staged, alias)
                .map_err(|error| format!("atomically switch canonical alias: {error}"))?;
            cycles = cycles.saturating_add(1);
        }
        thread::sleep(Duration::from_micros(100));
    }
    Ok(cycles)
}

#[cfg(target_os = "linux")]
fn reject_swapped_canonical_file_alias(
    alias: &Path,
    target: &Path,
    typed: bool,
) -> Result<(), String> {
    use std::thread;
    use std::time::{Duration, Instant};

    let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
        .arg("--profile")
        .arg(current_profile().id())
        .arg("--output")
        .arg(target)
        .arg("--")
        .arg(if typed {
            "--typed-file"
        } else {
            "--ternary-file"
        })
        .arg(alias)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| format!("racing canonical-file spawn: {error}"))?;
    let started = Instant::now();
    loop {
        if let Some(status) = child
            .try_wait()
            .map_err(|error| format!("racing canonical-file poll: {error}"))?
        {
            if status.success() || target.exists() {
                return Err(String::from(
                    "swapped invalid wire published a final target",
                ));
            }
            return Ok(());
        }
        if started.elapsed() > Duration::from_secs(5) {
            drop(child.kill());
            drop(child.wait());
            return Err(String::from(
                "canonical file open blocked during regular-to-FIFO alias swap",
            ));
        }
        thread::sleep(Duration::from_millis(5));
    }
}

#[cfg(target_os = "linux")]
#[test]
fn canonical_file_modes_survive_atomic_regular_fifo_symlink_replacement() -> Result<(), String> {
    use std::os::unix::fs::symlink;
    use std::sync::Arc;
    use std::thread;

    let workspace = OwnedFixture::new()?;
    let regular = workspace.path("invalid-wire.mcti");
    let pipe = workspace.path("writerless.fifo");
    let alias = workspace.path("swapping-wire.mcti");
    fs::write(&regular, b"wrong-wire-of-bounded-length")
        .map_err(|error| format!("racing regular fixture: {error}"))?;
    let created = Command::new("mkfifo")
        .arg(&pipe)
        .status()
        .map_err(|error| format!("racing FIFO fixture: {error}"))?;
    if !created.success() {
        return Err(String::from("racing FIFO fixture unavailable"));
    }
    symlink(&regular, &alias).map_err(|error| format!("initial racing symlink: {error}"))?;
    let still_running = Arc::new(AtomicBool::new(true));
    let toggler = {
        let running = Arc::clone(&still_running);
        let racing_alias = alias.clone();
        thread::spawn(move || cycle_canonical_file_alias(&running, &racing_alias, &regular, &pipe))
    };
    let observed = (|| -> Result<(), String> {
        for (i, typed) in [true, false].into_iter().cycle().take(32).enumerate() {
            let target = workspace.path(&format!("refused-racing-{i}.malbolge"));
            reject_swapped_canonical_file_alias(&alias, &target, typed)?;
        }
        Ok(())
    })();
    still_running.store(false, Ordering::Relaxed);
    let switches = toggler
        .join()
        .map_err(|_error| String::from("canonical alias toggler panicked"))??;
    observed?;
    if switches < 8 {
        return Err(format!("insufficient concurrent alias swaps: {switches}"));
    }
    Ok(())
}

fn initial_zero_typed_fixture(value: u8, outputs: usize) -> Result<Module, String> {
    let mut instructions = Vec::with_capacity(outputs.saturating_add(1));
    instructions.push(LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: adapter::typed::IntegerConstant::new(8, vec![value]),
            result: ValueId::new(0),
            type_id: TypeId::new(0),
        },
        span(0, 1),
    ));
    for offset in 0..outputs {
        let start = u32::try_from(offset.saturating_add(1))
            .map_err(|error| format!("typed zero-output source span: {error}"))?;
        instructions.push(LocatedInstruction::new(
            Instruction::ByteOutput {
                value: ValueId::new(0),
            },
            span(start, start.saturating_add(1)),
        ));
    }
    fixture_with_instructions(instructions, "fixtures/typed-initial-zero.c")
}

#[test]
fn canonical_initial_zero_typed_ir_reaches_guest_vm_without_reading() -> Result<(), String> {
    for outputs in [1usize, 2, 7, 64] {
        let module = initial_zero_typed_fixture(0, outputs)?;
        let typed = wire(&module)?;
        let decoded = canonical_module(&typed)
            .map_err(|error| format!("independent zero MCTI admission: {error:?}"))?;
        if decoded != module {
            return Err(String::from("canonical zero source identity changed"));
        }
        let compiled =
            adapter::compile_canonical_typed_initial_zero_outputs(&typed, current_profile())
                .map_err(|error| format!("typed zero target lowering: {error:?}"))?;
        let restored = canonical_ternary_program(compiled.ternary_bytes())
            .map_err(|error| format!("independent zero MCTR admission: {error:?}"))?;
        if restored.source_id != module.source_id()
            || restored.source_sha256 != *module.source_sha256()
            || restored.target_profile != current_profile().id()
        {
            return Err(String::from("zero typed source/target provenance changed"));
        }
        let independently_compiled =
            adapter::bridge::encode_initial_zero_outputs(&restored, current_profile())
                .map_err(|error| format!("independent zero bridge: {error:?}"))?;
        if compiled.layout() != &independently_compiled
            || compiled.layout().source().len() != outputs.saturating_add(1)
        {
            return Err(String::from(
                "zero typed and ternary executable source disagree",
            ));
        }
        for input in [Vec::new(), vec![255, 128, 0]] {
            let mut vm =
                ProfileMachine::from_source(current_profile(), compiled.layout().source(), input)
                    .map_err(|error| format!("typed zero real guest VM: {error:?}"))?;
            if !matches!(vm.run(outputs.saturating_add(1)),
                Ok(RunOutcome::Terminated { steps, .. }) if steps == outputs.saturating_add(1))
                || vm.input_consumed() != 0
                || vm.output() != vec![0; outputs]
            {
                return Err(String::from("zero typed source changed guest effects"));
            }
        }
    }
    Ok(())
}

#[test]
fn canonical_initial_zero_typed_rejects_unsupported_and_default_modes() -> Result<(), String> {
    let canonical = wire(&initial_zero_typed_fixture(0, 2)?)?;
    if compile_canonical_typed_echo(&canonical, current_profile()).is_ok()
        || adapter::compile_canonical_typed_latest_byte_trace(&canonical, current_profile()).is_ok()
    {
        return Err(String::from(
            "zero scalar broadened existing byte trace modes",
        ));
    }
    for (value, outputs) in [(0, 0), (1, 1), (255, 2)] {
        let input = wire(&initial_zero_typed_fixture(value, outputs)?)?;
        if adapter::compile_canonical_typed_initial_zero_outputs(&input, current_profile()).is_ok()
        {
            return Err(String::from(
                "typed zero mode admitted unsupported constant",
            ));
        }
    }
    if adapter::compile_canonical_typed_initial_zero_outputs(&canonical, historical_profile())
        != Err(TypedEchoAdapterError::Layout(
            adapter::bridge::ByteEchoBridgeError::ProfileMismatch,
        ))
    {
        return Err(String::from("typed zero mode accepted profile drift"));
    }
    // Keep the invalid SSA witness in canonical typed bytes, not in a
    // caller-invented lowering projection.
    let mut instructions = vec![LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: adapter::typed::IntegerConstant::new(8, vec![0]),
            result: ValueId::new(0),
            type_id: TypeId::new(0),
        },
        span(0, 1),
    )];
    instructions.push(LocatedInstruction::new(
        Instruction::ByteOutput {
            value: ValueId::new(7),
        },
        span(1, 2),
    ));
    let invalid = fixture_with_instructions(instructions, "fixtures/typed-stale-zero.c")?;
    if wire(&invalid).is_ok() {
        return Err(String::from("invalid typed SSA passed upstream admission"));
    }
    Ok(())
}

#[expect(
    clippy::too_many_arguments,
    reason = "external fixture selects canonical source form and framing"
)]
fn publish_initial_zero_wire(
    profile: &str,
    wire_bytes: &[u8],
    target: &Path,
    typed: bool,
    stdin: bool,
    capsule: bool,
) -> Result<Output, String> {
    let mut command = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"));
    let _profile = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    let _source = command.arg("--").arg("--initial-zero-output");
    if stdin {
        let _stdin = command.arg(if typed {
            "--typed-stdin"
        } else {
            "--ternary-stdin"
        });
    } else {
        let wire_path = target.with_extension(if typed { "mcti" } else { "mctr" });
        fs::write(&wire_path, wire_bytes)
            .map_err(|error| format!("zero canonical file fixture: {error}"))?;
        let _file = command
            .arg(if typed {
                "--typed-file"
            } else {
                "--ternary-file"
            })
            .arg(wire_path);
    }
    let mut child = command
        .stdin(if stdin { Stdio::piped() } else { Stdio::null() })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("zero canonical CLI spawn: {error}"))?;
    if stdin {
        child
            .stdin
            .take()
            .ok_or("canonical zero guest wire pipe absent")?
            .write_all(wire_bytes)
            .map_err(|error| format!("feed zero canonical source bytes: {error}"))?;
    }
    child
        .wait_with_output()
        .map_err(|error| format!("zero source CLI status: {error}"))
}

#[expect(
    clippy::too_many_arguments,
    reason = "external publication fixture covers two source forms and output framing"
)]
fn require_initial_zero_publication(
    bytes: &[u8],
    path: &Path,
    typed: bool,
    stdin: bool,
    capsule: bool,
) -> Result<(), String> {
    let process =
        publish_initial_zero_wire(current_profile().id(), bytes, path, typed, stdin, capsule)?;
    if !process.status.success() {
        return Err(format!(
            "zero guest publisher refused: {}",
            String::from_utf8_lossy(&process.stderr)
        ));
    }
    Ok(())
}

#[test]
fn canonical_initial_zero_cli_publishes_verified_raw_capsules_from_file_and_stdin()
-> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let canonical = wire(&initial_zero_typed_fixture(0, 2)?)?;
    let compiled =
        adapter::compile_canonical_typed_initial_zero_outputs(&canonical, current_profile())
            .map_err(|error| format!("zero typed compiler baseline: {error:?}"))?;
    let ternary = compiled.ternary_bytes();
    for (typed, bytes) in [(true, canonical.as_slice()), (false, ternary)] {
        for capsule in [false, true] {
            let kind = if typed { "typed" } else { "ternary" };
            let framing = if capsule { "capsule" } else { "raw" };
            let from_file = workspace.path(&format!("file-{kind}-{framing}.malbolge"));
            let from_stdin = workspace.path(&format!("stdin-{kind}-{framing}.malbolge"));
            for (stdin, path) in [(false, &from_file), (true, &from_stdin)] {
                require_initial_zero_publication(bytes, path, typed, stdin, capsule)?;
            }
            let file_bytes = fs::read(from_file).map_err(|error| error.to_string())?;
            let stdin_bytes = fs::read(from_stdin).map_err(|error| error.to_string())?;
            if file_bytes != stdin_bytes {
                return Err(format!(
                    "{kind} {framing} file and stdin target bytes differ"
                ));
            }
            let source = restored_canonical_stdin_source(file_bytes, capsule)?;
            if source != compiled.layout().source() {
                return Err(String::from(
                    "published zero target differs from typed MCTI",
                ));
            }
            let mut vm = ProfileMachine::from_source(current_profile(), &source, vec![255, 128])
                .map_err(|error| format!("published zero guest load: {error:?}"))?;
            if !matches!(vm.run(3), Ok(RunOutcome::Terminated { steps: 3, .. }))
                || vm.input_consumed() != 0
                || vm.output() != [0, 0]
            {
                return Err(String::from(
                    "published zero source did not execute on real VM",
                ));
            }
        }
    }
    Ok(())
}

#[test]
fn canonical_initial_zero_cli_fail_closes_without_final_output() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let canonical = wire(&initial_zero_typed_fixture(0, 2)?)?;
    let nonzero = wire(&initial_zero_typed_fixture(3, 2)?)?;
    let compiled =
        adapter::compile_canonical_typed_initial_zero_outputs(&canonical, current_profile())
            .map_err(|error| format!("zero negative MCTR baseline: {error:?}"))?;
    for (index, (typed, bytes, profile)) in [
        (true, canonical.as_slice(), historical_profile().id()),
        (false, compiled.ternary_bytes(), historical_profile().id()),
        (true, nonzero.as_slice(), current_profile().id()),
        (true, b"MCTI-invalid".as_slice(), current_profile().id()),
    ]
    .into_iter()
    .enumerate()
    {
        let output = workspace.path(&format!("refused-{index}.malbolge"));
        let verdict = publish_initial_zero_wire(profile, bytes, &output, typed, true, true)?;
        if verdict.status.success() || output.exists() {
            return Err(format!("invalid zero source published test index {index}"));
        }
    }
    let occupied = workspace.path("occupied.malbolge");
    let sentinel = b"existing guest target must remain intact";
    fs::write(&occupied, sentinel).map_err(|error| error.to_string())?;
    let verdict = publish_initial_zero_wire(
        current_profile().id(),
        &canonical,
        &occupied,
        true,
        false,
        false,
    )?;
    if verdict.status.success()
        || fs::read(&occupied).map_err(|error| error.to_string())? != sentinel
    {
        return Err(String::from("zero compiler replaced an occupied target"));
    }
    Ok(())
}

#[test]
fn canonical_initial_zero_cli_refuses_mixed_option_grammar() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for (index, args) in [
        vec!["--initial-zero-output"],
        vec![
            "--initial-zero-output",
            "--latest-byte-trace",
            "--typed-stdin",
        ],
        vec![
            "--latest-byte-trace",
            "--initial-zero-output",
            "--typed-stdin",
        ],
        vec!["--initial-zero-output", "--typed-stdin", "surplus"],
    ]
    .into_iter()
    .enumerate()
    {
        let target = workspace.path(&format!("bad-mode-{index}.malbolge"));
        let outcome = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
            .arg("--profile")
            .arg(current_profile().id())
            .arg("--output")
            .arg(&target)
            .arg("--")
            .args(args)
            .stdin(Stdio::null())
            .output()
            .map_err(|error| format!("bad mode process: {error}"))?;
        if outcome.status.success() || target.exists() {
            return Err(String::from("mixed zero and latest option was admitted"));
        }
    }
    Ok(())
}

#[test]
fn canonical_initial_zero_capsule_executes_in_real_general_cli() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let canonical = wire(&initial_zero_typed_fixture(0, 2)?)?;
    let target = workspace.path("initial-zero-runner.malbolge");
    require_initial_zero_publication(&canonical, &target, true, true, true)?;
    let published = fs::read(&target).map_err(|error| error.to_string())?;
    let capsule = malbolge::parse_capsule(&published)
        .map_err(|error| format!("initial zero capsule parser: {error}"))?
        .ok_or("zero capsule marker missing")?;
    if capsule.profile() != current_profile() || capsule.payload().len() != 3 {
        return Err(String::from(
            "zero capsule profile or executable size drift",
        ));
    }
    let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&target)
        .arg("--input-stdin")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("launch zero general guest runner: {error}"))?;
    child
        .stdin
        .take()
        .ok_or("zero real guest runner pipe absent")?
        .write_all(&[255, 0, 128])
        .map_err(|error| format!("feed zero guest binary stdin: {error}"))?;
    let result = child
        .wait_with_output()
        .map_err(|error| format!("zero general runner exit: {error}"))?;
    if !result.status.success() || result.stdout != [0, 0] || !result.stderr.is_empty() {
        return Err(format!(
            "real guest runner disagrees with zero VM: {result:?}"
        ));
    }
    Ok(())
}

#[test]
fn canonical_initial_zero_typed_exact_maximum_refuses_one_extra_output() -> Result<(), String> {
    let admitted = wire(&initial_zero_typed_fixture(0, 4095)?)?;
    let compiled =
        adapter::compile_canonical_typed_initial_zero_outputs(&admitted, current_profile())
            .map_err(|error| format!("maximum typed zero source: {error:?}"))?;
    if compiled.layout().source().len() != 4096 {
        return Err(String::from("typed zero output layout was not 4096 cells"));
    }
    let mut vm =
        ProfileMachine::from_source(current_profile(), compiled.layout().source(), Vec::new())
            .map_err(|error| format!("maximum typed zero VM load: {error:?}"))?;
    if !matches!(vm.run(4096), Ok(RunOutcome::Terminated { steps: 4096, .. }))
        || vm.output().len() != 4095
        || vm.output().iter().any(|byte| *byte != 0)
        || vm.input_consumed() != 0
    {
        return Err(String::from("maximum typed zero VM effects changed"));
    }
    let excessive = wire(&initial_zero_typed_fixture(0, 4096)?)?;
    if adapter::compile_canonical_typed_initial_zero_outputs(&excessive, current_profile()).is_ok()
    {
        return Err(String::from("typed zero source admitted 4097 code cells"));
    }
    Ok(())
}

#[test]
fn canonical_initial_zero_typed_refuses_valid_extra_constant_and_guest_read() -> Result<(), String>
{
    let constant = |result: u32, start: u32| {
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: adapter::typed::IntegerConstant::new(8, vec![0]),
                result: ValueId::new(result),
                type_id: TypeId::new(0),
            },
            span(start, start.saturating_add(1)),
        )
    };
    for middle in [
        constant(1, 1),
        LocatedInstruction::new(
            Instruction::ByteInput {
                result: ValueId::new(1),
                type_id: TypeId::new(0),
            },
            span(1, 2),
        ),
    ] {
        let module = fixture_with_instructions(
            vec![
                constant(0, 0),
                middle,
                LocatedInstruction::new(
                    Instruction::ByteOutput {
                        value: ValueId::new(0),
                    },
                    span(2, 3),
                ),
            ],
            "fixtures/typed-extra-initial-zero.c",
        )?;
        let canonical = wire(&module)?;
        if adapter::compile_canonical_typed_initial_zero_outputs(&canonical, current_profile())
            != Err(TypedEchoAdapterError::UnsupportedTypedIr)
        {
            return Err(String::from(
                "valid extra typed operation was silently ignored",
            ));
        }
    }
    Ok(())
}

#[test]
fn canonical_initial_zero_cli_rejects_nonzero_mctr_and_unselected_modes() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let canonical = wire(&initial_zero_typed_fixture(0, 2)?)?;
    let compiled =
        adapter::compile_canonical_typed_initial_zero_outputs(&canonical, current_profile())
            .map_err(|error| format!("canonical zero negative MCTR: {error:?}"))?;
    let mut nonzero = canonical_ternary_program(compiled.ternary_bytes())
        .map_err(|error| format!("admit zero ternary baseline: {error:?}"))?;
    let Some(TernaryOperation::MaterializeU8 { scalar, .. }) = nonzero
        .functions
        .first_mut()
        .and_then(|function| function.operations.first_mut())
    else {
        return Err(String::from("missing canonical zero materialization"));
    };
    *scalar = adapter::bridge::ternary::TernaryU8Scalar::from_bits(5);
    let nonzero_bytes = adapter::bridge::ternary::canonical_ternary_bytes(&nonzero)
        .map_err(|error| format!("independently valid nonzero MCTR: {error:?}"))?;
    let invalid_target = workspace.path("nonzero-canonical.malbolge");
    let rejected = publish_initial_zero_wire(
        current_profile().id(),
        &nonzero_bytes,
        &invalid_target,
        false,
        true,
        false,
    )?;
    if rejected.status.success() || invalid_target.exists() {
        return Err(String::from("valid nonzero MCTR published as initial zero"));
    }
    let typed_path = workspace.path("zero-typed.mcti");
    let ternary_path = workspace.path("zero-ternary.mctr");
    fs::write(&typed_path, &canonical).map_err(|error| error.to_string())?;
    fs::write(&ternary_path, compiled.ternary_bytes()).map_err(|error| error.to_string())?;
    for (index, (typed, latest)) in [(true, false), (false, false), (true, true), (false, true)]
        .into_iter()
        .enumerate()
    {
        let target = workspace.path(&format!("unselected-{index}.malbolge"));
        let admitted = if typed {
            publish_typed_wire(current_profile().id(), &typed_path, &target, latest, false)?
        } else {
            publish_ternary_wire(
                current_profile().id(),
                &ternary_path,
                &target,
                latest,
                false,
            )?
        };
        if admitted.status.success() || target.exists() {
            return Err(String::from("unselected echo mode emitted zero constant"));
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "one real subprocess test checks two wire kinds and both EOF boundaries"
)]
fn canonical_initial_zero_stream_waits_for_eof_before_publication() -> Result<(), String> {
    use std::thread;
    use std::time::Duration;

    let workspace = OwnedFixture::new()?;
    let canonical = wire(&initial_zero_typed_fixture(0, 2)?)?;
    let compiled =
        adapter::compile_canonical_typed_initial_zero_outputs(&canonical, current_profile())
            .map_err(|error| format!("fragmented zero MCTI baseline: {error:?}"))?;
    for (typed, source) in [
        (true, canonical.as_slice()),
        (false, compiled.ternary_bytes()),
    ] {
        let kind = if typed { "typed" } else { "ternary" };
        let target = workspace.path(&format!("fragmented-zero-{kind}.malbolge"));
        let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
            .arg("--profile")
            .arg(current_profile().id())
            .arg("--output")
            .arg(&target)
            .arg("--")
            .arg("--initial-zero-output")
            .arg(if typed {
                "--typed-stdin"
            } else {
                "--ternary-stdin"
            })
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|error| format!("fragmented zero CLI spawn: {error}"))?;
        let mut writer = child
            .stdin
            .take()
            .ok_or("zero canonical stdin pipe missing")?;
        let prefix = source
            .get(..16)
            .ok_or("zero canonical wire shorter than 16 bytes")?;
        let suffix = source.get(16..).ok_or("zero canonical suffix missing")?;
        for fragment in [prefix, suffix] {
            writer
                .write_all(fragment)
                .map_err(|error| format!("fragmented zero wire feed: {error}"))?;
            thread::sleep(Duration::from_millis(75));
            if target.exists()
                || child
                    .try_wait()
                    .map_err(|error| format!("zero-before-EOF child poll: {error}"))?
                    .is_some()
            {
                drop(child.kill());
                drop(child.wait());
                return Err(String::from("zero artifact published or exited before EOF"));
            }
        }
        drop(writer);
        let result = child
            .wait_with_output()
            .map_err(|error| format!("fragmented zero publisher exit: {error}"))?;
        if !result.status.success() {
            return Err(format!(
                "complete zero wire rejected: {}",
                String::from_utf8_lossy(&result.stderr)
            ));
        }
        if fs::read(&target).map_err(|error| error.to_string())? != compiled.layout().source() {
            return Err(String::from("fragmented zero wire changed target bytes"));
        }
    }
    Ok(())
}

#[test]
fn canonical_zero_prefixed_latest_trace_matches_independent_mctr_and_real_vm() -> Result<(), String>
{
    let typed_module = admitted_zero_prefix_fixture()?;
    let encoded = wire(&typed_module)?;
    if canonical_module(&encoded)
        .map_err(|error| format!("zero prefix canonical admission: {error:?}"))?
        != typed_module
    {
        return Err(String::from("canonical typed zero prefix changed source"));
    }
    let compiled = adapter::compile_canonical_typed_zero_prefixed_latest_byte_trace(
        &encoded,
        current_profile(),
    )
    .map_err(|error| format!("zero prefix typed compilation: {error:?}"))?;
    let ternary = canonical_ternary_program(compiled.ternary_bytes())
        .map_err(|error| format!("zero prefix independent MCTR: {error:?}"))?;
    if ternary.source_id != typed_module.source_id()
        || ternary.source_sha256 != *typed_module.source_sha256()
        || ternary.target_profile != current_profile().id()
    {
        return Err(String::from("zero prefix source identity drift"));
    }
    let independent =
        adapter::bridge::encode_zero_prefixed_latest_byte_trace(&ternary, current_profile())
            .map_err(|error| format!("independent ternary-to-layout admission: {error:?}"))?;
    if independent != *compiled.layout() || compiled.layout().source().len() != 8 {
        return Err(String::from("MCTI and independent MCTR target code differ"));
    }
    for (first, second) in [(0, 255), (255, 0), (128, 13), (42, 65)] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            compiled.layout().source(),
            vec![first, second, 170],
        )
        .map_err(|error| format!("typed mixed guest VM: {error:?}"))?;
        if !matches!(vm.run(8), Ok(RunOutcome::Terminated { steps: 8, .. }))
            || vm.input_consumed() != 2
            || vm.output() != [0, 0, first, first, second]
        {
            return Err(String::from("zero prefix typed guest effects drift"));
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "source-validated matrix of supported and forbidden mixed SSA flows"
)]
fn canonical_zero_prefixed_trace_rejects_valid_unsupported_typed_effects() -> Result<(), String> {
    let admitted = wire(&admitted_zero_prefix_fixture()?)?;
    for old in [
        compile_canonical_typed_echo(&admitted, current_profile()),
        adapter::compile_canonical_typed_latest_byte_trace(&admitted, current_profile()),
        adapter::compile_canonical_typed_initial_zero_outputs(&admitted, current_profile()),
    ] {
        if old != Err(TypedEchoAdapterError::UnsupportedTypedIr) {
            return Err(String::from("old canonical typed API silently broadened"));
        }
    }
    if adapter::compile_canonical_typed_zero_prefixed_latest_byte_trace(
        &admitted,
        historical_profile(),
    ) != Err(TypedEchoAdapterError::Layout(
        adapter::bridge::ByteEchoBridgeError::ProfileMismatch,
    )) {
        return Err(String::from("zero prefix accepted wrong profile"));
    }
    for (zero, effects) in [
        (
            1,
            vec![
                ZeroPrefixedEffect::Output(0),
                ZeroPrefixedEffect::Input(1),
                ZeroPrefixedEffect::Output(1),
            ],
        ),
        (
            0,
            vec![ZeroPrefixedEffect::Input(1), ZeroPrefixedEffect::Output(1)],
        ),
        (
            0,
            vec![ZeroPrefixedEffect::Output(0), ZeroPrefixedEffect::Input(1)],
        ),
        (
            0,
            vec![
                ZeroPrefixedEffect::Output(0),
                ZeroPrefixedEffect::Input(1),
                ZeroPrefixedEffect::Output(0),
            ],
        ),
        (
            0,
            vec![
                ZeroPrefixedEffect::Output(0),
                ZeroPrefixedEffect::Input(1),
                ZeroPrefixedEffect::Input(2),
                ZeroPrefixedEffect::Output(1),
            ],
        ),
        (
            0,
            vec![
                ZeroPrefixedEffect::Output(0),
                ZeroPrefixedEffect::Scalar(1),
                ZeroPrefixedEffect::Input(2),
                ZeroPrefixedEffect::Output(2),
            ],
        ),
    ] {
        let canonical = wire(&zero_prefixed_typed_fixture(zero, &effects)?)?;
        if adapter::compile_canonical_typed_zero_prefixed_latest_byte_trace(
            &canonical,
            current_profile(),
        ) != Err(TypedEchoAdapterError::UnsupportedTypedIr)
        {
            return Err(String::from("valid but unsupported typed effects admitted"));
        }
    }
    Ok(())
}

#[test]
fn canonical_zero_prefixed_trace_4096_code_cell_limit_is_exact() -> Result<(), String> {
    let mut effects = vec![ZeroPrefixedEffect::Output(0), ZeroPrefixedEffect::Input(1)];
    effects.extend(repeat_n(ZeroPrefixedEffect::Output(1), 4093));
    let canonical = wire(&zero_prefixed_typed_fixture(0, &effects)?)?;
    let compiled = adapter::compile_canonical_typed_zero_prefixed_latest_byte_trace(
        &canonical,
        current_profile(),
    )
    .map_err(|error| format!("maximum typed mixed layout: {error:?}"))?;
    if compiled.layout().source().len() != 4096 {
        return Err(String::from("typed mixed maximum is not 4096 cells"));
    }
    let mut vm =
        ProfileMachine::from_source(current_profile(), compiled.layout().source(), vec![255])
            .map_err(|error| format!("maximum typed mixed VM load: {error:?}"))?;
    if !matches!(vm.run(4096), Ok(RunOutcome::Terminated { steps: 4096, .. }))
        || vm.input_consumed() != 1
        || vm.output().len() != 4094
        || vm.output().first() != Some(&0)
        || vm
            .output()
            .get(1..)
            .is_none_or(|bytes| bytes.iter().any(|byte| *byte != 255))
    {
        return Err(String::from("maximum mixed typed VM effects disagree"));
    }
    effects.push(ZeroPrefixedEffect::Output(1));
    let excessive = wire(&zero_prefixed_typed_fixture(0, &effects)?)?;
    if adapter::compile_canonical_typed_zero_prefixed_latest_byte_trace(
        &excessive,
        current_profile(),
    ) != Err(TypedEchoAdapterError::UnsupportedTypedIr)
    {
        return Err(String::from("typed zero prefix accepted 4097 code cells"));
    }
    Ok(())
}

#[expect(
    clippy::too_many_arguments,
    reason = "external publisher needs wire kind, input medium and capsule format"
)]
fn publish_zero_prefixed_wire(
    profile: &str,
    wire_bytes: &[u8],
    target: &Path,
    typed: bool,
    from_stdin: bool,
    capsule: bool,
) -> Result<Output, String> {
    let mut command = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"));
    let _profile = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    let _source = command.arg("--").arg("--zero-prefixed-byte-trace");
    if from_stdin {
        let _stdin = command.arg(if typed {
            "--typed-stdin"
        } else {
            "--ternary-stdin"
        });
    } else {
        let wire_path = target.with_extension(if typed { "mcti" } else { "mctr" });
        fs::write(&wire_path, wire_bytes)
            .map_err(|error| format!("zero-prefixed canonical fixture: {error}"))?;
        let _file = command
            .arg(if typed {
                "--typed-file"
            } else {
                "--ternary-file"
            })
            .arg(wire_path);
    }
    let mut child = command
        .stdin(if from_stdin {
            Stdio::piped()
        } else {
            Stdio::null()
        })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("mixed canonical CLI spawn: {error}"))?;
    if from_stdin {
        child
            .stdin
            .take()
            .ok_or("mixed canonical stdin pipe absent")?
            .write_all(wire_bytes)
            .map_err(|error| format!("feed mixed canonical wire: {error}"))?;
    }
    child
        .wait_with_output()
        .map_err(|error| format!("mixed canonical CLI status: {error}"))
}

#[expect(
    clippy::too_many_arguments,
    reason = "real process input mode, wire kind and output framing"
)]
fn require_zero_prefixed_publication(
    profile: &str,
    wire_bytes: &[u8],
    target: &Path,
    typed: bool,
    from_stdin: bool,
    capsule: bool,
) -> Result<(), String> {
    let outcome =
        publish_zero_prefixed_wire(profile, wire_bytes, target, typed, from_stdin, capsule)?;
    if !outcome.status.success() {
        return Err(format!(
            "zero-prefixed mixed publisher refused: {}",
            String::from_utf8_lossy(&outcome.stderr)
        ));
    }
    Ok(())
}

#[test]
fn canonical_zero_prefixed_mcti_mctr_cli_file_stdin_raw_capsule_parity() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let typed_wire = wire(&admitted_zero_prefix_fixture()?)?;
    let compiled = adapter::compile_canonical_typed_zero_prefixed_latest_byte_trace(
        &typed_wire,
        current_profile(),
    )
    .map_err(|error| format!("publisher zero-prefixed compiler: {error:?}"))?;
    for (typed, wire_bytes) in [
        (true, typed_wire.as_slice()),
        (false, compiled.ternary_bytes()),
    ] {
        for capsule in [false, true] {
            let kind = if typed { "typed" } else { "ternary" };
            let framing = if capsule { "capsule" } else { "raw" };
            let file = workspace.path(&format!("file-{kind}-{framing}.malbolge"));
            let stdin = workspace.path(&format!("stdin-{kind}-{framing}.malbolge"));
            for (pipe, target) in [(false, &file), (true, &stdin)] {
                require_zero_prefixed_publication(
                    current_profile().id(),
                    wire_bytes,
                    target,
                    typed,
                    pipe,
                    capsule,
                )?;
            }
            let file_bytes = fs::read(file).map_err(|error| error.to_string())?;
            let stdin_bytes = fs::read(stdin).map_err(|error| error.to_string())?;
            if file_bytes != stdin_bytes {
                return Err(String::from("mixed stdin/file source bytes differ"));
            }
            let source = restored_canonical_stdin_source(file_bytes, capsule)?;
            if source != compiled.layout().source() {
                return Err(String::from("mixed MCTI/MCTR target source changed"));
            }
            let mut vm = ProfileMachine::from_source(current_profile(), &source, vec![0, 255, 128])
                .map_err(|error| format!("published mixed VM load: {error:?}"))?;
            if !matches!(vm.run(8), Ok(RunOutcome::Terminated { steps: 8, .. }))
                || vm.output() != [0, 0, 0, 0, 255]
                || vm.input_consumed() != 2
            {
                return Err(String::from("published zero prefix guest effects drift"));
            }
        }
    }
    Ok(())
}

#[test]
fn canonical_zero_prefixed_capsule_executes_in_actual_general_cli() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let canonical = wire(&admitted_zero_prefix_fixture()?)?;
    let target = workspace.path("zero-prefix-general.malbolge");
    let published = publish_zero_prefixed_wire(
        current_profile().id(),
        &canonical,
        &target,
        true,
        true,
        true,
    )?;
    if !published.status.success() {
        return Err(format!("mixed capsule publish refused: {published:?}"));
    }
    let parsed = fs::read(&target).map_err(|error| error.to_string())?;
    let capsule = malbolge::parse_capsule(&parsed)
        .map_err(|error| format!("mixed profile capsule parser: {error}"))?
        .ok_or("mixed capsule marker absent")?;
    if capsule.profile() != current_profile() || capsule.payload().len() != 8 {
        return Err(String::from("mixed capsule source or profile drift"));
    }
    let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&target)
        .arg("--input-stdin")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("zero-prefix real runner spawn: {error}"))?;
    child
        .stdin
        .take()
        .ok_or("zero-prefixed guest input pipe absent")?
        .write_all(&[0, 255, 128])
        .map_err(|error| format!("zero-prefixed guest input bytes: {error}"))?;
    let result = child
        .wait_with_output()
        .map_err(|error| format!("zero-prefixed real runner status: {error}"))?;
    if !result.status.success() || result.stdout != [0, 0, 0, 0, 255] || !result.stderr.is_empty() {
        return Err(format!(
            "general guest runner mixed trace mismatch: {result:?}"
        ));
    }
    Ok(())
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "real publisher rejects multiple independently invalid wire modes"
)]
fn canonical_zero_prefixed_cli_refuses_invalid_modes_profile_and_existing_target()
-> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let canonical = wire(&admitted_zero_prefix_fixture()?)?;
    let compiled = adapter::compile_canonical_typed_zero_prefixed_latest_byte_trace(
        &canonical,
        current_profile(),
    )
    .map_err(|error| format!("mixed invalid publisher fixture: {error:?}"))?;
    for (index, (typed, data, profile)) in [
        (true, canonical.as_slice(), historical_profile().id()),
        (false, compiled.ternary_bytes(), historical_profile().id()),
        (true, b"not-an-MCTI".as_slice(), current_profile().id()),
        (false, b"not-an-MCTR".as_slice(), current_profile().id()),
    ]
    .into_iter()
    .enumerate()
    {
        let target = workspace.path(&format!("refused-{index}.malbolge"));
        let result = publish_zero_prefixed_wire(profile, data, &target, typed, true, false)?;
        if result.status.success() || target.exists() {
            return Err(String::from("invalid mixed canonical wire published"));
        }
    }
    let occupied = workspace.path("existing.malbolge");
    let sentinel = b"original target contents stay intact";
    fs::write(&occupied, sentinel).map_err(|error| error.to_string())?;
    let refused = publish_zero_prefixed_wire(
        current_profile().id(),
        &canonical,
        &occupied,
        true,
        false,
        true,
    )?;
    if refused.status.success()
        || fs::read(occupied).map_err(|error| error.to_string())? != sentinel
    {
        return Err(String::from("mixed publisher clobbered existing target"));
    }
    for args in [
        vec!["--zero-prefixed-byte-trace"],
        vec![
            "--zero-prefixed-byte-trace",
            "--latest-byte-trace",
            "--typed-stdin",
        ],
        vec![
            "--latest-byte-trace",
            "--zero-prefixed-byte-trace",
            "--typed-stdin",
        ],
        vec!["--zero-prefixed-byte-trace", "--typed-stdin", "surplus"],
    ] {
        let target = workspace.path("bad-mixed-option.malbolge");
        let outcome = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
            .arg("--profile")
            .arg(current_profile().id())
            .arg("--output")
            .arg(&target)
            .arg("--")
            .args(args)
            .stdin(Stdio::null())
            .output()
            .map_err(|error| format!("bad mixed mode process: {error}"))?;
        if outcome.status.success() || target.exists() {
            return Err(String::from("mixed option syntax unexpectedly published"));
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "real subprocess proves MCTI/MCTR partial and full wire EOF boundaries"
)]
fn canonical_zero_prefixed_mixed_stream_never_publishes_before_eof() -> Result<(), String> {
    use std::thread;
    use std::time::Duration;

    let workspace = OwnedFixture::new()?;
    let typed_wire = wire(&admitted_zero_prefix_fixture()?)?;
    let compiled = adapter::compile_canonical_typed_zero_prefixed_latest_byte_trace(
        &typed_wire,
        current_profile(),
    )
    .map_err(|error| format!("fragmented mixed typed compiler: {error:?}"))?;
    for (typed, wire_bytes) in [
        (true, typed_wire.as_slice()),
        (false, compiled.ternary_bytes()),
    ] {
        let name = if typed { "typed" } else { "ternary" };
        let target = workspace.path(&format!("partial-{name}.malbolge"));
        let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
            .arg("--profile")
            .arg(current_profile().id())
            .arg("--output")
            .arg(&target)
            .arg("--")
            .arg("--zero-prefixed-byte-trace")
            .arg(if typed {
                "--typed-stdin"
            } else {
                "--ternary-stdin"
            })
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|error| format!("fragmented mixed source spawn: {error}"))?;
        let mut writer = child.stdin.take().ok_or("mixed wire writer unavailable")?;
        let prefix = wire_bytes
            .get(..16)
            .ok_or("canonical wire has no 16-byte prefix")?;
        let suffix = wire_bytes
            .get(16..)
            .ok_or("canonical wire suffix unavailable")?;
        for segment in [prefix, suffix] {
            writer
                .write_all(segment)
                .map_err(|error| format!("fragmented mixed source feed: {error}"))?;
            thread::sleep(Duration::from_millis(75));
            if target.exists()
                || child
                    .try_wait()
                    .map_err(|error| format!("poll mixed canonical publisher: {error}"))?
                    .is_some()
            {
                drop(child.kill());
                drop(child.wait());
                return Err(String::from("mixed source published or exited before EOF"));
            }
        }
        drop(writer);
        let outcome = child
            .wait_with_output()
            .map_err(|error| format!("complete mixed wire process: {error}"))?;
        if !outcome.status.success() {
            return Err(format!(
                "mixed complete wire rejected: {}",
                String::from_utf8_lossy(&outcome.stderr)
            ));
        }
        if fs::read(&target).map_err(|error| error.to_string())? != compiled.layout().source() {
            return Err(String::from("mixed canonical wire changed emitted source"));
        }
    }
    Ok(())
}

#[expect(
    clippy::too_many_lines,
    reason = "complete canonical signed-byte fixture"
)]
fn typed_identity_effects(effects: &[IdentityEffect]) -> Result<Module, String> {
    let mut instructions = Vec::with_capacity(effects.len());
    for (index, effect) in effects.iter().enumerate() {
        let at = u32::try_from(index).map_err(|error| format!("typed cast span: {error}"))?;
        let instruction = match effect {
            IdentityEffect::Input(result) => Instruction::ByteInput {
                result: ValueId::new(*result),
                type_id: TypeId::new(0),
            },
            IdentityEffect::Cast {
                result,
                value,
                type_id,
            } => Instruction::Cast {
                operation: adapter::typed::CastOp::IntegerBitcast,
                result: ValueId::new(*result),
                type_id: TypeId::new(*type_id),
                value: ValueId::new(*value),
            },
            IdentityEffect::Output(value) => Instruction::ByteOutput {
                value: ValueId::new(*value),
            },
            IdentityEffect::Literal { result, byte } => Instruction::ConstantInteger {
                constant: adapter::typed::IntegerConstant::new(8, vec![*byte]),
                result: ValueId::new(*result),
                type_id: TypeId::new(0),
            },
            IdentityEffect::Zero(result) => Instruction::ConstantInteger {
                constant: adapter::typed::IntegerConstant::new(8, vec![0]),
                result: ValueId::new(*result),
                type_id: TypeId::new(0),
            },
        };
        instructions.push(LocatedInstruction::new(
            instruction,
            span(at, at.saturating_add(1)),
        ));
    }
    let end = u32::try_from(effects.len().saturating_add(1))
        .map_err(|error| format!("typed cast return span: {error}"))?;
    Ok(Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: adapter::typed::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: span(0, end),
                terminator: Terminator::Return { value: None },
                terminator_span: span(end.saturating_sub(1), end),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("identity_byte_casts"),
            parameters: Vec::new(),
            signature: TypeId::new(1),
            span: span(0, end),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/typed-identity-byte.c"),
        source_sha256: [0xaf; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), TypeDef::U8),
            TypeEntry::new(TypeId::new(1), TypeDef::function(Vec::new(), None, false)),
            TypeEntry::new(TypeId::new(2), TypeDef::I8),
        ],
    }))
}

fn typed_identity_fixture() -> Result<Module, String> {
    typed_identity_effects(&[
        IdentityEffect::Input(0),
        IdentityEffect::Cast {
            result: 1,
            value: 0,
            type_id: 2,
        },
        IdentityEffect::Cast {
            result: 2,
            value: 1,
            type_id: 2,
        },
        IdentityEffect::Cast {
            result: 3,
            value: 2,
            type_id: 0,
        },
        IdentityEffect::Cast {
            result: 4,
            value: 3,
            type_id: 0,
        },
        IdentityEffect::Output(4),
        IdentityEffect::Output(0),
        IdentityEffect::Input(5),
        IdentityEffect::Cast {
            result: 6,
            value: 5,
            type_id: 2,
        },
        IdentityEffect::Cast {
            result: 7,
            value: 6,
            type_id: 0,
        },
        IdentityEffect::Output(7),
    ])
}

#[test]
fn canonical_typed_identity_casts_reach_genuine_vm_with_all_byte_bits() -> Result<(), String> {
    let module = typed_identity_fixture()?;
    let canonical = wire(&module)?;
    if canonical_module(&canonical).map_err(|error| format!("typed alias decode: {error:?}"))?
        != module
    {
        return Err(String::from("typed canonical alias bytes changed"));
    }
    let compiled =
        adapter::compile_canonical_typed_identity_byte_trace(&canonical, current_profile())
            .map_err(|error| format!("typed alias lowering: {error:?}"))?;
    let admitted = canonical_ternary_program(compiled.ternary_bytes())
        .map_err(|error| format!("typed alias independent MCTR: {error:?}"))?;
    if admitted.source_id != module.source_id()
        || admitted.source_sha256 != *module.source_sha256()
        || admitted.target_profile != current_profile().id()
    {
        return Err(String::from("typed identity alias provenance drift"));
    }
    let independent =
        adapter::bridge::encode_latest_byte_identity_trace(&admitted, current_profile())
            .map_err(|error| format!("independent identity trace bridge: {error:?}"))?;
    if independent != *compiled.layout() || compiled.layout().source().len() != 6 {
        return Err(String::from(
            "typed and ternary identity source disagreement",
        ));
    }
    for (first, second) in [(0, 255), (255, 0), (128, 13), (42, 65)] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            compiled.layout().source(),
            vec![first, second, 71],
        )
        .map_err(|error| format!("typed alias VM: {error:?}"))?;
        if !matches!(vm.run(6), Ok(RunOutcome::Terminated { steps: 6, .. }))
            || vm.output() != [first, first, second]
            || vm.input_consumed() != 2
        {
            return Err(String::from("typed alias guest output/input mismatch"));
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "invalid SSA and strict legacy mode matrix"
)]
fn canonical_typed_identity_mode_refuses_unrealizable_aliases() -> Result<(), String> {
    let good = wire(&typed_identity_fixture()?)?;
    for old in [
        compile_canonical_typed_echo(&good, current_profile()),
        adapter::compile_canonical_typed_latest_byte_trace(&good, current_profile()),
        adapter::compile_canonical_typed_zero_prefixed_latest_byte_trace(&good, current_profile()),
    ] {
        if old != Err(TypedEchoAdapterError::UnsupportedTypedIr) {
            return Err(String::from("old canonical typed mode admitted casts"));
        }
    }
    if adapter::compile_canonical_typed_identity_byte_trace(&good, historical_profile())
        != Err(TypedEchoAdapterError::Layout(
            adapter::bridge::ByteEchoBridgeError::ProfileMismatch,
        ))
    {
        return Err(String::from("typed alias source foreign profile accepted"));
    }
    for effects in [
        vec![IdentityEffect::Input(0), IdentityEffect::Output(0)],
        vec![
            IdentityEffect::Input(0),
            IdentityEffect::Cast {
                result: 1,
                value: 0,
                type_id: 0,
            },
        ],
        vec![
            IdentityEffect::Input(0),
            IdentityEffect::Cast {
                result: 1,
                value: 0,
                type_id: 0,
            },
            IdentityEffect::Input(2),
            IdentityEffect::Output(1),
        ],
        vec![
            IdentityEffect::Input(0),
            IdentityEffect::Input(1),
            IdentityEffect::Cast {
                result: 2,
                value: 0,
                type_id: 0,
            },
            IdentityEffect::Output(2),
        ],
        vec![
            IdentityEffect::Input(0),
            IdentityEffect::Cast {
                result: 1,
                value: 0,
                type_id: 0,
            },
            IdentityEffect::Zero(2),
            IdentityEffect::Output(1),
        ],
    ] {
        let wire_bytes = wire(&typed_identity_effects(&effects)?)?;
        if adapter::compile_canonical_typed_identity_byte_trace(&wire_bytes, current_profile())
            != Err(TypedEchoAdapterError::UnsupportedTypedIr)
        {
            return Err(String::from("typed identity accepted unproved SSA"));
        }
    }
    Ok(())
}

#[expect(
    clippy::too_many_arguments,
    reason = "external publisher requires wire and artifact medium selections"
)]
fn publish_identity_byte_wire(
    profile: &str,
    bytes: &[u8],
    target: &Path,
    typed: bool,
    from_stdin: bool,
    capsule: bool,
) -> Result<Output, String> {
    let mut command = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"));
    let _required = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    let _mode = command.arg("--").arg("--identity-byte-trace");
    if from_stdin {
        let _stdin = command.arg(if typed {
            "--typed-stdin"
        } else {
            "--ternary-stdin"
        });
    } else {
        let path = target.with_extension(if typed { "mcti" } else { "mctr" });
        fs::write(&path, bytes).map_err(|error| format!("identity wire write: {error}"))?;
        let _path = command
            .arg(if typed {
                "--typed-file"
            } else {
                "--ternary-file"
            })
            .arg(path);
    }
    let mut child = command
        .stdin(if from_stdin {
            Stdio::piped()
        } else {
            Stdio::null()
        })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("identity publisher spawn: {error}"))?;
    if from_stdin {
        child
            .stdin
            .take()
            .ok_or("identity stdin pipe absent")?
            .write_all(bytes)
            .map_err(|error| format!("identity wire feed: {error}"))?;
    }
    child
        .wait_with_output()
        .map_err(|error| format!("identity publisher exit: {error}"))
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "real MCTI/MCTR publisher and general VM cross-check"
)]
fn canonical_identity_byte_trace_publishes_capsule_file_and_raw_stdin() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let canonical = wire(&typed_identity_fixture()?)?;
    let compiled =
        adapter::compile_canonical_typed_identity_byte_trace(&canonical, current_profile())
            .map_err(|error| format!("identity source fixture: {error:?}"))?;
    let typed_target = workspace.path("identity-typed-capsule.malbolge");
    let ternary_target = workspace.path("identity-mctr-raw.malbolge");
    for (typed, bytes, target, capsule, stdin) in [
        (true, canonical.as_slice(), &typed_target, true, false),
        (
            false,
            compiled.ternary_bytes(),
            &ternary_target,
            false,
            true,
        ),
    ] {
        let result = publish_identity_byte_wire(
            current_profile().id(),
            bytes,
            target,
            typed,
            stdin,
            capsule,
        )?;
        if !result.status.success() {
            return Err(format!(
                "identity byte publisher refused: {}",
                String::from_utf8_lossy(&result.stderr)
            ));
        }
        let admitted = restored_canonical_stdin_source(
            fs::read(target).map_err(|error| error.to_string())?,
            capsule,
        )?;
        if admitted != compiled.layout().source() {
            return Err(String::from("typed and ternary identity artifacts differ"));
        }
        let mut vm = ProfileMachine::from_source(current_profile(), &admitted, vec![0, 255, 71])
            .map_err(|error| format!("published identity VM load: {error:?}"))?;
        if !matches!(vm.run(6), Ok(RunOutcome::Terminated { steps: 6, .. }))
            || vm.output() != [0, 0, 255]
            || vm.input_consumed() != 2
        {
            return Err(String::from("published identity VM input/output mismatch"));
        }
    }
    let mut runner = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&typed_target)
        .arg("--input-stdin")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("identity general runner spawn: {error}"))?;
    runner
        .stdin
        .take()
        .ok_or("identity general guest stdin absent")?
        .write_all(&[255, 128, 0])
        .map_err(|error| format!("identity general guest input: {error}"))?;
    let result = runner
        .wait_with_output()
        .map_err(|error| format!("identity general runner status: {error}"))?;
    if !result.status.success() || result.stdout != [255, 255, 128] || !result.stderr.is_empty() {
        return Err(format!(
            "identity general runner effects mismatch: {result:?}"
        ));
    }
    Ok(())
}

#[test]
fn canonical_identity_byte_cli_rejects_profile_drift_and_existing_file() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let canonical = wire(&typed_identity_fixture()?)?;
    let wrong = workspace.path("wrong.malbolge");
    let profile_rejected = publish_identity_byte_wire(
        historical_profile().id(),
        &canonical,
        &wrong,
        true,
        true,
        false,
    )?;
    if profile_rejected.status.success() || wrong.exists() {
        return Err(String::from("identity publisher accepted foreign profile"));
    }
    let malformed = workspace.path("malformed.malbolge");
    let malformed_rejected = publish_identity_byte_wire(
        current_profile().id(),
        b"invalid MCTR",
        &malformed,
        false,
        false,
        true,
    )?;
    if malformed_rejected.status.success() || malformed.exists() {
        return Err(String::from("identity publisher accepted invalid MCTR"));
    }
    let occupied = workspace.path("occupied.malbolge");
    let sentinel = b"never overwrite an existing file";
    fs::write(&occupied, sentinel).map_err(|error| error.to_string())?;
    let occupied_rejected = publish_identity_byte_wire(
        current_profile().id(),
        &canonical,
        &occupied,
        true,
        false,
        true,
    )?;
    if occupied_rejected.status.success()
        || fs::read(&occupied).map_err(|error| error.to_string())? != sentinel
    {
        return Err(String::from("identity publisher clobbered target"));
    }
    Ok(())
}

#[test]
fn canonical_identity_byte_trace_exact_4096_cell_boundary() -> Result<(), String> {
    let mut effects = vec![
        IdentityEffect::Input(0),
        IdentityEffect::Cast {
            result: 1,
            value: 0,
            type_id: 0,
        },
    ];
    effects.extend(repeat_n(IdentityEffect::Output(1), 4094));
    let canonical = wire(&typed_identity_effects(&effects)?)?;
    let compiled =
        adapter::compile_canonical_typed_identity_byte_trace(&canonical, current_profile())
            .map_err(|error| format!("max identity typed source: {error:?}"))?;
    if compiled.layout().source().len() != 4096 {
        return Err(String::from("typed identity full code capacity disagrees"));
    }
    let mut vm =
        ProfileMachine::from_source(current_profile(), compiled.layout().source(), vec![255])
            .map_err(|error| format!("max typed identity VM: {error:?}"))?;
    if !matches!(vm.run(4096), Ok(RunOutcome::Terminated { steps: 4096, .. }))
        || vm.input_consumed() != 1
        || vm.output().len() != 4094
        || vm.output().iter().any(|byte| *byte != 255)
    {
        return Err(String::from("maximum typed identity guest output drift"));
    }
    effects.push(IdentityEffect::Output(1));
    let excess = wire(&typed_identity_effects(&effects)?)?;
    if adapter::compile_canonical_typed_identity_byte_trace(&excess, current_profile())
        != Err(TypedEchoAdapterError::UnsupportedTypedIr)
    {
        return Err(String::from("typed identity accepted 4097 code cells"));
    }
    Ok(())
}

fn typed_rotated_literal_module_with_outputs(byte: u8, outputs: usize) -> Result<Module, String> {
    let mut effects = vec![IdentityEffect::Literal { result: 0, byte }];
    effects.extend(repeat_n(IdentityEffect::Output(0), outputs));
    typed_identity_effects(&effects)
}

fn typed_rotated_literal_module(byte: u8) -> Result<Module, String> {
    typed_rotated_literal_module_with_outputs(byte, 1)
}

#[test]
fn canonical_typed_rotated_nonzero_literals_execute_guest_data_rotation() -> Result<(), String> {
    for (byte, outputs) in [
        (23, 1),
        (253, 1),
        (183, 2),
        (64, 2),
        (146, 3),
        (3, 3),
        (252, 3),
        (43, 4),
        (192, 4),
        (10, 5),
        (142, 5),
        (137, 5),
        (47, 6),
        (200, 6),
        (21, 7),
        (253, 7),
    ] {
        let typed = typed_rotated_literal_module_with_outputs(byte, outputs)?;
        let canonical = wire(&typed)?;
        if canonical_module(&canonical).map_err(|error| format!("seeded MCTI decode: {error:?}"))?
            != typed
        {
            return Err(String::from("seeded literal MCTI roundtrip drift"));
        }
        let compiled =
            adapter::compile_canonical_typed_rotated_byte_literal(&canonical, current_profile())
                .map_err(|error| format!("seeded typed {byte} admission: {error:?}"))?;
        let mctr = canonical_ternary_program(compiled.ternary_bytes())
            .map_err(|error| format!("seeded MCTR admission: {error:?}"))?;
        if mctr.source_sha256 != *typed.source_sha256()
            || mctr.source_id != typed.source_id()
            || mctr.target_profile != current_profile().id()
        {
            return Err(String::from("seeded typed source/profile drift"));
        }
        let admitted = adapter::bridge::encode_rotated_byte_literal(&mctr, current_profile())
            .map_err(|error| format!("seeded independent target: {error:?}"))?;
        if admitted != *compiled.layout() {
            return Err(String::from("seeded typed and MCTR source mismatch"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), admitted.source(), vec![255, 0, 128])
                .map_err(|error| format!("seeded typed guest load: {error:?}"))?;
        if !matches!(vm.run(admitted.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == admitted.executed_code_positions().len())
            || vm.output() != vec![byte; outputs]
            || vm.input_consumed() != 0
        {
            return Err(format!("seeded typed real guest did not print {byte}"));
        }
        if compile_canonical_typed_echo(&canonical, current_profile()).is_ok()
            || adapter::compile_canonical_typed_initial_zero_outputs(&canonical, current_profile())
                .is_ok()
        {
            return Err(String::from("legacy typed mode accepted nonzero"));
        }
    }
    Ok(())
}

#[test]
fn canonical_typed_rotated_literal_rejects_unproved_constants() -> Result<(), String> {
    for byte in [0, 1, 7, 24, 42, 128, 255] {
        let canonical = wire(&typed_rotated_literal_module(byte)?)?;
        if adapter::compile_canonical_typed_rotated_byte_literal(&canonical, current_profile())
            != Err(TypedEchoAdapterError::Layout(
                adapter::bridge::ByteEchoBridgeError::UnsupportedEffectTrace,
            ))
        {
            return Err(format!("typed nonwitness literal {byte} admitted"));
        }
    }
    for (byte, outputs, expected) in [
        (
            23,
            2,
            TypedEchoAdapterError::Layout(
                adapter::bridge::ByteEchoBridgeError::UnsupportedEffectTrace,
            ),
        ),
        (
            183,
            3,
            TypedEchoAdapterError::Layout(
                adapter::bridge::ByteEchoBridgeError::UnsupportedEffectTrace,
            ),
        ),
        (
            183,
            4,
            TypedEchoAdapterError::Layout(
                adapter::bridge::ByteEchoBridgeError::UnsupportedEffectTrace,
            ),
        ),
    ] {
        let canonical = wire(&typed_rotated_literal_module_with_outputs(byte, outputs)?)?;
        if adapter::compile_canonical_typed_rotated_byte_literal(&canonical, current_profile())
            != Err(expected)
        {
            return Err(format!(
                "typed unproved seeded shape {byte} x{outputs} admitted"
            ));
        }
    }
    let canonical = wire(&typed_rotated_literal_module(23)?)?;
    if adapter::compile_canonical_typed_rotated_byte_literal(&canonical, historical_profile())
        != Err(TypedEchoAdapterError::Layout(
            adapter::bridge::ByteEchoBridgeError::ProfileMismatch,
        ))
    {
        return Err(String::from(
            "typed seeded literal accepted foreign profile",
        ));
    }
    Ok(())
}

#[test]
fn canonical_typed_rotated_literal_rejects_unwitnessed_output_counts() -> Result<(), String> {
    for (byte, outputs) in [(43, 5), (183, 5), (255, 5), (21, 6), (47, 7), (10, 8)] {
        let canonical = wire(&typed_rotated_literal_module_with_outputs(byte, outputs)?)?;
        if adapter::compile_canonical_typed_rotated_byte_literal(&canonical, current_profile())
            != Err(TypedEchoAdapterError::Layout(
                adapter::bridge::ByteEchoBridgeError::UnsupportedEffectTrace,
            ))
        {
            return Err(format!(
                "typed unwitnessed output {byte} x{outputs} admitted"
            ));
        }
    }
    let unsupported_ninth = wire(&typed_rotated_literal_module_with_outputs(175, 9)?)?;
    if adapter::compile_canonical_typed_rotated_byte_literal(&unsupported_ninth, current_profile())
        != Err(TypedEchoAdapterError::Layout(
            adapter::bridge::ByteEchoBridgeError::UnsupportedEffectTrace,
        ))
    {
        return Err(String::from("typed ninth output admitted unwitnessed byte"));
    }
    let unsupported_tenth = wire(&typed_rotated_literal_module_with_outputs(144, 10)?)?;
    if adapter::compile_canonical_typed_rotated_byte_literal(&unsupported_tenth, current_profile())
        != Err(TypedEchoAdapterError::Layout(
            adapter::bridge::ByteEchoBridgeError::UnsupportedEffectTrace,
        ))
    {
        return Err(String::from("typed tenth output admitted unwitnessed byte"));
    }
    let unsupported_eleventh = wire(&typed_rotated_literal_module_with_outputs(42, 11)?)?;
    if adapter::compile_canonical_typed_rotated_byte_literal(
        &unsupported_eleventh,
        current_profile(),
    ) != Err(TypedEchoAdapterError::Layout(
        adapter::bridge::ByteEchoBridgeError::UnsupportedEffectTrace,
    )) {
        return Err(String::from(
            "typed eleventh output admitted unwitnessed byte",
        ));
    }
    let twelfth = wire(&typed_rotated_literal_module_with_outputs(9, 12)?)?;
    if adapter::compile_canonical_typed_rotated_byte_literal(&twelfth, current_profile())
        != Err(TypedEchoAdapterError::UnsupportedTypedIr)
    {
        return Err(String::from("typed twelfth output admitted"));
    }
    Ok(())
}

#[expect(
    clippy::too_many_arguments,
    reason = "canonical wire type and target framing are independent process choices"
)]
fn publish_seeded_byte_literal(
    profile: &str,
    bytes: &[u8],
    target: &Path,
    typed: bool,
    stdin: bool,
    capsule: bool,
) -> Result<Output, String> {
    let mut command = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"));
    let _required = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    let _mode = command.arg("--").arg("--seeded-byte-literal");
    if stdin {
        let _input = command.arg(if typed {
            "--typed-stdin"
        } else {
            "--ternary-stdin"
        });
    } else {
        let wire_path = target.with_extension(if typed { "mcti" } else { "mctr" });
        fs::write(&wire_path, bytes)
            .map_err(|error| format!("seeded literal fixture write: {error}"))?;
        let _path = command
            .arg(if typed {
                "--typed-file"
            } else {
                "--ternary-file"
            })
            .arg(wire_path);
    }
    let mut child = command
        .stdin(if stdin { Stdio::piped() } else { Stdio::null() })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("seeded literal publisher spawn: {error}"))?;
    if stdin {
        child
            .stdin
            .take()
            .ok_or("seeded literal stdin pipe absent")?
            .write_all(bytes)
            .map_err(|error| format!("feed seeded literal canonical wire: {error}"))?;
    }
    child
        .wait_with_output()
        .map_err(|error| format!("seeded literal publisher status: {error}"))
}

#[expect(
    clippy::too_many_lines,
    reason = "canonical wire and real runner assertions require both process stages"
)]
fn verify_seeded_publisher_case(
    workspace: &OwnedFixture,
    case: SeededPublisherCase,
) -> Result<(), String> {
    let (literal, outputs, typed, stdin, capsule) = case;
    let canonical = wire(&typed_rotated_literal_module_with_outputs(
        literal, outputs,
    )?)?;
    let compiled =
        adapter::compile_canonical_typed_rotated_byte_literal(&canonical, current_profile())
            .map_err(|error| format!("publisher seeded source: {error:?}"))?;
    let bytes = if typed {
        canonical.as_slice()
    } else {
        compiled.ternary_bytes()
    };
    let file = workspace.path(&format!(
        "seeded-{literal}-x{outputs}-capsule-{capsule}.malbolge"
    ));
    let outcome =
        publish_seeded_byte_literal(current_profile().id(), bytes, &file, typed, stdin, capsule)?;
    if !outcome.status.success() {
        return Err(format!(
            "seeded literal process rejected: {}",
            String::from_utf8_lossy(&outcome.stderr)
        ));
    }
    let source = restored_canonical_stdin_source(
        fs::read(&file).map_err(|error| error.to_string())?,
        capsule,
    )?;
    if source != compiled.layout().source() {
        return Err(String::from(
            "typed and MCTR seeded graphical source diverged",
        ));
    }
    // Raw graphical source has no profile metadata. Verify it with the
    // selected normative current VM; only capsules can select a modern
    // profile in the general runner without an explicit profile option.
    let mut vm = ProfileMachine::from_source(current_profile(), &source, vec![255, 0, 128])
        .map_err(|error| format!("seeded raw guest load: {error:?}"))?;
    if !matches!(vm.run(compiled.layout().executed_code_positions().len()),
        Ok(RunOutcome::Terminated { steps, .. })
            if steps == compiled.layout().executed_code_positions().len())
        || vm.output() != vec![literal; outputs]
        || vm.input_consumed() != 0
    {
        return Err(String::from("seeded current-profile VM mismatch"));
    }
    if capsule {
        let mut runner = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .arg(&file)
            .arg("--input-stdin")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|error| format!("seeded guest runner spawn: {error}"))?;
        runner
            .stdin
            .take()
            .ok_or("seeded runner stdin pipe missing")?
            .write_all(&[255, 0, 128])
            .map_err(|error| format!("seeded guest stdin: {error}"))?;
        let run = runner
            .wait_with_output()
            .map_err(|error| format!("seeded runner exit: {error}"))?;
        if !run.status.success() || run.stdout != vec![literal; outputs] || !run.stderr.is_empty() {
            return Err(format!(
                "guest runner did not compute literal {literal}: {run:?}"
            ));
        }
    }
    Ok(())
}

#[test]
fn seeded_byte_literal_canonical_publisher_and_real_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for case in [
        (23, 1, true, false, true),
        (253, 1, false, true, false),
        (253, 1, false, true, true),
    ] {
        verify_seeded_publisher_case(&workspace, case)?;
    }
    Ok(())
}

#[test]
fn seeded_double_literal_canonical_publisher_and_real_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for case in [(183, 2, true, false, true), (64, 2, false, true, true)] {
        verify_seeded_publisher_case(&workspace, case)?;
    }
    Ok(())
}

#[test]
fn seeded_triple_literal_canonical_publisher_and_real_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for case in [(146, 3, true, false, true), (3, 3, false, true, true)] {
        verify_seeded_publisher_case(&workspace, case)?;
    }
    Ok(())
}

#[test]
fn seeded_four_output_literal_canonical_publisher_and_real_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for case in [(43, 4, true, false, true), (192, 4, false, true, true)] {
        verify_seeded_publisher_case(&workspace, case)?;
    }
    Ok(())
}

#[test]
fn seeded_five_output_literal_canonical_publisher_and_real_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for case in [(10, 5, true, false, true), (137, 5, false, true, true)] {
        verify_seeded_publisher_case(&workspace, case)?;
    }
    Ok(())
}

#[test]
fn seeded_six_and_seven_output_canonical_publisher_and_real_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for case in [
        (47, 6, true, false, true),
        (200, 6, false, true, true),
        (21, 7, true, false, true),
        (253, 7, false, true, true),
    ] {
        verify_seeded_publisher_case(&workspace, case)?;
    }
    Ok(())
}

#[test]
fn seeded_eight_output_literal_canonical_publisher_and_real_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for case in [(175, 8, true, false, true), (197, 8, false, true, true)] {
        verify_seeded_publisher_case(&workspace, case)?;
    }
    Ok(())
}

#[test]
fn seeded_nine_output_literal_canonical_publisher_and_real_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for case in [(144, 9, true, false, true), (1, 9, false, true, true)] {
        verify_seeded_publisher_case(&workspace, case)?;
    }
    Ok(())
}

#[test]
fn seeded_ten_output_literal_canonical_publisher_and_real_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for case in [(42, 10, true, false, true), (193, 10, false, true, true)] {
        verify_seeded_publisher_case(&workspace, case)?;
    }
    Ok(())
}

#[test]
fn seeded_eleven_output_literal_canonical_publisher_and_real_runner() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    for case in [(9, 11, true, false, true), (135, 11, false, true, true)] {
        verify_seeded_publisher_case(&workspace, case)?;
    }
    Ok(())
}

#[test]
fn seeded_literal_publisher_refuses_unsupported_or_occupied_artifacts() -> Result<(), String> {
    let workspace = OwnedFixture::new()?;
    let correct = wire(&typed_rotated_literal_module(23)?)?;
    let wrong_profile = workspace.path("seed-wrong-profile.malbolge");
    let profile_outcome = publish_seeded_byte_literal(
        historical_profile().id(),
        &correct,
        &wrong_profile,
        true,
        false,
        false,
    )?;
    if profile_outcome.status.success() || wrong_profile.exists() {
        return Err(String::from("seeded publisher admitted foreign profile"));
    }
    let unsupported = workspace.path("seed-unsupported.malbolge");
    let wrong = wire(&typed_rotated_literal_module(24)?)?;
    let unsupported_outcome = publish_seeded_byte_literal(
        current_profile().id(),
        &wrong,
        &unsupported,
        true,
        true,
        true,
    )?;
    if unsupported_outcome.status.success() || unsupported.exists() {
        return Err(String::from("seeded publisher admitted unproved 24"));
    }
    let existing = workspace.path("seed-occupied.malbolge");
    let sentinel = b"no-clobber seeded literal";
    fs::write(&existing, sentinel).map_err(|error| error.to_string())?;
    let existing_outcome = publish_seeded_byte_literal(
        current_profile().id(),
        &correct,
        &existing,
        true,
        false,
        true,
    )?;
    if existing_outcome.status.success()
        || fs::read(&existing).map_err(|error| error.to_string())? != sentinel
    {
        return Err(String::from("seeded publisher overwrote occupied output"));
    }
    Ok(())
}
