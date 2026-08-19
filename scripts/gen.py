#!/usr/bin/env python3
"""一键生成 SVG 配图：套用配色卡 + 多种排版 + 装饰元素 + 指定尺寸/比例 + 可选校验/渲染。

把「选配色卡 → 填文案 → 选版式 → 排版 → 校验 → 渲染」串成一条命令。
生成的 SVG 已内置：分区独立、留白、字体回退、无 emoji、对比度达标。

子命令（10 种版式）：
    cover         封面式（深底 + 标题 + 底部结论条），默认 900×383，支持 --align left/center
    infographic   信息图式（浅底 + 编号卡片），默认 900×520，支持 --cols 1/2
    quote         金句卡式（居中正文），默认 900×900
    compare       对比图式（左右两栏 VS），默认 900×560
    steps         横向步骤图（圆点连线流程），默认 900×380
    stats         数据卡式（大数字 + 标签），默认 900×420，支持 --cols N
    timeline      时间线式（竖线 + 事件），默认 900×560
    feature       两栏图文式（插图 + 要点），默认 900×480
    chart         图表式（bar 柱状 / donut 环形），默认 900×500
    flow          流程图式（方框 + 箭头），默认 900×400
    sizes         列出常用画布尺寸/比例速查

装饰元素（cover / quote / stats 支持）：
    --deco dots|circles|grid|diag   背景几何底纹（可选，默认无）

指定尺寸 / 比例（所有生成子命令都支持）：
    --size 1200x630      精确画布（宽x高）
    --aspect 16:9 --width 1200   按比例（宽:高），用 --width 定宽，高度自动算

用法示例：
    python3 gen.py cover --palette 深海蓝 --title "AI 编程工具横评" \
        --subtitle "实测" --badge "深度分析" --conclusion "一图看懂" \
        --align center --deco circles --font "LXGW WenKai" --check --render

    python3 gen.py timeline --palette 墨玉青 --title "项目里程碑" \
        --events "2024年|项目立项|确定方向" "2025年|研发完成|发布测试" "2026年|正式上线|全球发布" \
        --font "LXGW WenKai"

    python3 gen.py chart --palette 深海蓝 --title "市场份额" --chart-type donut \
        --data "A 产品:40" "B 产品:30" "C 产品:20" "其它:10" --font "LXGW WenKai"

    python3 gen.py chart --palette 静谧绿 --title "季度营收" --chart-type bar \
        --data "Q1:120" "Q2:180" "Q3:240" "Q4:320" --font "LXGW WenKai"

    python3 gen.py feature --palette 绛紫霞 --title "三大核心优势" \
        --points "更快:性能提升 3 倍" "更稳:可用性 99.9%" "更省:成本降低一半" --font "LXGW WenKai"

    python3 gen.py flow --palette 松石蓝绿 --title "处理流程" \
        --steps "提交申请" "系统审核" "结果通知" --font "LXGW WenKai"

通用参数：
    --palette NAME  配色卡名称（palette.py list 查看）
    --size WxH      画布尺寸，如 1200x630
    --aspect W:H    宽高比，如 16:9（配合 --width 定宽）
    --width N       --aspect 时的画布宽
    --font F        font-family（务必用 fc-match 验证过的中文字体）
    --out PATH      输出 SVG 路径
    --check         生成后用 check.py 校验（不达标 exit 1）
    --render        顺带导出 PNG（需 rsvg-convert）

依赖同目录 palette.py / layout.py / svgtext.py / check.py / contrast.py（纯 stdlib）。
"""
import argparse
import math
import os
import re
import shutil
import subprocess
import sys

from palette import find_palette, best_text, DEFAULT_FONT
from layout import wrap_text, center_x, center_y
from svgtext import text_width

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SIZES = [
    ("公众号封面", 900, 383, "2.35:1"),
    ("公众号封面(信息更密)", 900, 500, "1.8:1"),
    ("正文信息图", 900, 540, "5:3"),
    ("正方形金句卡", 900, 900, "1:1"),
    ("小红书配图", 900, 1200, "3:4"),
    ("社交分享 / OG 图", 1200, 630, "1.91:1"),
    ("横版 Banner", 1200, 675, "16:9"),
    ("竖版海报", 900, 1600, "9:16"),
]

DEFAULTS = {
    "cover": (900, 383), "infographic": (900, 520), "quote": (900, 900),
    "compare": (900, 560), "steps": (900, 380), "stats": (900, 420),
    "timeline": (900, 560), "feature": (900, 480), "chart": (900, 500),
    "flow": (900, 400), "poster": (900, 1200),
}

PIE_COLORS = ["primary", "accent", "warning", "success", "danger", "primary_soft"]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def _t(x, y, s, size, fill, font, bold=False, anchor="start"):
    w = ' font-weight="bold"' if bold else ""
    return (f'<text x="{x:g}" y="{y:g}" font-family="{font}" font-size="{size:g}"'
            f'{w} fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')


def resolve_canvas(args, default_w, default_h):
    if args.size:
        m = re.fullmatch(r"\s*(\d+)\s*[xX×,]\s*(\d+)\s*", args.size)
        if not m:
            sys.exit("--size 格式应为「宽x高」，如 1200x630")
        return int(m.group(1)), int(m.group(2))
    if args.aspect:
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[:：/]\s*(\d+(?:\.\d+)?)\s*", args.aspect)
        if not m:
            sys.exit("--aspect 格式应为「宽:高」，如 16:9")
        rw, rh = float(m.group(1)), float(m.group(2))
        w = args.width or default_w
        return int(w), int(round(w * rh / rw))
    return default_w, default_h


