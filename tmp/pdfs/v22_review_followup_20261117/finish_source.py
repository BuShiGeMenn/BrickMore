from pathlib import Path
import zipfile
import json
import re

job = Path(__file__).resolve().parent
stage = job / "source"
def replace(name, before, after):
    path = stage / name
    data = path.read_bytes()
    before, after = before.encode("utf-8"), after.encode("utf-8")
    assert data.count(before) == 1, (name, before)
    path.write_bytes(data.replace(before, after))

replace("main.tex",
        "Historical category-level geometric pass rates. Version and numerical labels require verification.",
        r"Geometric pass rates by category for the Strict v3, Relaxed, and Refined releases summarized in Table~\ref{tab:conversion}. The Refined bars use the October 13 release.")
replace("intro-xiao.tex",
        "Where should the geometric knowledge needed to answer concise requests come from? Can LLM-assisted programs encode object proportions and part structure in a form that can be inspected and used to train a compact model?",
        "Can LLM-assisted programs encode the geometric details omitted from concise prompts in a form suitable for training a compact model?")
replace("README.md",
        "The historical category chart has no per-bar data file attached to the figure, and the comparison tables contain missing results and literature entries without a common protocol. These materials remain in the project and in the draft for the author to review.",
        "The historical category chart was checked against the three release summaries at the precision of the plotted image. The historical comparison tables contain missing results and literature entries without a common protocol. The draft retains those tables for author review.")

