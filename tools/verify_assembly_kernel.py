"""Compare the frozen B and current A geometry kernels without executing source."""
import argparse
import ast
import json
from pathlib import Path
import package_assembly as p

METHODS=('dataset_model','feasibility','independent_audit','parse_ldr',
         'exported_audit','greedy','process','verify_job')


def functions(path):
    tree=ast.parse(path.read_bytes())
    return {n.name:p.a.sha(ast.dump(n,include_attributes=False).encode('utf8'))
            for n in tree.body if isinstance(n,ast.FunctionDef)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy',type=Path,required=True)
    parser.add_argument('--legacy-config',type=Path,required=True)
    parser.add_argument('--current-config',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    current=Path(p.a.__file__)
    left=functions(args.legacy);right=functions(current)
    old=json.loads(args.legacy_config.read_bytes());new=json.loads(args.current_config.read_bytes())
    if p.digest(args.legacy)!=old['sourceCodeSha256'] or p.digest(current)!=new['sourceCodeSha256']:
        raise ValueError('runner bytes differ from frozen processing configurations')
    toolkit={name:p.digest(p.a.SNAPSHOT/name) for name in p.a.TOOLKIT_FILES}
    same={name:left[name]==right[name] for name in METHODS}
    if not all(same.values()) or old['policy']!=new['policy'] or old['toolkitSourceSha256']!=toolkit or new['toolkitSourceSha256']!=toolkit:
        raise ValueError('legacy/current geometry kernels or policies differ')
    report={'passed':True,'legacyAlgorithmVersion':old['algorithmVersion'],
            'currentAlgorithmVersion':new['algorithmVersion'],
            'legacyRunnerSha256':p.digest(args.legacy),'currentRunnerSha256':p.digest(current),
            'equivalentMethodAstSha256':{name:right[name] for name in METHODS},
            'identicalFrozenPolicy':old['policy'],'identicalToolkitSourceSha256':toolkit,
            'scope':'Geometry, RGB/axis adapter, feasibility and actual export readback unchanged; v3 adds original A/B manifest compatibility',
            'fullPhysics':False}
    p.a.dump(args.out,report)
    print('FROZEN_ASSEMBLY_KERNEL_EQUIVALENCE_VERIFIED',flush=True)


if __name__=='__main__':main()