def deco(c, W, H, kind):
    """背景几何底纹。kind: dots / circles / grid / diag / none"""
    out = []
    if kind in ("", "none", None):
        return out
    if kind == "dots":
        step, r = 48, 2.5
        for x in range(step, W, step):
            for y in range(step, H, step):
                out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c["primary_soft"]}" opacity="0.18"/>')
    elif kind == "circles":
        out.append(f'<circle cx="{W * 0.85:g}" cy="{H * 0.2:g}" r="{min(W, H) * 0.35:g}" fill="{c["primary"]}" opacity="0.10"/>')
        out.append(f'<circle cx="{W * 0.08:g}" cy="{H * 0.85:g}" r="{min(W, H) * 0.25:g}" fill="{c["accent"]}" opacity="0.10"/>')
        out.append(f'<circle cx="{W * 0.95:g}" cy="{H * 0.9:g}" r="{min(W, H) * 0.15:g}" fill="{c["primary_soft"]}" opacity="0.12"/>')
    elif kind == "grid":
        step = 64
        for x in range(0, W, step):
            out.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="{c["primary_soft"]}" stroke-width="1" opacity="0.08"/>')
        for y in range(0, H, step):
            out.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="{c["primary_soft"]}" stroke-width="1" opacity="0.08"/>')
    elif kind == "diag":
        step = 56
        for x in range(-H, W, step):
            out.append(f'<line x1="{x}" y1="0" x2="{x + H}" y2="{H}" stroke="{c["primary_soft"]}" stroke-width="1" opacity="0.06"/>')
    return out


def build_cover(c, title, subtitle, badge, conclusion, footer, kicker, font, W, H, align="left", deco_kind="none"):
    M = 40
    center = (align == "center")
    band_h = max(56, min(96, round(H * 0.21)))
    band_y = H - band_h
    accent_w = round(W * 0.16)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')
    parts += deco(c, W, H, deco_kind)
    parts.append(f'<rect x="0" y="{band_y}" width="{W}" height="{band_h}" fill="{c["band"]}"/>')
    if not center:
        parts.append(f'<rect x="0" y="{band_y}" width="{accent_w}" height="{band_h}" fill="{c["primary"]}"/>')

    # 眉题（kicker）
    y0 = 110
    if kicker:
        kx = W / 2 if center else M
        anchor = "middle" if center else "start"
        parts.append(f'<rect x="{kx - 14:g}" y="62" width="28" height="4" rx="2" fill="{c["accent"]}"/>')
        parts.append(_t(kx + 20 if not center else kx, 74, kicker, 18, c["accent"], font, bold=True, anchor=anchor))
        y0 = 128

    size = 44
    lines = wrap_text(title, W - 2 * M, size)
    while len(lines) > 2 and size > 26:
        size -= 2
        lines = wrap_text(title, W - 2 * M, size)
    lh = 1.35
    for i, ln in enumerate(lines):
        parts.append(_t(W / 2 if center else M, y0 + i * size * lh, ln, size, c["light"], font, bold=True,
                        anchor="middle" if center else "start"))
    title_bottom = y0 + (len(lines) - 1) * size * lh

    y = title_bottom + 58
    if subtitle:
        parts.append(_t(W / 2 if center else M, y, subtitle, 26, c["primary_soft"], font, anchor="middle" if center else "start"))
        y += 50
    if badge:
        bh = 46
        if y + bh <= band_y - 12:
            tw = text_width(badge, 22)
            bw = tw + 44
            bx = (W - bw) / 2 if center else M
            parts.append(f'<rect x="{bx:g}" y="{y:g}" rx="23" width="{bw:g}" height="{bh:g}" fill="{c["accent"]}"/>')
            parts.append(_t(bx + bw / 2, center_y(y, bh, 22), badge, 22, best_text(c["accent"]), font, bold=True, anchor="middle"))
        else:
            print("[gen] 标题过长，徽章放不下已跳过", file=sys.stderr)

    if conclusion:
        parts.append(_t(W / 2 if center else accent_w + 30, center_y(band_y, band_h, 26), conclusion, 26, c["light"], font, bold=True,
                        anchor="middle" if center else "start"))
    if footer:
        parts.append(_t(W - M, center_y(band_y, band_h, 14), footer, 14, c["primary_soft"], font, anchor="end"))
    parts.append("</svg>")
    return "\n".join(parts)


