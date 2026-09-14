# Controller-to-Chat Architecture

## Executive conclusion

The closest controller experience possible while requiring public chat as the only transport is
a **full-state lease protocol**, not a stream of words and not a queue of individual button
commands. The viewer extension samples a standard browser gamepad every animation frame, keeps
the newest complete state, preserves short button edges, and sends one compact `hm1` snapshot
whenever that viewer's platform cadence permits. The streamer app validates and applies the
snapshot atomically, then holds it only until its lease expires.

This design cannot equal a controller plugged directly into the streamer PC. Public chat imposes
rate limits, moderation, network transit, and variable delivery delay. Twitch documents one
message per second per channel for an ordinary non-moderator account, while YouTube documents up
to 11 live-chat messages per 30 seconds.^1,2 The design therefore makes each delivered message
as useful as possible and fails safely when the next one is delayed.

## End-to-end data path

```text
viewer gamepad
    -> browser Gamepad API sampled at display refresh
    -> radial deadzone, response curve, quantization
    -> full-state + tap-edge snapshot
    -> platform-safe coalescing
    -> normal Twitch / YouTube / TikTok chat composer
    -> public chat service
    -> HID Maestro Streamer Edition chat reader
    -> strict hm1 parser + replay rejection
    -> per-viewer controller lease
    -> crowd state resolver
    -> HIDMaestro xbox-360-wired controller
    -> XInput game
```

There is no browser-to-streamer socket, WebRTC channel, native messaging host, local HTTP server,
or hidden fallback transport.

## Why full snapshots are required

A delta protocol such as `press A`, `move forward`, and `release A` fails when a chat message is
dropped or reordered. A missed release can leave a control held; a missed press can make an action
disappear. A full snapshot restates both the active and neutral controls on every accepted frame.
The lease provides an independent stop condition if no replacement arrives.

Short presses present a second problem. A viewer can press and release A between two one-second
Twitch sends. The extension therefore carries both:

- a held-button mask representing the state at send time; and
- a rising-edge tap mask accumulating buttons pressed since the last successful send.

The host turns each tap bit into a bounded 120 ms lease. A bitmask records at least one press per
button between frames; it deliberately does not claim to preserve the exact timing or count of
multiple repeated taps inside one platform interval.

## Wire protocol

Version 1 is one ASCII line with seven whitespace-separated fields:

```text
hm1 SESSION SEQUENCE LX,LY,RX,RY,LT,RT HELD_HEX TAP_HEX LEASE_MS
```

Example:

```text
hm1 mfr5z7k0 2f -20,80,35,-10,75,100 41 5 1470
```

| Field | Meaning | Validation |
|---|---|---|
| `hm1` | Protocol and version | Exact, optional leading `!` |
| `SESSION` | Base-36 Unix-millisecond session epoch | 0 through signed 63-bit max |
| `SEQUENCE` | Base-36 sequence in that session | Strictly increasing |
| `LX,LY,RX,RY` | Signed stick percentages | -100 through 100 |
| `LT,RT` | Trigger percentages | 0 through 100 |
| `HELD_HEX` | Current digital-button bitmask | 15 supported Xbox controls |
| `TAP_HEX` | Rising edges since last successful send | Same mask |
| `LEASE_MS` | Maximum lifetime of held snapshot | 250 through 5000 ms |

The normal browser gamepad convention reports stick-up as negative. The extension inverts both Y
axes before encoding, so positive `LY` always means forward and positive `RY` means camera up.
This matches the desktop state engine and avoids the earlier reversed-W behavior.

Button bits are stable: A `0x0001`, B `0x0002`, X `0x0004`, Y `0x0008`, LB `0x0010`, RB
`0x0020`, L3 `0x0040`, R3 `0x0080`, Back `0x0100`, Start `0x0200`, Guide `0x0400`, D-pad Up
`0x0800`, Down `0x1000`, Left `0x2000`, and Right `0x4000`.

TikTok currently accepts a second, chat-friendly spelling of the same frame because its LIVE chat
can silently suppress comma-heavy machine-looking strings:

```text
pad mu1k4879 q2f e1ao w80 a20 lr35 ld10 lt75 rt100 h41 t5
```

`q` carries the base-36 sequence, `e` carries the base-36 lease, `w/s/a/d` describe left-stick
directions, `ll/lr/lu/ld` describe look directions, `lt/rt` are triggers, and `h/t` are the held
and tap masks. It decodes to the same `PadFrame` object and receives identical validation,
ordering, replay protection, atomic replacement, and lease expiry. Twitch and YouTube retain the
denser `hm1` spelling.

## Browser sampling and shaping

The W3C Gamepad specification recommends sampling alongside `requestAnimationFrame`, at the
animation frequency, and browsers expose gamepads only after a controller gesture to reduce
fingerprinting.^3 The extension consequently requires the page to be visible and the viewer to
press or move the controller once before arming.

Each stick receives a radial deadzone rather than independent per-axis clipping. Radial processing
preserves diagonal direction and constrains the final magnitude to one. The configurable response
curve is applied after deadzone removal. Values are then quantized, defaulting to five-percent
steps, so tiny device jitter does not create needless chat frames. Triggers have their own small
deadzone and remain analog.

