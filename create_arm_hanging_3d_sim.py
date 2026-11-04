from __future__ import annotations

import math
from pathlib import Path

import imageio.v2 as imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
KEY_DIR = OUT / "arm_hanging_3d_keyframes"
GIF_PATH = OUT / "arm_hanging_3d_sim.gif"
MP4_PATH = OUT / "arm_hanging_3d_sim.mp4"

FPS = 14
DURATION = 6.0
N = int(FPS * DURATION)

BG = "#06111f"
CYAN = "#74f1ff"
CYAN_SOFT = "#8defff"
ORANGE = "#ff9b5a"
BLUE = "#4da3d9"
GREEN = "#63d391"


def setup_font():
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            matplotlib.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=p).get_name()]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return


setup_font()


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def bezier(p0, p1, p2, p3, u):
    p0 = np.array(p0, dtype=float)
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    p3 = np.array(p3, dtype=float)
    return (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u ** 2 * p2 + u ** 3 * p3


def stage(t):
    if t < 1.55:
        return "视觉定位", t / 1.55
    if t < 3.25:
        return "双臂撑开", (t - 1.55) / 1.7
    if t < 5.25:
        return "衣架穿入", (t - 3.25) / 2.0
    return "挂载完成", (t - 5.25) / 0.75


def cylinder_between(ax, p0, p1, r=0.055, color="#d9e4ea", alpha=1.0, res=12):
    p0 = np.array(p0, dtype=float)
    p1 = np.array(p1, dtype=float)
    v = p1 - p0
    length = np.linalg.norm(v)
    if length < 1e-5:
        return
    v = v / length
    not_v = np.array([1, 0, 0], dtype=float)
    if abs(np.dot(v, not_v)) > 0.9:
        not_v = np.array([0, 1, 0], dtype=float)
    n1 = np.cross(v, not_v)
    n1 /= np.linalg.norm(n1)
    n2 = np.cross(v, n1)
    theta = np.linspace(0, 2 * np.pi, res)
    z = np.linspace(0, length, 2)
    theta_grid, z_grid = np.meshgrid(theta, z)
    pts = p0 + z_grid[..., None] * v + r * np.cos(theta_grid[..., None]) * n1 + r * np.sin(theta_grid[..., None]) * n2
    ax.plot_surface(pts[..., 0], pts[..., 1], pts[..., 2], color=color, alpha=alpha, linewidth=0, shade=True)


def sphere(ax, c, r=0.09, color="#e9f3f8", alpha=1.0):
    c = np.array(c, dtype=float)
    u = np.linspace(0, 2 * np.pi, 14)
    v = np.linspace(0, np.pi, 8)
    x = c[0] + r * np.outer(np.cos(u), np.sin(v))
    y = c[1] + r * np.outer(np.sin(u), np.sin(v))
    z = c[2] + r * np.outer(np.ones_like(u), np.cos(v))
    ax.plot_surface(x, y, z, color=color, alpha=alpha, linewidth=0, shade=True)


def arm_points(base, target, side):
    base = np.array(base, dtype=float)
    target = np.array(target, dtype=float)
    mid = (base + target) / 2
    out = np.array([-0.22, -0.34, 0.38]) if side == "left" else np.array([0.22, -0.34, 0.38])
    dist = np.linalg.norm(target - base)
    lift = max(0.25, 0.9 - dist * 0.08)
    elbow = mid + out + np.array([0, 0, lift])
    return base, elbow, target


def draw_arm(ax, base, target, side, grip_open):
    base, elbow, end = arm_points(base, target, side)
    cylinder_between(ax, base, elbow, 0.055, "#7d9ab0")
    cylinder_between(ax, elbow, end, 0.047, "#cbdbe4")
    cylinder_between(ax, base + np.array([0, 0.006, 0.006]), elbow + np.array([0, 0.006, 0.006]), 0.025, "#eff8fb")
    cylinder_between(ax, elbow + np.array([0, 0.006, 0.006]), end + np.array([0, 0.006, 0.006]), 0.022, "#f6fbfd")
    for c, rr in [(base, 0.12), (elbow, 0.105), (end, 0.08)]:
        sphere(ax, c, rr, "#dff2fb")
        sphere(ax, c, rr * 0.55, BLUE, 0.55)

    # Two gripper fingers.
    direction = np.array([0.34 if side == "left" else -0.34, 0.04, -0.05])
    direction = direction / np.linalg.norm(direction)
    spread = lerp(0.05, 0.18, grip_open)
    for sgn in [-1, 1]:
        offset = np.array([0, sgn * spread, 0.03 * sgn])
        cylinder_between(ax, end + offset, end + offset + direction * 0.34, 0.018, "#eef7fb")
        sphere(ax, end + offset + direction * 0.34, 0.035, "#eef7fb")


def draw_shirt(ax, spread):
    collar_width = lerp(0.8, 1.62, spread)
    # Curved translucent shirt surface.
    z = np.linspace(0.0, 2.45, 38)
    u = np.linspace(-1.0, 1.0, 34)
    U, Z = np.meshgrid(u, z)
    width = 1.12 + 0.48 * np.exp(-((Z - 1.65) / 0.65) ** 2) + 0.18 * (1 - Z / 2.45)
    X = U * width
    Y = 0.08 * np.cos(U * np.pi) - 0.05 * np.sin(Z * 3.2)
    ax.plot_surface(X, Y, Z, color="#6bb7e2", alpha=0.20, linewidth=0, shade=True)
    ax.plot_wireframe(X, Y, Z, rstride=3, cstride=3, color="#bdf7ff", alpha=0.24, linewidth=0.45)

    # Sleeves / shoulders.
    ax.plot([-1.38, -2.02, -1.63], [0.03, 0.00, -0.02], [1.86, 1.28, 0.22], color="#8eeeff", alpha=0.45, linewidth=1.8)
    ax.plot([1.38, 2.02, 1.63], [0.03, 0.00, -0.02], [1.86, 1.28, 0.22], color="#8eeeff", alpha=0.45, linewidth=1.8)

    # Collar opening.
    left = np.array([-collar_width / 2, -0.08, 2.25])
    right = np.array([collar_width / 2, -0.08, 2.25])
    center = np.array([0, -0.08, 2.0])
    collar = np.array([left, [-collar_width * 0.25, -0.06, 2.36], center, [collar_width * 0.25, -0.06, 2.36], right])
    ax.plot(collar[:, 0], collar[:, 1], collar[:, 2], color=CYAN, linewidth=3.2, alpha=0.98)
    ax.plot(collar[:, 0], collar[:, 1], collar[:, 2] + 0.012, color="#ffffff", linewidth=1.0, alpha=0.72)
    return left, right, center, collar_width


def draw_scan_box(ax, collar_width, alpha):
    if alpha <= 0:
        return
    x0, x1 = -collar_width / 2 - 0.32, collar_width / 2 + 0.32
    z0, z1 = 1.93, 2.48
    y = -0.16
    pts = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1), (x0, y, z0)]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts], color=GREEN, alpha=alpha, linewidth=2.4)
    ax.scatter([0], [y], [2.21], marker="+", s=120, color=GREEN, alpha=alpha)


