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
//   - Exact signed unary putchar source admission and guest byte evidence.
// - Must-Not:
//   - Infer unchecked arithmetic or substitute host output for guest effects.
// - Allows:
//   - Inputs: pinned-Clang unary expression preorder with checked i32 values.
//   - Outputs: canonical typed IR, source spans, guest stdout or rejection.
//   - Side effects: one bounded normative VM run per positive fixture.
// - Split-When:
//   - General expression lowering replaces the exact unary literal admission.
// - Merge-When:
//   - A single source-C regression covers identical guarded behavior.
// - Summary:
//   - A unary C sign remains source-proven across byte output lowering.
// - Description:
//   - Signed negatives use C's putchar low-byte conversion, not host printing.
// - Usage:
//   - cargo test -p malbolge-c-frontend-json-adapter --test normalized_unary_output
// - Defaults:
//   - Pinned Clang source-to-guest execution is separately covered in Python.
//
//! Strict signed unary C literal admission with actual guest execution.

#[path = "../../typed-echo-adapter/composition/lib.rs"]
pub mod adapter;

use malbolge::{ProfileMachine, RunOutcome, target_profile};
use malbolge_c_frontend_json_adapter::{FrontendGuestMode, canonical_guest_typed_ir, typed};
use serde as _;
use serde_json::{Value, json};

fn span(begin: u32, end: u32) -> Value {
    json!({"begin":{"byte":begin,"line":2,"column":begin.saturating_sub(18)},
           "end":{"byte":end,"line":2,"column":end.saturating_sub(18)}})
}

// Exact one-call node shapes observed with pinned Clang 22.1.8 for
// `#include <stdio.h>\nvoid emit(void) { putchar(+65); }\n` and `-1`.
fn input(sign: &str, digits: &str) -> Value {
    let operand_end = 46 + u32::try_from(digits.len()).unwrap_or_default();
    let call_end = operand_end + 1;
    let body_end = call_end + 3;
    let value = if sign == "-" && digits != "0" {
        format!("-{digits}")
    } else {
        String::from(digits)
    };
    json!({
        "schema_version": 1,
        "artifact_id": "malbolge-c-frontend-v1",
        "clang": {"version":"22.1.8", "target":"wasm32-unknown-unknown", "language":"c23"},
        "profile": {"abi_id":"malbolge-c32-v1", "target_profile":"malbolge-2026"},
        "source": {"id":"unary.c", "sha256":
            "a89c18405bc20022ede681f378721e9ba71298fd250b2841417bfe1a01a43009"},
        "nodes": [
            {"id":1,"parent":0,"kind":"function-declaration","span":span(19,body_end),
             "name":"emit","type":"fn()->void","definition":"definition",
             "inline_specified":false,"linkage":"external","storage_class":"none"},
            {"id":2,"parent":1,"kind":"compound-statement","span":span(35,body_end)},
            {"id":3,"parent":2,"kind":"call-expression","span":span(37,call_end),
             "type":"i32","reference":"external:putchar"},
            {"id":4,"parent":3,"kind":"cast-expression","span":span(37,44),
             "type":"ptr(fn(i32)->i32)","operation":"function-to-pointer"},
            {"id":5,"parent":4,"kind":"declaration-reference-expression",
             "span":span(37,44),"type":"fn(i32)->i32","reference":"external:putchar"},
            {"id":6,"parent":3,"kind":"unary-expression","span":span(45,operand_end),
             "type":"i32","operation":sign,"constant_integer":value},
            {"id":7,"parent":6,"kind":"integer-literal","span":span(46,operand_end),
             "type":"i32","constant_integer":digits,"literal":digits}
        ]
    })
}

