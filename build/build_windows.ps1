$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..')

python -m pip install -r (Join-Path $ScriptDir 'requirements.txt')

$Version = if ($env:GITHUB_REF_NAME) { $env:GITHUB_REF_NAME } else { "v$(python -c "from bubbly_version import BUBBLY_VERSION; print(BUBBLY_VERSION)")" }
$BinaryName = "bubbly_$Version"

pyinstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name $BinaryName `
  --paths $RepoRoot `
  --hidden-import bubbly_version `
  --distpath (Join-Path $ScriptDir 'dist/windows') `
  --workpath (Join-Path $ScriptDir 'work/windows') `
  --specpath (Join-Path $ScriptDir 'spec') `
  --add-data "$RepoRoot\templates;templates" `
  (Join-Path $RepoRoot 'bubbly_launcher.py')

if (Test-Path (Join-Path $RepoRoot 'default_conf.json')) {
  Copy-Item (Join-Path $RepoRoot 'default_conf.json') (Join-Path $ScriptDir 'dist/windows/default_conf.json') -Force
  Write-Host "Copied: $(Join-Path $ScriptDir 'dist/windows/default_conf.json')"
}
if (Test-Path (Join-Path $ScriptDir 'README_release.txt')) {
  Copy-Item (Join-Path $ScriptDir 'README_release.txt') (Join-Path $ScriptDir 'dist/windows/README_release.txt') -Force
  Write-Host "Copied: $(Join-Path $ScriptDir 'dist/windows/README_release.txt')"
}

Write-Host "Built: $(Join-Path $ScriptDir "dist/windows/$BinaryName.exe")"
