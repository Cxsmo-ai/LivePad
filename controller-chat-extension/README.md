# HID Maestro Controller Chat

This Manifest V3 Chrome extension turns one viewer's physical gamepad into compact `hm1`
controller snapshots and sends them through the live-chat composer on Twitch, YouTube, or
TikTok. It never connects directly to the streamer computer.

## Install for development

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Choose **Load unpacked** and select this folder.
4. Open a supported live-chat page and sign in normally.
5. Press any controller button while the page is visible.
6. Open the extension and select **Arm Controller Chat**.

The extension disarms when the tab becomes hidden and attempts to send a neutral snapshot.
It never reads or stores site passwords, cookies, or chat history. It will not overwrite text
already present in the composer.

The automatic cadence follows published platform limits where available. Do not lower it to
bypass a platform limit. Platform DOM and policies can change, and TikTok/YouTube restrict
automated service interaction; use only where you have permission and in accordance with the
platform's current terms.
