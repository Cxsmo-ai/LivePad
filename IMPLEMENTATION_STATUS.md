# TikForever-HIDMaestro implementation status

The fork starts from TikForever commit `ddb30091c2ba0263dcd73fbcea872c13ff71aace`
on `claude/windows-tiktok-app-01PWfK7Bp8pSZ7dbZkz6hLKb`. Development is on
`hidmaestro-chatplays`.

## Completed

- TikTok LIVE comments are normalized and parsed as concurrent compound commands.
- Movement, camera, triggers, and buttons use monotonic timed leases with no sleeps or global cooldown.
- Repeated commands refresh one viewer's lease instead of multiplying that viewer's crowd weight.
- Left-stick crowd vectors are radially normalized; camera intent sums and clamps.
- Per-user token buckets independently limit movement, camera, buttons, and triggers.
- Command strengths, durations, and enabled states are editable live and saved atomically with backup recovery.
- Python and the C# bridge communicate over `TikForeverGamepad` using newline-delimited JSON.
- The bridge references the official HIDMaestro v1.7.3 SDK DLL and uses `xbox-360-wired`.
- The bridge never calls `InstallDriver()` and contains no game access, injection, hooks, or anti-cheat behavior.
- Changed-state submission runs on a configurable 250 Hz loop with 250 ms heartbeats.
- TikTok disconnect, Pause Chat, Clear Controller, shutdown, and global F12 all neutralize the pad.
- The bridge independently neutralizes once after a 1-second heartbeat timeout.
- TikTok reconnect uses bounded exponential backoff.
- The source and packaged PyQt app both have automated offscreen lifecycle tests.
- A read-only live-stream harness validates real TikTok comment ingestion without posting or interacting with viewers.
- An elevated unattended hardware harness verifies compound input, CLEAR, and watchdog neutralization through XInput.
- A self-contained Windows x64 release carries its own .NET runtime and the official HIDMaestro SDK.

## Automated verification

- 24 Python tests pass.
- C# bridge builds with zero warnings and zero errors.
- Required `w sprint ads fire right 35` state passes concurrently.
- 1,000-frame real named-pipe test passes at roughly 29,000 frames/second on this machine.
- C# malformed-message handling and the 1-second bridge watchdog are exercised end to end.
- 1,000-viewer / 5,000-command stress test remains far below the 4 ms resolver budget.
- The final windowed PyInstaller build passes its packaged bridge/startup/shutdown smoke test.
- A public `@typicalgamer` LIVE sample received 10 comments from 6 viewers in 30 seconds. Local processing measured 0.0368 ms median and 0.1518 ms p95.
- The real HIDMaestro controller exposed the five-part compound command through XInput, then returned to centered sticks with all triggers and buttons released after CLEAR.

## Real hardware verification

The packaged app was elevated with user-approved UAC and created the installed HIDMaestro
`xbox-360-wired` controller. XInput index 0 observed full movement, 35% camera input, both
triggers, and L3 concurrently at 78 ms, followed by a fully neutral state after CLEAR. The
packaged hardware harness also tests independent bridge-watchdog neutralization after Python
heartbeats stop. The app does not install or modify drivers automatically.

The only environment-specific check not represented by automated evidence is behavior inside a
particular game, because game installation, controller settings, and a running private session
are outside the application test harness. The output is a standard XInput Xbox 360 controller.
