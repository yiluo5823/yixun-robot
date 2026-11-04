# tools · 文档与图表构建脚本（归档）

本目录保存生成 `docs/` 与 `assets/` 中成品的构建脚本，用于复现排版流程。它们不是运行仿真的必需依赖。

| 脚本 | 作用 | 依赖 |
| --- | --- | --- |
| `build_design_report.py` | 生成《作品详细设计报告》DOCX | `python-docx`、`Pillow`、`matplotlib` |
| `create_report_2x2_figures.py` | 生成报告用的 2×2 对比插图 | `matplotlib`、`Pillow` |
| `build_development_log.py` | 生成《产品开发日志》PDF | `reportlab`、`Pillow` |

安装构建依赖：

```bash
pip install python-docx reportlab matplotlib pillow
```

运行方式（在仓库根目录执行）：

```bash
python tools/build_development_log.py        # -> docs/衣循_产品开发日志.pdf
python tools/build_design_report.py          # -> docs/衣循_作品详细设计报告.docx
```

## 注意事项

- `build_design_report.py` 与 `build_development_log.py` 原本依赖项目工作区中的原始素材目录（`output/`、`outputs/manual-yixun-provincial/`）。这些素材体积较大，未随仓库分发。脚本已做兼容处理：缺失素材时回退到 `assets/figures/` 中的归档插图，或输出占位说明，因此成品版式可能与 `docs/` 中的归档版本存在细微差异。
- `build_design_report.py` 产出的 DOCX 需要另行用 Word / LibreOffice 导出 PDF。
