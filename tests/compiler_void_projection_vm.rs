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
//   - Cross-stage evidence for one normalized C void-return semantic projection.
// - Must-Not:
//   - Treat a hand-projected frontend as a pinned-Clang parse of arbitrary C.
// - Allows:
//   - Inputs: one exact normalized void-return function and canonical typed IR.
//   - Outputs: source-bound MCTI, executable Malbolge and real VM observations.
//   - Side effects: owned ignored .temp fixtures only.
// - Split-When:
//   - Native C frontend-to-compiler orchestration owns process compilation.
// - Merge-When:
//   - Complete C compiler acceptance supersedes this bounded stage handoff.
// - Summary:
//   - Closes the normalized void frontend-to-verified guest target handoff.
// - Description:
//   - Compiler stages cannot silently invent guest return values or effects.
// - Usage:
//   - cargo test --test compiler_void_projection_vm.
// - Defaults:
//   - Rejected semantics never produce executable output.
//
//! Tests a typed projection of `void noop(void) { return; }`, not Clang parsing.

#[path = "../src/compiler/typed-echo-adapter/composition/lib.rs"]
pub mod adapter;

use std::fs;
use std::path::Path;
use std::process::{Command, id};

use adapter::typed::{
    FrontendArtifact, FrontendArtifactSpec, FrontendPosition, FrontendReturnVoidFunction,
    FrontendReturnVoidFunctionSpec, FrontendSpan, Terminator, TypeDef, TypeEntry, canonical_bytes,
    canonical_module, lower_frontend_artifact,
};
use malbolge::{ProfileMachine, RunOutcome, current_profile, parse_capsule};

// This is a source-offset-preserving normalized semantic projection. The
// native Clang frontend and a JSON-to-domain adapter are not yet wired here.
const C_SOURCE: &[u8] = b"void noop(void) { return; }\n";
const C_SOURCE_SHA256: [u8; 32] = [
    0xd3, 0x74, 0xbb, 0x94, 0xb0, 0x3d, 0x69, 0x02, 0xde, 0xb8, 0xb5, 0xcb, 0x25, 0xcf, 0x29, 0x13,
    0xd6, 0x3e, 0x21, 0x5d, 0x1a, 0x3e, 0xad, 0x8f, 0x75, 0x8b, 0x4a, 0x51, 0x4c, 0x24, 0xc5, 0x84,
];

const fn span(begin: u32, end: u32) -> FrontendSpan {
    FrontendSpan::new(
        FrontendPosition::new(begin, 1, begin.saturating_add(1)),
        FrontendPosition::new(end, 1, end.saturating_add(1)),
    )
}

