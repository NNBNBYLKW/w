$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Resolve-Path (Join-Path $scriptDir "..\..\backend")

Push-Location $backendDir
try {
  python -m pip install -r requirements.txt -r requirements-build.txt
  python -m PyInstaller --noconfirm --clean workbench-backend.spec
}
finally {
  Pop-Location
}
