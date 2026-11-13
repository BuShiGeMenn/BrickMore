# -*- coding: utf-8 -*-
"""第三轮提示词:空缺 7 组(basket L2 / bench L4-L5 / mug L3-L5 / table L5)
严格按 48³ 训练集模板与词库;每组 10 条,生成时取 R01/R03/R05/R07/R09。"""
import json
from pathlib import Path

def prop_en(w, h): return f"Overall width is {w:.2f} times depth; height is {h:.2f} times width. Parts follow functional positions."
def prop_zh(w, h): return f"总宽是深度的 {w:.2f} 倍;高度是宽度的 {h:.2f} 倍。各部件按功能位置排布。"
def color_en(c): return f"Continuous {c} color regions distinguish the body and attachments. The front reveals functional parts; side and top views reveal depth, connections and layout."
def color_zh(c): return f"连续的 {c} 色块区分主体与附件。正面显示功能部件;侧面与顶面显示深度、连接与布局。"

def variants(base_en, base_zh, n=10):
    return [(base_en[i % len(base_en)], base_zh[i % len(base_zh)]) for i in range(n)]

BASKET_L1 = ["An oval basket with closed base, walls and an arched carrying handle."]
BASKET_L1_ZH = ["一个椭圆篮,底封闭,有篮壁和拱形提手。"]
BASKET_L2 = [
 "Continuous walls surround the cavity; both handle ends attach to opposite sides.",
 "Walls run continuously around the cavity, and the two ends of the handle attach to opposite sides.",
 "The cavity is enclosed by continuous walls; the handle joins the rim at two opposite sides.",
 "Continuous walls close around the cavity while both ends of the arched handle fasten to opposite sides.",
 "A continuous wall wraps the cavity; each handle end is fixed to the opposite rim.",
 "Continuous walls surround the interior, with the handle attached at opposite points of the rim.",
 "The cavity sits inside continuous walls; the handle's two ends connect to facing sides.",
 "Walls stay continuous around the cavity and both handle ends attach on opposite sides.",
 "Continuous walls enclose the cavity; the arched handle is anchored to two facing sides.",
 "Round continuous walls bound the cavity, and the handle ends attach across from each other.",
]
BASKET_L2_ZH = [
 "连续的篮壁环绕空腔;提手两端分别接在相对的两侧。",
 "篮壁连续环绕空腔,提手两端接在相对两侧。",
 "空腔由连续篮壁围合;提手在相对的两侧与篮口相接。",
 "连续篮壁围住空腔,拱形提手的两端固定在相对两侧。",
 "一圈连续的篮壁包住空腔;提手每端固定在相对的篮口上。",
 "连续篮壁围绕内部,提手接在篮口相对的两点。",
 "空腔位于连续篮壁之内;提手两端连到相对的两侧。",
 "篮壁保持连续并环绕空腔,提手两端附着于相对两侧。",
 "连续篮壁围出空腔;拱形提手锚定在相对两侧。",
 "圆润的连续篮壁界定空腔,提手两端相对而接。",
]
BASKET_L3 = [
 "Oval continuous walls enclose the cavity; a thick rim and sealed base join those walls.",
 "The oval continuous walls enclose the cavity, joined by a thick rim and sealed base.",
 "A thick rim and a sealed base connect the oval continuous walls that enclose the cavity.",
 "Oval continuous walls bound the cavity; the thick rim and sealed base tie into them.",
 "The cavity is enclosed by oval continuous walls, with a thick rim and sealed base joining them.",
 "Oval continuous walls surround the cavity and meet a thick rim and sealed base.",
 "Thick rim and sealed base join the oval continuous walls enclosing the cavity.",
 "Oval walls run continuously around the cavity, joined by the thick rim and sealed base.",
 "The cavity is shut in by oval continuous walls, thick rim and sealed base together.",
 "Oval continuous walls hold the cavity; a thick rim and sealed base connect to them.",
]
BASKET_L3_ZH = [
 "椭圆的连续篮壁围合空腔;厚篮沿与封闭底与该壁相接。",
 "椭圆形连续篮壁围住空腔,并由厚篮沿和封闭底相连。",
 "厚篮沿与封闭底连接围住空腔的椭圆连续篮壁。",
 "椭圆连续篮壁界定空腔;厚篮沿和封闭底与之相接。",
 "空腔由椭圆连续篮壁围合,厚篮沿与封闭底把壁连成一体。",
 "椭圆连续篮壁环绕空腔,并与厚篮沿、封闭底相接。",
 "厚篮沿与封闭底连接着围合空腔的椭圆连续篮壁。",
 "椭圆篮壁连续环绕空腔,由厚篮沿与封闭底相连。",
 "空腔被椭圆连续篮壁、厚篮沿与封闭底共同封住。",
 "椭圆连续篮壁承托空腔;厚篮沿与封闭底与之相连。",
]
BASKET_RATIOS = [(0.65,0.72),(0.80,0.86),(0.95,0.96),(1.00,1.06),(1.15,1.16),
                 (1.30,1.26),(1.50,1.36),(1.70,1.52),(1.90,1.70),(2.00,1.86)]

