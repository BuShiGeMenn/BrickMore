# -*- coding: utf-8 -*-
"""按 48³ 训练集真实模板生成 tower/train/vessel 12 组 × 10 条提示词"""
import json
from pathlib import Path

GEOM_EN = [
 "Curved substantial surfaces carry their continuously attached functional parts.",
 "The curved substantial surfaces carry their functional parts continuously attached.",
 "Curved substantial surfaces hold their functional parts in continuous attachment.",
 "Its curved substantial surfaces carry functional parts attached continuously.",
 "Functional parts stay continuously attached to the curved substantial surfaces.",
 "The curved substantial surfaces keep their functional parts continuously attached.",
 "Curved substantial surfaces carry their attached functional parts without interruption.",
 "Continuously attached functional parts ride on the curved substantial surfaces.",
 "The curved, substantial surfaces carry the functional parts in one continuous attachment.",
 "All functional parts remain continuously attached to the curved substantial surfaces.",
]
GEOM_ZH = [
 "弧形的大面积表面连续承载其附属的功能部件。",
 "弧形的实体表面使其功能部件连续附着。",
 "弧形实体表面把功能部件连续地附着其上。",
 "其弧形实体表面承载着连续附着的功能部件。",
 "功能部件连续附着于弧形的实体表面。",
 "弧形实体表面保持其功能部件的连续附着。",
 "弧形实体表面不间断地承载附属功能部件。",
 "连续附着的功能部件位于弧形实体表面上。",
 "弧形的大表面以一体连续的方式承载功能部件。",
 "所有功能部件都连续附着在弧形实体表面上。",
]

def prop_en(w, h): return f"Overall width is {w:.2f} times depth; height is {h:.2f} times width. Parts follow functional positions."
def prop_zh(w, h): return f"总宽是深度的 {w:.2f} 倍;高度是宽度的 {h:.2f} 倍。各部件按功能位置排布。"
def color_en(colors): return f"Continuous {colors} color regions distinguish the body and attachments. The front reveals functional parts; side and top views reveal depth, connections and layout."
def color_zh(colors_zh): return f"连续的 {colors_zh} 色块区分主体与附件。正面显示功能部件;侧面与顶面显示深度、连接与布局。"

# ---------- TOWER ----------
TOWER_BASE_EN = [
 "A round tower with upright body, lower entrance and curved crown.",
 "A round tower whose upright body carries a curved crown above a lower entrance.",
 "A round tower with a straight upright body, a curved crown and a lower entrance at the front.",
 "A round tower formed by an upright body rising from the ground to a curved crown, with a lower entrance.",
 "A round tower with an upright body, a curved crown on top and an entrance at the lower front.",
 "A round tower of upright body and curved crown, with a lower entrance opening at its front.",
 "A round tower with a tall upright body, a curved crown and a lower front entrance.",
 "A round tower built from an upright body with a curved crown and a lower entrance.",
 "A round tower with an upright, evenly rising body, a curved crown and one lower entrance.",
 "A round tower with upright body and curved crown; a lower entrance sits at the front.",
]
TOWER_BASE_ZH = [
 "一座圆塔,塔身直立,下部有入口,塔冠呈弧形。",
 "一座圆塔,直立的塔身上托着弧形塔冠,下部开有入口。",
 "一座圆塔,塔身笔直向上,塔冠呈弧线,正面下部有一个入口。",
 "一座圆塔,由直立塔身从地面升至弧形塔冠,并有一个下部入口。",
 "一座圆塔,塔身直立,顶部为弧形塔冠,下前方有入口。",
 "一座圆塔,直立塔身与弧形塔冠,正面下部开口通入内部。",
 "一座圆塔,塔身修长直立,塔冠弧形,正下方有入口。",
 "一座圆塔,由直立塔身、弧形塔冠和下部入口构成。",
 "一座圆塔,塔身均匀直立上升,塔冠呈弧,下部只有一处入口。",
 "一座圆塔,直立塔身托弧形塔冠;正面下部设入口。",
]
TOWER_STRUCT_EN = [
 "Continuous walls rise from the base to the crown; a lower front entrance opens inside.",
 "Continuous walls rise from the base to the crown, and the lower front entrance opens into the inside.",
 "The wall runs continuously from base to crown; a lower front entrance opens inside.",
 "Unbroken walls rise from base to crown, with the lower front entrance opening inward.",
 "Continuous walls span the full height from base to crown; the lower front entrance opens to the interior.",
 "Walls rise continuously from the base to the crown; at the lower front, an entrance opens inside.",
 "From the base up to the crown the walls continue unbroken; the lower front entrance opens inside.",
 "The tower's walls rise continuously from base to crown; the lower front entrance leads inside.",
 "Continuous walls climb from the base to the crown; a lower front entrance opens into the interior.",
 "Walls stay continuous between base and crown; the lower front entrance opens inside.",
]
TOWER_STRUCT_ZH = [
 "连续的墙体从底部一直升到塔冠;正下方的入口通入内部。",
 "连续墙体从底部升至塔冠,正下方的入口向内开启。",
 "墙体从底到冠连续不断;正下方的入口通入内部。",
 "不间断的墙体由底升至冠,下部正面的入口向内开。",
 "连续墙体贯穿从底到冠的整个高度;正下方的入口通向内部。",
 "墙体由底至冠连续上升;在下部正面,一处入口向内开启。",
 "从底部到塔冠墙体连续不断;正下方的入口向内开。",
 "塔的墙体由底至冠连续升起;正下方的入口通入内部。",
 "连续墙体从底向上攀升到塔冠;正下方的入口向内开。",
 "墙体在底与冠之间保持连续;正下方的入口向内开。",
]
TOWER_RATIOS = [(0.60,2.11),(0.65,2.30),(0.70,2.50),(0.75,2.80),(0.82,3.00),
                (0.90,2.60),(1.00,2.20),(1.10,2.40),(1.22,2.27),(0.68,3.60)]

