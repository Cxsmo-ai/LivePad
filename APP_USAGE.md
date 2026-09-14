# TikTok Chat Gamepad

## Ready-to-run build

Extract `release/TikForeverChatGamepad-win-x64.zip`, then run
`TikForeverChatGamepad.exe`. The package includes the self-contained C# bridge and the official
HIDMaestro v1.7.3 SDK assembly; Python, Visual Studio, and a separate .NET installation are not
needed to run it.

Windows asks for administrator approval because HIDMaestro's controller shared memory requires
elevation on this machine. The app does not install or modify drivers automatically.

Enter the TikTok creator username and select **Connect**. Comments such as
`w sprint ads fire right 35` are applied concurrently. **Pause Chat** and global **F12** both
clear the controller immediately. The command table edits strength, duration, and enabled state
without restarting.

## Source verification

```powershell
.\verify.ps1
```

This builds the bridge, runs all Python tests, verifies compound controls, exercises 1,000 frames
through the actual named pipe, triggers the C# watchdog, runs the GUI offscreen, and reports local
throughput and latency.

`xinput_probe.py` is a read-only diagnostic that lists connected XInput controller state.

To sample a public LIVE without posting or sending controller output:

```powershell
.\.venv\Scripts\python.exe .\live_stream_smoke_test.py CREATOR_USERNAME --duration 30
```

The packaged executable also has an unattended real-hardware mode. It requests UAC, applies the
required five-part compound command, verifies it through XInput, verifies CLEAR and the bridge
watchdog, writes a JSON report, and exits:

```powershell
.\TikForeverChatGamepad.exe --hardware-smoke --hardware-report hardware-smoke-report.json
```

```powershell
.\package.ps1
```

This publishes the self-contained bridge, builds the windowed application, runs the packaged
smoke test, and produces the release ZIP plus its SHA-256 checksum.
