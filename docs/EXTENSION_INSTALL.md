# Install the LivePad browser extension

This guide is for viewers who want to use a physical controller from a browser
live-chat tab. The extension sends controller frames as chat messages; it never
connects directly to the streamer’s computer.

## 1. Get the extension folder

Download `LivePad-Extension.zip` from the [latest LivePad release](https://github.com/Cxsmo-ai/LivePad/releases/latest), then:

1. Right-click the ZIP file.
2. Choose **Extract All…**.
3. Extract it somewhere you will remember, such as `Documents\LivePad-Extension`.

Do not select the ZIP file itself in the browser. You must select the extracted
folder that contains `manifest.json`.

## 2. Load it in Microsoft Edge

1. Open Edge.
2. Type `edge://extensions` in the address bar and press **Enter**.
3. Turn on **Developer mode** using the switch on the left.
4. Click **Load unpacked**.
5. Select the extracted `LivePad-Extension` folder.
6. Click **Select Folder**.

The LivePad card should now appear on the extensions page. Pin it from the
puzzle-piece menu if you want the LivePad icon beside the address bar.

## 3. Load it in Google Chrome

1. Open Chrome.
2. Type `chrome://extensions` in the address bar and press **Enter**.
3. Turn on **Developer mode** in the top-right corner.
4. Click **Load unpacked**.
5. Select the extracted `LivePad-Extension` folder.
6. Click **Select Folder**.

Pin LivePad from the puzzle-piece menu for quick access.

## 4. Connect and arm a live chat

1. Plug in your controller before opening the live-chat page.
2. Open a supported TikTok LIVE, YouTube LIVE, or Twitch chat.
3. Keep that chat tab visible and active.
4. Click the LivePad extension icon.
5. Choose the controller shown in the popup.
6. Choose which platform to use and click **Arm Controller Chat**.
7. Press a controller button or move a stick. A compact LivePad message should
   appear in the chat composer and send according to that platform’s cadence.

The extension automatically disarms when the chat tab is hidden. Neutral input
does not create repeating messages. The streamer app must have the matching
platform armed before viewer input can affect its resolved controller state.

## Updating after a new download

1. Extract the new ZIP into a new folder, or replace the old extracted folder.
2. Return to `edge://extensions` or `chrome://extensions`.
3. Find LivePad and click **Reload**.
4. If the old card is still present, remove it and use **Load unpacked** on the
   new folder.

If **Load unpacked** is missing, Developer mode is still off. If the browser
reports that `manifest.json` is missing, select the inner folder that directly
contains `manifest.json`, rather than the outer download folder.

## Safety and privacy

LivePad does not request passwords, cookies, or direct access to the streamer
PC. Use the extension only in chats where you have permission, and follow the
current rules and policies of the platform you are using.