def draw_hanger(ax, t, center):
    if t < 3.25:
        return None
    u = ease((t - 3.25) / 2.0)
    start = np.array([2.45, -1.05, 1.74])
    pos = bezier(start, np.array([1.55, -0.95, 2.22]), np.array([0.75, -0.44, 2.25]), center + np.array([0, -0.06, 0.16]), u)
    scale = lerp(0.82, 1.0, u)
    # Motion trail.
    trail = np.array([bezier(start, np.array([1.55, -0.95, 2.22]), np.array([0.75, -0.44, 2.25]), center + np.array([0, -0.06, 0.16]), q) for q in np.linspace(0, u, 28)])
    if len(trail) > 1:
        ax.plot(trail[:, 0], trail[:, 1], trail[:, 2], color=CYAN, linewidth=3.0, alpha=0.45)

    left = pos + np.array([-0.72 * scale, 0, -0.36 * scale])
    right = pos + np.array([0.72 * scale, 0, -0.36 * scale])
    top = pos + np.array([0, 0, 0.22 * scale])
    cylinder_between(ax, top, left, 0.022, "#f4f9fb")
    cylinder_between(ax, top, right, 0.022, "#f4f9fb")
    cylinder_between(ax, left, right, 0.018, "#f4f9fb")
    # Hook curve.
    theta = np.linspace(-0.15 * np.pi, 1.25 * np.pi, 34)
    hook = np.column_stack([
        pos[0] + 0.12 * np.cos(theta),
        pos[1] + np.zeros_like(theta),
        pos[2] + 0.42 * scale + 0.18 * np.sin(theta),
    ])
    ax.plot(hook[:, 0], hook[:, 1], hook[:, 2], color="#f4f9fb", linewidth=3.2)
    return pos


def draw_floor(ax):
    xs = np.linspace(-3.4, 3.4, 9)
    ys = np.linspace(-1.8, 1.0, 7)
    for x in xs:
        ax.plot([x, x], [ys[0], ys[-1]], [-0.02, -0.02], color="#20435c", alpha=0.45, linewidth=0.7)
    for y in ys:
        ax.plot([xs[0], xs[-1]], [y, y], [-0.02, -0.02], color="#20435c", alpha=0.45, linewidth=0.7)


