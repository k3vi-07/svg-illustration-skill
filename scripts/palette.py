#!/usr/bin/env python3
"""专业配色卡库 + 系列配色工具（纯 stdlib，渲染 PNG 需 rsvg-convert）。

用途：
  - 为一个系列（多篇文章 / 多张封面 / 多张信息图）统一配色，保持「系列感」
  - 每张卡都覆盖「深底封面」与「浅底信息图」两套场景，取色即可用
  - 生成配色卡 SVG/PNG，方便对比挑选

子命令：
    list            列出全部配色卡（名称 + 一句话定位 + 关键色）
    show NAME       展示单张：每个角色 hex + 用途 + 关键对比度
    check [NAME]    对比度校验（不给 NAME 则校验全部），有不达标项时 exit 1
    card NAME       生成配色卡 SVG（--out 指定路径，--render 顺带导出 PNG）
    roles           打印角色（role）说明

用法示例：
    python3 palette.py list
    python3 palette.py show "深海蓝"
    python3 palette.py check
    python3 palette.py card "深海蓝" --render

依赖同目录 contrast.py（对比度计算）。
"""

# ======================================================================
# 配色卡数据 —— 在下方按同样结构添加你自己的卡即可
# 每个角色含义见 ROLES；hex 统一 6 位（#RRGGBB，可省略 #）
# ======================================================================

ROLES = [
    ("bg",           "深色主背景"),
    ("band",         "深色次级背景 / 底部结论条"),
    ("surface",      "浅色卡片背景"),
    ("border",       "浅色卡片边框"),
    ("primary",      "主强调色"),
    ("primary_soft", "主强调亮色（深底上的可读点缀）"),
    ("accent",       "第二强调色（点缀 / 图标）"),
    ("warning",      "警告 / 对比橙"),
    ("danger",       "对比红"),
    ("success",      "成功绿"),
    ("ink",          "主文字色（浅底用）"),
    ("ink_muted",    "次级文字灰"),
    ("light",        "深底上的文字（近白）"),
]