fn void_projection() -> FrontendArtifact {
    // Source ranges: function 0..27, braces/body 16..27, return 18..25.
    FrontendArtifact::new_void(
        FrontendArtifactSpec {
            abi_id: String::from("malbolge-c32-v1"),
            artifact_id: String::from("malbolge-c-frontend-v1"),
            clang_target: String::from("wasm32-unknown-unknown"),
            clang_version: String::from("22.1.8"),
            functions: Vec::new(),
            language: String::from("c23"),
            schema_version: 1,
            source_id: String::from("fixtures/void-return.c"),
            source_sha256: C_SOURCE_SHA256,
            target_profile: String::from("malbolge-2026"),
        },
        FrontendReturnVoidFunction::new(FrontendReturnVoidFunctionSpec {
            body_span: span(16, 27),
            definition: String::from("definition"),
            function_span: span(0, 27),
            inline_specified: false,
            linkage: String::from("external"),
            name: String::from("noop"),
            return_span: span(18, 25),
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        }),
    )
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "canonical source projection invariants"
)]
fn source_bound_typed_bytes() -> Result<Vec<u8>, String> {
    assert_eq!(
        C_SOURCE.len(),
        28,
        "canonical C source fixture length changed"
    );
    assert_eq!(
        C_SOURCE.get(18..25),
        Some(b"return;".as_slice()),
        "void-return statement source location changed",
    );
    let module = lower_frontend_artifact(&void_projection())
        .map_err(|error| format!("normalized C lowering: {error:?}"))?;
    let [function] = module.functions() else {
        return Err(String::from("expected one normalized C function"));
    };
    let [block] = function.blocks() else {
        return Err(String::from("expected one normalized C block"));
    };
    assert!(
        block.instructions().is_empty(),
        "void return has no guest effects"
    );
    assert!(
        matches!(block.terminator(), Terminator::Return { value: None }),
        "void return cannot invent a guest value",
    );
    assert_eq!(
        module.source_sha256(),
        &C_SOURCE_SHA256,
        "typed module must retain exact source digest",
    );
    assert!(
        matches!(
            module.types().first().map(TypeEntry::definition),
            Some(TypeDef::U8)
        ),
        "void ABI must match the verified typed-to-ternary adapter",
    );
    let typed = canonical_bytes(&module)
        .map_err(|error| format!("encode normalized typed IR: {error:?}"))?;
    assert_eq!(
        canonical_module(&typed),
        Ok(module),
        "canonical typed wire must decode to the same normalized module",
    );
    Ok(typed)
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "real guest execution assertions")]
fn normalized_void_return_reaches_two_step_real_vm() -> Result<(), String> {
    let typed = source_bound_typed_bytes()?;
    let emitted = adapter::compile_canonical_typed_empty_void(&typed, current_profile())
        .map_err(|error| format!("compile normalized typed IR: {error:?}"))?;
    assert_eq!(emitted.layout().source().len(), 2);
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut vm =
            ProfileMachine::from_source(current_profile(), emitted.layout().source(), input)
                .map_err(|error| format!("load normalized target: {error:?}"))?;
        assert!(matches!(
            vm.run(2),
            Ok(RunOutcome::Terminated { steps: 2, .. })
        ));
        assert!(vm.output().is_empty());
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "external source publication and VM assertions"
)]
fn normalized_void_return_publishes_capsule_replayed_by_general_runner() -> Result<(), String> {
    let typed = source_bound_typed_bytes()?;
    let expected = adapter::compile_canonical_typed_empty_void(&typed, current_profile())
        .map_err(|error| format!("compile expected target: {error:?}"))?;
    let fixture = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join(".temp")
        .join(format!("compiler-void-projection-{}", id()));
    #[expect(clippy::create_dir, reason = "refuse a pre-existing test fixture path")]
    fs::create_dir(&fixture).map_err(|error| format!("create void projection fixture: {error}"))?;
    let result = (|| {
        let typed_path = fixture.join("normalized.mcti");
        let target = fixture.join("normalized.malbolge");
        fs::write(&typed_path, &typed).map_err(|error| format!("write typed wire: {error}"))?;
        let emitted = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
            .arg("--profile")
            .arg(current_profile().id())
            .arg("--output")
            .arg(&target)
            .arg("--capsule")
            .arg("--")
            .arg("--empty-void")
            .arg("--typed-file")
            .arg(&typed_path)
            .output()
            .map_err(|error| format!("publish normalized C projection: {error}"))?;
        if !emitted.status.success() {
            return Err(format!(
                "publisher rejected projection: {}",
                String::from_utf8_lossy(&emitted.stderr)
            ));
        }
        let bytes =
            fs::read(&target).map_err(|error| format!("read normalized target: {error}"))?;
        let capsule = parse_capsule(&bytes)
            .map_err(|error| format!("parse normalized capsule: {error}"))?
            .ok_or("normalized output is not a capsule")?;
        assert_eq!(capsule.profile(), current_profile());
        assert_eq!(capsule.payload(), expected.layout().source());
        let run = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .arg(&target)
            .arg("--report-steps")
            .output()
            .map_err(|error| format!("execute published C projection: {error}"))?;
        if !run.status.success() {
            return Err(format!(
                "guest runner rejected target: {}",
                String::from_utf8_lossy(&run.stderr)
            ));
        }
        assert!(run.stdout.is_empty());
        assert_eq!(run.stderr, b"malbolge-steps-v1:2\n");
        Ok(())
    })();
    let cleanup =
        fs::remove_dir_all(&fixture).map_err(|error| format!("remove projection fixture: {error}"));
    result?;
    cleanup
}
