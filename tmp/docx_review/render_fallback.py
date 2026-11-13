import sys
from pathlib import Path
sys.path.insert(0, r'D:\BrickMore\tmp\docx_review\deps')
import aspose.words as aw
source=Path(r'D:\BrickMore\output\documents\BrickMore48_精简算法与逻辑说明.docx')
out=Path(r'D:\BrickMore\tmp\docx_review\render')
out.mkdir(parents=True,exist_ok=True)
doc=aw.Document(str(source))
doc.update_page_layout()
print('pages',doc.page_count)
doc.save(str(out/'qa.pdf'))
