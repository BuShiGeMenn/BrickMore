from pathlib import Path
from shutil import copy2
from collections import Counter
import csv
import json
import sys

from PIL import Image, ImageDraw

REPO = Path("D:/BrickMore")
WORK = Path(__file__).resolve().parent
PREVIOUS = REPO / "tmp/figure1_triplet_preview_20261117"
sys.path.insert(0, str(PREVIOUS))
import preview_figure1 as prior

MODEL_DATA = WORK / "named_assets"
MODEL_DATA.mkdir(exist_ok=True)
RENDER_DIR = WORK / "renders_21"
RENDER_DIR.mkdir(exist_ok=True)
prior.DATA = MODEL_DATA
prior.WORK = RENDER_DIR
OUTPUT = Path("D:/BrickMore/output/figures/BrickForma_Figure1_21categories_halfpage_preview.png")

CATEGORIES = ("basket", "bed", "bench", "birdhouse", "bookshelf",
              "bottle", "bowl", "bus", "camera",
              "car", "chair", "guitar", "jar",
              "mug", "piano", "pot", "sofa", "table", "tower", "train", "vessel")
assert len(set(CATEGORIES)) == 21
EXISTING = set(prior.GENERATED)
OLD = REPO / "BrickMore_Comparision/BrickMoreComparison_20261116/BrickMoreComparison_20261116"
NEW = REPO / "tmp/comparison_20261117_intake/BrickMore_A260_20261117"
PAPER = REPO / "Essay/BrickMore/V2"
WIDTH, HEIGHT = 2800, 1700
INTRA, BETWEEN, ROW_GAP = 8, 20, 20
ROWS = (4,4,5,4,4)
EDGES = (214,214,170,214,214)
assert sum(ROWS) == 21 and INTRA <= BETWEEN <= ROW_GAP