PALETTES = [
    {
        "name": "深海蓝",
        "desc": "科技 / AI / 专业，稳重冷静",
        "colors": {
            "bg": "#16223a", "band": "#141f36",
            "surface": "#f7f9fc", "border": "#e8eef6",
            "primary": "#1A6FC4", "primary_soft": "#4EA8E8",
            "accent": "#7C6FE8",
            "warning": "#F5A623", "danger": "#E34D3A", "success": "#2E8B57",
            "ink": "#16223a", "ink_muted": "#5a6b85", "light": "#ffffff",
        },
    },
    {
        "name": "墨玉青",
        "desc": "国风 / 文化 / 中式，温润雅致",
        "colors": {
            "bg": "#14352F", "band": "#0F2A26",
            "surface": "#f5f8f7", "border": "#e2ece9",
            "primary": "#2A9D8F", "primary_soft": "#7FD8C7",
            "accent": "#E9C46A",
            "warning": "#F4A261", "danger": "#E76F51", "success": "#2A9D8F",
            "ink": "#14352F", "ink_muted": "#4E6B64", "light": "#ffffff",
        },
    },
    {
        "name": "绛紫霞",
        "desc": "文艺 / 女性 / 情感，神秘优雅",
        "colors": {
            "bg": "#2A1B3D", "band": "#201330",
            "surface": "#faf7fb", "border": "#eadff2",
            "primary": "#7C3AED", "primary_soft": "#B794F6",
            "accent": "#F472B6",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#10B981",
            "ink": "#2A1B3D", "ink_muted": "#6b5b7d", "light": "#ffffff",
        },
    },
    {
        "name": "晨雾蓝灰",
        "desc": "商务 / 企业 / 数据，克制专业",
        "colors": {
            "bg": "#1E293B", "band": "#0F172A",
            "surface": "#f8fafc", "border": "#e2e8f0",
            "primary": "#3B82F6", "primary_soft": "#93C5FD",
            "accent": "#38BDF8",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#0F172A", "ink_muted": "#64748B", "light": "#ffffff",
        },
    },
    {
        "name": "暖阳橙",
        "desc": "生活 / 美食 / 活力，温暖亲切",
        "colors": {
            "bg": "#2B1F16", "band": "#1F150E",
            "surface": "#fdf9f3", "border": "#f0e6d8",
            "primary": "#F59E0B", "primary_soft": "#FCD34D",
            "accent": "#FB7185",
            "warning": "#F97316", "danger": "#DC2626", "success": "#65A30D",
            "ink": "#2B1F16", "ink_muted": "#6B5A44", "light": "#ffffff",
        },
    },
    {
        "name": "松石蓝绿",
        "desc": "清新 / 教育 / 医疗，清爽明快",
        "colors": {
            "bg": "#12333B", "band": "#0C2830",
            "surface": "#f2f8f9", "border": "#dcebf0",
            "primary": "#0EA5E9", "primary_soft": "#7DD3FC",
            "accent": "#2DD4BF",
            "warning": "#FBBF24", "danger": "#F87171", "success": "#34D399",
            "ink": "#12333B", "ink_muted": "#4C6A75", "light": "#ffffff",
        },
    },
    {
        "name": "静谧绿",
        "desc": "环保 / 健康 / 自然，清新治愈",
        "colors": {
            "bg": "#14271E", "band": "#0F1E17",
            "surface": "#f4f8f5", "border": "#dfeae3",
            "primary": "#22C55E", "primary_soft": "#86EFAC",
            "accent": "#A3E635",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#14271E", "ink_muted": "#5f7668", "light": "#ffffff",
        },
    },
    {
        "name": "曜石黑金",
        "desc": "高端 / 发布会 / 奢华，低调质感",
        "colors": {
            "bg": "#161616", "band": "#0B0B0B",
            "surface": "#fafafa", "border": "#ececec",
            "primary": "#D4AF37", "primary_soft": "#F1D27A",
            "accent": "#9CA3AF",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#161616", "ink_muted": "#6b6b6b", "light": "#ffffff",
        },
    },
    {
        "name": "珊瑚粉",
        "desc": "女性 / 母婴 / 婚恋，柔美温暖",
        "colors": {
            "bg": "#33101F", "band": "#250A15",
            "surface": "#fdf6f8", "border": "#f6dfe7",
            "primary": "#F43F5E", "primary_soft": "#FDA4AF",
            "accent": "#FB7185",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#10B981",
            "ink": "#33101F", "ink_muted": "#8a6470", "light": "#ffffff",
        },
    },
    {
        "name": "电光紫",
        "desc": "科技 / AI / 未来，神秘炫酷",
        "colors": {
            "bg": "#170A2E", "band": "#10061F",
            "surface": "#faf6ff", "border": "#eaddf7",
            "primary": "#8B5CF6", "primary_soft": "#C4B5FD",
            "accent": "#22D3EE",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#34D399",
            "ink": "#170A2E", "ink_muted": "#6b5f8a", "light": "#ffffff",
        },
    },
    {
        "name": "极简黑白",
        "desc": "极简 / 杂志 / 高端，黑白克制",
        "colors": {
            "bg": "#111111", "band": "#0A0A0A",
            "surface": "#fafafa", "border": "#e5e5e5",
            "primary": "#52525B", "primary_soft": "#D4D4D8",
            "accent": "#A1A1AA",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#16A34A",
            "ink": "#111111", "ink_muted": "#6B7280", "light": "#ffffff",
        },
    },
    {
        "name": "国潮红",
        "desc": "节日 / 促销 / 国潮，喜庆热烈",
        "colors": {
            "bg": "#6B1414", "band": "#4A0D0D",
            "surface": "#fdf5f5", "border": "#f3d9d9",
            "primary": "#DC2626", "primary_soft": "#FCA5A5",
            "accent": "#FBBF24",
            "warning": "#F59E0B", "danger": "#B91C1C", "success": "#16A34A",
            "ink": "#6B1414", "ink_muted": "#8a5a5a", "light": "#ffffff",
        },
    },
    {
        "name": "莫兰迪",
        "desc": "文艺 / 柔和 / 治愈，低饱和高级灰",
        "colors": {
            "bg": "#3E3A36", "band": "#2E2B27",
            "surface": "#F4F1EC", "border": "#E5DED4",
            "primary": "#9C8A74", "primary_soft": "#CBBBA8",
            "accent": "#8E8AA0",
            "warning": "#C08552", "danger": "#B4685F", "success": "#7A9B76",
            "ink": "#3E3A36", "ink_muted": "#756D62", "light": "#F7F3EC",
        },
    },
    {
        "name": "薄荷绿",
        "desc": "健康 / 医疗 / 清新，清爽治愈",
        "colors": {
            "bg": "#0E2A22", "band": "#0A1F19",
            "surface": "#f1f9f5", "border": "#dcefe6",
            "primary": "#10B981", "primary_soft": "#6EE7B7",
            "accent": "#34D399",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#10B981",
            "ink": "#0E2A22", "ink_muted": "#4f7568", "light": "#ffffff",
        },
    },
    {
        "name": "咖啡棕",
        "desc": "咖啡 / 复古 / 商务，沉稳醇厚",
        "colors": {
            "bg": "#2B1D15", "band": "#1F140E",
            "surface": "#faf6f1", "border": "#ecdfd2",
            "primary": "#C2703D", "primary_soft": "#E3A87C",
            "accent": "#A1622B",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#4D7C0F",
            "ink": "#2B1D15", "ink_muted": "#6B5547", "light": "#ffffff",
        },
    },
    {
        "name": "香槟金",
        "desc": "婚庆 / 高端 / 轻奢，温柔华丽",
        "colors": {
            "bg": "#4A3823", "band": "#37291A",
            "surface": "#FBF7EF", "border": "#EEE3CE",
            "primary": "#C9A227", "primary_soft": "#E8D18A",
            "accent": "#B8912B",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#16A34A",
            "ink": "#4A3823", "ink_muted": "#6B5C42", "light": "#FFFDF5",
        },
    },
    {
        "name": "马卡龙",
        "desc": "甜点 / 可爱 / 儿童，粉彩甜美",
        "colors": {
            "bg": "#3D2B3A", "band": "#2D1F2B",
            "surface": "#fdf7f9", "border": "#f3e2e8",
            "primary": "#F472B6", "primary_soft": "#F9A8D4",
            "accent": "#A78BFA",
            "warning": "#FBBF24", "danger": "#FB7185", "success": "#34D399",
            "ink": "#3D2B3A", "ink_muted": "#6B4E60", "light": "#ffffff",
        },
    },
    {
        "name": "复古橄榄",
        "desc": "复古 / 军工 / 户外，怀旧质感",
        "colors": {
            "bg": "#2A2A1A", "band": "#1E1E12",
            "surface": "#f7f6ef", "border": "#e6e2d2",
            "primary": "#B9A61A", "primary_soft": "#E3D47A",
            "accent": "#6B8E23",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#4D7C0F",
            "ink": "#2A2A1A", "ink_muted": "#5E5C45", "light": "#ffffff",
        },
    },
    {
        "name": "春日樱",
        "desc": "春日 / 少女 / 浪漫，樱花粉嫩",
        "colors": {
            "bg": "#3A1A2E", "band": "#2B1222",
            "surface": "#fdf6f8", "border": "#f3e0e6",
            "primary": "#EC4899", "primary_soft": "#F9A8D4",
            "accent": "#F472B6",
            "warning": "#F59E0B", "danger": "#E11D48", "success": "#10B981",
            "ink": "#3A1A2E", "ink_muted": "#8a6070", "light": "#ffffff",
        },
    },
    {
        "name": "夏日海",
        "desc": "夏日 / 海洋 / 清凉，清爽水感",
        "colors": {
            "bg": "#0A3D4B", "band": "#072E39",
            "surface": "#f2fafb", "border": "#d8eef1",
            "primary": "#06B6D4", "primary_soft": "#67E8F9",
            "accent": "#0EA5E9",
            "warning": "#FBBF24", "danger": "#F43F5E", "success": "#10B981",
            "ink": "#0A3D4B", "ink_muted": "#4f7580", "light": "#ffffff",
        },
    },
    {
        "name": "秋日枫",
        "desc": "秋日 / 丰收 / 温暖，枫叶暖橙",
        "colors": {
            "bg": "#3B2013", "band": "#2C170D",
            "surface": "#fbf5ef", "border": "#f0dfce",
            "primary": "#EA580C", "primary_soft": "#FDBA74",
            "accent": "#C2410C",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#65A30D",
            "ink": "#3B2013", "ink_muted": "#85624a", "light": "#ffffff",
        },
    },
    {
        "name": "冬日雪",
        "desc": "冬日 / 冰雪 / 纯净，冰蓝通透",
        "colors": {
            "bg": "#0F2E45", "band": "#0A2234",
            "surface": "#f4f9fc", "border": "#ddeaf2",
            "primary": "#38BDF8", "primary_soft": "#BAE6FD",
            "accent": "#7DD3FC",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#0F2E45", "ink_muted": "#54778c", "light": "#ffffff",
        },
    },
    {
        "name": "圣诞",
        "desc": "圣诞 / 节日 / 温暖，红绿金",
        "colors": {
            "bg": "#0E2E1F", "band": "#0A2217",
            "surface": "#f7faf6", "border": "#e2ece0",
            "primary": "#16A34A", "primary_soft": "#86EFAC",
            "accent": "#DC2626",
            "warning": "#F59E0B", "danger": "#B91C1C", "success": "#16A34A",
            "ink": "#0E2E1F", "ink_muted": "#56704a", "light": "#ffffff",
        },
    },
    {
        "name": "万圣节",
        "desc": "万圣 / 鬼怪 / 派对，橙紫黑",
        "colors": {
            "bg": "#1A0B14", "band": "#120710",
            "surface": "#faf5f8", "border": "#ecdde6",
            "primary": "#F97316", "primary_soft": "#FDBA74",
            "accent": "#A855F7",
            "warning": "#FBBF24", "danger": "#DC2626", "success": "#22C55E",
            "ink": "#1A0B14", "ink_muted": "#7a5a6a", "light": "#ffffff",
        },
    },
    {
        "name": "春节",
        "desc": "春节 / 新年 / 喜庆，中国红金",
        "colors": {
            "bg": "#991B1B", "band": "#7F1D1D",
            "surface": "#fef5f5", "border": "#f6dcdc",
            "primary": "#DC2626", "primary_soft": "#FECACA",
            "accent": "#FACC15",
            "warning": "#F59E0B", "danger": "#B91C1C", "success": "#16A34A",
            "ink": "#991B1B", "ink_muted": "#8a5a5a", "light": "#ffffff",
        },
    },
    {
        "name": "靛蓝",
        "desc": "金融 / 法律 / 权威，沉稳权威",
        "colors": {
            "bg": "#1E1B4B", "band": "#141139",
            "surface": "#f5f5fc", "border": "#e0e0f0",
            "primary": "#4F46E5", "primary_soft": "#A5B4FC",
            "accent": "#6366F1",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#1E1B4B", "ink_muted": "#5b5b7a", "light": "#ffffff",
        },
    },
    {
        "name": "天空蓝",
        "desc": "亲子 / 教育 / 医疗，明朗亲和",
        "colors": {
            "bg": "#0C4A6E", "band": "#093851",
            "surface": "#f2f8fc", "border": "#dcebf5",
            "primary": "#0284C7", "primary_soft": "#7DD3FC",
            "accent": "#38BDF8",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#0C4A6E", "ink_muted": "#54748a", "light": "#ffffff",
        },
    },
    {
        "name": "酒红",
        "desc": "红酒 / 复古 / 奢华，醇厚质感",
        "colors": {
            "bg": "#3D0F1E", "band": "#2B0A14",
            "surface": "#fbf5f6", "border": "#efdde0",
            "primary": "#9F1239", "primary_soft": "#FDA4AF",
            "accent": "#C0A062",
            "warning": "#F59E0B", "danger": "#BE123C", "success": "#16A34A",
            "ink": "#3D0F1E", "ink_muted": "#8a5560", "light": "#ffffff",
        },
    },
    {
        "name": "鼠尾草",
        "desc": "极简 / 家居 / 北欧，灰绿清新",
        "colors": {
            "bg": "#2F3A30", "band": "#232B24",
            "surface": "#f4f6f2", "border": "#e2e8de",
            "primary": "#7C8B6F", "primary_soft": "#B7C4A8",
            "accent": "#9CAF88",
            "warning": "#D0956B", "danger": "#C06B6B", "success": "#6B8E5A",
            "ink": "#2F3A30", "ink_muted": "#5A6454", "light": "#f4f6f2",
        },
    },
    {
        "name": "霓虹赛博",
        "desc": "赛博朋克 / 游戏 / 电音，霓虹炫酷",
        "colors": {
            "bg": "#0D0A14", "band": "#080611",
            "surface": "#f5f4fa", "border": "#e4e1f0",
            "primary": "#D946EF", "primary_soft": "#F0ABFC",
            "accent": "#22D3EE",
            "warning": "#FBBF24", "danger": "#F43F5E", "success": "#34D399",
            "ink": "#0D0A14", "ink_muted": "#6b6580", "light": "#ffffff",
        },
    },
    {
        "name": "房地产",
        "desc": "房产 / 家居 / 建筑，沉稳大气",
        "colors": {
            "bg": "#241F1A", "band": "#1A1612",
            "surface": "#f7f5f1", "border": "#e8e3da",
            "primary": "#8A6D3B", "primary_soft": "#C9B188",
            "accent": "#5B6B7A",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#4D7C0F",
            "ink": "#241F1A", "ink_muted": "#6e675d", "light": "#ffffff",
        },
    },
    {
        "name": "餐饮美食",
        "desc": "餐饮 / 美食 / 食欲，暖红诱人",
        "colors": {
            "bg": "#3B1212", "band": "#2B0D0D",
            "surface": "#fdf6f4", "border": "#f3deda",
            "primary": "#E0522D", "primary_soft": "#F7B7A0",
            "accent": "#F59E0B",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#65A30D",
            "ink": "#3B1212", "ink_muted": "#8a5f57", "light": "#ffffff",
        },
    },
    {
        "name": "运动健身",
        "desc": "运动 / 健身 / 活力，动感橙蓝",
        "colors": {
            "bg": "#1E2A3A", "band": "#15202D",
            "surface": "#f4f8fa", "border": "#dde8ee",
            "primary": "#F97316", "primary_soft": "#FDBA74",
            "accent": "#0EA5E9",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#1E2A3A", "ink_muted": "#5b6b7a", "light": "#ffffff",
        },
    },
    {
        "name": "母婴",
        "desc": "母婴 / 亲子 / 温柔，软萌粉黄",
        "colors": {
            "bg": "#3A2230", "band": "#2B1823",
            "surface": "#fdf8fa", "border": "#f5e4ea",
            "primary": "#EC4899", "primary_soft": "#FBCFE8",
            "accent": "#FCD34D",
            "warning": "#F59E0B", "danger": "#FB7185", "success": "#34D399",
            "ink": "#3A2230", "ink_muted": "#8a6a7a", "light": "#ffffff",
        },
    },
    {
        "name": "宠物",
        "desc": "宠物 / 萌宠 / 温暖，暖棕姜黄",
        "colors": {
            "bg": "#3B2A18", "band": "#2C1E10",
            "surface": "#faf6ef", "border": "#efdfc8",
            "primary": "#D97706", "primary_soft": "#FCD34D",
            "accent": "#92400E",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#65A30D",
            "ink": "#3B2A18", "ink_muted": "#6B5740", "light": "#ffffff",
        },
    },
    {
        "name": "金融科技",
        "desc": "金融 / 科技 / 信赖，深蓝青",
        "colors": {
            "bg": "#0B1F33", "band": "#081624",
            "surface": "#f3f8fb", "border": "#ddeaf2",
            "primary": "#0EA5E9", "primary_soft": "#7DD3FC",
            "accent": "#14B8A6",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#10B981",
            "ink": "#0B1F33", "ink_muted": "#547088", "light": "#ffffff",
        },
    },
    {
        "name": "教育",
        "desc": "教育 / 培训 / 成长，明快蓝黄",
        "colors": {
            "bg": "#16324A", "band": "#10263A",
            "surface": "#f5fafc", "border": "#ddecf4",
            "primary": "#2563EB", "primary_soft": "#93C5FD",
            "accent": "#F59E0B",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#16324A", "ink_muted": "#5b738c", "light": "#ffffff",
        },
    },
    {
        "name": "娱乐影视",
        "desc": "娱乐 / 影视 / 星光，绚紫金",
        "colors": {
            "bg": "#1A0B2E", "band": "#12071F",
            "surface": "#faf6ff", "border": "#eaddf7",
            "primary": "#D946EF", "primary_soft": "#F0ABFC",
            "accent": "#C9A227",
            "warning": "#F59E0B", "danger": "#F43F5E", "success": "#34D399",
            "ink": "#1A0B2E", "ink_muted": "#6b5f8a", "light": "#ffffff",
        },
    },
    {
        "name": "汽车",
        "desc": "汽车 / 工业 / 硬朗，石墨银蓝",
        "colors": {
            "bg": "#1A1F24", "band": "#12161A",
            "surface": "#f5f6f7", "border": "#e2e5e8",
            "primary": "#3B82F6", "primary_soft": "#93C5FD",
            "accent": "#94A3B8",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#1A1F24", "ink_muted": "#6b7278", "light": "#ffffff",
        },
    },
    {
        "name": "暮色紫",
        "desc": "黄昏 / 氛围 / 情绪，紫橙暮色",
        "colors": {
            "bg": "#1B1433", "band": "#120D24",
            "surface": "#f6f4fb", "border": "#e6e0f2",
            "primary": "#8B5CF6", "primary_soft": "#C4B5FD",
            "accent": "#FB923C",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#10B981",
            "ink": "#1B1433", "ink_muted": "#6b5f86", "light": "#ffffff",
        },
    },
    {
        "name": "海洋珊瑚",
        "desc": "海岛 / 度假 / 热带，青蓝珊瑚",
        "colors": {
            "bg": "#0A3A43", "band": "#072B32",
            "surface": "#f2fafb", "border": "#d8eef1",
            "primary": "#06B6D4", "primary_soft": "#67E8F9",
            "accent": "#FB7185",
            "warning": "#F59E0B", "danger": "#F43F5E", "success": "#10B981",
            "ink": "#0A3A43", "ink_muted": "#4f7880", "light": "#ffffff",
        },
    },
    {
        "name": "石墨银",
        "desc": "硬件 / 科技 / 极客，石墨电蓝",
        "colors": {
            "bg": "#17191C", "band": "#101214",
            "surface": "#f5f5f6", "border": "#e3e4e6",
            "primary": "#60A5FA", "primary_soft": "#BFDBFE",
            "accent": "#94A3B8",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#17191C", "ink_muted": "#6b7076", "light": "#ffffff",
        },
    },
    {
        "name": "和风",
        "desc": "日式 / 侘寂 / 极简，米白靛蓝",
        "colors": {
            "bg": "#26333F", "band": "#1A2630",
            "surface": "#f7f5f0", "border": "#e8e2d8",
            "primary": "#4A6B8A", "primary_soft": "#A3B8CC",
            "accent": "#C73E3A",
            "warning": "#D97706", "danger": "#C73E3A", "success": "#6B8E5A",
            "ink": "#26333F", "ink_muted": "#55606b", "light": "#f7f5f0",
        },
    },
    {
        "name": "港风",
        "desc": "港风 / 复古 / 霓虹，红绿霓虹",
        "colors": {
            "bg": "#2A0E12", "band": "#1F0A0D",
            "surface": "#faf5f4", "border": "#eddddc",
            "primary": "#E53935", "primary_soft": "#F5A3A0",
            "accent": "#39D98A",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#22C55E",
            "ink": "#2A0E12", "ink_muted": "#8a5f5e", "light": "#ffffff",
        },
    },
    {
        "name": "北欧",
        "desc": "北欧 / 极简 / 家居，原木白灰",
        "colors": {
            "bg": "#2E2E2C", "band": "#222220",
            "surface": "#faf9f7", "border": "#eae7e2",
            "primary": "#8B7355", "primary_soft": "#C0AC8C",
            "accent": "#5B7A9D",
            "warning": "#D9A05B", "danger": "#C06B6B", "success": "#7A9B76",
            "ink": "#2E2E2C", "ink_muted": "#6e6b66", "light": "#faf9f7",
        },
    },
    {
        "name": "新中式",
        "desc": "新中式 / 东方 / 雅致，黛青朱砂",
        "colors": {
            "bg": "#1F2E2B", "band": "#16211F",
            "surface": "#f6f5f1", "border": "#e6e1d8",
            "primary": "#B03A2E", "primary_soft": "#D98E84",
            "accent": "#C9A227",
            "warning": "#D97706", "danger": "#B03A2E", "success": "#6B8E5A",
            "ink": "#1F2E2B", "ink_muted": "#55605c", "light": "#f6f5f1",
        },
    },
    {
        "name": "敦煌",
        "desc": "敦煌 / 西域 / 壁画，土红石青",
        "colors": {
            "bg": "#4A2018", "band": "#361710",
            "surface": "#faf4ef", "border": "#eedfd4",
            "primary": "#C4703A", "primary_soft": "#E0A879",
            "accent": "#2E8B7A",
            "warning": "#D97706", "danger": "#B03A2E", "success": "#6B8E5A",
            "ink": "#4A2018", "ink_muted": "#6B5044", "light": "#ffffff",
        },
    },
    {
        "name": "双十一",
        "desc": "电商 / 促销 / 狂欢，红橙金",
        "colors": {
            "bg": "#A01818", "band": "#7A1111",
            "surface": "#fdf5f4", "border": "#f6dcdc",
            "primary": "#F97316", "primary_soft": "#FDBA74",
            "accent": "#FACC15",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#16A34A",
            "ink": "#A01818", "ink_muted": "#8a5a5a", "light": "#ffffff",
        },
    },
    {
        "name": "世界杯",
        "desc": "足球 / 体育 / 激情，绿茵金黄",
        "colors": {
            "bg": "#0E3B2E", "band": "#0A2B22",
            "surface": "#f4f9f5", "border": "#dcefe2",
            "primary": "#16A34A", "primary_soft": "#86EFAC",
            "accent": "#FACC15",
            "warning": "#F59E0B", "danger": "#DC2626", "success": "#16A34A",
            "ink": "#0E3B2E", "ink_muted": "#56704a", "light": "#ffffff",
        },
    },
    {
        "name": "音乐节",
        "desc": "音乐节 / 演出 / 狂欢，紫粉明黄",
        "colors": {
            "bg": "#2A1030", "band": "#1E0B23",
            "surface": "#faf6fd", "border": "#ecdcf5",
            "primary": "#EC4899", "primary_soft": "#F9A8D4",
            "accent": "#FACC15",
            "warning": "#FBBF24", "danger": "#F43F5E", "success": "#34D399",
            "ink": "#2A1030", "ink_muted": "#7a5f86", "light": "#ffffff",
        },
    },
    {
        "name": "复古波普",
        "desc": "波普 / 撞色 / 潮流，高饱和",
        "colors": {
            "bg": "#1A1A2E", "band": "#12121F",
            "surface": "#fafafc", "border": "#e8e8f0",
            "primary": "#FF3B5C", "primary_soft": "#FF8FA3",
            "accent": "#FFD23F",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#1A1A2E", "ink_muted": "#6b6b80", "light": "#ffffff",
        },
    },
    {
        "name": "极光",
        "desc": "极光 / 自然 / 梦幻，绿紫极光",
        "colors": {
            "bg": "#0B1D33", "band": "#071525",
            "surface": "#f2f7fb", "border": "#dceaf2",
            "primary": "#34D399", "primary_soft": "#6EE7B7",
            "accent": "#A78BFA",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#34D399",
            "ink": "#0B1D33", "ink_muted": "#547088", "light": "#ffffff",
        },
    },
    {
        "name": "太空",
        "desc": "太空 / 航天 / 深空，星蓝科幻",
        "colors": {
            "bg": "#0A0A14", "band": "#06060D",
            "surface": "#f5f5fa", "border": "#e4e4f0",
            "primary": "#6366F1", "primary_soft": "#A5B4FC",
            "accent": "#38BDF8",
            "warning": "#F59E0B", "danger": "#EF4444", "success": "#22C55E",
            "ink": "#0A0A14", "ink_muted": "#6b6b80", "light": "#ffffff",
        },
    },
    {
        "name": "宋韵",
        "desc": "宋式 / 留白 / 雅致，青灰朱红",
        "colors": {
            "bg": "#2A2E33", "band": "#1F2328",
            "surface": "#f7f6f3", "border": "#e6e3dd",
            "primary": "#6B7280", "primary_soft": "#A9B0B8",
            "accent": "#B04A3A",
            "warning": "#D97706", "danger": "#B04A3A", "success": "#6B8E5A",
            "ink": "#2A2E33", "ink_muted": "#595D63", "light": "#f7f6f3",
        },
    },
]

