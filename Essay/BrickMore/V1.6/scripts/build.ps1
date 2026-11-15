param(
    [string]$TeXBin = '',
    [string]$PdfLaTeX = 'pdflatex',
    [string]$BibTeX = 'bibtex',
    [string]$Latexmk = 'latexmk',
    [switch]$SkipFigures,
    [switch]$RenderPng
)
# V1.6: use the official AAAI-27 template with pdfLaTeX throughout.
# TeXBin optionally selects a portable TeX Live / MiKTeX bin directory.
# Its PATH addition is confined to this invocation; no machine settings change.
# Overleaf: select main.tex and the pdfLaTeX compiler. The supplied figure PDFs
# allow main.tex to compile directly without running this PowerShell script.
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$previousDirectory = Get-Location
$previousPath = $env:PATH
function Invoke-TeXPass([string]$Source) {
    & $PdfLaTeX -interaction=nonstopmode -halt-on-error -file-line-error $Source
    if ($LASTEXITCODE -ne 0) { throw "pdfLaTeX compilation failed: $Source" }
}
try {
    if ($TeXBin) {
        $resolvedTeXBin = (Resolve-Path -LiteralPath $TeXBin).Path
        $env:PATH = "$resolvedTeXBin;$previousPath"
    }
    if (-not (Get-Command $PdfLaTeX -ErrorAction SilentlyContinue)) {
        throw 'pdfLaTeX was not found. Install TeX Live/MiKTeX, supply -TeXBin, or use Overleaf with pdfLaTeX.'
    }
    Set-Location -LiteralPath $projectDirectory
    if (-not $SkipFigures) {
        foreach ($source in @('figure1.tex', 'figure2.tex')) {
            Invoke-TeXPass $source
        }
    }
    if (Get-Command $Latexmk -ErrorAction SilentlyContinue) {
        & $Latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex
        if ($LASTEXITCODE -ne 0) { throw 'latexmk compilation failed: main.tex' }
    } else {
        if (-not (Get-Command $BibTeX -ErrorAction SilentlyContinue)) {
            throw 'BibTeX was not found; it is required to resolve references.bib.'
        }
        Invoke-TeXPass 'main.tex'
        & $BibTeX main
        if ($LASTEXITCODE -ne 0) { throw 'BibTeX failed: main' }
        Invoke-TeXPass 'main.tex'
        Invoke-TeXPass 'main.tex'
    }
    if ($RenderPng) {
        foreach ($figure in @('figure1', 'figure2')) {
            & pdftoppm -png -singlefile -r 300 "$figure.pdf" "figures/$figure"
            if ($LASTEXITCODE -ne 0) { throw "PNG rendering failed: $figure" }
        }
    }
} finally {
    Set-Location -LiteralPath $previousDirectory
    $env:PATH = $previousPath
}
