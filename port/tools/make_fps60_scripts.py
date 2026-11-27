#!/usr/bin/env python3
"""Make the 60 Hz data archive of My Life as a King from Liara's own game files.

The game reads its Squirrel scripts from content 2 (00000002.app, an uncompressed U8 archive) through
ES/CNT, not from the DVD files. This tool copies that content and patches the script text in place,
always with replacements of the same length, so no offset of the archive moves. The runtime reads
the copy through LIFEKING_OVERLAY_ROOT/content (nand_isfs.cpp), set by the 60 FPS launcher.
The output is game content: never commit it.

Usage: python make_fps60_scripts.py [--data port/lifeking-data] [--out port/lifeking-mod60]
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (pattern, replacement, expected count, what). Same length each; the count guards against a
# different game version.
RULES = [
    # CUpdateModels takes the microseconds since the last update. During camera events and demo
    # scenes the scripts pass one 30 Hz (or 25 Hz) frame instead, which at 60 FPS ran every
    # cutscene animation twice as fast. GAME_SPF is the scripts' own 1/CGetFPS(); the line's
    # indentation and trailing tab make room. (A first try with the literal 1e6 broke the script
    # load: this Squirrel does not take that notation.)
    (b"			diff = 100000/3.0;	", b"diff=1000000*GAME_SPF;", 4, "camera-event model clock, 60 Hz branch"),
    (b"			diff = 100000/2.5;	", b"diff=1000000*GAME_SPF;", 3, "camera-event model clock, 50 Hz branch"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=HERE.parent / "lifeking-data")
    ap.add_argument("--out", type=Path, default=HERE.parent / "lifeking-mod60")
    args = ap.parse_args()
    src = args.data / "content" / "00000002.app"
    if not src.is_file():
        sys.exit(f"no data archive at {src}")
    data = bytearray(src.read_bytes())
    for pattern, repl, expected, what in RULES:
        assert len(pattern) == len(repl), what
        hits = [m.start() for m in re.finditer(re.escape(pattern), bytes(data))]
        print(f"{len(hits):5d}  {what}")
        if len(hits) != expected:
            sys.exit(f"expected {expected} matches of {pattern!r}")
        for at in hits:
            data[at:at + len(repl)] = repl
    out = args.out / "content" / "00000002.app"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"wrote {out}")
    stale = args.out / "files"
    if stale.is_dir():
        shutil.rmtree(stale)  # earlier versions patched the DVD copy, which the game never reads


if __name__ == "__main__":
    main()
