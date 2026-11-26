#!/usr/bin/env python3
"""Print the data addresses each named function references (from the decomp's dtk asm).

Usage: python refs.py FuncName [FuncName ...]
Shows, in order, every symbol used with @ha/@l/@sda21 and the instruction using it.
"""
import glob
import re
import sys
from pathlib import Path

ASM = Path(__file__).resolve().parent.parent.parent / "build" / "WFCPGD" / "asm"
SYMS = Path(__file__).resolve().parent.parent.parent / "config" / "WFCPGD" / "symbols.txt"

addr_of = {}
for line in SYMS.read_text(encoding="utf-8").splitlines():
    m = re.match(r"^(\S+) = (\S+):0x([0-9A-F]+);", line)
    if m:
        addr_of[m.group(1)] = int(m.group(3), 16)

wanted = set(sys.argv[1:])
for f in glob.glob(str(ASM / "*.s")):
    cur = None
    for line in open(f, encoding="utf-8"):
        m = re.match(r"^\.fn (\S+),", line)
        if m:
            cur = m.group(1).strip('"')
            if cur in wanted:
                print(f"== {cur} 0x{addr_of.get(cur, 0):08X}")
            continue
        if line.startswith(".endfn"):
            cur = None
            continue
        if cur in wanted:
            mm = re.match(r"/\* ([0-9A-F]{8}) [^*]*\*/\s+(.*)", line)
            if mm and re.search(r"@(ha|l|sda21|h)\b", mm.group(2)):
                ins = mm.group(2).strip()
                sm = re.search(r"([A-Za-z_\"][^\s,()]*)@(ha|l|sda21|h)", ins)
                sym = sm.group(1).strip('"') if sm else "?"
                a = addr_of.get(sym) or (int(sym[-8:], 16) if re.search(r"[0-9A-F]{8}$", sym) else 0)
                print(f"  {mm.group(1)}  {ins:<55} 0x{a:08X}")
