#!/usr/bin/env python3
"""Extract a U8 archive (e.g. a decrypted WiiWare content .app) to a folder, one level only:
nested archives (.arc) stay files, as the game expects to open them itself.

Usage: python u8extract.py <archive> <out_dir>
"""
import struct
import sys
from pathlib import Path


def extract(data: bytes, out: Path) -> int:
    magic, root_off, header_size, data_off = struct.unpack_from(">IIII", data, 0)
    if magic != 0x55AA382D:
        raise SystemExit("not a U8 archive")
    total = struct.unpack_from(">I", data, root_off + 8)[0]
    strings = root_off + total * 12

    def name_at(off):
        end = data.index(b"\0", strings + off)
        return data[strings + off : end].decode("latin-1")

    # Walk the flat node table keeping a stack of (directory path, end index).
    stack = [(out, total)]
    count = 0
    for i in range(1, total):
        while stack and i >= stack[-1][1]:
            stack.pop()
        kind_name, a, b = struct.unpack_from(">III", data, root_off + i * 12)
        kind = kind_name >> 24
        name = name_at(kind_name & 0xFFFFFF)
        parent = stack[-1][0]
        if kind == 1:
            path = parent / name
            path.mkdir(parents=True, exist_ok=True)
            stack.append((path, b))
        else:
            parent.mkdir(parents=True, exist_ok=True)
            (parent / name).write_bytes(data[a : a + b])
            count += 1
    return count


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    print(f"{extract(src.read_bytes(), dst)} files written to {dst}")
