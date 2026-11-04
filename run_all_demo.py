#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键运行可复现的演示流程。

1. 运行底盘综合仿真（SLAM -> A* -> DWA -> 趋光），输出动画与关键帧
2. 导出算法数据摘要（JSON / TXT）

用法：
    python run_all_demo.py
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    os.chdir(ROOT)
    print("\n[1/2] 运行底盘综合仿真（生成视频与关键帧）...")
    subprocess.check_call([sys.executable, "simulate_chassis.py"])

    print("\n[2/2] 导出算法数据摘要...")
    subprocess.check_call([sys.executable, "export_algorithm_summary.py"])

    print("\n" + "=" * 60)
    print("演示流程已完成！")
    print(f"输出目录: {os.path.join(ROOT, 'output')}")
    print("  - algorithm_snapshots/    仿真关键帧")
    print("  - chassis_demo.gif        底盘仿真演示动画")
    print("  - algorithm_summary.json  算法运行数据")
    print("=" * 60)


if __name__ == "__main__":
    main()