BENCH_L1 = ["A rounded bench with an elongated seat and four supporting legs."]
BENCH_L1_ZH = ["一条圆角长凳,座面狭长,由四条腿支撑。"]
BENCH_L2A = "A horizontal elongated seat rests on four separate legs beneath its ends."
BENCH_L2A_ZH = "水平的狭长座面架在它两端下方的四条独立腿上。"
BENCH_L2B = "A horizontal elongated seat rests on four separate legs beneath its ends. A rear backrest is attached to the seat."
BENCH_L2B_ZH = "水平的狭长座面架在两端下方的四条独立腿上;座面后部连着靠背。"
BENCH_L3 = [
 "Rounded thick surfaces attach continuously to four separate downward legs.",
 "The rounded thick surfaces join continuously to the four separate legs that extend downward.",
 "Four separate downward legs attach continuously to the rounded thick surfaces.",
 "Rounded thick surfaces connect continuously with four separate legs going down.",
 "The rounded thick surfaces carry four separate downward legs in continuous attachment.",
 "Continuous attachment joins the rounded thick surfaces to four separate legs below.",
 "The four downward legs attach continuously to the rounded thick surfaces.",
 "Rounded thick surfaces are continuously attached to four separate legs extending down.",
 "Four separate legs descend and attach continuously to the rounded thick surfaces.",
 "The rounded thick surfaces hold four separate downward legs, attached continuously.",
]
BENCH_L3_ZH = [
 "圆角厚实表面连续附着在四条独立向下的腿上。",
 "圆角厚实表面与向下延伸的四条独立腿连续相接。",
 "四条独立向下的腿连续附着在圆角厚实表面上。",
 "圆角厚实表面与四条向下的独立腿连续相连。",
 "圆角厚实表面以连续附着方式承载四条独立向下的腿。",
 "连续附着把圆角厚实表面与下方四条独立腿连在一起。",
 "四条向下的腿连续附着于圆角厚实表面。",
 "圆角厚实表面连续附着在向下延伸的四条独立腿上。",
 "四条独立的腿向下延伸并连续附着在圆角厚实表面上。",
 "圆角厚实表面托住四条独立向下的腿,且为连续附着。",
]
BENCH_RATIOS = [(1.95,0.22),(2.20,0.26),(2.50,0.30),(2.80,0.34),(3.10,0.38),
                (3.50,0.42),(3.90,0.46),(4.40,0.52),(5.00,0.60),(5.60,0.72)]

