#!/usr/bin/env python3
"""Build quicksilver.json from theme.css.

Run:     python3 build.py
Install: t3 theme set quicksilver.json --id quicksilver

Needs only Python 3.9 or later; no packages.
"""

import base64
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEME_ID = "quicksilver"
THEME_NAME = "Quicksilver"
CSS_LIMIT = 50_000  # T3 Code's limit on a theme's css

# T3 derives a full palette from canvas and accent; COLORS replaces single roles.
CANVAS = "#090909"
ACCENT = "#e6e6e6"
COLORS = {
    "chrome": "#090909",
    "toolbar": "#090909",
    "sidebar": "#0a0a0a",
    "sidebarBorder": "#1b1b1b",
    "sidebarControlSurface": "#141414",
    "sidebarRowHover": "#141414",
    "sidebarRowActive": "#1a1a1a",
    "sidebarRowSelected": "#1a1a1a",
    "border": "#1f1f1f",
    "surface": "#0e0e0e",
    "surfaceRaised": "#111111",
    "surfaceOverlay": "#141414",
    "input": "#262626",
    "accentForeground": "#0a0a0a",
    "messageSurface": "#1a1a1a",
    # T3 uses the action color for every solid control: primary buttons (Save,
    # Confirm), switches and sliders. Bright silver with dark text.
    "messageAction": "#e6e6e6",
    "messageActionForeground": "#0a0a0a",
    "messageActionHover": "#ffffff",
    "codeBackground": "#0d0d0d",
    "terminalBackground": "#090909",
}

# ---------------------------------------------------------------------------
# The liquid metal is one repeating wave. A "front" passes each point of an
# edge once per cycle. WAVE_COLORS is the color of one fixed point over a
# cycle: (fraction of the cycle since the front passed, color). Right after
# the front come two rainbow fringes around a thin white strip, then dark
# navy, which brightens back to white before the next front.
WAVE_COLORS = [
    (0.0000, "#f7fbb1"), (0.0097, "#f7c14c"), (0.0194, "#c91470"), (0.0291, "#3b605b"),
    (0.0388, "#574c4f"), (0.0485, "#552f9e"), (0.0583, "#4180e4"), (0.0680, "#75dff9"),
    (0.0777, "#c7fcfa"), (0.0874, "#f5f8fe"), (0.1165, "#f8f8fc"), (0.1262, "#f7f9e5"),
    (0.1359, "#f8eea6"), (0.1456, "#f8bb6e"), (0.1553, "#da7341"), (0.1650, "#a53630"),
    (0.1748, "#6f1930"), (0.1845, "#441330"), (0.1942, "#271731"), (0.2039, "#191a33"),
    (0.3010, "#222138"), (0.3980, "#34374f"), (0.4950, "#5c5e77"), (0.5920, "#808399"),
    (0.6890, "#989baf"), (0.7860, "#adb1c2"), (0.8350, "#bfc3d2"), (0.8830, "#d3d7e4"),
    (0.9320, "#e7eaf4"), (0.9810, "#f2f6fc"), (1.0000, "#f5f5ff"),
]

# One wave takes this long everywhere: on the box, the ring and the logo.
CYCLE_SECONDS = 5

# What the message box edge does in a thread while the agent is not working.
# (While it works, and on the new-thread page, the wave always runs at
# CYCLE_SECONDS.)
#   "still": the wave stops and the still metal shows (see --qs-box-still in
#            theme.css).
#   "slow":  the same wave, one pass every IDLE_CYCLE_SECONDS.
IDLE_EDGE = "slow"
IDLE_CYCLE_SECONDS = 15
IDLE_UPDATES_PER_SECOND = 30

# How many times a second the metal is redrawn. The wave moves in this many
# small steps a second instead of once per screen refresh; on a 120 Hz screen
# that halves the drawing work, and at 60 a second the steps cannot be seen.
UPDATES_PER_SECOND = 60

