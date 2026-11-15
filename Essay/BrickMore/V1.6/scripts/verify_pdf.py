"""Read-only PDF checks. Run after the final build; requires pypdf."""
from pathlib import Path
import hashlib,json,re
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
r=PdfReader(ROOT/'main.pdf')
texts=[p.extract_text() for p in r.pages]
fonts={}
seen=set()
def resources(res):
    if not res:return
    res=res.get_object()
    for ref in res.get('/Font',{}).values():
        f=ref.get_object();name=str(f.get('/BaseFont',f.get('/Name','unnamed')))
        variants=f.get('/DescendantFonts',[f]);embedded=True
        for v in variants:
            d=v.get_object().get('/FontDescriptor',{})
            d=d.get_object() if hasattr(d,'get_object') else d
            embedded &= any(k in d for k in ['/FontFile','/FontFile2','/FontFile3'])
        fonts[name]={'subtype':str(f.get('/Subtype')),'embedded':bool(embedded)}
    for ref in res.get('/XObject',{}).values():
        key=(getattr(ref,'idnum',None),getattr(ref,'generation',None))
        if key in seen:continue
        seen.add(key);resources(ref.get_object().get('/Resources'))
for p in r.pages:resources(p.get('/Resources'))
log=(ROOT/'main.log').read_text(encoding='utf-8',errors='replace')
def page_of(fragment):return next((i+1 for i,t in enumerate(texts) if fragment in t),None)
result={
 'format':'Official AAAI-27 anonymous submission, pdfLaTeX',
 'compiled_pages':len(r.pages),'conclusion_page':page_of('Conclusion'),
 'figure_1_page':page_of('(a) Voxel-to-brick construction'),
 'figure_2_page':page_of('Agentic batch voxel generation'),
 'figure_3_page':page_of('Figure 3:'),
 'letter_pages':all(abs(float(p.mediabox.width)-612)<.01 and abs(float(p.mediabox.height)-792)<.01 for p in r.pages),
 'overfull_boxes':len(re.findall('Overfull',log)),
 'undefined_references_or_citations':len(re.findall(r'(?:Reference|Citation) .* undefined',log)),
 'missing_characters':len(re.findall('Missing character:',log)),
 'cjk_in_pdf_text':sum(len(re.findall(r'[\u4e00-\u9fff]',t)) for t in texts),
 'fonts':fonts,'all_fonts_embedded':all(v['embedded'] for v in fonts.values()),
 'type3_fonts':sum(v['subtype']=='/Type3' for v in fonts.values()),
 'pdf_sha256':hashlib.sha256((ROOT/'main.pdf').read_bytes()).hexdigest(),
 'template_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['aaai2027.sty','aaai2027.bst']},
 'protected_content':{'method':'BrickForma','dataset':'BrickMore-48','diagnostic_samples':525,'main_comparison_prompts':114,'training_samples_as_recorded':396610},
 'notes':['English figure labels replace Chinese labels in the compiled paper.',
 'Raster figure labels require visual inspection; text extraction alone is insufficient.',
 'Historical source projects and GrokBoT review notes remain local and are not packaged.']}
(ROOT/'build_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
assert result['letter_pages'] and result['all_fonts_embedded']
assert not any(result[k] for k in ['overfull_boxes','undefined_references_or_citations','missing_characters','cjk_in_pdf_text','type3_fonts'])
print(json.dumps({k:v for k,v in result.items() if k!='fonts'},indent=2))