# ======================================================================
# 逻辑
# ======================================================================

import argparse
import math
import os
import shutil
import subprocess
import sys

from contrast import contrast_ratio, luminance


def norm_hex(c):
    c = c.strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return "#" + c.lower()


def find_palette(name):
    name = name.strip()
    for p in PALETTES:
        if p["name"] == name or p["name"].lower() == name.lower():
            return p
    return None


# 需要校验的「文字色 → 背景色」关键组合
CONTRAST_PAIRS = [
    ("light", "bg", 4.5, "深底主文字"),
    ("light", "band", 4.5, "底部结论条文字"),
    ("primary_soft", "bg", 4.5, "深底点缀 / 次级文字"),
    ("ink", "surface", 4.5, "浅底主文字"),
    ("ink_muted", "surface", 4.5, "浅底次级文字"),
    ("ink", "primary_soft", 4.5, "浅色徽章上的深字"),
]


def palette_checks(p):
    rows = []
    for (fgk, bgk, need, label) in CONTRAST_PAIRS:
        fg = p["colors"][fgk]
        bg = p["colors"][bgk]
        ratio = contrast_ratio(fg, bg)
        rows.append((label, fgk, bgk, fg, bg, ratio, need, ratio >= need))
    return rows


def cmd_list(args):
    print(f"共 {len(PALETTES)} 张配色卡（系列配色：同一系列固定一张卡，只变文案/图形）\n")
    for i, p in enumerate(PALETTES, 1):
        c = p["colors"]
        print(f"{i:>2}. {p['name']} —— {p['desc']}")
        print(f"     深底 bg={norm_hex(c['bg'])}  band={norm_hex(c['band'])}  "
              f"primary={norm_hex(c['primary'])}  light={norm_hex(c['light'])}")
        print(f"     浅底 surface={norm_hex(c['surface'])}  ink={norm_hex(c['ink'])}  "
              f"accent={norm_hex(c['accent'])}")
    print("\n用 `palette.py show <名称>` 看详情，`palette.py card <名称>` 生成配色卡图。")