def build_infographic(c, title, subtitle, points, conclusion, footer, kicker, font, W, H, cols=1):
    M = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>')
    parts.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="none" stroke="{c["border"]}" stroke-width="2"/>')

    off = 0
    if kicker:
        parts.append(f'<rect x="{M:g}" y="48" width="28" height="4" rx="2" fill="{c["primary"]}"/>')
        parts.append(_t(M + 40, 60, kicker, 16, c["primary"], font, bold=True))
        off = 30
    parts.append(_t(M, 74 + off, title, 32, c["ink"], font, bold=True))
    if subtitle:
        parts.append(_t(M, 106 + off, subtitle, 18, c["ink_muted"], font))

    top = 130 + off
    gap = 16
    card_h = 80
    reserve = 70 + (26 if footer else 0)
    max_rows = max(1, int((H - top - reserve) // (card_h + gap)))
    pts = list(points)
    if cols == 1:
        max_cards = max_rows
        col_w = W - 2 * M
    else:
        max_cards = max_rows * cols
        col_w = (W - 2 * M - (cols - 1) * gap) / cols
    if len(pts) > max_cards:
        print(f"[gen] 要点过多，截断到前 {max_cards} 个", file=sys.stderr)
        pts = pts[:max_cards]

    for i, pt in enumerate(pts):
        if ":" in pt:
            ttl, dsc = pt.split(":", 1)
        else:
            ttl, dsc = pt, ""
        r, cc = divmod(i, cols)
        y = top + r * (card_h + gap)
        x = M + cc * (col_w + gap)
        parts.append(f'<rect x="{x:g}" y="{y:g}" width="{col_w:g}" height="{card_h:g}" rx="12" fill="#ffffff" stroke="{c["border"]}"/>')
        cy = y + card_h / 2
        radius = 18 if cols == 1 else 16
        parts.append(f'<circle cx="{x + radius + 22:g}" cy="{cy:g}" r="{radius:g}" fill="{c["primary"]}"/>')
        parts.append(_t(x + radius + 22, center_y(cy - radius, 2 * radius, 20), str(i + 1), 20, best_text(c["primary"]), font, bold=True, anchor="middle"))
        tx = x + radius + 42
        parts.append(_t(tx, y + 38, ttl, 22 if cols == 1 else 20, c["ink"], font, bold=True))
        if dsc:
            parts.append(_t(tx, y + 62, dsc, 16 if cols == 1 else 14, c["ink_muted"], font))

    concl_y = top + ((len(pts) + cols - 1) // cols) * (card_h + gap) + 8
    parts.append(f'<rect x="{M:g}" y="{concl_y:g}" width="{W - 2 * M:g}" height="44" rx="8" fill="{c["bg"]}"/>')
    if conclusion:
        parts.append(_t(M + 20, center_y(concl_y, 44, 20), conclusion, 20, c["light"], font, bold=True))
    if footer:
        fy = H - 14
        parts.append(f'<line x1="{M}" y1="{fy - 14}" x2="{W - M}" y2="{fy - 14}" stroke="{c["border"]}" stroke-width="1"/>')
        parts.append(_t(W - M, fy, footer, 12, c["ink_muted"], font, anchor="end"))
    parts.append("</svg>")
    return "\n".join(parts)


def build_quote(c, text, author, footer, kicker, font, W, H, deco_kind="none"):
    M = 80
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')
    parts += deco(c, W, H, deco_kind)
    bar_y = H * 0.14
    if kicker:
        parts.append(_t(W / 2, bar_y - 26, kicker, 18, c["accent"], font, bold=True, anchor="middle"))
    parts.append(f'<rect x="{W / 2 - 40:g}" y="{bar_y:g}" width="80" height="6" rx="3" fill="{c["accent"]}"/>')

    size = 56
    maxw = W - 2 * M - 60
    lines = wrap_text(text, maxw, size)
    while len(lines) > 4 and size > 30:
        size -= 2
        lines = wrap_text(text, maxw, size)
    lh = 1.6
    block_h = len(lines) * size * lh
    y0 = (H - block_h) / 2 + 20
    for i, ln in enumerate(lines):
        parts.append(_t(W / 2, y0 + i * size * lh, ln, size, c["light"], font, bold=True, anchor="middle"))
    if author:
        parts.append(_t(W / 2, y0 + block_h + 60, author, 26, c["primary_soft"], font, anchor="middle"))
    if footer:
        parts.append(_t(W / 2, H - 40, footer, 14, c["primary_soft"], font, anchor="middle"))
    parts.append("</svg>")
    return "\n".join(parts)


def build_compare(c, title, left, right, left_points, right_points, conclusion, font, W, H):
    M = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>')
    parts.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="none" stroke="{c["border"]}" stroke-width="2"/>')
    parts.append(_t(M, 62, title, 30, c["ink"], font, bold=True))
    parts.append(f'<rect x="{M:g}" y="78" width="56" height="4" rx="2" fill="{c["primary"]}"/>')

    col_top = 100
    concl_h = 48
    col_h = H - col_top - concl_h - 30
    gap = 76
    col_w = (W - 2 * M - gap) / 2
    left_x = M
    right_x = M + col_w + gap

    def column(x, head, pts, head_color, dot_color):
        parts.append(f'<rect x="{x:g}" y="{col_top:g}" width="{col_w:g}" height="{col_h:g}" rx="14" fill="#ffffff" stroke="{c["border"]}"/>')
        parts.append(_t(x + 26, col_top + 42, head, 22, c["ink"], font, bold=True))
        parts.append(f'<rect x="{x + 26:g}" y="{col_top + 54:g}" width="44" height="4" rx="2" fill="{head_color}"/>')
        by = col_top + 84
        maxw = col_w - 52
        for p in pts:
            if by + 24 > col_top + col_h - 14:
                break
            parts.append(f'<circle cx="{x + 30:g}" cy="{by - 5:g}" r="5" fill="{dot_color}"/>')
            ln = wrap_text(p, maxw, 16)
            ty = by
            for line in ln[:2]:
                parts.append(_t(x + 44, ty, line, 16, c["ink"], font))
                ty += 24
            by += 24 * len(ln[:2]) + 12

    column(left_x, left, left_points, c["primary"], c["primary"])
    column(right_x, right, right_points, c["accent"], c["accent"])

    vsy = col_top + col_h / 2
    parts.append(f'<circle cx="{W / 2:g}" cy="{vsy:g}" r="28" fill="{c["bg"]}"/>')
    parts.append(_t(W / 2, vsy + 9, "VS", 22, c["light"], font, bold=True, anchor="middle"))

    cy = H - concl_h - 16
    parts.append(f'<rect x="{M:g}" y="{cy:g}" width="{W - 2 * M:g}" height="{concl_h:g}" rx="10" fill="{c["bg"]}"/>')
    if conclusion:
        parts.append(_t(W / 2, center_y(cy, concl_h, 22), conclusion, 22, c["light"], font, bold=True, anchor="middle"))
    parts.append("</svg>")
    return "\n".join(parts)


def build_steps(c, title, steps, font, W, H):
    M = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>')
    parts.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="none" stroke="{c["border"]}" stroke-width="2"/>')
    parts.append(_t(M, 62, title, 30, c["ink"], font, bold=True))
    parts.append(f'<rect x="{M:g}" y="78" width="56" height="4" rx="2" fill="{c["primary"]}"/>')

    n = len(steps)
    if n == 0:
        parts.append("</svg>")
        return "\n".join(parts)
    gap = 20
    card_w = (W - 2 * M - (n - 1) * gap) / n
    cy = 158
    r = 32
    for i, s in enumerate(steps):
        ttl, dsc = (s.split(":", 1) + [""])[:2] if ":" in s else (s, "")
        cx = M + i * (card_w + gap) + card_w / 2
        if i < n - 1:
            nx = M + (i + 1) * (card_w + gap) + card_w / 2
            parts.append(f'<line x1="{cx + r + 10:g}" y1="{cy:g}" x2="{nx - r - 10:g}" y2="{cy:g}" stroke="{c["accent"]}" stroke-width="3" stroke-dasharray="6 6"/>')
        parts.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{c["primary"]}"/>')
        parts.append(_t(cx, center_y(cy - r, 2 * r, 30), str(i + 1), 30, best_text(c["primary"]), font, bold=True, anchor="middle"))
        ty = cy + r + 32
        for ln in wrap_text(ttl, card_w - 12, 20)[:2]:
            parts.append(_t(cx, ty, ln, 20, c["ink"], font, bold=True, anchor="middle"))
            ty += 27
        if dsc:
            for ln in wrap_text(dsc, card_w - 12, 14)[:2]:
                parts.append(_t(cx, ty, ln, 14, c["ink_muted"], font, anchor="middle"))
                ty += 21
    parts.append("</svg>")
    return "\n".join(parts)


def build_stats(c, title, stats, conclusion, font, W, H, cols=0, deco_kind="none"):
    M = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')
    parts += deco(c, W, H, deco_kind)
    parts.append(_t(M, 66, title, 30, c["light"], font, bold=True))
    parts.append(f'<rect x="{M:g}" y="82" width="56" height="4" rx="2" fill="{c["primary"]}"/>')

    n = len(stats)
    if n == 0:
        parts.append("</svg>")
        return "\n".join(parts)
    cols = cols or min(n, 4)
    rows = (n + cols - 1) // cols
    gap = 20
    top = 118
    card_h = 130
    card_w = (W - 2 * M - (cols - 1) * gap) / cols
    for i, st in enumerate(stats):
        num, label = (st.split(":", 1) + [""])[:2] if ":" in st else (st, "")
        r, cc = divmod(i, cols)
        x = M + cc * (card_w + gap)
        y = top + r * (card_h + gap)
        parts.append(f'<rect x="{x:g}" y="{y:g}" width="{card_w:g}" height="{card_h:g}" rx="14" fill="{c["band"]}"/>')
        parts.append(_t(x + 20, y + card_h / 2 - 2, num, 40, c["light"], font, bold=True))
        if label:
            parts.append(_t(x + 20, y + card_h / 2 + 26, label, 16, c["primary_soft"], font))

    if conclusion:
        cy = top + rows * (card_h + gap) - gap + 8
        parts.append(_t(M, center_y(cy, 36, 18), conclusion, 18, c["primary_soft"], font, bold=True))
    parts.append("</svg>")
    return "\n".join(parts)


def build_timeline(c, title, events, font, W, H):
    M = 60
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>')
    parts.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="none" stroke="{c["border"]}" stroke-width="2"/>')
    parts.append(_t(M, 62, title, 30, c["ink"], font, bold=True))
    parts.append(f'<rect x="{M:g}" y="78" width="56" height="4" rx="2" fill="{c["primary"]}"/>')

    n = len(events)
    if n == 0:
        parts.append("</svg>")
        return "\n".join(parts)
    lx = M + 14
    top = 120
    line_h = H - top - 40
    parts.append(f'<line x1="{lx}" y1="{top}" x2="{lx}" y2="{top + line_h}" stroke="{c["border"]}" stroke-width="3"/>')
    gap = line_h / n
    for i, ev in enumerate(events):
        seg = ev.split("|", 2)
        if len(seg) == 3:
            date, ttl, dsc = seg
        elif len(seg) == 2:
            date, ttl, dsc = seg[0], seg[1], ""
        else:
            date, ttl, dsc = "", ev, ""
        y = top + i * gap + 22
        parts.append(f'<circle cx="{lx}" cy="{y - 5}" r="8" fill="{c["primary"]}"/>')
        parts.append(f'<circle cx="{lx}" cy="{y - 5}" r="3.5" fill="{c["surface"]}"/>')
        if date:
            parts.append(_t(lx + 30, y, date, 15, c["primary"], font, bold=True))
        parts.append(_t(lx + 30, y + 30, ttl, 21, c["ink"], font, bold=True))
        if dsc:
            parts.append(_t(lx + 30, y + 54, dsc, 15, c["ink_muted"], font))
    parts.append("</svg>")
    return "\n".join(parts)


def build_feature(c, title, subtitle, points, font, W, H, image_side="left"):
    M = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>')
    parts.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="none" stroke="{c["border"]}" stroke-width="2"/>')

    panel_w = round(W * 0.40)
    panel_x = M if image_side == "left" else W - M - panel_w
    text_x = M + panel_w + 40 if image_side == "left" else M
    text_w = W - M - text_x
    top = 60
    panel_h = H - 2 * top

    # 左侧插图面板：抽象矢量图形
    parts.append(f'<rect x="{panel_x:g}" y="{top:g}" width="{panel_w:g}" height="{panel_h:g}" rx="18" fill="{c["band"]}"/>')
    icx = panel_x + panel_w / 2
    icy = top + panel_h / 2
    parts.append(f'<circle cx="{icx:g}" cy="{icy:g}" r="{panel_w * 0.28:g}" fill="{c["primary"]}"/>')
    parts.append(f'<circle cx="{icx:g}" cy="{icy:g}" r="{panel_w * 0.28:g}" fill="none" stroke="{c["primary_soft"]}" stroke-width="3" opacity="0.5"/>')
    parts.append(f'<circle cx="{icx - panel_w * 0.34:g}" cy="{icy - panel_w * 0.2:g}" r="{panel_w * 0.07:g}" fill="{c["accent"]}"/>')
    parts.append(f'<circle cx="{icx + panel_w * 0.3:g}" cy="{icy + panel_w * 0.24:g}" r="{panel_w * 0.05:g}" fill="{c["primary_soft"]}"/>')
    parts.append(_spark(icx, icy, panel_w * 0.24, c["light"]))

    # 右侧文字
    parts.append(_t(text_x, top + 40, title, 30, c["ink"], font, bold=True))
    parts.append(f'<rect x="{text_x:g}" y="{top + 56:g}" width="56" height="4" rx="2" fill="{c["primary"]}"/>')
    yy = top + 90
    if subtitle:
        parts.append(_t(text_x, yy, subtitle, 18, c["ink_muted"], font))
        yy += 44
    for p in points:
        ttl, dsc = (p.split(":", 1) + [""])[:2] if ":" in p else (p, "")
        parts.append(f'<circle cx="{text_x + 8:g}" cy="{yy - 5:g}" r="5" fill="{c["primary"]}"/>')
        parts.append(_t(text_x + 24, yy, ttl, 20, c["ink"], font, bold=True))
        if dsc:
            parts.append(_t(text_x + 24, yy + 26, dsc, 15, c["ink_muted"], font))
            yy += 58
        else:
            yy += 38
    parts.append("</svg>")
    return "\n".join(parts)


def _spark(cx, cy, R, fill):
    """纯矢量四角星（高光图标，避免 emoji 字形）。"""
    pts = []
    for i in range(8):
        ang = math.pi * i / 4 - math.pi / 2
        rad = R if i % 2 == 0 else R * 0.35
        pts.append(f"{cx + rad * math.cos(ang):.1f},{cy + rad * math.sin(ang):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}"/>'


def _pie_arc(cx, cy, r, a0, a1):
    def pt(ang):
        rad = math.radians(ang - 90)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)
    x0, y0 = pt(a0)
    x1, y1 = pt(a1)
    large = 1 if (a1 - a0) > 180 else 0
    return f'M {cx:g} {cy:g} L {x0:.2f} {y0:.2f} A {r:g} {r:g} 0 {large} 1 {x1:.2f} {y1:.2f} Z'


def build_chart(c, title, chart_type, data, font, W, H):
    M = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>')
    parts.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="none" stroke="{c["border"]}" stroke-width="2"/>')
    parts.append(_t(M, 62, title, 30, c["ink"], font, bold=True))
    parts.append(f'<rect x="{M:g}" y="78" width="56" height="4" rx="2" fill="{c["primary"]}"/>')

    items = []
    for d in data:
        if ":" in d:
            label, val = d.split(":", 1)
        else:
            label, val = d, "1"
        try:
            val = float(val.strip())
        except ValueError:
            val = 1
        items.append((label, val))

    if chart_type == "bar":
        top = 120
        maxv = max((v for _, v in items), default=1) or 1
        bar_h = 30
        gap = 24
        for i, (label, v) in enumerate(items):
            y = top + i * (bar_h + gap)
            parts.append(_t(M, y + 20, label, 17, c["ink"], font))
            bw = max(20, (W - 2 * M - 240) * (v / maxv))
            color = c[PIE_COLORS[i % len(PIE_COLORS)]]
            parts.append(f'<rect x="{M + 140:g}" y="{y:g}" width="{bw:g}" height="{bar_h:g}" rx="6" fill="{color}"/>')
            parts.append(_t(M + 140 + bw + 12, y + 20, f"{v:g}", 17, c["ink"], font, bold=True))
    else:  # donut
        cx = W * 0.32
        cy = H / 2 + 10
        R = min(W, H) * 0.30
        total = sum(v for _, v in items) or 1
        a = 0
        for i, (label, v) in enumerate(items):
            sweep = v / total * 360
            color = c[PIE_COLORS[i % len(PIE_COLORS)]]
            parts.append(f'<path d="{_pie_arc(cx, cy, R, a, a + sweep)}" fill="{color}"/>')
            a += sweep
        parts.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{R * 0.55:g}" fill="{c["surface"]}"/>')
        parts.append(_t(cx, cy - 4, f"{total:g}", 40, c["ink"], font, bold=True, anchor="middle"))
        parts.append(_t(cx, cy + 24, "总量", 15, c["ink_muted"], font, anchor="middle"))
        # 图例
        lx = W * 0.60
        ly = 150
        for i, (label, v) in enumerate(items):
            color = c[PIE_COLORS[i % len(PIE_COLORS)]]
            parts.append(f'<rect x="{lx:g}" y="{ly - 12:g}" width="16" height="16" rx="3" fill="{color}"/>')
            parts.append(_t(lx + 24, ly, label, 16, c["ink"], font))
            parts.append(_t(lx + 200, ly, f"{v / total * 100:.0f}%", 16, c["ink"], font, bold=True))
            ly += 34
    parts.append("</svg>")
    return "\n".join(parts)


def build_flow(c, title, steps, font, W, H):
    M = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>')
    parts.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="none" stroke="{c["border"]}" stroke-width="2"/>')
    parts.append(_t(M, 62, title, 30, c["ink"], font, bold=True))
    parts.append(f'<rect x="{M:g}" y="78" width="56" height="4" rx="2" fill="{c["primary"]}"/>')

    n = len(steps)
    if n == 0:
        parts.append("</svg>")
        return "\n".join(parts)
    gap = 24
    box_w = (W - 2 * M - (n - 1) * gap) / n
    box_h = 96
    cy = 200
    for i, s in enumerate(steps):
        ttl, dsc = (s.split(":", 1) + [""])[:2] if ":" in s else (s, "")
        x = M + i * (box_w + gap)
        y = cy - box_h / 2
        color = c[PIE_COLORS[i % len(PIE_COLORS)]]
        parts.append(f'<rect x="{x:g}" y="{y:g}" width="{box_w:g}" height="{box_h:g}" rx="12" fill="#ffffff" stroke="{c["border"]}"/>')
        parts.append(f'<rect x="{x:g}" y="{y:g}" width="{box_w:g}" height="8" rx="4" fill="{color}"/>')
        parts.append(_t(x + box_w / 2, y + 46, ttl, 20, c["ink"], font, bold=True, anchor="middle"))
        if dsc:
            parts.append(_t(x + box_w / 2, y + 70, dsc, 14, c["ink_muted"], font, anchor="middle"))
        if i < n - 1:
            nx = M + (i + 1) * (box_w + gap)
            ax = x + box_w + 4
            parts.append(f'<path d="M {ax} {cy} L {ax + 8} {cy} M {ax + 2} {cy - 5} L {ax + 8} {cy} L {ax + 2} {cy + 5}" stroke="{c["accent"]}" stroke-width="3" fill="none" stroke-linecap="round"/>')
    parts.append("</svg>")
    return "\n".join(parts)


def build_poster(c, title, kicker, number, points, footer, font, W, H, deco_kind="none"):
    """杂志风海报：眉题 + 大标题 + 大数字高亮 + 目录式内容 + 页脚，非套路构图。"""
    M = 50
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')
    parts += deco(c, W, H, deco_kind)

    y = 90
    if kicker:
        parts.append(f'<rect x="{M:g}" y="{y - 14:g}" width="30" height="4" rx="2" fill="{c["accent"]}"/>')
        parts.append(_t(M + 42, y, kicker, 20, c["accent"], font, bold=True))
        y += 46

    size = 56
    lines = wrap_text(title, W - 2 * M, size)
    while len(lines) > 3 and size > 34:
        size -= 4
        lines = wrap_text(title, W - 2 * M, size)
    lh = 1.3
    for i, ln in enumerate(lines):
        parts.append(_t(M, y + i * size * lh, ln, size, c["light"], font, bold=True))
    title_bottom = y + (len(lines) - 1) * size * lh

    if number:
        nbase = title_bottom + 130
        parts.append(_t(M, nbase, number, 100, c["primary_soft"], font, bold=True))
        parts.append(f'<rect x="{M:g}" y="{nbase + 40:g}" width="{W - 2 * M:g}" height="3" fill="{c["primary"]}" opacity="0.4"/>')
        ty = nbase + 82
    else:
        parts.append(f'<rect x="{M:g}" y="{title_bottom + 36:g}" width="{W - 2 * M:g}" height="3" fill="{c["primary"]}" opacity="0.4"/>')
        ty = title_bottom + 72

    for i, p in enumerate(points):
        if ty + 30 > H - 70:
            break
        parts.append(_t(M, ty, f"{i + 1:02d}", 24, c["primary"], font, bold=True))
        parts.append(_t(M + 56, ty, p, 20, c["light"], font))
        parts.append(f'<line x1="{M}" y1="{ty + 12}" x2="{W - M}" y2="{ty + 12}" stroke="{c["primary_soft"]}" stroke-width="1" opacity="0.25"/>')
        ty += 48

    if footer:
        parts.append(_t(M, H - 40, footer, 14, c["primary_soft"], font))
    parts.append("</svg>")
    return "\n".join(parts)


def _palette_or_exit(name):
    p = find_palette(name)
    if not p:
        sys.exit(f"未找到配色卡「{name}」，用 palette.py list 查看可用名称")
    return p["colors"]


def _finish(out, do_check, do_render, font):
    if do_check:
        r = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "check.py"), out, "--margin", "40"], cwd=SCRIPT_DIR)
        if r.returncode != 0:
            sys.exit(f"check.py 校验未通过（{out}），请按上面提示调整")
        print("check.py 校验通过 ✅")
    if do_render:
        if shutil.which("rsvg-convert"):
            png = os.path.splitext(out)[0] + ".png"
            subprocess.run(["rsvg-convert", "-w", "900", out, "-o", png], check=True)
            print(f"已导出 PNG: {png}")
        else:
            print("[gen] 未找到 rsvg-convert，跳过 PNG 导出", file=sys.stderr)


