#!/usr/bin/env python3
"""SVG 渲染前静态检查：写之前先验算，一次画对。

检查项：
  1. 文字宽度估算 + 溢出画布（硬错误）与贴近留白（软警告）检测
  2. 相邻文字是否在同一行带内水平重叠
  3. 文字是否超出所在 <rect> 背景框（胶囊/卡片框不住）
  4. SVG 内是否出现 emoji（rsvg 无字形 → 实心方块）
  5. 是否缺 font-family（中文字体静默回退 → 豆腐块）
  6. 文字 fill 与背景的 WCAG 对比度（自动取所在背景框/卡片颜色）

用法：
    python3 check.py design.svg
    python3 check.py design.svg --canvas 900 520 --margin 40
    python3 check.py design.svg --font-size 16 --contrast "#16223a"

只读，不修改任何文件。依赖同目录 svgtext.py、contrast.py（纯 stdlib）。

说明：
  - "硬错误" = 文字实际越出画布 / 重叠 / 含 emoji / 超出背景框，必须修；
  - "软警告" = 贴近边缘、背景框偏窄、未显式字体、对比度不足，需人工确认。
  - font-family 按「元素自身 → 祖先/全局 <style>」近似解析，无法完整模拟 CSS 级联。
"""
import argparse
import re
import sys
import xml.etree.ElementTree as ET

from svgtext import text_width, find_emoji
from contrast import contrast_ratio

PAD = 15       # 胶囊背景框左右最小余量（px）
ASCENT = 0.8   # 字形上升部相对字号的比例（用于纵向裁剪判断）
DESCENT = 0.25  # 字形下降部相对字号的比例

HEX_RE = re.compile(r"#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?")


def localname(tag):
    return tag.rsplit("}", 1)[-1]


def parse_len(s, default=0.0):
    if s is None:
        return default
    s = str(s).strip().lower()
    if s.endswith("px"):
        s = s[:-2]
    elif s.endswith("pt"):
        return float(s[:-2]) * 96.0 / 72.0
    try:
        return float(s)
    except ValueError:
        return default


def parse_style(style):
    d = {}
    if not style:
        return d
    for part in str(style).split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            d[k.strip().lower()] = v.strip()
    return d


def parse_translate(el):
    tr = el.get("transform") or ""
    m = re.search(r"translate\(\s*(-?[\d.]+)[,\s]+(-?[\d.]+)\s*\)", tr)
    if m:
        return float(m.group(1)), float(m.group(2))
    return 0.0, 0.0


def find_all(root, name):
    for el in root.iter():
        if localname(el.tag) == name:
            yield el


def font_size_of(el, default):
    st = parse_style(el.get("style"))
    return parse_len(el.get("font-size") or st.get("font-size"), default)


def font_family_of(el):
    return el.get("font-family") or parse_style(el.get("style")).get("font-family")


def fill_of(el):
    return el.get("fill") or parse_style(el.get("style")).get("fill")


def font_weight_of(el):
    fw = (el.get("font-weight") or parse_style(el.get("style")).get("font-weight") or "").strip().lower()
    return fw in ("bold", "bolder", "700", "800", "900")


def opacity_of(el):
    o = (el.get("opacity") or parse_style(el.get("style")).get("opacity") or "").strip()
    try:
        return float(o) if o else 1.0
    except ValueError:
        return 1.0


def is_hex(color):
    return bool(color) and bool(HEX_RE.fullmatch(color.strip()))


def global_font_family(root):
    if root.get("font-family"):
        return "(根元素声明)"
    for el in find_all(root, "style"):
        if "font-family" in "".join(el.itertext()):
            return "(<style> 声明)"
    return None


