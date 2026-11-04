from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
ASSETS = OUT / "report_assets"
FINAL = ROOT / "docs" / "衣循_作品详细设计报告.docx"

ORANGE = "E87532"
ORANGE_LIGHT = "FCEBDD"
BLUE = "2F6F9F"
BLUE_LIGHT = "E8F2F8"
GREEN = "4C916C"
GRAY = "666666"
LIGHT_GRAY = "F3F4F5"
LINE = "D7D7D7"
BLACK = "000000"

FONT_CN = "宋体"
FONT_HEAD = "黑体"
FONT_EN = "Times New Roman"


def set_cell_shading(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=90, start=120, bottom=90, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, value in [("top", top), ("start", start), ("bottom", bottom), ("end", end)]:
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_width(cell, width_dxa: int):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(width_dxa))
    tc_w.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_dxa: list[int], total=9072, indent=0):
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(total))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(indent))
    tbl_ind.set(qn("w:type"), "dxa")
    grid = tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for w in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(w))
        grid.append(col)
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            set_cell_width(cell, widths_dxa[idx])
            set_cell_margins(cell)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_row_cant_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def set_run_font(run, name=FONT_CN, size=12, bold=False, color=BLACK, italic=False):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), FONT_EN)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), FONT_EN)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def set_para_font(paragraph, name=FONT_CN, size=12, bold=False, color=BLACK):
    for run in paragraph.runs:
        set_run_font(run, name, size, bold, color)


def add_field(paragraph, field_code: str):
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = field_code
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr, fld_char2])
    return run


def configure_document(doc: Document):
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.4)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.7)
    section.right_margin = Cm(2.4)
    section.header_distance = Cm(1.2)
    section.footer_distance = Cm(1.2)

    normal = doc.styles["Normal"]
    normal.font.name = FONT_CN
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    normal.font.size = Pt(12)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.first_line_indent = Cm(0.74)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE

    for style_name, size, before, after in [
        ("Heading 1", 16, 12, 8),
        ("Heading 2", 15, 10, 6),
        ("Heading 3", 13, 8, 5),
    ]:
        style = doc.styles[style_name]
        style.font.name = FONT_HEAD
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_HEAD)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.line_spacing = 1.0

    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run("衣循——洗晒收纳一站式家庭服务机器人  作品详细设计报告")
    set_run_font(r, FONT_CN, 9, False, "777777")
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), "D8D8D8")
    pBdr.append(bottom)
    pPr.append(pBdr)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_before = Pt(0)
    fp.paragraph_format.space_after = Pt(0)
    r = fp.add_run("— ")
    set_run_font(r, FONT_CN, 9, False, "777777")
    page_run = add_field(fp, "PAGE")
    set_run_font(page_run, FONT_CN, 9, False, "777777")
    r = fp.add_run(" —")
    set_run_font(r, FONT_CN, 9, False, "777777")


def add_title(doc, text, size=16, level=1, color=BLACK):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run(text)
    set_run_font(r, FONT_HEAD, size, True, color)
    return p


def add_body(doc, text, bold_lead: str | None = None, after=6):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(0.74)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_after = Pt(after)
    if bold_lead and text.startswith(bold_lead):
        r1 = p.add_run(bold_lead)
        set_run_font(r1, FONT_CN, 12, True)
        r2 = p.add_run(text[len(bold_lead):])
        set_run_font(r2, FONT_CN, 12)
    else:
        r = p.add_run(text)
        set_run_font(r, FONT_CN, 12)
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph(style=None)
    p.paragraph_format.left_indent = Cm(0.74)
    p.paragraph_format.first_line_indent = Cm(-0.38)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    r = p.add_run("（1）" + text)
    set_run_font(r, FONT_CN, 12)
    return p


def add_numbered_items(doc, items: Iterable[str]):
    for i, text in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.74)
        p.paragraph_format.first_line_indent = Cm(-0.74)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        r = p.add_run(f"{i}. {text}")
        set_run_font(r, FONT_CN, 12)


def add_callout(doc, title, text, fill=BLUE_LIGHT, accent=BLUE):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_geometry(table, [9072], total=9072)
    cell = table.cell(0, 0)
    set_cell_shading(cell, fill)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = cell.paragraphs[0]
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(title + "  ")
    set_run_font(r, FONT_HEAD, 11.5, True, accent)
    r = p.add_run(text)
    set_run_font(r, FONT_CN, 11.5, False, BLACK)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.keep_together = True
    r = p.add_run(text)
    set_run_font(r, FONT_CN, 10.5, False, BLACK)
    return p


def add_picture(doc, path: Path, width_cm: float, caption: str | None = None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width_cm))
    if caption:
        add_caption(doc, caption)
    return p


def add_table(doc, headers: list[str], rows: list[list[str]], widths: list[int], header_fill=BLUE_LIGHT,
              font_size=10.5, caption: str | None = None):
    if caption:
        add_caption(doc, caption)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_geometry(table, widths, total=sum(widths))
    table.style = "Table Grid"
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    set_row_cant_split(hdr)
    for idx, text in enumerate(headers):
        cell = hdr.cells[idx]
        set_cell_shading(cell, header_fill)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(text)
        set_run_font(r, FONT_HEAD, font_size, True, BLACK)
    for row in rows:
        cells = table.add_row().cells
        set_row_cant_split(table.rows[-1])
        for idx, text in enumerate(row):
            cell = cells[idx]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if len(text) > 10 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            r = p.add_run(text)
            set_run_font(r, FONT_CN, font_size)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def new_page(doc):
    doc.add_page_break()


def add_page_kicker(doc, chapter, claim):
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_geometry(table, [1800, 7272], total=9072)
    c0, c1 = table.rows[0].cells
    set_cell_shading(c0, ORANGE_LIGHT)
    set_cell_shading(c1, LIGHT_GRAY)
    for cell in [c0, c1]:
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = c0.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run(chapter)
    set_run_font(r, FONT_HEAD, 11, True, ORANGE)
    p = c1.paragraphs[0]
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run(claim)
    set_run_font(r, FONT_CN, 11, True, BLACK)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def compose_storyboard(paths: list[Path], labels: list[str], out: Path, title: str):
    canvas = Image.new("RGB", (1600, 900), "#fffaf2")
    d = ImageDraw.Draw(canvas)
    fonts = []
    for size, bold in [(52, True), (28, True)]:
        candidates = ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/simhei.ttf"]
        f = None
        for p in candidates:
            try:
                f = ImageFont.truetype(p, size)
                break
            except Exception:
                pass
        fonts.append(f or ImageFont.load_default())
    d.text((60, 35), title, font=fonts[0], fill="#243044")
    margin, gap = 55, 22
    box_w = (1600 - margin * 2 - gap * 3) // 4
    y, h = 150, 600
    for i, path in enumerate(paths):
        im = Image.open(path).convert("RGB")
        im.thumbnail((box_w - 18, h - 90))
        x = margin + i * (box_w + gap)
        d.rounded_rectangle((x, y, x + box_w, y + h), radius=26, fill="#ffffff", outline="#e8d8c7", width=3)
        px = x + (box_w - im.width) // 2
        py = y + 16 + (h - 90 - im.height) // 2
        canvas.paste(im, (px, py))
        d.text((x + 20, y + h - 58), labels[i], font=fonts[1], fill="#e87532")
    canvas.save(out, quality=92)


