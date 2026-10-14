from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import export_core as core

def preview(path,model):
    size=200; image=Image.new('RGB',(420,445),'white');draw=ImageDraw.Draw(image)
    for i,view in enumerate(['front','right','top']):
        x=(i%2)*210;y=(i//2)*220
        draw.text((x+8,y+5),view.upper(),fill='#28374b')
        image.paste(core.projection(model,view,size),(x+5,y+22))
    image.paste(iso(model,size),(215,242));draw.text((218,225),'ISOMETRIC',fill='#28374b')
    image.save(path,optimize=False)

def iso(model,size=200):
    cells=model.cells
    def proj(x,y,z):return x-z, -.98*y+.45*(x+z)
    points=[proj(x+dx,y+dy,z+dz) for x,y,z in cells for dx,dy,dz in [(0,0,0),(1,1,1)]]
    low=[min(p[i] for p in points) for i in [0,1]];high=[max(p[i] for p in points) for i in [0,1]]
    scale=min((size-20)/(high[i]-low[i]+2) for i in [0,1])
    def screen(p):
        a,b=proj(*p);return ((a-low[0])*scale+10,(b-low[1])*scale+10)
    im=Image.new('RGB',(size,size),'#f7f8fa');dr=ImageDraw.Draw(im)
    faces=[((1,0,0),[(1,0,0),(1,0,1),(1,1,1),(1,1,0)],.80),
           ((0,1,0),[(0,1,0),(1,1,0),(1,1,1),(0,1,1)],1.),
           ((0,0,1),[(0,0,1),(0,1,1),(1,1,1),(1,0,1)],.65)]
    # The camera is above +X,+Z. Painter ordering is far to near.
    for (x,y,z),cell in sorted(cells.items(),key=lambda a:sum(a[0])):
        rgb=core.PALETTE[cell.color][:3]
        for delta,corners,shade in faces:
            if tuple(a+b for a,b in zip((x,y,z),delta)) in cells:continue
            polygon=[screen((x+dx,y+dy,z+dz)) for dx,dy,dz in corners]
            col=tuple(int(v*shade) for v in rgb)
            dr.polygon(polygon,fill=col)
    return im

def sheets(root,rows):
    cats=list(dict.fromkeys(x['category'] for x in rows));selected=[]
    for cat in cats:
        cr=[r for r in rows if r['category']==cat]
        choices=[cr[min(len(cr)-1,j*len(cr)//8)] for j in range(8)]
        board=Image.new('RGB',(8*200,225),'white');dr=ImageDraw.Draw(board)
        for i,row in enumerate(choices):
            source=Image.open(root/row['previewPath']);board.paste(source.crop((215,242,415,442)),(i*200,25))
            dr.text((i*200+4,5),f"{cat} / {row['modelId'].split('_m')[-1]}",fill='#222222')
        board.save(root/'previews'/f'{cat}.png')
        selected.append(cr[0])
    board=Image.new('RGB',(7*200,3*225),'white');dr=ImageDraw.Draw(board)
    for i,row in enumerate(selected):
        x=i%7*200;y=i//7*225
        source=Image.open(root/row['previewPath']);board.paste(source.crop((215,242,415,442)),(x,y+25))
        dr.text((x+4,y+5),row['category'],fill='#222222')
    board.save(root/'preview_21_categories.png')
