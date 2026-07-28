# AArch64

## Status

Verified as of 2026-07-26.

## Subject

AArch64 and the A64 instruction set used by 64-bit Arm application processors.

## Repository Use

AArch64 is a first-class host CPU architecture and planned native-code backend.
This source supports terminology and architecture identity only; repository ABI,
cache, and backend decisions remain technical contracts.

## Provenance

Arm's official architecture documentation describes A64 as the instruction set
used in the 64-bit Armv8-A architecture, also known as AArch64.

## Identity And Version

- Authority: Arm Limited.
- Subject: A64 Instruction Set Architecture / AArch64 execution state.
- Review date: 2026-07-26.

## License Or Terms

Arm documentation is externally authored material. This repository cites it and
does not redistribute the manuals as project-owned content.

## Evidence

- A64 is the instruction set used in the AArch64 execution state.
- AArch64 exposes 64-bit general-purpose X registers while retaining 32-bit W
  views of those registers.
- The repository's choice to support AArch64 is independent from Arm's document
  licensing and from any single processor implementation.

### Unresolved

The exact repository CPU-feature baseline, calling convention, and native-backend
ABI are Malbolge technical decisions. The cited Arm architecture material does
not choose those repository policies.

## Sources

- <https://developer.arm.com/documentation/102374/latest/>
- Arm, *Armv8-A Instruction Set Architecture*, accessed 2026-07-26.
