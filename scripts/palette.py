#!/usr/bin/env python3
"""专业配色卡库 + 系列配色工具（纯 stdlib，渲染 PNG 需 rsvg-convert）。

用途：
  - 为一个系列（多篇文章 / 多张封面 / 多张信息图）统一配色，保持「系列感」
  - 每张卡都覆盖「深底封面」与「浅底信息图」两套场景，取色即可用
  - 生成配色卡 SVG/PNG，方便对比挑选

子命令：
    list            列出全部配色卡（名称 + 一句话定位 + 关键色）
    show NAME       展示单张：每个角色 hex + 用途 + 关键对比度
    check [NAME]    对比度校验（不给 NAME 则校验全部），有不达标项时 exit 1
    card NAME       生成配色卡 SVG（--out 指定路径，--render 顺带导出 PNG）
    roles           打印角色（role）说明

用法示例：
    python3 palette.py list
    python3 palette.py show "深海蓝"
    python3 palette.py check
    python3 palette.py card "深海蓝" --render

依赖同目录 contrast.py（对比度计算）。
"""

# ======================================================================
# 配色卡数据 —— 在下方按同样结构添加你自己的卡即可
# 每个角色含义见 ROLES；hex 统一 6 位（#RRGGBB，可省略 #）
# ======================================================================

ROLES = [
    ("bg",           "深色主背景"),
    ("band",         "深色次级背景 / 底部结论条"),
    ("surface",      "浅色卡片背景"),
    ("border",       "浅色卡片边框"),
    ("primary",      "主强调色"),
    ("primary_soft", "主强调亮色（深底上的可读点缀）"),
    ("accent",       "第二强调色（点缀 / 图标）"),
    ("warning",      "警告 / 对比橙"),
    ("danger",       "对比红"),
    ("success",      "成功绿"),
    ("ink",          "主文字色（浅底用）"),
    ("ink_muted",    "次级文字灰"),
    ("light",        "深底上的文字（近白）"),
]

PALETTES = [
    {
        "name": "深海蓝",
        "desc": "科技 / AI / 专业，稳重冷静",
        "colors": {
            "bg": "#16223a", "band": "#141f36",
            "surface": "#f7f9fc", "border": "#e8eef6",
            "primary": "#1A6FC4", "primary_soft": "#4EA8E8",
            "accent": "#7C6FE8",
            "warning": "#F5A623", "danger": "#E34D3A", "success": "#2E8B57",
            "ink": "#16223a", "ink_muted": "#5a6b85", "light": "#ffffff",
        },
    },
    {
        "name": "墨玉青",
        "desc": "国风 / 文化 / 中式，温润雅致",
        "colors": {
            "bg": "#14352F", "band": "#0F2A26",
            "surface": "#f5f8f7", "border": "#e2ece9",
            "primary": "#2A9D8F", "primary_soft": "#7FD8C7",
            "accent": "#E9C46A",
            "warning": "#F4A261", "danger": "#E76F51", "success": "#2A9D8F",
            "ink": "#14352F", "ink_muted": "#4E6B64", "light": "#ffffff",
        },
    },
    {
        "name": "绛紫霞",
        "desc": "文艺 / 女性 / 情感，神秘优雅",
        "colors": {
            "bg": "#2A1B3D", "band": "#201330",
            "surface": "#faf7fb", "border": "#eadff2",
            "primary": "#7C3AED", "primary_soft": "#B794F6",
            "accent": "#F472B6",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#10B981",
            "ink": "#2A1B3D", "ink_muted": "#6b5b7d", "light": "#ffffff",
        },
    },
    {
        "name": "晨雾蓝灰",
        "desc": "商务 / 企业 / 数据，克制专业",
        "colors": {
            "bg": "#1E293B", "band": "#0F172A",
            "surface": "#f8fafc", "border": "#e2e8f0",
            "primary": "#3B82F6", "primary_soft": "#93C5FD",
            "accent": "#38BDF8",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#0F172A", "ink_muted": "#64748B", "light": "#ffffff",
        },
    },
    {
        "name": "暖阳橙",
        "desc": "生活 / 美食 / 活力，温暖亲切",
        "colors": {
            "bg": "#2B1F16", "band": "#1F150E",
            "surface": "#fdf9f3", "border": "#f0e6d8",
            "primary": "#F59E0B", "primary_soft": "#FCD34D",
            "accent": "#FB7185",
            "warning": "#F97316", "danger": "#DC2626", "success": "#65A30D",
            "ink": "#2B1F16", "ink_muted": "#6B5A44", "light": "#ffffff",
        },
    },
    {
        "name": "松石蓝绿",
        "desc": "清新 / 教育 / 医疗，清爽明快",
        "colors": {
            "bg": "#12333B", "band": "#0C2830",
            "surface": "#f2f8f9", "border": "#dcebf0",
            "primary": "#0EA5E9", "primary_soft": "#7DD3FC",
            "accent": "#2DD4BF",
            "warning": "#FBBF24", "danger": "#F87171", "success": "#34D399",
            "ink": "#12333B", "ink_muted": "#4C6A75", "light": "#ffffff",
        },
    },
    {
        "name": "静谧绿",
        "desc": "环保 / 健康 / 自然，清新治愈",
        "colors": {
            "bg": "#14271E", "band": "#0F1E17",
            "surface": "#f4f8f5", "border": "#dfeae3",
            "primary": "#22C55E", "primary_soft": "#86EFAC",
            "accent": "#A3E635",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#14271E", "ink_muted": "#5f7668", "light": "#ffffff",
        },
    },
    {
        "name": "曜石黑金",
        "desc": "高端 / 发布会 / 奢华，低调质感",
        "colors": {
            "bg": "#161616", "band": "#0B0B0B",
            "surface": "#fafafa", "border": "#ececec",
            "primary": "#D4AF37", "primary_soft": "#F1D27A",
            "accent": "#9CA3AF",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#161616", "ink_muted": "#6b6b6b", "light": "#ffffff",
        },
    },
]