def _write(out, svg, kind, W, H, args):
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"已生成{kind}: {out}  ({W}x{H})")
    _finish(out, args.check, args.render, args.font)


def cmd_cover(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["cover"])
    svg = build_cover(c, args.title, args.subtitle or "", args.badge or "", args.conclusion or "",
                      args.footer or "", args.kicker or "", args.font, W, H, args.align, args.deco)
    _write(args.out, svg, "封面", W, H, args)


def cmd_infographic(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["infographic"])
    svg = build_infographic(c, args.title, args.subtitle or "", args.points, args.conclusion or "",
                            args.footer or "", args.kicker or "", args.font, W, H, args.cols)
    _write(args.out, svg, "信息图", W, H, args)


def cmd_quote(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["quote"])
    svg = build_quote(c, args.text, args.author or "", args.footer or "", args.kicker or "", args.font, W, H, args.deco)
    _write(args.out, svg, "金句卡", W, H, args)


def cmd_compare(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["compare"])
    svg = build_compare(c, args.title, args.left, args.right, args.left_points, args.right_points, args.conclusion or "", args.font, W, H)
    _write(args.out, svg, "对比图", W, H, args)


def cmd_steps(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["steps"])
    svg = build_steps(c, args.title, args.steps, args.font, W, H)
    _write(args.out, svg, "步骤图", W, H, args)


