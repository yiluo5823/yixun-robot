#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
衣循机器人底盘功能仿真
生成演示视频，展示：SLAM建图、A*规划、DWA避障、多地形越障、语音导航、趋光追踪

运行: python simulate_chassis.py
输出: output/chassis_demo.mp4, output/chassis_demo.gif, output/algorithm_snapshots/
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import animation
import numpy as np

# 项目根目录加入路径
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from chassis.robot import TrackedChassis, Pose2D
from chassis.terrain import TerrainMap, TerrainType, TERRAIN_COLORS
from chassis.slam import OccupancyGridSLAM
from chassis.path_planner import AStarPlanner
from chassis.obstacle_avoidance import DynamicWindowAvoidance, Obstacle
from chassis.phototropism import PhototropismTracker
from chassis.voice_nav import VoiceCommandNavigator

# 中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUTPUT_DIR = os.path.join(ROOT, "output")


@dataclass
class SimState:
    phase: str = "init"
    phase_label: str = ""
    path: List[Tuple[float, float]] = field(default_factory=list)
    path_idx: int = 0
    obstacles: List[Obstacle] = field(default_factory=list)
    trail: List[Tuple[float, float]] = field(default_factory=list)
    voice_text: str = ""
    sun_hour: float = 10.0
    phototrop_target: Optional[Tuple[float, float]] = None
    phototrop_smooth: Optional[Tuple[float, float]] = None
    phototrop_scan_path: List[Tuple[float, float]] = field(default_factory=list)
    phototrop_scan_idx: int = 0
    phototrop_elapsed: int = 0
    phototrop_done: bool = False
    frame: int = 0
    task_idx: int = 0