def cmd_show(args):
    p = find_palette(args.name)
    if not p:
        sys.exit(f"未找到配色卡「{args.name}」，用 `palette.py list` 查看可用名称")
    print(f"# {p['name']} —— {p['desc']}\n")
    print(f"{'角色':<14}{'hex':<10}{'用途'}")
    print("-" * 44)
    for key, desc in ROLES:
        print(f"{key:<14}{norm_hex(p['colors'][key]):<10}{desc}")
    print("\n[关键对比度]")
    ok_all = True
    for (label, fgk, bgk, fg, bg, ratio, need, ok) in palette_checks(p):
        tag = "✅" if ok else "❌"
        if not ok:
            ok_all = False
        print(f"  {tag} {label:<12} {norm_hex(fg)} on {norm_hex(bg)} = {ratio:.2f}:1 (需≥{need:g})")
    print("\n" + ("✅ 全部达标，可直接用于系列。" if ok_all else "❌ 存在不达标组合，慎用该角色搭配。"))


def cmd_check(args):
    targets = [p for p in PALETTES] if not args.name else [find_palette(args.name)]
    if args.name and targets[0] is None:
        sys.exit(f"未找到配色卡「{args.name}」")
    all_ok = True
    for p in targets:
        print(f"# {p['name']}")
        for (label, fgk, bgk, fg, bg, ratio, need, ok) in palette_checks(p):
            if not ok:
                all_ok = False
                print(f"  ❌ {label:<12} {norm_hex(fg)} on {norm_hex(bg)} = {ratio:.2f}:1 < {need:g}")
        print("  ✅ 全部达标" if all(ok for _, _, _, _, _, _, _, ok in palette_checks(p)) else "")
    print("\n结论：" + ("✅ 所有卡达标" if all_ok else "❌ 存在不达标组合"))
    sys.exit(0 if all_ok else 1)


