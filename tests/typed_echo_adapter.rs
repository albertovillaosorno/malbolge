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
use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, id};
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
        target_profile: String::from("malbolge-2026"),
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
