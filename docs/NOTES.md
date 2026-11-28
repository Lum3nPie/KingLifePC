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
- DLC (00010005-77464350, lowercase "wFCP", v2) is data only, no code; see "Add-on content (DLC)" below.
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
The HM patch widens the picture of foreign games (they are assumed 4:3). My Life as a King draws its own 16:9 (it asks SCGetAspectRatio) and keeps HUD pieces just outside the frame, so widening showed them in the corners. For WFCPGD the frame is not widened and stays 16:9 whatever the window or screen shape, with black bars (aurora's 16:9 viewport policy, `dynamic_aspect.cpp`); stretching it to the window distorted it.

### Sound (2026-11-26)
No sound at first: the AI DMA natives were not placed. Named in symbols.txt by order and size against MKW: AIRegisterDMACallback 0x800FC2F4, AIGetDMABytesLeft 0x800FC3DC, AIGetDMAStartAddr 0x800FC3EC, AIGetDMALength 0x800FC404, AICheckInit 0x800FC414, DSPCheckMailFromDSP 0x80100C64 (this SDK has no AIGetDSPSampleRate).

### Controls (2026-11-26)
The runtime (HM patch) emulates a Wii Remote fed by every connected pad (through the F10 GameCube bindings), the keyboard and the mouse (pointer, left click A, right click B). For WFCPGD the remote carries a **Classic Controller** instead of the Nunchuk (`emulated_remote*.cpp`, `patch_classic.py`): GameCube view of the Xbox/DualSense pad -> Classic by position: A/B/X/Y, D-pad, left stick, right stick (C-stick), analog L/R, Z = ZR, Start = +, Z+Start = Home, Z+Y = -, Z+X = ZL. The core remote buttons are still reported too (A, B, 1, 2, +, -, D-pad).

### Performance (2026-11-27)
Symptom: frame drops when Chime appears and while a building goes up; the game is 30 FPS with logic per frame, so slow frames slow the game and (through the audio service points) the music.
- Measuring: launcher "(mesures)" sets MKW_PERF_STATS=1 and LIFEKING_PROFILE=1. `[perf]` lines give busy ms/frame, then wall time, FPS and the waits per frame (vi pacing, GX worker, audio mix). The profiler samples the main thread, the GX worker and the AX mix worker every ms, files each sample under the frame it belongs to (heavy = busy >= 20 ms, or normal), tags waits (`wait:*`), names DLLs and finds the caller in the exe of DLL time (`^` lines). `port/tools/symbolize_profile.py` reads it. `busy` counts untagged system waits as busy, so read it with the profile.
- The `[vi] interpolation to N FPS ... game at X FPS` line is in every log, measures or not: the guest frame rate to compare runs.
- Finding (950 heavy frames, Liara's settings: Vulkan, resolution x5, frame interpolation 120 FPS): heavy scenes ran at 13-16 guest FPS. Game code was ~10% of the main thread; it waited 43% on the GX worker and 32% in system waits. The GX worker spent 40% in memmove (ucrtbase), plus aurora's finalize_frame_interpolation.
- Fix: frame interpolation Off (F10 menu, `video.frame_interpolation_fps = 0`): "much smoother", music no longer slows (Liara, 2026-11-27). It records every frame and replays it for the inserted ones, all on the GX worker, which the game thread then waits for. Off is the runtime default; Liara had chosen 120.
- 60 Hz experiment (`LIFEKING_FPS=60`, lifeking_natives.cpp): the present waits for 2 VI retraces (0x80091FC8, counter 0x8039DC10); the engine's frame rate lives in the system object 0x802B1B78 (+0x10 FPS, +0x14 seconds per frame, set by 0x80033664: 30 NTSC/EURGB60, 25 PAL 50 Hz; scripts read it via CGetFPS/CGetSPF/CIsRefreshRate60). The mode waits 1 retrace and sets 60: solid 60 FPS at ~4 ms busy/frame, but everything but the sound runs twice as fast, so movement, animation and effects step per frame, not per second.
- 60 Hz work (option A, chosen by Liara 2026-11-27; everything behind `LIFEKING_FPS=60` and the launcher "(60 FPS, mesures)", 30 Hz unchanged). What was learned, in order:
  - The engine FPS (system object 0x802B1B78 +0x10) is set to 60 by the 0x80033664 wrapper and stays 60 (traced); the frame-wait wrapper also re-sets it if anything ever writes another value.
  - The game reads its scripts from content 2 (00000002.app, uncompressed U8) through ES/CNT, not from the DVD files: patching `DATA/files/script` did nothing. `make_fps60_scripts.py` now patches a copy of content 2 in place with same-length replacements, read through `LIFEKING_OVERLAY_ROOT/content` (nand_isfs.cpp OpenTitleContent).
  - Model animations are time-based: scripts call CUpdateModels(us since last update) -> 0x80032E98 -> rate = elapsed_ns / 33.32 ms at 0x800AA4F8 (sites 0x800AAC9C/0x800AACD0/0x800AAD0C), through AnmObjChrBlend::SetUpdateRate 0x801B4224. So in gameplay they need no change. During camera events and demo scenes the scripts pass a fixed 100000/3 us (one 30 Hz frame): the script rule replaces it with 1e6/CGetFPS().
  - nw4r::g3d::FrameCtrl::smBaseUpdateRate is the float at 0x8039D818 (FrameCtrl::UpdateFrame 0x801B16C8 and six siblings: frame += rate * it). The mode sets it per update: 0.5 for objects whose last rate was exactly 1.0 (constant-rate animations), 1.0 for the time-based ones (sites that passed several rates).
  - Scripts are plain Squirrel source. Output in `port/lifeking-mod60/content/` (never in git). Script speed and pad-camera rescaling were dropped: they never reached the game (DVD copy), and walking and the gameplay camera are right without them.
  - Particle effects: the effect manager calc 0x800BBBA0 (system +0x6AA8) steps every nw4r::ef effect by one frame per call; the mode skips it on odd frames (drawn every frame).
  - Menus: script MenuAnime -> native anime object (speed +0xC, nw4r::lyt animation at +0x8, frame at its +0x10), stepped by 0x800CB040 once per frame; the mode halves the speed during that call.
  - Name keyboards: the input cursor blinks every `EFFECT_TIME` frames (6, script MenuKeyboard and the password keyboard); the data patch sets 12.
  - Simulation timers counted in frames (data patch): ArchParty.FRAMES_PER_STEP 60 -> 120 (adventurers came home early), city villager pop check `time % 60` -> 120, party creation check `gameTime % 90` -> 180. The displayed clock already scales (ONE_HOUR_FRAME = 21*CGetFPS). Left as is: villager AI random checks (`_algoCheckTimer % 60/150/200`, `_algoTimer % 10`), which only fire twice as often.
  - Status 2026-11-27: Liara validated gameplay, cutscenes, construction and menus at 60 FPS. Still to check: the in-game clock speed.
- Versioning (Liara, 2026-11-27): the app is "KingLife <version>" (window title, startup screen, F10 bar), version written once in `runtime/include/lifeking_version.h` (LIFEKING_VERSION); bump it and tag `v<version>` together. v0.3 = 60 FPS fixes (keyboard cursor, adventures) + controller by position.
- v0.2 (2026-11-27): 60 FPS is the default (`LIFEKING_FPS=30` for the original); without `LIFEKING_OVERLAY_ROOT` the runtime takes `port/lifeking-mod60` next to `lifeking-data`, and build.ps1 regenerates it. The app is KingLife: `KingLife.exe` (CMake OUTPUT_NAME of the WiiCompiled target, ninja target still `WiiCompiled`), window title from base_product.cpp, icon `runtime/resources/KingLife.ico` drawn by `port/tools/make_icon.py`. Settings, saves and logs stay in `%LOCALAPPDATA%\WiiCompiled`. Local launchers: "Lancer KingLife.cmd", "(30 FPS)", "(mesures)".
  - Traces (LIFEKING_ANIM_TRACE=1, set by the launcher): per-kind animation stats, rate setters by call site, model clock (CUpdateModels us) and halved/full steps every 300 frames.
- Note: from Claude's shell `%LOCALAPPDATA%\WiiCompiled\Config.toml` reads as a stale copy; trust the `[runtime-config] ... loaded` line of console.log for the settings in use.

### Graphics backend (question from Liara)
Rendering goes through aurora on Dawn (WebGPU), which already targets Direct3D 12, Vulkan and Metal: nothing is tied to D3D12. `graphics_api` in Config.toml (`auto`, `vulkan`, `d3d12`) picks it, and the F10 menu can change it for the next launch; `auto` chose D3D12 on Windows here.

### Field of view (27/11, validated by Liara at 150%)
F10 > Graphics "Field of view", 75-150% in steps of 5, saved as `[video] field_of_view`. What it does:
- Picture: `ApplyFieldOfView` (gx_transform.cpp) divides the x and y scales and skews of a world perspective (0 < m[0] <= 6) in the copy that GX__SetProjection/GX__SetProjectionv send to the GPU. What GXGetProjectionv returns stays the game's own, so nothing is scaled twice.
- C_MTXPerspective (0x800ECE28) is not the world camera's path. The world camera is set by scripts through GameCamera::SetFrustum 0x800406F4 (t, b, l, r, n, f; it also keeps a copy at camera +0x80..+0x94), which feeds nw4r::g3d::Camera (CameraData +0xBC..+0xC8, flag 0x10, C_MTXFrustum 0x800ECD8C).
- Culling, nw4r: wrapper `LifeKing_CullFrustum` on 0x801DC18C nw4r::math::FRUSTUM::Set (f1-f6 = t, b, l, r, n, f). It scales t, b, l, r for world cameras. ScnRoot::UpdateFrustum 0x801C69FC rebuilds it every call, for both camera kinds (the fovy variant 0x801DC0D8 ends there too).
- Culling, game: wrapper `LifeKing_CullObjects` on 0x800369D8, the game's own object wedge (left and right planes 0x80040840/0x800408EC from camera +0x88/+0x8C/+0x90, camera = r3 + [r3+0x5004]*0x22C + 0xA84). It scales the camera copy +0x80..+0x8C for the length of the call and restores it after. This fixed buildings vanishing at the sides in cutscenes.
- Near plane: when widening, world cameras with n < 1 get n/4 in the GPU copy (m[10] = -n/(f-n), m[11] = -f*n/(f-n)). This fixed the ground cut off at the bottom of the low-angle cutscene. The square shadow camera (n 20, f 80) keeps its own.

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

### Controller mapping (checked 27/11, validated by Liara)
The emulated Wii Remote never connects (console.log: "the game refused L2CAP PSM 0x11"): the game reads the pad through its own PADRead (0x800FB678 -> `PAD__Read_HLE`, `runtime/src/hle/input/pad.cpp`). The game uses GC A = confirm, B = cancel, X = top view, Y = Chime. `ApplyLifeKingLayout` (WFCPGD only) reads the face buttons by SDL position: right -> A, bottom -> B, left -> Y, top -> X. Aurora's own tables differ by brand (Xbox: EAST -> X, WEST -> B), so they are bypassed for these four buttons. Both C-stick axes are inverted. The `emulated_remote*.cpp` Classic Controller code has no effect on this game.

### Add-on content (DLC) (27/11)
- The DLC is title 00010005-77464350 (lowercase "wFCP"), TMD v2, 16 contents: index 0 = banner, 1 to 15 = `script/packN` (package.nut registers `::pack[N]` and sets the game flags; 11/12/14/15 add king and minister costumes). Contents 8, 9 and 10 also carry a newer copy of the game's program scripts (`script/ProgramArchlordComp_en_us.nut.press`, `ProgramSystemComp.nut.press`, `loadComp.nut.press`) and a `gameStart.nut` that loads them with `CIncludeOptionalFile(name, ::dataTitleCode, ::gameStartVersion)`: with the DLC, the game runs those scripts, not content 2's.
- `.press` = Nintendo LZ11 (byte 0x11 + 24-bit size), `port/tools/lz11.py`.
- The game probes DLC indexes 1 to 29 at boot through CNT (0x8004340C -> 0x801FE9C8: GetNumTicketViews 0x12, GetTicketViews 0x13, then ES OpenContent 0x24 with title id 0x00010005:<low of its own title>). -0x1391/-0x1392 mean "not there". Before the DLC support the runtime ignored the title id of 0x24 and handed back the base game's contents 2 to 9 for those probes.
- Runtime (nand_isfs.cpp): 0x24 with title hi 0x00010005 reads `<dvd_root>/../dlc/<index>.app`, or `lifeking-mod60/dlc/` (or `LIFEKING_OVERLAY_ROOT/dlc`) when present; 0x13 for the DLC builds the view from `dlc/0001000577464350.tik` (else a view owning everything). A missing pack returns -106 quietly. 0x12 still answers 1 view for every title.
- `port/tools/install_dlc.py [<folder>]` checks each decrypted content against the TMD SHA-1, copies them to `lifeking-data/dlc/` and reruns `make_fps60_scripts.py`, which now also patches the program scripts of the DLC packs (decompress, same rules, recompress, rebuild the U8 with `u8pack.py`) into `lifeking-mod60/dlc/`. `--remove` goes back to no DLC.

### UI scale per category (27/11, to test)
Liara asked for one size per kind of on-screen element, not one global setting, with corner elements kept in their corner. F10 > Graphics > "UI scale": one slider per category, 50-100% in steps of 5, live, saved as `[ui_scale] <key>` (clock, notifications, dialogue, system_messages, keyboard, menus, help_bar, titles, gauges).
- The whole 2D interface is nw4r::lyt (`menu/menu_eu.arc`: common, menu_build, menu_report, menu_room, map, e-commerce; `menuTitle_eu.arc`). Scripts find panes by name (`MenuPane(menu, "com_clk_nul")`, `rootPaneName = ...`) inside one tree per layout.
- Hook: wrapper `LifeKing_PaneCalculateMtx` (runtime/src/hle/lifeking_ui_scale.cpp) on nw4r::lyt::Pane::CalculateMtx 0x801CF6A8 (found by size order against MKW's map: Draw 0x801CF9A0 follows). Pane: +0x0C parent, +0x2C translate, +0x38 rotate, +0x44 scale, +0x54 mtx, +0x84 global mtx, +0xB8 alpha, +0xBB flags, +0xBC name. DrawInfo: +0x04 view mtx, +0x34 view rect, +0x44 location-adjust scale, +0x50 flags. The UI ortho is x -320..320 (4:3) or -422..422 (16:9), y -224..224 (0x800C2C94).
- For the root pane of an element (table in the file), translate moves towards the anchor by the scale and the pane's scale is multiplied, for the length of the call only (put back after: scripts never see it). The anchor is a screen corner/edge from the view rect, brought into the parent's space through the parent's global matrix; or the pane's own position for things that follow a character (speech bubble com_tlk, gauges); or "auto" (the third of the screen it is in) for menus. Panes under a scaled one are never scaled again.
- Left out on purpose: the full-screen lists of the report/room/map screens (rom_*, bom_*, ntc_lst_*, hio_*...), drawn on desk backgrounds that would not scale with them.
- The first scale of each pane logs `ui scale <pane> ...` (rect, parent scale, anchor) in console.log.
- Round 2 (27/11, after Liara's test, rest validated): the rect logged is +-320 but the UI ortho is +-422 in 16:9 (`GX_HLE_UiOrthoHalfWidth`, noted from the last 448-high ortho in gx_transform.cpp); anchors kept on the view rect (validated). Tutorial hand com_fin_L/R follows the clock or the info window depending on where it points (top third, left/right). Chancellor window rom_tlk_nul now centred. New category room_banner (bom_sig_nul / rom_sig_nul, the castle's "The Settlement of..."). The help band com_hlp_bas is widened to the whole 16:9 screen (it was 640 wide, a game limit).
- Icons over characters (!, smiley...) are 3D models (script ActorIcon) scaled by WorldEngine::setObjectScale 0x8003A438 (r4 id, f1-f3). make_fps60_scripts.py makes ActorIcon.setScale pass -x as a marker; wrapper `LifeKing_SetObjectScale` restores it and applies "Over characters" (key gauges); the frame wait re-applies a change live.
- Room characters (Chime, chancellor, signboard "Frog Board", shops) are MenuModel 3D models drawn in the model pane's draw 0x800C1FC0 with their own camera: wrapper `LifeKing_DrawMenuModel` keeps the game's FOV for that draw (`GX_HLE_SuppressFieldOfView`, also seen by the cull wrappers).
- Open: the camera going under the ground in the cutscene after day 2 ends (to isolate: FOV 100%, 30 FPS).
- Rounds 3-4 (28/11): 3D models in menus (MenuModel: model pane vtable 0x8028149C, model object at +0xD8, drawn by 0x800C1FC0) are placed by the scripts in screen units, outside the pane tree: inside a scaled element the model's projection is remapped while it is drawn (`GX_HLE_SetScreenRemap`: perspective screen offset -m[2]/-m[6] moved towards the element's anchor, m[0]/m[5] scaled), so the building menu's house follows and scales with its frame. Talk windows beside a speaker (com_men_nul_2: Chime's report, chancellor's costume talk, signboard; ntc_men_nul; rom_tlk_nul) are anchored on the tip of their tail (rule offset from the pane origin). Icons over characters keep their bottom: setObjectPosition 0x80035A48 is wrapped and y lowered by 0.5 x scale x (1 - setting) (icon.brres bubble is -0.5..0.5). The tutorial hand stays at 100% when the quest map (map_bas) or the castle room (rom_bg_nul) is drawn (wrapper on nw4r::lyt::Pane::Draw 0x801CF9A0).
- After v0.5 (28/11): the talk window under a centred speaker (com_men_nul_1: Chime at the Frog Board, MenuReport `_windowTalkD`) is anchored on the tip of its tail too (com_men_hge_TR1, tip at -21,-2.5 from the pane origin), instead of its third of the screen.
- After v0.5 (28/11), Frog Board: in the rooms (MenuRoom.setActorPos LEFT: Frog Board, shops, guild...) the scripts leave com_men_nul_2 at its layout place (-220, -70), so in 16:9 its tail is on the speaker's arm even at 100%. Liara wants the tail on Chime's mouth without hiding her face: the rule moves the pane to (-150, 15) at every scale, 100% included (its tail tip is about 0,+18 from the pane, measured on a 100% screenshot), then anchors on the tail when scaled. com_men_nul_2 goes through the wrapper even with nothing scaled for that.
- Set aside by Liara (28/11): the camera going under the ground in the cutscene after day 2 with FOV above 100%.

### Max detail / LOD (27/11, validated by Liara, in v0.5)
F10 > Graphics > "Max detail (LOD)", on by default, saved as `[video] max_detail`. The game picks a model's level of detail from 4 int distances at 0x8039D154..0x8039D160 (30/60/80/100), set by worldEngine.setLODDistances 0x80034BFC (scripts: LOD_NORMAL while walking, LOD_ALWAYSLOW 0 in the top view and building, LOD_ALWAYSHIGH 1000 never used). Wrapper `LifeKing_SetLODDistances` (lifeking_natives.cpp) writes 1000 when the box is ticked; the frame wait 0x80091FC8 re-applies a change live.

### Title screen and boot (28/11, validated by Liara)
- Strap screen skipped: the game's logo thread steps through a state machine at 0x800D125C (r3 the state, step at +0x0C: 0x0A-0x1F the Wii strap, 0x28-0x29 fade/mask, 0x32-0x3D the Square Enix logo, 0x3E-0x3F wait for loading). Wrapper `LifeKing_LogoThreadStep` (runtime/src/hle/lifeking_title.cpp) turns step 0x0A into 0x29.
- No "Checking Wii system memory" window at boot, no "Purchase Add-on content" in the title menu nor in Chime's menu at the castle (the shop needs the Wii Shop servers; the DLC comes from the `dlc` folder): same-length blanking rules in `make_fps60_scripts.py` (MenuSave STEP_CHECKFILEBOOT addText + open, MenuTitle `TXT_MENU_TITLE_CONTENT_STORE`, MenuRoom `TXT_MENU_CAS_menuH`), applied to content 2 and to the program scripts of DLC packs 8-10. Those are the only shop entries in the scripts.
- The UI layout is 4:3 (x +-320) stretched over the 16:9 picture, so all 2D is 4/3 too wide. `TitlePaneFixup` (first thing of `LifeKing_PaneCalculateMtx`, lifeking_ui_scale.cpp): the logo (pane `tittle_img`, menu_title.brlyt) is brought back to 0.75 in x, the copyright (`ar_tex`) is 50% anchored bottom-centre, the title menu (`ttl_men_nul`, window `ttl_men_win`) is centred halfway between the bottom of the logo and the top of the copyright and shrinks around that point with the "Menus" UI scale.

### Character shadows (28/11, validated by Liara)
- The game: one shadow map per world (System 0x802B1B78 + 0x1730, map at +0x5190, made by 0x800B1D88): +0x04/+0x06 size (512 x 512), +0x08 the A8 texture, +0x0C a falloff texture made on the CPU, +0x58/+0x5C half extents of its orthographic light camera (16, near 20, far 80), +0x84 shadow colour. 0x800B2070 sets the light camera up, 0x800B235C draws the casters into the top-left 512 x 512 of the EFB, 0x800B256C copies that corner to A8 (GX_CTF_A8 0x27) with clear, and the ground projects it (0x800B2228 / 0x800B1720).
- `runtime/src/hle/lifeking_shadows.cpp`: wrapper `LifeKing_DrawShadowMap` draws the casters into an offscreen target of their own (aurora `GXCreateFrameBufferLogical`, new command 0x0060), copies it to the game's texture right away (blurred through `GXSetCopyOverride`, command 0x0061, gaussian blur in tex_copy_conv) and the game's own copy is skipped (`LifeKing_HLE_SkipShadowCopy` in gx_copy.cpp).
- `LifeKing_SetupShadowCamera` (0x800B2070) widens the map: half extents x field of view (above 100%) x the "Shadow distance" reach (Near 1, Medium 3, Far 6), and moves its centre forward along the camera's view so the shadows reach far ahead; the falloff texture is refilled for each level so far shadows stay dark.
- F10 > Graphics: "Shadow resolution" (Same as picture / 2048 / 4096 default / 8192, `[video] shadow_resolution`), "Shadow distance" (Near / Medium default / Far, `[video] shadow_distance`), "Soft shadows" with - and + buttons, 0 (Off, default) to 10% by 0.25 (`[video] shadow_softness`, float; 100% would be a sigma of 3 texels of the 512 map). All live.
- Experimental, off: two cascades (a sharp near map plus a 6x far map with the near square cut out, a second TEV series added by `LifeKing_AddShadowToMaterial` on 0x800B1720, near map made beside the game's by `LifeKing_CreateShadowMap`). Too slow (3 s frames when on); only with `LIFEKING_SHADOW_CASCADES=1`.
- Aurora is checked out with CRLF in some files: edit them keeping CRLF; `port/patches/aurora-lifeking.patch` is made with the line ends of the upstream files (LF).
- Patches regenerated 28/11 from the working trees: `wiicompiled-lifeking.patch` = 27ff3b0 to the current `runtime/` and `translator/` (new files included), `aurora-lifeking.patch` = aurora-main 33067e3 to its current tree. `projects/lifeking/native/natives.cpp` and `native-index.json` are not in them: `make_layer.py` and `build.ps1` write them (wrappers come from the `FOREIGN_GAME_WRAPPER` lines of the runtime).
