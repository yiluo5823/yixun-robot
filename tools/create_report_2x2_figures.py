from __future__ import annotations

from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
FIG_DIR = OUT / "report_figures_2x2"

W, H = 1600, 1120
BG = "#fffaf2"
PANEL = "#ffffff"
INK = "#243044"
MUTED = "#66717e"
LINE = "#e8d8c7"
ORANGE = "#e87532"
BLUE = "#3371a5"
GREEN = "#58a66f"
CYAN = "#56bfc5"


def font(size: int, bold: bool = False):
    paths = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


F_TITLE = font(52, True)
F_LABEL = font(28, True)
F_NOTE = font(20)
F_MAP = font(18, True)
F_SMALL = font(15)


def cover_crop(im: Image.Image, box_w: int, box_h: int):
    ratio = max(box_w / im.width, box_h / im.height)
    size = (int(im.width * ratio), int(im.height * ratio))
    im = im.resize(size, Image.Resampling.LANCZOS)
    left = (im.width - box_w) // 2
    top = (im.height - box_h) // 2
    return im.crop((left, top, left + box_w, top + box_h))


def make_storyboard(title: str, paths: list[Path], labels: list[str], output: Path):
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    d.text((64, 38), title, font=F_TITLE, fill=INK)
    x0, y0 = 62, 135
    gap_x, gap_y = 30, 28
    card_w = (W - x0 * 2 - gap_x) // 2
    card_h = 440
    image_h = 342
    for i, (path, label) in enumerate(zip(paths, labels)):
        row, col = divmod(i, 2)
        x = x0 + col * (card_w + gap_x)
        y = y0 + row * (card_h + gap_y)
        d.rounded_rectangle((x, y, x + card_w, y + card_h), radius=25,
                            fill=PANEL, outline=LINE, width=3)
        im = Image.open(path).convert("RGB")
        im = cover_crop(im, card_w - 28, image_h - 18)
        canvas.paste(im, (x + 14, y + 14))
        d.text((x + 24, y + image_h + 28), label, font=F_LABEL, fill=ORANGE)
    canvas.save(output, quality=94)


def map_xy(x, y, box):
    bx0, by0, bx1, by1 = box
    return (
        bx0 + x / 8.0 * (bx1 - bx0),
        by1 - y / 6.0 * (by1 - by0),
    )


def draw_house_map(d: ImageDraw.ImageDraw, box, explored_ratio, path_fraction, stage_idx):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=18, fill="#f7faf7", outline="#9db1aa", width=2)

    # Progressive explored field: pale cells become visible from the start point outward.
    cols, rows = 24, 18
    for gy in range(rows):
        for gx in range(cols):
            cx = (gx + .5) / cols * 8
            cy = (gy + .5) / rows * 6
            dist = math.hypot(cx - 1.0, cy - 1.0)
            threshold = explored_ratio * 9.0
            if dist <= threshold + 0.35 * math.sin(gx * 1.4 + gy):
                px0 = x0 + gx / cols * (x1 - x0)
                py0 = y0 + gy / rows * (y1 - y0)
                px1 = x0 + (gx + 1) / cols * (x1 - x0)
                py1 = y0 + (gy + 1) / rows * (y1 - y0)
                alpha_color = "#e6f2e8" if (gx + gy) % 2 else "#edf6ef"
                d.rectangle((px0, py0, px1 + 1, py1 + 1), fill=alpha_color)

    # Walls and terrain.
    walls = [
        ((0.1, 0.1), (7.9, 0.1)), ((0.1, 0.1), (0.1, 5.9)),
        ((0.1, 5.9), (7.9, 5.9)), ((7.9, 0.1), (7.9, 5.9)),
        ((3.6, 2.0), (3.6, 5.9)),
    ]
    for a, b in walls:
        d.line((*map_xy(*a, box), *map_xy(*b, box)), fill="#55585c", width=8)
    # doorway break in middle wall
    p1 = map_xy(3.6, 3.0, box)
    p2 = map_xy(3.6, 4.0, box)
    d.line((*p1, *p2), fill="#f2b27d", width=9)
    # obstacle, carpet and balcony rail.
    a = map_xy(1.0, 4.8, box); b = map_xy(2.2, 3.6, box)
    d.rectangle((a[0], a[1], b[0], b[1]), fill="#777777")
    a = map_xy(4.1, 2.6, box); b = map_xy(6.5, 0.15, box)
    d.rectangle((a[0], a[1], b[0], b[1]), fill="#dfcaa6")
    a = map_xy(6.5, 5.0, box); b = map_xy(7.9, 4.7, box)
    d.rectangle((a[0], a[1], b[0], b[1]), fill="#e9aa79")

    nodes = [
        (1.0, 1.0, "起点"),
        (2.5, 1.25, "脏衣篮"),
        (2.0, 3.0, "洗衣机"),
        (5.5, 4.5, "智能柜"),
        (7.0, 5.2, "阳台"),
    ]
    full_path = [
        (1.0, 1.0), (1.5, 1.25), (2.5, 1.25),
        (2.0, 1.75), (1.7, 2.3), (2.0, 3.0),
        (2.4, 3.4), (3.1, 4.0), (3.7, 4.2),
        (4.5, 4.2), (5.5, 4.5), (6.3, 4.7), (7.0, 5.2),
    ]
    count = max(2, int(1 + path_fraction * (len(full_path) - 1)))
    path = full_path[:count]
    pts = [map_xy(px, py, box) for px, py in path]
    d.line(pts, fill=GREEN, width=6, joint="curve")
    for p in pts[::2]:
        d.ellipse((p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3), fill="#ffffff", outline=GREEN, width=2)

    # Planned remaining path in blue.
    if count < len(full_path):
        remain = [map_xy(px, py, box) for px, py in full_path[count - 1:]]
        d.line(remain, fill=BLUE, width=3, joint="curve")

    for idx, (px, py, name) in enumerate(nodes):
        p = map_xy(px, py, box)
        fill = ORANGE if idx <= stage_idx + 1 else "#b8c1c9"
        d.ellipse((p[0] - 8, p[1] - 8, p[0] + 8, p[1] + 8), fill=fill, outline="#ffffff", width=2)
        d.text((p[0] + 10, p[1] - 12), name, font=F_SMALL, fill=INK)

    robot = pts[-1]
    d.ellipse((robot[0] - 14, robot[1] - 14, robot[0] + 14, robot[1] + 14),
              fill="#2e86ab", outline="#ffffff", width=4)
    d.text((x0 + 14, y0 + 12), f"探索覆盖 {int(explored_ratio * 100)}%", font=F_MAP, fill=BLUE)


