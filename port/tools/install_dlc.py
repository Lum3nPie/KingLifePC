#!/usr/bin/env python3
"""Install the add-on content (DLC) of My Life as a King for KingLife, from the player's own dump.

The DLC is the WiiWare title 00010005-77464350: data only (script packs, costumes, dungeons). Give
the folder of its decrypted contents, named by index as dumping tools write them (00000000.app,
00000001.app...) with the title's .tmd (and .tik if there is one). Each content is checked
against the SHA-1 of the TMD, then copied to port/lifeking-data/dlc/, where the runtime finds it
(nand_isfs.cpp). The 60 FPS copies of the packs that carry the game's scripts are made again in
port/lifeking-mod60/dlc/. All of it is game content: never commit it.

Usage:
  python install_dlc.py [<dlc folder>]   (default: dev/work/LifeKing (DLC) of the game folder)
  python install_dlc.py --remove         (back to the game without DLC)
"""
import argparse
import hashlib
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = HERE.parent
DLC_TITLE = "0001000577464350"
DEFAULT_SRC = PORT.parent / "dev" / "work" / "LifeKing (DLC)"


def tmd_contents(tmd: bytes):
    if tmd[0x18C:0x194].hex() != DLC_TITLE:
        sys.exit(f"this TMD is for title {tmd[0x18C:0x194].hex()}, not the DLC {DLC_TITLE}")
    count = struct.unpack_from(">H", tmd, 0x1DE)[0]
    for i in range(count):
        cid, index, _kind, size = struct.unpack_from(">IHHQ", tmd, 0x1E4 + 36 * i)
        yield cid, index, size, tmd[0x1E4 + 36 * i + 16:0x1E4 + 36 * i + 36]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--data", type=Path, default=PORT / "lifeking-data")
    ap.add_argument("--remove", action="store_true")
    args = ap.parse_args()
    dst = args.data / "dlc"

    if args.remove:
        if dst.is_dir():
            shutil.rmtree(dst)
        mod = PORT / "lifeking-mod60" / "dlc"
        if mod.is_dir():
            shutil.rmtree(mod)
        print("DLC removed")
        return

    tmds = list(args.src.glob(f"{DLC_TITLE}.tmd")) or list(args.src.glob("*.tmd"))
    if not tmds:
        sys.exit(f"no {DLC_TITLE}.tmd in {args.src}")
    tmd = tmds[0].read_bytes()
    found = []
    for cid, index, size, sha1 in tmd_contents(tmd):
        app = args.src / f"{index:08x}.app"
        if not app.is_file():
            app = args.src / f"{cid:08x}.app"  # some tools name contents by id
        if not app.is_file():
            print(f"  content {index:2d}: missing (pack not bought?)")
            continue
        data = app.read_bytes()
        if hashlib.sha1(data[:size]).digest() != sha1:
            sys.exit(f"{app.name}: SHA-1 does not match the TMD (still encrypted, or another version)")
        found.append((index, data[:size]))
    if not found:
        sys.exit("no DLC content found")

    if dst.is_dir():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for index, data in found:
        (dst / f"{index:08x}.app").write_bytes(data)
    (dst / f"{DLC_TITLE}.tmd").write_bytes(tmd)
    tik = args.src / f"{DLC_TITLE}.tik"
    if tik.is_file():
        shutil.copyfile(tik, dst / tik.name)
    print(f"{len(found)} DLC contents installed in {dst}: " + ", ".join(str(i) for i, _ in found))

    if (args.data / "content" / "00000002.app").is_file():
        subprocess.run([sys.executable, "-I", str(HERE / "make_fps60_scripts.py"), "--data", str(args.data)],
                       check=True, stdout=subprocess.DEVNULL)
        print("60 FPS copies made in", PORT / "lifeking-mod60" / "dlc")


if __name__ == "__main__":
    main()
