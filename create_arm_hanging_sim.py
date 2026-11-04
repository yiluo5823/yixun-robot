from __future__ import annotations

import math
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
FRAME_DIR = OUT / "arm_hanging_frames"
KEY_DIR = OUT / "arm_hanging_keyframes"
GIF_PATH = OUT / "arm_hanging_sim.gif"
MP4_PATH = OUT / "arm_hanging_sim.mp4"

W, H = 1280, 720
FPS = 16
DURATION = 6.0
N = int(FPS * DURATION)
BG_CACHE = None


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


F_TITLE = font(34, True)
F_SUB = font(18)
F_LABEL = font(22, True)
F_SMALL = font(15, True)
F_TINY = font(12)


def lerp(a, b, u):
    return a + (b - a) * u


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def bezier(p0, p1, p2, p3, u):
    a = (1 - u) ** 3
    b = 3 * (1 - u) ** 2 * u
    c = 3 * (1 - u) * u ** 2
    d = u ** 3
    return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
            a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])


def stage_progress(t):
    if t < 1.45:
        return "视觉定位", t / 1.45
    if t < 3.2:
        return "动态撑开", (t - 1.45) / 1.75
    if t < 5.2:
        return "精准穿戴", (t - 3.2) / 2.0
    return "挂载完成", (t - 5.2) / 0.8


def make_bg():
    global BG_CACHE
    if BG_CACHE is not None:
        return BG_CACHE.copy()
    img = Image.new("RGB", (W, H), "#fffaf0")
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    y = np.arange(H, dtype=np.float32)[:, None]
    x = np.arange(W, dtype=np.float32)[None, :]
    arr[..., 0] = np.clip(255 - y * 0.018, 0, 255).astype(np.uint8)
    arr[..., 1] = np.clip(250 - y * 0.015, 0, 255).astype(np.uint8)
    arr[..., 2] = np.clip(240 + x * 0.006, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for x in range(0, W, 64):
        d.line((x, 0, x, H), fill=(51, 113, 165, 18), width=1)
    for y in range(0, H, 64):
        d.line((0, y, W, y), fill=(255, 143, 79, 16), width=1)
    d.ellipse((900, -160, 1350, 240), fill=(255, 143, 79, 28))
    d.ellipse((-160, 440, 340, 880), fill=(51, 113, 165, 20))
    BG_CACHE = Image.alpha_composite(img.convert("RGBA"), overlay)
    return BG_CACHE.copy()


def draw_polyline(d, pts, fill, width=2):
    if len(pts) > 1:
        d.line(pts, fill=fill, width=width, joint="curve")


def shirt_points(collar_width, collar_y=260):
    cx = 645
    left = cx - collar_width / 2
    right = cx + collar_width / 2
    collar = [
        (left, collar_y + 30),
        (cx - collar_width * 0.22, collar_y + 12),
        (cx, collar_y + 42),
        (cx + collar_width * 0.22, collar_y + 12),
        (right, collar_y + 30),
    ]
    body = [
        (left - 90, collar_y + 50),
        (left - 135, collar_y + 152),
        (left - 92, collar_y + 345),
        (right + 92, collar_y + 345),
        (right + 135, collar_y + 152),
        (right + 90, collar_y + 50),
    ]
    return cx, left, right, collar, body


def draw_shirt(img, collar_width, glow=0):
    cx, left, right, collar, body = shirt_points(collar_width)
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(panel)
    d.polygon(body, fill=(95, 149, 190, 46), outline=(77, 130, 171, 150))
    d.line(collar, fill=(54, 119, 165, 210), width=5, joint="curve")
    d.line([(cx, 320), (cx, 615)], fill=(54, 119, 165, 90), width=2)
    for i in range(8):
        yy = 330 + i * 34
        d.line((left - 62 + i * 5, yy, right + 62 - i * 5, yy + 10),
               fill=(54, 119, 165, 45), width=1)
    for i in range(9):
        xx = left - 74 + i * ((right - left + 148) / 8)
        d.line((xx, 330, xx + 18 * math.sin(i), 605),
               fill=(54, 119, 165, 36), width=1)
    if glow:
        d.rounded_rectangle((left - 24, 246, right + 24, 342), radius=24,
                            outline=(82, 211, 190, int(120 * glow)), width=4)
        d.line((cx - 18, 294, cx + 18, 294), fill=(82, 211, 190, int(180 * glow)), width=2)
        d.line((cx, 276, cx, 312), fill=(82, 211, 190, int(180 * glow)), width=2)
    return Image.alpha_composite(img, panel), left, right, cx


def ik(base, target, l1=170, l2=145, elbow_sign=1):
    bx, by = base
    tx, ty = target
    dx, dy = tx - bx, ty - by
    dist = max(30, min(math.hypot(dx, dy), l1 + l2 - 4))
    a = math.atan2(dy, dx)
    cos_elbow = (l1 * l1 + l2 * l2 - dist * dist) / (2 * l1 * l2)
    cos_elbow = max(-1, min(1, cos_elbow))
    elbow_angle = math.pi - math.acos(cos_elbow)
    cos_sh = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
    cos_sh = max(-1, min(1, cos_sh))
    shoulder_offset = math.acos(cos_sh)
    theta1 = a + elbow_sign * shoulder_offset
    ex = bx + l1 * math.cos(theta1)
    ey = by + l1 * math.sin(theta1)
    theta2 = math.atan2(ty - ey, tx - ex)
    return (ex, ey), theta1, theta2


def draw_arm(draw, base, target, side="left", open_grip=0.5):
    elbow_sign = -1 if side == "left" else 1
    elbow, th1, th2 = ik(base, target, elbow_sign=elbow_sign)
    bx, by = base
    ex, ey = elbow
    tx, ty = target
    color1 = (92, 124, 149, 255)
    color2 = (220, 235, 242, 255)
    accent = (69, 173, 205, 255)
    draw.line((bx, by, ex, ey), fill=color1, width=24)
    draw.line((ex, ey, tx, ty), fill=color1, width=20)
    draw.line((bx, by, ex, ey), fill=color2, width=15)
    draw.line((ex, ey, tx, ty), fill=color2, width=12)
    for p, r in [(base, 22), (elbow, 20), (target, 16)]:
        draw.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=(245, 250, 252, 255), outline=color1, width=3)
        draw.ellipse((p[0] - r + 7, p[1] - r + 7, p[0] + r - 7, p[1] + r - 7), outline=accent, width=2)
    angle = th2
    spread = lerp(0.18, 0.72, open_grip)
    length = 48
    for sgn in [-1, 1]:
        a = angle + sgn * spread
        x2 = tx + length * math.cos(a)
        y2 = ty + length * math.sin(a)
        draw.line((tx, ty, x2, y2), fill=(58, 70, 78, 255), width=7)
        draw.line((tx, ty, x2, y2), fill=(230, 241, 245, 255), width=4)


