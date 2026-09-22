param(
    [Parameter(Mandatory=$true)]
    [string]$RepositoryUrl,
    [string]$Branch = "main",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$pythonCommand = if (Test-Path .venv/Scripts/python.exe) { (Resolve-Path .venv/Scripts/python.exe).Path } else { "python" }

function Invoke-GitChecked {
    & git @args
    if ($LASTEXITCODE -ne 0) { throw "Git command failed (exit $LASTEXITCODE)." }
}

if (-not $SkipTests) {
    & $pythonCommand -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "pytest failed" }
    & $pythonCommand tests/validate_workflow_cases.py
    if ($LASTEXITCODE -ne 0) { throw "workflow validation failed" }
    & $pythonCommand scripts/evaluate_cases.py
    if ($LASTEXITCODE -ne 0) { throw "deterministic evaluation failed" }
}

& $pythonCommand scripts/build_release.py
if ($LASTEXITCODE -ne 0) { throw "release build failed" }

if (-not (Test-Path .git)) { Invoke-GitChecked init }
$currentRemote = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    if ($currentRemote -ne $RepositoryUrl) { throw "origin already points to another repository; review it before publishing." }
} else {
    Invoke-GitChecked remote add origin $RepositoryUrl
}
Invoke-GitChecked add -- .
git diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
    Invoke-GitChecked commit -m "Prepare smart travel agent publication"
} elseif ($LASTEXITCODE -ne 0) {
    throw "Could not inspect staged files."
}
Invoke-GitChecked push -u origin "HEAD:refs/heads/$Branch"
Write-Host "GitHub publish completed: $RepositoryUrl ($Branch)"
