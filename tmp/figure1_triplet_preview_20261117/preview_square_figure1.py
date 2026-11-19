from pathlib import Path
from PIL import Image, ImageDraw

from preview_figure1 import ACCENT, ARROW, CATEGORIES, LINE, MUTED, TYPES, WASH, label

HERE = Path(__file__).resolve().parent
OUTPUT = Path("D:/BrickMore/output/figures/BrickForma_Figure1_preview_square_transparent.png")
WIDTH, HEIGHT = 2016, 1712
H_GAP, V_GAP = 10, 20
TOP_SIZE, GALLERY_SIZE = 310, 324
GALLERY_Y = 679
LEFT = 34
assert H_GAP <= V_GAP


def square_tile(image, edge, pad=12):
    tile = Image.new("RGBA", (edge, edge))
    span = edge - 2 * pad
    factor = min(span / image.width, span / image.height)
    render = image.resize((round(image.width * factor), round(image.height * factor)),
                          Image.Resampling.LANCZOS)
    tile.alpha_composite(render, ((edge - render.width)//2, (edge - render.height)//2))
    assert tile.width == tile.height == edge
    assert tile.getpixel((0, 0))[3] == 0
    return tile


def line_arrow(draw, start, end, y):
    head = min(12, (end - start) // 2)
    draw.line((start, y, end - head + 1, y), fill=ARROW, width=3)
    draw.polygon(((end,y), (end-head,y-6), (end-head,y+6)), fill=ARROW)


def render_figure():
    canvas = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(canvas)
    assets = {
        p.stem.removeprefix("render-"): Image.open(p).convert("RGBA")
        for p in HERE.glob("render-*.png")
    }
    xs = [(WIDTH - (6 * TOP_SIZE + 5 * H_GAP))//2 + i * (TOP_SIZE + H_GAP) for i in range(6)]
    right = xs[-1] + TOP_SIZE
    split = xs[4] - H_GAP//2
    label(draw, (LEFT, 29), "(a) Voxel to LEGO brick", 42, True)
    label(draw, (split + 24, 29), "(b) Connectivity repair", 42, True)
    captions = ("Voxels", "Bricks", "Voxels", "Bricks", "Raw", "Retiled")
    keys = ("table_a_voxel", "table_a_brick", "birdhouse_a_voxel",
            "birdhouse_a_brick", "camera_raw", "camera_generated")
    for x, text, name in zip(xs, captions, keys):
        label(draw, (x + TOP_SIZE//2, 79), text, 38, anchor="mm")
        canvas.alpha_composite(square_tile(assets[name], TOP_SIZE, pad=15), (x, 103))
    for i in (0,2,4):
        x = xs[i] + TOP_SIZE + H_GAP//2
        line_arrow(draw,x-13,x+13,103+TOP_SIZE//2)
    for i, text in enumerate(("Table: 1,117 voxels → 197 bricks",
                             "Birdhouse: 937 voxels → 200 bricks", "Camera: raw → retiled")):
        center=(xs[i*2] + xs[i*2+1] + TOP_SIZE)//2
        label(draw,(center,443),text,35,anchor="mm")
    draw.line((split,7,split,459),fill=LINE,width=2)
    draw.line((LEFT,474,right,474),fill=LINE,width=2)

    label(draw,(LEFT,501),"Brick type",37,color=MUTED)
    for i, entry in enumerate(TYPES.values()):
        x=220+155*i
        draw.rounded_rectangle((x,487,x+28,515),3,fill=entry["hex"])
        label(draw,(x+41,501),entry["size"].replace("x","×"),36)
    draw.rounded_rectangle((LEFT,534,right,617),8,fill=WASH)
    label(draw,(53,553),"Automated dataset construction",39,True,color=ACCENT)
    label(draw,(53,597),"80k shapes · 21 classes · 5 captions",36,color=MUTED)
    line_arrow(draw,760,844,575)
    label(draw,(1029,553),"LoRA training",39,True,anchor="mm",color=ACCENT)
    label(draw,(1029,597),"Qwen3-1.7B",36,anchor="mm")
    line_arrow(draw,1244,1328,575)
    label(draw,(1619,553),"Text-to-brick pipeline",39,True,anchor="mm",color=ACCENT)
    label(draw,(1619,597),"Generate + repair",36,anchor="mm")

    label(draw,(LEFT,646),"(c) Category-wise comparison",42,True)
    gallery_left=right-(5*GALLERY_SIZE+4*H_GAP)
    gallery_height=3*GALLERY_SIZE+2*V_GAP
    for i in range(5):
        x=gallery_left+i*(GALLERY_SIZE+H_GAP)-H_GAP//2
        draw.line((x,GALLERY_Y,x,GALLERY_Y+gallery_height),fill=LINE,width=2)
    for i in (1,2):
        y=GALLERY_Y+i*(GALLERY_SIZE+V_GAP)-V_GAP//2
        draw.line((LEFT,y,right,y),fill=LINE,width=2)
    entries=(
        ("AI-generated","voxels","voxel"),
        ("Retiled LEGO","original colors","retiled"),
        ("BrickForma","by brick type","generated"),
    )
    for i, (title, subtitle, form) in enumerate(entries):
        y=GALLERY_Y+i*(GALLERY_SIZE+V_GAP)
        middle=y+GALLERY_SIZE//2
        label(draw,(LEFT,middle-23),title,38,True)
        label(draw,(LEFT,middle+23),subtitle,36,color=MUTED)
        for j, category in enumerate(CATEGORIES):
            x=gallery_left+j*(GALLERY_SIZE+H_GAP)
            canvas.alpha_composite(square_tile(assets[f"{category}_{form}"],GALLERY_SIZE),(x,y))
    assert canvas.getpixel((0,0))[3]==0
    assert canvas.getpixel((gallery_left+5,GALLERY_Y+5))[3]==0
    canvas.save(OUTPUT, optimize=True, dpi=(320,320))
    background=Image.new("RGBA",canvas.size,"white")
    background.alpha_composite(canvas)
    background.convert("RGB").resize((1210,1028), Image.Resampling.LANCZOS).save(HERE/"square_preview_white.jpg",quality=95)
    print(OUTPUT, canvas.size, canvas.mode, "tile gaps", H_GAP, V_GAP)


if __name__ == "__main__":
    render_figure()