def draw_hanger(img, t, collar_left, collar_right):
    if t < 3.2:
        return img
    u = ease((t - 3.2) / 2.0)
    start = (1035, 395)
    end = ((collar_left + collar_right) / 2, 318)
    p = bezier(start, (930, 330), (780, 350), end, u)
    scale = lerp(0.92, 1.04, u)
    x, y = p
    w = 190 * scale
    h = 76 * scale
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.line((start[0], start[1], 910, 350, 780, 340, end[0], end[1]),
            fill=(82, 211, 190, 70), width=6, joint="curve")
    gd.line((start[0], start[1], 910, 350, 780, 340, end[0], end[1]),
            fill=(82, 211, 190, 160), width=2, joint="curve")
    gd.arc((x - 20, y - 82, x + 24, y - 30), 200, 560, fill=(80, 95, 105, 255), width=5)
    gd.line((x, y - 32, x - w / 2, y + h / 2), fill=(230, 239, 243, 255), width=9)
    gd.line((x, y - 32, x + w / 2, y + h / 2), fill=(230, 239, 243, 255), width=9)
    gd.line((x - w / 2, y + h / 2, x + w / 2, y + h / 2), fill=(230, 239, 243, 255), width=8)
    gd.line((x, y - 32, x - w / 2, y + h / 2), fill=(84, 105, 118, 255), width=2)
    gd.line((x, y - 32, x + w / 2, y + h / 2), fill=(84, 105, 118, 255), width=2)
    return Image.alpha_composite(img, glow)


def draw_hud(draw, t, stage, p):
    draw.rounded_rectangle((42, 34, 394, 82), radius=20, fill=(255, 255, 255, 220), outline=(234, 220, 207, 255), width=1)
    draw.text((62, 45), "衣循机械臂挂衣仿真", font=F_LABEL, fill=(38, 50, 69, 255))
    draw.text((44, 102), "视觉定位  →  双臂撑开  →  衣架穿入  →  挂载完成", font=F_SUB, fill=(82, 96, 111, 255))
    chips = [("领口识别", 48, 642, "#3371A5"), ("双臂协同", 184, 642, "#FF8F4F"), ("柔性衣物", 320, 642, "#63B884")]
    for text, x, y, c in chips:
        draw.rounded_rectangle((x, y, x + 116, y + 34), radius=17, fill=(255, 255, 255, 230), outline=(234, 220, 207, 255))
        draw.text((x + 18, y + 7), text, font=F_SMALL, fill=c)
    draw.rounded_rectangle((945, 40, 1218, 90), radius=18, fill=(255, 255, 255, 230), outline=(234, 220, 207, 255))
    draw.text((966, 54), f"T+{t:0.1f}s  {stage}", font=F_LABEL, fill=(233, 111, 43, 255))
    bar_x, bar_y = 946, 106
    draw.rounded_rectangle((bar_x, bar_y, bar_x + 272, bar_y + 10), radius=5, fill=(238, 226, 214, 255))
    draw.rounded_rectangle((bar_x, bar_y, bar_x + int(272 * (t / DURATION)), bar_y + 10), radius=5, fill=(255, 143, 79, 255))


