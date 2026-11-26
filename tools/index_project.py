#!/usr/bin/env python3
"""Generate a reusable project index so nobody has to re-read every file.

Outputs (in docs/index/):
  <VERSION>.md      human summary: sections, code regions, units, source files, SDK libs
  functions.tsv     one line per function: address, size, name, unit (greppable)
  units.tsv         one line per unit: start, end, code size, functions, named, name

Inputs:
  config/<VERSION>/symbols.txt   (required)
  build/<VERSION>/report.json    (required, produced by `python -m ninja`)
  orig/<VERSION>/sys/main.dol    (optional, adds section table, source files and SDK versions)

Run after every change to symbols/splits:  python tools/index_project.py
"""

import argparse
import json
import re
import struct
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYMBOL_RE = re.compile(
    r"^(?P<name>\S+) = (?P<section>[^:]+):0x(?P<addr>[0-9A-Fa-f]+);\s*//(?P<attrs>.*)$"
)


def parse_symbols(path):
    syms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = SYMBOL_RE.match(line)
        if not m:
            continue
        attrs = m.group("attrs")
        typ = re.search(r"type:(\w+)", attrs)
        size = re.search(r"size:0x([0-9A-Fa-f]+)", attrs)
        scope = re.search(r"scope:(\w+)", attrs)
        syms.append(
            {
                "name": m.group("name"),
                "section": m.group("section"),
                "addr": int(m.group("addr"), 16),
                "type": typ.group(1) if typ else "",
                "size": int(size.group(1), 16) if size else 0,
                "scope": scope.group(1) if scope else "",
            }
        )
    return syms


def is_auto_name(name):
    return re.match(r"^(fn|lbl|jumptable|gap|dtor|ctor|switch|@)_?[0-9A-Fa-f]*", name) is not None and (
        re.search(r"[0-9A-F]{8}$", name) is not None or name.startswith("@")
    )


def parse_dol(path):
    data = path.read_bytes()
    off = struct.unpack(">18I", data[0:72])
    addr = struct.unpack(">18I", data[72:144])
    size = struct.unpack(">18I", data[144:216])
    secs = []
    for i in range(18):
        if size[i]:
            secs.append(("text" if i < 7 else "data", addr[i], size[i], off[i]))
    bss = struct.unpack(">II", data[0xD8:0xE0])
    entry = struct.unpack(">I", data[0xE0:0xE4])[0]
    return data, secs, bss, entry


def dol_strings(data, secs):
    """Yield (virtual address, string) for printable strings in data sections."""
    for kind, va, sz, off in secs:
        if kind != "data":
            continue
        blob = data[off : off + sz]
        for m in re.finditer(rb"[\x20-\x7e]{5,}", blob):
            yield va + m.start(), m.group().decode("ascii")


SDK_PREFIXES = sorted(
    "PPC OS DB DC IC LC L2 DVD VI PAD AI AX AXFX DSP GX EXI SI NAND SC WPAD KPAD WUD ENC CNT EC NHTTP SO NWC24 "
    "NCD SSL HBM MEM ARC TPL IPC ISFS IOS IPC ES FS CARD MIX SEQ SP SYN WENC VF NET USB BT".split(),
    key=len,
    reverse=True,
)


def lib_prefix(name):
    base = name.lstrip("_")
    for p in SDK_PREFIXES:
        if base.startswith(p) and (len(base) == len(p) or not base[len(p)].islower() or p in ("PPC",)):
            return p
    if "__" in name[2:] and name.startswith("__"):
        return "runtime (__*)"
    if re.match(r"^[a-z_]", name):
        return "C runtime / MSL (lowercase)"
    m = re.match(r"^(\w+?)__", name)
    if m:
        return "C++ (mangled)"
    return "other"