# 配色卡里含中文（卡名/角色说明），font-family 需含中文字体；用 --font 覆盖为 fc-match 验证过的字体
# 注意：这是写进 SVG `font-family="..."` 属性里的形式，字体名之间用逗号分隔、不带引号；
# 若写进 <style> CSS 里，可为带空格的字体名加引号（见 templates/*.svg）。
DEFAULT_FONT = 'Source Han Sans SC, Noto Sans CJK SC, LXGW WenKai, Smiley Sans, sans-serif'


# 配色卡上更紧凑的角色标签（完整说明见 ROLES / `palette.py roles`）
CARD_LABELS = {
    "bg": "深色主背景", "band": "深色次级背景", "surface": "浅色卡片背景",
    "border": "浅色卡片边框", "primary": "主强调色", "primary_soft": "主强调亮色",
    "accent": "第二强调 / 图标", "warning": "警告 / 对比橙", "danger": "对比红",
    "success": "成功绿", "ink": "主文字（浅底）", "ink_muted": "次级文字灰",
    "light": "深底文字（近白）",
}


def best_text(color):
    cb = contrast_ratio(color, "#000000")
    cw = contrast_ratio(color, "#ffffff")
    return "#ffffff" if cw >= cb else "#000000"


def palette_card_svg(p, font=DEFAULT_FONT):
    cols = 3
    margin = 40
    gap = 16
    sw = (900 - 2 * margin - (cols - 1) * gap) / cols
    sh = 100
    header_h = 150
    rows = math.ceil(len(ROLES) / cols)
    H = header_h + rows * sh + (rows - 1) * gap + margin

    c = p["colors"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{int(H)}" viewBox="0 0 900 {int(H)}">',
        f'<rect width="900" height="{int(H)}" fill="{norm_hex(c["bg"])}"/>',
        f'<text x="40" y="70" font-family="{font}" font-size="44" font-weight="bold" fill="{norm_hex(c["light"])}">{p["name"]}</text>',
        f'<text x="40" y="110" font-family="{font}" font-size="22" fill="{norm_hex(c["primary_soft"])}">{p["desc"]}</text>',
    ]

    for idx, (key, _desc) in enumerate(ROLES):
        r = idx // cols
        col = idx % cols
        x = margin + col * (sw + gap)
        y = header_h + r * (sh + gap)
        color = norm_hex(c[key])
        txt = best_text(color)
        label = CARD_LABELS.get(key, key)
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{sw:.1f}" height="{sh:.1f}" rx="10" fill="{color}"/>')
        parts.append(f'<text x="{x + 14:.1f}" y="{y + 34:.1f}" font-family="{font}" font-size="20" font-weight="bold" fill="{txt}">{key}</text>')
        parts.append(f'<text x="{x + 14:.1f}" y="{y + 60:.1f}" font-family="{font}" font-size="18" fill="{txt}">{color}</text>')
        parts.append(f'<text x="{x + 14:.1f}" y="{y + 84:.1f}" font-family="{font}" font-size="13" fill="{txt}" opacity="0.85">{label}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def cmd_card(args):
    p = find_palette(args.name)
    if not p:
        sys.exit(f"未找到配色卡「{args.name}」，用 `palette.py list` 查看可用名称")
    out = args.out or f"palette-{p['name']}.svg"
    svg = palette_card_svg(p, args.font)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"已生成配色卡: {out}")
    if args.render:
        if shutil.which("rsvg-convert"):
            png = os.path.splitext(out)[0] + ".png"
            subprocess.run(["rsvg-convert", "-w", "900", out, "-o", png], check=True)
            print(f"已导出 PNG: {png}")
        else:
            print("未找到 rsvg-convert，跳过 PNG 导出（可手动 rsvg-convert -w 900 <svg> -o <png>）")


