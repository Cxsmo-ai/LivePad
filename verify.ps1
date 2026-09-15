$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$dotnet = Join-Path $projectRoot '.dotnet\dotnet.exe'
if (-not (Test-Path -LiteralPath $dotnet)) {
    $dotnetCommand = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($dotnetCommand) { $dotnet = $dotnetCommand.Source }
}
if (-not (Test-Path -LiteralPath $dotnet) -and -not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw 'dotnet was not found. Install .NET 10 SDK or run the workflow setup step.'
}

& $dotnet build (Join-Path $projectRoot 'bridge\TikForever.HIDMaestro.csproj') --configuration Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Bridge build failed' }

& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Python tests failed' }

node --test (Join-Path $projectRoot 'controller-chat-extension\tests\protocol.test.js')
if ($LASTEXITCODE -ne 0) { throw 'Controller extension tests failed' }

& $python (Join-Path $projectRoot 'controller_test.py') w sprint ads fire right 35
if ($LASTEXITCODE -ne 0) { throw 'Controller compound-command test failed' }

& $python (Join-Path $projectRoot 'bridge_smoke_test.py')
if ($LASTEXITCODE -ne 0) { throw 'Bridge smoke test failed' }

$previousQtPlatform = $env:QT_QPA_PLATFORM
$env:QT_QPA_PLATFORM = 'offscreen'
try {
    & $python (Join-Path $projectRoot 'chat_gamepad_app.py') --smoke
    if ($LASTEXITCODE -ne 0) { throw 'Qt GUI smoke test failed' }
} finally {
    $env:QT_QPA_PLATFORM = $previousQtPlatform
}

& $python (Join-Path $projectRoot 'perf_test.py')
if ($LASTEXITCODE -ne 0) { throw 'Performance test failed' }
