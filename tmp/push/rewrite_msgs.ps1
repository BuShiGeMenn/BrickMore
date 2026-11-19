$ErrorActionPreference = 'Continue'
$repo = 'D:\BrickMore'
$base = '47d504a'
$tplPath = 'D:\BrickMore\tmp\push\msg_template.txt'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$tpl = [System.IO.File]::ReadAllText($tplPath, $utf8)
$US = [char]31

$commits = @(git -C $repo rev-list --reverse "$base..HEAD")
$n = $commits.Count
Write-Host "commits to rewrite: $n"

$parent = $base
$newTip = ''
for ($i = 0; $i -lt $n; $i++) {
    $c = $commits[$i]
    $count = (git -C $repo diff --name-only "$c^" $c | Measure-Object).Count
    $msg = $tpl.Replace('{i}', ($i + 1).ToString()).Replace('{n}', $n.ToString()).Replace('{count}', $count.ToString())
    $mf = Join-Path $env:TEMP ("bm_msg2_{0}.txt" -f $i)
    [System.IO.File]::WriteAllText($mf, $msg, $utf8)
    $tree = (git -C $repo rev-parse "$c^{tree}").Trim()
    $meta = (git -C $repo log -1 --format='%an%x1f%ae%x1f%ad' --date=raw $c) -join ''
    $f = $meta -split $US
    $env:GIT_AUTHOR_NAME = $f[0]
    $env:GIT_AUTHOR_EMAIL = $f[1]
    $env:GIT_AUTHOR_DATE = $f[2]
    $newTip = (git -C $repo commit-tree $tree -p $parent -F $mf).Trim()
    if (-not $newTip) { Write-Host "FAILED commit-tree at $i"; exit 1 }
    $parent = $newTip
    Write-Host ("  batch {0}/{1}: {2} files -> {3}" -f ($i + 1), $n, $count, $newTip.Substring(0, 8))
}

Write-Host "new tip: $newTip"
Write-Host "tree diff vs original target 8d7e5a2 (expect only the excluded rar):"
git -C $repo diff --stat $newTip 8d7e5a2 2>&1 | ForEach-Object { Write-Host "  $_" }

git -C $repo update-ref -m 'rewrite batch messages' refs/heads/main $newTip 0cf8699
Write-Host "local main moved to $newTip"