def square(image, edge, pad=7, inner=None):
    usable = edge - 2*pad if inner is None else inner
    scale = min(usable/image.width,usable/image.height)
    image=image.resize((round(image.width*scale),round(image.height*scale)),
                       Image.Resampling.LANCZOS)
    canvas=Image.new("RGBA",(edge,edge))
    canvas.alpha_composite(image,((edge-image.width)//2,(edge-image.height)//2))
    assert canvas.size==(edge,edge) and canvas.getpixel((0,0))[3]==0
    return canvas


def get_image(name, directory):
    return Image.open(directory/("render-"+name+".png")).convert("RGBA")


def normalize_source(category):
    source=WORK/category/"source.model.json"
    assert source.is_file() and (WORK/category/"model.ldr").is_file()
    copy2(source,MODEL_DATA/(category+"_voxels.json"))
    copy2(WORK/category/"model.ldr",MODEL_DATA/(category+"_dataset.ldr"))


def assembly(sample):
    item=json.loads(sample.read_text(encoding="utf-8"))
    records=[(r["part_stem"],prior.np.asarray(r["matrix_ldu"]),None)
             for r in item["instances"]]
    assert len(records)>0 and all(r[0] in prior.TYPES for r in records)
    return records


def choose_output(category, observations):
    choices=[r for r in observations if r["category"]==category and int(r["level"])<=2]
    paths={r["sample_id"]:(NEW if r["prompt_id"].startswith("A") else OLD)/
           "Data/assemblies"/(r["sample_id"]+".json") for r in choices}
    source=max((r for r in choices if paths[r["sample_id"]].is_file()),
               key=lambda r:(float(r["pinv"])==0,float(r["vqa"]),float(r["pe"])))
    return paths[source["sample_id"]],source["prompt_id"]


def draw_arrow(draw,x,y):
    dy=8
    draw.line((x-37,y,x+20,y),fill=prior.ARROW,width=3)
    draw.polygon(((x+37,y),(x+20,y-dy),(x+20,y+dy)),fill=prior.ARROW)


def draw_soft_divider(draw, bounds):
    x0, y0, x1, y1 = bounds
    dash, gap = 12, 8
    color = (164, 181, 193, 105)
    if x0 == x1:
        for y in range(y0, y1 + 1, dash + gap):
            draw.line((x0, y, x1, min(y + dash - 1, y1)), fill=color, width=2)
    else:
        assert y0 == y1
        for x in range(x0, x1 + 1, dash + gap):
            draw.line((x, y0, min(x + dash - 1, x1), y1), fill=color, width=2)


def compose(sprites):
    canvas=Image.new("RGBA",(WIDTH,HEIGHT))
    draw=ImageDraw.Draw(canvas)
    label=prior.label
    label(draw,(52,35),"(a) Voxel to LEGO brick",50,True)
    label(draw,(1869,35),"(b) Connectivity refinement",50,True)
    draw_soft_divider(draw, (1825,13,1825,402))
    centers=(194,635,1083,1514,2072,2548)
    names=("table_a_voxel","table_a_brick","birdhouse_a_voxel",
           "birdhouse_a_brick","camera_raw","camera_generated")
    for x, name in zip(centers,names):
        canvas.alpha_composite(square(sprites[name],326,12),(x-163,78))
    for a,b in zip(centers[::2],centers[1::2]):
        draw_arrow(draw,(a+b)//2,246)
    label(draw,(2072,73),"Raw",42,anchor="mm")
    label(draw,(2548,73),"Refined",42,anchor="mm")
    draw.line((48,418,2752,418),fill=prior.LINE,width=3)
    label(draw,(51,449),"Brick type",45,color=prior.MUTED)
    for i,entry in enumerate(prior.TYPES.values()):
        x=304+i*213
        draw.rounded_rectangle((x,432,x+34,465),radius=3,fill=entry["hex"])
        label(draw,(x+49,449),entry["size"].replace("x","×"),43)
    label(draw,(52,506),"(c) 21 object categories",50,True)
    y=544
    index=0
    for i,(count,edge) in enumerate(zip(ROWS,EDGES)):
        width=count*(3*edge+2*INTRA)+(count-1)*BETWEEN
        x=(WIDTH-width)//2
        for group in range(count):
            category=CATEGORIES[index]
            index+=1
            for j,form in enumerate(("voxel","refined","generated")):
                canvas.alpha_composite(square(sprites[category+"_"+form],edge),
                                       (x+j*(edge+INTRA),y))
            x+=3*edge+2*INTRA
            if group<count-1:
                draw_soft_divider(draw, (x+BETWEEN//2,y+8,x+BETWEEN//2,y+edge-8))
            x+=BETWEEN
        y+=edge+ROW_GAP
        if i<len(ROWS)-1:
            draw_soft_divider(draw, (48,y-ROW_GAP//2,2752,y-ROW_GAP//2))
    assert index==len(CATEGORIES) and y-ROW_GAP < HEIGHT
    assert canvas.getpixel((0,0))[3]==0
    canvas.save(OUTPUT,optimize=True,dpi=(400,400))
    proof=Image.new("RGBA",canvas.size,"white")
    proof.alpha_composite(canvas)
    proof.convert("RGB").resize((1512,918),Image.Resampling.LANCZOS).save(WORK/"halfpage_proof.jpg",quality=95)
    print(OUTPUT,canvas.size)


def main():
    with (PAPER/"data/20261117/scores.csv").open(encoding="utf-8-sig",newline="") as f:
        observations=[r for r in csv.DictReader(f) if r["system"]=="BrickMore"]
    sprites={}
    sources={}
    for name in ("table_a_voxel","table_a_brick","birdhouse_a_voxel","birdhouse_a_brick",
                 "camera_raw","camera_generated"):
        sprites[name]=get_image(name,PREVIOUS)
    for category in CATEGORIES:
        normalize_source(category)
        prebuilt_voxels = PREVIOUS / ("render-"+category+"_voxel.png")
        if prebuilt_voxels.exists():
            sprites[category+"_voxel"]=get_image(category+"_voxel",PREVIOUS)
        else:
            sprites[category+"_voxel"]=prior.render(category+"_voxel",prior.voxel_surface(category,True))
        sprites[category+"_refined"] = prior.render(
            category+"_refined",
            prior.brick_surface(prior.dataset_parts(category), use_original=False),
        )
        if category in EXISTING:
            sprites[category+"_generated"]=get_image(category+"_generated",PREVIOUS)
            source=PAPER/"figure_data"/(prior.GENERATED[category]+".json")
            case=prior.GENERATED[category]
        else:
            source,case=choose_output(category,observations)
            sprites[category+"_generated"]=prior.render(category+"_generated",
                        prior.brick_surface(assembly(source),False))
        sources[category]={"voxel":str(WORK/category/"source.model.json"),
                           "refined":str(WORK/category/"model.ldr"),
                           "brickforma":str(source),"case":case,"row_order":CATEGORIES.index(category)+1}
    assert len(sources)==21
    (WORK/"triplet_provenance.json").write_text(json.dumps(sources,indent=2),encoding="utf-8")
    compose(sprites)


if __name__=="__main__":
    main()

