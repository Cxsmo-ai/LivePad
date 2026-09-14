# HID Maestro Streamer Edition

## Ready-to-run build

Run `release/HIDMaestroStreamerEdition.exe`. The single file includes the self-contained C# bridge and the official
HIDMaestro v1.7.3 SDK assembly; Python, Visual Studio, and a separate .NET installation are not
needed to run it.

Windows asks for administrator approval because HIDMaestro's controller shared memory requires
elevation on this machine. The app does not install or modify drivers automatically.

Enable TikTok, YouTube, Twitch, or any combination. Enter each public channel and select its
Connect button or **Connect All Enabled**. Twitch needs only the public channel username and
uses anonymous read-only IRC over `wss://irc-ws.chat.twitch.tv:443`; no password is stored.
Twitch officially guarantees IRC only with OAuth `chat:read`, so the app reports a clear error
if Twitch stops accepting anonymous readers. Comments such as
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

For an elevated, exact-comment end-to-end validation through the real virtual controller:

```powershell
.\.venv\Scripts\python.exe .\live_hardware_smoke_test.py CREATOR_USERNAME `
    --timeout 90 --report .\live-hardware-report.json
```

The harness ignores every comment except `w sprint ads fire right 35`, verifies all five actions
through XInput, clears the controller, verifies neutral state, and exits. Posting the exact test
comment is intentionally a separate user-authorized browser action.

The packaged executable also has an unattended real-hardware mode. It requests UAC, applies the
required five-part compound command, verifies it through XInput, verifies CLEAR and the bridge
watchdog, writes a JSON report, and exits:

```powershell
.\HIDMaestroStreamerEdition.exe --hardware-smoke --hardware-report hardware-smoke-report.json
```

```powershell
.\package.ps1
```

This publishes the self-contained bridge, builds the windowed application, runs the packaged
smoke test, and produces the single release EXE plus its SHA-256 checksum.
