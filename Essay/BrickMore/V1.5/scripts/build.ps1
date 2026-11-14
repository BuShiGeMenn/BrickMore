param(
    [string]$Tectonic = 'tectonic',
    [string]$Latexmk = 'latexmk',
    [switch]$RenderPng
)
# V1.4: main.tex uses the official AAAI-27 style (aaai2027.sty), which requires pdfTeX.
# Tectonic (XeTeX-based) cannot compile main.tex any more; use latexmk/pdflatex
# (MiKTeX or TeX Live). The standalone TikZ figures can still be built with Tectonic.
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$previousDirectory = Get-Location
try {
    Set-Location -LiteralPath $projectDirectory
    foreach ($source in @('figure1.tex', 'figure2.tex')) {
        & $Tectonic --keep-logs $source
        if ($LASTEXITCODE -ne 0) { throw "LaTeX compilation failed: $source" }
    }
    & $Latexmk -pdf -interaction=nonstopmode main.tex
    if ($LASTEXITCODE -ne 0) { throw "LaTeX compilation failed: main.tex" }
    if ($RenderPng) {
        foreach ($figure in @('figure1', 'figure2')) {
            & pdftoppm -png -singlefile -r 300 "$figure.pdf" "figures/$figure"
            if ($LASTEXITCODE -ne 0) { throw "PNG rendering failed: $figure" }
        }
    }
} finally {
    Set-Location -LiteralPath $previousDirectory
}
