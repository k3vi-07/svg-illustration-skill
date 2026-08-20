# svg-illustration-skill

用 SVG 设计**信息图 / 配图 / 封面 / 金句卡**并导出 PNG 的 Agent 技能包 —— 面向 AI 的一整套「**一次画对，不返工**」工具链。

## 这是什么

一个可复用的 Agent Skill（技能），指导并辅助 AI 完成 SVG 静态配图的完整流程：

```
选配色卡 → 填文案 → 排版 → 静态校验 → 渲染 → 程序化验证 → 嵌入
```

所有规则都来自**实测**（rsvg-convert 渲染 + 像素级验证），专门解决 AI 画 SVG 时最高频的坑：

| 坑 | 症状 | 本项目的解法 |
|---|---|---|
| 中文字体缺失 | 中文全变豆腐块 □□□ | `fc-match` 验字体 + 字体回退链 |
| SVG 里放 emoji | 渲染成实心方块 | emoji 静态检测 + 矢量替代 |
| 文字不换行/不测量 | 溢出、压到别的元素 | CJK 感知宽度估算 + 自动换行 |
| 背景框框不住文字 | 胶囊/卡片溢出 | 静态校验 + 框宽公式 |
| 对比度不足 | 小字看不清 | WCAG 对比度校验 |
| 封面被裁剪 | 分享后关键内容被切 | 公众号封面安全区规则 |

## 特性

- **12 种版式**：封面 / 信息图 / 金句卡 / 对比 / 步骤 / 数据卡 / 时间线 / 两栏图文 / 柱状图 / 环形图 / 线性流程 / 完整流程图（判断+分支+循环）/ 杂志海报
- **版式变体**：`--align left/center`、`--cols 1/2/N`、`--side left/right`、`--chart-type bar/donut`
- **丰富排版层次**：`--kicker` 眉题 + `--footer` 页脚 + `--deco dots/circles/grid/diag` 背景底纹
- **中文排版**：`east_asian_width` 驱动的宽度估算，中文按字断行、英文按词断行
- **写前验算**：SVG 静态检查（溢出 / 重叠 / emoji / 字体 / 对比度），先算后画，杜绝返工
- **守卫机制**：最小画布 360×200 硬校验、图表数据条数守卫、长标签自动截断——不再产出「校验通过但视觉是废图」的结果
- **程序化验证**：ASCII 预览 + 像素级包围盒 / 颜色定位 —— AI 无法直接看图时的「眼睛」
- **专业配色卡**：54 套对比度校验过的配色卡 + 系列配色 + 配色卡图生成
- **回归测试**：`tests/run_all.py`，13 版式用例 × 2 配色卡 + 9 边界用例共 163 项断言，改代码 15 秒验回归

## 效果演示

以下 **24 张示例**均由本 skill 一键生成（选配色卡 → 自动排版 → 静态校验 → 渲染），覆盖 **12 种版式 × 54 配色卡 × 4 种比例**：

### 封面 cover（900×383，`--align` / `--kicker` / `--deco` 变体）

<p align="center">
  <img src="examples/cover-tech.png" width="48%" alt="科技封面 · 深海蓝（眉题+底纹）">
  <img src="examples/cover-sale.png" width="48%" alt="促销封面 · 国潮红">
  <img src="examples/cover-finance.png" width="48%" alt="理财封面 · 金融科技">
  <img src="examples/cover-center.png" width="48%" alt="居中封面 · 晨雾蓝灰">
</p>

### 信息图 infographic（编号卡片，`--cols 2` / `--kicker` 变体）

<p align="center">
  <img src="examples/info-tutorial.png" width="48%" alt="教程信息图 · 教育">
  <img src="examples/info-guofeng.png" width="48%" alt="国风信息图 · 墨玉青（眉题+页脚）">
  <img src="examples/info-cols2.png" width="48%" alt="两列卡片 · 松石蓝绿（--cols 2）">
</p>

### 金句卡 quote（1:1，居中排版 + `--kicker`/`--deco` 变体）

