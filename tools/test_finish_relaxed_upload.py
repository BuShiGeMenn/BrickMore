"""Offline regressions for exact-scope partial recovery and full-release guards."""
from datetime import datetime,timezone,timedelta
from pathlib import Path
import copy
import hashlib
import io
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error

import finish_relaxed_upload as f


def release():
    return {'id':f.RELEASE_ID,'tag_name':f.TAG,'draft':True,'url':f.gh.API+f'/releases/{f.RELEASE_ID}',
            'upload_url':f'https://uploads.github.com/repos/BuShiGeMenn/BrickMore/releases/{f.RELEASE_ID}/assets{{?name,label}}'}


def asset(name='fixture.zip',data=b'fixture model package'):
    return {'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'sourceRelativePath':'packages/'+name,
            'url':f'https://github.com/BuShiGeMenn/BrickMore/releases/download/{f.TAG}/{name}'}


def remote(a,identifier=17,state='uploaded'):
    return {'id':identifier,'name':a['name'],'size':a['bytes'],'state':state,
            'digest':'sha256:'+a['sha256'] if state=='uploaded' else None,
            'url':f.gh.API+'/releases/assets/'+str(identifier),'browser_download_url':a['url'],
            'updated_at':(datetime.now(timezone.utc)-timedelta(seconds=100)).isoformat()}


class FakeTransport:
    def __init__(self,expected,rows=(),lose_response=False,first_partial=False):
        self.expected={a['name']:a for a in expected};self.rows={r['name']:copy.deepcopy(r) for r in rows}
        self.calls=[];self.posts=0;self.lose_response=lose_response;self.first_partial=first_partial;self.mutex=threading.RLock()
    def release(self):return release()
    def assets(self):
        with self.mutex:return copy.deepcopy(list(self.rows.values()))
    def request(self,url,method='GET',value=None,stream=None,size=None):
        with self.mutex:
            self.calls.append((method,url))
            if method=='GET':return copy.deepcopy(next(r for r in self.rows.values() if r['url']==url))
            if method=='DELETE':
                name=next(n for n,r in self.rows.items() if r['url']==url);del self.rows[name];return None
            if method=='POST':
                self.posts+=1;name=f.urllib.parse.parse_qs(f.urllib.parse.urlsplit(url).query)['name'][0];a=self.expected[name]
                data=b''
                while True:
                    part=stream.read(7)
                    if not part:break
                    data+=part
                if len(data)!=size or hashlib.sha256(data).hexdigest()!=a['sha256']:raise ValueError('wrong streamed bytes')
                row=remote(a,100+self.posts,'starter' if self.first_partial and self.posts==1 else 'uploaded');self.rows[name]=row
                if self.lose_response or self.first_partial and self.posts==1:raise urllib.error.URLError('response lost after send')
                return copy.deepcopy(row)
            raise AssertionError(method)


