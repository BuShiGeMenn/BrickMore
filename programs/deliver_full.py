"""Complete required whole-shard checks, repair new models if needed, then package."""
import json,subprocess,sys,time,os
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
def run(name,*args):
    print('STAGE',name,flush=True)
    return subprocess.run([sys.executable,'-u',str(ROOT/'programs'/name),*args],env=dict(os.environ,PYTHONUTF8='1')).returncode

def main():
    print('Waiting for complete geometry and record aggregation',flush=True)
    while True:
        path=ROOT/'generation_status.json'
        if path.exists():
            try:
                status=json.loads(path.read_text(encoding='utf-8'))
                if status.get('completedModelCount')==40000 and status.get('completedPromptRecordCount')==200000:break
            except (OSError,json.JSONDecodeError):pass
        time.sleep(1)
    for iteration in range(1,9):
        assert run('review_full.py','--workers','10')==0
        structural=json.loads((ROOT/'structural_review.json').read_text(encoding='utf-8'))
        assert not structural['familyReviewPairs'],'Measured family partition needs review'
        if structural['nearDuplicateCandidates']:
            assert run('repair_remaining.py')==0;continue
        result=run('verify.py','--workers','12')
        if result==0:break
        verification=json.loads((ROOT/'independent_verification.json').read_text(encoding='utf-8'))
        assert all('modelId' in e for e in verification['errors']),'Aggregate or global verification error requires correction'
        assert run('repair_remaining.py')==0
    else:raise RuntimeError('Whole-shard repair iterations exhausted without a complete verified result')
    assert run('finish_full.py')==0
    print('AI_A COMPLETE: 40000 models / 200000 bilingual records / 40 model packages',flush=True)

if __name__=='__main__':main()
