"""Independent exporters and physical audits for an exact regenerated source."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(HERE))
import strict_core
VERSION='quality_supported_piano_b_exact_delivery_v1'

def loader(selected=None):
    spec=importlib.util.spec_from_file_location('supported_piano_delivery',HERE.parent/'voxel_assembly_retile/retile_pipeline.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    prior=module.code_hashes
    def hashes():
        value=prior()
        for name in ('strict_core.py','pipeline.py','generate.py'):
            p=HERE/name;value[p.relative_to(REPO).as_posix()]=module.digest(p)
        for p in (HERE/'generator_snapshot').glob('*.py'):value[p.relative_to(REPO).as_posix()]=module.digest(p)
        return value
    def chosen(original,seconds=8.,baseline=None):
        if selected is None:return strict_core.optimize(original,seconds)
        if original!=selected['targetCells'] or not strict_core.retile.base.audit(selected['bricks'],original)['passed']:raise ValueError('Preselected exact layout does not match source')
        return selected
    module.VERSION=VERSION
    module.core=SimpleNamespace(**{**vars(strict_core.retile),'VERSION':strict_core.VERSION,'optimize':chosen})
    module.code_hashes=hashes
    return module

def run_one(source,out,seconds=8.,physics_seconds=5.,selected=None):return loader(selected).run_one(source,out,seconds,physics_seconds)
def verify(folder):return loader().verify(folder)
def code_hashes():return loader().code_hashes()
if __name__=='__main__':loader().main()