MUG_L1 = ["An oval mug with open mouth and a pierced loop handle."]
MUG_L1_ZH = ["一个椭圆马克杯,杯口敞开,带穿环把手。"]
MUG_L2 = [
 "Walls surround a sealed bottom cavity; upper and lower roots of the right loop handle join the cup.",
 "The walls enclose a sealed-bottom cavity, and the right loop handle joins the cup at its upper and lower roots.",
 "A sealed base sits beneath cavity walls; the right-hand loop handle joins the cup by its upper and lower roots.",
 "Walls form a cavity with a sealed bottom; the loop handle on the right attaches at two roots to the cup.",
 "The cavity is walled and sealed below; upper and lower roots of the right loop handle connect to the cup.",
 "Sealed at the bottom cavity walls stand, with the right loop handle's two roots joining the cup.",
 "Walls surround the cavity above a sealed bottom, and both roots of the right handle attach to the cup.",
 "The right loop handle joins the cup through upper and lower roots, its walls enclosing a sealed-bottom cavity.",
 "A sealed-bottom cavity is surrounded by walls; the right loop handle connects at its top and bottom roots.",
 "Walls enclose a sealed bottom cavity; the right loop handle's upper and lower roots merge into the cup.",
]
MUG_L2_ZH = [
 "杯壁围出一个封底的空腔;右侧穿环把手的上下两个根部与杯身相接。",
 "杯壁围出封底空腔,右侧环形把手以上下两个根部连到杯身。",
 "封底之上是杯壁围成的空腔;右侧环形把手通过上下根与杯身相连。",
 "杯壁构成底部封住的空腔;右侧环形把手以两个根部附着于杯身。",
 "空腔被杯壁围住、底部封闭;右侧环形把手的上下根部接入杯身。",
 "底部封闭的空腔外有杯壁;右侧环形把手的两个根部连接杯身。",
 "杯壁环绕封底空腔,右侧把手的上下根部都附着在杯身上。",
 "右侧环形把手经上下根部与杯身相接,杯壁围住封底空腔。",
 "封底空腔由杯壁包围;右侧环形把手在上下两处根部连入杯身。",
 "杯壁围合封底空腔;右侧环形把手的上下根部并入杯身。",
]
MUG_L3 = [
 "Oval continuous walls enclose the cavity; a thick rim and sealed base join those walls.",
 "The oval continuous walls enclose the cavity, joined by a thick rim and sealed base.",
 "A thick rim and a sealed base connect the oval continuous walls that enclose the cavity.",
 "Oval continuous walls bound the cavity; the thick rim and sealed base tie into them.",
 "The cavity is enclosed by oval continuous walls, with a thick rim and sealed base joining them.",
 "Oval continuous walls surround the cavity and meet a thick rim and sealed base.",
 "Thick rim and sealed base join the oval continuous walls enclosing the cavity.",
 "Oval walls run continuously around the cavity, joined by the thick rim and sealed base.",
 "The cavity is shut in by oval continuous walls, thick rim and sealed base together.",
 "Oval continuous walls hold the cavity; a thick rim and sealed base connect to them.",
]
MUG_L3_ZH = BASKET_L3_ZH
MUG_RATIOS = [(0.90,0.34),(1.10,0.40),(1.30,0.46),(1.50,0.52),(1.70,0.58),
              (1.90,0.62),(2.20,0.66),(2.50,0.37),(2.70,0.44),(1.00,0.50)]

TABLE_L1 = ["An oval four leg table with continuous tabletop and separate supports."]
TABLE_L1_ZH = ["一张椭圆四腿桌,桌面连续,桌腿独立支撑。"]
TABLE_L2 = [
 "Four legs join the underside and reach the ground, leaving a usable horizontal tabletop.",
 "The four legs attach to the underside and stand on the ground, keeping a usable horizontal top.",
 "Four separate legs connect beneath and touch the ground, leaving the horizontal tabletop usable.",
 "Beneath the top, four legs join the underside and reach the floor, so the tabletop stays usable.",
 "Four legs run from the underside to the ground, leaving a clear horizontal tabletop above.",
 "The underside carries four legs down to the ground, preserving a usable horizontal top.",
 "Four legs join under the tabletop and reach the ground, leaving the horizontal surface usable.",
 "Legs beneath the top reach the ground in four places, keeping the tabletop horizontal and usable.",
 "Four supporting legs attach to the underside and reach the ground, leaving a usable flat tabletop.",
 "The tabletop stays horizontal and usable as four legs join its underside and reach the ground.",
]
TABLE_L2_ZH = [
 "四条腿连接桌面下侧并落到地面,留出可用的水平桌面。",
 "四条腿接在桌面下方、立于地面,保持水平桌面可用。",
 "四条独立的腿在下方连接并触地,使水平桌面保持可用。",
 "桌面下方四条腿接在下侧并落到地面,桌面仍然可用。",
 "四条腿从桌面下侧伸到地面,上方留出完整的水平桌面。",
 "桌面下侧的四条腿向下落到地面,保住可用的水平顶面。",
 "四条腿在桌面下连接并落到地面,留出可用的水平面。",
 "桌面下的腿在四处触地,使桌面保持水平可用。",
 "四条支撑腿接在下侧并落至地面,留出可用的平桌面。",
 "四条腿连接下侧直到地面,桌面保持水平且可用。",
]
TABLE_L3 = [
 "Rounded thick surfaces attach continuously to four separate downward legs.",
 "The rounded thick surfaces join continuously to the four separate legs that extend downward.",
 "Four separate downward legs attach continuously to the rounded thick surfaces.",
 "Rounded thick surfaces connect continuously with four separate legs going down.",
 "The rounded thick surfaces carry four separate downward legs in continuous attachment.",
 "Continuous attachment joins the rounded thick surfaces to four separate legs below.",
 "The four downward legs attach continuously to the rounded thick surfaces.",
 "Rounded thick surfaces are continuously attached to four separate legs extending down.",
 "Four separate legs descend and attach continuously to the rounded thick surfaces.",
 "The rounded thick surfaces hold four separate downward legs, attached continuously.",
]
TABLE_L3_ZH = BENCH_L3_ZH
TABLE_RATIOS = [(0.90,0.38),(1.10,0.48),(1.30,0.58),(1.50,0.68),(1.70,0.78),
                (1.90,0.88),(2.10,0.98),(2.30,1.08),(2.50,0.42),(1.00,0.62)]

