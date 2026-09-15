# Contributing to LivePad

Thank you for helping improve LivePad. Keep changes focused, testable, and
inside the chat-mediated controller boundary.

## Before opening a pull request

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test controller-chat-extension/tests/protocol.test.js
.\verify.ps1
```

Use the project dark slate/indigo tokens for UI work. Do not add light-theme
fallbacks, pure-white control fills, or platform-specific direct connections.

## Pull requests

- Explain the user-visible behavior and the safety impact.
- Include focused tests for parser, lease, rate-limit, protocol, or UI changes.
- Do not commit `.venv`, `build`, `dist`, `release`, logs, secrets, or tokens.
- Do not add game hooks, memory access, injection, anti-cheat bypasses, or
  driver-hiding behavior.
- Keep external platform credentials out of source and issue attachments.

Every push and pull request is checked by GitHub Actions on Windows. Release
tags additionally build the portable app, extension ZIP, command guide, and
SHA-256 manifests.
