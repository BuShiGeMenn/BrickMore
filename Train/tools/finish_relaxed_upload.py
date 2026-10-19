"""Finish one verified BrickMore census release; retry only owned draft placeholders."""
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime,timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

import github_release as gh

VERSION='verified_census_upload_recovery_v1'
REPOSITORY_URL='https://github.com/BuShiGeMenn/BrickMore.git'
TAG='lego-modular-grounded-ab-80000-20261012-v1'
RELEASE_ID=410611865
SOURCE_FILES=('tools/finish_relaxed_upload.py','tools/test_finish_relaxed_upload.py','tools/github_release.py')
TEST_REPORT='datasets/relaxed_assembly_80000/upload_recovery_tests.json'
PROOF_FILE='datasets/relaxed_assembly_80000/release_verification.json'


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(path)


def now():return datetime.now(timezone.utc).isoformat()


def lock(out):
    handle=(out/'run.lock').open('a+b')
    if os.name=='nt':
        import msvcrt
        handle.seek(0)
        try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:handle.close();raise RuntimeError('another census/upload process owns the run lock')
    else:
        import fcntl
        fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    return handle


def git(workspace,*args):
    return subprocess.check_output(['git','-c','http.proxy=','-c','https.proxy=',*args],cwd=workspace,text=True).strip()


def git_guard(workspace,commit,network=True):
    if git(workspace,'remote','get-url','origin')!=REPOSITORY_URL or git(workspace,'symbolic-ref','--short','HEAD')!='main':raise ValueError('authorized repository/branch changed')
    if git(workspace,'rev-parse','HEAD')!=commit or git(workspace,'diff','--cached','--name-only'):raise ValueError('user Git HEAD/index changed; no automatic reset or merge')
    if network and git(workspace,'ls-remote',REPOSITORY_URL,'refs/heads/main').split()[0]!=commit:raise ValueError('remote main changed; no force push')


def local_inputs(out):
    out=out.resolve();parent=json.loads((out/'plan.json').read_bytes());workspace=Path(parent['workspace']).resolve()
    if Path(parent['out']).resolve()!=out or not out.is_relative_to(workspace/'downloads') or out==workspace/'downloads':raise ValueError('invalid scoped census output')
    manifest=json.loads((out/'delivery/download_manifest.json').read_bytes());summary=json.loads((out/'full_verification.json').read_bytes())
    public=workspace/'datasets/relaxed_assembly_80000'
    if json.loads((public/'download_manifest.json').read_bytes())!=manifest or json.loads((public/'assembly_summary.json').read_bytes())!=summary:raise ValueError('public and sealed census metadata differ')
    if manifest['repository']!='BuShiGeMenn/BrickMore' or manifest['releaseTag']!=TAG or manifest['modelCount']!=80000 or manifest['promptRecordCount']!=400000 or manifest['assetCount']!=81 or len(manifest['assets'])!=81:raise ValueError('refuse incomplete/unrelated release manifest')
    if summary['processedModelCount']!=80000 or summary['remainingModelCount'] or not summary['allPublicZipCrcShaGeometryRepairGateAndPhysicsReadbackPassed'] or summary['runPlanSha256']!=digest(out/'plan.json'):raise ValueError('refuse upload before full census readback')
    if len({a['name'] for a in manifest['assets']})!=81:raise ValueError('duplicate asset name')
    for name,sha in parent['runtimeSourceCodeSha256'].items():
        if digest(out/'source_snapshot'/name)!=sha:raise ValueError('original frozen runtime changed')
    for asset in manifest['assets']:
        if Path(asset['name']).name!=asset['name'] or asset['sourceRelativePath']!='packages/'+asset['name'] or asset['url']!=f'https://github.com/BuShiGeMenn/BrickMore/releases/download/{TAG}/{asset["name"]}':raise ValueError('unsafe asset source/name/download path')
        path=out/'delivery'/asset['sourceRelativePath']
        if path.stat().st_size!=asset['bytes'] or digest(path)!=asset['sha256']:raise ValueError('sealed local asset differs: '+asset['name'])
    if sum(a['kind']=='assembly_package' and a['modelCount']==1000 and a['promptRecordCount']==5000 for a in manifest['assets'])!=80 or sum(a['kind']=='metadata' for a in manifest['assets'])!=1:raise ValueError('80 model packages and one metadata package required')
    commit=json.loads((out/'publication_commit.json').read_bytes())['commit']
    return workspace,parent,manifest,summary,commit