<p align="center">
  <img src="examples/quote-munger.png" width="24%" alt="芒格金句 · 曜石黑金">
  <img src="examples/quote-literary.png" width="24%" alt="文学金句 · 绛紫霞（眉题+页脚+底纹）">
</p>

### 对比 / 步骤 / 流程 / 完整流程图 / 时间线

<p align="center">
  <img src="examples/compare-dev.png" width="48%" alt="对比图 · 墨玉青">
  <img src="examples/steps-flow.png" width="48%" alt="步骤图 · 松石蓝绿">
  <img src="examples/flowchart-refund.png" width="32%" alt="完整流程图 · 晨雾蓝灰（菱形判断+分支+循环回跳）">
  <img src="examples/flow-process.png" width="48%" alt="线性流程 · 晨雾蓝灰">
  <img src="examples/timeline-project.png" width="48%" alt="时间线 · 墨玉青">
</p>

### 数据卡 / 柱状图 / 环形图

<p align="center">
  <img src="examples/stats-data.png" width="48%" alt="数据卡 · 深海蓝（--cols 4 + 底纹）">
  <img src="examples/chart-bar.png" width="48%" alt="柱状图 · 静谧绿（标签列自适应）">
  <img src="examples/chart-donut.png" width="48%" alt="环形图 · 深海蓝">
</p>

### 两栏图文 / 杂志海报

<p align="center">
  <img src="examples/feature-adv.png" width="48%" alt="两栏图文 · 绛紫霞">
  <img src="examples/poster-magazine.png" width="32%" alt="杂志海报 · 曜石黑金（大数字+目录）">
</p>

### 任意比例（`--aspect` / `--size`）

<p align="center">
  <img src="examples/banner-launch.png" width="48%" alt="16:9 Banner（1200×675）">
  <img src="examples/poster-sakura.png" width="24%" alt="3:4 竖版（900×1200）">
  <img src="examples/og-share.png" width="48%" alt="1.91:1 OG 图（1200×630）">
</p>

### 配色卡（`palette.py card`，54 套任意出卡）

<p align="center">
  <img src="examples/palette-deep.png" width="44%" alt="配色卡 · 深海蓝">
  <img src="examples/palette-jade.png" width="44%" alt="配色卡 · 墨玉青">
</p>

## 12 种版式速查

| 版式 | 默认尺寸 | 必填 | 常用可选参数 |
|---|---|---|---|
| `cover` | 900×383 | `--title` | `--subtitle --badge --conclusion --kicker --footer --align left/center --deco` |
| `infographic` | 900×520 | `--title --points` | `--subtitle --conclusion --kicker --footer --cols 1/2` |
| `quote` | 900×900 | `--text` | `--author --kicker --footer --deco` |
| `compare` | 900×560 | `--title --left --right` | `--left-points --right-points --conclusion` |
| `steps` | 900×380 | `--title --steps` | 每项支持「标题:说明」 |
| `stats` | 900×420 | `--title --stats` | `--conclusion --cols N --deco`，每项「数值:标签」 |
| `timeline` | 900×560 | `--title --events` | 每项「时间\|标题\|说明」 |
| `feature` | 900×480 | `--title --points` | `--subtitle --side left/right`，每项「标题:说明」 |
| `chart` | 900×500 | `--title --data` | `--chart-type bar/donut`，每项「标签:数值」 |
| `flow` | 900×400 | `--title --steps` | 每项「标题:说明」（线性） |
| `flowchart` | 900×自适应 | `--title --main` | `--branches 「锚点\|标签\|节点;节点…」 --loops 「源\|标签\|目标」`；节点「名称?」=菱形判断 |
| `poster` | 900×1200 | `--title` | `--kicker --number --points --footer --deco` |

所有版式通用：`--palette`（配色卡）、`--size 宽x高` / `--aspect 宽:高 --width N`（任意比例）、`--font`、`--out`、`--check`（静态校验）、`--render`（导出 PNG）。

## 快速开始

### 依赖

