$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$zip = Join-Path $root 'release\LivePad-Complete.zip'
$exe = Join-Path $root 'release\LivePad-Instant\LivePad.exe'
$extension = Join-Path $root 'release\LivePad-Extension.zip'

foreach ($path in @($zip, $exe, $extension)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing release artifact: $path" }
}

$entries = @(tar -tf $zip)
$exeCount = @($entries | Where-Object { $_ -match '(^|/)LivePad\.exe$' }).Count
$forbidden = @($entries | Where-Object { $_ -match '\.(pak|dfm)$' })
if ($exeCount -ne 1) { throw "Expected exactly one LivePad.exe in the complete ZIP; found $exeCount" }
if ($forbidden.Count -ne 0) { throw "Forbidden files in release: $($forbidden -join ', ')" }
if (@($entries | Where-Object { $_ -match 'LivePad-Extension-Edge/assets/livepad_mark\.png$' }).Count -ne 1) {
    throw 'Extension branding asset is missing from the complete ZIP'
}

Write-Host 'Release verification passed.'
Write-Host ("Complete SHA-256: {0}" -f (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant())
Write-Host ("EXE SHA-256:      {0}" -f (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant())
Write-Host ("Extension SHA-256: {0}" -f (Get-FileHash -LiteralPath $extension -Algorithm SHA256).Hash.ToLowerInvariant())
