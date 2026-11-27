# KingLife: My Life as a King PC port (v0.3)

A native Windows build of *My Life as a King* (WiiWare, PAL, `WFCP`), made by **static
recompilation**: the game's PowerPC code is translated to C++ by
[WiiCompiled](https://github.com/patchzyy/Wiicompiled) and runs on its runtime (rendering through
aurora/Dawn: Direct3D 12, Vulkan or Metal). No emulator at runtime.

**No game files are in this repository.** You need your own dump of the WiiWare title
(00010001-57464350): the decrypted contents `00000000.app` to `00000009.app` and the DOL
(content `00000001.app`).

## Licence

Everything under `port/` is **GPL-3.0** (see `port/LICENSE`): it patches WiiCompiled (GPL-3.0) and
reuses the foreign-game patches of
[HarvestMoonAnimalParadeRecomp](https://github.com/RodoLy/HarvestMoonAnimalParadeRecomp) (GPL-3.0).
The decompilation in the rest of this repository keeps its own licence.

## What works (v0.3)

- Boots to the title screen, new game, prologue and play.
- Controls: any pad (Xbox Series, DualSense...) through SDL, keyboard, mouse as the pointer. The
  game reads the pad as a GameCube controller. The face buttons go by position, as on a Wii Classic
  Controller: right (Xbox B) confirms, bottom (Xbox A) cancels, left (Xbox X) calls Chime, top
  (Xbox Y) is the top view. Left and right are swapped on the right stick, so the view turns the
  way it is pushed. F10 opens the settings (bindings, graphics API, resolution...).
- Sound, 16:9 picture stretched to the window.
- **Native 60 FPS** (new in v0.2): the game logic runs at 60 Hz with game, animations, cutscenes,
  effects, menus and music at their normal speed, without frame interpolation. `LIFEKING_FPS=30`
  gives the original 30 FPS. The 60 FPS mode needs a patched copy of the data archive, which
  `build.ps1` makes from your own content 2 into `port/lifeking-mod60` (see `docs/NOTES.md`).
- The app is called **KingLife** (`KingLife.exe`, blue crystal icon drawn by `tools/make_icon.py`); the
  window shows "KingLife <version>", written once in `runtime/include/lifeking_version.h`.

Tip: leave F10's frame interpolation Off. It costs a lot on the render thread, and since the game's
logic is tied to its frames, it slowed the game and the music in heavy scenes (Chime, buildings).

## Building

Tools: .NET 8 SDK, CMake >= 3.25, Ninja, LLVM-MinGW (clang), Python 3.

```powershell
winget install Microsoft.DotNet.SDK.8 Kitware.CMake MartinStorsjo.LLVM-MinGW.UCRT
pip install ninja
```

Layout (all inside `port/`, ignored by git except `tools/`, `patches/`, `project/`):

```
port/
  Wiicompiled/          clone of WiiCompiled at 27ff3b0 + patches/*.patch
  lifeking-data/DATA/   the game's data (see below)
  lifeking-data/content/ the decrypted .app contents
  tools/  patches/  project/
```

1. WiiCompiled:
   ```powershell
   git clone https://github.com/patchzyy/Wiicompiled port/Wiicompiled
   cd port/Wiicompiled
   git checkout 27ff3b0
   git submodule update --init
   git apply ../patches/wiicompiled-lifeking.patch
   git -C aurora-main apply ../../patches/aurora-lifeking.patch
   mkdir projects/lifeking/native
   copy ../project/recomp.yml projects/lifeking/recomp.yml
   mkdir Assets/lifeking; copy <your 00000001.app> Assets/lifeking/main.dol
   dotnet build translator/src/Translator.Cli/Translator.Cli.csproj -c Release
   ```
2. The function map: `python tools/index_project.py` at the repository root writes
   `docs/index/functions.tsv`; turn it into `projects/lifeking/MAP.txt` (one `addr 0xADDR` line per
   function), see `docs/NOTES.md`.
3. Game data: copy the decrypted `.app` files to `port/lifeking-data/content/`, then extract the U8
   archives (content 2 first, then 3 to 8 on top) into `port/lifeking-data/DATA/files`:
   ```powershell
   python port/tools/u8extract.py port/lifeking-data/content/00000002.app port/lifeking-data/DATA/files
   ```
   and create `DATA/sys/boot.bin` (0x440 bytes starting with `WFCPGD`), `DATA/sys/bi2.bin` and a
   minimal `DATA/sys/fst.bin` (see `docs/NOTES.md`).
4. Build: `pwsh port/tools/build.ps1` (writes the layer, translates, builds `KingLife.exe` in
   `port/Wiicompiled/build/lifeking-native`, then the 60 FPS data patch).

Run `KingLife.exe` from its folder (`set LIFEKING_FPS=30` first for 30 FPS). The game data folder is found next to the build; it can also
be set in `%LOCALAPPDATA%\WiiCompiled\Config.toml` (`[paths] dvd_root`).

## How it was made

See `docs/NOTES.md` (sections "PC port strategy" and after): the SDK functions were named in the
decompilation (Dolphin's signature database, then alignment with Mario Kart Wii's map), WiiCompiled's
natives placed at this game's addresses (`tools/make_layer.py`, `tools/tables/`), and the runtime
completed for a WiiWare title (ES contents, ticket views, DVD-on-NAND, Bluetooth start-up wait,
GXSetDrawDone/GXWaitDrawDone, Classic Controller).
