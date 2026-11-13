from pathlib import Path
import zipfile

root=Path('D:/BrickMore/Essay/BrickMore/V1.2')
target=root/'BrickMore_V1.2_LaTeX.zip'
files=[p for p in root.rglob('*') if p.is_file()
       and p!=target and '__pycache__' not in p.parts
       and p.suffix not in {'.log','.aux','.out','.pyc','.nbc','.nbi'}]
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in files:
        archive.write(path,path.relative_to(root).as_posix())
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
    for name in ['main.tex','main.pdf','figure1.tex','figure2.tex','figure1.pdf','figure2.pdf',
                 'figures/figure1.png','figures/figure2.png','figure_tex/figure1_content.tex',
                 'figure_tex/figure2_content.tex','scripts/build.ps1']:
        assert name in archive.namelist(),name
print(f'Packaged {len(files)} files; {target.stat().st_size/1024/1024:.2f} MiB')
print(target)
