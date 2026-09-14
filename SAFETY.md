# Safety boundary

TikForever-HIDMaestro only translates TikTok comments into ordinary virtual Xbox controller
state. It does not inspect or modify a game.

- No process or DLL injection
- No memory reading or writing
- No game patching, scripts, mod menus, or aimbot
- No anti-cheat bypass, driver hiding, or device-spoof evasion
- No automatic driver installation

The C# bridge uses HIDMaestro's documented `xbox-360-wired` profile and SDK state-submission API.