- Python 3.8+（生成/校验全链路纯 stdlib）
- [rsvg-convert](https://gitlab.gnome.org/GNOME/librsvg)（librsvg，SVG→PNG）
- 一款中文字体（用 `fc-match` 验证真实存在）

### 一键生成一张图

```bash
# 环境检查（字体必须验证真实存在，否则中文变豆腐块）
which rsvg-convert && fc-match "LXGW WenKai"

# 生成公众号封面（默认 900×383，2.35:1）
python3 scripts/gen.py cover \
  --palette 深海蓝 \
  --title "AI 编程工具横评：谁更强" \
  --subtitle "Claude Code / Codex / Cursor 实测" \
  --kicker "特别企划" --badge "深度分析" \
  --conclusion "谁更值得用？一图看懂" \
  --footer "2026 · 第 88 期" --deco circles \
  --font "LXGW WenKai" --check --render

# 其它版式
python3 scripts/gen.py chart --palette 静谧绿 --title "季度营收" --chart-type bar \
  --data "Q1:120" "Q2:185" "Q3:240" "Q4:326" --check --render
python3 scripts/gen.py timeline --palette 墨玉青 --title "产品里程碑" \
  --events "2024|立项|方向确定" "2025|公测|注册 10 万" "2026|商业化|首次盈利" --check --render
python3 scripts/gen.py flowchart --palette 晨雾蓝灰 --title "退款处理流程" \
  --main "开始" "提交申请" "客服初审" "金额超限?" "财务打款" "结束" \
  --branches "金额超限?|是|主管复核" --loops "客服初审|资料不全|提交申请" --check --render

# 指定比例 / 尺寸
python3 scripts/gen.py cover --palette 晨雾蓝灰 --title "活动预告" --aspect 16:9 --width 1200
python3 scripts/gen.py quote --palette 春日樱 --text "樱花落下的速度，是秒速五厘米" --aspect 3:4 --width 900
python3 scripts/gen.py cover --palette 靛蓝 --title "分享卡" --size 1200x630
```

### 手动流程（完全可控）

```bash
python3 scripts/palette.py list                    # 1. 选配色卡
python3 scripts/textwidth.py "标题" --size 40      # 2. 估算文字宽度
#     写 design.svg（可基于 templates/ 改）
python3 scripts/check.py design.svg --margin 40    # 3. 静态校验（exit 0 再继续）
rsvg-convert -w 1200 design.svg -o design.png      # 4. 渲染（2x 高清）
python3 scripts/preview.py design.png              # 5. ASCII 目检布局
python3 scripts/verify.py design.png --boxes --mode bright --svg-width 900
```

### 回归测试

改过 `scripts/` 之后先跑测试套件（15 秒，纯 stdlib）：

```bash
python3 tests/run_all.py
# ✅ 全部 163 项断言通过（13 版式用例 × 2 配色卡 + 9 个边界用例）
```

边界用例是历史真实 bug 的回归锁：柱状图长标签不压柱、小画布（<360×200）必须拒绝、图表数据超量必须截断并警告等。

## 目录结构

```
svg-illustration-skill/
├── SKILL.md                        # 技能指令（完整工作流 + 实测坑速查）
├── scripts/
│   ├── svgtext.py                  # 共享：CJK 宽度估算 + emoji 检测
│   ├── textwidth.py                # 文字宽度估算（CLI）
│   ├── layout.py                   # 换行 / 居中 / 网格定位（wrap/center/grid）
│   ├── check.py                    # SVG 静态检查（溢出/重叠/emoji/字体/对比度）
│   ├── palette.py                  # 专业配色卡库 + 系列配色（list/show/check/card）
│   ├── gen.py                      # 一键生成（12 种版式 + 变体 + 装饰，任意比例）
│   ├── contrast.py                 # WCAG 对比度计算
│   ├── preview.py                  # PNG → ASCII 可视化
│   └── verify.py                   # 像素级范围/包围盒/颜色定位
├── tests/
│   └── run_all.py                  # 回归测试（12 版式×2 配色 + 6 边界用例）
└── templates/
    ├── cover-template.svg          # 公众号封面模板（含安全区提示）
    └── infographic-template.svg    # 正文信息图模板
```

## 脚本清单

| 脚本 | 作用 | 阶段 |
|---|---|---|
| `textwidth.py` | 估算文字渲染宽度（CJK 感知） | 写之前 |
| `layout.py` | 换行 / 居中 / 网格定位 | 写之前 |
| `check.py` | SVG 静态检查 | 写之前 |
| `palette.py` | 配色卡库 + 系列配色 | 选色 |
| `contrast.py` | WCAG 对比度 | 选色 |
| `gen.py` | 一键生成（12 种版式） | 写之前 |
| `preview.py` | ASCII 预览 | 渲染后 |
| `verify.py` | 像素级检测 | 渲染后 |
| `tests/run_all.py` | 回归测试 | 改动 scripts 后必跑 |

## 内置配色卡

54 套经过对比度校验的专业配色卡（以 `python3 scripts/palette.py list` 为准），节选：

| 配色卡 | 定位 | 深底 / 主强调 / 点缀 |
|---|---|---|
| 深海蓝 | 科技 / AI / 专业 | `#16223a` / `#1A6FC4` / `#7C6FE8` |
| 墨玉青 | 国风 / 文化 / 中式 | `#14352F` / `#2A9D8F` / `#E9C46A` |
| 绛紫霞 | 文艺 / 女性 / 情感 | `#2A1B3D` / `#7C3AED` / `#F472B6` |
| 晨雾蓝灰 | 商务 / 企业 / 数据 | `#1E293B` / `#3B82F6` / `#38BDF8` |
| 暖阳橙 | 生活 / 美食 / 活力 | `#2B1F16` / `#F59E0B` / `#FB7185` |
| 松石蓝绿 | 清新 / 教育 / 医疗 | `#12333B` / `#0EA5E9` / `#2DD4BF` |
| 静谧绿 | 环保 / 健康 / 自然 | `#14271E` / `#22C55E` / `#A3E635` |
| 曜石黑金 | 高端 / 发布会 / 奢华 | `#161616` / `#D4AF37` / `#9CA3AF` |
| 国潮红 | 节日 / 促销 / 国潮 | `#6B1414` / `#DC2626` / `#FBBF24` |
| 霓虹赛博 | 赛博朋克 / 游戏 / 电音 | `#0D0A14` / `#D946EF` / `#22D3EE` |
| 春日樱 | 春日 / 少女 / 浪漫 | `#3A1A2E` / `#EC4899` / `#F472B6` |
| 靛蓝 | 金融 / 法律 / 权威 | `#1E1B4B` / `#4F46E5` / `#6366F1` |
| …… | 共 54 套（含节日 / 行业 / 四季 / 风格系列） | `palette.py list` 查看 |

## 常用画布尺寸

`python3 scripts/gen.py sizes`：

| 用途 | 尺寸 | 比例 |
|---|---|---|
| 公众号封面 | 900×383 | 2.35:1 |
| 正文信息图 | 900×540 | 5:3 |
| 正方形金句卡 | 900×900 | 1:1 |
| 小红书配图 | 900×1200 | 3:4 |
| 社交分享 / OG 图 | 1200×630 | 1.91:1 |
| 横版 Banner | 1200×675 | 16:9 |
| 竖版海报 | 900×1600 | 9:16 |

## 字体版权

本仓库**只写字体名、不打包任何字体文件**；渲染在你本机用已安装的字体完成，输出是 PNG 位图，因此不涉及字体再分发或嵌入问题。

- **推荐使用 OFL 免费商用字体**（可商用、可嵌入、可再分发）：思源黑体（Source Han Sans / Noto Sans CJK SC）、思源宋体（Source Han Serif / Noto Serif SC）、霞鹜文楷（LXGW WenKai）、得意黑（[Smiley Sans](https://github.com/atelier-anchor/smiley-sans)，斜体窄黑，适合标题/展示）
- **系统专有字体**（PingFang SC 苹方、Hiragino、微软雅黑）**能显示 ≠ 能免费商用**：公众号封面 / 商品图等商用场景渲染它们存在侵权风险（微软雅黑版权在方正），且**不要提交其 .ttf/.ttc 文件到仓库再分发**。商用请一律用上一条的 OFL 字体。

本项目 README 中的演示图均使用霞鹜文楷（OFL 1.1）渲染。

## License

[MIT](./LICENSE)
