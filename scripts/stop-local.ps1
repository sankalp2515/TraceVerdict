param([switch]$IncludeZetaris, [string]$ZetarisPath = 'E:\zetaris-platform\zetaris-platform')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    docker compose -f compose.data.yml -f compose.local.yml --profile app stop
    if ($LASTEXITCODE -ne 0) { throw 'TraceVerdict stop failed.' }
} finally { Pop-Location }
if ($IncludeZetaris) {
    Push-Location -LiteralPath $ZetarisPath
    try {
        docker compose stop
        if ($LASTEXITCODE -ne 0) { throw 'Zetaris stop failed.' }
    } finally { Pop-Location }
}
Write-Host 'Stopped without deleting data volumes. Quit Nightshift separately if desired.'
