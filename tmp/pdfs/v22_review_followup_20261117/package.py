from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
import pypdf

job = Path(__file__).resolve().parent
root = Path("D:/BrickMore")
live = root / "Essay/BrickMore/V2.2"
stage = job / "source"
bundle = job / "V2.2.zip"
test = job / "package-test"
snapshot = json.loads((job / "snapshot.json").read_text(encoding="utf-8"))
sources = [name for name in snapshot if name not in {"V2.2.zip", "main.pdf"}]

def read_text(path):
    doc = pypdf.PdfReader(path)
    pages = [re.sub(r"\s+", "", page.extract_text()) for page in doc.pages]
    return doc, pages

def validate(pdf):
    doc, pages = read_text(pdf)
    assert len(doc.pages) == 18, len(doc.pages)
    assert list(doc.pages[0].mediabox)[2:] == [612, 792]
    assert "Anonymoussubmission" in pages[0] and "BrickMore" not in "".join(pages)
    assert 0 < pages[0].find("Figure1:BrickFormaoverview.") < pages[0].find("Abstract")
    assert "Figure2:Data-constructionworkflow." in pages[3] and "Brickconversion" in pages[3]
    assert "Algorithm1BrickFormainferenceandrefinement" in "".join(pages[:7])
    assert "Figure3:" in pages[6] and "References" in pages[6]
    assert "Conclusion" in "".join(pages[:7])
    assert "Papers" not in doc.metadata.get("/Author", "")
    text = "".join(page.extract_text() for page in doc.pages)
    assert not re.search(r"\b(?:tiling|tiled|retile|retiled|retiling|TODO|placeholder)\b", text, re.I)
    assert "79,301" in pages[2]
    assert "VQAScore" in pages[1]
    assert "8incomplete" in "".join(pages)
    assert "merge_and_unload" in "".join(pages)
    assert "objectivecoefficients" in "".join(pages)
    assert "38177" in "".join(pages)
    assert "requireverification" not in "".join(pages)
    return pages

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

final_pages = validate(stage / "main.pdf")
for log in ["main.log", "figure2.log"]:
    contents = (stage / log).read_text(encoding="utf-8", errors="replace")
    assert "Overfull" not in contents
    assert "undefined references" not in contents

if len(sys.argv) == 1:
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        for name in sources:
            out.write(stage / name, name)
    with zipfile.ZipFile(bundle) as check:
        assert check.testzip() is None
        assert sorted(check.namelist()) == sorted(sources)
        assert all(check.read(name) == (stage / name).read_bytes() for name in sources)
        check.extractall(test)
    print(f"Verified {len(sources)} files in archive")
    sys.exit()

assert final_pages == validate(test / "main.pdf")
changed = [name for name in sources if digest(stage / name) != snapshot[name]] + ["main.pdf", "V2.2.zip"]
for name, expected in snapshot.items():
    assert digest(live / name) == expected, f"Live file changed during audit: {name}"

backup = job / "previous"
backup.mkdir(exist_ok=False)
for name in changed:
    dst = backup / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live / name, dst)

def atomic_copy(read_path, destination):
    permissions = destination.stat().st_mode
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp:
        pending = Path(temp.name)
        with read_path.open("rb") as src:
            shutil.copyfileobj(src, temp)
    try:
        if not permissions & stat.S_IWRITE:
            destination.chmod(permissions | stat.S_IWRITE)
        os.replace(pending, destination)
    finally:
        destination.chmod(permissions)
        if pending.exists():
            pending.unlink()

published = []
try:
    for name in changed:
        path = bundle if name == "V2.2.zip" else stage / name
        atomic_copy(path, live / name)
        published.append(name)
        assert digest(live / name) == digest(path), name
except BaseException:
    for name in reversed(published):
        atomic_copy(backup / name, live / name)
    raise

print("Published:", ", ".join(changed))
print("Verified 18 total pages, with Figure 3 and the start of the references on page 7")