def region_of(addr, regions):
    for start, end, label in regions:
        if start <= addr < end:
            return label
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default="WFCPGD")
    args = ap.parse_args()
    ver = args.version

    sym_path = ROOT / "config" / ver / "symbols.txt"
    report_path = ROOT / "build" / ver / "report.json"
    dol_path = ROOT / "orig" / ver / "sys" / "main.dol"
    notes_path = ROOT / "docs" / "NOTES.md"
    out_dir = ROOT / "docs" / "index"
    out_dir.mkdir(parents=True, exist_ok=True)

    syms = parse_symbols(sym_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    # Code regions: game code ends where the first SDK function (PPCArch) starts.
    sdk_start = min((s["addr"] for s in syms if s["name"] == "PPCMfmsr"), default=None)
    text_start = min((s["addr"] for s in syms if s["section"] == ".text"), default=0)
    regions = []
    if sdk_start:
        regions.append((text_start, sdk_start, "game"))
        regions.append((sdk_start, 0xFFFFFFFF, "sdk/libs"))

    # Units from the objdiff report.
    units = []
    func_unit = {}
    for u in report["units"]:
        name = u["name"].split("/", 1)[-1]
        m = u["measures"]
        code = int(m.get("total_code", 0) or 0)
        funcs = u.get("functions", []) or []
        text_secs = [s for s in u.get("sections", []) if s["name"] == ".text" or s["name"] == ".init"]
        if not text_secs:
            continue
        start = int(text_secs[0]["metadata"]["virtual_address"])
        size = int(text_secs[0]["size"])
        names = []
        for f in funcs:
            fva = int(f["metadata"]["virtual_address"])
            func_unit[fva] = name
            names.append(f["name"])
        named = [n for n in names if not is_auto_name(n)]
        units.append(
            {
                "name": name,
                "start": start,
                "end": start + size,
                "code": code,
                "functions": len(funcs),
                "named": len(named),
                "matched": float(m.get("matched_code_percent", 0) or 0),
                "auto": u.get("metadata", {}).get("auto_generated", False),
                "first_named": named[:6],
                "region": region_of(start, regions),
                "sinit": name.startswith("auto_fn_"),
            }
        )
    units.sort(key=lambda x: x["start"])

    funcs = sorted((s for s in syms if s["type"] == "function"), key=lambda s: s["addr"])

    # functions.tsv
    with open(out_dir / "functions.tsv", "w", encoding="utf-8", newline="\n") as f:
        f.write("addr\tsize\tname\tunit\tregion\n")
        for s in funcs:
            f.write(
                f"{s['addr']:08X}\t{s['size']:X}\t{s['name']}\t{func_unit.get(s['addr'], '')}\t{region_of(s['addr'], regions)}\n"
            )

    # units.tsv
    with open(out_dir / "units.tsv", "w", encoding="utf-8", newline="\n") as f:
        f.write("start\tend\tcode\tfunctions\tnamed\tmatched%\tregion\tname\n")
        for u in units:
            f.write(
                f"{u['start']:08X}\t{u['end']:08X}\t{u['code']}\t{u['functions']}\t{u['named']}\t{u['matched']:.1f}\t{u['region']}\t{u['name']}\n"
            )

    # Markdown summary
    md = []
    md.append(f"# Project index: {ver}\n")
    md.append("Generated by `python tools/index_project.py`. Do not edit by hand; hand-written notes go in `docs/NOTES.md`.\n")
    md.append("Lookups: `grep <name or address> docs/index/functions.tsv`, `docs/index/units.tsv` for unit ranges.\n")

    n_named = sum(1 for s in funcs if not is_auto_name(s["name"]))
    total_code = sum(u["code"] for u in units)
    matched_code = sum(u["code"] * u["matched"] / 100 for u in units if not u["auto"])
    md.append("## Totals\n")
    md.append(f"- Symbols: {len(syms)} ({len(funcs)} functions, {n_named} with real names)")
    md.append(f"- Units: {len(units)} with code ({sum(1 for u in units if not u['auto'])} hand-split)")
    md.append(f"- Code: {total_code} bytes, decompiled and matching: {matched_code:.0f} bytes\n")

    data = None
    if dol_path.exists():
        data, secs, bss, entry = parse_dol(dol_path)
        md.append("## DOL sections\n")
        md.append(f"Entry point 0x{entry:08X}, BSS 0x{bss[0]:08X} size 0x{bss[1]:X}.\n")
        md.append("| Section (from splits.txt) | Address | Size |")
        md.append("|---|---|---|")
        split_secs = []
        sp = (ROOT / "config" / ver / "splits.txt").read_text(encoding="utf-8").splitlines()
        for line in sp:
            m = re.match(r"^\t(\S+)\s+type:(\w+)", line)
            if m:
                split_secs.append(m.group(1))
        sec_addr = defaultdict(lambda: [0xFFFFFFFF, 0])
        for s in syms:
            a = sec_addr[s["section"]]
            a[0] = min(a[0], s["addr"])
            a[1] = max(a[1], s["addr"] + s["size"])
        dol_by_addr = {va: sz for _, va, sz, _ in secs}
        for name in split_secs:
            a = sec_addr.get(name)
            if a:
                sz = dol_by_addr.get(a[0])
                if name in (".bss", ".sbss", ".sbss2") or sz is None:
                    md.append(f"| {name} | 0x{a[0]:08X} | ~0x{a[1]-a[0]:X} (from symbols) |")
                else:
                    md.append(f"| {name} | 0x{a[0]:08X} | 0x{sz:X} (DOL, padded) |")
        md.append("")

    md.append("## Code regions\n")
    for start, end, label in regions:
        end_s = "end of .text" if end == 0xFFFFFFFF else f"0x{end:08X}"
        md.append(f"- **{label}**: 0x{start:08X} to {end_s}")
    md.append("")

    # Named function groups (SDK libraries etc.) by name prefix
    groups = defaultdict(list)
    for s in funcs:
        if is_auto_name(s["name"]):
            continue
        key = lib_prefix(s["name"])
        groups[key].append(s)
    md.append("## Named function groups (by prefix)\n")
    md.append("| Prefix | Count | First | Last |")
    md.append("|---|---|---|---|")
    for key, lst in sorted(groups.items(), key=lambda kv: kv[1][0]["addr"]):
        md.append(f"| `{key}` | {len(lst)} | 0x{lst[0]['addr']:08X} | 0x{lst[-1]['addr']:08X} |")
    md.append("")

    if data is not None:
        srcs, libs = [], []
        for va, s in dol_strings(data, secs):
            if re.fullmatch(r"[A-Za-z_][\w]*\.(cpp|c)", s):
                srcs.append((va, s))
            m = re.search(r"<< (RVL_SDK|NW4R)\s+- (\w+)", s)
            if m:
                libs.append((va, f"{m.group(1)} {m.group(2)}"))
            m = re.search(r"release build: (.+?) \((0x[0-9a-f_]+)\)", s)
            if m and libs and libs[-1][0] < va <= libs[-1][0] + 0x40:
                libs[-1] = (libs[-1][0], f"{libs[-1][1]}: {m.group(1)} ({m.group(2)})")
        md.append("## Source file names found in asserts / strings\n")
        md.append("Address is where the string lives in data, not the code. Find users with `grep <lbl> build/*/asm`.\n")
        seen = set()
        for va, s in srcs:
            if s in seen:
                continue
            seen.add(s)
            md.append(f"- 0x{va:08X} `{s}`")
        md.append("")
        md.append("## SDK / middleware libraries linked\n")
        for va, s in libs:
            md.append(f"- {s}")
        md.append("")

    md.append("## Game-code units\n")
    md.append("In game code, `auto_fn_*` units are `__sinit` functions: each one marks the end of a translation unit.\n")
    md.append("| Start | End | Code | Funcs | Matched | Unit |")
    md.append("|---|---|---|---|---|---|")
    for u in units:
        if u["region"] != "game":
            continue
        md.append(
            f"| 0x{u['start']:08X} | 0x{u['end']:08X} | {u['code']} | {u['functions']} | {u['matched']:.0f}% | {u['name']}{' (sinit)' if u['sinit'] else ''} |"
        )
    md.append("")

    hand = [u for u in units if not u["auto"]]
    md.append("## Hand-split units\n")
    if hand:
        for u in hand:
            md.append(f"- {u['name']}: 0x{u['start']:08X}-0x{u['end']:08X}, {u['matched']:.0f}% matched")
    else:
        md.append("None yet.")
    md.append("")
    if notes_path.exists():
        md.append("See also `docs/NOTES.md` for hand-written notes and gotchas.\n")

    (out_dir / f"{ver}.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(f"Wrote {out_dir / (ver + '.md')}, functions.tsv ({len(funcs)}), units.tsv ({len(units)})")


if __name__ == "__main__":
    main()
