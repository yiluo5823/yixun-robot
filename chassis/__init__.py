"""
衣循机器人 - 底盘移动算法模块
对应 PPT：SLAM自主巡检、多地形履带越障、语音导航、趋光追踪
"""

from .robot import TrackedChassis, Pose2D
from .terrain import TerrainMap, TerrainType
from .slam import OccupancyGridSLAM
from .path_planner import AStarPlanner
from .obstacle_avoidance import DynamicWindowAvoidance
from .phototropism import PhototropismTracker
from .voice_nav import VoiceCommandNavigator

__all__ = [
    "TrackedChassis",
    "Pose2D",
    "TerrainMap",
    "TerrainType",
    "OccupancyGridSLAM",
    "AStarPlanner",
    "DynamicWindowAvoidance",
    "PhototropismTracker",
    "VoiceCommandNavigator",
]
