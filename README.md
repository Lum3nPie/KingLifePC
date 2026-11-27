# KingLife

**KingLife** is a native Windows port of *My Life as a King* (WiiWare, PAL, `WFCPGD`), the city-building
game from 2008. The port is a **static recompilation**, not an emulator: the game's PowerPC code is
translated to C++ by [WiiCompiled](https://github.com/patchzyy/Wiicompiled) and runs on its runtime,
with rendering through [aurora](https://github.com/encounter/aurora) (Direct3D 12 or Vulkan).

Current version: **0.4**.

> **No game files are in this repository, and none are distributed.** To build and play KingLife you
> need your own dump of the game (and of its add-on content, if you want it).

## Features

- **Native 60 FPS.** The game logic runs at 60 Hz, with gameplay, animations, cutscenes, effects,
  menus and music at their normal speed, without frame interpolation. The original 30 FPS is one
  launcher away (`LIFEKING_FPS=30`).
- **Controllers.** Xbox, DualSense and other SDL pads, laid out by position like a Wii Classic
  Controller: right button (Xbox B) confirms, bottom (Xbox A) cancels, left (Xbox X) calls Chime,
  top (Xbox Y) is the top view. The right stick moves the view the way it is pushed. Keyboard and
  mouse (as the pointer) work too. F10 opens the settings (bindings, graphics API, resolution...).
- **16:9 picture** that keeps its shape in any window size or in full screen, with black bars.
- **Add-on content (DLC).** The 15 packs of the WiiWare DLC, installed from your own dump with
  `port/tools/install_dlc.py`.
- Sound, and a native `KingLife.exe` with its own icon.

## What you need

- Windows (x64).
- Your own decrypted dump of the WiiWare title `00010001-57464350` (contents `00000000.app` to
  `00000009.app`). The DLC (`00010005-77464350`) is optional.
- To build: .NET 8 SDK, CMake 3.25 or later, Ninja, LLVM-MinGW (clang) and Python 3.

## Building and playing

The full steps (WiiCompiled clone and patches, game data layout, build script) are in
[`port/README.md`](port/README.md). In short:

1. Clone WiiCompiled into `port/Wiicompiled` at the pinned commit and apply `port/patches/`.
2. Put your decrypted contents in `port/lifeking-data/content/` and extract the game data.
3. Run `pwsh port/tools/build.ps1`. It builds `KingLife.exe` in
   `port/Wiicompiled/build/lifeking-native` and makes the 60 FPS data patch from your own files.
4. Optional: `python port/tools/install_dlc.py <folder with your DLC contents>`.
5. Start `KingLife.exe` from its folder.

## Repository layout

- `port/`: the PC port (WiiCompiled patches, recompiler project, build and data tools).
- `config/`, `src/`, `include/`: a decompilation of the game, built with
  [decomp-toolkit](https://github.com/encounter/decomp-toolkit). It is the reference used to name the
  game's functions for the port.
- `docs/NOTES.md`: the project notes (how the port was made, 60 FPS work, controller, DLC).

## Licence

Everything under `port/` is **GPL-3.0** (see `port/LICENSE`), because it patches WiiCompiled
(GPL-3.0) and reuses the foreign-game patches of
[HarvestMoonAnimalParadeRecomp](https://github.com/RodoLy/HarvestMoonAnimalParadeRecomp) (GPL-3.0).
The rest of the repository comes from
[dtk-template](https://github.com/encounter/dtk-template) and keeps its CC0 licence (`LICENSE`).
*My Life as a King* belongs to its rights holders. This project is not affiliated with them.

## Credits

- [WiiCompiled](https://github.com/patchzyy/Wiicompiled): Wii static recompiler and runtime.
- [HarvestMoonAnimalParadeRecomp](https://github.com/RodoLy/HarvestMoonAnimalParadeRecomp):
  foreign-game support for the WiiCompiled runtime.
- [aurora](https://github.com/encounter/aurora): GX rendering layer (on Dawn) and SDL input.
- [decomp-toolkit](https://github.com/encounter/decomp-toolkit) and
  [dtk-template](https://github.com/encounter/dtk-template): the decompilation tooling.
- [Dolphin](https://github.com/dolphin-emu/dolphin): reference for the hardware and the SDK.
