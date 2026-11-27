#!/usr/bin/env python3
"""Turn %TEMP%/lifeking_profile.txt into the hottest functions of WiiCompiled.exe, per section.

Usage: python symbolize_profile.py <profile.txt> <nm_output.txt> [top] [section-filter]
nm_output.txt: `llvm-nm -C --defined-only WiiCompiled.exe` (addresses with image base 0x140000000).
Sections are "[<thread> heavy]" / "[<thread> normal]" (heavy = frames whose busy time is >= 20 ms).
Lines are "<rva> <count>", "@<module>+<offset> <count>" (outside the exe), "wait:<kind> <count>"
or "^<caller rva> <count>" (who called into DLLs, found on the stack).
Older profiles without sections are read as one section.
"""
import bisect
import re
import sys
from collections import Counter

prof, nmfile = sys.argv[1], sys.argv[2]
top = int(sys.argv[3]) if len(sys.argv) > 3 else 40
only = sys.argv[4] if len(sys.argv) > 4 else None
BASE = 0x140000000

syms = []
for line in open(nmfile, encoding="utf-8", errors="replace"):
    m = re.match(r"^([0-9a-f]+) ([tTwW]) (.+)$", line.strip())
    if m:
        syms.append((int(m.group(1), 16) - BASE, m.group(3)))
syms.sort()
addrs = [a for a, _ in syms]

sections = {}
callers = {}
order = []
current = "all"
for line in open(prof):
    line = line.strip()
    if not line:
        continue
    if line.startswith("#"):
        print(line)
        continue
    if line.startswith("["):
        current = line.strip("[]")
        continue
    key, n_s = line.rsplit(" ", 1)
    n = int(n_s)
    if current not in sections:
        sections[current] = Counter()
        order.append(current)
    c = sections[current]
    if key.startswith("^"):
        rva = int(key[1:], 16)
        if rva == 0:
            name = "<no caller found>"
        else:
            i = bisect.bisect_right(addrs, rva) - 1
            name = syms[i][1] if i >= 0 else "<?>"
        callers.setdefault(current, Counter())[name] += n
        continue
    if key.startswith("wait:"):
        c["<" + key + ">"] += n
    elif key.startswith("@"):
        c["<dll " + key[1:].split("+")[0] + ">"] += n
    else:
        rva = int(key, 16)
        if rva >= 1 << 40 or rva > addrs[-1] + 0x100000:
            c["<outside the exe>"] += n
        else:
            i = bisect.bisect_right(addrs, rva) - 1
            c[syms[i][1] if i >= 0 else "<?>"] += n

for name in order:
    if only and only not in name:
        continue
    c = sections[name]
    total = sum(c.values())
    waits = sum(v for k, v in c.items() if k.startswith("<wait:"))
    dlls = sum(v for k, v in c.items() if k.startswith("<dll") or k == "<outside the exe>")
    print(f"\n== {name}: {total} samples, waits {waits * 100.0 / max(total, 1):.1f}%, "
          f"outside the exe (not waiting) {dlls * 100.0 / max(total, 1):.1f}%")
    for sym, n in c.most_common(top):
        print(f"{n * 100.0 / total:6.2f}%  {n:7d}  {sym[:140]}")
    if name in callers:
        print(f"  -- callers in the exe of the time outside it (not waiting):")
        for sym, n in callers[name].most_common(15):
            print(f"{n * 100.0 / total:6.2f}%  {n:7d}  {sym[:140]}")
