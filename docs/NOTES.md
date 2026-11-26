# Working notes: My Life as a King (WFCPGD)

## Project goal (from Liara)
A bootable game, identical to the original, plus Xbox Series and DualSense controller support.
- "Identical" is the matching decomp: `ninja` must keep producing the original main.dol (SHA-1 check).
- Target confirmed: a **PC port**. Liara has no Wiimote, so the game must be fully playable with an Xbox Series or DualSense pad.
- Controller support lives outside the matching build (PC port layer). The input layer (WPAD/KPAD and the game code that reads them) must be replaced by a pad-to-Wiimote mapping (buttons, and a substitute for pointer/IR and motion if the game uses them). Study it once the MSL containers are unblocked.
- Mapping guideline (Liara): base the Xbox/DualSense layout on the Wii **Classic Controller** layout (see Dolphin's Classic Controller mapping in `dev/ref/dolphin-master`). To check: whether the game already reads the Classic Controller through KPAD/WPAD (extension type checks), which would make the mapping direct.

Hand-written notes. Keep them short and up to date. The generated index is in `docs/index/`.

## Game and files
- WiiWare, PAL, title 00010001-57464350 ("WFCP"), maker GD (Square Enix), title version 1.
- `orig/WFCPGD/sys/main.dol` = NAND content `00000001.app` (SHA-1 ab2944ddbae018d562839a4a48b222ada1d3c915). Boot content 9 is the NAND loader. No REL/RSO.
- DLC (00010005-57464350, v2) is data only, no code.
- Original files are gitignored (`orig/*/*`). Never commit them.

## PC port strategy (decided 2026-11-26)
Liara chose **static recompilation** (PowerPC translated to C/C++, system layer rewritten by hand) over a full matching decomp first. The matching decomp continues in parallel where understanding the code helps (input, menus).

### Classic Controller support (checked)
The game reads the Classic Controller through KPAD. Input function at 0x800D1EB4 calls KPADRead (fn_801746A8, buffer of 0x84-byte KPADStatus) per channel after WPADProbe (fn_801626A4), then:
- reads `ex_status.cl.hold` (+0x60) masked with 0xC003 = Classic d-pad (UP 0x1, LEFT 0x2, DOWN 0x4000, RIGHT 0x8000) to move a cursor, diagonals included;
- reads `ex_status.cl.lstick` (+0x6C/+0x70) as an analog stick.
Other game input code lives around 0x80041500-0x80045000. So an Xbox/DualSense pad can be presented to the game as a Classic Controller (Dolphin's layout as reference). Still to check: whether some screens need the Wii Remote pointer (IR) or motion.

### Existing tools (Nov 2026, all GPL-3.0)
- **WiiCompiled** (github.com/patchzyy/Wiicompiled): Wii static recompiler + runtime, rendering through aurora (GX compatibility layer), SDL pads with per-button mapping and Classic Controller support. Base of several Wii ports (NSMB Wii, Wario Land Shake It, PokePark, Mario Kart Wii). Most proven option.
- **DolRecomp** (github.com/ExpansionPak/DolRecomp): GameCube/Wii recompiler (Eternal Darkness, MoH Frontline ports). `mstan/powerpc-recomp-core` is a reusable extraction of its compiler core.
- **wii-recomp** (github.com/Zontex/wii-recomp): recompiles games and the Wii Menu into a whole emulated-console runtime; heavier than needed.
- Example full ports to learn from: arelkair/wiiparty-recomp (D3D11, gamepads), WitherBlitz/NSMB-Wii-Recompilation.
- Licensing: these are GPL-3.0. A port built on them must be GPL-3.0; keep it separate from the decomp sources (own repo or folder) so the decomp keeps its license.
- WiiWare specifics: the game is a NAND title, not a disc. main.dol (content 1) and the data archive (content 2, already extracted in dev/work/LifeKing/00000002) must be fed in by hand; NAND save and content access must be mapped to local files.

### Port workspace (local only, GPL, never pushed with game files)
- `C:/Jeux/My Life As A King/port/Wiicompiled`: clone of WiiCompiled (depth 1).
- `projects/lifeking/recomp.yml`: manifest for main.dol (entry 0x8000403C, SDA base 0x803A47A0, SDA2 base 0x803A6660, SHA-256 99852f92...b30b), `allow_unsupported_instructions: true` for the first pass.
- `projects/lifeking/MAP.txt`: the 10,307 function starts from `docs/index/functions.tsv` (regenerate when the index changes).
- `Assets/lifeking/main.dol`: local copy of the DOL (gitignored by WiiCompiled).
- Toolchain needed: .NET 8 SDK, CMake >= 3.25, Ninja (pip ninja ok), LLVM-MinGW clang (MSVC is not supported by the runtime's CMake). On 2026-11-26 only ninja was installed.
- Local patches to WiiCompiled (keep them when updating the clone):
  - translator: disassembly budget raised to 65536 instructions / 0x40000 bytes (`FunctionTranslator.cs`, `InferredGuestFunctionAbiProvider.cs`, `Program.cs`), because fn_8004CDB8 is 0x149FC bytes;
  - manifest: `native_registration_root`/`native_index` point to an empty `projects/lifeking/native`, so the stock runtime/src registrations (Mario Kart Wii addresses) are not applied at translation time; output root is `generated/` (the runtime CMake reads it there);
  - `runtime/include/system_bridge.h`: `kDefaultEntryAddress` = 0x8000403C (our `__start`);
  - `runtime/src/music_attenuation.cpp`: WinRT music ducking disabled (`LIFEKING_NO_WINRT`), the Windows SDK 19041 C++/WinRT headers do not build with clang/libc++.
- Build commands: translator `translate-recursive 0x8000403C --output-metadata generated/base_translation_output.json`, `generate-data-init`, `emit-native-index --out projects/lifeking/native-index.json`, `emit-build-shards --base-metadata generated/base_translation_output.json --base-functions-dir generated/functions --native-index projects/lifeking/native-index.json`; then `cmake -S runtime -B build/lifeking-native -G Ninja -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release` and `ninja -C build/lifeking-native WiiCompiled.exe`.
- First boot (2026-11-26): translation 10,367 functions, 0 unsupported instructions; WiiCompiled.exe builds (D3D12 via aurora), loads the DOL sections, starts at `__start`, then stops on the first hardware write: 0xCC003004 (PI interrupt mask) from OS init. Also "Executed 0 main DOL static constructors" (ctor table discovery to check).
- The WiiCompiled runtime is tied to Mario Kart Wii: ~150 hard-coded guest addresses in `runtime/src` (HLE of OS, GX, AX, input, storage). Those hooks must be re-targeted to this game's SDK functions, using the decomp index to find them.

### Port status (2026-11-26, evening)
- WiiCompiled clone, local branch `lifeking` = upstream 27ff3b0 + HarvestMoonAnimalParadeRecomp foreign-game patches (+ its 4 aurora patches) + our edits: translator budget, WinRT off, lazy display-list/AXFX addresses, WiiWare title ID (00010001) in `nand_internal.h`, ES content ioctls (0x09/0x0A/0x0B/0x23/0x24) in `nand_isfs.cpp`, DVD synthetic extents start at 0x440 in `dvd.cpp`, `runtime/src/hle/lifeking_natives.cpp` (WUDGetStatus pump, GXSetDrawDone/GXWaitDrawDone, debug wrappers).
- Tools in `port/lk-tools`: `make_layer.py` (natives + address tables -> foreign_game_*.inc + natives.cpp), `tables/*.txt` (OS, GX, VI, audio, storage, startup, functions), `build.ps1` (full pipeline, `-SkipTranslate`), `run.ps1` (rebuild + run N seconds, filtered log), `u8extract.py`, `refs.py` (data refs of named functions from the decomp asm).
- Game data: `port/lifeking-data/DATA/files` = content 2 extracted with `u8extract.py` (nested .arc stay files), `DATA/sys/{boot,bi2,fst}.bin` minimal; `port/lifeking-data/content/*.app` for ES. `%LOCALAPPDATA%/WiiCompiled/Config.toml` has `[paths] dvd_root` pointing there.
- FIRST IMAGE (2026-11-26 ~21:55): Liara saw the Square Enix logo in the window. TITLE SCREEN (~22:10) after: SelectThread native (it was translated and spun), ESP_InitLib/CloseLib kept translated (the MKW stubs never open /dev/es, CNT needs it), ES ticket-view ioctls 0x12/0x13/0x1B, contents 3-8 merged into DATA/files. Known artifact: HUD pieces drawn at the top-left corner on the title screen. "Press Start" fading is the game, not a bug. Our PrintWindow captures stay black (capture limitation with D3D12, not the game).
- Result: boots through OSInit, WPAD/Bluetooth, loads Squirrel scripts, sounds, menus and models, runs the loading-screen thread and presents ~25 frames/s with no crash. Window content still to confirm (PrintWindow shows black; may be capture of D3D12 flip model).
- Facts learned: the game uses DVD calls (WiiWare DVD-on-NAND), polls `WPADGetStatus` in a busy loop at 0x80041A44, uses GXSetDrawDone/GXWaitDrawDone (MKW does not), tries `<file>.press` before each file, loads `/menu/menuSystem_eu.arc` etc.

### Picture (2026-11-26)
The HM patch widens the picture of foreign games (they are assumed 4:3). My Life as a King draws its own 16:9 (it asks SCGetAspectRatio) and keeps HUD pieces just outside the frame, so widening showed them in the corners. For WFCPGD the frame is now only stretched to the window (`dynamic_aspect.cpp`).

### Sound (2026-11-26)
No sound at first: the AI DMA natives were not placed. Named in symbols.txt by order and size against MKW: AIRegisterDMACallback 0x800FC2F4, AIGetDMABytesLeft 0x800FC3DC, AIGetDMAStartAddr 0x800FC3EC, AIGetDMALength 0x800FC404, AICheckInit 0x800FC414, DSPCheckMailFromDSP 0x80100C64 (this SDK has no AIGetDSPSampleRate).

### Controls (2026-11-26)
The runtime (HM patch) emulates a Wii Remote fed by every connected pad (through the F10 GameCube bindings), the keyboard and the mouse (pointer, left click A, right click B). For WFCPGD the remote carries a **Classic Controller** instead of the Nunchuk (`emulated_remote*.cpp`, `patch_classic.py`): GameCube view of the Xbox/DualSense pad -> Classic by position: A/B/X/Y, D-pad, left stick, right stick (C-stick), analog L/R, Z = ZR, Start = +, Z+Start = Home, Z+Y = -, Z+X = ZL. The core remote buttons are still reported too (A, B, 1, 2, +, -, D-pad).

### Graphics backend (question from Liara)
Rendering goes through aurora on Dawn (WebGPU), which already targets Direct3D 12, Vulkan and Metal: nothing is tied to D3D12. `graphics_api` in Config.toml (`auto`, `vulkan`, `d3d12`) picks it, and the F10 menu can change it for the next launch; `auto` chose D3D12 on Windows here.

## SDK names from Dolphin's signature database
`python tools/match_dsy.py ../dev/ref/dolphin-master/Data/Sys/totaldb.dsy --apply` names SDK functions (address >= 0x800DDCB0, size >= 0x10, plain C names, unique match only) with Dolphin's opcode checksum. First run (2026-11-26): 1,628 matches, 1,102 functions renamed; the DOL still matches. The database entries also carry the library and object (e.g. `os.a OSMessage.o`), useful for future splits.

`python tools/name_by_anchors.py <WiiCompiled>/projects/mkwii/MAP.txt --apply [--lib GX]` then transfers names from Mario Kart Wii's map: between functions both games already name (longest increasing chain of anchors), it aligns the function sizes (Needleman-Wunsch) and copies names of exact-size pairs. Jump-table labels of the map (`_switch`, `_caseD_`) are skipped. Run globally, then per library (GX, OS, DVD, VI, NAND, EXI, IPC, AI...). 2026-11-26: about 530 more SDK functions named this way; the DOL still matches.

## Toolchain
- Linker must stay `GC/1.3.2`: Wii/1.x and GC/3.0 linkers drop the `.ctors`/`.dtors` null terminators and shift every later section.
- SDK (RVL_SDK) libs were built with `0x4199_60831` = `GC/3.0a5.2` (mwcc 4.1 build 60831).
- Runtime.PPCEABI.H also matches with GC/3.0a5.2 (GC/1.3.2, Wii/1.x and GC/2.6 do not).
- Game code compiler: GC/3.0a5.2 with `-O4,s -use_lmw_stmw on -str reuse,readonly` (`cflags_game` / `GameLib` in configure.py). Confirmed by WCThread.cpp. `-O4,s` is what gives the `subic/subfe` bool idiom; `-O4,p` gives `neg/or/srwi`. Wii/1.x compilers align functions to 16 bytes, game functions are packed at 4.
- Ninja: `pip install ninja`, then `python -m ninja`.

## Splits gotchas
- dtk named the last BSS section (0x803A0800, 0x38) `.sbss` a second time. It must be `.sbss2` in splits.txt and symbols.txt.

## Matching tips
- `.dtors` entries for both `__destroy_global_chain` and `__fini_cpp_exceptions` live in `__init_cpp_exceptions.cpp`, not in global_destructor_chain.c (otherwise link order swaps them).
- `__init_cpp_exceptions` reads r2 with an inline `asm { mr temp, r2 }`; a separate GetR2 function adds 0xC bytes.
- In PPCArch.c, HID2 must be written as SPR 920: the compiler's `HID2` name maps to 1011 (that is HID4 on Broadway).
- `-multibyte` usage warning from the template cflags is harmless.

## main.cpp (0x8000C680) analysis
- main + __sinit (0x8000C924), rodata 0x80256900 (0x78: "main", "GX", "settings_master.xml", basic_string error messages).
- Two static `WCThread` objects at 0x802B1200 / 0x802B1214, attached to the current thread ("main") and to the GX thread ("GX") with `WCThread::Attach`.
- Most of main is an inlined MSL/EWL `std::string` (12 bytes, bit 31 of word 0 = long mode, SSO capacity 11, growth `(len+16)&~15`, errors printed with fprintf(stderr)+abort since exceptions are off). Weak string helpers follow the sinit: fn_8000C958 (default ctor), dtor_8000C978, fn_8000C9D4 (replace), fn_8000CC7C (allocate).
- Matching it needs a reconstructed MSL `<string>` that inlines the same way. WIP in `include/msl/string` (based on TheLastStoryDecomp's CC0 reconstruction). `do_replace`, `reserve` and the layout look right.
- Inlining puzzle (not solved): the original inlines the `const char*` ctor and `reserve` into main (reserve's message is in main's string pool), but calls `__zero` (fn_8000C958), the dtor (dtor_8000C978) and `allocator::allocate` (fn_8000CC7C, its message is a weak `@STRING@` object in .data, so it is an in-class inline function). With -O4,s nothing big inlines; with -O4,p in-class members inline (too much) and out-of-class template members do not. main.cpp is configured NonMatching with -O4,p until this is solved.
- Rules measured with GC/3.0a5.2 (standalone probes): with -O4,s only small straight-line inline functions get inlined (loops and branchy functions are called); with -O4,p everything in-class inlines. A string literal in an in-class (implicitly inline) member goes to a weak `@STRING@<func>` object in .data; in an out-of-class member it goes to the file's `@stringBase0` pool. Out-of-class template members are not inlined under either setting. `-str pool` and the `-inline` variants change nothing here.
- The class at 0x800CFE4C (vtable 0x80281B38) inlines `std::vector` growth ("vector length error"), same blocker.

## Game classes found
- `WCThread` (src/game/WCThread.cpp, 0x800CFC78): wraps an OSThread (fields: own thread, arg, stack, current thread, name).
- Game allocators near 0x800920C4: `operator new(size, heap)` = 0x800922B4, `operator new[](size, align, heap)` = 0x8009210C, `operator delete` = 0x8009230C, `operator delete[]` = 0x8009227C. Heap 1 vs other selects one of two heaps at 0x802D877C / 0x802D872C. The names are guesses that fit the call sites.

## Layout
- Game code: 0x8000C680 to 0x800DDCB0. SDK starts at PPCArch (0x800DDCB0).
- In game code, `auto_fn_*` units are `__sinit` functions marking the end of a translation unit.
- Source names from asserts: wiiGameWorld.cpp, wiiDataManager.cpp, wiiMenuManager.cpp, wiiGameObjects.cpp, wiiShadowMap.cpp, wiiSoundManager.cpp, WCLytUtil.cpp, WCMenuActor.cpp, WCLayout.cpp, WCSubDataManager.cpp, WCHomeButtonMenu.cpp, tempDEMOInit.c.

## Progress log
- 2026-11-26: skeleton set up, build matches.
- 2026-11-26: matched Runtime.PPCEABI.H/global_destructor_chain.c, Runtime.PPCEABI.H/__init_cpp_exceptions.cpp, revolution/os/PPCArch.c.
- 2026-11-26: matched game/WCThread.cpp (first game code). main.cpp deferred until MSL std::string is reconstructed.
