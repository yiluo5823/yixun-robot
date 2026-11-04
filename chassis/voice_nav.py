"""
语音指令导航
PPT：用户语音指令驱动，自主定位脏衣篮/洗衣机/阳台等语义地标
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .terrain import TerrainMap


@dataclass
class NavTask:
    command: str
    goal_name: str
    goal_xy: Tuple[float, float]
    description: str


class VoiceCommandNavigator:
    """语音语义解析 -> 导航目标序列"""

    COMMAND_PATTERNS = [
        (r"去.*脏衣|收.*衣服|回收", "脏衣篮", "前往脏衣篮回收衣物"),
        (r"洗衣|投放|洗衣机", "洗衣机", "将衣物投放至洗衣机"),
        (r"阳台|晾晒|晾衣", "阳台", "前往阳台晾晒区"),
        (r"智能柜|收纳|存放", "智能柜", "前往智能柜存放"),
        (r"回家|起点|充电", "起点", "返回起始位置"),
    ]

    def __init__(self, terrain: TerrainMap):
        self.terrain = terrain
        self.landmarks = terrain.get_landmarks()

    def parse(self, utterance: str) -> Optional[NavTask]:
        """解析单条语音指令"""
        utterance = utterance.strip()
        for pattern, landmark, desc in self.COMMAND_PATTERNS:
            if re.search(pattern, utterance):
                if landmark in self.landmarks:
                    xy = self.landmarks[landmark]
                    return NavTask(
                        command=utterance,
                        goal_name=landmark,
                        goal_xy=xy,
                        description=desc,
                    )
        return None

    def parse_workflow(self) -> List[NavTask]:
        """
        完整工作流（PPT 全流程）:
        回收脏衣 -> 洗衣机 -> 阳台晾晒 -> 智能柜收纳
        """
        workflow_commands = [
            "去脏衣篮收衣服",
            "把衣服放到洗衣机",
            "去阳台晾晒",
            "送到智能柜收纳",
        ]
        tasks = []
        for cmd in workflow_commands:
            t = self.parse(cmd)
            if t:
                tasks.append(t)
        return tasks
