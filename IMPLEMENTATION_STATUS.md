# LivePad implementation status

This is the LivePad source tree and production branch. Internal compatibility
identifiers remain only where they are required by the bridge cache and existing
local installations.

## Completed

- TikTok LIVE, YouTube LIVE, and Twitch comments are normalized and parsed as concurrent compound commands.
- Twitch uses secure IRC-over-WebSocket with anonymous read-only login, IRCv3 tag parsing,
  PING/PONG, bounded deduplication, and automatic exponential-backoff reconnect.
- Twitch identity includes user ID, login/display name, badges, moderator, subscriber, VIP,
  first-message, channel, message ID, and server timestamp metadata.
- The unified chat renders a distinct vector logo for every platform and HTML-escapes all
  externally supplied names, messages, timestamps, and result text.
- Movement, camera, triggers, and buttons use monotonic timed leases with no sleeps or global cooldown.
- Repeated commands refresh one viewer's lease instead of multiplying that viewer's crowd weight.
- Left-stick crowd vectors are radially normalized; camera intent sums and clamps.
- Per-user token buckets independently limit movement, camera, buttons, and triggers.
- Command strengths, durations, and enabled states are editable live and saved atomically with backup recovery.
- Python and the C# bridge communicate over the local newline-delimited JSON pipe.
- The bridge references the official HIDMaestro v1.7.3 SDK DLL and uses `xbox-360-wired`.
- The bridge never calls `InstallDriver()` and contains no game access, injection, hooks, or anti-cheat behavior.
- Changed-state submission is serviced by a configurable scheduler up to 1000 Hz
  with precise 1 ms timer resolution; the GUI timer sleeps between the next lease deadline
  instead of polling every millisecond while neutral, and HIDMaestro receives only changed frames.
- TikTok disconnect, Pause Chat, Clear Controller, shutdown, and global F12 all neutralize the pad.
- The bridge independently neutralizes once after a 1-second heartbeat timeout.
- TikTok reconnect uses bounded exponential backoff.
- The source and packaged PyQt app both have automated offscreen lifecycle tests.
- A read-only live-stream harness validates real TikTok comment ingestion without posting or interacting with viewers.
- An elevated unattended hardware harness verifies compound input, CLEAR, and watchdog neutralization through XInput.
- A self-contained Windows x64 release carries its own .NET runtime and the official HIDMaestro SDK.
- A Chrome Manifest V3 viewer extension converts standard physical gamepads into compact, full-state
  `hm1` frames sent only through Twitch, YouTube, or TikTok chat.
- Controller frames include both held state and queued tap edges, monotonic sessions/sequences,
  replay rejection, bounded leases, explicit neutral frames, and corrected positive-forward Y.
- TikTok uses a chat-friendly `pad ... w80 lr35` frame because current LIVE chat silently filters
  comma-heavy controller strings; the host decodes both wire spellings into the same atomic state.
- The extension fast path uses a reusable Chrome Port, cached successful chat frame, and cached
  composer/send nodes; YouTube honors the server continuation timeout without a client-imposed
  one-second floor.
- The desktop app remains one EXE, while viewers receive a separate load-unpacked Chrome extension ZIP.

## Automated verification

- 79 Python tests and 11 JavaScript controller-protocol tests pass; extension/service-worker files
  also pass Node syntax checks.
- C# bridge builds with zero warnings and zero errors.
- Required `w sprint ads fire right 35` state passes concurrently.
- 1,000-frame real named-pipe test passes at roughly 29,000 frames/second on this machine.
- C# malformed-message handling and the 1-second bridge watchdog are exercised end to end.
- 1,000-viewer / 5,000-command stress test remains far below the 4 ms resolver budget.
- The final windowed PyInstaller build passes its packaged bridge/startup/shutdown smoke test.
- A public `@typicalgamer` LIVE sample received 10 comments from 6 viewers in 30 seconds. Local processing measured 0.0368 ms median and 0.1518 ms p95.
- The real HIDMaestro controller exposed the five-part compound command through XInput, then returned to centered sticks with all triggers and buttons released after CLEAR.
- A user-authorized public test comment completed the full TikTok LIVE -> TikTokLive -> parser -> named pipe -> HIDMaestro -> XInput path. All five actions were visible in XInput at 66.318 ms and the controller returned to neutral after CLEAR.

## Real hardware verification

The packaged app was elevated with user-approved UAC and created the installed HIDMaestro
`xbox-360-wired` controller. XInput index 0 observed full movement, 35% camera input, both
triggers, and L3 concurrently at 78 ms, followed by a fully neutral state after CLEAR. The
packaged hardware harness also tests independent bridge-watchdog neutralization after Python
heartbeats stop. The app does not install or modify drivers automatically.

The only environment-specific check not represented by automated evidence is behavior inside a
particular game, because game installation, controller settings, and a running private session
are outside the application test harness. The output is a standard XInput Xbox 360 controller.
