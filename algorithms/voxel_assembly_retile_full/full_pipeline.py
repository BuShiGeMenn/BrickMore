"""Versioned exporter using the existing independent auditors without mutation."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'voxel_assembly_retile'))
import full_core
import retile_core

spec=importlib.util.spec_from_file_location('fresh_retile_delivery_base',HERE.parent/'voxel_assembly_retile'/'retile_pipeline.py')
delivery=importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)
_original_hashes=delivery.code_hashes
_original_target=delivery.target_value

VERSION='quality_fresh_local_bridge_retile_delivery_v2'

def code_hashes():
    result=_original_hashes()
    for path in (HERE/'full_core.py',HERE/'full_pipeline.py'):
        result[path.relative_to(REPO).as_posix()]=delivery.digest(path)
    return result

def target_value(source,cells,repair):
    target=_original_target(source,cells,repair)
    if target['derivedGeometry']:target['modelId']=target['modelId'].replace('_q6_','_q7_')
    return target

delivery.VERSION=VERSION
delivery.core=SimpleNamespace(**{**vars(retile_core),'VERSION':full_core.VERSION,'optimize':full_core.optimize})
delivery.code_hashes=code_hashes
delivery.target_value=target_value
run_one=delivery.run_one
verify=delivery.verify
read_baseline=delivery.read_baseline
digest=delivery.digest
dump=delivery.dump
base=retile_core.base

if __name__=='__main__':delivery.main()
