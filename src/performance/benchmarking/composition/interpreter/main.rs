// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Reproducible CPU microbenchmark samples for VM word operations and
//     profile crazy chunk geometry.
// - Must-Not:
//   - Claim semantic authority or hide slower optimized implementations.
// - Allows:
//   - Inputs: public classic Word/profile-crazy APIs and independent scalar
//     word formulas.
//   - Outputs: raw nanosecond samples and deterministic checksums on stdout.
//   - Side effects: benchmark-process CPU time and stdout only.
// - Split-When:
//   - Split when full-machine workloads require independent benchmark control.
// - Merge-When:
//   - Merge when another interpreter benchmark owns the same word operations.
// - Summary:
//   - Measures rotate/crazy table paths and N10-N14 scalar/native/padded crazy
//     geometry.
// - Description:
//   - Emits raw samples so performance conclusions can retain dispersion data.
// - Usage:
//   - Run with `cargo run --release --bin interpreter_benchmark` on an
//   - identified host/toolchain.
// - Defaults:
//   - Uses fixed sample/repetition counts and alternates paired profile order.
//

//! Raw scalar-versus-table microbenchmarks for classic VM word operations.

use std::hint::black_box;
use std::io::{Error as IoError, ErrorKind, Result as IoResult, Write, stdout};
use std::time::Instant;

use malbolge::{
    BatchRequest, BatchResult, ExecutionMode, MAX_WORD_VALUE, RunOutcome, Word,
    execute_batch, execute_batch_parallel, profile_crazy,
};

const BATCH_JOBS: u8 = 96;
const BATCH_STEP_BUDGET: usize = 16;
const CRAZY_REPETITIONS: u16 = 16;
const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;
const PROFILE_CHUNK_MODULUS: u32 = 243;
const PROFILE_CHUNK_SQUARE: u32 = 59_049;
const PROFILE_CORPUS_SIZE: u32 = 59_049;
// Coprime to every 3^N, so each N10-N14 corpus contains no duplicate words.
const PROFILE_STRIDE: u32 = 104_729;
const PROFILE_CRAZY_GEOMETRIES: [ProfileCrazyGeometry; 5] = [
    ProfileCrazyGeometry {
        benchmark_label: "profile-crazy-10",
        native_label: "native-5+5",
        padded_label: "padded-5+5",
        padded_trits: 10,
        semantic_modulus: 59_049,
        semantic_trits: 10,
    },
    ProfileCrazyGeometry {
        benchmark_label: "profile-crazy-11",
        native_label: "native-5+5+1",
        padded_label: "padded-5+5+5",
        padded_trits: 15,
        semantic_modulus: 177_147,
        semantic_trits: 11,
    },
    ProfileCrazyGeometry {
        benchmark_label: "profile-crazy-12",
        native_label: "native-5+5+2",
        padded_label: "padded-5+5+5",
        padded_trits: 15,
        semantic_modulus: 531_441,
        semantic_trits: 12,
    },
    ProfileCrazyGeometry {
        benchmark_label: "profile-crazy-13",
        native_label: "native-5+5+3",
        padded_label: "padded-5+5+5",
        padded_trits: 15,
        semantic_modulus: 1_594_323,
        semantic_trits: 13,
    },
    ProfileCrazyGeometry {
        benchmark_label: "profile-crazy-14",
        native_label: "native-5+5+4",
        padded_label: "padded-5+5+5",
        padded_trits: 15,
        semantic_modulus: 4_782_969,
        semantic_trits: 14,
    },
];
const IO_ROUNDTRIP: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/tests/compatibility/specification/spec-io-roundtrip.malbolge",
));
const ROTATE_HIGH_TRIT_WEIGHT: u16 = 19_683;
const ROTATE_REPETITIONS: u16 = 128;
const SAMPLE_COUNT: u8 = 15;
const TRIT_COUNT: u8 = 10;

#[derive(Clone, Copy)]
struct ProfileCrazyGeometry {
    benchmark_label: &'static str,
    native_label: &'static str,
    padded_label: &'static str,
    padded_trits: u8,
    semantic_modulus: u32,
    semantic_trits: u8,
}

