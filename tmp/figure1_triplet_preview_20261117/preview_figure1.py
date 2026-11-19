from hashlib import sha256
from pathlib import Path
import json
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from raster_source import mesh, raster

ROOT = Path("D:/BrickMore")
DATA = ROOT / "Essay/BrickMore/V2/figure_data"
OUTPUT = ROOT / "output/figures/BrickForma_Figure1_preview.png"
WORK = Path(__file__).resolve().parent
TYPES = json.loads((DATA / "brick_type_colors.json").read_text(encoding="utf-8"))
PROVENANCE = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
CATEGORIES = ("birdhouse", "camera", "chair", "car", "vessel")
GENERATED = {
    "birdhouse": "brickmore__birdhouse-L1__stitched",
    "camera": "brickmore__camera_L2_P1_G__stitched",
    "chair": "brickmore__chair-L2V5__raw",
    "car": "brickmore__car-L1V2__stitched",
    "vessel": "brickmore__vessel_L1_P2_G__stitched",
}
RAW_CAMERA = "brickmore__camera_L2_P1_G__raw"
PITCH = np.array((20, 24, 20), dtype=np.float32)
WIDTH, HEIGHT = 2240, 1266
INK = "#172b34"
MUTED = "#52636d"
ACCENT = "#235780"
LINE = "#dce4e8"
WASH = "#f0f4f8"
ARROW = "#718592"
FONTS = Path("C:/Windows/Fonts")
SQUARES = (
    ((-1, 0, 0), ((0, 0, 0),(0, 0, 1),(0, 1, 1),(0, 1, 0))),
    ((1, 0, 0), ((1, 0, 1),(1, 0, 0),(1, 1, 0),(1, 1, 1))),
    ((0, -1, 0), ((0, 0, 0),(1, 0, 0),(1, 0, 1),(0, 0, 1))),
    ((0, 1, 0), ((1, 1, 0),(0, 1, 0),(0, 1, 1),(1, 1, 1))),
    ((0, 0, -1), ((1, 0, 0),(0, 0, 0),(0, 1, 0),(1, 1, 0))),
    ((0, 0, 1), ((0, 0, 1),(1, 0, 1),(1, 1, 1),(0, 1, 1))),
)


