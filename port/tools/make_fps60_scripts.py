#!/usr/bin/env python3
"""Make the 60 Hz versions of My Life as a King's Squirrel scripts from Liara's own game files.

The game's logic steps once per frame. At 60 FPS (LIFEKING_FPS=60) the engine reports 60 to the
scripts (CGetFPS), and the scripts that already scale with it (modFrame, modFrameSpeed, the day
clock's ONE_HOUR_FRAME) keep their speed; the values written per frame in the scripts are rescaled
here by 30/CGetFPS (speeds) or CGetFPS/30 (frame counts). Only changed files are written, into a
disc-shaped overlay folder (files/script/...) that the runtime reads through LIFEKING_OVERLAY_ROOT.
The output is game content: never commit it.

Usage: python make_fps60_scripts.py [--data port/lifeking-data/DATA] [--out port/lifeking-mod60]
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEED = "*30.0/::CGetFPS()"   # per-frame amount -> same amount per second
FRAMES = "*::CGetFPS()/30"    # frame count -> same duration

# (file glob, regex, replacement, what). Each rule must match at least once, so a game update or a
# typo shows up instead of silently doing nothing.
# Speeds are rescaled where the scripts hand them to the engine (and back), so every script keeps
# working in its own per-30-Hz-frame units, events with constant speeds included.
RULES = [
    ("ProgramArchlordComp_*.nut", r"::worldEngine\.setTopSpeed\(([^,()]+), (.+)\);",
     rf"::worldEngine.setTopSpeed(\1, (\2){SPEED});", "actor top speed, script -> engine"),
    ("ProgramArchlordComp_*.nut", r"return ::worldEngine\.(getTopSpeed|getSpeed)\(([^()]+)\);",
     rf"return ::worldEngine.\1(\2){FRAMES};", "actor speed, engine -> script"),
    ("ProgramArchlordComp_*.nut", r"::worldEngine\.setSpeed\(([^,()]+), ([^;]+)\);",
     rf"::worldEngine.setSpeed(\1, (\2){SPEED});", "path-following object speed"),
    # CUpdateModels takes the microseconds since the last update; during camera events the scripts
    # pass one 30 (or 25) FPS frame instead, which at 60 FPS ran cutscenes twice as fast.
    ("ProgramArchlordComp_*.nut", r"diff = 100000/(3\.0|2\.5);",
     r"diff = 1000000.0/::CGetFPS();", "camera-event model clock (one frame)"),
    # Camera moved by the pad (height, swing) and rolled by events, all by an amount per frame.
    ("ProgramArchlordComp_*.nut", r"(function changeHeight\(change\)\r?\n\t\{)",
     rf"\1 change = change{SPEED};", "camera height step"),
    ("ProgramArchlordComp_*.nut", r"return ::worldEngine\.changeCameraSwingAngle\(_id, yAngle\);",
     rf"return ::worldEngine.changeCameraSwingAngle(_id, (yAngle){SPEED});", "camera swing step"),
    ("ProgramArchlordComp_*.nut", r"_twistAdd = twistByFrame;",
     rf"_twistAdd = twistByFrame{SPEED};", "camera roll step"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=HERE.parent / "lifeking-data" / "DATA")
    ap.add_argument("--out", type=Path, default=HERE.parent / "lifeking-mod60")
    args = ap.parse_args()
    src_dir = args.data / "files" / "script"
    out_dir = args.out / "files" / "script"
    if not src_dir.is_dir():
        sys.exit(f"no scripts at {src_dir}")
    texts = {}
    failed = False
    for glob, pattern, repl, what in RULES:
        files = sorted(src_dir.glob(glob))
        total = 0
        for f in files:
            text = texts.get(f) or f.read_bytes().decode("latin-1")
            text, n = re.subn(pattern, repl, text)
            texts[f] = text
            total += n
        print(f"{total:5d}  {what}")
        if total == 0:
            print(f"       no match for {pattern!r} in {glob}")
            failed = True
    if failed:
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)
    for f, text in texts.items():
        if text != f.read_bytes().decode("latin-1"):
            (out_dir / f.name).write_bytes(text.encode("latin-1"))
            print(f"wrote {out_dir / f.name}")


if __name__ == "__main__":
    main()
