param(
    [string]$ZetarisPath = 'E:\zetaris-platform\zetaris-platform',
    [switch]$Build
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
function Assert-NativeSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit $LASTEXITCODE)." }
}
docker info --format '{{.ServerVersion}}'
Assert-NativeSuccess 'Docker readiness check; start Docker Desktop first'
if (-not (Test-Path -LiteralPath $ZetarisPath -PathType Container)) {
    throw "Zetaris folder missing: $ZetarisPath. Pass -ZetarisPath for your installation."
}
Push-Location -LiteralPath $ZetarisPath
try {
    docker compose up -d
    Assert-NativeSuccess 'Zetaris startup'
} finally { Pop-Location }
Push-Location -LiteralPath $projectRoot
try {
    $composeArgs = @('compose', '-f', 'compose.data.yml', '-f', 'compose.local.yml', '--profile', 'app', 'up', '-d', '--wait', '--wait-timeout', '180')
    if ($Build) { $composeArgs += '--build' }
    & docker @composeArgs
    Assert-NativeSuccess 'TraceVerdict startup'
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'recover_local_stack.py') -Raw |
        docker compose -f compose.data.yml -f compose.local.yml --profile app exec -T case-api python -
    Assert-NativeSuccess 'Live sponsor readiness; start Nightshift and check platform health'
    $ready = Invoke-RestMethod 'http://127.0.0.1:5173/api/readyz' -TimeoutSec 15
    Write-Host 'TraceVerdict: http://localhost:5173 | API docs: http://localhost:8000/docs'
    Write-Host 'Nightshift must be running separately with its existing NVIDIA provider configuration.'
    Write-Host 'Use the authenticated Connections page to verify real sponsor connectivity.'
} finally { Pop-Location }