#[derive(Clone, Copy)]
enum ProfileCrazyImplementation {
    Native,
    Padded,
    Scalar,
}

impl ProfileCrazyImplementation {
    const fn label(self, geometry: ProfileCrazyGeometry) -> &'static str {
        match self {
            Self::Native => geometry.native_label,
            Self::Padded => geometry.padded_label,
            Self::Scalar => "scalar-tritwise",
        }
    }
}

fn batch_checksum(results: &[BatchResult]) -> u64 {
    let mut hash = FNV_OFFSET;
    for result in results {
        hash = result.error().map_or_else(
            || hash_byte(hash, 0),
            |_error| hash_byte(hash, u8::MAX),
        );
        if let Some(machine) = result.machine() {
            for byte in machine.output() {
                hash = hash_byte(hash, *byte);
            }
            let registers = machine.registers();
            hash = hash_word(hash, registers.accumulator);
            hash = hash_word(hash, registers.code_pointer);
            hash = hash_word(hash, registers.data_pointer);
        }
        hash = match result.outcome() {
            Some(RunOutcome::BudgetExhausted { steps }) => {
                hash_usize(hash_byte(hash, 1), steps)
            },
            Some(RunOutcome::Terminated { steps, .. }) => {
                hash_usize(hash_byte(hash, 2), steps)
            },
            None => hash_byte(hash, 3),
        };
    }
    hash
}

fn batch_requests() -> Vec<BatchRequest> {
    (0u8..BATCH_JOBS)
        .map(|byte| {
            BatchRequest::from_source(
                IO_ROUNDTRIP.to_vec(),
                vec![byte],
                ExecutionMode::Specification,
                BATCH_STEP_BUDGET,
            )
        })
        .collect()
}

fn benchmark_batch_parallel(worker_count: usize) -> u64 {
    match execute_batch_parallel(batch_requests(), worker_count) {
        Ok(results) => batch_checksum(&results),
        Err(_error) => 0,
    }
}

fn benchmark_batch_sequential() -> u64 {
    batch_checksum(&execute_batch(batch_requests()))
}

fn benchmark_crazy_optimized(words: &[Word]) -> u64 {
    let mut checksum = 0u64;
    let mut repetition = 0u16;
    while repetition < CRAZY_REPETITIONS {
        for (&data, &accumulator) in words.iter().zip(words.iter().rev()) {
            checksum = checksum.saturating_add(u64::from(
                black_box(data).crazy(black_box(accumulator)).value(),
            ));
        }
        repetition = repetition.saturating_add(1);
    }
    checksum
}

fn benchmark_crazy_scalar(words: &[Word]) -> u64 {
    let mut checksum = 0u64;
    let mut repetition = 0u16;
    while repetition < CRAZY_REPETITIONS {
        for (&data, &accumulator) in words.iter().zip(words.iter().rev()) {
            checksum = checksum.saturating_add(u64::from(
                crazy_scalar(black_box(data), black_box(accumulator)).value(),
            ));
        }
        repetition = repetition.saturating_add(1);
    }
    checksum
}

fn benchmark_profile_crazy_padded(
    words: &[u32],
    geometry: ProfileCrazyGeometry,
) -> u64 {
    let mut checksum = 0u64;
    let mut repetition = 0u16;
    while repetition < CRAZY_REPETITIONS {
        for (&data, &accumulator) in words.iter().zip(words.iter().rev()) {
            let value = profile_crazy_padded_unrolled(
                black_box(data),
                black_box(accumulator),
                geometry.padded_trits,
            )
            .rem_euclid(geometry.semantic_modulus);
            checksum = checksum.saturating_add(u64::from(value));
        }
        repetition = repetition.saturating_add(1);
    }
    checksum
}