# ---------- TRAIN ----------
TRAIN_BASE_EN = [
 "A curved roof train with driving area, side windows and attached wheel groups.",
 "A train with a curved roof, a driving area, side windows and wheel groups attached to the body.",
 "A curved-roof train carrying a driving area, side windows and attached wheel groups.",
 "A train whose curved roof shelters a driving area, with side windows and attached wheel groups.",
 "A curved roof train featuring a driving area, windows along both sides and attached wheel groups.",
 "A train with a curved roof over the driving area, side windows and wheel groups attached underneath.",
 "A curved roof train with a driving area, side windows, and wheel groups attached on the sides.",
 "A train built with a curved roof, driving area, side windows and attached wheel groups.",
 "A curved roof train with windows on the sides, a driving area and attached wheel groups.",
 "A train with a curved roof and driving area, side windows, plus attached wheel groups.",
]
TRAIN_BASE_ZH = [
 "一列弧顶火车,有驾驶区、侧窗和附着的轮组。",
 "一列火车,弧形车顶,带驾驶区、侧窗以及附着在车身上的轮组。",
 "一列弧顶火车,载有驾驶区、侧窗和附着的轮组。",
 "一列火车,弧形车顶覆盖驾驶区,两侧有车窗,轮组附着于车身。",
 "一列弧顶火车,设有驾驶区、两侧车窗和附着的轮组。",
 "一列火车,驾驶区上方为弧形车顶,两侧开窗,下方附着轮组。",
 "一列弧顶火车,带驾驶区、侧窗,轮组附着于两侧。",
 "一列火车,弧形车顶、驾驶区、侧窗与附着的轮组。",
 "一列弧顶火车,侧面有车窗,前部为驾驶区,轮组附着。",
 "一列火车,弧顶与驾驶区,侧窗,外加附着的轮组。",
]
TRAIN_STRUCT = [
 ("An elongated body supports the curved roof cabin; rail wheel groups attach on both sides by shared faces. It has {n} wheels. End couplers attach to the underframe.",
  "细长车身承托弧顶驾驶舱;轨道轮组通过共享面附着在两侧。共有 {n} 个轮子。端部车钩连接到底架。"),
 ("An elongated body carries the curved roof cabin; rail wheel groups attach on both sides through shared faces. It has {n} wheels. End couplers attach to the underframe.",
  "细长的车身承载弧顶驾驶舱;轨道轮组以共享面附着于两侧。共有 {n} 个轮子。端部车钩连接到底架。"),
 ("The stretched body supports the curved roof cabin; rail wheel groups attach to both sides by shared faces. It has {n} wheels. End couplers are fixed to the underframe.",
  "修长车身托起弧顶驾驶舱;轨道轮组借共享面连在两侧。全车 {n} 个轮子。两端车钩接到底架。"),
 ("An elongated body holds up the curved roof cabin; rail wheel groups attach on both sides by shared faces. It has {n} wheels; end couplers connect to the underframe.",
  "拉长的车身承托弧顶驾驶舱;轨道轮组以共享面安装在两侧。共有 {n} 个轮子;端部车钩连接底架。"),
 ("The elongated body supports the curved roof cabin; rail wheel groups attach on both sides of the body by shared faces. It has {n} wheels, and end couplers attach to the underframe.",
  "细长的车身托着弧顶驾驶舱;轨道轮组通过共享面附着在车身两侧。共有 {n} 个轮子,端部车钩接于底架。"),
]
TRAIN_WHEELS = [(0,4),(1,6),(2,4),(3,6),(4,4),(0,6),(1,4),(2,6),(3,4),(4,6)]
TRAIN_RATIOS = [(0.29,0.73),(0.33,0.82),(0.36,0.89),(0.41,0.95),(0.44,1.00),
                (0.31,0.78),(0.38,0.85),(0.42,0.92),(0.35,0.88),(0.40,0.97)]

