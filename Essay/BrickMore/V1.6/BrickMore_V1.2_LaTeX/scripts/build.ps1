param(
    [string]$Tectonic = 'tectonic',
    [switch]$RenderPng
)
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$previousDirectory = Get-Location
try {
    Set-Location -LiteralPath $projectDirectory
    foreach ($source in @('figure1.tex', 'figure2.tex', 'main.tex')) {
        & $Tectonic --keep-logs $source
        if ($LASTEXITCODE -ne 0) { throw "LaTeX compilation failed: $source" }
    }
    if ($RenderPng) {
        foreach ($figure in @('figure1', 'figure2')) {
            & pdftoppm -png -singlefile -r 300 "$figure.pdf" "figures/$figure"
            if ($LASTEXITCODE -ne 0) { throw "PNG rendering failed: $figure" }
        }
    }
} finally {
    Set-Location -LiteralPath $previousDirectory
}
