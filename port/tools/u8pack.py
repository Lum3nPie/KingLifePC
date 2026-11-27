#!/usr/bin/env python3
"""Read a U8 archive (a decrypted WiiWare content .app) and write it back with some files replaced.

files(data) -> {path: bytes}; rebuild(data, {path: new bytes}) -> bytes. The node and name tables
stay as they are; only file offsets and sizes change, and the data is laid out again in the
original order with 0x20 alignment.
"""
import struct

MAGIC = 0x55AA382D


def _nodes(data: bytes):
    magic, root, _header_size, _data_off = struct.unpack_from(">IIII", data, 0)
    if magic != MAGIC:
        raise ValueError("not a U8 archive")
    total = struct.unpack_from(">I", data, root + 8)[0]
    strings = root + total * 12

    def name_at(off):
        end = data.index(b"\0", strings + off)
        return data[strings + off:end].decode("latin-1")

    stack = [("", total)]
    for i in range(1, total):
        while stack and i >= stack[-1][1]:
            stack.pop()
        kind_name, a, b = struct.unpack_from(">III", data, root + i * 12)
        path = stack[-1][0] + "/" + name_at(kind_name & 0xFFFFFF)
        if kind_name >> 24 == 1:
            stack.append((path, b))
        else:
            yield i, path, a, b


def is_u8(data: bytes) -> bool:
    return len(data) >= 4 and struct.unpack_from(">I", data, 0)[0] == MAGIC


def files(data: bytes) -> dict:
    return {path: data[a:a + b] for _i, path, a, b in _nodes(data)}


def rebuild(data: bytes, replace: dict) -> bytes:
    _magic, root, _header_size, data_off = struct.unpack_from(">IIII", data, 0)
    entries = sorted(_nodes(data), key=lambda e: e[2])
    missing = set(replace) - {e[1] for e in entries}
    if missing:
        raise KeyError(f"not in the archive: {sorted(missing)}")
    out = bytearray(data[:data_off])
    for i, path, a, b in entries:
        blob = replace.get(path, data[a:a + b])
        while len(out) % 0x20:
            out.append(0)
        struct.pack_into(">II", out, root + i * 12 + 4, len(out), len(blob))
        out += blob
    while len(out) % 0x20:
        out.append(0)
    return bytes(out)