# The message box: when the front passes each point of the box's edge, as a
# fraction of the cycle. Each edge is a list of (position along the edge,
# time); positions run from the left on the top and bottom edges and from the
# top on the sides, and the time changes evenly between two neighbouring
# points.
#
# Read as motion: a front is born on the bottom edge a quarter of the way from
# the left (time 0). It spreads slowly at first. One front then runs right
# along the bottom and up the right side. The other runs left, up the left
# side and along the top, and the two meet high on the right side.
BOX_TIMING = {
    "bottom": [(0.0, 0.18), (0.09, 0.045), (0.25, 0.0), (0.5, 0.12), (0.88, 0.65), (1.0, 0.74)],
    "right": [(0.0, 0.89), (0.22, 1.08), (1.0, 0.74)],
    "top": [(0.0, 0.62), (1.0, 0.89)],
    "left": [(0.0, 0.62), (1.0, 0.18)],
}

# The send button's ring. `source` is where the front is born, in degrees
# clockwise from the top; the two fronts meet on the opposite side. `waves` is
# how many waves fit on each way round. Twice `waves` must be a whole number,
# so the pattern closes around the full circle.
RING = {"source": 206, "waves": 1.5}

# The logo on the new-thread page: T3's "T3" mark, used as a mask over the
# wave. `height` is in pixels. The wave spreads in circles from `source`, a
# point measured from the mark's top left corner (here just below the T), and
# `wave` is the distance between two fronts in pixels; the mark is about 73
# pixels wide, so one or two fronts show at a time.
LOGO = {
    "height": 44,
    "source": "12.2px 58px",
    "wave": 52,
    "viewbox": (15.5309, 37, 94.3941, 56.96),
    "path": (
        "M33.4509 93V47.56H15.5309V37H64.3309V47.56H46.4109V93H33.4509ZM86.7253 93.96C82.832 93.96 78.9653 93.4533 "
        "75.1253 92.44C71.2853 91.3733 68.032 89.88 65.3653 87.96L70.4053 78.04C72.5386 79.5867 75.0186 80.8133 "
        "77.8453 81.72C80.672 82.6267 83.5253 83.08 86.4053 83.08C89.6586 83.08 92.2186 82.44 94.0853 81.16C95.952 "
        "79.88 96.8853 78.12 96.8853 75.88C96.8853 73.7467 96.0586 72.0667 94.4053 70.84C92.752 69.6133 90.0853 69 "
        "86.4053 69H80.4853V60.44L96.0853 42.76L97.5253 47.4H68.1653V37H107.365V45.4L91.8453 63.08L85.2853 "
        "59.32H89.0453C95.9253 59.32 101.125 60.8667 104.645 63.96C108.165 67.0533 109.925 71.0267 109.925 "
        "75.88C109.925 79.0267 109.099 81.9867 107.445 84.76C105.792 87.48 103.259 89.6933 99.8453 91.4C96.432 "
        "93.1067 92.0586 93.96 86.7253 93.96Z"
    ),
}


def pct(value: float) -> str:
    return f"{value * 100:.3f}".rstrip("0").rstrip(".") + "%"


