"""Versioned local bridge / old-brick retiling entry point."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'algorithms/voxel_assembly_retile'))
from retile_pipeline import main
if __name__=='__main__':raise SystemExit(main())
