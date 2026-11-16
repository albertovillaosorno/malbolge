# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Stable teaching C/guest pair identities and real VM replay.
# - Must-Not:
#   - Replace guest execution with a host C run or loosen digest comparisons.
# - Allows:
#   - Inputs: retained example files and repository-pinned local tools.
#   - Outputs: byte-exact regeneration, digest and guest-stdout evidence.
#   - Side effects: temporary compiler output under project-local .temp.
# - Split-When:
#   - The fixed challenge corpus introduces a separate fixture family.
# - Merge-When:
#   - A shared corpus runner can verify identical source/artifact contracts.
# - Summary:
#   - Replay checked-in Malbolge programs and their C compiler provenance.
# - Description:
#   - Compiler output identity and normative guest behavior are separate tests.
# - Usage:
#   - python3.14 -B -m unittest tests.test_versioned_example_corpus -v
# - Defaults:
#   - Portable digest check always runs; tool-dependent tests skip if absent.

"""Retained C-to-guest examples must be executable and reproducible."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import final

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs/technical/examples/corpus"
DRIVER = ROOT / "src/interface/command-line/composition/scripts/c2malbolge.py"
FRONTEND = ROOT / ".dependencies/compiler-c-frontend/22.1.8/bin/malbolge-c-frontend"
RESOURCE = ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
GUEST_INCLUDE = ROOT / "src/runtime/guest-c-library/contract/include"
BIN_ROOT = Path(
    os.environ.get("MALBOLGE_CORPUS_BIN_ROOT", str(ROOT / ".cache/rust/target/debug"))
)
ADAPTER = BIN_ROOT / "c2malbolge_json"
LAYOUT = BIN_ROOT / "malbolge_layout"
VM = BIN_ROOT / "malbolge"


@dataclass(frozen=True, slots=True)
class Case:
    stem: str
    source_sha256: str
    capsule_sha256: str
    stdout: bytes
    steps: int
    size: int

    @property
    def source(self) -> Path:
        return CORPUS / f"{self.stem}.c"

    @property
    def capsule(self) -> Path:
        return CORPUS / f"{self.stem}.malbolge"


CASES = (
    Case(
        "emit-qp",
        "d2138a5388fd64358c0bfdeec8404fd2d1e310617011379abc475545367c96e9",
        "4112557f6f320f8827278ff8b623fddba73812c49801569093e815f27a9fa2b8",
        b"Q.",
        8,
        1111,
    ),
    Case(
        "emit-zph",
        "886dbf337d7f685c2afa04eec03767674fe9cec9a9f4650029999b750cff1a0f",
        "44ef08f92ac1c352ff5df820e63d4830664b6f7a569cd6e0f5504deb4cba9eb8",
        b"Z%H",
        8,
        1111,
    ),
    Case(
        "emit-t4",
        "adf878d0935344d5f0a103544988927bc0994fa7e12c236521ef5d28650beecd",
        "9ee602682624425da80c13786df338c80df15a65e1df083613c37100ed81f72d",
        b"T=4>",
        21,
        1215,
    ),
    Case(
        "emit-qesc79",
        "6f46d7d7e2789646f24e018c4af21f9399474197bc58670ad59a8f5361f39abd",
        "09be18cd3358663cf7c8434f4b4c910f9ae2a87f0e6b799238372d2110fae2b6",
        b'Q"\x1b79',
        23,
        1231,
    ),
    Case(
        "emit-qop6",
        "0de0b18a8b5abfd5a6271062c350ab18fddf621546cfa97785e4205a4eb0698c",
        "bcf659b66b69e7dac57505ac70a516451b60393bc9a2510d6fd6a59d897b7a76",
        bytes((0x51, 0x1C, 0x4F, 0x1D, 0x50, 0x1B)),
        15,
        1167,
    ),
    Case(
        "emit-seven",
        "08f98ac45b496d4ceed5c85efefdff0b91c20ed0a2a76687f90538f2924ffbbe",
        "4f0c732c3b55dd48b12795044f106989ffc84cd7839bcbff1e11c1b9643b99f8",
        bytes((0x36, 0x3E, 0x35, 0x02, 0x54, 0x1F, 0x18)),
        21,
        1215,
    ),
    Case(
        "emit-eight",
        "2dad8927207bd98292974ae068b6c0213d16efd3348fa404abf8228f640a0489",
        "59106439d2b0c203a6f934952adcd10b1d0dae7049df62fb708da48203e8a578",
        bytes((0x53, 0x20, 0x17, 0x3C, 0x36, 0x01, 0x52, 0x06)),
        21,
        1215,
    ),
    Case(
        "emit-nine",
        "256a09a44911bfbd8371438e10cd6b4068d78a0e47fcad91accd31cb77b1966a",
        "1d09fccde1f7d346ebc7e72439b82544da2dda37ff2a6e93b020996189e7bbeb",
        bytes((0x54, 0x3D, 0x8D, 0xD1, 0xC0, 0xB4, 0xBF, 0xD2, 0xA2)),
        21,
        1215,
    ),
    Case(
        "emit-ten",
        "92c5aa4ac7210f84073ef50e34db1ae8a462343023ef5969473de0ee85128277",
        "7befd3c590d03e94889bc93348bb37c51358f4b719dc2f371e07f918130386b0",
        bytes((0x51, 0x22, 0xFD, 0xCE, 0xA5, 0x98, 0xBA, 0xB6, 0x87, 0xCB)),
        23,
        1231,
    ),
    Case(
        "emit-eleven",
        "ecc66119b9e63dfdee3e33a82c2b76c07b59219f4ad81fe47f6147d572dd9aa9",
        "6b7381c638e959fa3f1cca6376317340c4278c4611bc518aa54b4ce2fcc6d8af",
        bytes((0x50, 0x1D, 0x1A, 0x36, 0x05, 0xB4, 0xBA, 0xB3, 0x84, 0xCF, 0x9E)),
        24,
        1239,
    ),
    Case(
        "emit-twelve",
        "6100ffbb742b162bba01f9df5890edf9497f19e19c0c535534ee01fc01ebddfb",
        "5bc03bb8ce1d9ab95a9aad99d387d4752f148c5be30dcab7919ffd53fbc52a34",
        bytes((0x51, 0x37, 0x34, 0x38, 0xFB, 0xCE, 0x9F, 0x98, 0xB8, 0xB4, 0x83, 0xCD)),
        27,
        1263,
    ),
    Case(
        "emit-thirteen",
        "4cf2ebd351daf7795b4bd6108b7b9acea5f1d45769af660fbe27eac191debdd8",
        "10b08a4c61f6e5a28f9ef1e01809cdc455178b0523328205bb101325c7a78bc5",
        bytes(
            (
                0x42,
                0x43,
                0x30,
                0x16,
                0x54,
                0x09,
                0xBF,
                0xC6,
                0xC8,
                0x87,
                0xE3,
                0xAB,
                0xA4,
            )
        ),
        29,
        1279,
    ),
    Case(
        "emit-fourteen",
        "175baa125b40d5c2986d2bc56f93e63cfd2d65091e1597b48447e02e03b46050",
        "e3ea5ad67954382872f2f2a6dbd03dfb497a91a52a1fbe04d2aa92afd9e7b438",
        bytes(
            (
                0x59,
                0x45,
                0x2C,
                0x48,
                0x53,
                0x17,
                0x4C,
                0x4F,
                0x3D,
                0x40,
                0x5B,
                0x31,
                0x19,
                0x34,
            )
        ),
        31,
        1295,
    ),
    Case(
        "emit-fifteen",
        "2b649eff0f561ab94977bbf95fd8c062cb5534f8067f8eaf64f8acffbba40a0a",
        "c69df83c4073806ef27c976de1a029a9f550ad7937e3432a7bda0908a8b58d9b",
        bytes(
            (
                0x51,
                0x2E,
                0x19,
                0x38,
                0x3E,
                0x89,
                0xD2,
                0xAD,
                0xA3,
                0xB7,
                0xC8,
                0x88,
                0x08,
                0xD5,
                0xC6,
            )
        ),
        33,
        1311,
    ),
    Case(
        "emit-sixteen",
        "ec64864dbcdf552917b4de490f1ed483a5059ded1d57cbf8ed5f098b89b1a86f",
        "74ad2a4f6cb71221199a1bbeaa79feb8639c10d0646f697442c42aea96d5b094",
        bytes(
            (
                0x3F,
                0x49,
                0x36,
                0x13,
                0x5A,
                0x0A,
                0xBA,
                0xB3,
                0xC3,
                0x86,
                0xCC,
                0xAA,
                0x01,
                0x07,
                0xD5,
                0xC5,
            )
        ),
        35,
        1327,
    ),
    Case(
        "emit-seventeen",
        "263893349a361c04dcc625e33b9c8a1227d137594e4f18e01434aefcc185e8f9",
        "2f2087fcac832159d1759b9d1b3fd7da96f51904eafd27eda84f2242573df952",
        bytes(
            (
                0x59,
                0x3F,
                0x2C,
                0x48,
                0x50,
                0x1B,
                0x18,
                0x32,
                0x15,
                0x4D,
                0x4B,
                0x3B,
                0x42,
                0x0F,
                0x44,
                0x30,
                0x17,
            )
        ),
        37,
        1343,
    ),
    Case(
        "emit-eighteen",
        "78732a00faab500e389a44a5974cce3e0bafedc4ddc292c1f11e9c00db621f3e",
        "23855763efbc636c108d5da73b723391e66d481c489de17482344b37326c5b8a",
        bytes(
            (
                0x54,
                0x22,
                0x19,
                0x3E,
                0x38,
                0x03,
                0x09,
                0xDD,
                0x87,
                0xD1,
                0xA5,
                0x99,
                0xBF,
                0x08,
                0xC7,
                0xC6,
                0xC2,
                0x91,
            )
        ),
        39,
        1359,
    ),
    Case(
        "emit-nineteen",
        "8e24c37b466ba4603321884abc17ef2dffe0a7a937600ffc48f1913bd68c900a",
        "7836c69e89d97d7d82b1fcec171199e34a1223a2f239447e62f696737ced1379",
        bytes(
            (
                0x53,
                0x21,
                0x1A,
                0x3C,
                0x38,
                0x03,
                0x17,
                0x55,
                0x0E,
                0x49,
                0x2B,
                0x10,
                0x46,
                0x16,
                0x40,
                0x4C,
                0x3A,
                0x19,
                0x58,
            )
        ),
        40,
        1367,
    ),
    Case(
        "emit-twenty",
        "409e71280abefe32cc574c19050e5fdb539104cbe20b1dbba6bf839905373536",
        "e0f9a1d80c98be4a5d1c1bc5fa9800772e2e7fafc8fbbc4a22b72409e9eedfcb",
        bytes(
            (
                0x3E,
                0x14,
                0x35,
                0x12,
                0x3F,
                0x0A,
                0xA4,
                0x9C,
                0xAD,
                0xA3,
                0x1A,
                0xA8,
                0xA2,
                0x95,
                0xAB,
                0x9F,
                0x98,
                0x1D,
                0xAC,
                0xAE,
            )
        ),
        54,
        1479,
    ),
    Case(
        "emit-twenty-one",
        "e565097636ef21b5bbecc1373dde4045564e1f59275fae1128c537515bc2f8b4",
        "4d5bc3b62c7525898863d2a3b9dae6f62f8700ab6ae6f3557425896c9f6f661d",
        bytes(
            (
                0x41,
                0x0E,
                0x3B,
                0x0F,
                0x3F,
                0x0A,
                0x40,
                0x8E,
                0x26,
                0x92,
                0x27,
                0x96,
                0x22,
                0x97,
                0x8D,
                0x15,
                0x31,
                0x18,
                0x35,
                0x1A,
                0x2F,
            )
        ),
        60,
        1527,
    ),
    Case(
        "emit-twenty-two",
        "211e9babb6f29f2984ef8e0ac53e48df1dac8fd7849e634d9767ada6e3c6a765",
        "8d65a853bf783a7af690f44aa04029838bf9056179eee1033c04ac972c0c1fdb",
        bytes(
            (
                0x39,
                0x16,
                0x37,
                0x05,
                0x41,
                0x0C,
                0x30,
                0x8E,
                0x24,
                0x9F,
                0x1B,
                0xA0,
                0x23,
                0x97,
                0x15,
                0x28,
                0x27,
                0x29,
                0x14,
                0x32,
                0x1E,
                0x1F,
            )
        ),
        57,
        1503,
    ),
    Case(
        "emit-twenty-three",
        "bc1baa982f773d8292d266d34375782a9ce1d8505c9af008cb46683507c58dd1",
        "6a4351b4fb7afc894fca6ac00790b97de44db6150ffd955c13a5462ba08b8f66",
        bytes(
            (
                0x42,
                0x0E,
                0x2F,
                0x17,
                0x39,
                0x04,
                0x8E,
                0x24,
                0x9F,
                0x1B,
                0xA0,
                0x23,
                0x97,
                0x15,
                0x28,
                0x27,
                0x29,
                0x14,
                0x32,
                0x1E,
                0x8B,
                0x26,
                0x92,
            )
        ),
        57,
        1503,
    ),
    Case(
        "emit-twenty-four",
        "40d4e9e55b35b660f41128b22b532a96ff55cb8f500ae1ea3a9afcc3dee22853",
        "97cbe0aa9f95c315919cfec5f3cfbc151f3f31e28fd1272bf740bb2e0f1f2f73",
        bytes(
            (
                0x3E,
                0x0B,
                0x2C,
                0x12,
                0x36,
                0x01,
                0x3D,
                0x95,
                0x0F,
                0x9D,
                0x17,
                0x8B,
                0x21,
                0x93,
                0x92,
                0x20,
                0x94,
                0x0E,
                0x9B,
                0x18,
                0x8A,
                0x1C,
                0x2F,
                0x23,
            )
        ),
        72,
        1623,
    ),
    Case(
        "emit-twenty-five",
        "bfff8a7925d5c6e35ec0b8577dbaf75a5abea0d92e3ebbf319f2daeba45af741",
        "2d58c920bb132efe10668d4f6035bdf8ed988c2114323f7ac859277ac2579683",
        bytes(
            (
                0x51,
                0x3E,
                0x35,
                0x38,
                0x54,
                0x1F,
                0x4E,
                0x33,
                0x3D,
                0x39,
                0x05,
                0x53,
                0x23,
                0x1B,
                0xB5,
                0x2C,
                0xCB,
                0x12,
                0xC6,
                0x2E,
                0xAF,
                0xB4,
                0xF8,
                0xCA,
                0x0E,
            )
        ),
        105,
        1887,
    ),
    Case(
        "emit-twenty-six",
        "7f5c459abdf70f50605b68f198d1618503db49eef78d2acfb31ee150e46045d9",
        "ee6f2e7133685a4c913c2cc2a6ba54664f34ab8f5f6a0623b63caf84bd81c586",
        bytes(
            (
                0x51,
                0x3E,
                0x35,
                0x38,
                0x54,
                0x1F,
                0x4E,
                0x33,
                0x3D,
                0x39,
                0x05,
                0x53,
                0x23,
                0x1B,
                0xB5,
                0x2C,
                0xCB,
                0x12,
                0xC6,
                0x2E,
                0xAF,
                0xB4,
                0xF8,
                0xCA,
                0x0E,
                0x95,
            )
        ),
        105,
        1887,
    ),
    Case(
        "emit-twenty-seven",
        "a3af465616fd176da3c19e53c0a2421ca0f5ac4dad3cadd6059291aea46bd4a0",
        "bd99663a6cef14f03546a72c4236a6849b35770733da141c652cf433da4f0ff9",
        bytes(
            (
                0x51,
                0x3E,
                0x35,
                0x38,
                0x54,
                0x1F,
                0x4E,
                0x33,
                0x3D,
                0x39,
                0x05,
                0x53,
                0x23,
                0x1B,
                0xB5,
                0x2C,
                0xCB,
                0x12,
                0xC6,
                0x2E,
                0xAF,
                0xB4,
                0xF8,
                0xCA,
                0x0E,
                0x95,
                0x2D,
            )
        ),
        105,
        1887,
    ),
    Case(
        "emit-twenty-eight",
        "8712784e9ac4722c983d92dd123a852164879fc6f11841be609167a5f4037743",
        "05e36945d4660f14ebab4efe600b2f6b44fdc7dcf0369055c90099def82aeb50",
        bytes(
            (
                0x51,
                0x3E,
                0x35,
                0x38,
                0x54,
                0x1F,
                0x4E,
                0x33,
                0x3D,
                0x39,
                0x05,
                0x53,
                0x23,
                0x1B,
                0xB5,
                0x2C,
                0xCB,
                0x12,
                0xC6,
                0x2E,
                0xAF,
                0xB4,
                0xF8,
                0xCA,
                0x0E,
                0x95,
                0x2D,
                0xAB,
            )
        ),
        105,
        1887,
    ),
    Case(
        "emit-twenty-nine",
        "08d6b10d70725ea0593230765831c5f2cd21ec374f052596c0a30b7aa4c5207b",
        "0066976f557e119fa30b580fe6c73018dd4ca922700a7796a59d0acea2f46d26",
        bytes(
            (
                0x87,
                0xB7,
                0xBC,
                0xB1,
                0x8A,
                0xCE,
                0x9F,
                0x9C,
                0xB5,
                0x2C,
                0xCB,
                0x12,
                0xC6,
                0x2E,
                0xAF,
                0xB4,
                0xF8,
                0xCA,
                0x0E,
                0x95,
                0x2D,
                0xAB,
                0x33,
                0x3D,
                0x39,
                0x05,
                0x53,
                0x23,
                0x1B,
            )
        ),
        105,
        1887,
    ),
    Case(
        "emit-thirty",
        "e3078c1ddf6a7d82af2fcd03d7bccd43b034b2723f821039b413129e8487242a",
        "778fc6a678185dddff20772d58641335a1131af08cd28403fa364952286506f9",
        bytes(
            (
                0x39,
                0xA8,
                0x07,
                0xDA,
                0x99,
                0xDD,
                0xA3,
                0xCF,
                0xA7,
                0xD9,
                0x09,
                0xD4,
                0xAC,
                0xE1,
                0x9E,
                0xE2,
                0xAB,
                0x0B,
                0xD6,
                0x9C,
                0xE3,
                0xA0,
                0xD2,
                0xAD,
                0x93,
                0xE0,
                0x9F,
                0xE4,
                0xAA,
                0xD5,
            )
        ),
        97,
        1823,
    ),
    Case(
        "emit-thirty-two",
        "28233e1aa816b9dad6bc749c8fdae9763d87f0ae0374af867bc90a43fd1a840e",
        "f9322856b876e52e368a51b54cdecab167fc0b9d5baa8e11aa2bdbe95c201205",
        bytes((
            0x41, 0x17, 0x32, 0x18, 0x50, 0x23, 0x5C, 0x27,
            0x4B, 0x34, 0x4F, 0x09, 0xD4, 0xAC, 0xE1, 0x9E,
            0xE2, 0xAB, 0x0B, 0xD6, 0x9C, 0xE3, 0xA0, 0xD2,
            0xAD, 0x93, 0xE0, 0x9F, 0xE4, 0xAA, 0xD5, 0xAE,
        )),
        97,
        1823,
    ),
    Case(
        "emit-thirty-four",
        "b6609c9b750b2d272c3c034ad4e663577d755a77a83532d0258e93db6f2c04c7",
        "a21549a604de61c889020a1574560fc02ef9c34beee0afa592e02c31a1857959",
        bytes((
            0x3F, 0x11, 0x2C, 0x14, 0x39, 0x04, 0xA8, 0x50,
            0x36, 0x3D, 0x42, 0x44, 0x2F, 0x0B, 0xD6, 0x9C,
            0xE3, 0xA0, 0xD2, 0xAD, 0x93, 0xE0, 0x9F, 0xE4,
            0xAA, 0xD5, 0xAE, 0x09, 0xD4, 0xAC, 0xE1, 0x9E,
            0xE2, 0xAB,
        )),
        97,
        1823,
    ),
    Case(
        "emit-thirty-five",
        "3df37b1afe8aefc09d529b448f5468ccd0f1c8fd019585bd1477798381f0aa9b",
        "766476813c35af5b6e3830292a71fa1d8c22fd7b9866e0a5b3e2c74e8530513e",
        bytes((
            0x30, 0x0D, 0x3C, 0x11, 0x2C, 0x14, 0x39, 0xA6,
            0x46, 0x42, 0x44, 0x2F, 0x50, 0x36, 0x09, 0xD4,
            0xAC, 0xE1, 0x9E, 0xE2, 0xAB, 0x0B, 0xD6, 0x9C,
            0xE3, 0xA0, 0xD2, 0xAD, 0x93, 0xE0, 0x9F, 0xE4,
            0xAA, 0xD5, 0xAE,
        )),
        97,
        1823,
    ),
    Case(
        "emit-thirty-six",
        "195e41025d8cfcf322439ae93924478a8d3989a9ad0525616a9f481720732a5b",
        "3a86aea76aeb2fc166a137cf54697b8bb70df85b7fb21bf42f75e183521f6cd0",
        bytes((
            0x39, 0xA8, 0x07, 0xBB, 0x02, 0xB6, 0x0C, 0xB1,
            0x30, 0x0D, 0x4B, 0x34, 0x4F, 0x23, 0x5C, 0x93,
            0xE0, 0x9F, 0xE4, 0xAA, 0xD5, 0xAE, 0x09, 0xD4,
            0xAC, 0xE1, 0x9E, 0xE2, 0xAB, 0x0B, 0xD6, 0x9C,
            0xE3, 0xA0, 0xD2, 0xAD,
        )),
        97,
        1823,
    ),
    Case(
        "emit-thirty-seven",
        "140399437ad666f6ecdef3965369f77d375a2d57b79f37630708f7c918c9f1f2",
        "2f5344960a12ca10e847339ee466eb4bd22c63d9ff584650938807e2f139b577",
        bytes((
            0x3F, 0x11, 0x2C, 0xA8, 0x07, 0xBB, 0x02, 0xB6,
            0x0C, 0xB1, 0x30, 0x0D, 0x4B, 0x34, 0x4F, 0x23,
            0x5C, 0x93, 0xE0, 0x9F, 0xE4, 0xAA, 0xD5, 0xAE,
            0x09, 0xD4, 0xAC, 0xE1, 0x9E, 0xE2, 0xAB, 0x0B,
            0xD6, 0x9C, 0xE3, 0xA0, 0xD2,
        )),
        97,
        1823,
    ),
    Case(
        "emit-thirty-eight",
        "48c2cce2ad5a9aa5a48e671b9cab74e6349b863b8c86747d729718701b274365",
        "f4acddf3964d448b763f8d92278818fd77ddaa16b24d88409bd76c8f79b2ee7d",
        bytes((
            0x41, 0x17, 0x32, 0x30, 0x0D, 0x3C, 0x11, 0x2C,
            0x14, 0x39, 0xA6, 0x46, 0x42, 0x44, 0x2F, 0x50,
            0x36, 0x09, 0xD4, 0xAC, 0xE1, 0x9E, 0xE2, 0xAB,
            0x0B, 0xD6, 0x9C, 0xE3, 0xA0, 0xD2, 0xAD, 0x93,
            0xE0, 0x9F, 0xE4, 0xAA, 0xD5, 0xAE,
        )),
        97,
        1823,
    ),
    Case(
        "emit-thirty-nine",
        "e329ceebec7483bc8a4cc7513e021f1267551c90441e10033a3029374f00cb66",
        "20bca04da87da684d1c61b3d1a0f3d8b80feb4c28dd37347249e332fa198f816",
        bytes((
            0x5C, 0x32, 0x26, 0xA8, 0x07, 0xBB, 0x02, 0xB6,
            0x0C, 0xB1, 0x30, 0x0D, 0x3C, 0x11, 0x2C, 0x14,
            0x39, 0xA6, 0x46, 0x42, 0x44, 0x2F, 0x50, 0x36,
            0x09, 0xD4, 0xAC, 0xE1, 0x9E, 0xE2, 0xAB, 0x0B,
            0xD6, 0x9C, 0xE3, 0xA0, 0xD2, 0xAD, 0x93,
        )),
        97,
        1823,
    ),
    Case(
        "emit-forty",
        "2988f5852da08056b95fcc05c7dba3dccc0b040014671e04831010ee62eb4c49",
        "0e990005bbdc9b2b3b1a956df09a68582e4fb6ab3c529fb1a52b492ad59c34e6",
        bytes((
            0xA8, 0x07, 0xBB, 0x02, 0xB6, 0x0C, 0xB1, 0x30,
            0x0D, 0x3C, 0x11, 0x2C, 0x14, 0x39, 0xA6, 0x46,
            0x42, 0x44, 0x2F, 0x50, 0x36, 0x09, 0xD4, 0xAC,
            0xE1, 0x9E, 0xE2, 0xAB, 0x0B, 0xD6, 0x9C, 0xE3,
            0xA0, 0xD2, 0xAD, 0x93, 0xE0, 0x9F, 0xE4, 0xAA,
        )),
        97,
        1823,
    ),
    Case(
        "emit-forty-one",
        "e9c800f4361c5e18a5bfba494144ddf99c3f54cbd3807d9bf0ce0d4b80af4c67",
        "af079783ce7479c86540f95f4854ef9e081e7f56ca9147a9af2aaec40e5722f0",
        bytes((
            0x5A, 0xA8, 0x07, 0xBB, 0x02, 0xB6, 0x0C, 0xB1,
            0x30, 0x0D, 0x3C, 0x11, 0x2C, 0x14, 0x39, 0xA6,
            0x46, 0x42, 0x44, 0x2F, 0x50, 0x36, 0x09, 0xD4,
            0xAC, 0xE1, 0x9E, 0xE2, 0xAB, 0x0B, 0xD6, 0x9C,
            0xE3, 0xA0, 0xD2, 0xAD, 0x93, 0xE0, 0x9F, 0xE4,
            0xAA,
        )),
        97,
        1823,
    ),
    Case(
        "emit-forty-two",
        "d8046497a2931c30dbb8adba7e64d8b91577e780531950c28244c68882f39862",
        "c88ee1dc8e6bd0acfd1c1ea08c20231767c1a5288140ffea157e02c031816951",
        bytes((
            0xA8, 0x07, 0xBB, 0x02, 0xB6, 0x0C, 0xB1, 0x30,
            0x0D, 0x3C, 0x11, 0x2C, 0x14, 0x39, 0xA6, 0x46,
            0x42, 0x44, 0x2F, 0x50, 0x36, 0x09, 0xD4, 0xAC,
            0xE1, 0x9E, 0xE2, 0xAB, 0x0B, 0xD6, 0x9C, 0xE3,
            0xA0, 0xD2, 0xAD, 0x93, 0xE0, 0x9F, 0xE4, 0xAA,
            0xD5, 0xAE,
        )),
        97,
        1823,
    ),
    Case(
        "emit-forty-six",
        "43c9e428eebebffd1c2a36aaba2e3bbbaa658c525c8db6b49b259b5e4eaa6da6",
        "5a11922ef7e50e8b6c5612938c8fffb3228afd9d0272a7c254a377483fcbf4b5",
        bytes((
            0x54, 0x22, 0x4F, 0x23, 0x53, 0x1E, 0x09, 0x08,
            0xE2, 0xAB, 0xDD, 0x7E, 0xC0, 0x7D, 0xBA, 0x81,
            0xBC, 0x7B, 0x2A, 0x10, 0x30, 0x0E, 0x2F, 0x11,
            0x2D, 0xA3, 0xFF, 0xA7, 0x00, 0xA2, 0x01, 0xA6,
            0xFC, 0xCF, 0xA5, 0xCE, 0x9F, 0xD2, 0xA1, 0xCC,
            0x90, 0xE3, 0xAE, 0xE1, 0xAD, 0xE4,
        )),
        106,
        1895,
    ),

    Case(
        "emit-forty-seven",
        "0d556825d271692f541a1cff84a71fc0e38f0c07d45b8cd09ca10d144c738684",
        "3130215c9ba054edc462792a37cfe3e304132b51498c6185b0e35ce8576b8488",
        bytes((
            0x05, 0xFC, 0xCD, 0xA7, 0xD8, 0xC2, 0xBB, 0xC3,
            0xD7, 0x40, 0x41, 0x59, 0x24, 0x5A, 0x1C, 0x1B,
            0x2E, 0x4F, 0x2F, 0x1A, 0x48, 0xB9, 0xFD, 0xD3,
            0x17, 0x9D, 0x33, 0xB7, 0xB0, 0x3B, 0xAF, 0x37,
            0x51, 0x1D, 0x50, 0x38, 0x36, 0x4A, 0x35, 0x14,
            0x2C, 0x3F, 0x2D, 0x0A, 0x46, 0x26, 0x11,
        )),
        118,
        1991,
    ),
    Case(
        "emit-forty-eight",
        "65e37ec484f1be04b1e15fc90b2948035fc3c62e7c13adfbed6a7df612b1ce22",
        "5c5892d0f601e8cd44ad7ffe152d91bc48b3a53d5ec71d08c8de0502313c6bdc",
        bytes((
            0x51, 0x37, 0x34, 0x38, 0xFB, 0xCE, 0x9F, 0x98,
            0xB8, 0xB4, 0x83, 0xCD, 0x04, 0xCA, 0x1C, 0x1B,
            0x2E, 0x4F, 0x8B, 0xCF, 0xA7, 0xA2, 0x95, 0xD6,
            0x96, 0xA1, 0xAF, 0xC5, 0xBA, 0xE0, 0x9D, 0xE1,
            0xB9, 0x41, 0x47, 0x5C, 0x2A, 0x44, 0x29, 0x0E,
            0x32, 0x4E, 0x31, 0x18, 0x1F, 0x4C, 0x20, 0x17,
        )),
        121,
        2015,
    ),
)


def has_executables(*paths: Path) -> bool:
    return all(path.is_file() and os.access(path, os.X_OK) for path in paths)


@final
class VersionedExampleCorpusTests(unittest.TestCase):
    def test_retained_source_and_artifact_digests(self) -> None:
        for case in CASES:
            with self.subTest(example=case.stem):
                self.assertTrue(case.source.is_file())
                self.assertTrue(case.capsule.is_file())
                self.assertEqual(
                    hashlib.sha256(case.source.read_bytes()).hexdigest(),
                    case.source_sha256,
                )
                self.assertEqual(
                    hashlib.sha256(case.capsule.read_bytes()).hexdigest(),
                    case.capsule_sha256,
                )
                self.assertEqual(case.capsule.stat().st_size, case.size)

    def test_retained_guest_runs_under_normative_vm(self) -> None:
        if not has_executables(VM):
            self.skipTest("repository VM binary is not built")
        for case in CASES:
            with self.subTest(example=case.stem):
                result = subprocess.run(
                    [str(VM), str(case.capsule), "--report-steps"],
                    check=False,
                    capture_output=True,
                    timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, case.stdout)
                self.assertEqual(
                    result.stderr, f"malbolge-steps-v1:{case.steps}\n".encode()
                )

    def test_retained_guest_output_ignores_unused_binary_stdin(self) -> None:
        if not has_executables(VM):
            self.skipTest("repository VM binary is not built")
        for case in CASES:
            with self.subTest(example=case.stem):
                result = subprocess.run(
                    [str(VM), str(case.capsule), "--input-stdin", "--report-steps"],
                    input=bytes((0x00, 0x80, 0xFF)),
                    check=False,
                    capture_output=True,
                    timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, case.stdout)
                self.assertEqual(
                    result.stderr, f"malbolge-steps-v1:{case.steps}\n".encode()
                )

    def test_semantics_preserving_c_comments_preserve_guest_capsule(self) -> None:
        if (
            not has_executables(FRONTEND, ADAPTER, LAYOUT)
            or not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
        ):
            if "MALBOLGE_CORPUS_BIN_ROOT" in os.environ:
                self.fail("explicitly selected compiler binaries are missing")
            self.skipTest("pinned native compiler stages are not built")

        # Span and spelling changes must not become guest output effects.
        # Exercise the smallest and largest retained output-only C traces.
        selected = {case.stem: case for case in (CASES[0], CASES[-1])}
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp_dir:
            for case in selected.values():
                with self.subTest(example=case.stem):
                    source = case.source.read_text(encoding="utf-8")
                    self.assertIn("putchar(", source)
                    transformed = source.replace(
                        "putchar(", "/* equivalent tokens */ putchar ("
                    )
                    self.assertNotEqual(source, transformed)
                    variant = Path(temp_dir) / f"{case.stem}-relayout.c"
                    _ = variant.write_text(transformed, encoding="utf-8")
                    output = Path(temp_dir) / f"{case.stem}-relayout.malbolge"
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--frontend",
                            str(FRONTEND),
                            "--json-adapter",
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--guest-include",
                            str(GUEST_INCLUDE),
                            "--resource-dir",
                            str(RESOURCE),
                            "--source-id",
                            f"corpus/{case.stem}-v1",
                            "--capsule",
                            "--output",
                            str(output),
                            str(variant),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=150,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(output.read_bytes(), case.capsule.read_bytes())

    def test_pinned_c_frontend_reproduces_the_retained_capsules(self) -> None:
        if (
            not has_executables(FRONTEND, ADAPTER, LAYOUT)
            or not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
        ):
            if "MALBOLGE_CORPUS_BIN_ROOT" in os.environ:
                self.fail("explicitly selected compiler binaries are missing")
            self.skipTest("pinned native compiler stages are not built")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp_dir:
            for case in CASES:
                with self.subTest(example=case.stem):
                    output = Path(temp_dir) / f"{case.stem}.malbolge"
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(DRIVER),
                            "--frontend",
                            str(FRONTEND),
                            "--json-adapter",
                            str(ADAPTER),
                            "--layout-backend",
                            str(LAYOUT),
                            "--guest-include",
                            str(GUEST_INCLUDE),
                            "--resource-dir",
                            str(RESOURCE),
                            "--source-id",
                            f"corpus/{case.stem}-v1",
                            "--capsule",
                            "--output",
                            str(output),
                            str(case.source),
                        ],
                        check=False,
                        capture_output=True,
                        timeout=150,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(output.read_bytes(), case.capsule.read_bytes())

    def test_forty_retained_source_and_artifact_digests(self) -> None:
        case = next(case for case in CASES if case.stem == "emit-forty")
        self.assertEqual(
            hashlib.sha256(case.source.read_bytes()).hexdigest(),
            case.source_sha256,
        )
        self.assertEqual(
            hashlib.sha256(case.capsule.read_bytes()).hexdigest(),
            case.capsule_sha256,
        )
        self.assertEqual(case.capsule.stat().st_size, 1823)

    def test_forty_retained_guest_runs_under_normative_vm(self) -> None:
        if not has_executables(VM):
            self.skipTest("repository VM binary is not built")
        case = next(case for case in CASES if case.stem == "emit-forty")
        result = subprocess.run(
            [str(VM), str(case.capsule), "--report-steps"],
            check=False,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, case.stdout)
        self.assertEqual(result.stderr, b"malbolge-steps-v1:97\n")

    def test_forty_retained_pinned_recompile_is_byte_identical(self) -> None:
        if (
            not has_executables(FRONTEND, ADAPTER, LAYOUT)
            or not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
        ):
            if "MALBOLGE_CORPUS_BIN_ROOT" in os.environ:
                self.fail("explicit compiler binaries are missing")
            self.skipTest("pinned native compiler stages are not built")
        case = next(case for case in CASES if case.stem == "emit-forty")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp_dir:
            output = Path(temp_dir) / "emit-forty.malbolge"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--frontend",
                    str(FRONTEND),
                    "--json-adapter",
                    str(ADAPTER),
                    "--layout-backend",
                    str(LAYOUT),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "corpus/emit-forty-v1",
                    "--capsule",
                    "--output",
                    str(output),
                    str(case.source),
                ],
                check=False,
                capture_output=True,
                timeout=150,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), case.capsule.read_bytes())

    def test_forty_one_retained_source_and_artifact_digests(self) -> None:
        case = next(case for case in CASES if case.stem == "emit-forty-one")
        self.assertEqual(
            hashlib.sha256(case.source.read_bytes()).hexdigest(),
            case.source_sha256,
        )
        self.assertEqual(
            hashlib.sha256(case.capsule.read_bytes()).hexdigest(),
            case.capsule_sha256,
        )
        self.assertEqual(case.capsule.stat().st_size, 1823)

    def test_forty_one_retained_guest_runs_under_normative_vm(self) -> None:
        if not has_executables(VM):
            self.skipTest("repository VM binary is not built")
        case = next(case for case in CASES if case.stem == "emit-forty-one")
        result = subprocess.run(
            [str(VM), str(case.capsule), "--report-steps"],
            check=False,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, case.stdout)
        self.assertEqual(result.stderr, b"malbolge-steps-v1:97\n")

    def test_forty_one_retained_pinned_recompile_is_byte_identical(self) -> None:
        if (
            not has_executables(FRONTEND, ADAPTER, LAYOUT)
            or not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
        ):
            if "MALBOLGE_CORPUS_BIN_ROOT" in os.environ:
                self.fail("explicit compiler binaries are missing")
            self.skipTest("pinned native compiler stages are not built")
        case = next(case for case in CASES if case.stem == "emit-forty-one")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp_dir:
            output = Path(temp_dir) / "emit-forty-one.malbolge"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--frontend",
                    str(FRONTEND),
                    "--json-adapter",
                    str(ADAPTER),
                    "--layout-backend",
                    str(LAYOUT),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "corpus/emit-forty-one-v1",
                    "--capsule",
                    "--output",
                    str(output),
                    str(case.source),
                ],
                check=False,
                capture_output=True,
                timeout=150,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), case.capsule.read_bytes())

    def test_forty_two_retained_source_and_artifact_digests(self) -> None:
        case = next(case for case in CASES if case.stem == "emit-forty-two")
        self.assertEqual(
            hashlib.sha256(case.source.read_bytes()).hexdigest(),
            case.source_sha256,
        )
        self.assertEqual(
            hashlib.sha256(case.capsule.read_bytes()).hexdigest(),
            case.capsule_sha256,
        )
        self.assertEqual(case.capsule.stat().st_size, 1823)

    def test_forty_two_retained_guest_runs_under_normative_vm(self) -> None:
        if not has_executables(VM):
            self.skipTest("repository VM binary is not built")
        case = next(case for case in CASES if case.stem == "emit-forty-two")
        result = subprocess.run(
            [str(VM), str(case.capsule), "--report-steps"],
            check=False,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, case.stdout)
        self.assertEqual(result.stderr, b"malbolge-steps-v1:97\n")

    def test_forty_two_retained_pinned_recompile_is_byte_identical(self) -> None:
        if (
            not has_executables(FRONTEND, ADAPTER, LAYOUT)
            or not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
        ):
            if "MALBOLGE_CORPUS_BIN_ROOT" in os.environ:
                self.fail("explicit compiler binaries are missing")
            self.skipTest("pinned native compiler stages are not built")
        case = next(case for case in CASES if case.stem == "emit-forty-two")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp_dir:
            output = Path(temp_dir) / "emit-forty-two.malbolge"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--frontend",
                    str(FRONTEND),
                    "--json-adapter",
                    str(ADAPTER),
                    "--layout-backend",
                    str(LAYOUT),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "corpus/emit-forty-two-v1",
                    "--capsule",
                    "--output",
                    str(output),
                    str(case.source),
                ],
                check=False,
                capture_output=True,
                timeout=150,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), case.capsule.read_bytes())

    def test_forty_six_retained_source_and_artifact_digests(self) -> None:
        case = next(case for case in CASES if case.stem == "emit-forty-six")
        self.assertEqual(
            hashlib.sha256(case.source.read_bytes()).hexdigest(),
            case.source_sha256,
        )
        self.assertEqual(
            hashlib.sha256(case.capsule.read_bytes()).hexdigest(),
            case.capsule_sha256,
        )
        self.assertEqual(case.capsule.stat().st_size, 1895)

    def test_forty_six_retained_guest_runs_under_normative_vm(self) -> None:
        if not has_executables(VM):
            self.skipTest("repository VM binary is not built")
        case = next(case for case in CASES if case.stem == "emit-forty-six")
        result = subprocess.run(
            [str(VM), str(case.capsule), "--report-steps"],
            check=False,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, case.stdout)
        self.assertEqual(result.stderr, b"malbolge-steps-v1:106\n")

    def test_forty_six_retained_pinned_recompile_is_byte_identical(self) -> None:
        if (
            not has_executables(FRONTEND, ADAPTER, LAYOUT)
            or not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
        ):
            if "MALBOLGE_CORPUS_BIN_ROOT" in os.environ:
                self.fail("explicit compiler binaries are missing")
            self.skipTest("pinned native compiler stages are not built")
        case = next(case for case in CASES if case.stem == "emit-forty-six")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp_dir:
            output = Path(temp_dir) / "emit-forty-six.malbolge"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--frontend",
                    str(FRONTEND),
                    "--json-adapter",
                    str(ADAPTER),
                    "--layout-backend",
                    str(LAYOUT),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "corpus/emit-forty-six-v1",
                    "--capsule",
                    "--output",
                    str(output),
                    str(case.source),
                ],
                check=False,
                capture_output=True,
                timeout=150,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), case.capsule.read_bytes())

    def test_forty_seven_retained_source_and_artifact_digests(self) -> None:
        case = next(case for case in CASES if case.stem == "emit-forty-seven")
        self.assertEqual(
            hashlib.sha256(case.source.read_bytes()).hexdigest(),
            case.source_sha256,
        )
        self.assertEqual(
            hashlib.sha256(case.capsule.read_bytes()).hexdigest(),
            case.capsule_sha256,
        )
        self.assertEqual(case.capsule.stat().st_size, 1991)

    def test_forty_seven_retained_guest_runs_under_normative_vm(self) -> None:
        if not has_executables(VM):
            self.skipTest("repository VM binary is not built")
        case = next(case for case in CASES if case.stem == "emit-forty-seven")
        result = subprocess.run(
            [str(VM), str(case.capsule), "--report-steps"],
            check=False,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, case.stdout)
        self.assertEqual(result.stderr, b"malbolge-steps-v1:118\n")

    def test_forty_seven_retained_pinned_recompile_is_byte_identical(self) -> None:
        if (
            not has_executables(FRONTEND, ADAPTER, LAYOUT)
            or not GUEST_INCLUDE.is_dir()
            or not RESOURCE.is_dir()
        ):
            if "MALBOLGE_CORPUS_BIN_ROOT" in os.environ:
                self.fail("explicit compiler binaries are missing")
            self.skipTest("pinned native compiler stages are not built")
        case = next(case for case in CASES if case.stem == "emit-forty-seven")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as temp_dir:
            output = Path(temp_dir) / "emit-forty-seven.malbolge"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--frontend",
                    str(FRONTEND),
                    "--json-adapter",
                    str(ADAPTER),
                    "--layout-backend",
                    str(LAYOUT),
                    "--guest-include",
                    str(GUEST_INCLUDE),
                    "--resource-dir",
                    str(RESOURCE),
                    "--source-id",
                    "corpus/emit-forty-seven-v1",
                    "--capsule",
                    "--output",
                    str(output),
                    str(case.source),
                ],
                check=False,
                capture_output=True,
                timeout=150,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), case.capsule.read_bytes())