def make_exploration_figure(output: Path):
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    d.text((64, 38), "家庭任务流转与底盘探索路径", font=F_TITLE, fill=INK)
    stages = [
        ("起点建图", 0.20, 0.10),
        ("探索扩张", 0.47, 0.38),
        ("跨区导航", 0.72, 0.70),
        ("路径闭环", 0.87, 1.00),
    ]
    x0, y0 = 62, 135
    gap_x, gap_y = 30, 28
    card_w = (W - x0 * 2 - gap_x) // 2
    card_h = 440
    for i, (label, explored, fraction) in enumerate(stages):
        row, col = divmod(i, 2)
        x = x0 + col * (card_w + gap_x)
        y = y0 + row * (card_h + gap_y)
        d.rounded_rectangle((x, y, x + card_w, y + card_h), radius=25,
                            fill=PANEL, outline=LINE, width=3)
        draw_house_map(d, (x + 20, y + 20, x + card_w - 20, y + 350),
                       explored, fraction, i)
        d.text((x + 24, y + 374), label, font=F_LABEL, fill=ORANGE)
        notes = [
            "机器人从洗衣区起点启动，建立局部占用栅格。",
            "沿左侧生活区巡检，已探索区域持续向外扩张。",
            "穿过门口进入右侧区域，执行跨房间路径规划。",
            "依次连接脏衣篮、洗衣机、智能柜和阳台目标点。",
        ]
        d.text((x + 24, y + 414), notes[i], font=F_NOTE, fill=MUTED)
    canvas.save(output, quality=94)


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    make_exploration_figure(FIG_DIR / "01_底盘探索路径_2x2.png")
    make_storyboard(
        "单臂夹领、单臂持架的协同挂载过程",
        [
            OUT / "arm_hanging_3d_keyframes" / "01_视觉定位_3d.png",
            OUT / "arm_hanging_3d_keyframes" / "02_双臂撑开_3d.png",
            OUT / "arm_hanging_3d_keyframes" / "03_衣架穿入_3d.png",
            OUT / "arm_hanging_3d_keyframes" / "04_挂载完成_3d.png",
        ],
        ["视觉定位", "夹领准备", "衣架穿入", "挂载完成"],
        FIG_DIR / "02_机械臂协同挂载_2x2.png",
    )
    make_storyboard(
        "伞状晾衣杆整杆入柜过程",
        [
            OUT / "wardrobe_storage_keyframes" / "01_旋转存衣仓.png",
            OUT / "wardrobe_storage_keyframes" / "02_伸缩挂杆.png",
            OUT / "wardrobe_storage_keyframes" / "03_整杆对接.png",
            OUT / "wardrobe_storage_keyframes" / "04_收纳完成.png",
        ],
        ["仓位旋转", "挂杆伸出", "整杆对接", "回转入柜"],
        FIG_DIR / "03_衣柜整杆入柜_2x2.png",
    )
    for p in sorted(FIG_DIR.glob("*.png")):
        print(p.resolve())


if __name__ == "__main__":
    main()