COLORS = {
 "basket": ("dark brown, tan, brown", "深棕、棕褐、棕"),
 "bench": ("dark brown, brown", "深棕、棕"),
 "mug": ("blue, dark brown, tan", "蓝、深棕、棕褐"),
 "table": ("dark brown, tan", "深棕、棕褐"),
}

def build(cat, lvl, base_en, base_zh, l2_en, l2_zh, l3_en, l3_zh, ratios, n=10):
    prompts = []
    for i in range(n):
        pe = [base_en[0] if isinstance(base_en, list) else base_en]
        pz = [base_zh[0] if isinstance(base_zh, list) else base_zh]
        l2e = l2_en[i] if isinstance(l2_en, list) else l2_en
        l2z = l2_zh[i] if isinstance(l2_zh, list) else l2_zh
        pe.append(l2e); pz.append(l2z)
        if lvl >= 3:
            l3e = l3_en[i] if isinstance(l3_en, list) else l3_en
            l3z = l3_zh[i] if isinstance(l3_zh, list) else l3_zh
            pe.append(l3e); pz.append(l3z)
        if lvl >= 4:
            w, h = ratios[i]; pe.append(prop_en(w, h)); pz.append(prop_zh(w, h))
        if lvl >= 5:
            ce, cz = COLORS[cat]; pe.append(color_en(ce)); pz.append(color_zh(cz))
        prompts.append({"id": f"{cat}-L{lvl}-Q{i+1:02d}", "en": " ".join(pe), "zh": "".join(pz)})
    return prompts

groups = {}
groups["basket_L2"] = build("basket", 2, BASKET_L1, BASKET_L1_ZH, BASKET_L2, BASKET_L2_ZH, None, None, None)
bench_l2 = [BENCH_L2A if i < 5 else BENCH_L2B for i in range(10)]
bench_l2_zh = [BENCH_L2A_ZH if i < 5 else BENCH_L2B_ZH for i in range(10)]
groups["bench_L4"] = build("bench", 4, BENCH_L1, BENCH_L1_ZH, bench_l2, bench_l2_zh, BENCH_L3, BENCH_L3_ZH, BENCH_RATIOS)
groups["bench_L5"] = build("bench", 5, BENCH_L1, BENCH_L1_ZH, bench_l2, bench_l2_zh, BENCH_L3, BENCH_L3_ZH, BENCH_RATIOS)
groups["mug_L3"] = build("mug", 3, MUG_L1, MUG_L1_ZH, MUG_L2, MUG_L2_ZH, MUG_L3, MUG_L3_ZH, None)
groups["mug_L4"] = build("mug", 4, MUG_L1, MUG_L1_ZH, MUG_L2, MUG_L2_ZH, MUG_L3, MUG_L3_ZH, MUG_RATIOS)
groups["mug_L5"] = build("mug", 5, MUG_L1, MUG_L1_ZH, MUG_L2, MUG_L2_ZH, MUG_L3, MUG_L3_ZH, MUG_RATIOS)
groups["table_L5"] = build("table", 5, TABLE_L1, TABLE_L1_ZH, TABLE_L2, TABLE_L2_ZH, TABLE_L3, TABLE_L3_ZH, TABLE_RATIOS)

out = {"note": "第三轮:空缺 7 组,严格按训练集模板/词库;每组 10 条", "groups": groups,
       "evidence": {
         "trained_l1": {"basket": BASKET_L1[0], "bench": BENCH_L1[0], "mug": MUG_L1[0], "table": TABLE_L1[0]},
         "variation_axes": {"bench": "靠背有无(训练 17/45 带靠背)", "L4": "比例数值", "L5": "配色"},
         "colors": {k: v[0] for k, v in COLORS.items()},
         "ratio_ranges": {"basket": "W/D 0.52-2.09, H/W 0.65-1.91",
                          "bench": "W/D 1.91-5.86, H/W 0.20-0.76",
                          "mug": "W/D 0.86-2.78, H/W 0.31-0.68",
                          "table": "W/D 0.88-2.64, H/W 0.36-1.13"}}}
Path("round3_prompts.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
n = sum(len(g) for g in groups.values())
print(f"round3: {len(groups)} 组 × 10 = {n} 条")
for k, g in groups.items():
    print(f"\n--- {k} R01 ---\n{g[0]['en']}")
