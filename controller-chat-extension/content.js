(function () {
  "use strict";

  const runtimeKey = `__HM_CONTROLLER_CHAT_${chrome.runtime.getManifest().version.replaceAll(".", "_")}`;
  if (globalThis[runtimeKey]) return;
  globalThis[runtimeKey] = true;

  const isTop = window.top === window;
  const extensionVersion = chrome.runtime.getManifest().version;
  const DEFAULT_SETTINGS = Object.freeze({ deadzone: 0.14, triggerDeadzone: 0.05, curve: 1, quantizeStep: 5, cadenceMs: 0 });
  let armed = false;
  let settings = { ...DEFAULT_SETTINGS };
  let engine = new HMGamepad.FrameEngine();
  let selectedIndex = null;
  let sendPending = false;
  let lastPacket = "";
  let lastError = "";
  let lastSentAt = 0;
  let hud = null;

  function platformFromLocation() {
    const host = location.hostname.toLowerCase();
    if (host.endsWith("twitch.tv")) return "twitch";
    if (host.endsWith("youtube.com")) return "youtube";
    if (host.endsWith("tiktok.com")) return "tiktok";
    return "unsupported";
  }

  function gamepads() {
    try { return Array.from(navigator.getGamepads?.() || []).filter(Boolean); }
    catch (_) { return []; }
  }

  function activeGamepad() {
    const pads = gamepads();
    let pad = pads.find((item) => item.index === selectedIndex);
    if (!pad) pad = pads.find((item) => !item.mapping || item.mapping === "standard") || pads[0] || null;
    if (pad) selectedIndex = pad.index;
    return pad;
  }

  function status() {
    const pad = activeGamepad();
    return {
      ok: true,
      platform: platformFromLocation(),
      armed,
      visible: document.visibilityState === "visible",
      gamepad: pad ? { id: pad.id, index: pad.index, mapping: pad.mapping || "unmapped" } : null,
      packet: lastPacket,
      lastError,
      lastSentAt,
      version: extensionVersion,
      timing: HMGamepad.timingFor(platformFromLocation(), settings.cadenceMs),
      state: engine.current
    };
  }

  function ensureHud() {
    if (!isTop || hud || !document.documentElement) return;
    hud = document.createElement("div");
    hud.id = "deepascension-livepad-hud";
    Object.assign(hud.style, {
      position: "fixed", right: "16px", bottom: "16px", zIndex: "2147483647",
      display: "none", maxWidth: "360px", padding: "9px 12px",
      border: "1px solid #2C3037", borderRadius: "7px", background: "#191B20",
      color: "#E8EAEE", font: "600 12px/1.35 Segoe UI, sans-serif",
      boxShadow: "0 8px 28px rgba(0,0,0,.45)", pointerEvents: "none"
    });
    document.documentElement.appendChild(hud);
  }

  function updateHud(text, danger = false) {
    ensureHud();
    if (!hud) return;
    hud.style.display = armed || danger ? "block" : "none";
    hud.style.borderColor = danger ? "#EF4444" : "#6366F1";
    hud.style.color = danger ? "#F87171" : "#A5B4FC";
    hud.textContent = text;
  }

  async function route(packet, now) {
    if (sendPending) return;
    sendPending = true;
    try {
      const result = await chrome.runtime.sendMessage({
        type: "HM_ROUTE_PACKET", packet, platform: platformFromLocation()
      });
      if (!result?.ok) throw new Error(result?.error || "Chat send failed");
      engine.markSent(now, packet);
      lastPacket = packet;
      lastSentAt = Date.now();
      lastError = "";
      updateHud(`ARMED · ${platformFromLocation().toUpperCase()} v${extensionVersion} · sent ${packet}`);
    } catch (error) {
      lastError = String(error?.message || error);
      updateHud(`ARMED · ${platformFromLocation().toUpperCase()} v${extensionVersion} · ${lastError}`, true);
    } finally {
      sendPending = false;
    }
  }

  function maybeSend(now) {
    if (!armed || sendPending || document.visibilityState !== "visible") return;
    const packet = engine.packet(now, platformFromLocation(), settings.cadenceMs);
    if (packet) route(packet, now);
  }

  function poll(now) {
    if (isTop) {
      const pad = activeGamepad();
      if (pad) {
        try {
          engine.update(pad, settings);
          if (armed) updateHud(`ARMED · ${platformFromLocation().toUpperCase()} v${extensionVersion} · controller connected`);
          maybeSend(now);
        } catch (error) {
          lastError = String(error?.message || error);
          if (armed) updateHud(`ARMED · ${platformFromLocation().toUpperCase()} v${extensionVersion} · ${lastError}`, true);
        }
      } else if (armed) {
        lastError = "Press any controller button while this tab is visible";
        updateHud(`ARMED · ${platformFromLocation().toUpperCase()} v${extensionVersion} · ${lastError}`, true);
      }
    }
    requestAnimationFrame(poll);
  }

  async function disarm(sendNeutral = true) {
    if (armed && sendNeutral) {
      engine.neutral();
      const cadence = HMGamepad.timingFor(platformFromLocation(), settings.cadenceMs).cadenceMs;
      const sendAt = Math.max(performance.now(), engine.lastSentAt + cadence + 5);
      const delay = Math.max(0, sendAt - performance.now());
      setTimeout(() => {
        const now = performance.now();
        const packet = engine.packet(now, platformFromLocation(), settings.cadenceMs);
        if (packet) route(packet, now);
      }, delay);
    }
    armed = false;
    updateHud("");
  }

  document.addEventListener("visibilitychange", () => {
    if (isTop && armed && document.visibilityState !== "visible") disarm(true);
  });

  chrome.storage.sync.get(DEFAULT_SETTINGS, (stored) => { settings = { ...DEFAULT_SETTINGS, ...stored }; });
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "sync") return;
    for (const key of Object.keys(DEFAULT_SETTINGS)) if (changes[key]) settings[key] = changes[key].newValue;
  });

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "HM_GET_STATUS" && isTop) {
      sendResponse(status());
      return false;
    }
    if (message?.type === "HM_SET_ARMED" && isTop) {
      if (message.armed) {
        const platform = platformFromLocation();
        const pad = activeGamepad();
        if (platform === "unsupported") sendResponse({ ok: false, error: "Open Twitch, YouTube, or TikTok first" });
        else if (!pad) sendResponse({ ok: false, error: "Press a controller button while this page is visible, then try again" });
        else if (pad.mapping && pad.mapping !== "standard") sendResponse({ ok: false, error: "This controller has no standard browser mapping" });
        else {
          engine = new HMGamepad.FrameEngine();
          armed = true;
          lastError = "";
          updateHud(`ARMED · ${platform.toUpperCase()} v${extensionVersion} · move the controller`);
          sendResponse({ ok: true, ...status() });
        }
      } else {
        disarm(true).then(() => sendResponse({ ok: true, ...status() }));
        return true;
      }
      return false;
    }
    if (message?.type === "HM_INJECT_PACKET") {
      injectPacket(String(message.packet || ""), String(message.platform || ""))
        .then(sendResponse)
        .catch((error) => sendResponse({ ok: false, error: String(error?.message || error) }));
      return true;
    }
    return false;
  });

  async function injectPacket(packet, platform) {
    const submit = platform === "tiktok"
      ? () => chrome.runtime.sendMessage({ type: "HM_TIKTOK_SUBMIT" })
      : null;
    return HMInjector.injectPacket(packet, platform, submit);
  }

  if (isTop) requestAnimationFrame(poll);
})();
