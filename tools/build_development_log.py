from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "衣循_产品开发日志.pdf"
TMP = ROOT / "tmp" / "pdfs"

PAGE_W, PAGE_H = A4
MARGIN_X = 17 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 17 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X
CONTENT_H = PAGE_H - MARGIN_TOP - MARGIN_BOTTOM

INK = colors.HexColor("#263442")
NAVY = colors.HexColor("#30485E")
MUTED = colors.HexColor("#687783")
ACCENT = colors.HexColor("#C9783C")
ACCENT_SOFT = colors.HexColor("#F4E9DF")
LINE = colors.HexColor("#D9DEE2")
LIGHT = colors.HexColor("#F5F7F8")
WHITE = colors.white
GOOD = colors.HexColor("#3B7A68")
WARN = colors.HexColor("#9A6A2F")
RISK = colors.HexColor("#9B4D4D")

pdfmetrics.registerFont(TTFont("MSYH", r"C:\Windows\Fonts\msyh.ttc"))
pdfmetrics.registerFont(TTFont("SIMHEI", r"C:\Windows\Fonts\simhei.ttf"))


def esc(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CNBody",
        fontName="MSYH",
        fontSize=9.3,
        leading=15,
        textColor=INK,
        spaceAfter=6,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        name="CNBodySmall",
        parent=styles["CNBody"],
        fontSize=8.1,
        leading=12.3,
        textColor=MUTED,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="CNTitle",
        fontName="SIMHEI",
        fontSize=25,
        leading=31,
        textColor=INK,
        alignment=TA_LEFT,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="CNH1",
        fontName="SIMHEI",
        fontSize=17,
        leading=22,
        textColor=NAVY,
        spaceAfter=8,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        name="CNH2",
        fontName="SIMHEI",
        fontSize=11.5,
        leading=16,
        textColor=INK,
        spaceBefore=5,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="CNCaption",
        fontName="MSYH",
        fontSize=7.3,
        leading=10.5,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceBefore=3,
        spaceAfter=6,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        name="CNTable",
        fontName="MSYH",
        fontSize=7.4,
        leading=10.4,
        textColor=INK,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        name="CNTableHead",
        fontName="SIMHEI",
        fontSize=7.5,
        leading=10,
        textColor=WHITE,
        alignment=TA_CENTER,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        name="CNMetric",
        fontName="SIMHEI",
        fontSize=20,
        leading=24,
        textColor=ACCENT,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="CNMetricLabel",
        fontName="MSYH",
        fontSize=7.5,
        leading=10,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="CNNote",
        fontName="MSYH",
        fontSize=8.4,
        leading=13,
        textColor=INK,
        leftIndent=0,
        wordWrap="CJK",
    )
)
styles.add(
    ParagraphStyle(
        name="CNCode",
        fontName="MSYH",
        fontSize=7.2,
        leading=10.5,
        textColor=INK,
        wordWrap="CJK",
    )
)


class SectionRule(Flowable):
    def __init__(self, label: str):
        super().__init__()
        self.label = label
        self.height = 19

    def wrap(self, availWidth, availHeight):
        self._availWidth = availWidth
        return availWidth, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(ACCENT)
        c.roundRect(0, 6, 20, 7, 3.5, stroke=0, fill=1)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.7)
        c.line(27, 9.5, self._availWidth, 9.5)
        c.setFillColor(MUTED)
        c.setFont("MSYH", 7.2)
        c.drawRightString(self._availWidth, 12, self.label)


def P(text: object, style: str = "CNBody") -> Paragraph:
    return Paragraph(esc(text), styles[style])


def rich(text: str, style: str = "CNBody") -> Paragraph:
    return Paragraph(text, styles[style])


def fit_image(path: Path, max_w: float, max_h: float) -> Image:
    """缩放图片；若素材未随仓库分发则退化为占位说明，保证脚本仍可运行。"""
    if not Path(path).exists():
        return P(f"[素材缺失：{Path(path).name}]", "CNCaption")
    with PILImage.open(path) as im:
        w, h = im.size
    scale = min(max_w / w, max_h / h)
    return Image(str(path), width=w * scale, height=h * scale)


def figure(path: Path, caption: str, max_w: float = CONTENT_W, max_h: float = 105 * mm):
    return KeepTogether([fit_image(path, max_w, max_h), P(caption, "CNCaption")])


def section(title: str, code: str):
    return [SectionRule(code), P(title, "CNH1")]


