"""
局部动态避障 - 动态窗口法 (DWA)
PPT：实时避障，应对动态障碍（行人、临时物品）
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from .robot import Pose2D, TrackedChassis


@dataclass
class Obstacle:
    x: float
    y: float
    radius: float = 0.25
    vx: float = 0.0
    vy: float = 0.0


class DynamicWindowAvoidance:
    """
    动态窗口法 (Dynamic Window Approach)
    在速度空间 (v, omega) 中采样，评价:
      G = alpha*heading + beta*dist + gamma*velocity - delta*obstacle_cost
    """

    def __init__(
        self,
        chassis: TrackedChassis,
        predict_time: float = 1.5,
        v_samples: int = 12,
        omega_samples: int = 16,
    ):
        self.chassis = chassis
        self.predict_time = predict_time
        self.v_samples = v_samples
        self.omega_samples = omega_samples
        self.alpha, self.beta, self.gamma, self.delta = 1.0, 2.0, 0.5, 2.5

    def _predict_pose(self, pose: Pose2D, v: float, omega: float, t: float) -> Pose2D:
        p = pose.copy()
        if abs(omega) < 1e-6:
            p.x += v * math.cos(p.theta) * t
            p.y += v * math.sin(p.theta) * t
        else:
            r = v / omega
            d_theta = omega * t
            p.x += r * (math.sin(p.theta + d_theta) - math.sin(p.theta))
            p.y += r * (-math.cos(p.theta + d_theta) + math.cos(p.theta))
            p.theta += d_theta
        return p

    def _obstacle_cost(
        self, pose: Pose2D, obstacles: List[Obstacle], t: float
    ) -> float:
        cost = 0.0
        for obs in obstacles:
            ox = obs.x + obs.vx * t
            oy = obs.y + obs.vy * t
            d = math.hypot(pose.x - ox, pose.y - oy) - obs.radius - 0.2
            if d < 0:
                return float("inf")
            cost += 1.0 / (d + 0.01)
        return cost

    def compute(
        self,
        goal: Tuple[float, float],
        obstacles: List[Obstacle],
        dt: float,
    ) -> Tuple[float, float]:
        """返回最优 (v, omega)"""
        pose = self.chassis.pose
        v_min = max(0.0, -self.chassis.max_linear_speed * 0.3)
        v_max = self.chassis.max_linear_speed
        w_min = -self.chassis.max_angular_speed
        w_max = self.chassis.max_angular_speed

        best_score = -float("inf")
        best_v, best_w = 0.0, 0.0
        goal_angle = math.atan2(goal[1] - pose.y, goal[0] - pose.x)

        for vi in range(self.v_samples):
            v = v_min + (v_max - v_min) * vi / max(1, self.v_samples - 1)
            for wi in range(self.omega_samples):
                omega = w_min + (w_max - w_min) * wi / max(1, self.omega_samples - 1)
                pred = self._predict_pose(pose, v, omega, self.predict_time)
                heading = math.cos(pred.theta - goal_angle)
                dist = -math.hypot(pred.x - goal[0], pred.y - goal[1])
                vel = abs(v)
                obs_c = self._obstacle_cost(pred, obstacles, self.predict_time)
                if obs_c == float("inf"):
                    continue
                score = (
                    self.alpha * heading
                    + self.beta * dist
                    + self.gamma * vel
                    - self.delta * obs_c
                )
                if score > best_score:
                    best_score = score
                    best_v, best_w = v, omega

        return best_v, best_w

    def follow_path(
        self,
        path: List[Tuple[float, float]],
        lookahead: float = 0.4,
    ) -> Tuple[float, float]:
        """Pure Pursuit 路径跟踪"""
        pose = self.chassis.pose
        if not path:
            return 0.0, 0.0

        # 找前视点
        target = path[-1]
        for px, py in path:
            if math.hypot(px - pose.x, py - pose.y) >= lookahead:
                target = (px, py)
                break

        dx = target[0] - pose.x
        dy = target[1] - pose.y
        target_angle = math.atan2(dy, dx)
        err = target_angle - pose.theta
        err = math.atan2(math.sin(err), math.cos(err))

        v = self.chassis.max_linear_speed * max(0.3, 1.0 - 2.0 * abs(err))
        omega = 2.0 * err
        return v, omega
