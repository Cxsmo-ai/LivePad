# Building LivePad

## Local prerequisites

- Windows 10/11 x64
- Python 3.10 or newer
- Node.js 20 or newer
- .NET 10 SDK, either in `.dotnet/` or on `PATH`
- The vendored official HIDMaestro SDK assembly under `bridge/vendor/`

Install Python dependencies and run the full verification path:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\verify.ps1
```

Build the instant-launch application and complete bundle:

```powershell
.\package.ps1
.\bundle_all.ps1
```

The application is collected in `release/LivePad-Instant/LivePad.exe`. The
complete distribution is `release/LivePad-Complete.zip` and the extension-only
distribution is `release/LivePad-Extension.zip`.

## Test layers

`verify.ps1` runs:

1. C# bridge compilation.
2. Python unit and stress tests.
3. Browser-extension protocol tests.
4. Compound-command and mock named-pipe tests.
5. Offscreen Qt lifecycle smoke test.
6. Runtime performance checks.

Hardware smoke tests are separate because they require a real elevated
Windows session and an installed HIDMaestro environment:

```powershell
.\.venv\Scripts\python.exe live_hardware_smoke_test.py
```
