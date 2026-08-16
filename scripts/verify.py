#!/usr/bin/env python3
"""像素级验证脚本：定位元素位置、检测重叠/溢出、提取内容包围盒。

三种模式（三选一）：
  1. 单行扫描（--y Y）           ：扫描指定行，报告目标像素的 x 分段
  2. 多行扫描（--y-range A,B）   ：扫描纵向区间，报告目标像素的联合 x 范围
  3. 包围盒（--boxes）           ：全图提取目标像素的连通包围盒（--merge 合并成区域）

目标定义（三选一）：
  --mode bright   亮像素（深色背景上的文字/图形），阈值：像素值 > --thresh
  --mode dark     暗像素（浅色背景上的内容），阈值：像素值 < --thresh
  --color #RRGGBB 接近某颜色的像素（精确找某个元素），配合 --tol

用法：
    python3 verify.py assets/cover.png --y 243 --mode bright --svg-width 900
    python3 verify.py assets/card.png --boxes --mode dark --svg-width 900 --svg-height 520
    python3 verify.py assets/cover.png --color "#F5A623" --boxes --svg-width 900

参数：
    --y Y           单行扫描（PNG 坐标，从 0 开始）
    --y-range A,B   多行扫描区间（含端点）
    --boxes         全图包围盒
    --merge N       合并相距 <N px 的包围盒（默认 12，0 表示不合并；文字逐字拆开时很有用）
    --mode          bright / dark（与 --color 互斥）
    --color HEX     目标颜色（#RGB 或 #RRGGBB）
    --tol N         颜色容差（RGB 欧氏距离），默认 40
    --thresh T      亮度阈值，默认 140
    --svg-width W   SVG viewBox 宽度（输出 SVG x 坐标）
    --svg-height H  SVG viewBox 高度（输出 SVG y 坐标）
    --min-area A    包围盒最小面积（px²），默认 40，过滤噪点
"""
import argparse
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：pip install Pillow")