class Transport:
    def __init__(self,token):self.token=token
    def request(self,url,method='GET',value=None,stream=None,size=None):
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or parsed.hostname not in ('api.github.com','uploads.github.com'):raise ValueError('authenticated host rejected')
        headers={'Authorization':'Bearer '+self.token,'User-Agent':'BrickMore-verified-upload-recovery','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
        data=json.dumps(value).encode('utf8') if value is not None else stream
        if stream is not None:headers.update({'Content-Type':'application/octet-stream','Content-Length':str(size)})
        elif data is not None:headers['Content-Type']='application/json'
        request=urllib.request.Request(url,data=data,headers=headers,method=method)
        with urllib.request.urlopen(request,timeout=300 if stream is not None else 30) as response:
            return None if response.status==204 else json.load(response)
    def release(self):return self.request(gh.API+f'/releases/{RELEASE_ID}')
    def assets(self):
        result=[];page=1
        while True:
            batch=self.request(gh.API+f'/releases/{RELEASE_ID}/assets?per_page=100&page={page}');result.extend(batch)
            if len(batch)<100:return result
            page+=1


def release_guard(release):
    if release['id']!=RELEASE_ID or release['tag_name']!=TAG or release['url']!=gh.API+f'/releases/{RELEASE_ID}':raise ValueError('unrelated release; refuse mutation')
    upload=urllib.parse.urlsplit(release['upload_url'].split('{',1)[0])
    if upload.scheme!='https' or upload.netloc!='uploads.github.com' or upload.path!=f'/repos/BuShiGeMenn/BrickMore/releases/{RELEASE_ID}/assets':raise ValueError('unrelated upload endpoint')


def remote_inventory(rows,expected):
    if len({r['name'] for r in rows})!=len(rows) or any(r['name'] not in expected for r in rows):raise ValueError('unexpected/duplicate target asset; preserve and stop')
    return {r['name']:r for r in rows}


def partial_guard(release,row,expected):
    """Only unpublished, hash-less, exact-name placeholders are recoverable."""
    release_guard(release)
    if not release['draft'] or row['name']!=expected['name'] or row.get('state')!='starter' or row.get('digest') is not None:
        raise ValueError('not an owned incomplete draft placeholder; refuse deletion')
    if type(row.get('size')) is not int or not 0<=row['size']<=expected['bytes'] or row.get('url')!=gh.API+'/releases/assets/'+str(row['id']):raise ValueError('partial asset identity/size differs')
    updated=datetime.fromisoformat(row['updated_at'].replace('Z','+00:00'))
    if datetime.now(timezone.utc).timestamp()-updated.timestamp()<30:raise BlockingIOError('new placeholder may still be processing')


def publish_guard(rows,manifest):
    expected={a['name']:a for a in manifest['assets']};remote=remote_inventory(rows,expected)
    if len(expected)!=81 or set(remote)!=set(expected) or any(not gh.matches(remote[n],a) for n,a in expected.items()):raise ValueError('81 exact remote sizes/SHA required before publishing')
    return remote


def original_releases(transport,workspace,parent):
    for name,sha in parent['originalReleaseManifestSha256'].items():
        path=workspace/name
        if digest(path)!=sha:raise ValueError('original manifest changed')
        manifest=json.loads(path.read_bytes());tag=urllib.parse.quote(manifest['releaseTag'],safe='')
        release=transport.request(gh.API+'/releases/tags/'+tag)
        if release['draft']:raise ValueError('original release is no longer public')
        rows=[];page=1
        while True:
            batch=transport.request(gh.API+f'/releases/{release["id"]}/assets?per_page=100&page={page}');rows.extend(batch)
            if len(batch)<100:break
            page+=1
        expected={r['name']:r for r in manifest['assets']};actual={r['name']:r for r in rows}
        if len(actual)!=len(rows) or set(actual)!=set(expected) or any(not gh.matches(actual[n],r) for n,r in expected.items()):raise ValueError('original release inventory/SHA changed')
    return True


class ProgressStream:
    def __init__(self,stream,callback):self.stream=stream;self.callback=callback;self.sent=0
    def read(self,size=-1):
        chunk=self.stream.read(size);self.sent+=len(chunk);self.callback(self.sent);return chunk


class Uploader:
    def __init__(self,transport,out,manifest,summary,plan):
        self.transport=transport;self.out=out;self.manifest=manifest;self.summary=summary;self.plan=plan
        self.expected={a['name']:a for a in manifest['assets']};self.mutex=threading.RLock();self.verified=set();self.active={};self.errors={}
        journal_path=out/'upload_recovery_journal.json'
        self.journal=json.loads(journal_path.read_bytes()) if journal_path.exists() else {'version':VERSION,'releaseId':RELEASE_ID,'events':[]}
        if self.journal['version']!=VERSION or self.journal['releaseId']!=RELEASE_ID:raise ValueError('recovery journal differs')
    def event(self,kind,**data):
        with self.mutex:
            self.journal['events'].append({'kind':kind,'atUtc':now(),**data});atomic_json(self.out/'upload_recovery_journal.json',self.journal)
    def status(self,phase='uploading_recovery',**extra):
        with self.mutex:
            s=self.summary
            atomic_json(self.out/'status.json',{'workflowVersion':VERSION,'phase':phase,'modelCount':80000,'processedModelCount':80000,
                'geometryPassed':s['geometryPassed'],'gravityScreenedPassed':s['gravityScreenedPassed'],'statusCounts':s['statusCounts'],
                'geometryTier':s['geometryTier'],'releaseTag':TAG,'releaseId':RELEASE_ID,'deadlineUtc':self.plan['deadlineUtc'],
                'updatedAtUtc':now(),'pid':os.getpid(),'verifiedAssetCount':len(self.verified),'expectedAssetCount':81,
                'remainingAssetCount':81-len(self.verified),'activeUploads':self.active.copy(),'uploadErrors':self.errors.copy(),**extra})
    def reconcile(self):
        remote=remote_inventory(self.transport.assets(),self.expected)
        with self.mutex:self.verified={n for n,r in remote.items() if gh.matches(r,self.expected[n])}
        self.status();return remote
    def cleanup(self,row,asset):
        # Re-fetch both release and asset immediately before the scoped DELETE.
        release=self.transport.release();fresh=self.transport.request(gh.API+'/releases/assets/'+str(row['id']))
        if gh.matches(fresh,asset):return True
        if fresh['id']!=row['id']:raise ValueError('placeholder asset ID changed')
        partial_guard(release,fresh,asset)
        self.event('incomplete_placeholder_removal_planned',assetId=fresh['id'],name=fresh['name'],state=fresh['state'],bytes=fresh['size'],localSha256=asset['sha256'])
        self.transport.request(gh.API+'/releases/assets/'+str(fresh['id']),'DELETE')
        self.event('incomplete_placeholder_removed',assetId=fresh['id'],name=fresh['name'],localSha256=asset['sha256'])
        return False
    def sent(self,name,count):
        with self.mutex:
            if name in self.active:self.active[name]['sentBytes']=count
    def upload_one(self,asset):
        name=asset['name'];path=self.out/'delivery'/asset['sourceRelativePath']
        for attempt in range(1,5):
            try:
                release=self.transport.release();release_guard(release)
                remote=remote_inventory(self.transport.assets(),self.expected);existing=remote.get(name)
                if existing and gh.matches(existing,asset):return name,None
                if not release['draft']:raise ValueError('published release incomplete; refuse mutation')
                if existing:
                    if self.cleanup(existing,asset):return name,None
                if path.stat().st_size!=asset['bytes'] or digest(path)!=asset['sha256']:raise ValueError('local bytes changed before upload')
                with self.mutex:self.active[name]={'attempt':attempt,'sentBytes':0,'totalBytes':asset['bytes'],'startedAtUtc':now()}
                self.event('upload_attempt_started',name=name,attempt=attempt,bytes=asset['bytes'],sha256=asset['sha256'])
                url=release['upload_url'].split('{',1)[0]+'?'+urllib.parse.urlencode({'name':name})
                with path.open('rb') as stream:
                    uploaded=self.transport.request(url,'POST',stream=ProgressStream(stream,lambda count:self.sent(name,count)),size=asset['bytes'])
                if gh.matches(uploaded,asset):return name,None
                # A response may precede final SHA calculation; verify real API state.
                for _ in range(3):
                    time.sleep(10);remote=remote_inventory(self.transport.assets(),self.expected)
                    if name in remote and gh.matches(remote[name],asset):return name,None
                raise OSError('upload response not yet size/SHA verified')
            except (OSError,urllib.error.URLError) as error:
                self.event('upload_retry',name=name,attempt=attempt,errorType=type(error).__name__,error=str(error))
                # Lost responses never justify reuploading/deleting a complete asset.
                try:
                    remote=remote_inventory(self.transport.assets(),self.expected)
                    if name in remote and gh.matches(remote[name],asset):return name,None
                except (OSError,urllib.error.URLError):pass
                if attempt==4:return name,str(error)
                time.sleep(min(15,5*attempt))
            except Exception as error:
                self.event('upload_conflict_preserved',name=name,errorType=type(error).__name__,error=str(error));return name,str(error)
            finally:
                with self.mutex:self.active.pop(name,None)
        return name,'upload attempts exhausted'
    def upload(self,workers):
        remote=self.reconcile();missing=[a for a in self.manifest['assets'] if a['name'] not in remote or not gh.matches(remote[a['name']],a)]
        print('REMOTE_VERIFIED_INITIAL',len(self.verified),'/81',flush=True)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending={pool.submit(self.upload_one,a) for a in missing}
            while pending:
                done,pending=wait(pending,timeout=15,return_when=FIRST_COMPLETED)
                for future in done:
                    name,error=future.result()
                    with self.mutex:
                        if error:self.errors[name]=error
                        else:self.verified.add(name);self.errors.pop(name,None)
                    print('UPLOAD_RECOVERY',len(self.verified),'/81',name,'verified' if error is None else 'failed: '+error,flush=True)
                self.status()
        remote=self.reconcile()
        if self.errors:raise RuntimeError('some uploads need attention: '+json.dumps(self.errors,ensure_ascii=False))
        return publish_guard(list(remote.values()),self.manifest)


def prepare(out,workers):
    workspace,parent,manifest,summary,commit=local_inputs(out);git_guard(workspace,commit,network=False)
    report=json.loads((workspace/TEST_REPORT).read_bytes())
    sources={name:digest(workspace/name) for name in SOURCE_FILES}
    if not report['passed'] or report['sourceCodeSha256']!=sources:raise ValueError('matching successful upload recovery tests required')
    target=out/'upload_recovery_source';plan_path=out/'upload_recovery_plan.json'
    if target.exists() or plan_path.exists():raise ValueError('upload recovery freeze already exists; do not overwrite')
    plan={'version':VERSION,'workspace':str(workspace),'out':str(out.resolve()),'releaseId':RELEASE_ID,'releaseTag':TAG,'workers':workers,
          'parentPlanSha256':digest(out/'plan.json'),'manifestSha256':digest(out/'delivery/download_manifest.json'),
          'fullVerificationSha256':digest(out/'full_verification.json'),'publicationCommit':commit,'sourceCodeSha256':sources,
          'testReportSha256':digest(workspace/TEST_REPORT),'startedAtUtc':now(),
          'policy':'keep every uploaded size/SHA match; remove only exact-name hash-less starter placeholders on this owned draft; never modify models or old releases'}
    for name,sha in sources.items():
        destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(workspace/name,destination)
        if digest(destination)!=sha:raise ValueError('upload source freeze differs')
    atomic_json(plan_path,plan);print('UPLOAD_RECOVERY_FROZEN',81,'assets;',workers,'workers',flush=True)


def run(out):
    recovery=json.loads((out/'upload_recovery_plan.json').read_bytes());workspace,parent,manifest,summary,commit=local_inputs(out)
    if Path(__file__).resolve().parent.parent!=(out/'upload_recovery_source').resolve() or recovery['version']!=VERSION or recovery['publicationCommit']!=commit or Path(recovery['workspace'])!=workspace or Path(recovery['out'])!=out.resolve():raise ValueError('use exact frozen upload recovery identity')
    for name,sha in recovery['sourceCodeSha256'].items():
        if digest(out/'upload_recovery_source'/name)!=sha or digest(workspace/name)!=sha:raise ValueError('upload recovery source changed')
    for name,field in (('plan.json','parentPlanSha256'),('delivery/download_manifest.json','manifestSha256'),('full_verification.json','fullVerificationSha256')):
        if digest(out/name)!=recovery[field]:raise ValueError('sealed upload inputs changed')
    if digest(workspace/TEST_REPORT)!=recovery['testReportSha256']:raise ValueError('test report changed')
    handle=lock(out);uploader=None
    try:
        gh.ROOT=workspace;transport=Transport(gh.credential())
        uploader=Uploader(transport,out,manifest,summary,parent);uploader.status('checking_upload_inputs')
        git_guard(workspace,commit);original_releases(transport,workspace,parent);release=transport.release();release_guard(release)
        remote=uploader.upload(recovery['workers'])
        # No publication before all 81 real remote sizes/digests are confirmed.
        uploader.status('publishing');release=transport.release();release_guard(release)
        if release['draft']:release=transport.request(gh.API+f'/releases/{RELEASE_ID}','PATCH',{'draft':False,'make_latest':'false','target_commitish':commit})
        release_guard(release);remote=publish_guard(transport.assets(),manifest)
        if release['draft'] or any(remote[a['name']]['browser_download_url']!=a['url'] for a in manifest['assets']):raise ValueError('published asset URLs/status differ')
        original_releases(transport,workspace,parent)
        removals=[e for e in uploader.journal['events'] if e['kind']=='incomplete_placeholder_removed']
        proof={'published':True,'releaseTag':TAG,'releaseUrl':release['html_url'],'modelCount':80000,'promptRecordCount':400000,'assetCount':81,
               'allRemoteAssetSizesAndSha256Passed':True,'originalAReleaseUnchanged':True,'originalBReleaseUnchanged':True,'originalAssemblyReleaseUnchanged':True,
               'geometryPassed':summary['geometryPassed'],'geometryPassRate':summary['geometryPassRate'],'gravityScreenedPassed':summary['gravityScreenedPassed'],
               'fullPhysics':False,'staticVerified':None,'publicationCommit':commit,'uploadRecoveryVersion':VERSION,
               'uploadRecoverySourceCodeSha256':recovery['sourceCodeSha256'],'incompletePlaceholdersRemoved':removals,'verifiedAtUtc':now(),
               'assets':[{'name':a['name'],'bytes':remote[a['name']]['size'],'sha256':remote[a['name']]['digest'].removeprefix('sha256:'),'url':remote[a['name']]['browser_download_url']} for a in manifest['assets']]}
        atomic_json(workspace/PROOF_FILE,proof)
        uploader.status('published_proof_pending_git',releaseUrl=proof['releaseUrl'],allRemoteAssetSizesAndSha256Passed=True)
        git_guard(workspace,commit)
        files=list(SOURCE_FILES[:2])+[TEST_REPORT,PROOF_FILE]
        expected={n:digest(workspace/n) for n in files}
        subprocess.run(['git','add','--',*files],cwd=workspace,check=True)
        subprocess.run(['git','commit','--only','-m','上传校验：完成全部80000模型资源，保留已上传包并恢复未完成条目','--',*files],cwd=workspace,check=True)
        new_commit=git(workspace,'rev-parse','HEAD')
        for name,sha in expected.items():
            raw=(workspace/name).read_bytes();blob=subprocess.check_output(['git','show',new_commit+':'+name],cwd=workspace)
            if digest(workspace/name)!=sha or raw.replace(b'\r\n',b'\n')!=blob.replace(b'\r\n',b'\n'):raise ValueError('proof source changed during commit')
        subprocess.run(['git','-c','http.proxy=','-c','https.proxy=','push',REPOSITORY_URL,'HEAD:main'],cwd=workspace,check=True)
        if git(workspace,'ls-remote',REPOSITORY_URL,'refs/heads/main').split()[0]!=new_commit:raise ValueError('pushed proof not visible')
        uploader.status('complete',releaseUrl=proof['releaseUrl'],allRemoteAssetSizesAndSha256Passed=True,proofCommit=new_commit,
                        finishedBeforeDeadline=time.time()<=parent['deadlineEpoch'],incompletePlaceholderRemovalCount=len(removals))
        print('ALL_80000_MODELS_PUBLISHED',proof['releaseUrl'],'81/81 SHA verified',flush=True)
    except BaseException as error:
        if uploader:uploader.status('needs_attention',errorType=type(error).__name__,error=str(error),checkpointsPreserved=True)
        traceback.print_exc();raise
    finally:handle.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('init','run'));parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=2);args=parser.parse_args();out=args.out.resolve()
    if not 1<=args.workers<=3:parser.error('workers must be 1..3')
    if args.action=='init':
        handle=lock(out)
        try:prepare(out,args.workers)
        finally:handle.close()
    else:run(out)


if __name__=='__main__':main()
