#!/usr/bin/env python3
"""WCAG 对比度计算（选文字颜色前先算，避免文字看不清）。

用法：
    python3 contrast.py "#1A6FC4" "#16223a"
    python3 contrast.py "#fff" "#E34D3A"

输出：对比度比值 + 是否满足 WCAG AA/AAA（普通文字 / 大字 ≥24px 或 ≥18.66px 加粗）。
"""
import argparse
import sys


def _hex(color):
    color = color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    if len(color) != 6:
        raise ValueError(f"无法解析颜色: {color!r}（需要 #RGB 或 #RRGGBB）")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color):
    r, g, b = _hex(color)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(fg, bg):
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def verdict(ratio):
    return [
        "AA 普通" if ratio >= 4.5 else "AA 普通 ✗",
        "AA 大字" if ratio >= 3.0 else "AA 大字 ✗",
        "AAA 普通" if ratio >= 7.0 else "AAA 普通 ✗",
        "AAA 大字" if ratio >= 4.5 else "AAA 大字 ✗",
    ]


def main():
    ap = argparse.ArgumentParser(description="WCAG 对比度计算")
    ap.add_argument("fg", help="前景色（文字）")
    ap.add_argument("bg", help="背景色")
    args = ap.parse_args()
    try:
        ratio = contrast_ratio(args.fg, args.bg)
    except ValueError as e:
        sys.exit(f"错误：{e}")
    print(f"对比度 = {ratio:.2f}:1")
    print("  " + "  ".join(verdict(ratio)))


if __name__ == "__main__":
    main()
