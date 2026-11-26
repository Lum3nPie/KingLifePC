#!/usr/bin/env python3
"""Write the WiiCompiled "foreign game" layer for My Life as a King (WFCPGD).

Our own tool, written after the method of HarvestMoonAnimalParadeRecomp (GPL-3.0): WiiCompiled's
runtime registers its natives at Mario Kart Wii's PAL addresses; the foreign-game patch maps each PAL
address to this game's through guest_abi/foreign_game_addresses.inc. This tool writes:

  <wiicompiled>/runtime/include/guest_abi/foreign_game_addresses.inc
  <wiicompiled>/runtime/include/guest_abi/foreign_game_facts.inc
  <wiicompiled>/runtime/include/guest_abi/foreign_game_ios.inc
  <wiicompiled>/projects/lifeking/native/natives.cpp   (read by the translator only)

Natives are matched by name: the Mario Kart Wii map name at the address, then the C++ name of the
native, against the SDK names in our decomp's symbols.txt. Extra rows (SDK variables, functions the
natives call) come from tables/*.txt: "PAL_ADDR  OUR_ADDR  what" per line ("-" = not in this game).

Usage: python make_layer.py --wiicompiled <clone> --symbols <KingLifePC/config/WFCPGD/symbols.txt>
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

MACROS = (
    "PPC_NATIVE_OVERRIDE_VOID",
    "PPC_NATIVE_OVERRIDE",
    "REGISTER_NATIVE_FUNCTION_AS",
    "REGISTER_NATIVE_FUNCTION",
    "REGISTER_NATIVE_WRAPPER_AS",
    "REGISTER_NATIVE_REPLACEMENT_AS",
    "GX_FATAL_STUB",
)
MACRO_START = re.compile(r"\b(" + "|".join(MACROS) + r")\(")

# Kept translated even though WiiCompiled has a native (see HarvestMoonAnimalParadeRecomp's notes:
# the MKW native NANDInit does not set the current directory that the game's own NAND calls use).
KEPT_TRANSLATED = {"NANDInit", "ESP_InitLib", "ESP_CloseLib"}  # ESP_*Lib: the MKW stubs never open /dev/es, and CNT needs the real fd

# MKW addresses whose native C++ name does not say the SDK function (NAND_IOS_Open_HLE is IOS_Open).
ALIASES = {
    0x801938F8: "IOS_Open",
    0x80193AD8: "IOS_Close",
    0x80193C80: "IOS_Read",
    0x80193E88: "IOS_Write",
    0x80194070: "IOS_Seek",
    0x80194290: "IOS_Ioctl",
    0x801945E0: "IOS_Ioctlv",
}

# Static SDK functions WiiCompiled has natives for; their names say no library, so they are accepted
# by name explicitly (named in our symbols.txt from Dolphin's signature database).
SDK_STATIC_NATIVES = {"SelectThread"}

GAME_ID = "WFCPGD"
FACTS = '    {"WFCPGD", \'P\', 0x57464350u /* WFCP */, 1u /* PAL */, 0x803B2840u, "EUR", "RVL-001(EUR)", "LEH", "PAL", "EU"},'
# The TMD of title 00010001-57464350 names IOS37 (0x25); 5663 is IOS37's last release.
IOS_VERSION = (37 << 16) | 5663


def balanced_call(text, start):
    """Return the text of a macro call starting at `start` (at the macro name) up to its ')'."""
    depth = 0
    i = text.index("(", start)
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[start : j + 1]
    return None


def read_registrations(wiicompiled):
    regs = []
    for src in sorted((wiicompiled / "runtime" / "src").rglob("*.cpp")):
        text = src.read_text(encoding="utf-8", errors="replace")
        for m in MACRO_START.finditer(text):
            # skip macro definitions and comments
            line_start = text.rfind("\n", 0, m.start()) + 1
            prefix = text[line_start : m.start()]
            if "#define" in prefix or "//" in prefix:
                continue
            call = balanced_call(text, m.start())
            if not call:
                continue
            args = [a.strip() for a in call[call.index("(") + 1 : -1].split(",")]
            addr = args[0].lower().replace("0x", "")
            if not re.fullmatch(r"[0-9a-f]{8}", addr):
                continue
            names = []
            if m.group(1) == "GX_FATAL_STUB" and len(args) > 1:
                names.append(args[1].strip('"'))
            elif len(args) > 1:
                names.append(args[1])
            if m.group(1).endswith("_AS") and len(args) > 2:
                names.append(args[2].strip('"'))
            regs.append(
                {
                    "macro": m.group(1),
                    "pal": int(addr, 16),
                    "names": names,
                    "statement": call + ";",
                    "src": src.relative_to(wiicompiled).as_posix(),
                }
            )
    return regs


def read_mkw_map(wiicompiled):
    names = {}
    for line in (wiicompiled / "projects" / "mkwii" / "MAP.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and not parts[1].startswith("0x"):
            names.setdefault(int(parts[0], 16), parts[1].strip())
    return names


def normalize(name):
    """Turn MKW map / native C++ spellings into SDK C names."""
    out = []
    n = name.strip()
    if "::" in n:
        lib, rest = n.split("::", 1)
        out.append("__" + lib + rest[2:] if rest.startswith("__") else lib + rest)
        out.append(lib + "_" + rest)  # IOS::Open is IOS_Open, ISFS::OpenLib is ISFS_OpenLib
        out.append(rest)
    n = re.sub(r"(_HLE|_hle|_stub|_native)+(_[0-9a-fA-F]{8})?$", "", n)
    n = re.sub(r"_[0-9a-fA-F]{8}(_HLE|_hle)?$", "", n)
    n = re.sub(r"(_HLE|_hle)$", "", n)
    out.append(n)
    m = re.match(r"^(_*)([A-Z][A-Z0-9]*)__(.*)$", n)
    if m:
        lead, lib, rest = m.groups()
        out.append(lead + ("__" + lib + rest[2:] if rest.startswith("__") else lib + rest))
        out.append(rest)  # MTX__C_MTXPerspective is C_MTXPerspective
    return [x for x in out if x]


def is_sdk_name(name):
    if re.match(r"^(C_|PS)(MTX|VEC|QUAT)", name) or name in SDK_STATIC_NATIVES:
        return True
    return re.match(r"^_*[A-Z][A-Z0-9]+(_?[A-Z][A-Za-z0-9]*)", name) is not None or name in {
        "memcpy", "memset", "strlen", "strcmp", "sprintf", "printf", "fprintf", "vprintf"
    }


def read_symbols(path):
    by_name = defaultdict(list)
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\S+) = \.(?:text|init):0x([0-9A-F]+); // type:function", line)
        if m and not re.match(r"^(fn|lbl|dtor|ctor)_[0-9A-F]{8}$", m.group(1)):
            by_name[m.group(1)].append(int(m.group(2), 16))
    return by_name


def read_tables():
    rows = []
    for path in sorted((HERE / "tables").glob("*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            pal, here, what = re.split(r"\s{2,}", line.strip(), maxsplit=2)
            if here != "-":
                rows.append((int(pal, 16), int(here, 16), what))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiicompiled", type=Path, required=True)
    ap.add_argument("--symbols", type=Path, required=True)
    args = ap.parse_args()

    regs = read_registrations(args.wiicompiled)
    mkw_names = read_mkw_map(args.wiicompiled)
    ours = read_symbols(args.symbols)

    placed = {}  # pal -> (here, name)
    natives = []
    missing = []
    for r in regs:
        cands = [ALIASES[r["pal"]]] if r["pal"] in ALIASES else []
        if r["pal"] in mkw_names:
            cands += normalize(mkw_names[r["pal"]])
        for n in r["names"]:
            cands += normalize(n)
        found = None
        for c in cands:
            if is_sdk_name(c) and len(ours.get(c, [])) == 1:
                found = (ours[c][0], c)
                break
        if not found or found[1] in KEPT_TRANSLATED:
            missing.append((r, cands[:3]))
            continue
        here, name = found
        if r["pal"] in placed and placed[r["pal"]][0] != here:
            print(f"clash at {r['pal']:08X}: {placed[r['pal']]} vs {found}")
            continue
        placed[r["pal"]] = found
        stmt = re.sub(r"\((\s*(?:0x)?)[0-9A-Fa-f]{8}", lambda m: f"({m.group(1)}{here:08X}", r["statement"], count=1)
        natives.append(f"// {name} (MKW 0x{r['pal']:08X}, {r['src']})\n{stmt}")

    # Our own natives for this game's code (FOREIGN_GAME_NATIVE(WFCPGD, addr, ...)): the translator must
    # leave those addresses to the runtime.
    for src in sorted((args.wiicompiled / "runtime" / "src").rglob("*.cpp")):
        text = src.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"FOREIGN_GAME_NATIVE\(\s*" + GAME_ID + r"\s*,\s*([0-9A-Fa-f]{8})\s*,", text):
            call = balanced_call(text, m.start())
            inner = call[call.index("(") + 1 : -1]
            rest = inner.split(",", 2)[2].strip()
            natives.append(f"// This game's own code at 0x{m.group(1).upper()} ({src.relative_to(args.wiicompiled).as_posix()})\n"
                           f"PPC_NATIVE_OVERRIDE({m.group(1).upper()}, {rest});")

        for m in re.finditer(r"FOREIGN_GAME_WRAPPER\(\s*" + GAME_ID + r"\s*,\s*([0-9A-Fa-f]{8})\s*,\s*(\w+)\s*\)", text):
            natives.append(f"// A wrapper around this game's own code at 0x{m.group(1).upper()}\n"
                           f'REGISTER_NATIVE_WRAPPER_AS(0x{m.group(1).upper()}, {m.group(2)}, "{m.group(2)}");')

        for m in re.finditer(r"^LIFEKING_TRACE\(\s*([0-9A-Fa-f]{8})\s*,", text, re.M):
            a = m.group(1).upper()
            natives.append(f"// Debug trace wrapper at 0x{a}\n"
                           f'REGISTER_NATIVE_WRAPPER_AS(0x{a}, LifeKing_Trace_{m.group(1)}, "LifeKing_Trace_{m.group(1)}");')

    rows = {pal: v for pal, v in placed.items()}
    for pal, here, what in read_tables():
        if pal in rows and rows[pal][0] != here:
            raise SystemExit(f"table row {pal:08X} -> {here:08X} disagrees with native {rows[pal]}")
        rows.setdefault(pal, (here, what))

    inc = args.wiicompiled / "runtime" / "include" / "guest_abi"
    header = "// Written by port/lk-tools/make_layer.py for My Life as a King (WFCPGD); do not edit by hand.\n"
    (inc / "foreign_game_addresses.inc").write_text(
        header + "// Mario Kart Wii's PAL address -> My Life as a King. Sorted by the first column.\n"
        + "".join(f"MKW_FOREIGN_ADDRESS({pal:08X}, {here:08X})  // {what}\n" for pal, (here, what) in sorted(rows.items())),
        encoding="utf-8", newline="\n")
    (inc / "foreign_game_facts.inc").write_text(header + FACTS + "\n", encoding="utf-8", newline="\n")
    (inc / "foreign_game_ios.inc").write_text(header + f"    0x{IOS_VERSION:08X}u\n", encoding="utf-8", newline="\n")
    nat_dir = args.wiicompiled / "projects" / "lifeking" / "native"
    nat_dir.mkdir(parents=True, exist_ok=True)
    (nat_dir / "natives.cpp").write_text(
        header + "// Only the translator reads this file; it is never compiled.\n\n" + "\n\n".join(natives) + "\n",
        encoding="utf-8", newline="\n")

    with open(HERE / "layer_report.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write(f"registrations: {len(regs)}, placed natives: {len(natives)}, rows: {len(rows)}, missing: {len(missing)}\n\n")
        for r, c in missing:
            f.write(f"{r['pal']:08X}\t{r['macro']}\t{'/'.join(r['names'])}\t{r['src']}\ttried={c}\n")
    print(f"registrations {len(regs)}, natives placed {len(natives)}, address rows {len(rows)}, missing {len(missing)}")


if __name__ == "__main__":
    main()
