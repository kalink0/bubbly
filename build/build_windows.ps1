$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..')

python -m pip install -r (Join-Path $ScriptDir 'requirements.txt')

pyinstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name bubbly `
  --distpath (Join-Path $ScriptDir 'dist/windows') `
  --workpath (Join-Path $ScriptDir 'work/windows') `
  --specpath (Join-Path $ScriptDir 'spec') `
  --add-data "$RepoRoot\templates;templates" `
  (Join-Path $RepoRoot 'bubbly_launcher.py')

if (Test-Path (Join-Path $RepoRoot 'default_conf.json')) {
  Copy-Item (Join-Path $RepoRoot 'default_conf.json') (Join-Path $ScriptDir 'dist/windows/default_conf.json') -Force
  Write-Host "Copied: $(Join-Path $ScriptDir 'dist/windows/default_conf.json')"
}

Write-Host "Built: $(Join-Path $ScriptDir 'dist/windows/bubbly.exe')"
