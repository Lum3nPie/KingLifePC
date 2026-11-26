# Working notes: My Life as a King (WFCPGD)

Hand-written notes. Keep them short and up to date. The generated index is in `docs/index/`.

## Game and files
- WiiWare, PAL, title 00010001-57464350 ("WFCP"), maker GD (Square Enix), title version 1.
- `orig/WFCPGD/sys/main.dol` = NAND content `00000001.app` (SHA-1 ab2944ddbae018d562839a4a48b222ada1d3c915). Boot content 9 is the NAND loader. No REL/RSO.
- DLC (00010005-57464350, v2) is data only, no code.
- Original files are gitignored (`orig/*/*`). Never commit them.

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
- Matching it needs a reconstructed MSL `<string>` that inlines the same way.

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