fn benchmark_profile_crazy_scalar(
    words: &[u32],
    geometry: ProfileCrazyGeometry,
) -> u64 {
    let mut checksum = 0u64;
    let mut repetition = 0u16;
    while repetition < CRAZY_REPETITIONS {
        for (&data, &accumulator) in words.iter().zip(words.iter().rev()) {
            let value = profile_crazy_scalar(
                black_box(data),
                black_box(accumulator),
                geometry.semantic_trits,
            );
            checksum = checksum.saturating_add(u64::from(value));
        }
        repetition = repetition.saturating_add(1);
    }
    checksum
}

fn benchmark_profile_crazy_table(
    words: &[u32],
    geometry: ProfileCrazyGeometry,
    physical_trits: u8,
) -> u64 {
    let mut checksum = 0u64;
    let mut repetition = 0u16;
    while repetition < CRAZY_REPETITIONS {
        for (&data, &accumulator) in words.iter().zip(words.iter().rev()) {
            let value = profile_crazy(
                black_box(data),
                black_box(accumulator),
                physical_trits,
            )
            .rem_euclid(geometry.semantic_modulus);
            checksum = checksum.saturating_add(u64::from(value));
        }
        repetition = repetition.saturating_add(1);
    }
    checksum
}

fn benchmark_profile_crazy_implementation(
    words: &[u32],
    geometry: ProfileCrazyGeometry,
    implementation: ProfileCrazyImplementation,
) -> u64 {
    match implementation {
        ProfileCrazyImplementation::Scalar => {
            benchmark_profile_crazy_scalar(words, geometry)
        },
        ProfileCrazyImplementation::Native => benchmark_profile_crazy_table(
            words,
            geometry,
            geometry.semantic_trits,
        ),
        ProfileCrazyImplementation::Padded => {
            benchmark_profile_crazy_padded(words, geometry)
        },
    }
}

fn benchmark_rotate_optimized(words: &[Word]) -> u64 {
    let mut checksum = 0u64;
    let mut repetition = 0u16;
    while repetition < ROTATE_REPETITIONS {
        for &word in words {
            checksum = checksum
                .saturating_add(u64::from(black_box(word).rotate().value()));
        }
        repetition = repetition.saturating_add(1);
    }
    checksum
}

fn benchmark_rotate_scalar(words: &[Word]) -> u64 {
    let mut checksum = 0u64;
    let mut repetition = 0u16;
    while repetition < ROTATE_REPETITIONS {
        for &word in words {
            checksum = checksum.saturating_add(u64::from(
                rotate_scalar(black_box(word)).value(),
            ));
        }
        repetition = repetition.saturating_add(1);
    }
    checksum
}

fn crazy_scalar(data: Word, accumulator: Word) -> Word {
    let mut remaining_data = data.value();
    let mut remaining_accumulator = accumulator.value();
    let mut result = 0u16;
    let mut place = 1u16;
    let mut trit = 0u8;
    while trit < TRIT_COUNT {
        let output = crazy_trit_scalar(
            remaining_data.rem_euclid(3),
            remaining_accumulator.rem_euclid(3),
        );
        result = result.saturating_add(output.saturating_mul(place));
        place = place.saturating_mul(3);
        remaining_data = remaining_data.div_euclid(3);
        remaining_accumulator = remaining_accumulator.div_euclid(3);
        trit = trit.saturating_add(1);
    }
    Word::new(result).unwrap_or(Word::ZERO)
}

const fn crazy_trit_scalar(data: u16, accumulator: u16) -> u16 {
    if ((data == 0 || data == 1) && accumulator == 0)
        || (data == 2 && accumulator == 2)
    {
        1
    } else if (data == 1 && accumulator == 2)
        || (data == 2 && (accumulator == 0 || accumulator == 1))
    {
        2
    } else {
        0
    }
}

