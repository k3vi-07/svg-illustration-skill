---
name: svg-illustration
description: 用 SVG 设计信息图/配图/封面并导出 PNG 的技能。Use whenever the user wants to create 配图/插图/信息图/示意图/封面图 for an article, document, or WeChat 公众号 post; mentions SVG, 用图/画图/做图, 图片重叠, 文字溢出, 豆腐块, 字体缺失, 封面尺寸, 文字宽度, 对比度, 配色卡, 系列配色; or already has SVG files that need 导出 PNG / 修复渲染问题 / 验证布局. Covers layout design, Chinese font handling, text-width estimation, static SVG checking, overlap detection, contrast checking, templates, and PNG export.
---

# SVG 信息图配图技能

用 SVG 设计高质量信息图/配图/封面，导出 PNG 嵌入文档或公众号。**本技能的所有坑都来自实测**（rsvg-convert 渲染 + 像素级验证），核心目标是：**一次画对，不返工**。

配套脚本（`scripts/` 目录，纯 Python + Pillow，无其他依赖）：

| 脚本 | 作用 | 阶段 |
|---|---|---|
| `scripts/textwidth.py` | 估算文字渲染宽度（CJK 感知） | 写 SVG 之前 |
| `scripts/layout.py` | 文字换行 / 居中 / 网格定位计算 | 写 SVG 之前 |
| `scripts/gen.py` | 一键生成封面/信息图/金句卡（配色卡+自动排版） | 写 SVG 之前 |
| `scripts/check.py` | **SVG 静态检查**：溢出/重叠/emoji/字体/对比度 | 写 SVG 之前 |
| `scripts/palette.py` | 专业配色卡库 + 系列配色 + 生成配色卡图 | 选颜色时 |
| `scripts/contrast.py` | WCAG 对比度计算 | 选颜色时 |
| `scripts/preview.py` | PNG → ASCII 可视化（看布局） | 渲染之后 |
| `scripts/verify.py` | 像素级范围/包围盒/颜色定位 | 渲染之后 |

---

## 核心工作流（6 步）

```
① 环境检查（字体！最关键，跳过必踩坑）
② 写之前先验算（textwidth + check.py 静态检查，★ 新增，杜绝返工）
③ 设计布局（分区独立、留白、配色、模板、换行/居中/网格）
④ 渲染导出（rsvg-convert，2x 高清）
⑤ 程序化验证（preview.py / verify.py，模型不能直接看图时的替代方案）
⑥ 嵌入文档/公众号
```

---

## Step 1: 环境检查（30 秒，跳过必踩坑）

### 1a. 检查渲染工具

```bash
which rsvg-convert        # 首选：librsvg，命令行 SVG→PNG
which inkscape convert magick   # 备选
python3 -c "import cairosvg"    # 备选（Python）
```

至少有一个可用才继续。**推荐 `rsvg-convert`**：快、纯 CLI、无 GUI 依赖。

### 1b. 确定中文字体（★ 最关键，务必逐字照做）

**先说结论**：默认用 **OFL 免费商用字体**（思源黑体 / 霞鹜文楷 / 得意黑等，全部可商用、可嵌入、可内置打包）；渲染前必须 `fc-match` 验证字体真实存在，把**验证过的字体名写到 `font-family` 的第一位**。

**为什么**：SVG 里的 `font-family` 只是"请求"，找不到就静默回退——回退到无中文字形的字体时，中文全部变**豆腐块（□□□）**。

#### ① 推荐字体清单（全部 SIL OFL 1.1，免费商用 + 可嵌入 + 可内置）

| 用途 | 写在 font-family 里的名字 | 类别 |
|---|---|---|
| 信息图 / 封面默认 | `Source Han Sans SC` / `Noto Sans CJK SC`（思源黑体） | 黑体 |
| 国风 / 正文 / 标题 | `Source Han Serif SC` / `Noto Serif SC`（思源宋体） | 宋体 |
| 文艺 / 手写 / 金句卡 | `LXGW WenKai`（霞鹜文楷） | 楷体 |
| 标题 / 展示 / 海报 | `Smiley Sans`（得意黑，斜体窄黑，视觉冲击强） | 黑体 |

