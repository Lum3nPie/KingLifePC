# Notes for Claude

Matching decomp of My Life as a King (WiiWare, version `WFCPGD`), built on dtk-template.

Before reading source or asm files, read these first:
- `docs/NOTES.md`: hand-written facts, toolchain choices and gotchas.
- `docs/index/WFCPGD.md`: generated summary (sections, regions, units, SDK libs, source names).
- `docs/index/functions.tsv` and `docs/index/units.tsv`: grep them to find a function or unit by name or address instead of scanning `config/` or `build/`.

After changing symbols, splits or `configure.py` objects: run `python -m ninja`, then `python tools/index_project.py`, and update `docs/NOTES.md` if you learned something new.
