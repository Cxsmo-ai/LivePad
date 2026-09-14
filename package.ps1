$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$dotnet = Join-Path $projectRoot '.dotnet\dotnet.exe'

& $dotnet publish (Join-Path $projectRoot 'bridge\TikForever.HIDMaestro.csproj') `
    --configuration Release --runtime win-x64 --self-contained true `
    --output (Join-Path $projectRoot 'build\bridge') --nologo `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
if ($LASTEXITCODE -ne 0) { throw 'Self-contained bridge publish failed' }

$bridgeExe = Join-Path $projectRoot 'build\bridge\TikForever.HIDMaestro.exe'
$bridgeZip = Join-Path $projectRoot 'build\bridge\TikForever.HIDMaestro.zip'
Compress-Archive -LiteralPath $bridgeExe -DestinationPath $bridgeZip -Force

& $python -m PyInstaller --noconfirm --clean (Join-Path $projectRoot 'TikForeverChatGamepad.spec')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller packaging failed' }

$packagedApp = Join-Path $projectRoot 'dist\TikForeverChatGamepad\TikForeverChatGamepad.exe'
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

Copy-Item (Join-Path $projectRoot 'QUICK_START.txt') (Join-Path $projectRoot 'dist\TikForeverChatGamepad\QUICK_START.txt') -Force

$releaseDirectory = Join-Path $projectRoot 'release'
$releaseArchive = Join-Path $releaseDirectory 'TikForeverChatGamepad-win-x64.zip'
$releaseChecksum = "$releaseArchive.sha256"
New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null
Compress-Archive -Path (Join-Path $projectRoot 'dist\TikForeverChatGamepad\*') `
    -DestinationPath $releaseArchive -Force
$hash = (Get-FileHash -LiteralPath $releaseArchive -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath $releaseChecksum -Value "$hash  TikForeverChatGamepad-win-x64.zip" `
    -Encoding utf8NoBOM
Write-Host "Release archive: $releaseArchive"
Write-Host "SHA-256: $hash"