def cmd_roles(args):
    print(f"{'角色':<14}{'用途'}")
    print("-" * 44)
    for key, desc in ROLES:
        print(f"{key:<14}{desc}")


def main():
    ap = argparse.ArgumentParser(description="专业配色卡库 + 系列配色工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp_list = sub.add_parser("list", help="列出全部配色卡")
    sp_list.set_defaults(func=cmd_list)

    sp_show = sub.add_parser("show", help="查看单张配色卡")
    sp_show.add_argument("name", help="配色卡名称")
    sp_show.set_defaults(func=cmd_show)

    sp_check = sub.add_parser("check", help="对比度校验")
    sp_check.add_argument("name", nargs="?", help="配色卡名称（缺省校验全部）")
    sp_check.set_defaults(func=cmd_check)

    sp_card = sub.add_parser("card", help="生成配色卡 SVG/PNG")
    sp_card.add_argument("name", help="配色卡名称")
    sp_card.add_argument("--out", help="输出 SVG 路径")
    sp_card.add_argument("--font", default=DEFAULT_FONT, help="font-family（含中文字体；用 fc-match 验证过的覆盖）")
    sp_card.add_argument("--render", action="store_true", help="顺带导出 PNG（需 rsvg-convert）")
    sp_card.set_defaults(func=cmd_card)

    sp_roles = sub.add_parser("roles", help="打印角色说明")
    sp_roles.set_defaults(func=cmd_roles)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
