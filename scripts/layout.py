#!/usr/bin/env python3
"""文字排版 / 元素布局计算工具（纯 stdlib，写 SVG 前排版用）。

解决 SVG 布局里的高频痛点（SVG 的 <text> 不自动换行 / 不居中 / 不测量）：
  1. 文字自动换行：CJK 按字断行，英文/数字按词断行
  2. 多行文字的行高与每行 baseline y
  3. 水平 / 垂直居中对齐（text-anchor 与 baseline 计算）
  4. N 个元素的均匀网格 / 单行等分定位

子命令：
    wrap TEXT   按最大宽度换行（CJK 感知），可输出 <text> 片段
    center TEXT 在给定框内水平+垂直居中，输出 x / baseline y
    grid N      等分定位 N 个元素（可选多行）

用法示例：
    python3 layout.py wrap "凭什么敢和 Claude Code、Codex 叫板？" --size 37 --max-width 700 --svg
    python3 layout.py wrap "标题文案" --size 40 --max-width 700 --y 100 --line-height 1.6
    python3 layout.py center "深度分析" --size 24 --box 40 205 230 46
    python3 layout.py grid 4 --width 900 --margin 40 --gap 24

依赖同目录 svgtext.py（纯 stdlib）。
"""
import argparse

from svgtext import text_width, char_width, is_wide


def _tokenize(text):
    """拆成 (cjk 单字 | 拉丁词 | 空格分隔) 的单元流。"""
    units = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in " \t":
            while i < n and text[i] in " \t":
                i += 1
            units.append(("sep", None))
        elif is_wide(ch):
            units.append(("cjk", ch))
            i += 1
        else:
            j = i
            while j < n and not is_wide(text[j]) and text[j] not in " \t":
                j += 1
            units.append(("word", text[i:j]))
            i = j
    return units


def _hard_split(word, max_width, font_size, ambiguous):
    """单词本身超宽时按字符硬切。"""
    chunks = []
    cur = ""
    cur_w = 0.0
    for ch in word:
        w = text_width(ch, font_size, ambiguous)
        if cur and cur_w + w > max_width:
            chunks.append(cur)
            cur = ""
            cur_w = 0.0
        cur += ch
        cur_w += w
    if cur:
        chunks.append(cur)
    return chunks


def wrap_text(text, max_width, font_size, ambiguous=0.5):
    """CJK 感知换行：返回行列表。中文按字断行，英文/数字按词断行（不拆词）。"""
    max_width = float(max_width)
    if max_width <= 0:
        raise ValueError("max-width 必须 > 0")
    tokens = _tokenize(text)
    lines = []
    cur = ""
    cur_w = 0.0
    for kind, val in tokens:
        if kind == "sep":
            if not cur:
                continue  # 行首空格丢弃
            cur += " "
            cur_w += char_width(" ") * font_size
            continue
        w = text_width(val, font_size, ambiguous)
        if cur and cur_w + w > max_width:
            lines.append(cur.rstrip())
            cur = ""
            cur_w = 0.0
        if not cur and kind == "word" and w > max_width:
            lines.extend(_hard_split(val, max_width, font_size, ambiguous))
            cur = ""
            cur_w = 0.0
            continue
        cur += val
        cur_w += w
    if cur.strip():
        lines.append(cur.rstrip())
    return lines or [""]


def center_x(box_x, box_w):
    """水平居中：返回文字 x（配合 text-anchor="middle"）。"""
    return box_x + box_w / 2


def center_y(box_y, box_h, font_size, factor=0.35):
    """垂直居中：返回文字的 baseline y。box_y 为框顶，box_h 为框高。

    近似公式 baseline = 框中心 y + factor×字号（factor 默认 0.35）。
    若渲染后偏上/偏下，在 0.3~0.4 之间微调（可用 preview.py 目检确认）。
    """
    return box_y + box_h / 2 + factor * font_size