def make_assets():
    ASSETS.mkdir(parents=True, exist_ok=True)
    arm_paths = [
        OUT / "arm_hanging_3d_keyframes" / "01_视觉定位_3d.png",
        OUT / "arm_hanging_3d_keyframes" / "02_双臂撑开_3d.png",
        OUT / "arm_hanging_3d_keyframes" / "03_衣架穿入_3d.png",
        OUT / "arm_hanging_3d_keyframes" / "04_挂载完成_3d.png",
    ]
    wardrobe_paths = [
        OUT / "wardrobe_storage_keyframes" / "01_旋转存衣仓.png",
        OUT / "wardrobe_storage_keyframes" / "02_伸缩挂杆.png",
        OUT / "wardrobe_storage_keyframes" / "03_整杆对接.png",
        OUT / "wardrobe_storage_keyframes" / "04_收纳完成.png",
    ]
    chassis_paths = [
        OUT / "algorithm_snapshots" / "frame_0020.png",
        OUT / "algorithm_snapshots" / "frame_0120.png",
        OUT / "algorithm_snapshots" / "frame_0280.png",
        OUT / "algorithm_snapshots" / "frame_0400.png",
    ]
    compose_storyboard(arm_paths, ["视觉定位", "夹领准备", "衣架穿入", "挂载完成"],
                       ASSETS / "arm_storyboard.jpg", "单臂夹领、单臂持架的协同挂载过程")
    compose_storyboard(wardrobe_paths, ["仓位旋转", "挂杆伸出", "整杆对接", "回转入柜"],
                       ASSETS / "wardrobe_storyboard.jpg", "伞状晾衣杆整杆入柜过程")
    compose_storyboard(chassis_paths, ["任务启动", "地图探索", "路径执行", "流程完成"],
                       ASSETS / "chassis_storyboard.jpg", "家庭任务流转与底盘导航仿真")


