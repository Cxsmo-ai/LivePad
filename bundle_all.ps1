$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$release = Join-Path $projectRoot 'release'
$distExe = Join-Path $projectRoot 'dist\HIDMaestroStreamerEdition.exe'
$bundleDir = Join-Path $projectRoot 'build\CompletePackage'
if (Test-Path $bundleDir) { Remove-Item -LiteralPath $bundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $bundleDir -Force | Out-Null

Copy-Item -LiteralPath $distExe -Destination (Join-Path $bundleDir 'HIDMaestroStreamerEdition.exe') -Force
Copy-Item -LiteralPath (Join-Path $release 'commands_guide.html') -Destination (Join-Path $bundleDir 'commands_guide.html') -Force
Copy-Item -LiteralPath (Join-Path $release 'HIDMaestroControllerChat.zip') -Destination (Join-Path $bundleDir 'HIDMaestroControllerChat.zip') -Force
Copy-Item -LiteralPath (Join-Path $release 'HIDMaestroControllerChat-Edge') -Destination (Join-Path $bundleDir 'HIDMaestroControllerChat-Edge') -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'README.md') -Destination (Join-Path $bundleDir 'README.md') -Force

$completeZip = Join-Path $release 'HIDMaestroStreamerEdition-Complete.zip'
if (Test-Path $completeZip) { Remove-Item -LiteralPath $completeZip -Force }
Compress-Archive -Path "$bundleDir\*" -DestinationPath $completeZip -Force

$zipHash = (Get-FileHash -LiteralPath $completeZip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$completeZip.sha256" -Value "$zipHash  HIDMaestroStreamerEdition-Complete.zip" -Encoding UTF8

$distHash = (Get-FileHash -LiteralPath $distExe -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$release\HIDMaestroStreamerEdition.exe.sha256" -Value "$distHash  HIDMaestroStreamerEdition.exe" -Encoding UTF8

Write-Host "Complete package created: $completeZip"
Write-Host "Size: $([math]::Round((Get-Item $completeZip).Length / 1MB, 2)) MB"
Write-Host "SHA-256: $zipHash"
