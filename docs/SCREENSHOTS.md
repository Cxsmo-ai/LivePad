# LivePad visual assets

These images are maintained with the source repository so the product surface
can be reviewed without installing the application.

| Asset | Use |
| --- | --- |
| [livepad-desktop-preview.png](images/livepad-desktop-preview.png) | Readable README preview of the complete desktop workspace |
| [livepad-desktop-full.png](images/livepad-desktop-full.png) | Full-height desktop app capture |
| [commands_guide_16x9.png](images/commands_guide_16x9.png) | Stream overlay / desktop guide format |
| [commands_guide_9x16.png](images/commands_guide_9x16.png) | Mobile and vertical-stream guide format |
| [livepad_mark.png](images/livepad_mark.png) | Indigo LP brand mark |
| [app_icon.png](images/app_icon.png) | Desktop and package icon |

## Recreate the desktop captures

From the repository root:

```powershell
.\.venv\Scripts\python.exe tools\capture_ui_screenshots.py
```

The default capture uses Qt offscreen rendering for CI. To capture with the
native Windows font stack while developing locally:

```powershell
$env:LIVEPAD_CAPTURE_VISIBLE = '1'
.\.venv\Scripts\python.exe tools\capture_ui_screenshots.py
```

The capture uses a mock bridge and synthetic status/chat entries only. It never
connects to TikTok, YouTube, Twitch, or a game.
