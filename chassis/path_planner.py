"""
全局路径规划 - A* 算法
PPT：全屋自主导航，考虑多地形通行代价
"""

from __future__ import annotations

import heapq
import math
from typing import List, Optional, Tuple

import numpy as np

from .terrain import TerrainMap


class AStarPlanner:
    """
    A* 路径规划
    f(n) = g(n) + h(n),  h 为欧几里得启发式
    边代价融合地形权重，体现履带越障能力差异
    """

    def __init__(self, terrain: TerrainMap):
        self.terrain = terrain
        # 8 邻域
        self.neighbors = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        ]

    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def plan(
        self,
        start_world: Tuple[float, float],
        goal_world: Tuple[float, float],
    ) -> Optional[List[Tuple[float, float]]]:
        """返回世界坐标路径点列表，失败返回 None"""
        sx = int(start_world[0] / self.terrain.resolution)
        sy = int(start_world[1] / self.terrain.resolution)
        gx = int(goal_world[0] / self.terrain.resolution)
        gy = int(goal_world[1] / self.terrain.resolution)

        if not self.terrain.is_traversable(gx, gy):
            # 目标被占时搜索最近可通行格
            for r in range(1, 15):
                for dx in range(-r, r + 1):
                    for dy in range(-r, r + 1):
                        nx, ny = gx + dx, gy + dy
                        if self.terrain.is_traversable(nx, ny):
                            gx, gy = nx, ny
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break

        start, goal = (sx, sy), (gx, gy)
        if not self.terrain.is_traversable(*start):
            return None

        open_set: List[Tuple[float, Tuple[int, int]]] = []
        heapq.heappush(open_set, (0.0, start))
        came_from: dict = {}
        g_score = {start: 0.0}
        f_score = {start: self._heuristic(start, goal)}

        while open_set:
            _, current = heapq.heappop(open_set)
            if current == goal:
                return self._reconstruct_path(came_from, current)

            for dx, dy in self.neighbors:
                neighbor = (current[0] + dx, current[1] + dy)
                nx, ny = neighbor
                if not (0 <= nx < self.terrain.width and 0 <= ny < self.terrain.height):
                    continue
                cost = self.terrain.get_cost(nx, ny)
                if cost == float("inf"):
                    continue
                move_cost = math.hypot(dx, dy) * cost
                tentative = g_score[current] + move_cost
                if tentative < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    f = tentative + self._heuristic(neighbor, goal)
                    f_score[neighbor] = f
                    heapq.heappush(open_set, (f, neighbor))

        return None

    def _reconstruct_path(
        self, came_from: dict, current: Tuple[int, int]
    ) -> List[Tuple[float, float]]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        res = []
        for gx, gy in path:
            x = (gx + 0.5) * self.terrain.resolution
            y = (gy + 0.5) * self.terrain.resolution
            res.append((x, y))
        return self._smooth_path(res)

    def _smooth_path(
        self, path: List[Tuple[float, float]], window: int = 3
    ) -> List[Tuple[float, float]]:
        """路径平滑：移动平均，便于履带跟踪"""
        if len(path) <= 2:
            return path
        arr = np.array(path)
        kernel = np.ones(window) / window
        sx = np.convolve(arr[:, 0], kernel, mode="same")
        sy = np.convolve(arr[:, 1], kernel, mode="same")
        smoothed = list(zip(sx, sy))
        smoothed[0] = path[0]
        smoothed[-1] = path[-1]
        return smoothed