def main():
    ap = argparse.ArgumentParser(description="SVG 渲染前静态检查")
    ap.add_argument("svg", help="SVG 文件路径")
    ap.add_argument("--canvas", nargs=2, type=float, metavar=("W", "H"),
                    help="画布宽高（SVG 未声明 viewBox/width/height 时使用）")
    ap.add_argument("--margin", type=float, default=0.0,
                    help="四周留白阈值 px（贴近边缘则警告），默认 0")
    ap.add_argument("--font-size", type=float, default=16.0,
                    help="未解析到 font-size 时的默认字号，默认 16")
    ap.add_argument("--contrast", metavar="BG",
                    help="画布背景色回退（如 #16223a），用于文字对比度检查")
    args = ap.parse_args()

    try:
        tree = ET.parse(args.svg)
    except Exception as e:
        sys.exit(f"解析 SVG 失败：{e}")
    root = tree.getroot()

    # 画布尺寸：优先 viewBox，其次 width/height，最后 --canvas
    cw = ch = None
    vb = root.get("viewBox")
    if vb:
        nums = [float(p) for p in re.split(r"[,\s]+", vb.strip())]
        if len(nums) >= 4:
            cw, ch = nums[2], nums[3]
    if cw is None:
        cw = parse_len(root.get("width"), None)
    if ch is None:
        ch = parse_len(root.get("height"), None)
    if args.canvas:
        cw, ch = args.canvas
    if not cw or not ch:
        sys.exit("无法确定画布尺寸：请在 SVG 声明 viewBox 或 width/height，或用 --canvas W H")

    print(f"# SVG 静态检查: {args.svg}  画布 {cw:g}×{ch:g}  留白阈值 {args.margin:g}px")

    gfamily = global_font_family(root)

    # 收集文字
    texts = []
    for el in find_all(root, "text"):
        content = "".join(el.itertext()).strip()
        if not content:
            continue
        fs = font_size_of(el, args.font_size)
        x = parse_len(el.get("x"), 0.0)
        y = parse_len(el.get("y"), 0.0)
        tx, ty = parse_translate(el)
        x += tx
        y += ty
        w = text_width(content, fs)
        anchor = (el.get("text-anchor") or "start").strip()
        if anchor == "middle":
            start = x - w / 2
        elif anchor == "end":
            start = x - w
        else:
            start = x
        texts.append(dict(
            content=content, x=x, y=y, start=start, end=start + w,
            fs=fs, w=w, emoji=find_emoji(content),
            family=font_family_of(el) or gfamily, fill=fill_of(el),
            bold=font_weight_of(el),
        ))

    # 收集背景矩形（带 fill，用于背景框包含性与对比度背景）
    rects = []
    for el in find_all(root, "rect"):
        rx = parse_len(el.get("x"), 0.0)
        ry = parse_len(el.get("y"), 0.0)
        rw = parse_len(el.get("width"), 0.0)
        rh = parse_len(el.get("height"), 0.0)
        # 半透明（<0.3）的矩形是装饰底纹，不作为背景框/背景色参与判定
        if rw > 0 and rh > 0 and opacity_of(el) >= 0.3:
            rects.append(dict(x=rx, y=ry, w=rw, h=rh, fill=fill_of(el)))

    # 对比度背景候选 = 矩形 + 圆形（圆形按外接框定位，只用于取背景色，不做框宽校验）
    bg_boxes = list(rects)
    for el in find_all(root, "circle"):
        cx = parse_len(el.get("cx"), 0.0)
        cy = parse_len(el.get("cy"), 0.0)
        r = parse_len(el.get("r"), 0.0)
        if r > 0 and opacity_of(el) >= 0.3:
            bg_boxes.append(dict(x=cx - r, y=cy - r, w=2 * r, h=2 * r, fill=fill_of(el)))
    for el in find_all(root, "polygon"):
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", el.get("points") or "")]
        if len(nums) >= 4 and opacity_of(el) >= 0.3:
            xs, ys = nums[0::2], nums[1::2]
            bg_boxes.append(dict(x=min(xs), y=min(ys), w=max(xs) - min(xs),
                                 h=max(ys) - min(ys), fill=fill_of(el)))

    errors = []  # 必须修
    warns = []   # 需人工确认

    print(f"\n[文字] 共 {len(texts)} 处")
    for i, t in enumerate(texts, 1):
        flags = []
        # 硬错误：实际越出画布
        if t["start"] < 0:
            flags.append(f"越出左边界({t['start']:.0f}<0)")
            errors.append(f"文字「{t['content'][:16]}」越出画布左边")
        if t["end"] > cw:
            flags.append(f"越出右边界({t['end']:.0f}>{cw:g})")
            errors.append(f"文字「{t['content'][:16]}」越出画布右边")
        if t["y"] - t["fs"] * ASCENT < 0:
            flags.append(f"越出顶部(y-字形高={t['y'] - t['fs'] * ASCENT:.0f}<0)")
            errors.append(f"文字「{t['content'][:16]}」越出画布顶部")
        if t["y"] + t["fs"] * DESCENT > ch:
            flags.append(f"越出底部(y+下降部={t['y'] + t['fs'] * DESCENT:.0f}>{ch:g})")
            errors.append(f"文字「{t['content'][:16]}」越出画布底部")
        # 软警告：贴近边缘（未达到留白阈值）
        if args.margin and 0 <= t["start"] < args.margin:
            flags.append(f"贴左边({t['start']:.0f}<留白{args.margin:g})")
            warns.append(f"文字「{t['content'][:16]}」贴近左边（<{args.margin:g}px 留白）")
        if args.margin and t["end"] <= cw and t["end"] > cw - args.margin:
            flags.append(f"贴右边({t['end']:.0f}>{cw - args.margin:g})")
            warns.append(f"文字「{t['content'][:16]}」贴近右边（<{args.margin:g}px 留白）")
        if args.margin and t["y"] - t["fs"] < args.margin:
            flags.append(f"贴顶部")
            warns.append(f"文字「{t['content'][:16]}」贴近顶部")
        if args.margin and t["y"] > ch - args.margin:
            flags.append(f"贴底部")
            warns.append(f"文字「{t['content'][:16]}」贴近底部")
        if t["emoji"]:
            flags.append("emoji:" + "".join(t["emoji"]))
            errors.append(f"文字含 emoji：{''.join(t['emoji'])} → rsvg 会渲染成方块")
        if not t["family"]:
            flags.append("未设 font-family")
            warns.append(f"文字「{t['content'][:16]}」未显式 font-family（依赖继承）")
        # 背景框包含性：取包含文字锚点的最小矩形（跳过整幅画布背景矩形）
        containing = [r for r in rects
                      if r["x"] <= t["x"] <= r["x"] + r["w"] and r["y"] <= t["y"] <= r["y"] + r["h"]
                      and not (r["x"] <= 0 and r["y"] <= 0
                               and r["w"] >= cw - 1 and r["h"] >= ch - 1)]
        if containing:
            box = min(containing, key=lambda r: r["w"] * r["h"])
            if t["start"] < box["x"] or t["end"] > box["x"] + box["w"]:
                flags.append(f"超出背景框(w={box['w']:g})")
                errors.append(f"文字「{t['content'][:16]}」横向超出背景框 x={box['x']:g} w={box['w']:g}")
            elif box["w"] - t["w"] < 2 * PAD:
                flags.append(f"背景框偏窄(w={box['w']:g}<{t['w']:.0f}+{2 * PAD})")
                warns.append(f"文字「{t['content'][:16]}」背景框偏窄")
        status = "OK" if not flags else "⚠ " + " / ".join(flags)
        print(f"  #{i:<2} y={t['y']:<6g} x={t['x']:<6g} {t['fs']:g}px "
              f"估宽≈{t['w']:.0f}px [{t['start']:.0f}→{t['end']:.0f}] "
              f"{t['content'][:22]}  {status}")

    # 文字间水平重叠
    print("\n[重叠]")
    overlaps = 0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a, b = texts[i], texts[j]
            if abs(a["y"] - b["y"]) < 0.7 * max(a["fs"], b["fs"]):
                if a["start"] < b["end"] and b["start"] < a["end"]:
                    overlaps += 1
                    errors.append(
                        f"文字「{a['content'][:12]}」与「{b['content'][:12]}」在同一行带内水平重叠")
                    print(f"  ⚠ y={a['y']:.0f}「{a['content'][:12]}」与 "
                          f"y={b['y']:.0f}「{b['content'][:12]}」重叠")
    if overlaps == 0:
        print("  无")

    # 对比度：背景 = 所在最小矩形 fill > 全画布矩形 fill > --contrast
    contrast_rows = []
    full_bg = None
    full_rects = [r for r in bg_boxes if r["x"] == 0 and r["y"] == 0
                  and r["w"] >= cw - 1 and r["h"] >= ch - 1 and is_hex(r["fill"])]
    if full_rects:
        full_bg = full_rects[0]["fill"]
    fallback_bg = full_bg or (args.contrast if args.contrast and is_hex(args.contrast) else None)

    for i, t in enumerate(texts, 1):
        fill = (t["fill"] or "").strip()
        if not is_hex(fill):
            continue
        containing = [r for r in bg_boxes
                      if r["x"] <= t["x"] <= r["x"] + r["w"] and r["y"] <= t["y"] <= r["y"] + r["h"]
                      and is_hex(r["fill"])]
        bg = None
        if containing:
            bg = min(containing, key=lambda r: r["w"] * r["h"])["fill"]
        if bg is None:
            bg = fallback_bg
        if bg is None:
            continue
        ratio = contrast_ratio(fill, bg)
        # 大字：≥24px，或 ≥18.66px 且加粗（WCAG large text）
        is_large = t["fs"] >= 24 or (t["fs"] >= 18.66 and t.get("bold"))
        need = 3.0 if is_large else 4.5
        ok = ratio >= need
        contrast_rows.append((i, t, fill, bg, ratio, need, ok))
        if not ok:
            warns.append(f"文字「{t['content'][:16]}」fill {fill} vs {bg} 对比度 {ratio:.2f}:1 < {need:g}")

    if contrast_rows:
        print(f"\n[对比度] 回退画布背景 {fallback_bg or '（未定）'}")
        for (i, t, fill, bg, ratio, need, ok) in contrast_rows:
            tag = "OK" if ok else "✗ 偏低"
            print(f"  #{i:<2} fill {fill} vs {bg} = {ratio:.2f}:1 (需≥{need:g})  {tag}")

    print(f"\n[结论] 错误 {len(errors)} 处, 警告 {len(warns)} 处")
    for e in errors:
        print(f"  ✗ {e}")
    for w in warns:
        print(f"  ⚠ {w}")
    if errors:
        print("  → 存在必须修复的问题，先修再渲染。")
        sys.exit(1)
    if warns:
        print("  → 通过（存在警告，请人工确认后渲染）。")
    else:
        print("  → ✅ 通过")
    sys.exit(0)


if __name__ == "__main__":
    main()
