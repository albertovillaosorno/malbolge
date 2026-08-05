# Historical Interpreter Evidence

This directory owns deterministic host-tool evidence for Ben Olmstead's
immutable interpreter. It does not benchmark the modern VM and does not make
historical undefined C behavior normative.

`sanitizer-cases.json` declares one clean interpreter-authority program and the
two H-003 loader boundaries. The runner materializes inline hex sources only in
`.temp`, verifies the pinned historical source hash, compiles the untouched
source with Clang 22.1.8 AddressSanitizer and UndefinedBehaviorSanitizer, and
normalizes findings without retaining addresses or host-specific stacks.

`evidence/windows-x86_64-sanitizer-findings.json` is the reviewed normalized
result. Empty and one-word sources both expose an AddressSanitizer
`heap-buffer-overflow`; the clean interpreter roundtrip emits byte `0xA8` and
has no sanitizer finding.

Run the check from the repository root:

```powershell
.dependencies\python\3.14.6\Scripts\python-jig.cmd -m `
  scripts.validate.historical_interpreter_sanitizer
```

The Windows `_halloc` compatibility function is generated and linked as a
separate temporary translation unit. The historical `main.c` is never patched,
wrapped, copied back, or used as a source of safe modern semantics.
