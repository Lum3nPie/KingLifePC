#!/usr/bin/env python3
"""Nintendo LZ11 (header byte 0x11), the compression of the game's ".press" files.

decompress(data) -> bytes, compress(data) -> bytes. The compressor is a greedy match search with
hash chains: much slower than C but fine for the few script files the 60 FPS patch rewrites.
"""


def decompress(src: bytes) -> bytes:
    if not src or src[0] != 0x11:
        raise ValueError("not LZ11 data")
    size = int.from_bytes(src[1:4], "little")
    pos = 4
    if size == 0:
        size = int.from_bytes(src[4:8], "little")
        pos = 8
    out = bytearray()
    while len(out) < size:
        flags = src[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= size:
                break
            if not (flags >> bit) & 1:
                out.append(src[pos])
                pos += 1
                continue
            b0 = src[pos]
            ind = b0 >> 4
            if ind == 0:
                length = (((b0 & 0xF) << 4) | (src[pos + 1] >> 4)) + 0x11
                disp = ((src[pos + 1] & 0xF) << 8) | src[pos + 2]
                pos += 3
            elif ind == 1:
                length = (((b0 & 0xF) << 12) | (src[pos + 1] << 4) | (src[pos + 2] >> 4)) + 0x111
                disp = ((src[pos + 2] & 0xF) << 8) | src[pos + 3]
                pos += 4
            else:
                length = ind + 1
                disp = ((b0 & 0xF) << 8) | src[pos + 1]
                pos += 2
            start = len(out) - disp - 1
            if start < 0:
                raise ValueError("bad LZ11 back-reference")
            for i in range(length):
                out.append(out[start + i])
    return bytes(out[:size])


WINDOW = 0x1000
MAX_LEN = 0x10110
CHAIN = 32


def compress(data: bytes) -> bytes:
    n = len(data)
    out = bytearray([0x11])
    if n < 0x1000000:
        out += n.to_bytes(3, "little")
    else:
        out += b"\0\0\0" + n.to_bytes(4, "little")
    heads = {}
    pos = 0

    def insert(p):
        if p + 3 <= n:
            key = data[p:p + 3]
            chain = heads.get(key)
            if chain is None:
                heads[key] = [p]
            else:
                chain.append(p)
                if len(chain) > CHAIN * 4:
                    del chain[:-CHAIN]

    while pos < n:
        flag_at = len(out)
        out.append(0)
        flags = 0
        for bit in range(7, -1, -1):
            if pos >= n:
                break
            best_len, best_disp = 0, 0
            if pos + 3 <= n:
                chain = heads.get(data[pos:pos + 3])
                if chain:
                    limit = min(MAX_LEN, n - pos)
                    for cand in reversed(chain[-CHAIN:]):
                        disp = pos - cand
                        if disp > WINDOW:
                            break
                        length = 3
                        while length < limit and data[cand + length] == data[pos + length]:
                            length += 1
                        if length > best_len:
                            best_len, best_disp = length, disp
                            if length == limit:
                                break
            if best_len >= 3:
                flags |= 1 << bit
                d = best_disp - 1
                if best_len <= 0x10:
                    out += bytes([((best_len - 1) << 4) | (d >> 8), d & 0xFF])
                elif best_len <= 0x110:
                    l = best_len - 0x11
                    out += bytes([l >> 4, ((l & 0xF) << 4) | (d >> 8), d & 0xFF])
                else:
                    l = best_len - 0x111
                    out += bytes([0x10 | (l >> 12), (l >> 4) & 0xFF, ((l & 0xF) << 4) | (d >> 8), d & 0xFF])
                for p in range(pos, pos + best_len):
                    insert(p)
                pos += best_len
            else:
                out.append(data[pos])
                insert(pos)
                pos += 1
        out[flag_at] = flags
    while len(out) % 4:
        out.append(0)
    return bytes(out)