def cmd_stats(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["stats"])
    svg = build_stats(c, args.title, args.stats, args.conclusion or "", args.font, W, H, args.cols, args.deco)
    _write(args.out, svg, "数据卡", W, H, args)


def cmd_timeline(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["timeline"])
    svg = build_timeline(c, args.title, args.events, args.font, W, H)
    _write(args.out, svg, "时间线", W, H, args)


def cmd_feature(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["feature"])
    svg = build_feature(c, args.title, args.subtitle or "", args.points, args.font, W, H, args.side)
    _write(args.out, svg, "两栏图文", W, H, args)


def cmd_chart(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["chart"])
    svg = build_chart(c, args.title, args.chart_type, args.data, args.font, W, H)
    _write(args.out, svg, "图表", W, H, args)


def cmd_flow(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["flow"])
    svg = build_flow(c, args.title, args.steps, args.font, W, H)
    _write(args.out, svg, "流程图", W, H, args)


def cmd_poster(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["poster"])
    svg = build_poster(c, args.title, args.kicker or "", args.number or "", args.points, args.footer or "", args.font, W, H, args.deco)
    _write(args.out, svg, "海报", W, H, args)


def cmd_sizes(args):
    print(f"常用画布尺寸/比例（共 {len(SIZES)} 个）\n")
    print(f"{'用途':<18}{'尺寸':<14}{'比例'}")
    print("-" * 44)
    for name, w, h, ratio in SIZES:
        print(f"{name:<18}{w}x{h:<10}{ratio}")
    print("\n用法：gen.py <类型> --size 宽x高  或  --aspect 宽:高 --width 宽")


