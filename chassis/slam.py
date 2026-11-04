"""
占用栅格 SLAM（简化版）
PPT：SLAM 自主巡检 — 激光雷达扫描 + 贝叶斯占用更新 + 位姿图探索
"""

from __future__ import annotations

import math
from typing import List, Tuple

import numpy as np

from .robot import Pose2D
from .terrain import TerrainMap, TerrainType


class OccupancyGridSLAM:
    """
    2D 占用栅格 SLAM
    log-odds 更新: L(m|z) = L(m|z-1) + log(P(occ)/P(free)) - L0
    """

    L0 = 0.0
    L_OCC = 0.85
    L_FREE = -0.4
    L_MIN, L_MAX = -4.0, 4.0

    def __init__(self, terrain: TerrainMap):
        self.terrain = terrain
        self.log_odds = np.full(
            (terrain.height, terrain.width), self.L0, dtype=np.float32
        )
        self.explored_ratio = 0.0

    def ray_cast(
        self, pose: Pose2D, angle: float, max_range: float = 4.0
    ) -> Tuple[float, bool]:
        """模拟 2D 激光测距，返回 (距离, 是否命中真实障碍)"""
        step = self.terrain.resolution * 0.5
        dist = 0.0
        while dist < max_range:
            x = pose.x + dist * math.cos(pose.theta + angle)
            y = pose.y + dist * math.sin(pose.theta + angle)
            gx = int(x / self.terrain.resolution)
            gy = int(y / self.terrain.resolution)
            if not (0 <= gx < self.terrain.width and 0 <= gy < self.terrain.height):
                return dist, True
            if self.terrain.grid[gy, gx] == TerrainType.OBSTACLE:
                return dist, True
            dist += step
        return max_range, False

    def scan(self, pose: Pose2D, num_rays: int = 36) -> List[Tuple[float, float]]:
        """执行一圈激光扫描，返回 [(angle, range), ...]"""
        readings = []
        for i in range(num_rays):
            angle = -math.pi + (2 * math.pi * i / num_rays)
            r, _ = self.ray_cast(pose, angle)
            readings.append((angle, r))
        return readings

    def _bresenham(self, x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
        cells = []
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            cells.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        return cells

    def update(self, pose: Pose2D, readings: List[Tuple[float, float]]) -> None:
        """根据扫描结果更新占用栅格"""
        gx0 = int(pose.x / self.terrain.resolution)
        gy0 = int(pose.y / self.terrain.resolution)

        for angle, rng in readings:
            gx1 = int((pose.x + rng * math.cos(pose.theta + angle)) / self.terrain.resolution)
            gy1 = int((pose.y + rng * math.sin(pose.theta + angle)) / self.terrain.resolution)
            cells = self._bresenham(gx0, gy0, gx1, gy1)
            for gx, gy in cells[:-1]:
                if 0 <= gx < self.terrain.width and 0 <= gy < self.terrain.height:
                    self.log_odds[gy, gx] = np.clip(
                        self.log_odds[gy, gx] + self.L_FREE, self.L_MIN, self.L_MAX
                    )
            if cells:
                gx, gy = cells[-1]
                if 0 <= gx < self.terrain.width and 0 <= gy < self.terrain.height:
                    self.log_odds[gy, gx] = np.clip(
                        self.log_odds[gy, gx] + self.L_OCC, self.L_MIN, self.L_MAX
                    )

        known = np.sum(np.abs(self.log_odds - self.L0) > 0.3)
        self.explored_ratio = known / self.log_odds.size

    def get_probability_map(self) -> np.ndarray:
        """占用概率 P(occ) = 1 - 1/(1+exp(L))"""
        return 1.0 - 1.0 / (1.0 + np.exp(self.log_odds))
