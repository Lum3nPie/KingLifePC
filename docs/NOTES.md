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
- Game code compiler: not identified yet.
- Ninja: `pip install ninja`, then `python -m ninja`.

## Splits gotchas
- dtk named the last BSS section (0x803A0800, 0x38) `.sbss` a second time. It must be `.sbss2` in splits.txt and symbols.txt.

## Layout
- Game code: 0x8000C680 to 0x800DDCB0. SDK starts at PPCArch (0x800DDCB0).
- In game code, `auto_fn_*` units are `__sinit` functions marking the end of a translation unit.
- Source names from asserts: wiiGameWorld.cpp, wiiDataManager.cpp, wiiMenuManager.cpp, wiiGameObjects.cpp, wiiShadowMap.cpp, wiiSoundManager.cpp, WCLytUtil.cpp, WCMenuActor.cpp, WCLayout.cpp, WCSubDataManager.cpp, WCHomeButtonMenu.cpp, tempDEMOInit.c.

## Progress log
- 2026-11-26: skeleton set up, build matches. Next: global_destructor_chain.c, then PPCArch.c.
