$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..')

python -m pip install -r (Join-Path $ScriptDir 'requirements.txt')

$Version = if ($env:GITHUB_REF_TYPE -eq 'tag' -and $env:GITHUB_REF_NAME) { $env:GITHUB_REF_NAME } else { "v$(python -c 'from bubbly_version import BUBBLY_VERSION; print(BUBBLY_VERSION)')" }
function Build-One {
  param (
    [string]$Entry,
    [string]$Name
  )

  pyinstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name $Name `
    --paths $RepoRoot `
    --hidden-import bubbly_version `
    --distpath (Join-Path $ScriptDir 'dist/windows') `
    --workpath (Join-Path $ScriptDir 'work/windows') `
    --specpath (Join-Path $ScriptDir 'spec') `
    --add-data "$RepoRoot\templates;templates" `
    (Join-Path $RepoRoot $Entry)

  Write-Host "Built: $(Join-Path $ScriptDir "dist/windows/$Name.exe")"
}

Build-One -Entry 'bubbly_launcher.py' -Name "bubbly_$Version"
Build-One -Entry 'bubbly_gui.py' -Name "bubbly_gui_$Version"
Build-One -Entry 'input_to_bubbly_gui.py' -Name "input_to_bubbly_gui_$Version"
