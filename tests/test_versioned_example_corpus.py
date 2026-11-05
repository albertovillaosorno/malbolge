# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
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
        "9d99117ec1218be5102aef819fc872e098fcfea7f7efede831c765e5104886f3",
        "4112557f6f320f8827278ff8b623fddba73812c49801569093e815f27a9fa2b8",
        b"Q.",
        8,
        1111,
    ),
    Case(
        "emit-zph",
        "94e5a35dcf0df2da9676ef630c0e1dc0e1926962c4b951adf0f80cec7558dcb4",
        "44ef08f92ac1c352ff5df820e63d4830664b6f7a569cd6e0f5504deb4cba9eb8",
        b"Z%H",
        8,
        1111,
    ),
    Case(
        "emit-t4",
        "34d1144628330399658b36bfe57e2d34cf71f40ad46645ec075a6390ea45fb1a",
        "9ee602682624425da80c13786df338c80df15a65e1df083613c37100ed81f72d",
        b"T=4>",
        21,
        1215,
    ),
    Case(
        "emit-qesc79",
        "5a753a10b51b5211022694a2b3f9c45fe4afb92cd8e0ebf7f9cc37876953688d",
        "09be18cd3358663cf7c8434f4b4c910f9ae2a87f0e6b799238372d2110fae2b6",
        b'Q"\x1b79',
        23,
        1231,
    ),
    Case(
        "emit-qop6",
        "91f7d5bdcb226014082d80e3d15a944811366506d5ecd0ce24441699235f434e",
        "bcf659b66b69e7dac57505ac70a516451b60393bc9a2510d6fd6a59d897b7a76",
        bytes((0x51, 0x1C, 0x4F, 0x1D, 0x50, 0x1B)),
        15,
        1167,
    ),
    Case(
        "emit-seven",
        "1bf0848c18f712c2e7b87e0305563a73cb9299aa45cc74d463e4f6098db19140",
        "4f0c732c3b55dd48b12795044f106989ffc84cd7839bcbff1e11c1b9643b99f8",
        bytes((0x36, 0x3E, 0x35, 0x02, 0x54, 0x1F, 0x18)),
        21,
        1215,
    ),
    Case(
        "emit-eight",
        "5971c3577e8087ed2a895790fefc2a8b3b4c931445c03a7d06de451e3e1fa711",
        "59106439d2b0c203a6f934952adcd10b1d0dae7049df62fb708da48203e8a578",
        bytes((0x53, 0x20, 0x17, 0x3C, 0x36, 0x01, 0x52, 0x06)),
        21,
        1215,
    ),
    Case(
        "emit-nine",
        "45229743a0d515e503b190695307694985a7ba47c2dc74f616839e8bf680f430",
        "1d09fccde1f7d346ebc7e72439b82544da2dda37ff2a6e93b020996189e7bbeb",
        bytes((0x54, 0x3D, 0x8D, 0xD1, 0xC0, 0xB4, 0xBF, 0xD2, 0xA2)),
        21,
        1215,
    ),
    Case(
        "emit-ten",
        "eeacae21350d6c88dbfbd8be4b1d1294e04be60868324463b8a97e24a5553675",
        "7befd3c590d03e94889bc93348bb37c51358f4b719dc2f371e07f918130386b0",
        bytes((0x51, 0x22, 0xFD, 0xCE, 0xA5, 0x98, 0xBA, 0xB6, 0x87, 0xCB)),
        23,
        1231,
    ),
    Case(
        "emit-eleven",
        "4a42a412d63b0131f9d6c613b4f6dedca7fc2a01fd94433add89e5c873853c39",
        "6b7381c638e959fa3f1cca6376317340c4278c4611bc518aa54b4ce2fcc6d8af",
        bytes((0x50, 0x1D, 0x1A, 0x36, 0x05, 0xB4, 0xBA, 0xB3, 0x84, 0xCF, 0x9E)),
        24,
        1239,
    ),
    Case(
        "emit-twelve",
        "f5e8963f704c59cc34e15b217d30f69c2b1816c1bf1e5b20369392b3b1085fc7",
        "5bc03bb8ce1d9ab95a9aad99d387d4752f148c5be30dcab7919ffd53fbc52a34",
        bytes((0x51, 0x37, 0x34, 0x38, 0xFB, 0xCE, 0x9F, 0x98, 0xB8, 0xB4, 0x83, 0xCD)),
        27,
        1263,
    ),
    Case(
        "emit-thirteen",
        "59a96352ab35a582e2424d15818ce59c105fc8222cd3b07394c1486e3ed32e0e",
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
        "923b7245d13803ffbb1615b4f9684fd076a618f4e25d80861ab1e0fe2a807c14",
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
        "a82eecdcfc33fafa28e365d3d8a9792c649f2edd65d23d90d33ea8ecf04e801c",
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
        "e49132f84f6a2afff02dd289f1e0844325e0fe6bf372fcb39ebac4b5f1dd6a72",
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
        "a02514adb41a373560e30ed7a4b68cf995872b0c0aca174a20abbdb8618b9cb6",
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
        "ac2df0d8547294c5307acaa9e9777eac94f98f83842b039b5fde50ad98bcb091",
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
        "9fe717e9e002dee994ece2089602b5c8813edc23f364f37e6424d823a903d9fa",
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
        "f6f81dfbc9abef2429d1090866bf6bae42d8495a3ed91219f6e703e37545aee6",
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
        "221655ff1f398b6745e2174e611b554c479b3c278a6069e14c1ac6f32e70d26c",
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
        "140a3ad6d13fefddfdc910fca0121a00f5a3fd0c262bb962108d3d694fdb1013",
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
        "6df4c2a4e60d238b7dc6bb3201a9ec739fc1e0b5a08d751b5c8916062ee3b662",
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
        "1bab4a3ece74188988944e0f98834aa3f86709c517508f125d93dc126b0119ea",
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
        "64dcdaa83db80adbc87c3cb0ff76a1ef834cc60d367eff442f25c4dfeb37beb9",
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
        "d43d8cfc015160c9e6b26ec14b23cea1931d9d5f7968bdfa334da25dcc1bcea8",
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
        "cc703648b791fd1d36131c1a373edba2ebd75c33517fead73531b50d1df5a518",
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
        "c9b88ebb690b203c079dc394001ee9a85d3286d5580ac1809ba0644070bc65c0",
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
        "4262ba655782c6678cc266922e23086dd397232afe6b41196492c3919f81c6e3",
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
        "163cc08af89a4a5aff7d26791b2a3639e2b2f37f164025bd04d26a4d85131625",
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
        "a10e977d9912ef2bea54c9bb702a1295345a5ffe58b7721a8afac4e2bb02dd7b",
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
        "af99582479ac6ead9b3c326835e7c2d5f3f1102338f8f3769026d72989d8e196",
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
        "2f93cff11c619933cca4d6b92543cefc1ca2b433ef0550ea5d8de6bf6f36cbdc",
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
        "f265c7d119f22fb8feb203b93f314d12ad97c6dd77d3d1cd43389819f1c0172d",
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
        "f4888a38cd96f63b398bb0b3576de2b12dad860a486af3c7fe0f86cfe6d58b46",
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
        "3e1e3f7dd3def1b13e617f6e4f356aba3c5cfe7343b2fcc8677fbe6a6dd09e22",
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
        "a2b0c3c514ce0af1568fa4b97c57efb1e5b23cfaa952dcf98f65ce645bb0871d",
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
        "20fe0bd02f9d640daf57156d4734aaa9544204418c99eaa0e473929735993360",
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
        "16973e6e709b07c044ccf158464bbd93a390ab299c1abfd4837ba31ae1774b53",
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
