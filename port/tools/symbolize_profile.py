#!/usr/bin/env python3
"""Turn %TEMP%/lifeking_profile.txt (RVA counts) into the hottest functions of WiiCompiled.exe.

Usage: python symbolize_profile.py <profile.txt> <nm_output.txt> [top]
nm_output.txt: `llvm-nm -C --defined-only WiiCompiled.exe` (addresses with image base 0x140000000).
"""
import bisect
import re
import sys
from collections import Counter

prof, nmfile = sys.argv[1], sys.argv[2]
top = int(sys.argv[3]) if len(sys.argv) > 3 else 40
BASE = 0x140000000

syms = []
for line in open(nmfile, encoding="utf-8", errors="replace"):
    m = re.match(r"^([0-9a-f]+) ([tTwW]) (.+)$", line.strip())
    if m:
        syms.append((int(m.group(1), 16) - BASE, m.group(3)))
syms.sort()
addrs = [a for a, _ in syms]

counts = Counter()
total = 0
outside = 0
for line in open(prof):
    if line.startswith("#"):
        continue
    rva_s, n_s = line.split()
    rva, n = int(rva_s, 16), int(n_s)
    total += n
    if rva >= 1 << 40 or rva > addrs[-1] + 0x100000:
        outside += n
        counts["<outside the exe: system DLLs, driver, sleeping>"] += n
        continue
    i = bisect.bisect_right(addrs, rva) - 1
    counts[syms[i][1] if i >= 0 else "<?>"] += n

print(f"{total} samples, {outside} outside the exe ({outside * 100.0 / max(total, 1):.1f}%)")
for name, n in counts.most_common(top):
    print(f"{n * 100.0 / total:6.2f}%  {n:7d}  {name[:140]}")