# ======================================================================
# 逻辑
# ======================================================================

import argparse
import math
import os
import shutil
import subprocess
import sys

from contrast import contrast_ratio, luminance


def norm_hex(c):
    c = c.strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return "#" + c.lower()


def find_palette(name):
    name = name.strip()
    for p in PALETTES:
        if p["name"] == name or p["name"].lower() == name.lower():
            return p
    return None


# 需要校验的「文字色 → 背景色」关键组合
CONTRAST_PAIRS = [
    ("light", "bg", 4.5, "深底主文字"),
    ("light", "band", 4.5, "底部结论条文字"),
    ("primary_soft", "bg", 4.5, "深底点缀 / 次级文字"),
    ("ink", "surface", 4.5, "浅底主文字"),
    ("ink_muted", "surface", 4.5, "浅底次级文字"),
    ("ink", "primary_soft", 4.5, "浅色徽章上的深字"),
]


def palette_checks(p):
    rows = []
    for (fgk, bgk, need, label) in CONTRAST_PAIRS:
        fg = p["colors"][fgk]
        bg = p["colors"][bgk]
        ratio = contrast_ratio(fg, bg)
        rows.append((label, fgk, bgk, fg, bg, ratio, need, ratio >= need))
    return rows


def cmd_list(args):
    print(f"共 {len(PALETTES)} 张配色卡（系列配色：同一系列固定一张卡，只变文案/图形）\n")
    for i, p in enumerate(PALETTES, 1):
        c = p["colors"]
        print(f"{i:>2}. {p['name']} —— {p['desc']}")
        print(f"     深底 bg={norm_hex(c['bg'])}  band={norm_hex(c['band'])}  "
              f"primary={norm_hex(c['primary'])}  light={norm_hex(c['light'])}")
        print(f"     浅底 surface={norm_hex(c['surface'])}  ink={norm_hex(c['ink'])}  "
              f"accent={norm_hex(c['accent'])}")
    print("\n用 `palette.py show <名称>` 看详情，`palette.py card <名称>` 生成配色卡图。")


def cmd_show(args):
    p = find_palette(args.name)
    if not p:
        sys.exit(f"未找到配色卡「{args.name}」，用 `palette.py list` 查看可用名称")
    print(f"# {p['name']} —— {p['desc']}\n")
    print(f"{'角色':<14}{'hex':<10}{'用途'}")
    print("-" * 44)
    for key, desc in ROLES:
        print(f"{key:<14}{norm_hex(p['colors'][key]):<10}{desc}")
    print("\n[关键对比度]")
    ok_all = True
    for (label, fgk, bgk, fg, bg, ratio, need, ok) in palette_checks(p):
        tag = "✅" if ok else "❌"
        if not ok:
            ok_all = False
        print(f"  {tag} {label:<12} {norm_hex(fg)} on {norm_hex(bg)} = {ratio:.2f}:1 (需≥{need:g})")
    print("\n" + ("✅ 全部达标，可直接用于系列。" if ok_all else "❌ 存在不达标组合，慎用该角色搭配。"))


def cmd_check(args):
    targets = [p for p in PALETTES] if not args.name else [find_palette(args.name)]
    if args.name and targets[0] is None:
        sys.exit(f"未找到配色卡「{args.name}」")
    all_ok = True
    for p in targets:
        print(f"# {p['name']}")
        for (label, fgk, bgk, fg, bg, ratio, need, ok) in palette_checks(p):
            if not ok:
                all_ok = False
                print(f"  ❌ {label:<12} {norm_hex(fg)} on {norm_hex(bg)} = {ratio:.2f}:1 < {need:g}")
        print("  ✅ 全部达标" if all(ok for _, _, _, _, _, _, _, ok in palette_checks(p)) else "")
    print("\n结论：" + ("✅ 所有卡达标" if all_ok else "❌ 存在不达标组合"))
    sys.exit(0 if all_ok else 1)