class UploadRecoveryTests(unittest.TestCase):
    def fixture(self,root,a=None,rows=(),**kw):
        a=a or asset();out=root/'run';path=out/'delivery'/a['sourceRelativePath'];path.parent.mkdir(parents=True)
        path.write_bytes(b'fixture model package')
        transport=FakeTransport([a],rows,**kw)
        summary={'geometryPassed':65503,'gravityScreenedPassed':478,'statusCounts':{'success':65503,'draft':14497},'geometryTier':'relaxed_modular_grounded_not_physical_certification'}
        uploader=f.Uploader(transport,out,{'assets':[a]},summary,{'deadlineUtc':'2026-10-12T14:09:29Z'})
        return a,transport,uploader

    def test_exact_owned_draft_placeholder_is_recoverable(self):
        a=asset();f.partial_guard(release(),remote(a,state='starter'),a)

    def test_uploaded_asset_never_deleted(self):
        a=asset()
        with self.assertRaises(ValueError):f.partial_guard(release(),remote(a),a)

    def test_published_release_never_mutated_for_partial_recovery(self):
        a=asset();r=release();r['draft']=False
        with self.assertRaises(ValueError):f.partial_guard(r,remote(a,state='starter'),a)

    def test_other_release_id_tag_or_upload_host_rejected(self):
        for key,value in (('id',1),('tag_name','another-tag'),('upload_url','https://evil.example/upload')):
            r=release();r[key]=value
            with self.assertRaises(ValueError):f.release_guard(r)

    def test_other_asset_name_or_id_endpoint_rejected(self):
        a=asset();r=remote(a,state='starter');r['name']='other.zip'
        with self.assertRaises(ValueError):f.partial_guard(release(),r,a)
        r=remote(a,state='starter');r['url']=f.gh.API+'/releases/assets/999'
        with self.assertRaises(ValueError):f.partial_guard(release(),r,a)

    def test_digest_present_or_oversize_placeholder_is_preserved(self):
        a=asset()
        for key,value in (('digest','sha256:unknown'),('size',a['bytes']+1),('size',-1)):
            r=remote(a,state='starter');r[key]=value
            with self.assertRaises(ValueError):f.partial_guard(release(),r,a)

    def test_recent_placeholder_is_not_immediately_deleted(self):
        a=asset();r=remote(a,state='starter');r['updated_at']=datetime.now(timezone.utc).isoformat()
        with self.assertRaises(BlockingIOError):f.partial_guard(release(),r,a)

    def test_unknown_and_duplicate_inventory_rejected(self):
        a=asset()
        with self.assertRaises(ValueError):f.remote_inventory([remote(asset('other.zip'))],{a['name']:a})
        with self.assertRaises(ValueError):f.remote_inventory([remote(a),remote(a)],{a['name']:a})

    def test_full_81_exact_sizes_and_sha_required_for_publication(self):
        expected=[asset(f'fixture_{i:02d}.zip') for i in range(81)];rows=[remote(a,i+1) for i,a in enumerate(expected)]
        manifest={'assets':expected};self.assertEqual(len(f.publish_guard(rows,manifest)),81)
        with self.assertRaises(ValueError):f.publish_guard(rows[:-1],manifest)
        rows[-1]['digest']='sha256:wrong'
        with self.assertRaises(ValueError):f.publish_guard(rows,manifest)

    def test_complete_asset_is_reused_without_any_post_or_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=asset();a,t,u=self.fixture(Path(tmp),a,[remote(a)])
            self.assertEqual(u.upload_one(a),(a['name'],None));self.assertFalse(any(method in ('POST','DELETE') for method,_ in t.calls))

    def test_cleanup_rechecks_asset_and_preserves_it_if_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=asset();a,t,u=self.fixture(Path(tmp),a,[remote(a)])
            self.assertTrue(u.cleanup(remote(a,state='starter'),a));self.assertFalse(any(method=='DELETE' for method,_ in t.calls))

    def test_partial_cleanup_is_journaled_and_local_model_bytes_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=asset();a,t,u=self.fixture(Path(tmp),a,[remote(a,state='starter')]);path=u.out/'delivery'/a['sourceRelativePath'];before=path.read_bytes()
            self.assertEqual(u.upload_one(a),(a['name'],None));self.assertEqual(path.read_bytes(),before)
            self.assertEqual(sum(method=='DELETE' for method,_ in t.calls),1);self.assertEqual(t.posts,1)
            events=u.journal['events'];self.assertEqual(events[0]['kind'],'incomplete_placeholder_removal_planned')
            self.assertEqual(events[1]['kind'],'incomplete_placeholder_removed');self.assertEqual(events[1]['localSha256'],a['sha256'])

    def test_wrong_uploaded_digest_is_preserved_and_returns_visible_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=asset();r=remote(a);r['digest']='sha256:wrong';a,t,u=self.fixture(Path(tmp),a,[r])
            name,error=u.upload_one(a);self.assertEqual(name,a['name']);self.assertIsNotNone(error)
            self.assertFalse(any(method in ('POST','DELETE') for method,_ in t.calls));self.assertTrue(any(e['kind']=='upload_conflict_preserved' for e in u.journal['events']))

    def test_lost_response_reuses_server_sha_without_duplicate_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,u=self.fixture(Path(tmp),lose_response=True)
            self.assertEqual(u.upload_one(a),(a['name'],None));self.assertEqual(t.posts,1);self.assertFalse(any(method=='DELETE' for method,_ in t.calls))

    def test_partial_failed_upload_is_safely_removed_and_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,u=self.fixture(Path(tmp),first_partial=True)
            with patch.object(f.time,'sleep',return_value=None):self.assertEqual(u.upload_one(a),(a['name'],None))
            self.assertEqual(t.posts,2);self.assertEqual(sum(method=='DELETE' for method,_ in t.calls),1)

    def test_progress_stream_counts_real_read_bytes(self):
        calls=[];stream=f.ProgressStream(io.BytesIO(b'0123456789'),calls.append)
        self.assertEqual(stream.read(4),b'0123');self.assertEqual(stream.read(9),b'456789');self.assertEqual(calls,[4,10])

    def test_authenticated_request_rejects_other_hosts_before_network(self):
        transport=f.Transport('dummy')
        with patch.object(f.urllib.request,'urlopen') as opener:
            with self.assertRaises(ValueError):transport.request('https://evil.example/')
            opener.assert_not_called()

    def test_visible_errors_do_not_stop_other_queued_uploads(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,t,u=self.fixture(Path(tmp));other=asset('other.zip');u.manifest['assets'].append(other);u.expected[other['name']]=other
            with patch.object(u,'upload_one',side_effect=lambda row:(row['name'],'error' if row['name']==a['name'] else None)) as send:
                with self.assertRaises(RuntimeError):u.upload(2)
            self.assertEqual(send.call_count,2);self.assertIn(a['name'],u.errors)
            status=json.loads((u.out/'status.json').read_bytes());self.assertIn(a['name'],status['uploadErrors'])


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(UploadRecoveryTests))
    workspace=Path(__file__).resolve().parent.parent
    f.atomic_json(workspace/f.TEST_REPORT,{'passed':result.wasSuccessful(),'testCount':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                                        'version':f.VERSION,'sourceCodeSha256':{name:f.digest(workspace/name) for name in f.SOURCE_FILES}})
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
