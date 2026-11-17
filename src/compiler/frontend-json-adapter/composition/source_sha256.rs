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
//   - Rechecking source bytes against the normalized C frontend SHA-256 claim.
// - Must-Not:
//   - Trust frontend-provided digest bytes without hashing the source witness.
// - Allows:
//   - Inputs: an exact immutable source byte stream.
//   - Outputs: deterministic 32-byte SHA-256 digest.
//   - Side effects: none.
// - Split-When:
//   - A maintained audited digest library becomes available at this boundary.
// - Merge-When:
//   - The native frontend and this adapter share one cryptographic verifier.
// - Summary:
//   - Rejects substituted source witnesses before any typed-IR publication.

//! Dependency-free SHA-256 adapted from this repository's algorithm runtime.

const SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];
pub(super) fn sha256(data: &[u8]) -> [u8; 32] {
    let bit_len = (data.len() as u64).wrapping_mul(8);
    let mut padded = Vec::with_capacity(data.len() + 72);
    padded.extend_from_slice(data);
    padded.push(0x80);
    while padded.len() % 64 != 56 {
        padded.push(0);
    }
    padded.extend_from_slice(&bit_len.to_be_bytes());
    let mut s = [
        0x6a09e667u32,
        0xbb67ae85,
        0x3c6ef372,
        0xa54ff53a,
        0x510e527f,
        0x9b05688c,
        0x1f83d9ab,
        0x5be0cd19,
    ];
    for chunk in padded.chunks_exact(64) {
        let mut w = [0u32; 64];
        for (i, x) in w[..16].iter_mut().enumerate() {
            let j = i * 4;
            *x = u32::from_be_bytes(
                chunk[j..j + 4].try_into().expect("sha word"),
            );
        }
        for i in 16..64 {
            let a = w[i - 15].rotate_right(7)
                ^ w[i - 15].rotate_right(18)
                ^ (w[i - 15] >> 3);
            let b = w[i - 2].rotate_right(17)
                ^ w[i - 2].rotate_right(19)
                ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(a)
                .wrapping_add(w[i - 7])
                .wrapping_add(b);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h) =
            (s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7]);
        for i in 0..64 {
            let q = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ (!e & g);
            let t1 = h
                .wrapping_add(q)
                .wrapping_add(ch)
                .wrapping_add(SHA256_K[i])
                .wrapping_add(w[i]);
            let p = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = p.wrapping_add(maj);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        for (i, x) in [a, b, c, d, e, f, g, h].iter().enumerate() {
            s[i] = s[i].wrapping_add(*x);
        }
    }
    let mut out = [0u8; 32];
    for (i, x) in s.iter().enumerate() {
        out[i * 4..i * 4 + 4].copy_from_slice(&x.to_be_bytes());
    }
    out
}

#[cfg(test)]
mod tests {
    use super::sha256;

    #[test]
    fn known_nist_vectors() {
        for (input, expected) in [
            (
                b"".as_slice(),
                concat!(
                    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991",
                    "b7852b855"
                ),
            ),
            (
                b"abc".as_slice(),
                concat!(
                    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff",
                    "61f20015ad"
                ),
            ),
        ] {
            let actual = sha256(input);
            let text: String =
                actual.iter().map(|byte| format!("{byte:02x}")).collect();
            assert_eq!(text, expected);
        }
    }
}
