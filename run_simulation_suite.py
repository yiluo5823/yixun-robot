#!/usr/bin/env python3
"""衣循仿真统一启动器。

在 VS Code 终端中运行：
    python run_simulation_suite.py --list
    python run_simulation_suite.py chassis
    python run_simulation_suite.py arm
    python run_simulation_suite.py wardrobe
    python run_simulation_suite.py all
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

SIMULATIONS = {
    "chassis": {
        "name": "底盘自主导航仿真",
        "script": "simulate_chassis.py",
        "outputs": ["output/chassis_demo.gif", "output/chassis_demo.mp4"],
        "route": "语音解析 -> SLAM建图 -> A*规划 -> DWA避障 -> 趋光定位",
    },
    "arm": {
        "name": "双机械臂挂衣仿真",
        "script": "create_arm_hanging_3d_sim.py",
        "outputs": ["output/arm_hanging_3d_sim.gif", "output/arm_hanging_3d_sim.mp4"],
        "route": "领口定位 -> 左臂夹领 -> 右臂持架 -> 衣架穿入",
    },
    "wardrobe": {
        "name": "旋转衣柜收纳仿真",
        "script": "create_wardrobe_storage_sim.py",
        "outputs": ["output/wardrobe_storage_sim.gif", "output/wardrobe_storage_sim.mp4"],
        "route": "仓位旋转 -> 挂杆伸出 -> 整杆对接 -> 回转入柜",
    },
}


def print_catalog() -> None:
    print("=" * 68)
    print("衣循机器人仿真模块")
    print("=" * 68)
    for key, item in SIMULATIONS.items():
        print(f"[{key}] {item['name']}")
        print(f"  技术路线: {item['route']}")
        print(f"  运行脚本: {item['script']}")
        print(f"  输出文件: {', '.join(item['outputs'])}")
    print("=" * 68)


def run_one(key: str) -> None:
    item = SIMULATIONS[key]
    script = ROOT / item["script"]
    print(f"\n>>> 正在运行：{item['name']}")
    print(f">>> 技术路线：{item['route']}")
    if not script.exists():
        print(f">>> [跳过] 源文件 {item['script']} 未包含在本仓库中。")
        for output in item["outputs"]:
            path = ROOT / output
            if path.exists() and path.stat().st_size > 0:
                print(f"    [已归档输出] {output}")
        return
    print(f">>> 命令：{sys.executable} {script.name}\n")
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)
    print(f"\n>>> {item['name']}运行完成")
    for output in item["outputs"]:
        path = ROOT / output
        status = "已生成" if path.exists() and path.stat().st_size > 0 else "未生成"
        print(f"    [{status}] {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="衣循仿真统一启动器")
    parser.add_argument(
        "module",
        nargs="?",
        choices=[*SIMULATIONS.keys(), "all"],
        help="要运行的仿真模块",
    )
    parser.add_argument("--list", action="store_true", help="列出仿真模块和技术路线")
    args = parser.parse_args()

    if args.list or args.module is None:
        print_catalog()
        return

    keys = list(SIMULATIONS) if args.module == "all" else [args.module]
    for key in keys:
        run_one(key)

    print("\n全部指定仿真任务已完成，输出目录：")
    print(ROOT / "output")


if __name__ == "__main__":
    main()
