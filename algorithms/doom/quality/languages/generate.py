from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent / "in" / "doom" / "linuxdoom-1.10"
SOURCE = ROOT / "d_englsh.h"

STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"')
FORMAT_RE = re.compile(
    r'%(?:[-+ #0]*)(?:\d+|\*)?(?:\.(?:\d+|\*))?'
    r'(?:hh|h|ll|l|j|z|t|L)?[diuoxXfFeEgGaAcspn%]'
)

LEET = str.maketrans({
    "a": "4", "A": "4", "b": "8", "B": "8", "e": "3", "E": "3",
    "g": "9", "G": "9", "i": "1", "I": "1", "o": "0", "O": "0",
    "s": "5", "S": "5", "t": "7", "T": "7", "z": "2", "Z": "2",
})

# Canonical printable-character encryption table used by Malbolge.  Generated
# text uses this table but replaces a generated '%' with '#' so translated
# prose cannot accidentally create a new printf conversion.
MALBOLGE_XLAT2 = (
    "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|"
    "jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@"
)


def transform_literal(raw: str, mode: str) -> str:
    inner = raw[1:-1]
    out: list[str] = []
    i = 0
    while i < len(inner):
        if inner[i] == "\\" and i + 1 < len(inner):
            out.append(inner[i : i + 2])
            i += 2
            continue
        if inner[i] == "%":
            match = FORMAT_RE.match(inner, i)
            if match is not None:
                out.append(match.group(0))
                i = match.end()
                continue

        ch = inner[i]
        if mode == "leet":
            mapped = ch.translate(LEET)
        elif mode == "malbolge":
            if 33 <= ord(ch) <= 126:
                mapped = MALBOLGE_XLAT2[ord(ch) - 33]
                if mapped == "%":
                    mapped = "#"
            else:
                mapped = ch
        else:
            raise ValueError(f"Unknown mode: {mode}")

        if mapped == "\\":
            out.append("\\\\")
        elif mapped == '"':
            out.append('\\"')
        else:
            out.append(mapped)
        i += 1

    return '"' + "".join(out) + '"'


def generate(filename: str, guard: str, description: str, mode: str) -> None:
    text = SOURCE.read_text(encoding="utf-8")
    text = text.replace("English language support (default).", description)
    text = text.replace("__D_ENGLSH__", guard)
    text = STRING_RE.sub(lambda match: transform_literal(match.group(0), mode), text)
    (ROOT / filename).write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    generate(
        "d_1337spk.h",
        "__D_1337SPK__",
        "Leetspeak language support (generated from English).",
        "leet",
    )
    generate(
        "d_malbolge.h",
        "__D_MALBOLGE__",
        "Malbolge textual language support (generated from English).",
        "malbolge",
    )


if __name__ == "__main__":
    main()
