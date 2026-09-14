$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$dotnet = Join-Path $projectRoot '.dotnet\dotnet.exe'

Write-Host "Publishing self-contained HIDMaestro C# bridge..."
& $dotnet publish (Join-Path $projectRoot 'bridge\TikForever.HIDMaestro.csproj') `
    --configuration Release --runtime win-x64 --self-contained true `
    --output (Join-Path $projectRoot 'build\bridge') --nologo `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
if ($LASTEXITCODE -ne 0) { throw 'Self-contained bridge publish failed' }

$bridgeExe = Join-Path $projectRoot 'build\bridge\TikForever.HIDMaestro.exe'
$bridgeZip = Join-Path $projectRoot 'build\bridge\TikForever.HIDMaestro.zip'
Compress-Archive -LiteralPath $bridgeExe -DestinationPath $bridgeZip -Force

Write-Host "Packaging HID Maestro Streamer Edition with PyInstaller..."
& $python -m PyInstaller --noconfirm --clean (Join-Path $projectRoot 'HIDMaestroStreamerEdition.spec')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller packaging failed' }

$packagedApp = Join-Path $projectRoot 'dist\HIDMaestroStreamerEdition.exe'
$previousQtPlatform = $env:QT_QPA_PLATFORM
try {
    $env:QT_QPA_PLATFORM = 'offscreen'
    $smoke = Start-Process -FilePath $packagedApp -ArgumentList '--smoke' `
        -Wait -PassThru -WindowStyle Hidden
    if ($smoke.ExitCode -ne 0) {
        throw "Packaged application smoke test failed with exit code $($smoke.ExitCode)"
    }
}
finally {
    $env:QT_QPA_PLATFORM = $previousQtPlatform
}

Write-Host "Packaged application smoke test passed: $packagedApp"

$releaseDirectory = Join-Path $projectRoot 'release'
$releaseExe = Join-Path $releaseDirectory 'HIDMaestroStreamerEdition.exe'
$releaseChecksum = "$releaseExe.sha256"
New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null
Copy-Item -LiteralPath $packagedApp -Destination $releaseExe -Force
$hash = (Get-FileHash -LiteralPath $releaseExe -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath $releaseChecksum -Value "$hash  HIDMaestroStreamerEdition.exe" `
    -Encoding utf8NoBOM
Write-Host "Single-file release: $releaseExe"
Write-Host "SHA-256: $hash"