> **版权（重要）**：上表全部为 [SIL OFL 1.1](https://openfontlicense.org/)，免费商用、可嵌入 PDF/SVG、可把 .otf/.ttf **内置打包**进项目（例如 [得意黑 Smiley Sans](https://github.com/atelier-anchor/smiley-sans)）。**系统字体 ≠ 免费商用**：`PingFang SC`（苹方）、`Microsoft YaHei`（微软雅黑，版权在方正）等本机虽能正常显示，但把它们的渲染结果用于**公众号封面、商品图、海报、logo 等商用场景存在侵权风险**，也**不可分发/内置**——**商用一律用上表 OFL 字体，系统字体不要写进默认链**。

#### ② 查你机器上实际有哪些（30 秒）

```bash
fc-list | grep -iE "source han|noto|wenkai|wangkai|smiley|songti|pingfang|hiragino|yahei" | head
fc-match "Smiley Sans"   # 必须返回中文字体；返回 DejaVu Sans 就说明该字体不存在
```

**踩坑实录**：某系统 `fc-match "PingFang SC"` 回退到 `DejaVuSans.ttf`（无中文字形）→ 全部中文变豆腐块；该机实际可用的是 `LXGW WenKai`、`Noto Serif SC`、`Hiragino Kaku Gothic Pro`。

#### ③ 写进 SVG（字体名换成②里验证过的，放第一位）

统一用 `<style>` 声明（模板和 `gen.py` 都这样做），给整份图一条回退链：

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="520" viewBox="0 0 900 520">
  <style>
    text { font-family: "Source Han Sans SC", "Noto Sans CJK SC", "LXGW WenKai", "Smiley Sans", sans-serif; }
  </style>
  <text x="40" y="80" font-size="40" fill="#16223a">标题文字</text>
</svg>
```

**默认回退链（全部免费商用；可直接复制，第一位务必换成你 `fc-match` 验证过的字体）**：

```
"Source Han Sans SC", "Noto Sans CJK SC", "LXGW WenKai", "Smiley Sans", sans-serif
```

末尾放 `LXGW WenKai`、`Smiley Sans`（均 OFL、全 CJK 覆盖）兜底，避免最后落到无中文字形的 `sans-serif` 变豆腐块。`gen.py` 的默认字体和模板都用这条链，用 `--font` 传验证过的字体即可覆盖。

> **想彻底不依赖系统字体**：直接下载一款 OFL 字体的 .otf/.ttf（如 [得意黑 Smiley Sans 的 release](https://github.com/atelier-anchor/smiley-sans/releases)）内置到项目，安装或 `fontconfig` 挂载后渲染——OFL 允许这样做，绝无版权风险。

> 写法区别：写在 `<style>` 的 CSS 里，带空格的字体名要**加引号**（如模板那样）；写在 `<text font-family="...">` **属性**里则**不加引号**（如 `gen.py` 的默认值）。两种都可用，效果一致。

#### ④ 铁律

1. **先 `fc-match` 验证，再写 SVG**，把验证过的字体名放 `font-family` 第一位。
2. **SVG 里绝对不要放 emoji**（🚗🛸🧱📊🏆 等）——rsvg 无 emoji 字形会渲染成实心方块。用矢量图形或纯文字代替。
3. fontconfig 报 `No writable cache directories` 是噪音，忽略；只要 `fc-match` 返回正确即可。
4. **字体版权：能显示 ≠ 能免费商用**。公众号封面、商品图、海报等**商用场景一律用 OFL 字体**；`PingFang SC` / `Microsoft YaHei` 等系统字体即便本机能正常显示，商用渲染也**有侵权风险**（微软雅黑版权在方正）。本 skill 默认链只含 OFL 字体、只写字体名不打包字体文件，无版权风险。

#### ⑤ 商用字体自查清单（动手前 3 问）

只要产出可能商用（公众号封面 / 商品图 / 海报 / logo / 广告），动手前逐条确认：

1. **授权可商用吗？** 只认 SIL OFL 1.1 或明确标注「免费商用」的字体（如①里的四款）。
2. **是不是系统自带字体？** `PingFang SC` / `Microsoft YaHei` / `Hiragino` 等系统字体，**能显示 ≠ 能商用**，商用渲染即踩线。
3. **用在哪？** 涉及封面 / 商品图 / 海报 / logo 等商用场景 → **只用 OFL 字体**。

> 判定一句话：**不确定能不能商用，就当它不能商用**，换 OFL 字体。三条任一存疑，一律换 OFL。

---

## Step 2: 写之前先验算（★ 核心增强：杜绝返工）

写 SVG 之前，用两个脚本把"宽度溢出 / 元素重叠 / emoji / 字体 / 对比度"全部算一遍，**不要画完才返工**。

### 2a. 估算文字宽度（textwidth.py）

SVG 的 `<text>` 是**单行、不自动换行、不自动缩小**的。文字超出画布就溢出，压到旁边的元素就是"重叠"。

```bash
python3 scripts/textwidth.py "凭什么敢和 Claude Code、Codex 叫板？" --size 37
python3 scripts/textwidth.py "深度分析 · AI 编程工具" --size 15
printf '%s\n' "标题一" "标题二" | python3 scripts/textwidth.py --batch --size 24
```

宽度公式（脚本内部用 `unicodedata.east_asian_width` 实现，比硬编码 Unicode 区间更准）：

| 字符类型 | 宽度（×字号） |
|---|---|
| 全角/宽字符（汉字、中文标点、全角符号） | 1.0 |
| 歧义字符（`·` `—` 等） | 0.5（`--ambiguous` 可调） |
| 空格 | 0.3 |
| 拉丁字母/数字/半角标点 | 0.55 |

**核心规则**：`元素起点 x + 估算宽度 < 下一元素起点 x`，每个元素都验一遍再写。

例：标题 `凭什么敢和 Claude Code、Codex 叫板？` 37px → 估宽 ≈ **672px**，从 `x=42` 起：`42 + 672 = 714 < 790` ✅（右侧 VS 徽章在 `x=790`）。若 `> 790` → 缩小字号 / 缩短文案 / 把右侧元素移走。

### 2b. SVG 静态检查（check.py，★ 一键全查）

写完 SVG（哪怕只写了草稿），跑一遍检查，能自动抓出 6 类问题：

```bash
python3 scripts/check.py design.svg                    # 基本检查
python3 scripts/check.py design.svg --margin 40        # 指定留白阈值（贴近边缘报警）
python3 scripts/check.py design.svg --contrast "#16223a"   # 检查文字对比度
```

检查项与判定：

| # | 检查项 | 硬错误（必须修） | 软警告（人工确认） |
|---|---|---|---|
| 1 | 文字宽度估算 + 越界 | 越出画布边界 | 贴近留白边缘 |
| 2 | 相邻文字水平重叠 | 同一行带内重叠 | — |
| 3 | 超出背景框（胶囊/卡片） | 文字横向超出框 | 框偏窄（<文字宽+30px） |
| 4 | emoji | 发现 emoji（rsvg→方块） | — |
| 5 | 缺 font-family | — | 未显式声明（依赖继承） |
| 6 | 文字/背景对比度 | — | 低于 WCAG AA |

- **硬错误 → `exit 1`，先修再渲染**；只有警告 → `exit 0`。
- 对比度背景自动取「所在最小 `<rect>`/`<circle>` 的 fill」，其次全画布背景矩形，最后 `--contrast`。
- 已知局限：`<g>` 上继承的 font-size 不会完全解析（用 `--font-size` 兜底）；`<path>`/`<polygon>` 作背景时对比度不识别（用 `--contrast` 手动指定）。

### 2c. 颜色对比度（contrast.py）

选文字颜色前先算，避免文字看不清：

```bash
python3 scripts/contrast.py "#ffffff" "#16223a"   # 白字深底
python3 scripts/contrast.py "#1A6FC4" "#16223a"   # 主蓝 on 深底（实测 3.11:1，仅大字达标）
```

判定标准：普通文字 ≥4.5:1（AA）/ ≥7:1（AAA）；大字（≥24px）≥3:1（AA）/ ≥4.5:1（AAA）。

---

## Step 3: 设计布局（画之前先算，画完不用返工）

### 3a. 画布与留白

| 用途 | 建议尺寸（SVG viewBox） |
|---|---|
| 公众号封面 | `900×383`（2.35:1）或 `900×500`（1.8:1 信息更密） |
| 正文信息图 | `900×520` ~ `900×560` |
| 正方形金句卡 | `900×900` |

**任意比例/尺寸**：手写 SVG 直接改 `width/height/viewBox`；用 `gen.py` 生成则加 `--size 宽x高`（精确）或 `--aspect 宽:高 --width 宽`（按比例），三种图（cover/infographic/quote）都支持。常用平台尺寸速查：`python3 scripts/gen.py sizes`（公众号封面 / 小红书 3:4 / OG 1.91:1 / Banner 16:9 / 竖版海报 9:16 等）。

- **四周留白 ≥ 40px**，元素不要贴边
- **分区独立**：标题区 / 图形区 / 底部结论条 各占一块，**不同功能区的元素禁止共用同一高度带**（这是"重叠"的第一来源）

### 3b. 文字背景

- 标题文字直接放**纯色背景**上（不要放在装饰线/网格上——装饰线会从文字间隙透出来，观感极差）
- 需要"徽章/胶囊"时，**背景框要预留足够宽度**：`深度分析 · AI 编程工具`（15px）估宽 158px，背景框至少 `158 + 2×15 = 188px`。**框宽 = 估算文字宽 + 左右各 ≥15px 余量**（`check.py` 会自动校验）

### 3c. 配色建议（附实测对比度）

| 用途 | 颜色 | 在深底 `#16223a` 上的对比度 |
|---|---|---|
| 深色主背景/底部结论条 | `#16223a` / `#141f36` | — |
| 主强调蓝 | `#1A6FC4` / `#4EA8E8` | `#1A6FC4`→3.11:1（仅大字）；`#4EA8E8`→6.11:1 ✅ |
| 警告/对比橙 | `#F5A623` | 7.83:1 ✅ |
| 对比红 | `#E34D3A` | 4.07:1（仅大字） |
| 成功绿 | `#2E8B57` | 3.74:1（仅大字） |
| 浅背景卡片 | `#f7f9fc`，边框 `#e8eef6` | 深色文字 on 它 15:1 ✅ |

**注意**：`#1A6FC4` 直接放深色背景上做小字会偏暗（3.11:1），做**大标题或图标色块**可以，小字建议用更亮的 `#4EA8E8` 或白字。

### 3d. 模板（templates/，可直接改）

| 模板 | 尺寸 | 用途 |
|---|---|---|
| `templates/cover-template.svg` | 900×383 | 公众号封面 |
| `templates/infographic-template.svg` | 900×520 | 正文信息图（三卡片+结论条） |

模板已内置：分区独立、留白、字体回退链、徽章框宽、无 emoji、对比度达标。**用前先做两件事**：① `fc-match` 把 `font-family` 换成验证过的字体；② `python3 scripts/check.py` 该文件验算一遍。

> **更快的方式**：`scripts/gen.py` 一键生成（套配色卡 + 自动换行/居中/网格 + 可选校验/渲染），见下方 3f 与「完整工作流示例」。

> 小坑：SVG 的 XML 注释里**不能出现 `--`**（会被当成注释结束符导致解析失败）。模板注释里若写命令行参数，用「留白阈值 40px」这类描述代替 `--margin 40`。

### 3e. 专业配色卡 / 系列配色（palette.py）

**做系列内容（同一栏目多篇、多张封面/信息图）时，固定用一张配色卡，只换文案与图形、颜色统一 → 一眼看出是同一个系列。**

内置 18 张经过对比度校验的专业配色卡（`scripts/palette.py`，全部通过 `check` 校验）：

| # | 配色卡 | 定位 | 深底 bg / 主强调 / 点缀 |
|---|---|---|---|
| 1 | 深海蓝 | 科技 / AI / 专业 | `#16223a` / `#1A6FC4` / `#7C6FE8` |
| 2 | 墨玉青 | 国风 / 文化 / 中式 | `#14352F` / `#2A9D8F` / `#E9C46A` |
| 3 | 绛紫霞 | 文艺 / 女性 / 情感 | `#2A1B3D` / `#7C3AED` / `#F472B6` |
| 4 | 晨雾蓝灰 | 商务 / 企业 / 数据 | `#1E293B` / `#3B82F6` / `#38BDF8` |
| 5 | 暖阳橙 | 生活 / 美食 / 活力 | `#2B1F16` / `#F59E0B` / `#FB7185` |
| 6 | 松石蓝绿 | 清新 / 教育 / 医疗 | `#12333B` / `#0EA5E9` / `#2DD4BF` |
| 7 | 静谧绿 | 环保 / 健康 / 自然 | `#14271E` / `#22C55E` / `#A3E635` |
| 8 | 曜石黑金 | 高端 / 发布会 / 奢华 | `#161616` / `#D4AF37` / `#9CA3AF` |
| 9 | 珊瑚粉 | 女性 / 母婴 / 婚恋 | `#33101F` / `#F43F5E` / `#FB7185` |
| 10 | 电光紫 | 科技 / AI / 未来 | `#170A2E` / `#8B5CF6` / `#22D3EE` |
| 11 | 极简黑白 | 极简 / 杂志 / 高端 | `#111111` / `#52525B` / `#A1A1AA` |
| 12 | 国潮红 | 节日 / 促销 / 国潮 | `#6B1414` / `#DC2626` / `#FBBF24` |
| 13 | 莫兰迪 | 文艺 / 柔和 / 治愈 | `#3E3A36` / `#9C8A74` / `#8E8AA0` |
| 14 | 薄荷绿 | 健康 / 医疗 / 清新 | `#0E2A22` / `#10B981` / `#34D399` |
| 15 | 咖啡棕 | 咖啡 / 复古 / 商务 | `#2B1D15` / `#C2703D` / `#A1622B` |
| 16 | 香槟金 | 婚庆 / 高端 / 轻奢 | `#4A3823` / `#C9A227` / `#B8912B` |
| 17 | 马卡龙 | 甜点 / 可爱 / 儿童 | `#3D2B3A` / `#F472B6` / `#A78BFA` |
| 18 | 复古橄榄 | 复古 / 军工 / 户外 | `#2A2A1A` / `#B9A61A` / `#6B8E23` |

```bash
python3 scripts/palette.py list                  # 列出全部配色卡
python3 scripts/palette.py show "深海蓝"          # 查看单张：每个角色 hex + 关键对比度
python3 scripts/palette.py check                  # 校验所有卡的对比度（exit 0 = 全达标）
python3 scripts/palette.py roles                  # 打印角色说明
python3 scripts/palette.py card "深海蓝" --font "LXGW WenKai" --render   # 生成配色卡图（SVG+PNG）
```

- 每张卡 13 个角色：`bg`(深底) / `band`(深底次级) / `surface`(浅卡片) / `border` / `primary` / `primary_soft` / `accent` / `warning` / `danger` / `success` / `ink` / `ink_muted` / `light`
- **深底封面**用 `bg`+`band`+`primary`+`light`；**浅底信息图**用 `surface`+`ink`+`primary`——同一张卡两套场景都自洽
- `card` 生成配色卡图时**务必用 `--font` 传 `fc-match` 验证过的中文字体**（默认字体链在无中文字体的机器上会豆腐）
- 想加自己的卡：编辑 `scripts/palette.py` 里的 `PALETTES`，照抄一个对象改 hex，然后 `palette.py check` 验一遍

### 3f. 布局进阶（换行 / 居中 / 网格 / 封面安全区）

SVG 的 `<text>` **不自动换行、不自动居中、不自动测量**，多行文字全靠手排 y 坐标——`scripts/layout.py` 把这类计算自动化：

```bash
# 1. 自动换行（CJK 按字断行，英文按词断行，保留中英间空格）
python3 scripts/layout.py wrap "凭什么敢和 Claude Code、Codex 叫板？" --size 37 --max-width 600 --y 100 --line-height 1.5 --svg

# 2. 框内水平+垂直居中（输出 text-anchor 与 baseline）
python3 scripts/layout.py center "深度分析" --size 24 --box 40 205 230 46

# 3. N 个元素等分定位（单行或多行网格）
python3 scripts/layout.py grid 4 --width 900 --margin 40 --gap 24
```

**四条布局公式（记牢，手排也不踩坑）：**

| 需求 | 公式 |
|---|---|
| 行高 | `第 i 行 baseline y = 首行 y + i × 行高倍数 × 字号`（行高倍数常用 1.5~1.6） |
| 水平居中 | `x = 框中心 x`，配 `text-anchor="middle"` |
| 垂直居中 | `baseline y = 框中心 y + 0.35 × 字号`（渲染偏上/偏下时在 0.3~0.4 微调） |
| 等分网格 | `元素宽 = (画布宽 − 2×留白 − (列数−1)×间距) / 列数`，`x = 留白 + 列号 × (元素宽 + 间距)` |

**公众号封面安全区（900×383，2.35:1）**——封面会经历两种裁剪，文字位置要兼顾：

1. **信息流列表**：以 2.35:1 全宽显示，别把关键信息贴边/贴角（四周留 ≥40px）
2. **转发/分享**：会**居中裁成 1:1 正方形**，左右各裁掉约 `(900−383)/2 ≈ 258px` → **核心信息放在中间 1:1 区域（x≈258~642），左右边缘的内容会被切掉**
3. 列表/分享里标题文字会**单独显示在封面下方**，所以封面上的字要精简，别和标题重复

> 参考：[公众号封面尺寸与防裁切安全区](https://tudingai.cn/cover-size/)

---

## Step 4: 渲染导出

```bash
# 2x 高清（导出宽度 = 目标显示宽度 × 2）
rsvg-convert -w 1200 input.svg -o output.png

# 封面专用尺寸
rsvg-convert -w 900 cover.svg -o cover-900x383.png   # 若 viewBox 是 900x383
```

- 建议导出 **1200px 宽**（公众号正文显示 600px 左右，2x 清晰）
- 导出后 `file output.png` 确认尺寸正确

---

## Step 5: 程序化验证（★ 模型不能直接看图时的核心手段）

AI agent（如本技能使用者）通常**无法直接查看 PNG**，必须用程序化手段验证渲染结果。

### 5a. ASCII 可视化（preview.py，看整体布局）

```bash
python3 scripts/preview.py assets/cover.png
python3 scripts/preview.py assets/card.png --width 120 --auto-contrast   # 低对比图拉伸
python3 scripts/preview.py assets/cover.png --color "#F5A623"            # 高亮某颜色位置（'#'=该色）
```

- `--auto-contrast`：按整图亮度范围拉伸，浅色/低对比图更清晰
- `--color`：只高亮目标颜色所在位置，用于确认"某元素画在哪"（输出里 `#` 密集处就是该元素）

### 5b. 像素级检测（verify.py，精确到 px）

```bash
# 单行扫描：某一行上目标像素的 x 分段
python3 scripts/verify.py assets/cover.png --y 243 --mode bright --svg-width 900

# 全图包围盒：内容块位置（--merge 把逐字拆开的文字合并成区域）
python3 scripts/verify.py assets/card.png --boxes --mode dark --svg-width 900 --svg-height 520

# 颜色定位：精确找某个色块（如橙色警告条）的位置
python3 scripts/verify.py assets/cover.png --color "#F5A623" --boxes --svg-width 900
```

关键检查项：
- **深色背景图**（封面）：文字是**亮像素**（`>140`）→ 用 `--mode bright`
- **浅色背景图**（正文卡片）：图形/文字是**暗像素**（`<120`）→ 用 `--mode dark`
- **检测模式用错会全图误报**（例：深色背景上检测暗像素会把背景全算进去）
- `--boxes` 默认 `--merge 12` 把相邻像素块合并；文字逐字拆开是正常现象，看合并后的区域即可
- `--svg-width/--svg-height` 把 PNG 坐标映射回 SVG viewBox 坐标，方便回查源文件

### 5c. 必须验证的 4 件事

| # | 验证项 | 方法 |
|---|---|---|
| 1 | 文字没有豆腐块 | `fc-match` 字体存在（Step 1b）+ ASCII 文字区域是笔画纹理（稀疏不规则）而非实心方块 |
| 2 | 元素无重叠 | `check.py` 已验 + `verify.py --boxes` 确认各区域不相交 + ASCII 目检 |
| 3 | 背景框完整框住文字 | `check.py`（文字 ⊆ 背景框）+ `verify.py --color` 定位框与文字 |
| 4 | 中文正常渲染 | `fc-match` + ASCII 文字区域有笔画 |

---

## Step 6: 嵌入文档/公众号

### Markdown

```markdown
![图注文字](assets/xxx.png)
```
- 图片放 md 同级 `assets/` 目录，相对路径引用
- 图注 alt 文字写清楚，Typora/VS Code/GitHub 直接渲染

### 微信公众号

**微信对"内联 `<svg>` 标签"支持极不稳定**（经常被剥离），但 `<img>` 引用 PNG 100% 安全。所以：

1. **用导出的 PNG**，不要直接贴 SVG
2. 图片必须上传微信图床（`media/uploadimg`）拿 `mmbiz.qpic.cn` 永久链接，外链图片不显示
3. 封面用 `900×383`（2.35:1）的 PNG，上传 `material/add_material` 拿 `thumb_media_id`

---

## 常见坑速查表（全部实测）

| 症状 | 原因 | 解法 |
|---|---|---|
| 中文全是方块 □□□ | 渲染字体无中文字形 | `fc-match` 找真实存在的字体，SVG 写它 |
| 标题处有实心方块，像元素重叠 | SVG 里用了 emoji | 删 emoji，用矢量图形/纯文字（`check.py` 会自动抓） |
| 文字压到旁边图形上 | 文字太宽溢出（SVG 不自动换行） | `textwidth.py` 估算宽度，缩字号/移元素 |
| 多行文字行距不齐 / 第二行叠第一行 | 手排每行 y 坐标算错 | `layout.py wrap --svg` 自动换行 + 算每行 baseline |
| 徽章/胶囊里文字偏上或偏下 | baseline 没做垂直居中 | `baseline = 框中心 y + 0.35×字号`（`layout.py center`） |
| 封面分享后被裁掉关键内容 | 公众号分享按 1:1 居中裁切 | 核心信息放中间 1:1 区（左右各留约 258px） |
| 背景框没框住文字 | 框宽 < 文字实际宽 | 框宽 = 估算文字宽 + 两侧 ≥15px（`check.py` 校验） |
| 装饰线从文字底下透出 | 文字放在网格/装饰线上 | 文字放纯色背景或加底板 |
| 浅色图上检测"重叠"误报全图 | 检测模式用错 | 浅底 `--mode dark`，深底 `--mode bright` |
| 导出的图发虚 | 只导出了 1x | 导出宽度 = 显示宽度 × 2 |
| 小字颜色看不清 | 文字/背景对比度不足 | `contrast.py` 或 `check.py --contrast` 验算 |
| SVG 解析报 `not well-formed` | XML 注释里出现 `--` | 注释里别写 `--margin` 这类带双连字符的参数 |
| `fc-match` 返回 DejaVu Sans | 请求的字体不存在 | 换 `fc-list` 里真实存在的中文字体名 |

---

## 完整工作流示例（一图走完）

**快速路径（一键生成）**：`python3 scripts/gen.py cover --palette 深海蓝 --title "..." --subtitle "..." --font "LXGW WenKai" --check --render` —— 套配色卡 + 自动排版 + 校验 + 渲染一条命令搞定。

**手动路径（完全可控）**：

```bash
# 1. 环境（工具 + 字体，字体必须验证真实存在）
which rsvg-convert && fc-match "LXGW WenKai"

# 2. 写之前验算（★ 关键：先算后画）
python3 scripts/textwidth.py "你的主标题文案" --size 40          # 估宽度
#    写 design.svg（可基于 templates/ 改，分区独立、无 emoji、纯色背景）
python3 scripts/check.py design.svg --margin 40 --contrast "#16223a"   # 静态检查，exit 0 再继续

# 3. 渲染
rsvg-convert -w 1200 design.svg -o assets/design.png
file assets/design.png

# 4. 验证
python3 scripts/preview.py assets/design.png                    # ASCII 看布局
python3 scripts/verify.py assets/design.png --boxes --mode bright --svg-width 900 --svg-height 520

# 5. 嵌入
#    Markdown: ![图注](assets/design.png)
#    公众号: 上传图床拿 mmbiz 链接，用 <img> 嵌入
```

---

## 脚本清单与依赖

- `scripts/svgtext.py` —— 共享模块：CJK 宽度估算 + emoji 检测（`textwidth.py` / `check.py` 依赖它）
- `scripts/textwidth.py` —— 文字宽度估算（CLI，`--batch` 支持逐行）
- `scripts/layout.py` —— 文字换行 / 居中 / 网格定位（wrap / center / grid）
- `scripts/gen.py` —— 一键生成配图（cover / infographic / quote，套配色卡+自动排版）
- `scripts/check.py` —— SVG 静态检查（溢出/重叠/emoji/字体/对比度）
- `scripts/palette.py` —— 专业配色卡库 + 系列配色（list/show/check/card）
- `scripts/contrast.py` —— WCAG 对比度计算
- `scripts/preview.py` —— PNG → ASCII 可视化（`--auto-contrast` / `--color` 高亮）
- `scripts/verify.py` —— 像素级检测（`--y` / `--y-range` / `--boxes` / `--color`）

全部纯 Python + Pillow（`pip install Pillow`），`check.py`/`textwidth.py` 需与 `svgtext.py`、`contrast.py` 同目录。