The Gamepad API's `standard` mapping is preferred because it defines the familiar Xbox-style
indices. Unmapped controllers are rejected instead of silently assigning the wrong physical
buttons. The W3C API is intentionally low-level, and device mappings can differ when the browser
cannot supply `standard`.^3

## Scheduling and latency budget

Automatic starting cadences are:

| Platform | Extension cadence | Frame lease | Basis |
|---|---:|---:|---|
| Twitch | 1050 ms | 1470 ms | Official one-message-per-second channel limit |
| YouTube | 2800 ms | 3920 ms | Official 11 messages per 30 seconds limit |
| TikTok | 1200 ms | 1680 ms | Conservative configurable starting point; no stable official web-chat send API |

Sampling latency is normally one display frame, but cadence wait dominates. A controller change
arriving at a random point in a Twitch interval waits about 525 ms on average and up to roughly
1050 ms before the extension can attempt the next message. YouTube's corresponding cadence wait
is about 1400 ms average and 2800 ms worst case. Chat ingestion adds platform-dependent network,
moderation, and delivery delay after that. The desktop parser, resolver, named pipe, and XInput
submission remain sub-frame local work, but they cannot remove upstream chat delay.

For one viewer, movement is therefore stepped rather than native 60 Hz. For a crowd, messages from
different viewer accounts can arrive throughout each second, providing much denser aggregate
control while each account still follows its own platform limit. Leases turn those sparse snapshots
into continuous states between arrivals.

## Coalescing, ordering, and failure safety

Only the newest full analog state is retained while waiting to send. Button rising edges are ORed
into the pending tap mask. A pending edge sampled during asynchronous DOM injection is preserved
for the next frame rather than accidentally cleared.

The host tracks `(platform, user, session, sequence)`. Duplicate or lower sequences are rejected.
A lower session epoch is also rejected after a newer session has appeared, preventing a delayed
message from a previous page load from restoring stale movement. Frame-order memory is bounded.

Disarming and tab hiding queue a neutral full-state frame at the next legal cadence. If the page,
browser, or chat send fails before neutral arrives, the previous lease still expires. The extension
will not overwrite text the viewer has already typed into the composer; it pauses and reports that
condition instead.

## Chrome extension architecture

Chrome Manifest V3 content scripts run in isolated worlds and require declared host match patterns.
YouTube chat commonly lives in a child frame, so the extension declares `all_frames` and routes a
packet through the service worker to the frame containing the active composer.^4 The controller
poller runs only in the top frame, preventing duplicate gamepad sampling.

The package requests only storage, tab routing, web-navigation frame discovery, and the three
supported site origins. It does not collect credentials, cookies, browsing history, chat history,
or personal files. Chrome's extension guidance recommends treating host-page DOM as untrusted;
the injector uses fixed selectors, validates the packet grammar, writes plain text, and never uses
`eval` or remote code.^5

Platform DOM is not a stable API. Selectors may change without notice, and a site can reject
synthetic events. Deterministic fixtures verify the current Twitch, YouTube, and TikTok adapter
contracts, while a real signed-in live test remains necessary after a platform redesign.

## Platform policy boundary

Twitch publishes supported chat APIs and explicit bot/message limits. YouTube offers an authorized
`liveChatMessages.insert` API, which can return `rateLimitExceeded`, but this extension intentionally
uses the visible logged-in composer because the requested workflow is viewer-controlled input and
does not collect OAuth credentials.^6

YouTube's terms restrict automated access, and TikTok's current US terms restrict automated systems
and scripts used to interact with the service.^7,8 The extension does not bypass rate limits,
moderation, login, phone verification, subscriber-only mode, or any other platform control. It
must be used only where the account holder and stream owner permit it and where the platform's
current terms allow it. TikTok and YouTube DOM sending should be treated as compatibility modes,
not guaranteed public APIs.

## Verification completed

- Python parser and state-engine tests cover all ranges, invalid frames, button masks, taps, neutral,
  newer sessions, delayed old sessions, and replayed sequences.
- JavaScript tests cover axis signs, radial deadzones, analog triggers, the standard button map,
  tap retention, cadence, keepalive, and input edges sampled during an in-flight send.
- Deterministic browser fixtures pass for Twitch, YouTube, and TikTok composer injection.
- A real Manifest V3 Chromium context loads the service worker and injects a packet from the actual
  extension content script into an intercepted Twitch page.
- The existing desktop suite continues to cover compound text commands, crowd resolution, IPC,
  watchdog neutralization, the PyQt GUI, and real XInput hardware smoke testing.

## Sources

1. Twitch Developers. [Chat & Chatbots — Rate Limits](https://dev.twitch.tv/docs/chat/).
2. YouTube Help. [Learn about live streams](https://support.google.com/youtube/answer/15270973).
3. W3C. [Gamepad](https://www.w3.org/TR/gamepad/), Working Draft.
4. Chrome for Developers. [Content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts).
5. Chrome for Developers. [Stay secure](https://developer.chrome.com/docs/extensions/develop/security-privacy/stay-secure).
6. Google for Developers. [LiveChatMessages: insert](https://developers.google.com/youtube/v3/live/docs/liveChatMessages/insert).
7. YouTube. [Terms of Service](https://www.youtube.com/static?template=terms).
8. TikTok. [Terms of Service](https://www.tiktok.com/legal/page/us/terms-of-service/en).