def callout(title: str, body: str, tone: str = "neutral") -> Table:
    fill = {"neutral": LIGHT, "accent": ACCENT_SOFT, "good": colors.HexColor("#EAF3EF"), "warn": colors.HexColor("#F5EEE2")}[tone]
    title_color = {"neutral": NAVY, "accent": ACCENT, "good": GOOD, "warn": WARN}[tone]
    data = [[rich(f"<font color='{title_color.hexval()}'><b>{esc(title)}</b></font><br/>{esc(body)}", "CNNote")]]
    t = Table(data, colWidths=[CONTENT_W], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


def table(rows, widths=None, header=True, small=False, repeat=1):
    converted = []
    for r_idx, row in enumerate(rows):
        converted.append(
            [
                P(cell, "CNTableHead" if header and r_idx == 0 else ("CNBodySmall" if small else "CNTable"))
                for cell in row
            ]
        )
    if widths is None:
        widths = [CONTENT_W / len(rows[0])] * len(rows[0])
    t = Table(converted, colWidths=widths, repeatRows=repeat if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#FAFBFB")]),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    t.setStyle(TableStyle(commands))
    return t


def metrics(items):
    cells = []
    for value, label in items:
        cells.append([P(value, "CNMetric"), P(label, "CNMetricLabel")])
    # Transpose into two rows for even spacing.
    data = [[c[0] for c in cells], [c[1] for c in cells]]
    t = Table(data, colWidths=[CONTENT_W / len(items)] * len(items), hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("TOPPADDING", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def bullet(text: str):
    return rich(f"<font color='{ACCENT.hexval()}'>■</font>&nbsp;&nbsp;{esc(text)}", "CNBody")


class DevLogDocTemplate(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=MARGIN_X,
            rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="衣循产品开发日志",
            author="衣循项目组",
            subject="产品开发过程、实验验证、问题闭环和版本迭代记录",
        )
        normal = PageTemplate(
            id="normal",
            frames=[Frame(MARGIN_X, MARGIN_BOTTOM, CONTENT_W, CONTENT_H, id="content", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)],
            onPage=draw_page,
        )
        self.addPageTemplates([normal])


def draw_page(canvas: Canvas, doc):
    page = canvas.getPageNumber()
    canvas.saveState()
    if page == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - 14 * mm, PAGE_W, 14 * mm, fill=1, stroke=0)
        canvas.setFillColor(ACCENT)
        canvas.rect(0, PAGE_H - 16 * mm, PAGE_W, 2 * mm, fill=1, stroke=0)
    else:
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN_X, PAGE_H - 11.5 * mm, PAGE_W - MARGIN_X, PAGE_H - 11.5 * mm)
        canvas.setFont("MSYH", 7.1)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN_X, PAGE_H - 9 * mm, "衣循 | 产品开发日志")
        canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 9 * mm, "DEVELOPMENT LOG")
        canvas.line(MARGIN_X, 10.5 * mm, PAGE_W - MARGIN_X, 10.5 * mm)
        canvas.drawString(MARGIN_X, 7 * mm, "内部技术文档 | 依据可核验材料整理")
        canvas.drawRightString(PAGE_W - MARGIN_X, 7 * mm, f"{page:02d}")
    canvas.restoreState()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


story = []

