"""
趋光追踪算法
PPT：根据太阳入射角，阳台小范围位移寻找最佳日照位
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


@dataclass
class SunState:
    """太阳状态：方位角(度,北=0顺时针)、高度角(度)、时间(小时)"""

    azimuth_deg: float
    elevation_deg: float
    hour: float = 12.0


class PhototropismTracker:
    """
    趋光追踪：在阳台可行区域内搜索光照强度最大的位置

    光照模型:
      I(x,y) = I0 * sin(elevation) * cos(θ_incident)
      θ_incident = angle between surface normal and sun direction

    对于水平晾晒面，近似 I ∝ sin(elevation) * cos(azimuth - wall_azimuth)
    """

    def __init__(
        self,
        balcony_bounds: Tuple[float, float, float, float],
        resolution: float = 0.15,
        wall_azimuth_deg: float = 180.0,
    ):
        """
        balcony_bounds: (x_min, y_min, x_max, y_max) 阳台区域
        wall_azimuth_deg: 阳台朝向（南墙=180°）
        """
        self.bounds = balcony_bounds
        self.resolution = resolution
        self.wall_azimuth = math.radians(wall_azimuth_deg)

    def sun_direction_3d(self, sun: SunState) -> Tuple[float, float, float]:
        """单位太阳方向向量 (东, 北, 上)"""
        az = math.radians(sun.azimuth_deg)
        el = math.radians(sun.elevation_deg)
        # 方位角从北顺时针
        dx = math.cos(el) * math.sin(az)
        dy = math.cos(el) * math.cos(az)
        dz = math.sin(el)
        return dx, dy, dz

    def irradiance_at(self, x: float, y: float, sun: SunState) -> float:
        """
        计算位置 (x,y) 处水平晾晒面辐照度
        考虑阳台遮挡：西侧墙在下午产生阴影
        """
        dx, dy, dz = self.sun_direction_3d(sun)
        if dz <= 0:
            return 0.0

        # 水平面法向量 (0,0,1)，入射角余弦 = dz/|sun|
        cos_incident = dz

        # 朝向阳台外侧墙的方向增益
        wall_x = math.sin(self.wall_azimuth)
        wall_y = math.cos(self.wall_azimuth)
        facing = max(0.0, dx * wall_x + dy * wall_y)

        # 简易遮挡：x<6.8 且太阳在西侧时减光
        shadow = 1.0
        if x < 6.8 and sun.azimuth_deg > 200:
            shadow = 0.4 + 0.6 * (x - 6.0) / 0.8

        return cos_incident * (0.5 + 0.5 * facing) * shadow

    def build_irradiance_map(self, sun: SunState) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """生成阳台区域辐照度热力图数据"""
        x_min, y_min, x_max, y_max = self.bounds
        xs = np.arange(x_min, x_max, self.resolution)
        ys = np.arange(y_min, y_max, self.resolution)
        X, Y = np.meshgrid(xs, ys)
        Z = np.zeros_like(X)
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                Z[i, j] = self.irradiance_at(X[i, j], Y[i, j], sun)
        return X, Y, Z

    def find_optimal_position(
        self, sun: SunState, current: Tuple[float, float]
    ) -> Tuple[float, float, float]:
        """
        梯度上升搜索最佳日照点
        返回 (x*, y*, max_irradiance)
        """
        x, y = current
        x_min, y_min, x_max, y_max = self.bounds
        best_i = self.irradiance_at(x, y, sun)
        best_pos = (x, y)

        step = self.resolution
        for _ in range(30):
            improved = False
            for dx, dy in [
                (step, 0), (-step, 0), (0, step), (0, -step),
                (step, step), (-step, step), (step, -step), (-step, -step),
            ]:
                nx = np.clip(x + dx, x_min, x_max)
                ny = np.clip(y + dy, y_min, y_max)
                ir = self.irradiance_at(nx, ny, sun)
                if ir > best_i:
                    best_i = ir
                    x, y = nx, ny
                    best_pos = (x, y)
                    improved = True
            if not improved:
                break

        return best_pos[0], best_pos[1], best_i

    @staticmethod
    def sun_at_hour(hour: float, day_of_year: int = 172) -> SunState:
        """
        简化太阳位置模型（夏至附近）
        hour: 0-24 本地太阳时近似
        """
        # 高度角：正午最高
        elevation = max(0.0, 75.0 * math.sin(math.pi * (hour - 6.0) / 12.0))
        # 方位角：6点东(90°) -> 12南(180°) -> 18西(270°)
        azimuth = 90.0 + (hour - 6.0) * 15.0
        azimuth = azimuth % 360.0
        return SunState(azimuth_deg=azimuth, elevation_deg=elevation, hour=hour)