def main():
    ap = argparse.ArgumentParser(description="一键生成 SVG 配图（配色卡 + 10 种版式 + 装饰 + 指定尺寸）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(sp):
        sp.add_argument("--palette", required=True, help="配色卡名称")
        sp.add_argument("--size", default="", help="画布尺寸 宽x高，如 1200x630")
        sp.add_argument("--aspect", default="", help="宽高比 宽:高，如 16:9（配合 --width）")
        sp.add_argument("--width", type=int, default=0, help="--aspect 时的画布宽")
        sp.add_argument("--font", default=DEFAULT_FONT, help="font-family（用 fc-match 验证过的中文字体）")
        sp.add_argument("--out", help="输出 SVG 路径")
        sp.add_argument("--check", action="store_true", help="生成后用 check.py 校验")
        sp.add_argument("--render", action="store_true", help="顺带导出 PNG（需 rsvg-convert）")

    def add_deco(sp):
        sp.add_argument("--deco", default="none", choices=["none", "dots", "circles", "grid", "diag"], help="背景几何底纹")

    sp_cover = sub.add_parser("cover", help="封面式（默认 900×383）")
    sp_cover.add_argument("--title", required=True)
    sp_cover.add_argument("--subtitle", default="")
    sp_cover.add_argument("--badge", default="")
    sp_cover.add_argument("--conclusion", default="")
    sp_cover.add_argument("--kicker", default="", help="眉题（标题上方的小标签）")
    sp_cover.add_argument("--footer", default="", help="页脚（底部元信息，如来源/日期）")
    sp_cover.add_argument("--align", default="left", choices=["left", "center"])
    add_deco(sp_cover)
    add_common(sp_cover)
    sp_cover.set_defaults(func=cmd_cover)

    sp_info = sub.add_parser("infographic", help="信息图式（默认 900×520）")
    sp_info.add_argument("--title", required=True)
    sp_info.add_argument("--subtitle", default="")
    sp_info.add_argument("--points", nargs="*", default=[])
    sp_info.add_argument("--conclusion", default="")
    sp_info.add_argument("--kicker", default="", help="眉题（标题上方小标签）")
    sp_info.add_argument("--footer", default="", help="页脚（底部元信息）")
    sp_info.add_argument("--cols", type=int, default=1, choices=[1, 2], help="卡片列数 1/2")
    add_common(sp_info)
    sp_info.set_defaults(func=cmd_infographic)

    sp_quote = sub.add_parser("quote", help="金句卡式（默认 900×900）")
    sp_quote.add_argument("--text", required=True)
    sp_quote.add_argument("--author", default="")
    sp_quote.add_argument("--kicker", default="", help="眉题（正文上方小标签）")
    sp_quote.add_argument("--footer", default="", help="页脚（底部元信息）")
    add_deco(sp_quote)
    add_common(sp_quote)
    sp_quote.set_defaults(func=cmd_quote)

    sp_compare = sub.add_parser("compare", help="对比图式（默认 900×560）")
    sp_compare.add_argument("--title", required=True)
    sp_compare.add_argument("--left", required=True)
    sp_compare.add_argument("--right", required=True)
    sp_compare.add_argument("--left-points", nargs="*", default=[])
    sp_compare.add_argument("--right-points", nargs="*", default=[])
    sp_compare.add_argument("--conclusion", default="")
    add_common(sp_compare)
    sp_compare.set_defaults(func=cmd_compare)

    sp_steps = sub.add_parser("steps", help="横向步骤图（默认 900×380）")
    sp_steps.add_argument("--title", required=True)
    sp_steps.add_argument("--steps", nargs="*", default=[])
    add_common(sp_steps)
    sp_steps.set_defaults(func=cmd_steps)

    sp_stats = sub.add_parser("stats", help="数据卡式（默认 900×420）")
    sp_stats.add_argument("--title", required=True)
    sp_stats.add_argument("--stats", nargs="*", default=[])
    sp_stats.add_argument("--conclusion", default="")
    sp_stats.add_argument("--cols", type=int, default=0, help="列数（0=自动）")
    add_deco(sp_stats)
    add_common(sp_stats)
    sp_stats.set_defaults(func=cmd_stats)

    sp_timeline = sub.add_parser("timeline", help="时间线式（默认 900×560）")
    sp_timeline.add_argument("--title", required=True)
    sp_timeline.add_argument("--events", nargs="*", default=[], help="事件列表，每个为「时间|标题|说明」")
    add_common(sp_timeline)
    sp_timeline.set_defaults(func=cmd_timeline)

    sp_feature = sub.add_parser("feature", help="两栏图文式（默认 900×480）")
    sp_feature.add_argument("--title", required=True)
    sp_feature.add_argument("--subtitle", default="")
    sp_feature.add_argument("--points", nargs="*", default=[], help="要点列表「标题:说明」")
    sp_feature.add_argument("--side", default="left", choices=["left", "right"], help="插图位置")
    add_common(sp_feature)
    sp_feature.set_defaults(func=cmd_feature)

    sp_chart = sub.add_parser("chart", help="图表式（bar 柱状 / donut 环形，默认 900×500）")
    sp_chart.add_argument("--title", required=True)
    sp_chart.add_argument("--chart-type", default="bar", choices=["bar", "donut"])
    sp_chart.add_argument("--data", nargs="*", default=[], help="数据列表「标签:数值」")
    add_common(sp_chart)
    sp_chart.set_defaults(func=cmd_chart)

    sp_flow = sub.add_parser("flow", help="流程图式（默认 900×400）")
    sp_flow.add_argument("--title", required=True)
    sp_flow.add_argument("--steps", nargs="*", default=[], help="步骤列表「标题:说明」")
    add_common(sp_flow)
    sp_flow.set_defaults(func=cmd_flow)

    sp_poster = sub.add_parser("poster", help="杂志风海报式（默认 900×1200）")
    sp_poster.add_argument("--title", required=True, help="大标题")
    sp_poster.add_argument("--kicker", default="", help="眉题（分类标签）")
    sp_poster.add_argument("--number", default="", help="大数字高亮，如 2026 / NO.01")
    sp_poster.add_argument("--points", nargs="*", default=[], help="目录式内容预览行")
    sp_poster.add_argument("--footer", default="", help="页脚元信息")
    add_deco(sp_poster)
    add_common(sp_poster)
    sp_poster.set_defaults(func=cmd_poster)

    sp_sizes = sub.add_parser("sizes", help="列出常用画布尺寸/比例")
    sp_sizes.set_defaults(func=cmd_sizes)

    args = ap.parse_args()
    if args.cmd != "sizes" and not args.out:
        args.out = f"gen-{args.cmd}-{args.palette}.svg"
    args.func(args)


if __name__ == "__main__":
    main()
