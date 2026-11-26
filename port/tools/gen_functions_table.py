"""Write tables/functions.txt: the functions WiiCompiled's natives call, matched by name.
The list of needed functions (MKW address + SDK name) comes from HarvestMoonAnimalParadeRecomp's
address tables (rows whose evidence is "name"); read as data only."""
import glob, re
syms = {}
for l in open('../../config/WFCPGD/symbols.txt', encoding='utf-8'):
    m = re.match(r'^(\S+) = \.(text|init):0x([0-9A-F]+);', l)
    if m:
        syms.setdefault(m.group(1), []).append(int(m.group(3), 16))
out, miss = [], []
for f in sorted(glob.glob('../ref-hmap/wiicompiled/RBIEE9-*-addresses.txt')):
    for line in open(f, encoding='utf-8'):
        if not line.strip() or line.startswith('#'):
            continue
        pal, here, what, ev = re.split(r'\s{2,}', line.strip(), maxsplit=3)
        if ev != 'name':
            continue
        name = what.split(' ')[0]
        if len(syms.get(name, [])) == 1:
            out.append(f"{pal}  0x{syms[name][0]:08X}  {what}")
        else:
            miss.append((pal, name))
open('tables/functions.txt', 'w').write("# Functions the natives call, matched by name in our symbols\n" + "\n".join(out) + "\n")
print(len(out), 'found; missing:', miss)
