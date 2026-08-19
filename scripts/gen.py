#!/usr/bin/env python3
"""一键生成 SVG 配图：套用配色卡 + 多种排版 + 指定尺寸/比例 + 可选校验/渲染。

把「选配色卡 → 填文案 → 选版式 → 排版 → 校验 → 渲染」串成一条命令。
生成的 SVG 已内置：分区独立、留白、字体回退、无 emoji、对比度达标。

子命令（6 种版式）：
    cover         封面式（深底 + 标题 + 底部结论条），默认 900×383，支持 --align left/center
    infographic   信息图式（浅底 + 编号卡片），默认 900×520
    quote         金句卡式（居中正文），默认 900×900
    compare       对比图式（左右两栏 VS），默认 900×560
    steps         横向步骤图（圆点连线流程），默认 900×380
    stats         数据卡式（大数字 + 标签），默认 900×420
    sizes         列出常用画布尺寸/比例速查

指定尺寸 / 比例（所有生成子命令都支持）：
    --size 1200x630      精确画布（宽x高）
    --aspect 16:9 --width 1200   按比例（宽:高），用 --width 定宽，高度自动算
    （都不给时用该类型的默认尺寸）

用法示例：
    python3 gen.py cover --palette 深海蓝 --title "AI 编程工具横评" \
        --subtitle "Claude Code / Codex / Cursor 实测" --badge "深度分析" \
        --conclusion "谁更值得用？" --font "LXGW WenKai" --check --render

    python3 gen.py cover --palette 晨雾蓝灰 --title "活动预告" --align center \
        --aspect 16:9 --width 1200 --font "LXGW WenKai"

    python3 gen.py compare --palette 墨玉青 --title "A vs B 怎么选" \
        --left "方案 A" --right "方案 B" \
        --left-points "优点一" "优点二" "优点三" \
        --right-points "优点一" "优点二" \
        --conclusion "结论" --font "LXGW WenKai"

    python3 gen.py steps --palette 松石蓝绿 --title "三步上手" \
        --steps "第一步:安装环境" "第二步:写 SVG" "第三步:渲染导出" --font "LXGW WenKai"

    python3 gen.py stats --palette 深海蓝 --title "平台数据一览" \
        --stats "500万+:累计用户" "99.9%:服务可用性" "24h:全年在线" "100+:合作品牌" --font "LXGW WenKai"

通用参数：
    --palette NAME  配色卡名称（palette.py list 查看）
    --size WxH      画布尺寸，如 1200x630
    --aspect W:H    宽高比，如 16:9（配合 --width 定宽）
    --width N       --aspect 时的画布宽（缺省用类型默认宽）
    --font F        font-family（务必用 fc-match 验证过的中文字体）
    --out PATH      输出 SVG 路径
    --check         生成后用 check.py 校验（不达标 exit 1）
    --render        顺带导出 PNG（需 rsvg-convert）

依赖同目录 palette.py / layout.py / svgtext.py / check.py / contrast.py（纯 stdlib）。
"""
import argparse
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
}


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


def build_cover(c, title, subtitle, badge, conclusion, font, W, H, align="left"):
    M = 40
    center = (align == "center")
    band_h = max(56, min(96, round(H * 0.21)))
    band_y = H - band_h
    accent_w = round(W * 0.16)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')
    parts.append(f'<rect x="0" y="{band_y}" width="{W}" height="{band_h}" fill="{c["band"]}"/>')
    if not center:
        parts.append(f'<rect x="0" y="{band_y}" width="{accent_w}" height="{band_h}" fill="{c["primary"]}"/>')

    size = 44
    lines = wrap_text(title, W - 2 * M, size)
    while len(lines) > 2 and size > 26:
        size -= 2
        lines = wrap_text(title, W - 2 * M, size)
    lh = 1.35
    y0 = 110
    for i, ln in enumerate(lines):
        if center:
            parts.append(_t(W / 2, y0 + i * size * lh, ln, size, c["light"], font, bold=True, anchor="middle"))
        else:
            parts.append(_t(M, y0 + i * size * lh, ln, size, c["light"], font, bold=True))
    title_bottom = y0 + (len(lines) - 1) * size * lh

    y = title_bottom + 58
    if subtitle:
        if center:
            parts.append(_t(W / 2, y, subtitle, 26, c["primary_soft"], font, anchor="middle"))
        else:
            parts.append(_t(M, y, subtitle, 26, c["primary_soft"], font))
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
            print("[gen] 标题过长，徽章放不下已跳过（可缩短文案或删副标题）", file=sys.stderr)

    if conclusion:
        if center:
            parts.append(_t(W / 2, center_y(band_y, band_h, 26), conclusion, 26, c["light"], font, bold=True, anchor="middle"))
        else:
            parts.append(_t(accent_w + 30, center_y(band_y, band_h, 26), conclusion, 26, c["light"], font, bold=True))
    parts.append("</svg>")
    return "\n".join(parts)


