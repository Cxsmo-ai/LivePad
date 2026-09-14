
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$release = Join-Path $projectRoot 'release'
$distExe = Join-Path $projectRoot 'dist\LivePad.exe'
$releaseExe = Join-Path $release 'LivePad.exe'

# 1. Extension packages
$extSource = Join-Path $projectRoot 'controller-chat-extension'
$extZip = Join-Path $release 'DeepAscension-LivePad-Extension.zip'
$extUnpacked = Join-Path $release 'DeepAscension-LivePad-Extension-Edge'

New-Item -ItemType Directory -Path $extUnpacked -Force | Out-Null
foreach ($file in @('manifest.json','service_worker.js','content.js','popup.html','popup.css','popup.js','README.md')) {
    Copy-Item -LiteralPath (Join-Path $extSource $file) -Destination (Join-Path $extUnpacked $file) -Force
}
New-Item -ItemType Directory -Path (Join-Path $extUnpacked 'shared') -Force | Out-Null
foreach ($file in @('protocol.js','gamepad_engine.js','dom_injector.js')) {
    Copy-Item -LiteralPath (Join-Path $extSource "shared\$file") -Destination (Join-Path $extUnpacked "shared\$file") -Force
}

Push-Location $extSource
try {
    if (Test-Path $extZip) { Remove-Item -LiteralPath $extZip -Force }
    Compress-Archive -Path @('manifest.json','service_worker.js','content.js','popup.html','popup.css','popup.js','shared','README.md') -DestinationPath $extZip -Force
}
finally { Pop-Location }

$extHash = (Get-FileHash -LiteralPath $extZip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$extZip.sha256" -Value "$extHash  DeepAscension-LivePad-Extension.zip" -Encoding UTF8

# 2. Exe in release
if (Test-Path $distExe) {
    Copy-Item -LiteralPath $distExe -Destination $releaseExe -Force
    $exeHash = (Get-FileHash -LiteralPath $releaseExe -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath "$releaseExe.sha256" -Value "$exeHash  LivePad.exe" -Encoding UTF8
}

# Instant Launcher Folder (No decompression delay)
$distDir = Join-Path $projectRoot 'dist\LivePad'
$releaseInstant = Join-Path $release 'LivePad-Instant'
if (Test-Path $distDir) {
    if (Test-Path $releaseInstant) { Remove-Item -LiteralPath $releaseInstant -Recurse -Force }
    Copy-Item -LiteralPath $distDir -Destination $releaseInstant -Recurse -Force
}

# 3. Master all-in-one Complete zip
$bundleDir = Join-Path $projectRoot 'build\LivePadPackage'
if (Test-Path $bundleDir) { Remove-Item -LiteralPath $bundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $bundleDir -Force | Out-Null

Copy-Item -LiteralPath $releaseExe -Destination (Join-Path $bundleDir 'LivePad.exe') -Force
if (Test-Path $distDir) {
    Copy-Item -LiteralPath $distDir -Destination (Join-Path $bundleDir 'LivePad-Instant') -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $release 'commands_guide.html') -Destination (Join-Path $bundleDir 'commands_guide.html') -Force
Copy-Item -LiteralPath $extZip -Destination (Join-Path $bundleDir 'DeepAscension-LivePad-Extension.zip') -Force
Copy-Item -LiteralPath $extUnpacked -Destination (Join-Path $bundleDir 'DeepAscension-LivePad-Extension-Edge') -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'README.md') -Destination (Join-Path $bundleDir 'README.md') -Force

$completeZip = Join-Path $release 'LivePad-Complete.zip'
if (Test-Path $completeZip) { Remove-Item -LiteralPath $completeZip -Force }
Compress-Archive -Path "$bundleDir\*" -DestinationPath $completeZip -Force

$zipHash = (Get-FileHash -LiteralPath $completeZip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$completeZip.sha256" -Value "$zipHash  LivePad-Complete.zip" -Encoding UTF8

Write-Host "LivePad Package Ready:"
Write-Host "  Executable: $releaseExe"
Write-Host "  Extension:  $extZip"
Write-Host "  Guide:      $(Join-Path $release 'commands_guide.html')"
Write-Host "  Master Zip: $completeZip ($([math]::Round((Get-Item $completeZip).Length / 1MB, 2)) MB)"
Write-Host "  SHA-256:    $zipHash"