fn profile_crazy_padded_unrolled(
    data: u32,
    accumulator: u32,
    padded_trits: u8,
) -> u32 {
    let low = profile_crazy(
        data.rem_euclid(PROFILE_CHUNK_MODULUS),
        accumulator.rem_euclid(PROFILE_CHUNK_MODULUS),
        5,
    );
    let middle = profile_crazy(
        data.div_euclid(PROFILE_CHUNK_MODULUS)
            .rem_euclid(PROFILE_CHUNK_MODULUS),
        accumulator
            .div_euclid(PROFILE_CHUNK_MODULUS)
            .rem_euclid(PROFILE_CHUNK_MODULUS),
        5,
    );
    let two_chunks =
        low.saturating_add(middle.saturating_mul(PROFILE_CHUNK_MODULUS));
    if padded_trits == 10 {
        return two_chunks;
    }
    let high = profile_crazy(
        data.div_euclid(PROFILE_CHUNK_SQUARE)
            .rem_euclid(PROFILE_CHUNK_MODULUS),
        accumulator
            .div_euclid(PROFILE_CHUNK_SQUARE)
            .rem_euclid(PROFILE_CHUNK_MODULUS),
        5,
    );
    two_chunks.saturating_add(high.saturating_mul(PROFILE_CHUNK_SQUARE))
}

fn profile_crazy_scalar(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
    let mut result = 0u32;
    let mut place = 1u32;
    let mut trit = 0u8;
    while trit < trits {
        let data_digit = u16::try_from(data.rem_euclid(3)).ok().unwrap_or(0);
        let accumulator_digit =
            u16::try_from(accumulator.rem_euclid(3)).ok().unwrap_or(0);
        let output =
            u32::from(crazy_trit_scalar(data_digit, accumulator_digit));
        result = result.saturating_add(output.saturating_mul(place));
        data = data.div_euclid(3);
        accumulator = accumulator.div_euclid(3);
        place = place.saturating_mul(3);
        trit = trit.saturating_add(1);
    }
    result
}

/// Runs the fixed benchmark matrix and emits raw CSV samples.
///
/// # Errors
///
/// Returns an I/O error if writing benchmark samples to stdout fails.
pub fn run() -> IoResult<()> {
    let words = classic_words();
    let mut output = stdout().lock();
    writeln!(
        output,
        "benchmark,implementation,sample,nanoseconds,checksum"
    )?;
    emit_samples(&mut output, "batch-96", "sequential", || {
        benchmark_batch_sequential()
    })?;
    emit_samples(&mut output, "batch-96", "parallel-1", || {
        benchmark_batch_parallel(1)
    })?;
    emit_samples(&mut output, "batch-96", "parallel-2", || {
        benchmark_batch_parallel(2)
    })?;
    emit_samples(&mut output, "batch-96", "parallel-4", || {
        benchmark_batch_parallel(4)
    })?;
    emit_samples(&mut output, "batch-96", "parallel-8", || {
        benchmark_batch_parallel(8)
    })?;
    emit_samples(&mut output, "crazy", "scalar", || {
        benchmark_crazy_scalar(&words)
    })?;
    emit_samples(&mut output, "crazy", "table", || {
        benchmark_crazy_optimized(&words)
    })?;
    emit_profile_crazy_matrix(&mut output)?;
    emit_samples(&mut output, "rotate", "scalar", || {
        benchmark_rotate_scalar(&words)
    })?;
    emit_samples(&mut output, "rotate", "table", || {
        benchmark_rotate_optimized(&words)
    })?;
    Ok(())
}

fn classic_words() -> Vec<Word> {
    let mut words =
        Vec::with_capacity(usize::from(MAX_WORD_VALUE).saturating_add(1));
    let mut raw = 0u16;
    loop {
        if let Ok(word) = Word::new(raw) {
            words.push(word);
        }
        if raw == MAX_WORD_VALUE {
            break;
        }
        raw = raw.saturating_add(1);
    }
    words
}

fn emit_profile_crazy_matrix(output: &mut impl Write) -> IoResult<()> {
    for geometry in PROFILE_CRAZY_GEOMETRIES {
        let words = profile_words(geometry);
        emit_profile_crazy_samples(output, &words, geometry)?;
    }
    Ok(())
}