def number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def box_tokens() -> dict[str, str]:
    """The message box: one background layer per stretch of edge between two
    points of BOX_TIMING.

    Each layer is a repeating radial gradient of the wave, cut to its stretch.
    Its ellipse is one wave long and enormously tall (or wide, on the sides),
    so across the thin band its rings are straight lines. The stops never
    change; only the ellipse's centre moves with --qs-p (the cycle's progress,
    0 to 1), which carries the fronts along the stretch. The centre always
    lies ahead of the stretch's far end, so the stretch only ever shows the
    side of the rings that is behind a front.

    One moving value per stretch keeps this cheap. An earlier version moved
    every stop of a linear gradient instead (31 calc() expressions per
    stretch), and re-reading those on every frame took several times the
    processor time for the same picture.
    """
    stops = ", ".join(f"{color} {number(u * 100)}%" for u, color in WAVE_COLORS)
    images, sizes, positions = [], [], []
    for edge, points in BOX_TIMING.items():
        horizontal = edge in ("top", "bottom")
        for (a, t_a), (b, t_b) in zip(points, points[1:]):
            t0, span = min(t_a, t_b), max(abs(t_b - t_a), 0.01)
            wave = 100 / span                       # one wave, in percent of the stretch
            # Where the centre is, in percent of the stretch along the way the
            # front travels: a whole number of waves ahead of the front, enough
            # to stay beyond the far end for the whole cycle.
            waves_ahead = math.ceil(t0 + span)
            rate, start = wave, (waves_ahead - t0) * wave
            if t_b < t_a:                           # the front travels toward the stretch's start
                rate, start = -rate, 100 - start
            centre = f"calc(var(--qs-p) * {number(rate)}% + {number(start)}%)"
            if horizontal:
                shape = f"ellipse {number(wave)}% 99999px at {centre} 50%"
            else:
                shape = f"ellipse 99999px {number(wave)}% at 50% {centre}"
            images.append(f"repeating-radial-gradient({shape}, {stops})")
            k = b - a
            # One extra pixel, so neighbouring stretches overlap instead of leaving a gap.
            length = f"calc({pct(k)} + 1px)"
            where = pct(a / (1 - k)) if k < 1 else "0%"
            if horizontal:
                sizes.append(f"{length} var(--qs-band)")
                positions.append(f"{where} {'0%' if edge == 'top' else '100%'}")
            else:
                sizes.append(f"var(--qs-band) {length}")
                positions.append(f"{'0%' if edge == 'left' else '100%'} {where}")
    return {
        "box-images": ",\n    ".join(images),
        "box-sizes": ", ".join(sizes),
        "box-positions": ", ".join(positions),
    }


def ring_tokens() -> dict[str, str]:
    """The send button's ring: the wave as conic gradients, one per half."""
    # One wave in the direction the front travels: white just ahead of a front,
    # darkening toward the next front's fringes.
    tile = sorted((1 - u, color) for u, color in WAVE_COLORS)
    wave = 180 / RING["waves"]  # degrees per wave, the same both ways round
    if (360 / wave) % 1:
        raise SystemExit("RING: twice `waves` must be a whole number")

    def wedge(start: float, arc: float) -> str:
        """A clip-path polygon covering the ring from `start` clockwise over `arc` degrees."""
        points = ["50% 50%"]
        steps = 4
        for i in range(steps + 1):
            a = math.radians(start + arc * i / steps)
            points.append(f"{50 + 100 * math.sin(a):.1f}% {50 - 100 * math.cos(a):.1f}%")
        return "polygon(" + ", ".join(points) + ")"

    return {
        "ring-source": f"{RING['source']}deg",
        "ring-wave": f"{wave:g}deg",
        "pal-cw": ", ".join(f"{color} {v * wave:.2f}deg" for v, color in tile),
        "pal-ccw": ", ".join(f"{color} {(1 - v) * wave:.2f}deg" for v, color in reversed(tile)),
        # The clockwise half lies on top and overlaps the seams by a few degrees, so no gap shows.
        "ring-cw-clip": wedge(RING["source"] - 3, 186),
        "ring-ccw-clip": wedge(RING["source"] + 180, 180),
    }


