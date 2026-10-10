"""Publish verified dataset assets using the current Git credential, never print it."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
REPO = 'BuShiGeMenn/BrickMore'
API = 'https://api.github.com/repos/' + REPO


def checksum(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def credential():
    result = subprocess.run(['git', '-c', 'credential.interactive=false', 'credential', 'fill'],
        input='protocol=https\nhost=github.com\npath=' + REPO + '.git\n\n',
        capture_output=True, text=True, cwd=ROOT)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if result.returncode or not values.get('password'):
        raise RuntimeError('GitHub Git credential unavailable; sign in with a repository writer')
    return values['password']


def request(token, url, method='GET', value=None, stream=None, size=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('api.github.com', 'uploads.github.com'):
        raise ValueError('Authenticated request host rejected')
    headers = {'Authorization': 'Bearer ' + token, 'User-Agent': 'BrickMore-dataset-publisher',
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    data = json.dumps(value).encode('utf8') if value is not None else stream
    if stream is not None:
        headers.update({'Content-Type': 'application/octet-stream', 'Content-Length': str(size)})
    elif data is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=300) as response:
        if response.status == 204:
            return None
        return json.load(response)


def assets(token, release_id):
    rows = []
    page = 1
    while True:
        batch = request(token, f'{API}/releases/{release_id}/assets?per_page=100&page={page}')
        rows.extend(batch)
        if len(batch) < 100:
            return rows
        page += 1


def matches(row, asset):
    return row.get('state') == 'uploaded' and row['size'] == asset['bytes'] and \
        row.get('digest') == 'sha256:' + asset['sha256']


def inspect(token):
    user = request(token, 'https://api.github.com/user')
    repo = request(token, API)
    releases = request(token, API + '/releases?per_page=100')
    print(json.dumps({'login': user['login'], 'permissions': repo.get('permissions'),
        'releases': [{'tag': r['tag_name'], 'id': r['id'], 'draft': r['draft'],
                     'assetCount': len(r['assets'])} for r in releases]}, ensure_ascii=False), flush=True)


def fetch_a(token, directory):
    manifest = json.loads((ROOT/'download_manifest.json').read_text(encoding='utf8'))
    asset = next(row for row in manifest['assets'] if row['name'] == 'metadata.zip')
    directory.mkdir(parents=True, exist_ok=True)
    # Public download URL: do not forward an API credential to redirected asset storage.
    from download_dataset import download
    result = download(asset, directory)
    print('A_METADATA_VERIFIED', result.name, flush=True)


def find_release(token, tag, release_id=None):
    # GitHub's by-tag endpoint does not reliably expose drafts. Enumerate them
    # with the writer credential, or use the exact known ID; never duplicate one.
    if release_id is not None:
        release = request(token, API+'/releases/'+str(release_id))
        if release['tag_name'] != tag:
            raise ValueError('Release ID does not belong to the requested tag')
        return release
    releases = request(token, API+'/releases?per_page=100')
    candidates = [row for row in releases if row['tag_name']==tag]
    if len(candidates)>1:
        raise ValueError('Multiple release drafts match; supply the exact --release-id')
    return candidates[0] if candidates else None


def upload(token, manifest_path, source, workers, commit, keep_draft=False, release_id=None):
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    tag = manifest['releaseTag']
    checked = []
    for row in manifest['assets']:
        path = (source/row.get('sourceRelativePath', row['name'])).resolve()
        if not path.is_relative_to(source.resolve()):
            raise ValueError('Asset source outside declared dataset')
        if path.stat().st_size != row['bytes'] or checksum(path) != row['sha256']:
            raise ValueError('Local asset checksum mismatch: ' + row['name'])
        checked.append((row, path))
    print('LOCAL_ASSETS_VERIFIED', len(checked), flush=True)
    release = find_release(token, tag, release_id)
    if release is None:
        release = request(token, API + '/releases', 'POST', {
            'tag_name': tag, 'target_commitish': commit, 'name': 'AI_B 40,000 voxel models / 200,000 bilingual records',
            'body': '完整AI_B体素模型与五级中英双语提示词。40个模型分包及B_metadata.zip解压到同一AI_B目录。'
                    '\n原AI_A发布保持不变。统一下载与A/B去重说明见仓库README和datasets/merge_report.json。'
                    '\n几何模型不等于通过物理稳定性验证的LEGO装配；未更改原模型或颜色。',
            'draft': True, 'prerelease': False, 'make_latest': 'false'})
    existing = {row['name']: row for row in assets(token, release['id'])}
    expected = {row['name'] for row, _ in checked}
    if set(existing) - expected:
        raise ValueError('Unexpected assets in target release; refusing mutation')
    for row, _ in checked:
        if row['name'] in existing and not matches(existing[row['name']], row):
            raise ValueError('Existing asset differs; refusing overwrite: ' + row['name'])
    upload_url = release['upload_url'].split('{', 1)[0]

    def send(pair):
        row, path = pair
        if row['name'] in existing:
            return row['name'], 'verified_existing'
        url = upload_url + '?' + urllib.parse.urlencode({'name': row['name']})
        for attempt in range(3):
            try:
                with path.open('rb') as stream:
                    uploaded = request(token, url, 'POST', stream=stream, size=row['bytes'])
                if not matches(uploaded, row):
                    raise ValueError('Uploaded asset SHA/size mismatch: ' + row['name'])
                return row['name'], 'uploaded_sha256_verified'
            except (OSError, urllib.error.URLError):
                # A lost response may follow a successful upload: verify before retrying.
                now = {r['name']: r for r in assets(token, release['id'])}
                if row['name'] in now:
                    if matches(now[row['name']], row):
                        return row['name'], 'uploaded_sha256_verified'
                    raise ValueError('Partial/conflicting remote asset; no automatic deletion: ' + row['name'])
                if attempt == 2:
                    raise
                time.sleep(3)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(send, pair) for pair in checked]
        for number, future in enumerate(as_completed(futures), 1):
            name, status = future.result()
            print('ASSET_PROGRESS', number, '/', len(checked), name, status, flush=True)
    final = {row['name']: row for row in assets(token, release['id'])}
    if set(final) != expected or not all(matches(final[r['name']], r) for r, _ in checked):
        raise ValueError('Final remote asset inventory or SHA-256 mismatch')
    if release['draft'] and not keep_draft:
        release = request(token, API + '/releases/' + str(release['id']), 'PATCH',
                          {'draft': False, 'make_latest': 'false', 'target_commitish': commit})
    if not keep_draft:
        # Publishing changes draft-only download URLs to the public tag URL.
        final = {row['name']: row for row in assets(token, release['id'])}
        if set(final) != expected or not all(matches(final[r['name']], r) and
            final[r['name']]['browser_download_url'] == r['url'] for r, _ in checked):
            raise ValueError('Published asset SHA/inventory/download URLs disagree with manifest')
        # Record only public asset metadata, never credentials or local paths.
        a_manifest = json.loads((ROOT/'download_manifest.json').read_text(encoding='utf8'))
        a_release = request(token, API+'/releases/tags/'+a_manifest['releaseTag'])
        a_rows = {row['name']: row for row in assets(token, a_release['id'])}
        a_intact = set(a_rows) == {row['name'] for row in a_manifest['assets']} and all(
            matches(a_rows[row['name']], row) for row in a_manifest['assets'])
        if not a_intact:
            raise ValueError('Original A release asset inventory or SHA differs from its manifest')
        report = {'published': not release['draft'], 'releaseTag': tag, 'releaseUrl': release['html_url'],
            'modelCount': manifest['modelCount'], 'promptRecordCount': manifest['promptRecordCount'],
            'assetCount': len(final), 'allRemoteAssetSizesAndSha256Passed': True,
            'originalAReleaseUnchanged': a_intact,
            'assets': [{'name': row['name'], 'bytes': final[row['name']]['size'],
                        'sha256': final[row['name']]['digest'].removeprefix('sha256:'),
                        'url': final[row['name']]['browser_download_url']} for row, _ in checked]}
        target = ROOT/'datasets'/'AI_B'/'release_verification.json'
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
        temporary.replace(target)
    print('RELEASE_VERIFIED', release['html_url'], 'assets', len(final), 'draft', release['draft'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'fetch-a', 'upload'))
    parser.add_argument('--directory', type=Path, default=ROOT/'downloads'/'merge_b')
    parser.add_argument('--manifest', type=Path, default=ROOT/'datasets'/'AI_B'/'download_manifest.json')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--commit', default='main')
    parser.add_argument('--keep-draft', action='store_true')
    parser.add_argument('--release-id',type=int,help='Exact existing draft ID; avoids by-tag draft lookup')
    args = parser.parse_args()
    token = credential()
    if args.action == 'inspect':
        inspect(token)
    elif args.action == 'fetch-a':
        fetch_a(token, args.directory)
    else:
        if args.source is None or not 1 <= args.workers <= 4:
            parser.error('--source and 1..4 workers required')
        upload(token, args.manifest, args.source, args.workers, args.commit, args.keep_draft, args.release_id)


if __name__ == '__main__':
    main()
