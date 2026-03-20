"""
logo.py — Chris's Cannabis Counter
Programmatically generates a cannabis leaf graphic using Pillow.
No external image files required.
"""

import math
from PIL import Image, ImageDraw


def _leaflet_points(cx, cy, angle_rad, length, width, n_teeth=7):
    """
    Generate polygon points for a single serrated leaflet.
    Uses a sinusoidal envelope for the leaf width and toothed serrations along both edges.
    """
    perp = angle_rad + math.pi / 2
    points = []
    steps = n_teeth * 4  # more steps = smoother serrations

    # Left edge: base → tip
    for i in range(steps + 1):
        t = i / steps
        # Bell-shaped width envelope: wide in middle, tapers to tip
        envelope = math.sin(math.pi * (t * 0.88 + 0.06)) * (1.0 - t * 0.25)
        w = width * envelope
        # Serration bumps (teeth): more prominent near middle, fade at tip
        serr = width * 0.30 * abs(math.sin(math.pi * t * n_teeth)) * (1.0 - t)
        ax = cx + math.cos(angle_rad) * length * t
        ay = cy + math.sin(angle_rad) * length * t
        points.append((ax + math.cos(perp) * (w + serr),
                        ay + math.sin(perp) * (w + serr)))

    # Pointy tip
    points.append((cx + math.cos(angle_rad) * length,
                   cy + math.sin(angle_rad) * length))

    # Right edge: tip → base
    for i in range(steps, -1, -1):
        t = i / steps
        envelope = math.sin(math.pi * (t * 0.88 + 0.06)) * (1.0 - t * 0.25)
        w = width * envelope
        serr = width * 0.30 * abs(math.sin(math.pi * t * n_teeth)) * (1.0 - t)
        ax = cx + math.cos(angle_rad) * length * t
        ay = cy + math.sin(angle_rad) * length * t
        points.append((ax - math.cos(perp) * (w + serr),
                        ay - math.sin(perp) * (w + serr)))

    return points


def make_cannabis_logo(size: int = 80) -> Image.Image:
    """
    Return a PIL RGBA Image of a stylised cannabis leaf at `size`×`size` pixels.
    Renders at 4× resolution internally and downsamples for smooth anti-aliasing.
    """
    scale = 4
    s = size * scale

    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── Background circle ────────────────────────────────────────────────
    pad = int(s * 0.04)
    draw.ellipse(
        [pad, pad, s - pad, s - pad],
        fill=(18, 80, 18, 255),
        outline=(8, 50, 8, 255),
        width=max(2, s // 60),
    )

    # ── Leaflet layout ───────────────────────────────────────────────────
    # cx/cy is the base of the stem (lower-centre of circle)
    cx = s // 2
    cy = int(s * 0.60)

    max_len   = s * 0.36   # longest (centre) leaflet
    max_width = s * 0.065  # widest leaflet half-width

    # (angle from straight-up in degrees, relative length)
    leaflets = [
        (  0, 1.00),   # centre — tallest
        (-26, 0.86),   # inner pair
        ( 26, 0.86),
        (-53, 0.66),   # middle pair
        ( 53, 0.66),
        (-76, 0.46),   # outer pair — shortest
        ( 76, 0.46),
    ]

    leaf_fill    = (52, 168, 52, 255)   # bright mid-green
    leaf_outline = (18, 100, 18, 255)   # dark green outline
    vein_color   = (15,  80, 15, 255)   # midrib vein

    for angle_deg, rel_len in leaflets:
        angle_rad = math.radians(angle_deg - 90)   # -90° so 0° points up
        length    = max_len  * rel_len
        width     = max_width * (rel_len ** 0.5)   # slightly taper width too

        pts = _leaflet_points(cx, cy, angle_rad, length, width, n_teeth=7)
        draw.polygon(pts, fill=leaf_fill, outline=leaf_outline)

        # Midrib vein
        tip_x = cx + math.cos(angle_rad) * length
        tip_y = cy + math.sin(angle_rad) * length
        vein_w = max(1, s // 90)
        draw.line([(cx, cy), (tip_x, tip_y)], fill=vein_color, width=vein_w)

    # ── Stem ─────────────────────────────────────────────────────────────
    stem_len = int(s * 0.12)
    stem_w   = max(2, s // 36)
    draw.line(
        [(cx, cy), (cx, cy + stem_len)],
        fill=(90, 55, 20, 255),
        width=stem_w,
    )

    # ── Downsample (LANCZOS = best anti-aliasing) ─────────────────────────
    return img.resize((size, size), Image.LANCZOS)


def get_ctk_logo(size: int = 72):
    """Return a customtkinter CTkImage wrapping the cannabis leaf graphic."""
    import customtkinter as ctk
    pil_img = make_cannabis_logo(size)
    return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size))