# 配色卡里含中文（卡名/角色说明），font-family 需含中文字体；用 --font 覆盖为 fc-match 验证过的字体
DEFAULT_FONT = '"PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "LXGW WenKai", "Microsoft YaHei", sans-serif'


# 配色卡上更紧凑的角色标签（完整说明见 ROLES / `palette.py roles`）
CARD_LABELS = {
    "bg": "深色主背景", "band": "深色次级背景", "surface": "浅色卡片背景",
    "border": "浅色卡片边框", "primary": "主强调色", "primary_soft": "主强调亮色",
    "accent": "第二强调 / 图标", "warning": "警告 / 对比橙", "danger": "对比红",
    "success": "成功绿", "ink": "主文字（浅底）", "ink_muted": "次级文字灰",
    "light": "深底文字（近白）",
}


def best_text(color):
    cb = contrast_ratio(color, "#000000")
    cw = contrast_ratio(color, "#ffffff")
    return "#ffffff" if cw >= cb else "#000000"


def palette_card_svg(p, font=DEFAULT_FONT):
    cols = 3
    margin = 40
    gap = 16
    sw = (900 - 2 * margin - (cols - 1) * gap) / cols
    sh = 100
    header_h = 150
    rows = math.ceil(len(ROLES) / cols)
    H = header_h + rows * sh + (rows - 1) * gap + margin

    c = p["colors"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{int(H)}" viewBox="0 0 900 {int(H)}">',
        f'<rect width="900" height="{int(H)}" fill="{norm_hex(c["bg"])}"/>',
        f'<text x="40" y="70" font-family="{font}" font-size="44" font-weight="bold" fill="{norm_hex(c["light"])}">{p["name"]}</text>',
        f'<text x="40" y="110" font-family="{font}" font-size="22" fill="{norm_hex(c["primary_soft"])}">{p["desc"]}</text>',
    ]

    for idx, (key, _desc) in enumerate(ROLES):
        r = idx // cols
        col = idx % cols
        x = margin + col * (sw + gap)
        y = header_h + r * (sh + gap)
        color = norm_hex(c[key])
        txt = best_text(color)
        label = CARD_LABELS.get(key, key)
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{sw:.1f}" height="{sh:.1f}" rx="10" fill="{color}"/>')
        parts.append(f'<text x="{x + 14:.1f}" y="{y + 34:.1f}" font-family="{font}" font-size="20" font-weight="bold" fill="{txt}">{key}</text>')
        parts.append(f'<text x="{x + 14:.1f}" y="{y + 60:.1f}" font-family="{font}" font-size="18" fill="{txt}">{color}</text>')
        parts.append(f'<text x="{x + 14:.1f}" y="{y + 84:.1f}" font-family="{font}" font-size="13" fill="{txt}" opacity="0.85">{label}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def cmd_card(args):
    p = find_palette(args.name)
    if not p:
        sys.exit(f"未找到配色卡「{args.name}」，用 `palette.py list` 查看可用名称")
    out = args.out or f"palette-{p['name']}.svg"
    svg = palette_card_svg(p, args.font)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"已生成配色卡: {out}")
    if args.render:
        if shutil.which("rsvg-convert"):
            png = os.path.splitext(out)[0] + ".png"
            subprocess.run(["rsvg-convert", "-w", "900", out, "-o", png], check=True)
            print(f"已导出 PNG: {png}")
        else:
            print("未找到 rsvg-convert，跳过 PNG 导出（可手动 rsvg-convert -w 900 <svg> -o <png>）")


def cmd_roles(args):
    print(f"{'角色':<14}{'用途'}")
    print("-" * 44)
    for key, desc in ROLES:
        print(f"{key:<14}{desc}")


def main():
    ap = argparse.ArgumentParser(description="专业配色卡库 + 系列配色工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp_list = sub.add_parser("list", help="列出全部配色卡")
    sp_list.set_defaults(func=cmd_list)

    sp_show = sub.add_parser("show", help="查看单张配色卡")
    sp_show.add_argument("name", help="配色卡名称")
    sp_show.set_defaults(func=cmd_show)

    sp_check = sub.add_parser("check", help="对比度校验")
    sp_check.add_argument("name", nargs="?", help="配色卡名称（缺省校验全部）")
    sp_check.set_defaults(func=cmd_check)

    sp_card = sub.add_parser("card", help="生成配色卡 SVG/PNG")
    sp_card.add_argument("name", help="配色卡名称")
    sp_card.add_argument("--out", help="输出 SVG 路径")
    sp_card.add_argument("--font", default=DEFAULT_FONT, help="font-family（含中文字体；用 fc-match 验证过的覆盖）")
    sp_card.add_argument("--render", action="store_true", help="顺带导出 PNG（需 rsvg-convert）")
    sp_card.set_defaults(func=cmd_card)

    sp_roles = sub.add_parser("roles", help="打印角色说明")
    sp_roles.set_defaults(func=cmd_roles)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
