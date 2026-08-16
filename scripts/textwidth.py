#!/usr/bin/env python3
"""CJK 感知的文字宽度估算（写 SVG 前先算，避免溢出/重叠）。

用法：
    python3 textwidth.py "凭什么敢和 Claude Code、Codex 叫板？" --size 37
    python3 textwidth.py "深度分析 · AI 编程工具" --size 15
    printf '%s\n' "第一行标题" "第二行文字" | python3 textwidth.py --batch --size 24

参数：
    --size N      字号（px），默认 16
    --ambiguous F 歧义字符（·、— 等）按多少倍字号计，默认 0.5
    --batch       从 stdin 逐行读取并估算（每行一条）

依赖同目录 svgtext.py（纯 stdlib）。
"""
import argparse
import sys

from svgtext import text_width


def main():
    ap = argparse.ArgumentParser(description="估算文字渲染宽度（CJK 感知）")
    ap.add_argument("text", nargs="?", help="要估算的文字（--batch 时可省略）")
    ap.add_argument("--size", type=float, default=16, help="字号 px，默认 16")
    ap.add_argument("--ambiguous", type=float, default=0.5,
                    help="歧义字符宽度系数，默认 0.5")
    ap.add_argument("--batch", action="store_true", help="从 stdin 逐行读取")
    args = ap.parse_args()

    def report(s):
        w = text_width(s, args.size, args.ambiguous)
        print(f"字号 {args.size:g}px  宽度≈{w:.0f}px   [{s}]")

    if args.batch:
        for line in sys.stdin:
            line = line.rstrip("\n")
            if line.strip():
                report(line)
    elif args.text is not None:
        report(args.text)
    else:
        ap.error("需要提供文字，或用 --batch 从 stdin 读取")


if __name__ == "__main__":
    main()
