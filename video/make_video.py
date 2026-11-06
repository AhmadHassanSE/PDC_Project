"""Renders the Live Delivery Tracker project video (MP4, 1280x720, 30 fps, no audio).

Usage:
    py -3.13 make_video.py              render the full video
    py -3.13 make_video.py --preview    save a few still frames to check the look

Needs ffmpeg on PATH. Uses route.json (saved from Amazon Location Routes) when present,
otherwise a straight line between the start and end points in demo/config.py.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "demo"))
import config  # noqa: E402
from truck_simulator import distance_m, resample  # noqa: E402

W, H, FPS = 1280, 720, 30
WORK = r"D:\PDC_video_work"          # tile cache and preview frames
OUT = os.path.join(HERE, "DeliveryTracker_video.mp4")
ROUTE_FILE = os.path.join(HERE, "route.json")
ZOOM = 14
TILE_URL = ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/"
            "World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}")
SPEEDUP = 5                          # the map scene plays the 1-message-per-second trip 5x faster

NAVY = (14, 21, 38)
NAVY2 = (22, 32, 58)
EDGE = (38, 51, 90)
ORANGE = (255, 159, 28)
TEAL = (46, 196, 182)
LIGHT = (244, 241, 234)
MUTED = (196, 204, 221)
DIM = (128, 140, 168)
RED = (255, 84, 84)

_fonts = {}


def font(kind, size):
    name = {"bold": "segoeuib.ttf", "semi": "seguisb.ttf", "reg": "segoeui.ttf", "mono": "consola.ttf"}[kind]
    if (name, size) not in _fonts:
        _fonts[(name, size)] = ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", name), size)
    return _fonts[(name, size)]


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def window(t, start, dur):
    """0 before `start`, easing to 1 over `dur` seconds."""
    return smooth((t - start) / dur)


def lerp(a, b, u):
    return a + (b - a) * u


def rgba(c, a):
    return (c[0], c[1], c[2], int(255 * clamp(a)))


def text(d, xy, s, f, color, alpha=1.0, anchor="la"):
    if alpha > 0.01:
        d.text(xy, s, font=f, fill=rgba(color, alpha), anchor=anchor)


def pin(d, x, y, color, alpha=1.0, size=1.0):
    """Teardrop map pin whose tip is at (x, y)."""
    r = 13 * size
    cy = y - 26 * size
    d.ellipse([x - r, cy - r, x + r, cy + r], fill=rgba(color, alpha))
    d.polygon([(x - r * 0.75, cy + r * 0.6), (x + r * 0.75, cy + r * 0.6), (x, y)], fill=rgba(color, alpha))
    d.ellipse([x - r * 0.4, cy - r * 0.4, x + r * 0.4, cy + r * 0.4], fill=rgba(NAVY, alpha))


def label_pill(d, x, y, s, color, alpha):
    f = font("semi", 17)
    w = d.textlength(s, font=f)
    d.rounded_rectangle([x, y - 15, x + w + 24, y + 15], radius=15, fill=rgba(NAVY, 0.85 * alpha),
                        outline=rgba(color, alpha), width=2)
    text(d, (x + 12, y), s, f, LIGHT, alpha, "lm")


def make_bg():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot((xx - 0.76 * W) / W, (yy - 0.36 * H) / H) / 0.8
    u = np.clip(r, 0, 1)[..., None]
    c0, c1 = np.array([32, 46, 86]), np.array(NAVY)
    return Image.fromarray((c0 * (1 - u) + c1 * u).astype(np.uint8))


BG = make_bg()
NAVY_IMG = Image.new("RGB", (W, H), NAVY)


def cubic(p0, p1, p2, p3, n=40):
    out = []
    for t in np.linspace(0, 1, n):
        a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
    return out


# The same decorative route as on the title slide.
DECO = (cubic((60, 700), (200, 640), (160, 480), (320, 460))
        + cubic((320, 460), (480, 440), (520, 360), (480, 240))[1:]
        + cubic((480, 240), (440, 120), (600, 80), (700, 70))[1:])
DECO = [(x * 0.62 + 770, y * 0.62 + 120) for x, y in DECO]


def draw_grid(d, alpha=10):
    for x in range(0, W, 80):
        d.line([(x, 0), (x, H)], fill=(244, 241, 234, alpha))
    for y in range(0, H, 80):
        d.line([(0, y), (W, y)], fill=(244, 241, 234, alpha))


def draw_deco(d, progress, solid=False):
    k = int(len(DECO) * progress)
    if solid:
        d.line(DECO[:max(k, 2)], fill=rgba(ORANGE, 0.95), width=6, joint="curve")
    else:
        for i in range(0, k, 3):
            x, y = DECO[i]
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=rgba(ORANGE, 0.95))
    sx, sy = DECO[0]
    a = clamp(progress * 6)
    d.ellipse([sx - 11, sy - 11, sx + 11, sy + 11], fill=rgba(TEAL, a))
    d.ellipse([sx - 22, sy - 22, sx + 22, sy + 22], outline=rgba(TEAL, 0.35 * a), width=3)
    if progress >= 0.98:
        ex, ey = DECO[-1]
        pin(d, ex, ey + 12, ORANGE, 1.0, 1.3)


# ---------------------------------------------------------------- scenes

def scene_title(t):
    im = BG.copy()
    d = ImageDraw.Draw(im, "RGBA")
    draw_grid(d)
    draw_deco(d, window(t, 0.3, 2.6))
    a = [window(t, s, 0.7) for s in (0.2, 0.5, 1.0, 1.4)]
    text(d, (90, 222 + 20 * (1 - a[0])), "PDC · CLOUD SERVICES PRESENTATION", font("mono", 18), ORANGE, a[0])
    text(d, (84, 262 + 20 * (1 - a[1])), "Live Delivery", font("bold", 84), LIGHT, a[1])
    text(d, (84, 352 + 20 * (1 - a[1])), "Tracker", font("bold", 84), LIGHT, a[1])
    text(d, (90, 470 + 20 * (1 - a[2])), "Amazon Location Service + AWS IoT Core", font("reg", 30), MUTED, a[2])
    text(d, (90, 522 + 20 * (1 - a[3])), config.START_NAME, font("semi", 22), LIGHT, a[3])
    return im


def scene_problem(t):
    im = NAVY_IMG.copy()
    d = ImageDraw.Draw(im, "RGBA")
    draw_grid(d, 8)
    q = "“Where is my delivery right now?”"
    f = font("bold", 60)
    x0 = (W - d.textlength(q, font=f)) / 2
    n = int(len(q) * window(t, 0.3, 2.0))
    text(d, (x0, 250), q[:n], f, LIGHT)
    if 0 < n < len(q) and int(t * 3) % 2 == 0:
        cx = x0 + d.textlength(q[:n], font=f) + 4
        d.rectangle([cx, 262, cx + 4, 318], fill=rgba(ORANGE, 1))
    chips = [("Every vehicle reports", ORANGE), ("Every position is kept", TEAL), ("Every answer is live", ORANGE)]
    cf = font("semi", 22)
    widths = [d.textlength(s, font=cf) + 64 for s, _ in chips]
    x = (W - sum(widths) - 24 * (len(chips) - 1)) / 2
    for i, ((s, c), w) in enumerate(zip(chips, widths)):
        a = window(t, 2.8 + 0.5 * i, 0.5)
        y = 400 + 16 * (1 - a)
        d.rounded_rectangle([x, y, x + w, y + 54], radius=27, fill=rgba(NAVY2, a), outline=rgba(EDGE, a), width=2)
        d.ellipse([x + 22, y + 21, x + 34, y + 33], fill=rgba(c, a))
        text(d, (x + 44, y + 27), s, cf, LIGHT, a, "lm")
        x += w + 24
    text(d, (W / 2, 530), "Building that yourself means servers, databases and a lot of scaling work.",
         font("reg", 22), MUTED, window(t, 5.0, 0.8), "mm")
    return im


NODES = [
    ("Truck", "Python GPS simulator", "truck01", DIM),
    ("IoT Core", "MQTT over TLS", "trucks/location", ORANGE),
    ("IoT rule", "Forwards messages", "SELECT *", ORANGE),
    ("Tracker", "Position history", "DeliveryTracker", TEAL),
    ("Live map", "Draws the route", "localhost:8000", TEAL),
]
NW, NH, NGAP, NY = 200, 170, 52, 250
NX0 = (W - (5 * NW + 4 * NGAP)) / 2


def scene_flow(t):
    im = NAVY_IMG.copy()
    d = ImageDraw.Draw(im, "RGBA")
    draw_grid(d, 8)
    a = window(t, 0.1, 0.6)
    text(d, (NX0, 70), "OUR SOLUTION", font("mono", 16), ORANGE, a)
    text(d, (NX0, 92), "How the data flows", font("bold", 44), LIGHT, a)

    # packets: each hop crosses one gap between boxes
    hop_time, period = 0.55, 1.1
    lit = [0.0] * 5
    packets = []
    if t > 4.2:
        for k in range(8):
            p = (t - 4.2 - k * period) / hop_time
            if 0 <= p < 4:
                hop, frac = int(p), p - int(p)
                gx0 = NX0 + (hop + 1) * NW + hop * NGAP
                packets.append((lerp(gx0 - 6, gx0 + NGAP + 6, smooth(frac)), NY + NH / 2))
                if frac > 0.85:
                    lit[hop + 1] = max(lit[hop + 1], (frac - 0.85) / 0.15)
            elif 4 <= p < 4.6:
                lit[4] = max(lit[4], 1 - (p - 4) / 0.6)

    for i, (name, sub, code, c) in enumerate(NODES):
        a = window(t, 0.6 + 0.45 * i, 0.5)
        x, y = NX0 + i * (NW + NGAP), NY + 18 * (1 - a)
        edge = tuple(int(lerp(EDGE[j], c[j], lit[i])) for j in range(3))
        d.rounded_rectangle([x, y, x + NW, y + NH], radius=14, fill=rgba(NAVY2, a), outline=rgba(edge, a), width=2)
        d.rounded_rectangle([x, y, x + NW, y + 8], radius=4, fill=rgba(c, a))
        text(d, (x + 18, y + 26), name, font("semi", 26), LIGHT, a)
        text(d, (x + 18, y + 70), sub, font("reg", 17), MUTED, a)
        text(d, (x + 18, y + 130), code, font("mono", 15), c, a)
        if i < 4:
            ca = window(t, 0.9 + 0.45 * i, 0.4)
            gx0, gy = x + NW + 6, NY + NH / 2
            gx1 = lerp(gx0, gx0 + NGAP - 12, ca)
            if ca > 0:
                d.line([(gx0, gy), (gx1, gy)], fill=rgba(DIM, 1), width=3)
                if ca >= 1:
                    d.polygon([(gx1, gy), (gx1 - 9, gy - 6), (gx1 - 9, gy + 6)], fill=rgba(DIM, 1))

    for px, py in packets:
        for r, al in ((14, 0.15), (9, 0.35), (5, 1.0)):
            d.ellipse([px - r, py - r, px + r, py + r], fill=rgba(ORANGE, al))

    # group brackets
    for (i0, i1, s, c), st in zip([(1, 2, "AWS IoT Core", ORANGE), (3, 4, "Amazon Location Service", TEAL)], (3.0, 3.4)):
        a = window(t, st, 0.6)
        x0, x1 = NX0 + i0 * (NW + NGAP), NX0 + i1 * (NW + NGAP) + NW
        by = NY + NH + 34
        d.line([(x0, by - 10), (x0, by), (x1, by), (x1, by - 10)], fill=rgba(c, a), width=3)
        text(d, ((x0 + x1) / 2, by + 26), s, font("semi", 20), c, a, "mm")

    # the JSON message
    a = window(t, 5.0, 0.6)
    msg = '{"deviceId": "truck01", "latitude": 33.6563, "longitude": 73.0153}'
    mf = font("mono", 15)
    mw = d.textlength(msg, font=mf) + 28
    mx, my = NX0, NY - 66
    d.rounded_rectangle([mx, my, mx + mw, my + 36], radius=10, fill=rgba(NAVY2, a), outline=rgba(ORANGE, a), width=1)
    text(d, (mx + 14, my + 18), msg, mf, LIGHT, a, "lm")
    text(d, (W / 2, 620), "No part talks directly to another: each one only hands data to the cloud.",
         font("reg", 22), MUTED, window(t, 8.5, 0.8), "mm")
    return im


# ---------------------------------------------------------------- map scene

def merc(lat, lon):
    n = 256 * 2 ** ZOOM
    x = (lon + 180) / 360 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def load_route():
    if os.path.exists(ROUTE_FILE):
        with open(ROUTE_FILE) as fh:
            pts = [tuple(p) for p in json.load(fh)]
        print(f"Using route.json ({len(pts)} points)")
        return pts, True
    print("route.json not found: using a straight line")
    return resample([config.START, config.END], config.STEP_METERS), False


class MapScene:
    def __init__(self):
        self.route, self.road = load_route()
        self.n = len(self.route)
        self.trip = self.n / SPEEDUP
        self.dur = 1.5 + self.trip + 3.0
        self.cum = [0.0]
        for a, b in zip(self.route, self.route[1:]):
            self.cum.append(self.cum[-1] + distance_m(a, b))
        self.total_km = self.cum[-1] / 1000
        self.px = [merc(lat, lon) for lat, lon in self.route]
        xs, ys = [p[0] for p in self.px], [p[1] for p in self.px]
        self.center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        self.s_fit = min(540 / (max(ys) - min(ys) + 1), 640 / (max(xs) - min(xs) + 1), 1.0)
        self.s_near = max(self.s_fit * 1.8, 1.0)
        self.focus = (430, 360)        # screen point the camera centres on (the panel covers the right side)
        self._build_mosaic()

    def _build_mosaic(self):
        # the widest view is centred on the route at s_fit; closer views stay inside it
        fx, fy = self.focus
        cx, cy = self.center
        tx0 = int((cx - fx / self.s_fit - 256) // 256)
        tx1 = int((cx + (W - fx) / self.s_fit + 256) // 256)
        ty0 = int((cy - fy / self.s_fit - 256) // 256)
        ty1 = int((cy + (H - fy) / self.s_fit + 256) // 256)
        os.makedirs(os.path.join(WORK, "tiles"), exist_ok=True)
        mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
        count = (tx1 - tx0 + 1) * (ty1 - ty0 + 1)
        print(f"Map: {count} tiles")
        for tx in range(tx0, tx1 + 1):
            for ty in range(ty0, ty1 + 1):
                path = os.path.join(WORK, "tiles", f"{ZOOM}_{tx}_{ty}.jpg")
                if not os.path.exists(path):
                    req = urllib.request.Request(TILE_URL.format(z=ZOOM, x=tx, y=ty),
                                                 headers={"User-Agent": "PDC-student-demo-video/1.0"})
                    with urllib.request.urlopen(req, timeout=30) as r, open(path, "wb") as fh:
                        fh.write(r.read())
                mosaic.paste(Image.open(path).convert("RGB"), ((tx - tx0) * 256, (ty - ty0) * 256))
        # tint the grey basemap navy to match the slides
        g = np.asarray(mosaic.convert("L")).astype(np.float32)
        v = np.clip((g - 30) / 120, 0, 1)[..., None] ** 1.1
        dark, light = np.array([9, 14, 30]), np.array([92, 116, 166])
        self.mosaic = Image.fromarray((dark * (1 - v) + light * v).astype(np.uint8))
        self.origin = (tx0 * 256, ty0 * 256)

    def at_distance(self, dist):
        i = max(0, min(self.n - 2, int(np.searchsorted(self.cum, dist) - 1)))
        seg = self.cum[i + 1] - self.cum[i]
        f = 0 if seg == 0 else clamp((dist - self.cum[i]) / seg)
        (x0, y0), (x1, y1) = self.px[i], self.px[i + 1]
        return (lerp(x0, x1, f), lerp(y0, y1, f)), i

    def __call__(self, t):
        u = clamp((t - 1.5) / self.trip)
        sent_f = u * (self.n - 1) + 1 if t >= 1.5 else 0
        sent = int(sent_f)
        truck, seg = self.at_distance(u * self.cum[-1])

        k = window(t, 1.2, 3.0) * (1 - window(t, 1.5 + self.trip - 2.0, 2.5))
        s = lerp(self.s_fit, self.s_near, k)
        cx, cy = lerp(self.center[0], truck[0], k), lerp(self.center[1], truck[1], k)
        fx, fy = self.focus
        left, top = cx - fx / s - self.origin[0], cy - fy / s - self.origin[1]
        im = self.mosaic.crop((int(left), int(top), int(left + W / s), int(top + H / s))).resize((W, H), Image.BILINEAR)

        def scr(p):
            return ((p[0] - cx) * s + fx, (p[1] - cy) * s + fy)

        # planned route, dashed
        d = ImageDraw.Draw(im, "RGBA")
        pts = [scr(p) for p in self.px]
        ga = window(t, 0.4, 1.0)
        for i in range(0, len(pts) - 1, 2):
            d.line([pts[i], pts[i + 1]], fill=rgba(LIGHT, 0.28 * ga), width=3)

        # driven trail with glow
        trail = pts[:seg + 1] + [scr(truck)] if sent else []
        if len(trail) >= 2:
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(glow).line(trail, fill=rgba(ORANGE, 0.55), width=16, joint="curve")
            glow = glow.filter(ImageFilter.GaussianBlur(7))
            im = Image.alpha_composite(im.convert("RGBA"), glow).convert("RGB")
            d = ImageDraw.Draw(im, "RGBA")
            d.line(trail, fill=rgba(ORANGE, 1), width=5, joint="curve")

        # pins
        sx, sy = scr(self.px[0])
        ex, ey = scr(self.px[-1])
        pa = window(t, 0.6, 0.6)
        d.ellipse([sx - 10, sy - 10, sx + 10, sy + 10], fill=rgba(TEAL, pa))
        d.ellipse([sx - 20, sy - 20, sx + 20, sy + 20], outline=rgba(TEAL, 0.4 * pa), width=3)
        label_pill(d, sx + 26, sy, config.START_NAME, TEAL, pa)
        pin(d, ex, ey, ORANGE, pa, 1.2)
        label_pill(d, ex + 22, ey - 30, config.END_NAME, ORANGE, pa)

        # truck with a ping for every message it sends
        if sent:
            tx, ty = scr(truck)
            f = sent_f - sent
            r = 10 + 34 * f
            d.ellipse([tx - r, ty - r, tx + r, ty + r], outline=rgba(ORANGE, 0.8 * (1 - f)), width=3)
            d.ellipse([tx - 16, ty - 16, tx + 16, ty + 16], fill=rgba(ORANGE, 0.25))
            d.ellipse([tx - 9, ty - 9, tx + 9, ty + 9], fill=rgba(LIGHT, 1), outline=rgba(ORANGE, 1), width=3)

        self._panel(d, t, sent, sent_f - sent, u)
        self._hud(d, t)

        if t > 1.5 + self.trip:
            a = window(t, 1.5 + self.trip, 0.6)
            msg = f"Delivered · {config.END_NAME}"
            bf = font("semi", 26)
            w = d.textlength(msg, font=bf) + 60
            x, y = 24, 86 + 14 * (1 - a)
            d.rounded_rectangle([x, y, x + w, y + 56], radius=28, fill=rgba(ORANGE, a))
            text(d, (x + w / 2, y + 28), msg, bf, NAVY, a, "mm")
        return im

    def _panel(self, d, t, sent, frac, u):
        a = window(t, 0.6, 0.7)
        px = 880 + 60 * (1 - a)
        d.rounded_rectangle([px, 30, px + 370, 690], radius=18, fill=rgba(NAVY, 0.88 * a), outline=rgba(EDGE, a), width=2)
        text(d, (px + 24, 52), "AWS IOT CORE · MQTT", font("mono", 15), ORANGE, a)
        text(d, (px + 24, 74), "trucks/location", font("semi", 24), LIGHT, a)
        d.line([(px + 24, 118), (px + 346, 118)], fill=rgba(EDGE, a), width=2)
        rows = 11
        for j in range(rows):
            i = sent - 1 - j
            if i < 0:
                break
            lat, lon = self.route[i]
            sec = 20 * 60 + i
            stamp = f"16:{sec // 60:02d}:{sec % 60:02d}"
            y = 136 + j * 29
            al = a * (1 - j / (rows + 2)) * (clamp(frac * 4) if j == 0 and u < 1 else 1)
            text(d, (px + 24, y), stamp, font("mono", 15), DIM, al)
            text(d, (px + 116, y), f"{lat:.5f}, {lon:.5f}", font("mono", 15), ORANGE if j == 0 else LIGHT, al)
        d.line([(px + 24, 470), (px + 346, 470)], fill=rgba(EDGE, a), width=2)
        text(d, (px + 24, 490), "AMAZON LOCATION TRACKER", font("mono", 15), TEAL, a)
        text(d, (px + 24, 512), "DeliveryTracker", font("semi", 22), LIGHT, a)
        text(d, (px + 24, 560), f"{sent}", font("bold", 46), LIGHT, a)
        text(d, (px + 24, 622), "positions stored", font("reg", 17), MUTED, a)
        text(d, (px + 196, 560), f"{u * self.total_km:.1f}", font("bold", 46), LIGHT, a)
        text(d, (px + 196, 622), "km driven", font("reg", 17), MUTED, a)

    def _hud(self, d, t):
        a = window(t, 0.3, 0.6)
        d.rounded_rectangle([24, 24, 330, 66], radius=21, fill=rgba(NAVY, 0.85 * a), outline=rgba(EDGE, a), width=2)
        pulse = 0.5 + 0.5 * math.sin(t * 6)
        d.ellipse([42, 38, 56, 52], fill=rgba(RED, a * (0.5 + 0.5 * pulse)))
        text(d, (66, 45), "LIVE · truck01", font("semi", 19), LIGHT, a, "lm")
        text(d, (226, 45), f"{SPEEDUP}× speed", font("reg", 17), MUTED, a, "lm")
        credit = "Basemap: Esri, HERE, Garmin, © OpenStreetMap contributors"
        if self.road:
            credit += " · Route: Amazon Location Routes"
        text(d, (24, H - 26), credit, font("reg", 13), DIM, a)


def make_stats(map_scene):
    stats = [
        (map_scene.n, "{:.0f}", "GPS messages", ORANGE),
        (map_scene.total_km, "{:.1f} km", "driven", TEAL),
        (None, "1 / s", "update rate", ORANGE),
        (None, "$0", "out of pocket", TEAL),
    ]

    def scene(t):
        im = NAVY_IMG.copy()
        d = ImageDraw.Draw(im, "RGBA")
        draw_grid(d, 8)
        text(d, (W / 2, 170), "The trip in numbers", font("semi", 34), LIGHT, window(t, 0.1, 0.6), "mm")
        for i, (val, fmt, label, c) in enumerate(stats):
            a = window(t, 0.5 + 0.3 * i, 0.5)
            x = W / 8 + i * W / 4
            shown = fmt if val is None else fmt.format(val * window(t, 0.5 + 0.3 * i, 1.4))
            text(d, (x, 330 + 14 * (1 - a)), shown, font("bold", 70), c, a, "mm")
            text(d, (x, 400 + 14 * (1 - a)), label, font("reg", 22), MUTED, a, "mm")
        text(d, (W / 2, 520), "truck01  →  AWS IoT Core  →  IoT rule  →  Amazon Location tracker  →  live map",
             font("mono", 18), DIM, window(t, 2.2, 0.8), "mm")
        return im
    return scene


def scene_outro(t):
    im = BG.copy()
    d = ImageDraw.Draw(im, "RGBA")
    draw_grid(d)
    draw_deco(d, window(t, 0.0, 1.6), solid=True)
    a = [window(t, s, 0.7) for s in (0.2, 0.6, 1.0, 1.6)]
    text(d, (90, 200 + 20 * (1 - a[0])), "DELIVERED · " + config.END_NAME.upper(), font("mono", 18), ORANGE, a[0])
    text(d, (84, 236 + 20 * (1 - a[1])), "Thank you", font("bold", 84), LIGHT, a[1])
    text(d, (90, 370), "AWS IoT Core", font("semi", 26), ORANGE, a[2])
    text(d, (90 + d.textlength("AWS IoT Core ", font=font("semi", 26)), 370),
         "gets device data into the cloud, securely.", font("reg", 26), MUTED, a[2])
    text(d, (90, 414), "Amazon Location Service", font("semi", 26), TEAL, a[3])
    text(d, (90 + d.textlength("Amazon Location Service ", font=font("semi", 26)), 414),
         "turns it into places on a map.", font("reg", 26), MUTED, a[3])
    text(d, (90, 500), f"{config.START_NAME} · Parallel & Distributed Computing", font("reg", 20), DIM,
         window(t, 2.2, 0.8))
    return im


# ---------------------------------------------------------------- render

def faded(scene, dur):
    def f(t):
        im = scene(t)
        a = min(window(t, 0, 0.5), 1 - window(t, dur - 0.5, 0.5))
        return im if a >= 1 else Image.blend(NAVY_IMG, im, a)
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    map_scene = MapScene()
    scenes = [(scene_title, 6.0), (scene_problem, 8.0), (scene_flow, 12.0), (map_scene, map_scene.dur),
              (make_stats(map_scene), 6.0), (scene_outro, 6.0)]
    timeline, t0 = [], 0.0
    for fn, dur in scenes:
        timeline.append((t0, dur, faded(fn, dur)))
        t0 += dur
    total = t0
    print(f"Video length: {total:.1f} s")

    def frame_at(t):
        for start, dur, fn in timeline:
            if t < start + dur:
                return fn(t - start)
        return timeline[-1][2](timeline[-1][1] - 1e-3)

    if args.preview:
        os.makedirs(os.path.join(WORK, "preview"), exist_ok=True)
        for t in (3.5, 10.5, 24.0, 33.0, 45.0, total - 15.5, total - 3.0):
            path = os.path.join(WORK, "preview", f"frame_{t:05.1f}.png")
            frame_at(t).save(path)
            print("saved", path)
        return

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found on PATH")
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    frames = int(total * FPS)
    for i in range(frames):
        proc.stdin.write(frame_at(i / FPS).tobytes())
        if i % (FPS * 5) == 0:
            print(f"{i / FPS:5.1f} / {total:.1f} s")
    proc.stdin.close()
    proc.wait()
    print("Saved", OUT)


if __name__ == "__main__":
    main()
