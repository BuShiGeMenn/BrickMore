$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:GIT_TERMINAL_PROMPT = '0'

$repo   = 'D:\BrickMore'
$wt     = 'D:\BrickMore_pushwork'
$base   = '47d504a'
$target = '8d7e5a2'
$rar    = 'BrickMore_Comparision/BrickMoreComparison_20261116.rar'
$limit  = 30MB

function Log($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }
function Fail($m) { Log "FAILED: $m"; exit 9 }

# run git, log output, return exit code
function GitRun([string[]]$gitArgs) {
    $out = & git @gitArgs 2>&1
    $code = $LASTEXITCODE
    foreach ($l in $out) { if ("$l" -ne '') { Log "  $l" } }
    return $code
}
function GitText([string[]]$gitArgs) {
    return (& git @gitArgs 2>$null)
}

GitRun @('-C', $repo, 'config', 'http.postBuffer', '524288000') | Out-Null
GitRun @('-C', $repo, 'config', 'http.version', 'HTTP/1.1') | Out-Null
GitRun @('-C', $repo, 'config', 'http.lowSpeedLimit', '0') | Out-Null

if (Test-Path $wt) { Log "removing stale worktree dir"; GitRun @('-C', $repo, 'worktree', 'remove', '--force', $wt) | Out-Null; Remove-Item -Recurse -Force $wt -ErrorAction SilentlyContinue }
$br = GitText @('-C', $repo, 'branch', '--list', 'push/batched')
if ($br) { GitRun @('-C', $repo, 'branch', '-D', 'push/batched') | Out-Null }
GitRun @('-C', $repo, 'worktree', 'prune') | Out-Null

Log "creating worktree at $wt from $base"
$code = GitRun @('-C', $repo, 'worktree', 'add', '-b', 'push/batched', $wt, $base)
if ($code -ne 0) { Fail "worktree add (exit $code)" }

Log "materializing target tree $target"
$code = GitRun @('-C', $wt, 'checkout', $target, '--', '.')
if ($code -ne 0) { Fail "checkout target (exit $code)" }

Log "excluding oversized archive: $rar"
GitRun @('-C', $wt, 'rm', '--cached', '--ignore-unmatch', '--', $rar) | Out-Null
Remove-Item -LiteralPath (Join-Path $wt ($rar -replace '/', '\')) -Force -ErrorAction SilentlyContinue

$code = GitRun @('-C', $wt, 'reset', '-q', $base)
if ($code -ne 0) { Fail "reset to base (exit $code)" }
Log "index reset to base; worktree keeps target files"

$raw = GitText @('-C', $wt, '-c', 'core.quotepath=false', 'diff', '--name-only', '-z', $base, $target)
$list = ($raw -join '') -split "`0" | Where-Object { $_ -ne '' -and $_ -ne $rar }
$list = @($list)
Log "files to commit: $($list.Count)"

$items = New-Object System.Collections.Generic.List[object]
$missing = 0
foreach ($p in $list) {
    $f = Join-Path $wt ($p -replace '/', '\')
    if (Test-Path -LiteralPath $f -PathType Leaf) {
        $items.Add([pscustomobject]@{ Path = $p; Size = (Get-Item -LiteralPath $f).Length })
    } else { $missing++; Log "MISSING in worktree: $p" }
}
$totalMB = [math]::Round((($items | Measure-Object Size -Sum).Sum) / 1MB, 1)
Log "sized: $($items.Count) files, missing: $missing, total $totalMB MB"

$batches = New-Object System.Collections.Generic.List[object]
$cur = New-Object System.Collections.Generic.List[object]
$curSize = 0L
foreach ($it in ($items | Sort-Object Size -Descending)) {
    if ($curSize + $it.Size -gt $limit -and $cur.Count -gt 0) {
        $batches.Add($cur.ToArray()); $cur = New-Object System.Collections.Generic.List[object]; $curSize = 0L
    }
    $cur.Add($it); $curSize += $it.Size
}
if ($cur.Count -gt 0) { $batches.Add($cur.ToArray()) }
$n = $batches.Count
Log "batches planned: $n"

for ($i = 0; $i -lt $n; $i++) {
    $b = $batches[$i]
    $mb = [math]::Round((($b | Measure-Object Size -Sum).Sum) / 1MB, 1)
    $pf = Join-Path $env:TEMP ("bm_batch_{0}.paths" -f $i)
    $txt = (($b | ForEach-Object { $_.Path }) -join "`0") + "`0"
    [System.IO.File]::WriteAllText($pf, $txt, (New-Object System.Text.UTF8Encoding($false)))

    $code = GitRun @('-C', $wt, 'add', "--pathspec-from-file=$pf", '--pathspec-file-nul')
    if ($code -ne 0) { Fail "git add batch $($i+1) (exit $code)" }
    $msg = "上传对比实验数据（批次 $($i+1)/$n，$mb MB，$($b.Count) 个文件）"
    $msgFile = Join-Path $env:TEMP ("bm_msg_{0}.txt" -f $i)
    [System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
    $code = GitRun @('-C', $wt, 'commit', '-q', '-F', $msgFile)
    if ($code -ne 0) { Fail "git commit batch $($i+1) (exit $code)" }

    $ok = $false
    for ($a = 1; $a -le 5; $a++) {
        Log "push batch $($i+1)/$n ($mb MB, $($b.Count) files) attempt $a"
        $out = & git -C $wt push origin HEAD:refs/heads/main 2>&1
        $pcode = $LASTEXITCODE
        foreach ($l in $out) { if ("$l" -ne '') { Log "  $l" } }
        if ($pcode -eq 0) { $ok = $true; break }
        Log "  push failed (exit $pcode), sleeping"
        Start-Sleep -Seconds (10 * $a)
    }
    if (-not $ok) { Fail "push batch $($i+1) permanently failed" }
    Remove-Item -LiteralPath $pf, $msgFile -Force -ErrorAction SilentlyContinue
}

$tip = (GitText @('-C', $wt, 'rev-parse', 'HEAD') | Select-Object -First 1).Trim()
Log "all batches pushed; tip=$tip"
Log "tree difference vs target (expect only the excluded rar):"
GitRun @('-C', $wt, 'diff', '--stat', $tip, $target) | Out-Null
Log "DONE"
