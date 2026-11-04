"""
多地形代价地图
PPT：跨越门槛、地毯、阳台滑轨等家庭复杂地形
"""

from __future__ import annotations

from enum import IntEnum
from typing import Tuple

import numpy as np


class TerrainType(IntEnum):
    FREE = 0          # 普通地面
    OBSTACLE = 1      # 墙体/家具
    CARPET = 2        # 地毯（减速）
    THRESHOLD = 3     # 门槛（摆臂越障，高代价可通行）
    BALCONY_RAIL = 4  # 阳台滑轨（定向通行）


# 通行代价：越大越难通过，inf 表示不可通行
TERRAIN_COST = {
    TerrainType.FREE: 1.0,
    TerrainType.CARPET: 2.5,
    TerrainType.THRESHOLD: 4.0,      # 履带摆臂可越障
    TerrainType.BALCONY_RAIL: 3.0,
    TerrainType.OBSTACLE: float("inf"),
}

TERRAIN_COLORS = {
    TerrainType.FREE: "#E8F4E8",
    TerrainType.OBSTACLE: "#4A4A4A",
    TerrainType.CARPET: "#C9A86C",
    TerrainType.THRESHOLD: "#E07B39",
    TerrainType.BALCONY_RAIL: "#5B9BD5",
}


class TerrainMap:
    """室内家庭环境栅格地图"""

    def __init__(self, width_m: float = 8.0, height_m: float = 6.0, resolution: float = 0.1):
        self.resolution = resolution
        self.width_m = width_m
        self.height_m = height_m
        self.width = int(width_m / resolution)
        self.height = int(height_m / resolution)
        self.grid = np.zeros((self.height, self.width), dtype=np.int8)
        self._build_default_home_layout()

    def _world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        gx = int(np.clip(x / self.resolution, 0, self.width - 1))
        gy = int(np.clip(y / self.resolution, 0, self.height - 1))
        return gx, gy

    def _grid_to_world(self, gx: int, gy: int) -> Tuple[float, float]:
        return (gx + 0.5) * self.resolution, (gy + 0.5) * self.resolution

    def set_region(self, x0: float, y0: float, x1: float, y1: float, terrain: TerrainType) -> None:
        gx0, gy0 = self._world_to_grid(x0, y0)
        gx1, gy1 = self._world_to_grid(x1, y1)
        self.grid[gy0 : gy1 + 1, gx0 : gx1 + 1] = int(terrain)

    def _build_default_home_layout(self) -> None:
        """模拟典型户型：客厅、卧室通道、阳台、门槛、地毯区"""
        # 外墙障碍
        self.set_region(0, 0, 8.0, 0.15, TerrainType.OBSTACLE)
        self.set_region(0, 5.85, 8.0, 6.0, TerrainType.OBSTACLE)
        self.set_region(0, 0, 0.15, 6.0, TerrainType.OBSTACLE)
        self.set_region(7.85, 0, 8.0, 6.0, TerrainType.OBSTACLE)

        # 内墙 / 家具
        self.set_region(3.5, 2.0, 3.65, 6.0, TerrainType.OBSTACLE)   # 隔断墙
        self.set_region(1.0, 3.5, 2.2, 4.8, TerrainType.OBSTACLE)     # 沙发
        self.set_region(5.0, 1.0, 6.2, 2.0, TerrainType.OBSTACLE)     # 柜子

        # 门槛（卧室入口、阳台门）
        self.set_region(3.5, 4.2, 3.65, 4.5, TerrainType.THRESHOLD)
        self.set_region(6.5, 4.8, 7.85, 4.95, TerrainType.THRESHOLD)

        # 地毯
        self.set_region(4.0, 0.3, 6.5, 2.5, TerrainType.CARPET)

        # 阳台滑轨区域
        self.set_region(6.8, 5.0, 7.7, 5.7, TerrainType.BALCONY_RAIL)

    def get_cost(self, gx: int, gy: int) -> float:
        if 0 <= gx < self.width and 0 <= gy < self.height:
            t = TerrainType(self.grid[gy, gx])
            return TERRAIN_COST[t]
        return float("inf")

    def is_traversable(self, gx: int, gy: int) -> bool:
        return self.get_cost(gx, gy) < float("inf")

    def get_landmarks(self) -> dict:
        """语音导航语义地标（脏衣篮、洗衣机、阳台晾晒位）"""
        return {
            "起点": (1.0, 1.0),
            "脏衣篮": (2.5, 1.2),
            "洗衣机": (2.0, 3.0),
            "阳台": (7.0, 5.2),
            "智能柜": (5.5, 4.5),
        }
