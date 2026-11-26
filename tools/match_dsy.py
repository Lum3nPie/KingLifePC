#!/usr/bin/env python3
"""Name SDK functions by matching them against a Dolphin .dsy signature database.

Uses the same opcode-only checksum as Dolphin's HashSignatureDB, so relocations and
register numbers do not matter. A match needs the same checksum and the same size.

Usage:
  python tools/match_dsy.py <totaldb.dsy> [--apply]

Without --apply it prints the matches (address, size, name). With --apply it renames
the matching auto-named functions (fn_XXXXXXXX) in config/<VERSION>/symbols.txt.
"""

import argparse
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def checksum(words):
    s = 0
    for opcode in words:
        op = opcode & 0xFC000000
        op2 = 0
        op3 = 0
        aux = op >> 26
        if aux == 4:
            op2 = opcode & 0x3F
            if op2 in (0, 8, 16, 21, 22):
                op3 = opcode & 0x7C0
        elif aux in (7, 8, 10, 11, 12, 13, 14, 15):
            op2 = opcode & 0x03FF0000
        elif aux in (19, 31, 63):
            op2 = opcode & 0x7FF
        elif aux == 59:
            op2 = opcode & 0x3F
            if op2 < 16:
                op3 = opcode & 0x7C0
        elif 32 <= aux < 56:
            op2 = opcode & 0x03FF0000
        s = ((s << 17) & 0xFFFE0000) | ((s >> 15) & 0x0001FFFF)
        s ^= op | op2 | op3
    return s


def load_dsy(path):
    data = Path(path).read_bytes()
    count = struct.unpack_from("<I", data, 0)[0]
    db = {}
    off = 4
    for _ in range(count):
        cs, size = struct.unpack_from("<II", data, off)
        raw = data[off + 8 : off + 136].split(b"\0", 1)[0].decode("latin-1")
        # Entries look like "OSInitMessageQueue \tos.a OSMessage.o": name, then library and object.
        name = raw.split("\t")[0].strip()
        db.setdefault(cs, []).append((size, name))
        off += 136
    return db


def load_dol(path):
    data = Path(path).read_bytes()
    offs = struct.unpack(">18I", data[0:72])
    addrs = struct.unpack(">18I", data[72:144])
    sizes = struct.unpack(">18I", data[144:216])
    secs = [(addrs[i], sizes[i], offs[i]) for i in range(7) if sizes[i]]

    def read(addr, n):
        for a, sz, o in secs:
            if a <= addr and addr + n <= a + sz:
                return data[o + addr - a : o + addr - a + n]
        return None

    return read


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dsy")
    ap.add_argument("--version", default="WFCPGD")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-addr", type=lambda x: int(x, 0), default=0x800DDCB0,
                    help="only match at or above this address (default: start of the SDK)")
    ap.add_argument("--min-size", type=lambda x: int(x, 0), default=0x10)
    args = ap.parse_args()

    db = load_dsy(args.dsy)
    read = load_dol(ROOT / "orig" / args.version / "sys" / "main.dol")
    sym_path = ROOT / "config" / args.version / "symbols.txt"
    lines = sym_path.read_text(encoding="utf-8").split("\n")
    existing = {l.split(" = ")[0] for l in lines if " = " in l}

    matches = {}
    for i, line in enumerate(lines):
        m = re.match(r"^(\S+) = \.(?:text|init):0x([0-9A-F]+); // type:function size:0x([0-9A-F]+)", line)
        if not m:
            continue
        name, addr, size = m.group(1), int(m.group(2), 16), int(m.group(3), 16)
        code = read(addr, size)
        if code is None or size < args.min_size or addr < args.min_addr:
            continue
        cs = checksum(struct.unpack(">%dI" % (size // 4), code[: size // 4 * 4]))
        # Plain C identifiers only: the C++ entries in the database are mostly other games' code.
        cands = sorted({n for s, n in db.get(cs, []) if s == size and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", n)})
        if len(cands) == 1:
            matches[i] = (addr, size, name, cands[0])

    # Drop names that would collide (same DB name matched twice, or already used elsewhere).
    by_name = {}
    for i, (_, _, _, new) in matches.items():
        by_name.setdefault(new, []).append(i)
    applied = 0
    for i, (addr, size, old, new) in sorted(matches.items(), key=lambda kv: kv[1][0]):
        unique = len(by_name[new]) == 1 and (new == old or new not in existing)
        print(f"{addr:08X}\t{size:X}\t{old}\t{new}{'' if unique else '\t(ambiguous, skipped)'}")
        if args.apply and unique and old != new and re.match(r"^fn_[0-9A-F]{8}$", old):
            lines[i] = new + lines[i][len(old):]
            applied += 1
    if args.apply:
        sym_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"# {len(matches)} matches, {applied} renamed")


if __name__ == "__main__":
    main()
