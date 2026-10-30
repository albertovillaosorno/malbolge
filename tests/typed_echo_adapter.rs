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
use std::sync::atomic::{AtomicUsize, Ordering};

static TEST_SEQUENCE: AtomicUsize = AtomicUsize::new(0);

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
    reason = "owned fixture directory cleanup"
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
