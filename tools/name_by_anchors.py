#!/usr/bin/env python3
"""Name SDK functions from a reference game's map, between functions both games already name.

SDK libraries keep the same function order from game to game. Between two consecutive "anchors"
(functions with the same name in both games, in the same order), if both games have the same number
of functions in between and every pair has the same size (or both sizes are within --tolerance),
the reference names are copied onto our auto-named functions.

Reference map format: one "address name" per line (e.g. WiiCompiled's projects/mkwii/MAP.txt, where
"OS::X" means OSX and "OS::__X" means __OSX). Function sizes are taken as the distance to the next entry.

Usage: python tools/name_by_anchors.py <reference MAP.txt> [--apply]
"""

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def normalize(name):
    if "::" in name:
        lib, rest = name.split("::", 1)
        if "::" in rest or not re.match(r"^[A-Z][A-Z0-9]*$", lib):
            return None
        name = "__" + lib + rest[2:] if rest.startswith("__") else lib + rest
    return name if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) else None


def read_reference(path):
    entries = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2 or parts[1].startswith("0x"):
            continue
        # Labels inside functions (jump-table targets), not functions.
        if re.search(r"_(switch|caseD_\w+|def_\w+)$", parts[1].strip()):
            continue
        entries.append((int(parts[0], 16), parts[1].strip()))
    entries.sort()
    out = []
    for i, (addr, name) in enumerate(entries):
        size = entries[i + 1][0] - addr if i + 1 < len(entries) else 0
        out.append((addr, size, normalize(name)))
    return out


def library(name):
    m = re.match(r"^_*([A-Z]{2,}[a-z]?)(?=[A-Z_]|$)", name or "")
    if not m:
        return None
    lib = m.group(1)
    return lib[:-1] if lib[-1].islower() else lib


def align(mine, theirs, tolerance):
    """Needleman-Wunsch on function sizes: pairs whose sizes are equal (or within tolerance)."""
    n, m = len(mine), len(theirs)

    def score(a, b):
        if a[1] == b[1]:
            return 3
        if abs(a[1] - b[1]) <= tolerance:
            return 1
        return -3

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = -i
    for j in range(1, m + 1):
        dp[0][j] = -j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = max(dp[i - 1][j - 1] + score(mine[i - 1], theirs[j - 1]), dp[i - 1][j] - 1, dp[i][j - 1] - 1)
    pairs = []
    i, j = n, m
    while i > 0 and j > 0:
        if dp[i][j] == dp[i - 1][j - 1] + score(mine[i - 1], theirs[j - 1]):
            if score(mine[i - 1], theirs[j - 1]) > 0:
                pairs.append((mine[i - 1], theirs[j - 1]))
            i, j = i - 1, j - 1
        elif dp[i][j] == dp[i - 1][j] - 1:
            i -= 1
        else:
            j -= 1
    return reversed(pairs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("--version", default="WFCPGD")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tolerance", type=lambda x: int(x, 0), default=0)
    ap.add_argument("--min-addr", type=lambda x: int(x, 0), default=0x800DDCB0)
    ap.add_argument("--lib", help="only work inside the address windows of this library prefix (e.g. GX)")
    ap.add_argument("--margin", type=int, default=40, help="functions kept around a --lib window")
    args = ap.parse_args()

    ref = read_reference(args.reference)
    sym_path = ROOT / "config" / args.version / "symbols.txt"
    lines = sym_path.read_text(encoding="utf-8").split("\n")
    ours = []  # (addr, size, name, line index)
    for i, line in enumerate(lines):
        m = re.match(r"^(\S+) = \.(?:text|init):0x([0-9A-F]+); // type:function size:0x([0-9A-F]+)", line)
        if m and int(m.group(2), 16) >= args.min_addr:
            ours.append((int(m.group(2), 16), int(m.group(3), 16), m.group(1), i))
    ours.sort()
    used = {o[2] for o in ours}
    if args.lib:
        def window(seq, name_of):
            idx = [i for i, e in enumerate(seq) if (name_of(e) or "").lstrip("_").startswith(args.lib)]
            if not idx:
                return seq[:0]
            return seq[max(0, idx[0] - args.margin) : idx[-1] + args.margin + 1]
        ours = window(ours, lambda e: e[2] if not re.match(r"^(fn|lbl)_", e[2]) else None)
        ref = window(ref, lambda e: e[2])

    ref_pos = {}
    for j, (_, _, n) in enumerate(ref):
        if n:
            ref_pos.setdefault(n, []).append(j)
    # Anchors: our named functions whose name appears exactly once in the reference.
    anchors = []
    for k, (_, _, n, _) in enumerate(ours):
        if not re.match(r"^(fn|lbl)_[0-9A-F]{8}$", n) and len(ref_pos.get(n, [])) == 1:
            anchors.append((k, ref_pos[n][0]))
    # Keep the longest chain of anchors increasing in both sequences (libraries can be linked in a
    # different order from game to game, so a greedy pass would drop whole libraries).
    import bisect
    tails, tails_idx, parent = [], [], [None] * len(anchors)
    for idx, (k, j) in enumerate(anchors):
        pos = bisect.bisect_left(tails, j)
        if pos == len(tails):
            tails.append(j)
            tails_idx.append(idx)
        else:
            tails[pos] = j
            tails_idx[pos] = idx
        parent[idx] = tails_idx[pos - 1] if pos > 0 else None
    filtered = []
    idx = tails_idx[-1] if tails_idx else None
    while idx is not None:
        filtered.append(anchors[idx])
        idx = parent[idx]
    filtered.reverse()

    renames = []
    for (k0, j0), (k1, j1) in zip(filtered, filtered[1:]):
        mine = ours[k0 + 1 : k1]
        theirs = ref[j0 + 1 : j1]
        if not mine or not theirs or len(mine) * len(theirs) > 250000:
            continue
        lib0 = library(ours[k0][2])
        lib1 = library(ours[k1][2])
        for m, t in align(mine, theirs, args.tolerance):
            # Only names of the library the surrounding anchors belong to: an exact-size pair across
            # unrelated libraries is a coincidence (it once put SC names on AX callbacks).
            if not t[2] or library(t[2]) not in (lib0, lib1) or not library(t[2]):
                continue
            if t[2] and re.match(r"^fn_[0-9A-F]{8}$", m[2]) and t[2] not in used:
                renames.append((m, t[2]))
                used.add(t[2])

    for (addr, size, old, i), new in renames:
        print(f"{addr:08X}\t{size:X}\t{old}\t{new}")
        if args.apply:
            lines[i] = new + lines[i][len(old):]
    if args.apply:
        sym_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"# anchors {len(filtered)}, renamed {len(renames)}")


if __name__ == "__main__":
    main()