fn emit_profile_crazy_samples(
    output: &mut impl Write,
    words: &[u32],
    geometry: ProfileCrazyGeometry,
) -> IoResult<()> {
    let scalar = black_box(benchmark_profile_crazy_implementation(
        words,
        geometry,
        ProfileCrazyImplementation::Scalar,
    ));
    let native = black_box(benchmark_profile_crazy_implementation(
        words,
        geometry,
        ProfileCrazyImplementation::Native,
    ));
    let padded = black_box(benchmark_profile_crazy_implementation(
        words,
        geometry,
        ProfileCrazyImplementation::Padded,
    ));
    if scalar != native || scalar != padded {
        return Err(IoError::new(
            ErrorKind::InvalidData,
            "profile crazy benchmark implementations disagree",
        ));
    }
    let mut sample = 0u8;
    while sample < SAMPLE_COUNT {
        let order = match sample.rem_euclid(3) {
            0 => [
                ProfileCrazyImplementation::Scalar,
                ProfileCrazyImplementation::Native,
                ProfileCrazyImplementation::Padded,
            ],
            1 => [
                ProfileCrazyImplementation::Native,
                ProfileCrazyImplementation::Padded,
                ProfileCrazyImplementation::Scalar,
            ],
            _ => [
                ProfileCrazyImplementation::Padded,
                ProfileCrazyImplementation::Scalar,
                ProfileCrazyImplementation::Native,
            ],
        };
        for implementation in order {
            emit_profile_crazy_sample(
                output,
                words,
                geometry,
                (implementation, sample),
            )?;
        }
        sample = sample.saturating_add(1);
    }
    Ok(())
}

fn emit_profile_crazy_sample(
    output: &mut impl Write,
    words: &[u32],
    geometry: ProfileCrazyGeometry,
    identity: (ProfileCrazyImplementation, u8),
) -> IoResult<()> {
    let (implementation, sample) = identity;
    emit_sample(
        output,
        (
            geometry.benchmark_label,
            implementation.label(geometry),
            sample,
        ),
        || {
            benchmark_profile_crazy_implementation(
                words,
                geometry,
                implementation,
            )
        },
    )
}

fn profile_words(geometry: ProfileCrazyGeometry) -> Vec<u32> {
    (0..PROFILE_CORPUS_SIZE)
        .map(|index| {
            index
                .wrapping_mul(PROFILE_STRIDE)
                .rem_euclid(geometry.semantic_modulus)
        })
        .collect()
}

fn emit_samples<Run>(
    output: &mut impl Write,
    benchmark: &str,
    implementation: &str,
    mut run: Run,
) -> IoResult<()>
where
    Run: FnMut() -> u64,
{
    let warmup_checksum = black_box(run());
    let _warmup_sink = black_box(warmup_checksum);
    let mut sample = 0u8;
    while sample < SAMPLE_COUNT {
        emit_sample(output, (benchmark, implementation, sample), &mut run)?;
        sample = sample.saturating_add(1);
    }
    Ok(())
}

fn emit_sample<Run>(
    output: &mut impl Write,
    identity: (&str, &str, u8),
    mut run: Run,
) -> IoResult<()>
where
    Run: FnMut() -> u64,
{
    let (benchmark, implementation, sample) = identity;
    let start = Instant::now();
    let checksum = black_box(run());
    let elapsed = start.elapsed();
    let nanoseconds = elapsed.as_nanos();
    writeln!(
        output,
        "{benchmark},{implementation},{sample},{nanoseconds},{checksum}"
    )
}

fn hash_byte(hash: u64, value: u8) -> u64 {
    (hash ^ u64::from(value)).wrapping_mul(FNV_PRIME)
}

fn hash_usize(hash: u64, value: usize) -> u64 {
    value.to_le_bytes().into_iter().fold(hash, hash_byte)
}

fn hash_word(mut hash: u64, value: Word) -> u64 {
    for byte in value.value().to_le_bytes() {
        hash = hash_byte(hash, byte);
    }
    hash
}

const fn rotate_scalar(value: Word) -> Word {
    let raw = value.value();
    let quotient = raw.div_euclid(3);
    let low_trit = raw.rem_euclid(3);
    let rotated = quotient
        .saturating_add(low_trit.saturating_mul(ROTATE_HIGH_TRIT_WEIGHT));
    match Word::new(rotated) {
        Ok(word) => word,
        Err(_error) => Word::ZERO,
    }
}
