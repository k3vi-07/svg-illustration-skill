#!/usr/bin/env python3
"""一键生成 SVG 配图：套用配色卡 + 自动排版 + 指定尺寸/比例 + 可选校验/渲染。

把「选配色卡 → 填文案 → 指定比例 → 排版 → 校验 → 渲染」串成一条命令。
生成的 SVG 已内置：分区独立、留白、字体回退、无 emoji、对比度达标。

子命令：
    cover         封面式（深底 + 标题 + 底部结论条），默认 900×383
    infographic   信息图式（浅底 + 编号卡片），默认 900×520
    quote         金句卡式（居中正文），默认 900×900
    sizes         列出常用画布尺寸/比例速查

指定尺寸 / 比例（三个子命令都支持）：
    --size 1200x630      精确画布（宽x高）
    --aspect 16:9 --width 1200   按比例（宽:高），用 --width 定宽，高度自动算
    （都不给时用该类型的默认尺寸）

用法示例：
    python3 gen.py cover --palette 深海蓝 --title "AI 编程工具横评" \
        --subtitle "Claude Code / Codex / Cursor 实测" --badge "深度分析" \
        --conclusion "谁更值得用？" --font "LXGW WenKai" --check --render

    python3 gen.py cover --palette 晨雾蓝灰 --title "活动预告" \
        --aspect 16:9 --width 1200 --font "LXGW WenKai"

    python3 gen.py quote --palette 曜石黑金 --text "把复杂的事讲简单" \
        --aspect 3:4 --width 900 --font "LXGW WenKai"

    python3 gen.py infographic --palette 墨玉青 --title "三步上手" \
        --points "第一步:安装环境" "第二步:配置字体" "第三步:渲染导出" \
        --conclusion "一次画对" --font "LXGW WenKai"

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

# 常用画布尺寸/比例速查（sizes 子命令展示；gen.py 不依赖此表）
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

# 三种类型的默认画布
DEFAULTS = {"cover": (900, 383), "infographic": (900, 520), "quote": (900, 900)}


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def _t(x, y, s, size, fill, font, bold=False, anchor="start"):
    w = ' font-weight="bold"' if bold else ""
    return (f'<text x="{x:g}" y="{y:g}" font-family="{font}" font-size="{size:g}"'
            f'{w} fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')


def resolve_canvas(args, default_w, default_h):
    """根据 --size / --aspect / --width 解析画布 (W, H)。"""
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


def build_cover(c, title, subtitle, badge, conclusion, font, W, H):
    M = 40
    band_h = max(56, min(96, round(H * 0.21)))
    band_y = H - band_h
    accent_w = round(W * 0.16)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    parts.append(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')
    parts.append(f'<rect x="0" y="{band_y}" width="{W}" height="{band_h}" fill="{c["band"]}"/>')
    parts.append(f'<rect x="0" y="{band_y}" width="{accent_w}" height="{band_h}" fill="{c["primary"]}"/>')

    size = 44
    lines = wrap_text(title, W - 2 * M, size)
    while len(lines) > 2 and size > 26:
        size -= 2
        lines = wrap_text(title, W - 2 * M, size)
    lh = 1.35
    y0 = 110
    for i, ln in enumerate(lines):
        parts.append(_t(M, y0 + i * size * lh, ln, size, c["light"], font, bold=True))
    title_bottom = y0 + (len(lines) - 1) * size * lh

    y = title_bottom + 58
    if subtitle:
        parts.append(_t(M, y, subtitle, 26, c["primary_soft"], font))
        y += 50
    if badge:
        bh = 46
        if y + bh <= band_y - 12:
            tw = text_width(badge, 22)
            bw = tw + 44
            parts.append(f'<rect x="{M:g}" y="{y:g}" rx="23" width="{bw:g}" height="{bh:g}" fill="{c["accent"]}"/>')
            parts.append(_t(center_x(M, bw), center_y(y, bh, 22), badge, 22, best_text(c["accent"]), font, bold=True, anchor="middle"))
        else:
            print("[gen] 标题过长，徽章放不下已跳过（可缩短文案或删副标题）", file=sys.stderr)

    if conclusion:
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
    svg = build_cover(c, args.title, args.subtitle or "", args.badge or "", args.conclusion or "", args.font, W, H)
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


def cmd_sizes(args):
    print(f"常用画布尺寸/比例（共 {len(SIZES)} 个）\n")
    print(f"{'用途':<18}{'尺寸':<14}{'比例'}")
    print("-" * 44)
    for name, w, h, ratio in SIZES:
        print(f"{name:<18}{w}x{h:<10}{ratio}")
    print("\n用法：gen.py <cover|infographic|quote> --size 宽x高  或  --aspect 宽:高 --width 宽")


def main():
    ap = argparse.ArgumentParser(description="一键生成 SVG 配图（配色卡 + 自动排版 + 指定尺寸）")
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

    sp_sizes = sub.add_parser("sizes", help="列出常用画布尺寸/比例")
    sp_sizes.set_defaults(func=cmd_sizes)

    args = ap.parse_args()
    if args.cmd != "sizes" and not args.out:
        args.out = f"gen-{args.cmd}-{args.palette}.svg"
    args.func(args)


if __name__ == "__main__":
    main()
