"""Verify transfer-host downloads before any offline pip install."""
import argparse,json
from pathlib import Path
from common import sha

def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    if (a.folder/'wheel_manifest.json').exists():
        items=json.loads((a.folder/'wheel_manifest.json').read_text(encoding='utf-8'))['packages']
        expected={v['file']:v['sha256'] for v in items}
    elif (a.folder/'pip_download_plan.json').exists():
        from urllib.parse import unquote,urlparse
        items=json.loads((a.folder/'pip_download_plan.json').read_text(encoding='utf-8'))['install']
        expected={Path(unquote(urlparse(v['download_info']['url']).path)).name:v['download_info']['archive_info']['hashes']['sha256'] for v in items}
    else:raise ValueError('Missing hash manifest; transfer the complete download folder')
    for name,checksum in expected.items():
        assert sha(a.folder/name)==checksum,name
        print('OK '+name)
    print('VERIFIED_DOWNLOADS',len(expected))

if __name__=='__main__':main()
