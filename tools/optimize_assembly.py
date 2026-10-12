"""Entry point for the additive, <=2% geometry-repair optimization lane."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'algorithms'/'voxel_assembly_q2'))
from quality_pipeline import main

if __name__=='__main__':raise SystemExit(main())
