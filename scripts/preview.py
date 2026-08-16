#!/usr/bin/env python3
"""PNG → ASCII 可视化预览脚本（AI 无法直接看图时的"眼睛"）。

用途：把 PNG 降采样成 ASCII 字符画，从文本输出中"看到"整体布局，
发现元素重叠、错位、分区混乱等问题。

用法：
    python3 preview.py assets/cover.png
    python3 preview.py assets/card.png --width 120 --auto-contrast
    python3 preview.py assets/cover.png --color "#F5A623"   # 高亮某个颜色所在位置

参数：
    --width W        输出宽度（字符数），默认 150
    --aspect R       终端字符高宽比校正（字符高/宽），默认 0.5
    --invert         反转明暗
    --auto-contrast  按整图亮度范围拉伸（低对比图更清晰）
    --color HEX      高亮目标颜色（#RGB / #RRGGBB），其余变暗
    --tol N          颜色容差（RGB 欧氏距离），默认 40
"""
import argparse
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：pip install Pillow")

CHARS = " .:-=+*#%@"


def parse_hex(color):
    color = color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    if len(color) != 6:
        sys.exit(f"无法解析颜色: {color!r}（需要 #RGB 或 #RRGGBB）")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def main():
    ap = argparse.ArgumentParser(description="PNG → ASCII 预览")
    ap.add_argument("path", help="PNG 文件路径")
    ap.add_argument("--width", type=int, default=150, help="输出宽度（字符数）")
    ap.add_argument("--aspect", type=float, default=0.5,
                    help="终端字符高宽比校正，默认 0.5")
    ap.add_argument("--invert", action="store_true", help="反转明暗")
    ap.add_argument("--auto-contrast", action="store_true", help="按整图亮度范围拉伸")
    ap.add_argument("--color", default=None, help="高亮目标颜色 #RRGGBB")
    ap.add_argument("--tol", type=int, default=40, help="颜色容差，默认 40")
    args = ap.parse_args()

    im = Image.open(args.path)
    rgb = im.convert("RGB")
    gray = im.convert("L")
    w, h = gray.size
    out_h = max(1, int(args.width * h / w * args.aspect))

    # 块尺寸：每个输出字符对应源图里的一个矩形块
    bw = w / args.width
    bh = h / out_h

    # 亮度拉伸（--auto-contrast）
    lo, hi = 0, 255
    if args.auto_contrast:
        px = list(gray.getdata())
        lo, hi = min(px), max(px)
        if hi <= lo:
            hi = lo + 1

    target = parse_hex(args.color) if args.color else None

    print(f"# {args.path}  ({w}x{h}) → {args.width}x{out_h} 字符")
    if target:
        print(f"# 高亮颜色 {args.color}（容差 {args.tol}），'#'=目标色，'.'=少量，空白=无")
    else:
        print(f"# 明暗阶梯（暗→亮）：{CHARS}" + (" [反转]" if args.invert else ""))

    for oy in range(out_h):
        row = []
        for ox in range(args.width):
            # 采样块
            x0 = int(ox * bw)
            x1 = max(x0 + 1, int((ox + 1) * bw))
            y0 = int(oy * bh)
            y1 = max(y0 + 1, int((oy + 1) * bh))
            if target is not None:
                match = 0
                total = 0
                for y in range(y0, min(y1, h)):
                    for x in range(x0, min(x1, w)):
                        r, g, b = rgb.getpixel((x, y))
                        tr, tg, tb = target
                        d = ((r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2) ** 0.5
                        total += 1
                        if d <= args.tol:
                            match += 1
                frac = match / total if total else 0
                row.append("#" if frac >= 0.15 else ("+" if frac >= 0.04 else ("." if frac >= 0.01 else " ")))
            else:
                acc = 0
                cnt = 0
                for y in range(y0, min(y1, h)):
                    for x in range(x0, min(x1, w)):
                        acc += gray.getpixel((x, y))
                        cnt += 1
                v = acc / cnt if cnt else 0
                if args.invert:
                    v = 255 - v
                v = (v - lo) * 255 / (hi - lo)
                v = max(0, min(255, v))
                idx = min(9, int(v * 10 // 256))
                row.append(CHARS[idx])
        print("".join(row))


if __name__ == "__main__":
    main()