def build_infographic(c, title, subtitle, points, conclusion, font, W, H):
    M = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>')
    parts.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="none" stroke="{c["border"]}" stroke-width="2"/>')

    parts.append(_t(M, 74, title, 32, c["ink"], font, bold=True))
    if subtitle:
        parts.append(_t(M, 106, subtitle, 18, c["ink_muted"], font))

    top = 130
    card_h = 80
    gap = 16
    max_cards = max(1, int((H - top - 70) // (card_h + gap)))
    pts = list(points)
    if len(pts) > max_cards:
        print(f"[gen] 要点过多，截断到前 {max_cards} 个", file=sys.stderr)
        pts = pts[:max_cards]

    for i, pt in enumerate(pts):
        if ":" in pt:
            ttl, dsc = pt.split(":", 1)
        else:
            ttl, dsc = pt, ""
        y = top + i * (card_h + gap)
        parts.append(f'<rect x="{M:g}" y="{y:g}" width="{W - 2 * M:g}" height="{card_h:g}" rx="12" fill="#ffffff" stroke="{c["border"]}"/>')
        cy = y + card_h / 2
        r = 18
        parts.append(f'<circle cx="{M + r + 22:g}" cy="{cy:g}" r="{r:g}" fill="{c["primary"]}"/>')
        parts.append(_t(M + r + 22, center_y(cy - r, 2 * r, 20), str(i + 1), 20, best_text(c["primary"]), font, bold=True, anchor="middle"))
        parts.append(_t(M + r + 62, y + 38, ttl, 22, c["ink"], font, bold=True))
        if dsc:
            parts.append(_t(M + r + 62, y + 62, dsc, 16, c["ink_muted"], font))

    concl_y = top + len(pts) * (card_h + gap) + 8
    parts.append(f'<rect x="{M:g}" y="{concl_y:g}" width="{W - 2 * M:g}" height="44" rx="8" fill="{c["bg"]}"/>')
    if conclusion:
        parts.append(_t(M + 20, center_y(concl_y, 44, 20), conclusion, 20, c["light"], font, bold=True))
    parts.append("</svg>")
    return "\n".join(parts)


def build_quote(c, text, author, font, W, H):
    M = 80
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')
    parts.append(f'<rect x="{W / 2 - 40:g}" y="{H * 0.14:g}" width="80" height="6" rx="3" fill="{c["accent"]}"/>')

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
    parts.append("</svg>")
    return "\n".join(parts)


def build_compare(c, title, left, right, left_points, right_points, conclusion, font, W, H):
    M = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>')
    parts.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="none" stroke="{c["border"]}" stroke-width="2"/>')

    # 标题
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
        return by

    column(left_x, left, left_points, c["primary"], c["primary"])
    column(right_x, right, right_points, c["accent"], c["accent"])

    # VS 圆
    vsy = col_top + col_h / 2
    parts.append(f'<circle cx="{W / 2:g}" cy="{vsy:g}" r="28" fill="{c["bg"]}"/>')
    parts.append(_t(W / 2, vsy + 9, "VS", 22, c["light"], font, bold=True, anchor="middle"))

    # 结论条
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
        if ":" in s:
            ttl, dsc = s.split(":", 1)
        else:
            ttl, dsc = s, ""
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


def build_stats(c, title, stats, conclusion, font, W, H):
    M = 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')
    parts.append(_t(M, 66, title, 30, c["light"], font, bold=True))
    parts.append(f'<rect x="{M:g}" y="82" width="56" height="4" rx="2" fill="{c["primary"]}"/>')

    n = len(stats)
    if n == 0:
        parts.append("</svg>")
        return "\n".join(parts)
    cols = min(n, 4)
    rows = (n + cols - 1) // cols
    gap = 20
    top = 118
    card_h = 130
    card_w = (W - 2 * M - (cols - 1) * gap) / cols
    for i, st in enumerate(stats):
        if ":" in st:
            num, label = st.split(":", 1)
        else:
            num, label = st, ""
        r = i // cols
        col = i % cols
        x = M + col * (card_w + gap)
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


def _palette_or_exit(name):
    p = find_palette(name)
    if not p:
        sys.exit(f"未找到配色卡「{name}」，用 palette.py list 查看可用名称")
    return p["colors"]


def _finish(out, do_check, do_render, font):
    if do_check:
        r = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "check.py"), out, "--margin", "40"],
                           cwd=SCRIPT_DIR)
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


def cmd_cover(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["cover"])
    svg = build_cover(c, args.title, args.subtitle or "", args.badge or "", args.conclusion or "", args.font, W, H, args.align)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"已生成封面: {args.out}  ({W}x{H})")
    _finish(args.out, args.check, args.render, args.font)


def cmd_infographic(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["infographic"])
    svg = build_infographic(c, args.title, args.subtitle or "", args.points, args.conclusion or "", args.font, W, H)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"已生成信息图: {args.out}  ({W}x{H})")
    _finish(args.out, args.check, args.render, args.font)


