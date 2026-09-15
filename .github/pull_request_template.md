## What changed

<!-- Describe the user-visible behavior. -->

## Why

<!-- Explain the problem or feature. -->

## Verification

- [ ] `pytest -q`
- [ ] `node --test controller-chat-extension/tests/protocol.test.js`
- [ ] `./verify.ps1` (or explain why not)
- [ ] UI screenshots included for visual changes

## Safety checklist

- [ ] No game process access, injection, hooks, or memory reads/writes
- [ ] No direct viewer-to-streamer-PC connection
- [ ] Disconnect, clear, shutdown, and watchdog behavior remain neutral-safe