def cover_page(doc: Document, product_img: Path):
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("衣 循")
    set_run_font(r, FONT_HEAD, 30, True, ORANGE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run("洗晒收纳一站式家庭服务机器人")
    set_run_font(r, FONT_HEAD, 22, True, BLACK)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(20)
    r = p.add_run("作品详细设计报告")
    set_run_font(r, FONT_CN, 18, False, BLUE)
    add_picture(doc, product_img, 10.6)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(18)
    r = p.add_run("参赛类别：主题一·家用智能机器人")
    set_run_font(r, FONT_CN, 12, False, GRAY)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("2026年6月")
    set_run_font(r, FONT_CN, 12, False, GRAY)


def build():
    make_assets()
    doc = Document()
    configure_document(doc)
    media = ROOT / "outputs" / "manual-yixun-provincial" / "presentations" / "yixun-provincial-defense" / "assets" / "source_ppt_media"
    if media.exists():
        product = media / "image2.png"
        floorplan = media / "image7.png"
        umbrella = media / "image11.png"
    else:
        # 仓库版：原始素材目录未随仓库分发，回退到已归档的插图
        product = ROOT / "assets" / "poster" / "展板主海报_预览.png"
        floorplan = ROOT / "assets" / "figures" / "ppt_figures" / "03_SLAM建图.png"
        umbrella = ROOT / "assets" / "figures" / "ppt_figures" / "05_趋光追踪.png"

    cover_page(doc, product)
    new_page(doc)

    # Page 2: abstract
    add_title(doc, "摘  要", 18, 1)
    add_body(doc, "针对现有洗衣设备仅完成清洗环节，而脏衣回收、洗后转运、湿衣挂载、阳台晾晒及入柜收纳仍依赖人工的问题，本文提出“衣循”洗晒收纳一站式家庭服务机器人。系统以履带式移动底盘为载体，集成双机械臂、伞状自适应晾晒模块、四仓旋转智能衣柜及家庭衣物护理软件，实现衣物护理任务在洗衣机、阳台和衣柜之间的连续流转。")
    add_body(doc, "在移动层，系统采用占用栅格SLAM构建家庭环境地图，以融合地形代价的A*算法完成全局路径规划，并利用动态窗口法进行局部避障；在操作层，采用“单臂夹持领口、单臂持衣架穿入”的协同策略，降低柔性湿衣挂载过程中的褶皱和滑落风险；在晾晒与收纳层，伞状晾衣杆可根据阳台光照场进行位置微调，并通过顶部伸缩挂杆与旋转衣柜实现整杆对接，避免晾晒完成后的逐件取衣。")
    add_body(doc, "目前已完成底盘任务流转、机械臂挂载和智能衣柜整杆入柜的运动仿真。底盘仿真包含4段家庭语音任务，总路径长度10.97 m，环境探索率为76.7%；机械臂与衣柜部分已形成结构方案、动作时序和关键帧验证。结果表明，该方案能够从系统层面连接洗、晒、收三个原本割裂的家务环节，为双职工家庭、老年家庭及行动不便人群提供新的家庭衣物护理方式。")
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("关键词：")
    set_run_font(r, FONT_HEAD, 12, True)
    r = p.add_run("家庭服务机器人；柔性衣物操作；双机械臂；自主导航；趋光晾晒；旋转衣柜")
    set_run_font(r, FONT_CN, 12)
    add_callout(doc, "作品定位", "衣循不是单一晾衣设备，而是以移动机器人为载体，重新组织衣物从洗涤、晾晒到收纳的空间流转方式。", ORANGE_LIGHT, ORANGE)
    new_page(doc)

    # Page 3: contents
    add_title(doc, "目  录", 18, 1)
    toc = [
        ("第1章 研究背景与需求分析", "4"),
        ("第2章 总体方案与系统架构", "6"),
        ("第3章 移动底盘设计与导航算法", "8"),
        ("第4章 双机械臂湿衣挂载系统", "11"),
        ("第5章 伞状晾晒模块与趋光策略", "14"),
        ("第6章 旋转智能衣柜与整杆入柜", "16"),
        ("第7章 多模块协同控制与软件交互", "19"),
        ("第8章 仿真验证、测试方案与风险分析", "21"),
        ("第9章 创新性、应用前景与实施路线", "24"),
        ("结论", "27"),
        ("参考文献", "28"),
    ]
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_geometry(table, [7900, 1172], total=9072)
    for title, page in toc:
        cells = table.add_row().cells
        for c in cells:
            set_cell_margins(c, 100, 80, 100, 80)
        p = cells[0].paragraphs[0]
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(title)
        set_run_font(r, FONT_CN, 12, title.startswith("第") and "章" in title, BLACK)
        p = cells[1].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(page)
        set_run_font(r, FONT_EN, 12)
    add_callout(doc, "阅读提示", "报告采用“问题—设计—原理—证据—边界”的叙事结构，各技术章节均明确区分已完成仿真、当前设计状态与后续实物验证计划。")
    new_page(doc)

    # Page 4
    add_page_kicker(doc, "第1章", "先证明问题足够真实，再讨论机器人如何解决。")
    add_title(doc, "1 研究背景与需求分析", 16, 1)
    add_title(doc, "1.1 洗衣后的连续家务仍高度依赖人工", 15, 2)
    add_body(doc, "洗衣机的普及显著降低了清洗本身的劳动强度，但没有消除洗前回收、洗后取衣、湿衣转移、穿架挂晒、收回整理和入柜存放等后续工作。第三次全国时间利用调查显示，我国居民无酬劳动领域参与者每日平均投入时间仍达到2小时5分钟，其中家务劳动是重要组成部分[1]。衣物护理具有高频、分散和需要反复接手的特点，因此其负担往往不是单次动作强度，而是对时间和注意力的持续切割。")
    add_body(doc, "传统流程中，用户需要在脏衣篮、洗衣机、阳台和衣柜之间多次往返。当洗涤程序结束时，用户必须及时接管后续环节；如果遗忘，湿衣可能长时间滞留在洗衣机内，带来异味、褶皱或重复洗涤。由此可见，真正需要解决的并非“让晾衣架自动升降”，而是让衣物在多个家庭空间之间自动完成流转。")
    add_table(doc, ["环节", "典型人工动作", "造成的负担"],
              [["洗前", "收集并搬运脏衣", "跨房间往返"],
               ["洗后", "取出湿衣并转运", "重量增加、易滴水"],
               ["晾晒", "抖开、穿架、逐件挂起", "重复精细操作"],
               ["收纳", "逐件收回、分类、再次挂放", "二次劳动与空间占用"]],
              [1400, 3600, 4072], header_fill=ORANGE_LIGHT)
    new_page(doc)

    # Page 5
    add_page_kicker(doc, "需求分析", "现有产品解决局部动作，衣循解决环节之间的断层。")
    add_title(doc, "1.2 现有方案局限与设计目标", 15, 2)
    add_table(doc, ["产品类型", "已解决问题", "仍存在的断点"],
              [["洗衣机", "清洗与脱水", "无法回收、转运和晾晒"],
               ["烘干机", "缩短干燥时间", "能耗较高，且不负责入柜"],
               ["智能晾衣架", "升降、照明、烘干", "仍需人工穿架和收衣"],
               ["清洁/配送机器人", "自主移动或物品配送", "缺少柔性衣物操作机构"],
               ["衣循", "移动、挂载、晾晒和收纳协同", "目标是形成完整衣物护理闭环"]],
              [1650, 2950, 4472], header_fill=BLUE_LIGHT)
    add_title(doc, "1.3 工程需求转化", 15, 2)
    add_numbered_items(doc, [
        "移动能力：能够在洗衣区、阳台和衣柜之间自主导航，适应门槛、地毯与阳台滑轨等家庭地形。",
        "操作能力：能够识别并稳定湿衣领口，完成衣架穿入与衣物挂载。",
        "晾晒能力：晾晒模块在移动时收拢，在阳台展开，并依据光照条件进行位置调整。",
        "收纳能力：晾晒结束后无需逐件取衣，伞状晾衣杆可与智能衣柜整杆对接。",
        "安全与交互：与家庭成员共处时具备动态避障、状态反馈、暂停和召回能力。"
    ])
    add_callout(doc, "核心设计命题", "如何让一个家庭机器人既能跨空间移动，又能操作柔性湿衣，并在晾晒结束后完成真正意义上的收纳闭环？", ORANGE_LIGHT, ORANGE)
    new_page(doc)

    # Page 6
    add_page_kicker(doc, "第2章", "以移动底盘为载体，将操作、晾晒和收纳组织为一个系统。")
    add_title(doc, "2 总体方案与系统架构", 16, 1)
    add_title(doc, "2.1 产品总体构型", 15, 2)
    add_picture(doc, product, 10.8, "图2-1 衣循机器人总体构型示意")
    add_table(doc, ["组成模块", "主要功能", "与其他模块的关系"],
              [["履带移动底盘", "全屋导航、越障与任务转运", "承载机械臂和晾晒结构"],
               ["双机械臂", "领口夹持、衣架穿入与湿衣挂载", "接收视觉目标与动作规划"],
               ["伞状晾晒模块", "收拢移动、展开晾晒与趋光定位", "与底盘共同完成阳台作业"],
               ["旋转智能衣柜", "仓位回转、整杆入柜与维护", "承接晾晒模块，形成收纳闭环"],
               ["衣物护理软件", "任务选择、状态展示与提醒", "向用户屏蔽复杂底层技术"]],
              [1900, 3000, 4172], header_fill=BLUE_LIGHT, font_size=10)
    new_page(doc)

    # Page 7
    add_page_kicker(doc, "总体方案", "感知、决策与执行三层共同完成家庭任务。")
    add_title(doc, "2.2 系统架构与完整任务流程", 15, 2)
    add_picture(doc, OUT / "ppt_figures" / "01_算法架构.png", 15.0, "图2-2 衣循系统算法与执行架构")
    add_body(doc, "系统采用三层架构。感知层接收语音指令、距离信息、环境地图、领口视觉特征与阳台光照信息；决策层完成语义目标解析、SLAM建图、全局路径规划、局部避障、机械臂轨迹规划和晾晒位置优化；执行层驱动履带底盘、机械臂、伞状晾晒机构和旋转衣柜。各模块通过任务状态机进行协调，避免某一机构未到位时提前触发下一动作。")
    add_picture(doc, floorplan, 8.2, "图2-3 家庭空间目标点示意")
    add_callout(doc, "完整闭环", "脏衣篮回收 → 洗衣机投放 → 湿衣挂载 → 阳台趋光晾晒 → 伞状晾衣杆整杆入柜。")
    new_page(doc)

    # Page 8
    add_page_kicker(doc, "第3章", "底盘不是附属部件，而是跨空间服务成立的基础。")
    add_title(doc, "3 移动底盘设计与导航算法", 16, 1)
    add_title(doc, "3.1 履带底盘与家庭地形适应", 15, 2)
    add_body(doc, "家庭场景虽然空间尺度较小，但通行条件并不简单。门槛、地毯、家具边缘、阳台滑轨及临时摆放物会造成离散高度变化和动态障碍。衣循采用履带差速底盘，并将地形类型映射为规划代价，使“可通行”不仅表示几何上没有墙体，还包含履带通过难度和载荷稳定性。")
    add_table(doc, ["地形类型", "规划含义", "控制策略"],
              [["普通地面", "低代价通行区", "常规速度"],
               ["地毯", "滚动阻力增加", "降低速度并保持直行"],
               ["门槛", "短时高度突变", "提高驱动力，限制转向"],
               ["阳台滑轨", "窄且具有落差", "正向跨越并限制横摆"],
               ["动态障碍", "人员或临时物品", "DWA局部绕行或停车"]],
              [1800, 3200, 4072], header_fill=ORANGE_LIGHT)
    add_body(doc, "底盘采用差速运动学模型，根据左右履带速度获得线速度和角速度。控制层将全局路径点转换为速度指令，并在接近机械臂作业点、阳台入口和衣柜对接区时降低速度，以提高定位和机构衔接的稳定性。")
    add_callout(doc, "设计边界", "当前底盘结果属于软件仿真验证；门槛高度、湿衣载荷下的制动距离和真实家庭噪声仍需通过样机试验标定。", LIGHT_GRAY, GRAY)
    new_page(doc)

    # Page 9
    add_page_kicker(doc, "导航算法", "语音目标、地图认知、全局规划和局部避障形成闭环。")
    add_title(doc, "3.2 自主导航算法", 15, 2)
    add_picture(doc, OUT / "ppt_figures" / "06_语音导航流程.png", 15.2, "图3-1 语音任务到运动执行的处理流程")
    add_title(doc, "3.2.1 占用栅格SLAM", 13, 3)
    add_body(doc, "系统采用Log-Odds形式维护占用栅格。激光或距离射线沿Bresenham路径更新自由栅格与占用栅格，更新关系表示为：L(m|zₜ)=clip[L(m|zₜ₋₁)+ΔL,Lmin,Lmax]。栅格概率用于判断墙体、家具和可通行区域。")
    add_title(doc, "3.2.2 融合地形代价的A*规划", 13, 3)
    add_body(doc, "全局规划评价函数为f(n)=g(n)+h(n)。其中g(n)累积路径距离和地形代价，h(n)采用目标点欧氏距离。门槛、地毯与滑轨赋予不同代价，使规划结果优先选择更稳定的家庭通道。")
    add_title(doc, "3.2.3 DWA局部避障", 13, 3)
    add_body(doc, "动态窗口法在可达速度空间内采样(v,ω)，预测短时轨迹，并综合朝向、目标距离、速度和障碍代价进行评分，从而对移动人员、临时物品等动态障碍做出减速、绕行或停车决策[3]。")
    new_page(doc)

    # Page 10
    add_page_kicker(doc, "验证结果", "用任务路径、地图探索和关键帧证明底盘具备连续执行能力。")
    add_title(doc, "3.3 底盘任务流转仿真", 15, 2)
    add_picture(doc, ASSETS / "chassis_storyboard.jpg", 15.2, "图3-2 底盘任务流转仿真关键帧")
    add_table(doc, ["语音任务", "目标点", "路径长度", "路径点数"],
              [["去脏衣篮收衣服", "脏衣篮", "1.53 m", "16"],
               ["把衣服放到洗衣机", "洗衣机", "2.03 m", "20"],
               ["去阳台晾晒", "阳台", "5.73 m", "51"],
               ["送到智能柜收纳", "智能衣柜", "1.68 m", "16"]],
              [3700, 1900, 1700, 1772], header_fill=BLUE_LIGHT)
    add_callout(doc, "阶段结果", "四段任务总路径长度为10.97 m，SLAM环境探索率为76.7%。仿真证明语义目标、地图、路径和运动执行能够形成完整软件链路。", ORANGE_LIGHT, ORANGE)
    new_page(doc)

    # Page 11
    add_page_kicker(doc, "第4章", "柔性湿衣不是刚性零件，挂载需要重新设计双臂分工。")
    add_title(doc, "4 双机械臂湿衣挂载系统", 16, 1)
    add_title(doc, "4.1 湿衣操作难点", 15, 2)
    add_body(doc, "湿衣具有柔性、形状不确定和摩擦状态变化明显等特征。衣领会在重力作用下塌陷，湿度增加后衣物质量上升，夹爪过度拉扯可能造成褶皱、滑脱或领口变形。因此，直接套用刚性物体抓取方案难以稳定完成挂衣任务。")
    add_table(doc, ["难点", "产生原因", "设计应对"],
              [["领口位置不稳定", "柔性变形和遮挡", "视觉定位领口区域并设置容错窗口"],
               ["衣架进入空间不足", "领口自然闭合", "一只机械臂夹持并稳定领口"],
               ["衣架易碰撞衣物", "穿入路径狭窄", "另一只机械臂持架沿规划轨迹进入"],
               ["湿衣易滑落", "质量增加、摩擦变化", "限制速度和夹持力，完成后再释放"]],
              [1900, 3300, 3872], header_fill=ORANGE_LIGHT)
    add_callout(doc, "最终动作策略", "左机械臂夹住并稳定领口；右机械臂拿着衣架，从领口开口方向穿入；衣架到达稳定位置后，两臂依次释放。")
    add_body(doc, "该分工避免两只机械臂同时拉扯领口，也使衣架运动轨迹具有明确的起点、通过窗口和终点，便于后续建立逆运动学、碰撞检测和力控制模型。")
    new_page(doc)

    # Page 12
    add_page_kicker(doc, "协同流程", "单臂夹领提供稳定约束，单臂持架完成主要操作。")
    add_title(doc, "4.2 双臂协同动作时序", 15, 2)
    add_picture(doc, ASSETS / "arm_storyboard.jpg", 15.2, "图4-1 单臂夹领、单臂持架的3D运动仿真关键帧")
    add_numbered_items(doc, [
        "视觉定位：提取领口候选区域，得到夹持点、衣架进入方向和目标位姿。",
        "夹领稳定：左机械臂接近领口边缘，夹爪闭合后保持位置，为穿架动作提供稳定边界。",
        "持架穿入：右机械臂抓持衣架挂钩附近区域，沿三次曲线插值轨迹进入领口。",
        "挂载完成：衣架到达肩部稳定位置，右臂释放衣架，左臂确认衣物未滑落后释放。"
    ])
    add_callout(doc, "仿真含义", "关键帧用于验证动作关系与空间可达性，不等同于真实湿衣力学实验。后续需要通过实物样机标定夹持力、视觉误差和衣架碰撞边界。", LIGHT_GRAY, GRAY)
    new_page(doc)

    # Page 13
    add_page_kicker(doc, "技术路线", "从视觉目标到关节轨迹，形成可复现的机械臂控制链路。")
    add_title(doc, "4.3 机械臂控制方法与安全约束", 15, 2)
    add_table(doc, ["处理阶段", "输入", "方法", "输出"],
              [["领口识别", "RGB/深度图像", "轮廓与关键点检测", "夹持点、开口方向"],
               ["任务分配", "目标点与衣架位姿", "左右臂角色约束", "夹领臂/持架臂任务"],
               ["轨迹生成", "起点、过渡点、终点", "三次插值与逆运动学", "连续关节轨迹"],
               ["协同控制", "双臂时序和安全距离", "状态机与互锁", "动作执行指令"],
               ["结果确认", "视觉/力反馈", "位置与滑落判断", "完成或重试"]],
              [1600, 2200, 2700, 2572], header_fill=BLUE_LIGHT)
    add_body(doc, "轨迹规划首先在笛卡尔空间定义接近点、夹持点、衣架进入点和最终挂载点，再通过逆运动学转换为关节角。为降低衣架划伤衣物或机械臂互碰风险，双臂工作空间设置安全包络：左臂夹领后保持低速，右臂仅在领口开口达到阈值后进入；任何一侧出现目标丢失、关节超限或距离过近时，状态机立即暂停。")
    add_body(doc, "控制策略优先保证稳定性而非速度。机械臂在接触衣物前采用位置控制，进入夹持与穿架阶段后降低速度，并预留力传感器或电流反馈接口。对于不同领型和衣物厚度，可通过调整夹持点间距、衣架进入角度和运动速度进行参数适配。")
    add_callout(doc, "后续实物指标", "领口定位误差、挂载成功率、单次动作时长、最大夹持力、双臂最小安全距离以及不同面料适应率。", ORANGE_LIGHT, ORANGE)
    new_page(doc)

    # Page 14
    add_page_kicker(doc, "第5章", "移动时收拢，作业时展开，让晾晒结构适应家庭空间。")
    add_title(doc, "5 伞状晾晒模块与趋光策略", 16, 1)
    add_title(doc, "5.1 伞状可展开结构", 15, 2)
    add_picture(doc, umbrella, 12.5, "图5-1 伞状晾晒模块结构示意")
    add_body(doc, "晾晒模块采用中心立柱与多根径向支杆组成的伞状结构。移动状态下支杆向立柱收拢，以降低横向尺寸并减小通过门框和家具间隙时的碰撞风险；到达阳台作业区后，支杆展开形成环形挂载空间，使衣物之间保持间距。立柱具备升降能力，可根据衣物长度和阳台高度调整晾晒位置。")
    add_table(doc, ["状态", "结构特征", "设计目的"],
              [["收拢状态", "支杆贴近中心立柱", "提高通过性，降低重心扰动"],
               ["展开状态", "支杆径向展开", "扩大挂载面积并保持衣物间距"],
               ["升降状态", "立柱高度可调", "适配不同衣长与阳台空间"],
               ["对接状态", "顶部接口与衣柜挂杆连接", "实现整杆转移与入柜"]],
              [1600, 3300, 4172], header_fill=ORANGE_LIGHT)
    new_page(doc)

    # Page 15
    add_page_kicker(doc, "趋光晾晒", "机器人不仅到达阳台，还继续寻找更有效的晾晒位置。")
    add_title(doc, "5.2 光照场建模与位置优化", 15, 2)
    add_picture(doc, OUT / "ppt_figures" / "05_趋光追踪.png", 15.2, "图5-2 阳台光照场与趋光路径示意")
    add_body(doc, "系统将太阳高度角、方位角、阳台朝向和局部阴影近似为时变光照场I(x,y,t)。在阳台可行域内，通过梯度搜索或离散候选点评分得到最优位置(x*,y*)=argmax I(x,y,t)。底盘只在阳台内进行小范围位移，避免频繁移动影响家庭使用。")
    add_table(doc, ["时刻", "最优位置", "光照评分", "控制含义"],
              [["09:00", "(7.0, 5.2)", "0.569", "完成初始趋光定位"],
               ["12:00", "(7.0, 5.2)", "0.608", "保持位置并延长有效日照"]],
              [1800, 2300, 2000, 2972], header_fill=BLUE_LIGHT)
    add_callout(doc, "设计价值", "传统自动晾衣方案通常以“到达阳台”为终点；衣循将光照有效性纳入决策，使自动化结果更贴近真实晾晒需求。")
    add_body(doc, "当前模型主要用于验证决策逻辑，尚未纳入天气突变、玻璃透射率、衣物遮挡和室内温湿度等因素。实物阶段可接入光照与温湿度传感器，对模型参数进行在线修正。")
    new_page(doc)

    # Page 16
    add_page_kicker(doc, "第6章", "整杆入柜是衣循区别于传统晾衣设备的关键结构创新。")
    add_title(doc, "6 旋转智能衣柜与整杆入柜", 16, 1)
    add_title(doc, "6.1 衣柜结构设计", 15, 2)
    add_picture(doc, OUT / "wardrobe_structure_annotated.png", 15.2, "图6-1 旋转智能衣柜结构标注图")
    add_body(doc, "衣柜内部设置四扇围绕中央回转轴布置的存衣空间，可通过转轴将目标仓位旋转至正面。柜体上方设置可调长度的伸缩挂杆，用于承接伞状晾衣杆。晾晒完成后，晾衣杆不需要拆分，直接挂接到伸缩杆并随目标仓位回转至柜内。")
    add_callout(doc, "核心创新", "衣物不再经历“逐件取下—分类—再次挂入衣柜”的二次操作，而是随晾衣杆整体完成从阳台到衣柜的转移。", ORANGE_LIGHT, ORANGE)
    new_page(doc)

    # Page 17
    add_page_kicker(doc, "整杆对接", "用明确的机构时序完成晾晒与收纳的无缝衔接。")
    add_title(doc, "6.2 整杆入柜工作原理", 15, 2)
    add_picture(doc, ASSETS / "wardrobe_storyboard.jpg", 15.2, "图6-2 伞状晾衣杆整杆入柜仿真关键帧")
    add_numbered_items(doc, [
        "仓位选择：中央转轴带动四扇存衣空间旋转，将目标仓位对准柜门。",
        "挂杆伸出：顶部伸缩挂杆向柜外伸出，并根据伞状晾衣杆接口位置调整长度。",
        "整杆对接：机器人将伞状晾衣杆整体挂入伸缩杆，确认接口稳定。",
        "回转收纳：伸缩杆回收，目标存衣仓旋转进入柜体，完成日常或换季存放。",
        "维护处理：根据衣物状态启动通风、除湿或紫外杀菌等辅助功能。"
    ])
    add_table(doc, ["对比项", "传统收衣", "衣循整杆入柜"],
              [["人工操作", "逐件取下并重新分类挂放", "确认任务后自动对接"],
               ["衣物状态", "多次抓取，易产生褶皱", "保持原挂载姿态"],
               ["时间占用", "持续人工参与", "仅需查看状态反馈"],
               ["空间管理", "衣柜与晾晒设备分离", "晾晒与收纳接口统一"]],
              [1700, 3600, 3772], header_fill=ORANGE_LIGHT)
    new_page(doc)

    # Page 18
    add_page_kicker(doc, "衣柜控制", "结构创新必须配合位置检测和互锁，才能可靠工作。")
    add_title(doc, "6.3 衣柜控制与安全设计", 15, 2)
    add_table(doc, ["控制对象", "检测信息", "安全措施"],
              [["中央回转轴", "仓位角度、转速", "到位锁止，柜门开启时限速"],
               ["顶部伸缩杆", "伸出长度、末端位置", "超程保护与负载检测"],
               ["晾衣杆接口", "对接到位、挂载重量", "未到位禁止回收与旋转"],
               ["柜门与人员", "门磁/距离检测", "人员接近时停止机构"],
               ["维护模块", "湿度、运行时间", "超温、超时和开门断电"]],
              [1900, 3100, 4072], header_fill=BLUE_LIGHT)
    add_body(doc, "衣柜控制采用分级互锁。只有当目标仓位到位、伸缩挂杆完成对准且晾衣杆接口确认稳定后，系统才允许执行回收动作；回收完成后，中央转轴才能旋转。柜门开启或检测到人员接近时，回转轴与伸缩机构进入低速或停止状态。")
    add_body(doc, "四扇存衣空间可分别对应日常区、待熨烫区、换季区和维护区。软件根据衣物类型、使用频率和柜内容量推荐仓位，但用户保留最终选择权。该方案使智能衣柜不只是储物容器，而是衣物护理闭环中的主动执行设备。")
    add_callout(doc, "待验证项目", "整杆对接允许误差、挂杆额定载荷、回转轴扭矩、柜内衣物摆动、接口脱落保护及四仓空间利用率。", LIGHT_GRAY, GRAY)
    new_page(doc)

    # Page 19
    add_page_kicker(doc, "第7章", "底盘、机械臂、晾晒机构和衣柜必须按统一状态机协同。")
    add_title(doc, "7 多模块协同控制与软件交互", 16, 1)
    add_title(doc, "7.1 任务状态机与异常处理", 15, 2)
    add_table(doc, ["状态", "进入条件", "主要动作", "异常处理"],
              [["任务接收", "语音/App确认", "解析目标与衣物类型", "意图不明确时二次确认"],
               ["底盘导航", "地图和目标有效", "规划路径并移动", "路径阻挡则重规划或停车"],
               ["机械臂挂载", "到达作业位", "夹领、持架、穿入", "视觉丢失则退回安全位"],
               ["趋光晾晒", "挂载完成", "展开并优化位置", "光照不足则采用通风策略"],
               ["衣柜对接", "晾晒结束", "伸缩挂杆对接入柜", "接口未到位则禁止回转"],
               ["任务完成", "衣物进入仓位", "记录状态并提醒用户", "异常状态保留人工接管"]],
              [1450, 2300, 2700, 2622], header_fill=BLUE_LIGHT, font_size=10)
    add_body(doc, "状态机将各模块动作分解为可检查的阶段，每个阶段均包含进入条件、完成条件和超时条件。这样可以避免底盘尚未稳定时机械臂提前动作，也能防止晾衣杆未挂牢时衣柜开始旋转。系统对用户显示的是“正在转运、正在挂晒、正在收纳”等生活化状态，而不是SLAM、关节角和控制器参数。")
    add_callout(doc, "安全原则", "默认安全停止、关键机构互锁、异常允许人工接管、任务状态全程可追溯。", ORANGE_LIGHT, ORANGE)
    new_page(doc)

    # Page 20
    add_page_kicker(doc, "用户交互", "面向家庭用户，界面应减少技术词，突出任务与结果。")
    add_title(doc, "7.2 家庭衣物护理软件设计", 15, 2)
    add_body(doc, "配套网页版App采用暖白、橙色和蓝色的家庭化视觉风格，主要服务于家庭日常使用，而非展示机器人底层参数。界面围绕“今天有哪些衣物、当前进行到哪一步、是否需要用户处理”三个问题组织信息。")
    add_table(doc, ["功能区", "展示内容", "用户价值"],
              [["今日护理", "待处理衣物、预计时间、当前位置", "快速了解今日任务"],
               ["衣物队列", "衣物类型、护理方式与优先级", "避免混洗和不当晾晒"],
               ["任务控制", "开始、暂停、召回与场景切换", "保留用户控制权"],
               ["晾晒提醒", "光照、通风、是否延长晾晒", "减少反复查看阳台"],
               ["衣柜提示", "容量、仓位和除湿状态", "提高收纳可见性"],
               ["记录与异常", "任务日志、失败原因、处理建议", "增强信任与可追溯性"]],
              [1800, 3500, 3772], header_fill=ORANGE_LIGHT)
    add_body(doc, "软件提供日常洗晒、阳台晾晒、换季收纳和安静模式。安静模式会降低底盘速度、机械动作速度和提示音量；换季模式则优先使用高密度仓位和维护功能。对于识别失败或对接异常，界面采用明确的解决建议，而非仅显示错误代码。")
    add_callout(doc, "交互原则", "技术隐藏在系统内部，用户只需要理解任务、进度、结果和是否需要接管。")
    new_page(doc)

    # Page 21
    add_page_kicker(doc, "第8章", "通过已有仿真证明链路可行，并明确下一步实物验证指标。")
    add_title(doc, "8 仿真验证、测试方案与风险分析", 16, 1)
    add_title(doc, "8.1 阶段成果与证据链", 15, 2)
    add_table(doc, ["模块", "当前证据", "可证明内容", "验证边界"],
              [["底盘", "任务GIF、SLAM/A*/DWA图", "软件导航链路可运行", "尚未完成实物越障与载荷测试"],
               ["机械臂", "3D运动仿真与关键帧", "动作分工和空间轨迹可表达", "尚未验证真实湿衣力学"],
               ["趋光晾晒", "光照场与最优点计算", "位置优化逻辑可运行", "模型参数需真实阳台标定"],
               ["智能衣柜", "结构标注图与整杆入柜仿真", "机构时序与接口概念可行", "需验证公差、载荷与锁止"],
               ["软件交互", "网页版App原型", "任务流程与用户信息架构", "需进行家庭用户可用性测试"]],
              [1550, 2550, 2650, 2322], header_fill=BLUE_LIGHT, font_size=9.8)
    add_body(doc, "现阶段成果重点证明系统架构、算法链路和机构动作关系具备一致性。报告不将仿真结果表述为实物性能，而是以此确定样机研制中的关键接口、控制时序和测试指标。")
    add_picture(doc, OUT / "ppt_figures" / "03_SLAM建图.png", 12.8, "图8-1 占用栅格SLAM探索结果")
    new_page(doc)

    # Page 22
    add_page_kicker(doc, "测试计划", "每个创新点都需要对应可量化的验收指标。")
    add_title(doc, "8.2 样机测试矩阵", 15, 2)
    add_table(doc, ["测试项目", "评价指标", "当前结果", "下一阶段目标"],
              [["家庭导航", "任务完成率、定位误差", "4段仿真任务完成", "在典型户型连续运行"],
               ["环境建图", "探索率、地图一致性", "探索率76.7%", "提高覆盖率与重复定位稳定性"],
               ["复杂地形", "最大门槛、滑轨通过率", "地形代价模型完成", "实物门槛与地毯测试"],
               ["湿衣挂载", "成功率、时长、夹持力", "3D动作仿真完成", "多种领型与面料测试"],
               ["趋光晾晒", "光照提升、定位误差", "最优点评分0.608", "接入光照传感器验证"],
               ["整杆入柜", "对接成功率、允许误差", "机构时序仿真完成", "制作接口和回转仓样机"],
               ["人机安全", "急停距离、互锁响应", "状态机逻辑完成", "人员接近与异常中断测试"]],
              [1800, 2700, 2200, 2372], header_fill=ORANGE_LIGHT, font_size=9.5)
    add_body(doc, "测试遵循“单模块验证—接口联调—整机连续任务”的顺序。首先分别验证底盘、机械臂、晾晒模块和衣柜；随后验证底盘到位与机械臂启动、晾衣杆与衣柜接口等跨模块条件；最后在真实家庭模拟环境中执行完整任务，并记录成功率、异常次数和人工接管原因。")
    add_callout(doc, "验收原则", "不以单次演示成功作为结论，应进行重复测试并报告均值、离散性和失败案例。", LIGHT_GRAY, GRAY)
    new_page(doc)

    # Page 23
    add_page_kicker(doc, "风险分析", "主动说明边界和改进措施，比回避问题更能建立可信度。")
    add_title(doc, "8.3 关键风险与应对措施", 15, 2)
    add_table(doc, ["风险", "可能后果", "原因", "应对措施"],
              [["领口识别失败", "无法挂衣", "遮挡、褶皱、光照变化", "多视角识别、人工确认、重试策略"],
               ["湿衣滑脱", "衣物掉落或拉扯", "夹持力不足、面料光滑", "力/电流反馈、软质夹爪、限速"],
               ["底盘重心变化", "转弯不稳", "晾晒结构展开或湿衣偏载", "展开时停车、限制速度、载荷估计"],
               ["衣柜对接偏差", "接口卡滞或脱落", "定位误差和机构公差", "导向结构、到位检测、机械锁止"],
               ["人员进入作业区", "碰撞风险", "家庭环境动态变化", "距离检测、低速模式、急停互锁"],
               ["任务链中断", "衣物滞留在中间状态", "网络、传感器或机构故障", "本地状态保存、断点恢复、人工接管"]],
              [1700, 2300, 2300, 2772], header_fill=BLUE_LIGHT, font_size=9.7)
    add_body(doc, "衣循涉及移动、操作和收纳多个机构，系统复杂度高于单一功能家电。设计中采用分层控制和状态互锁，确保任一模块异常时不会直接驱动后续机构。对于当前尚未完成实物验证的部分，报告采用“设计方案+仿真证据+测试计划”的表达，避免夸大成熟度。")
    add_callout(doc, "风险管理重点", "柔性衣物操作与整杆对接是最需要实物验证的两项技术，应优先制作缩比功能样机。", ORANGE_LIGHT, ORANGE)
    new_page(doc)

    # Page 24
    add_page_kicker(doc, "第9章", "创新不在单个算法，而在重新组织家庭衣物护理流程。")
    add_title(doc, "9 创新性、应用前景与实施路线", 16, 1)
    add_title(doc, "9.1 核心创新点", 15, 2)
    add_table(doc, ["创新点", "现有方式", "衣循方案", "对应证据"],
              [["全流程闭环", "设备完成局部动作，环节间依赖人工", "移动机器人串联洗、晒、收", "总体架构与任务流转仿真"],
               ["柔性湿衣挂载", "人工穿架或仅处理刚性物体", "单臂夹领、单臂持架穿入", "机械臂3D运动仿真"],
               ["趋光移动晾晒", "固定位置晾晒", "阳台内依据光照场优化位置", "趋光算法图与评分结果"],
               ["整杆入柜", "晾晒后逐件取衣再入柜", "伞状晾衣杆整体对接旋转衣柜", "衣柜结构图与收纳仿真"],
               ["家庭化交互", "展示底层参数或单设备控制", "围绕衣物、进度与提醒组织", "网页版App原型"]],
              [1750, 2500, 3000, 1822], header_fill=ORANGE_LIGHT, font_size=9.6)
    add_body(doc, "上述创新相互依赖：没有移动底盘，机械臂与晾晒模块无法连接不同空间；没有机械臂，衣物仍需人工穿架；没有整杆入柜，晾晒完成后仍存在最后一次人工接管。因此，衣循的主要创新价值体现为系统级闭环，而不是简单叠加若干常见功能。")
    add_callout(doc, "评审记忆点", "一只手夹领口，一只手拿衣架；晾晒完成后，整根伞状晾衣杆直接进入旋转衣柜。", ORANGE_LIGHT, ORANGE)
    new_page(doc)

    # Page 25
    add_page_kicker(doc, "应用前景", "从高频家庭家务切入，并向养老与专业洗护场景扩展。")
    add_title(doc, "9.2 目标用户与应用场景", 15, 2)
    add_table(doc, ["目标场景", "核心需求", "衣循价值"],
              [["双职工家庭", "减少下班后的重复家务", "自动衔接洗后转运、晾晒和收纳"],
               ["老年家庭", "降低搬运湿衣和反复弯腰", "提供移动、挂晒和低打扰提醒"],
               ["行动不便人群", "难以跨空间搬运与高处晾晒", "通过机器人完成主要物理操作"],
               ["大户型家庭", "洗衣区、阳台和衣柜距离较远", "自主导航减少往返"],
               ["养老/公寓机构", "衣物处理频繁、人员成本高", "多任务调度和标准化护理"],
               ["洗护服务机构", "需要挂载、转运和分类", "模块化扩展为柔性衣物操作平台"]],
              [1900, 3400, 3772], header_fill=BLUE_LIGHT)
    add_title(doc, "9.3 产品化约束", 15, 2)
    add_body(doc, "产品化需要在结构尺寸、成本、噪声、清洁维护和家庭审美之间取得平衡。首代样机不必覆盖所有衣物类型，应优先选择圆领衫、衬衫和毛巾等代表性对象，验证完整闭环后再扩展至裤装、裙装和特殊面料。衣柜模块可先制作单仓缩比样机，再扩展为四仓结构。")
    add_callout(doc, "市场切入策略", "先证明“洗衣机—阳台—衣柜”的连续任务，再逐步丰富衣物识别和护理策略。")
    new_page(doc)

    # Page 26
    add_page_kicker(doc, "实施路线", "以可验证的小步迭代降低多模块系统的研发风险。")
    add_title(doc, "9.4 样机迭代与知识产权规划", 15, 2)
    add_table(doc, ["阶段", "主要任务", "交付成果"],
              [["阶段一：单模块验证", "底盘实物导航；单臂夹领与持架试验；伸缩挂杆与单仓对接", "底盘样机、机械臂工装、衣柜对接样机"],
               ["阶段二：接口联调", "底盘到位后机械臂启动；晾衣杆与衣柜对接；状态机互锁", "半实物联调平台与测试报告"],
               ["阶段三：整机闭环", "在模拟家庭环境连续完成回收、投放、晾晒和收纳", "整机样机、完整演示视频"],
               ["阶段四：家庭测试", "噪声、交互、可靠性与可维护性评估", "用户反馈与产品化改进方案"]],
              [2000, 4800, 2272], header_fill=ORANGE_LIGHT, font_size=10)
    add_title(doc, "知识产权方向", 15, 2)
    add_numbered_items(doc, [
        "伞状晾衣杆与顶部伸缩挂杆的整杆对接结构。",
        "四扇旋转存衣空间及其仓位调度方法。",
        "单臂夹持领口、单臂持衣架穿入的双臂协同挂衣方法。",
        "面向家庭洗晒收纳流程的多模块状态机与控制方法。",
        "融合地形代价和趋光策略的家庭衣物护理机器人导航方法。"
    ])
    add_callout(doc, "原创性管理", "对公开材料、开源算法和自研结构分别建立来源清单；拟公开前优先完成专利检索与申请。", LIGHT_GRAY, GRAY)
    new_page(doc)

    # Page 27 conclusion
    add_page_kicker(doc, "结论", "用系统级闭环回答家庭衣物护理中的最后一公里问题。")
    add_title(doc, "结  论", 18, 1)
    add_body(doc, "本文面向家庭洗衣后仍需人工转运、挂晒和收纳的问题，提出衣循洗晒收纳一站式家庭服务机器人。系统以履带移动底盘连接洗衣机、阳台和智能衣柜，以双机械臂完成柔性湿衣领口夹持和衣架穿入，以伞状结构实现收拢移动、展开晾晒和趋光定位，并通过顶部伸缩挂杆与四仓旋转衣柜实现整杆入柜。")
    add_body(doc, "在算法与仿真方面，已建立语音目标解析、占用栅格SLAM、融合地形代价的A*路径规划、DWA局部避障和趋光搜索流程；底盘完成4段家庭任务仿真，总路径长度为10.97 m，环境探索率为76.7%。机械臂和衣柜分别完成3D挂载动作与整杆入柜时序仿真，为后续结构样机和控制系统实现提供了明确接口。")
    add_body(doc, "衣循的创新并非单一算法或机构，而是将移动、操作、晾晒和收纳统一到连续任务中。当前工作仍处于设计与仿真验证阶段，下一步将优先制作机械臂挂衣工装和衣柜对接缩比样机，开展领口识别误差、挂载成功率、接口允许偏差、载荷稳定性和家庭通行安全等实物测试。")
    add_callout(doc, "最终价值主张", "让用户不再围绕洗衣机、阳台和衣柜反复接手，让衣物护理从一串碎片化动作变成一次可完成、可查看、可接管的家庭服务。", ORANGE_LIGHT, ORANGE)
    new_page(doc)

    # Page 28 references
    add_title(doc, "参考文献", 18, 1)
    refs = [
        "[1] 国家统计局. 第三次全国时间利用调查公报（第二号）[EB/OL]. 2024.",
        "[2] Hart P E, Nilsson N J, Raphael B. A Formal Basis for the Heuristic Determination of Minimum Cost Paths[J]. IEEE Transactions on Systems Science and Cybernetics, 1968, 4(2): 100-107.",
        "[3] Fox D, Burgard W, Thrun S. The Dynamic Window Approach to Collision Avoidance[J]. IEEE Robotics & Automation Magazine, 1997, 4(1): 23-33.",
        "[4] Moravec H P, Elfes A. High Resolution Maps from Wide Angle Sonar[C]//Proceedings of the IEEE International Conference on Robotics and Automation. 1985: 116-121.",
        "[5] Siciliano B, Khatib O. Springer Handbook of Robotics[M]. 2nd ed. Springer, 2016.",
        "[6] Craig J J. Introduction to Robotics: Mechanics and Control[M]. 4th ed. Pearson, 2017.",
        "[7] 衣循项目组. 底盘移动算法说明、仿真脚本与阶段输出物[Z]. 2026.",
    ]
    for ref in refs:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.74)
        p.paragraph_format.first_line_indent = Cm(-0.74)
        p.paragraph_format.space_after = Pt(7)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        r = p.add_run(ref)
        set_run_font(r, FONT_CN, 11.5)
    add_title(doc, "附录A 主要软件与输出物", 15, 2)
    add_table(doc, ["内容", "文件/模块", "用途"],
              [["底盘算法", "chassis/*.py", "SLAM、路径规划、避障、趋光与语音任务"],
               ["底盘仿真", "simulate_chassis.py / chassis_demo.gif", "任务流转验证"],
               ["机械臂仿真", "create_arm_hanging_3d_sim.py", "双臂协同挂载验证"],
               ["衣柜仿真", "create_wardrobe_storage_sim.py", "整杆入柜机构时序验证"],
               ["交互原型", "衣循家庭衣物护理App.html", "家庭用户任务与状态交互"]],
              [1700, 3800, 3572], header_fill=BLUE_LIGHT, font_size=9.8)

    doc.core_properties.title = "衣循——洗晒收纳一站式家庭服务机器人 作品详细设计报告"
    doc.core_properties.subject = "第九届中国高校智能机器人创意大赛主题一作品详细设计报告"
    doc.core_properties.author = "衣循项目组"
    doc.core_properties.keywords = "家庭服务机器人, 洗晒收纳, 双机械臂, 自主导航, 智能衣柜"
    OUT.mkdir(exist_ok=True)
    doc.save(FINAL)
    print(FINAL.resolve())


if __name__ == "__main__":
    build()
