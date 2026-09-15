# HIDMaestro bridge

This process owns one `xbox-360-wired` HIDMaestro controller and accepts the
Python state protocol on `\\.\pipe\LivePadGamepad`.

The bridge deliberately does **not** call `HMContext.InstallDriver()`. Driver
installation is an explicit machine setup step and should not happen as a side
effect of launching a stream controller.

The official v1.7.3 release's root `HIDMaestro.Core.dll` is vendored under
`bridge/vendor/` with its license and third-party notices. To use a different
official build, override the path at build time:

```powershell
$env:HIDMAESTRO_CORE_DLL = 'C:\path\to\HIDMaestro.Core.dll'
dotnet build .\bridge\LivePad.HIDMaestro.csproj
```

The bridge never calls `HMContext.InstallDriver()` automatically.
