#!/usr/bin/env python3
"""svg-illustration-skill 回归测试套件（纯 stdlib，无第三方依赖）。

覆盖两层：
  1) 矩阵：12 个版式用例 × 2 张配色卡，每例走完整链路
     「gen.py 生成 → check.py 校验 → rsvg-convert 渲染 → SVG 结构断言」
  2) 边界用例（回归锁，对应历史上真实出现过的问题）：
     R1 柱状图长标签不得压到柱子        （曾因固定 140px 标签列而重叠）
     R2 小于 360x200 的画布必须拒绝    （曾生成 0 错误的废图）
     R3 柱状图数据条数超出容量必须截断并警告、不得画出界
     R4 环形图图例超出容量必须截断并警告
     R5 palette.py check 全配色卡对比度校验
     R6 gen.py sizes 子命令可用

用法（在仓库任意位置执行）：
    python3 tests/run_all.py
任何一项断言失败 → exit 1 并列出明细；改动 scripts/ 后请先跑本套件。
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from svgtext import text_width  # noqa: E402  （与 gen.py 同一宽度估算，保证断言口径一致）

PALETTES = ["深海蓝", "绛紫霞"]
RSVG = shutil.which("rsvg-convert")

# (用例名, gen.py 参数, 必须出现在 SVG 里的结构/内容标记)
CASES = [
    ("cover-rich", ["cover", "--title", "回归测试封面", "--subtitle", "副标题文案",
                    "--badge", "深度", "--conclusion", "底部结论", "--kicker", "特别企划",
                    "--footer", "页脚信息", "--align", "center", "--deco", "circles"],
     ["回归测试封面", "特别企划", "页脚信息"]),
    ("infographic-cols2", ["infographic", "--title", "信息图回归", "--subtitle", "副标题",
                           "--points", "要点一:说明文字", "要点二:说明文字", "要点三:说明文字",
                           "--conclusion", "结论", "--kicker", "眉题", "--footer", "页脚", "--cols", "2"],
     ["信息图回归", "要点一", "结论"]),
    ("quote-rich", ["quote", "--text", "少即是多，多即是少，简单胜于复杂。",
                    "--author", "—— 某作者", "--kicker", "设计箴言", "--footer", "页脚", "--deco", "dots"],
     ["设计箴言", "某作者"]),
    ("compare", ["compare", "--title", "对比回归", "--left", "左方案", "--right", "右方案",
                 "--left-points", "左要点一", "左要点二", "--right-points", "右要点一", "右要点二",
                 "--conclusion", "结论"],
     [">VS<", "左方案", "右方案"]),
    ("steps", ["steps", "--title", "步骤回归", "--steps", "第一步:说明", "第二步:说明", "第三步:说明"],
     ["第一步", "第三步"]),
    ("stats-cols3", ["stats", "--title", "数据回归", "--stats", "90%:高可用", "3x:更快", "120:规模",
                     "--cols", "3", "--conclusion", "结论", "--deco", "grid"],
     ["90%", "高可用"]),
    ("timeline", ["timeline", "--title", "时间线回归",
                  "--events", "2024年|立项|确定方向", "2025年|研发|完成测试", "2026年|上线|全球发布"],
     ["2024年", "立项"]),
    ("feature-right", ["feature", "--title", "图文回归", "--subtitle", "副标题",
                       "--points", "优点一:说明", "优点二:说明", "优点三:说明", "--side", "right"],
     ["优点一", "优点三"]),
    ("chart-bar", ["chart", "--title", "柱状回归", "--chart-type", "bar",
                   "--data", "一季度:120", "二季度:180", "三季度:240", "四季度:320"],
     ["一季度", "320"]),
    ("chart-donut", ["chart", "--title", "环形回归", "--chart-type", "donut",
                     "--data", "甲:40", "乙:30", "丙:20", "丁:10"],
     ["%", "甲", "丁"]),
    ("flow", ["flow", "--title", "流程回归",
              "--steps", "提交:填写表单", "审核:人工复核", "发布:全网推送", "复盘:数据回顾"],
     ["提交", "发布", "复盘"]),
    ("poster", ["poster", "--title", "年度特辑", "--kicker", "SPECIAL", "--number", "2026",
                "--points", "内容一", "内容二", "内容三", "--footer", "页脚", "--deco", "circles"],
     ["2026", "内容一", "SPECIAL"]),
]

BAR_RECT = re.compile(r'<rect x="([\d.]+)" y="([\d.]+)" width="[\d.]+" height="30" rx="6"')

total = 0
fails = []


def ok(cond, label, detail=""):
    global total
    total += 1
    if cond:
        return True
    fails.append(f"{label}" + (f" — {detail}" if detail else ""))
    return False


def run_gen(args, palette, out):
    return subprocess.run([sys.executable, "gen.py", *args, "--palette", palette, "--out", out, "--check"],
                          capture_output=True, text=True, cwd=str(SCRIPTS))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        # ---- 1) 版式 × 配色矩阵 ----
        for palette in PALETTES:
            for name, args, marks in CASES:
                label = f"矩阵 {palette}·{name}"
                out = str(Path(tmp) / f"{palette}-{name}.svg")
                r = run_gen(args, palette, out)
                if not ok(r.returncode == 0, label + " 生成+校验",
                          f"exit={r.returncode} stderr={r.stderr[-300:]}"):
                    continue
                svg = Path(out).read_text(encoding="utf-8")
                ok(svg.lstrip().startswith("<svg") and "</svg>" in svg and "viewBox=" in svg,
                   label + " SVG结构", svg[:100])
                for mk in marks:
                    ok(mk in svg, label + f" 内容[{mk}]", "标记缺失")
                if RSVG:
                    png = out[:-4] + ".png"
                    rp = subprocess.run([RSVG, "-w", "900", out, "-o", png],
                                        capture_output=True, text=True)
                    ok(rp.returncode == 0 and Path(png).exists() and Path(png).stat().st_size > 0,
                       label + " 渲染", rp.stderr[-200:])
                print(f"  ✅ {label}" if not any(f.startswith(label) for f in fails)
                      else f"  ⚠️  {label} 有断言未过", flush=True)

        # ---- 2) R1 柱状图长标签不得压柱 ----
        long_label = "这是一个特别特别长的数据标签回归测试用例"
        out = str(Path(tmp) / "r1.svg")
        r = run_gen(["chart", "--title", "R1", "--chart-type", "bar",
                     "--data", f"{long_label}:80", "B:20"], PALETTES[0], out)
        if ok(r.returncode == 0, "R1 长标签 生成+校验", r.stderr[-200:]):
            svg = Path(out).read_text(encoding="utf-8")
            m = re.search(r'<text x="([\d.]+)" y="140"[^>]*>([^<]+)</text>', svg)
            b = BAR_RECT.search(svg)
            if ok(m and b, "R1 解析标签/柱子坐标", "未找到对应元素"):
                lx, shown = float(m.group(1)), m.group(2)
                bx = float(b.group(1))
                ok(bx >= lx + text_width(shown, 17), "R1 标签不压柱",
                   f"标签右缘 {lx + text_width(shown, 17):.0f}px vs 柱子 x={bx:.0f}px")

        # ---- R2 最小画布必须拒绝 ----
        r = subprocess.run([sys.executable, "gen.py", "cover", "--title", "R2", "--size", "200x150",
                            "--palette", PALETTES[0], "--out", str(Path(tmp) / "r2.svg")],
                           capture_output=True, text=True, cwd=str(SCRIPTS))
        ok(r.returncode != 0 and "画布过小" in (r.stdout + r.stderr),
           "R2 小画布拒绝", f"exit={r.returncode} out={(r.stdout + r.stderr)[:200]}")

        # ---- R3 柱状图条数守卫 ----
        out = str(Path(tmp) / "r3.svg")
        r = run_gen(["chart", "--title", "R3", "--chart-type", "bar", "--data"]
                    + [f"项{i}:{i + 1}" for i in range(12)], PALETTES[0], out)
        if ok(r.returncode == 0, "R3 超量数据 生成+校验", r.stderr[-200:]):
            ok("截断" in r.stderr, "R3 截断警告", "stderr 无截断提示")
            svg = Path(out).read_text(encoding="utf-8")
            ys = [float(y) for _, y in BAR_RECT.findall(svg)]
            H = float(re.search(r'height="(\d+)"', svg).group(1))
            ok(ys and max(ys) + 30 <= H, "R3 柱子不出界", f"最后一条 y+30={max(ys) + 30 if ys else 'NA'} vs H={H:g}")

        # ---- R4 环形图图例守卫 ----
        r = run_gen(["chart", "--title", "R4", "--chart-type", "donut", "--data"]
                    + [f"类{i}:{i + 1}" for i in range(12)], PALETTES[0], str(Path(tmp) / "r4.svg"))
        ok(r.returncode == 0 and "截断" in r.stderr, "R4 环形图例守卫",
           f"exit={r.returncode} stderr={r.stderr[-200:]}")

        # ---- R5 全配色卡对比度校验 ----
        r = subprocess.run([sys.executable, "palette.py", "check"],
                           capture_output=True, text=True, cwd=str(SCRIPTS))
        ok(r.returncode == 0, "R5 palette check", (r.stdout + r.stderr)[-300:])

        # ---- R6 sizes 子命令 ----
        r = subprocess.run([sys.executable, "gen.py", "sizes"],
                           capture_output=True, text=True, cwd=str(SCRIPTS))
        ok(r.returncode == 0 and "比例" in r.stdout, "R6 sizes 子命令", r.stdout[-200:])

    print()
    if fails:
        print(f"❌ {len(fails)}/{total} 项断言未通过：")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print(f"✅ 全部 {total} 项断言通过"
          f"（{len(CASES)} 版式用例 × {len(PALETTES)} 配色卡 + 6 个边界用例；"
          f"渲染验证{'已启用' if RSVG else '跳过（未装 rsvg-convert）'}）")


if __name__ == "__main__":
    main()
