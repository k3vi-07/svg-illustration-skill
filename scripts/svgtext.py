#!/usr/bin/env python3
"""CJK 感知的文字宽度估算与字符分类（纯 stdlib，供 textwidth.py / check.py 复用）。

背景：SVG 的 <text> 不自动换行、不自动测量，渲染前必须估算宽度以避免溢出/重叠。
这里的宽度是"估算值"——不同字体实际字宽略有差异，估算公式按"中文全宽、拉丁约半宽"近似。

估算规则（以 font_size 为 1 单位）：
  - 全角/宽字符（CJK 汉字、中文标点、全角符号，east_asian_width ∈ {F,W}）→ 1.0
  - 歧义字符（· 等，east_asian_width = A）                              → 0.5（可调）
  - 空格 / 制表符                                                       → 0.3
  - 其他（拉丁字母、数字、半角标点）                                     → 0.55

用 unicodedata.east_asian_width 而非硬编码 Unicode 区间，能正确处理中文标点
（，。！？、；：“” 等全角）、全角数字/字母，以及 CJK 扩展区字符。
"""
import unicodedata


def is_wide(ch):
    """字符是否属于全角/宽字符（CJK 汉字、中文标点、全角符号）。"""
    return unicodedata.east_asian_width(ch) in ("F", "W")


def char_width(ch, ambiguous=0.5):
    """返回单个字符的估算宽度（以 font_size 为 1 单位）。"""
    if ch in " \t":
        return 0.3
    ea = unicodedata.east_asian_width(ch)
    if ea in ("F", "W"):
        return 1.0
    if ea == "A":
        return ambiguous
    return 0.55


def text_width(s, font_size=16, ambiguous=0.5):
    """估算整串文字的渲染宽度（px）。font_size 为字号（px）。"""
    return sum(char_width(ch, ambiguous) * font_size for ch in s)


# emoji / rsvg 无字形区块（渲染时会变成实心方块，看起来像元素重叠/错乱）
EMOJI_BLOCKS = (
    (0x1F000, 0x1FAFF),  # 表情 / 交通 / 符号 / 补充符号与象形文字
    (0x2600, 0x27BF),    # 杂项符号、装饰符号（含部分 emoji）
    (0x2B00, 0x2BFF),    # 杂项符号与箭头
    (0xFE00, 0xFE0F),    # 变体选择符
    (0x1F1E6, 0x1F1FF),  # 区域指示符（旗帜 emoji 组合用）
)


def is_emoji(ch):
    """粗略判断字符是否属于 rsvg 无字形的 emoji / 特殊符号区块。"""
    cp = ord(ch)
    if cp >= 0x10000:  # 非 BMP（astral）：绝大多数是 emoji / 罕见 CJK 扩展
        return True
    return any(a <= cp <= b for a, b in EMOJI_BLOCKS)


def find_emoji(s):
    """返回字符串中疑似 emoji 的字符列表（去重，保持出现顺序）。"""
    seen = []
    for ch in s:
        if is_emoji(ch) and ch not in seen:
            seen.append(ch)
    return seen