# 1 Cover
story += [Spacer(1, 35 * mm)]
story.append(rich(f"<font color='{ACCENT.hexval()}'><b>衣循</b></font>", "CNTitle"))
story.append(P("洗晒收纳一站式家庭服务机器人", "CNH1"))
story.append(Spacer(1, 5 * mm))
story.append(P("产品开发日志", "CNTitle"))
story.append(P("方案设计、仿真验证、问题闭环与版本迭代记录", "CNH2"))
story.append(Spacer(1, 10 * mm))
hero = ROOT / "output" / "poster_assets_v12" / "hero_compact_trimmed.png"
story.append(fit_image(hero, 145 * mm, 88 * mm))
story.append(Spacer(1, 8 * mm))
cover_meta = Table(
    [
        [P("记录周期", "CNBodySmall"), P("2026年5月26日至2026年8月12日", "CNBody")],
        [P("汇编日期", "CNBodySmall"), P("2026年8月31日", "CNBody")],
        [P("文档版本", "CNBodySmall"), P("DL-1.0", "CNBody")],
        [P("当前阶段", "CNBodySmall"), P("系统方案与仿真验证完成，进入实物接口验证准备", "CNBody")],
    ],
    colWidths=[30 * mm, 120 * mm],
)
cover_meta.setStyle(
    TableStyle(
        [
            ("LINEABOVE", (0, 0), (-1, 0), 0.8, NAVY),
            ("LINEBELOW", (0, -1), (-1, -1), 0.8, NAVY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )
)
story.append(cover_meta)
story.append(PageBreak())

# 2 Document control
story += section("文档说明与证据边界", "00 / DOCUMENT CONTROL")
story.append(callout("记录原则", "本日志仅依据现有产品文件、代码、仿真输出、设计报告和版本时间信息整理。没有独立原始记录支撑的会议发言、样机测试和个人主责不作补写。", "accent"))
story.append(Spacer(1, 4 * mm))
story.append(P("本文件用于说明衣循产品从系统概念到多模块仿真验证的开发过程。记录重点包括：需求和方案形成、导航与控制算法实现、机械臂动作迭代、晾晒与衣柜接口设计、家庭端交互、问题排查、数据核查、版本演进和当前风险。"))
story.append(P("所有“已完成”均限定于现有证据范围。底盘、机械臂和衣柜的当前成果主要为软件仿真、运动时序和结构方案验证，不等同于完整样机实测。"))
story.append(Spacer(1, 4 * mm))
story.append(P("证据等级", "CNH2"))
story.append(
    table(
        [
            ["等级", "定义", "本日志采用的证据"],
            ["A", "可重复运行或直接读取的数据", "Python源文件、JSON/TXT输出、MP4/GIF、关键帧"],
            ["B", "结构化设计成果", "详细设计报告、结构标注图、算法说明、网页原型"],
            ["C", "版本与沟通归纳", "文件时间戳、版本序列、此前开发沟通中的明确修改决定"],
            ["D", "尚待验证的假设", "载荷、公差、湿衣力学、定位误差、连续运行可靠性"],
        ],
        widths=[18 * mm, 55 * mm, CONTENT_W - 73 * mm],
    )
)
story.append(Spacer(1, 5 * mm))
story.append(P("团队与协作说明", "CNH2"))
story.append(P("可核验成员为项目组三名成员。现有材料记录了三人协同开发，但未保存逐人逐日工时或署名任务台账，因此本日志以工作包方式呈现分工，不对无法核验的个人主责作推断。"))
story.append(PageBreak())

# 3 Executive summary
story += section("开发摘要与当前状态", "01 / EXECUTIVE SUMMARY")
story.append(P("衣循围绕家庭衣物在脏衣篮、洗衣机、阳台和衣柜之间反复人工接力的问题，建立“移动底盘连接空间、双机械臂完成柔性挂载、伞状装置执行晾晒、多仓衣柜承接整杆收纳”的系统闭环。开发工作并非堆叠四个独立部件，而是持续解决模块间的状态、接口与任务衔接。"))
story.append(Spacer(1, 3 * mm))
story.append(metrics([("7", "底盘算法模块"), ("4", "连续家庭任务"), ("10.97 m", "仿真总路径"), ("3", "核心运动仿真")]))
story.append(Spacer(1, 5 * mm))
summary_rows = [
    ["工作包", "状态", "可核验输出", "边界"],
    ["移动底盘", "已完成软件链路", "语音解析、SLAM、A*、DWA、趋光与演示视频", "未进行实物定位与越障测试"],
    ["双机械臂", "已完成3D动作仿真", "视觉定位、夹领、持架、穿入、完成四阶段", "未验证真实湿衣形变与夹持力"],
    ["晾晒装置", "结构和趋光策略完成", "伞状展开逻辑、光照场、最优点计算", "参数需在真实阳台标定"],
    ["多仓衣柜", "结构及时序仿真完成", "仓位旋转、挂杆伸出、整杆对接、回转入柜", "公差、锁止与载荷待样机验证"],
    ["家庭端软件", "网页原型完成", "任务、队列、位置、天气、衣柜状态与偏好设置", "尚未连接真实设备与账号体系"],
]
story.append(table(summary_rows, widths=[31 * mm, 32 * mm, 65 * mm, CONTENT_W - 128 * mm]))
story.append(Spacer(1, 5 * mm))
story.append(callout("当前结论", "系统级技术路线已经形成，三条运动仿真可独立运行，关键接口已被明确；下一阶段的核心不是继续增加展示内容，而是把接口尺寸、载荷、定位误差和安全互锁转化为可测量的样机指标。", "good"))
story.append(PageBreak())

# 4 Timeline
story += section("开发时间线", "02 / TIMELINE")
timeline = [
    ["日期", "阶段", "关键活动", "形成证据"],
    ["2026-05-26", "底盘算法成型", "拆分差速运动学、地形、SLAM、A*、DWA、趋光、语音导航七个模块；完成综合仿真。", "chassis/*.py；simulate_chassis.py；algorithm_summary.json"],
    ["2026-06-04", "家庭端原型", "将产品能力转换为家庭用户可理解的任务、队列、状态与提醒界面。", "衣循家庭衣物护理App.html"],
    ["2026-06-05", "机械臂迭代", "先完成二维动作演示；因衣物和动作表达不足，升级为三维双臂协同路径。", "arm_hanging_sim.gif；arm_hanging_3d_sim.gif"],
    ["2026-06-05", "衣柜接口方案", "形成旋转仓位、顶部伸缩挂杆和整杆入柜动作链。", "wardrobe_storage_sim.gif；结构标注图"],
    ["2026-06-18", "仿真集成", "建立统一启动器和三条技术路线目录，整理2×2关键帧证据。", "run_simulation_suite.py；report_assets；report_figures_2x2"],
    ["2026-06-19", "设计固化", "系统化整理需求、架构、算法、机构、测试矩阵与风险。", "衣循_作品详细设计报告.pdf"],
    ["2026-08-11", "衣柜方案更新", "刷新衣柜运动输出，统一“多仓旋转+整杆入柜”表达。", "wardrobe_storage_sim.*；wardrobe_structure_annotated.png"],
    ["2026-08-12", "资料一致性整理", "统一产品图、爆炸结构、流程、算法路线和视觉材料。", "产品总图与结构化展示材料"],
]
story.append(table(timeline, widths=[24 * mm, 28 * mm, 78 * mm, CONTENT_W - 130 * mm]))
story.append(Spacer(1, 5 * mm))
story.append(callout("时间线判定方法", "日期以文件最后修改时间和可核验输出为主。对同一天的多轮修改，按成果逻辑而非分钟级操作拆分。", "neutral"))
story.append(PageBreak())

# 5 Requirements
story += section("需求定义与系统边界", "03 / REQUIREMENTS")
story.append(P("需求分析将“洗衣”重新定义为跨空间衣物护理链，而不是单台洗衣机的清洗过程。开发目标由四项连续任务构成：回收与投放、洗后转运、挂载与晾晒、整杆收纳。"))
workflow = [
    ["阶段", "输入", "核心动作", "输出/接口"],
    ["01 回收投放", "语音任务、脏衣篮位置", "导航到脏衣篮，机械臂取衣并投放洗衣机", "洗涤任务启动"],
    ["02 洗后挂载", "洗涤完成、湿衣领口", "单臂夹领稳定，另一臂持衣架穿入", "衣物挂载到伞状晾衣杆"],
    ["03 晾晒优化", "阳台地图、光照场", "底盘移动、装置展开、趋光定位", "获得有效晾晒位置"],
    ["04 整杆入柜", "晾晒完成、目标仓位", "仓位旋转、挂杆伸出、整杆对接、回转", "衣物进入多仓衣柜"],
]
story.append(table(workflow, widths=[28 * mm, 41 * mm, 66 * mm, CONTENT_W - 135 * mm]))
story.append(Spacer(1, 5 * mm))
story.append(P("设计约束", "CNH2"))
for item in [
    "家庭空间存在普通地面、地毯、门槛、障碍物和阳台滑轨，路径规划必须考虑地形代价。",
    "湿衣柔性大、领口易闭合，机械臂动作优先保证稳定性和安全，不追求高速。",
    "晾晒装置在移动时需收拢，在作业区展开，并为衣柜整杆接收保留统一接口。",
    "底盘未稳定、衣杆未锁止或目标仓位未到位时，后续机构不得提前动作。",
    "家庭端只呈现任务状态、剩余时间和异常处理，不向普通用户暴露算法参数。",
]:
    story.append(bullet(item))
story.append(PageBreak())

# 6 Architecture and work packages
story += section("技术架构与工作包分工", "04 / ARCHITECTURE")
arch = [
    ["层级", "组成", "职责"],
    ["交互层", "语音指令、家庭端网页", "输入任务、显示阶段、异常与偏好设置"],
    ["感知层", "距离/激光射线、视觉目标、光照信息、仓位状态", "形成地图、领口目标、辐照度场和机构到位信号"],
    ["决策层", "语义解析、SLAM、A*、DWA、轨迹规划、趋光搜索", "把任务转换为可执行路径与动作序列"],
    ["执行层", "履带底盘、双机械臂、伞状晾晒装置、多仓衣柜", "完成跨空间搬运、柔性操作、晾晒和收纳"],
    ["协调层", "任务状态机与安全互锁", "控制模块先后关系，处理暂停、重试与异常中断"],
]
story.append(table(arch, widths=[27 * mm, 63 * mm, CONTENT_W - 90 * mm]))
story.append(Spacer(1, 5 * mm))
story.append(P("工作包分工", "CNH2"))
work = [
    ["工作包", "主要产出", "协作方式"],
    ["系统与机构", "任务链、机械臂动作、晾晒接口、衣柜结构", "机构边界与控制时序共同评审"],
    ["算法与仿真", "底盘算法包、三类仿真、关键帧与数据摘要", "模块独立实现，统一入口集成"],
    ["交互与文档", "家庭端网页、图表、设计报告、证据清单", "将工程状态转译为用户任务状态"],
]
story.append(table(work, widths=[35 * mm, 75 * mm, CONTENT_W - 110 * mm]))
story.append(Spacer(1, 5 * mm))
story.append(callout("分工说明", "项目组三名成员采用交叉协作。由于现有材料没有逐项署名责任表，本日志不把工作包强行映射到个人，以免形成无法核验的归属。", "warn"))
story.append(PageBreak())

# 7 Chassis design
story += section("阶段一：移动底盘与导航算法", "05 / CHASSIS DESIGN")
story.append(P("首轮工程重点是把跨房间任务转化为可复现的软件链路。底盘采用差速履带模型，地图显式区分普通地面、障碍、地毯、门槛和阳台滑轨，并在全局路径代价中体现通行难度。"))
modules = [
    ["模块", "文件", "关键方法"],
    ["运动学", "chassis/robot.py", "履带差速运动、位姿更新、速度限制"],
    ["家庭地形", "chassis/terrain.py", "五类地形栅格与代价映射"],
    ["地图构建", "chassis/slam.py", "Log-Odds占用栅格、Bresenham射线更新"],
    ["全局规划", "chassis/path_planner.py", "A*：f(n)=g(n)+h(n)，融合地形代价"],
    ["局部避障", "chassis/obstacle_avoidance.py", "DWA速度空间采样与轨迹评分"],
    ["趋光定位", "chassis/phototropism.py", "辐照度场与可行域梯度搜索"],
    ["语音目标", "chassis/voice_nav.py", "自然语言任务到家庭地标的映射"],
]
story.append(table(modules, widths=[27 * mm, 58 * mm, CONTENT_W - 85 * mm]))
story.append(Spacer(1, 5 * mm))
story.append(P("算法闭环", "CNH2"))
story.append(P("语音目标解析 → 地形与占用栅格建图 → 融合地形代价的A*全局路径 → DWA局部避障 → 差速运动执行 → 到达阳台后进行趋光位置优化。"))
story.append(callout("阶段输出", "simulate_chassis.py将上述模块编排为一个连续家庭任务仿真，并生成MP4、GIF、关键帧和JSON/TXT摘要。", "good"))
story.append(PageBreak())

# 8 Chassis testing
story += section("阶段一验证：底盘任务流转与数据核查", "06 / CHASSIS TEST")
story.append(figure(ROOT / "assets" / "figures" / "report_assets" / "chassis_storyboard.jpg", "图6-1 任务启动、地图探索、路径执行和流程完成四个阶段", max_h=86 * mm))
path_rows = [
    ["语音任务", "目标", "路径点", "长度"],
    ["去脏衣篮收衣服", "脏衣篮", "16", "1.53 m"],
    ["把衣服放到洗衣机", "洗衣机", "20", "2.03 m"],
    ["去阳台晾晒", "阳台", "51", "5.73 m"],
    ["送到智能柜收纳", "智能柜", "16", "1.68 m"],
    ["合计", "四段连续任务", "103", "10.97 m"],
]
story.append(table(path_rows, widths=[63 * mm, 36 * mm, 24 * mm, CONTENT_W - 123 * mm]))
story.append(Spacer(1, 4 * mm))
story.append(callout("数据口径核查", "2026-05-26生成的algorithm_summary.json记录SLAM探索率为76.7%；2026-06-19设计报告正文记录为87%。现有材料未保留两次运行的参数差异，因此本日志把76.7%作为可直接复现的原始输出，并将87%列为待复跑确认的后期记录。", "warn"))
story.append(PageBreak())

# 9 App
story += section("阶段二：家庭端交互原型", "07 / HOME APP")
story.append(P("家庭端原型的目标不是展示算法，而是降低任务理解和异常处理成本。界面以“今天要做什么、设备正在做什么、是否需要用户处理”为主线，将导航、机械臂和衣柜状态转换为生活化语言。"))
story.append(figure(TMP / "app_home.png", "图7-1 家庭衣物护理工作台：任务队列、当前阶段、位置、光照、衣柜容量和偏好设置", max_h=112 * mm))
app_rows = [
    ["界面模块", "记录内容", "开发目的"],
    ["今日护理", "待处理衣物、当前位置、剩余时间、光照与容量", "快速了解当天负荷"],
    ["任务状态", "洗后转运、机械臂挂载、趋光晾晒、智能收纳", "显示系统阶段而非算法参数"],
    ["衣物队列", "衣物类型、护理方式、优先级", "避免混洗和不当晾晒"],
    ["偏好设置", "提示音量、机械臂速度等", "适应安静模式和家庭习惯"],
]
story.append(table(app_rows, widths=[35 * mm, 74 * mm, CONTENT_W - 109 * mm]))
story.append(PageBreak())

# 10 Arm iteration
story += section("阶段三：双机械臂挂衣动作迭代", "08 / ARM ITERATION")
story.append(P("机械臂最初采用二维示意验证动作顺序，但衣服轮廓、空间深度和两臂分工不够清楚。开发决定保留二维版本作为保底证据，同时转向三维运动仿真，并把动作明确为“一臂夹住领口，另一臂拿衣架穿入领口”。"))
story.append(figure(ROOT / "assets" / "figures" / "report_assets" / "arm_storyboard.jpg", "图8-1 双机械臂三维协同：视觉定位、夹领准备、衣架穿入、挂载完成", max_h=88 * mm))
arm_rows = [
    ["阶段", "时间区间", "动作与控制重点"],
    ["视觉定位", "0.0至1.55 s", "识别领口开口与衣架姿态，确定安全接近位"],
    ["夹领稳定", "1.55至3.25 s", "左臂夹持领口边缘并保持，建立稳定边界"],
    ["持架穿入", "3.25至5.25 s", "右臂抓持衣架挂钩附近，沿三次曲线轨迹穿入"],
    ["挂载完成", "5.25至6.00 s", "确认位置后两臂依次释放并退出工作区"],
]
story.append(table(arm_rows, widths=[30 * mm, 31 * mm, CONTENT_W - 61 * mm]))
story.append(Spacer(1, 4 * mm))
story.append(callout("问题闭环", "二维表达不足 → 增加三维空间和阶段时间 → 明确双臂非对称分工 → 用关键帧检查路径是否穿过衣物与对侧机械臂。", "good"))
story.append(PageBreak())

# 11 Drying
story += section("阶段四：伞状晾晒模块与趋光策略", "09 / DRYING")
story.append(P("伞状晾晒模块采用中心立柱与径向支杆。移动状态收拢，减少通行包络；晾晒状态展开，增加衣物间通风距离；对接状态保留顶部接口，使整杆衣物可以直接转移到衣柜。"))
story.append(figure(ROOT / "assets" / "figures" / "ppt_figures" / "05_趋光追踪.png", "图9-1 阳台辐照度场与不同时刻的最优日照位置", max_h=88 * mm))
photo_rows = [
    ["时刻", "最优位置", "光照评分I", "动作"],
    ["09:00", "(7.00, 5.20)", "0.569", "移动到最优点"],
    ["12:00", "(7.00, 5.20)", "0.608", "保持位置，延长有效日照"],
    ["16:00", "(7.00, 5.20)", "0.425", "根据光照下降评估延时或通风策略"],
]
story.append(table(photo_rows, widths=[28 * mm, 48 * mm, 35 * mm, CONTENT_W - 111 * mm]))
story.append(Spacer(1, 4 * mm))
story.append(callout("验证边界", "评分来自设定的太阳辐照度场和阳台可行域，证明位置优化逻辑可运行；真实效果仍取决于阳台朝向、遮挡、风速和传感器标定。", "warn"))
story.append(PageBreak())

# 12 Wardrobe
story += section("阶段五：多仓旋转衣柜与整杆入柜", "10 / WARDROBE")
story.append(P("衣柜方案的关键不是增加一个独立收纳设备，而是消除晾晒完成后的最后一次人工逐件取衣。结构由多仓旋转存衣空间、中央回转轴、顶部可伸缩挂杆和整杆对接接口组成。"))
two = Table(
    [[fit_image(ROOT / "assets" / "figures" / "wardrobe_structure_annotated.png", 78 * mm, 82 * mm), fit_image(ROOT / "assets" / "figures" / "report_assets" / "wardrobe_storyboard.jpg", 88 * mm, 82 * mm)]],
    colWidths=[82 * mm, CONTENT_W - 82 * mm],
)
two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
story.append(two)
story.append(P("图10-1 结构标注与仓位旋转、挂杆伸出、整杆对接、回转入柜时序", "CNCaption"))
ward_rows = [
    ["动作", "前置条件", "完成判据", "异常处理"],
    ["仓位旋转", "目标仓可用", "目标仓到达正面", "未到位则保持挂杆收回"],
    ["挂杆伸出", "底盘与衣柜相对位姿稳定", "挂杆到达对接区", "超差则停止并重新定位"],
    ["整杆对接", "衣杆姿态和接口匹配", "锁止信号有效", "未锁止禁止回转"],
    ["回转入柜", "锁止和仓位信号均有效", "衣杆进入存衣仓", "检测卡滞并反向退出"],
]
story.append(table(ward_rows, widths=[28 * mm, 57 * mm, 44 * mm, CONTENT_W - 129 * mm]))
story.append(Spacer(1, 4 * mm))
story.append(callout("版本修订", "早期说明采用固定“四仓”表述；后续结构改为“多仓旋转存衣空间”，以便根据柜体尺寸参数化扩展，日志以多仓为当前版本。", "accent"))
story.append(PageBreak())

# 13 Integration
story += section("阶段六：统一仿真入口与系统协调", "11 / INTEGRATION")
story.append(P("随着底盘、机械臂和衣柜仿真分别形成，新的问题是入口分散、运行说明不一致。2026年6月18日建立run_simulation_suite.py，将三个模块纳入统一目录，并支持列出、单独运行和顺序运行全部仿真。"))
launcher = [
    ["入口", "技术路线", "主要输出"],
    ["chassis", "语音解析 → SLAM → A* → DWA → 趋光", "chassis_demo.gif / mp4"],
    ["arm", "领口定位 → 左臂夹领 → 右臂持架 → 衣架穿入", "arm_hanging_3d_sim.gif / mp4"],
    ["wardrobe", "仓位旋转 → 挂杆伸出 → 整杆对接 → 回转入柜", "wardrobe_storage_sim.gif / mp4"],
]
story.append(table(launcher, widths=[27 * mm, 87 * mm, CONTENT_W - 114 * mm]))
story.append(Spacer(1, 6 * mm))
story.append(P("系统状态机", "CNH2"))
state_rows = [
    ["状态", "允许动作", "互锁条件"],
    ["导航中", "底盘规划与移动", "机械臂和晾晒装置保持收拢"],
    ["挂载中", "夹领、持架、穿入", "底盘到位并制动，人员进入工作区则暂停"],
    ["晾晒中", "展开、趋光、状态监测", "挂载确认，移动速度受限"],
    ["对接中", "仓位旋转、挂杆伸出、锁止", "衣杆到位前禁止回转"],
    ["异常/暂停", "停止执行、保留状态、等待重试", "急停、视觉丢失、障碍或接口超差"],
]
story.append(table(state_rows, widths=[30 * mm, 70 * mm, CONTENT_W - 100 * mm]))
story.append(Spacer(1, 5 * mm))
story.append(callout("已发现的集成缺口", "统一启动器引用create_wardrobe_storage_sim.py，但当前根目录未保留该源文件；衣柜输出物仍存在。后续归档必须补齐脚本或将其从启动器中移除，否则“all”模式不能完全复现。", "warn"))
story.append(PageBreak())

# 14 Issues
story += section("问题排查与解决记录", "12 / ISSUE LOG")
issues = [
    ["编号", "发现的问题", "处理措施", "结果/状态"],
    ["P-01", "四个部件像孤立功能，缺少产品主线", "以衣物任务链为主线，明确洗衣区、阳台、衣柜之间的状态和接口", "系统边界清晰"],
    ["P-02", "底盘演示缺少家庭多地形与动态障碍", "加入地毯、门槛、滑轨地形代价和DWA局部避障", "软件链路完成"],
    ["P-03", "二维机械臂仿真难以看懂，衣物表达不清", "升级三维仿真，明确一臂夹领、一臂持架，并输出四阶段关键帧", "表达与路径可核查"],
    ["P-04", "衣柜仅描述仓位，未说明如何免去逐件取衣", "增加顶部伸缩挂杆和整杆对接接口，形成回转入柜时序", "闭环补全"],
    ["P-05", "三个仿真文件运行入口分散", "建立统一启动器和输出目录", "目录统一；衣柜源脚本待补齐"],
    ["P-06", "探索率出现76.7%与87%两种记录", "区分原始输出与后期报告，当前以JSON原始输出为复现基线", "数据口径已标注"],
    ["P-07", "家庭端曾偏工程展示，包含用户不需要的算法信息", "改为任务、队列、提醒、容量与偏好，弱化技术名词", "用户路径更清楚"],
    ["P-08", "早期衣柜固定“四仓”表述限制扩展", "修订为多仓旋转结构，保留参数化空间", "当前结构表述统一"],
]
story.append(table(issues, widths=[17 * mm, 49 * mm, 72 * mm, CONTENT_W - 138 * mm], small=True))
story.append(Spacer(1, 5 * mm))
story.append(callout("关闭标准", "问题只有在对应输出、数据或结构图能够被复查时才标记为解决；仍依赖实物的内容统一标记为“待验证”，不以视觉演示替代工程测试。", "neutral"))
story.append(PageBreak())

# 15 Test matrix and risk
story += section("验证矩阵、风险与下一步测试", "13 / TEST & RISK")
test_rows = [
    ["测试项目", "当前证据", "当前结论", "下一步可量化指标"],
    ["家庭导航", "四段任务、路径和关键帧", "语义目标至运动执行链路可运行", "任务完成率、定位误差、重规划次数"],
    ["复杂地形", "五类地形代价模型", "规划可区分不同通行代价", "最大门槛、滑轨通过率、侧翻裕度"],
    ["湿衣挂载", "三维动作仿真", "双臂分工和路径时序可表达", "不同领型成功率、夹持力、耗时"],
    ["趋光晾晒", "辐照度场与最优点", "位置搜索逻辑可运行", "相对光照提升、定位误差、风速影响"],
    ["整杆入柜", "结构图和时序仿真", "接口概念和互锁顺序明确", "允许误差、锁止载荷、对接成功率"],
    ["人机安全", "状态机和异常策略", "逻辑层已考虑暂停与互锁", "急停距离、人员接近响应、恢复策略"],
]
story.append(table(test_rows, widths=[31 * mm, 51 * mm, 58 * mm, CONTENT_W - 140 * mm], small=True))
story.append(Spacer(1, 5 * mm))
risk_rows = [
    ["风险", "严重度", "原因", "控制措施"],
    ["湿衣滑落或领口变形", "高", "仿真未包含真实面料力学", "柔性夹爪、力限位、滑落检测、分面料测试"],
    ["双臂互碰", "高", "工作空间交叠", "安全区、时间错位、轨迹预检与急停"],
    ["衣杆对接偏差", "高", "底盘定位和机构公差叠加", "导向结构、视觉标记、允许误差与锁止反馈"],
    ["家庭动态障碍", "中", "人员和临时物品不可预测", "DWA、降速、停车等待和重新规划"],
    ["晾晒位置收益不足", "中", "真实遮挡和天气变化", "接入传感器，结合通风与天气策略"],
]
story.append(table(risk_rows, widths=[42 * mm, 20 * mm, 61 * mm, CONTENT_W - 123 * mm], small=True))
story.append(PageBreak())

# 16 Version and decisions
story += section("版本迭代与协作决策纪要", "14 / VERSION HISTORY")
versions = [
    ["版本", "日期", "主要变更", "保留成果"],
    ["V0.1", "05-26", "底盘七个算法模块和综合仿真", "代码包、JSON/TXT、MP4/GIF"],
    ["V0.2", "06-04", "家庭端网页原型", "任务与状态交互框架"],
    ["V0.3", "06-05", "机械臂二维动作演示", "动作顺序基线"],
    ["V0.4", "06-05", "机械臂升级为三维双臂协同", "四阶段关键帧和6秒仿真"],
    ["V0.5", "06-05", "旋转衣柜整杆入柜方案", "结构图、GIF/MP4"],
    ["V0.6", "06-18", "统一仿真入口、证据拼图", "run_simulation_suite.py、storyboard"],
    ["V0.7", "06-19", "系统设计、测试矩阵和风险固化", "详细设计报告"],
    ["V0.8", "08-11", "衣柜更新为多仓表达并刷新运动输出", "最新衣柜仿真"],
    ["V1.0", "08-12", "统一产品结构、技术路线和文档证据", "当前开发基线"],
]
story.append(table(versions, widths=[19 * mm, 24 * mm, 89 * mm, CONTENT_W - 132 * mm], small=True))
story.append(Spacer(1, 5 * mm))
story.append(P("协作决策记录（由文件版本与开发沟通归纳，并非逐字会议记录）", "CNH2"))
decisions = [
    ["日期", "决策", "理由", "影响"],
    ["05-26", "底盘按算法职责拆分，而非单脚本堆叠", "便于独立验证和后续替换", "形成七模块结构"],
    ["06-05", "保留二维机械臂版本，同时转向三维", "二维可作保底，但不能说明空间可行性", "建立三维动作证据"],
    ["06-05", "固定“一臂夹领、一臂持架”动作分工", "减少同时拉扯和碰撞", "明确轨迹与安全边界"],
    ["06-18", "三类仿真统一入口和输出清单", "避免运行方式分散", "建立集成脚本"],
    ["08-11", "衣柜由固定四仓改为多仓", "适配不同柜体容量和尺寸", "结构表达参数化"],
]
story.append(table(decisions, widths=[24 * mm, 68 * mm, 56 * mm, CONTENT_W - 148 * mm], small=True))
story.append(PageBreak())

# 17 Evidence appendix
story += section("证据材料索引与文件指纹", "A / EVIDENCE INDEX")
evidence_paths = [
    ROOT / "docs" / "算法说明.md",
    ROOT / "simulate_chassis.py",
    ROOT / "run_simulation_suite.py",
    ROOT / "create_arm_hanging_3d_sim.py",
    ROOT / "assets" / "data" / "algorithm_summary.json",
    ROOT / "assets" / "demos" / "chassis_demo.gif",
    ROOT / "assets" / "demos" / "arm_hanging_3d_sim.gif",
    ROOT / "assets" / "demos" / "wardrobe_storage_sim.gif",
    ROOT / "assets" / "figures" / "wardrobe_structure_annotated.png",
    ROOT / "assets" / "app" / "衣循家庭衣物护理App.html",
    ROOT / "docs" / "衣循_作品详细设计报告.pdf",
]
evidence_rows = [["编号", "文件", "最后修改", "大小", "SHA-256前16位"]]
for idx, path in enumerate(evidence_paths, 1):
    stat = path.stat()
    evidence_rows.append(
        [
            f"E-{idx:02d}",
            str(path.relative_to(ROOT)).replace("\\", "/"),
            __import__("datetime").datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024 * 1024 else f"{stat.st_size / 1024 / 1024:.2f} MB",
            sha256(path)[:16],
        ]
    )
story.append(table(evidence_rows, widths=[16 * mm, 82 * mm, 37 * mm, 25 * mm, CONTENT_W - 160 * mm], small=True))
story.append(Spacer(1, 5 * mm))
story.append(P("证据说明", "CNH2"))
story.append(P("文件指纹用于确认日志编制时读取的具体版本。GIF和MP4只证明既定模型和时序能够生成连续画面，不能替代真实机构载荷、材料、定位和耐久性测试。网页截图为本地HTML原型的实际渲染结果。"))
story.append(callout("归档缺口", "当前统一启动器所引用的create_wardrobe_storage_sim.py不在根目录；建议在下一次归档前补回衣柜仿真源文件，并为每次完整仿真保存参数、运行时间、Git提交或压缩包校验值。", "warn"))
story.append(PageBreak())

# 18 Conclusion
story += section("阶段结论与后续开发清单", "15 / CONCLUSION")
story.append(P("截至本日志记录结束，衣循已经完成从问题定义、系统架构、关键算法、机构动作到家庭端交互的完整方案闭环，并通过三类仿真输出证明任务链在模型层面具备可执行性。产品的主要价值不在某一个机构或算法，而在于把分散的家庭设备和空间连接成连续衣物护理流程。"))
story.append(Spacer(1, 4 * mm))
story.append(P("已完成", "CNH2"))
for item in [
    "底盘语义目标、地图构建、全局路径、局部避障、运动执行和趋光搜索的软件链路。",
    "双机械臂夹领、持架、穿入和释放的三维动作分工与关键帧验证。",
    "伞状晾晒装置的收拢、展开和整杆转移接口设计。",
    "多仓旋转衣柜的仓位、伸缩挂杆、对接、锁止和回转时序。",
    "面向家庭用户的任务、状态、提醒、衣物队列和偏好设置原型。",
]:
    story.append(bullet(item))
story.append(Spacer(1, 3 * mm))
story.append(P("下一阶段优先级", "CNH2"))
next_rows = [
    ["优先级", "任务", "交付判据"],
    ["P0", "补齐衣柜仿真源文件与运行参数", "统一启动器all模式可从空输出目录完整复现"],
    ["P0", "制作机械臂挂衣工装", "三种领型、三种面料形成成功率和夹持力数据"],
    ["P0", "制作伸缩挂杆与整杆锁止接口", "获得允许误差、锁止载荷和对接成功率"],
    ["P1", "底盘在典型家庭通道连续运行", "记录定位误差、越障通过率、重规划和急停距离"],
    ["P1", "趋光算法接入真实光照传感器", "比较固定点与优化点的有效光照提升"],
    ["P2", "家庭端与真实状态机联调", "任务、暂停、召回、异常和恢复状态可追踪"],
]
story.append(table(next_rows, widths=[20 * mm, 83 * mm, CONTENT_W - 103 * mm]))
story.append(Spacer(1, 7 * mm))
story.append(callout("阶段判断", "当前产品处于“系统方案和仿真验证完成、实物接口验证待启动”的阶段。开发日志已经形成可追溯基线，后续每轮样机测试应继续追加日期、参数、原始数据、异常、修复和版本号。", "good"))
story.append(Spacer(1, 14 * mm))
story.append(HRFlowable(width="100%", thickness=0.8, color=LINE))
story.append(Spacer(1, 4 * mm))
story.append(P("文档结束 | 衣循产品开发日志 DL-1.0", "CNCaption"))


doc = DevLogDocTemplate(str(OUT))
doc.build(story)
print(OUT)