def grid(n, total_w, margin=0, gap=0, cols=None):
    """等分定位 n 个等宽元素。返回 (元素宽度, [(x, 行号0-based), ...])。

    cols=None 时单行等分；给定 cols 则按列数换行。
    """
    cols = cols or n
    cols = max(1, min(cols, n))
    inner = total_w - 2 * margin - (cols - 1) * gap
    w = inner / cols
    positions = [(margin + (i % cols) * (w + gap), i // cols) for i in range(n)]
    return w, positions


# ---- CLI ----

def cmd_wrap(args):
    lines = wrap_text(args.text, args.max_width, args.size, args.ambiguous)
    lh = args.line_height * args.size
    print(f"换行结果（字号 {args.size:g}，最大行宽 {args.max_width:g}，行高 {args.line_height}）")
    for i, line in enumerate(lines):
        w = text_width(line, args.size, args.ambiguous)
        print(f"  第{i + 1}行 y={args.y + i * lh:g}  估宽≈{w:.0f}px  {line}")
    print(f"共 {len(lines)} 行，块高≈{len(lines) * lh:.0f}px")
    if args.svg:
        print("\n可直接粘贴的 <text>：")
        for i, line in enumerate(lines):
            print(f'  <text x="{args.x:g}" y="{args.y + i * lh:g}" font-size="{args.size:g}">{line}</text>')


def cmd_center(args):
    x0, y0, w0, h0 = args.box
    tw = text_width(args.text, args.size, args.ambiguous)
    cx = center_x(x0, w0)
    cy = center_y(y0, h0, args.size, args.factor)
    print(f"文字「{args.text}」字号 {args.size:g}，估宽≈{tw:.0f}px")
    print(f"  框: x={x0:g} y={y0:g} w={w0:g} h={h0:g}")
    print(f"  水平居中: x={cx:g}（text-anchor=\"middle\"）")
    print(f"  垂直居中: baseline y={cy:g}（factor={args.factor}，可 0.3~0.4 微调）")
    print(f'  完整: <text x="{cx:g}" y="{cy:g}" text-anchor="middle" font-size="{args.size:g}">{args.text}</text>')


def cmd_grid(args):
    w, positions = grid(args.n, args.width, args.margin, args.gap, args.cols)
    cols = args.cols or args.n
    rows = (args.n + cols - 1) // cols
    print(f"{args.n} 个等宽元素（{cols} 列 × {rows} 行），每个宽 {w:.1f}px")
    for i, (x, r) in enumerate(positions):
        print(f"  元素{i + 1}: x={x:.1f}  行={r + 1}")


def main():
    ap = argparse.ArgumentParser(description="文字排版 / 元素布局计算工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp_wrap = sub.add_parser("wrap", help="按最大宽度换行（CJK 感知）")
    sp_wrap.add_argument("text", help="要换行的文字")
    sp_wrap.add_argument("--size", type=float, default=24, help="字号 px")
    sp_wrap.add_argument("--max-width", type=float, required=True, help="最大行宽 px")
    sp_wrap.add_argument("--ambiguous", type=float, default=0.5, help="歧义字符宽度系数")
    sp_wrap.add_argument("--y", type=float, default=0, help="第一行 baseline y")
    sp_wrap.add_argument("--x", type=float, default=0, help="文字 x（--svg 输出用）")
    sp_wrap.add_argument("--line-height", type=float, default=1.5, help="行高倍数，默认 1.5")
    sp_wrap.add_argument("--svg", action="store_true", help="同时输出 <text> 片段")
    sp_wrap.set_defaults(func=cmd_wrap)

    sp_center = sub.add_parser("center", help="框内居中")
    sp_center.add_argument("text", help="文字")
    sp_center.add_argument("--size", type=float, default=24, help="字号 px")
    sp_center.add_argument("--ambiguous", type=float, default=0.5)
    sp_center.add_argument("--box", nargs=4, type=float, required=True,
                           metavar=("X", "Y", "W", "H"), help="框 x y w h")
    sp_center.add_argument("--factor", type=float, default=0.35, help="垂直居中系数，默认 0.35")
    sp_center.set_defaults(func=cmd_center)

    sp_grid = sub.add_parser("grid", help="等分定位")
    sp_grid.add_argument("n", type=int, help="元素个数")
    sp_grid.add_argument("--width", type=float, default=900, help="画布宽，默认 900")
    sp_grid.add_argument("--margin", type=float, default=40, help="左右留白，默认 40")
    sp_grid.add_argument("--gap", type=float, default=24, help="元素间距，默认 24")
    sp_grid.add_argument("--cols", type=int, default=None, help="列数（缺省单行）")
    sp_grid.set_defaults(func=cmd_grid)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
