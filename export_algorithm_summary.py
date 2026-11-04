#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出算法运行摘要 (JSON + 文本)，便于 PPT 引用数据"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from chassis.terrain import TerrainMap
from chassis.path_planner import AStarPlanner
from chassis.slam import OccupancyGridSLAM
from chassis.robot import Pose2D
from chassis.voice_nav import VoiceCommandNavigator
from chassis.phototropism import PhototropismTracker

OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)


def main():
    terrain = TerrainMap()
    planner = AStarPlanner(terrain)
    nav = VoiceCommandNavigator(terrain)
    photo = PhototropismTracker(balcony_bounds=(6.5, 4.8, 7.8, 5.8))

    landmarks = terrain.get_landmarks()
    workflow = nav.parse_workflow()
    paths_info = []
    prev = landmarks["起点"]
    total_len = 0.0
    for task in workflow:
        path = planner.plan(prev, task.goal_xy)
        length = 0.0
        if path:
            for i in range(1, len(path)):
                dx = path[i][0] - path[i - 1][0]
                dy = path[i][1] - path[i - 1][1]
                length += (dx * dx + dy * dy) ** 0.5
            total_len += length
            prev = task.goal_xy
        paths_info.append({
            "command": task.command,
            "goal": task.goal_name,
            "path_points": len(path) if path else 0,
            "length_m": round(length, 2),
        })

    slam = OccupancyGridSLAM(terrain)
    pose = Pose2D(2, 2, 0)
    for i in range(30):
        pose.x += 0.2
        pose.theta += 0.2
        slam.update(pose, slam.scan(pose, 24))

    sun_morning = photo.sun_at_hour(9)
    sun_noon = photo.sun_at_hour(12)
    opt_am = photo.find_optimal_position(sun_morning, (7.0, 5.2))
    opt_noon = photo.find_optimal_position(sun_noon, (7.0, 5.2))

    summary = {
        "project": "衣循 - 洗晒收纳一站式服务机器人",
        "algorithms": ["A*", "Occupancy Grid SLAM", "DWA", "Phototropism", "Voice Nav"],
        "workflow_paths": paths_info,
        "total_path_length_m": round(total_len, 2),
        "slam_explored_percent": round(slam.explored_ratio * 100, 1),
        "phototropism": {
            "9am_optimal": {"x": round(opt_am[0], 2), "y": round(opt_am[1], 2), "I": round(opt_am[2], 3)},
            "12pm_optimal": {"x": round(opt_noon[0], 2), "y": round(opt_noon[1], 2), "I": round(opt_noon[2], 3)},
        },
        "terrain_types": ["普通地面", "障碍", "地毯", "门槛", "阳台滑轨"],
    }

    json_path = os.path.join(OUT, "algorithm_summary.json")
    txt_path = os.path.join(OUT, "algorithm_summary.txt")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    lines = [
        "衣循机器人底盘算法运行摘要",
        "=" * 40,
        f"全流程路径总长: {summary['total_path_length_m']} m",
        f"SLAM 探索率: {summary['slam_explored_percent']}%",
        "",
        "语音导航任务:",
    ]
    for p in paths_info:
        lines.append(f"  - {p['command']} -> {p['goal']} ({p['length_m']}m, {p['path_points']}点)")
    lines += [
        "",
        f"趋光 9:00  最优位 ({opt_am[0]:.2f}, {opt_am[1]:.2f})",
        f"趋光 12:00 最优位 ({opt_noon[0]:.2f}, {opt_noon[1]:.2f})",
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"已导出: {json_path}")
    print(f"已导出: {txt_path}")


if __name__ == "__main__":
    main()
