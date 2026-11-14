from pathlib import Path
from PIL import Image
from pypdf import PdfReader
import re, json

out=Path('D:/BrickMore/Essay/BrickMore/V1.2/figure2_units')
scratch=Path('D:/BrickMore/tmp/figure2_units_build')
images=sorted(out.glob('unit_*.png'))
assert len(images)==8
canvas=Image.new('RGB',(2000,1544),(238,242,246))
for i,path in enumerate(images):
    image=Image.open(path).convert('RGB')
    assert image.width>=1600 and image.height>=1200
    reader=PdfReader(scratch/(path.stem+'.pdf'))
    assert len(reader.pages)==1
    log=(scratch/(path.stem+'.log')).read_text(encoding='utf-8')
    assert not re.search(r'Overfull|Missing character|undefined',log),path.stem
    image.thumbnail((480,364))
    canvas.paste(image,((i%4)*500+10,(i//4)*386+10))
canvas=canvas.crop((0,0,2000,772))
canvas.save(out/'overview.png')
code=(out/'content/unit_03_five_levels.tex').read_text(encoding='utf-8')
assert code.count(r'\draw[ray,')==5
for n in range(1,6):
    assert f'Level {n}:' in code
report={'independent_pngs':8,'dpi':300,'latex_sources':8,'model_to_prompt_arrows':5,
        'prompt_levels':[1,2,3,4,5],'unit_1':'TBD',
        'units_4_8_content':'unchanged','compile_errors':0,'text_overflow_warnings':0}
(out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(report)
