# LivePad Controller Chat

This Manifest V3 Chrome extension turns one viewer's physical gamepad into compact `hm1`
controller snapshots and sends them through the live-chat composer on Twitch, YouTube, or
TikTok. It never connects directly to the streamer computer.

## Install for development

1. Open `chrome://extensions` (or `edge://extensions` in Microsoft Edge).
2. Enable **Developer mode**.
3. Choose **Load unpacked** and select this folder.
4. Open a supported live-chat page and sign in normally.
5. Press any controller button while the page is visible.
6. Open the extension and select **Arm Controller Chat**.

For a click-by-click Edge and Chrome walkthrough, see
[`docs/EXTENSION_INSTALL.md`](../docs/EXTENSION_INSTALL.md) in the repository.

The extension disarms when the tab becomes hidden. When neutral, no chat commands are sent;
the streamer engine automatically returns controls to center when leases expire.
It never reads or stores site passwords, cookies, or chat history. It will not overwrite text
already present in the composer.

The automatic cadence follows published platform limits where available. Do not lower it to
bypass a platform limit. Platform DOM and policies can change, and TikTok/YouTube restrict
automated service interaction; use only where you have permission and in accordance with the
platform's current terms.

Automatic changed-state cadence is 350 ms for TikTok, 1.55 seconds for Twitch, and 2 seconds
for YouTube. Steady active inputs use a separate keepalive and neutral state does not generate
repeating chat messages. Custom settings below 250 ms are experimental and may be throttled.

The fast path keeps one reusable extension Port for frame routing, remembers the last successful
chat frame, and caches the visible composer/send controls. These reduce local extension overhead;
they do not bypass chat moderation, server pacing, or platform rate limits.