fn encode(value: &Value) -> Result<Vec<u8>, String> {
    serde_json::to_vec(value).map_err(|error| error.to_string())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "fail visibly for any mismatched source or guest output"
)]
fn unary_plus_a_reaches_real_malbolge_and_negative_one_preserves_signed_byte() -> Result<(), String>
{
    let profile = target_profile("malbolge-2026").ok_or("missing current target profile")?;
    for (sign, digits, expected) in [("+", "65", 65u8), ("-", "1", 255)] {
        let artifact = input(sign, digits);
        let (wire, mode) = canonical_guest_typed_ir(&encode(&artifact)?)
            .map_err(|error| format!("{sign}{digits} frontend failed: {error:?}"))?;
        assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
        let module = typed::canonical_module(&wire)
            .map_err(|error| format!("canonical typed IR: {error:?}"))?;
        let instructions = module
            .functions()
            .first()
            .and_then(|function| function.blocks().first())
            .ok_or("missing compiled instruction block")?
            .instructions();
        assert_eq!(
            instructions
                .first()
                .map(|effect| effect.span().begin().byte()),
            Some(45)
        );
        assert_eq!(
            instructions
                .first()
                .map(|effect| effect.span().end().byte()),
            Some(46 + u32::try_from(digits.len()).unwrap_or_default())
        );
        assert!(matches!(
            instructions.first().map(typed::LocatedInstruction::instruction),
            Some(typed::Instruction::ConstantInteger { constant, .. })
                if constant.bit_width() == 8 && constant.little_endian() == [expected]
        ));
        if expected == 65 {
            let compiled = adapter::compile_canonical_typed_rotated_byte_literal(&wire, profile)
                .map_err(|error| format!("guest A compilation: {error:?}"))?;
            let mut vm =
                ProfileMachine::from_source(profile, compiled.layout().source(), Vec::new())
                    .map_err(|error| format!("guest A load: {error:?}"))?;
            assert!(matches!(
                vm.run(compiled.layout().executed_code_positions().len()),
                Ok(RunOutcome::Terminated { .. })
            ));
            assert_eq!(vm.output(), &[65]);
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "guest signed zero must execute exactly"
)]
fn signed_unary_zero_preserves_guest_zero_output() -> Result<(), String> {
    let profile = target_profile("malbolge-2026").ok_or("missing current target profile")?;
    for sign in ["+", "-"] {
        let (wire, mode) = canonical_guest_typed_ir(&encode(&input(sign, "0"))?)
            .map_err(|error| format!("{sign}0 frontend: {error:?}"))?;
        assert_eq!(mode, FrontendGuestMode::InitialZeroOutput);
        let compiled = adapter::compile_canonical_typed_initial_zero_outputs(&wire, profile)
            .map_err(|error| format!("{sign}0 compiler: {error:?}"))?;
        let mut vm = ProfileMachine::from_source(profile, compiled.layout().source(), Vec::new())
            .map_err(|error| format!("{sign}0 VM: {error:?}"))?;
        assert!(matches!(
            vm.run(2),
            Ok(RunOutcome::Terminated { steps: 2, .. })
        ));
        assert_eq!(vm.output(), &[0]);
    }
    Ok(())
}

#[test]
fn unary_metadata_mutations_reject_before_guest_effects() -> Result<(), String> {
    for (field, replacement) in [
        ("operation", json!("~")),
        ("type", json!("u32")),
        ("constant_integer", json!("66")),
        ("literal", json!("1")),
        ("reference", json!("external:other")),
    ] {
        let mut artifact = input("+", "65");
        artifact["nodes"][5][field] = replacement;
        assert!(
            canonical_guest_typed_ir(&encode(&artifact)?).is_err(),
            "{field}"
        );
    }
    let mut forged = input("-", "1");
    forged["nodes"][5]["span"]["begin"]["byte"] = json!(46);
    assert!(canonical_guest_typed_ir(&encode(&forged)?).is_err());
    let mut forged = input("-", "1");
    forged["nodes"][6]["parent"] = json!(3);
    assert!(canonical_guest_typed_ir(&encode(&forged)?).is_err());
    let mut forged = input("-", "2147483648");
    forged["nodes"][6]["type"] = json!("i64");
    assert!(canonical_guest_typed_ir(&encode(&forged)?).is_err());
    Ok(())
}