# ---------- VESSEL ----------
VESSEL_BASE_EN = [
 "A rounded monohull boat with bow, stern, deck and interior opening.",
 "A rounded monohull boat showing bow, stern, a deck and an interior opening.",
 "A boat with a rounded monohull, bow and stern, a deck and an opening inside.",
 "A rounded monohull boat whose deck surrounds an interior opening between bow and stern.",
 "A rounded monohull boat with a bow, a stern, a connected deck and an interior opening.",
 "A rounded monohull boat carrying a deck with an interior opening, bow and stern.",
 "A rounded monohull boat with bow and stern, deck surface and interior opening.",
 "A rounded monohull boat; its bow and stern frame a deck with an interior opening.",
 "A rounded monohull boat with a bow, stern, flat deck and an interior opening.",
 "A rounded monohull boat with bow, stern, deck and open interior.",
]
VESSEL_BASE_ZH = [
 "一艘圆润的单体船,有船头、船尾、甲板和内部开口。",
 "一艘圆润单体船,可见船头、船尾、甲板与内部开口。",
 "一艘圆润单体船,船头船尾,甲板上有一处内部开口。",
 "一艘圆润单体船,甲板在船头与船尾之间围出内部开口。",
 "一艘圆润单体船,带船头、船尾、连通的甲板和内部开口。",
 "一艘圆润单体船,甲板带内部开口,两端为船头与船尾。",
 "一艘圆润单体船,有船头、船尾、甲板面和内部开口。",
 "一艘圆润单体船;船头船尾框出一块带内部开口的甲板。",
 "一艘圆润单体船,带船头、船尾、平甲板与内部开口。",
 "一艘圆润单体船,船头、船尾、甲板与敞开的内部。",
]
VESSEL_STRUCT = [
 ("The curved hull defines bow and stern; the connected perimeter deck leaves an interior opening.",
  "弧形船体界定船头与船尾;连通的周圈甲板留出内部开口。"),
 ("The curved hull shapes the bow and stern; the connected perimeter deck leaves an interior opening.",
  "弧形船身形成船头与船尾;相连的周边甲板围出内部开口。"),
 ("A curved hull sets the bow and stern apart; the connected perimeter deck leaves an interior opening.",
  "弧形船体勾出船头船尾;连在一起的环绕甲板留下内部开口。"),
 ("The curved hull separates bow and stern; the continuous perimeter deck leaves an interior opening.",
  "弯曲船身区分船头与船尾;连续的外圈甲板形成内部开口。"),
 ("The curved hull forms the bow and stern; the connected perimeter deck encloses an interior opening.",
  "弧形船体塑造出船头与船尾;连通的周边甲板在内侧留出开口。"),
]
VESSEL_CABIN = (" A small cabin attaches toward the stern.", "船尾方向附着一间小舱室。")
VESSEL_RATIOS = [(0.22,0.55),(0.25,0.45),(0.27,0.60),(0.29,0.75),(0.31,0.90),
                 (0.35,0.29),(0.40,1.20),(0.45,1.33),(0.55,0.50),(0.63,0.65)]
VESSEL_COLORS = [("tan, brown","棕褐、棕"),("white, brown","白、棕")]

def tower_prompt(lvl, i):
    pe = [TOWER_BASE_EN[i], TOWER_STRUCT_EN[i]]
    pz = [TOWER_BASE_ZH[i], TOWER_STRUCT_ZH[i]]
    if lvl >= 3: pe.append(GEOM_EN[i]); pz.append(GEOM_ZH[i])
    if lvl >= 4:
        w, h = TOWER_RATIOS[i]; pe.append(prop_en(w, h)); pz.append(prop_zh(w, h))
    if lvl >= 5:
        pe.append(color_en("gray, red")); pz.append(color_zh("灰、红"))
    return " ".join(pe), "".join(pz)

