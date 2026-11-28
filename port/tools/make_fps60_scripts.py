#!/usr/bin/env python3
"""Make the 60 Hz data archive of My Life as a King from Liara's own game files.

The game reads its Squirrel scripts from content 2 (00000002.app, an uncompressed U8 archive) through
ES/CNT, not from the DVD files. This tool copies that content and patches the script text in place,
always with replacements of the same length, so no offset of the archive moves. The runtime reads
the copy through LIFEKING_OVERLAY_ROOT/content (nand_isfs.cpp), set by the 60 FPS launcher.
The output is game content: never commit it.

Add-on content (DLC, port/lifeking-data/dlc, see install_dlc.py): packs 8 to 10 carry a newer copy
of the game's program scripts (script/*.nut.press, LZ11), which the game loads instead of content 2's.
Those copies get the same replacements: decompressed, patched, compressed again, and their U8
archive rebuilt into lifeking-mod60/dlc/.

Usage: python make_fps60_scripts.py [--data port/lifeking-data] [--out port/lifeking-mod60]
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lz11  # noqa: E402
import u8pack  # noqa: E402

HERE = Path(__file__).resolve().parent

# (pattern, replacement, expected count, what). Same length each; the count guards against a
# different game version.
RULES = [
    # CUpdateModels takes the microseconds since the last update. During camera events and demo
    # scenes the scripts pass one 30 Hz (or 25 Hz) frame instead, which at 60 FPS ran every
    # cutscene animation twice as fast. GAME_SPF is the scripts' own 1/CGetFPS(); the line's
    # indentation and trailing tab make room. (A first try with the literal 1e6 broke the script
    # load: this Squirrel does not take that notation.)
    (b"\t\t\tdiff = 100000/3.0;\t", b"diff=1000000*GAME_SPF;", 4, "camera-event model clock, 60 Hz branch"),
    (b"\t\t\tdiff = 100000/2.5;\t", b"diff=1000000*GAME_SPF;", 3, "camera-event model clock, 50 Hz branch"),
    # The name keyboards (MenuKeyboard, MenuKeyboardParentalControlPassword) blink the input cursor
    # every EFFECT_TIME frames: 6 frames at 30 Hz, so 12 at 60 Hz.
    (b"static EFFECT_TIME\t= 6;\t", b"static EFFECT_TIME\t=12;\t", 1, "name keyboard cursor blink"),
    (b"static EFFECT_TIME\t\t= 6;\t", b"static EFFECT_TIME\t\t=12;\t", 1, "password keyboard cursor blink"),
    # Adventuring parties (ArchParty) take one step in their dungeon every FRAMES_PER_STEP frames:
    # 60 frames, two seconds at 30 Hz. At 60 Hz they explored twice as fast and came home early.
    (b"static FRAMES_PER_STEP\t\t\t= 60;", b"static FRAMES_PER_STEP\t\t\t=120;", 1, "adventure step interval"),
    # The city checks every 60 frames whether to send more villagers out, and the adventurer
    # dispatcher every 90: keep those at two and three seconds.
    (b"if ( (time % 60) == 20 ) {", b"if ( (time %120) == 20 ) {", 1, "villager pop check interval"),
    (b"(gameTime % 90) == 0", b"(gameTime %180) == 0", 1, "party creation check interval"),
    # Not a 60 Hz rule: F10 "UI scale" > "Over characters" (lifeking_ui_scale.cpp). ActorIcon.setScale
    # passes a negative x scale, which tells the runtime the object is an icon over a character (!,
    # smiley...); the runtime makes it positive again and applies the setting.
    (b"setObjectScale(_iconID, scale, scale, scale)", b"setObjectScale(_iconID,-scale, scale, scale)", 1,
     "icons over characters marked for the UI scale"),
]


def patch(data: bytearray, label: str) -> None:
    for pattern, repl, expected, what in RULES:
        assert len(pattern) == len(repl), what
        hits = [m.start() for m in re.finditer(re.escape(pattern), bytes(data))]
        print(f"{len(hits):5d}  {what}")
        if len(hits) != expected:
            sys.exit(f"{label}: expected {expected} matches of {pattern!r}")
        for at in hits:
            data[at:at + len(repl)] = repl


def patch_dlc(src_dir: Path, out_dir: Path) -> None:
    """Patched copies of the DLC contents whose scripts hold the 60 Hz rules; the rest is not copied
    (the runtime falls back to lifeking-data/dlc for a content missing here)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.app"):
        old.unlink()
    for app in sorted(src_dir.glob("*.app")):
        data = app.read_bytes()
        if not u8pack.is_u8(data):
            continue
        replace = {}
        for path, blob in u8pack.files(data).items():
            if "/script/" not in path or not path.endswith((".nut", ".nut.press")):
                continue
            packed = blob[:1] == b"\x11"
            text = lz11.decompress(blob) if packed else blob
            if not any(rule[0] in text for rule in RULES):
                continue
            print(f"dlc {app.name}{path}")
            text = bytearray(text)
            patch(text, f"{app.name}{path}")
            replace[path] = lz11.compress(bytes(text)) if packed else bytes(text)
        if replace:
            (out_dir / app.name).write_bytes(u8pack.rebuild(data, replace))
            print(f"wrote {out_dir / app.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=HERE.parent / "lifeking-data")
    ap.add_argument("--out", type=Path, default=HERE.parent / "lifeking-mod60")
    args = ap.parse_args()
    src = args.data / "content" / "00000002.app"
    if not src.is_file():
        sys.exit(f"no data archive at {src}")
    data = bytearray(src.read_bytes())
    patch(data, src.name)
    out = args.out / "content" / "00000002.app"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"wrote {out}")
    stale = args.out / "files"
    if stale.is_dir():
        shutil.rmtree(stale)  # earlier versions patched the DVD copy, which the game never reads
    if (args.data / "dlc").is_dir():
        patch_dlc(args.data / "dlc", args.out / "dlc")
    elif (args.out / "dlc").is_dir():
        shutil.rmtree(args.out / "dlc")


if __name__ == "__main__":
    main()