def parse_hex(color):
    color = color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    if len(color) != 6:
        sys.exit(f"无法解析颜色: {color!r}（需要 #RGB 或 #RRGGBB）")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def build_mask(im_rgb, im_l, w, h, mode, thresh, color, tol):
    mask = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            if color is not None:
                r, g, b = im_rgb.getpixel((x, y))
                tr, tg, tb = color
                hit = ((r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2) ** 0.5 <= tol
            elif mode == "bright":
                hit = im_l.getpixel((x, y)) > thresh
            else:  # dark
                hit = im_l.getpixel((x, y)) < thresh
            if hit:
                mask[y * w + x] = 1
    return mask


def row_segments(mask, w, y, gap=10):
    hits = [x for x in range(w) if mask[y * w + x]]
    if not hits:
        return []
    segs = []
    start = prev = hits[0]
    for x in hits[1:]:
        if x - prev > gap:
            segs.append((start, prev))
            start = x
        prev = x
    segs.append((start, prev))
    return segs


def connected_boxes(mask, w, h, min_area):
    visited = bytearray(w * h)
    boxes = []
    for i in range(w * h):
        if mask[i] and not visited[i]:
            stack = [i]
            visited[i] = 1
            xs = []
            ys = []
            while stack:
                p = stack.pop()
                px = p % w
                py = p // w
                xs.append(px)
                ys.append(py)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = px + dx, py + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            ni = ny * w + nx
                            if mask[ni] and not visited[ni]:
                                visited[ni] = 1
                                stack.append(ni)
            area = len(xs)
            if area >= min_area:
                boxes.append([min(xs), min(ys), max(xs), max(ys), area])
    return boxes


def merge_boxes(boxes, gap):
    """合并相距 <gap px 的包围盒（按各向扩展 gap/2 后判断重叠）。"""
    if gap <= 0 or len(boxes) < 2:
        return [tuple(b) for b in boxes]
    items = [list(b) for b in boxes]  # [x0, y0, x1, y1, area]
    pad = gap / 2.0
    merged = True
    while merged:
        merged = False
        i = 0
        while i < len(items):
            j = i + 1
            while j < len(items):
                a, b = items[i], items[j]
                if not (a[2] + pad < b[0] or b[2] + pad < a[0] or
                        a[3] + pad < b[1] or b[3] + pad < a[1]):
                    items[i] = [min(a[0], b[0]), min(a[1], b[1]),
                                max(a[2], b[2]), max(a[3], b[3]), a[4] + b[4]]
                    del items[j]
                    merged = True
                else:
                    j += 1
            i += 1
    items.sort(key=lambda r: (r[1], r[0]))
    return [tuple(r) for r in items]


def main():
    ap = argparse.ArgumentParser(description="像素级范围检测 / 包围盒提取")
    ap.add_argument("path", help="PNG 文件路径")
    ap.add_argument("--y", type=int, default=None, help="单行扫描（PNG 坐标）")
    ap.add_argument("--y-range", default=None, metavar="A,B",
                    help="多行扫描区间，如 100,200")
    ap.add_argument("--boxes", action="store_true", help="全图包围盒")
    ap.add_argument("--merge", type=int, default=12,
                    help="合并相距 <N px 的包围盒，默认 12，0 表示不合并")
    ap.add_argument("--mode", choices=["bright", "dark"], default="bright",
                    help="bright=找亮像素（深底）/ dark=找暗像素（浅底）")
    ap.add_argument("--color", default=None, help="目标颜色 #RRGGBB（优先于 --mode）")
    ap.add_argument("--tol", type=int, default=40, help="颜色容差，默认 40")
    ap.add_argument("--thresh", type=int, default=140,
                    help="亮度阈值：bright 像素值>thresh；dark 像素值<thresh")
    ap.add_argument("--svg-width", type=float, default=0, help="SVG viewBox 宽度")
    ap.add_argument("--svg-height", type=float, default=0, help="SVG viewBox 高度")
    ap.add_argument("--min-area", type=int, default=40, help="包围盒最小面积 px²")
    args = ap.parse_args()

    modes = [args.y is not None, args.y_range is not None, args.boxes]
    if sum(modes) != 1:
        ap.error("请且仅请指定一种模式：--y / --y-range / --boxes")

    im = Image.open(args.path)
    im_rgb = im.convert("RGB")
    im_l = im.convert("L")
    w, h = im.size

    color = parse_hex(args.color) if args.color else None
    sx = w / args.svg_width if args.svg_width else 1.0
    sy = h / args.svg_height if args.svg_height else 1.0

    def svg_map(x, y):
        s = f"→ SVG x={x / sx:.0f}"
        if args.svg_height:
            s += f" y={y / sy:.0f}"
        return s

    target = ("color " + (args.color or "")) if color else args.mode
    print(f"# {args.path}  ({w}x{h})  target={target}")

    if args.y is not None:
        if not (0 <= args.y < h):
            sys.exit(f"错误：y={args.y} 超出图片高度 {h}")
        mask = build_mask(im_rgb, im_l, w, h, args.mode, args.thresh, color, args.tol)
        segs = row_segments(mask, w, args.y)
        if not segs:
            print(f"y={args.y}: 无目标像素")
            return
        total = sum(b - a + 1 for a, b in segs)
        print(f"y={args.y}: 共 {total} 个目标像素, {len(segs)} 段")
        for i, (a, b) in enumerate(segs):
            line = f"  段{i}: PNG x={a}-{b} (宽 {b - a}px)"
            if args.svg_width:
                line += f"  → SVG x={a / sx:.0f}-{b / sx:.0f}"
            print(line)
        return

    if args.y_range is not None:
        try:
            y0, y1 = (int(v) for v in args.y_range.split(","))
        except ValueError:
            sys.exit("错误：--y-range 格式应为 A,B")
        if y0 > y1:
            y0, y1 = y1, y0
        if y0 < 0 or y1 >= h:
            sys.exit(f"错误：y-range {y0}-{y1} 超出图片高度 {h}")
        mask = build_mask(im_rgb, im_l, w, h, args.mode, args.thresh, color, args.tol)
        all_hits = set()
        hit_rows = 0
        for y in range(y0, y1 + 1):
            segs = row_segments(mask, w, y)
            if segs:
                hit_rows += 1
                for a, b in segs:
                    all_hits.update(range(a, b + 1))
        if not all_hits:
            print(f"y-range {y0}-{y1}: 无目标像素")
            return
        xmin, xmax = min(all_hits), max(all_hits)
        print(f"y-range {y0}-{y1}: {hit_rows} 行含目标像素, 联合 x 范围 {xmin}-{xmax}")
        if args.svg_width:
            print(f"  → SVG x={xmin / sx:.0f}-{xmax / sx:.0f}")
        return

    # --boxes
    mask = build_mask(im_rgb, im_l, w, h, args.mode, args.thresh, color, args.tol)
    boxes = connected_boxes(mask, w, h, args.min_area)
    boxes = merge_boxes(boxes, args.merge)
    if not boxes:
        print("无符合最小面积的包围盒")
        return
    print(f"共 {len(boxes)} 个包围盒（最小面积 {args.min_area}px²，合并阈值 {args.merge}px）")
    for i, (x0, y0, x1, y1, area) in enumerate(boxes):
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        line = f"  框{i}: PNG x={x0}-{x1} y={y0}-{y1} ({bw}x{bh}, 面积 {area})"
        if args.svg_width:
            line += f"  {svg_map(x0, y0)}"
        print(line)


if __name__ == "__main__":
    main()