def read_model(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def voxel_surface(category, original_colors):
    source = read_model(category + "_voxels.json")
    cells = {(v["x"], v["y"], v["z"]): tuple(v["color"]) for v in source["voxels"]}
    assert len(cells) == len(source["voxels"])
    vertices, faces, colors = [], [], []
    indexes = np.array(((0, 1, 2),(0, 2, 3)))
    for position, color in cells.items():
        for normal, corners in SQUARES:
            neighbor = tuple(p + d for p, d in zip(position, normal))
            if neighbor in cells:
                continue
            faces.extend(indexes + len(vertices))
            vertices.extend((np.asarray(corners) + position) * PITCH)
            colors.extend([color if original_colors else (181, 191, 202)] * 2)
    return (np.asarray(vertices), np.asarray(faces), np.asarray(colors),
            np.zeros(len(faces), dtype=bool))


def dataset_parts(category):
    records = []
    for line in (DATA / (category + "_dataset.ldr")).read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields or fields[0] != "1":
            continue
        color = fields[1]
        assert color.startswith("0x2") and len(color) == 9
        values = np.asarray(fields[2:14], dtype=np.float32)
        matrix = np.eye(4)
        matrix[:3, 3] = values[:3]
        matrix[:3, :3] = values[3:].reshape(3, 3)
        records.append((Path(fields[-1]).stem, matrix, tuple(bytes.fromhex(color[3:]))))
    source = read_model(category + "_voxels.json")
    source_palette = {tuple(v["color"]) for v in source["voxels"]}
    assert {r[2] for r in records} <= source_palette
    return records


def generated_parts(name):
    assert name in PROVENANCE["generated_examples"]
    return [(p["part_stem"], np.asarray(p["matrix_ldu"]), None)
            for p in read_model(name + ".json")["instances"]]


def brick_surface(records, use_original):
    vertices, faces, colors, studs = [], [], [], []
    offset = 0
    for index, (part, matrix, original) in enumerate(records):
        local, tri = mesh(part)
        oriented = local @ matrix[:3,:3].T + matrix[:3,3]
        oriented[:,1] *= -1
        center = (oriented.min(0) + oriented.max(0)) * 0.5
        # A small visual gap reveals seams without changing the assembly files.
        oriented = center + (oriented - center) * .980
        material = np.asarray(original if use_original else TYPES[part]["rgb"], dtype=np.float32)
        if use_original:
            material *= 1 + ((index * 7) % 13 - 6) * .008
        vertices.append(oriented)
        faces.append(tri + offset)
        colors.append(np.tile(material, (len(tri), 1)))
        studs.append(np.mean(local[tri, 1], axis=1) < -.25)
        offset += len(local)
    return (np.concatenate(vertices), np.concatenate(faces), np.concatenate(colors),
            np.concatenate(studs))


def render(name, geometry, azimuth=40, elevation=35):
    vertices, faces, base, studs = geometry
    vertices, faces = vertices.astype(np.float32), faces.astype(np.int32)
    assert len(faces) == len(base) == len(studs)
    normals = np.cross(vertices[faces[:,1]] - vertices[faces[:,0]], vertices[faces[:,2]] - vertices[faces[:,0]])
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:,None], 1e-12)
    theta, phi = np.deg2rad([azimuth, elevation])
    camera = np.array([np.sin(theta)*np.cos(phi), np.sin(phi), np.cos(theta)*np.cos(phi)])
    right = np.cross([0,1,0], camera)
    right /= np.linalg.norm(right)
    up = np.cross(camera,right)
    light = np.array([-.44, .87, .23])
    light /= np.linalg.norm(light)
    exposure = .55 + .42 * np.abs(normals @ light)
    specular = np.abs(normals @ ((camera + light) / np.linalg.norm(camera + light))) ** 12
    shaded = base * exposure[:,None] + 16 * specular[:,None]
    # Real studs come from the part meshes. A restrained highlight makes their rims readable.
    stud_highlight = np.where(studs, 20 * np.abs(normals[:,1]) + 7 * specular, 0)
    shaded += stud_highlight[:,None]
    shaded = np.clip(shaded, 3, 249).astype(np.float32)
    flat = np.column_stack((vertices @ right, vertices @ up))
    center = (flat.min(0) + flat.max(0)) * .5
    target = 730
    scale = target * .92 / max(np.ptp(flat, axis=0))
    projected = np.column_stack(((flat[:,0]-center[0])*scale + target/2,
                                 -(flat[:,1]-center[1])*scale + target/2,
                                 vertices @ camera)).astype(np.float32)
    pixels = raster(projected, faces, shaded, target)
    mask = np.any(pixels < 254, axis=2)
    yy, xx = np.nonzero(mask)
    assert len(xx) > 0
    rgba = Image.fromarray(pixels).convert("RGBA")
    rgba.putalpha(Image.fromarray(mask.astype(np.uint8)*255))
    crop = rgba.crop((xx.min(), yy.min(), xx.max()+1, yy.max()+1))
    crop.save(WORK / ("render-" + name + ".png"))
    return crop


def label(draw, xy, value, size, bold=False, anchor="lm", color=INK):
    font = ImageFont.truetype(str(FONTS / ("arialbd.ttf" if bold else "arial.ttf")), size)
    draw.text(xy, value, font=font, fill=color, anchor=anchor)


def arrow(draw, x0, x1, y):
    draw.line((x0,y,x1-10,y), fill=ARROW, width=3)
    draw.polygon(((x1,y),(x1-13,y-7),(x1-13,y+7)), fill=ARROW)