def cmd_quote(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["quote"])
    svg = build_quote(c, args.text, args.author or "", args.font, W, H)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"已生成金句卡: {args.out}  ({W}x{H})")
    _finish(args.out, args.check, args.render, args.font)


def cmd_compare(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["compare"])
    svg = build_compare(c, args.title, args.left, args.right, args.left_points, args.right_points, args.conclusion or "", args.font, W, H)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"已生成对比图: {args.out}  ({W}x{H})")
    _finish(args.out, args.check, args.render, args.font)


def cmd_steps(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["steps"])
    svg = build_steps(c, args.title, args.steps, args.font, W, H)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"已生成步骤图: {args.out}  ({W}x{H})")
    _finish(args.out, args.check, args.render, args.font)


def cmd_stats(args):
    c = _palette_or_exit(args.palette)
    W, H = resolve_canvas(args, *DEFAULTS["stats"])
    svg = build_stats(c, args.title, args.stats, args.conclusion or "", args.font, W, H)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"已生成数据卡: {args.out}  ({W}x{H})")
    _finish(args.out, args.check, args.render, args.font)


def cmd_sizes(args):
    print(f"常用画布尺寸/比例（共 {len(SIZES)} 个）\n")
    print(f"{'用途':<18}{'尺寸':<14}{'比例'}")
    print("-" * 44)
    for name, w, h, ratio in SIZES:
        print(f"{name:<18}{w}x{h:<10}{ratio}")
    print("\n用法：gen.py <cover|infographic|quote|compare|steps|stats> --size 宽x高  或  --aspect 宽:高 --width 宽")


def main():
    ap = argparse.ArgumentParser(description="一键生成 SVG 配图（配色卡 + 多种排版 + 指定尺寸）")
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

    sp_cover = sub.add_parser("cover", help="封面式（默认 900×383）")
    sp_cover.add_argument("--title", required=True, help="主标题")
    sp_cover.add_argument("--subtitle", default="", help="副标题")
    sp_cover.add_argument("--badge", default="", help="徽章文字（可选）")
    sp_cover.add_argument("--conclusion", default="", help="底部结论文字")
    sp_cover.add_argument("--align", default="left", choices=["left", "center"], help="对齐方式：left（默认）/ center")
    add_common(sp_cover)
    sp_cover.set_defaults(func=cmd_cover)

    sp_info = sub.add_parser("infographic", help="信息图式（默认 900×520）")
    sp_info.add_argument("--title", required=True, help="标题")
    sp_info.add_argument("--subtitle", default="", help="副标题")
    sp_info.add_argument("--points", nargs="*", default=[], help="要点列表，每个为「标题」或「标题:说明」")
    sp_info.add_argument("--conclusion", default="", help="底部结论")
    add_common(sp_info)
    sp_info.set_defaults(func=cmd_infographic)

    sp_quote = sub.add_parser("quote", help="金句卡式（默认 900×900）")
    sp_quote.add_argument("--text", required=True, help="金句正文")
    sp_quote.add_argument("--author", default="", help="署名 / 出处")
    add_common(sp_quote)
    sp_quote.set_defaults(func=cmd_quote)

    sp_compare = sub.add_parser("compare", help="对比图式（左右两栏 VS，默认 900×560）")
    sp_compare.add_argument("--title", required=True, help="标题")
    sp_compare.add_argument("--left", required=True, help="左栏标题")
    sp_compare.add_argument("--right", required=True, help="右栏标题")
    sp_compare.add_argument("--left-points", nargs="*", default=[], help="左栏要点列表")
    sp_compare.add_argument("--right-points", nargs="*", default=[], help="右栏要点列表")
    sp_compare.add_argument("--conclusion", default="", help="底部结论")
    add_common(sp_compare)
    sp_compare.set_defaults(func=cmd_compare)

    sp_steps = sub.add_parser("steps", help="横向步骤图（默认 900×380）")
    sp_steps.add_argument("--title", required=True, help="标题")
    sp_steps.add_argument("--steps", nargs="*", default=[], help="步骤列表，每个为「标题」或「标题:说明」")
    add_common(sp_steps)
    sp_steps.set_defaults(func=cmd_steps)

    sp_stats = sub.add_parser("stats", help="数据卡式（默认 900×420）")
    sp_stats.add_argument("--title", required=True, help="标题")
    sp_stats.add_argument("--stats", nargs="*", default=[], help="数据列表，每个为「数字:标签」")
    sp_stats.add_argument("--conclusion", default="", help="底部结论")
    add_common(sp_stats)
    sp_stats.set_defaults(func=cmd_stats)

    sp_sizes = sub.add_parser("sizes", help="列出常用画布尺寸/比例")
    sp_sizes.set_defaults(func=cmd_sizes)

    args = ap.parse_args()
    if args.cmd != "sizes" and not args.out:
        args.out = f"gen-{args.cmd}-{args.palette}.svg"
    args.func(args)


if __name__ == "__main__":
    main()
