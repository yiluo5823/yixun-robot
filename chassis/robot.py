"""
履带底盘运动学模型
PPT：摆臂式高抓地力履带，差速转向，适应室内全向移动
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Pose2D:
    """二维位姿 (x, y, theta) 单位：米、弧度"""

    x: float
    y: float
    theta: float

    def copy(self) -> "Pose2D":
        return Pose2D(self.x, self.y, self.theta)

    def distance_to(self, other: "Pose2D") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


class TrackedChassis:
    """
    差速履带底盘运动学
    状态: (x, y, theta), 控制: (v, omega) 线速度/角速度
    """

    def __init__(
        self,
        track_width: float = 0.32,
        max_linear_speed: float = 0.5,
        max_angular_speed: float = 1.2,
    ):
        self.track_width = track_width
        self.max_linear_speed = max_linear_speed
        self.max_angular_speed = max_angular_speed
        self.pose = Pose2D(0.0, 0.0, 0.0)

    def update(self, v: float, omega: float, dt: float) -> None:
        """根据控制量推进一个时间步"""
        v = max(-self.max_linear_speed, min(self.max_linear_speed, v))
        omega = max(-self.max_angular_speed, min(self.max_angular_speed, omega))

        if abs(omega) < 1e-6:
            self.pose.x += v * math.cos(self.pose.theta) * dt
            self.pose.y += v * math.sin(self.pose.theta) * dt
        else:
            # 圆弧运动模型
            radius = v / omega
            d_theta = omega * dt
            self.pose.x += radius * (
                math.sin(self.pose.theta + d_theta) - math.sin(self.pose.theta)
            )
            self.pose.y += radius * (
                -math.cos(self.pose.theta + d_theta) + math.cos(self.pose.theta)
            )
            self.pose.theta += d_theta

        self.pose.theta = math.atan2(
            math.sin(self.pose.theta), math.cos(self.pose.theta)
        )

    def set_pose(self, x: float, y: float, theta: float = 0.0) -> None:
        self.pose = Pose2D(x, y, theta)
