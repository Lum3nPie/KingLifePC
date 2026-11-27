#!/usr/bin/env python3
"""Draw KingLife's icon: a blue crystal floating in a soft glow, with sparkling particles around it.

Original drawing (not taken from the game). Writes a multi-size .ico (and a 512 px PNG preview).
Usage: python make_icon.py <out.ico> [preview.png]
"""
import math
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

S = 1024  # drawn at 1024 px, then scaled down


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def crystal_layer():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, top, mid, bottom = S * 0.5, S * 0.10, S * 0.40, S * 0.90
    half = S * 0.20
    belt = S * 0.47  # lower edge of the crown band
    # Points of an elongated gem seen slightly from the left: crown band, then a long pavilion.
    tip = (cx, top)
    left, right = (cx - half, mid), (cx + half, mid)
    cl, cr = (cx - half * 0.42, mid - S * 0.03), (cx + half * 0.30, mid - S * 0.025)
    bl, br = (cx - half * 0.92, belt), (cx + half * 0.92, belt)
    bc = (cx - half * 0.05, belt + S * 0.012)
    low = (cx - S * 0.01, bottom)
    facets = [
        # crown (above the girdle)
        ([tip, left, cl], (120, 205, 255)),
        ([tip, cl, cr], (185, 235, 255)),
        ([tip, cr, right], (70, 150, 240)),
        # girdle band
        ([left, cl, bc, bl], (60, 140, 235)),
        ([cl, cr, br, bc], (100, 185, 255)),
        ([cr, right, br], (35, 95, 205)),
        # pavilion (long lower point)
        ([bl, bc, low], (40, 110, 225)),
        ([bc, br, low], (20, 65, 170)),
    ]
    for poly, color in facets:
        d.polygon(poly, fill=color + (255,))
    # Thin light edges between facets.
    edge = (225, 245, 255, 200)
    for a, b in [(tip, cl), (tip, cr), (left, cl), (cl, cr), (cr, right), (cl, bc), (cr, br),
                 (bl, bc), (bc, br), (bc, low), (left, bl), (right, br)]:
        d.line([a, b], fill=edge, width=int(S * 0.006))
    # A soft white gleam on the brightest facet.
    gleam = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(gleam)
    g.polygon([(cx - S * 0.03, top + S * 0.10), (cx + S * 0.02, top + S * 0.10),
               (cx - S * 0.055, mid - S * 0.02), (cx - S * 0.095, mid - S * 0.02)], fill=(255, 255, 255, 170))
    gleam = gleam.filter(ImageFilter.GaussianBlur(S * 0.006))
    img = Image.alpha_composite(img, gleam)
    return img


def glow_layer(shape):
    alpha = shape.getchannel("A")
    glow = Image.new("RGBA", (S, S), (80, 170, 255, 0))
    glow.putalpha(alpha.filter(ImageFilter.GaussianBlur(S * 0.06)).point(lambda v: int(v * 0.9)))
    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    r = S * 0.36
    hd.ellipse([S / 2 - r, S * 0.5 - r, S / 2 + r, S * 0.5 + r], fill=(60, 140, 255, 90))
    halo = halo.filter(ImageFilter.GaussianBlur(S * 0.08))
    return Image.alpha_composite(halo, glow)


def sparkle(d, x, y, size, alpha):
    c = (230, 248, 255, alpha)
    w = max(2, int(size * 0.16))
    d.polygon([(x, y - size), (x + w, y), (x, y + size), (x - w, y)], fill=c)
    d.polygon([(x - size * 0.7, y), (x, y - w), (x + size * 0.7, y), (x, y + w)], fill=c)


def particles_layer():
    rnd = random.Random(7)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Small motes drifting up around the crystal.
    for _ in range(55):
        ang = rnd.uniform(0, 2 * math.pi)
        rad = rnd.uniform(S * 0.22, S * 0.44)
        x = S / 2 + math.cos(ang) * rad * 0.85
        y = S * 0.52 + math.sin(ang) * rad
        r = rnd.uniform(S * 0.004, S * 0.012)
        a = rnd.randint(110, 230)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(150, 215, 255, a))
    blurred = img.filter(ImageFilter.GaussianBlur(S * 0.004))
    img = Image.alpha_composite(blurred, img)
    d = ImageDraw.Draw(img)
    # A few four-point sparkles.
    for x, y, size, a in [(0.25, 0.25, 0.07, 240), (0.77, 0.36, 0.05, 230), (0.70, 0.78, 0.06, 220),
                          (0.30, 0.70, 0.04, 200), (0.62, 0.14, 0.035, 210), (0.18, 0.50, 0.03, 190)]:
        sparkle(d, x * S, y * S, size * S, a)
    return img


def main():
    out = sys.argv[1]
    crystal = crystal_layer()
    art = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    art = Image.alpha_composite(art, glow_layer(crystal))
    art = Image.alpha_composite(art, particles_layer())
    art = Image.alpha_composite(art, crystal)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    big = art.resize((256, 256), Image.LANCZOS)
    big.save(out, format="ICO", sizes=sizes)
    if len(sys.argv) > 2:
        art.resize((512, 512), Image.LANCZOS).save(sys.argv[2])
    print("wrote", out)


if __name__ == "__main__":
    main()