def train_prompt(lvl, i):
    pe = [TRAIN_BASE_EN[i]]; pz = [TRAIN_BASE_ZH[i]]
    if lvl >= 2:
        si, n = TRAIN_WHEELS[i]
        se, sz = TRAIN_STRUCT[si]
        pe.append(se.format(n=n)); pz.append(sz.format(n=n))
    if lvl >= 3: pe.append(GEOM_EN[i]); pz.append(GEOM_ZH[i])
    if lvl >= 4:
        w, h = TRAIN_RATIOS[i]; pe.append(prop_en(w, h)); pz.append(prop_zh(w, h))
    if lvl >= 5:
        pe.append(color_en("near black, blue, light blue")); pz.append(color_zh("近黑、蓝、浅蓝"))
    return " ".join(pe), "".join(pz)

def vessel_prompt(lvl, i):
    pe = [VESSEL_BASE_EN[i]]; pz = [VESSEL_BASE_ZH[i]]
    if lvl >= 2:
        se, sz = VESSEL_STRUCT[i % 5]
        pe.append(se); pz.append(sz)
        if i >= 5:
            pe.append(VESSEL_CABIN[0]); pz.append(VESSEL_CABIN[1])
    if lvl >= 3: pe.append(GEOM_EN[i]); pz.append(GEOM_ZH[i])
    if lvl >= 4:
        w, h = VESSEL_RATIOS[i]; pe.append(prop_en(w, h)); pz.append(prop_zh(w, h))
    if lvl >= 5:
        ce, cz = VESSEL_COLORS[i % 2]
        pe.append(color_en(ce)); pz.append(color_zh(cz))
    return " ".join(pe), "".join(pz)

GROUPS = [("tower", [3,4,5], tower_prompt), ("train", [1,2,3,4,5], train_prompt), ("vessel", [2,3,4,5], vessel_prompt)]
CAT_ZH = dict(tower="塔", train="火车", vessel="帆船")
out = {"note": "提示词严格按 48³ 训练集模板(promptLevel 1-5)与训练词库生成;训练证据见 evidence 字段",
       "groups": {}, "evidence": {
 "source": "release lego-retile-ab-80000-20261013-v1 的 source.prompts.json(A 分片 1000 模型样本)",
 "trained_l1_captions": {
   "tower": "A round tower with upright body, lower entrance and curved crown.",
   "train": "A curved roof train with driving area, side windows and attached wheel groups.",
   "vessel": "A rounded monohull boat with bow, stern, deck and interior opening."},
 "level_template": {
   "L1": "minimal: 仅基础描述",
   "L2": "basic_structure: +结构关系句",
   "L3": "geometry: +Curved substantial surfaces carry their continuously attached functional parts.",
   "L4": "proportion: +Overall width is X times depth; height is Y times width.",
   "L5": "comprehensive: +颜色分区句(训练出现的配色)+视角句"},
 "trained_variation_axes": {"train": "轮子数 4/6", "vessel": "船尾小舱室(可选)",
                            "L4": "宽深比/高宽比数值", "L5": "配色组合(tower: gray,red | train: near black,blue,light blue | vessel: tan,brown / white,brown)"},
 "untrained_features_avoid": {
   "tower": ["battlements/雉堞", "arrow slits/箭孔", "cone roof/锥顶", "flag pennant/旗帜"],
   "train": ["chimney/烟囱", "boiler/锅炉", "cab(训练用 driving area)", "cowcatcher/排障器", "whistle/汽笛"],
   "vessel": ["mast/桅杆", "sail/帆", "rudder/舵", "jib/前帆", "boom/帆桁"]},
 "warning": "上述 untrained_features 在 48³ 训练集中未出现,写进提示词会造成分布外;旧版提示词大量使用这些特征,是本轮重做的主因之一。"}}

for cat, levels, fn in GROUPS:
    for lvl in levels:
        prompts = []
        for i in range(10):
            en, zh = fn(lvl, i)
            prompts.append({"id": f"{cat}-L{lvl}-R{i+1:02d}", "en": en, "zh": zh})
        out["groups"][f"{cat}_L{lvl}"] = {"category": cat, "level": lvl, "cat_zh": CAT_ZH[cat], "prompts": prompts}

Path("round2_prompts.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
n = sum(len(g["prompts"]) for g in out["groups"].values())
print(f"生成 {len(out['groups'])} 组 × 10 条 = {n} 条 → round2_prompts.json")
for k, g in out["groups"].items():
    print(f"\n--- {k} 示例 R01 ---\n{g['prompts'][0]['en']}")