def logo_tokens() -> dict[str, str]:
    """The logo: its size, its mask, and the wave as circles around its source."""
    x, y, width, height = LOGO["viewbox"]
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='{x} {y} {width} {height}'>"
        f"<path d='{LOGO['path']}'/></svg>"
    )
    # Base64, so nothing in the image can be mistaken for CSS.
    mask = base64.b64encode(svg.encode()).decode()
    # A point at distance d from the source shows the color for "p - d / wave"
    # of a cycle since the front passed.
    wave = LOGO["wave"]
    stops = ", ".join(
        f"{color} calc(var(--qs-p) * {wave}px + {(1 - u) * wave:.2f}px)"
        for u, color in sorted(WAVE_COLORS, reverse=True)
    )
    return {
        "logo-mask": f'url("data:image/svg+xml;base64,{mask}")',
        "logo-width": f"{LOGO['height'] * width / height:.1f}px",
        "logo-height": f"{LOGO['height']}px",
        "logo-wave": f"repeating-radial-gradient(circle at {LOGO['source']}, {stops})",
    }


def idle_edge_rule() -> str:
    """The CSS for IDLE_EDGE.

    "slow" keeps one wave and only changes its speed, so it never jumps. Two
    animations add up on the wave's progress (--qs-p): a slow one that always
    runs, and a push that runs only while the agent works (and on the
    new-thread page). Together they make one pass every CYCLE_SECONDS. A
    paused animation keeps its value, so pausing or resuming the push changes
    the speed without moving the wave.
    """
    if IDLE_EDGE == "still":
        return ""
    if IDLE_EDGE != "slow":
        raise SystemExit(f"IDLE_EDGE must be 'still' or 'slow', not {IDLE_EDGE!r}")
    push = 1 / (1 / CYCLE_SECONDS - 1 / IDLE_CYCLE_SECONDS)   # seconds per pass of the push alone
    slow = f"qs-cycle {IDLE_CYCLE_SECONDS:g}s steps({round(IDLE_CYCLE_SECONDS * IDLE_UPDATES_PER_SECOND)}) infinite"
    fast = f"qs-push {push:g}s steps({round(push * UPDATES_PER_SECOND)}) infinite"
    host = ".dark [data-slot=composer-host]"
    return f"""@keyframes qs-push {{
  from {{ --qs-p: 0; }}
  to {{ --qs-p: 1; }}
}}

@media (prefers-reduced-motion: no-preference) {{
  {host}::after {{
    opacity: 1;
    transition: none;
    animation: {slow}, {fast};
    animation-composition: replace, add;
    animation-play-state: running, paused;
  }}
  .dark [data-chat-composer-stack]:has(h1) [data-slot=composer-host]::after,
  {host}:has(button[aria-label^="Stop"], button[aria-label="Queue message"], button[aria-label="Steer message"])::after {{
    opacity: 1;
    transition: none;
    animation: {slow}, {fast};
    animation-composition: replace, add;
    animation-play-state: running, running;
  }}
}}"""


def fill_tokens(css: str, tokens: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        return tokens[match.group(1)]  # an unknown placeholder is an error

    return re.sub(r"\{\{([a-z0-9-]+)\}\}", replace, css)


def minify(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    return css.replace(";}", "}").strip()


def main() -> None:
    tokens = {
        "cycle": f"{CYCLE_SECONDS:g}s",
        "cycle-steps": str(round(CYCLE_SECONDS * UPDATES_PER_SECOND)),
        "idle-edge": idle_edge_rule(),
        **box_tokens(), **ring_tokens(), **logo_tokens(),
    }
    css = minify(fill_tokens((HERE / "theme.css").read_text(), tokens))
    if len(css) > CSS_LIMIT:
        raise SystemExit(f"css is {len(css)} characters; T3 allows {CSS_LIMIT}")
    if css.count("{") != css.count("}"):
        raise SystemExit("unbalanced braces in theme.css")
    theme = {
        "version": 1,
        "name": THEME_NAME,
        "appearance": "dark",
        "canvas": CANVAS,
        "accent": ACCENT,
        "colors": COLORS,
        "css": css,
    }
    out = HERE / f"{THEME_ID}.json"
    out.write_text(json.dumps(theme, indent=2) + "\n")
    print(f"wrote {out.name}: {len(css)} characters of css")


if __name__ == "__main__":
    main()