def draw_frame(i):
    t = i / FPS
    stage, sp = stage_progress(t)
    locate = 1.0 if t > 0.35 else ease(t / 0.35)
    spread = ease((t - 1.45) / 1.75)
    collar_width = lerp(122, 238, spread)
    bg = make_bg()
    draw = ImageDraw.Draw(bg, "RGBA")

    # Main presentation panel.
    draw.rounded_rectangle((36, 144, 1244, 624), radius=34, fill=(255, 255, 255, 190), outline=(234, 220, 207, 255), width=2)
    bg, collar_left, collar_right, cx = draw_shirt(bg, collar_width, glow=locate if t < 2.2 else max(0.25, 1 - (t - 2.2) / 2))
    draw = ImageDraw.Draw(bg, "RGBA")

    # Target points and planned trajectories.
    left_target = (lerp(302, collar_left + 22, ease((t - 0.9) / 1.4)), lerp(410, 300, ease((t - 0.9) / 1.4)))
    right_target = (lerp(988, collar_right - 22, ease((t - 0.9) / 1.4)), lerp(410, 300, ease((t - 0.9) / 1.4)))
    if t > 1.1:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.line((240, 430, 380, 360, collar_left + 22, 300), fill=(82, 211, 190, 94), width=5, joint="curve")
        gd.line((1040, 430, 900, 360, collar_right - 22, 300), fill=(82, 211, 190, 94), width=5, joint="curve")
        bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(0.8)))
        draw = ImageDraw.Draw(bg, "RGBA")

    draw_arm(draw, (180, 520), left_target, "left", open_grip=0.25 + 0.7 * spread)
    draw_arm(draw, (1110, 520), right_target, "right", open_grip=0.25 + 0.7 * spread)
    bg = draw_hanger(bg, t, collar_left, collar_right)
    draw = ImageDraw.Draw(bg, "RGBA")

    if t > 5.05:
        u = ease((t - 5.05) / 0.8)
        draw.rounded_rectangle((492, 172, 790, 222), radius=20, fill=(239, 250, 244, int(225 * u)), outline=(99, 184, 132, int(220 * u)), width=2)
        draw.text((524, 185), "挂载完成：领口穿入稳定", font=F_LABEL, fill=(52, 142, 90, int(255 * u)))

    # Stage captions.
    captions = {
        "视觉定位": "识别领口区域，确定双臂接近点",
        "动态撑开": "双臂轻柔拉开领口，为衣架留出通道",
        "精准穿戴": "衣架沿规划轨迹穿入领口",
        "挂载完成": "完成挂载并保持衣物稳定",
    }
    draw.rounded_rectangle((50, 548, 572, 604), radius=18, fill=(255, 255, 255, 232), outline=(234, 220, 207, 255))
    draw.text((74, 562), captions[stage], font=F_SUB, fill=(38, 50, 69, 255))
    draw_hud(draw, t, stage, sp)
    return bg.convert("RGB")


def main():
    OUT.mkdir(exist_ok=True)
    FRAME_DIR.mkdir(exist_ok=True)
    KEY_DIR.mkdir(exist_ok=True)
    frames = []
    key_indices = {
        "01_视觉定位.png": int(0.9 * FPS),
        "02_动态撑开.png": int(2.65 * FPS),
        "03_精准穿戴.png": int(4.45 * FPS),
        "04_挂载完成.png": int(5.7 * FPS),
    }
    for i in range(N):
        im = draw_frame(i)
        frames.append(np.asarray(im))
        if i % 16 == 0:
            im.save(FRAME_DIR / f"frame_{i:04d}.png")
        for name, idx in key_indices.items():
            if i == idx:
                im.save(KEY_DIR / name)
    imageio.mimsave(GIF_PATH, frames, fps=FPS, loop=0)
    try:
        imageio.mimsave(MP4_PATH, frames, fps=FPS, quality=8)
    except Exception as exc:
        print(f"MP4 skipped: {exc}")
    print(GIF_PATH.resolve())
    print(MP4_PATH.resolve() if MP4_PATH.exists() else "MP4 not created")
    print(KEY_DIR.resolve())


if __name__ == "__main__":
    main()