def place(canvas, image, bounds, shadow=False):
    x0, y0, x1, y1 = bounds
    sw, sh = x1-x0, y1-y0
    factor = min(sw/image.width, sh/image.height)
    tile = image.resize((round(image.width*factor),round(image.height*factor)),Image.Resampling.LANCZOS)
    x = round((x0+x1-tile.width)/2)
    y = y1 - tile.height
    if shadow:
        blur = Image.new("RGBA", (sw, 26))
        shape = ImageDraw.Draw(blur)
        spread = max(40,min(round(tile.width*.77),sw-12))
        shape.ellipse(((sw-spread)//2,9,(sw+spread)//2,18),fill=(55,70,79,46))
        canvas.alpha_composite(blur.filter(ImageFilter.GaussianBlur(5)), (x0,y1-15))
    canvas.alpha_composite(tile,(x,y))


def compose(sprites):
    canvas = Image.new("RGBA", (WIDTH,HEIGHT), "white")
    draw = ImageDraw.Draw(canvas)
    label(draw,(34,31),"(a) Voxel to LEGO brick",45,True)
    label(draw,(1506,31),"(b) Connectivity repair",45,True)
    draw.line((1477,9,1477,356),fill=LINE,width=3)
    centers = (202,553,927,1278,1684,2051)
    names = ("Voxels","Bricks","Voxels","Bricks","Raw","Retiled")
    keys = ("table_a_voxel","table_a_brick","birdhouse_a_voxel","birdhouse_a_brick","camera_raw","camera_generated")
    for x, name, key in zip(centers, names, keys):
        label(draw,(x,82),name,40,anchor="mm")
        place(canvas, sprites[key], (x-141,115,x+141,311), shadow=True)
    for first, second in zip(centers[::2],centers[1::2]):
        center=(first+second)//2
        arrow(draw,center-22,center+22,209)
    for x, text in [(377,"Table: 1,117 voxels → 197 bricks"),
                    (1105,"Birdhouse: 937 voxels → 200 bricks"),
                    (1867,"Camera: raw → retiled")]:
        label(draw,(x,345),text,38,anchor="mm")

    draw.line((34,371,2206,371),fill=LINE,width=3)
    label(draw,(35,403),"Brick type",39,color=MUTED)
    for index, brick in enumerate(TYPES.values()):
        x = 238 + index * 174
        draw.rounded_rectangle((x,388,x+32,419),radius=3,fill=brick["hex"])
        label(draw,(x+45,403),brick["size"].replace("x","×"),39)
    draw.rounded_rectangle((34,439,2206,528),radius=9,fill=WASH)
    label(draw,(54,462),"Automated dataset construction",41,True,color=ACCENT)
    label(draw,(54,505),"80k shapes · 21 classes · 5 captions",38,color=MUTED)
    arrow(draw,823,928,483)
    label(draw,(1146,462),"LoRA training",41,True,anchor="mm",color=ACCENT)
    label(draw,(1146,505),"Qwen3-1.7B",38,anchor="mm")
    arrow(draw,1397,1499,483)
    label(draw,(1837,462),"Text-to-brick pipeline",41,True,anchor="mm",color=ACCENT)
    label(draw,(1837,505),"Generate + repair",38,anchor="mm")

    label(draw,(34,566),"(c) Category-wise comparison",45,True)
    left, right = 295, 2205
    col_width=(right-left)//len(CATEGORIES)
    for i in range(len(CATEGORIES)+1):
        x=left+col_width*i
        draw.line((x,605,x,1242),fill=LINE,width=2)
    for y in (808,1027):
        draw.line((35,y,2206,y),fill=LINE,width=2)
    rows = (
        ("AI-generated","voxels","voxel",603,793),
        ("Retiled LEGO","original colors","retiled",823,1012),
        ("BrickForma","by brick type","generated",1041,1231),
    )
    for heading, detail, kind, y0, y1 in rows:
        mid=(y0+y1)//2
        label(draw,(34,mid-22),heading,39,True)
        label(draw,(34,mid+22),detail,37,color=MUTED)
        for column, category in enumerate(CATEGORIES):
            x=left+column*col_width
            place(canvas,sprites[category+"_"+kind],(x+21,y0,x+col_width-21,y1),shadow=kind!="voxel")
    canvas.convert("RGB").save(OUTPUT, optimize=True, dpi=(320,320))
    print(OUTPUT, canvas.size)


def main():
    sources = list(DATA.glob("*.ldr")) + list(DATA.glob("*.json")) + list((DATA/"meshes").glob("*.npz"))
    before = {p:sha256(p.read_bytes()).hexdigest() for p in sources}
    sprites = {}
    top = (("table",1117,197),("birdhouse",937,200))
    for category, nvox, nbrick in top:
        parts = dataset_parts(category)
        assert len(parts)==nbrick and len(read_model(category+"_voxels.json")["voxels"])==nvox
        sprites[category+"_a_voxel"] = render(category+"_a_voxel",voxel_surface(category,False))
        sprites[category+"_a_brick"] = render(category+"_a_brick",brick_surface(parts,False))
    sprites["camera_raw"] = render("camera_raw",brick_surface(generated_parts(RAW_CAMERA),False))
    for category in CATEGORIES:
        sprites[category+"_voxel"] = render(category+"_voxel",voxel_surface(category,True))
        sprites[category+"_retiled"] = render(category+"_retiled",brick_surface(dataset_parts(category),True))
        sprites[category+"_generated"] = render(category+"_generated",brick_surface(generated_parts(GENERATED[category]),False))
    compose(sprites)
    assert all(sha256(p.read_bytes()).hexdigest()==h for p,h in before.items())
    print("All input model hashes unchanged.")


if __name__ == "__main__":
    main()

