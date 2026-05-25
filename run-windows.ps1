$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$SitePackages = Join-Path $ProjectRoot ".venv\lib\python3.11\site-packages"
$SourcePath = Join-Path $ProjectRoot "src"

Set-Location $ProjectRoot
$env:PYTHONHOME = $null
$env:PYTHONPATH = @($SourcePath, $SitePackages) -join [IO.Path]::PathSeparator
$env:PYTHONDONTWRITEBYTECODE = "1"

& $Python -m token_usage @args
