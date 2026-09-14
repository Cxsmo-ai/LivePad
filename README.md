# HID Maestro Streamer Edition

TikTok LIVE, YouTube LIVE, and Twitch comments drive one low-latency virtual Xbox 360
controller through HIDMaestro, independently or together in one unified chat.
The game receives ordinary XInput and requires no game-specific code, hooks, mods, or injection.

## Run the finished Windows build

Open `release/HIDMaestroStreamerEdition.exe`. Approve the Windows administrator prompt, enable
the desired stream sources, enter their public channel names/URLs, and connect them individually
or select **Connect All Enabled**. Twitch uses anonymous read-only IRC over secure WebSockets;
no Twitch password is requested or stored.

Compound comments execute together:

```text
w sprint ads fire right 35
```

That produces forward movement, left-stick click, full ADS, full fire, and 35% right camera at
the same time. Global **F12** pauses chat and immediately neutralizes the controller.

See [APP_USAGE.md](APP_USAGE.md), [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md), and
[SAFETY.md](SAFETY.md) for operation, verification results, and the strict non-cheat boundary.
The viewer-controller protocol, real latency limits, browser design, and source-backed platform
constraints are documented in [CONTROLLER_CHAT_ARCHITECTURE.md](CONTROLLER_CHAT_ARCHITECTURE.md).

## Physical controller through chat

Send `release/HIDMaestroControllerChat.zip` to a viewer separately from the streamer EXE. They
unzip it and load that folder from `chrome://extensions` using Developer mode. Their physical
controller is sampled in the browser and encoded into compact `hm1` full-state frames that still
travel only through Twitch, YouTube, or TikTok chat.

The extension is separate browser code and Chrome does not permit an ordinary portable EXE to
silently install it. The desktop application remains one EXE and the viewer extension remains one
separate ZIP; viewers do not need HIDMaestro,
.NET, Python, or the desktop app.

The extension is completely optional. Ordinary typed commands such as `w sprint ads fire right 35`
continue to work exactly as before, and typed-command viewers can play at the same time as viewers
using physical controllers through the extension.

## Build and verify from source

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\verify.ps1
.\package.ps1
```

The C# bridge targets .NET 10. `package.ps1` uses the project-local `.dotnet` SDK installed during
development and emits a self-contained bridge, so release users do not need .NET installed.

The official HIDMaestro v1.7.3 SDK license and third-party notices are retained under
`bridge/vendor/` and in the packaged application.
