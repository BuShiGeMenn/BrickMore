$ErrorActionPreference = 'Continue'
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$env:GIT_TERMINAL_PROMPT = '0'

$repo    = 'D:\BrickMore'
$logDir  = 'D:\BrickMore\tmp\push'
$tplPath = Join-Path $logDir 'msg_workspace.txt'
$batchMB = 10MB
$maxFile = 100MB
$backoff = @(5, 10, 20, 30, 45, 60, 60, 60)

function Log($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }

$lowPri = @('tmp/texlive/', 'Tools/', 'tmp/pdfs/', 'Deploy/build/', 'tmp/figure1_21_preview_20261117/')
$tpl = [System.IO.File]::ReadAllText($tplPath, $utf8)

Log "collecting untracked files..."
$status = git -C $repo status --porcelain=v1 --untracked-files=all
$files = @($status | Where-Object { $_ -match '^\?\?' } | ForEach-Object { $_.Substring(3).Trim('"') })
Log "untracked: $($files.Count)"

$items = New-Object System.Collections.Generic.List[object]
$blocked = New-Object System.Collections.Generic.List[object]
foreach ($f in $files) {
    $p = Join-Path $repo ($f -replace '/', '\')
    if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { continue }
    $len = (Get-Item -LiteralPath $p).Length
    if ($len -gt $maxFile) { $blocked.Add([pscustomobject]@{ Path = $f; Size = $len }); continue }
    $pri = 0
    foreach ($lp in $lowPri) { if ($f.StartsWith($lp)) { $pri = 1; break } }
    $items.Add([pscustomobject]@{ Path = $f; Size = $len; Pri = $pri })
}
Log ("pushable: {0} files, {1:N2} GB; blocked >100MB: {2} files, {3:N2} GB" -f $items.Count, (($items | Measure-Object Size -Sum).Sum/1GB), $blocked.Count, (($blocked | Measure-Object Size -Sum).Sum/1GB))
foreach ($b in ($blocked | Sort-Object Size -Descending)) { Log ("  BLOCKED {0:N1} MB  {1}" -f ($b.Size/1MB), $b.Path) }

$ordered = @($items | Sort-Object Pri, Size)
$batches = New-Object System.Collections.Generic.List[object]
$cur = New-Object System.Collections.Generic.List[object]
$curSize = 0L
foreach ($it in $ordered) {
    if ($curSize -ge $batchMB -and $cur.Count -gt 0) { $batches.Add($cur.ToArray()); $cur = New-Object System.Collections.Generic.List[object]; $curSize = 0L }
    $cur.Add($it); $curSize += $it.Size
}
if ($cur.Count -gt 0) { $batches.Add($cur.ToArray()) }
$n = $batches.Count
Log "batches planned: $n"

for ($i = 0; $i -lt $n; $i++) {
    $b = $batches[$i]
    $mb = [math]::Round((($b | Measure-Object Size -Sum).Sum) / 1MB, 1)
    $no = $i + 1
    $pf = Join-Path $env:TEMP ("ws_batch_{0}.paths" -f $no)
    $txt = (($b | ForEach-Object { $_.Path }) -join "`0") + "`0"
    [System.IO.File]::WriteAllText($pf, $txt, $utf8)
    git -C $repo add --pathspec-from-file=$pf --pathspec-file-nul 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Log "git add failed (batch $no)"; exit 3 }

    $msg = $tpl.Replace('{i}', $no.ToString()).Replace('{n}', $n.ToString()).Replace('{mb}', $mb.ToString()).Replace('{count}', $b.Count.ToString())
    $mf = Join-Path $env:TEMP ("ws_msg_{0}.txt" -f $no)
    [System.IO.File]::WriteAllText($mf, $msg, $utf8)
    git -C $repo commit -q -F $mf 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Log "git commit failed (batch $no)"; exit 4 }

    $ok = $false
    $failLog = Join-Path $logDir ("fail_batch_{0}.log" -f $no)
    for ($a = 0; $a -lt $backoff.Count; $a++) {
        $out = & git -C $repo push origin main 2>&1
        $code = $LASTEXITCODE
        if ($code -eq 0) { $ok = $true; break }
        $text = ($out | ForEach-Object { "$_" }) -join "`n"
        [System.IO.File]::WriteAllText($failLog, ("batch $no attempt $($a+1)`n" + $text), $utf8)
        $terminal = $false
        if ($text -match 'exceeds.*100\.00 MB|file size limit|repository.*size limit|GH001|GH002|GH003|Permission|denied|403|protected branch|non-fast-forward') { $terminal = $true }
        $kind = 'NET/TLS'
        if ($text -match 'size limit|permission|denied|403|protected|non-fast-forward') { $kind = 'SERVER' }
        Log ("  batch {0}/{1} attempt {2} failed [{3}]{4}" -f $no, $n, ($a + 1), $kind, $(if ($terminal) { ' TERMINAL' } else { '' }))
        Log ("    " + (($text -split "`n" | Where-Object { $_ -ne '' } | Select-Object -First 3) -join ' | '))
        if ($terminal) { Log "aborting: see $failLog"; exit 5 }
        Start-Sleep -Seconds $backoff[$a]
    }
    if (-not $ok) { Log "push failed after all retries at batch $no; see $failLog"; exit 6 }
    Log ("batch {0}/{1} pushed: {2} MB, {3} files" -f $no, $n, $mb, $b.Count)
    Remove-Item -LiteralPath $pf, $mf -Force -ErrorAction SilentlyContinue
}

Log "DONE: all $n batches pushed"
