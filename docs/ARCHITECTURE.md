# LivePad architecture

```text
TikTok / YouTube / Twitch chat
            |
            v
     normalized chat event
            |
            v
 parser + aliases + per-user limits
            |
            v
 timed lease state engine
            |
            v
 newline-delimited JSON named pipe
            |
            v
 C# HIDMaestro bridge -> xbox-360-wired -> XInput
```

Chat providers are isolated from controller timing. The state engine combines
movement vectors, camera pulses, trigger strengths, and digital-button leases
into one authoritative state. Only changed states are sent to the bridge.

The browser extension follows the same user-visible route: it samples a local
viewer controller, writes compact frames into the platform chat composer, and
never contacts the streamer machine directly.
