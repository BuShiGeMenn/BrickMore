from pathlib import Path
import os
import re
import subprocess


def git(*args, env=None, data=None):
    return subprocess.run(['git', *args], input=data, stdout=subprocess.PIPE,
                          check=True, env=env).stdout


old = git('rev-parse', 'refs/heads/main').strip().decode()
base = git('rev-parse', 'refs/remotes/origin/main').strip().decode()
assert git('rev-list', '--parents', '-n', '1', old).split() == [old.encode(), base.encode()]
remote_line = git('ls-remote', '--exit-code', 'origin', 'refs/heads/main').split()
assert remote_line[0].decode() == base, 'origin/main changed; recheck before pushing'

changes = git('diff-tree', '-z', '-r', '--no-renames', '--no-commit-id',
              '--name-status', base, old).rstrip(b'\0').split(b'\0')
excluded = []
kept = {}
for status, raw_path in zip(changes[::2], changes[1::2]):
    path = raw_path.decode('utf-8')
    scratch = (
        path.startswith('tmp/')
        or '/tmp/' in path
        or '/backup_v18/' in path
        or bool(re.search(r'\.(aux|log|blg|fls|fdb_latexmk)$', path))
        # Per-view raw traces contain local computer paths. Keep tables and scripts.
        or bool(re.search(r'/stats/(pe|siglip2)\.jsonl$', path))
    )
    if scratch and status == b'A':
        excluded.append(raw_path)
    else:
        assert path.startswith('Essay/BrickMore/'), f'Unexpected unrelated change: {path}'
        paper_version = path.split('/')[2]
        kept[paper_version] = kept.get(paper_version, 0) + 1

assert excluded and kept.get('V1.8'), 'Expected manuscript and scratch additions'
project_dir = Path('tmp/v16_review').resolve()
index = project_dir / f'push-paper-index-{old[:12]}'
assert not index.exists(), 'A temporary push index already exists'
env = dict(os.environ, GIT_INDEX_FILE=str(index))
git('read-tree', old, env=env)
git('update-index', '--force-remove', '-z', '--stdin', env=env,
    data=b'\0'.join(excluded) + b'\0')
tree = git('write-tree', env=env).strip().decode()

expected = set(excluded)
diff = git('diff-tree', '-z', '-r', '--no-renames', '--no-commit-id',
           '--name-status', old, tree).rstrip(b'\0').split(b'\0')
assert set(diff[::2]) == {b'D'} and set(diff[1::2]) == expected
assert not any(int(line.split(b'\t', 1)[0].split()[-1]) > 100 * 1024 * 1024
               for line in git('ls-tree', '-r', '-l', tree, '--', 'Essay/BrickMore').splitlines()
               if b' blob ' in line)

original_commit = git('cat-file', 'commit', old)
header, message = original_commit.split(b'\n\n', 1)
author = re.search(rb'^author (.+) <([^>]+)> (\d+ [+-]\d{4})$', header, re.M)
assert author
env = dict(os.environ, **{name: value.decode('utf-8') for name, value in zip(
    ['GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_AUTHOR_DATE'], author.groups())})
new = git('commit-tree', tree, '-p', base, env=env, data=message).strip().decode()
assert git('rev-parse', 'refs/heads/main').strip().decode() == old
git('update-ref', f'refs/codex/pre-push-paper-{old[:12]}', old)
(project_dir / 'paper_push_commit.txt').write_text(new + '\n', encoding='ascii')
print(f'Original commit {old}; clean commit {new}', flush=True)
print(f'Paper changes retained: {kept}; local-only additions excluded: {len(excluded)}', flush=True)
