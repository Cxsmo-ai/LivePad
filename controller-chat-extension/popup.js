"use strict";

const DEFAULTS = {
  deadzone: 0.14, triggerDeadzone: 0.05, curve: 1, quantizeStep: 5, cadenceMs: 0, gamepadIndex: -1,
  armedPlatforms: { tiktok: false, youtube: false, twitch: false }
};
const ALL_KEYS = ["deadzone", "curve", "quantizeStep", "cadenceMs", "gamepadIndex"];
let previewArmed = false;
const previewApi = {
  tabs: {
    query: async () => [{ id: 1 }],
    sendMessage: async (_id, message) => {
      if (message.type === "HM_SET_ARMED") previewArmed = Boolean(message.armed);
      return {
        ok: true, platform: "twitch", armed: previewArmed, visible: true,
        gamepad: { id: "Xbox Wireless Controller", index: 0, mapping: "standard" },
        packet: previewArmed ? "hm1 mfr5z7k0 1 0,80,35,0,100,100 40 1 1470" : "",
        lastError: "", lastSentAt: 0, version: "1.3.3",
        timing: { cadenceMs: 1550, keepaliveMs: 2500, leaseMs: 3500 }
      };
    }
  },
  storage: {
    sync: {
      get: (defaults, callback) => callback(defaults),
      set: async () => {}
    }
  }
};
const extensionApi = globalThis.chrome?.storage?.sync && globalThis.chrome?.tabs
  ? globalThis.chrome
  : previewApi;
const elements = Object.fromEntries([
  "platform", "controller", "relay", "arm", "message", "packet",
  "deadzone", "deadzoneValue", "curve", "quantizeStep", "cadenceMs", "gamepadIndex",
  "stateTiktok", "btnTiktok", "stateYoutube", "btnYoutube", "stateTwitch", "btnTwitch"
].map((id) => [id, document.getElementById(id)]));
let currentTab = null;
let armed = false;
let armedPlatforms = { tiktok: false, youtube: false, twitch: false };

function updatePlatformUI() {
  const map = [
    ["tiktok", elements.stateTiktok, elements.btnTiktok],
    ["youtube", elements.stateYoutube, elements.btnYoutube],
    ["twitch", elements.stateTwitch, elements.btnTwitch]
  ];
  for (const [platform, stateEl, btnEl] of map) {
    const isArmed = Boolean(armedPlatforms[platform]);
    if (stateEl) {
      stateEl.textContent = isArmed ? "Armed" : "Disarmed";
      stateEl.className = isArmed ? "platform-state armed" : "platform-state";
    }
    if (btnEl) {
      btnEl.textContent = isArmed ? `DISARM ${platform.toUpperCase()}` : `ARM ${platform.toUpperCase()}`;
      btnEl.classList.toggle("armed", isArmed);
    }
  }
}

function setMessage(text, error = false) {
  elements.message.textContent = text;
  elements.message.classList.toggle("error", error);
}

function setStatus(element, text, state = "") {
  element.textContent = text;
  element.className = state;
}

function render(status) {
  if (!status?.ok) {
    setStatus(elements.platform, "Unsupported page", "bad");
    setStatus(elements.controller, "Unavailable", "bad");
    setStatus(elements.relay, "Disarmed", "warn");
    if (status?.error) setMessage(status.error, true);
    armed = false;
    return;
  }
  armed = Boolean(status.armed);
  const platformLabel = String(status.platform || "unknown").toUpperCase();
  setStatus(elements.platform, status.version ? `${platformLabel} · v${status.version}` : platformLabel, status.platform === "unsupported" ? "bad" : "good");
  setStatus(elements.controller, status.gamepad?.id || "Press any button", status.gamepad ? "good" : "warn");
  setStatus(elements.relay, armed ? `Armed · ${status.timing?.cadenceMs || "?"} ms` : "Disarmed", armed ? "good" : "warn");
  elements.arm.textContent = armed ? "DISARM AND SEND NEUTRAL" : "ARM CONTROLLER CHAT";
  elements.arm.classList.toggle("armed", armed);
  elements.packet.textContent = status.packet || "No frame sent yet";
  if (status.lastError) setMessage(status.lastError, true);
  else if (armed) setMessage(`Changed inputs send within ${status.timing?.cadenceMs || "the selected cadence"} ms; steady holds refresh separately.`);
  if (status.armedPlatforms) {
    armedPlatforms = { ...armedPlatforms, ...status.armedPlatforms };
  }
  updatePlatformUI();
}

