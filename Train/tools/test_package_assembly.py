import json
import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import package_assembly as p
import download_dataset as d
import download_assembly as delivery


class PackageTests(unittest.TestCase):
    def source(self,identifier,points):
        return {'modelId':identifier,'actualVoxelCount':len(points),
                'voxels':[{'x':x,'y':y,'z':z,'color':color} for x,y,z,color in points]}

    def test_public_archive_success_and_failure_are_independently_re_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);dataset=root/'dataset';run=root/'run';out=root/'export'
            policy=dict(world_dim=48,brick_library='extended',min_support_fraction=.1,
                        max_cantilever_distance=2,max_components=64,max_seconds=1,max_nodes=100,beam_width=2)
            p.a.initialize(dataset,run,policy)
            items=[]
            for identifier,points in (
                ('good',[(0,0,0,[0,0,0]),(1,0,0,[0,0,0])]),
                ('bad',[(0,0,0,[0,0,0]),(1,0,0,[255,0,0])])):
                source=self.source(identifier,points)
                _,cells=p.a.dataset_model(source)
                job=dict(modelId=identifier,category='test',modelSeed=1,
                         modelPath='models/test/'+identifier,
                         exactOccupancyHash=p.a.exact_hash(cells),canonicalGeometryHash='canonical')
                source_folder=dataset/job['modelPath']
                p.a.dump(source_folder/'model.json',source)
                prompts=[dict(modelId=identifier,recordId=identifier+'_l'+str(level),promptLevel=level,
                              targetOccupancyHash=job['exactOccupancyHash'],targetCanonicalGeometryHash='canonical')
                         for level in range(1,6)]
                p.a.dump(source_folder/'prompts.json',prompts)
                report=p.a.process(job)
                folder=run/job['modelPath']
                selection={'modelId':identifier,'status':report['status'],
                           'reportFileSha256':p.digest(folder/'report.json')}
                items.append(dict(job=job,selection=selection,folder=str(folder),sourceFolder=str(source_folder)))
            result=p.build_package(('A',1,items,str(out),'test-tag'))
            self.assertTrue(result['allPublicZipMemberCrcShaAndReadbackPassed'])
            self.assertEqual([r['geometryPassed'] for r in result['rows']],[True,False])
            self.assertEqual(result['promptRecordCount'],10)
            with zipfile.ZipFile(out/result['asset']['sourceRelativePath']) as archive:
                for row in result['rows']:
                    report=json.loads(archive.read(row['reportPath']))
                    self.assertEqual(report['sourceModelPath'],'source.model.json')
                    self.assertFalse(p.private_paths(report))
                    files={name:archive.read(row['resultPath']+'/'+name) for name in report['outputFileSha256']}
                    self.assertEqual(p.payload_audit(files)['passed'],row['geometryPassed'])
                good=result['rows'][0]
                report=json.loads(archive.read(good['reportPath']))
                files={name:archive.read(good['resultPath']+'/'+name) for name in report['outputFileSha256']}
                files['model.txt']=b'1x1 (0,0,0)\n'
                self.assertFalse(p.payload_audit(files)['passed'])
            self.assertEqual(p.build_package(('A',1,items,str(out),'test-tag')),result)

    def test_wrong_prompt_target_rejected(self):
        job=dict(modelId='one',exactOccupancyHash='right',canonicalGeometryHash='canonical')
        rows=[dict(modelId='one',recordId=str(i),promptLevel=i,targetOccupancyHash='wrong',
                   targetCanonicalGeometryHash='canonical') for i in range(1,6)]
        with self.assertRaises(ValueError):p.check_prompts(p.encode(rows),job)

    def test_private_paths_detected_without_rejecting_public_urls(self):
        self.assertTrue(p.private_paths({'nested':['D:\\private\\file.json']}))
        self.assertFalse(p.private_paths({'url':'https://github.com/x/y','path':'AI_A/models/one'}))

    def test_parallel_source_download_keeps_authoritative_metadata_last(self):
        manifest={'assets':[{'name':'p1.zip','kind':'model_package'},
                            {'name':'metadata.zip','kind':'metadata'},
                            {'name':'p2.zip','kind':'model_package'}], 'totalDownloadBytes':0}
        events=[]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(d,'get_manifest',return_value=manifest), \
                 patch.object(d,'download',side_effect=lambda asset,folder:folder/asset['name']), \
                 patch.object(d,'extract',side_effect=lambda path,*args:events.append(path.name)), \
                 patch.object(d,'verify_extracted',return_value={'complete':True}):
                self.assertEqual(d.run_shard('A',root,True,2),{'complete':True})
        self.assertEqual(events[-1],'metadata.zip')
        self.assertEqual(set(events[:-1]),{'p1.zip','p2.zip'})

    def test_public_download_index_paths_must_stay_inside_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('../escape','C:/escape','/escape','AI_A/../../escape'):
                with self.assertRaises(ValueError):delivery.inside(root,name)
            self.assertEqual(delivery.inside(root,'AI_A/models/one'),root/'AI_A/models/one')

    def test_truncated_download_resumes_and_still_checks_full_sha(self):
        data=b'complete-original-asset'
        class Response(io.BytesIO):
            def __init__(self,data,status,headers):
                super().__init__(data);self.status=status;self.headers=headers
        responses=[Response(data[:5],200,{}),Response(data[5:],206,{'Content-Range':'bytes 5-22/23'})]
        requests=[]
        def open_url(request,timeout):
            requests.append(request);return responses.pop(0)
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(d.urllib.request,'urlopen',side_effect=open_url), \
             patch.object(d.time,'sleep'):
            asset={'name':'asset.zip','bytes':len(data),'sha256':p.a.sha(data),'url':'https://example.test/asset'}
            result=d.download(asset,Path(temp))
            self.assertEqual(result.read_bytes(),data)
            self.assertEqual(requests[1].get_header('Range'),'bytes=5-')

    def test_full_size_wrong_sha_is_not_promoted_or_silently_retried(self):
        class Response(io.BytesIO):
            status=200
            headers={}
        data=b'wrong original bytes'
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(d.urllib.request,'urlopen',return_value=Response(data)) as open_url:
            root=Path(temp)
            asset={'name':'bad.zip','bytes':len(data),'sha256':'0'*64,'url':'https://example.test/bad'}
            with self.assertRaises(ValueError):d.download(asset,root)
            self.assertFalse((root/'bad.zip').exists())
            self.assertEqual((root/'bad.zip.part').read_bytes(),data)
            self.assertEqual(open_url.call_count,1)


if __name__=='__main__':unittest.main()