class ChassisSimulator:
    """全流程仿真编排"""

    DT = 0.08
    MAX_FRAMES = 520
    PHOTOTROP_DURATION = 160  # 趋光扫描阶段仿真帧数

    def __init__(self):
        self.terrain = TerrainMap()
        self.chassis = TrackedChassis()
        self.slam = OccupancyGridSLAM(self.terrain)
        self.planner = AStarPlanner(self.terrain)
        self.dwa = DynamicWindowAvoidance(self.chassis)
        self.photo = PhototropismTracker(balcony_bounds=(6.5, 4.8, 7.8, 5.8))
        self.voice = VoiceCommandNavigator(self.terrain)
        self.state = SimState()
        self.tasks = self.voice.parse_workflow()
        self._setup_figure()

    def _setup_figure(self):
        self.fig, self.axes = plt.subplots(1, 2, figsize=(12, 5))
        self.ax_map = self.axes[0]
        self.ax_photo = self.axes[1]
        self.fig.subplots_adjust(wspace=0.25)

    def _draw_terrain(self, ax):
        from matplotlib.colors import ListedColormap
        cmap_list = [
            TERRAIN_COLORS[TerrainType.FREE],
            TERRAIN_COLORS[TerrainType.OBSTACLE],
            TERRAIN_COLORS[TerrainType.CARPET],
            TERRAIN_COLORS[TerrainType.THRESHOLD],
            TERRAIN_COLORS[TerrainType.BALCONY_RAIL],
        ]
        cmap = ListedColormap(cmap_list)
        ax.imshow(
            self.terrain.grid,
            origin="lower",
            extent=[0, self.terrain.width_m, 0, self.terrain.height_m],
            cmap=cmap,
            vmin=0,
            vmax=4,
            alpha=0.85,
        )

    def _init_plot(self):
        self.ax_map.clear()
        self.ax_photo.clear()
        self._draw_terrain(self.ax_map)

        # SLAM 图层
        prob = self.slam.get_probability_map()
        self.slam_overlay = self.ax_map.imshow(
            prob,
            origin="lower",
            extent=[0, self.terrain.width_m, 0, self.terrain.height_m],
            cmap="Greys",
            alpha=0.35,
            vmin=0,
            vmax=1,
        )

        # 地标
        for name, (lx, ly) in self.terrain.get_landmarks().items():
            self.ax_map.plot(lx, ly, "r*", markersize=10)
            self.ax_map.annotate(name, (lx, ly), fontsize=8, color="darkred")

        # 路径
        self.path_line, = self.ax_map.plot([], [], "b-", linewidth=2, label="A*路径")
        self.trail_line, = self.ax_map.plot([], [], "g-", linewidth=1, alpha=0.6, label="轨迹")
        self.robot_dot, = self.ax_map.plot([], [], "o", color="#2E86AB",
                                            markersize=14, markeredgecolor="white",
                                            markeredgewidth=2, label="履带底盘")
        self.heading_line, = self.ax_map.plot([], [], "w-", linewidth=2)

        # 动态障碍
        self.obs_patches = []
        for _ in self.state.obstacles:
            p = plt.Circle((0, 0), 0.25, color="red", alpha=0.5)
            self.ax_map.add_patch(p)
            self.obs_patches.append(p)

        self.ax_map.set_xlim(0, self.terrain.width_m)
        self.ax_map.set_ylim(0, self.terrain.height_m)
        self.ax_map.set_aspect("equal")
        self.ax_map.set_title("SLAM建图 + 路径规划 + 动态避障 + 多地形越障")
        self.ax_map.legend(loc="upper left", fontsize=7)

        # 趋光子图
        sun = self.photo.sun_at_hour(self.state.sun_hour)
        X, Y, Z = self.photo.build_irradiance_map(sun)
        self.photo_im = self.ax_photo.imshow(
            Z, origin="lower",
            extent=[X.min(), X.max(), Y.min(), Y.max()],
            cmap="YlOrRd", aspect="auto",
        )
        self.opt_marker, = self.ax_photo.plot([], [], "c*", markersize=15, label="最优日照点")
        self.robot_photo, = self.ax_photo.plot([], [], "bo", markersize=8, label="机器人")
        self.ax_photo.set_title(f"趋光追踪 (t={self.state.sun_hour:.1f}h)")
        self.ax_photo.legend(fontsize=7)

        self.title_text = self.fig.suptitle("", fontsize=12, fontweight="bold")
        self.voice_text = self.fig.text(
            0.5, 0.02, "", ha="center", fontsize=10,
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9),
        )

    def _update_robot_visual(self):
        p = self.chassis.pose
        self.robot_dot.set_data([p.x], [p.y])
        hx = [p.x, p.x + 0.4 * math.cos(p.theta)]
        hy = [p.y, p.y + 0.4 * math.sin(p.theta)]
        self.heading_line.set_data(hx, hy)

    def _build_balcony_scan_path(self) -> List[Tuple[float, float]]:
        """阳台区域内之字形扫描路径，用于演示趋光搜索过程"""
        x0, y0, x1, y1 = self.photo.bounds
        margin = 0.18
        pts: List[Tuple[float, float]] = []
        y = y0 + margin
        left_to_right = True
        while y <= y1 - margin:
            if left_to_right:
                pts.append((x0 + margin, y))
                pts.append((x1 - margin, y))
            else:
                pts.append((x1 - margin, y))
                pts.append((x0 + margin, y))
            y += 0.24
            left_to_right = not left_to_right
        return pts

    def _nearest_scan_index(self, path: List[Tuple[float, float]]) -> int:
        p = self.chassis.pose
        best_i, best_d = 0, float("inf")
        for i, (px, py) in enumerate(path):
            d = math.hypot(p.x - px, p.y - py)
            if d < best_d:
                best_d, best_i = d, i
        return best_i

    def _enter_phototrop_phase(self):
        """到达阳台后进入趋光阶段，保持当前位姿，沿扫描路径逐步搜索"""
        s = self.state
        if s.phase == "phototrop":
            return
        s.phase = "phototrop"
        s.phase_label = "阶段5: 趋光追踪 — 阳台扫描寻找最佳日照位"
        s.voice_text = "根据太阳入射角，小范围移动寻找最佳日照位"
        s.path = []
        s.path_idx = 0
        s.phototrop_elapsed = 0
        s.phototrop_done = False
        s.phototrop_smooth = None
        s.phototrop_scan_path = self._build_balcony_scan_path()
        s.phototrop_scan_idx = self._nearest_scan_index(s.phototrop_scan_path)

    def _start_navigation_task(self, task_idx: int):
        if task_idx >= len(self.tasks):
            return
        task = self.tasks[task_idx]
        self.state.task_idx = task_idx
        self.state.voice_text = f"[语音] \"{task.command}\" -> {task.description}"
        start = (self.chassis.pose.x, self.chassis.pose.y)
        path = self.planner.plan(start, task.goal_xy)
        if path:
            self.state.path = path
            self.state.path_idx = 0
            self.state.phase = "navigate"
            self.state.phase_label = f"阶段2-4: 语音导航 → {task.goal_name} (A* + DWA)"
        else:
            self.state.path = [task.goal_xy]
            self.state.phase = "navigate"

    def _animate_frame(self, frame: int):
        self.state.frame = frame
        s = self.state

        # 阶段切换逻辑
        if frame == 0:
            self.chassis.set_pose(1.0, 1.0, 0.0)
            s.phase = "slam"
            s.phase_label = "阶段1: SLAM自主巡检建图"
            s.voice_text = "机器人启动，开始激光SLAM扫描建图..."

        elif frame == 80:
            s.phase = "voice"
            s.phase_label = "阶段2: 语音指令驱动导航"
            s.voice_text = "收到语音: \"去脏衣篮收衣服\""
            self._start_navigation_task(0)

        elif frame == 100 and s.task_idx == 0:
            self._start_navigation_task(1)

        elif frame == 160 and s.task_idx == 1:
            # 添加动态障碍
            s.obstacles = [
                Obstacle(4.5, 2.5, 0.3, -0.15, 0.05),
                Obstacle(5.8, 3.8, 0.25, 0.08, -0.1),
            ]
            s.phase_label = "阶段3: 动态避障 (DWA) — 穿越地毯/门槛"
            self._start_navigation_task(2)

        elif frame == 300 and s.task_idx >= 2 and not s.phototrop_done and s.phase != "phototrop":
            # 兜底：完成阳台导航后若未进入趋光，强制开始扫描
            self._enter_phototrop_phase()

        elif frame == 460 and s.phototrop_done and s.task_idx < 3:
            # 兜底：趋光结束后补发智能柜任务
            self._start_navigation_task(3)

        # 物理更新
        if s.phase == "slam":
            # 探索式移动
            v, w = 0.25, 0.35
            self.chassis.update(v, w, self.DT)
            readings = self.slam.scan(self.chassis.pose)
            self.slam.update(self.chassis.pose, readings)

        elif s.phase in ("navigate", "voice"):
            if s.path:
                goal = s.path[-1]
                if s.obstacles:
                    v, w = self.dwa.compute(goal, s.obstacles, self.DT)
                else:
                    v, w = self.dwa.follow_path(s.path[s.path_idx :])
                self.chassis.update(v, w, self.DT)
                readings = self.slam.scan(self.chassis.pose, num_rays=18)
                self.slam.update(self.chassis.pose, readings)

                # 路径点推进
                p = self.chassis.pose
                if s.path_idx < len(s.path) - 1:
                    tx, ty = s.path[s.path_idx]
                    if math.hypot(p.x - tx, p.y - ty) < 0.2:
                        s.path_idx += 1
                if math.hypot(p.x - goal[0], p.y - goal[1]) < 0.25:
                    finished_task = s.task_idx
                    s.path = []
                    s.path_idx = 0
                    if finished_task == 2 and not s.phototrop_done:
                        self._enter_phototrop_phase()
                    elif finished_task < 2:
                        self._start_navigation_task(finished_task + 1)

        elif s.phase == "phototrop":
            s.phototrop_elapsed += 1
            progress = min(1.0, s.phototrop_elapsed / self.PHOTOTROP_DURATION)
            s.sun_hour = 8.0 + progress * 8.0  # 8h -> 16h，与扫描进度同步
            sun = self.photo.sun_at_hour(s.sun_hour)
            opt_x, opt_y, _ = self.photo.find_optimal_position(
                sun, (self.chassis.pose.x, self.chassis.pose.y)
            )
            if s.phototrop_smooth is None:
                s.phototrop_smooth = (opt_x, opt_y)
            else:
                ox, oy = s.phototrop_smooth
                s.phototrop_smooth = (
                    ox + 0.12 * (opt_x - ox),
                    oy + 0.12 * (opt_y - oy),
                )
            s.phototrop_target = s.phototrop_smooth

            scan = s.phototrop_scan_path
            if scan and progress < 0.82:
                v, w = self.dwa.follow_path(scan[s.phototrop_scan_idx :])
                self.chassis.update(v, w, self.DT)
                p = self.chassis.pose
                if s.phototrop_scan_idx < len(scan) - 1:
                    tx, ty = scan[s.phototrop_scan_idx]
                    if math.hypot(p.x - tx, p.y - ty) < 0.18:
                        s.phototrop_scan_idx += 1
            else:
                tx, ty = s.phototrop_smooth
                dx, dy = tx - self.chassis.pose.x, ty - self.chassis.pose.y
                dist = math.hypot(dx, dy)
                if dist > 0.06:
                    target_angle = math.atan2(dy, dx)
                    err = math.atan2(
                        math.sin(target_angle - self.chassis.pose.theta),
                        math.cos(target_angle - self.chassis.pose.theta),
                    )
                    self.chassis.update(min(0.12, dist), 2.0 * err, self.DT)
                else:
                    self.chassis.update(0, 0.05, self.DT)

            if progress >= 1.0 and not s.phototrop_done:
                s.phototrop_done = True
                s.phase = "navigate"
                s.phase_label = "阶段4: 语音导航 → 智能柜收纳"
                self._start_navigation_task(3)

        # 更新动态障碍位置
        for obs in s.obstacles:
            obs.x += obs.vx * self.DT
            obs.y += obs.vy * self.DT

        s.trail.append((self.chassis.pose.x, self.chassis.pose.y))
        if len(s.trail) > 500:
            s.trail = s.trail[-500:]

        # 绘图更新
        self.slam_overlay.set_data(self.slam.get_probability_map())
        if s.path:
            xs, ys = zip(*s.path)
            self.path_line.set_data(xs, ys)
        else:
            self.path_line.set_data([], [])
        if s.trail:
            tx, ty = zip(*s.trail)
            self.trail_line.set_data(tx, ty)
        self._update_robot_visual()

        for i, obs in enumerate(s.obstacles):
            if i < len(self.obs_patches):
                self.obs_patches[i].center = (obs.x, obs.y)

        # 趋光图更新（降频以节省内存）
        sun = self.photo.sun_at_hour(s.sun_hour)
        if s.frame % 8 == 0 or s.phase == "phototrop":
            X, Y, Z = self.photo.build_irradiance_map(sun)
            self._photo_extent = [X.min(), X.max(), Y.min(), Y.max()]
            self._photo_Z = Z
        self.photo_im.set_data(self._photo_Z)
        self.photo_im.set_extent(self._photo_extent)
        p = self.chassis.pose
        self.robot_photo.set_data([p.x], [p.y])
        if s.phototrop_target:
            self.opt_marker.set_data([s.phototrop_target[0]], [s.phototrop_target[1]])
        self.ax_photo.set_title(
            f"趋光追踪 | 太阳高度={sun.elevation_deg:.0f}° 方位={sun.azimuth_deg:.0f}°"
        )

        self.title_text.set_text(
            f"衣循机器人底盘仿真 | {s.phase_label} | 探索率={self.slam.explored_ratio*100:.0f}%"
        )
        self.voice_text.set_text(s.voice_text)

        return []

    def _init_photo_cache(self):
        sun = self.photo.sun_at_hour(10.0)
        X, Y, Z = self.photo.build_irradiance_map(sun)
        self._photo_Z = Z
        self._photo_extent = [X.min(), X.max(), Y.min(), Y.max()]

    def _save_video_incremental(self, out_path: str, fps: int = 15) -> str:
        """逐帧渲染写入 GIF，避免一次性占用大量内存"""
        from PIL import Image
        import io

        frames_pil = []
        step = max(1, self.MAX_FRAMES // 180)  # 约180帧输出，控制体积
        n_out = (self.MAX_FRAMES + step - 1) // step
        print(f"正在仿真 {self.MAX_FRAMES} 帧，输出 {n_out} 帧动画...")

        for f in range(self.MAX_FRAMES):
            self._animate_frame(f)
            if f % step != 0:
                continue
            self.fig.canvas.draw()
            buf = io.BytesIO()
            self.fig.savefig(buf, format="png", dpi=90, bbox_inches="tight", facecolor="white")
            buf.seek(0)
            frames_pil.append(Image.open(buf).convert("P", palette=Image.Palette.ADAPTIVE))

        duration_ms = int(1000 / fps)
        frames_pil[0].save(
            out_path,
            save_all=True,
            append_images=frames_pil[1:],
            duration=duration_ms,
            loop=0,
            optimize=True,
        )
        return out_path

    def run(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self._init_photo_cache()
        self._init_plot()

        gif_path = os.path.join(OUTPUT_DIR, "chassis_demo.gif")
        print("正在渲染仿真动画...")
        self._save_video_incremental(gif_path, fps=12)
        print(f"GIF 已保存: {gif_path}")

        # 尝试用 imageio 转 MP4（若已安装 imageio-ffmpeg）
        mp4_path = os.path.join(OUTPUT_DIR, "chassis_demo.mp4")
        try:
            import imageio.v2 as imageio
            reader = imageio.mimread(gif_path)
            imageio.mimsave(mp4_path, reader, fps=12)
            print(f"MP4 已保存: {mp4_path}")
            out_main = mp4_path
        except Exception:
            out_main = gif_path
            print("提示: 安装 imageio-ffmpeg 可额外生成 MP4")

        snap_dir = os.path.join(OUTPUT_DIR, "algorithm_snapshots")
        os.makedirs(snap_dir, exist_ok=True)
        key_frames = [20, 60, 120, 180, 280, 400]
        for kf in key_frames:
            if kf < self.MAX_FRAMES:
                self._animate_frame(kf)
                snap_path = os.path.join(snap_dir, f"frame_{kf:04d}.png")
                self.fig.savefig(snap_path, dpi=120, bbox_inches="tight")
        print(f"算法截图已保存: {snap_dir}")

        plt.close(self.fig)
        return out_main


def main():
    print("=" * 60)
    print("  衣循机器人 - 底盘移动算法仿真")
    print("  功能: SLAM | A* | DWA | 多地形 | 语音导航 | 趋光追踪")
    print("=" * 60)
    sim = ChassisSimulator()
    out = sim.run()
    print(f"\n完成! 输出目录: {OUTPUT_DIR}")
    print(f"主视频: {out}")


if __name__ == "__main__":
    main()