function supportsCurrentTab() {
  try {
    const host = new URL(currentTab?.url || "").hostname.toLowerCase();
    return ["tiktok.com", "twitch.tv", "youtube.com"].some((domain) => host === domain || host.endsWith(`.${domain}`));
  } catch (_) {
    return false;
  }
}

async function attachContentRuntime() {
  if (!currentTab?.id || !supportsCurrentTab() || !extensionApi.scripting?.executeScript) return false;
  await extensionApi.scripting.executeScript({
    target: { tabId: currentTab.id, allFrames: true },
    files: [
      "shared/protocol.js",
      "shared/gamepad_engine.js",
      "shared/dom_injector.js",
      "content.js"
    ]
  });
  return true;
}

async function sendToTop(message) {
  if (!currentTab?.id) return { ok: false, error: "No active tab" };
  try {
    return await extensionApi.tabs.sendMessage(currentTab.id, message, { frameId: 0 });
  } catch (_) {
    try {
      if (!await attachContentRuntime()) {
        return { ok: false, error: "Open a supported Twitch, YouTube, or TikTok LIVE tab" };
      }
      return await extensionApi.tabs.sendMessage(currentTab.id, message, { frameId: 0 });
    } catch (error) {
      return { ok: false, error: `Could not attach to this LIVE tab: ${String(error?.message || error)}` };
    }
  }
}

async function refresh() {
  [currentTab] = await extensionApi.tabs.query({ active: true, currentWindow: true });
  render(await sendToTop({ type: "HM_GET_STATUS" }));
}

async function togglePlatform(platform) {
  armedPlatforms[platform] = !armedPlatforms[platform];
  await extensionApi.storage.sync.set({ armedPlatforms });
  updatePlatformUI();
  const activePlatform = (elements.platform.textContent || "").toLowerCase();
  if (activePlatform.includes(platform)) {
    const result = await sendToTop({ type: "HM_SET_ARMED", armed: armedPlatforms[platform] });
    render(result);
  }
}

elements.btnTiktok?.addEventListener("click", () => togglePlatform("tiktok"));
elements.btnYoutube?.addEventListener("click", () => togglePlatform("youtube"));
elements.btnTwitch?.addEventListener("click", () => togglePlatform("twitch"));

elements.arm.addEventListener("click", async () => {
  const activePlatform = (elements.platform.textContent || "").toLowerCase();
  let target = "tiktok";
  if (activePlatform.includes("youtube")) target = "youtube";
  else if (activePlatform.includes("twitch")) target = "twitch";
  await togglePlatform(target);
});

async function saveSettings() {
  const values = {
    deadzone: Number(elements.deadzone.value) / 100,
    curve: Number(elements.curve.value),
    quantizeStep: Number(elements.quantizeStep.value),
    cadenceMs: Number(elements.cadenceMs.value),
    gamepadIndex: Number(elements.gamepadIndex?.value ?? -1)
  };
  elements.deadzoneValue.textContent = elements.deadzone.value;
  await extensionApi.storage.sync.set(values);
}

for (const key of ALL_KEYS) {
  if (elements[key]) {
    elements[key].addEventListener("input", saveSettings);
    elements[key].addEventListener("change", saveSettings);
  }
}

extensionApi.storage.sync.get(DEFAULTS, (values) => {
  elements.deadzone.value = Math.round(Number(values.deadzone) * 100);
  elements.deadzoneValue.textContent = elements.deadzone.value;
  elements.curve.value = String(values.curve);
  elements.quantizeStep.value = String(values.quantizeStep);
  elements.cadenceMs.value = String(values.cadenceMs);
  if (elements.gamepadIndex && values.gamepadIndex !== undefined) {
    elements.gamepadIndex.value = String(values.gamepadIndex);
  }
  if (values.armedPlatforms) {
    armedPlatforms = { ...armedPlatforms, ...values.armedPlatforms };
  }
  updatePlatformUI();
});

refresh();