def render_frame(i):
    t = i / FPS
    st, sp = stage(t)
    spread = ease((t - 1.55) / 1.7)
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    fig.patch.set_facecolor(BG)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor(BG)
    ax.view_init(elev=18, azim=-69)
    ax.set_xlim(-3.4, 3.4)
    ax.set_ylim(-1.8, 1.05)
    ax.set_zlim(-0.05, 3.1)
    ax.set_box_aspect((6.8, 2.85, 3.15))
    ax.set_axis_off()
    for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
        axis.pane.set_facecolor((0.02, 0.06, 0.11, 0.0))
        axis.pane.set_edgecolor((0.2, 0.5, 0.65, 0.0))

    draw_floor(ax)
    left, right, center, collar_width = draw_shirt(ax, spread)
    draw_scan_box(ax, collar_width, max(0.0, 1.0 - max(0, t - 1.6) / 0.9))

    approach = ease((t - 0.7) / 1.25)
    left_start = np.array([-2.75, -1.05, 1.18])
    right_start = np.array([2.75, -1.05, 1.18])
    # Left arm: clamp the collar and hold it open.
    left_clamp = left + np.array([0.04, -0.08, 0.02])
    left_target = left_start * (1 - approach) + left_clamp * approach

    # Right arm: carry the hanger, then guide it through the opened collar.
    hanger_pre = np.array([2.45, -1.05, 1.74])
    if t < 3.25:
        right_goal = hanger_pre
    else:
        hu = ease((t - 3.25) / 2.0)
        right_goal = bezier(
            hanger_pre + np.array([0.18, -0.02, -0.04]),
            np.array([1.70, -1.00, 2.15]),
            np.array([0.92, -0.54, 2.20]),
            center + np.array([0.26, -0.12, 0.18]),
            hu,
        )
    right_target = right_start * (1 - approach) + right_goal * approach

    draw_arm(ax, (-3.15, -1.2, 0.82), left_target, "left", 0.08 + 0.15 * spread)
    draw_arm(ax, (3.15, -1.2, 0.82), right_target, "right", 0.18 + 0.55 * min(1, max(0, (t - 1.3) / 1.2)))
    hanger_pos = draw_hanger(ax, t, center)
    if hanger_pos is not None:
        # Small link between the right gripper and hanger hook to make it clear the arm is holding the hanger.
        ax.plot(
            [right_target[0], hanger_pos[0] + 0.10],
            [right_target[1], hanger_pos[1]],
            [right_target[2], hanger_pos[2] + 0.32],
            color="#f4f9fb",
            linewidth=2.4,
            alpha=0.9,
        )

    # Text overlay.
    fig.text(0.055, 0.91, "衣循机械臂挂衣 3D 仿真", color="#eaf8ff", fontsize=24, weight="bold")
    fig.text(0.055, 0.865, "视觉定位 → 双臂撑开 → 衣架穿入 → 挂载完成", color="#a7bed1", fontsize=14)
    fig.text(0.76, 0.89, f"T+{t:0.1f}s  {st}", color=ORANGE, fontsize=20, weight="bold",
             bbox=dict(boxstyle="round,pad=0.45,rounding_size=0.6", fc="#0e2233", ec="#315c78", alpha=0.92))
    fig.text(0.06, 0.08, {
        "视觉定位": "识别领口目标点，确定双臂接近位置",
        "双臂撑开": "两侧夹爪轻柔撑开领口，扩大衣架进入通道",
        "衣架穿入": "衣架沿规划轨迹穿入领口，避免拉扯衣物",
        "挂载完成": "衣架进入稳定位置，衣物保持挂载姿态",
    }[st], color="#eaf8ff", fontsize=17,
             bbox=dict(boxstyle="round,pad=0.55,rounding_size=0.35", fc="#0e2233", ec="#315c78", alpha=0.86))
    if st == "挂载完成":
        fig.text(0.43, 0.78, "挂载完成", color="#dffbea", fontsize=23, weight="bold",
                 bbox=dict(boxstyle="round,pad=0.45,rounding_size=0.5", fc="#0f3a2b", ec="#63d391", alpha=0.92))

    fig.canvas.draw()
    arr = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
    plt.close(fig)
    return arr


def main():
    OUT.mkdir(exist_ok=True)
    KEY_DIR.mkdir(exist_ok=True)
    frames = []
    key_indices = {
        "01_视觉定位_3d.png": int(1.0 * FPS),
        "02_双臂撑开_3d.png": int(2.7 * FPS),
        "03_衣架穿入_3d.png": int(4.45 * FPS),
        "04_挂载完成_3d.png": int(5.75 * FPS),
    }
    for i in range(N):
        arr = render_frame(i)
        frames.append(arr)
        for name, idx in key_indices.items():
            if i == idx:
                imageio.imwrite(KEY_DIR / name, arr)
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
