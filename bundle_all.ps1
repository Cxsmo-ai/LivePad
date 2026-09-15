$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$release = Join-Path $projectRoot 'release'
$distDir = Join-Path (Join-Path $projectRoot 'dist') 'LivePad'

foreach ($staleExtensionPath in @(
    (Join-Path $release 'HIDMaestroControllerChat-Edge'),
    (Join-Path $release 'LivePad-Extension-Edge')
)) {
    if (Test-Path -LiteralPath $staleExtensionPath) {
        Remove-Item -LiteralPath $staleExtensionPath -Recurse -Force
    }
}

# 1. Extension packages
$extSource = Join-Path $projectRoot 'controller-chat-extension'
$extZip = Join-Path $release 'LivePad-Extension.zip'
$extUnpacked = Join-Path $release 'LivePad-Extension-Edge'

New-Item -ItemType Directory -Path $extUnpacked -Force | Out-Null
foreach ($file in @('manifest.json','service_worker.js','content.js','popup.html','popup.css','popup.js','README.md')) {
    Copy-Item -LiteralPath (Join-Path $extSource $file) -Destination (Join-Path $extUnpacked $file) -Force
}
New-Item -ItemType Directory -Path (Join-Path $extUnpacked 'assets') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'assets\livepad_mark.png') -Destination (Join-Path $extUnpacked 'assets\livepad_mark.png') -Force
New-Item -ItemType Directory -Path (Join-Path $extUnpacked 'shared') -Force | Out-Null
foreach ($file in @('protocol.js','gamepad_engine.js','dom_injector.js')) {
    $src = Join-Path (Join-Path $extSource 'shared') $file
    $dst = Join-Path (Join-Path $extUnpacked 'shared') $file
    Copy-Item -LiteralPath $src -Destination $dst -Force
}

Push-Location $extSource
try {
    if (Test-Path $extZip) { Remove-Item -LiteralPath $extZip -Force }
    Compress-Archive -Path @('manifest.json','service_worker.js','content.js','popup.html','popup.css','popup.js','assets','shared','README.md') -DestinationPath $extZip -Force
}
finally { Pop-Location }

$extHash = (Get-FileHash -LiteralPath $extZip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath ('{0}.sha256' -f $extZip) -Value ('{0}  LivePad-Extension.zip' -f $extHash) -Encoding UTF8

# 2. Instant-launch folder (the only EXE distribution)
$releaseInstant = Join-Path $release 'LivePad-Instant'
if (Test-Path $distDir) {
    if (Test-Path $releaseInstant) { Remove-Item -LiteralPath $releaseInstant -Recurse -Force }
    Copy-Item -LiteralPath $distDir -Destination $releaseInstant -Recurse -Force
}
$instantExe = Join-Path $releaseInstant 'LivePad.exe'
if (Test-Path $instantExe) {
    $instantHash = (Get-FileHash -LiteralPath $instantExe -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath ($instantExe + '.sha256') -Value ('{0}  LivePad.exe' -f $instantHash) -Encoding UTF8
}

# 3. Master all-in-one Complete zip
$bundleDir = Join-Path (Join-Path $projectRoot 'build') 'LivePadPackage'
if (Test-Path $bundleDir) { Remove-Item -LiteralPath $bundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $bundleDir -Force | Out-Null

# Copy instant folder contents into bundle root so LivePad.exe is at top level
if (Test-Path $releaseInstant) {
    Get-ChildItem -LiteralPath $releaseInstant | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $bundleDir -Recurse -Force
    }
}
Copy-Item -LiteralPath (Join-Path $release 'commands_guide.html') -Destination (Join-Path $bundleDir 'commands_guide.html') -Force
$mdGuide = Join-Path $release 'commands_guide.md'
if (Test-Path $mdGuide) {
    Copy-Item -LiteralPath $mdGuide -Destination (Join-Path $bundleDir 'commands_guide.md') -Force
}
Copy-Item -LiteralPath $extZip -Destination (Join-Path $bundleDir 'LivePad-Extension.zip') -Force
Copy-Item -LiteralPath $extUnpacked -Destination (Join-Path $bundleDir 'LivePad-Extension-Edge') -Recurse -Force
$readmeSrc = Join-Path $projectRoot 'README.md'
if (Test-Path $readmeSrc) {
    Copy-Item -LiteralPath $readmeSrc -Destination (Join-Path $bundleDir 'README.md') -Force
}

$completeZip = Join-Path $release 'LivePad-Complete.zip'
if (Test-Path $completeZip) { Remove-Item -LiteralPath $completeZip -Force }
$bundleItems = Join-Path $bundleDir '*'
Compress-Archive -Path $bundleItems -DestinationPath $completeZip -Force

$zipHash = (Get-FileHash -LiteralPath $completeZip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath ('{0}.sha256' -f $completeZip) -Value ('{0}  LivePad-Complete.zip' -f $zipHash) -Encoding UTF8

$zipSizeMB = [math]::Round((Get-Item $completeZip).Length / 1MB, 2)
Write-Host 'LivePad Package Ready:'
Write-Host ('  App:        LivePad.exe (instant launch)')
Write-Host ('  Extension:  {0}' -f $extZip)
Write-Host ('  Guide:      {0}' -f (Join-Path $release 'commands_guide.html'))
Write-Host ('  Master Zip: {0} ({1} MB)' -f $completeZip, $zipSizeMB)
Write-Host ('  SHA-256:    {0}' -f $zipHash)
