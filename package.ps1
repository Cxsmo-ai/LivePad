$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $python = $pythonCommand.Source }
}
if (-not (Test-Path -LiteralPath $python) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'python was not found. Install Python 3.10+ or create the project .venv.'
}
$dotnet = Join-Path $projectRoot '.dotnet\dotnet.exe'
if (-not (Test-Path -LiteralPath $dotnet)) {
    $dotnetCommand = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($dotnetCommand) { $dotnet = $dotnetCommand.Source }
}
if (-not (Test-Path -LiteralPath $dotnet) -and -not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw 'dotnet was not found. Install .NET 10 SDK or run the workflow setup step.'
}

Write-Host "Publishing self-contained HIDMaestro C# bridge..."
& $dotnet publish (Join-Path $projectRoot 'bridge\LivePad.HIDMaestro.csproj') `
    --configuration Release --runtime win-x64 --self-contained true `
    --output (Join-Path $projectRoot 'build\bridge') --nologo `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true
if ($LASTEXITCODE -ne 0) { throw 'Self-contained bridge publish failed' }

$bridgeExe = Join-Path $projectRoot 'build\bridge\LivePad.HIDMaestro.exe'
$bridgeZip = Join-Path $projectRoot 'build\bridge\LivePad.HIDMaestro.zip'
Compress-Archive -LiteralPath $bridgeExe -DestinationPath $bridgeZip -Force

Write-Host "Packaging viewer controller-to-chat extension..."
$extensionRoot = Join-Path $projectRoot 'controller-chat-extension'
$extensionZip = Join-Path $projectRoot 'build\LivePad-Extension.zip'
$extensionAssets = Join-Path $extensionRoot 'assets'
New-Item -ItemType Directory -Path $extensionAssets -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'assets\livepad_mark.png') -Destination (Join-Path $extensionAssets 'livepad_mark.png') -Force
Push-Location $extensionRoot
try {
    Compress-Archive -Path @(
        'manifest.json', 'service_worker.js', 'content.js',
        'popup.html', 'popup.css', 'popup.js', 'assets', 'shared', 'README.md'
    ) -DestinationPath $extensionZip -Force
}
finally {
    Pop-Location
}

Write-Host "Packaging LivePad instant-launch onedir application with PyInstaller..."
& $python -m PyInstaller --noconfirm --clean (Join-Path $projectRoot 'LivePad-onedir.spec')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller packaging failed' }

$packagedApp = Join-Path $projectRoot 'dist\LivePad\LivePad.exe'
# LivePad intentionally carries an elevation manifest for HIDMaestro. A
# frozen --smoke invocation therefore prompts for UAC before the test harness
# can run it. Run the identical application smoke path from the project
# interpreter here; the resulting onedir EXE is then checked for all assets.
$previousQtPlatform = $env:QT_QPA_PLATFORM
try {
    $env:QT_QPA_PLATFORM = 'offscreen'
    & $python (Join-Path $projectRoot 'chat_gamepad_app.py') '--smoke'
    if ($LASTEXITCODE -ne 0) { throw "Application source smoke test failed with exit code $LASTEXITCODE" }
}
finally {
    $env:QT_QPA_PLATFORM = $previousQtPlatform
}
Write-Host "Application smoke test passed: $packagedApp"

$releaseDirectory = Join-Path $projectRoot 'release'
$releaseInstant = Join-Path $releaseDirectory 'LivePad-Instant'
$releaseExe = Join-Path $releaseInstant 'LivePad.exe'
$releaseChecksum = "$releaseExe.sha256"
$releaseExtension = Join-Path $releaseDirectory 'LivePad-Extension.zip'
$releaseExtensionChecksum = "$releaseExtension.sha256"
New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null
foreach ($staleExtension in @(
    (Join-Path $releaseDirectory 'HIDMaestroControllerChat.zip'),
    (Join-Path $releaseDirectory 'HIDMaestroControllerChat.zip.sha256'),
    (Join-Path $releaseDirectory 'LivePad-Extension.zip'),
    (Join-Path $releaseDirectory 'LivePad-Extension.zip.sha256')
)) {
    if (Test-Path -LiteralPath $staleExtension) {
        Remove-Item -LiteralPath $staleExtension -Force
    }
}
if (Test-Path $releaseInstant) { Remove-Item -LiteralPath $releaseInstant -Recurse -Force }
Copy-Item -LiteralPath (Split-Path -Parent $packagedApp) -Destination $releaseInstant -Recurse -Force
Copy-Item -LiteralPath $extensionZip -Destination $releaseExtension -Force
$guideSource = Join-Path $projectRoot 'commands_guide.html'
$guideDestination = Join-Path $releaseDirectory 'commands_guide.html'
Copy-Item -LiteralPath $guideSource -Destination $guideDestination -Force
$markdownGuideSource = Join-Path $projectRoot 'commands_guide.md'
if (Test-Path -LiteralPath $markdownGuideSource) {
    Copy-Item -LiteralPath $markdownGuideSource -Destination (Join-Path $releaseDirectory 'commands_guide.md') -Force
}
$hash = (Get-FileHash -LiteralPath $releaseExe -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath $releaseChecksum -Value "$hash  LivePad.exe" -Encoding UTF8
$extensionHash = (Get-FileHash -LiteralPath $releaseExtension -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath $releaseExtensionChecksum -Value "$extensionHash  LivePad-Extension.zip" -Encoding UTF8
Write-Host "Instant-launch release: $releaseExe"
Write-Host "SHA-256: $hash"
Write-Host "Separate viewer extension: $releaseExtension"
Write-Host "Extension SHA-256: $extensionHash"
